# Orologic, prove dell'avvio: la lingua del primo avvio nella finestra (T5a).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La lingua del primo avvio: le lingue col catalogo, la lingua salvata, la
scelta salvata da polipo e la finestra vera sul desktop nascosto di
conftest.py. Il file della lingua delle prove si mette da parte e si
rimette."""

import os
import shutil

import pytest
import wx
from conftest import pompa

from orologic_modules import avvio


@pytest.fixture
def senza_lingua():
    """Il primo avvio: la cartella delle prove senza selected_language.json."""
    file = os.path.join(avvio.cartella_delle_impostazioni(), "selected_language.json")
    da_parte = file + ".da_parte"
    shutil.move(file, da_parte)
    try:
        yield
    finally:
        if os.path.exists(file):
            os.remove(file)
        shutil.move(da_parte, file)


def test_le_lingue_col_catalogo():
    assert avvio.lingue() == ["en", "es", "fr", "it", "pt"]
    assert avvio.nome("it").lower() == "italiano"


def test_con_la_lingua_salvata_non_si_chiede(monkeypatch):
    chieste = []
    assert avvio.lingua_salvata() == "it"
    assert avvio.scegli_la_lingua_se_serve(lambda *argomenti: chieste.append(argomenti)) is None
    assert chieste == []


def test_al_primo_avvio_si_chiede_e_si_salva(senza_lingua, monkeypatch):
    monkeypatch.setattr(avvio, "lingua_di_windows", lambda: "it")
    chieste = []

    def chiedi(codici, scelta):
        chieste.append((codici, scelta))
        return "en"

    assert avvio.lingua_salvata() is None
    assert avvio.scegli_la_lingua_se_serve(chiedi) == "en"
    assert chieste == [(["en", "es", "fr", "it", "pt"], 3)]
    assert avvio.lingua_salvata() == "en"


def test_esc_lascia_la_scelta_a_polipo(senza_lingua, monkeypatch):
    monkeypatch.setattr(avvio, "lingua_di_windows", lambda: None)
    assert avvio.scegli_la_lingua_se_serve(lambda _codici, _scelta: None) is None
    # polipo sceglie da se' e salva: al prossimo avvio non si chiede piu'.
    assert avvio.lingua_salvata() in avvio.lingue()


def test_la_finestra_della_lingua(app):
    viste = []

    def chiudi():
        for aperta in wx.GetTopLevelWindows():
            if isinstance(aperta, wx.Dialog) and aperta.IsModal():
                lista = next(figlio for figlio in aperta.GetChildren()[0].GetChildren() if isinstance(figlio, wx.ListBox))
                viste.append((aperta.GetTitle(), lista.GetName(), lista.GetStringSelection(), aperta.IsMaximized()))
                lista.SetSelection(0)
                aperta.EndModal(wx.ID_OK)
                return
        wx.CallLater(50, chiudi)

    wx.CallLater(50, chiudi)
    scelta = avvio.scegli_nella_finestra(["en", "it"], 1)
    assert scelta == "en"
    assert viste == [("Orologic", "Select your language:", avvio.nome("it"), True)]
    pompa(lambda: False, 0.1)
