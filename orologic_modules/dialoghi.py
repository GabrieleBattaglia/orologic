# Orologic: le finestre di dialogo della GUI.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le finestre di dialogo della GUI, dalla tappa T3 (Piano della GUI.txt).

  FinestraImpostazioni  la lista piatta delle impostazioni, una riga per
                        voce, Etichetta: valore, col filtro, come in MeTeOra.
  FinestraScelta        una scelta da una lista.

Si aprono massimizzate, e Esc chiude come Chiudi o Annulla: le finestre
massimizzate si leggono meglio con lo screen reader e il display braille.
Ogni lista ha il suo nome, che NVDA legge, e le istruzioni nella riga sopra.
"""

import unicodedata

import wx
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from .config import _


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

    def __init__(self, genitore, voci, al_cambio):
        super().__init__(genitore, title=_("Impostazioni"), style=STILE_ADATTABILE)
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
        etichetta = wx.StaticText(pannello, label=_("Impostazioni. Invio cambia la voce, Esc chiude, Maiuscolo con Tab va al filtro."))
        self.lista = wx.ListBox(pannello, choices=[testo for _chiave, testo in voci], style=wx.LB_SINGLE)
        self.lista.SetName(_("Impostazioni"))
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
