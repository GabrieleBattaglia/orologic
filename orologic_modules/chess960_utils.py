"""Modulo centralizzato per la gestione della variante Chess960 (Fischer Random).
Espone funzioni per generare posizioni, configurare il motore e interagire con l'utente.
"""

import random
from GBUtils import dgt, Acusticator
from . import board_utils
from . import config
from .config import _

# Mappa simbolo pezzo → chiave nel dizionario L10N
PIECE_SYMBOL_TO_KEY = {
    "R": "rook",
    "N": "knight",
    "B": "bishop",
    "Q": "queen",
    "K": "king",
    "P": "pawn",
}


def get_random_pos_number():
    """Restituisce un intero casuale tra 0 e 959 (inclusi)."""
    return random.randint(0, 959)


def get_starting_board(pos_num):
    """Crea e restituisce un CustomBoard configurato per Chess960.
    Args:
        pos_num: Numero della posizione (0-959).
    Returns:
        Tupla (board, fen) con il CustomBoard e il FEN della posizione iniziale.
    """
    board = board_utils.CustomBoard.from_chess960_pos(pos_num)
    return board, board.fen()


def configure_engine_for_chess960(engine_instance, enable=True):
    """Configura l'opzione UCI_Chess960 sull'istanza del motore Stockfish.
    Args:
        engine_instance: Istanza del motore chess.engine.
        enable: True per abilitare Chess960, False per disabilitare.
    """
    if engine_instance is None:
        return
    try:
        engine_instance.configure({"UCI_Chess960": enable})
    except Exception:
        pass


def describe_960_position(board, pos_number=None):
    """Genera una descrizione testuale della posizione Chess960 iniziale.
    Usa i nomi delle colonne e dei pezzi dal dizionario di localizzazione attivo.
    Args:
        board: CustomBoard con la posizione Chess960.
        pos_number: Numero della posizione (opzionale, per il titolo).
    Returns:
        Stringa descrittiva della posizione.
    """
    L10N = config.L10N
    pieces_dict = L10N.get("pieces", {})
    columns_dict = L10N.get("columns", {})
    col_letters = "abcdefgh"
    lines = []
    if pos_number is not None:
        lines.append(_("Variante Fischer Random 960, numero {n}:").format(n=pos_number))
    else:
        # Tenta di recuperare il numero dalla board
        try:
            num = board.chess960_pos()
            lines.append(_("Variante Fischer Random 960, numero {n}:").format(n=num))
        except Exception:
            lines.append(_("Variante Fischer Random 960:"))
    # Descrizione pezzo per colonna (prima traversa, da A a H)
    parts = []
    for i, col in enumerate(col_letters):
        piece = board.piece_at(i)
        if piece:
            piece_key = PIECE_SYMBOL_TO_KEY.get(piece.symbol().upper(), "")
            piece_name = pieces_dict.get(piece_key, {}).get(
                "name", piece.symbol().upper()
            )
        else:
            piece_name = "?"
        col_name = columns_dict.get(col, col).upper()
        parts.append(f"{col_name} {piece_name}")
    lines.append(", ".join(parts))
    return "\n".join(lines)


def setup_pgn_headers_chess960(pgn_game, board, starting_fen=None):
    """Configura gli header PGN per una partita Chess960.
    Args:
        pgn_game: Oggetto chess.pgn.Game.
        board: CustomBoard con posizione Chess960.
        starting_fen: FEN iniziale (se None, usa board.fen()).
    """
    pgn_game.headers["Variant"] = "Chess960"
    pgn_game.headers["SetUp"] = "1"
    pgn_game.headers["FEN"] = starting_fen if starting_fen else board.fen()
    pgn_game.setup(board)


def setup_fischer_random_board_interactive():
    """Logica interattiva per la configurazione di una posizione Fischer Random.
    Chiede all'utente una sequenza di 8 pezzi, '?' per una casuale, o '.' per annullare.
    Returns:
        Tupla (board, fen, pos_number) oppure (None, None, None) se annullato.
    """
    print(_("\n--- Configurazione Fischer Random (Chess960) ---"))
    while True:
        prompt = _(
            "\nInserisci la sequenza di 8 pezzi, '?' per una casuale, o '.' per annullare: "
        )
        user_input = dgt(prompt, kind="s").upper()
        if user_input == "?":
            pos_number = get_random_pos_number()
            board, starting_fen = get_starting_board(pos_number)
            piece_sequence = "".join(
                [board.piece_at(i).symbol().upper() for i in range(8)]
            )
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.8,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.2,
                    0.8,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
            print(
                _("Posizione generata: {sequence} (Numero: {number})").format(
                    sequence=piece_sequence, number=pos_number
                )
            )
            print(describe_960_position(board, pos_number))
            return board, starting_fen, pos_number
        elif user_input == ".":
            return None, None, None
        elif len(user_input) != 8:
            print(_("Errore: la sequenza deve contenere 8 caratteri."))
            Acusticator(["b3", 0.2, 0, config.VOLUME], kind=2)
            continue
        else:
            fen_to_try = "{sequence}/pppppppp/8/8/8/8/PPPPPPPP/{sequence_upper} w - - 0 1".format(
                sequence=user_input.lower(), sequence_upper=user_input
            )
            try:
                board = board_utils.CustomBoard(fen_to_try, chess960=True)
                Acusticator(
                    [
                        "c5",
                        0.1,
                        -0.8,
                        config.VOLUME,
                        "e5",
                        0.1,
                        0,
                        config.VOLUME,
                        "g5",
                        0.2,
                        0.8,
                        config.VOLUME,
                    ],
                    kind=1,
                    adsr=[2, 8, 90, 0],
                )
                pos_number = board.chess960_pos()
                print(
                    _("Posizione valida! Numero Chess960: {number}").format(
                        number=pos_number
                    )
                )
                print(describe_960_position(board, pos_number))
                return board, fen_to_try, pos_number
            except Exception:
                Acusticator(["a3", 0.3, 0, config.VOLUME], kind=2)
                continue
