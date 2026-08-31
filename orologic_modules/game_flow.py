# Orologic, partita arbitrata: svolgimento e salvataggio.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import datetime
import io
import os

import chess
import chess.pgn
import pyperclip
from GBUtils import Acusticator, dgt, enter_escape, key, menu

from . import (
    board_utils,
    chess960_utils,
    clock,
    config,
    engine,
    orologio,
    storage,
    ui,
    version,
)
from .config import _

# Volume ora gestito via config.VOLUME


def RiprendiPartita(dati_partita):
    print(_("Ricostruzione dello stato della partita..."))
    game_state = board_utils.GameState(dati_partita["clock_config"])
    e_chess960 = bool(dati_partita.get("chess960", False))
    game_state.board = board_utils.CustomBoard(
        dati_partita["board_fen"], chess960=e_chess960
    )
    game_state.white_remaining = dati_partita["white_remaining"]
    game_state.black_remaining = dati_partita["black_remaining"]
    game_state.white_phase = dati_partita["white_phase"]
    game_state.black_phase = dati_partita["black_phase"]
    game_state.white_moves = dati_partita["white_moves"]
    game_state.black_moves = dati_partita["black_moves"]
    game_state.active_color = dati_partita["active_color"]
    game_state.move_history = dati_partita["move_history"]
    game_state.white_player = dati_partita["white_player"]
    game_state.black_player = dati_partita["black_player"]
    game_state.move_times = dati_partita.get(
        "move_times", [0.0] * len(game_state.move_history)
    )
    game_state.clocks_history = dati_partita.get(
        "clocks_history", [0.0] * len(game_state.move_history)
    )
    try:
        pgn_io = io.StringIO(dati_partita["pgn_string"])
        game_state.pgn_game = chess.pgn.read_game(pgn_io)
        if game_state.pgn_game is None:
            print(
                _(
                    "Attenzione: PGN non valido nel file di salvataggio. Ne creo uno nuovo."
                )
            )
            game_state.pgn_game = chess.pgn.Game.from_board(game_state.board)
        game_state.pgn_node = game_state.pgn_game.end()
    except (ValueError, KeyError, AttributeError) as e:
        print(
            _(
                "Errore nella lettura del PGN salvato: {error}. La partita riprendera' senza cronologia PGN."
            ).format(error=e)
        )
        game_state.pgn_game = chess.pgn.Game.from_board(game_state.board)
        game_state.pgn_node = game_state.pgn_game.end()
    game_state.paused = True
    chess960_utils.configure_engine_for_chess960(engine.ENGINE, e_chess960)
    orologio.avvia(game_state)
    db = storage.LoadDB()
    autosave_is_on = db.get("autosave_enabled", False)
    eco_database = board_utils.LoadEcoDatabaseWithFEN("eco.db")
    print("\n" + "Riepilogo Partita")
    print(
        _("Bianco: {player} - Tempo: {time}").format(
            player=game_state.white_player,
            time=board_utils.FormatTime(game_state.white_remaining),
        )
    )
    print(
        _("Nero: {player} - Tempo: {time}").format(
            player=game_state.black_player,
            time=board_utils.FormatTime(game_state.black_remaining),
        )
    )
    if game_state.move_history:
        last_move_san = game_state.move_history[-1]
        if game_state.active_color == "black":
            move_num = (len(game_state.move_history) + 1) // 2
            last_move_str = f"{move_num}. {last_move_san}"
        else:
            move_num = len(game_state.move_history) // 2
            last_move_str = f"{move_num}... {last_move_san}"
        print(_("Ultima mossa: {move}").format(move=last_move_str))
    tocca_a_player = (
        game_state.white_player
        if game_state.active_color == "white"
        else game_state.black_player
    )
    print(_("Tocca a: {player}").format(player=tocca_a_player))
    last_valid_eco_entry = _loop_principale_partita(
        game_state, eco_database, autosave_is_on
    )
    _finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on)


