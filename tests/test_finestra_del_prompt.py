# Orologic, prove della finestra di composizione del prompt.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra del prompt chiesta da Gabriele nel collaudo della T6: il
modello come fila di elementi, avanti e indietro, e la finestra guidata coi
tasti, Invio, Spazio, Canc e Ctrl con le frecce, come la usa lui."""

import time

import pytest
import wx
from conftest import pompa

from orologic_modules import dialoghi, modello_prompt

# Il modello come elementi, senza finestre.


@pytest.mark.parametrize(
    ("modello", "elementi", "secondi", "riscritto"),
    [
        ("%b %n %m", [{"codice": "b", "verboso": False}, {"codice": "n", "verboso": False}, {"codice": "m", "verboso": False}], 0, "%b %n %m"),
        ("%4 %bv %np %m", [{"codice": "b", "verboso": True}, {"codice": "np", "verboso": False}, {"codice": "m", "verboso": False}], 4, "%4 %bv %np %m"),
        ("%i/%a %m", [{"codice": "i", "verboso": False}, {"testo": "/"}, {"codice": "a", "verboso": False}, {"codice": "m", "verboso": False}], 0, "%i / %a %m"),
        ("%B %VV fine", [{"codice": "b", "verboso": False}, {"codice": "v", "verboso": True}, {"testo": "fine"}], 0, "%b %vv fine"),
        ("%b 100%% %z", [{"codice": "b", "verboso": False}, {"testo": "100% %z"}], 0, "%b 100%% %%z"),
    ],
)
def test_il_modello_come_elementi(modello, elementi, secondi, riscritto):
    assert modello_prompt.elementi(modello) == (elementi, secondi)
    assert modello_prompt.modello_degli_elementi(elementi, secondi) == riscritto
    assert modello_prompt.elementi(riscritto) == (elementi, secondi)


def test_i_simboli_e_le_loro_regole():
    codici = [codice for codice, _descrizione in modello_prompt.simboli()]
    assert codici[:4] == ["b", "n", "bp", "np"]
    assert set(codici) == modello_prompt.lettere() | {"bp", "np"}
    regole = modello_prompt._regole()
    # La regola della v no: nella finestra la forma estesa e' un interruttore.
    assert modello_prompt.regole_del_simbolo("b") == []
    assert modello_prompt.regole_del_simbolo("bp") == [regole["percentuali"]]
    assert modello_prompt.regole_del_simbolo("m") == [regole["dopo_la_mossa"], regole["scacchiera"]]
    assert modello_prompt.regole_del_simbolo("o") == []
    # Le righe del Blocco note sono quelle di prima.
    assert len(modello_prompt.righe_d_aiuto()) == len(modello_prompt.catalogo()) + 7


# La finestra.


class Prova:
    """La finestra del prompt, mostrata sul desktop nascosto, con i testi
    liberi, gli annunci e i suoni d'errore registrati."""

    def __init__(self, modello):
        self.testi = []
        self.annunci = []
        self.errori = []
        self.dialogo = dialoghi.FinestraPrompt(None, modello, self._chiedi, self.annunci.append, lambda: self.errori.append("errore"))
        self.dialogo.Show()
        pompa(lambda: wx.Window.FindFocus() is self.dialogo.disponibili)
        self.dialogo.ultimo_invio = 0

    def _chiedi(self, _genitore, valore):
        self.testi.append(valore)
        return self.risposta

    def tasto(self, controllo, codice, ctrl=False):
        """Un tasto sul controllo, fuori dalla grazia dell'Invio; restituisce
        se e' passato oltre."""
        self.dialogo.ultimo_invio = 0
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.SetKeyCode(codice)
        evento.SetControlDown(ctrl)
        evento.SetEventObject(controllo)
        self.dialogo._tasto(evento)
        return evento.GetSkipped()

    def voci(self, lista):
        return [lista.GetString(i) for i in range(lista.GetCount())]

    def seleziona(self, lista, testo):
        lista.SetSelection(self.voci(lista).index(testo))


@pytest.fixture
def prova(app):
    aperte = []

    def apri(modello):
        aperta = Prova(modello)
        aperte.append(aperta)
        return aperta

    yield apri
    for aperta in aperte:
        aperta.dialogo.Destroy()
    pompa(lambda: False, 0.1)


def test_disponibili_e_prompt_all_apertura(prova):
    p = prova("%b %n %m")
    d = p.dialogo
    assert p.voci(d.prompt) == ["%b tempo del Bianco", "%n tempo del Nero", "%m numero di mossa con l'ultima mossa, come il prompt classico"]
    assert p.voci(d.disponibili)[0] == "%bp percentuale di tempo consumato dal Bianco"
    assert p.voci(d.disponibili)[-1] == "Testo libero"
    assert len(p.voci(d.disponibili)) == len(modello_prompt.simboli()) - 3 + 1
    assert d.esempio.GetValue().startswith("Anteprima: ")
    assert d.spiegazione.GetValue().startswith("%bp percentuale di tempo consumato dal Bianco\n%bp e %np:")
    assert d.modello == "%b %n %m"


