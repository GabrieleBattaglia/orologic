# Orologic: la finestra dell'albero delle aperture.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'albero delle aperture nella finestra (Gabriele, 25 novembre 2026): le
linee di eco.pgn in un albero nativo di Windows a selezione singola,
costruito un ramo alla volta quando si apre, come quello della ricerca PGN.
La logica sta in aperture.py.

Ogni voce e' una mossa: la mossa descritta, la mossa col suo numero, la
percentuale delle linee di eco.pgn che ci passano, sul totale, e il nome
dell'apertura. Invio su un ramo lo apre o lo chiude, su una foglia dice la
linea. Sotto l'albero il campo Linea, con le mosse fino alla voce e il nome,
poi Analisi manuale, Passa a Easyfish e Chiudi; Esc chiude. I due pulsanti
vogliono una linea di almeno due semimosse: con meno suonano il no e lo
dicono. La finestra si chiude con la linea come partita in uscita, e il
nucleo la passa all'analisi o a Easyfish; al ritorno si riapre allo stesso
punto.
"""

import wx
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aperture, aspetto, dialoghi, finestra_ricerca
from .config import _


def suona(evento):
    """I suoni della finestra, quelli della ricerca PGN; le prove li
    sostituiscono."""
    finestra_ricerca.suona(evento)


class FinestraAperture(wx.Dialog):
    """stato e' quello di aperture.py, con l'albero e la linea scelta;
    annuncia(righe) le dice in coda, se gli annunci sono attivi. uscita,
    alla chiusura, e' (azione, partita) per l'analisi manuale o Easyfish, o
    None."""

    def __init__(self, genitore, stato, annuncia):
        super().__init__(genitore, title=_("Albero aperture"), style=STILE_ADATTABILE)
        self.stato = stato
        self._annuncia = annuncia
        self.uscita = None
        self._popolati = set()
        if stato.albero is None:
            stato.albero = aperture.carica()
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende il
        # nome del testo creato subito prima.
        intestazione = _("Linee di eco.pgn: {n}").format(n=stato.albero.totale)
        sizer.Add(wx.StaticText(pannello, label=intestazione), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.albero = wx.TreeCtrl(pannello, style=wx.TR_HAS_BUTTONS | wx.TR_SINGLE | wx.TR_HIDE_ROOT)
        self.albero.SetName(intestazione)
        sizer.Add(self.albero, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticText(pannello, label=_("Linea")), 0, wx.LEFT | wx.RIGHT, 5)
        self.linea = wx.TextCtrl(pannello, style=wx.TE_READONLY)
        self.linea.SetName(_("Linea"))
        sizer.Add(self.linea, 0, wx.EXPAND | wx.ALL, 5)
        pulsanti = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_manuale = wx.Button(pannello, label=_("Analisi &manuale"))
        self.pulsante_easyfish = wx.Button(pannello, label=_("Passa a &Easyfish"))
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        for pulsante in (self.pulsante_manuale, self.pulsante_easyfish, chiudi):
            pulsanti.Add(pulsante, 0, wx.ALL, 5)
        sizer.Add(pulsanti, 0)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        self.albero.SetMinSize(wx.Size(-1, self.albero.GetCharHeight() * 12))
        adatta_finestra(self, pannello, (800, 600))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.Bind(wx.EVT_BUTTON, lambda _evento: finestra_ricerca.finisci(self, wx.ID_CANCEL), id=wx.ID_CANCEL)
        self.pulsante_manuale.Bind(wx.EVT_BUTTON, lambda _evento: self.vai("manuale"))
        self.pulsante_easyfish.Bind(wx.EVT_BUTTON, lambda _evento: self.vai("easyfish"))
        self.albero.Bind(wx.EVT_TREE_ITEM_EXPANDING, lambda evento: self._popola(evento.GetItem()))
        self.albero.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda evento: self.attiva(evento.GetItem()))
        self.albero.Bind(wx.EVT_TREE_SEL_CHANGED, lambda _evento: self._mostra_la_linea())
        radice = self.albero.AddRoot("", data=stato.albero.radice)
        self._popola(radice)
        self._vai_alla_linea(stato.mosse)
        self.albero.SetFocus()

    # L'albero.

    def _popola(self, voce):
        """I figli della voce, la prima volta che servono."""
        if not voce.IsOk():
            return
        nodo = self.albero.GetItemData(voce)
        if nodo is None or id(nodo) in self._popolati:
            return
        self._popolati.add(id(nodo))
        for figlio in nodo.figli_in_ordine():
            elemento = self.albero.AppendItem(voce, aperture.voce_del_nodo(figlio, self.stato.albero.totale), data=figlio)
            if figlio.figli:
                self.albero.SetItemHasChildren(elemento, True)

    def _figlio(self, voce, mossa):
        figlio, cookie = self.albero.GetFirstChild(voce)
        while figlio.IsOk():
            if self.albero.GetItemData(figlio).mossa == mossa:
                return figlio
            figlio, cookie = self.albero.GetNextChild(voce, cookie)
        return None

    def _vai_alla_linea(self, mosse):
        """La voce in fondo alle mosse, aprendo i rami sopra; senza mosse la
        prima voce."""
        voce = self.albero.GetRootItem()
        for mossa in mosse:
            self._popola(voce)
            figlio = self._figlio(voce, mossa)
            if figlio is None:
                break
            if voce != self.albero.GetRootItem():
                self.albero.Expand(voce)
            voce = figlio
        if voce == self.albero.GetRootItem():
            voce, _cookie = self.albero.GetFirstChild(voce)
        if voce.IsOk():
            self.albero.SelectItem(voce)
            self.albero.EnsureVisible(voce)
        self._mostra_la_linea()

    def selezionata(self):
        """La voce scelta e il suo nodo, o (None, None)."""
        voce = self.albero.GetSelection()
        if not voce.IsOk() or voce == self.albero.GetRootItem():
            return None, None
        return voce, self.albero.GetItemData(voce)

    def testo_della_linea(self, nodo):
        """La linea fino al nodo, col nome dell'apertura: 1. e4 c5 | B20 Sicilian defence."""
        voce = nodo.voce_piu_vicina()
        linea = aperture.linea(nodo)
        return f"{linea}, {aperture.nome_della_voce(voce)}" if voce else linea

    def _mostra_la_linea(self):
        # Mentre la finestra si chiude l'albero toglie le voci, e la scelta
        # cambia su un controllo che se ne sta andando.
        if not self or self.IsBeingDeleted() or not self.albero or self.albero.IsBeingDeleted():
            return
        _voce, nodo = self.selezionata()
        if nodo is None:
            self.linea.ChangeValue("")
            return
        self.stato.mosse = nodo.percorso()
        self.linea.ChangeValue(self.testo_della_linea(nodo))

    def attiva(self, voce=None):
        """Invio: un ramo si apre o si chiude, una foglia dice la linea."""
        if voce is None or not voce.IsOk():
            voce, nodo = self.selezionata()
        else:
            nodo = self.albero.GetItemData(voce)
        if nodo is None:
            return
        if not nodo.figli:
            self._annuncia([self.testo_della_linea(nodo)])
        elif self.albero.IsExpanded(voce):
            self.albero.Collapse(voce)
        else:
            self._popola(voce)
            self.albero.Expand(voce)

    # I pulsanti.

    def vai(self, azione):
        """Analisi manuale o Easyfish con la linea scelta: la finestra si
        chiude con la partita in uscita. Con meno di due semimosse no."""
        _voce, nodo = self.selezionata()
        if nodo is None or nodo.semimosse < aperture.SEMIMOSSE_MINIME:
            suona("no")
            self._annuncia([_("Serve una linea di almeno {n} semimosse.").format(n=aperture.SEMIMOSSE_MINIME)])
            return
        self.stato.mosse = nodo.percorso()
        self.uscita = (azione, aperture.partita(nodo))
        finestra_ricerca.finisci(self, wx.ID_OK)

    def _tasto(self, evento):
        if dialoghi.premuto_invio(evento) and evento.GetEventObject() is self.albero:
            self.attiva()
            return
        evento.Skip()
