import chess
import chess.engine
import pyperclip
import re
from GBUtils import dgt, menu, Acusticator
from .constants import MNMAIN

# DRY: Uso le utility di Orologic
from ..board_utils import CustomBoard, DescribeMove, GameState, NormalizeMove
from .utils import CalculateMaterial
from .pgn_handler import (
    InitNewPGN,
    PastePGNFromClipboard,
    CopyPGNToClipboard,
    SaveGameToFile,
    AddingPGNTAGS,
)
from .. import engine as orologic_engine
from .. import config
from ..config import _
from .engine_handler import ShowStats
from .interaction import ExplorerMode, BoardEditor
from . import game_mode
from .image_exporter import image_settings_menu, export_board_pdf
from .drawing import drawing_menu, verbalize_drawings
from .. import chess960_utils
from .sharing_window import PygameBoardWindow
import builtins

_orig_print = builtins.print
show_output_on_board = False
sharing_window = None

def custom_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    sep = kwargs.get('sep', ' ')
    text = sep.join(str(arg) for arg in args)
    if not text.strip():
        return
    global sharing_window, show_output_on_board
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

    prefix = f"Lvl{variant_level} "

    if not board.move_stack:
        return _("{p}INIZIO {n}. ").format(p=prefix, n=n)

    last_move = board.pop()
    last_san = board.san(last_move)
    board.push(last_move)

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
                    0.5,
                    "e5",
                    0.1,
                    0,
                    0.5,
                    "g5",
                    0.1,
                    0.5,
                    0.5,
                    "c6",
                    0.2,
                    0,
                    0.5,
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
                    0.5,
                    "e5",
                    0.1,
                    0,
                    0.5,
                    "g5",
                    0.1,
                    0.5,
                    0.5,
                    "c6",
                    0.2,
                    0,
                    0.5,
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
                    0.5,
                    "e5",
                    0.1,
                    0,
                    0.5,
                    "g5",
                    0.1,
                    0.5,
                    0.5,
                    "c6",
                    0.2,
                    0,
                    0.5,
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
                    0.5,
                    "e5",
                    0.1,
                    0,
                    0.5,
                    "g5",
                    0.1,
                    0.5,
                    0.5,
                    "c6",
                    0.2,
                    0,
                    0.5,
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
                    0.5,
                    "e5",
                    0.1,
                    0,
                    0.5,
                    "g5",
                    0.1,
                    0.5,
                    0.5,
                    "c6",
                    0.2,
                    0,
                    0.5,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )


