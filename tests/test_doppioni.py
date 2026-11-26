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


# R26: le partite che non partono dalla scacchiera standard restano fuori.


def _archivio(tmp_path, testo):
    file = tmp_path / "varianti.pgn"
    file.write_text(testo, encoding="utf-8")
    archivio, _righe = archivio_pgn.carica("file", str(file))
    return archivio


def test_crazyhouse_e_fen_senza_setup_restano_fuori(tmp_path):
    crazyhouse = '[Event "Z"]\n[Variant "Crazyhouse"]\n[Result "*"]\n\n1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 4. P@d4 *\n\n'
    senza_setup = '[Event "F"]\n[FEN "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"]\n[Result "*"]\n\n1. Kd2 *\n\n'
    normale = '[Event "N"]\n[Result "*"]\n\n1. e4 e5 *\n\n'
    archivio = _archivio(tmp_path, crazyhouse + senza_setup + normale)
    assert [scheda.fuori for scheda in archivio.schede] == [True, True, False]


def test_la_continuazione_si_ferma_su_una_mossa_impossibile(tmp_path):
    import array

    import chess

    from orologic_modules import lettura_pgn

    archivio = _archivio(tmp_path, '[Event "N"]\n[Result "*"]\n\n1. e4 e5 *\n\n')
    # e4, e5, e poi una mossa da una casa vuota.
    mosse = array.array("H", [lettura_pgn.codice(chess.Move.from_uci(u)) for u in ("e2e4", "e7e5", "d3d4")])
    assert archivio.continuazione(chess.Board(), mosse, 0) == "1. e4 e5"
    voce = archivio_pgn.voce_del_ramo(archivio, chess.Board(), chess.Move.from_uci("d3d4"), [0], [], 1, {})
    assert "d3d4" in voce
