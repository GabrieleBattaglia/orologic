# Orologic, Easyfish: menu principale della modalita'.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import builtins
import contextlib
import re

import chess
import chess.engine
import pyperclip
from GBUtils import Acusticator, dgt, enter_escape, menu

from .. import config, ui
from .. import engine as orologic_engine

# DRY: Uso le utility di Orologic
from ..board_utils import (
    CustomBoard,
    DescribeMove,
    GameState,
    NormalizeMove,
    accoda_commento,
    format_pv_descriptively,
    mosse_fino_al_nodo,
    testo_valutazione,
)
from ..config import _
from .constants import MNMAIN
from .drawing import drawing_menu, verbalize_drawings
from .engine_handler import ShowStats
from .image_exporter import export_board_pdf, image_settings_menu
from .interaction import BoardEditor, ExplorerMode
from .pgn_handler import (
    AddingPGNTAGS,
    CopyPGNToClipboard,
    InitNewPGN,
    PastePGNFromClipboard,
    SaveGameToFile,
    ScegliPartitaDallaCartella,
)
from .sharing_window import PygameBoardWindow
from .utils import suona_annulla

_orig_print = builtins.print
show_output_on_board = False
sharing_window = None


def custom_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    sep = kwargs.get("sep", " ")
    text = sep.join(str(arg) for arg in args)
    if not text.strip():
        return
    if show_output_on_board and sharing_window and sharing_window.is_active():
        sharing_window.update_text(text)


def GetDynamicPrompt(board, node):
    """Genera il prompt basandosi sul turno, numero di mossa e livello variante."""
    n = board.fullmove_number

    # Calcolo livello variante
    variant_level = 0
    temp_node = node
    while temp_node.parent:
        if temp_node.parent.variations[0] != temp_node:
            variant_level += 1
        temp_node = temp_node.parent

    prefix = f"var{variant_level} " if variant_level else ""

    if not board.move_stack:
        return _("{p}INIZIO {n}. ").format(p=prefix, n=n)

    # La notazione si ricava su una copia: prima la mossa veniva tolta e
    # rimessa sulla scacchiera vera, e un errore fra le due operazioni
    # avrebbe lasciato la posizione senza una mossa.
    copia = board.copy()
    last_move = copia.pop()
    last_san = copia.san(last_move)

    if board.turn == chess.WHITE:
        return f"{prefix}{n - 1}... {last_san}: "
    else:
        return f"{prefix}{n}. {last_san}: "


def CheckGameOver(board, node=None):
    """Controlla se la partita è finita (matto, patta) e stampa l'esito."""
    if board.is_game_over(claim_draw=True):
        if board.is_checkmate():
            res = "1-0" if board.turn == chess.BLACK else "0-1"
            if node and node.root():
                node.root().headers["Result"] = res
            print(_("Scacco matto!"))
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
        elif board.is_stalemate():
            if node and node.root():
                node.root().headers["Result"] = "1/2-1/2"
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
        elif board.is_insufficient_material():
            if node and node.root():
                node.root().headers["Result"] = "1/2-1/2"
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
        elif board.is_seventyfive_moves() or board.can_claim_fifty_moves():
            if node and node.root():
                node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per la regola delle 50/75 mosse!"))
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
        elif board.is_fivefold_repetition() or board.can_claim_threefold_repetition():
            if node and node.root():
                node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per ripetizione della posizione!"))
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


