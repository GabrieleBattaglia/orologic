# Orologic, Orolichess: partite giocate e osservate.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import json
import queue
import sys
import threading
import time

import chess
from GBUtils import Acusticator

from . import board_utils, config, cruscotto, modello_prompt, rete, strato, tempo, ui
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
        self.refresh_interval = modello_prompt.intervallo()
        self.vista_fermabile = True
        self.vista_ferma = False
        # Nella finestra la scacchiera interattiva qui e' solo da guardare.
        self.solo_da_guardare = True
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


def _aggiorna_orologi(game_state, bianco, nero):
    """I tempi che lo stream manda con la mossa. Una partita senza orologio,
    per corrispondenza o senza limite, non li manda: prima il confronto era
    con la stringa "None", e il valore vuoto vero finiva in int(float(None))."""
    if bianco not in (None, "None"):
        game_state.white_time = int(float(bianco))
    if nero not in (None, "None"):
        game_state.black_time = int(float(nero))
    game_state.last_clock_sync = time.time()


def mossa_dallo_stream(board, uci, fen=None):
    """La mossa annunciata dallo stream di una partita osservata.

    Il campo lm di Lichess porta le due case da evidenziare, non la mossa
    intera: in una promozione manca il pezzo, f7f8 invece di f7f8q, e
    python-chess la rifiutava facendo cadere Orologic. Il pezzo si ricava
    dalla posizione che arriva insieme alla mossa, e se manca si prende la
    donna. Restituisce None per una mossa che non si riconosce.
    """
    try:
        return board.parse_uci(uci)
    except ValueError:
        pass
    try:
        da, a = chess.parse_square(uci[:2]), chess.parse_square(uci[2:4])
    except (ValueError, TypeError):
        return None
    candidate = [m for m in board.legal_moves if m.from_square == da and m.to_square == a]
    if fen:
        disposizione = fen.split(" ")[0]
        for mossa in candidate:
            prova = board.copy(stack=False)
            prova.push(mossa)
            if prova.board_fen() == disposizione:
                return mossa
    for mossa in candidate:
        if mossa.promotion == chess.QUEEN:
            return mossa
    return candidate[0] if candidate else None


def save_lichess_game(game_state, result_str="*"):
    import io

    from .easyfish import pgn_handler

    if getattr(game_state, "saved", False):
        return
    game_state.saved = True

    pgn_text = ""
    # Se abbiamo un game_id, proviamo a scaricare il PGN completo e ufficiale da Lichess
    if hasattr(game_state, "game_id") and game_state.game_id:
        # Lichess, se non gli si dice altro, scrive nei commenti tempi e
        # valutazioni. Si chiede il PGN pulito, con tag, mosse e risultato,
        # e i tempi soltanto se l'utente ha scelto di salvarli.
        tempi = "true" if getattr(game_state, "save_clock_times", False) else "false"
        url = (
            f"https://lichess.org/game/export/{game_state.game_id}"
            f"?clocks={tempi}&evals=false&literate=false"
        )
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
        # Come sopra: la partita online continua anche se un dato
        # secondario non si legge.
        except Exception:  # noqa: BLE001, S110
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
    # Come sopra: la partita online continua anche se un dato
    # secondario non si legge.
    except Exception as e:  # noqa: BLE001
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
                        giocatori = d.get("players") or {}
                        w = giocatori.get("white") or {}
                        b = giocatori.get("black") or {}
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
                                "fen": d.get("fen"),
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
    # Come sopra: la partita online continua anche se un dato
    # secondario non si legge.
    except Exception as e:  # noqa: BLE001
        q.put({"tipo": "errore", "motivo": e})
    q.put({"tipo": "fine"})


def _righe_comuni():
    return [
        _(".1 : Tempo Bianco"),
        _(".2 : Tempo Nero"),
        _(".3 : Tempo di entrambi"),
        _(".4 : Confronto tempi"),
        _(".5 : A chi tocca muovere"),
        _(".6 : Modifica timing aggiornamento orologio"),
        _(".m : Materiale in gioco"),
        _(".l : Lista mosse"),
        _(".s oppure .b : Mostra scacchiera"),
    ]


def _righe_dell_osservazione():
    """Le righe dell'aiuto della partita osservata, chiave : descrizione."""
    return [*_righe_comuni(), _(".  : Esci")]