def test_invio_spazio_e_testo_libero(prova):
    p = prova("%b %n %m")
    d = p.dialogo
    # Invio: il simbolo in fondo al prompt, il fuoco resta sul vicino.
    assert not p.tasto(d.disponibili, wx.WXK_RETURN)
    assert d.elementi[-1] == {"codice": "bp", "verboso": False}
    assert d.disponibili.GetStringSelection() == "%np percentuale di tempo consumato dal Nero"
    assert pompa(lambda: wx.Window.FindFocus() is d.disponibili)
    # Lo Spazio sul simbolo con la forma estesa la accende, accanto alla voce.
    p.seleziona(d.disponibili, "%i il tuo tempo, dove hai un colore: Easyfish e Lichess")
    assert not p.tasto(d.disponibili, wx.WXK_SPACE)
    assert d.disponibili.GetStringSelection() == "%i il tuo tempo, dove hai un colore: Easyfish e Lichess (verboso)"
    assert not p.tasto(d.disponibili, wx.WXK_RETURN)
    assert d.elementi[-1] == {"codice": "i", "verboso": True}
    assert d.prompt.GetString(d.prompt.GetCount() - 1).endswith("(verboso)")
    # Su un simbolo senza forma estesa, la nota bassa dell'errore.
    p.seleziona(d.disponibili, "%h chi ha piu' tempo: < il Bianco, > il Nero, = pari")
    p.tasto(d.disponibili, wx.WXK_SPACE)
    assert p.errori == ["errore"]
    # Testo libero: chiede il testo, lo mette nel prompt, e resta.
    p.risposta = "  /  "
    d.disponibili.SetSelection(d.disponibili.GetCount() - 1)
    p.tasto(d.disponibili, wx.WXK_RETURN)
    assert d.elementi[-1] == {"testo": "/"}
    assert p.voci(d.disponibili)[-1] == "Testo libero"
    assert d.modello == "%b %n %m %bp %iv /"
    # Un Invio dentro la grazia non fa niente.
    d.ultimo_invio = time.monotonic()
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(wx.WXK_RETURN)
    evento.SetEventObject(d.disponibili)
    d._tasto(evento)
    assert len(d.elementi) == 6


def test_canc_ctrl_frecce_e_testo_da_riscrivere(prova):
    p = prova("%i/%a %m")
    d = p.dialogo
    assert p.voci(d.prompt)[1] == "Testo libero: /"
    # Invio sul testo libero del prompt lo fa riscrivere.
    d.prompt.SetSelection(1)
    p.risposta = "-"
    p.tasto(d.prompt, wx.WXK_RETURN)
    assert p.testi == ["/"]
    assert d.elementi[1] == {"testo": "-"}
    assert d.prompt.GetSelection() == 1
    # Ctrl e freccia su: prima; in cima, la nota bassa dell'errore.
    p.tasto(d.prompt, wx.WXK_UP, ctrl=True)
    assert d.elementi[0] == {"testo": "-"}
    assert d.prompt.GetSelection() == 0
    p.tasto(d.prompt, wx.WXK_UP, ctrl=True)
    assert p.errori == ["errore"]
    p.tasto(d.prompt, wx.WXK_DOWN, ctrl=True)
    assert d.elementi[1] == {"testo": "-"}
    assert d.modello == "%i - %a %m"
    # Canc: il simbolo torna fra i disponibili, il fuoco resta nel prompt.
    d.prompt.SetFocus()
    d.prompt.SetSelection(0)
    p.tasto(d.prompt, wx.WXK_DELETE)
    assert "%i il tuo tempo, dove hai un colore: Easyfish e Lichess" in p.voci(d.disponibili)
    assert d.prompt.GetSelection() == 0
    assert pompa(lambda: wx.Window.FindFocus() is d.prompt)
    # Svuotato il prompt, il fuoco torna ai disponibili, sull'ultimo tornato.
    for _volta in range(3):
        p.tasto(d.prompt, wx.WXK_DELETE)
    assert d.elementi == []
    assert pompa(lambda: wx.Window.FindFocus() is d.disponibili)
    assert d.disponibili.GetStringSelection().startswith("%m ")
    assert d.esempio.GetValue() == ""


