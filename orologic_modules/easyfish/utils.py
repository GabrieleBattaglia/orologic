import chess
from ..config import _
from .constants import PIECE_VALUES, COLUMN_TO_NATO, CHESSPIECE_TO_NAME, SAN_CHESSPIECES, SYMBOLS_TO_NAME

def CalculateMaterial(board):
    """Calcola il valore del materiale per bianco e nero."""
    white_value = 0
    black_value = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            piece_symbol = piece.symbol()
            if piece_symbol.isupper():
                white_value += PIECE_VALUES[piece_symbol]
            else:
                black_value += PIECE_VALUES[piece_symbol]
    return white_value, black_value

def InsertedCounter(board, l):
    """Conta i pezzi inseriti e mostra il materiale."""
    p=''; p1= '';white_material=0;black_material=0
    for j in l:
        if l.count(j)>0:
            if j not in p: p+=f"{j}-{l.count(j)}, "
    white_material,black_material=CalculateMaterial(board)
    p1=f"[{white_material}/{black_material}]: {p}> "
    return p1

def SquaresListToString(board, l, report_piece=False, occupied_only=False):
    """Converte una lista di case in una stringa leggibile."""
    result=""
    for j in l:
        is_piece = board.piece_at(chess.parse_square(j))
        if is_piece:
            color = _('Bianco') if is_piece.color == chess.WHITE else _('Nero')
            if report_piece:
                result += f"{color} {CHESSPIECE_TO_NAME[is_piece.piece_type]} in {COLUMN_TO_NATO[j[0]]} {j[1]}, "
            elif not occupied_only:
                result += f"{COLUMN_TO_NATO[j[0]]} {j[1]}, "
        elif not occupied_only:
            result += f"{COLUMN_TO_NATO[j[0]]} {j[1]}, "
    if result == "":
        result = _("Nessuno.")
    else:
        result = result[:-2] + "."
    return result

def ExploreColumnsOrRows(board, index, vertical=True):
    """Restituisce una lista di case per una colonna o riga."""
    squares = []
    if board.turn: s1,s2,s3=0,8,1
    else: s1,s2,s3=7,-1,-1
    if vertical:
        for row in range(s1,s2,s3):
            square = chess.square(index, row)
            squares.append(chess.square_name(square))
    else:
        for col in range(s1,s2,s3):
            square = chess.square(col, index)
            squares.append(chess.square_name(square))
    return squares

def GetPiecesPosition(board, piece_type):
    """Trova tutte le posizioni di un tipo di pezzo."""
    if piece_type not in SAN_CHESSPIECES:
        return []
    piece_code = SAN_CHESSPIECES[piece_type]
    piece_color = chess.WHITE if piece_type.isupper() else chess.BLACK
    positions = [square for square in chess.SQUARES if board.piece_at(square) == chess.Piece(piece_code, piece_color)]
    positions_algebraic = [chess.square_name(pos) for pos in positions]
    return positions_algebraic

def InfoSquare(board, square):
    """Fornisce informazioni dettagliate su una casa."""
    piece = board.piece_at(square)
    if piece:
        piece_info = SYMBOLS_TO_NAME[piece.symbol()]
    else: piece_info=_("nessun pezzo")
    attacked_by_white = board.is_attacked_by(chess.WHITE, square)
    attacked_by_black = board.is_attacked_by(chess.BLACK, square)
    defended_by_white = any(board.is_attacked_by(chess.WHITE, s) for s in board.attackers(chess.WHITE, square))
    defended_by_black = any(board.is_attacked_by(chess.BLACK, s) for s in board.attackers(chess.BLACK, square))
    square_color = _("Scura") if (chess.square_rank(square) + chess.square_file(square)) % 2 == 0 else _("Chiara")
    
    if attacked_by_white and attacked_by_black: attacked_info = _("bianco e nero")
    elif attacked_by_white: attacked_info = _("bianco")
    elif attacked_by_black: attacked_info = _("nero")
    else: attacked_info = _("nessuno")
    
    if defended_by_white and defended_by_black: defended_info = _("bianco e nero")
    elif defended_by_white: defended_info = _("bianco")
    elif defended_by_black: defended_info = _("nero")
    else: defended_info = _("nessuno")
    
    info_string = _("Casa {col} {sq} contiene {p}, attaccata da {att}, difesa da {defn}.").format(col=square_color, sq=chess.square_name(square), p=piece_info, att=attacked_info, defn=defended_info)
    return info_string

