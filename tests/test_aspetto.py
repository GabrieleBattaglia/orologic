# Orologic, prove dei colori e delle dimensioni dei caratteri.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Colori e dimensioni, dalla richiesta di Gabriele del 21 novembre 2026: le
impostazioni lette e salvate, i colori personali, la finestra principale e
ogni finestra di dialogo con la plancia per elenchi e alberi e l'area per il
resto, e la finestra dei colori guidata con Invio, come la usa Gabriele."""

import time

import pytest
import wx
from conftest import pompa

from orologic_modules import aspetto, dialoghi, impostazioni, modello_prompt, storage

SCELTE = {
    "plancia": {"testo": [100, 100, 0], "sfondo": [0, 0, 0], "dimensione": 16},
    "area": {"testo": [0, 100, 0], "sfondo": [5, 5, 25], "dimensione": 20},
}


def _colore(controllo, parte):
    return (controllo.GetForegroundColour() if parte == "testo" else controllo.GetBackgroundColour()).Get(includeAlpha=False)


def _atteso(ruolo, parte):
    return aspetto.colore(SCELTE[ruolo][parte]).Get(includeAlpha=False)


def _stile_del_testo(area, posizione):
    attributi = wx.TextAttr()
    area.GetStyle(posizione, attributi)
    return attributi.GetTextColour().Get(includeAlpha=False), attributi.GetBackgroundColour().Get(includeAlpha=False), attributi.GetFont().GetPointSize()


@pytest.fixture
def db_pulito():
    def togli(db):
        db.pop(aspetto.CHIAVE, None)
        db.pop(aspetto.CHIAVE_DEI_PERSONALI, None)

    storage.UpdateDB(togli)
    yield
    storage.UpdateDB(togli)


@pytest.fixture
def aspetto_scelto(db_pulito):
    aspetto.salva(SCELTE)
    return SCELTE


# Il modulo, senza finestre.


def test_le_impostazioni_lette():
    assert aspetto.valide(None) == aspetto.vuote()
    assert aspetto.di_windows(aspetto.vuote())
    assert aspetto.valide(SCELTE) == SCELTE
    rovinate = {"plancia": {"testo": [101, 0, 0], "sfondo": [1, 2], "dimensione": 7}, "area": {"testo": [True, 0, 0], "dimensione": 73}}
    assert aspetto.valide(rovinate) == aspetto.vuote()
    assert aspetto.valide({"area": {"dimensione": 72, "testo": (0, 50, 100)}})["area"] == {"testo": [0, 50, 100], "sfondo": None, "dimensione": 72}


def test_le_percentuali_e_i_predefiniti():
    assert [aspetto.da_percentuale(p) for p in (0, 50, 100)] == [0, 127, 255]
    assert [aspetto.a_percentuale(b) for b in (0, 128, 255)] == [0, 50, 100]
    nomi = [nome for nome, _colore in aspetto.predefiniti()]
    assert len(nomi) == len(set(nomi)) >= 12
    assert all(aspetto._colore_valido(colore) for _nome, colore in aspetto.predefiniti())


def test_i_colori_personali(db_pulito):
    assert aspetto.personali() == []
    aspetto.salva_personale("  Mio   giallo ", [90, 90, 10])
    aspetto.salva_personale("Notte", [0, 0, 20])
    assert aspetto.personali() == [("Mio giallo", (90, 90, 10)), ("Notte", (0, 0, 20))]
    # Lo stesso nome prende il colore nuovo, e va in fondo.
    assert aspetto.salva_personale("Mio giallo", [100, 90, 0]) == [("Notte", (0, 0, 20)), ("Mio giallo", (100, 90, 0))]


# Le finestre.


def test_la_finestra_principale_e_il_testo_che_arriva(aspetto_scelto, finestra):
    assert _colore(finestra.plancia, "testo") == _atteso("plancia", "testo")
    assert _colore(finestra.plancia, "sfondo") == _atteso("plancia", "sfondo")
    assert finestra.plancia.GetFont().GetPointSize() == 16
    assert _colore(finestra.area, "sfondo") == _atteso("area", "sfondo")
    finestra.avvia_il_nucleo(lambda: print("Benvenuto.\nSeconda riga."))
    assert pompa(lambda: "Seconda riga." in finestra.area.GetValue())
    # Il testo arrivato dopo ha lo stile dell'area: il RichEdit non lo
    # prende dai colori del controllo.
    for posizione in (1, finestra.area.GetLastPosition() - 2):
        assert _stile_del_testo(finestra.area, posizione) == (_atteso("area", "testo"), _atteso("area", "sfondo"), 20)


def test_ogni_finestra_di_dialogo(aspetto_scelto, app):
    def controlla(dialogo, plancia=(), area=(), pulsanti=()):
        try:
            for controllo in plancia:
                assert (_colore(controllo, "testo"), _colore(controllo, "sfondo")) == (_atteso("plancia", "testo"), _atteso("plancia", "sfondo"))
                assert controllo.GetFont().GetPointSize() == 16
            for controllo in area:
                assert (_colore(controllo, "testo"), _colore(controllo, "sfondo")) == (_atteso("area", "testo"), _atteso("area", "sfondo"))
                assert controllo.GetFont().GetPointSize() == 20
            for controllo in pulsanti:
                assert controllo.GetFont().GetPointSize() == 20
        finally:
            dialogo.Destroy()

    elenco = dialoghi.FinestraImpostazioni(None, [("a", "Voce: 1")], lambda *_argomenti: None)
    pulsante = next(c for c in elenco.GetChildren()[0].GetChildren() if isinstance(c, wx.Button))
    controlla(elenco, plancia=[elenco.lista], area=[elenco.filtro, elenco.GetChildren()[0]], pulsanti=[pulsante])
    scelta = dialoghi.FinestraScelta(None, "Scelta", ["uno", "due"])
    controlla(scelta, plancia=[scelta.lista])
    valore = dialoghi.FinestraValore(None, "Valore", "Quanto?", 5, "intero", 0, 10)
    controlla(valore, area=[valore.campo])
    prompt = dialoghi.FinestraPrompt(None, "%b %4", modello_prompt.righe_d_aiuto(), modello_prompt.righe_d_anteprima, modello_prompt.errori_del_modello)
    # L'anteprima del prompt si riscrive con ChangeValue: lo stile resta.
    assert _stile_del_testo(prompt.esito, 1) == (_atteso("area", "testo"), _atteso("area", "sfondo"), 20)
    controlla(prompt, area=[prompt.campo, prompt.esito, prompt.codici])
    caffe = dialoghi.Caffe(None, "Grazie.")
    controlla(caffe, area=[caffe.testo])


def test_con_le_impostazioni_di_windows_niente_cambia(db_pulito, app):
    elenco = dialoghi.FinestraImpostazioni(None, [("a", "Voce: 1")], lambda *_argomenti: None)
    try:
        di_classe = wx.ListBox.GetClassDefaultAttributes()
        assert elenco.lista.GetForegroundColour() == di_classe.colFg
        assert elenco.lista.GetFont().GetPointSize() == aspetto.carattere_di_windows().GetPointSize()
    finally:
        elenco.Destroy()


# La finestra dei colori, dalle impostazioni.


def _invio(dialogo, controllo):
    """Invio sul controllo, fuori dalla grazia; restituisce se l'evento e'
    passato oltre, al pulsante predefinito."""
    dialogo.ultimo_invio = 0
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(wx.WXK_RETURN)
    evento.SetEventObject(controllo)
    dialogo._tasto(evento)
    return evento.GetSkipped()


def _con_la_finestra_dei_colori(finestra, azioni):
    """Apre la finestra dei colori dalle impostazioni, e quando c'e' le fa
    fare azioni(dialogo), che la chiude."""
    errori = []

    def guida():
        dialogo = finestra.gestore.finestra_dei_colori
        if dialogo is None or not dialogo.IsModal():
            wx.CallLater(30, guida)
            return
        try:
            azioni(dialogo)
        except Exception as errore:  # noqa: BLE001 - si rilancia fuori dal dialogo
            errori.append(errore)
            dialogo.EndModal(wx.ID_CANCEL)

    wx.CallLater(30, guida)
    finestra.gestore.cambia("colori", None)
    if errori:
        raise errori[0]


def test_la_voce_delle_impostazioni():
    assert impostazioni.VOCI.index("colori") == impostazioni.VOCI.index("stile") + 1


def test_colori_e_dimensioni_con_invio(db_pulito, finestra, monkeypatch):
    suoni = []
    monkeypatch.setattr(finestra.gestore, "_suono_dei_colori", suoni.append)
    monkeypatch.setattr(finestra, "chiedi_valore", lambda *_argomenti, **_opzioni: "Mio giallo")
    assert finestra.gestore.riga("colori") == "Colori e dimensioni"
    visti = {}

    def azioni(dialogo):
        # I cursori partono dal colore di Windows dei caratteri della plancia.
        assert dialogo.colore_dei_cursori() == list(aspetto.colore_in_uso(aspetto.vuote(), "plancia", "testo"))
        assert dialogo.predefiniti.GetString(dialogo.predefiniti.GetCount() - 1) == "Salva colore"
        # Cambiare voce in Applica a non tocca i cursori.
        for cursore, valore in zip(dialogo.cursori, (10, 20, 30), strict=True):
            cursore.SetValue(valore)
        dialogo.applica_colori.SetSelection(3)
        assert dialogo.colore_dei_cursori() == [10, 20, 30]
        assert not _invio(dialogo, dialogo.applica_colori)
        assert dialogo.impostazioni["area"]["sfondo"] == [10, 20, 30]
        assert _colore(finestra.area, "sfondo") == aspetto.colore([10, 20, 30]).Get(includeAlpha=False)
        assert suoni == ["applicato"]
        # Invio su un colore predefinito: i cursori lo prendono.
        nomi = [dialogo.predefiniti.GetString(i) for i in range(dialogo.predefiniti.GetCount())]
        dialogo.predefiniti.SetSelection(nomi.index("Giallo"))
        assert not _invio(dialogo, dialogo.predefiniti)
        assert dialogo.colore_dei_cursori() == [100, 100, 0]
        assert suoni[-1] == "caricato"
        # Salva colore: il nome, il colore dei cursori, la voce selezionata.
        dialogo.cursori[2].SetValue(40)
        dialogo.predefiniti.SetSelection(dialogo.predefiniti.GetCount() - 1)
        assert not _invio(dialogo, dialogo.predefiniti)
        assert aspetto.personali() == [("Mio giallo", (100, 100, 40))]
        assert dialogo.predefiniti.GetStringSelection() == "Mio giallo"
        assert dialogo.predefiniti.GetString(dialogo.predefiniti.GetCount() - 1) == "Salva colore"
        # Le dimensioni: 24 punti all'area centrale.
        dialogo.schede.SetSelection(1)
        dialogo.dimensione.SetSelection(24 - aspetto.DIMENSIONE_MINIMA)
        assert not _invio(dialogo, dialogo.dimensione)
        assert dialogo.impostazioni["area"]["dimensione"] is None
        dialogo.applica_dimensione.SetSelection(1)
        assert not _invio(dialogo, dialogo.applica_dimensione)
        assert finestra.area.GetFont().GetPointSize() == 24
        # L'anteprima mostra l'area centrale con la dimensione scelta.
        assert dialogo.anteprima.GetFont().GetPointSize() == 24
        # Un Invio dentro la grazia non fa niente; su un cursore va a OK.
        dialogo.applica_dimensione.SetSelection(0)
        dialogo.ultimo_invio = time.monotonic()
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.SetKeyCode(wx.WXK_RETURN)
        evento.SetEventObject(dialogo.applica_dimensione)
        dialogo._tasto(evento)
        assert dialogo.impostazioni["plancia"]["dimensione"] is None
        assert _invio(dialogo, dialogo.cursori[0])
        visti["suoni"] = list(suoni)
        dialogo.EndModal(wx.ID_OK)

    _con_la_finestra_dei_colori(finestra, azioni)
    assert visti["suoni"] == ["applicato", "caricato", "applicato"]
    salvate = aspetto.carica()
    assert salvate["area"] == {"testo": None, "sfondo": [10, 20, 30], "dimensione": 24}
    assert salvate["plancia"] == {"testo": None, "sfondo": None, "dimensione": None}


def test_annulla_rimette_quello_di_prima(db_pulito, finestra, monkeypatch):
    monkeypatch.setattr(finestra.gestore, "_suono_dei_colori", lambda _evento: None)
    di_windows = _colore(finestra.area, "testo")

    def azioni(dialogo):
        for cursore, valore in zip(dialogo.cursori, (100, 0, 0), strict=True):
            cursore.SetValue(valore)
        dialogo.applica_colori.SetSelection(1)
        _invio(dialogo, dialogo.applica_colori)
        assert _colore(finestra.area, "testo") == aspetto.colore([100, 0, 0]).Get(includeAlpha=False)
        dialogo.EndModal(wx.ID_CANCEL)

    _con_la_finestra_dei_colori(finestra, azioni)
    assert _colore(finestra.area, "testo") == di_windows
    assert aspetto.carica() == aspetto.vuote()


def test_salva_colore_senza_nome_non_salva(db_pulito, finestra, monkeypatch):
    monkeypatch.setattr(finestra, "chiedi_valore", lambda *_argomenti, **_opzioni: None)

    def azioni(dialogo):
        conteggio = dialogo.predefiniti.GetCount()
        dialogo.predefiniti.SetSelection(conteggio - 1)
        _invio(dialogo, dialogo.predefiniti)
        assert dialogo.predefiniti.GetCount() == conteggio
        dialogo.EndModal(wx.ID_CANCEL)

    _con_la_finestra_dei_colori(finestra, azioni)
    assert aspetto.personali() == []
