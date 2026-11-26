# Orologic, prove della chiave dei doppioni dell'archivio PGN (rilievo R24
# della revisione 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Due partite con le stesse mosse e le stesse intestazioni generiche, ma
una posizione di partenza o un turno diversi, non sono doppioni."""

from orologic_modules import archivio_pgn

STUDIO = '[Event "Studi"]\n[White "?"]\n[Black "?"]\n[Date "????.??.??"]\n[Round "{turno}"]\n[Result "*"]\n{fen}\n1. Kd2 *\n\n'
FEN_UNO = '[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/8/4K3 w - - 0 1"]'
FEN_DUE = '[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/3P4/4K3 w - - 0 1"]'


def _doppioni(tmp_path, testo):
    file = tmp_path / "studi.pgn"
    file.write_text(testo, encoding="utf-8")
    archivio, _righe = archivio_pgn.carica("file", str(file))
    return archivio_pgn.cerca_i_doppioni(archivio)


def test_posizioni_di_partenza_diverse_non_sono_doppioni(tmp_path):
    testo = STUDIO.format(turno="1", fen=FEN_UNO) + STUDIO.format(turno="1", fen=FEN_DUE)
    assert _doppioni(tmp_path, testo) == {}


def test_turni_diversi_non_sono_doppioni(tmp_path):
    testo = STUDIO.format(turno="1", fen=FEN_UNO) + STUDIO.format(turno="2", fen=FEN_UNO)
    assert _doppioni(tmp_path, testo) == {}


def test_la_stessa_partita_due_volte_e_un_doppione(tmp_path):
    testo = STUDIO.format(turno="1", fen=FEN_UNO) * 2
    assert _doppioni(tmp_path, testo) == {1: 0}
