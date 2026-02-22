import chess
import chess.engine
from GBUtils import dgt, key, menu
from .constants import MNEXPLORER
from .board import CustomBoard
from .utils import InsertedCounter
from ..config import _

def BoardEditor():
    """Editor della scacchiera per impostare posizioni personalizzate."""
    print(_("\\nBoard Editor. Setting up a new position by placing pieces over the board.\\nPlease enter piece and square like Ng1. Type 'ok' when you're done; type Xf2 to remove a piece."))
    tmp_board=CustomBoard()
    tmp_board.clear()
    prompt=_("PieceSquare (e.g. Kc4)> ")
    inserted_pieces=[]
    while True:
        while True:
            wherewho=dgt(prompt=prompt,kind="s",smin=2,smax=3)
            if wherewho=="ok": break
            square=wherewho[-2:]; piece_name = wherewho[0]
            square=square.lower()
            if square[0] in 'abcdefgh' and square[1] in '12345678' and piece_name in 'RrBbNnKkQqPpXx': break
            else: print(_("It is not a valid square or piece kind"))
        if wherewho=="done" and tmp_board.is_valid(): break
        if wherewho=="ok":
             if tmp_board.is_valid(): break
             else:
                 print(_("Position illegal (e.g. missing Kings). Continue editing."))
                 continue

        position = chess.parse_square(square)
        piece = None
        if piece_name.lower() == 'p':
            piece = chess.Piece(chess.PAWN, chess.WHITE if piece_name.isupper() else chess.BLACK)
        elif piece_name.lower() == 'n':
            piece = chess.Piece(chess.KNIGHT, chess.WHITE if piece_name.isupper() else chess.BLACK)
        elif piece_name.lower() == 'b':
            piece = chess.Piece(chess.BISHOP, chess.WHITE if piece_name.isupper() else chess.BLACK)
        elif piece_name.lower() == 'r':
            piece = chess.Piece(chess.ROOK, chess.WHITE if piece_name.isupper() else chess.BLACK)
        elif piece_name.lower() == 'q':
            piece = chess.Piece(chess.QUEEN, chess.WHITE if piece_name.isupper() else chess.BLACK)
        elif piece_name.lower() == 'k':
            piece = chess.Piece(chess.KING, chess.WHITE if piece_name.isupper() else chess.BLACK)
        
        if piece_name in "Xx":
            tmp_board.remove_piece_at(position)
        else: tmp_board.set_piece_at(position, piece)
        
        if not tmp_board.is_valid(): print(_("Position still illegal."))
        inserted_pieces.append(piece_name)
        prompt = InsertedCounter(tmp_board, inserted_pieces)
        
    print(_("Now tell me if it's white's turn (W) or black's (B)? "))
    while True:
        color_turn = key(attesa=45).lower()
        if color_turn in "bw": break
        else: print(_("Please choose W for White or B for Black"))
    if color_turn == "w": tmp_board.turn = chess.WHITE
    else: tmp_board.turn = chess.BLACK
    
    any_en_passant=dgt(prompt=_("is there en_passant? If so enter the square, otherwise just hit enter:"),kind="s",smax=2)
    if any_en_passant!="":
        if any_en_passant[0] in "ABCDEFGH" and any_en_passant[1] in "12345678":
            tmp_board.set_ep_square(chess.parse_square(any_en_passant[:2]))
            print(_("Set"))
            
    print(_("Let me know what about castling rights."))
    castling_rights = 0
    questions = [
        (_("White kingside castling (O-O)"), chess.BB_H1),
        (_("White queenside castling (O-O-O)"), chess.BB_A1),
        (_("Black kingside castling (O-O)"), chess.BB_H8),
        (_("Black queenside castling (O-O-O)"), chess.BB_A8)]
    for question, bb in questions:
        response = key(prompt=f"{question}? (y/n): ").strip().lower()
        if response == 'y':
            castling_rights |= bb
    tmp_board.castling_rights = castling_rights
    print(_("Set"))
    
    tmp_board.fullmove_number = dgt(prompt=_("Moves starting from, 1? "),kind="i",imin=1,imax=250,default=1)
    tmp_board.halfmove_clock = dgt(prompt=_("Half move clock counting from, 0? "),kind="i",imin=0,imax=250,default=0)
    print(_("Set")+"\\n"+str(tmp_board))
    return tmp_board.fen()

