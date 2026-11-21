# Orologic: la finestra della ricerca PGN.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La ricerca PGN nella finestra, come l'ha descritta Gabriele il 21
novembre 2026 (Piano della GUI.txt).

Si apre sulla finestra standard di Windows per scegliere il file; Dagli
appunti carica un indirizzo o un testo PGN, come la ricerca del terminale, e
il profilatore di Lichess passa il suo indirizzo direttamente. Il caricamento
gira in un filo, con l'avanzamento ogni tre secondi; Esc lo ferma e tiene
quello che e' arrivato.

In cima le statistiche generali dell'archivio; poi i dieci filtri del
terminale, con per etichetta la loro domanda, Applica i filtri e Azzera i
filtri; poi l'albero delle mosse, un albero nativo di Windows a selezione
singola, costruito un ramo alla volta quando si apre. Ogni voce ha la riga
del terminale, con la mossa descritta, la mossa, le partite, la percentuale
fra le mosse dello stesso punto e le statistiche; la foglia e' la partita,
quando un ramo ne ha una sola. Invio su un ramo lo apre o lo chiude, su una
foglia mostra la partita, coi pulsanti Passa a Easyfish, Analisi automatica,
Analisi manuale e Chiudi.

Dopo l'albero, con Tab: Inizio, Partite del ramo (il tasto 0 del
terminale), Salva il PGN (il tasto s), Percorso, che legge la linea fino
alla voce, e Chiudi.

