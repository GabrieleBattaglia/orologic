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