def _righe_del_gioco(game_state):
    """Le righe dell'aiuto della partita giocata, chiave : descrizione."""
    righe = [
        *_righe_comuni(),
        _("draw : Proponi patta"),
        _("nodraw : Rifiuta la patta offerta dall'avversario"),
        _("resign : Abbandona la partita"),
        _("takeback : Chiedi di ritirare la mossa"),
        _("notakeback : Rifiuta il ritiro chiesto dall'avversario"),
        _("claim : Reclama vittoria per abbandono avversario"),
        _("claimdraw : Reclama la patta per abbandono avversario"),
    ]
    if getattr(game_state, "tournament_id", None):
        righe.append(_(".berserk : Dimezza il tuo tempo per un punto in piu', torneo arena"))
    righe.append(_("_[testo] : Invia un messaggio in chat (es. _Ciao)"))
    righe.append(_(".  : Esci dalla visuale (non abbandona la partita)"))
    return righe


def _comandi_delle_righe(righe):
    """Le righe dell'aiuto come coppie (chiave, riga), per la plancia della
    finestra, che le mostra cosi' come sono."""
    return [(riga.partition(" : ")[0].strip(), riga) for riga in righe]


def async_spectator_loop(q, game_state):
    strato.fornisci(lambda: cruscotto.dati_di(game_state), _comandi_delle_righe(_righe_dell_osservazione()))
    buf = []

    def get_prompt():
        # Il corpo viene dal modello dell'utente; la cornice, a capo davanti
        # e segno di maggiore in fondo, resta quella della partita osservata.
        return _corpo_del_prompt(game_state, None, "", inizio="\n", fine=">")

    memoria = {}

    def refresh_line():
        ui.pulisci_riga()
        # Con la scacchiera ferma gli eventi passano, e sotto di loro torna
        # la riga che chiede un tasto, non il prompt.
        if ui.vista_ferma(game_state):
            sys.stdout.write(ui.riga_vista_ferma())
            sys.stdout.flush()
        else:
            ui.scrivi_prompt(memoria, get_prompt(), buf)

    last_refresh = time.time()
    refresh_line()

    while True:
        refresh_interval = getattr(game_state, "refresh_interval", 1)
        if (
            refresh_interval > 0
            and not ui.vista_ferma(game_state)
            and time.time() - last_refresh >= refresh_interval
        ):
            # Il rinfresco periodico: nella finestra non si annuncia.
            with strato.rinfresco():
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
                move = mossa_dallo_stream(game_state.board, msg["uci"], msg.get("fen"))
                if move is None:
                    # Una mossa che non si riconosce non deve chiudere la
                    # visuale: la scacchiera torna alla posizione di Lichess.
                    ui.pulisci_riga()
                    sys.stdout.write(
                        _(
                            "Mossa {uci} non riconosciuta: la scacchiera torna alla posizione di Lichess."
                        ).format(uci=msg["uci"])
                        + "\n"
                    )
                    if msg.get("fen"):
                        try:
                            game_state.board.set_fen(msg["fen"])
                        except ValueError:
                            pass
                    _aggiorna_orologi(game_state, wc, bc)
                    refresh_line()
                    continue
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
                _aggiorna_orologi(game_state, wc, bc)
                if not game_state.started:
                    game_state.started = True

                if game_state.is_live:
                    ui.pulisci_riga()
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
                    ui.pulisci_riga()
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

                ui.pulisci_riga()
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
                # Una volta sola: all'uscita dall'osservazione non si salva
                # di nuovo, e nemmeno dopo "Salto il salvataggio" (R78).
                game_state.salvataggio_fatto = True
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
                ui.pulisci_riga()
                sys.stdout.write(_("La scacchiera e' pronta!\n"))
                refresh_line()

        if strato.kbhit():
            c = strato.getwch()
            if c in ("\x00", "\xe0"):
                strato.getwch()
                if not ui.vista_ferma(game_state):
                    continue
            if ui.vista_ferma(game_state):
                # Il tasto serve solo a tornare al prompt.
                game_state.vista_ferma = False
                refresh_line()
                last_refresh = time.time()
                continue

            if c == "\r" or c == "\n":
                sys.stdout.write("\n")
                return "".join(buf)
            elif c == "\b":
                if buf:
                    buf.pop()
                    if memoria.get("coda"):
                        # Dopo il cursore c'e' il resto del prompt: si riscrive.
                        refresh_line()
                    else:
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
            elif c == "\x03" or c == "\x1b":  # Ctrl+C
                sys.stdout.write("\n")
                return "."
            elif c.isprintable():
                buf.append(c)
                if memoria.get("coda"):
                    refresh_line()
                else:
                    sys.stdout.write(c)
                    sys.stdout.flush()

        time.sleep(0.02)