def run():
    global sharing_window, show_output_on_board
    builtins.print = custom_print
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
            from GBUtils import enter_escape

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

            elif cmd == ".v":
                # Segnalazione visuale per l'utente
                print(
                    _(
                        "Pronto per nuova variante. Inserisci una mossa diversa per creare un nuovo ramo."
                    )
                )

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
                    except Exception:
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

            elif cmd == ".?":
                menu(d=MNMAIN, show_only=True)

            elif cmd == ".e":
                print(_("Accesso alla modalità esplorazione..."))
                mod_in_exp, final_node = ExplorerMode(game, engine, sharing_window=sharing_window)
                node = final_node
                board = node.board()
                game_state.board = board
                if mod_in_exp:
                    is_modified = True

            elif cmd == ".g":
                from GBUtils import enter_escape
                is_standard = enter_escape(_("Vuoi giocare alla variante standard (scacchi ortodossi)? (INVIO per si', ESC per no): "))
                if not is_standard:
                    fr_board, fr_fen, fr_num = chess960_utils.setup_fischer_random_board_interactive()
                    if fr_board is not None:
                        if is_modified:
                            SaveGameToFile(game)
                        board = fr_board
                        game, node = InitNewPGN(board)
                        chess960_utils.setup_pgn_headers_chess960(game, board, fr_fen)
                        game_state.board = board
                        is_modified = False
                        chess960_utils.configure_engine_for_chess960(engine, True)
                    else:
                        print(_("Configurazione Fischer Random annullata."))
                        continue
                else:
                    chess960_utils.configure_engine_for_chess960(engine, False)

                # Avvio partita contro il motore
                final_node = game_mode.StartEngineGame(node, engine, sharing_window=sharing_window)
                # Sincronizza stato al ritorno
                node = final_node
                board = node.board()  # Ricrea board dallo stato finale
                game_state.board = board
                is_modified = True
                from GBUtils import enter_escape
                print(_("\nSuggerimento: puoi esplorare e analizzare la partita appena conclusa."))
                if enter_escape(_("Vuoi analizzare la partita? (INVIO per si', ESC per no): ")):
                    print(_("Accesso alla modalità esplorazione..."))
                    mod_in_exp, final_node = ExplorerMode(game, engine, sharing_window=sharing_window)
                    node = final_node
                    board = node.board()
                    game_state.board = board
                    if mod_in_exp:
                        is_modified = True

            elif cmd == ".b":
                print(board)

            elif cmd == ".d":
                if drawing_menu(game, node):
                    is_modified = True
                    if sharing_window and sharing_window.is_active():
                        sharing_window.trigger_update()

            elif cmd == ".bm":
                white, black = CalculateMaterial(board)
                print(
                    _("Materiale sulla scacchiera: {w}/{b} Bianco/Nero").format(
                        w=white, b=black
                    )
                )

            elif cmd == ".pt":
                AddingPGNTAGS(game)
                is_modified = True

            elif cmd == ".gp":
                CopyPGNToClipboard(game)

            elif cmd == ".i":
                export_board_pdf(board, node)

            elif cmd == ".ii":
                image_settings_menu()
                if sharing_window and sharing_window.is_active():
                    sharing_window.trigger_update()

            elif cmd == ".cs":
                if sharing_window is None or not sharing_window.is_active():
                    print(_("\nAttivazione condivisione scacchiera (finestra grafica per didattica)..."))
                    print(_("ISTRUZIONI:"))
                    print(_("- Puoi condividere la nuova finestra su Meet, Zoom o Teams."))
                    print(_("- Per continuare ad inserire comandi, ricordati di riportare il focus (cliccare) su questa finestra di testo della console."))
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

            elif cmd in [".csb", ".csn", ".cst"]:
                if sharing_window is None or not sharing_window.is_active():
                    print(_("Errore: devi prima avviare la condivisione con il comando .cs"))
                else:
                    if cmd == ".csb":
                        sharing_window.set_orientation("white")
                        print(_("Orientamento scacchiera condivisa impostato: Bianco (fisso)."))
                    elif cmd == ".csn":
                        sharing_window.set_orientation("black")
                        print(_("Orientamento scacchiera condivisa impostato: Nero (fisso)."))
                    elif cmd == ".cst":
                        sharing_window.set_orientation("turn")
                        print(_("Orientamento scacchiera condivisa impostato: in base al turno (dinamico)."))

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
                print(_("Visualizzazione dell'output di testo sotto la scacchiera {status}.").format(status=status_str))
                Acusticator(["c5", 0.08, 0, config.VOLUME, "g5", 0.08, 0, config.VOLUME])
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
                    node = game
                    board = CustomBoard()
                    if "FEN" in game.headers:
                        board.set_fen(game.headers["FEN"])
                    for move in game.mainline_moves():
                        board.push(move)
                    node = game.end()
                    game_state.board = board
                    is_modified = is_corrected
                    print(_("Nuova partita caricata."))
                    print(board)
                else:
                    print(_("PGN non valido o appunti vuoti."))

            elif cmd == ".gf":
                pyperclip.copy(board.fen())
                print(_("Partita in FEN. Copiata negli appunti"))

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
                new_fen = BoardEditor(starting_fen=board.fen(), sharing_window=sharing_window)
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

            elif cmd_clean == ".a":
                if not engine:
                    print(_("Motore non caricato in Orologic."))
                else:
                    sec = number_command if number_command > 0 else 1
                    print(
                        _("Analisi posizione corrente per {s} secondi.").format(s=sec)
                    )
                    limit = chess.engine.Limit(time=sec)
                    try:
                        info_result = engine.analyse(
                            board, limit, multipv=orologic_engine.multipv
                        )
                        info = info_result
                        if isinstance(info, list):
                            ShowStats(board, info[0])
                        elif isinstance(info, dict):
                            ShowStats(board, info)
                    except Exception as e:
                        print(_("Errore analisi: {e}").format(e=e))

            elif cmd_clean == ".l":
                if info:
                    idx = number_command - 1 if number_command > 0 else 0
                    if idx < 0:
                        idx = 0
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
                        from ..ui import enter_escape

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
    builtins.print = _orig_print
