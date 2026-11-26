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


# R27: la rilettura delle partite cambiate.


def _molte(tmp_path, quante):
    testo = "".join(f'[Event "E{n}"]\n[White "B{n}"]\n[Black "N{n}"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 *\n\n' for n in range(quante))
    return _archivio(tmp_path, testo)


def test_la_rilettura_tiene_le_posizioni(tmp_path):
    archivio = _molte(tmp_path, 300)
    cambi = {n: archivio.testo_della_partita(n).replace(f'[Event "E{n}"]', f'[Event "Nuovo {n}"]') for n in range(0, 300, 3)}
    nuovo = archivio_pgn.riscritto(archivio, cambi, tolte={1})
    assert len(nuovo) == 299
    for inizio, fine, indice in nuovo.pezzi:
        if indice is not None:
            assert (nuovo.schede[indice].inizio, nuovo.schede[indice].fine) == (inizio, fine)
    assert nuovo.info[0]["Event"] == "Nuovo 0" and nuovo.info[2]["Event"] == "Nuovo 3"
    assert nuovo.testo_della_partita(2).startswith('[Event "Nuovo 3"]')


def test_la_rilettura_si_ferma(tmp_path):
    archivio = _molte(tmp_path, 50)
    cambi = {n: archivio.testo_della_partita(n) for n in range(50)}
    nuovo, righe = archivio_pgn.applica_le_modifiche(archivio, cambi, fermato=lambda: True)
    assert nuovo is None and righe == ["Modifiche annullate: l'archivio resta com'era."]


# R69: il giocatore principale; R70: il Result dal segno in fondo.


def test_il_giocatore_principale_degli_archivi_piccoli():
    from orologic_modules import pgn_search

    trova = pgn_search._trova_giocatore_comune
    assert trova([{"White": "Rossi", "Black": "Bianchi"}]) is None
    assert trova([{"White": "?", "Black": "?"}] * 3) is None
    partite = [{"White": "Gabry", "Black": f"N{n}"} for n in range(9)] + [{"White": "X", "Black": "Y"}]
    assert trova(partite) == "Gabry"
    assert trova([{"White": "Gabry", "Black": "A"}, {"White": "B", "Black": "Gabry"}]) == "Gabry"


def test_ripara_prende_il_result_dal_segno_in_fondo(tmp_path):
    testo = '[Event "E"]\n[Site "S"]\n[Date "2024.01.01"]\n[Round "1"]\n[White "A"]\n[Black "B"]\n\n1. e4 e5 1-0\n\n'
    archivio = _archivio(tmp_path, testo)
    assert "Result" in archivio.schede[0].problemi["intestazioni"]
    cambi, _tolte, _conti = archivio_pgn.ripara(archivio, [0], {"intestazioni"})
    assert '[Result "1-0"]' in cambi[0]


def test_un_errore_di_rete_a_meta_tiene_le_partite_arrivate(monkeypatch):
    """R64: un errore di rete a meta' scaricamento buttava tutti i blocchi
    arrivati, mentre Esc li teneva."""
    import contextlib
    import http.client

    from orologic_modules import pgn_search

    class Risposta:
        def __init__(self):
            self.blocchi = [b'[Event "A"]\n[Result "*"]\n\n1. e4 *\n\n']

        def read(self, _quanto):
            if self.blocchi:
                return self.blocchi.pop()
            raise http.client.IncompleteRead(b"")

    monkeypatch.setattr(pgn_search, "_apri_indirizzo", lambda indirizzo: contextlib.nullcontext(Risposta()))
    righe = []
    dati = archivio_pgn._scarica("https://lichess.org/x.pgn", righe)
    assert dati.startswith(b'[Event "A"]')
    assert righe[-1].startswith("Scaricamento interrotto dalla rete")
