# Orologic: le finestre di dialogo della GUI.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le finestre di dialogo della GUI, dalla tappa T3 (Piano della GUI.txt).

  FinestraImpostazioni  la lista piatta delle impostazioni, una riga per
                        voce, Etichetta: valore, col filtro, come in MeTeOra.
  FinestraScelta        una scelta da una lista.
  FinestraValore        un numero o un testo, in un campo che ha per
                        etichetta la domanda del terminale.
  FinestraPrompt        la composizione del prompt di gioco: i simboli
                        disponibili, il prompt, la spiegazione,
                        l'aggiornamento e l'esempio.
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

from . import aspetto, modello_prompt
from .config import _

INDIRIZZO_PAYPAL = "https://paypal.me/GabrieleBattaglia780"
# Un Invio entro tanti secondi dall'apertura, o dall'Invio di prima, e' un
# tasto tenuto giu', o rimandato da NVDA: non chiude. La misura di Ciechino.
GRAZIA_INVIO = 0.65


def premuto_invio(evento):
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
        if evento.GetEventObject() is self.lista and premuto_invio(evento):
            self.cambia()
            return
        if evento.GetEventObject() is self.filtro and premuto_invio(evento):
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
        if evento.GetEventObject() is self.lista and premuto_invio(evento):
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


# Il suono di Rendi verbosa: qualcosa che si apre, una banda che si
# allarga; firmato da Orologic in GBUtils V314.
SUONO_DELLA_FORMA_VERBOSA = "banda_che_si_allarga"


