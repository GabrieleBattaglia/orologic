# Orologic: le finestre di dialogo della GUI.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le finestre di dialogo della GUI, dalla tappa T3 (Piano della GUI.txt).

  FinestraImpostazioni  la lista piatta delle impostazioni, una riga per
                        voce, Etichetta: valore, come in MeTeOra.
  FinestraScelta        una scelta da una lista.

Si aprono massimizzate, e Esc chiude come Chiudi o Annulla: le finestre
massimizzate si leggono meglio con lo screen reader e il display braille.
Ogni lista ha il suo nome, che NVDA legge, e le istruzioni nella riga sopra.
"""

import wx
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from .config import _


def _premuto_invio(evento):
    return evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not evento.HasAnyModifiers()


class FinestraImpostazioni(wx.Dialog):
    """voci e' una lista di (chiave, testo della riga). Invio sulla lista, o
    il doppio clic, chiama al_cambio(chiave, dialogo): chi apre la finestra
    chiede il valore nuovo, lo applica e riscrive la riga con aggiorna."""

    def __init__(self, genitore, voci, al_cambio):
        super().__init__(genitore, title=_("Impostazioni"), style=STILE_ADATTABILE)
        self._chiavi = [chiave for chiave, _testo in voci]
        self._al_cambio = al_cambio
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # Windows da' a un controllo il nome del testo creato subito prima:
        # le istruzioni, poi la lista.
        etichetta = wx.StaticText(pannello, label=_("Impostazioni. Invio cambia la voce, Esc chiude."))
        self.lista = wx.ListBox(pannello, choices=[testo for _chiave, testo in voci], style=wx.LB_SINGLE)
        self.lista.SetName(_("Impostazioni"))
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        sizer.Add(etichetta, 0, wx.ALL, 5)
        sizer.Add(self.lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(chiudi, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        adatta_finestra(self, pannello, (560, 420))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.lista.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: self.cambia())
        if voci:
            self.lista.SetSelection(0)
        self.lista.SetFocus()

    def _tasto(self, evento):
        if evento.GetEventObject() is self.lista and _premuto_invio(evento):
            self.cambia()
            return
        evento.Skip()

    def cambia(self):
        indice = self.lista.GetSelection()
        if 0 <= indice < len(self._chiavi):
            self._al_cambio(self._chiavi[indice], self)

    def aggiorna(self, chiave, testo):
        """Riscrive la riga della voce, senza spostare la selezione."""
        if chiave not in self._chiavi:
            return
        indice = self._chiavi.index(chiave)
        if self.lista.GetString(indice) == testo:
            return
        selezionata = self.lista.GetSelection()
        self.lista.SetString(indice, testo)
        if selezionata != wx.NOT_FOUND:
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