def _comandi_informativi(cmd, board, node, game, sharing_window):
    """Comandi del menu che si limitano a riferire qualcosa.

    Scacchiera, elenco comandi, mossa migliore, intestazioni del PGN e
    stato della finestra di condivisione. Restituisce vero se il
    comando e' stato riconosciuto.
    """
    if cmd == ".v":
        print(
            _(
                "Pronto per nuova variante. Inserisci una mossa diversa per creare un nuovo ramo."
            )
        )
    elif cmd == ".?":
        menu(d=MNMAIN, show_only=True)
    elif cmd in ui.COMANDI_SCACCHIERA or cmd in (".m", ".bm"):
        # Scacchiera e materiale sono quelli di tutte le altre modalita':
        # qui il menu stampava una scacchiera grezza, senza le colonne.
        ui.comandi_lettura(".m" if cmd in (".m", ".bm") else ".s", game, board=board)
    elif cmd == ".gp":
        CopyPGNToClipboard(game)
    elif cmd == ".i":
        export_board_pdf(board, node)
    elif cmd == ".ii":
        image_settings_menu()
        if sharing_window and sharing_window.is_active():
            sharing_window.trigger_update()
    elif cmd == ".gf":
        ui.copia_negli_appunti(board.fen(), _("Partita in FEN. Copiata negli appunti"))
    elif cmd == ".gb":
        # La stessa griglia di .s, girata dal lato di chi ha il tratto, poi il
        # tratto a parole e il FEN, per chi la vuole portare in un programma.
        if board.turn == chess.WHITE:
            tratto = _("Tocca al Bianco muovere.")
        else:
            tratto = _("Tocca al Nero muovere.")
        ui.copia_negli_appunti(
            f"{CustomBoard(board.fen())}\n{tratto}\n{board.fen()}\n",
            _("Scacchiera copiata negli appunti, con il tratto e il FEN."),
        )
    elif cmd in [".csb", ".csn", ".cst"]:
        if sharing_window is None or not sharing_window.is_active():
            print(_("Errore: devi prima avviare la condivisione con il comando .cs"))
        elif cmd == ".csb":
            sharing_window.set_orientation("white")
            print(_("Orientamento scacchiera condivisa impostato: Bianco (fisso)."))
        elif cmd == ".csn":
            sharing_window.set_orientation("black")
            print(_("Orientamento scacchiera condivisa impostato: Nero (fisso)."))
        elif cmd == ".cst":
            sharing_window.set_orientation("turn")
            print(
                _(
                    "Orientamento scacchiera condivisa impostato: in base al turno (dinamico)."
                )
            )
    else:
        return False
    return True


def _comandi_analisi(cmd_clean, board, engine, number_command, info, info_fen):
    """Analizza la posizione e rilegge le linee gia' trovate.

    Restituisce il risultato dell'analisi, che il comando punto a elle
    riusa senza interrogare di nuovo il motore, e il FEN della posizione
    analizzata, che serve a .ac per sapere se quel risultato vale ancora.
    Le linee stavano su punto elle, che pero' in tutte le altre modalita' e'
    la lista delle mosse: era l'ultimo comando rimasto con due significati
    diversi.
    """
    if cmd_clean == ".a":
        if not engine:
            print(_("Motore non caricato in Orologic."))
        else:
            sec = number_command if number_command > 0 else 1
            print(_("Analisi posizione corrente per {s} secondi.").format(s=sec))
            limit = chess.engine.Limit(time=sec)
            try:
                info_result = engine.analyse(
                    board, limit, multipv=orologic_engine.multipv
                )
                info = info_result
                info_fen = board.fen()
                if isinstance(info, list):
                    ShowStats(board, info[0])
                elif isinstance(info, dict):
                    ShowStats(board, info)
            # Contorno di Easyfish: si prosegue.
            except Exception as e:  # noqa: BLE001
                print(_("Errore analisi: {e}").format(e=e))
    elif cmd_clean == ".al":
        # Le linee valgono solo per la posizione analizzata: dopo una mossa
        # le loro mosse non sono piu' legali, e python-chess, chiamato a
        # scriverle, faceva cadere Easyfish.
        if info and info_fen != board.fen():
            print(
                _("L'ultima analisi riguarda un'altra posizione: rifalla con .a")
            )
        elif info:
            idx = number_command - 1 if number_command > 0 else 0
            idx = max(idx, 0)
            current_info_list = info if isinstance(info, list) else [info]
            if idx >= len(current_info_list):
                print(
                    _("Ci sono solo {n} linee di analisi disponibili").format(
                        n=len(current_info_list)
                    )
                )
                idx = len(current_info_list) - 1
            if idx == 0:
                print(_("Migliore:"))
            else:
                print(_("{n}° scelta:").format(n=idx + 1))
            ShowStats(board, current_info_list[idx])
        else:
            print(_("Prima devi eseguire l'analisi con il comando .a"))
    return info, info_fen


