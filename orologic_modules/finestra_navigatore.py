# Orologic: il navigatore della partita di Easyfish nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il navigatore della partita PGN di Easyfish, il comando .na, come l'ha
voluto Gabriele il 22 novembre 2026: le mosse in un albero nativo di
Windows, la linea principale in fila sotto la partita, e ogni variante come
ramo sotto la mossa che sostituisce, con le sue mosse in fila e le sue
varianti allo stesso modo. Ogni voce dice il numero, la mossa, la mossa a
parole, i segni e il commento; Invio porta Easyfish a quella posizione.

Dopo l'albero, con Tab: Vai alla posizione, come Invio; Commento, che
riscrive il testo del commento e tiene analisi e disegni; Taglia, la mossa
col suo seguito, con la conferma; Promuovi la variante, un gradino verso la
linea principale; Analizza, col motore, nei secondi e nelle linee
dell'analisi di Orologic, in una finestra da leggere; Chiudi, che torna a
Easyfish dov'era. Le modifiche stanno nella partita, e Easyfish la salva
all'uscita come sempre.
"""

import threading

import chess.engine
import wx
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto, dialoghi
from . import engine as orologic_engine
from .config import _
from .easyfish import analysis_utils, posizione


class analisi_fermabile:
    """Il motore di Orologic per il navigatore, con l'analisi che si ferma
    quando ferma e' acceso: chiuso il navigatore, l'analisi continuava sul
    motore fino a 1800 secondi (R140). Il resto viene dal motore vivo."""

    def __init__(self, ferma):
        self.ferma = ferma

    def __bool__(self):
        return orologic_engine.ENGINE is not None

    def __getattr__(self, nome):
        return getattr(orologic_engine.MOTORE, nome)

    def analyse(self, board, limit, multipv=1):
        motore = orologic_engine.ENGINE
        if motore is None:
            raise chess.engine.EngineTerminatedError(_("Il motore non c'e'."))
        with motore.analysis(board, limit, multipv=multipv) as corsa:
            finita = threading.Event()

            def aspetta():
                corsa.wait()
                finita.set()

            threading.Thread(target=aspetta, name="analisi del navigatore", daemon=True).start()
            while not finita.wait(0.1):
                if self.ferma.is_set():
                    corsa.stop()
                    break
            finita.wait(5)
            return list(corsa.multipv)


def analizza(board, ferma=None):
    """L'analisi della posizione col motore di Orologic: (righe, forma
    verbosa o None, riga della prima linea o None); con ferma, si ferma
    quando ferma si accende (R140). Le prove la sostituiscono."""
    # Il motore vivo, che riparte se e' morto (R41).
    motore = orologic_engine.MOTORE if ferma is None else analisi_fermabile(ferma)
    analisi, righe = analysis_utils.analizza(board, motore, orologic_engine.analysis_time, orologic_engine.multipv)
    if not analisi:
        return righe, None, None
    return (righe, *analysis_utils.dettagli_della_lettura(board, analisi, righe))


class Navigatore(wx.Dialog):
    """game e' la partita, nodo la mossa dove si e'. scelto, alla chiusura,
    e' la mossa dove andare, o None; modificata dice se la partita e'
    cambiata. chiedi_conferma, chiedi_valore e annuncia vengono dalla
    finestra principale."""

    def __init__(self, genitore, game, nodo, chiedi_conferma, chiedi_valore, annuncia):
        super().__init__(genitore, title=_("Navigatore della partita"), style=STILE_ADATTABILE)
        self.game = game
        self.scelto = None
        self.modificata = False
        self._chiedi_conferma = chiedi_conferma
        self._chiedi_valore = chiedi_valore
        self._annuncia = annuncia
        self.filo = None
        # Si accende alla chiusura, e l'analisi in corso si ferma (R140).
        self.ferma_l_analisi = threading.Event()
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(pannello, label=_("Mosse e varianti")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.albero = wx.TreeCtrl(pannello, style=wx.TR_HAS_BUTTONS | wx.TR_SINGLE)
        self.albero.SetName(_("Mosse e varianti"))
        sizer.Add(self.albero, 1, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsanti = {}
        for chiave, etichetta, azione in (
            ("vai", _("&Vai alla posizione"), self.vai),
            ("commento", _("&Commento"), self.commento),
            ("taglia", _("&Taglia"), self.taglia),
            ("promuovi", _("Pro&muovi la variante"), self.promuovi),
            ("analizza", _("&Analizza"), self.analizza),
            ("disegni", _("&Disegni"), self.disegni),
        ):
            pulsante = wx.Button(pannello, label=etichetta)
            pulsante.Bind(wx.EVT_BUTTON, lambda _evento, fai=azione: fai())
            self.pulsanti[chiave] = pulsante
            riga.Add(pulsante, 0, wx.RIGHT, 5)
        riga.Add(wx.Button(pannello, wx.ID_CANCEL, _("Chiudi")), 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        self.albero.SetMinSize(wx.Size(-1, self.albero.GetCharHeight() * 12))
        adatta_finestra(self, pannello, (720, 520))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.albero.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda _evento: self.vai())
        self.ricostruisci(nodo)
        self.albero.SetFocus()

    # L'albero.

    def ricostruisci(self, nodo=None):
        """L'albero da capo, con la mossa nodo selezionata, o la partita."""
        self.voci = {}
        self.albero.DeleteAllItems()
        radice = self.albero.AddRoot(posizione.voce_della_partita(self.game), data=self.game)
        self.voci[id(self.game)] = radice
        self._aggiungi(radice, posizione.albero(self.game))
        self.albero.Expand(radice)
        voce = self.voci.get(id(nodo), radice) if nodo is not None else radice
        # Le varianti chiuse che portano alla voce si aprono.
        self.albero.EnsureVisible(voce)
        self.albero.SelectItem(voce)

    def _aggiungi(self, genitore, passi):
        for nodo, testo, varianti in passi:
            voce = self.albero.AppendItem(genitore, testo, data=nodo)
            self.voci[id(nodo)] = voce
            for alternativa, testo_della_variante, seguito in varianti:
                ramo = self.albero.AppendItem(voce, testo_della_variante, data=alternativa)
                self.voci[id(alternativa)] = ramo
                self._aggiungi(ramo, seguito)

    def selezionato(self):
        voce = self.albero.GetSelection()
        if not voce.IsOk():
            return self.game
        return self.albero.GetItemData(voce)

    # I pulsanti.

    def vai(self):
        """Invio: Easyfish va alla posizione della voce."""
        self.scelto = self.selezionato()
        self._finisci(wx.ID_OK)

    def commento(self):
        """Il testo del commento: prende il posto di quello di prima, e
        tiene analisi e disegni."""
        nodo = self.selezionato()
        attuale = posizione.testo_libero(nodo.comment)
        testo = self._chiedi_valore(self, _("Commento"), _("Commento della mossa"), attuale, "testo", 0, 2000)
        self.albero.SetFocus()
        if testo is None:
            return
        posizione.metti_il_testo(nodo, testo)
        self.modificata = True
        self.ricostruisci(nodo)
        self._annuncia([_("Commento registrato.")])

    def disegni(self):
        """La finestra dei disegni, coi nuovi sulla mossa della voce
        (Gabriele, collaudo del 23 novembre 2026)."""
        from . import finestra_disegni

        nodo = self.selezionato()
        if finestra_disegni.disegna(self, self.game, nodo, self._chiedi_conferma, self._annuncia):
            self.modificata = True
            self.ricostruisci(nodo)
        self.albero.SetFocus()

    def taglia(self):
        """La mossa col suo seguito, dopo la conferma."""
        nodo = self.selezionato()
        if nodo.parent is None:
            self._annuncia([_("Impossibile eliminare l'inizio della partita.")])
            return
        seguito = posizione.semimosse_dopo(nodo)
        if seguito and not self._chiedi_conferma(self, posizione.domanda_del_taglio(seguito)):
            self.albero.SetFocus()
            return
        genitore = nodo.parent
        genitore.variations.remove(nodo)
        self.modificata = True
        self.ricostruisci(genitore)
        self.albero.SetFocus()
        self._annuncia([_("Mossa/Variante eliminata. Tornati indietro.")])

    def promuovi(self):
        """La variante dove sta la voce sale di un gradino: prende il posto
        della linea da cui si stacca."""
        nodo = self.selezionato()
        inizio = posizione.inizio_della_variante(nodo)
        if inizio is None:
            self._annuncia([_("Questa linea è già la principale.")])
            return
        varianti = inizio.parent.variations
        indice = varianti.index(inizio)
        varianti[0], varianti[indice] = varianti[indice], varianti[0]
        self.modificata = True
        self.ricostruisci(nodo)
        self._annuncia([_("Variante promossa a linea principale!")])

    def analizza(self):
        """L'analisi della posizione della voce, in un filo; le righe in
        una finestra da leggere."""
        if self.filo is not None:
            return
        board = posizione.scacchiera_del_nodo(self.game, self.selezionato())
        self._annuncia([_("Analisi in corso...")])

        def nel_filo():
            wx.CallAfter(self._analizzata, analizza(board, ferma=self.ferma_l_analisi))

        self.filo = threading.Thread(target=nel_filo, name="navigatore", daemon=True)
        self.filo.start()

    def _analizzata(self, lettura):
        # A navigatore chiuso l'analisi arrivata si scarta.
        if not self:
            return
        self.filo = None
        righe, verbosa, inizio = lettura
        dialoghi.da_leggere(self, _("Analisi"), righe, verbosa, inizio)
        self.albero.SetFocus()

    def _finisci(self, codice):
        if self.IsModal():
            self.EndModal(codice)
        else:
            self.SetReturnCode(codice)
            self.Hide()

    def _tasto(self, evento):
        if dialoghi.premuto_invio(evento) and evento.GetEventObject() is self.albero:
            self.vai()
            return
        evento.Skip()


def naviga(genitore, game, nodo, chiedi_conferma, chiedi_valore, annuncia):
    """Il navigatore aperto su nodo: (mossa dove andare o None, vero se la
    partita e' cambiata); le prove lo sostituiscono."""
    # Nessuna attesa dell'analisi in corso: il filo di wx l'aspettava alla
    # chiusura, fino a mezz'ora con l'analisi lunga. Il filo finisce da
    # solo, e il suo risultato si scarta (R85).
    with Navigatore(genitore, game, nodo, chiedi_conferma, chiedi_valore, annuncia) as dialogo:
        try:
            dialogo.ShowModal()
        finally:
            dialogo.ferma_l_analisi.set()
        return dialogo.scelto, dialogo.modificata