def EseguiAutosave(game_state):
    AUTOSAVE_FILENAME = "autosave.json"
    full_path = config.percorso_salvataggio(os.path.join("settings", AUTOSAVE_FILENAME))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    dati_partita = {
        "board_fen": game_state.board.fen(),
        "clock_config": game_state.clock_config,
        "white_remaining": game_state.white_remaining,
        "black_remaining": game_state.black_remaining,
        "white_phase": game_state.white_phase,
        "black_phase": game_state.black_phase,
        "white_moves": game_state.white_moves,
        "black_moves": game_state.black_moves,
        "active_color": game_state.active_color,
        "move_history": game_state.move_history,
        "pgn_string": str(game_state.pgn_game),
        "white_player": game_state.white_player,
        "black_player": game_state.black_player,
        "move_times": getattr(game_state, "move_times", []),
        "clocks_history": getattr(game_state, "clocks_history", []),
        "chess960": bool(getattr(game_state.board, "chess960", False)),
        "starting_fen": game_state.pgn_game.headers.get("FEN", ""),
    }
    try:
        # Scrittura atomica: un'interruzione a meta' lasciava un file
        # troncato, e la partita non era piu' recuperabile.
        storage.scrivi_json(full_path, dati_partita, indent="\t")
    except Exception as e:
        print(
            _("\n[Errore durante il salvataggio automatico: {error}]").format(error=e)
        )


def async_arbitration_input(game_state, get_prompt):
    import msvcrt
    import sys
    import time

    buf = []

    def refresh_line():
        ui.pulisci_riga()
        sys.stdout.write(get_prompt() + "".join(buf))
        sys.stdout.flush()

    last_refresh = time.time()
    refresh_line()

    while True:
        if game_state.flag_fallen and not game_state.ignore_clock:
            return None

        refresh_interval = getattr(game_state, "refresh_interval", 0)
        if refresh_interval > 0 and time.time() - last_refresh >= refresh_interval:
            refresh_line()
            last_refresh = time.time()

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
            elif c == "\x03" or c == "\x1b":
                sys.stdout.write("\n")
                return "."
            elif c.isprintable():
                buf.append(c)
                sys.stdout.write(c)
                sys.stdout.flush()

        time.sleep(0.02)


def comandi_di_lettura(cmd, game_state):
    """Comandi che si limitano a leggere o annunciare qualcosa.

    L'aiuto e' proprio della partita, il resto lo fa ui.comandi_lettura,
    uguale per tutte le modalita'. Restituisce vero se il comando e' stato
    riconosciuto.
    """
    if cmd == ".?":
        Acusticator(
            [440.0, 0.3, 0, config.VOLUME, 880.0, 0.3, 0, config.VOLUME],
            kind=1,
            adsr=[10, 0, 100, 20],
        )
        menu(
            config.DOT_COMMANDS,
            show_only=True,
            p=_("Comandi disponibili:"),
            ordered=False,
        )
        return True

    return ui.comandi_lettura(cmd, game_state)


_COMANDI_RISULTATO = (".1-0", ".0-1", ".1/2", ".*")


