import chess

from .. import board_utils, localizzazione
from ..config import _


# Il conteggio del materiale e' quello di board_utils, valido per tutto
# il programma.
CalculateMaterial = board_utils.CalculateMaterial


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
