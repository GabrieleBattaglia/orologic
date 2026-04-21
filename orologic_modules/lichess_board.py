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
        self.last_clock_sync = time.time()
        self.started = False
        self.is_live = False
        self.move_history = []

    def get_clocks(self):
        w_time = self.white_time
        b_time = self.black_time
        if self.started:
            elapsed = time.time() - self.last_clock_sync
            if self.board.turn == chess.WHITE:
                w_time = max(0, w_time - elapsed)
            else:
                b_time = max(0, b_time - elapsed)
        return w_time, b_time


def format_time(seconds):
    return board_utils.FormatTime(seconds)


def save_lichess_game(game_state, result_str="*"):
    from .easyfish import pgn_handler
    import io

    pgn_text = ""
    # Se abbiamo un game_id, proviamo a scaricare il PGN completo e ufficiale da Lichess
    if hasattr(game_state, "game_id") and game_state.game_id:
        try:
            url = f"https://lichess.org/game/export/{game_state.game_id}?clocks=false&evals=false"
            req = urllib.request.Request(url)
            if hasattr(game_state, "token") and game_state.token:
                req.add_header("Authorization", f"Bearer {game_state.token}")

            with urllib.request.urlopen(req) as resp:
                pgn_text = resp.read().decode("utf-8")
        except Exception:
            pgn_text = ""  # Fallback alla ricostruzione manuale se il download fallisce

    if pgn_text:
        try:
            # Carichiamo il PGN scaricato in un oggetto Game per validarlo e salvarlo tramite pgn_handler
            game = chess.pgn.read_game(io.StringIO(pgn_text))
            if game:
                pgn_handler.SaveGameToFile(game)
                print(
                    _(
                        "La partita e' stata scaricata da Lichess e salvata nella cartella PGN."
                    )
                )
                return
        except Exception:
            pass  # Procedi con la ricostruzione manuale se il parsing fallisce

    # Ricostruzione manuale (Fallback)
    game = chess.pgn.Game()

    def clean_name(name_str):
        if " (" in name_str:
            return name_str.split(" (")[0]
        return name_str

    game.headers["Event"] = "Lichess Game"
    if hasattr(game_state, "game_id") and game_state.game_id:
        game.headers["Site"] = f"https://lichess.org/{game_state.game_id}"
    else:
        game.headers["Site"] = "Lichess"

    game.headers["White"] = clean_name(game_state.white_player)
    game.headers["Black"] = clean_name(game_state.black_player)

    # Mappatura risultato Lichess a PGN standard
    res_map = {"white": "1-0", "black": "0-1", "draw": "1/2-1/2"}
    game.headers["Result"] = res_map.get(result_str, "*")

    # Se la posizione iniziale non è quella standard, impostiamo i tag FEN
    if game_state.board.epd() != chess.Board().epd():
        # Dobbiamo tornare alla posizione iniziale per il PGN se non è standard
        # Ma game_state.board è quella attuale.
        # Per semplicità in questo fallback, usiamo l'initial_fen se disponibile o assumiamo standard
        pass

    node = game
    temp_board = chess.Board()  # Qui servirebbe il FEN iniziale se non standard
    for san in game_state.move_history:
        try:
            move = temp_board.parse_san(san)
            node = node.add_variation(move)
            temp_board.push(move)
        except ValueError:
            break

    try:
        pgn_handler.SaveGameToFile(game)
        print(
            _("La partita e' stata salvata nella cartella PGN (ricostruzione locale).")
        )
    except Exception as e:
        print(_("Errore nel salvataggio della partita PGN: {e}").format(e=e))