def annulla_ultima_mossa(game_state):
    """Toglie dalla partita l'ultima mossa giocata.

    Disfa anche quanto la mossa aveva prodotto: incremento, contatore
    delle mosse ed eventuale passaggio di fase. Restituisce vero se
    c'era davvero una mossa da annullare.
    """
    if game_state.paused and game_state.move_history:
        Acusticator(
            [
                "c5",
                0.1,
                1,
                config.VOLUME,
                "g4",
                0.1,
                0.3,
                config.VOLUME,
                "e4",
                0.1,
                -0.3,
                config.VOLUME,
                "c4",
                0.1,
                -1,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 80, 10],
        )
        undone_move_san = game_state.move_history.pop()
        game_state.board.pop()
        current_node = game_state.pgn_node
        parent = current_node.parent
        if current_node in parent.variations:
            parent.variations.remove(current_node)
        game_state.pgn_node = parent
        game_state.cancelled_san_moves.insert(0, undone_move_san)
        # Il tratto torna a chi aveva mosso, poi si disfa quanto
        # la mossa aveva prodotto: incremento, contatore delle
        # mosse ed eventuale passaggio di fase.
        game_state.active_color = (
            "white" if game_state.active_color == "black" else "black"
        )
        fasi = game_state.clock_config["phases"]
        if game_state.active_color == "white":
            orologio.aggiungi(
                game_state, True, -fasi[game_state.white_phase]["white_inc"]
            )
        else:
            orologio.aggiungi(
                game_state,
                False,
                -fasi[game_state.black_phase]["black_inc"],
            )
        tempo_di_fase = game_state.annulla_mossa()
        if tempo_di_fase:
            if game_state.active_color == "white":
                orologio.aggiungi(game_state, True, -tempo_di_fase)
            else:
                orologio.aggiungi(game_state, False, -tempo_di_fase)
            print(_("Rientro nella fase precedente, tolto il tempo aggiunto."))
        if game_state.move_times:
            game_state.move_times.pop()
        if game_state.clocks_history:
            game_state.clocks_history.pop()
        if game_state.descriptive_move_history:
            # Senza questo, il riepilogo testuale di fine partita
            # conteneva la mossa annullata e sfalsava la numerazione.
            game_state.descriptive_move_history.pop()
        print(_("Ultima mossa annullata: {mossa}").format(mossa=undone_move_san))
        return True
    return False


def assegna_risultato(cmd, game_state):
    """Chiude la partita con il risultato indicato dall'arbitro."""
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
    if cmd == ".1-0":
        result = "1-0"
    elif cmd == ".0-1":
        result = "0-1"
    elif cmd == ".1/2":
        result = "1/2-1/2"
    else:
        result = "*"
    print(_("Risultato assegnato: {risultato}").format(risultato=result))
    game_state.pgn_game.headers["Result"] = result
    game_state.game_over = True