@strato.in_partita
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
            for riga in _righe_dell_osservazione():
                print(riga)
        else:
            print(_("\nComando non riconosciuto. Usa .? per l'aiuto."))

    # All'uscita si salva solo una partita vista davvero, e non gia'
    # salvata o scartata alla sua fine: prima il salvataggio partiva
    # sempre, anche se il flusso non si era mai aperto, con file inutili e
    # appunti sovrascritti (R78).
    if game_state.started and game_state.move_history and not getattr(game_state, "salvataggio_fatto", False):
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
        self.refresh_interval = modello_prompt.intervallo()
        self.vista_fermabile = True
        self.vista_ferma = False
        self.initial_fen = chess.STARTING_FEN
        self.variant = "standard"
        self.move_times = []
        self.clocks_history = []
        # Le mosse come le manda Lichess, in UCI: il confronto con l'elenco
        # di gameState si fa su queste (R16, R17).
        self.mosse_uci = []
        self.clock_increment = 0
        # Il torneo arena della partita, se c'e': serve al berserk.
        self.tournament_id = None
        self.berserk = False

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


def ricostruisci_le_mosse(game_state, mosse_uci):
    """Scacchiera e storia dall'elenco completo delle mosse di Lichess, dalla
    posizione iniziale. Alla riconnessione Lichess rimanda gameFull con
    tutte le mosse, che prima si accodavano alla storia senza svuotarla, e
    da li' le mosse dell'avversario non si applicavano piu' (R16); dopo un
    ritiro accettato gameState ha meno mosse, e la scacchiera locale teneva
    quelle ritirate (R17). I tempi delle mosse gia' note restano."""
    board = game_state.board
    if game_state.initial_fen == chess.STARTING_FEN:
        board.reset()
    else:
        board.set_fen(game_state.initial_fen)
    game_state.move_history.clear()
    for uci in mosse_uci:
        move = board.parse_uci(uci)
        game_state.move_history.append(board.san(move))
        board.push(move)
    game_state.mosse_uci = list(mosse_uci)
    quante = len(mosse_uci)
    game_state.move_times = (list(game_state.move_times) + [0.0] * quante)[:quante]
    game_state.clocks_history = (list(game_state.clocks_history) + [0.0] * quante)[:quante]


def prolunga(game_state, mosse_uci):
    """Vero se l'elenco di Lichess comincia con le mosse gia' sulla
    scacchiera locale: allora basta giocare quelle nuove."""
    note = game_state.mosse_uci
    return len(note) == len(game_state.move_history) and mosse_uci[: len(note)] == note


def mie_mosse(game_state):
    """Le mosse gia' giocate dall'utente nella partita. Si conta da chi
    aveva il tratto nella posizione di partenza, che in un torneo tematico o
    da FEN puo' essere il Nero."""
    totali = len(game_state.move_history)
    try:
        primo = chess.Board(game_state.initial_fen).turn
    except ValueError:
        primo = chess.WHITE
    if game_state.my_color == primo:
        return (totali + 1) // 2
    return totali // 2


def berserk(game_id, token, game_state):
    """Il berserk dei tornei arena: dimezza il tempo dell'utente, e una
    vittoria vale un punto in piu'. Solo in una partita di torneo e prima
    della prima mossa dell'utente."""
    if not game_state.started:
        print(_("La partita non e' ancora collegata: riprova fra un attimo."))
        return
    if not game_state.tournament_id:
        print(_("Il berserk vale solo nelle partite dei tornei arena."))
        return
    if game_state.berserk:
        print(_("Sei gia' in berserk."))
        return
    if mie_mosse(game_state) > 0:
        print(_("Il berserk si dichiara prima della tua prima mossa."))
        return
    motivo = []
    if send_action(game_id, token, "berserk", motivo=motivo):
        game_state.berserk = True
        Acusticator.play("orologic_berserk", volume=config.VOLUME)
        print(
            _(
                "Berserk: il tuo tempo e' dimezzato, e se vinci prendi un punto "
                "in piu'."
            )
        )
    else:
        Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
        print(
            _("Berserk non riuscito. {motivo}").format(
                motivo=motivo[0] if motivo else ""
            ).strip()
        )