def handle_exploration_command(user_input, game_state):
    # Ripresa da lichess_app.py
    if user_input.startswith("/"):
        Acusticator(
            [
                "c5",
                0.07,
                -1,
                config.VOLUME,
                "d5",
                0.07,
                -0.75,
                config.VOLUME,
                "e5",
                0.07,
                -0.5,
                config.VOLUME,
                "f5",
                0.07,
                -0.25,
                config.VOLUME,
                "g5",
                0.07,
                0,
                config.VOLUME,
                "a5",
                0.07,
                0.25,
                config.VOLUME,
                "b5",
                0.07,
                0.5,
                config.VOLUME,
                "c6",
                0.07,
                0.75,
                config.VOLUME,
            ],
            kind=3,
            adsr=[0, 0, 100, 100],
        )
        base_column = user_input[1:2].strip()
        ui.read_diagonal(game_state, base_column, True)
        return True
    elif user_input.startswith("\\"):
        Acusticator(
            [
                "c5",
                0.07,
                1,
                config.VOLUME,
                "d5",
                0.07,
                0.75,
                config.VOLUME,
                "e5",
                0.07,
                0.5,
                config.VOLUME,
                "f5",
                0.07,
                0.25,
                config.VOLUME,
                "g5",
                0.07,
                0,
                config.VOLUME,
                "a5",
                0.07,
                -0.25,
                config.VOLUME,
                "b5",
                0.07,
                -0.5,
                config.VOLUME,
                "c6",
                0.07,
                -0.75,
                config.VOLUME,
            ],
            kind=3,
            adsr=[0, 0, 100, 100],
        )
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
            Acusticator(
                [
                    "c5",
                    0.07,
                    0,
                    config.VOLUME,
                    "d5",
                    0.07,
                    0,
                    config.VOLUME,
                    "e5",
                    0.07,
                    0,
                    config.VOLUME,
                    "f5",
                    0.07,
                    0,
                    config.VOLUME,
                    "g5",
                    0.07,
                    0,
                    config.VOLUME,
                    "a5",
                    0.07,
                    0,
                    config.VOLUME,
                    "b5",
                    0.07,
                    0,
                    config.VOLUME,
                    "c6",
                    0.07,
                    0,
                    config.VOLUME,
                ],
                kind=3,
                adsr=[0, 0, 100, 100],
            )
            ui.read_file(game_state, param)
        elif len(param) == 1 and param.isdigit():
            rank_number = int(param)
            if 1 <= rank_number <= 8:
                Acusticator(
                    [
                        "g5",
                        0.07,
                        -1,
                        config.VOLUME,
                        "g5",
                        0.07,
                        -0.75,
                        config.VOLUME,
                        "g5",
                        0.07,
                        -0.5,
                        config.VOLUME,
                        "g5",
                        0.07,
                        -0.25,
                        config.VOLUME,
                        "g5",
                        0.07,
                        0,
                        config.VOLUME,
                        "g5",
                        0.07,
                        0.25,
                        config.VOLUME,
                        "g5",
                        0.07,
                        0.5,
                        config.VOLUME,
                        "g5",
                        0.07,
                        0.75,
                        config.VOLUME,
                    ],
                    kind=3,
                    adsr=[0, 0, 100, 100],
                )
                ui.read_rank(game_state, rank_number)
            else:
                print(_("Traversa non valida."))
        elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
            Acusticator(["d#4", 0.7, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            ui.read_square(game_state, param)
        else:
            print(_("Comando dash non riconosciuto."))
        return True
    elif user_input == "+":
        Acusticator(["c4", 0.07, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        ui.report_all_pieces(game_state, chess.BLACK)
        return True
    elif user_input.startswith(","):
        Acusticator(
            [
                "a3",
                0.06,
                -1,
                config.VOLUME,
                "c4",
                0.06,
                -0.5,
                config.VOLUME,
                "d#4",
                0.06,
                0.5,
                config.VOLUME,
                "f4",
                0.06,
                1,
                config.VOLUME,
            ],
            kind=3,
            adsr=[20, 5, 70, 25],
        )
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
                        q.put(
                            f"End:{d['status'].get('name', 'unknown')}|{d.get('winner', 'none')}"
                        )
    except Exception as e:
        q.put(f"Error: {e}")
    q.put("EOF")


def async_spectator_loop(q, game_state):
    buf = []

    def get_prompt():
        if not game_state.move_history:
            return _("\nInizio, mossa 0.>")
        elif len(game_state.move_history) % 2 == 1:
            return "\n{num}. {last_move}>".format(
                num=(len(game_state.move_history) + 1) // 2,
                last_move=game_state.move_history[-1],
            )
        else:
            return "\n{num}... {last_move}>".format(
                num=len(game_state.move_history) // 2,
                last_move=game_state.move_history[-1],
            )

    def refresh_line():
        sys.stdout.write("\r" + " " * 79 + "\r")
        sys.stdout.write(get_prompt() + "".join(buf))
        sys.stdout.flush()

    refresh_line()

    while True:
        try:
            msg = q.get_nowait()
            if msg == "EOF":
                sys.stdout.write(
                    "\n" + _("Partita terminata o connessione chiusa.") + "\n"
                )
                return None
            elif msg.startswith("Error:"):
                sys.stdout.write(
                    "\n"
                    + _("Errore durante lo streaming: {e}").format(e=msg[7:])
                    + "\n"
                )
                return None
            elif msg.startswith("Move:"):
                uci_move, wc, bc = msg[5:].split("|")
                move = game_state.board.parse_uci(uci_move)
                desc = board_utils.DescribeMove(move, game_state.board)
                san_move = game_state.board.san(move)

                is_white_turn = game_state.board.turn == chess.WHITE
                turn_name = (
                    game_state.white_player
                    if is_white_turn
                    else game_state.black_player
                )

                game_state.board.push(move)
                game_state.move_history.append(san_move)
                if wc != "None":
                    game_state.white_time = int(float(wc))
                if bc != "None":
                    game_state.black_time = int(float(bc))

                if game_state.is_live:
                    sys.stdout.write("\r" + " " * 79 + "\r")
                    sys.stdout.write(
                        _("{turn} gioca: {desc}\n").format(turn=turn_name, desc=desc)
                    )
                    Acusticator(
                        [
                            "c5",
                            0.05,
                            0,
                            config.VOLUME,
                            "e5",
                            0.05,
                            0,
                            config.VOLUME,
                            "g5",
                            0.05,
                            0,
                            config.VOLUME,
                        ],
                        kind=1,
                        adsr=[0, 0, 100, 5],
                    )
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
                w, wr, b, br = msg[8:].split("|")
                new_w = f"{w} ({wr})"
                new_b = f"{b} ({br})"
                if game_state.white_player != new_w or game_state.black_player != new_b:
                    game_state.white_player = new_w
                    game_state.black_player = new_b
                    sys.stdout.write("\r" + " " * 79 + "\r")
                    sys.stdout.write(
                        _("Partita: {wp} vs {bp}\n").format(
                            wp=game_state.white_player, bp=game_state.black_player
                        )
                    )
                    refresh_line()
            elif msg.startswith("End:"):
                status_name, winner = msg[4:].split("|")
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
                    "aborted": _("Partita annullata"),
                }.get(status_name, status_name)

                if winner == "white":
                    winner_str = _("Il Bianco vince")
                elif winner == "black":
                    winner_str = _("Il Nero vince")
                else:
                    winner_str = _("Nessun vincitore")

                sys.stdout.write("\r" + " " * 79 + "\r")
                sys.stdout.write(
                    _("\nPartita terminata: {s}. {w}.\n").format(
                        s=status_tr, w=winner_str
                    )
                )
                Acusticator(
                    [
                        "c5",
                        0.1,
                        -0.5,
                        config.VOLUME,
                        "e5",
                        0.1,
                        0,
                        config.VOLUME,
                        "g5",
                        0.1,
                        0.5,
                        config.VOLUME,
                        "c6",
                        0.2,
                        0,
                        config.VOLUME,
                    ],
                    kind=1,
                    adsr=[2, 8, 90, 0],
                )
                save_lichess_game(game_state, winner)
                refresh_line()
        except queue.Empty:
            if not game_state.is_live and game_state.started:
                game_state.is_live = True
                sys.stdout.write("\r" + " " * 79 + "\r")
                sys.stdout.write(_("La scacchiera e' pronta!\n"))
                refresh_line()

        if msvcrt.kbhit():
            c = msvcrt.getwch()
            if c in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue

            if c == "\r" or c == "\n":
                sys.stdout.write("\n")
                return "".join(buf)
            elif c == "\b":
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif c == "\x03":  # Ctrl+C
                sys.stdout.write("\n")
                return "."
            elif c == "\x1b":  # ESC
                sys.stdout.write("\n")
                return "."
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
    t = threading.Thread(
        target=_spectate_worker, args=(req, q, stop_event), daemon=True
    )
    t.start()

    print(
        _(
            "\nConnessione al tavolo in corso... (Premi ESC o digita . per interrompere l'osservazione)"
        )
    )

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
            w_time, _b_time = game_state.get_clocks()
            Acusticator(["a6", 0.14, -1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(
                _("\nTempo {p}: {t}").format(
                    p=game_state.white_player, t=format_time(w_time)
                )
            )
        elif cmd == ".2":
            _w_time, b_time = game_state.get_clocks()
            Acusticator(["b6", 0.14, 1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(
                _("\nTempo {p}: {t}").format(
                    p=game_state.black_player, t=format_time(b_time)
                )
            )
        elif cmd == ".3":
            w_time, b_time = game_state.get_clocks()
            Acusticator(["e7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(
                _("\nTempo {p}: {t}").format(
                    p=game_state.white_player, t=format_time(w_time)
                )
            )
            print(
                _("Tempo {p}: {t}").format(
                    p=game_state.black_player, t=format_time(b_time)
                )
            )
        elif cmd == ".4":
            w_time, b_time = game_state.get_clocks()
            Acusticator(["f7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            diff = abs(w_time - b_time)
            adv = _("bianco") if w_time > b_time else _("nero")
            print(
                _("\n{player} in vantaggio di {t}").format(
                    player=adv, t=format_time(diff)
                )
            )
        elif cmd == ".5":
            Acusticator(["f4", 0.54, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            player = (
                game_state.white_player
                if game_state.board.turn == chess.WHITE
                else game_state.black_player
            )
            print(_("\nOrologio di {player} in moto").format(player=player))
        elif cmd == ".m":
            Acusticator(
                [
                    "c4",
                    0.1,
                    -1,
                    config.VOLUME,
                    "e4",
                    0.1,
                    -0.3,
                    config.VOLUME,
                    "g4",
                    0.1,
                    0.3,
                    config.VOLUME,
                    "c5",
                    0.1,
                    1,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 80, 10],
            )
            w_mat, b_mat = board_utils.CalculateMaterial(game_state.board)
            print(
                _("\nMateriale: {wp} {wm}, {bp} {bm}").format(
                    wp=game_state.white_player,
                    wm=w_mat,
                    bp=game_state.black_player,
                    bm=b_mat,
                )
            )
        elif cmd == ".l":
            Acusticator(
                [900.0, 0.1, 0, config.VOLUME, 440.0, 0.3, 0, config.VOLUME],
                kind=1,
                adsr=[1, 0, 80, 19],
            )
            summary = ui.GenerateMoveSummary(game_state)
            if summary:
                print(_("\nLista mosse giocate:\n"))
                for line in summary:
                    print(line)
            else:
                print(_("\nNessuna mossa ancora giocata."))
        elif cmd == ".b":
            Acusticator(
                [
                    "c4",
                    0.2,
                    -1,
                    config.VOLUME,
                    "g4",
                    0.2,
                    -0.3,
                    config.VOLUME,
                    "c5",
                    0.2,
                    0.3,
                    config.VOLUME,
                    "e5",
                    0.2,
                    1,
                    config.VOLUME,
                    "g5",
                    0.4,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[10, 5, 80, 5],
            )
            print("\n" + str(game_state.board))
        elif cmd == ".?":
            print(_("\nComandi disponibili:"))
            print(_(".1 : Tempo Bianco"))
            print(_(".2 : Tempo Nero"))
            print(_(".3 : Tempo di entrambi"))
            print(_(".4 : Confronto tempi"))
            print(_(".5 : A chi tocca muovere"))
            print(_(".m : Materiale in gioco"))
            print(_(".l : Lista mosse"))
            print(_(".b : Mostra scacchiera"))
            print(_(".  : Esci"))
        else:
            print(_("\nComando non riconosciuto. Usa .? per l'aiuto."))


class GamePlayState:
    def __init__(self, board, my_username):
        self.board = board
        self.my_username = my_username
        self.my_color = chess.WHITE
        self.white_player = _("Bianco")
        self.black_player = _("Nero")
        self.white_time = 0
        self.black_time = 0
        self.last_clock_sync = time.time()
        self.started = False
        self.move_history = []
        self.premove = None
        self.game_id = None
        self.token = None
        self.opponent_gone = False
        self.opponent_gone_announced = False
        self.claim_win_in_seconds = None

    def get_clocks(self):
        w_time = self.white_time
        b_time = self.black_time
        if self.started:
            elapsed = time.time() - self.last_clock_sync
            if self.board.turn == chess.WHITE:
                w_time = max(0, w_time - elapsed)
            else:
                b_time = max(0, b_time - elapsed)
        return w_time, b_time


def _play_worker(req, q, stop_event):
    try:
        with urllib.request.urlopen(req) as resp:
            for line in resp:
                if stop_event.is_set():
                    break
                if line.strip():
                    d = json.loads(line.decode("utf-8"))
                    q.put(d)
    except Exception as e:
        q.put({"type": "error", "error": str(e)})
    q.put({"type": "eof"})


def send_action(game_id, token, action, uci=None, chat_text=None):
    import urllib.parse

    url = f"https://lichess.org/api/board/game/{game_id}/{action}"
    if action == "move":
        url += f"/{uci}"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    data = None
    if action == "chat" and chat_text:
        data = urllib.parse.urlencode({"room": "player", "text": chat_text}).encode(
            "utf-8"
        )
    try:
        with urllib.request.urlopen(req, data=data) as resp:
            return resp.status == 200
    except Exception:
        return False


def async_play_loop(q, game_state):
    buf = []

    def get_prompt():
        wt = getattr(game_state, "white_time", 0)
        bt = getattr(game_state, "black_time", 0)
        if getattr(game_state, "started", False) and getattr(
            game_state, "last_clock_sync", None
        ):
            elapsed = time.time() - game_state.last_clock_sync
            if game_state.board.turn == chess.WHITE:
                wt = max(0, wt - elapsed)
            else:
                bt = max(0, bt - elapsed)

        def fmt(sec):
            sec = max(0, int(sec))
            m, s = divmod(sec, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            if d > 0:
                d_str = _("{d}g").format(d=d)
                return f"{d_str} {h:02d}:{m:02d}:{s:02d}"
            if h > 0:
                return f"{h}:{m:02d}:{s:02d}"
            return f"{m:02d}:{s:02d}"

        clock_str = (
            f"{fmt(wt)} {fmt(bt)} " if getattr(game_state, "started", False) else ""
        )

        p = ""
        if not game_state.move_history:
            p = clock_str + _("Inizio, mossa 0. ")
        elif len(game_state.move_history) % 2 == 1:
            p = "{c}{num}. {last_move} ".format(
                c=clock_str,
                num=(len(game_state.move_history) + 1) // 2,
                last_move=game_state.move_history[-1],
            )
        else:
            p = "{c}{num}... {last_move} ".format(
                c=clock_str,
                num=len(game_state.move_history) // 2,
                last_move=game_state.move_history[-1],
            )

        if hasattr(game_state, "premove") and game_state.premove:
            p = p.rstrip() + f" [{game_state.premove}] "

        if hasattr(game_state, "opponent_gone") and game_state.opponent_gone:
            claim_in = getattr(game_state, "claim_win_in_seconds", 0)
            if claim_in and claim_in > 0:
                elapsed_gone = int(
                    time.time() - getattr(game_state, "opponent_gone_time", time.time())
                )
                rem = max(0, claim_in - elapsed_gone)
                if rem > 0:
                    p = p.rstrip() + f" [CLAIM IN {rem}s] "
                else:
                    p = p.rstrip() + " [CLAIM] "
            else:
                p = p.rstrip() + " [CLAIM] "

        return p

    def refresh_line():
        sys.stdout.write("\r" + " " * 79 + "\r")
        sys.stdout.write(get_prompt() + "".join(buf))
        sys.stdout.flush()

    last_refresh = time.time()
    refresh_line()

    while True:
        if time.time() - last_refresh >= 1.0:
            refresh_line()
            last_refresh = time.time()
        try:
            msg = q.get_nowait()
            if msg.get("type") == "eof":
                sys.stdout.write("\n" + _("Connessione al server chiusa.") + "\n")
                return None
            elif msg.get("type") == "error":
                sys.stdout.write(
                    "\n"
                    + _("Errore durante lo streaming: {e}").format(e=msg.get("error"))
                    + "\n"
                )
                return None
            elif msg.get("type") == "gameFull":
                game_state.game_id = msg.get("id")
                w = msg.get("white", {})
                b = msg.get("black", {})

                w_name = w.get("name", w.get("id", _("Anonimo")))
                if "aiLevel" in w:
                    w_name = f"Stockfish level {w['aiLevel']}"
                w_rat = w.get("rating", "?")

                b_name = b.get("name", b.get("id", _("Anonimo")))
                if "aiLevel" in b:
                    b_name = f"Stockfish level {b['aiLevel']}"
                b_rat = b.get("rating", "?")

                game_state.white_player = f"{w_name} ({w_rat})"
                game_state.black_player = f"{b_name} ({b_rat})"

                if w.get("id") == game_state.my_username.lower():
                    game_state.my_color = chess.WHITE
                elif b.get("id") == game_state.my_username.lower():
                    game_state.my_color = chess.BLACK

                fen = msg.get("initialFen", "startpos")
                if fen == "startpos":
                    game_state.board.reset()
                else:
                    game_state.board.set_fen(fen)

                state = msg.get("state", {})
                moves = state.get("moves", "").strip()
                if moves:
                    for uci_move in moves.split(" "):
                        move = game_state.board.parse_uci(uci_move)
                        game_state.move_history.append(game_state.board.san(move))
                        game_state.board.push(move)

                game_state.white_time = int(state.get("wtime", 0)) / 1000.0
                game_state.black_time = int(state.get("btime", 0)) / 1000.0
                game_state.last_clock_sync = time.time()

                sys.stdout.write("\r" + " " * 79 + "\r")
                sys.stdout.write(
                    _("Partita: {wp} vs {bp}\n").format(
                        wp=game_state.white_player, bp=game_state.black_player
                    )
                )
                col_str = (
                    _("Bianco") if game_state.my_color == chess.WHITE else _("Nero")
                )
                sys.stdout.write(_("Tu sei il {c}!\n").format(c=col_str))
                game_state.started = True
                refresh_line()

            elif msg.get("type") == "gameState":
                moves = msg.get("moves", "").strip()
                new_moves = moves.split(" ") if moves else []
                current_ply = len(game_state.move_history)

                if len(new_moves) > current_ply:
                    # Apply new moves
                    for i in range(current_ply, len(new_moves)):
                        uci_move = new_moves[i]
                        move = game_state.board.parse_uci(uci_move)
                        desc = board_utils.DescribeMove(move, game_state.board)
                        san_move = game_state.board.san(move)

                        is_white_turn = game_state.board.turn == chess.WHITE
                        turn_name = (
                            game_state.white_player
                            if is_white_turn
                            else game_state.black_player
                        )

                        game_state.board.push(move)
                        game_state.move_history.append(san_move)

                        sys.stdout.write("\r" + " " * 79 + "\r")
                        sys.stdout.write(
                            _("{turn} gioca: {desc}\n").format(
                                turn=turn_name, desc=desc
                            )
                        )
                        if is_white_turn == (game_state.my_color == chess.WHITE):
                            # It was my move
                            Acusticator(
                                [
                                    "c5",
                                    0.05,
                                    0,
                                    config.VOLUME,
                                    "e5",
                                    0.05,
                                    0,
                                    config.VOLUME,
                                    "g5",
                                    0.05,
                                    0,
                                    config.VOLUME,
                                ],
                                kind=1,
                                adsr=[0, 0, 100, 5],
                            )
                        else:
                            # Opponent played a move, meaning it's now my turn!
                            Acusticator(
                                [
                                    "c5",
                                    0.05,
                                    0,
                                    config.VOLUME,
                                    "e5",
                                    0.05,
                                    0,
                                    config.VOLUME,
                                    "g5",
                                    0.05,
                                    0,
                                    config.VOLUME,
                                ],
                                kind=1,
                                adsr=[0, 0, 100, 5],
                            )
                            Acusticator(
                                [1000.0, 0.05, 0, config.VOLUME],
                                kind=1,
                                adsr=[0, 0, 100, 0],
                            )  # Extra beep for my turn

                game_state.white_time = int(msg.get("wtime", 0)) / 1000.0
                game_state.black_time = int(msg.get("btime", 0)) / 1000.0
                game_state.last_clock_sync = time.time()

                status = msg.get("status", "started")
                if status != "started":
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
                        "aborted": _("Partita annullata"),
                    }.get(status, status)

                    winner = msg.get("winner")
                    if winner == "white":
                        winner_str = _("Il Bianco vince")
                    elif winner == "black":
                        winner_str = _("Il Nero vince")
                    else:
                        winner_str = _("Nessun vincitore")

                    sys.stdout.write("\r" + " " * 79 + "\r")
                    sys.stdout.write(
                        _("\nPartita terminata: {s}. {w}.\n").format(
                            s=status_tr, w=winner_str
                        )
                    )
                    Acusticator(
                        [
                            "c5",
                            0.1,
                            -0.5,
                            config.VOLUME,
                            "e5",
                            0.1,
                            0,
                            config.VOLUME,
                            "g5",
                            0.1,
                            0.5,
                            config.VOLUME,
                            "c6",
                            0.2,
                            0,
                            config.VOLUME,
                        ],
                        kind=1,
                        adsr=[2, 8, 90, 0],
                    )
                    save_lichess_game(game_state, winner)
                    return None

                # Evaluate premove
                if game_state.board.turn == game_state.my_color and game_state.premove:
                    try:
                        move = game_state.board.parse_san(game_state.premove)
                        uci = move.uci()
                        sys.stdout.write("\r" + " " * 79 + "\r")
                        sys.stdout.write(
                            _("Eseguo premove: {m}...\n").format(m=game_state.premove)
                        )
                        threading.Thread(
                            target=send_action,
                            args=(game_state.game_id, game_state.token, "move", uci),
                            daemon=True,
                        ).start()
                    except Exception:
                        sys.stdout.write("\r" + " " * 79 + "\r")
                        sys.stdout.write(
                            _("La premove ({m}) non e' piu' valida.\n").format(
                                m=game_state.premove
                            )
                        )
                    game_state.premove = None

                refresh_line()
            elif msg.get("type") == "chatLine":
                user = msg.get("username", "Sistema")
                text = msg.get("text", "")
                if user.lower() != game_state.my_username.lower() and user != "lichess":
                    sys.stdout.write("\r" + " " * 79 + "\r")
                    sys.stdout.write(_("{u} dice: {t}\n").format(u=user, t=text))
                    Acusticator(
                        [800.0, 0.1, 0, config.VOLUME, 1200.0, 0.1, 0, config.VOLUME],
                        kind=2,
                    )
                    refresh_line()
            elif msg.get("type") == "opponentGone":
                gone = msg.get("gone")
                claim_in = msg.get("claimWinInSeconds")
                game_state.opponent_gone = gone
                game_state.claim_win_in_seconds = claim_in
                game_state.opponent_gone_time = time.time()
                if gone and not getattr(game_state, "opponent_gone_announced", False):
                    sys.stdout.write("\r" + " " * 79 + "\r")
                    sys.stdout.write(
                        _(
                            "L'avversario ha lasciato la partita. Puoi reclamare la vittoria (comando: claim).\n"
                        )
                    )
                    Acusticator(
                        [400.0, 0.2, 0, config.VOLUME, 300.0, 0.2, 0, config.VOLUME],
                        kind=1,
                    )
                    game_state.opponent_gone_announced = True
                    refresh_line()
                elif not gone and game_state.opponent_gone_announced:
                    # Se l'avversario torna
                    game_state.opponent_gone_announced = False
                    sys.stdout.write("\r" + " " * 79 + "\r")
                    sys.stdout.write(_("L'avversario e' tornato in partita.\n"))
                    Acusticator(
                        [300.0, 0.2, 0, config.VOLUME, 400.0, 0.2, 0, config.VOLUME],
                        kind=1,
                    )
                    refresh_line()
                else:
                    if gone:
                        refresh_line()  # To update the prompt with [CLAIM]
        except queue.Empty:
            pass

        if msvcrt.kbhit():
            c = msvcrt.getwch()
            if c in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue

            if c == "\r" or c == "\n":
                sys.stdout.write("\n")
                return "".join(buf)
            elif c == "\b":
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif c == "\x03":  # Ctrl+C
                sys.stdout.write("\n")
                return "."
            elif c == "\x1b":  # ESC
                sys.stdout.write("\n")
                return "."
            elif c.isprintable():
                buf.append(c)
                sys.stdout.write(c)
                sys.stdout.flush()

        time.sleep(0.02)


def show_post_game_report(game_id, token):
    print(_("\n--- Recupero Report Partita da Lichess (Attendi...) ---"))
    time.sleep(2)
    req = urllib.request.Request(
        f"https://lichess.org/game/export/{game_id}?evals=true&clocks=false"
    )
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        try:
            req_an = urllib.request.Request(
                f"https://lichess.org/api/game/{game_id}/analyze", method="POST"
            )
            req_an.add_header("Authorization", f"Bearer {token}")
            urllib.request.urlopen(req_an)
        except Exception:
            pass

    data = None
    for i in range(4):
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            w = data.get("players", {}).get("white", {})
            b = data.get("players", {}).get("black", {})
            if "analysis" in w or "analysis" in b:
                break
        except Exception:
            pass
        time.sleep(1.5)

    if not data:
        print(_("Impossibile recuperare il report della partita."))
        return

    w = data.get("players", {}).get("white", {})
    b = data.get("players", {}).get("black", {})

    print(_("\n[Risultato Elo]"))
    rated = data.get("rated", False)
    if rated:

        def format_elo(p):
            name = p.get("user", {}).get("name", _("Anonimo"))
            rating = p.get("rating", "?")
            diff = p.get("ratingDiff")
            diff_str = f"+{diff}" if diff and diff > 0 else str(diff) if diff else "0"
            return f"{name}: {rating} ({diff_str})"

        print(_("Bianco ({b})").format(b=format_elo(w)))
        print(_("Nero ({n})").format(n=format_elo(b)))
    else:
        print(_("Partita amichevole (nessuna variazione Elo)."))

    print(_("\n[Analisi Computer]"))

    def format_analysis(p):
        an = p.get("analysis")
        if not an:
            return _("Nessuna analisi disponibile.")
        return _("Inesattezze: {i}, Errori: {m}, Svarioni: {b}, ACPL: {a}").format(
            i=an.get("inaccuracy", 0),
            m=an.get("mistake", 0),
            b=an.get("blunder", 0),
            a=an.get("acpl", 0),
        )

    w_name = w.get("user", {}).get("name", _("Bianco"))
    b_name = b.get("user", {}).get("name", _("Nero"))
    print(_("{u} (Bianco): {a}").format(u=w_name, a=format_analysis(w)))
    print(_("{u} (Nero): {a}").format(u=b_name, a=format_analysis(b)))

    from GBUtils import enter_escape

    enter_escape(_("\nPremi Invio per continuare..."))


def play_game(game_id, token, username):
    req = urllib.request.Request(f"https://lichess.org/api/board/game/stream/{game_id}")
    req.add_header("Authorization", f"Bearer {token}")

    q = queue.Queue()
    stop_event = threading.Event()
    t = threading.Thread(target=_play_worker, args=(req, q, stop_event), daemon=True)
    t.start()

    from GBUtils import enter_escape

    print(
        _(
            "\nConnessione al tavolo in corso... (Premi ESC o digita . per abbandonare la visuale)"
        )
    )

    board = board_utils.CustomBoard()
    game_state = GamePlayState(board, username)
    game_state.token = token

    while True:
        user_input = async_play_loop(q, game_state)

        if user_input is None:
            show_post_game_report(game_id, token)
            break

        user_input = user_input.strip()
        if not user_input:
            if game_state.premove:
                game_state.premove = None
                print(_("Premove annullata."))
            continue

        if user_input == "." or user_input.lower() == ".q":
            if enter_escape(
                _(
                    "Vuoi davvero disconnetterti da questa partita? Non la abbandonerai su Lichess (Invio = Si', Esc = No): "
                )
            ):
                stop_event.set()
                break
            continue

        if user_input.startswith("_"):
            chat_text = user_input[1:].strip()
            if chat_text:
                threading.Thread(
                    target=send_action,
                    args=(game_id, token, "chat", None, chat_text),
                    daemon=True,
                ).start()
                print(_("Messaggio inviato."))
            continue

        cmd = user_input.lower()
        if cmd == "resign":
            if enter_escape(
                _("Sei sicuro di voler abbandonare (resign)? (Invio = Si', Esc = No): ")
            ):
                send_action(game_id, token, "resign")
            continue
        elif cmd == "draw":
            print(_("Offerta di patta inviata."))
            send_action(game_id, token, "draw/yes")
            continue
        elif cmd == "takeback":
            print(_("Richiesta di annullamento mossa inviata."))
            send_action(game_id, token, "takeback/yes")
            continue
        elif cmd == "claim":
            if game_state.claim_win_in_seconds and game_state.claim_win_in_seconds > 0:
                print(
                    _(
                        "Troppo presto. Potrai reclamare la vittoria tra {s} secondi."
                    ).format(s=game_state.claim_win_in_seconds)
                )
            else:
                print(_("Tentativo di reclamare la vittoria (claim victory)..."))
                if send_action(game_id, token, "claim-victory"):
                    print(_("Vittoria reclamata con successo!"))
                else:
                    print(_("Impossibile reclamare la vittoria in questo momento."))
            continue

        if handle_exploration_command(user_input, game_state):
            continue

        if cmd == ".1":
            w_time, _b_time = game_state.get_clocks()
            Acusticator(["a6", 0.14, -1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(
                _("\nTempo {p}: {t}").format(
                    p=game_state.white_player, t=format_time(w_time)
                )
            )
        elif cmd == ".2":
            _w_time, b_time = game_state.get_clocks()
            Acusticator(["b6", 0.14, 1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(
                _("\nTempo {p}: {t}").format(
                    p=game_state.black_player, t=format_time(b_time)
                )
            )
        elif cmd == ".3":
            w_time, b_time = game_state.get_clocks()
            Acusticator(["e7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            print(
                _("\nTempo {p}: {t}").format(
                    p=game_state.white_player, t=format_time(w_time)
                )
            )
            print(
                _("Tempo {p}: {t}").format(
                    p=game_state.black_player, t=format_time(b_time)
                )
            )
        elif cmd == ".4":
            w_time, b_time = game_state.get_clocks()
            Acusticator(["f7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            diff = abs(w_time - b_time)
            adv = _("bianco") if w_time > b_time else _("nero")
            print(
                _("\n{player} in vantaggio di {t}").format(
                    player=adv, t=format_time(diff)
                )
            )
        elif cmd == ".5":
            Acusticator(["f4", 0.54, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            player = (
                game_state.white_player
                if game_state.board.turn == chess.WHITE
                else game_state.black_player
            )
            print(_("\nOrologio di {player} in moto").format(player=player))
        elif cmd == ".m":
            Acusticator(
                [
                    "c4",
                    0.1,
                    -1,
                    config.VOLUME,
                    "e4",
                    0.1,
                    -0.3,
                    config.VOLUME,
                    "g4",
                    0.1,
                    0.3,
                    config.VOLUME,
                    "c5",
                    0.1,
                    1,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 80, 10],
            )
            w_mat, b_mat = board_utils.CalculateMaterial(game_state.board)
            print(
                _("\nMateriale: {wp} {wm}, {bp} {bm}").format(
                    wp=game_state.white_player,
                    wm=w_mat,
                    bp=game_state.black_player,
                    bm=b_mat,
                )
            )
        elif cmd == ".l":
            Acusticator(
                [900.0, 0.1, 0, config.VOLUME, 440.0, 0.3, 0, config.VOLUME],
                kind=1,
                adsr=[1, 0, 80, 19],
            )
            summary = ui.GenerateMoveSummary(game_state)
            if summary:
                print(_("\nLista mosse giocate:\n"))
                for line in summary:
                    print(line)
            else:
                print(_("\nNessuna mossa ancora giocata."))
        elif cmd == ".b":
            Acusticator(
                [
                    "c4",
                    0.2,
                    -1,
                    config.VOLUME,
                    "g4",
                    0.2,
                    -0.3,
                    config.VOLUME,
                    "c5",
                    0.2,
                    0.3,
                    config.VOLUME,
                    "e5",
                    0.2,
                    1,
                    config.VOLUME,
                    "g5",
                    0.4,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[10, 5, 80, 5],
            )
            print("\n" + str(game_state.board))
        elif cmd == ".?":
            print(_("\nComandi disponibili per giocare:"))
            print(_(".1 : Tempo Bianco"))
            print(_(".2 : Tempo Nero"))
            print(_(".3 : Tempo di entrambi"))
            print(_(".4 : Confronto tempi"))
            print(_(".5 : A chi tocca muovere"))
            print(_(".m : Materiale in gioco"))
            print(_(".l : Lista mosse"))
            print(_(".b : Mostra scacchiera"))
            print(_("draw : Proponi patta"))
            print(_("resign : Abbandona la partita"))
            print(_("takeback : Chiedi di ritirare la mossa"))
            print(_("claim : Reclama vittoria per abbandono avversario"))
            print(_("_[testo] : Invia un messaggio in chat (es. _Ciao)"))
            print(_(".  : Esci dalla visuale (non abbandona la partita)"))
        else:
            if not game_state.started:
                print(_("La partita non e' ancora iniziata!"))
                continue

            try:
                raw_input = board_utils.NormalizeMove(user_input)
                move = game_state.board.parse_san(raw_input)
                is_valid = True
            except ValueError:
                try:
                    move = game_state.board.parse_uci(raw_input)
                    is_valid = True
                except ValueError:
                    is_valid = False

            if is_valid:
                if game_state.board.turn == game_state.my_color:
                    uci = move.uci()
                    threading.Thread(
                        target=send_action,
                        args=(game_id, token, "move", uci),
                        daemon=True,
                    ).start()
                else:
                    game_state.premove = raw_input
                    print(
                        _(
                            "Premove impostata: {m}. Verra' giocata al tuo turno."
                        ).format(m=raw_input)
                    )
            else:
                Acusticator([600.0, 0.6, 0, config.VOLUME], adsr=[5, 0, 35, 90])
                print(_("Mossa non valida. Digita .? per l'aiuto."))
