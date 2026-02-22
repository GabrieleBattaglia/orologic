import chess
import chess.engine
import pyperclip
import os
import sys
from GBUtils import dgt, menu
from .constants import (
    VER, PGN_FILE_PATH, MNMAIN, SYMBOLS_TO_NAME, COLUMN_TO_NATO
)
from .board import CustomBoard
from .utils import (
    CalculateMaterial, SquaresListToString, InfoSquare, ExploreColumnsOrRows,
    GetPiecesPosition, GetPieceMoves
    # MoveToString rimosso, usiamo quella di Orologic
)
from .pgn_handler import (
    LoadGamesFromPGN, NewGame, PastePGNFromClipboard, CopyPGNToClipboard,
    AppendGameToPGN, AddingPGNTAGS
)
from .. import engine as orologic_engine
from ..config import _ 
from ..board_utils import DescribeMove # Import da Orologic
from .engine_handler import ShowStats
from .interaction import ExplorerMode, BoardEditor

def run():
    print(_("Ciao, sono Easyfish {ver}, qui Gabriele Battaglia (IZ4APU).\n\tSono pronto ad aiutarti. Buon divertimento!").format(ver=VER))

    # Init Engine
    if not orologic_engine.ENGINE:
        print(_("Inizializzazione Motore Orologic per Easyfish..."))
        orologic_engine.InitEngine()
    
    engine = orologic_engine.ENGINE
    
    # Load Games
    existing_games = LoadGamesFromPGN(PGN_FILE_PATH)
    print(_("Caricate {n} partite esistenti nel database PGN.").format(n=len(existing_games)))
    
    # New Game
    game, node = NewGame()
    board = CustomBoard()
    
    # State
    analysis_time = 2
    info = {}
    multipv = 3
    prompt = _("MOSSA 1.: ") # Tradotto
    fen_from_clip = ""

    while True:
        key_command = dgt(prompt=prompt, kind="s", smin=1, smax=8192)
        
        if not key_command:
            continue

        number_command_str = ''.join([char for char in key_command if char.isdigit()])
        number_command = int(number_command_str) if number_command_str else 0
        if number_command < 1: number_command = 1
        elif number_command > 600: number_command = 600

        if key_command.startswith("."):
            cmd = key_command.lower()
            cmd_clean = ''.join([char for char in cmd if not char.isdigit()])
            
            if cmd == ".q":
                break
            
            elif cmd == ".?":
                menu(d=MNMAIN, show=True)
            
            elif cmd == ".e":
                print(_("Accesso alla modalità esplorazione..."))
                ExplorerMode(game, engine)
                
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
                    AppendGameToPGN(PGN_FILE_PATH, game, board)
                    game = loaded_game
                    node = game 
                    board = CustomBoard()
                    prompt = "START 1.: "
                    print(_("Partita caricata con successo."))
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
                    print(_("Incolla una nuova posizione FEN dagli appunti...\n\tVerifica FEN..."))
                    try:
                        tmp_board = board.copy()
                        tmp_board.set_fen(fen_from_clip)
                        print(_("FEN valido."))
                        AppendGameToPGN(PGN_FILE_PATH, game, board)
                        print(_("Partita corrente salvata."))
                        
                        existing_games = LoadGamesFromPGN(PGN_FILE_PATH)
                        print(_("Caricate {n} partite esistenti nel database PGN.").format(n=len(existing_games)))
                        
                        board = CustomBoard()
                        board.set_fen(fen_from_clip)
                        
                        game, node = NewGame()
                        game.setup(board) 
                        
                        prompt = "START 1.: "
                        print(board)
                    except ValueError:
                        print(_("Stringa FEN non valida."))
                        
            elif cmd == ".n":
                print(_("Nuova scacchiera pronta. Si parte!"))
                AppendGameToPGN(PGN_FILE_PATH, game, board)
                print(_("Vecchia partita salvata."))
                existing_games = LoadGamesFromPGN(PGN_FILE_PATH)
                print(_("Caricate {n} partite esistenti nel database PGN.").format(n=len(existing_games)))
                game, node = NewGame()
                board = CustomBoard()
                prompt = "START 1.: "
                
            elif cmd == ".be":
                AppendGameToPGN(PGN_FILE_PATH, game, board)
                existing_games = LoadGamesFromPGN(PGN_FILE_PATH)
                game, node = NewGame()
                board = CustomBoard()
                fen = BoardEditor()
                board.set_fen(fen)
                game.setup(board)
                prompt = "START 1.: "
                
            elif cmd == ".ssf":
                os.startfile(".") 
                
            elif cmd == ".snl":
                multipv = dgt(prompt=_("Imposta numero di linee di analisi, attuale {m}: ").format(m=multipv), kind="i", imin=1, imax=256, default=3)
                print(multipv, _("impostato."))
                
            elif cmd_clean == ".a":
                if not engine:
                    print(_("Motore non caricato in Orologic."))
                else:
                    sec = number_command if number_command > 0 else 1
                    print(_("Analisi posizione corrente per {s} secondi.").format(s=sec))
                    limit = chess.engine.Limit(time=sec)
                    try:
                        info = engine.analyse(board, limit, multipv=multipv)
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

        elif key_command.startswith(","):
            if len(key_command) > 1 and key_command[1] in SYMBOLS_TO_NAME:
                algebric = GetPiecesPosition(board, key_command[1])
                found = SYMBOLS_TO_NAME[key_command[1]]
                found += ": " + SquaresListToString(board, algebric)
                print(found)
            else:
                print(_("{p} non è un nome di pezzo valido").format(p=key_command[1] if len(key_command)>1 else ''))

        elif key_command.startswith("-"):
            cmd = key_command.lower()
            if len(cmd) == 3:
                square = cmd[-2:]
                if square[0] in "abcdefgh" and square[1] in "12345678":
                    print(InfoSquare(board, chess.parse_square(square)))
                else:
                    print(_("Casa non valida"))
            elif len(cmd) == 2:
                if cmd[1] in "abcdefgh":
                    found_occupied_square = SquaresListToString(board, ExploreColumnsOrRows(board, ord(cmd[1])-97, vertical=True), True, True)
                    print(_("Pezzi sulla colonna {c}: {s}").format(c=COLUMN_TO_NATO[cmd[1]], s=found_occupied_square))
                elif cmd[1] in "12345678":
                    found_occupied_square = SquaresListToString(board, ExploreColumnsOrRows(board, int(cmd[1])-1, vertical=False), True, True)
                    print(_("Pezzi sulla traversa {r}: {s}").format(r=cmd[1], s=found_occupied_square))
            elif len(cmd) == 4:
                square = cmd[-2:]
                piece = key_command[1].upper()
                
                if square[0] in "abcdefgh" and square[1] in "12345678" and piece in SYMBOLS_TO_NAME:
                     lm = False if board.piece_at(chess.parse_square(square)) else True
                     oos = False
                     legal_move_str = GetPieceMoves(board, piece, square, legal_moves=lm, occupied_only_square=oos)
                     print(_("Mosse di {p} da {c} {r}: {m}").format(p=SYMBOLS_TO_NAME[piece][6:].capitalize(), c=COLUMN_TO_NATO[square[0]], r=square[1], m=legal_move_str))
                else:
                    print(_("Nome pezzo o casa non validi"))
            else:
                print(_("comando di esplorazione non valido"))

        elif key_command.startswith("_"):
            node.comment = key_command[1:]
            print(_("Commento registrato."))

        else:
            move_input = key_command
            if move_input.lower() in ('o-o', 'oo', '00'): move_input = "O-O"
            elif move_input.lower() in ('o-o-o', 'ooo', '000'): move_input = "O-O-O"
            elif move_input[0].lower() in "rnqk": 
                move_input = move_input[0].upper() + move_input[1:]
            
            try:
                move = board.parse_san(move_input)
                # DRY: Usa DescribeMove di Orologic
                print(DescribeMove(move, board))
                
                board.push(move)
                node = node.add_main_variation(move)
                
                if board.turn:
                     temp_move = board.pop()
                     last_san = board.san(temp_move)
                     board.push(temp_move)
                     prompt = f"{board.fullmove_number}... {last_san}: "
                else:
                     temp_move = board.pop()
                     last_san = board.san(temp_move)
                     board.push(temp_move)
                     prompt = f"{board.fullmove_number}. {last_san}: "

            except ValueError:
                print(_("{k}: mossa illegale.").format(k=key_command))

    AppendGameToPGN(PGN_FILE_PATH, game, board)
    updated_games = LoadGamesFromPGN(PGN_FILE_PATH)
    print(_("{n} partite nel database PGN in {p}.\n\tChiusura modalità Easyfish...").format(n=len(updated_games), p=PGN_FILE_PATH))
