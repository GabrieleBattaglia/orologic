# Orologic, prove della finestra degli orologi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra degli orologi chiesta da Gabriele il 21 novembre 2026: la
collezione in un elenco, Crea nuovo, Modifica, Vedi e Canc, i campi che
compaiono e spariscono, le fasi, le tipologie e gli allarmi, guidati coi
tasti come li usa lui, sul desktop nascosto, con suoni e domande registrati."""

import pytest
import wx
from conftest import pompa

from orologic_modules import controlli, finestra_orologi, storage


@pytest.fixture
def collezione():
    """Gli orologi del database delle prove, rimessi com'erano alla fine."""
    prima = storage.LoadDB().get("clocks", [])

    def metti(orologi):
        def scrivi(db):
            db["clocks"] = orologi

        storage.UpdateDB(scrivi)

    metti([])
    yield metti
    metti(prima)


class Prova:
    def __init__(self, monkeypatch):
        self.suoni = []
        self.domande = []
        self.avvisi = []
        self.risposta = True
        monkeypatch.setattr(finestra_orologi, "suona", self.suoni.append)
        monkeypatch.setattr(finestra_orologi, "_bip", lambda: self.suoni.append("bip"))
        self.dialogo = finestra_orologi.FinestraOrologi(None, self._conferma, lambda _g, testo: self.avvisi.append(testo))
        self.dialogo.Show()
        pompa(lambda: wx.Window.FindFocus() is self.dialogo.elenco)

    def _conferma(self, _genitore, testo):
        self.domande.append(testo)
        return self.risposta

    def tasto(self, controllo, codice):
        self.dialogo.ultimo_invio = 0
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.SetKeyCode(codice)
        evento.SetEventObject(controllo)
        self.dialogo._tasto(evento)
        return evento.GetSkipped()

    @staticmethod
    def voci(lista):
        return [lista.GetString(i) for i in range(lista.GetCount())]


@pytest.fixture
def prova(app, collezione, monkeypatch):
    aperte = []

    def apri():
        aperta = Prova(monkeypatch)
        aperte.append(aperta)
        return aperta

    yield apri
    for aperta in aperte:
        aperta.dialogo.Destroy()
    pompa(lambda: False, 0.1)


def _scegli(campo, numero):
    campo.valore = numero
    campo.scelta.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_CHOICE, campo.scelta.GetId()))


def test_crea_un_orologio_con_due_fasi_e_un_allarme(prova):
    p = prova()
    d = p.dialogo
    assert p.voci(d.elenco) == ["Crea nuovo"]
    assert not d.editor.IsShown()
    # Invio su Crea nuovo: i campi compaiono, col fuoco sul nome.
    p.tasto(d.elenco, wx.WXK_RETURN)
    assert p.suoni == ["crea"]
    assert d.editor.IsShown()
    assert pompa(lambda: wx.Window.FindFocus() is d.nome)
    d.nome.ChangeValue("Torneo")
    assert p.voci(d.fasi) == ["Fase 1", "Nuova fase"]
    _scegli(d.gruppi["white"]["ore"], 1)
    _scegli(d.gruppi["white"]["minuti"], 30)
    _scegli(d.gruppi["white"]["inc"], 30)
    _scegli(d.mosse, 40)
    # Nuova fase: la fase di prima ripetuta, col bip del terminale.
    d.fasi.SetSelection(1)
    p.tasto(d.fasi, wx.WXK_RETURN)
    assert p.suoni[-1] == "bip"
    assert p.voci(d.fasi) == ["Fase 1", "Fase 2", "Nuova fase"]
    assert d.fasi.GetSelection() == 1
    assert d.gruppi["white"]["ore"].valore == 1
    _scegli(d.gruppi["white"]["ore"], 0)
    _scegli(d.gruppi["white"]["minuti"], 30)
    # Un allarme a due minuti.
    assert p.voci(d.allarmi) == ["Nuovo allarme"]
    p.tasto(d.allarmi, wx.WXK_RETURN)
    assert pompa(lambda: wx.Window.FindFocus() is d.tempo_allarme)
    d.tempo_allarme.ChangeValue("2:00")
    p.tasto(d.tempo_allarme, wx.WXK_RETURN)
    assert p.voci(d.allarmi) == ["Allarme 1: 2 minuti", "Nuovo allarme"]
    # Salva: l'orologio nel database, l'elenco col sommario, i campi chiusi.
    d.salva()
    assert p.suoni[-1] == "salvato"
    assert not d.editor.IsShown()
    salvato = storage.LoadDB()["clocks"][0]
    assert salvato["name"] == "Torneo"
    assert salvato["alarms"] == [120]
    assert [(f["white_time"], f["black_time"], f["white_inc"], f["moves"], f["tipo"]) for f in salvato["phases"]] == [
        (5400, 5400, 30, 40, "dopo"),
        (1800, 1800, 30, 0, "dopo"),
    ]
    assert p.voci(d.elenco)[0].startswith("Torneo: fase 1: 1 ora e 30 minuti piu' 30 secondi di incremento, per: 40 mosse; fase 2")
    assert salvato["run_seconds"] == 0


