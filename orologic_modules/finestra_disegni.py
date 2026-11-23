# Orologic: la finestra dei disegni di Easyfish, frecce e cerchi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra dei disegni, come l'ha chiesta Gabriele dopo il collaudo del
23 novembre 2026, sullo stile della composizione del prompt, al posto del
menu .d del terminale, che resta per --cli.

In cima l'elenco dei disegni di tutta la partita, mossa per mossa, con
[mossa attuale] su quelli della mossa dove si e': Canc toglie il disegno
scelto. Sotto, gli elenchi per farne uno nuovo: la forma, freccia o cerchio,
il colore, e le case, colonna e traversa, di partenza e, per la freccia, di
arrivo; Aggiungi lo mette sulla mossa attuale. Pulisci tutto, dopo la
conferma, toglie i disegni da tutta la partita. Le modifiche valgono subito;
Chiudi, o Esc, chiude.

I disegni sono quelli del PGN di Lichess e ChessBase, [%cal Ge2e4] e
[%csl Rd5], nel commento della mossa: verde, rosso, blu e giallo. I suoni
sono quelli del menu del terminale per gli stessi eventi; la cancellazione
di un disegno, che il terminale non ha, ha il suo.
"""

import chess
import wx
from GBUtils import Acusticator
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto, config, localizzazione
from .config import _
from .easyfish import drawing, posizione

# Il colore nel PGN e il suo nome, nell'ordine degli elenchi e del terminale.
COLORI = ("G", "R", "B", "Y")
COLONNE = "abcdefgh"
TRAVERSE = "12345678"
# La cancellazione di un disegno: una cosa che si cancella; firmato da
# Orologic in GBUtils V314.
SUONO_DELLA_CANCELLAZIONE = "due_cadute_di_quinta"

SUONI = {
    "apri": drawing.suono_del_menu,
    "aggiunto": drawing.suono_dell_aggiunta,
    "pulito": drawing.suono_della_pulizia,
    "cancellato": lambda: Acusticator.play(SUONO_DELLA_CANCELLAZIONE, volume=config.VOLUME),
    # Come il no della pulizia e della ricerca: adesso non si puo'.
    "no": lambda: Acusticator(["e3", 0.2, 0, config.VOLUME], kind=2),
}


def suona(evento):
    """I suoni della finestra; le prove li sostituiscono."""
    SUONI[evento]()


def nodi_in_ordine(game):
    """La partita e le sue mosse nell'ordine del PGN: ogni mossa, poi le
    sue alternative col loro seguito, poi il seguito della linea. Senza la
    ricorsione, per le partite lunghe."""
    yield game
    pila = [("seguito", game)]
    while pila:
        cosa, nodo = pila.pop()
        if cosa == "mossa":
            yield nodo
            continue
        if not nodo.variations:
            continue
        principale, *altre = nodo.variations
        pila.append(("seguito", principale))
        for alternativa in reversed(altre):
            pila.append(("seguito", alternativa))
            pila.append(("mossa", alternativa))
        pila.append(("mossa", principale))


def nome_della_mossa(game, nodo):
    """12. Nf3, 12... Nf6, o Posizione iniziale per la partita."""
    if nodo.parent is None:
        return _("Posizione iniziale")
    prima = posizione.scacchiera_del_nodo(game, nodo.parent)
    return f"{posizione.numero(prima)} {prima.san(nodo.move)}"


def disegni_della_partita(game):
    """[(nodo, forma, codice)] di tutta la partita: forma e' freccia o
    cerchio, codice come nel PGN, Ge2e4 o Rd5."""
    disegni = []
    for nodo in nodi_in_ordine(game):
        frecce, cerchi = drawing.get_drawings_from_node(nodo)
        disegni.extend((nodo, "freccia", codice) for codice in frecce)
        disegni.extend((nodo, "cerchio", codice) for codice in cerchi)
    return disegni


def descrizione(forma, codice):
    """Freccia da Empoli 2 a Empoli 4 (verde), con le frasi del terminale."""
    return drawing.descrivi_freccia(codice) if forma == "freccia" else drawing.descrivi_cerchio(codice)


def togli(nodo, forma, codice):
    frecce, cerchi = drawing.get_drawings_from_node(nodo)
    if forma == "freccia":
        frecce = [freccia for freccia in frecce if freccia != codice]
    else:
        cerchi = [cerchio for cerchio in cerchi if cerchio != codice]
    drawing.set_drawings_to_node(nodo, frecce, cerchi)


def aggiungi(nodo, forma, colore, da, a=None):
    """Il disegno sulla mossa: 'aggiunto', 'cambiato' se c'era con un altro
    colore, o 'presente' se c'era gia' com'e'."""
    frecce, cerchi = drawing.get_drawings_from_node(nodo)
    elenco = frecce if forma == "freccia" else cerchi
    case = da + (a or "")
    codice = colore + case
    if codice in elenco:
        return "presente"
    esito = "aggiunto"
    for numero, esistente in enumerate(elenco):
        if esistente[1:] == case:
            elenco[numero] = codice
            esito = "cambiato"
            break
    else:
        elenco.append(codice)
    drawing.set_drawings_to_node(nodo, frecce, cerchi)
    return esito


class FinestraDisegni(wx.Dialog):
    """game e' la partita, nodo la mossa attuale, dove vanno i disegni
    nuovi; modificata, alla chiusura, dice se la partita e' cambiata.
    chiedi_conferma(genitore, testo) chiede si' o no, annuncia(righe) le
    dice in coda, se gli annunci sono attivi."""

    def __init__(self, genitore, game, nodo, chiedi_conferma, annuncia):
        super().__init__(genitore, title=_("Disegni"), style=STILE_ADATTABILE)
        self.game = game
        self.nodo = nodo
        self.modificata = False
        self._chiedi_conferma = chiedi_conferma
        self._annuncia = annuncia
        self.disegni = []
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        sizer.Add(wx.StaticText(pannello, label=_("Disegni della partita")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.elenco = wx.ListBox(pannello, style=wx.LB_SINGLE)
        self.elenco.SetName(_("Disegni della partita"))
        sizer.Add(self.elenco, 1, wx.EXPAND | wx.ALL, 5)
        griglia = wx.FlexGridSizer(cols=2, vgap=5, hgap=5)
        griglia.AddGrowableCol(1)
        colonne = [f"{colonna} {localizzazione.colonna(colonna)}" for colonna in COLONNE]
        self.forma = self._scelta(pannello, griglia, _("Forma"), [_("Freccia"), _("Cerchio")])
        self.colore = self._scelta(pannello, griglia, _("Colore"), [drawing.verbalize_color(colore) for colore in COLORI])
        self.colonna_da = self._scelta(pannello, griglia, _("Colonna di partenza"), colonne)
        self.traversa_da = self._scelta(pannello, griglia, _("Traversa di partenza"), list(TRAVERSE))
        self.colonna_a = self._scelta(pannello, griglia, _("Colonna di arrivo"), colonne)
        self.traversa_a = self._scelta(pannello, griglia, _("Traversa di arrivo"), list(TRAVERSE))
        sizer.Add(griglia, 0, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_aggiungi = wx.Button(pannello, label=_("&Aggiungi"))
        self.pulsante_pulisci = wx.Button(pannello, label=_("&Pulisci tutto"))
        riga.Add(self.pulsante_aggiungi, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_pulisci, 0, wx.RIGHT, 5)
        riga.Add(wx.Button(pannello, wx.ID_CANCEL, _("Chiudi")), 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pannello.SetSizer(sizer)
        self.pulsante_aggiungi.Bind(wx.EVT_BUTTON, lambda _evento: self.aggiungi())
        self.pulsante_pulisci.Bind(wx.EVT_BUTTON, lambda _evento: self.pulisci_tutto())
        self.forma.Bind(wx.EVT_CHOICE, lambda _evento: self._forma_scelta())
        self.elenco.Bind(wx.EVT_KEY_DOWN, self._tasto_dell_elenco)
        aspetto.applica_alla_finestra(self)
        self.elenco.SetMinSize(wx.Size(-1, self.elenco.GetCharHeight() * 10))
        adatta_finestra(self, pannello, (640, 520))
        self.Maximize()
        self._case_di_partenza()
        self._forma_scelta()
        self.rinfresca()
        suona("apri")
        self.elenco.SetFocus()

    def _scelta(self, pannello, griglia, etichetta, voci):
        griglia.Add(wx.StaticText(pannello, label=etichetta), 0, wx.ALIGN_CENTER_VERTICAL)
        scelta = wx.Choice(pannello, choices=voci)
        scelta.SetName(etichetta)
        scelta.SetSelection(0)
        griglia.Add(scelta, 1, wx.EXPAND)
        return scelta

    def _case_di_partenza(self):
        """Le case partono dalla mossa attuale: da dove a dove si e' mossi,
        o e2 ed e4 all'inizio."""
        mossa = self.nodo.move if self.nodo.parent is not None else None
        da, a = (chess.square_name(mossa.from_square), chess.square_name(mossa.to_square)) if mossa else ("e2", "e4")
        for colonna, traversa, casa in ((self.colonna_da, self.traversa_da, da), (self.colonna_a, self.traversa_a, a)):
            colonna.SetSelection(COLONNE.index(casa[0]))
            traversa.SetSelection(TRAVERSE.index(casa[1]))

    def _forma_scelta(self):
        """Il cerchio ha una casa sola: le caselle dell'arrivo si spengono,
        e il Tab le salta."""
        freccia = self.forma.GetSelection() == 0
        self.colonna_a.Enable(freccia)
        self.traversa_a.Enable(freccia)

    # L'elenco.

    def rinfresca(self, scelta=None):
        """L'elenco da capo, con scelta, un indice, selezionata."""
        self.disegni = disegni_della_partita(self.game)
        attuale = _("[mossa attuale]")
        voci = []
        for nodo, forma, codice in self.disegni:
            voce = _("{mossa}: {disegno}").format(mossa=nome_della_mossa(self.game, nodo), disegno=descrizione(forma, codice))
            voci.append(f"{voce} {attuale}" if nodo is self.nodo else voce)
        self.elenco.Set(voci)
        if voci:
            self.elenco.SetSelection(max(0, min(scelta or 0, len(voci) - 1)))

    def _tasto_dell_elenco(self, evento):
        if evento.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and not evento.HasAnyModifiers():
            self.cancella()
            return
        evento.Skip()

    def cancella(self):
        """Canc: il disegno scelto se ne va, e il fuoco resta sul vicino."""
        scelto = self.elenco.GetSelection()
        if scelto == wx.NOT_FOUND or scelto >= len(self.disegni):
            suona("no")
            return
        nodo, forma, codice = self.disegni[scelto]
        togli(nodo, forma, codice)
        self.modificata = True
        suona("cancellato")
        self.rinfresca(scelto)
        self.elenco.SetFocus()

    # I pulsanti.

    def aggiungi(self):
        """Il disegno degli elenchi sulla mossa attuale."""
        da = COLONNE[self.colonna_da.GetSelection()] + TRAVERSE[self.traversa_da.GetSelection()]
        colore = COLORI[self.colore.GetSelection()]
        if self.forma.GetSelection() == 0:
            a = COLONNE[self.colonna_a.GetSelection()] + TRAVERSE[self.traversa_a.GetSelection()]
            if a == da:
                suona("no")
                self._annuncia([_("La freccia deve andare da una casa a un'altra.")])
                return
            forma, case = "freccia", (da, a)
        else:
            forma, case = "cerchio", (da,)
        esito = aggiungi(self.nodo, forma, colore, *case)
        if esito == "presente":
            suona("no")
            self._annuncia([_("Questo disegno c'e' gia'.")])
            return
        self.modificata = True
        suona("aggiunto")
        codice = colore + "".join(case)
        self.rinfresca()
        self.elenco.SetSelection(next(numero for numero, disegno in enumerate(self.disegni) if disegno[0] is self.nodo and disegno[2] == codice))
        self._annuncia([_("Aggiunto: {disegno}").format(disegno=descrizione(forma, codice))])

    def pulisci_tutto(self):
        """Tutti i disegni di tutta la partita, dopo la conferma."""
        if not self.disegni:
            suona("no")
            self._annuncia([_("Nessun disegno nella partita.")])
            return
        if not self._chiedi_conferma(self, _("Cancello tutti i disegni della partita?")):
            return
        mosse = drawing.clear_all_drawings(self.game)
        self.modificata = True
        suona("pulito")
        self.rinfresca()
        self._annuncia([_("Pulizia completata. Cancellati disegni in {n} mosse.").format(n=mosse)])
        self.elenco.SetFocus()


def disegna(genitore, game, nodo, chiedi_conferma, annuncia):
    """Apre la finestra dei disegni e aspetta che si chiuda: vero se la
    partita e' cambiata."""
    with FinestraDisegni(genitore, game, nodo, chiedi_conferma, annuncia) as dialogo:
        dialogo.ShowModal()
        return dialogo.modificata
