# Orologic: le finestre di dialogo della GUI.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le finestre di dialogo della GUI, dalla tappa T3 (Piano della GUI.txt).

  FinestraImpostazioni  la lista piatta delle impostazioni, una riga per
                        voce, Etichetta: valore, col filtro, come in MeTeOra.
  FinestraScelta        una scelta da una lista.
  FinestraValore        un numero o un testo, in un campo che ha per
                        etichetta la domanda del terminale.
  FinestraPrompt        il modello del prompt di gioco, con i codici e
                        l'anteprima.
  Caffe                 l'invito a offrire un caffè, solo a richiesta,
                        con Dona con PayPal e Chiudi.

Si aprono massimizzate, e Esc chiude come Chiudi o Annulla: le finestre
massimizzate si leggono meglio con lo screen reader e il display braille.
Ogni lista ha il suo nome, che NVDA legge, e le istruzioni nella riga sopra.
"""

import contextlib
import time
import unicodedata
import webbrowser

import wx
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from .config import _

INDIRIZZO_PAYPAL = "https://paypal.me/GabrieleBattaglia780"
# Un Invio entro tanti secondi dall'apertura, o dall'Invio di prima, e' un
# tasto tenuto giu', o rimandato da NVDA: non chiude. La misura di Ciechino.
GRAZIA_INVIO = 0.65


def _premuto_invio(evento):
    return evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not evento.HasAnyModifiers()


def normale(testo):
    """Senza maiuscole e senza accenti, per il filtro."""
    scomposto = unicodedata.normalize("NFD", str(testo))
    return "".join(c for c in scomposto if not unicodedata.combining(c)).casefold()


class FinestraImpostazioni(wx.Dialog):
    """Le impostazioni, come in MeTeOra: una lista piatta, una riga per voce,
    Etichetta: valore. voci e' una lista di (chiave, testo della riga). Invio
    sulla lista, o il doppio clic, chiama al_cambio(chiave, dialogo): chi
    apre la finestra chiede il valore nuovo, lo applica e riscrive la riga
    con aggiorna. Il pulsante Chiudi, o Esc, chiude.
    Prima della lista, con Maiuscolo e Tab, il filtro: restano solo le voci
    il cui nome, la parte prima dei due punti, contiene il testo scritto,
    senza badare a maiuscole e accenti. Invio nel filtro torna alla lista."""

    def __init__(self, genitore, voci, al_cambio, titolo=None):
        titolo = titolo or _("Impostazioni")
        super().__init__(genitore, title=titolo, style=STILE_ADATTABILE)
        self._chiavi = [chiave for chiave, _testo in voci]
        self._testi = dict(voci)
        # Le voci mostrate dalla lista, nel suo ordine: tutte, finche' il
        # filtro e' vuoto.
        self._visibili = list(self._chiavi)
        # La voce scelta da chi usa la lista: resta anche quando il filtro la
        # nasconde, e ritorna selezionata quando ricompare.
        self._scelta = self._chiavi[0] if self._chiavi else None
        self._al_cambio = al_cambio
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e Windows da' a un
        # controllo il nome del testo creato subito prima: il filtro, poi le
        # istruzioni, che sono il nome della lista, poi la lista. Il sizer
        # mette comunque le istruzioni in cima.
        etichetta_del_filtro = wx.StaticText(pannello, label=_("Filtro delle voci:"))
        self.filtro = wx.TextCtrl(pannello)
        self.filtro.SetName(_("Filtro delle voci"))
        # Traduttori: {titolo} e' il titolo dell'elenco, come Impostazioni.
        etichetta = wx.StaticText(pannello, label=_("{titolo}. Invio cambia la voce, Esc chiude, Maiuscolo con Tab va al filtro.").format(titolo=titolo))
        self.lista = wx.ListBox(pannello, choices=[testo for _chiave, testo in voci], style=wx.LB_SINGLE)
        self.lista.SetName(titolo)
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        sizer.Add(etichetta, 0, wx.ALL, 5)
        riga_del_filtro = wx.BoxSizer(wx.HORIZONTAL)
        riga_del_filtro.Add(etichetta_del_filtro, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        riga_del_filtro.Add(self.filtro, 1)
        sizer.Add(riga_del_filtro, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(self.lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(chiudi, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        adatta_finestra(self, pannello, (560, 420))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.lista.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: self.cambia())
        self.lista.Bind(wx.EVT_LISTBOX, lambda _evento: self._ricorda_la_scelta())
        self.filtro.Bind(wx.EVT_TEXT, lambda _evento: self.filtra())
        if voci:
            self.lista.SetSelection(0)
        self.lista.SetFocus()

    def _tasto(self, evento):
        if evento.GetEventObject() is self.lista and _premuto_invio(evento):
            self.cambia()
            return
        if evento.GetEventObject() is self.filtro and _premuto_invio(evento):
            self.lista.SetFocus()
            return
        evento.Skip()

    def _ricorda_la_scelta(self):
        """La selezione l'ha mossa chi usa la lista: la voce si ricorda."""
        indice = self.lista.GetSelection()
        if 0 <= indice < len(self._visibili):
            self._scelta = self._visibili[indice]

    def filtra(self):
        """Il testo del filtro e' cambiato: la lista mostra le voci il cui
        nome lo contiene, con selezionata la voce scelta, se c'e', altrimenti
        la prima, che pero' non diventa la scelta. Senza voci, una riga lo
        dice: una lista vuota, per NVDA, non dice niente."""
        scritto = " ".join(self.filtro.GetValue().split())
        cercato = normale(scritto)
        self._visibili = [chiave for chiave in self._chiavi if cercato in normale(self._testi[chiave].split(": ", 1)[0])]
        if self._visibili:
            self.lista.Set([self._testi[chiave] for chiave in self._visibili])
            self.lista.SetSelection(self._visibili.index(self._scelta) if self._scelta in self._visibili else 0)
        else:
            self.lista.Set([_("Nessuna voce contiene {testo}.").format(testo=scritto)])
            self.lista.SetSelection(0)

    def cambia(self):
        indice = self.lista.GetSelection()
        if 0 <= indice < len(self._visibili):
            self._scelta = self._visibili[indice]
            self._al_cambio(self._scelta, self)

    def aggiorna(self, chiave, testo):
        """Riscrive la riga della voce senza spostare la selezione; una voce
        nascosta dal filtro ha il testo nuovo quando ricompare."""
        if chiave not in self._testi:
            return
        self._testi[chiave] = testo
        if chiave not in self._visibili:
            return
        indice = self._visibili.index(chiave)
        if self.lista.GetString(indice) == testo:
            return
        selezionata = self.lista.GetSelection()
        self.lista.SetString(indice, testo)
        if selezionata != wx.NOT_FOUND and self.lista.GetSelection() != selezionata:
            self.lista.SetSelection(selezionata)


