import chess
import chess.engine
from GBUtils import dgt, key, menu
from .constants import MNEXPLORER, MNEDITOR
from ..board_utils import CustomBoard
from .utils import InsertedCounter
from ..config import _
from .. import engine as orologic_engine

def BoardEditor(starting_fen=None):
    """Editor della scacchiera con gestione intelligente dei Re e menu a comandi.
       Se starting_fen è fornito, l'editor inizia da quella posizione.
    """
    
    tmp_board = CustomBoard()
    if starting_fen:
        try:
            tmp_board.set_fen(starting_fen)
            print(_("\nEditor avviato dalla posizione corrente."))
        except ValueError:
            print(_("\nErrore FEN posizione iniziale, reset scacchiera."))
            tmp_board.clear()
            tmp_board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
            tmp_board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    else:
        print(_("\nEditor avviato con scacchiera standard."))
        tmp_board.clear()
        # Inserimento Re di default
        tmp_board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        tmp_board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))

    print(_("Comandi principali: Pe4 per piazzare, e4 per svuotare, .? per il menu, . per salvare ed uscire."))
    
    while True:
        prompt = InsertedCounter(tmp_board)
        wherewho = dgt(prompt=prompt, kind="s", smin=1, smax=10).strip()
        
        # Gestione Comandi
        if wherewho.startswith("."):
            if wherewho == ".":
                if tmp_board.is_valid():
                    break
                else:
                    status = tmp_board.status()
                    print(_("Posizione illegale:"))
                    if status & chess.STATUS_NO_WHITE_KING: print(_("- Manca il Re bianco."))
                    if status & chess.STATUS_NO_BLACK_KING: print(_("- Manca il Re nero."))
                    if status & chess.STATUS_TOO_MANY_KINGS: print(_("- Troppi Re sulla scacchiera."))
                    if status & chess.STATUS_TOO_MANY_WHITE_KINGS: print(_("- Troppi Re bianchi."))
                    if status & chess.STATUS_TOO_MANY_BLACK_KINGS: print(_("- Troppi Re neri."))
                    if status & chess.STATUS_PAWNS_ON_FIRST_LAST_RANK: print(_("- Pedoni in prima o ottava traversa."))
                    if status & chess.STATUS_OPPOSITE_CHECK: print(_("- Il giocatore che non ha il turno è sotto scacco."))
                    if status & chess.STATUS_TOO_MANY_CHECKS: print(_("- Troppi scacchi simultanei."))
                    if status & chess.STATUS_IMPOSSIBLE_CHECK: print(_("- Posizione di scacco impossibile."))
                    continue
            
            elif wherewho == ".?":
                menu(d=MNEDITOR, show_only=True)
                continue
                
            elif wherewho == ".s":
                print("\n" + str(tmp_board))
                continue

            elif wherewho == ".t":
                tmp_board.turn = not tmp_board.turn
                color = _("Bianco") if tmp_board.turn == chess.WHITE else _("Nero")
                print(_("Turno impostato al: {c}").format(c=color))
                
            elif wherewho == ".c":
                rights = dgt(prompt=_("Diritti arrocco (es. KQkq o -): "), kind="s", default="").strip()
                try:
                    if rights == "-": tmp_board.castling_rights = 0
                    else: tmp_board.set_castling_fen(rights)
                    print(_("Diritti arrocco aggiornati."))
                except ValueError: print(_("Formato non valido. Usa KQkq."))
                
            elif wherewho == ".e":
                sq_str = dgt(prompt=_("Casa en passant (es. e3 o invio): "), kind="s", default="").strip()
                if not sq_str:
                    tmp_board.ep_square = None
                else:
                    try:
                        tmp_board.ep_square = chess.parse_square(sq_str.lower())
                        print(_("Casa en passant impostata."))
                    except ValueError: print(_("Casa non valida."))
                    
            elif wherewho == ".n":
                n = dgt(prompt=_("Numero mossa: "), kind="i", imin=1, imax=500, default=tmp_board.fullmove_number)
                tmp_board.fullmove_number = n
                
            elif wherewho == ".h":
                h = dgt(prompt=_("Orologio semimosse (halfmove): "), kind="i", imin=0, imax=100, default=tmp_board.halfmove_clock)
                tmp_board.halfmove_clock = h
            
            continue

        # Gestione Inserimento Pezzi / Svuotamento Case
        try:
            if len(wherewho) == 2:
                square_str = wherewho.lower()
                piece_name = None
            elif len(wherewho) == 3:
                piece_name = wherewho[0]
                square_str = wherewho[1:].lower()
            else:
                print(_("Formato non valido. Usa Pe4 o e4."))
                continue
                
            square = chess.parse_square(square_str)
            existing_piece = tmp_board.piece_at(square)
            
            if piece_name is None:
                if existing_piece and existing_piece.piece_type == chess.KING:
                    print(_("Non puoi rimuovere il Re. Spostalo usando Ke4 o ke4."))
                else:
                    tmp_board.remove_piece_at(square)
            else:
                if piece_name.upper() == 'K':
                    color = chess.WHITE if piece_name.isupper() else chess.BLACK
                    old_sq = tmp_board.king(color)
                    if old_sq is not None: tmp_board.remove_piece_at(old_sq)
                    tmp_board.set_piece_at(square, chess.Piece(chess.KING, color))
                else:
                    if existing_piece and existing_piece.piece_type == chess.KING:
                        print(_("Casa occupata dal Re. Sposta prima il Re."))
                    else:
                        color = chess.WHITE if piece_name.isupper() else chess.BLACK
                        p_type = chess.PIECE_SYMBOLS.index(piece_name.lower())
                        tmp_board.set_piece_at(square, chess.Piece(p_type, color))
                        
        except (ValueError, IndexError):
            print(_("Input non riconosciuto."))

    print(_("Editing completato.") + "\n" + str(tmp_board))
    return tmp_board.fen()

