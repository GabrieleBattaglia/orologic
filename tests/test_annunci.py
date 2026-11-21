# Orologic, prove delle impostazioni degli annunci (tappa T3 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le impostazioni degli annunci: i valori, il database e la finestra che
annuncia secondo le impostazioni, sul desktop nascosto di conftest.py, con
la voce sostituita dal registro."""

import pytest
import wx
from conftest import pompa
from GBsintesi import AUTOMATICA

from orologic_modules import annunci, dialoghi, storage


@pytest.fixture
def database_pulito():
    """Le prove che salvano tolgono poi la chiave dal database delle prove."""
    yield
    storage.UpdateDB(lambda db: db.pop(annunci.CHIAVE, None))


def test_i_predefiniti_e_i_valori_sbagliati():
    assert annunci.normalizza(None) == annunci.PREDEFINITE
    sbagliati = {"attivi": 1, "uscita": "dolphin", "destinazione": "altrove", "tasti_interrompono": "si", "sconosciuta": 3}
    assert annunci.normalizza(sbagliati) == annunci.PREDEFINITE
    giusti = {"attivi": False, "uscita": "nvda", "destinazione": "braille", "tasti_interrompono": False, "testo_interrompe": True}
    assert annunci.normalizza(giusti) == giusti


def test_di_partenza_i_tasti_interrompono_e_il_resto_si_accoda():
    valori = annunci.normalizza({})
    assert annunci.interrompe(valori, dal_tasto=True)
    assert not annunci.interrompe(valori, dal_tasto=False)
    assert valori["uscita"] == AUTOMATICA


def test_le_impostazioni_si_salvano_nel_database(database_pulito):
    valori = annunci.normalizza({"destinazione": "entrambi", "testo_interrompe": True})
    annunci.salva(valori)
    assert annunci.carica() == valori
    assert storage.LoadDB()["volume"] == 0.0


def test_le_righe_delle_impostazioni():
    valori = annunci.normalizza({})
    assert annunci.riga("attivi", valori) == "Annunci: sì"
    assert annunci.riga("destinazione", valori) == "Destinazione degli annunci: solo la sintesi"
    assert annunci.riga("tasti_interrompono", valori) == "La risposta a un tasto: interrompe l'annuncio in corso"
    assert annunci.riga("testo_interrompe", valori) == "Il testo che arriva da sé: si accoda all'annuncio in corso"
    for voce in annunci.VOCI:
        nomi = [annunci.nome_della_scelta(voce, scelta) for scelta in annunci.SCELTE[voce]]
        assert len(set(nomi)) == len(nomi), voce


# La finestra.


def _annuncia(finestra, testo, causa):
    prima = len(finestra.sintesi.chiamate)
    finestra.faccia.scrivi(testo, causa)
    # La finestra mostra e annuncia nello stesso giro.
    assert pompa(lambda: testo.strip() in finestra.area.GetValue())
    return finestra.sintesi.chiamate[prima:]


def test_la_finestra_annuncia_secondo_le_impostazioni(finestra):
    assert _annuncia(finestra, "Tocca a te.\n", "tasto") == [("Tocca a te.", AUTOMATICA, "sintesi", True)]
    assert _annuncia(finestra, "Il nero ha mosso.\n", None) == [("Il nero ha mosso.", AUTOMATICA, "sintesi", False)]
    finestra.annunci = annunci.normalizza(
        {"uscita": "nvda", "destinazione": "entrambi", "tasti_interrompono": False, "testo_interrompe": True}
    )
    assert _annuncia(finestra, "Tocca ancora a te.\n", "tasto") == [("Tocca ancora a te.", "nvda", "entrambi", False)]
    assert _annuncia(finestra, "Il bianco ha mosso.\n", None) == [("Il bianco ha mosso.", "nvda", "entrambi", True)]
    finestra.annunci = annunci.normalizza({"attivi": False})
    assert _annuncia(finestra, "Silenzio.\n", "tasto") == []
    assert "Silenzio." in finestra.area.GetValue()


def test_la_finestra_delle_impostazioni_cambia_e_salva(finestra, monkeypatch, database_pulito):
    proposte = []

    def scegli(genitore, titolo, voci, scelta):
        proposte.append((titolo, voci, scelta))
        return voci.index("sintesi e braille")

    monkeypatch.setattr(finestra, "scegli", scegli)
    voci = [(voce, annunci.riga(voce, finestra.annunci)) for voce in annunci.VOCI]
    dialogo = dialoghi.FinestraImpostazioni(finestra, voci, finestra.gestore.cambia)
    try:
        assert dialogo.lista.GetName() == "Impostazioni"
        assert dialogo.lista.GetCount() == len(annunci.VOCI)
        dialogo.lista.SetSelection(annunci.VOCI.index("destinazione"))
        dialogo.cambia()
        assert proposte == [("Destinazione degli annunci", ["sintesi e braille", "solo la sintesi", "solo il braille"], 1)]
        assert dialogo.lista.GetString(2) == "Destinazione degli annunci: sintesi e braille"
        assert dialogo.lista.GetSelection() == 2
        assert finestra.annunci["destinazione"] == "entrambi"
        assert annunci.carica()["destinazione"] == "entrambi"
        # Annullare la scelta non cambia niente.
        monkeypatch.setattr(finestra, "scegli", lambda *_argomenti: None)
        dialogo.cambia()
        assert finestra.annunci["destinazione"] == "entrambi"
    finally:
        dialogo.Destroy()


def test_ctrl_virgola_apre_le_impostazioni_e_il_fuoco_torna_all_area(finestra):
    """La finestra vera, modale, con il nucleo fermo: si chiude da sola
    poco dopo, come con Esc, e il fuoco torna alla console."""
    viste = []

    def chiudi():
        for aperta in wx.GetTopLevelWindows():
            if isinstance(aperta, dialoghi.FinestraImpostazioni) and aperta.IsModal():
                viste.append((aperta.GetTitle(), aperta.IsMaximized(), aperta.lista.GetString(0)))
                aperta.EndModal(wx.ID_CANCEL)
                return
        wx.CallLater(50, chiudi)

    wx.CallLater(50, chiudi)
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(ord(","))
    evento.SetControlDown(True)
    finestra._tasto_della_finestra(evento)
    assert viste == [("Impostazioni", True, "Tempo analisi default (sec): 1.0")]
    pompa(lambda: False, 0.1)
    assert wx.Window.FindFocus() is finestra.area


def test_il_filtro_delle_impostazioni(app):
    voci = [("a", "Annunci: sì"), ("b", "Volume dei suoni: 40%"), ("c", "Destinazione degli annunci: solo la sintesi")]
    cambiate = []
    dialogo = dialoghi.FinestraImpostazioni(None, voci, lambda chiave, _dialogo: cambiate.append(chiave))
    try:
        assert dialogo.filtro.GetName() == "Filtro delle voci"
        dialogo.filtro.ChangeValue("annùnci")
        dialogo.filtra()
        assert [dialogo.lista.GetString(i) for i in range(dialogo.lista.GetCount())] == ["Annunci: sì", "Destinazione degli annunci: solo la sintesi"]
        dialogo.lista.SetSelection(1)
        dialogo.cambia()
        assert cambiate == ["c"]
        # Il filtro guarda solo il nome, la parte prima dei due punti.
        dialogo.filtro.ChangeValue("sintesi")
        dialogo.filtra()
        assert dialogo.lista.GetString(0) == "Nessuna voce contiene sintesi."
        dialogo.cambia()
        assert cambiate == ["c"]
        dialogo.filtro.ChangeValue("")
        dialogo.filtra()
        assert dialogo.lista.GetCount() == 3
        assert dialogo.lista.GetStringSelection() == "Destinazione degli annunci: solo la sintesi"
    finally:
        dialogo.Destroy()
