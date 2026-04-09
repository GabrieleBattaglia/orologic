import json
import urllib.request
import threading
import queue
import msvcrt
import time
import sys
import chess

from GBUtils import Acusticator
from . import board_utils, config, ui

def _(testo):
    from .config import L10N
    return L10N.get(testo, testo)

class SpectatorGameState:
    def __init__(self, board):
        self.board = board
        self.white_player = _("Bianco")
        self.black_player = _("Nero")
        self.white_time = 0
        self.black_time = 0
        self.started = False
        self.is_live = False
        self.move_history = []

def format_time(seconds):
    return board_utils.FormatTime(seconds)

def handle_exploration_command(user_input, game_state):
    # Ripresa da lichess_app.py
    if user_input.startswith("/"):
        Acusticator(["c5", 0.07, -1, config.VOLUME,"d5", 0.07, -.75, config.VOLUME,"e5", 0.07, -.5, config.VOLUME,"f5", 0.07, -.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"a5", 0.07, .25, config.VOLUME,"b5", 0.07, .5, config.VOLUME,"c6", 0.07, .75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
        base_column = user_input[1:2].strip()
        ui.read_diagonal(game_state, base_column, True)
        return True
    elif user_input.startswith("\\"):
        Acusticator(["c5", 0.07, 1, config.VOLUME,"d5", 0.07, 0.75, config.VOLUME,"e5", 0.07, 0.5, config.VOLUME,"f5", 0.07, 0.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"a5", 0.07, -0.25, config.VOLUME,"b5", 0.07, -0.5, config.VOLUME,"c6", 0.07, -0.75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
        base_column = user_input[1:2].strip()
        ui.read_diagonal(game_state, base_column, False)
        return True
    elif user_input.startswith("-"):
        param = user_input[1:].strip()
        if not param:
            Acusticator(["c5", 0.07, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            ui.report_all_pieces(game_state, chess.WHITE)
            return True
        elif len(param) == 1 and param.isalpha():
            Acusticator(["c5", 0.07, 0, config.VOLUME, "d5", 0.07, 0, config.VOLUME, "e5", 0.07, 0, config.VOLUME, "f5", 0.07, 0, config.VOLUME, "g5", 0.07, 0, config.VOLUME, "a5", 0.07, 0, config.VOLUME, "b5", 0.07, 0, config.VOLUME, "c6", 0.07, 0, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
            ui.read_file(game_state, param)
        elif len(param) == 1 and param.isdigit():
            rank_number = int(param)
            if 1 <= rank_number <= 8:
                Acusticator(["g5", 0.07, -1, config.VOLUME,"g5", 0.07, -.75, config.VOLUME,"g5", 0.07, -.5, config.VOLUME,"g5", 0.07, -.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"g5", 0.07, .25, config.VOLUME,"g5", 0.07, .5, config.VOLUME,"g5", 0.07, .75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
                ui.read_rank(game_state, rank_number)
            else:
                print(_("Traversa non valida."))
        elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
            Acusticator(["d#4", .7, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            ui.read_square(game_state, param)
        else:
            print(_("Comando dash non riconosciuto."))
        return True
    elif user_input == "+":
        Acusticator(["c4", 0.07, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        ui.report_all_pieces(game_state, chess.BLACK)
        return True
    elif user_input.startswith(","):
        Acusticator(["a3", .06, -1, config.VOLUME, "c4", .06, -0.5, config.VOLUME, "d#4", .06, 0.5, config.VOLUME, "f4", .06, 1, config.VOLUME], kind=3, adsr=[20, 5, 70, 25])
        ui.report_piece_positions(game_state, user_input[1:2])
        return True
    return False

def _spectate_worker(req, q, stop_event):
    try:
        with urllib.request.urlopen(req) as resp:
            for line in resp:
                if stop_event.is_set():
                    break
                if line.strip():
                    d = json.loads(line.decode("utf-8"))
                    if "players" in d:
                        w = d["players"]["white"]
                        b = d["players"]["black"]
                        w_name = w.get("user", {}).get("name", "Anonimo")
                        w_rat = w.get("rating", "?")
                        b_name = b.get("user", {}).get("name", "Anonimo")
                        b_rat = b.get("rating", "?")
                        q.put(f"Players:{w_name}|{w_rat}|{b_name}|{b_rat}")
                    
                    if "initialFen" in d:
                        q.put(f"Start:{d['initialFen']}")
                    elif "fen" in d and "lm" not in d:
                        q.put(f"Start:{d['fen']}")
                        
                    if "lm" in d:
                        wc = d.get("wc", "None")
                        bc = d.get("bc", "None")
                        q.put(f"Move:{d['lm']}|{wc}|{bc}")
                        
                    if "status" in d and isinstance(d["status"], dict):
                        q.put(f"End:{d['status'].get('name', 'unknown')}|{d.get('winner', 'none')}")
    except Exception as e:
        q.put(f"Error: {e}")
    q.put("EOF")

def async_spectator_loop(q, game_state):
    buf = []
    
    def get_prompt():
        if not game_state.move_history:
            return _("\nInizio, mossa 0. ")
        elif len(game_state.move_history) % 2 == 1:
            return "\n{num}. {last_move} ".format(num=(len(game_state.move_history)+1)//2, last_move=game_state.move_history[-1])
        else:
            return "\n{num}... {last_move} ".format(num=len(game_state.move_history)//2, last_move=game_state.move_history[-1])

    def refresh_line():
        sys.stdout.write('\r' + ' ' * 79 + '\r')
        sys.stdout.write(get_prompt() + ''.join(buf))
        sys.stdout.flush()

    refresh_line()

    while True:
        try:
            msg = q.get_nowait()
            if msg == "EOF":
                sys.stdout.write('\n' + _("Partita terminata o connessione chiusa.") + '\n')
                return None
            elif msg.startswith("Error:"):
                sys.stdout.write('\n' + _("Errore durante lo streaming: {e}").format(e=msg[7:]) + '\n')
                return None
            elif msg.startswith("Move:"):
                uci_move, wc, bc = msg[5:].split('|')
                move = game_state.board.parse_uci(uci_move)
                desc = board_utils.DescribeMove(move, game_state.board)
                san_move = game_state.board.san(move)
                
                is_white_turn = (game_state.board.turn == chess.WHITE)
                turn_name = game_state.white_player if is_white_turn else game_state.black_player
                
                game_state.board.push(move)
                game_state.move_history.append(san_move)
                if wc != 'None': game_state.white_time = int(float(wc))
                if bc != 'None': game_state.black_time = int(float(bc))
                
                if game_state.is_live:
                    sys.stdout.write('\r' + ' ' * 79 + '\r')
                    sys.stdout.write(_("Il {turn} gioca: {desc}\n").format(turn=turn_name, desc=desc))
                    Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
                    refresh_line()
            elif msg.startswith("Start:"):
                fen = msg[6:]
                if fen == "start":
                    game_state.board.reset()
                else:
                    game_state.board.set_fen(fen)
                if not game_state.started:
                    game_state.started = True
            elif msg.startswith("Players:"):
                w, wr, b, br = msg[8:].split('|')
                new_w = f"{w} ({wr})"
                new_b = f"{b} ({br})"
                if game_state.white_player != new_w or game_state.black_player != new_b:
                    game_state.white_player = new_w
                    game_state.black_player = new_b
                    sys.stdout.write('\r' + ' ' * 79 + '\r')
                    sys.stdout.write(_("Partita: {wp} vs {bp}\n").format(wp=game_state.white_player, bp=game_state.black_player))
                    refresh_line()
            elif msg.startswith("End:"):
                status_name, winner = msg[4:].split('|')
                status_tr = {
                    "mate": _("Scacco matto"),
                    "resign": _("Abbandono"),
                    "stalemate": _("Stallo"),
                    "timeout": _("Tempo scaduto"),
                    "draw": _("Patta"),
                    "outoftime": _("Tempo scaduto"),
                    "cheat": _("Vittoria a tavolino (Cheat)"),
                    "noStart": _("Partita non iniziata"),
                    "unknownFinish": _("Fine sconosciuta"),
                    "variantEnd": _("Fine variante"),
                    "aborted": _("Partita annullata")
                }.get(status_name, status_name)
                
                if winner == "white":
                    winner_str = _("Il Bianco vince")
                elif winner == "black":
                    winner_str = _("Il Nero vince")
                else:
                    winner_str = _("Nessun vincitore")
                
                sys.stdout.write('\r' + ' ' * 79 + '\r')
                sys.stdout.write(_("\nPartita terminata: {s}. {w}.\n").format(s=status_tr, w=winner_str))
                Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
                refresh_line()
        except queue.Empty:
            if not game_state.is_live and game_state.started:
                game_state.is_live = True
                sys.stdout.write('\r' + ' ' * 79 + '\r')
                sys.stdout.write(_("La scacchiera e' pronta!\n"))
                refresh_line()

        if msvcrt.kbhit():
            c = msvcrt.getwch()
            if c in ('\x00', '\xe0'):
                msvcrt.getwch()
                continue
            
            if c == '\r' or c == '\n':
                sys.stdout.write('\n')
                return ''.join(buf)
            elif c == '\b':
                if buf:
                    buf.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif c == '\x03': # Ctrl+C
                sys.stdout.write('\n')
                return '.'
            elif c == '\x1b': # ESC
                sys.stdout.write('\n')
                return '.'
            elif c.isprintable():
                buf.append(c)
                sys.stdout.write(c)
                sys.stdout.flush()
                
        time.sleep(0.02)

def spectate_game(game_id, token=None):
    req = urllib.request.Request(f"https://lichess.org/api/stream/game/{game_id}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    q = queue.Queue()
    stop_event = threading.Event()
    t = threading.Thread(target=_spectate_worker, args=(req, q, stop_event), daemon=True)
    t.start()
    
    print(_("\nConnessione al tavolo in corso... (Premi ESC o digita . per interrompere l'osservazione)"))
    
    board = board_utils.CustomBoard()
    game_state = SpectatorGameState(board)
    
    while True:
        user_input = async_spectator_loop(q, game_state)
        
        if user_input is None:
            # Stream ended or error
            break
            
        user_input = user_input.strip()
        
        if not user_input:
            continue
            
        if user_input == "." or user_input.lower() == ".q":
            print(_("\nOsservazione interrotta."))
            stop_event.set()
            break
            
        if handle_exploration_command(user_input, game_state):
            continue
            
        cmd = user_input.lower()
        if cmd == ".1":
            Acusticator(['a6', 0.14, -1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(_("\nTempo {p}: {t}").format(p=game_state.white_player, t=format_time(game_state.white_time)))
        elif cmd == ".2":
            Acusticator(['b6', 0.14, 1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(_("\nTempo {p}: {t}").format(p=game_state.black_player, t=format_time(game_state.black_time)))
        elif cmd == ".3":
            Acusticator(['e7', 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(_("\nTempo {p}: {t}").format(p=game_state.white_player, t=format_time(game_state.white_time)))
            print(_("Tempo {p}: {t}").format(p=game_state.black_player, t=format_time(game_state.black_time)))
        elif cmd == ".4":
            Acusticator(['f7', 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            diff = abs(game_state.white_time - game_state.black_time)
            adv = _("bianco") if game_state.white_time > game_state.black_time else _("nero")
            print(_("\n{player} in vantaggio di {t}").format(player=adv, t=format_time(diff)))
        elif cmd == ".5":
            print(_("\nStato orologi: {wp} {wt} - {bp} {bt}").format(
                wp=game_state.white_player, wt=format_time(game_state.white_time),
                bp=game_state.black_player, bt=format_time(game_state.black_time)))
        elif cmd == ".m":
            Acusticator(["c4", 0.1, -1, config.VOLUME, "e4", 0.1, -0.3, config.VOLUME, "g4", 0.1, 0.3, config.VOLUME, "c5", 0.1, 1, config.VOLUME], kind=1, adsr=[2, 8, 80, 10])
            w_mat, b_mat = board_utils.CalculateMaterial(game_state.board)
            print(_("\nMateriale: {wp} {wm}, {bp} {bm}").format(wp=game_state.white_player, wm=w_mat, bp=game_state.black_player, bm=b_mat))
        elif cmd == ".l":
            Acusticator([900.0, 0.1, 0, config.VOLUME, 440.0, 0.3, 0, config.VOLUME], kind=1, adsr=[1, 0, 80, 19])
            summary = ui.GenerateMoveSummary(game_state)
            if summary:
                print(_("\nLista mosse giocate:\n"))
                for line in summary:
                    print(line)
            else:
                print(_("\nNessuna mossa ancora giocata."))
        elif cmd == ".b":
            Acusticator(["c4", 0.2, -1, config.VOLUME, "g4", 0.2, -0.3, config.VOLUME, "c5", 0.2, 0.3, config.VOLUME, "e5", 0.2, 1, config.VOLUME, "g5", 0.4, 0, config.VOLUME], kind=1, adsr=[10, 5, 80, 5])
            print("\n" + str(game_state.board))
        elif cmd == ".?":
            print(_("\nComandi disponibili:"))
            print(_(".1 : Tempo Bianco"))
            print(_(".2 : Tempo Nero"))
            print(_(".3 : Tempo di entrambi"))
            print(_(".4 : Confronto tempi"))
            print(_(".5 : Stato orologi"))
            print(_(".m : Materiale in gioco"))
            print(_(".l : Lista mosse"))
            print(_(".b : Mostra scacchiera"))
            print(_(".  : Esci"))
        else:
            print(_("\nComando non riconosciuto. Usa .? per l'aiuto."))