Lo stato resta in pgn_search.Ricerca: dopo Easyfish o l'analisi la finestra
si riapre allo stesso punto, coi filtri di prima.
"""

import os
import threading

import chess.pgn
import pyperclip
import wx
from GBUtils import Acusticator
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto, config, dialoghi, pgn_search
from .config import _

SUONI = {
    # Come il no della pulizia: un'azione che adesso non si puo' fare.
    "no": lambda: Acusticator(["e3", 0.2, 0, config.VOLUME], kind=2),
}


def suona(evento):
    """I suoni della finestra; le prove li sostituiscono."""
    SUONI[evento]()


def domande_dei_filtri():
    """I filtri del terminale: chiave, domanda e tipo, il massimo per i
    numeri."""
    return (
        ("white", _("Nome giocatore Bianco (vuoto=qualsiasi): "), "testo"),
        ("black", _("Nome giocatore Nero (vuoto=qualsiasi): "), "testo"),
        ("player", _("Nome giocatore (cerca in bianco E nero, vuoto=qualsiasi): "), "testo"),
        ("result", _("Scegli risultato: "), "risultato"),
        ("elo_min", _("ELO minimo (0=nessun limite): "), 4000),
        ("elo_max", _("ELO massimo (0=nessun limite): "), 4000),
        ("event", _("Nome evento (vuoto=qualsiasi): "), "testo"),
        ("year_from", _("Anno dal (0=nessun limite): "), 2100),
        ("year_to", _("Anno al (0=nessun limite): "), 2100),
        ("eco", _("Codice ECO (es. 'B', 'B90', vuoto=qualsiasi): "), "testo"),
    )


def risultati():
    """Le scelte del filtro del risultato, con Qualsiasi per prima."""
    return (
        ("", _("Qualsiasi risultato")),
        ("1-0", _("Vittoria Bianco (1-0)")),
        ("0-1", _("Vittoria Nero (0-1)")),
        ("1/2-1/2", _("Patta (1/2-1/2)")),
    )


def etichetta_della_domanda(domanda):
    """La domanda del terminale come etichetta: senza i due punti in fondo."""
    return " ".join(domanda.split()).rstrip(":").rstrip()


def testo_della_partita(game):
    """Le intestazioni che dicono qualcosa, come le stampava il terminale,
    e le mosse, con varianti e commenti."""
    righe = [f"{chiave}: {valore}" for chiave, valore in game.headers.items() if valore and valore not in ("?", "????.??.??")]
    righe.append(game.accept(chess.pgn.StringExporter(headers=False, variations=True, comments=True, columns=None)))
    return "\n".join(righe)


def scegli_il_file(genitore):
    """La finestra standard di Windows per aprire un PGN; le prove la
    sostituiscono."""
    with wx.FileDialog(genitore, _("Ricerca PGN"), wildcard=_("Partite PGN (*.pgn)|*.pgn|Tutti i file (*.*)|*.*"),
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetPath()


def scegli_dove_salvare(genitore):
    """La finestra standard di Windows per salvare, nella cartella pgn di
    Orologic; le prove la sostituiscono."""
    cartella = config.percorso_salvataggio("pgn")
    os.makedirs(cartella, exist_ok=True)
    with wx.FileDialog(genitore, wx.StripMenuCodes(_("&Salva il PGN")), defaultDir=cartella, wildcard=_("Partite PGN (*.pgn)|*.pgn|Tutti i file (*.*)|*.*"),
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetPath()


def mostra_la_partita(genitore, testo):
    """La partita, coi suoi pulsanti: easyfish, automatica, manuale, o
    None per Chiudi; le prove la sostituiscono."""
    with VistaDellaPartita(genitore, testo) as dialogo:
        dialogo.ShowModal()
        return dialogo.azione


def finisci(dialogo, codice):
    """EndModal; fuori dal ciclo modale, come nelle prove, la finestra si
    nasconde col suo codice."""
    if dialogo.IsModal():
        dialogo.EndModal(codice)
    else:
        dialogo.SetReturnCode(codice)
        dialogo.Hide()


def scegli(genitore, titolo, voci, scelta=0):
    """La scelta da una lista; le prove la sostituiscono."""
    return dialoghi.scegli(genitore, titolo, voci, scelta)


class VistaDellaPartita(wx.Dialog):
    """La partita scelta: le intestazioni e le mosse, da leggere, e i
    pulsanti Passa a Easyfish, Analisi automatica, Analisi manuale e
    Chiudi. azione dice il pulsante premuto, None per Chiudi o Esc."""

    def __init__(self, genitore, testo):
        super().__init__(genitore, title=_("Partita selezionata"), style=STILE_ADATTABILE)
        self.azione = None
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(pannello, label=_("Partita selezionata")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.testo = wx.TextCtrl(pannello, value=testo, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.testo.SetName(_("Partita selezionata"))
        sizer.Add(self.testo, 1, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsanti = {}
        for azione, etichetta in (("easyfish", _("Passa a &Easyfish")), ("automatica", _("Analisi &automatica")), ("manuale", _("Analisi &manuale"))):
            pulsante = wx.Button(pannello, label=etichetta)
            pulsante.Bind(wx.EVT_BUTTON, lambda _evento, scelta=azione: self.scegli(scelta))
            self.pulsanti[azione] = pulsante
            riga.Add(pulsante, 0, wx.RIGHT, 5)
        riga.Add(wx.Button(pannello, wx.ID_CANCEL, _("Chiudi")), 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        self.testo.SetMinSize(wx.Size(-1, self.testo.GetCharHeight() * 10))
        adatta_finestra(self, pannello, (640, 480))
        self.Maximize()
        self.testo.SetInsertionPoint(0)
        self.testo.SetFocus()

    def scegli(self, azione):
        self.azione = azione
        finisci(self, wx.ID_OK)


class Nodo:
    """I dati di una voce dell'albero: le mosse dalla posizione iniziale, le
    partite che le hanno giocate, e la partita, se la voce e' una foglia."""

    def __init__(self, percorso, indici, partita=None):
        self.percorso = percorso
        self.indici = indici
        self.partita = partita
        self.popolato = False


