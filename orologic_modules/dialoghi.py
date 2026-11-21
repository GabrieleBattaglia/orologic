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
  FinestraColori        colori e dimensioni dei caratteri della plancia e
                        dell'area centrale, con l'anteprima.

Ogni finestra prende colori e dimensioni dei caratteri di aspetto.py prima
di prendere la sua misura.

Si aprono massimizzate, e Esc chiude come Chiudi o Annulla: le finestre
massimizzate si leggono meglio con lo screen reader e il display braille.
Ogni lista ha il suo nome, che NVDA legge, e le istruzioni nella riga sopra.
"""

import contextlib
import copy
import sys
import time
import unicodedata
import webbrowser

import wx
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto
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
        aspetto.applica_alla_finestra(self)
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
        aspetto.applica_alla_finestra(self)
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
        aspetto.applica_alla_finestra(self)
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
        aspetto.applica_alla_finestra(self)
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
        aspetto.applica_alla_finestra(self)
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


# Il messaggio di Windows che dice se la tendina di una combo e' aperta.
CB_GETDROPPEDSTATE = 0x0157


def _tendina_aperta(scelta):
    """Vero se la tendina della combo e' aperta: li' Invio la chiude e
    sceglie, come sempre, e non e' un comando della finestra."""
    if sys.platform != "win32":
        return False
    import ctypes

    return bool(ctypes.windll.user32.SendMessageW(scelta.GetHandle(), CB_GETDROPPEDSTATE, 0, 0))


def bersagli_dei_colori():
    """Le voci di Applica a nella scheda dei colori: (testo, ruolo, parte)."""
    return [
        (_("Caratteri plancia"), "plancia", "testo"),
        (_("Caratteri area centrale"), "area", "testo"),
        (_("Sfondo plancia"), "plancia", "sfondo"),
        (_("Sfondo area"), "area", "sfondo"),
    ]


def bersagli_delle_dimensioni():
    """Le voci di Applica a nella scheda delle dimensioni: (testo, ruolo)."""
    return [(_("Plancia"), "plancia"), (_("Area centrale"), "area")]


