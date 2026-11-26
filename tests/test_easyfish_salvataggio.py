# Orologic, prove del salvataggio all'uscita da Easyfish (rilievo R12 della
# revisione 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""All'uscita la partita modificata si salva guardando la partita, non la
scacchiera del momento: chi tornava all'inizio e poi usciva la perdeva."""

from conftest import pompa
from test_easyfish_finestra import _premi, partita

from orologic_modules import engine as orologic_engine
from orologic_modules import finestra_navigatore
from orologic_modules.easyfish import easyfish_app


def test_chi_torna_all_inizio_e_esce_salva_la_partita(finestra, monkeypatch):
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    salvate = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", salvate.append)
    # Il navigatore riporta alla posizione iniziale, la radice della partita.
    monkeypatch.setattr(finestra_navigatore, "naviga", lambda _genitore, partita_navigata, _nodo, *_altro: (partita_navigata, False))
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, "_Bella\r")
    assert pompa(lambda: game.end().comment == "Bella")
    _premi(finestra, ".na\r")
    assert pompa(lambda: finestra.fornitore is not None and not finestra.fornitore()["board"].move_stack)
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert salvate == [game]


def test_il_matto_in_una_variante_non_cambia_il_risultato(monkeypatch):
    """R14: una variante che da' matto col Bianco, in una partita finita
    0-1, scriveva 1-0 nell'intestazione Result."""
    import io

    import chess.pgn

    monkeypatch.setattr(easyfish_app, "Acusticator", lambda *a, **k: None)
    game = chess.pgn.read_game(io.StringIO('[Result "0-1"]\n\n1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Nc3 Bc5 5. d3 0-1'))
    # Dopo 3...Nf6 la linea principale gioca 4.Nc3; la variante il matto.
    nf6 = game.variations[0].variations[0].variations[0].variations[0].variations[0].variations[0]
    matto = nf6.add_variation(chess.Move.from_uci("h5f7"))
    assert matto.board().is_checkmate() and not matto.is_mainline()
    easyfish_app.CheckGameOver(matto.board(), matto)
    assert game.headers["Result"] == "0-1"


def test_il_matto_alla_fine_della_linea_principale_si_segna(monkeypatch):
    import io

    import chess.pgn

    monkeypatch.setattr(easyfish_app, "Acusticator", lambda *a, **k: None)
    game = chess.pgn.read_game(io.StringIO("1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# *"))
    easyfish_app.CheckGameOver(game.end().board(), game.end())
    assert game.headers["Result"] == "1-0"


def test_la_tripla_ripetizione_non_scrive_il_risultato(monkeypatch):
    import io

    import chess.pgn

    monkeypatch.setattr(easyfish_app, "Acusticator", lambda *a, **k: None)
    game = chess.pgn.read_game(io.StringIO("1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 *"))
    assert game.end().board().can_claim_threefold_repetition()
    easyfish_app.CheckGameOver(game.end().board(), game.end())
    assert game.headers["Result"] == "*"
