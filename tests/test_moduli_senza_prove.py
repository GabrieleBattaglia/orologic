# Orologic, prove dei moduli che non ne avevano (rilievo R92 della revisione
# 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""chess960_utils, pub, e in Easyfish il punteggio e le statistiche contro
il motore, e i motivi di una posizione illegale dell'editor. Niente rete,
niente motore: le funzioni pure, e il database della cartella delle prove."""

import chess
import pytest

from orologic_modules import chess960_utils, pub, storage
from orologic_modules.easyfish import interaction, punteggio_motore, statistiche_motore


def test_le_posizioni_fischer_random():
    board, fen = chess960_utils.get_starting_board(518)
    assert board.chess960 and fen.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
    numero = chess960_utils.get_random_pos_number()
    assert 0 <= numero <= 959
    descrizione = chess960_utils.describe_960_position(board, 518)
    assert "518" in descrizione


def test_le_mail_del_pub():
    iscrizione = pub.mail_d_iscrizione()
    assert iscrizione["destinatario"] and iscrizione["titolo"]
    aiuto = pub.mail_d_aiuto("9.5.0", False, {})
    assert "9.5.0" in str(aiuto)


@pytest.fixture
def senza_carriera(impostazioni_rimesse):
    storage.UpdateDB(lambda db: db.pop(punteggio_motore.CHIAVE, None))
    yield


def test_l_elo_contro_il_motore(senza_carriera):
    assert punteggio_motore.atteso(1500, 1500) == pytest.approx(0.5)
    # Oltre 400 punti di differenza si conta 400, come la FIDE.
    assert punteggio_motore.atteso(1500, 2500) == punteggio_motore.atteso(1500, 1900)
    dati, variazione = punteggio_motore.registra(1, 1500)
    assert variazione == 20 and dati["punteggio"] == 1520 and dati["vinte"] == 1
    assert punteggio_motore.coefficiente({"partite": 40, "punteggio": 2450}) == 10
    assert punteggio_motore.coefficiente({"partite": 40, "punteggio": 2000}) == 20
    righe = punteggio_motore.righe_riepilogo(dati)
    assert righe[0].startswith("Partite 1: vinte 1")


def test_le_statistiche_contro_il_motore():
    assert statistiche_motore.punti_del_risultato("1-0", chess.WHITE) == 1
    assert statistiche_motore.punti_del_risultato("1-0", chess.BLACK) == 0
    assert statistiche_motore.punti_del_risultato("1/2-1/2", chess.BLACK) == 0.5
    assert statistiche_motore.punti_del_risultato("*", chess.WHITE) is None
    partite = [{"punti": 1}, {"punti": 1}, {"punti": 0}, {"punti": 1}, {"punti": 1}, {"punti": 1}]
    assert statistiche_motore.serie_in_corso(partite) == (1, 3)
    assert statistiche_motore.serie_piu_lunga_di_vittorie(partite) == 3
    assert statistiche_motore.serie_in_corso([]) == (None, 0)


def test_i_motivi_della_posizione_illegale():
    assert interaction.errori_della_posizione(chess.Board()) == []
    righe = interaction.errori_della_posizione(chess.Board("8/8/8/8/8/8/8/4k3 w - - 0 1"))
    assert "- Manca il Re bianco." in righe
