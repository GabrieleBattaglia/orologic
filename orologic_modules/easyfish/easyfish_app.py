import chess
import chess.engine
import pyperclip
import os
import sys
from GBUtils import dgt, menu, Acusticator
from .constants import (
    MNMAIN, SYMBOLS_TO_NAME, COLUMN_TO_NATO
)
# DRY: Uso le utility di Orologic
from ..board_utils import CustomBoard, DescribeMove, GameState, NormalizeMove
from .. import ui as orologic_ui
from .utils import (
    CalculateMaterial, SquaresListToString
)
from .pgn_handler import (
    InitNewPGN, PastePGNFromClipboard, CopyPGNToClipboard,
    SaveGameToFile, AddingPGNTAGS
)
from .. import engine as orologic_engine
from ..config import _ 
from .engine_handler import ShowStats
from .interaction import ExplorerMode, BoardEditor

def GetDynamicPrompt(board):
    """Genera il prompt basandosi sul turno e sul numero di mossa."""
    n = board.fullmove_number
    if not board.move_stack:
        return _("INIZIO {n}. ").format(n=n)
    
    last_move = board.pop()
    last_san = board.san(last_move)
    board.push(last_move)
    
    if board.turn == chess.WHITE:
        return f"{n-1}... {last_san}: "
    else:
        return f"{n}. {last_san}: "