def test_aggiornamento_spiegazione_e_annunci(prova):
    p = prova("%b %n %m")
    d = p.dialogo
    d.secondi.SetValue(5)
    d.aggiorna()
    assert d.modello == "%5 %b %n %m"
    assert "Prompt dinamico, riscritto ogni 5 secondi." in d.esempio.GetValue()
    # Scegliendo una voce, la spiegazione la segue e si annunciano le regole.
    d.prompt.SetSelection(2)
    evento = wx.CommandEvent(wx.wxEVT_LISTBOX, d.prompt.GetId())
    evento.SetEventObject(d.prompt)
    evento.SetInt(2)
    d.prompt.GetEventHandler().ProcessEvent(evento)
    regole = modello_prompt.regole_del_simbolo("m")
    assert d.spiegazione.GetValue() == "\n".join([d.prompt.GetString(2), *regole])
    # L'annuncio arriva dopo il ritardo, in coda alla voce letta da NVDA.
    assert p.annunci == []
    assert pompa(lambda: p.annunci == [regole])


def test_verboso_o_breve_in_coda_e_solo_l_ultimo_annuncio(prova):
    p = prova("%b %n %m")
    d = p.dialogo
    pompa(lambda: False, 0.5)
    del p.annunci[:]
    p.seleziona(d.disponibili, "%i il tuo tempo, dove hai un colore: Easyfish e Lichess")
    d._spiega(d.disponibili, annuncia=True)
    assert d.spiegazione.GetValue().split("\n")[-1] == "breve"
    # Lo Spazio: la voce si riscrive, e in coda si annuncia il nuovo stato.
    p.tasto(d.disponibili, wx.WXK_SPACE)
    assert d.spiegazione.GetValue().split("\n")[-1] == "verboso"
    assert pompa(lambda: p.annunci == [["verboso"]])
    # Scorrendo in fretta si annuncia solo l'ultima voce; un simbolo senza
    # regole e senza forma estesa non annuncia niente.
    p.seleziona(d.disponibili, "%a il tempo dell'avversario, dove hai un colore")
    d._spiega(d.disponibili, annuncia=True)
    p.seleziona(d.disponibili, "%o nome dell'avversario")
    d._spiega(d.disponibili, annuncia=True)
    pompa(lambda: False, 0.5)
    assert p.annunci == [["verboso"]]
    assert d.spiegazione.GetValue() == "%o nome dell'avversario"


def test_ok_lascia_com_era_il_modello_che_non_cambia(prova):
    p = prova("%i/%a %m")
    assert p.dialogo.modello == "%i/%a %m"
    p.dialogo.secondi.SetValue(3)
    assert p.dialogo.modello == "%3 %i / %a %m"
    p.dialogo.secondi.SetValue(0)
    assert p.dialogo.modello == "%i/%a %m"


# Dalle impostazioni.


def _con_la_finestra_del_prompt(finestra, azioni):
    errori = []

    def guida():
        dialogo = finestra.gestore.finestra_del_prompt
        if dialogo is None or not dialogo.IsModal():
            wx.CallLater(30, guida)
            return
        try:
            azioni(dialogo)
        except Exception as errore:  # noqa: BLE001 - si rilancia fuori dal dialogo
            errori.append(errore)
            dialogo.EndModal(wx.ID_CANCEL)

    wx.CallLater(30, guida)
    finestra.gestore.cambia("prompt", None)
    if errori:
        raise errori[0]


@pytest.fixture
def prompt_di_prima():
    prima = modello_prompt.modello()
    yield prima
    modello_prompt.salva(prima)


def test_dalle_impostazioni_ok_salva_annulla_no(finestra, prompt_di_prima, monkeypatch):
    monkeypatch.setitem(finestra.annunci, "attivi", True)
    # Anche se il testo che arriva interrompe, la spiegazione va in coda.
    monkeypatch.setitem(finestra.annunci, "testo_interrompe", True)
    modello_prompt.salva("%b %n %m")

    def aggiungi_e_conferma(dialogo):
        dialogo.disponibili.SetSelection(0)
        dialogo.aggiungi()
        # Gli annunci attivi: le regole del simbolo vanno alla sintesi, in coda.
        regola = modello_prompt._regole()["percentuali"]
        assert pompa(lambda: regola in finestra.sintesi.testi())
        assert all(not interrompi for testo, _chiave, _dove, interrompi in finestra.sintesi.chiamate if testo == regola)
        dialogo.conferma()

    _con_la_finestra_del_prompt(finestra, aggiungi_e_conferma)
    assert modello_prompt.modello() == "%b %n %m %bp"

    def aggiungi_e_annulla(dialogo):
        dialogo.disponibili.SetSelection(0)
        dialogo.aggiungi()
        dialogo.EndModal(wx.ID_CANCEL)

    _con_la_finestra_del_prompt(finestra, aggiungi_e_annulla)
    assert modello_prompt.modello() == "%b %n %m %bp"