# Quante semimosse della linea principale entrano nel commento di .ac: la
# linea intera di un'analisi lunga sarebbe troppo da rileggere.
LINEA_SEMIMOSSE = 10


def _analisi_nel_commento(board, node, engine, secondi, info, info_fen):
    """Comando .ac: scrive nel commento della mossa valutazione, mossa
    migliore e linea principale, nella forma di x e v della modalita' Analisi.

    Senza numero riusa l'ultima analisi, se e' di questa posizione; se non lo
    e', o con un numero, ne fa una nuova, di un secondo o dei secondi scritti.
    Restituisce l'analisi, il suo FEN e vero se il commento e' cambiato.
    """
    if not engine:
        print(_("Motore non caricato in Orologic."))
        return info, info_fen, False
    if secondi > 0 or not info or info_fen != board.fen():
        sec = secondi if secondi > 0 else 1
        print(_("Analisi posizione corrente per {s} secondi.").format(s=sec))
        try:
            info = engine.analyse(
                board,
                chess.engine.Limit(time=sec),
                multipv=orologic_engine.multipv,
            )
            info_fen = board.fen()
        # Contorno di Easyfish: si prosegue.
        except Exception as e:  # noqa: BLE001
            print(_("Errore analisi: {e}").format(e=e))
            return info, info_fen, False
    migliore = info[0] if isinstance(info, list) else info
    pv = migliore.get("pv", [])
    score = migliore.get("score")
    if not pv or score is None:
        print(_("Nessuna linea trovata."))
        return info, info_fen, False
    annotazione = " ".join(
        (
            _("[Val: {ev}]").format(ev=testo_valutazione(score)),
            _("[BM: {bm}]").format(bm=format_pv_descriptively(board, pv[:1])),
            _("[Linea: {linea}]").format(
                linea=board.variation_san(pv[:LINEA_SEMIMOSSE])
            ),
        )
    )
    accoda_commento(node, annotazione)
    print(annotazione)
    print(_("Commento registrato."))
    return info, info_fen, True