def _corpo_del_prompt(game_state, mio, avversario, stati=(), inizio="", fine=" "):
    """Il corpo del prompt di una partita su Lichess, osservata o giocata,
    dal modello dell'utente. I tempi corrono da soli fra un messaggio e
    l'altro dello stream, e si vedono solo a partita iniziata con .6 acceso."""
    bianco, nero = game_state.get_clocks()
    bianco, nero = modello_prompt.tempi_visibili(
        getattr(game_state, "refresh_interval", 1),
        bianco,
        nero,
        not getattr(game_state, "started", False),
    )
    dati = {
        "bianco": bianco,
        "nero": nero,
        "mio": mio,
        "board": game_state.board,
        "mosse": game_state.move_history,
        "mossa": modello_prompt.mossa_classica(game_state.move_history),
        "pausa": False,
        "senza_orologio": False,
        "altri_stati": list(stati),
        "mosse_al_controllo": None,
        "inizio": getattr(game_state, "inizio_partita", None),
        "avversario": avversario,
    }
    return modello_prompt.prompt_per_input(dati, inizio=inizio, fine=fine)


# Le pause fra un tentativo e l'altro di riprendere il flusso della partita
# crescono, raddoppiando, fino alla massima; i tentativi falliti di fila
# prima di arrendersi, una decina di minuti senza rete (R19).
PAUSA_INIZIALE = 1
PAUSA_MASSIMA = 30
TENTATIVI_DI_FILA = 25


def _partita_finita(msg):
    """Vero se il messaggio del flusso dice che la partita e' finita."""
    if msg.get("type") == "gameFull":
        stato = (msg.get("state") or {}).get("status")
    elif msg.get("type") == "gameState":
        stato = msg.get("status")
    else:
        return False
    return stato not in (None, "created", "started")


def _play_worker(url, token, q, stop_event, tentativi=TENTATIVI_DI_FILA):
    """Segue la partita e, se la connessione cade, prova a riprenderla
    finche' la partita e' in corso, con pause che crescono; il conto dei
    tentativi riparte a ogni riga ricevuta.

    Prima bastava un singhiozzo di rete per abbandonare la partita mentre su
    Lichess il tempo continuava a scorrere; poi i tentativi erano tre in
    tutta la partita, a due secondi l'uno dall'altro, e senza rete finivano
    in pochi secondi, con le domande di fine partita a partita in corso
    (R19).
    """
    falliti = 0
    finita = False
    while not stop_event.is_set():
        risposta, errore = rete.apri(url, token=token, timeout=rete.TIMEOUT_STREAM)
        if not errore:
            try:
                with risposta as resp:
                    for line in resp:
                        if stop_event.is_set():
                            break
                        if line.strip():
                            msg = json.loads(line.decode("utf-8"))
                            falliti = 0
                            finita = finita or _partita_finita(msg)
                            q.put(msg)
                errore = ""
            except (OSError, ValueError) as e:
                errore = str(e)
        # A partita finita il flusso si chiude, e non si riprende.
        if stop_event.is_set() or finita:
            break
        falliti += 1
        if falliti >= tentativi:
            q.put({"type": "error", "error": errore or _("Lichess ha chiuso il collegamento.")})
            break
        q.put({"type": "riconnessione", "tentativo": falliti, "motivo": errore})
        stop_event.wait(min(PAUSA_MASSIMA, PAUSA_INIZIALE * 2 ** (falliti - 1)))
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


def secondi_al_reclamo(game_state):
    """I secondi che restano prima di poter reclamare la vittoria contro un
    avversario che se ne e' andato; zero se si puo' gia' (R83)."""
    claim_in = getattr(game_state, "claim_win_in_seconds", 0) or 0
    if claim_in <= 0:
        return 0
    passati = int(time.time() - getattr(game_state, "opponent_gone_time", time.time()))
    return max(0, claim_in - passati)


def offerte_dell_avversario(game_state, msg):
    """Le righe da dire per le offerte nuove dell'avversario in un
    gameState: la patta e il ritiro della mossa, una volta per offerta.
    Prima wdraw, bdraw, wtakeback e btakeback non si leggevano, e l'utente
    non sapeva dell'offerta (R72)."""
    avversario = "b" if game_state.my_color == chess.WHITE else "w"
    righe = []
    for campo, attributo, testo in (
        (f"{avversario}draw", "patta_offerta", _("L'avversario offre patta: draw accetta, nodraw rifiuta.")),
        (f"{avversario}takeback", "ritiro_chiesto", _("L'avversario chiede di ritirare la mossa: takeback accetta, notakeback rifiuta.")),
    ):
        attiva = bool(msg.get(campo))
        if attiva and not getattr(game_state, attributo, False):
            righe.append(testo)
        setattr(game_state, attributo, attiva)
    return righe