def ExplorerMode(game, engine, analysis_time_default=2):
    """Modalità esplorazione per navigare nella partita."""
    node = game
    initial_board = CustomBoard()
    analysis_time = analysis_time_default

    def SyncBoardToNode(node):
        board = initial_board.copy()
        move_stack = []
        temp = node
        while temp.parent:
            move_stack.append(temp.move)
            temp = temp.parent
        move_stack.reverse()
        for move in move_stack:
            if move:
                board.push(move)
        return board

    def GetPrincipalVariationSan(board, pv):
        temp_board = board.copy()
        san_moves = []
        for move in pv:
            san_moves.append(temp_board.san(move))
            temp_board.push(move)
        return san_moves

    current_board = SyncBoardToNode(node)
    
    while True:
        if node.parent:
            parent_move = node.parent.san() if node.parent.move else None
        else:
            parent_move = None
        if node.move:
            current_move = node.san()
        else:
            current_move = _("start")
        if node.variations:
            next_move = node.variations[0].san()
            variant_count = len(node.variations)
        else:
            next_move = game.headers.get("Result", _("end"))
            variant_count = 0
            
        if node.comment:
            print(node.comment)
            
        level = 0
        temp_node = node
        while temp_node.parent:
            if len(temp_node.parent.variations) > 1:
                level += 1
            temp_node = temp_node.parent
            
        level_prefix = f"Lvl{level}" if level > 0 else _("Mainline")
        prompt = f"\\n[{level_prefix}] {parent_move or ''} ({current_move}) {next_move}"
        if variant_count > 1:
            prompt += f" V{variant_count}"
        
        command = key(prompt=prompt)
        
        if command == 'a':
            if node.parent:
                node = node.parent
                current_board = SyncBoardToNode(node)
            else:
                print(_("No previous move"))
        elif command == '?': menu(d=MNEXPLORER,show=True)
        elif command == 'd':
            if node.variations:
                if variant_count > 1:
                    while True:
                        var_index = 0
                        while True:
                            var_prompt = f"\\nVariant {var_index+1}/{variant_count}: {node.variations[var_index].san()}"
                            var_command = key(prompt=var_prompt)
                            if var_command == 'x' and var_index < variant_count - 1:
                                var_index += 1
                            elif var_command == 'w' and var_index > 0:
                                var_index -= 1
                            elif var_command == 'd':
                                node = node.variations[var_index]
                                current_board.push(node.move)
                                break
                            elif var_command == chr(27):  # ESC key
                                return
                        break
                else:
                    node = node.variations[0]
                    current_board.push(node.move)
            else:
                print(_("end of the game"))
        elif command == 'q':
            node = game
            current_board = SyncBoardToNode(node)  # Ripristina la scacchiera iniziale
        elif command == 'e':
            while node.variations:
                node = node.variations[0]
                current_board.push(node.move)  # Applica la mossa per aggiornare la posizione
        elif command == 'z':
            while node.parent and node.parent.variations[0] != node:
                node = node.parent
                current_board = SyncBoardToNode(node)
            if node.parent:
                node = node.parent
                current_board = SyncBoardToNode(node)
        elif command == 'c':
            if node.comment:
                print(node.comment)
        elif command == 's':
            current_board = SyncBoardToNode(node)
            print(_("Analyzing..."))
            if engine:
                 try:
                    analysis = engine.analyse(current_board, chess.engine.Limit(time=analysis_time))
                    best_move_san = current_board.san(analysis['pv'][0])
                    principal_variation_san = ' '.join(GetPrincipalVariationSan(current_board, analysis['pv']))
                    print("\\n"+_("Best move:")+" "+best_move_san)
                    print(_("Best line:")+" "+principal_variation_san)
                 except Exception as e:
                     print(_("Analysis failed: {e}").format(e=e))
            else:
                print(_("Engine not available."))
        elif command == 'r':
            new_time = dgt(prompt=_("Enter analysis time in seconds: "), kind="i", imin=1,imax=1800)
            analysis_time = new_time
        elif command == chr(27):
            print()
            return