def test_modifica_vedi_e_canc(prova, collezione):
    collezione([{"name": "Lampo", "same_time": True, "phases": [{"white_time": 300, "black_time": 300, "white_inc": 3, "black_inc": 3, "moves": 0}],
                 "alarms": [], "note": "per gli amici", "created": "2026-11-01T10:00", "run_seconds": 125}])
    p = prova()
    d = p.dialogo
    assert p.voci(d.elenco) == ["Lampo: 5 minuti piu' 3 secondi di incremento; nessun allarme", "Crea nuovo"]
    # Vedi: la scheda col tachimetro.
    p.tasto(d.elenco, wx.WXK_RETURN)
    assert p.suoni == ["vedi"]
    assert pompa(lambda: wx.Window.FindFocus() is d.scheda)
    assert "Tachimetro: questo orologio ha corso per 125 secondi." in d.scheda.GetValue()
    assert "per gli amici" in d.scheda.GetValue()
    # Modifica: i campi coi dati; il nome cambia, tachimetro e data restano.
    d.elenco.SetSelection(0)
    d.modifica()
    assert p.suoni[-1] == "modifica"
    assert d.nome.GetValue() == "Lampo"
    assert d.gruppi["white"]["minuti"].valore == 5
    assert d.gruppi["white"]["inc"].valore == 3
    d.nome.ChangeValue("Lampo 5+3")
    d.salva()
    salvato = storage.LoadDB()["clocks"][0]
    assert (salvato["name"], salvato["run_seconds"], salvato["created"]) == ("Lampo 5+3", 125, "2026-11-01T10:00")
    # Canc: la domanda, e con si' l'orologio se ne va.
    d.elenco.SetSelection(0)
    p.risposta = False
    p.tasto(d.elenco, wx.WXK_DELETE)
    assert p.domande == ["Sei sicuro di voler eliminare Lampo 5+3?"]
    assert len(storage.LoadDB()["clocks"]) == 1
    p.risposta = True
    p.tasto(d.elenco, wx.WXK_DELETE)
    assert storage.LoadDB()["clocks"] == []
    assert p.suoni[-2:] == ["elimina", "eliminato"]
    assert p.voci(d.elenco) == ["Crea nuovo"]