def ExplorerMode(game, engine, analysis_time_default=2):
    """Modalità esplorazione per navigare nella partita."""
    node = game
    # Fondamentale: usiamo la scacchiera del PGN come base per la sincronizzazione
    initial_board = game.board() 
    analysis_time = analysis_time_default
    local_multipv = orologic_engine.multipv

    def SyncBoardToNode(node):
        board = initial_board.copy()
        for move in node.mainline_moves(): # Logica più sicura per PGN
            pass # Non usiamo questa, ma la versione a stack
        
        move_stack = []
        temp = node
        while temp.parent:
            move_stack.append(temp.move)
            temp = temp.parent
        move_stack.reverse()
        for move in move_stack:
            if move: board.push(move)
        return board

    def GetPrincipalVariationSan(board, pv):
        temp_board = board.copy()
        san_moves = []
        for move in pv:
            try:
                san_moves.append(temp_board.san(move))
                temp_board.push(move)
            except: break # Evitiamo crash su linee engine sporche
        return san_moves

    current_board = SyncBoardToNode(node)
    
    while True:
        if node.parent:
            parent_move = node.parent.san() if node.parent.move else None
        else: parent_move = None
        
        current_move = node.san() if node.move else _("inizio")
        
        if node.variations:
            next_move = node.variations[0].san()
            variant_count = len(node.variations)
        else:
            next_move = game.headers.get("Result", _("fine"))
            variant_count = 0
            
        if node.comment: print(node.comment)
            
        level = 0
        temp_node = node
        while temp_node.parent:
            if len(temp_node.parent.variations) > 1: level += 1
            temp_node = temp_node.parent
            
        level_prefix = f"Lvl{level}" if level > 0 else _("Principale")
        prompt = f"\n[{level_prefix}] {parent_move or ''} ({current_move}) {next_move}"
        if variant_count > 1: prompt += f" V{variant_count}"
        
        command = key(prompt=prompt)
        
        if command == 'a':
            if node.parent:
                node = node.parent
                current_board = SyncBoardToNode(node)
            else: print(_("Nessuna mossa precedente"))
        elif command == '?': menu(d=MNEXPLORER, show_only=True)
        elif command == 'd':
            if node.variations:
                if variant_count > 1:
                    var_index = 0
                    while True:
                        var_prompt = f"\nVariante {var_index+1}/{variant_count}: {node.variations[var_index].san()}"
                        var_command = key(prompt=var_prompt)
                        if var_command == 'x' and var_index < variant_count - 1: var_index += 1
                        elif var_command == 'w' and var_index > 0: var_index -= 1
                        elif var_command == 'd':
                            node = node.variations[var_index]
                            current_board = SyncBoardToNode(node)
                            break
                        elif var_command == '.': break
                else:
                    node = node.variations[0]
                    current_board.push(node.move)
            else: print(_("fine della partita"))
        elif command == 'q':
            node = game
            current_board = SyncBoardToNode(node)
        elif command == 'e':
            while node.variations:
                node = node.variations[0]
                current_board.push(node.move)
        elif command == 'z':
            while node.parent and node.parent.variations[0] != node:
                node = node.parent
                current_board = SyncBoardToNode(node)
            if node.parent:
                node = node.parent
                current_board = SyncBoardToNode(node)
        elif command == 'b':
            current_board = SyncBoardToNode(node)
            print(current_board)
        elif command == 'u':
            # UNDO/CUT - Elimina mossa corrente e figli
            if node.parent:
                parent = node.parent
                if node in parent.variations:
                    parent.variations.remove(node)
                    node = parent
                    current_board = SyncBoardToNode(node)
                    print(_("Mossa/Variante eliminata. Tornati indietro."))
                else:
                    print(_("Errore: Impossibile trovare la mossa nella lista varianti del padre."))
            else:
                print(_("Impossibile eliminare l'inizio della partita."))
        elif command == 'c':
            if node.comment: print(node.comment)
        elif command == 's':
            current_board = SyncBoardToNode(node)
            print(_("Analisi in corso..."))
            if engine:
                 try:
                    info_list = engine.analyse(current_board, chess.engine.Limit(time=analysis_time), multipv=local_multipv)
                    if not isinstance(info_list, list): info_list = [info_list]
                    for i, info in enumerate(info_list):
                        pv = info.get("pv", [])
                        if not pv: continue
                        score_val = info.get('score').pov(current_board.turn)
                        eval_str = "M{m}".format(m=abs(score_val.mate())) if score_val.is_mate() else "{cp:+.2f}".format(cp=score_val.score(mate_score=10000)/100)
                        wdl = info.get("wdl")
                        wdl_str = "({:.1f}/{:.1f}/{:.1f}) ".format(wdl[0]/10, wdl[1]/10, wdl[2]/10) if wdl else ""
                        line_san = ' '.join(GetPrincipalVariationSan(current_board, pv))
                        print(f"{i+1}. {eval_str} {wdl_str}{line_san}")
                 except Exception as e: print(_("Analisi fallita: {e}").format(e=e))
            else: print(_("Motore non disponibile."))
        elif command == 'r':
            analysis_time = dgt(prompt=_("Secondi analisi: "), kind="i", imin=1, imax=1800, default=analysis_time)
        elif command == 't':
            local_multipv = dgt(prompt=_("Linee analisi: "), kind="i", imin=1, imax=20, default=local_multipv)
            print(_("Linee impostate a {n}").format(n=local_multipv))
        elif command == '.':
            print()
            return