class FinestraRicerca(wx.Dialog):
    """ricerca e' lo stato, pgn_search.Ricerca; chiedi_conferma(genitore,
    testo) chiede si' o no, avvisa(genitore, testo) dice cosa non e'
    andato, annuncia(righe) le dice in coda, se gli annunci sono attivi. uscita, alla chiusura, e'
    (azione, indice) per Easyfish o l'analisi, o None."""

    def __init__(self, genitore, ricerca, chiedi_conferma, avvisa, annuncia):
        super().__init__(genitore, title=_("Ricerca PGN"), style=STILE_ADATTABILE)
        self.ricerca = ricerca
        self._chiedi_conferma = chiedi_conferma
        self._avvisa = avvisa
        self._annuncia = annuncia
        self.uscita = None
        self.indici = []
        # Durante il caricamento: l'evento che lo ferma, e il filo.
        self._fermato = None
        self.filo = None
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_file = wx.Button(pannello, label=_("Apri &file"))
        self.pulsante_appunti = wx.Button(pannello, label=_("Dagli &appunti"))
        riga.Add(self.pulsante_file, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_appunti, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        sizer.Add(wx.StaticText(pannello, label=_("Archivio")), 0, wx.LEFT | wx.RIGHT, 5)
        self.riepilogo = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP)
        self.riepilogo.SetName(_("Archivio"))
        sizer.Add(self.riepilogo, 0, wx.EXPAND | wx.ALL, 5)
        griglia = wx.FlexGridSizer(cols=4, vgap=5, hgap=5)
        griglia.AddGrowableCol(1)
        griglia.AddGrowableCol(3)
        self.campi = {}
        for chiave, domanda, tipo in domande_dei_filtri():
            etichetta = etichetta_della_domanda(domanda)
            griglia.Add(wx.StaticText(pannello, label=etichetta), 0, wx.ALIGN_CENTER_VERTICAL)
            if tipo == "testo":
                campo = wx.TextCtrl(pannello)
            elif tipo == "risultato":
                campo = wx.Choice(pannello, choices=[testo for _codice, testo in risultati()])
                campo.SetSelection(0)
            else:
                campo = wx.SpinCtrl(pannello, min=0, max=tipo, initial=0)
            campo.SetName(etichetta)
            self.campi[chiave] = campo
            griglia.Add(campo, 1, wx.EXPAND)
        sizer.Add(griglia, 0, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_applica = wx.Button(pannello, label=_("Appli&ca i filtri"))
        self.pulsante_azzera = wx.Button(pannello, label=_("A&zzera i filtri"))
        riga.Add(self.pulsante_applica, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_azzera, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        self.etichetta_dell_albero = wx.StaticText(pannello, label=_("Nessun archivio caricato."))
        sizer.Add(self.etichetta_dell_albero, 0, wx.LEFT | wx.RIGHT, 5)
        self.albero = wx.TreeCtrl(pannello, style=wx.TR_HAS_BUTTONS | wx.TR_SINGLE)
        self.albero.SetName(_("Nessun archivio caricato."))
        sizer.Add(self.albero, 1, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_inizio = wx.Button(pannello, label=_("&Inizio"))
        self.pulsante_partite = wx.Button(pannello, label=_("Partite del &ramo"))
        self.pulsante_salva = wx.Button(pannello, label=_("&Salva il PGN"))
        self.pulsante_percorso = wx.Button(pannello, label=_("&Percorso"))
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        for pulsante in (self.pulsante_inizio, self.pulsante_partite, self.pulsante_salva, self.pulsante_percorso):
            riga.Add(pulsante, 0, wx.RIGHT, 5)
        riga.Add(chiudi, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        self.riepilogo.SetMinSize(wx.Size(-1, self.riepilogo.GetCharHeight() * 6))
        self.albero.SetMinSize(wx.Size(-1, self.albero.GetCharHeight() * 12))
        adatta_finestra(self, pannello, (800, 600))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.Bind(wx.EVT_BUTTON, self._chiudi, id=wx.ID_CANCEL)
        self.pulsante_file.Bind(wx.EVT_BUTTON, lambda _evento: self.apri_file())
        self.pulsante_appunti.Bind(wx.EVT_BUTTON, lambda _evento: self.dagli_appunti())
        self.pulsante_applica.Bind(wx.EVT_BUTTON, lambda _evento: self.applica())
        self.pulsante_azzera.Bind(wx.EVT_BUTTON, lambda _evento: self.azzera())
        self.pulsante_inizio.Bind(wx.EVT_BUTTON, lambda _evento: self.inizio())
        self.pulsante_partite.Bind(wx.EVT_BUTTON, lambda _evento: self.partite_del_ramo())
        self.pulsante_salva.Bind(wx.EVT_BUTTON, lambda _evento: self.salva())
        self.pulsante_percorso.Bind(wx.EVT_BUTTON, lambda _evento: self.percorso())
        self.albero.Bind(wx.EVT_TREE_ITEM_EXPANDING, lambda evento: self._popola(evento.GetItem()))
        self.albero.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda evento: self.attiva(evento.GetItem()))
        self._mostra()
        if ricerca.archivio is not None:
            self.albero.SetFocus()
        else:
            self.riepilogo.SetFocus()
            if ricerca.indirizzo:
                indirizzo, ricerca.indirizzo = ricerca.indirizzo, None
                wx.CallAfter(self._carica_se_aperta, "url", indirizzo)
            else:
                wx.CallAfter(self._apri_se_aperta)

    # Il caricamento.

    def _apri_se_aperta(self):
        if self:
            self.apri_file()

    def _carica_se_aperta(self, tipo, sorgente):
        if self:
            self.carica(tipo, sorgente)

    def carica_in_corso(self):
        return self._fermato is not None

    def apri_file(self):
        if self.carica_in_corso():
            suona("no")
            return
        percorso = scegli_il_file(self)
        if percorso:
            self.carica("file", percorso)

    def dagli_appunti(self):
        """Come il terminale: un percorso, un indirizzo o il testo PGN."""
        if self.carica_in_corso():
            suona("no")
            return
        try:
            testo = pyperclip.paste()
        # Gli appunti possono essere occupati o contenere di tutto.
        except Exception:  # noqa: BLE001
            self._avvisa(self, _("Impossibile accedere agli appunti."))
            return
        testo = (testo or "").strip().strip('"')
        if not testo:
            self._avvisa(self, _("Gli appunti sono vuoti."))
            return
        self.carica(pgn_search.tipo_di_sorgente(testo), testo)

    def carica(self, tipo, sorgente):
        """Il caricamento nel filo: l'avanzamento nell'area dell'archivio e
        alla voce; alla fine l'albero, o l'avviso di cosa non e' andato."""
        fermato = self._fermato = threading.Event()
        testo = _("Analisi del PGN in corso...")
        self.riepilogo.ChangeValue(testo)
        self.riepilogo.SetFocus()
        self._annuncia([testo])
        self.filo = threading.Thread(target=self._carica_nel_filo, args=(tipo, sorgente, fermato), name="ricerca_pgn", daemon=True)
        self.filo.start()

    def _carica_nel_filo(self, tipo, sorgente, fermato):
        try:
            archivio, righe = pgn_search.carica_archivio(tipo, sorgente, lambda testo: wx.CallAfter(self._avanzamento, testo), fermato.is_set)
        # Gli archivi PGN arrivano da fuori e possono essere malformati
        # in modi imprevedibili: il filo non deve morire in silenzio.
        except Exception as errore:  # noqa: BLE001
            archivio, righe = None, [str(errore)]
        wx.CallAfter(self._caricato, archivio, righe)

    def _avanzamento(self, testo):
        if not self or not self.carica_in_corso():
            return
        self.riepilogo.ChangeValue(testo)
        self._annuncia([testo])

    def _caricato(self, archivio, righe):
        if not self:
            return
        self._fermato = None
        if archivio is None:
            self._mostra()
            suona("no")
            self._avvisa(self, "\n".join(righe))
            (self.albero if self.ricerca.archivio is not None else self.riepilogo).SetFocus()
            return
        self.ricerca.archivio = archivio
        self.ricerca.righe = righe
        self.ricerca.filtri = {}
        self.ricerca.posizione = None
        self._mostra()
        self.albero.SetFocus()
        self._annuncia([righe[-1]])

    def ferma(self):
        """Esc durante il caricamento: si tiene quello che e' arrivato."""
        if self._fermato is not None:
            self._fermato.set()

    # L'archivio, i filtri e l'albero.

    def _mostra(self):
        """L'area dell'archivio, i filtri e l'albero dallo stato."""
        archivio = self.ricerca.archivio
        righe = list(self.ricerca.righe)
        if archivio is not None:
            righe += pgn_search.righe_dell_archivio(archivio)
        self.riepilogo.ChangeValue("\n".join(righe) if righe else _("Nessun archivio caricato."))
        self.riepilogo.SetInsertionPoint(0)
        self.metti_i_filtri(self.ricerca.filtri)
        self.ricostruisci(self.ricerca.posizione)

    def metti_i_filtri(self, filtri):
        for chiave, campo in self.campi.items():
            valore = filtri.get(chiave)
            if isinstance(campo, wx.TextCtrl):
                campo.ChangeValue(valore or "")
            elif isinstance(campo, wx.Choice):
                codici = [codice for codice, _testo in risultati()]
                campo.SetSelection(codici.index(valore) if valore in codici else 0)
            else:
                campo.SetValue(valore or 0)

    def filtri_dei_campi(self):
        """I filtri dei campi, con le chiavi del terminale: un campo vuoto o
        a zero non filtra."""
        filtri = {}
        for chiave, campo in self.campi.items():
            if isinstance(campo, wx.TextCtrl):
                valore = campo.GetValue().strip()
                if valore:
                    filtri[chiave] = valore.upper() if chiave == "eco" else valore
            elif isinstance(campo, wx.Choice):
                codice = risultati()[max(campo.GetSelection(), 0)][0]
                if codice:
                    filtri[chiave] = codice
            elif campo.GetValue() > 0:
                filtri[chiave] = campo.GetValue()
        return filtri

    def applica(self):
        if self.ricerca.archivio is None or self.carica_in_corso():
            suona("no")
            return
        self.ricerca.filtri = self.filtri_dei_campi()
        self.ricerca.posizione = None
        self.ricostruisci()
        self._annuncia([self.etichetta_dell_albero.GetLabel()])

    def azzera(self):
        if self.ricerca.archivio is None or self.carica_in_corso():
            suona("no")
            return
        self.ricerca.filtri = {}
        self.ricerca.posizione = None
        self.metti_i_filtri({})
        self.ricostruisci()
        self._annuncia([_("Tutti i filtri sono stati rimossi (azzerati).") + " " + self.etichetta_dell_albero.GetLabel()])

    def ricostruisci(self, posizione=None):
        """L'albero da capo, coi filtri dello stato, e la voce di posizione
        selezionata, o la radice."""
        self.albero.DeleteAllItems()
        archivio = self.ricerca.archivio
        if archivio is None:
            self.indici = []
            testo = _("Nessun archivio caricato.")
        else:
            self.indici = pgn_search.applica_filtri(archivio.info, self.ricerca.filtri)
            totale = len(archivio.games)
            pct = len(self.indici) / totale * 100 if totale else 0.0
            testo = pgn_search.pulita(_("Partite corrispondenti: {n} di {tot} ({pct:.2f}%)").format(n=len(self.indici), tot=totale, pct=pct))
        self.etichetta_dell_albero.SetLabel(testo)
        self.albero.SetName(testo)
        if archivio is None:
            return
        radice = self.albero.AddRoot(pgn_search.voce_della_radice(archivio, self.indici, self.ricerca.filtri), data=Nodo((), self.indici))
        self._popola(radice)
        self.albero.Expand(radice)
        voce = self._trova(radice, posizione) if posizione else radice
        self.albero.SelectItem(voce)
        self.albero.EnsureVisible(voce)

    def _popola(self, voce):
        """I figli della voce, la prima volta che servono: le mosse dalla
        piu' giocata, poi le partite che finiscono li'."""
        if not voce.IsOk():
            return
        nodo = self.albero.GetItemData(voce)
        if nodo is None or nodo.popolato or nodo.partita is not None:
            return
        nodo.popolato = True
        archivio = self.ricerca.archivio
        scacchiera = pgn_search.scacchiera_del_percorso(nodo.percorso)
        rami, finite = archivio.figli(nodo.indici, len(nodo.percorso))
        for mossa, indici in rami:
            testo = pgn_search.voce_del_ramo(archivio, scacchiera, mossa, indici, len(nodo.indici), self.ricerca.filtri)
            foglia = indici[0] if len(indici) == 1 else None
            figlio = self.albero.AppendItem(voce, testo, data=Nodo((*nodo.percorso, mossa), indici, foglia))
            if foglia is None:
                self.albero.SetItemHasChildren(figlio, True)
        for indice in finite:
            self.albero.AppendItem(voce, archivio.partita(indice), data=Nodo(nodo.percorso, [indice], indice))

    def figli(self, voce):
        figlio, biscotto = self.albero.GetFirstChild(voce)
        while figlio.IsOk():
            yield figlio
            figlio, biscotto = self.albero.GetNextChild(voce, biscotto)

    def _trova(self, radice, posizione):
        """La voce di posizione, (percorso, partita), aprendo i rami lungo la
        strada; dove la strada non c'e' piu', l'ultima voce trovata."""
        percorso, partita = posizione
        voce = radice
        for passo in range(1, len(percorso) + 1):
            self._popola(voce)
            prossima = next((figlio for figlio in self.figli(voce) if self.albero.GetItemData(figlio).percorso == percorso[:passo]), None)
            if prossima is None:
                return voce
            voce = prossima
        if partita is not None and self.albero.GetItemData(voce).partita != partita:
            self._popola(voce)
            voce = next((figlio for figlio in self.figli(voce) if self.albero.GetItemData(figlio).partita == partita), voce)
        return voce

    def selezionata(self):
        """La voce selezionata e il suo nodo, o (None, None)."""
        if self.ricerca.archivio is None or self.carica_in_corso():
            return None, None
        voce = self.albero.GetSelection()
        if not voce.IsOk():
            voce = self.albero.GetRootItem()
        if not voce.IsOk():
            return None, None
        return voce, self.albero.GetItemData(voce)

    def attiva(self, voce=None):
        """Invio: un ramo si apre o si chiude, una foglia mostra la partita."""
        if voce is None or not voce.IsOk():
            voce, nodo = self.selezionata()
        else:
            nodo = self.albero.GetItemData(voce)
        if nodo is None:
            return
        if nodo.partita is not None:
            self.mostra_partita(nodo.partita)
        elif self.albero.IsExpanded(voce):
            self.albero.Collapse(voce)
        else:
            self._popola(voce)
            self.albero.Expand(voce)

    # La partita e i pulsanti.

    def mostra_partita(self, indice):
        """La vista della partita: vero se si va a Easyfish o all'analisi,
        e la finestra si chiude con l'uscita."""
        azione = mostra_la_partita(self, testo_della_partita(self.ricerca.archivio.games[indice]))
        if azione is None:
            return False
        _voce, nodo = self.selezionata()
        self.ricerca.posizione = (nodo.percorso, nodo.partita) if nodo is not None else None
        self.uscita = (azione, indice)
        finisci(self, wx.ID_OK)
        return True

    def inizio(self):
        if self.ricerca.archivio is None or self.carica_in_corso():
            suona("no")
            return
        self.ricerca.posizione = None
        self.ricostruisci()
        self.albero.SetFocus()

    def partite_del_ramo(self):
        """Il tasto 0 del terminale: le partite del ramo, con le mosse che
        seguono; Invio mostra la partita, e chiudendola si torna all'elenco."""
        _voce, nodo = self.selezionata()
        if nodo is None or not nodo.indici:
            suona("no")
            return
        archivio = self.ricerca.archivio
        scacchiera = pgn_search.scacchiera_del_percorso(nodo.percorso)
        with wx.BusyCursor():
            voci = [archivio.voce_della_lista(scacchiera, indice, len(nodo.percorso), numero) for numero, indice in enumerate(nodo.indici, 1)]
        scelta = 0
        while True:
            scelta = scegli(self, wx.StripMenuCodes(_("Partite del &ramo")), voci, scelta)
            if scelta is None or self.mostra_partita(nodo.indici[scelta]):
                return

    def salva(self):
        """Il tasto s del terminale: le partite della voce in un file, con
        varianti e commenti."""
        _voce, nodo = self.selezionata()
        if nodo is None or not nodo.indici:
            suona("no")
            return
        if not self.ricerca.filtri and not nodo.percorso:
            avviso = pgn_search.pulita(
                _("\nAttenzione: non ci sono filtri attivi. " "Il file salvato sarebbe una copia dell'archivio originale.")
            )
            if not self._chiedi_conferma(self, avviso + " " + _("Salvo lo stesso?")):
                return
        percorso = scegli_dove_salvare(self)
        if not percorso:
            return
        if not os.path.splitext(percorso)[1]:
            percorso += ".pgn"
        try:
            pgn_search.scrivi_pgn(percorso, self.ricerca.archivio.games, nodo.indici)
        except OSError as errore:
            suona("no")
            self._avvisa(self, pgn_search.pulita(_("Errore nel salvataggio: {e}").format(e=errore)))
            return
        self._annuncia([pgn_search.pulita(_("Salvate {n} partite in: {path}").format(n=len(nodo.indici), path=percorso))])

    def percorso(self):
        """La linea dalla prima mossa alla voce selezionata, alla voce."""
        _voce, nodo = self.selezionata()
        if nodo is None:
            suona("no")
            return
        self._annuncia([pgn_search.sequenza_del_percorso(nodo.percorso)])

    def _chiudi(self, _evento=None):
        """Chiudi, Esc fuori dal caricamento, o la X: un caricamento in corso
        si ferma, e la finestra si chiude senza uscita."""
        self.ferma()
        finisci(self, wx.ID_CANCEL)

    def _tasto(self, evento):
        codice = evento.GetKeyCode()
        if codice == wx.WXK_ESCAPE and not evento.HasAnyModifiers() and self.carica_in_corso():
            self.ferma()
            return
        if dialoghi.premuto_invio(evento):
            oggetto = evento.GetEventObject()
            if oggetto is self.albero:
                self.attiva()
                return
            if oggetto in self.campi.values():
                self.applica()
                return
        evento.Skip()