def test_tempi_distinti_fasi_e_errori(prova, collezione):
    collezione([{"name": "Lampo", "same_time": True, "phases": [{"white_time": 300, "black_time": 300, "white_inc": 3, "black_inc": 3, "moves": 0}],
                 "alarms": [], "note": "", "created": "2026-11-01T10:00", "run_seconds": 0}])
    p = prova()
    d = p.dialogo
    d.elenco.SetSelection(1)
    p.tasto(d.elenco, wx.WXK_RETURN)
    # Senza la spunta compaiono le combo del Nero, coi colori nei nomi.
    assert not d.gruppi["black"]["ore"].scelta.IsShown()
    d.stesso_tempo.SetValue(False)
    d.stesso_tempo.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_CHECKBOX, d.stesso_tempo.GetId()))
    assert d.gruppi["black"]["ore"].scelta.IsShown()
    assert d.gruppi["white"]["minuti"].scelta.GetName() == "Minuti del Bianco"
    assert d.gruppi["black"]["inc"].scelta.GetName() == "Incremento del Nero"
    _scegli(d.gruppi["black"]["minuti"], 3)
    # Gli errori: nome gia' usato, fase con 0 mosse prima di un'altra.
    d.nome.ChangeValue("Lampo")
    d.fasi.SetSelection(1)
    p.tasto(d.fasi, wx.WXK_RETURN)
    d.salva()
    assert p.suoni[-1] == "nome_usato"
    assert "Un orologio con questo nome esiste gia'." in p.avvisi[-1]
    assert "La fase 1 ha 0 mosse: la fase dopo non comincerebbe mai." in p.avvisi[-1]
    # Canc sulla fase 1 non la toglie, sulla 2 si'.
    d.fasi.SetSelection(0)
    p.tasto(d.fasi, wx.WXK_DELETE)
    assert p.suoni[-1] == "no"
    d.fasi.SetSelection(1)
    p.tasto(d.fasi, wx.WXK_DELETE)
    assert p.suoni[-1] == "tolto"
    assert p.voci(d.fasi) == ["Fase 1", "Nuova fase"]
    d.nome.ChangeValue("Asimmetrico")
    d.salva()
    salvato = storage.LoadDB()["clocks"][1]
    assert (salvato["same_time"], salvato["phases"][0]["white_time"], salvato["phases"][0]["black_time"]) == (False, 300, 180)
    # Esc nei campi li chiude senza salvare.
    d.modifica()
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(wx.WXK_ESCAPE)
    evento.SetEventObject(d.nome)
    d._tasto(evento)
    assert not d.editor.IsShown()
    assert p.suoni[-1] == "annullato"


def test_le_tipologie_nell_elenco(prova):
    p = prova()
    d = p.dialogo
    p.tasto(d.elenco, wx.WXK_RETURN)
    assert p.voci(d.tipologie) == [controlli.voce(t) for t in controlli.tipi()]
    assert d.tipologie.GetSelection() == controlli.indice(controlli.PREDEFINITO)


def test_la_tipologia_cambia_i_valori(prova):
    p = prova()
    d = p.dialogo
    p.tasto(d.elenco, wx.WXK_RETURN)
    assert d.gruppi["white"]["inc"].scelta.IsShown()
    assert not d.gruppi["white"]["periodi"].scelta.IsShown()
    # Il byo-yomi: via l'incremento, i secondi e il numero dei periodi.
    d.tipologie.SetSelection(controlli.indice("byoyomi"))
    d.tipologie.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_LISTBOX, d.tipologie.GetId()))
    assert not d.gruppi["white"]["inc"].scelta.IsShown()
    assert d.gruppi["white"]["periodi"].scelta.IsShown()
    assert d.gruppi["white"]["periodo"].scelta.GetName() == "Secondi del periodo"
    _scegli(d.gruppi["white"]["periodi"], 3)
    d.nome.ChangeValue("Go")
    d.salva()
    fase = storage.LoadDB()["clocks"][0]["phases"][0]
    assert (fase["tipo"], fase["white_periodi"], fase["black_periodi"], fase["white_periodo"]) == ("byoyomi", 3, 3, 30)
    assert "byo-yomi di 3 periodi da 30 secondi" in p.voci(d.elenco)[0]
    # Un tempo supplementare prima dell'ultima fase non si salva.
    d.elenco.SetSelection(0)
    d.modifica()
    d.fasi.SetSelection(1)
    p.tasto(d.fasi, wx.WXK_RETURN)
    d.fasi.SetSelection(0)
    d.fasi.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_LISTBOX, d.fasi.GetId()))
    _scegli(d.mosse, 40)
    d.salva()
    assert "Fase 1: Byo-yomi giapponese sta solo nell'ultima fase." in p.avvisi[-1]


def test_la_voce_orologi_del_menu_apre_la_finestra(finestra, collezione):
    from orologic_modules import strato

    finiti = []

    def nucleo():
        strato.orologi()
        finiti.append(True)

    def chiudi():
        if finestra.dialogo_orologi is not None and finestra.dialogo_orologi.IsModal():
            finestra.dialogo_orologi.EndModal(wx.ID_CANCEL)
            return
        wx.CallLater(30, chiudi)

    wx.CallLater(30, chiudi)
    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finiti == [True])