def _apri_condivisione(board, node, sharing_window):
    """Apre o chiude la finestra grafica per la didattica.

    Restituisce la finestra da usare d'ora in poi, che puo' essere
    quella appena aperta, quella gia' attiva o nessuna.
    """
    if sharing_window is None or not sharing_window.is_active():
        print(
            _(
                "\nAttivazione condivisione scacchiera (finestra grafica per didattica)..."
            )
        )
        print(_("ISTRUZIONI:"))
        print(_("- Puoi condividere la nuova finestra su Meet, Zoom o Teams."))
        print(
            _(
                "- Per continuare ad inserire comandi, ricordati di riportare il focus (cliccare) su questa finestra di testo della console."
            )
        )
        Acusticator(
            [
                "c5",
                0.1,
                0,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
        )
        sharing_window = PygameBoardWindow(config.VERSION)
        sharing_window.start(board, node)
    else:
        Acusticator(
            [
                "c6",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "c5",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
        )
        sharing_window.stop()
        sharing_window = None
        print(_("\nCondivisione scacchiera disattivata."))
    return sharing_window


@contextlib.contextmanager
def _stampa_deviata():
    """Manda le stampe alla finestra grafica, e le rimette a posto comunque.

    Il ripristino stava sull'ultima riga della funzione: un'uscita
    anticipata o un errore lasciavano tutte le stampe del programma,
    motore e scacchiera compresi, dirottate sulla finestra di Easyfish
    anche dopo esserne usciti.
    """
    originale = builtins.print
    builtins.print = custom_print
    try:
        yield
    finally:
        builtins.print = originale


def _semimosse_dopo(node):
    """Quante semimosse, varianti comprese, vengono dopo questo nodo."""
    conto = 0
    da_visitare = list(node.variations)
    while da_visitare:
        figlio = da_visitare.pop()
        conto += 1
        da_visitare.extend(figlio.variations)
    return conto


def _apri_partita(game):
    """La scacchiera e il nodo finale di una partita da aprire in Easyfish.

    Serve a .pg e alle partite che arrivano da altri moduli: in tutti e due i
    casi ci si ritrova sull'ultima mossa della linea principale.
    """
    board = CustomBoard()
    if "FEN" in game.headers:
        board.set_fen(game.headers["FEN"])
    for move in game.mainline_moves():
        board.push(move)
    return board, game.end()


def run(partita=None):
    """Avvia Easyfish, riportando la stampa alla normalita' all'uscita.

    partita, se c'e', e' un chess.pgn.Game che Easyfish apre subito, come
    dopo .pg: cosi' arrivano le partite scelte nel profilatore di Lichess.
    """
    with _stampa_deviata():
        _esegui(partita)


def _esegui(partita=None):
    global sharing_window, show_output_on_board
    print(
        _(
            "\nBenvenuto in Easyfish, la tua interfaccia testuale con il motore scacchistico.\n\tBuon divertimento!"
        )
    )

    # Init Engine
    if not orologic_engine.ENGINE:
        from ..storage import LoadDB

        db = LoadDB()
        cfg = db.get("engine_config", {})
        if not cfg or not cfg.get("engine_path"):
            if enter_escape(
                _(
                    "Il motore scacchistico non e' configurato, ma e' necessario per Easyfish. Vuoi configurarlo ora? (INVIO per si', ESC per no): "
                )
            ):
                orologic_engine.MenuMotore()

        print(_("Inizializzazione Motore Orologic per Easyfish..."))
        orologic_engine.InitEngine()

    engine = orologic_engine.ENGINE

    # New Game
    board = CustomBoard()
    game, node = InitNewPGN(board)
    if partita is not None:
        game = partita
        board, node = _apri_partita(game)
        print(_("Nuova partita caricata."))
        print(board)

    # DRY: GameState
    fake_clock = {
        "phases": [
            {
                "white_time": 0,
                "black_time": 0,
                "white_inc": 0,
                "black_inc": 0,
                "moves": 0,
            }
        ]
    }
    game_state = GameState(fake_clock)
    game_state.board = board

    # State
    info = {}
    info_fen = None
    fen_from_clip = ""
    is_modified = False
    last_checked_state = None
    sharing_window = None

    while True:
        if sharing_window and not sharing_window.is_active():
            Acusticator(
                [
                    "c6",
                    0.05,
                    0,
                    config.VOLUME,
                    "g5",
                    0.05,
                    0,
                    config.VOLUME,
                    "e5",
                    0.05,
                    0,
                    config.VOLUME,
                    "c5",
                    0.1,
                    0,
                    config.VOLUME,
                ],
                kind=1,
            )
            print(_("\nFinestra di condivisione scacchiera chiusa."))
            sharing_window = None

        current_state = (board.fen(), len(board.move_stack))
        if current_state != last_checked_state:
            CheckGameOver(board, node)
            drawings_text = verbalize_drawings(node)
            if drawings_text:
                print(drawings_text)
            last_checked_state = current_state
            if sharing_window and sharing_window.is_active():
                sharing_window.update_board(board, node)

        prompt = GetDynamicPrompt(board, node)
        key_command = dgt(prompt=prompt, kind="s", smin=1, smax=8192).strip()

        if not key_command:
            continue

        number_command_str = "".join([char for char in key_command if char.isdigit()])
        number_command = int(number_command_str) if number_command_str else 0

        if key_command.startswith("."):
            cmd = key_command.lower()
            cmd_clean = "".join([char for char in cmd if not char.isdigit()])

            if cmd == ".":  # ESCI o RISALI
                # Logica di risalita variante
                is_variant = False
                temp = node
                while temp.parent:
                    if temp.parent.variations[0] != temp:
                        is_variant = True
                        break
                    temp = temp.parent

                if is_variant and node.parent:
                    temp_node = node
                    while (
                        temp_node.parent and temp_node.parent.variations[0] == temp_node
                    ):
                        board.pop()
                        temp_node = temp_node.parent
                    if temp_node.parent:
                        board.pop()
                        temp_node = temp_node.parent
                    node = temp_node
                    print(_("Chiusa variante. Ritorno al nodo padre."))
                    continue

                if is_modified and (
                    len(board.move_stack) > 0 or board.fen() != chess.STARTING_FEN
                ):
                    print(_("Salvataggio partita in corso..."))
                    SaveGameToFile(game)
                if sharing_window:
                    sharing_window.stop()
                break

            elif _comandi_informativi(cmd, board, node, game, sharing_window):
                pass

            elif cmd == ".vm":
                # Promuovi Variante a Mainline
                if node.parent and len(node.parent.variations) > 1:
                    parent = node.parent
                    vars_list = parent.variations

                    # Trova l'indice del nodo corrente
                    try:
                        current_idx = vars_list.index(node)
                        if current_idx > 0:
                            # Scambia con l'indice 0 (Mainline)
                            vars_list[0], vars_list[current_idx] = (
                                vars_list[current_idx],
                                vars_list[0],
                            )
                            is_modified = True
                            print(_("Variante promossa a linea principale!"))
                        else:
                            print(_("Questa linea è già la principale."))
                    except ValueError:
                        print(_("Errore: nodo non trovato nelle varianti."))
                else:
                    print(
                        _(
                            "Non sei in una variante o non ci sono alternative da promuovere."
                        )
                    )

            elif cmd_clean in [".k", ".k+", ".k-"]:
                target_move = 0
                is_black = False

                # Parsing regex
                match = re.search(r"^\.k(\d+)([+-]?)$", key_command.lower())
                if match:
                    target_move = int(match.group(1))
                    is_black = match.group(2) == "-"

                # Se non parsato o 0, chiedi interattivamente
                if target_move <= 0:
                    try:
                        target_move = dgt(
                            prompt=_("Numero mossa: "),
                            kind="i",
                            imin=1,
                            imax=600,
                            default=1,
                        )
                        turn_choice = (
                            dgt(
                                prompt=_("B per Bianco, N per Nero: "),
                                kind="s",
                                default="B",
                            )
                            .strip()
                            .upper()
                        )
                        is_black = turn_choice == "N"
                    # Contorno di Easyfish: si prosegue.
                    except Exception:  # noqa: BLE001
                        target_move = 1
                        is_black = False

                color_str = _("Nero") if is_black else _("Bianco")
                print(
                    _("Salto alla mossa {n} ({c})...").format(
                        n=target_move, c=color_str
                    )
                )

                board.reset()
                if "FEN" in game.headers:
                    board.set_fen(game.headers["FEN"])
                node = game

                found = False
                # Gestione caso speciale: Inizio Partita (se corrisponde alla richiesta)
                if target_move == board.fullmove_number and board.turn == (
                    chess.BLACK if is_black else chess.WHITE
                ):
                    found = True
                else:
                    for move in game.mainline_moves():
                        current_turn_is_black = board.turn == chess.BLACK

                        if board.fullmove_number == target_move:
                            if is_black == current_turn_is_black:
                                found = True
                                break

                        board.push(move)
                        if node.variations:
                            node = node.variations[0]
                        else:
                            # Fine partita raggiunta
                            break

                    # Check finale se la richiesta corrisponde all'ultima posizione raggiunta (es. ultima mossa nera giocata -> siamo al bianco successivo, ma loop finito)
                    if (
                        not found
                        and board.fullmove_number == target_move
                        and (board.turn == chess.BLACK) == is_black
                    ):
                        found = True

                if not found:
                    print(
                        _("Mossa {n} {c} non raggiunta (fine partita).").format(
                            n=target_move, c=color_str
                        )
                    )

                game_state.board = board
                print(board)

            elif cmd == ".e":
                print(_("Accesso alla modalità esplorazione..."))
                mod_in_exp, final_node = ExplorerMode(
                    game, engine, sharing_window=sharing_window
                )
                node = final_node
                board = node.board()
                game_state.board = board
                if mod_in_exp:
                    is_modified = True

            elif cmd == ".d":
                if drawing_menu(game, node):
                    is_modified = True
                    if sharing_window and sharing_window.is_active():
                        sharing_window.trigger_update()

            elif cmd == ".pt":
                AddingPGNTAGS(game)
                is_modified = True

            elif cmd == ".cs":
                sharing_window = _apri_condivisione(board, node, sharing_window)

            elif cmd_clean == ".cso":
                parts = key_command.strip().split()
                if len(parts) > 1:
                    val = parts[1].lower()
                    if val == "on":
                        show_output_on_board = True
                    elif val == "off":
                        show_output_on_board = False
                    else:
                        print(_("Opzione non valida. Usa: .cso on | .cso off"))
                        continue
                else:
                    show_output_on_board = not show_output_on_board
                status_str = _("attivata") if show_output_on_board else _("disattivata")
                print(
                    _(
                        "Visualizzazione dell'output di testo sotto la scacchiera {status}."
                    ).format(status=status_str)
                )
                Acusticator(
                    ["c5", 0.08, 0, config.VOLUME, "g5", 0.08, 0, config.VOLUME]
                )
                if sharing_window and sharing_window.is_active():
                    sharing_window.set_show_text_mode(show_output_on_board)

            elif cmd == ".pg":
                print(_("Incolla una nuova posizione PGN dagli appunti..."))
                res = PastePGNFromClipboard()
                if res:
                    loaded_game, is_corrected = res
                    print(
                        _(
                            "ATTENZIONE: La partita corrente verrà salvata e ne inizierà una nuova."
                        )
                    )
                    if is_modified:
                        SaveGameToFile(game)
                    game = loaded_game
                    board, node = _apri_partita(game)
                    game_state.board = board
                    is_modified = is_corrected
                    print(_("Nuova partita caricata."))
                    print(board)
                else:
                    print(_("PGN non valido o appunti vuoti."))

            elif cmd == ".u":
                # Si ritira la mossa in cui ci si trova, con il suo seguito.
                # Senza seguito, il caso dell'errore di battitura, sparisce
                # subito; con un seguito si chiede, perche' si perde di piu'.
                seguito = _semimosse_dopo(node)
                if seguito == 1:
                    domanda = _(
                        "La mossa ha un seguito di 1 semimossa, che sparira' "
                        "con lei. Confermi? (INVIO per si', ESC per no): "
                    )
                else:
                    domanda = _(
                        "La mossa ha un seguito di {n} semimosse, che "
                        "spariranno con lei. Confermi? (INVIO per si', "
                        "ESC per no): "
                    ).format(n=seguito)
                if not node.parent:
                    print(_("Impossibile eliminare l'inizio della partita."))
                elif seguito == 0 or enter_escape(domanda):
                    node.parent.variations.remove(node)
                    node = node.parent
                    board.pop()
                    is_modified = True
                    suona_annulla()
                    print(_("Mossa/Variante eliminata. Tornati indietro."))

            elif cmd == ".pa":
                scelta = ScegliPartitaDallaCartella()
                if scelta is not None:
                    # Come .pg: la partita modificata si salva in un file
                    # nuovo, quindi aprirne un'altra non fa perdere niente.
                    if is_modified:
                        print(_("Salvataggio partita in corso..."))
                        SaveGameToFile(game)
                    game = scelta
                    board, node = _apri_partita(game)
                    game_state.board = board
                    is_modified = False
                    print(_("Nuova partita caricata."))
                    print(board)

            elif cmd == ".fg":
                fen_from_clip = pyperclip.paste()
                if not fen_from_clip:
                    print(_("Spiacente, appunti vuoti. Copia prima un FEN valido."))
                else:
                    print(_("Incolla una nuova posizione FEN dagli appunti..."))
                    try:
                        tmp_board = board.copy()
                        tmp_board.set_fen(fen_from_clip)
                        print(
                            _(
                                "FEN valido. ATTENZIONE: La partita corrente verrà salvata e ne inizierà una nuova da questa posizione."
                            )
                        )
                        if is_modified:
                            SaveGameToFile(game)
                        board = CustomBoard()
                        board.set_fen(fen_from_clip)
                        game, node = InitNewPGN(board)
                        game_state.board = board
                        is_modified = False
                        print(board)
                    except ValueError:
                        print(_("Stringa FEN non valida."))

            elif cmd == ".n":
                print(_("Nuova partita. La corrente verrà salvata."))
                if is_modified:
                    SaveGameToFile(game)
                print(_("Nuova scacchiera pronta. Si parte!"))
                board = CustomBoard()
                game, node = InitNewPGN(board)
                game_state.board = board
                is_modified = False

            elif cmd == ".be":
                print(
                    _(
                        "Accesso all'editor. ATTENZIONE: Al termine dell'editing, la partita corrente verrà salvata e ne inizierà una nuova dalla posizione impostata."
                    )
                )
                new_fen = BoardEditor(
                    starting_fen=board.fen(), sharing_window=sharing_window
                )
                if new_fen:
                    if is_modified:
                        SaveGameToFile(game)
                    board = CustomBoard()
                    board.set_fen(new_fen)
                    game, node = InitNewPGN(board)
                    game_state.board = board
                    is_modified = False
                    print(_("Nuova partita avviata dalla posizione editata."))
                    print(board)

            elif cmd_clean in (".a", ".al"):
                info, info_fen = _comandi_analisi(
                    cmd_clean, board, engine, number_command, info, info_fen
                )

            elif cmd_clean == ".ac":
                info, info_fen, scritto = _analisi_nel_commento(
                    board, node, engine, number_command, info, info_fen
                )
                if scritto:
                    is_modified = True

            elif cmd_clean == ".l":
                # La lista delle mosse e' quella di tutte le altre
                # modalita': qui le mosse si ricostruiscono dal PGN.
                ui.comandi_lettura(
                    ".l", game, board=board, mosse=mosse_fino_al_nodo(node)
                )

            else:
                print(
                    _(
                        "Spiacente, {cmd} non è un comando valido.\nDigita '.?' per il menu."
                    ).format(cmd=cmd)
                )

        elif key_command.startswith("_"):
            node.comment = key_command[1:]
            is_modified = True
            print(_("Commento registrato."))

        else:
            from ..lichess_board import handle_exploration_command

            if handle_exploration_command(key_command, game_state):
                continue
            move_san = NormalizeMove(key_command)
            move = None
            try:
                move = board.parse_san(move_san)
            except ValueError:
                pass

            if (
                not move
                and len(move_san) == 3
                and move_san[0].islower()
                and move_san[1].islower()
                and move_san[2].isdigit()
            ):
                try:
                    move_capture = move_san[0] + "x" + move_san[1:]
                    move = board.parse_san(move_capture)
                except ValueError:
                    pass

            if not move and move_san and move_san[0] == "b":
                try:
                    move = board.parse_san("B" + move_san[1:])
                except ValueError:
                    if len(move_san) == 3:
                        try:
                            move = board.parse_san("Bx" + move_san[1:])
                        except ValueError:
                            pass

            if move:
                print(DescribeMove(move, board))
                board.push(move)

                existing_variation = None
                for variant in node.variations:
                    if variant.move == move:
                        existing_variation = variant
                        break

                if existing_variation:
                    node = existing_variation
                else:
                    if node.variations:
                        # Divergenza: chiediamo cosa fare
                        print(_("Mossa diversa trovata."))
                        scelta = enter_escape(
                            _("Sovrascrivi linea (Invio) o Aggiungi Variante (Esc)? ")
                        )
                        if scelta:
                            # Invio -> Sovrascrivi (cancella le altre e tieni questa come principale)
                            node.variations.clear()
                            node = node.add_variation(move)
                            print(_("Linea sovrascritta."))
                        else:
                            # Esc -> Aggiungi variante
                            node = node.add_variation(move)
                            print(_("Nuova variante creata."))
                    else:
                        node = node.add_variation(move)
                    is_modified = True
            else:
                color = _("Bianco") if board.turn == chess.WHITE else _("Nero")
                print(
                    _("{k}: mossa illegale per il {c}.").format(k=key_command, c=color)
                )
