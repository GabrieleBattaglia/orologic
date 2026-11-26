# Orologic: la finestra della ricerca PGN.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La ricerca PGN nella finestra, come l'ha descritta Gabriele il 21
novembre 2026 (Piano della GUI.txt) e come l'ha voluta dopo il collaudo del
22 novembre.

Si apre guardando gli appunti: il percorso di un file PGN o un testo PGN si
caricano subito, altrimenti si sceglie il file con la finestra standard di
Windows. Dagli appunti carica anche un indirizzo, come la ricerca del
terminale, e il profilatore di Lichess passa il suo indirizzo direttamente.
Il caricamento gira in un filo, con tutti i processori per gli archivi
grandi e l'avanzamento ogni tre secondi; Esc lo ferma e tiene quello che
e' arrivato.

Due schede. Partite: in cima le statistiche generali dell'archivio, poi
l'albero delle mosse, un albero nativo di Windows a selezione singola,
costruito un ramo alla volta quando si apre, e i pulsanti. Filtri: i dieci
filtri del terminale, con per etichetta la loro domanda, quelli delle mosse,
del matto e della promozione, Applica i filtri e Azzera i filtri.

Ogni mossa dell'albero ha la riga del terminale, con la mossa descritta, la
mossa, le partite, la percentuale fra le mosse dello stesso punto e le
statistiche; le partite che ci arrivano da una variante dei commenti sono
contate a parte, fuori dalle statistiche. La foglia e' la partita, quando un
ramo ne ha una sola. In fondo alla radice Non classificate, le partite senza
mosse, da una posizione di studio o senza codice ECO, e Con errori, un ramo per
tipo, coi doppioni cercati da un filo mentre si naviga.

Invio su un ramo lo apre o lo chiude, su una foglia mostra la partita, coi
pulsanti Passa a Easyfish, Analisi automatica, Analisi manuale e Chiudi.
Dopo l'albero, con Tab: Inizio, Partite del ramo (il tasto 0 del terminale),
Salva il PGN (il tasto s), Percorso, che legge la linea fino alla voce,
Classifica, che scrive il codice ECO alle non classificate, e Ripara gli
errori. Alt+1 porta all'archivio, Alt+2 all'albero, Alt+3 ai pulsanti,
Alt+4 al primo filtro.

Lo stato resta in archivio_pgn.Ricerca: dopo Easyfish o l'analisi la
finestra si riapre allo stesso punto, coi filtri di prima.
"""

import os
import re
import threading
import time

import pyperclip
import wx
from GBUtils import Acusticator
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import archivio_pgn, aspetto, config, dialoghi, pgn_search
from .config import _

# I filtri degli anni, elenchi con gli anni dell'archivio, e quanto si
# aspetta fra una cifra e l'altra dell'anno scritto.
ANNI = ("year_from", "year_to")
PAUSA_FRA_LE_CIFRE = 1.5
# Oltre questo numero le partite di un gruppo o di un tipo di problema
# stanno in blocchi di questa misura (R66).
PARTITE_PER_BLOCCO = 500
# Le partite che Partite del ramo mette al piu' nell'elenco: prima una voce
# per partita senza limite, residuo di R66 (R138).
MASSIMO_DEL_RAMO = 1000

SUONI = {
    # Come il no della pulizia: un'azione che adesso non si puo' fare.
    "no": lambda: Acusticator(["e3", 0.2, 0, config.VOLUME], kind=2),
}


def suona(evento):
    """I suoni della finestra; le prove li sostituiscono."""
    SUONI[evento]()


def domande_dei_filtri():
    """I filtri: chiave, domanda e tipo, il massimo per i numeri. Dal
    secondo all'undicesimo sono quelli del terminale; gli anni, dal 23
    novembre 2026, sono elenchi con gli anni dell'archivio (Gabriele: lo 0
    per nessun limite non era chiaro). Cerca testo cerca in tutto il testo
    della partita, intestazioni, mosse e commenti."""
    return (
        ("cerca", _("Cerca testo"), "testo"),
        ("white", _("Nome giocatore Bianco (vuoto=qualsiasi): "), "testo"),
        ("black", _("Nome giocatore Nero (vuoto=qualsiasi): "), "testo"),
        ("player", _("Nome giocatore (cerca in bianco E nero, vuoto=qualsiasi): "), "testo"),
        ("result", _("Scegli risultato: "), "risultato"),
        ("elo_min", _("ELO minimo (0=nessun limite): "), 4000),
        ("elo_max", _("ELO massimo (0=nessun limite): "), 4000),
        ("event", _("Nome evento (vuoto=qualsiasi): "), "testo"),
        ("year_from", _("Anno dal"), "anno"),
        ("year_to", _("Anno al"), "anno"),
        ("eco", _("Codice ECO (es. 'B', 'B90', vuoto=qualsiasi): "), "testo"),
        ("mosse_min", _("Con almeno queste mosse (0=nessun limite): "), 1000),
        ("mosse_max", _("Con meno di queste mosse (0=nessun limite): "), 1000),
        ("matto", _("Terminata con il matto"), "casella"),
        ("promozione", _("Con promozione"), "casella"),
    )


def risultati():
    """Le scelte del filtro del risultato, con Qualsiasi per prima."""
    return (
        ("", _("Qualsiasi risultato")),
        ("1-0", _("Vittoria Bianco (1-0)")),
        ("0-1", _("Vittoria Nero (0-1)")),
        ("1/2-1/2", _("Patta (1/2-1/2)")),
        ("*", _("Non specificato (*)")),
    )


def etichetta_della_domanda(domanda):
    """La domanda del terminale come etichetta: senza i due punti in fondo."""
    return " ".join(domanda.split()).rstrip(":").rstrip()


# Un testo PGN: una riga d'intestazione, o la prima mossa col suo numero.
PGN_NEL_TESTO = re.compile(r'^\s*\[[A-Za-z]\w* "|(?:^|\s)1\.\s*(?:[a-h][1-8]|[NBRQK][a-h1-8x]|O-O)', re.MULTILINE)


def sorgente_negli_appunti():
    """(tipo, sorgente) se negli appunti c'e' il percorso di un file .pgn o
    un testo PGN, altrimenti None. Gli indirizzi no: un collegamento
    copiato per altro farebbe partire uno scaricamento; per quelli c'e'
    Dagli appunti."""
    try:
        testo = pyperclip.paste()
    # Gli appunti possono essere occupati o contenere di tutto.
    except Exception:  # noqa: BLE001
        return None
    testo = (testo or "").strip().strip('"')
    if not testo:
        return None
    if "\n" not in testo and testo.lower().endswith(".pgn") and os.path.isfile(testo):
        return "file", testo
    if PGN_NEL_TESTO.search(testo):
        return "testo", testo
    return None


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


def mostra_la_partita(genitore, testo, chiedi_conferma, avvisa):
    """La partita nel suo PGN, da correggere a mano, coi suoi pulsanti:
    (azione, testo nuovo o None). azione e' easyfish, automatica, manuale,
    o None per Chiudi; il testo nuovo c'e' se e' cambiato, e' una partita
    valida e si e' scelto di salvarlo. Le prove la sostituiscono."""
    with VistaDellaPartita(genitore, testo, chiedi_conferma, avvisa) as dialogo:
        dialogo.ShowModal()
        return dialogo.azione, dialogo.nuovo