def GetPieceMoves(board, piece_symbol, square_str, legal_moves=True, occupied_only_square=True):
    """Restituisce le mosse possibili per un pezzo."""
    tmp_board = board.copy()
    square = chess.parse_square(square_str)
    tmp_board.set_piece_at(square, chess.Piece.from_symbol(piece_symbol))
    if legal_moves:
        moves = tmp_board.legal_moves
    else:
        tmp_board.clear()
        tmp_board.set_piece_at(square, chess.Piece.from_symbol(piece_symbol))
        moves = tmp_board.generate_pseudo_legal_moves()
    piece_moves = [move for move in moves if move.from_square == square]
    piece_moves_squares = [move.uci()[2:] for move in piece_moves]
    result = []
    for dest_square_str in piece_moves_squares:
        dest_square = chess.parse_square(dest_square_str)
        piece_at_dest = board.piece_at(dest_square)
        if occupied_only_square:
            if piece_at_dest:
                piece_color = _("Bianco") if piece_at_dest.color == chess.WHITE else _("Nero")
                piece_type = piece_at_dest.symbol().lower() if piece_at_dest.color == chess.BLACK else piece_at_dest.symbol()
                piece_type_full = chess.piece_name(piece_at_dest.piece_type)
                piece_info = f"{piece_color} {piece_type_full} in {COLUMN_TO_NATO[dest_square_str[0]]} {dest_square_str[1]}"
                result.append(piece_info)
        else:
            if piece_at_dest:
                piece_color = _("Bianco") if piece_at_dest.color == chess.WHITE else _("Nero")
                piece_type = piece_at_dest.symbol().lower() if piece_at_dest.color == chess.BLACK else piece_at_dest.symbol()
                piece_type_full = chess.piece_name(piece_at_dest.piece_type)
                piece_info = f"{piece_color} {piece_type_full} in {COLUMN_TO_NATO[dest_square_str[0]]} {dest_square_str[1]}"
            else:
                piece_info = f"{COLUMN_TO_NATO[dest_square_str[0]]} {dest_square_str[1]}"
            result.append(piece_info)
    s = ', '.join(result)
    result = ''
    current_line = ''
    words = s.split(' ')
    for word in words:
        if len(current_line) + len(word) + 1 > 75:
            result += current_line.strip() + '\\n'
            current_line = word + ' '
        else:
            current_line += word + ' '
    result += current_line.strip()
    return result

def DisambiguateMove(board, move):
    """Risolve ambiguità nelle mosse SAN."""
    piece = board.piece_at(move.from_square)
    if not piece:
        return ""
    disambiguation = ""
    for other_move in board.legal_moves:
        if other_move != move and other_move.to_square == move.to_square:
            other_piece = board.piece_at(other_move.from_square)
            if other_piece and other_piece.piece_type == piece.piece_type:
                if chess.square_file(other_move.from_square) == chess.square_file(move.from_square):
                    disambiguation = str(chess.square_rank(move.from_square) + 1)
                elif chess.square_rank(other_move.from_square) == chess.square_rank(move.from_square):
                    disambiguation = COLUMN_TO_NATO[chess.FILE_NAMES[chess.square_file(move.from_square)]]
                else:
                    disambiguation = COLUMN_TO_NATO[chess.FILE_NAMES[chess.square_file(move.from_square)]] + " " + str(chess.square_rank(move.from_square) + 1)
                break
    return disambiguation

def MoveToString(board, move):
    """Converte una mossa in una stringa descrittiva."""
    piece = board.piece_at(move.from_square)
    if piece is None:
        return _("Mossa non valida")
    to_file = chess.square_file(move.to_square)
    to_rank = chess.square_rank(move.to_square)
    to_nato = COLUMN_TO_NATO[chess.FILE_NAMES[to_file]]
    to_square = f"{to_nato} {to_rank + 1}"
    capture = board.is_capture(move)
    capture_text = ""
    if capture:
        captured_piece = board.piece_at(move.to_square)
        if captured_piece:
            capture_text = _("cattura {p} in ").format(p=CHESSPIECE_TO_NAME[captured_piece.piece_type])
        else:
            capture_text = _("cattura in ")  # en passant
    promotion_text = ""
    if move.promotion:
        promotion_text = _(", promuove a {p}").format(p=CHESSPIECE_TO_NAME[move.promotion])
    if board.is_castling(move):
        if move.to_square > move.from_square:
            return _("Arrocco corto")
        else:
            return _("Arrocco lungo")
    board.push(move)
    check_text = ""
    if board.is_checkmate():
        check_text = _(", scacco matto")
    elif board.is_check():
        check_text = _(", scacco")
    board.pop()
    disambiguation = DisambiguateMove(board, move)
    move_description = f"{CHESSPIECE_TO_NAME[piece.piece_type]} {disambiguation} in {to_square}"
    if capture_text:
        move_description = f"{CHESSPIECE_TO_NAME[piece.piece_type]} {disambiguation} {capture_text}{to_square}"
    if promotion_text:
        move_description += promotion_text
    move_description += check_text
    return move_description