class FinestraColori(wx.Dialog):
    """Colori e dimensioni dei caratteri, come li ha chiesti Gabriele il 21
    novembre 2026. Due schede. Colori: i cursori di rosso, verde e blu, da 0
    a 100; Applica a, coi caratteri e lo sfondo della plancia e dell'area
    centrale; i colori predefiniti, poi quelli personali, e in fondo Salva
    colore. Dimensioni: la dimensione in punti, da 8 a 72, e Applica a, la
    plancia o l'area centrale. Sotto le schede l'anteprima di cio' che dice
    Applica a nella scheda aperta.
    Tutto con Invio, come ha scelto Gabriele: nelle combo le frecce scorrono
    le voci senza effetti; Invio su un colore porta li' i cursori, Invio su
    Salva colore chiede il nome e salva il colore dei cursori, Invio su
    Applica a mette nella voce scelta il colore dei cursori, o la
    dimensione, e lo mette in uso subito in tutte le finestre. Cambiare voce
    in Applica a non tocca i cursori. OK chiude e chi ha aperto salva
    impostazioni; Annulla o Esc chiudono, e chi ha aperto rimette quelle di
    prima. I colori personali si salvano subito.
    chiedi_nome(genitore) chiede il nome del colore, o None; suona(evento)
    riceve applicato o caricato."""

    def __init__(self, genitore, impostazioni, chiedi_nome, suona=None):
        super().__init__(genitore, title=_("Colori e dimensioni"), style=STILE_ADATTABILE)
        self.impostazioni = copy.deepcopy(impostazioni)
        # Vero se Invio su Applica a ha cambiato le finestre.
        self.applicate = False
        self._chiedi_nome = chiedi_nome
        self._suona = suona or (lambda _evento: None)
        self._colori = aspetto.predefiniti() + aspetto.personali()
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        self.schede = wx.Notebook(pannello)
        pagina = wx.Panel(self.schede)
        colonna = wx.BoxSizer(wx.VERTICAL)
        _testo, ruolo, parte = bersagli_dei_colori()[0]
        self.cursori = []
        for etichetta, valore in zip((_("Rosso (%):"), _("Verde (%):"), _("Blu (%):")), aspetto.colore_in_uso(self.impostazioni, ruolo, parte), strict=True):
            colonna.Add(wx.StaticText(pagina, label=etichetta), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
            cursore = wx.Slider(pagina, value=valore, minValue=0, maxValue=100)
            cursore.SetName(etichetta.rstrip(":").rstrip())
            colonna.Add(cursore, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
            self.cursori.append(cursore)
        colonna.Add(wx.StaticText(pagina, label=_("Applica a:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.applica_colori = wx.Choice(pagina, choices=[testo for testo, _ruolo, _parte in bersagli_dei_colori()])
        self.applica_colori.SetName(_("Applica a:").rstrip(":").rstrip())
        self.applica_colori.SetSelection(0)
        colonna.Add(self.applica_colori, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        colonna.Add(wx.StaticText(pagina, label=_("Colori predefiniti:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.predefiniti = wx.Choice(pagina, choices=self._voci_dei_colori())
        self.predefiniti.SetName(_("Colori predefiniti:").rstrip(":").rstrip())
        self.predefiniti.SetSelection(0)
        colonna.Add(self.predefiniti, 0, wx.EXPAND | wx.ALL, 5)
        pagina.SetSizer(colonna)
        self.schede.AddPage(pagina, _("Colori"))
        pagina = wx.Panel(self.schede)
        colonna = wx.BoxSizer(wx.VERTICAL)
        colonna.Add(wx.StaticText(pagina, label=_("Dimensione (pt):")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.dimensione = wx.Choice(pagina, choices=[str(n) for n in range(aspetto.DIMENSIONE_MINIMA, aspetto.DIMENSIONE_MASSIMA + 1)])
        self.dimensione.SetName(_("Dimensione (pt):").rstrip(":").rstrip())
        _testo, ruolo = bersagli_delle_dimensioni()[0]
        in_uso = aspetto.dimensione_in_uso(self.impostazioni, ruolo)
        self.dimensione.SetSelection(max(aspetto.DIMENSIONE_MINIMA, min(in_uso, aspetto.DIMENSIONE_MASSIMA)) - aspetto.DIMENSIONE_MINIMA)
        colonna.Add(self.dimensione, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        colonna.Add(wx.StaticText(pagina, label=_("Applica a:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.applica_dimensione = wx.Choice(pagina, choices=[testo for testo, _ruolo in bersagli_delle_dimensioni()])
        self.applica_dimensione.SetName(_("Applica a:").rstrip(":").rstrip())
        self.applica_dimensione.SetSelection(0)
        colonna.Add(self.applica_dimensione, 0, wx.EXPAND | wx.ALL, 5)
        pagina.SetSizer(colonna)
        self.schede.AddPage(pagina, _("Dimensioni"))
        etichetta_dell_anteprima = wx.StaticText(pannello, label=_("Anteprima"))
        self.anteprima = wx.TextCtrl(pannello, value=_("Così appare il testo della finestra."), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.anteprima.SetName(_("Anteprima"))
        pulsanti = wx.StdDialogButtonSizer()
        ok = wx.Button(pannello, wx.ID_OK, _("OK"))
        ok.SetDefault()
        pulsanti.AddButton(ok)
        pulsanti.AddButton(wx.Button(pannello, wx.ID_CANCEL, _("Annulla")))
        pulsanti.Realize()
        sizer.Add(self.schede, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(etichetta_dell_anteprima, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.Add(self.anteprima, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(pulsanti, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self, self.impostazioni)
        self.aggiorna_l_anteprima()
        adatta_finestra(self, pannello, (560, 480))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        for cursore in self.cursori:
            cursore.Bind(wx.EVT_SLIDER, lambda _evento: self.aggiorna_l_anteprima())
        for scelta in (self.applica_colori, self.dimensione, self.applica_dimensione):
            scelta.Bind(wx.EVT_CHOICE, lambda _evento: self.aggiorna_l_anteprima())
        self.schede.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._scheda_cambiata)
        # L'apertura conta come un Invio: quello della voce che l'ha aperta
        # non la chiude appena aperta.
        self.ultimo_invio = time.monotonic()
        self.cursori[0].SetFocus()

    def _voci_dei_colori(self):
        return [nome for nome, _colore in self._colori] + [_("Salva colore")]

    def colore_dei_cursori(self):
        return [cursore.GetValue() for cursore in self.cursori]

    def dimensione_scelta(self):
        return aspetto.DIMENSIONE_MINIMA + self.dimensione.GetSelection()

    def _scheda_cambiata(self, evento):
        evento.Skip()
        self.aggiorna_l_anteprima(evento.GetSelection())

    def aggiorna_l_anteprima(self, scheda=None):
        """L'anteprima mostra la voce di Applica a della scheda aperta, coi
        cursori, o con la dimensione scelta, al posto del suo valore."""
        scheda = self.schede.GetSelection() if scheda is None else scheda
        prova = copy.deepcopy(self.impostazioni)
        if scheda == 1:
            _testo, ruolo = bersagli_delle_dimensioni()[self.applica_dimensione.GetSelection()]
            prova[ruolo]["dimensione"] = self.dimensione_scelta()
        else:
            _testo, ruolo, parte = bersagli_dei_colori()[self.applica_colori.GetSelection()]
            prova[ruolo][parte] = self.colore_dei_cursori()
        aspetto.applica_al_controllo(self.anteprima, prova, ruolo)
        # Piccola, ma alta abbastanza per qualche riga del suo carattere.
        self.anteprima.SetMinSize(wx.Size(-1, self.anteprima.GetCharHeight() * 4))
        self.anteprima.GetParent().Layout()

    def _tasto(self, evento):
        if not _premuto_invio(evento):
            evento.Skip()
            return
        oggetto = evento.GetEventObject()
        if isinstance(oggetto, wx.Choice) and _tendina_aperta(oggetto):
            evento.Skip()
            return
        adesso = time.monotonic()
        precedente, self.ultimo_invio = self.ultimo_invio, adesso
        if evento.IsAutoRepeat() or adesso - precedente < GRAZIA_INVIO:
            return
        if oggetto is self.applica_colori:
            self.applica_il_colore()
        elif oggetto is self.predefiniti:
            self.scegli_il_colore()
        elif oggetto is self.applica_dimensione:
            self.applica_la_dimensione()
        elif oggetto is not self.dimensione:
            # Altrove Invio vale OK, il pulsante predefinito; sulla
            # dimensione non fa niente, perche' la si applica con Applica a.
            evento.Skip()

    def applica_il_colore(self):
        _testo, ruolo, parte = bersagli_dei_colori()[self.applica_colori.GetSelection()]
        self.impostazioni[ruolo][parte] = self.colore_dei_cursori()
        self._metti_in_uso()

    def applica_la_dimensione(self):
        _testo, ruolo = bersagli_delle_dimensioni()[self.applica_dimensione.GetSelection()]
        self.impostazioni[ruolo]["dimensione"] = self.dimensione_scelta()
        self._metti_in_uso()

    def _metti_in_uso(self):
        self.applicate = True
        aspetto.applica_a_tutte(self.impostazioni)
        self.aggiorna_l_anteprima()
        self._suona("applicato")

    def scegli_il_colore(self):
        """Invio sui colori: un colore va nei cursori; Salva colore chiede il
        nome e salva quello dei cursori, che poi resta selezionato."""
        indice = self.predefiniti.GetSelection()
        if indice == len(self._colori):
            nome = self._chiedi_nome(self)
            if not nome or not nome.strip():
                return
            nome = aspetto.salva_personale(nome, self.colore_dei_cursori())[-1][0]
            self._colori = aspetto.predefiniti() + aspetto.personali()
            self.predefiniti.Set(self._voci_dei_colori())
            nomi = [n for n, _colore in self._colori]
            # Il personale col nome salvato: l'ultimo con quel nome.
            self.predefiniti.SetSelection(len(nomi) - 1 - nomi[::-1].index(nome))
            return
        for cursore, valore in zip(self.cursori, self._colori[indice][1], strict=True):
            cursore.SetValue(valore)
        self.aggiorna_l_anteprima()
        self._suona("caricato")
