import json
import msvcrt
import queue
import sys
import threading
import time

import chess

from GBUtils import Acusticator

from . import board_utils, config, rete, tempo, ui
from .config import _


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
        self.refresh_interval = 1
        self.initial_fen = chess.STARTING_FEN
        self.variant = "standard"

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


format_time = tempo.parlato


def save_lichess_game(game_state, result_str="*"):
    import io

    from .easyfish import pgn_handler

    if getattr(game_state, "saved", False):
        return
    game_state.saved = True

    pgn_text = ""
    # Se abbiamo un game_id, proviamo a scaricare il PGN completo e ufficiale da Lichess
    if hasattr(game_state, "game_id") and game_state.game_id:
        url = f"https://lichess.org/game/export/{game_state.game_id}?clocks=true&evals=true&literate=true"
        pgn_text, errore = rete.leggi(url, token=getattr(game_state, "token", None))
        if errore:
            # Si prosegue con la ricostruzione locale, ma l'utente sa perche'.
            print(_("PGN ufficiale non scaricato. {motivo}").format(motivo=errore))
            pgn_text = ""

    if pgn_text:
        try:
            # Carichiamo il PGN scaricato in un oggetto Game per validarlo e salvarlo tramite pgn_handler
            game = chess.pgn.read_game(io.StringIO(pgn_text))
            if game:
                pgn_handler.SaveGameToFile(game)
                print(
                    _(
                        "La partita e' stata scaricata da Lichess, salvata nella cartella PGN e copiata negli appunti."
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
    initial_fen = getattr(game_state, "initial_fen", chess.STARTING_FEN)
    variant = getattr(game_state, "variant", "standard")

    if variant == "chess960":
        game.headers["Variant"] = "Chess960"

    if initial_fen != chess.STARTING_FEN:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = initial_fen

    node = game
    temp_board = chess.Board(initial_fen, chess960=(variant == "chess960"))
    for numero, san in enumerate(game_state.move_history, start=1):
        try:
            move = temp_board.parse_san(san)
            node = node.add_variation(move)
            temp_board.push(move)
        except ValueError:
            # Prima il ciclo si fermava in silenzio e il file salvato
            # risultava troncato senza che nulla lo segnalasse.
            print(
                _(
                    "Attenzione: la mossa {san}, numero {n}, non e' interpretabile. "
                    "Il PGN salvato si ferma alla mossa precedente."
                ).format(san=san, n=numero)
            )
            break

    # Before calling SaveGameToFile:
    if getattr(game_state, "save_clock_times", False):
        board_utils.AggiungiTempiPgn(
            game,
            getattr(game_state, "clocks_history", []),
            getattr(game_state, "move_times", []),
        )

    try:
        pgn_handler.SaveGameToFile(game)
        print(
            _("La partita e' stata salvata nella cartella PGN (ricostruzione locale).")
        )
    except Exception as e:
        print(_("Errore nel salvataggio della partita PGN: {e}").format(e=e))


def handle_exploration_command(user_input, game_state):
    """Comandi di esplorazione della scacchiera, gestiti da ui."""
    return ui.esplora_scacchiera(user_input, game_state)


def _spectate_worker(url, token, q, stop_event):
    risposta, errore = rete.apri(url, token=token, timeout=rete.TIMEOUT_STREAM)
    if errore:
        q.put({"tipo": "errore", "motivo": errore})
        q.put({"tipo": "fine"})
        return
    try:
        with risposta as resp:
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
                        q.put(
                            {
                                "tipo": "giocatori",
                                "bianco": w_name,
                                "elo_bianco": w_rat,
                                "nero": b_name,
                                "elo_nero": b_rat,
                            }
                        )

                    variant = d.get("variant", {}).get("key")
                    if variant:
                        q.put({"tipo": "variante", "chiave": variant})

                    if "initialFen" in d:
                        q.put({"tipo": "inizio", "fen": d["initialFen"]})
                    elif "fen" in d and "lm" not in d:
                        q.put({"tipo": "inizio", "fen": d["fen"]})

                    if "clock" in d and isinstance(d["clock"], dict):
                        limit = d["clock"].get("limit")
                        if limit is not None:
                            q.put({"tipo": "tempo_iniziale", "secondi": limit})

                    wc = d.get("wc")
                    bc = d.get("bc")
                    if wc is not None or bc is not None:
                        q.put({"tipo": "orologi", "bianco": wc, "nero": bc})

                    if "lm" in d:
                        q.put(
                            {
                                "tipo": "mossa",
                                "uci": d["lm"],
                                "bianco": d.get("wc"),
                                "nero": d.get("bc"),
                            }
                        )

                    if "status" in d and isinstance(d["status"], dict):
                        q.put(
                            {
                                "tipo": "esito",
                                "stato": d["status"].get("name", "unknown"),
                                "vincitore": d.get("winner"),
                            }
                        )
    except Exception as e:
        q.put({"tipo": "errore", "motivo": e})
    q.put({"tipo": "fine"})


def async_spectator_loop(q, game_state):
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

        fmt = tempo.compatto

        refresh_interval = getattr(game_state, "refresh_interval", 1)
        clock_str = (
            f"{fmt(wt)} {fmt(bt)} "
            if (getattr(game_state, "started", False) and refresh_interval > 0)
            else ""
        )

        if not game_state.move_history:
            return "\n" + clock_str + _("Inizio, mossa 0.>")
        elif len(game_state.move_history) % 2 == 1:
            return (
                "\n"
                + clock_str
                + f"{(len(game_state.move_history) + 1) // 2}. {game_state.move_history[-1]}>"
            )
        else:
            return (
                "\n"
                + clock_str
                + f"{len(game_state.move_history) // 2}... {game_state.move_history[-1]}>"
            )

    def refresh_line():
        sys.stdout.write("\r" + " " * 79 + "\r")
        sys.stdout.write(get_prompt() + "".join(buf))
        sys.stdout.flush()

    last_refresh = time.time()
    refresh_line()

    while True:
        refresh_interval = getattr(game_state, "refresh_interval", 1)
        if refresh_interval > 0 and time.time() - last_refresh >= refresh_interval:
            refresh_line()
            last_refresh = time.time()
        try:
            msg = q.get_nowait()
            tipo = msg.get("tipo") if isinstance(msg, dict) else None
            if tipo == "fine":
                sys.stdout.write(
                    "\n" + _("Partita terminata o connessione chiusa.") + "\n"
                )
                return None
            elif tipo == "errore":
                sys.stdout.write(
                    "\n"
                    + _("Errore durante lo streaming: {e}").format(
                        e=msg.get("motivo", "")
                    )
                    + "\n"
                )
                return None
            elif tipo == "tempo_iniziale":
                limit = int(float(msg["secondi"]))
                game_state.white_time = limit
                game_state.black_time = limit
                game_state.last_clock_sync = time.time()
            elif tipo == "orologi":
                if msg.get("bianco") is not None:
                    game_state.white_time = int(float(msg["bianco"]))
                if msg.get("nero") is not None:
                    game_state.black_time = int(float(msg["nero"]))
                game_state.last_clock_sync = time.time()
            elif tipo == "mossa":
                wc = msg.get("bianco")
                bc = msg.get("nero")
                move = game_state.board.parse_uci(msg["uci"])
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
                game_state.last_clock_sync = time.time()
                if not game_state.started:
                    game_state.started = True

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
            elif tipo == "variante":
                variant_name = msg["chiave"]
                game_state.variant = variant_name
                if variant_name == "chess960":
                    game_state.board.chess960 = True
            elif tipo == "inizio":
                fen = msg["fen"]
                if fen == "start":
                    game_state.board.reset()
                    game_state.initial_fen = chess.STARTING_FEN
                else:
                    game_state.board.set_fen(fen)
                    game_state.initial_fen = fen
                if not game_state.started:
                    game_state.started = True
                game_state.last_clock_sync = time.time()
            elif tipo == "giocatori":
                new_w = f"{msg['bianco']} ({msg['elo_bianco']})"
                new_b = f"{msg['nero']} ({msg['elo_nero']})"
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
            elif tipo == "esito":
                status_name = msg.get("stato", "unknown")
                winner = msg.get("vincitore")
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
                if len(game_state.move_history) > 10:
                    save_lichess_game(game_state, winner)
                else:
                    sys.stdout.write(
                        "\n"
                        + _(
                            "Partita terminata con 5 o meno mosse. Salto il salvataggio."
                        )
                        + "\n"
                    )
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
            elif c == "\x03" or c == "\x1b":  # Ctrl+C
                sys.stdout.write("\n")
                return "."
            elif c.isprintable():
                buf.append(c)
                sys.stdout.write(c)
                sys.stdout.flush()

        time.sleep(0.02)


def spectate_game(game_id, token=None):
    url_stream = f"https://lichess.org/api/stream/game/{game_id}"

    q = queue.Queue()
    stop_event = threading.Event()
    t = threading.Thread(
        target=_spectate_worker, args=(url_stream, token, q, stop_event), daemon=True
    )
    t.start()

    print(
        _(
            "\nConnessione al tavolo in corso... (Premi ESC o digita . per interrompere l'osservazione)"
        )
    )

    board = board_utils.CustomBoard()
    game_state = SpectatorGameState(board)
    game_state.game_id = game_id
    game_state.token = token

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
        if ui.comandi_orologio(cmd, game_state):
            if cmd == ".6":
                continue
        elif ui.comandi_lettura(cmd, game_state):
            pass
        elif cmd == ".?":
            print(_("\nComandi disponibili:"))
            print(_(".1 : Tempo Bianco"))
            print(_(".2 : Tempo Nero"))
            print(_(".3 : Tempo di entrambi"))
            print(_(".4 : Confronto tempi"))
            print(_(".5 : A chi tocca muovere"))
            print(_(".6 : Modifica timing aggiornamento orologio"))
            print(_(".m : Materiale in gioco"))
            print(_(".l : Lista mosse"))
            print(_(".s oppure .b : Mostra scacchiera"))
            print(_(".  : Esci"))
        else:
            print(_("\nComando non riconosciuto. Usa .? per l'aiuto."))

    save_lichess_game(game_state, getattr(game_state, "winner", "*"))


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
        self.refresh_interval = 1
        self.initial_fen = chess.STARTING_FEN
        self.variant = "standard"
        self.move_times = []
        self.clocks_history = []
        self.clock_increment = 0

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


def _play_worker(url, token, q, stop_event, tentativi=3):
    """Segue la partita e, se la connessione cade, prova a riprenderla.

    Prima bastava un singhiozzo di rete per abbandonare la partita mentre su
    Lichess il tempo continuava a scorrere.
    """
    for tentativo in range(1, tentativi + 1):
        if stop_event.is_set():
            break
        risposta, errore = rete.apri(url, token=token, timeout=rete.TIMEOUT_STREAM)
        if errore:
            if tentativo >= tentativi:
                q.put({"type": "error", "error": errore})
                break
            q.put({"type": "riconnessione", "tentativo": tentativo, "motivo": errore})
            time.sleep(2)
            continue
        try:
            with risposta as resp:
                for line in resp:
                    if stop_event.is_set():
                        break
                    if line.strip():
                        q.put(json.loads(line.decode("utf-8")))
            # Lo stream si e' chiuso senza errori: se la partita non e' finita
            # ritentiamo, altrimenti il ciclo esterno chiudera' comunque.
            if stop_event.is_set() or tentativo >= tentativi:
                break
            q.put({"type": "riconnessione", "tentativo": tentativo, "motivo": ""})
            time.sleep(1)
        except (OSError, ValueError) as e:
            if tentativo >= tentativi:
                q.put({"type": "error", "error": str(e)})
                break
            q.put({"type": "riconnessione", "tentativo": tentativo, "motivo": str(e)})
            time.sleep(2)
    q.put({"type": "eof"})


def send_action(game_id, token, action, uci=None, chat_text=None, motivo=None):
    """Invia mossa, resa, patta o messaggio. Restituisce vero o falso e, se
    riceve una lista in motivo, vi lascia la spiegazione del rifiuto."""
    url = f"https://lichess.org/api/board/game/{game_id}/{action}"
    if action == "move":
        url += f"/{uci}"
    dati = (
        {"room": "player", "text": chat_text}
        if action == "chat" and chat_text
        else None
    )
    riuscito, errore = rete.invia(url, token=token, dati=dati)
    if not riuscito and motivo is not None:
        motivo.append(errore)
    return riuscito


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

        fmt = tempo.compatto

        refresh_interval = getattr(game_state, "refresh_interval", 1)
        clock_str = (
            f"{fmt(wt)} {fmt(bt)} "
            if (getattr(game_state, "started", False) and refresh_interval > 0)
            else ""
        )

        p = ""
        if not game_state.move_history:
            p = clock_str + _("Inizio, mossa 0. ")
        elif len(game_state.move_history) % 2 == 1:
            p = f"{clock_str}{(len(game_state.move_history) + 1) // 2}. {game_state.move_history[-1]} "
        else:
            p = f"{clock_str}{len(game_state.move_history) // 2}... {game_state.move_history[-1]} "

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
                    p = p.rstrip() + _(" [RECLAMA TRA {rem}s] ").format(rem=rem)
                else:
                    p = p.rstrip() + _(" [RECLAMA] ")
            else:
                p = p.rstrip() + _(" [RECLAMA] ")

        return p

    def refresh_line():
        sys.stdout.write("\r" + " " * 79 + "\r")
        sys.stdout.write(get_prompt() + "".join(buf))
        sys.stdout.flush()

    last_refresh = time.time()
    refresh_line()

    while True:
        refresh_interval = getattr(game_state, "refresh_interval", 1)
        if refresh_interval > 0 and time.time() - last_refresh >= refresh_interval:
            refresh_line()
            last_refresh = time.time()
        try:
            msg = q.get_nowait()
            if msg.get("type") == "eof":
                sys.stdout.write("\n" + _("Connessione al server chiusa.") + "\n")
                return None
            elif msg.get("type") == "riconnessione":
                motivo = msg.get("motivo") or _("connessione interrotta")
                sys.stdout.write(
                    "\n"
                    + _(
                        "Riprovo a collegarmi alla partita, tentativo {n}. {motivo}"
                    ).format(n=msg.get("tentativo", 1), motivo=motivo)
                    + "\n"
                )
                sys.stdout.flush()
                continue
            elif msg.get("type") == "error":
                sys.stdout.write(
                    "\n"
                    + _("Collegamento alla partita perduto. {motivo}").format(
                        motivo=msg.get("error")
                    )
                    + "\n"
                )
                return None
            elif msg.get("type") == "gameFull":
                game_state.game_id = msg.get("id")
                clock_data = msg.get("clock", {})
                game_state.clock_increment = (
                    int(clock_data.get("increment", 0)) / 1000.0
                )
                w = msg.get("white", {})
                b = msg.get("black", {})

                w_name = w.get("name", w.get("id", _("Anonimo")))
                if "aiLevel" in w:
                    w_name = _("Stockfish livello {level}").format(level=w["aiLevel"])
                w_rat = w.get("rating", "?")

                b_name = b.get("name", b.get("id", _("Anonimo")))
                if "aiLevel" in b:
                    b_name = _("Stockfish livello {level}").format(level=b["aiLevel"])
                b_rat = b.get("rating", "?")

                game_state.white_player = f"{w_name} ({w_rat})"
                game_state.black_player = f"{b_name} ({b_rat})"

                if w.get("id") == game_state.my_username.lower():
                    game_state.my_color = chess.WHITE
                elif b.get("id") == game_state.my_username.lower():
                    game_state.my_color = chess.BLACK

                variant = msg.get("variant", {}).get("key", "standard")
                game_state.variant = variant
                if variant == "chess960":
                    game_state.board.chess960 = True

                fen = msg.get("initialFen", "startpos")
                if fen == "startpos":
                    game_state.board.reset()
                    game_state.initial_fen = chess.STARTING_FEN
                else:
                    game_state.board.set_fen(fen)
                    game_state.initial_fen = fen

                state = msg.get("state", {})
                moves = state.get("moves", "").strip()
                if moves:
                    num_existing_moves = len(moves.split(" "))
                    game_state.move_times = [0.0] * num_existing_moves
                    game_state.clocks_history = [0.0] * num_existing_moves
                    for uci_move in moves.split(" "):
                        move = game_state.board.parse_uci(uci_move)
                        game_state.move_history.append(game_state.board.san(move))
                        game_state.board.push(move)

                if "wtime" in state and state.get("wtime") is not None:
                    game_state.white_time = int(state.get("wtime")) / 1000.0
                if "btime" in state and state.get("btime") is not None:
                    game_state.black_time = int(state.get("btime")) / 1000.0
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

                        # Calculate and store time_spent and clk_time before push
                        if not hasattr(game_state, "move_times"):
                            game_state.move_times = []
                        if not hasattr(game_state, "clocks_history"):
                            game_state.clocks_history = []

                        if i == current_ply:
                            increment = getattr(game_state, "clock_increment", 0)
                            if is_white_turn:
                                time_spent = max(
                                    0.0,
                                    game_state.white_time
                                    - int(msg.get("wtime", 0)) / 1000.0
                                    + increment,
                                )
                                clk_time = int(msg.get("wtime", 0)) / 1000.0
                            else:
                                time_spent = max(
                                    0.0,
                                    game_state.black_time
                                    - int(msg.get("btime", 0)) / 1000.0
                                    + increment,
                                )
                                clk_time = int(msg.get("btime", 0)) / 1000.0
                        else:
                            time_spent = 0.0
                            clk_time = (
                                int(msg.get("wtime", 0)) / 1000.0
                                if is_white_turn
                                else int(msg.get("btime", 0)) / 1000.0
                            )

                        game_state.move_times.append(time_spent)
                        game_state.clocks_history.append(clk_time)

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

                if "wtime" in msg and msg.get("wtime") is not None:
                    game_state.white_time = int(msg.get("wtime")) / 1000.0
                if "btime" in msg and msg.get("btime") is not None:
                    game_state.black_time = int(msg.get("btime")) / 1000.0
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
                    game_state.winner = winner
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
                user = msg.get("username", _("Sistema"))
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
            elif c == "\x03" or c == "\x1b":  # Ctrl+C
                sys.stdout.write("\n")
                return "."
            elif c.isprintable():
                buf.append(c)
                sys.stdout.write(c)
                sys.stdout.flush()

        time.sleep(0.02)


def show_post_game_report(game_id, token, username):
    print(_("Recupero Report Partita da Lichess (Attendi...)"))
    time.sleep(2)
    data, errore = rete.leggi_json(
        f"https://lichess.org/game/export/{game_id}?evals=true&clocks=true", token=token
    )
    if errore:
        print(_("Report della partita non recuperato. {motivo}").format(motivo=errore))
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

        white_user = w.get("user", {}).get("name", "")
        black_user = b.get("user", {}).get("name", "")
        my_player = None
        if white_user.lower() == username.lower():
            my_player = w
        elif black_user.lower() == username.lower():
            my_player = b

        if my_player:
            rating = my_player.get("rating")
            diff = my_player.get("ratingDiff")
            if rating is not None and diff is not None:
                nelo = rating + diff
                from .lichess_stats import fetch_rating_history

                history_data = fetch_rating_history(username)
                if history_data:
                    perf_name = data.get("perf")
                    if not perf_name:
                        perf_name = data.get("speed")

                    if perf_name:
                        selected_item = next(
                            (
                                item
                                for item in history_data
                                if item.get("name", "").lower() == perf_name.lower()
                            ),
                            None,
                        )
                        if selected_item:
                            points = selected_item.get("points", [])
                            elo_list = [pt[3] for pt in points]

                            if elo_list and elo_list[-1] == nelo:
                                elo = elo_list[:-1]
                            else:
                                elo = elo_list

                            if elo:
                                import statistics

                                celo = elo.count(nelo)
                                if celo == 0:
                                    print(
                                        _(
                                            "\nL'Elo {nelo} non è mai stato registrato prima in questa lista."
                                        ).format(nelo=nelo)
                                    )
                                else:
                                    print(
                                        _(
                                            "\nL'elo inserito, {nelo}, compare altre {celo} volte, in questa lista."
                                        ).format(nelo=nelo, celo=celo)
                                    )

                                omed = statistics.mean(elo)
                                elorange = max(elo) - min(elo)
                                if len(elo) > 2 and elorange > 0:
                                    pos_pct = (nelo - min(elo)) * 100 / elorange
                                    print(
                                        _(
                                            "Minimo / Valore inserito (posizionamento) / Massimo:\n\t{min_elo} / {nelo}=({pct:.3f}%) / {max_elo}."
                                        ).format(
                                            min_elo=min(elo),
                                            nelo=nelo,
                                            pct=pos_pct,
                                            max_elo=max(elo),
                                        )
                                    )

                                elo_after = elo + [nelo]
                                print(_("Nuovo ELO aggiunto."))
                                nmed = statistics.mean(elo_after)
                                print(
                                    _(
                                        "Variazione della media, prima / dopo / differenza:\n\t{omed:.3f} / {nmed:.3f} / {diff:.3f}"
                                    ).format(omed=omed, nmed=nmed, diff=nmed - omed)
                                )
    else:
        print(_("Partita amichevole (nessuna variazione Elo)."))

    from GBUtils import enter_escape

    enter_escape(_("\nPremi Invio per continuare..."))


def play_game(game_id, token, username):
    url_partita = f"https://lichess.org/api/board/game/stream/{game_id}"

    q = queue.Queue()
    stop_event = threading.Event()
    t = threading.Thread(
        target=_play_worker, args=(url_partita, token, q, stop_event), daemon=True
    )
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
            if len(game_state.move_history) > 10:
                from GBUtils import enter_escape

                if enter_escape(
                    _(
                        "Vuoi vedere come hai usato il tempo a tua disposizione? (INVIO per si', ESC per no): "
                    )
                ):
                    board_utils.AnalizzaEStampaStatisticheTempo(
                        game_state, color_filter=None
                    )
                    if enter_escape(
                        _(
                            "Desideri salvare i tempi mossa nel PGN? (INVIO per si', ESC per no): "
                        )
                    ):
                        game_state.save_clock_times = True
                show_post_game_report(game_id, token, username)
                save_lichess_game(game_state, getattr(game_state, "winner", "*"))
            else:
                print(
                    _(
                        "\nPartita terminata con 5 o meno mosse. Salto l'analisi e il salvataggio."
                    )
                )
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

        if ui.comandi_orologio(cmd, game_state):
            if cmd == ".6":
                continue
        elif ui.comandi_lettura(cmd, game_state):
            pass
        elif cmd == ".?":
            print(_("\nComandi disponibili per giocare:"))
            print(_(".1 : Tempo Bianco"))
            print(_(".2 : Tempo Nero"))
            print(_(".3 : Tempo di entrambi"))
            print(_(".4 : Confronto tempi"))
            print(_(".5 : A chi tocca muovere"))
            print(_(".6 : Modifica timing aggiornamento orologio"))
            print(_(".m : Materiale in gioco"))
            print(_(".l : Lista mosse"))
            print(_(".s oppure .b : Mostra scacchiera"))
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
