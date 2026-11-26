# Orologic, prove della chiusura del motore (rilievo R8 della revisione 2).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il motore si chiude comunque si esca da Orologic: prima lo chiudeva solo
il punto del menu, e su Alt+F4 restava atexit, che non arrivava mai perche'
l'interprete aspetta prima il filo di SimpleEngine."""

import pytest
from conftest import pompa


def test_alt_f4_al_menu_chiude_il_motore(finestra, monkeypatch):
    import os

    import orologic
    from orologic_modules import engine

    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    chiusure = []
    monkeypatch.setattr(engine, "CloseEngine", lambda: chiusure.append(True))
    monkeypatch.setattr(os, "_exit", lambda codice: None)
    finestra.avvia_il_nucleo(lambda: orologic.esegui(con_la_finestra=True))
    assert pompa(lambda: finestra.attesa.tipo == "menu", 30)
    assert chiusure == []
    finestra.Close()
    assert pompa(lambda: not finestra.nucleo.is_alive(), 10)
    assert chiusure


def test_un_errore_di_main_chiude_comunque_il_motore(monkeypatch):
    import orologic
    from orologic_modules import engine

    chiusure = []
    monkeypatch.setattr(engine, "CloseEngine", lambda: chiusure.append(True))

    def guasto():
        raise RuntimeError("guasto di prova")

    monkeypatch.setattr(orologic, "Main", guasto)
    with pytest.raises(RuntimeError):
        orologic.esegui(con_la_finestra=True)
    assert chiusure == [True]