def salva_all_uscita(genitore, ricerca, chiedi_conferma, avvisa, scarta=True):
    """Uscendo dalla ricerca, o chiudendo Orologic, con un archivio da file
    modificato: si chiede se salvare nel file, poi se fare prima la copia di
    sicurezza (Gabriele, collaudo del 23 novembre 2026). Vero se si puo'
    andare avanti; falso se il salvataggio non e' riuscito: chi chiama
    resta dov'e', e si puo' riprovare. Prima la finestra si chiudeva lo
    stesso, e le modifiche se ne andavano (R61). scarta falso, prima di
    caricare un altro archivio: col no il segno di modificato resta finche'
    il caricamento non riesce, e se fallisce la domanda torna. Prima si
    spegneva subito (R138)."""
    archivio = ricerca.archivio
    if archivio is None or not archivio.modificato or archivio.percorso is None:
        return True
    domanda = _("Hai modificato l'archivio. Salvo le modifiche nel file {percorso}? Se rispondi no, si perdono.")
    if not chiedi_conferma(genitore, pgn_search.pulita(domanda.format(percorso=archivio.percorso))):
        if scarta:
            archivio.modificato = False
        return True
    con_la_copia = chiedi_conferma(genitore, _("Prima di salvare faccio una copia di sicurezza del file, nella cartella pgn di Orologic?"))
    try:
        with wx.BusyCursor():
            righe = archivio_pgn.salva_nel_file(archivio, con_la_copia)
    except OSError as errore:
        suona("no")
        testo = _("Errore nel salvataggio: {e}").format(e=errore) + " " + _("Le modifiche restano: puoi riprovare.")
        avvisa(genitore, pgn_search.pulita(testo))
        return False
    avvisa(genitore, "\n".join(righe))
    return True


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
    """La partita scelta nel suo PGN, com'e' nell'archivio, da leggere e da
    correggere a mano, e i pulsanti Passa a Easyfish, Analisi automatica,
    Analisi manuale e Chiudi. azione dice il pulsante premuto, None per
    Chiudi o Esc. Uscendo, se il testo e' cambiato: una partita valida si
    salva nell'archivio, se lo si vuole, in nuovo; una che non lo e' si
    torna a correggere, o si lascia (Gabriele, collaudo del 23 novembre
    2026)."""

    def __init__(self, genitore, testo, chiedi_conferma, avvisa):
        super().__init__(genitore, title=_("Partita selezionata"), style=STILE_ADATTABILE)
        self.azione = None
        self.nuovo = None
        self._chiedi_conferma = chiedi_conferma
        self._avvisa = avvisa
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(pannello, label=_("Partita selezionata")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.testo = wx.TextCtrl(pannello, value=testo, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self.testo.SetName(_("Partita selezionata"))
        # Il testo come lo da' il controllo, per sapere se e' cambiato.
        self.originale = self.testo.GetValue()
        sizer.Add(self.testo, 1, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsanti = {}
        for azione, etichetta in (("easyfish", _("Passa a &Easyfish")), ("automatica", _("Analisi &automatica")), ("manuale", _("Analisi &manuale"))):
            pulsante = wx.Button(pannello, label=etichetta)
            pulsante.Bind(wx.EVT_BUTTON, lambda _evento, scelta=azione: self.scegli(scelta))
            self.pulsanti[azione] = pulsante
            riga.Add(pulsante, 0, wx.RIGHT, 5)
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        chiudi.Bind(wx.EVT_BUTTON, lambda _evento: self.scegli(None))
        riga.Add(chiudi, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pannello.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, lambda _evento: self.scegli(None))
        aspetto.applica_alla_finestra(self)
        self.testo.SetMinSize(wx.Size(-1, self.testo.GetCharHeight() * 10))
        adatta_finestra(self, pannello, (640, 480))
        self.Maximize()
        self.testo.SetInsertionPoint(0)
        self.testo.SetFocus()

    def scegli(self, azione):
        """Un pulsante, Chiudi o Esc: prima la partita corretta, se c'e'."""
        if not self._lascia_la_partita():
            return
        self.azione = azione
        finisci(self, wx.ID_OK if azione else wx.ID_CANCEL)

    def _lascia_la_partita(self):
        """Falso se si torna a correggere."""
        testo = self.testo.GetValue()
        if testo == self.originale:
            return True
        motivo = archivio_pgn.motivo_non_valida(testo)
        if motivo is not None:
            suona("no")
            self._avvisa(self, _("La partita corretta non e' valida: {motivo}").format(motivo=motivo))
            if self._chiedi_conferma(self, _("Torno alla partita per correggerla? Se rispondi no, le correzioni si perdono.")):
                self.testo.SetFocus()
                return False
            return True
        if self._chiedi_conferma(self, _("La partita e' cambiata. La salvo nell'archivio?")):
            self.nuovo = testo
        return True


class Nodo:
    """I dati di una voce dell'albero. chiave la distingue fra le sorelle,
    per tornarci; tipo e' radice, mosse, non_classificate, gruppo,
    problemi, problema o foglia. indici sono le partite della voce, per le
    mosse quelle che l'hanno giocata; percorso le mosse dalla posizione
    iniziale; linee le linee delle varianti che passano di li', [(partita,
    linea)], e varianti le partite che ci arrivano solo da una variante;
    partita la partita della foglia; problema il tipo, nel ramo Con errori."""

    def __init__(self, chiave, tipo, indici=(), percorso=(), linee=(), varianti=(), partita=None, problema=None):
        self.chiave = chiave
        self.tipo = tipo
        self.indici = indici
        self.percorso = percorso
        self.linee = linee
        self.varianti = varianti
        self.partita = partita
        self.problema = problema
        self.popolato = False

    def tutte(self):
        """Le partite della voce: quelle giocate, poi quelle delle varianti."""
        return [*self.indici, *(indice for indice, _linea in self.varianti)]


class FinestraRicerca(wx.Dialog):
    """ricerca e' lo stato, archivio_pgn.Ricerca; chiedi_conferma(genitore,
    testo) chiede si' o no, avvisa(genitore, testo) dice cosa non e' andato
    o com'e' andata, annuncia(righe) le dice in coda, se gli annunci sono
    attivi. uscita, alla chiusura, e' (azione, indice) per Easyfish o
    l'analisi, o None."""

    def __init__(self, genitore, ricerca, chiedi_conferma, avvisa, annuncia):
        super().__init__(genitore, title=_("Ricerca PGN"), style=STILE_ADATTABILE)
        self.ricerca = ricerca
        self._cifre = ""
        self._ultima_cifra = 0.0
        self._chiedi_conferma = chiedi_conferma
        self._avvisa = avvisa
        self._annuncia = annuncia
        self.uscita = None
        self.indici = []
        # Durante il caricamento, Classifica o Ripara: l'evento che li ferma,
        # e il filo.
        self._fermato = None
        self.filo = None
        # La ricerca dei doppioni, mentre si naviga.
        self._fermati_i_doppioni = None
        self.filo_doppioni = None
        self.avanzamento_doppioni = 0
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.schede = wx.Notebook(pannello)
        self.pagina_partite = wx.Panel(self.schede)
        self.pagina_filtri = wx.Panel(self.schede)
        self.schede.AddPage(self.pagina_partite, _("Partite"))
        self.schede.AddPage(self.pagina_filtri, _("Filtri"))
        self._pagina_delle_partite(self.pagina_partite)
        self._pagina_dei_filtri(self.pagina_filtri)
        sizer.Add(self.schede, 1, wx.EXPAND | wx.ALL, 5)
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        sizer.Add(chiudi, 0, wx.ALL, 5)
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
        self.pulsante_classifica.Bind(wx.EVT_BUTTON, lambda _evento: self.classifica())
        self.pulsante_ripara.Bind(wx.EVT_BUTTON, lambda _evento: self.ripara())
        self.albero.Bind(wx.EVT_TREE_ITEM_EXPANDING, lambda evento: self._popola(evento.GetItem()))
        self.albero.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda evento: self.attiva(evento.GetItem()))
        self._mostra()
        if ricerca.archivio is not None:
            self.albero.SetFocus()
            self._cerca_i_doppioni()
        else:
            self.riepilogo.SetFocus()
            if ricerca.indirizzo:
                indirizzo, ricerca.indirizzo = ricerca.indirizzo, None
                wx.CallAfter(self._carica_se_aperta, "url", indirizzo)
            else:
                wx.CallAfter(self._all_ingresso)

    def _pagina_delle_partite(self, pagina):
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        sizer = wx.BoxSizer(wx.VERTICAL)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_file = wx.Button(pagina, label=_("Apri &file"))
        self.pulsante_appunti = wx.Button(pagina, label=_("Dagli &appunti"))
        riga.Add(self.pulsante_file, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_appunti, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        sizer.Add(wx.StaticText(pagina, label=_("Archivio")), 0, wx.LEFT | wx.RIGHT, 5)
        self.riepilogo = wx.TextCtrl(pagina, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP)
        self.riepilogo.SetName(_("Archivio"))
        sizer.Add(self.riepilogo, 0, wx.EXPAND | wx.ALL, 5)
        self.etichetta_dell_albero = wx.StaticText(pagina, label=_("Nessun archivio caricato."))
        sizer.Add(self.etichetta_dell_albero, 0, wx.LEFT | wx.RIGHT, 5)
        self.albero = wx.TreeCtrl(pagina, style=wx.TR_HAS_BUTTONS | wx.TR_SINGLE)
        self.albero.SetName(_("Nessun archivio caricato."))
        sizer.Add(self.albero, 1, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_inizio = wx.Button(pagina, label=_("&Inizio"))
        self.pulsante_partite = wx.Button(pagina, label=_("Partite del &ramo"))
        self.pulsante_salva = wx.Button(pagina, label=_("&Salva il PGN"))
        self.pulsante_percorso = wx.Button(pagina, label=_("&Percorso"))
        self.pulsante_classifica = wx.Button(pagina, label=_("C&lassifica"))
        self.pulsante_ripara = wx.Button(pagina, label=_("Ripara gli &errori"))
        for pulsante in (self.pulsante_inizio, self.pulsante_partite, self.pulsante_salva, self.pulsante_percorso, self.pulsante_classifica):
            riga.Add(pulsante, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_ripara, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pagina.SetSizer(sizer)

    def _pagina_dei_filtri(self, pagina):
        sizer = wx.BoxSizer(wx.VERTICAL)
        griglia = wx.FlexGridSizer(cols=4, vgap=5, hgap=5)
        griglia.AddGrowableCol(1)
        griglia.AddGrowableCol(3)
        self.campi = {}
        for chiave, domanda, tipo in domande_dei_filtri():
            etichetta = etichetta_della_domanda(domanda)
            if tipo == "casella":
                griglia.Add((0, 0))
                campo = wx.CheckBox(pagina, label=etichetta)
            else:
                griglia.Add(wx.StaticText(pagina, label=etichetta), 0, wx.ALIGN_CENTER_VERTICAL)
                if tipo == "testo":
                    campo = wx.TextCtrl(pagina)
                elif tipo == "anno":
                    # Gli anni dell'archivio, che metti_i_filtri riempie:
                    # frecce, pagine a passi di dieci, o le quattro cifre.
                    campo = wx.Choice(pagina, choices=[])
                    campo.Bind(wx.EVT_KEY_DOWN, self._tasto_dell_anno)
                    campo.Bind(wx.EVT_CHAR, self._cifra_dell_anno)
                elif tipo == "risultato":
                    campo = wx.Choice(pagina, choices=[testo for _codice, testo in risultati()])
                    campo.SetSelection(0)
                else:
                    campo = wx.SpinCtrl(pagina, min=0, max=tipo, initial=0)
            campo.SetName(etichetta)
            self.campi[chiave] = campo
            griglia.Add(campo, 1, wx.EXPAND)
        sizer.Add(griglia, 0, wx.EXPAND | wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_applica = wx.Button(pagina, label=_("Appli&ca i filtri"))
        self.pulsante_azzera = wx.Button(pagina, label=_("A&zzera i filtri"))
        riga.Add(self.pulsante_applica, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_azzera, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pagina.SetSizer(sizer)

    # I lavori lunghi: il caricamento, Classifica e Ripara.

    def _all_ingresso(self):
        """Prima gli appunti: il percorso di un file PGN o un testo PGN si
        caricano subito, altrimenti si sceglie il file. Chiesto da Gabriele
        il 22 novembre 2026, dopo il collaudo."""
        if not self:
            return
        sorgente = sorgente_negli_appunti()
        if sorgente is None:
            self.apri_file()
        else:
            self.carica(*sorgente)

    def _carica_se_aperta(self, tipo, sorgente):
        if self:
            self.carica(tipo, sorgente)

    def in_corso(self):
        """Vero mentre si carica, si classifica o si ripara."""
        return self._fermato is not None

    def apri_file(self):
        if self.in_corso():
            suona("no")
            return
        percorso = scegli_il_file(self)
        if percorso:
            self.carica("file", percorso)

    def dagli_appunti(self):
        """Come il terminale: un percorso, un indirizzo o il testo PGN."""
        if self.in_corso():
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

    def _lavora(self, testo, lavoro, finito):
        """lavoro(avanzamento, fermato) nel filo; finito(risultato) alla fine,
        nella finestra. L'avanzamento va nell'area dell'archivio e alla voce."""
        self._ferma_i_doppioni()
        fermato = self._fermato = threading.Event()
        self.schede.SetSelection(0)
        self.riepilogo.ChangeValue(testo)
        self.riepilogo.SetFocus()
        self._annuncia([testo])

        def nel_filo():
            try:
                risultato = lavoro(lambda riga: wx.CallAfter(self._avanzamento, riga), fermato.is_set)
            # Gli archivi PGN arrivano da fuori e possono essere malformati
            # in modi imprevedibili, e il disco puo' rifiutarsi: il filo non
            # deve morire in silenzio.
            except Exception as errore:  # noqa: BLE001
                risultato = (None, [str(errore)])
            wx.CallAfter(self._lavorato, finito, risultato)

        self.filo = threading.Thread(target=nel_filo, name="ricerca_pgn", daemon=True)
        self.filo.start()

    def _lavorato(self, finito, risultato):
        if not self:
            return
        self._fermato = None
        finito(risultato)

    def carica(self, tipo, sorgente):
        """Il caricamento nel filo; alla fine l'albero, o l'avviso di cosa
        non e' andato. Prima, le modifiche dell'archivio aperto: con Apri
        file o Dagli appunti sparivano in silenzio (R25)."""
        if not salva_all_uscita(self, self.ricerca, self._chiedi_conferma, self._avvisa, scarta=False):
            return
        self._lavora(_("Analisi del PGN in corso..."), lambda avanzamento, fermato: archivio_pgn.carica(tipo, sorgente, avanzamento, fermato), self._caricato)

    def _avanzamento(self, testo):
        if not self or not self.in_corso():
            return
        self.riepilogo.ChangeValue(testo)
        self._annuncia([testo])

    def _caricato(self, risultato):
        archivio, righe = risultato
        if archivio is None:
            self._mostra()
            suona("no")
            self._avvisa(self, "\n".join(righe))
            (self.albero if self.ricerca.archivio is not None else self.riepilogo).SetFocus()
            self._cerca_i_doppioni()
            return
        self.ricerca.archivio = archivio
        self.ricerca.righe = righe
        self.ricerca.filtri = {}
        self.ricerca.posizione = None
        self._mostra()
        self.albero.SetFocus()
        self._annuncia([righe[-1]])
        self._cerca_i_doppioni()

    def ferma(self):
        """Esc durante un lavoro: si tiene quello che e' fatto."""
        if self._fermato is not None:
            self._fermato.set()

    # I doppioni, in un filo, mentre si naviga.

    def _cerca_i_doppioni(self):
        archivio = self.ricerca.archivio
        if archivio is None or archivio.doppioni_cercati or self._fermati_i_doppioni is not None:
            return
        fermati = self._fermati_i_doppioni = threading.Event()
        self.avanzamento_doppioni = 0
        self._rinfresca_i_problemi()

        def nel_filo():
            try:
                doppioni = archivio_pgn.cerca_i_doppioni(archivio, lambda pct: wx.CallAfter(self._doppioni_al, archivio, pct), fermati.is_set)
            # Come nel caricamento: il filo non deve morire in silenzio.
            except Exception:  # noqa: BLE001
                doppioni = {}
            if doppioni is not None:
                wx.CallAfter(self._doppioni_trovati, archivio, doppioni)

        self.filo_doppioni = threading.Thread(target=nel_filo, name="doppioni", daemon=True)
        self.filo_doppioni.start()

    def _ferma_i_doppioni(self):
        if self._fermati_i_doppioni is not None:
            self._fermati_i_doppioni.set()
            self._fermati_i_doppioni = None

    def _doppioni_al(self, archivio, pct):
        if not self or archivio is not self.ricerca.archivio or self._fermati_i_doppioni is None:
            return
        self.avanzamento_doppioni = pct
        self._rinfresca_i_problemi()

    def _doppioni_trovati(self, archivio, doppioni):
        if not self or archivio is not self.ricerca.archivio or self._fermati_i_doppioni is None:
            return
        self._fermati_i_doppioni = None
        archivio_pgn.segna_i_doppioni(archivio, doppioni)
        self._rinfresca_i_problemi(finita=True)

    def _voce_dei_problemi(self):
        radice = self.albero.GetRootItem()
        if not radice.IsOk():
            return None
        return next((figlio for figlio in self.figli(radice) if self.albero.GetItemData(figlio).tipo == "problemi"), None)

    def _rinfresca_i_problemi(self, finita=False):
        """La voce Con errori dice a che punto e' la ricerca dei doppioni; alla
        fine, se il ramo e' gia' aperto, vi si aggiungono i doppioni."""
        voce = self._voce_dei_problemi()
        archivio = self.ricerca.archivio
        if voce is None or archivio is None:
            return
        nodo = self.albero.GetItemData(voce)
        nodo.indici = archivio.con_problemi(self.indici)
        avanzamento = None if archivio.doppioni_cercati else self.avanzamento_doppioni
        self.albero.SetItemText(voce, archivio_pgn.voce_dei_problemi(len(nodo.indici), avanzamento))
        self.albero.SetItemHasChildren(voce, bool(nodo.indici))
        if not finita or not nodo.popolato:
            return
        doppioni = archivio.problemi(nodo.indici).get("doppioni")
        if doppioni:
            nome = dict(archivio_pgn.tipi_dei_problemi())["doppioni"]
            figlio = self.albero.AppendItem(voce, archivio_pgn.voce_del_gruppo(nome, len(doppioni)), data=Nodo("doppioni", "problema", doppioni, problema="doppioni"))
            self.albero.SetItemHasChildren(figlio, True)

    # L'archivio, i filtri e l'albero.

    def _mostra(self):
        """L'area dell'archivio, i filtri e l'albero dallo stato."""
        archivio = self.ricerca.archivio
        righe = list(self.ricerca.righe)
        if archivio is not None:
            righe += archivio_pgn.righe_dell_archivio(archivio)
        self.riepilogo.ChangeValue("\n".join(righe) if righe else _("Nessun archivio caricato."))
        self.riepilogo.SetInsertionPoint(0)
        self.metti_i_filtri(self.ricerca.filtri)
        self.ricostruisci(self.ricerca.posizione)

    def metti_i_filtri(self, filtri):
        for chiave, campo in self.campi.items():
            valore = filtri.get(chiave)
            if chiave in ANNI:
                anni = self.anni()
                campo.Set(anni)
                if anni:
                    estremo = 0 if chiave == "year_from" else len(anni) - 1
                    campo.SetSelection(anni.index(str(valore)) if str(valore) in anni else estremo)
            elif isinstance(campo, wx.CheckBox):
                campo.SetValue(bool(valore))
            elif isinstance(campo, wx.TextCtrl):
                campo.ChangeValue(valore or "")
            elif isinstance(campo, wx.Choice):
                codici = [codice for codice, _testo in risultati()]
                campo.SetSelection(codici.index(valore) if valore in codici else 0)
            else:
                campo.SetValue(valore or 0)

    def anni(self):
        """Gli anni delle partite dell'archivio, dal piu' lontano, come testi."""
        archivio = self.ricerca.archivio
        if archivio is None:
            return []
        return [str(anno) for anno in sorted({info["Year"] for info in archivio.info if info.get("Year")})]

    def filtri_dei_campi(self):
        """I filtri dei campi, con le chiavi del terminale: un campo vuoto, a
        zero o spento non filtra, e gli anni nemmeno, quando stanno agli
        estremi, cosi' le partite senza data restano."""
        filtri = {}
        for chiave, campo in self.campi.items():
            if chiave in ANNI:
                scelto, ultimo = campo.GetSelection(), campo.GetCount() - 1
                if scelto >= 0 and scelto != (0 if chiave == "year_from" else ultimo):
                    filtri[chiave] = int(campo.GetString(scelto))
            elif isinstance(campo, wx.CheckBox):
                if campo.GetValue():
                    filtri[chiave] = True
            elif isinstance(campo, wx.TextCtrl):
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

    def _tasto_dell_anno(self, evento):
        """Pagina su e Pagina giu' saltano dieci anni dell'elenco."""
        campo = evento.GetEventObject()
        passo = {wx.WXK_PAGEUP: -10, wx.WXK_PAGEDOWN: 10, wx.WXK_NUMPAD_PAGEUP: -10, wx.WXK_NUMPAD_PAGEDOWN: 10}.get(evento.GetKeyCode())
        if passo is None or evento.HasAnyModifiers() or not campo.GetCount():
            evento.Skip()
            return
        self._scegli_l_anno(campo, max(0, min(campo.GetCount() - 1, campo.GetSelection() + passo)))

    def _cifra_dell_anno(self, evento):
        """Quattro cifre di fila scelgono l'anno, o il piu' vicino che c'e'."""
        codice = evento.GetUnicodeKey()
        carattere = chr(codice) if codice not in (wx.WXK_NONE, 0) else ""
        campo = evento.GetEventObject()
        if not carattere.isdigit() or not campo.GetCount():
            evento.Skip()
            return
        adesso = time.monotonic()
        if adesso - self._ultima_cifra > PAUSA_FRA_LE_CIFRE:
            self._cifre = ""
        self._ultima_cifra = adesso
        self._cifre += carattere
        if len(self._cifre) < 4:
            return
        voluto, self._cifre = int(self._cifre), ""
        anni = [int(campo.GetString(indice)) for indice in range(campo.GetCount())]
        self._scegli_l_anno(campo, min(range(len(anni)), key=lambda indice: abs(anni[indice] - voluto)))

    def _scegli_l_anno(self, campo, indice):
        campo.SetSelection(indice)
        self._annuncia([campo.GetString(indice)])

    def applica(self):
        if self.ricerca.archivio is None or self.in_corso():
            suona("no")
            return
        self.ricerca.filtri = self.filtri_dei_campi()
        self.ricerca.posizione = None
        self.ricostruisci()
        self._annuncia([self.etichetta_dell_albero.GetLabel()])

    def azzera(self):
        if self.ricerca.archivio is None or self.in_corso():
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
            if self.ricerca.filtri.get("cerca"):
                self.indici = archivio.con_il_testo(self.indici, self.ricerca.filtri["cerca"])
            totale = len(archivio)
            pct = len(self.indici) / totale * 100 if totale else 0.0
            testo = pgn_search.pulita(_("Partite corrispondenti: {n} di {tot} ({pct:.2f}%)").format(n=len(self.indici), tot=totale, pct=pct))
        self.etichetta_dell_albero.SetLabel(testo)
        self.albero.SetName(testo)
        if archivio is None:
            return
        radice = self.albero.AddRoot(archivio_pgn.voce_della_radice(archivio, self.indici, self.ricerca.filtri), data=Nodo(None, "radice", self.indici))
        self._popola(radice)
        self.albero.Expand(radice)
        voce = self._trova(radice, posizione) if posizione else radice
        self.albero.SelectItem(voce)
        self.albero.EnsureVisible(voce)

    def _aggiungi(self, voce, testo, nodo, con_figli=False):
        figlio = self.albero.AppendItem(voce, testo, data=nodo)
        if con_figli:
            self.albero.SetItemHasChildren(figlio, True)
        return figlio

    def _popola(self, voce):
        """I figli della voce, la prima volta che servono."""
        if not voce.IsOk():
            return
        nodo = self.albero.GetItemData(voce)
        if nodo is None or nodo.popolato or nodo.partita is not None:
            return
        nodo.popolato = True
        archivio = self.ricerca.archivio
        if nodo.tipo == "radice":
            nell_albero = [indice for indice in nodo.indici if archivio.nell_albero(indice)]
            self._aggiungi_le_mosse(voce, (), nell_albero, archivio.linee_di(nell_albero))
            self._aggiungi_i_rami_fuori(voce, nodo.indici)
        elif nodo.tipo == "mosse":
            self._aggiungi_le_mosse(voce, nodo.percorso, nodo.indici, nodo.linee)
        elif nodo.tipo == "non_classificate":
            senza_mosse, studio, senza_eco = archivio.non_classificate(nodo.indici)
            for chiave, nome, indici in (("senza_mosse", _("Senza mosse"), senza_mosse), ("studio", _("Da una posizione di studio"), studio)):
                if indici:
                    self._aggiungi(voce, archivio_pgn.voce_del_gruppo(nome, len(indici)), Nodo(chiave, "gruppo", indici), True)
            if senza_eco:
                figlio = Nodo("senza_eco", "mosse", senza_eco, linee=archivio.linee_di(senza_eco))
                self._aggiungi(voce, archivio_pgn.voce_del_gruppo(_("Senza codice ECO"), len(senza_eco)), figlio, True)
        elif nodo.tipo == "gruppo" and len(nodo.indici) > PARTITE_PER_BLOCCO:
            self._aggiungi_i_blocchi(voce, nodo)
        elif nodo.tipo == "gruppo" or (nodo.tipo == "blocco" and nodo.problema is None):
            for indice in nodo.indici:
                self._aggiungi(voce, archivio.partita(indice), Nodo(("partita", indice), "foglia", [indice], partita=indice))
        elif nodo.tipo == "problemi":
            trovati = archivio.problemi(nodo.indici)
            for tipo, nome in archivio_pgn.tipi_dei_problemi():
                if trovati.get(tipo):
                    self._aggiungi(voce, archivio_pgn.voce_del_gruppo(nome, len(trovati[tipo])), Nodo(tipo, "problema", trovati[tipo], problema=tipo), True)
        elif nodo.tipo == "problema" and len(nodo.indici) > PARTITE_PER_BLOCCO:
            self._aggiungi_i_blocchi(voce, nodo)
        elif nodo.tipo in ("problema", "blocco"):
            for indice in nodo.indici:
                foglia = Nodo(("partita", indice), "foglia", [indice], partita=indice, problema=nodo.problema)
                self._aggiungi(voce, archivio_pgn.voce_del_problema(archivio, indice, nodo.problema), foglia)

    def _aggiungi_i_blocchi(self, voce, nodo):
        """Un gruppo o un tipo di problema con troppe partite, a blocchi:
        prima c'era una voce per partita senza limite, e con un'intestazione
        mancante in tutte nascevano decine di migliaia di voci (R66). Il
        blocco tiene il problema del ramo, ma non e' il ramo: Ripara, da li'
        dentro, ripara ancora tutto il ramo."""
        for inizio in range(0, len(nodo.indici), PARTITE_PER_BLOCCO):
            indici = nodo.indici[inizio : inizio + PARTITE_PER_BLOCCO]
            testo = _("Partite da {primo} a {ultimo}").format(primo=inizio + 1, ultimo=inizio + len(indici))
            self._aggiungi(voce, testo, Nodo(("blocco", inizio), "blocco", indici, problema=nodo.problema), True)

    def _aggiungi_le_mosse(self, voce, percorso, indici, linee):
        """Le mosse dalla piu' giocata, poi le partite che finiscono li', e
        quelle che ci finiscono con una variante."""
        archivio = self.ricerca.archivio
        scacchiera = archivio_pgn.scacchiera_del_percorso(percorso)
        rami, finite, finite_varianti = archivio.figli(indici, linee, len(percorso))
        for giocata, partite, coppie, varianti in rami:
            testo = archivio_pgn.voce_del_ramo(archivio, scacchiera, giocata, partite, varianti, len(indici), self.ricerca.filtri)
            foglia = None
            if len(partite) == 1 and not varianti:
                foglia = partite[0]
            elif not partite and len(varianti) == 1:
                foglia = varianti[0][0]
            nodo = Nodo(archivio_pgn.codice(giocata), "mosse", partite, (*percorso, giocata), coppie, varianti, foglia)
            self._aggiungi(voce, testo, nodo, foglia is None)
        for indice in finite:
            self._aggiungi(voce, archivio.partita(indice), Nodo(("partita", indice), "foglia", [indice], percorso, partita=indice))
        for indice, linea in finite_varianti:
            nodo = Nodo(("partita", indice), "foglia", [], percorso, varianti=[(indice, linea)], partita=indice)
            self._aggiungi(voce, archivio_pgn.voce_della_variante_finita(archivio, indice), nodo)

    def _aggiungi_i_rami_fuori(self, voce, indici):
        """In fondo alla radice: Non classificate, se ce ne sono, e Con errori."""
        archivio = self.ricerca.archivio
        senza_mosse, studio, senza_eco = archivio.non_classificate(indici)
        fuori = sorted([*senza_mosse, *studio, *senza_eco])
        if fuori:
            self._aggiungi(voce, archivio_pgn.voce_del_gruppo(_("Non classificate"), len(fuori)), Nodo("non_classificate", "non_classificate", fuori), True)
        con_problemi = archivio.con_problemi(indici)
        avanzamento = None if archivio.doppioni_cercati else self.avanzamento_doppioni
        self._aggiungi(voce, archivio_pgn.voce_dei_problemi(len(con_problemi), avanzamento), Nodo("problemi", "problemi", con_problemi), bool(con_problemi))

    def figli(self, voce):
        figlio, biscotto = self.albero.GetFirstChild(voce)
        while figlio.IsOk():
            yield figlio
            figlio, biscotto = self.albero.GetNextChild(voce, biscotto)

    def antenati(self, voce):
        """La voce e quelle che la contengono, fino alla radice, coi nodi."""
        while voce.IsOk():
            yield voce, self.albero.GetItemData(voce)
            voce = self.albero.GetItemParent(voce)

    def chiavi(self, voce):
        """La posizione della voce: le chiavi dalla radice, per tornarci."""
        return tuple(reversed([nodo.chiave for _voce, nodo in self.antenati(voce) if nodo.tipo != "radice"]))

    def _trova(self, radice, posizione):
        """La voce di posizione, aprendo i rami lungo la strada; dove la
        strada non c'e' piu', l'ultima voce trovata."""
        voce = radice
        for chiave in posizione:
            self._popola(voce)
            prossima = next((figlio for figlio in self.figli(voce) if self.albero.GetItemData(figlio).chiave == chiave), None)
            if prossima is None:
                return voce
            voce = prossima
        return voce

    def selezionata(self):
        """La voce selezionata e il suo nodo, o (None, None)."""
        if self.ricerca.archivio is None or self.in_corso():
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
        """La vista della partita, nel suo PGN: vero se si va a Easyfish o
        all'analisi, e la finestra si chiude con l'uscita. La partita
        corretta a mano va nell'archivio aperto, e nel file all'uscita."""
        archivio = self.ricerca.archivio
        azione, nuovo = mostra_la_partita(self, archivio.testo_della_partita(indice).strip("\n"), self._chiedi_conferma, self._avvisa)
        if nuovo is not None:
            self.ricerca.archivio, righe = archivio_pgn.con_la_partita(archivio, indice, nuovo)
            voce, _nodo = self.selezionata()
            self.ricerca.posizione = self.chiavi(voce) if voce is not None else None
            self._mostra()
            self._annuncia([_("Partita salvata nell'archivio."), *righe])
            self._cerca_i_doppioni()
        if azione is None:
            return False
        voce, _nodo = self.selezionata()
        self.ricerca.posizione = self.chiavi(voce) if voce is not None else None
        self.uscita = (azione, indice)
        self._ferma_i_doppioni()
        finisci(self, wx.ID_OK)
        return True

    def inizio(self):
        if self.ricerca.archivio is None or self.in_corso():
            suona("no")
            return
        self.ricerca.posizione = None
        self.ricostruisci()
        self.schede.SetSelection(0)
        self.albero.SetFocus()

    def partite_del_ramo(self):
        """Il tasto 0 del terminale: le partite del ramo, con le mosse che
        seguono, quelle delle varianti in fondo; Invio mostra la partita, e
        chiudendola si torna all'elenco."""
        _voce, nodo = self.selezionata()
        if nodo is None or not nodo.tutte():
            suona("no")
            return
        archivio = self.ricerca.archivio
        scacchiera = archivio_pgn.scacchiera_del_percorso(nodo.percorso)
        profondita = len(nodo.percorso)
        partite = [(indice, None) for indice in nodo.indici] + list(nodo.varianti)
        titolo = wx.StripMenuCodes(_("Partite del &ramo"))
        # Le prime, con un tetto, e il titolo che lo dice (R138).
        if len(partite) > MASSIMO_DEL_RAMO:
            titolo = _("{titolo}, le prime {n} di {totale}").format(titolo=titolo, n=MASSIMO_DEL_RAMO, totale=len(partite))
            partite = partite[:MASSIMO_DEL_RAMO]
        with wx.BusyCursor():
            voci = [archivio.voce_della_lista(scacchiera, indice, profondita, numero, linea) for numero, (indice, linea) in enumerate(partite, 1)]
        scelta = 0
        while True:
            scelta = scegli(self, titolo, voci, scelta)
            if scelta is None or self.mostra_partita(partite[scelta][0]):
                return

    def salva(self):
        """Il tasto s del terminale: le partite della voce in un file, con
        varianti e commenti, com'erano."""
        _voce, nodo = self.selezionata()
        if nodo is None or not nodo.tutte():
            suona("no")
            return
        if not self.ricerca.filtri and nodo.tipo == "radice":
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
        partite = nodo.tutte()
        try:
            archivio_pgn.scrivi_pgn(percorso, self.ricerca.archivio, partite)
        except OSError as errore:
            suona("no")
            self._avvisa(self, pgn_search.pulita(_("Errore nel salvataggio: {e}").format(e=errore)))
            return
        self._annuncia([pgn_search.pulita(_("Salvate {n} partite in: {path}").format(n=len(partite), path=percorso))])

    def percorso(self):
        """La linea dalla prima mossa alla voce selezionata, alla voce."""
        _voce, nodo = self.selezionata()
        if nodo is None:
            suona("no")
            return
        self._annuncia([archivio_pgn.sequenza_del_percorso(nodo.percorso)])

    def classifica(self):
        """Dal ramo Non classificate: il codice ECO, l'apertura e la variante
        da eco.pgn alle partite senza codice ECO, dove le mosse lo dicono."""
        voce, nodo = self.selezionata()
        if nodo is None or not any(antenato.tipo == "non_classificate" for _voce, antenato in self.antenati(voce)):
            suona("no")
            return
        archivio = self.ricerca.archivio
        senza_mosse, studio, senza_eco = archivio.non_classificate(self.indici)
        if not senza_eco:
            suona("no")
            self._annuncia([_("Nessuna partita da classificare.")])
            return
        self.ricerca.posizione = self.chiavi(voce)

        def lavoro(avanzamento, fermato):
            aperture = archivio_pgn.carica_le_aperture()
            cambi = archivio_pgn.classifica(archivio, senza_eco, aperture, lambda pct: avanzamento(_("Classificazione: {pct}%").format(pct=pct)), fermato)
            righe = [_("Classificate {n} partite su {m}.").format(n=len(cambi), m=len(senza_eco))]
            if len(cambi) < len(senza_eco):
                righe.append(_("Le altre restano senza codice ECO: le loro mosse non si trovano in eco.pgn."))
            if senza_mosse or studio:
                righe.append(_("Le partite senza mosse o da una posizione di studio non si classificano."))
            # La rilettura non si ferma: applica quello che la
            # classificazione ha fatto, come dice il manuale. Prima riceveva
            # lo stesso segnale, e Esc durante la classificazione annullava
            # tutto (R116, scelta di Gabriele del 26 novembre 2026).
            nuovo, altre = archivio_pgn.applica_le_modifiche(
                archivio, cambi, avanzamento=lambda pct: avanzamento(_("Rilettura delle partite cambiate: {pct}%").format(pct=pct))
            )
            return nuovo, (righe if nuovo is not None else []) + altre

        self._lavora(_("Classificazione delle aperture in corso..."), lavoro, self._modificato)

    def ripara(self):
        """Dal ramo Con errori tutti i tipi, da un suo sottoramo quel tipo: le
        riparazioni possibili, e il resoconto."""
        voce, nodo = self.selezionata()
        if nodo is None:
            suona("no")
            return
        archivio = self.ricerca.archivio
        ramo = next((antenato for _voce, antenato in self.antenati(voce) if antenato.tipo in ("problema", "problemi")), None)
        if ramo is None or not ramo.indici:
            suona("no")
            return
        tipi = {ramo.problema} if ramo.tipo == "problema" else {tipo for tipo, _nome in archivio_pgn.tipi_dei_problemi()}
        if "doppioni" in tipi and not archivio.doppioni_cercati:
            suona("no")
            self._annuncia([_("La ricerca dei doppioni non e' finita: riprova fra poco.")])
            return
        indici = list(ramo.indici)
        # Prima di togliere partite dall'archivio, il loro numero e una
        # domanda (R24).
        doppie = sum(1 for indice in indici if "doppioni" in (archivio.schede[indice].problemi or {}))
        if "doppioni" in tipi and doppie:
            if not self._chiedi_conferma(self, _("Tolgo dall'archivio {n} partite doppie?").format(n=doppie)):
                tipi = tipi - {"doppioni"}
                if not tipi:
                    return
        self.ricerca.posizione = self.chiavi(voce)

        def lavoro(avanzamento, fermato):
            cambi, tolte, conti = archivio_pgn.ripara(archivio, indici, tipi)
            righe = archivio_pgn.righe_della_riparazione(conti)
            nuovo, altre = archivio_pgn.applica_le_modifiche(
                archivio, cambi, tolte, riscrivi_comunque=bool(conti["codifica"]),
                avanzamento=lambda pct: avanzamento(_("Rilettura delle partite cambiate: {pct}%").format(pct=pct)), fermato=fermato,
            )
            if nuovo is None:
                return nuovo, altre
            return nuovo, (righe or [_("Niente da riparare.")]) + altre

        self._lavora(_("Riparazione in corso..."), lavoro, self._modificato)

    def _modificato(self, risultato):
        """Dopo Classifica o Ripara: l'archivio nuovo, l'albero allo stesso
        punto, dove c'e' ancora, e il resoconto."""
        archivio, righe = risultato
        if archivio is None:
            suona("no")
        else:
            self.ricerca.archivio = archivio
        self._mostra()
        self.albero.SetFocus()
        self._avvisa(self, "\n".join(righe))
        self._cerca_i_doppioni()

    def vai_alla_sezione(self, numero):
        """Alt+1 l'archivio, Alt+2 l'albero, Alt+3 i pulsanti, Alt+4 il primo
        filtro."""
        if numero == 4:
            self.schede.SetSelection(1)
            next(iter(self.campi.values())).SetFocus()
            return
        self.schede.SetSelection(0)
        (self.riepilogo, self.albero, self.pulsante_inizio)[numero - 1].SetFocus()

    def _chiudi(self, _evento=None):
        """Chiudi, Esc fuori da un lavoro, o la X: un lavoro in corso si
        ferma, la ricerca dei doppioni anche, e la finestra si chiude senza
        uscita."""
        self.ferma()
        self._ferma_i_doppioni()
        if not salva_all_uscita(self, self.ricerca, self._chiedi_conferma, self._avvisa):
            return
        finisci(self, wx.ID_CANCEL)

    def _tasto(self, evento):
        codice = evento.GetKeyCode()
        if codice == wx.WXK_ESCAPE and not evento.HasAnyModifiers() and self.in_corso():
            self.ferma()
            return
        if evento.GetModifiers() == wx.MOD_ALT and ord("1") <= codice <= ord("4"):
            self.vai_alla_sezione(codice - ord("0"))
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