def run():
    print(_("\nBenvenuto in Easyfish, la tua interfaccia testuale con il motore scacchistico.\n\tBuon divertimento!"))

    # Init Engine
    if not orologic_engine.ENGINE:
        print(_("Inizializzazione Motore Orologic per Easyfish..."))
        orologic_engine.InitEngine()
    
    engine = orologic_engine.ENGINE
    
    # New Game
    board = CustomBoard() 
    game, node = InitNewPGN(board)
    
    # DRY: GameState
    fake_clock = {"phases": [{"white_time": 0, "black_time": 0, "white_inc": 0, "black_inc": 0, "moves": 0}]}
    game_state = GameState(fake_clock)
    game_state.board = board
    
    # State
    info = {}
    fen_from_clip = ""

    while True:
        prompt = GetDynamicPrompt(board)
        key_command = dgt(prompt=prompt, kind="s", smin=1, smax=8192).strip()
        
        if not key_command:
            continue

        number_command_str = ''.join([char for char in key_command if char.isdigit()])
        number_command = int(number_command_str) if number_command_str else 0
        if number_command < 1: number_command = 1
        elif number_command > 600: number_command = 600

        if key_command.startswith("."):
            cmd = key_command.lower()
            cmd_clean = ''.join([char for char in cmd if not char.isdigit()])
            
            if cmd == ".": # ESCI
                if len(board.move_stack) > 0 or board.fen() != chess.STARTING_FEN:
                     print(_("Salvataggio partita in corso..."))
                     SaveGameToFile(game)
                break
            
            elif cmd == ".?":
                menu(d=MNMAIN, show_only=True)
            
            elif cmd == ".e":
                print(_("Accesso alla modalità esplorazione..."))
                ExplorerMode(game, engine)
                pass
                
            elif cmd == ".b":
                print(board)
                
            elif cmd == ".bm":
                white, black = CalculateMaterial(board)
                print(_("Materiale sulla scacchiera: {w}/{b} Bianco/Nero").format(w=white, b=black))
                
            elif cmd == ".pt":
                AddingPGNTAGS(game)
                
            elif cmd == ".gp":
                CopyPGNToClipboard(game)
                
            elif cmd == ".pg":
                print(_("Incolla una nuova posizione PGN dagli appunti..."))
                loaded_game = PastePGNFromClipboard()
                if loaded_game:
                    print(_("ATTENZIONE: La partita corrente verrà salvata e ne inizierà una nuova."))
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
                        print(_("FEN valido. ATTENZIONE: La partita corrente verrà salvata e ne inizierà una nuova da questa posizione."))
                        SaveGameToFile(game)
                        board = CustomBoard()
                        board.set_fen(fen_from_clip)
                        game, node = InitNewPGN(board)
                        game_state.board = board
                        print(board)
                    except ValueError:
                        print(_("Stringa FEN non valida."))
                        
            elif cmd == ".n":
                print(_("Nuova partita. La corrente verrà salvata."))
                SaveGameToFile(game)
                print(_("Nuova scacchiera pronta. Si parte!"))
                board = CustomBoard()
                game, node = InitNewPGN(board)
                game_state.board = board
                
            elif cmd == ".be":
                print(_("Accesso all'editor. ATTENZIONE: Al termine dell'editing, la partita corrente verrà salvata e ne inizierà una nuova dalla posizione impostata."))
                new_fen = BoardEditor(starting_fen=board.fen())
                if new_fen:
                    SaveGameToFile(game)
                    board = CustomBoard()
                    board.set_fen(new_fen)
                    game, node = InitNewPGN(board)
                    game_state.board = board
                    print(_("Nuova partita avviata dalla posizione editata."))
                    print(board)
                
            elif cmd_clean == ".a":
                if not engine:
                    print(_("Motore non caricato in Orologic."))
                else:
                    sec = number_command if number_command > 0 else 1
                    print(_("Analisi posizione corrente per {s} secondi.").format(s=sec))
                    limit = chess.engine.Limit(time=sec)
                    try:
                        info_result = engine.analyse(board, limit, multipv=orologic_engine.multipv)
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
                    if idx < 0: idx = 0
                    current_info_list = info if isinstance(info, list) else [info]
                    if idx >= len(current_info_list):
                        print(_("Ci sono solo {n} linee di analisi disponibili").format(n=len(current_info_list)))
                        idx = len(current_info_list) - 1
                    if idx == 0:
                        print(_("Migliore:"))
                    else:
                        print(_("{n}° scelta:").format(n=idx+1))
                    ShowStats(board, current_info_list[idx])
                else:
                    print(_("Prima devi eseguire l'analisi con il comando .a"))
            
            else:
                print(_("Spiacente, {cmd} non è un comando valido.\nDigita '.?' per il menu.").format(cmd=cmd))

        elif key_command.startswith("-"):
            param = key_command[1:].strip()
            from .. import config as o_config
            if len(param) == 1 and param.isalpha(): # Colonna
                Acusticator(["c5", 0.07, 0, o_config.VOLUME, "d5", 0.07, 0, o_config.VOLUME, "e5", 0.07, 0, o_config.VOLUME, "f5", 0.07, 0, o_config.VOLUME, "g5", 0.07, 0, o_config.VOLUME, "a5", 0.07, 0, o_config.VOLUME, "b5", 0.07, 0, o_config.VOLUME, "c6", 0.07, 0, o_config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
                orologic_ui.read_file(game_state, param)
            elif len(param) == 1 and param.isdigit(): # Traversa
                rank_number = int(param)
                if 1 <= rank_number <= 8:
                    Acusticator(["g5", 0.07, -1, o_config.VOLUME,"g5", 0.07, -.75, o_config.VOLUME,"g5", 0.07, -.5, o_config.VOLUME,"g5", 0.07, -.25, o_config.VOLUME,"g5", 0.07, 0, o_config.VOLUME,"g5", 0.07, .25, o_config.VOLUME,"g5", 0.07, .5, o_config.VOLUME,"g5", 0.07, .75, o_config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
                    orologic_ui.read_rank(game_state, rank_number)
                else: print(_("Traversa non valida."))
            elif len(param) == 2 and param[0].isalpha() and param[1].isdigit(): # Casa
                Acusticator(["d#4", .7, 0, o_config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
                orologic_ui.read_square(game_state, param)
            else: print(_("Comando esplorazione non riconosciuto."))

        elif key_command.startswith(","):
            from .. import config as o_config
            Acusticator(["a3", .06, -1, o_config.VOLUME, "c4", .06, -0.5, o_config.VOLUME, "d#4", .06, 0.5, o_config.VOLUME, "f4", .06, 1, o_config.VOLUME], kind=3, adsr=[20, 5, 70, 25])
            orologic_ui.report_piece_positions(game_state, key_command[1:2])

        elif key_command.startswith("_"):
            node.comment = key_command[1:]
            print(_("Commento registrato."))

        else:
            move_san = NormalizeMove(key_command)
            move = None
            
            # --- LOGICA ROBUSTA PER INTERPRETAZIONE MOSSA ---
            # 1. Tentativo Standard (come scritto)
            try:
                move = board.parse_san(move_san)
            except ValueError:
                pass
            
            # 2. Tentativo Cattura Pedone senza 'x' (es. ed5 -> exd5)
            if not move and len(move_san) == 3 and move_san[0].islower() and move_san[1].islower() and move_san[2].isdigit():
                try:
                    move_capture = move_san[0] + 'x' + move_san[1:]
                    move = board.parse_san(move_capture)
                except ValueError:
                    pass
            
            # 3. Tentativo Smart 'b' -> Alfiere (es. bc4 -> Bc4 o bxc4)
            if not move and move_san and move_san[0] == 'b':
                # Prova Alfiere maiuscolo
                try:
                    move = board.parse_san('B' + move_san[1:])
                except ValueError:
                    # Se fallisce, prova Alfiere che cattura (es. bc4 -> Bxc4)
                     if len(move_san) == 3: # es. bc4
                        try:
                            move = board.parse_san('Bx' + move_san[1:])
                        except ValueError:
                            pass

            if move:
                print(DescribeMove(move, board))
                board.push(move)
                node = node.add_main_variation(move)
            else:
                color = _("Bianco") if board.turn == chess.WHITE else _("Nero")
                print(_("{k}: mossa illegale per il {c}.").format(k=key_command, c=color))