def suono_dell_offerta():
    """Tre note che salgono e tornano, da sinistra a destra: l'avversario
    offre patta o chiede il ritiro (R72)."""
    Acusticator([523.0, 0.06, -0.5, config.VOLUME, 784.0, 0.06, 0.5, config.VOLUME, 523.0, 0.1, 0, config.VOLUME], kind=3, adsr=[2, 10, 80, 10])


def suono_dell_invio_fallito():
    """Tre note che scendono, un tritono: l'invio a Lichess non e' riuscito."""
    Acusticator(["b4", 0.07, 0, config.VOLUME, "f4", 0.07, 0, config.VOLUME, "b3", 0.25, 0, config.VOLUME], kind=2, adsr=[2, 10, 70, 20])


def invia_e_riferisci(q, game_id, token, azione, uci=None, testo=None, riuscita=None, fallita=""):
    """Manda l'azione a Lichess in un filo suo e ne mette l'esito nella coda
    dei messaggi della partita: la conferma, riuscita, solo a invio fatto,
    e il fallimento, con il motivo di Lichess, sempre. Prima l'esito si
    ignorava, e le conferme arrivavano prima dell'invio: chi credeva di
    aver mosso aspettava, col suo orologio che correva (R18)."""

    def filo():
        motivo = []
        if send_action(game_id, token, azione, uci, testo, motivo=motivo):
            if riuscita:
                q.put({"type": "esito_invio", "testo": riuscita, "riuscito": True})
            return
        q.put({"type": "esito_invio", "testo": " ".join([fallita, *[m for m in motivo if m]]).strip(), "riuscito": False})

    threading.Thread(target=filo, daemon=True, name="invio a Lichess").start()