class FinestraDaLeggere(wx.Dialog):
    """Righe da leggere, in un testo navigabile col titolo per nome, e
    Chiudi; Esc chiude. Servono alle analisi e agli aiuti di Easyfish, che
    nel cruscotto non ci stanno. Con verbosa, la forma verbosa del testo,
    prima di Chiudi c'e' Rendi verbosa, che la mette al posto del testo col
    suo suono: per le analisi, le linee con le mosse a parole e senza
    l'intestazione del motore (Gabriele, collaudo del 23 novembre 2026).
    inizio e' la riga dove si apre il cursore, come la prima linea
    dell'analisi; senza, la prima."""

    def __init__(self, genitore, titolo, righe, verbosa=None, inizio=None, suona=None):
        super().__init__(genitore, title=titolo, style=STILE_ADATTABILE)
        self.verbosa = list(verbosa) if verbosa else None
        self._suona = suona or _suona_un_preset
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.testo = wx.TextCtrl(pannello, value="\n".join(righe), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.testo.SetName(titolo)
        sizer.Add(self.testo, 1, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_verboso = None
        if self.verbosa:
            self.pulsante_verboso = wx.Button(pannello, label=_("Rendi verbosa"))
            self.pulsante_verboso.Bind(wx.EVT_BUTTON, lambda _evento: self.rendi_verbosa())
            riga.Add(self.pulsante_verboso, 0, wx.RIGHT, 5)
        riga.Add(wx.Button(pannello, wx.ID_CANCEL, _("Chiudi")), 0)
        sizer.Add(riga, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        self.testo.SetMinSize(wx.Size(-1, self.testo.GetCharHeight() * 10))
        adatta_finestra(self, pannello, (560, 420))
        self.Maximize()
        self.testo.SetInsertionPoint(self._posizione_della_riga(righe, inizio))
        self.testo.SetFocus()

    @staticmethod
    def _posizione_della_riga(righe, inizio):
        """Dove comincia la riga inizio nel testo, o 0. Si conta sul testo,
        non con XYToPosition, che col testo che va a capo conta le righe a
        schermo; nel controllo ricco ogni a capo vale un carattere."""
        if inizio is None or inizio not in righe:
            return 0
        return sum(len(riga) + 1 for riga in righe[: righe.index(inizio)])

    def rendi_verbosa(self):
        """La forma verbosa al posto del testo, col cursore in cima; il
        pulsante non serve piu' e si toglie."""
        if not self.verbosa:
            return
        self._suona(SUONO_DELLA_FORMA_VERBOSA)
        self.testo.SetValue("\n".join(self.verbosa))
        self.testo.SetInsertionPoint(0)
        self.testo.SetFocus()
        self.verbosa = None
        if self.pulsante_verboso is not None:
            self.pulsante_verboso.Hide()
            self.pulsante_verboso.GetContainingSizer().Layout()


def _suona_un_preset(nome):
    from GBUtils import Acusticator

    from . import config

    Acusticator.play(nome, volume=config.VOLUME)


def da_leggere(genitore, titolo, righe, verbosa=None, inizio=None):
    """Apre una FinestraDaLeggere e aspetta che si chiuda; le prove la
    sostituiscono."""
    with FinestraDaLeggere(genitore, titolo, righe, verbosa, inizio) as dialogo:
        dialogo.ShowModal()


# Il segnaposto del testo libero fra i simboli disponibili: non si esaurisce.
TESTO_LIBERO = None
# I millisecondi fra la voce scelta e l'annuncio della sua spiegazione: lo
# screen reader legge prima la voce, e l'annuncio le si mette in coda invece
# di passarle davanti (Gabriele, collaudo della finestra del prompt).
RITARDO_DELL_ANNUNCIO = 300


def _seleziona(lista, indice):
    if lista.GetCount():
        lista.SetSelection(max(0, min(indice, lista.GetCount() - 1)))


class FinestraPrompt(wx.Dialog):
    """La composizione del prompt di gioco, come l'ha chiesta Gabriele nel
    collaudo della T6, con due elenchi come i criteri di spareggio di
    Tornello. Disponibili ha i simboli che il prompt non usa, ognuno con la
    sua descrizione, e in fondo Testo libero; Prompt ha gli elementi del
    modello, nell'ordine. Sotto, la spiegazione del simbolo scelto, che si
    annuncia se gli annunci sono attivi, l'aggiornamento in secondi, e
    l'anteprima del prompt coi dati di prova.
    Nei disponibili Invio mette il simbolo in fondo al prompt, e il fuoco
    resta sul vicino; su Testo libero chiede il testo. Un simbolo con la
    forma estesa puo' starci breve e verboso: messa una forma, l'altra resta
    fra i disponibili. Nel prompt Canc
    rimette il simbolo fra i disponibili, e il fuoco va al vicino, o ai
    disponibili se il prompt e' vuoto; Ctrl con le frecce su e giu' sposta
    l'elemento prima o dopo; Invio su un testo libero lo fa riscrivere. Lo
    Spazio, nei due elenchi, accende e spegne la forma estesa, (verboso),
    dove il simbolo ce l'ha. OK salva e chiude, Annulla o Esc chiudono.
    chiedi_testo(genitore, valore) chiede un testo libero, o None;
    annuncia(righe) le annuncia se gli annunci sono attivi."""

    def __init__(self, genitore, modello, chiedi_testo, annuncia=None, suono_d_errore=None):
        super().__init__(genitore, title=_("Prompt di gioco"), style=STILE_ADATTABILE)
        self.elementi, secondi = modello_prompt.elementi(modello)
        # Il modello di partenza: se nulla cambia, OK lo lascia com'era.
        self._originale = (modello, copy.deepcopy(self.elementi), secondi)
        self._descrizioni = dict(modello_prompt.simboli())
        # La forma estesa dei simboli disponibili, che torna con loro nel prompt.
        self._verbosi = {}
        self._chiedi_testo = chiedi_testo
        self._annuncia = annuncia or (lambda _righe: None)
        # L'annuncio in attesa del suo ritardo: uno nuovo prende il suo posto.
        self._annuncio = None
        self._suono_d_errore = suono_d_errore or wx.Bell
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        etichetta_dei_disponibili = wx.StaticText(pannello, label=_("Disponibili"))
        self.disponibili = wx.ListBox(pannello, style=wx.LB_SINGLE)
        self.disponibili.SetName(_("Disponibili"))
        etichetta_della_spiegazione = wx.StaticText(pannello, label=_("Spiegazione"))
        self.spiegazione = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.spiegazione.SetName(_("Spiegazione"))
        etichetta_del_prompt = wx.StaticText(pannello, label=_("Prompt"))
        self.prompt = wx.ListBox(pannello, style=wx.LB_SINGLE)
        self.prompt.SetName(_("Prompt"))
        domanda_dei_secondi = _("Aggiornamento in secondi, da 0, statico, a 120:")
        etichetta_dei_secondi = wx.StaticText(pannello, label=domanda_dei_secondi)
        self.secondi = wx.SpinCtrl(pannello, min=0, max=modello_prompt.INTERVALLO_MASSIMO, initial=secondi)
        self.secondi.SetName(domanda_dei_secondi.rstrip(":").rstrip())
        # La parola Anteprima sta nell'etichetta, che NVDA legge col fuoco:
        # la casella riporta il prompt e basta (secondo giro del collaudo).
        etichetta_dell_esempio = wx.StaticText(pannello, label=_("Anteprima"))
        self.esempio = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP)
        self.esempio.SetName(_("Anteprima"))
        pulsanti = wx.StdDialogButtonSizer()
        ok = wx.Button(pannello, wx.ID_OK, _("OK"))
        ok.SetDefault()
        pulsanti.AddButton(ok)
        pulsanti.AddButton(wx.Button(pannello, wx.ID_CANCEL, _("Annulla")))
        pulsanti.Realize()
        elenchi = wx.BoxSizer(wx.HORIZONTAL)
        for etichetta, lista in ((etichetta_dei_disponibili, self.disponibili), (etichetta_del_prompt, self.prompt)):
            colonna = wx.BoxSizer(wx.VERTICAL)
            colonna.Add(etichetta, 0, wx.BOTTOM, 5)
            colonna.Add(lista, 1, wx.EXPAND)
            elenchi.Add(colonna, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(elenchi, 2, wx.EXPAND)
        sizer.Add(etichetta_della_spiegazione, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.Add(self.spiegazione, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        riga_dei_secondi = wx.BoxSizer(wx.HORIZONTAL)
        riga_dei_secondi.Add(etichetta_dei_secondi, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        riga_dei_secondi.Add(self.secondi, 0)
        sizer.Add(riga_dei_secondi, 0, wx.ALL, 5)
        sizer.Add(etichetta_dell_esempio, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.Add(self.esempio, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(pulsanti, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        # La spiegazione e' piccola, ma tiene qualche riga del suo carattere;
        # gli elenchi si misurano vuoti, come in Tornello, perche' la voce
        # piu' lunga non allarghi la finestra.
        self.spiegazione.SetMinSize(wx.Size(-1, self.spiegazione.GetCharHeight() * 4))
        for lista in (self.disponibili, self.prompt):
            lista.SetMinSize(lista.GetEffectiveMinSize())
        adatta_finestra(self, pannello, (640, 480))
        self.Maximize()
        self._riempi(0, 0)
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        for lista in (self.disponibili, self.prompt):
            lista.Bind(wx.EVT_LISTBOX, lambda evento: self._spiega(evento.GetEventObject(), annuncia=True))
            lista.Bind(wx.EVT_SET_FOCUS, self._fuoco_a_un_elenco)
        self.disponibili.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: self.aggiungi())
        self.secondi.Bind(wx.EVT_SPINCTRL, lambda _evento: self.aggiorna())
        self.secondi.Bind(wx.EVT_TEXT, lambda _evento: self.aggiorna())
        ok.Bind(wx.EVT_BUTTON, lambda _evento: self.conferma())
        self._spiega(self.disponibili)
        self.aggiorna()
        # L'apertura conta come un Invio: quello della voce che l'ha aperta
        # non mette un simbolo nel prompt.
        self.ultimo_invio = time.monotonic()
        self.disponibili.SetFocus()

    # Le voci.

    def _forme_usate(self, codice, escluso=None):
        """Le forme del simbolo gia' nel prompt, verboso vero o falso,
        senza contare l'elemento escluso."""
        return {elemento["verboso"] for elemento in self.elementi if elemento is not escluso and elemento.get("codice") == codice}

    def _forme_libere(self, codice):
        """Le forme del simbolo che il prompt non usa: un simbolo con la
        forma estesa puo' starci breve e verboso (Gabriele, secondo giro del
        collaudo della finestra); gli altri una volta sola."""
        forme = {False, True} if codice in modello_prompt.ESTESE else {False}
        return forme - self._forme_usate(codice)

    def _verboso_disponibile(self, codice):
        """La forma del simbolo fra i disponibili: quella rimasta, se l'altra
        e' gia' nel prompt, altrimenti quella dell'interruttore."""
        libere = self._forme_libere(codice)
        if len(libere) == 1:
            return next(iter(libere))
        return self._verbosi.get(codice, False)

    def voci_disponibili(self):
        """I simboli con almeno una forma che il prompt non usa, nell'ordine
        del catalogo, e Testo libero."""
        return [codice for codice, _descrizione in modello_prompt.simboli() if self._forme_libere(codice)] + [TESTO_LIBERO]

    def _etichetta(self, codice, verboso):
        testo = f"%{codice} {self._descrizioni[codice]}"
        return f"{testo} {_('(verboso)')}" if verboso else testo

    def etichetta_dell_elemento(self, elemento):
        if "testo" in elemento:
            return _("Testo libero: {testo}").format(testo=elemento["testo"])
        return self._etichetta(elemento["codice"], elemento["verboso"])

    def _etichetta_disponibile(self, voce):
        return _("Testo libero") if voce is TESTO_LIBERO else self._etichetta(voce, self._verboso_disponibile(voce))

    def _riempi(self, nei_disponibili=None, nel_prompt=None):
        """Riscrive i due elenchi, con selezionate le voci a quegli indici, o
        a quelli di prima."""
        if nei_disponibili is None:
            nei_disponibili = max(self.disponibili.GetSelection(), 0)
        if nel_prompt is None:
            nel_prompt = max(self.prompt.GetSelection(), 0)
        self.disponibili.Set([self._etichetta_disponibile(voce) for voce in self.voci_disponibili()])
        self.prompt.Set([self.etichetta_dell_elemento(elemento) for elemento in self.elementi])
        _seleziona(self.disponibili, nei_disponibili)
        _seleziona(self.prompt, nel_prompt)

    def _scelto(self, lista):
        """Il codice e il verboso della voce scelta nell'elenco; il codice e'
        None per un testo libero, e la voce None se non c'e' scelta."""
        indice = lista.GetSelection()
        if indice == wx.NOT_FOUND:
            return None
        if lista is self.disponibili:
            voce = self.voci_disponibili()[indice]
            return voce, voce is not TESTO_LIBERO and self._verboso_disponibile(voce)
        elemento = self.elementi[indice]
        return elemento.get("codice"), elemento.get("verboso", False)

    @staticmethod
    def _stato(codice, verboso):
        """In coda alla spiegazione dei simboli con la forma estesa: verboso
        se e' accesa, breve se e' spenta."""
        if codice not in modello_prompt.ESTESE:
            return []
        return [_("verboso") if verboso else _("breve")]

    @classmethod
    def _stato_da_annunciare(cls, codice, verboso):
        """Solo breve: verboso NVDA lo legge gia' nella voce, (verboso), e
        annunciato arrivava doppio (Gabriele, secondo giro del collaudo)."""
        return [] if verboso else cls._stato(codice, verboso)

    def _spiega(self, lista, annuncia=False):
        """La spiegazione della voce scelta nell'elenco: la voce, le regole
        dell'aiuto che la riguardano e, per i simboli con la forma estesa,
        verboso o breve. Si annunciano le regole e breve; la voce, con
        (verboso), la legge gia' lo screen reader."""
        scelto = self._scelto(lista)
        if scelto is None:
            return
        codice, verboso = scelto
        indice = lista.GetSelection()
        if lista is self.disponibili:
            riga = self._etichetta_disponibile(codice)
        else:
            riga = self.etichetta_dell_elemento(self.elementi[indice])
        regole = [] if codice is None else modello_prompt.regole_del_simbolo(codice)
        self.spiegazione.ChangeValue("\n".join([riga, *regole, *self._stato(codice, verboso)]))
        if annuncia:
            self._annuncia_dopo([*regole, *self._stato_da_annunciare(codice, verboso)])

    def _annuncia_dopo(self, righe):
        """L'annuncio parte dopo RITARDO_DELL_ANNUNCIO, in coda alla voce che
        lo screen reader legge; uno nuovo prende il posto di quello in
        attesa, cosi' scorrendo l'elenco si sente solo l'ultimo."""
        if self._annuncio is not None:
            self._annuncio.Stop()
            self._annuncio = None
        if righe:
            self._annuncio = wx.CallLater(RITARDO_DELL_ANNUNCIO, self._annuncia_ora, list(righe))

    def _annuncia_ora(self, righe):
        self._annuncio = None
        if self:
            self._annuncia(righe)

    def _fuoco_a_un_elenco(self, evento):
        evento.Skip()
        self._spiega(evento.GetEventObject(), annuncia=True)

    # Il modello e l'esempio.

    def _invariato(self):
        _originale, elementi, secondi = self._originale
        return self.elementi == elementi and self.secondi.GetValue() == secondi

    @property
    def modello(self):
        """Il modello composto; quello di partenza, scritto com'era, se nulla e' cambiato."""
        if self._invariato():
            return self._originale[0]
        return modello_prompt.modello_degli_elementi(self.elementi, self.secondi.GetValue())

    def aggiorna(self):
        """L'anteprima: il prompt coi dati di prova, fedele, senza altre
        parole; oppure che cosa non va."""
        modello = self.modello
        errori = modello_prompt.errori_del_modello(modello) if modello else []
        if errori:
            testo = "\n".join(errori)
        else:
            testo = modello_prompt.componi(modello_prompt.esempio(), modello) if modello else ""
        self.esempio.ChangeValue(testo)
        return errori

    def conferma(self):
        """Un modello cambiato con errori non si conferma: l'esempio dice
        perche'. Uno che non e' cambiato si lascia com'era."""
        if not self._invariato() and self.aggiorna():
            self._suono_d_errore()
            self.esempio.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    # I tasti.

    def _tasto(self, evento):
        codice = evento.GetKeyCode()
        oggetto = evento.GetEventObject()
        senza_modificatori = not evento.HasAnyModifiers()
        if oggetto is self.prompt and evento.GetModifiers() == wx.MOD_CONTROL and codice in (wx.WXK_UP, wx.WXK_DOWN):
            self.sposta(-1 if codice == wx.WXK_UP else 1)
            return
        if oggetto in (self.disponibili, self.prompt) and codice == wx.WXK_SPACE and senza_modificatori:
            self.cambia_il_verboso(oggetto)
            return
        if oggetto is self.prompt and codice in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and senza_modificatori:
            self.rimuovi()
            return
        if oggetto in (self.disponibili, self.prompt) and premuto_invio(evento):
            adesso = time.monotonic()
            precedente, self.ultimo_invio = self.ultimo_invio, adesso
            if evento.IsAutoRepeat() or adesso - precedente < GRAZIA_INVIO:
                return
            if oggetto is self.disponibili:
                self.aggiungi()
            else:
                self.riscrivi_il_testo()
            return
        evento.Skip()

    def aggiungi(self):
        """Invio nei disponibili: il simbolo in fondo al prompt, col suo
        verboso; il fuoco resta sulla voce vicina, o va al prompt se i
        disponibili sono finiti. Testo libero chiede il testo e resta."""
        indice = self.disponibili.GetSelection()
        if indice == wx.NOT_FOUND:
            return
        voce = self.voci_disponibili()[indice]
        if voce is TESTO_LIBERO:
            testo = self._chiedi_testo(self, "")
            if not testo or not testo.strip():
                return
            elemento = {"testo": testo.strip()}
        else:
            elemento = {"codice": voce, "verboso": self._verboso_disponibile(voce)}
            self._verbosi.pop(voce, None)
        self.elementi.append(elemento)
        self._riempi(indice, len(self.elementi) - 1)
        if not self.voci_disponibili():
            self.prompt.SetFocus()
        self._spiega(self.disponibili, annuncia=True)
        self.aggiorna()

    def rimuovi(self):
        """Canc nel prompt: il simbolo torna fra i disponibili, al suo posto,
        e il fuoco va all'elemento vicino; se il prompt e' vuoto, ai
        disponibili, sul simbolo appena tornato. Un testo libero se ne va."""
        indice = self.prompt.GetSelection()
        if indice == wx.NOT_FOUND:
            return
        voci = self.voci_disponibili()
        scelta = voci[max(self.disponibili.GetSelection(), 0)]
        elemento = self.elementi.pop(indice)
        if "codice" in elemento:
            self._verbosi[elemento["codice"]] = elemento["verboso"]
        voci = self.voci_disponibili()
        if self.elementi:
            self._riempi(voci.index(scelta), indice)
            self._spiega(self.prompt, annuncia=True)
        else:
            self._riempi(voci.index(elemento["codice"]) if "codice" in elemento else voci.index(scelta), 0)
            self.disponibili.SetFocus()
        self.aggiorna()

    def sposta(self, passo):
        """Ctrl con le frecce nel prompt: l'elemento prima o dopo; agli
        estremi, la nota bassa dell'errore."""
        indice = self.prompt.GetSelection()
        nuovo = indice + passo
        if indice == wx.NOT_FOUND or not 0 <= nuovo < len(self.elementi):
            self._suono_d_errore()
            return
        self.elementi[indice], self.elementi[nuovo] = self.elementi[nuovo], self.elementi[indice]
        self._riempi(None, nuovo)
        self._spiega(self.prompt)
        self.aggiorna()

    def cambia_il_verboso(self, lista):
        """Lo Spazio: la forma estesa accesa o spenta; su un simbolo che non
        ce l'ha, su uno che ha gia' l'altra forma nel prompt, o su un testo,
        la nota bassa dell'errore."""
        indice = lista.GetSelection()
        if indice == wx.NOT_FOUND:
            return
        if lista is self.disponibili:
            voce = self.voci_disponibili()[indice]
            # L'altra forma e' gia' nel prompt: questa non cambia.
            if voce not in modello_prompt.ESTESE or len(self._forme_libere(voce)) < 2:
                self._suono_d_errore()
                return
            self._verbosi[voce] = not self._verbosi.get(voce, False)
        else:
            elemento = self.elementi[indice]
            codice = elemento.get("codice")
            if codice not in modello_prompt.ESTESE or (not elemento["verboso"]) in self._forme_usate(codice, escluso=elemento):
                self._suono_d_errore()
                return
            elemento["verboso"] = not elemento["verboso"]
        self._riempi()
        self._spiega(lista)
        # Dopo la voce riletta, solo breve: verboso lo dice gia' la voce.
        self._annuncia_dopo(self._stato_da_annunciare(*self._scelto(lista)))
        self.aggiorna()

    def riscrivi_il_testo(self):
        """Invio su un testo libero del prompt: si riscrive; vuoto, resta
        com'era, e per toglierlo c'e' Canc."""
        indice = self.prompt.GetSelection()
        if indice == wx.NOT_FOUND or "testo" not in self.elementi[indice]:
            return
        testo = self._chiedi_testo(self, self.elementi[indice]["testo"])
        if not testo or not testo.strip():
            return
        self.elementi[indice]["testo"] = testo.strip()
        self._riempi()
        self._spiega(self.prompt)
        self.aggiorna()


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
        if not premuto_invio(evento):
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