class FinestraScelta(wx.Dialog):
    """Una scelta da una lista: voci sono le righe, scelta l'indice di
    partenza. Invio, il doppio clic o Conferma confermano, Esc o Annulla
    annullano; GetSelection dice l'indice della riga scelta."""

    def __init__(self, genitore, titolo, voci, scelta=0):
        super().__init__(genitore, title=titolo, style=STILE_ADATTABILE)
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # Traduttori: {titolo} e' il nome della voce che si sceglie, come Uscita degli annunci.
        etichetta = wx.StaticText(pannello, label=_("{titolo}. Invio conferma, Esc annulla.").format(titolo=titolo))
        self.lista = wx.ListBox(pannello, choices=list(voci), style=wx.LB_SINGLE)
        self.lista.SetName(titolo)
        pulsanti = wx.StdDialogButtonSizer()
        conferma = wx.Button(pannello, wx.ID_OK, _("Conferma"))
        conferma.SetDefault()
        pulsanti.AddButton(conferma)
        pulsanti.AddButton(wx.Button(pannello, wx.ID_CANCEL, _("Annulla")))
        pulsanti.Realize()
        sizer.Add(etichetta, 0, wx.ALL, 5)
        sizer.Add(self.lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(pulsanti, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        adatta_finestra(self, pannello, (560, 360))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.lista.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: self.EndModal(wx.ID_OK))
        if voci:
            self.lista.SetSelection(max(0, min(scelta, len(voci) - 1)))
        self.lista.SetFocus()

    def _tasto(self, evento):
        if evento.GetEventObject() is self.lista and _premuto_invio(evento):
            if self.lista.GetSelection() != wx.NOT_FOUND:
                self.EndModal(wx.ID_OK)
            return
        evento.Skip()

    def GetSelection(self):
        return self.lista.GetSelection()


def scegli(genitore, titolo, voci, scelta=0):
    """Apre una FinestraScelta e restituisce l'indice scelto, o None se si
    annulla."""
    with FinestraScelta(genitore, titolo, voci, scelta) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        indice = dialogo.GetSelection()
    return None if indice == wx.NOT_FOUND else indice


class FinestraValore(wx.Dialog):
    """Un valore da scrivere: un numero intero o decimale fra minimo e
    massimo, in un campo che non ne accetta altri, o un testo lungo al piu'
    massimo caratteri. L'etichetta del campo e' la domanda del terminale.
    Conferma, o Invio nel campo, conferma; Esc o Annulla annullano. valore
    dice il valore confermato."""

    def __init__(self, genitore, titolo, domanda, valore, tipo="testo", minimo=0, massimo=256):
        super().__init__(genitore, title=titolo, style=STILE_ADATTABILE)
        self._tipo = tipo
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        etichetta = wx.StaticText(pannello, label=" ".join(domanda.split()))
        if tipo == "intero":
            self.campo = wx.SpinCtrl(pannello, min=int(minimo), max=int(massimo), initial=int(valore), style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
        elif tipo == "decimale":
            self.campo = wx.SpinCtrlDouble(pannello, min=minimo, max=massimo, initial=float(valore), inc=0.1, style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
            self.campo.SetDigits(1)
        else:
            self.campo = wx.TextCtrl(pannello, value=str(valore), style=wx.TE_PROCESS_ENTER)
            self.campo.SetMaxLength(int(massimo))
        self.campo.SetName(" ".join(domanda.split()))
        pulsanti = wx.StdDialogButtonSizer()
        conferma = wx.Button(pannello, wx.ID_OK, _("Conferma"))
        conferma.SetDefault()
        pulsanti.AddButton(conferma)
        pulsanti.AddButton(wx.Button(pannello, wx.ID_CANCEL, _("Annulla")))
        pulsanti.Realize()
        sizer.Add(etichetta, 0, wx.ALL, 5)
        sizer.Add(self.campo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(pulsanti, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        adatta_finestra(self, pannello, (480, 200))
        self.Maximize()
        self.campo.Bind(wx.EVT_TEXT_ENTER, lambda _evento: self.EndModal(wx.ID_OK))
        self.campo.SetFocus()
        if tipo == "testo":
            self.campo.SelectAll()

    @property
    def valore(self):
        if self._tipo == "intero":
            return int(self.campo.GetValue())
        if self._tipo == "decimale":
            return round(float(self.campo.GetValue()), 1)
        return self.campo.GetValue().strip()


def chiedi_valore(genitore, titolo, domanda, valore, tipo="testo", minimo=0, massimo=256):
    """Apre una FinestraValore e restituisce il valore confermato, o None se
    si annulla."""
    with FinestraValore(genitore, titolo, domanda, valore, tipo, minimo, massimo) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.valore


class FinestraPrompt(wx.Dialog):
    """Il modello del prompt di gioco, al posto del Blocco note: il campo col
    modello, i codici e le loro regole in sola lettura, e un riquadro che
    dice l'anteprima, o che cosa non va. aiuto e' la lista delle righe dei
    codici, anteprima(testo) le righe dell'anteprima, errori(testo) le frasi
    degli errori, vuote se il modello va bene. Conferma accetta solo un
    modello senza errori; Esc o Annulla annullano."""

    def __init__(self, genitore, modello, aiuto, anteprima, errori, suono_d_errore=None):
        super().__init__(genitore, title=_("Prompt di gioco"), style=STILE_ADATTABILE)
        self._anteprima = anteprima
        self._errori = errori
        self._suono_d_errore = suono_d_errore or wx.Bell
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab: il campo, l'esito, i
        # codici, i pulsanti; ogni controllo prende il nome del testo prima.
        etichetta = wx.StaticText(pannello, label=_("Modello del prompt"))
        self.campo = wx.TextCtrl(pannello, value=modello, style=wx.TE_PROCESS_ENTER)
        self.campo.SetName(_("Modello del prompt"))
        self.esito = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.esito.SetName(_("Anteprima: {p}").format(p="").strip(" :"))
        spiegazione = _("Ogni codice e' il percento seguito da una lettera, maiuscola o minuscola; il resto e' testo libero.")
        etichetta_dei_codici = wx.StaticText(pannello, label=spiegazione)
        self.codici = wx.TextCtrl(pannello, value="\n".join(aiuto), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.codici.SetName(spiegazione)
        pulsanti = wx.StdDialogButtonSizer()
        conferma = wx.Button(pannello, wx.ID_OK, _("Conferma"))
        conferma.SetDefault()
        pulsanti.AddButton(conferma)
        pulsanti.AddButton(wx.Button(pannello, wx.ID_CANCEL, _("Annulla")))
        pulsanti.Realize()
        sizer.Add(etichetta, 0, wx.ALL, 5)
        sizer.Add(self.campo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(self.esito, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(etichetta_dei_codici, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.Add(self.codici, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(pulsanti, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        adatta_finestra(self, pannello, (640, 480))
        self.Maximize()
        self.campo.Bind(wx.EVT_TEXT, lambda _evento: self.aggiorna())
        self.campo.Bind(wx.EVT_TEXT_ENTER, lambda _evento: self.conferma())
        conferma.Bind(wx.EVT_BUTTON, lambda _evento: self.conferma())
        self.aggiorna()
        self.campo.SetFocus()
        self.campo.SetInsertionPointEnd()

    @property
    def modello(self):
        return self.campo.GetValue().strip()

    def aggiorna(self):
        """L'esito del modello scritto: gli errori, o l'anteprima."""
        errori = self._errori(self.modello) if self.modello else []
        righe = errori or (self._anteprima(self.modello) if self.modello else [])
        self.esito.ChangeValue("\n".join(righe))
        return errori

    def conferma(self):
        """Un modello con errori non si conferma: l'esito dice perche'."""
        if self.aggiorna():
            self._suono_d_errore()
            self.esito.SetFocus()
            return
        self.EndModal(wx.ID_OK)


class Caffe(wx.Dialog):
    """L'invito a offrire un caffè, solo a richiesta, dalle impostazioni (S2):
    il testo in sola lettura, che ha il fuoco, e i pulsanti Dona con PayPal e
    Chiudi, il predefinito. Invio nel testo ed Esc chiudono; donare deve
    essere una scelta, non un tasto premuto per abitudine. suona riceve il
    nome dell'evento sonoro."""

    def __init__(self, genitore, testo, suona=None):
        super().__init__(genitore, title=_("Offrimi un caffè"), style=STILE_ADATTABILE)
        self._suona = suona or (lambda _evento: None)
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.testo = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, value=testo)
        self.testo.SetName(_("Offrimi un caffè"))
        dona = wx.Button(pannello, wx.ID_ANY, _("Dona con &PayPal"))
        chiudi = wx.Button(pannello, wx.ID_OK, _("&Chiudi"))
        chiudi.SetDefault()
        riga = wx.BoxSizer(wx.HORIZONTAL)
        riga.Add(dona, 0, wx.RIGHT, 5)
        riga.Add(chiudi, 0)
        sizer.Add(self.testo, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(riga, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        adatta_finestra(self, pannello, (560, 360))
        self.Maximize()
        self.SetEscapeId(wx.ID_OK)
        dona.Bind(wx.EVT_BUTTON, lambda _evento: self.dona())
        chiudi.Bind(wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_OK))
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        # L'apertura conta come un Invio: quello della voce che l'ha aperta
        # non la chiude appena aperta.
        self.ultimo_invio = time.monotonic()
        self.testo.SetInsertionPoint(0)
        self.testo.SetFocus()

    def _tasto(self, evento):
        if evento.GetEventObject() is self.testo and evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            adesso = time.monotonic()
            precedente, self.ultimo_invio = self.ultimo_invio, adesso
            if not evento.IsAutoRepeat() and adesso - precedente >= GRAZIA_INVIO:
                self.EndModal(wx.ID_OK)
            return
        evento.Skip()

    def dona(self):
        self._suona("caffe_paypal")
        with contextlib.suppress(webbrowser.Error):
            webbrowser.open(INDIRIZZO_PAYPAL)
        self.EndModal(wx.ID_OK)