def async_play_loop(q, game_state):
    strato.fornisci(lambda: cruscotto.dati_di(game_state), _comandi_delle_righe(_righe_del_gioco(game_state)))
    buf = []

    def get_prompt():
        stati = []
        if getattr(game_state, "premove", None):
            stati.append(f"[{game_state.premove}]")

        if hasattr(game_state, "opponent_gone") and game_state.opponent_gone:
            rem = secondi_al_reclamo(game_state)
            if rem > 0:
                stati.append(_(" [RECLAMA TRA {rem}s] ").format(rem=rem).strip())
            else:
                stati.append(_(" [RECLAMA] ").strip())

        mio = game_state.my_color
        avversario = (
            game_state.black_player if mio == chess.WHITE else game_state.white_player
        )
        return _corpo_del_prompt(game_state, mio, avversario, stati)

    memoria = {}

    def refresh_line():
        ui.pulisci_riga()
        # Con la scacchiera ferma gli eventi passano, e sotto di loro torna
        # la riga che chiede un tasto, non il prompt.
        if ui.vista_ferma(game_state):
            sys.stdout.write(ui.riga_vista_ferma())
            sys.stdout.flush()
        else:
            ui.scrivi_prompt(memoria, get_prompt(), buf)

    last_refresh = time.time()
    refresh_line()

    while True:
        refresh_interval = getattr(game_state, "refresh_interval", 1)
        if (
            refresh_interval > 0
            and not ui.vista_ferma(game_state)
            and time.time() - last_refresh >= refresh_interval
        ):
            # Il rinfresco periodico: nella finestra non si annuncia.
            with strato.rinfresco():
                refresh_line()
            last_refresh = time.time()
        try:
            msg = q.get_nowait()
            if msg.get("type") == "eof":
                sys.stdout.write("\n" + _("Connessione al server chiusa.") + "\n")
                return None
            elif msg.get("type") == "esito_invio":
                ui.pulisci_riga()
                sys.stdout.write(msg["testo"] + "\n")
                if not msg["riuscito"]:
                    suono_dell_invio_fallito()
                refresh_line()
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
                if msg.get("createdAt"):
                    game_state.inizio_partita = msg["createdAt"] / 1000
                game_state.tournament_id = msg.get("tournamentId")
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
                # Riaprendo una partita, il berserk gia' dichiarato da una
                # parte o dall'altra sta nello stato iniziale.
                stato_iniziale = msg.get("state") or {}
                mio_bianco = game_state.my_color == chess.WHITE
                if stato_iniziale.get("wbrsk" if mio_bianco else "bbrsk"):
                    game_state.berserk = True
                if stato_iniziale.get("bbrsk" if mio_bianco else "wbrsk"):
                    game_state.berserk_avversario = True

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
                # Anche alla riconnessione: la storia si ricostruisce, non
                # si accoda (R16).
                ricostruisci_le_mosse(game_state, moves.split(" ") if moves else [])

                if "wtime" in state and state.get("wtime") is not None:
                    game_state.white_time = int(state.get("wtime")) / 1000.0
                if "btime" in state and state.get("btime") is not None:
                    game_state.black_time = int(state.get("btime")) / 1000.0
                game_state.last_clock_sync = time.time()

                ui.pulisci_riga()
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
                for riga in offerte_dell_avversario(game_state, msg):
                    ui.pulisci_riga()
                    sys.stdout.write(riga + "\n")
                    suono_dell_offerta()
                    refresh_line()
                moves = msg.get("moves", "").strip()
                new_moves = moves.split(" ") if moves else []
                # Un elenco che non prolunga quello locale, dopo un ritiro
                # accettato, ricostruisce la partita (R17).
                if not prolunga(game_state, new_moves):
                    ritirate = len(new_moves) < len(game_state.move_history)
                    ricostruisci_le_mosse(game_state, new_moves)
                    if ritirate:
                        ui.pulisci_riga()
                        sys.stdout.write(_("Mosse ritirate: la scacchiera torna alla posizione di Lichess.") + "\n")
                        refresh_line()
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
                        game_state.mosse_uci.append(uci_move)

                        ui.pulisci_riga()
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
                # Il berserk dell'avversario, nei tornei arena: lo si dice
                # una volta, perche' il suo tempo dimezzato cambia la partita.
                # I campi wbrsk e bbrsk lila li manda, ma la specifica non li
                # documenta: se mancano, semplicemente non si dice nulla.
                chiave = "bbrsk" if game_state.my_color == chess.WHITE else "wbrsk"
                if msg.get(chiave) and not getattr(game_state, "berserk_avversario", False):
                    game_state.berserk_avversario = True
                    ui.pulisci_riga()
                    sys.stdout.write(
                        _("L'avversario e' andato in berserk: il suo tempo e' dimezzato.")
                        + "\n"
                    )
                    refresh_line()

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

                    ui.pulisci_riga()
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
                        # Come la mossa scritta al proprio turno: in SAN, o
                        # in coordinate (R73).
                        try:
                            move = game_state.board.parse_san(game_state.premove)
                        except ValueError:
                            move = game_state.board.parse_uci(game_state.premove)
                        uci = move.uci()
                        ui.pulisci_riga()
                        sys.stdout.write(
                            _("Eseguo premove: {m}...\n").format(m=game_state.premove)
                        )
                        invia_e_riferisci(
                            q, game_state.game_id, game_state.token, "move", uci,
                            fallita=_("La mossa {m} non e' arrivata a Lichess.").format(m=game_state.premove),
                        )
                    # Come sopra: la partita online continua anche se un dato
                    # secondario non si legge.
                    except Exception:  # noqa: BLE001
                        ui.pulisci_riga()
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
                    ui.pulisci_riga()
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
                    ui.pulisci_riga()
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
                    ui.pulisci_riga()
                    sys.stdout.write(_("L'avversario e' tornato in partita.\n"))
                    Acusticator(
                        [300.0, 0.2, 0, config.VOLUME, 400.0, 0.2, 0, config.VOLUME],
                        kind=1,
                    )
                    refresh_line()
                elif gone:
                    refresh_line()  # To update the prompt with [CLAIM]
        except queue.Empty:
            pass

        if strato.kbhit():
            c = strato.getwch()
            if c in ("\x00", "\xe0"):
                strato.getwch()
                if not ui.vista_ferma(game_state):
                    continue
            if ui.vista_ferma(game_state):
                # Il tasto serve solo a tornare al prompt.
                game_state.vista_ferma = False
                refresh_line()
                last_refresh = time.time()
                continue

            if c == "\r" or c == "\n":
                sys.stdout.write("\n")
                return "".join(buf)
            elif c == "\b":
                if buf:
                    buf.pop()
                    if memoria.get("coda"):
                        # Dopo il cursore c'e' il resto del prompt: si riscrive.
                        refresh_line()
                    else:
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
            elif c == "\x03" or c == "\x1b":  # Ctrl+C
                sys.stdout.write("\n")
                return "."
            elif c.isprintable():
                buf.append(c)
                if memoria.get("coda"):
                    refresh_line()
                else:
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

                history_data = fetch_rating_history(username, token)
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