def commenta_mossa(cmd, game_state):
    """Aggiunge al PGN il commento scritto dopo il comando."""
    new_comment = cmd[2:].strip()
    if new_comment:
        if game_state.move_history:
            if game_state.pgn_node.comment:
                game_state.pgn_node.comment += "\n" + new_comment
            else:
                game_state.pgn_node.comment = new_comment
            Acusticator(
                [
                    "f5",
                    0.1,
                    0,
                    config.VOLUME,
                    "p",
                    0.04,
                    0,
                    0,
                    "c5",
                    0.02,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[3, 7, 88, 2],
            )
            print(
                _("Commento registrato per la mossa {mossa}").format(
                    mossa=game_state.move_history[-1]
                )
            )
        else:
            print(_("Nessuna mossa da commentare."))


def verifica_fine_partita(game_state):
    """Riconosce le posizioni che chiudono la partita.

    Matto, stallo, materiale insufficiente, ripetizione e le altre
    patte. Restituisce vero quando la partita e' finita, cosi' il ciclo
    si ferma senza passare il tratto.
    """
    if game_state.board.is_checkmate():
        game_state.game_over = True
        result = "1-0" if game_state.active_color == "white" else "0-1"
        game_state.pgn_game.headers["Result"] = result
        winner = game_state.black_player if result == "0-1" else game_state.white_player
        print(_("Scacco matto! Vince {winner}.").format(winner=winner))
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
        return True
    elif game_state.board.is_stalemate():
        game_state.game_over = True
        game_state.pgn_game.headers["Result"] = "1/2-1/2"
        print(_("Patta per stallo!"))
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
        return True
    elif game_state.board.is_insufficient_material():
        game_state.game_over = True
        game_state.pgn_game.headers["Result"] = "1/2-1/2"
        print(_("Patta per materiale insufficiente!"))
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
        return True
    elif game_state.board.is_seventyfive_moves():
        game_state.game_over = True
        game_state.pgn_game.headers["Result"] = "1/2-1/2"
        print(_("Patta per la regola delle 75 mosse!"))
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
        return True
    elif game_state.board.is_fivefold_repetition():
        game_state.game_over = True
        game_state.pgn_game.headers["Result"] = "1/2-1/2"
        print(_("Patta per ripetizione della posizione (5 volte)!"))
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
        return True
    elif game_state.board.can_claim_fifty_moves():
        game_state.game_over = True
        game_state.pgn_game.headers["Result"] = "1/2-1/2"
        print(_("Patta per la regola delle 50 mosse!"))
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
        return True
    elif game_state.board.can_claim_threefold_repetition():
        game_state.game_over = True
        game_state.pgn_game.headers["Result"] = "1/2-1/2"
        print(_("Patta per triplice ripetizione della posizione!"))
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
        return True
    return False


def salva_pgn_partita(pgn_str, nome_file):
    """Scrive su disco il PGN della partita appena finita.

    Se la cartella di sempre non si puo' usare, per disco pieno o permessi,
    prova nella cartella personale invece di lasciare cadere il programma
    con un errore: la partita e' appena stata giocata e non si rigioca.
    Restituisce il percorso scritto, oppure nulla se non c'e' stato verso.
    """
    percorsi = [config.percorso_salvataggio(os.path.join("pgn", nome_file))]
    percorsi.append(os.path.join(os.path.expanduser("~"), nome_file))
    ultimo_errore = None
    for percorso in percorsi:
        try:
            cartella = os.path.dirname(percorso)
            if cartella:
                os.makedirs(cartella, exist_ok=True)
            with open(percorso, "w", encoding="utf-8") as f:
                f.write(pgn_str)
        except Exception as e:
            ultimo_errore = e
            continue
        if percorso != percorsi[0]:
            print(
                _("La cartella di sempre non era scrivibile: {errore}").format(
                    errore=ultimo_errore
                )
            )
        print(_("PGN salvato come {percorso}.").format(percorso=percorso))
        return percorso
    print(
        _("Non sono riuscita a salvare il PGN su disco: {errore}").format(
            errore=ultimo_errore
        )
    )
    print(_("La partita resta negli appunti, incollala subito da qualche parte."))
    Acusticator(
        ["e3", 0.4, 0, config.VOLUME, "a2", 0.6, 0, config.VOLUME],
        kind=3,
        adsr=[1, 7, 100, 92],
    )
    return None


def _loop_principale_partita(game_state, eco_database, autosave_is_on):
    # Qui c'e' un arbitro: puo' fermare gli orologi e correggere i tempi.
    game_state.arbitro_presente = True
    last_eco_msg = ""
    last_valid_eco_entry = None
    current_turn_clock_before = None
    while not game_state.game_over:
        if current_turn_clock_before is None:
            if game_state.active_color == "white":
                current_turn_clock_before = game_state.white_remaining
            else:
                current_turn_clock_before = game_state.black_remaining
        # --- GESTIONE BANDIERINA CADUTA (Thread-Safe ish) ---
        if game_state.flag_fallen and not game_state.ignore_clock:
            # Il clock_thread ha settato il flag. Ora chiediamo all'utente.
            print(_("\nTempo scaduto!"))
            print(
                _(
                    "Premere INVIO per continuare la partita senza orologio, oppure ESC per terminare e assegnare la vittoria."
                )
            )
            # Usiamo key per un input secco
            choice = key(_("Scegli, INVIO o ESC: "))
            if choice in ("\x1b", "esc"):  # ESC
                game_state.game_over = True
                # Assegna risultato
                if game_state.white_remaining <= 0:
                    game_state.pgn_game.headers["Result"] = "0-1"
                    print(_("Vince il Nero per tempo."))
                else:
                    game_state.pgn_game.headers["Result"] = "1-0"
                    print(_("Vince il Bianco per tempo."))
                break  # Esce dal loop
            else:
                # Continua
                game_state.ignore_clock = True
                game_state.paused = False  # Sblocca (ma il tempo non scenderà più grazie a ignore_clock nel thread)
                print(
                    _(
                        "Partita continuata senza limiti di tempo. Usa i comandi .1-0, .0-1, .1/2, .* per terminare."
                    )
                )
                game_state.flag_fallen = False  # Reset flag per non rientrare qui
                continue  # Riavvia il loop per stampare il prompt corretto

        def get_prompt():
            return board_utils.prompt_partita(game_state)

        user_input = async_arbitration_input(game_state, get_prompt)
        if user_input is None:
            continue

        # Rilevamento bandierina immediato dopo input (nel caso sia caduta mentre scrivevo)
        if game_state.flag_fallen and not game_state.ignore_clock:
            continue  # Torna su a gestire il flag

        if user_input == "/" or user_input == "\\" or user_input == ",":
            user_input = ".?"

        # I comandi di esplorazione sono gli stessi di Orolichess e della
        # partita su Lichess: una sola funzione li gestisce per tutti.
        if ui.esplora_scacchiera(user_input, game_state):
            continue

        if user_input.startswith("."):
            u = user_input.strip()
            cmd = u.rstrip(".").lower()

            if (
                ui.comandi_orologio(cmd, game_state)
                or comandi_di_lettura(cmd, game_state)
                or ui.comandi_pausa(cmd, game_state)
            ):
                pass
            elif cmd == ".q":
                if annulla_ultima_mossa(game_state):
                    current_turn_clock_before = None
            elif cmd in _COMANDI_RISULTATO:
                assegna_risultato(cmd, game_state)
            elif cmd.startswith(".c"):
                commenta_mossa(cmd, game_state)
            else:
                Acusticator(
                    ["e3", 1, 0, config.VOLUME, "a2", 1, 0, config.VOLUME],
                    kind=3,
                    adsr=[1, 7, 100, 92],
                )
                print(_("Comando non riconosciuto."))
        else:
            if game_state.paused:
                print(
                    _(
                        "Non e' possibile inserire nuove mosse mentre il tempo e' in pausa. Riavvia il tempo con .p"
                    )
                )
                Acusticator(["b3", 0.2, 0, config.VOLUME], kind=2)
                continue
            raw_input = board_utils.NormalizeMove(user_input)
            annotation_suffix = None
            move_san_only = raw_input
            match = config.ANNOTATION_SUFFIX_PATTERN.search(raw_input)
            if match:
                annotation_suffix = match.group(1)
                move_san_only = raw_input[: -len(annotation_suffix)].strip()
            try:
                move = game_state.board.parse_san(move_san_only)
                board_copy = game_state.board.copy()
                description = board_utils.DescribeMove(
                    move, board_copy, annotation=annotation_suffix
                )
                game_state.descriptive_move_history.append(description)
                Acusticator(
                    [1000.0, 0.01, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0]
                )
                if game_state.active_color == "white":
                    print(game_state.white_player + ": " + description)
                else:
                    print(game_state.black_player + ": " + description)
                san_move_base = game_state.board.san(move)
                san_move_base = san_move_base.replace("!", "").replace("?", "")
                game_state.board.push(move)
                game_state.move_history.append(san_move_base)

                # Calculate time spent on this move
                if game_state.active_color == "white":
                    time_after = game_state.white_remaining
                else:
                    time_after = game_state.black_remaining

                if current_turn_clock_before is not None:
                    time_spent = max(0.0, current_turn_clock_before - time_after)
                else:
                    time_spent = 0.0

                game_state.move_times.append(time_spent)
                new_node = game_state.pgn_node.add_variation(move)
                if annotation_suffix:
                    if annotation_suffix == "=":
                        existing_comment = new_node.comment or ""
                        if existing_comment:
                            new_node.comment = existing_comment + _(
                                " proposta di patta"
                            )
                        else:
                            new_node.comment = _("proposta di patta")
                    elif annotation_suffix in config.NAG_MAP:
                        nag_value = config.NAG_MAP[annotation_suffix][0]
                        new_node.nags.add(nag_value)
                if (
                    hasattr(game_state, "cancelled_san_moves")
                    and game_state.cancelled_san_moves
                ):
                    undo_comment = _("Mosse annullate: {mosse}").format(
                        mosse=" ".join(game_state.cancelled_san_moves)
                    )
                    existing_comment = new_node.comment or ""
                    if existing_comment:
                        new_node.comment = existing_comment + " " + undo_comment
                    else:
                        new_node.comment = undo_comment
                    del game_state.cancelled_san_moves
                game_state.pgn_node = new_node
                if eco_database:
                    current_board = game_state.board
                    eco_entry = board_utils.DetectOpeningByFEN(
                        current_board, eco_database
                    )
                    new_eco_msg = ""
                    current_entry_this_turn = eco_entry if eco_entry else None
                    if eco_entry:
                        new_eco_msg = "{eco} - {opening}".format(
                            eco=eco_entry["eco"], opening=eco_entry["opening"]
                        )
                        if eco_entry["variation"]:
                            new_eco_msg += " ({variation})".format(
                                variation=eco_entry["variation"]
                            )
                    if new_eco_msg and new_eco_msg != last_eco_msg:
                        print(
                            _("Apertura rilevata: {apertura}").format(
                                apertura=new_eco_msg
                            )
                        )
                        Acusticator(["f7", 0.018, 0, config.VOLUME])
                        last_eco_msg = new_eco_msg
                        last_valid_eco_entry = current_entry_this_turn
                    elif not new_eco_msg and last_eco_msg:
                        last_eco_msg = ""
                if verifica_fine_partita(game_state):
                    break
                if game_state.active_color == "white":
                    orologio.aggiungi(
                        game_state,
                        True,
                        game_state.clock_config["phases"][game_state.white_phase][
                            "white_inc"
                        ],
                    )
                else:
                    orologio.aggiungi(
                        game_state,
                        False,
                        game_state.clock_config["phases"][game_state.black_phase][
                            "black_inc"
                        ],
                    )

                if game_state.active_color == "white":
                    game_state.clocks_history.append(game_state.white_remaining)
                else:
                    game_state.clocks_history.append(game_state.black_remaining)

                game_state.switch_turn()
                current_turn_clock_before = None
                if autosave_is_on:
                    EseguiAutosave(game_state)
                    Acusticator(["f3", 0.012, 0, config.VOLUME], sync=True)
            except Exception:
                illegal_result = ui.verbose_legal_moves_for_san(
                    game_state.board, move_san_only
                )
                Acusticator([600.0, 0.6, 0, config.VOLUME], adsr=[5, 0, 35, 90])
                print(
                    _("Mossa '{move}' non valida. Alternative:\n{alternatives}").format(
                        move=move_san_only, alternatives=illegal_result
                    )
                )
    return last_valid_eco_entry


def _finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on):
    game_state.pgn_game.headers["WhiteClock"] = board_utils.FormatClock(
        game_state.white_remaining
    )
    game_state.pgn_game.headers["BlackClock"] = board_utils.FormatClock(
        game_state.black_remaining
    )
    print(_("Partita terminata."))

    if len(game_state.move_history) >= 8:
        from GBUtils import enter_escape

        if enter_escape(
            _(
                "Vuoi vedere come hai usato il tempo a tua disposizione? (INVIO per si', ESC per no): "
            )
        ):
            board_utils.AnalizzaEStampaStatisticheTempo(game_state, color_filter=None)
            if enter_escape(
                _(
                    "Desideri salvare i tempi mossa nel PGN? (INVIO per si', ESC per no): "
                )
            ):
                board_utils.AggiungiTempiPgn(
                    game_state.pgn_game,
                    game_state.clocks_history,
                    game_state.move_times,
                )
    if last_valid_eco_entry:
        game_state.pgn_game.headers["ECO"] = last_valid_eco_entry["eco"]
        game_state.pgn_game.headers["Opening"] = last_valid_eco_entry["opening"]
        if last_valid_eco_entry["variation"]:
            game_state.pgn_game.headers["Variation"] = last_valid_eco_entry["variation"]
    pgn_str = str(game_state.pgn_game)
    pgn_str = board_utils.format_pgn_comments(pgn_str)
    base_filename = "{white}-{black}-{result}-{timestamp}.pgn".format(
        white=game_state.pgn_game.headers.get("White"),
        black=game_state.pgn_game.headers.get("Black"),
        result=game_state.pgn_game.headers.get("Result", "*"),
        timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
    )
    sanitized_name = config.sanitize_filename(base_filename)
    salva_pgn_partita(pgn_str, sanitized_name)
    ui.save_text_summary(
        game_state, game_state.descriptive_move_history, last_valid_eco_entry
    )
    try:
        pyperclip.copy(pgn_str)
        print(_("PGN copiato negli appunti."))
    except Exception as e:
        print(
            _("Errore durante la copia del PGN negli appunti: {error}").format(error=e)
        )
    if autosave_is_on:
        try:
            autosave_file_path = config.percorso_salvataggio(
                os.path.join("settings", "autosave.json")
            )
            if os.path.exists(autosave_file_path):
                os.remove(autosave_file_path)
                print(_("File di salvataggio automatico eliminato."))
        except Exception as e:
            print(
                _(
                    "\n[Attenzione: impossibile eliminare il file di autosave: {error}]"
                ).format(error=e)
            )
    if len(game_state.move_history) >= 8:
        if ui.enter_escape(
            _("Vuoi analizzare la partita? (INVIO per si', ESC per no): ")
        ):
            db = storage.LoadDB()
            engine_config = db.get("engine_config", {})
            if not engine_config or not engine_config.get("engine_path"):
                if ui.enter_escape(
                    _(
                        "Il motore scacchistico non e' configurato. Vuoi configurarlo ora? (INVIO per si', ESC per no): "
                    )
                ):
                    engine.MenuMotore()
                # MenuMotore salva su disco: rileggo, altrimenti userei la
                # copia caricata prima della configurazione appena fatta.
                engine_config = storage.LoadDB().get("engine_config", {})
                if not engine_config or not engine_config.get("engine_path"):
                    print(_("Motore non configurato. Ritorno al menu'."))
                    return
            if engine.ENGINE is None and not engine.InitEngine():
                print(_("Impossibile inizializzare il motore. Analisi annullata."))
                return
            engine.cache_analysis.clear()
            chess960_utils.configure_engine_for_chess960(
                engine.ENGINE,
                game_state.pgn_game.headers.get("Variant", "") == "Chess960",
            )
            if ui.enter_escape(
                _("Desideri l'analisi automatica? (INVIO per si', ESC per manuale): ")
            ):
                engine.AnalisiAutomatica(board_utils.CopyPgnGame(game_state.pgn_game))
            else:
                engine.AnalyzeGame(game_state.pgn_game)
        else:
            Acusticator(
                [880.0, 0.2, 0, config.VOLUME, 440.0, 0.2, 0, config.VOLUME],
                kind=1,
                adsr=[25, 0, 50, 25],
            )
    return


