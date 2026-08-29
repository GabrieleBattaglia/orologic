import chess

from .. import localizzazione
from ..config import _
from .constants import PIECE_VALUES


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


def InsertedCounter(board):
    """Conta i pezzi presenti sulla scacchiera nell'ordine di importanza: Q R B N P."""
    order = ["q", "r", "b", "n", "p"]
    p_parts = []

    white_material, black_material = CalculateMaterial(board)

    for piece_char in order:
        piece_type = chess.PIECE_SYMBOLS.index(piece_char)
        white_count = len(board.pieces(piece_type, chess.WHITE))
        black_count = len(board.pieces(piece_type, chess.BLACK))
        if white_count > 0 or black_count > 0:
            p_parts.append(f"{piece_char.upper()}={white_count}/{black_count}")

    p_string = ", ".join(p_parts)
    if p_string:
        p_string += " "

    p1 = f"[{white_material}/{black_material}]: {p_string}> "
    return p1


def SquaresListToString(board, sq_list, report_piece=False, occupied_only=False):
    """Converte una lista di case in una stringa leggibile.

    Nomi di colonne e pezzi vengono dal dizionario unico del programma, cosi'
    Easyfish parla come il resto di Orologic e rispetta le personalizzazioni.
    """
    voci = []
    for j in sq_list:
        casa = f"{localizzazione.colonna(j[0])} {j[1]}"
        pezzo = board.piece_at(chess.parse_square(j))
        if pezzo:
            if report_piece:
                nome = localizzazione.nome_pezzo(pezzo.piece_type)
                colore = localizzazione.aggettivo_colore(
                    pezzo.color == chess.WHITE,
                    localizzazione.genere_pezzo(pezzo.piece_type),
                )
                voci.append(f"{nome.capitalize()} {colore} in {casa}")
            elif not occupied_only:
                voci.append(casa)
        elif not occupied_only:
            voci.append(casa)
    if not voci:
        return _("Nessuno.")
    return ", ".join(voci) + "."