@strato.in_partita
def play_game(game_id, token, username):
    """Gioca una partita su Lichess. Durante la partita gli avvisi delle sfide
    in arrivo sono solo un suono, per non coprire le mosse."""
    from . import lichess_eventi

    with lichess_eventi.solo_suono():
        return _gioca_partita(game_id, token, username)


def _gioca_partita(game_id, token, username):
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
            ui.svuota_tastiera()
            if len(game_state.move_history) > 10:
                from GBUtils import enter_escape

                # Il PGN si salva comunque, anche chiudendo Orologic durante
                # le domande o il resoconto: prima si salvava solo alla fine
                # di tutto, e si perdeva (R83).
                try:
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
                finally:
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
                invia_e_riferisci(
                    q, game_id, token, "chat", testo=chat_text,
                    riuscita=_("Messaggio inviato."), fallita=_("Il messaggio non e' arrivato a Lichess."),
                )
            continue

        cmd = user_input.lower()
        if cmd == "resign":
            if enter_escape(
                _("Sei sicuro di voler abbandonare (resign)? (Invio = Si', Esc = No): ")
            ):
                invia_e_riferisci(q, game_id, token, "resign", fallita=_("L'abbandono non e' arrivato a Lichess."))
            continue
        elif cmd == "draw":
            invia_e_riferisci(
                q, game_id, token, "draw/yes",
                riuscita=_("Offerta di patta inviata."), fallita=_("L'offerta di patta non e' arrivata a Lichess."),
            )
            continue
        elif cmd in (".berserk", "berserk"):
            berserk(game_id, token, game_state)
            continue
        elif cmd == "takeback":
            invia_e_riferisci(
                q, game_id, token, "takeback/yes",
                riuscita=_("Richiesta di annullamento mossa inviata."),
                fallita=_("La richiesta di annullamento non e' arrivata a Lichess."),
            )
            continue
        # Rifiutare le offerte dell'avversario e reclamare la patta: prima
        # mancavano (R72).
        elif cmd == "nodraw":
            invia_e_riferisci(q, game_id, token, "draw/no", riuscita=_("Patta rifiutata."), fallita=_("Il rifiuto della patta non e' arrivato a Lichess."))
            continue
        elif cmd == "notakeback":
            invia_e_riferisci(q, game_id, token, "takeback/no", riuscita=_("Ritiro della mossa rifiutato."), fallita=_("Il rifiuto del ritiro non e' arrivato a Lichess."))
            continue
        elif cmd == "claimdraw":
            invia_e_riferisci(q, game_id, token, "claim-draw", riuscita=_("Patta reclamata."), fallita=_("Il reclamo della patta non e' arrivato a Lichess."))
            continue
        elif cmd == "claim":
            # I secondi che restano, come li mostra il prompt: prima si
            # guardavano quelli iniziali, e col prompt gia' a RECLAMA il
            # comando diceva ancora troppo presto (R83).
            if secondi_al_reclamo(game_state) > 0:
                print(
                    _(
                        "Troppo presto. Potrai reclamare la vittoria tra {s} secondi."
                    ).format(s=secondi_al_reclamo(game_state))
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
            for riga in _righe_del_gioco(game_state):
                print(riga)
        else:
            if not game_state.started:
                print(_("La partita non e' ancora iniziata!"))
                continue

            # A tratto altrui e' una premossa: si controlla al proprio turno,
            # sulla posizione di allora. Convalidata su quella di adesso, come
            # se fosse dell'avversario, quasi ogni premossa vera riceveva
            # "Mossa non valida" (R73).
            if game_state.board.turn != game_state.my_color:
                game_state.premove = board_utils.NormalizeMove(user_input)
                print(_("Premove impostata: {m}. Verra' giocata al tuo turno.").format(m=game_state.premove))
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
                    invia_e_riferisci(
                        q, game_id, token, "move", uci,
                        fallita=_("La mossa {m} non e' arrivata a Lichess.").format(m=raw_input),
                    )
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
