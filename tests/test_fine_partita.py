# Orologic, prove della fine partita (rilievi R9 e R94 della revisione 2).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La fine della partita in una funzione sola, board_utils.fine_della_partita,
al posto delle quattro copie di game_flow, easyfish_app e game_mode (R94),
con la regola scelta da Gabriele il 26 novembre 2026 per le patte
richiedibili (R9): matto, stallo, materiale insufficiente, 75 mosse e
quintupla ripetizione chiudono da sole dovunque; triplice ripetizione e 50
mosse contano solo a fatto avvenuto, chiudono da sole contro il motore e in
Easyfish, e in arbitraggio la partita continua finche' l'arbitro non le
assegna."""

import chess
import chess.pgn
import pytest

from orologic_modules import board_utils
from orologic_modules.easyfish import easyfish_app, game_mode

# Due giri di cavalli: dopo la settima semimossa la ripetizione arriverebbe
# con Cg8, dopo l'ottava la posizione iniziale c'e' per la terza volta.
GIRO = ("g1f3", "g8f6", "f3g1", "f6g8")


def _dopo(mosse, fen=chess.STARTING_FEN):
    board = chess.Board(fen)
    for mossa in mosse:
        board.push_uci(mossa)
    return board


@pytest.fixture(autouse=True)
def _senza_suoni(monkeypatch):
    monkeypatch.setattr(board_utils, "suona_la_fine", lambda: None)


def test_la_ripetizione_che_arriverebbe_non_chiude():
    board = _dopo(GIRO + GIRO[:3])
    assert board.can_claim_threefold_repetition()
    assert board_utils.fine_della_partita(board) is None
    assert board_utils.fine_della_partita(board, arbitrata=True) is None


def test_la_triplice_avvenuta_chiude_tranne_in_arbitraggio():
    board = _dopo(GIRO * 2)
    fine = board_utils.fine_della_partita(board)
    assert (fine.risultato, fine.motivo, fine.chiude) == ("1/2-1/2", "triplice", True)
    arbitrata = board_utils.fine_della_partita(board, arbitrata=True)
    assert (arbitrata.motivo, arbitrata.chiude) == ("triplice", False)
    assert ".1/2" in arbitrata.frase()


def test_le_cinquanta_mosse_avvenute_e_le_settantacinque():
    # Re e torre contro re: niente materiale insufficiente.
    prima = chess.Board("8/8/8/4k3/8/8/4K3/7R w - - 99 80")
    assert prima.can_claim_fifty_moves()
    assert board_utils.fine_della_partita(prima) is None
    cinquanta = chess.Board("8/8/8/4k3/8/8/4K3/7R w - - 100 80")
    assert board_utils.fine_della_partita(cinquanta).motivo == "50"
    assert board_utils.fine_della_partita(cinquanta, arbitrata=True).chiude is False
    settantacinque = board_utils.fine_della_partita(chess.Board("8/8/8/4k3/8/8/4K3/7R w - - 150 105"), arbitrata=True)
    assert (settantacinque.motivo, settantacinque.chiude) == ("75", True)


def test_matto_stallo_materiale_e_quintupla_chiudono_dovunque():
    matto = board_utils.fine_della_partita(_dopo(("f2f3", "e7e5", "g2g4", "d8h4")), arbitrata=True)
    assert (matto.risultato, matto.motivo, matto.chiude) == ("0-1", "matto", True)
    assert matto.frase("Rossi") == "Scacco matto! Vince Rossi."
    stallo = board_utils.fine_della_partita(chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"), arbitrata=True)
    assert (stallo.motivo, stallo.chiude) == ("stallo", True)
    materiale = board_utils.fine_della_partita(chess.Board("8/8/8/4k3/8/8/4K3/8 w - - 0 1"), arbitrata=True)
    assert materiale.motivo == "materiale"
    quintupla = board_utils.fine_della_partita(_dopo(GIRO * 4), arbitrata=True)
    assert (quintupla.motivo, quintupla.chiude) == ("quintupla", True)


def test_contro_il_motore_la_patta_solo_a_fatto_avvenuto():
    """game_mode: la patta richiedibile non chiude piu' la partita prima che
    la ripetizione ci sia davvero (R9)."""
    stato = game_mode.EasyfishGameState()
    stato.active_color = chess.BLACK
    stato.game_over = False
    partita = chess.pgn.Game()
    nodo = partita.add_line([chess.Move.from_uci(mossa) for mossa in GIRO + GIRO[:3]])
    board = nodo.board()
    assert not game_mode._chiudi_se_finita(board, nodo, stato)
    assert not stato.game_over
    nodo = nodo.add_main_variation(chess.Move.from_uci(GIRO[3]))
    stato.active_color = chess.WHITE
    assert game_mode._chiudi_se_finita(nodo.board(), nodo, stato)
    assert stato.game_over and partita.headers["Result"] == "1/2-1/2"


def test_in_easyfish_la_patta_solo_a_fatto_avvenuto(capsys):
    partita = chess.pgn.Game()
    nodo = partita.add_line([chess.Move.from_uci(mossa) for mossa in GIRO + GIRO[:3]])
    easyfish_app.CheckGameOver(nodo.board(), nodo)
    assert partita.headers["Result"] == "*"
    assert "Patta" not in capsys.readouterr().out
    nodo = nodo.add_main_variation(chess.Move.from_uci(GIRO[3]))
    easyfish_app.CheckGameOver(nodo.board(), nodo)
    assert partita.headers["Result"] == "1/2-1/2"
    assert "Patta per triplice ripetizione della posizione!" in capsys.readouterr().out