def StartGame(clock_config):
    print(_("\nAvvio partita\n"))
    is_standard = enter_escape(
        _(
            "Vuoi giocare alla variante standard (scacchi standard)? (INVIO per si', ESC per Fischer Random): "
        )
    )
    is_fischer_random = not is_standard
    Acusticator(
        [
            "c4",
            0.05,
            0,
            config.VOLUME,
            "e4",
            0.05,
            0,
            config.VOLUME,
            "g4",
            0.05,
            0,
            config.VOLUME,
        ],
        kind=1,
        adsr=[0, 0, 100, 5],
    )
    starting_board = None
    starting_fen = None
    if is_fischer_random:
        starting_board, starting_fen, numero_posizione = ui.setup_fischer_random_board()
        if starting_board is None:
            return
    db = storage.LoadDB()
    autosave_is_on = db.get("autosave_enabled", False)
    default_pgn = db.get("default_pgn", {})
    white_default = default_pgn.get("White", _("Bianco"))
    black_default = default_pgn.get("Black", _("Nero"))
    white_elo_default = default_pgn.get("WhiteElo", "1399")
    black_elo_default = default_pgn.get("BlackElo", "1399")
    event_default = default_pgn.get("Event", "Orologic Game")
    site_default = default_pgn.get("Site", _("Sede sconosciuta"))
    round_default = default_pgn.get("Round", "Round 1")
    eco_database = board_utils.LoadEcoDatabaseWithFEN("eco.db")
    # Le sette voci dell'intestazione si chiedevano con sette blocchi identici
    # di prompt, suono e ripiego sul valore precedente: ora e' un giro solo.
    CAMPI_PGN = (
        ("White", _("Nome del bianco"), white_default, True),
        ("Black", _("Nome del nero"), black_default, True),
        ("WhiteElo", _("Elo del bianco"), white_elo_default, False),
        ("BlackElo", _("Elo del nero"), black_elo_default, False),
        ("Event", _("Evento"), event_default, False),
        ("Site", _("Sede"), site_default, False),
        ("Round", _("Round"), round_default, False),
    )
    intestazione = {}
    for chiave, domanda, predefinito, e_un_nome in CAMPI_PGN:
        risposta = dgt(
            _("{domanda} [{predefinito}]: ").format(
                domanda=domanda, predefinito=predefinito
            ),
            kind="s",
            default=predefinito,
        ).strip()
        if not risposta:
            risposta = predefinito
        elif e_un_nome:
            risposta = config.maiuscole_nomi(risposta)
        intestazione[chiave] = risposta
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

    white_player = intestazione["White"]
    black_player = intestazione["Black"]
    white_elo = intestazione["WhiteElo"]
    black_elo = intestazione["BlackElo"]
    event = intestazione["Event"]
    site = intestazione["Site"]
    round_ = intestazione["Round"]

    storage.SetValue(
        "default_pgn",
        {
            "Event": event,
            "Site": site,
            "Round": round_,
            "White": white_player,
            "Black": black_player,
            "WhiteElo": white_elo,
            "BlackElo": black_elo,
        },
    )
    key(
        _("Premi un tasto qualsiasi per iniziare la partita quando sei pronto..."),
        attesa=7200,
    )
    Acusticator(
        [
            "c6",
            0.07,
            0,
            config.VOLUME,
            "p",
            0.93,
            0,
            0.5,
            "c6",
            0.07,
            0,
            config.VOLUME,
            "p",
            0.93,
            0,
            0.5,
            "c6",
            0.07,
            0,
            config.VOLUME,
            "p",
            0.93,
            0,
            0.5,
            "c7",
            0.5,
            0,
            config.VOLUME,
        ],
        kind=1,
        sync=True,
    )
    game_state = board_utils.GameState(clock_config)
    if is_fischer_random:
        game_state.board = starting_board
        chess960_utils.setup_pgn_headers_chess960(
            game_state.pgn_game, starting_board, starting_fen, numero_posizione
        )
        chess960_utils.configure_engine_for_chess960(engine.ENGINE, True)
    else:
        chess960_utils.configure_engine_for_chess960(engine.ENGINE, False)
    game_state.white_player = white_player
    game_state.black_player = black_player
    game_state.pgn_game.headers["White"] = white_player
    game_state.pgn_game.headers["Black"] = black_player
    game_state.pgn_game.headers["WhiteElo"] = white_elo
    game_state.pgn_game.headers["BlackElo"] = black_elo
    game_state.pgn_game.headers["Event"] = event
    game_state.pgn_game.headers["Site"] = site
    game_state.pgn_game.headers["Round"] = round_
    game_state.pgn_game.headers["TimeControl"] = clock.generate_time_control_string(
        clock_config
    )
    game_state.pgn_game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
    game_state.pgn_game.headers["Annotator"] = (
        f"Orologic V{version.VERSION} by {version.PROGRAMMER}"
    )
    orologio.avvia(game_state)
    last_valid_eco_entry = _loop_principale_partita(
        game_state, eco_database, autosave_is_on
    )
    _finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on)
    return
