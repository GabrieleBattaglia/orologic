# Orologic: la finestra, con l'area unica che fa da console.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra di Orologic, tappe T2, T3 e T4 della GUI (Piano della GUI.txt).

Il nucleo di Orologic gira in un filo suo, esattamente come nel terminale:
scrive con print e sys.stdout, legge con key, menu, enter_escape e dgt di
GBUtils e con lo strato. La finestra gli fa da terminale con una grande area
di testo, uscita e ingresso insieme.

  FacciaFinestra   la tastiera e lo schermo del nucleo: una sola coda di
                   tasti, letta dallo strato (kbhit, getwch), da key con
                   sorgente_dei_tasti di GBUtils e da input e getpass con
                   leggi_riga; e il testo scritto, consegnato alla finestra a
                   pezzi, ognuno con la sua causa.
  UscitaFinestra   lo stdout del nucleo.
  IngressoFinestra lo stdin del nucleo, per input e quindi per dgt.
  Terminale        il terminale imitato: la riga in corso e la colonna del
                   cursore, con i ritorni carrello, i backspace e gli a capo.
  Attesa           nella fila del testo, cio' che il nucleo aspetta adesso.
  Finestra         la plancia, l'area, i tasti e gli annunci con GBsintesi.

La plancia, l'albero accanto all'area (P1-P4 e A1-A4 del piano). menu di
GBUtils, con sorgente_delle_scelte, le consegna le sue voci invece di
scriverle, e aspetta la scelta; enter_escape le fa mostrare INVIO ed ESC, e
il tasto lo legge come sempre. E' un albero vero, che tiene plancia.py: le
voci del menu principale in cima, e le voci che aprono un altro menu sono
rami. Freccia destra, Invio o il clic aprono un ramo, e Orologic entra nel
suo menu; freccia sinistra lo chiude, e Orologic torna al menu sopra con la
voce punto, o con Esc dove il punto non c'e'. Le voci dei menu sopra restano
attorno al ramo aperto: Invio su una di loro fa tornare Orologic fin li' e
poi la sceglie. Il fuoco segue la domanda: alla plancia per un menu,
all'area per un testo, una mossa o un tasto, INVIO ed ESC compresi; F5 va
alla plancia, F6 all'area, e Tab e Shift+Tab passano dall'una all'altra.
Solo il primo menu, all'avvio, lascia il fuoco sull'area, all'inizio del
benvenuto. Ogni passaggio ha il suo suono, quelli di MeTeOra. Mentre la plancia
aspetta, cio' che si scrive nell'area non va al nucleo: il fuoco torna alla
plancia.

Gli annunci seguono le impostazioni di annunci.py: se si fanno, con quale
uscita e dove, e se interrompono quello in corso. Ctrl e virgola apre la
finestra delle impostazioni.

Le due forme dell'area. Fuori dal gioco scorre come un terminale. Durante una
partita, quando lo strato le consegna chi da' i dati, diventa il cruscotto di
cruscotto.py, che si riscrive da solo ogni secondo, col prompt in fondo: le
righe stampate diventano i messaggi, e restano anche nel registro della
console, che torna intero a fine partita. Nel cruscotto i rinfreschi lasciano
il cursore sulla stessa riga della stessa sezione e alla stessa colonna.

Le cause del testo. eco e' cio' che il nucleo scrive subito dopo un
carattere letto con getwch, cioe' l'eco del carattere nei cicli d'attesa, e
l'eco che leggi_riga fa da se': NVDA dice gia' i caratteri premuti, quindi
la riga in corso cambiata dall'eco non si annuncia. tasto e' cio' che segue
Invio, Esc o un tasto letto da key: e' la risposta a un tasto, e di partenza
interrompe la voce. None e' il testo che il nucleo scrive da se', per
l'orologio, per una mossa arrivata o da un altro filo, e di partenza si
accoda. Le righe chiuse si
annunciano sempre, tranne quella del prompt in cui si e' appena scritto.

Le lezioni della T0: riga e colonna si chiedono all'area, che non va a capo
da sola; frecce, pagine, Home e Fine passano all'area, per leggere liberi;
ogni altro tasto riporta il cursore al suo posto nella riga in corso.
"""

import getpass
import io
import os
import queue
import sys
import threading
import time
import traceback

import wx
from GBsintesi import AUTOMATICA, CON_IL_BRAILLE, Sintesi
from GBUtils import Acusticator, sorgente_dei_tasti, sorgente_delle_scelte

from . import (
    annunci,
    aspetto,
    componente_nvda,
    config,
    cruscotto,
    dialoghi,
    plancia,
    registro,
    richedit,
    strato,
    version,
)
from . import impostazioni as modulo_impostazioni
from .config import _

# L'eco e' solo cio' che il nucleo scrive entro questi secondi dal tasto: i
# cicli d'attesa guardano l'orologio prima di kbhit, e un rinfresco a tempo
# che cade al giro dopo un tasto non e' un eco.
ECO_MASSIMO = 0.015
# Le righe che l'area tiene, dalle impostazioni, coi loro limiti; oltre, le
# piu' vecchie se ne vanno a gruppi, di un quarto delle tenute.
CHIAVE_DELLE_RIGHE = "righe_dell_area"
# Ogni quanti millesimi la riga del cursore torna alla barra finche' non
# si preme un tasto, e quanto aspetta dopo un annuncio mandato alla barra.
RIPASSO_DEL_BRAILLE = 1000
RIPASSO_DOPO_UN_ANNUNCIO = 5000
RIGHE_PREDEFINITE = 200
RIGHE_MINIME = 20
RIGHE_MASSIME = 10000
# Quanti secondi il nucleo ha per chiudersi da solo, quando si chiude la finestra.
ATTESA_DELLA_CHIUSURA = 5.0
# Quante risposte la plancia da' da sola per arrivare a una voce: oltre,
# Orologic e' andato dove la plancia non se l'aspettava, e la strada si ferma.
PASSI_MASSIMI = 20
# I suoni del fuoco, gli stessi di MeTeOra per le stesse funzioni (P3).
SUONI_DEL_FUOCO = {"plancia": "spostamento_f5", "console": "spostamento_f6"}
# La larghezza che lo strato dichiara: pulisci_riga scrive tanti spazi, che
# l'area non mostra.
COLONNE = 300
# Il testo della voce della plancia che apre la scacchiera interattiva: non
# si scrive nel prompt.
APRI_LA_SCACCHIERA = "\x00scacchiera"


class ApriImpostazioni:
    """Nella fila del testo, la voce impostazioni del menu principale: la
    finestra apre le impostazioni e, quando si chiudono, accende chiuse, che
    il nucleo aspetta."""

    def __init__(self):
        self.chiuse = threading.Event()


class ApriOrologi(ApriImpostazioni):
    """Nella fila del testo, la voce orologi del menu principale: la
    finestra apre quella degli orologi, e il nucleo aspetta che si chiuda."""


class ApriPulizia(ApriImpostazioni):
    """Nella fila del testo, la pulizia che si apre da sola all'avvio, coi
    file vecchi: il nucleo aspetta che si chiuda."""


class ApriRicerca(ApriImpostazioni):
    """Nella fila del testo, la ricerca PGN del menu principale: la finestra
    apre la sua, con lo stato di ricerca, e scrive in uscita la partita
    scelta per Easyfish o per l'analisi; il nucleo aspetta che si chiuda."""

    def __init__(self, ricerca):
        super().__init__()
        self.ricerca = ricerca
        self.uscita = None


class ApriArchivi(ApriImpostazioni):
    """Nella fila del testo, PGN gestione archivi del menu principale: la
    finestra cerca pgn-extract e apre la sua; il nucleo aspetta che si
    chiuda."""


class ApriAperture(ApriImpostazioni):
    """Nella fila del testo, l'albero delle aperture del menu principale: la
    finestra apre il suo, con lo stato di aperture.py, e scrive in uscita la
    linea scelta per l'analisi o per Easyfish; il nucleo aspetta che si
    chiuda."""

    def __init__(self, stato):
        super().__init__()
        self.stato = stato
        self.uscita = None


class ApriLettura(ApriImpostazioni):
    """Nella fila del testo, le righe da leggere in una finestra, col loro
    titolo: le analisi e gli aiuti di Easyfish, che nel cruscotto non ci
    stanno; il nucleo aspetta che si chiuda."""

    def __init__(self, titolo, righe, verbosa=None, inizio=None):
        super().__init__()
        self.titolo = titolo
        self.righe = list(righe)
        self.verbosa = verbosa
        self.inizio = inizio


class ApriNavigatore(ApriImpostazioni):
    """Nella fila del testo, il navigatore della partita di Easyfish, aperto
    sul nodo; alla chiusura nodo e' quello scelto, o None, e modificata dice
    se la partita e' cambiata."""

    def __init__(self, game, nodo):
        super().__init__()
        self.game = game
        self.nodo = nodo
        self.scelto = None
        self.modificata = False


class ApriDisegni(ApriImpostazioni):
    """Nella fila del testo, la finestra dei disegni di Easyfish, coi nuovi
    sulla mossa nodo; alla chiusura modificata dice se la partita e'
    cambiata."""

    def __init__(self, game, nodo):
        super().__init__()
        self.game = game
        self.nodo = nodo
        self.modificata = False


class ApriEditor(ApriImpostazioni):
    """Nella fila del testo, l'editor della scacchiera di Easyfish sulla
    posizione fen; alla chiusura fen e' quella nuova, o None se si e'
    annullato."""

    def __init__(self, fen):
        super().__init__()
        self.fen = fen
        self.nuova = None


class CambioDiForma:
    """Nella fila del testo, il punto in cui l'area cambia forma: il
    fornitore dei dati del cruscotto, o None per tornare alla console. Sta
    nella stessa fila del testo perche' l'ordine non si perda: cio' che il
    nucleo scrive dopo l'inizio della partita va nel cruscotto."""

    def __init__(self, fornitore, comandi=None):
        self.fornitore = fornitore
        self.comandi = comandi


class Attesa:
    """Nella fila del testo, cio' che il nucleo aspetta da qui in poi:
    "menu", una scelta della plancia, con le voci; "sino", il tasto di una
    domanda di enter_escape, con la domanda; "area", un testo, una mossa o
    un tasto; None, niente, perche' lavora. Sta nella fila del testo perche'
    plancia e fuoco cambino dopo il testo scritto prima. gioco e' vero per il
    prompt delle mosse, che legge i tasti con kbhit e getwch, e per i
    prompt di Easyfish, con strato.prompt_di_gioco: li' lo spazio apre la
    scacchiera interattiva. tasto e' vero quando il nucleo legge un tasto
    solo, con key, come l'esploratore di Easyfish: ogni tasto e' una
    risposta intera. mosse e' vero solo per il prompt delle mosse vero e
    proprio, quello delle partite che legge i tasti con kbhit e getwch: li'
    il prompt riscritto dopo una mossa o un messaggio non si annuncia
    (Gabriele, 24 novembre 2026)."""

    def __init__(self, tipo, voci=(), prompt="", vuoto=None, sito=None, alla_radice=False, gioco=False, tasto=False, mosse=False):
        self.tipo = tipo
        self.voci = list(voci)
        self.prompt = prompt
        self.vuoto = vuoto
        self.sito = sito
        self.alla_radice = alla_radice
        self.gioco = gioco
        self.tasto = tasto
        self.mosse = mosse


def _sito_della_chiamata():
    """Il punto del programma che ha chiamato menu, fuori da GBUtils e da
    questo modulo, e se e' il menu principale di orologic.py."""
    quadro = sys._getframe(1)
    while quadro is not None:
        nome = os.path.basename(quadro.f_code.co_filename)
        if nome not in ("GBUtils.py", "finestra.py"):
            sito = (quadro.f_code.co_filename, quadro.f_code.co_name, quadro.f_lineno)
            return sito, nome == "orologic.py" and quadro.f_code.co_name == "Main"
        quadro = quadro.f_back
    return None, False


class FacciaFinestra:
    """La faccia dello strato per la finestra, la sorgente dei tasti di key
    e la sorgente delle scelte di menu ed enter_escape."""

    def __init__(self):
        self._tasti = queue.Queue()
        self._scelte = queue.Queue()
        # Cio' che il nucleo aspetta, come l'ultima Attesa messa in fila: il
        # tipo, e se e' il prompt delle mosse.
        self._attesa = None
        self._gioco = False
        self._tasto = False
        self._mosse = False
        # Vero dentro strato.prompt_di_gioco: le domande di dgt e key valgono
        # come il prompt delle mosse.
        self._di_gioco = False
        # L'evento che interrompe la scelta della plancia, se c'e'.
        self._interruttore = None
        self._lucchetto = threading.Lock()
        self._pezzi = []
        self._causa = None
        self._quando = 0.0
        self._chiusura = threading.Event()
        # Dentro strato.rinfresco: quello che si scrive e' il rinfresco
        # periodico del prompt, che la finestra non annuncia.
        self._rinfresco = False
        self.avvisa = None

    # Il lato del nucleo.

    def _controlla_chiusura(self):
        if self._chiusura.is_set():
            raise KeyboardInterrupt

    def _prendi(self, attesa=None):
        """Il prossimo tasto, o None se l'attesa scade. Con la finestra che
        si chiude solleva KeyboardInterrupt, come Ctrl+C nel terminale."""
        scadenza = None if attesa is None else time.monotonic() + max(0.0, attesa)
        while True:
            self._controlla_chiusura()
            passo = 0.05 if scadenza is None else min(0.05, max(0.0, scadenza - time.monotonic()))
            try:
                return self._tasti.get(timeout=passo)
            except queue.Empty:
                if scadenza is not None and time.monotonic() >= scadenza:
                    return None

    def _aspetta(self, attesa):
        """Mette in fila l'Attesa, se cambia cio' che il nucleo aspetta."""
        if (
            attesa.tipo in ("menu", "sino")
            or attesa.tipo != self._attesa
            or attesa.gioco != self._gioco
            or attesa.tasto != self._tasto
            or attesa.mosse != self._mosse
        ):
            self._attesa = attesa.tipo
            self._gioco = attesa.gioco
            self._tasto = attesa.tasto
            self._mosse = attesa.mosse
            self._metti(attesa)

    def di_gioco(self, valore):
        """strato.prompt_di_gioco: restituisce il valore di prima."""
        precedente = self._di_gioco
        self._di_gioco = valore
        return precedente

    def kbhit(self):
        self._controlla_chiusura()
        self._causa = None
        self._aspetta(Attesa("area", gioco=True, mosse=True))
        return not self._tasti.empty()

    def getwch(self):
        self._aspetta(Attesa("area", gioco=True, mosse=True))
        tasto = self._prendi()
        self._causa = "tasto" if tasto in ("\r", "\x1b") else "eco"
        self._quando = time.monotonic()
        return tasto

    def tasto_per_key(self, attesa):
        """La sorgente di key: key non fa l'eco, quindi quello che segue e'
        sempre una risposta. Per una domanda di enter_escape la plancia
        tiene il suo Si' e No finche' arriva il tasto."""
        if self._attesa != "sino":
            self._aspetta(Attesa("area", gioco=self._di_gioco, tasto=True))
        tasto = self._prendi(attesa)
        if tasto is not None:
            self._causa = "tasto"
            self._quando = time.monotonic()
        if self._attesa == "sino":
            self._aspetta(Attesa(None))
        return tasto

    def scelte_per_menu(self, tipo, voci, prompt, vuoto):
        """La sorgente delle scelte di GBUtils. Per enter_escape mette in
        fila la domanda, e il tasto lo legge key; per menu mette in fila le
        voci e aspetta la scelta della plancia, che restituisce."""
        if tipo == "enter_escape":
            self._aspetta(Attesa("sino", prompt=prompt))
            return None
        sito, alla_radice = _sito_della_chiamata()
        # I tasti scritti prima non devono finire nella domanda dopo.
        self.svuota_tastiera()
        while True:
            try:
                self._scelte.get_nowait()
            except queue.Empty:
                break
        self._aspetta(Attesa("menu", voci, prompt, vuoto, sito, alla_radice))
        while True:
            self._controlla_chiusura()
            if self._interruttore is not None and self._interruttore.is_set():
                self._aspetta(Attesa(None))
                return strato.SCELTA_INTERROTTA
            try:
                scelta = self._scelte.get(timeout=0.05)
            except queue.Empty:
                continue
            self._aspetta(Attesa(None))
            return scelta

    def con_la_plancia(self):
        return True

    def impostazioni(self):
        """La voce impostazioni del menu principale: la finestra apre le
        impostazioni, e il nucleo aspetta che si chiudano."""
        self._apri_e_aspetta(ApriImpostazioni())

    def orologi(self):
        """La voce orologi del menu principale: la finestra apre quella
        degli orologi, e il nucleo aspetta che si chiuda."""
        self._apri_e_aspetta(ApriOrologi())

    def pulizia(self):
        """All'avvio, coi file vecchi: la finestra apre la pulizia, e il
        nucleo aspetta che si chiuda."""
        self._apri_e_aspetta(ApriPulizia())

    def ricerca_pgn(self, ricerca):
        """La voce ricerca del menu principale: la finestra apre quella
        della ricerca PGN, e il nucleo aspetta che si chiuda."""
        richiesta = ApriRicerca(ricerca)
        self._apri_e_aspetta(richiesta)
        return richiesta.uscita

    def archivi_pgn(self):
        """La voce PGN gestione archivi del menu principale: la finestra
        apre la sua, con pgn-extract, e il nucleo aspetta che si chiuda."""
        self._apri_e_aspetta(ApriArchivi())

    def albero_aperture(self, stato):
        """La voce aperture del menu principale: la finestra apre l'albero
        delle aperture, e il nucleo aspetta che si chiuda."""
        richiesta = ApriAperture(stato)
        self._apri_e_aspetta(richiesta)
        return richiesta.uscita

    def da_leggere(self, titolo, righe, verbosa=None, inizio=None):
        """Le analisi e gli aiuti di Easyfish in una finestra da leggere; il
        nucleo aspetta che si chiuda."""
        self._apri_e_aspetta(ApriLettura(titolo, righe, verbosa, inizio))

    def navigatore(self, game, nodo):
        """Il navigatore della partita di Easyfish: (nodo scelto o None,
        vero se la partita e' cambiata)."""
        richiesta = ApriNavigatore(game, nodo)
        self._apri_e_aspetta(richiesta)
        return richiesta.scelto, richiesta.modificata

    def disegni(self, game, nodo):
        """La finestra dei disegni di Easyfish: vero se la partita e'
        cambiata."""
        richiesta = ApriDisegni(game, nodo)
        self._apri_e_aspetta(richiesta)
        return richiesta.modificata

    def editor_della_scacchiera(self, fen):
        """L'editor della scacchiera di Easyfish: il FEN nuovo, o None."""
        richiesta = ApriEditor(fen)
        self._apri_e_aspetta(richiesta)
        return richiesta.nuova

    def _apri_e_aspetta(self, richiesta):
        self._aspetta(Attesa(None))
        self._metti(richiesta)
        while not richiesta.chiuse.wait(0.05):
            self._controlla_chiusura()

    def interrompi_la_scelta_con(self, evento):
        precedente = self._interruttore
        self._interruttore = evento
        return precedente

    def leggi_riga(self, eco=True):
        """Una riga, come la console la da' a input: i caratteri con l'eco
        se eco e' vero, Backspace cancella, Esc svuota la riga, Invio la
        consegna."""
        self._aspetta(Attesa("area", gioco=self._di_gioco))
        scritti = []
        while True:
            tasto = self._prendi()
            if tasto == "\r":
                self.scrivi("\n", "tasto")
                self._causa = "tasto"
                self._quando = time.monotonic()
                return "".join(scritti)
            if tasto == "\x08":
                if scritti:
                    scritti.pop()
                    if eco:
                        self.scrivi("\b \b", "eco")
            elif tasto == "\x1b":
                if scritti and eco:
                    self.scrivi("\b \b" * len(scritti), "eco")
                scritti.clear()
            elif tasto.isprintable():
                scritti.append(tasto)
                if eco:
                    self.scrivi(tasto, "eco")

    def svuota_tastiera(self):
        while True:
            try:
                self._tasti.get_nowait()
            except queue.Empty:
                return

    def larghezza(self):
        return COLONNE

    def cruscotto(self, fornitore, comandi=None):
        self._metti(CambioDiForma(fornitore, comandi))

    def rinfresco(self, acceso):
        """strato.rinfresco: le scritture di adesso sono un rinfresco."""
        self._rinfresco = acceso

    def scrivi(self, testo, causa=None):
        if self._rinfresco:
            causa = "rinfresco"
        if causa is None:
            causa = self._causa
            if causa == "eco" and time.monotonic() - self._quando > ECO_MASSIMO:
                causa = None
        self._metti(testo, causa)

    def _metti(self, pezzo, causa=None):
        with self._lucchetto:
            primo = not self._pezzi
            self._pezzi.append((pezzo, causa))
        if primo and self.avvisa is not None:
            self.avvisa()

    # Il lato della finestra.

    def premi(self, tasto):
        self._tasti.put(tasto)

    def scegli(self, valore):
        """La scelta della plancia per il menu che aspetta: la chiave, o
        None come Esc."""
        self._scelte.put(valore)

    def prendi_il_testo(self):
        with self._lucchetto:
            pezzi, self._pezzi = self._pezzi, []
        return pezzi

    def chiudi(self):
        self._chiusura.set()


class UscitaFinestra(io.TextIOBase):
    """Lo stdout del nucleo: tutto quello che scrive va alla faccia."""

    def __init__(self, faccia):
        super().__init__()
        self._faccia = faccia

    def writable(self):
        return True

    def write(self, testo):
        if testo:
            self._faccia.scrivi(testo)
        return len(testo)

    def flush(self):
        pass

    def isatty(self):
        return False

    @property
    def encoding(self):
        return "utf-8"


class IngressoFinestra(io.TextIOBase):
    """Lo stdin del nucleo: input lo legge una riga alla volta."""

    def __init__(self, faccia):
        super().__init__()
        self._faccia = faccia

    def readable(self):
        return True

    def readline(self, size=-1):
        return self._faccia.leggi_riga() + "\n"

    def isatty(self):
        return False

    @property
    def encoding(self):
        return "utf-8"


class Terminale:
    """Il terminale imitato: le righe si chiudono con l'a capo, il ritorno
    carrello riporta il cursore a inizio riga, il backspace lo sposta indietro
    di uno, ogni altro carattere scrive sopra o in fondo."""

    def __init__(self):
        self.riga = []
        self.colonna = 0

    def applica(self, testo):
        """Applica il testo e restituisce le righe chiuse, senza spazi in fondo."""
        chiuse = []
        for carattere in testo:
            if carattere == "\n":
                chiuse.append(self.visibile().rstrip())
                self.riga, self.colonna = [], 0
            elif carattere == "\r":
                self.colonna = 0
            elif carattere == "\b":
                self.colonna = max(0, self.colonna - 1)
            elif carattere == "\t" or carattere >= " ":
                if self.colonna < len(self.riga):
                    self.riga[self.colonna] = carattere
                else:
                    self.riga.extend(" " * (self.colonna - len(self.riga)))
                    self.riga.append(carattere)
                self.colonna += 1
        return chiuse

    def visibile(self):
        """La riga in corso, senza gli spazi in fondo che stanno oltre il cursore."""
        testo = "".join(self.riga)
        return testo[: max(self.colonna, len(testo.rstrip()))]


def righe_da_tenere():
    """Le righe che l'area principale conserva, dalle impostazioni."""
    from . import storage

    try:
        valore = int(storage.LoadDB().get(CHIAVE_DELLE_RIGHE, RIGHE_PREDEFINITE))
    except (TypeError, ValueError):
        valore = RIGHE_PREDEFINITE
    return min(max(valore, RIGHE_MINIME), RIGHE_MASSIME)


def _parte_nuova(riga, detta):
    """Cio' che di una riga va annunciato, sapendo che detta e' gia' stata
    sentita: niente se e' la stessa, la sola coda se la riga la continua,
    come dice NVDA nel terminale, altrimenti la riga intera."""
    riga, detta = riga.rstrip(), detta.rstrip()
    if not riga.strip() or riga == detta:
        return ""
    if detta.strip() and riga.startswith(detta):
        return riga[len(detta):].strip()
    return riga.strip()


class Finestra(wx.Frame):
    def __init__(self, faccia):
        super().__init__(None, title=_("Orologic {versione}").format(versione=version.VERSION))
        self.faccia = faccia
        pannello = wx.Panel(self)
        # L'ordine di creazione e' quello di Tab: la plancia, poi l'area.
        self.plancia = wx.TreeCtrl(pannello, style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_SINGLE)
        self.plancia.SetName(_("Plancia"))
        self.area = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL | wx.TE_DONTWRAP)
        self.area.Bind(wx.EVT_WINDOW_DESTROY, self._area_distrutta)
        self.area.SetName(_("Console"))
        # Il segno della console per il componente di NVDA per Orologic.
        componente_nvda.segna(self.area, componente_nvda.CONSOLE)
        # Lo spazio orizzontale: la plancia a sinistra, l'area piu' larga.
        dimensionatore = wx.BoxSizer(wx.HORIZONTAL)
        dimensionatore.Add(self.plancia, 1, wx.EXPAND)
        dimensionatore.Add(self.area, 3, wx.EXPAND)
        pannello.SetSizer(dimensionatore)
        # Colori e dimensioni dei caratteri, se sono stati cambiati; nell'area
        # wx mette lo stile anche nel testo che arriva dopo.
        aspetto.applica_alla_finestra(self)
        # La plancia: i menu aperti, cio' che il nucleo aspetta, e i dati di
        # ogni elemento dell'albero.
        self.albero = plancia.Albero()
        self.attesa = Attesa(None)
        # Vero mentre sono aperte le impostazioni chieste dal nucleo, con la
        # voce impostazioni del menu principale: il nucleo e' fermo.
        self.impostazioni_del_nucleo = False
        self.voci_della_plancia = {}
        # La strada verso una voce: (percorso, voce finale), i passi fatti, e
        # la voce da selezionare all'arrivo, come (livello, chiave).
        self.meta = None
        self.passi = 0
        self.da_selezionare = None
        # Dopo una risposta della strada, come deve cambiare la pila:
        # ("avanti", livelli attesi) o ("indietro", livelli al massimo).
        self.atteso = None
        self.ricostruendo = False
        # L'ultima voce scelta in ogni menu, per sito: tornando al menu e'
        # di nuovo selezionata.
        self.ultime_scelte = {}
        # I comandi della modalita' in gioco, per la plancia, e l'ultimo
        # scelto, come etichette dalla cima, che resta selezionato.
        self.comandi = None
        self.ultimo_comando = None
        # Dove sta il fuoco, e dove lo vuole la domanda: all'attivazione
        # della finestra torna li'.
        self.fuoco = "console"
        self.fuoco_voluto = "console"
        # Il primo menu della sessione non porta via il fuoco dall'area.
        self.primo_menu = True
        # Dove comincia cio' che stampa la foglia del menu appena scelta,
        # come (riga, colonna) dell'area; None se l'ultima scelta non e' una
        # foglia.
        self.inizio_della_foglia = None
        self.terminale = Terminale()
        # Le righe chiuse della console; la riga in corso viene dopo. Durante
        # il cruscotto continuano a raccogliersi, e tornano a fine partita.
        self.righe = []
        # Quante l'area ne conserva: le impostazioni lo cambiano.
        self.righe_tenute = righe_da_tenere()
        # Il cruscotto: chi da' i dati, i messaggi della partita, le righe
        # mostrate come coppie (sezione, testo), l'orologio che lo rinfresca.
        self.fornitore = None
        self.messaggi = []
        self.mostrate = []
        self.orologio = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _evento: self._ridisegna(), self.orologio)
        # Il braille del testo che cambia: NVDA rilegge l'area solo dopo un
        # tasto, quindi la riga sotto il cursore, se e' cambiata dopo
        # l'ultimo tasto, va alla barra come messaggio, rimandato ogni secondo
        # finche' non se ne preme uno (Gabriele, 23 novembre 2026, prova del
        # braille). Il documento del RichEdit cambia il testo senza toccare il
        # cursore: None finche' non serve, False se non c'e'.
        self.braille_indietro = False
        self.ripasso_del_braille = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _evento: self._ripassa_il_braille(), self.ripasso_del_braille)
        self.documento_dell_area = None
        # La riga in corso come l'utente l'ha gia' sentita o scritta.
        self.detta = ""
        self.programmato = False
        self.sintesi = Sintesi()
        self.annunci = annunci.carica()
        # Le impostazioni: chi scrive le righe e le cambia, e l'elenco aperto.
        self.gestore = modulo_impostazioni.Impostazioni(self)
        self.dialogo_impostazioni = None
        self.dialogo_orologi = None
        self.dialogo_pulizia = None
        self.dialogo_ricerca = None
        self.dialogo_archivi = None
        self.dialogo_aperture = None
        # La scacchiera interattiva: aperta, o da riaprire quando il nucleo
        # torna al prompt delle mosse dopo una domanda; e i caratteri scritti
        # nella riga del prompt, perche' lo spazio la apra solo a riga vuota.
        self.dialogo_scacchiera = None
        self.scacchiera_da_riaprire = False
        self.digitati = 0
        self.nucleo = None
        self.chiudendo = False
        # Finito il nucleo la finestra si chiude; le prove la tengono aperta
        # per leggerla.
        self.chiudi_alla_fine = True
        self.area.Bind(wx.EVT_CHAR, self._carattere)
        self.area.Bind(wx.EVT_KEY_DOWN, self._tasto_giu)
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto_della_finestra)
        self.plancia.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._voce_attivata)
        self.plancia.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._si_apre)
        self.plancia.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self._si_chiude)
        self.Bind(wx.EVT_ACTIVATE, self._attivata)
        self.plancia.Bind(wx.EVT_KEY_DOWN, self._tasto_della_plancia)
        self.plancia.Bind(wx.EVT_SET_FOCUS, lambda evento: self._fuoco_a("plancia", evento))
        self.area.Bind(wx.EVT_SET_FOCUS, lambda evento: self._fuoco_a("console", evento))
        self.Bind(wx.EVT_CLOSE, self._chiudi)
        faccia.avvisa = self._avvisa
        self.Maximize()
        self.area.SetFocus()

    # I tasti.

    def _riga_del_prompt(self):
        """La riga in corso, l'ultima dell'area, nelle due forme."""
        if self.fornitore is not None and self.mostrate:
            return len(self.mostrate) - 1
        return len(self.righe)

    def _riga_e_colonna(self):
        trovata, colonna, riga = self.area.PositionToXY(self.area.GetInsertionPoint())
        if not trovata:
            return self._riga_del_prompt(), 0
        return min(riga, self._riga_del_prompt()), colonna

    def _vai(self, riga, colonna):
        lunghezza = self.area.GetLineLength(riga)
        posizione = self.area.XYToPosition(max(0, min(colonna, lunghezza)), riga)
        # Dov'e' gia', il cursore non si tocca: ogni spostamento riporta la
        # barra di NVDA sul cursore.
        if posizione != self.area.GetInsertionPoint():
            self.area.SetInsertionPoint(posizione)

    # Il testo che cambia e il braille.

    def _documento(self):
        """Il documento del RichEdit, ITextDocument, che cambia il testo
        senza toccare il cursore; None se non c'e', per esempio senza
        pywin32: allora si cambia con Replace."""
        if self.documento_dell_area is None:
            self.documento_dell_area = richedit.documento(self.area) or False
        return self.documento_dell_area or None

    def _area_distrutta(self, evento):
        """L'area si chiude: il documento del RichEdit si lascia prima, o il
        suo rilascio cadrebbe su un oggetto gia' distrutto e la memoria si
        corromperebbe, come nelle prove del 23 novembre 2026."""
        evento.Skip()
        self.documento_dell_area = False
        # E il ripasso del braille si ferma: un timer acceso che scatta su
        # una finestra distrutta la fa cadere.
        self.ripasso_del_braille.Stop()
        componente_nvda.togli_il_segno(self.area)

    def _sostituisci(self, inizio, fine, testo):
        """Il testo dell'area da inizio a fine prende il posto: col documento
        del RichEdit il cursore resta dov'era nel testo, e se si legge
        altrove NVDA non riporta la barra sul cursore. Vero se il cursore non
        e' stato toccato; senza documento si usa Replace, e lo si tocca."""
        documento = self._documento()
        riuscito = richedit.sostituisci(documento, self.area, inizio, fine, testo)
        if documento is not None and not riuscito:
            # Un documento che non risponde piu': da qui in poi Replace.
            self.documento_dell_area = False
        return riuscito

    def _riga_sotto_il_cursore(self):
        _trovata, _colonna, riga = self.area.PositionToXY(self.area.GetInsertionPoint())
        return self.area.GetLineText(riga)

    def _braille_dopo_il_cambio(self, prima):
        """Dopo un cambio del testo NVDA riceve valueChange: col componente
        di NVDA per Orologic la barra rilegge da se' la riga, e il display
        resta sulla pagina che si legge. Senza, se la riga sotto il cursore
        non e' piu' quella di prima, e il fuoco e' sull'area, la riga va alla
        barra, e il ripasso la rimanda finche' non si preme un tasto."""
        componente_nvda.avvisa(self.area)
        if componente_nvda.attivo(self.area):
            self._braille_letto()
            return
        if self._riga_sotto_il_cursore() == prima or wx.Window.FindFocus() is not self.area:
            return
        self.braille_indietro = True
        self._ripassa_il_braille()
        if not self.ripasso_del_braille.IsRunning():
            self.ripasso_del_braille.Start(RIPASSO_DEL_BRAILLE)

    def _ripassa_il_braille(self):
        """La riga sotto il cursore alla barra, come messaggio, finche' NVDA
        non l'ha riletta da se' dopo un tasto; col fuoco altrove, o con la
        scacchiera aperta, il ripasso si ferma."""
        if (
            not self
            or not self.braille_indietro
            or wx.Window.FindFocus() is not self.area
            or self.dialogo_scacchiera is not None
            or componente_nvda.attivo(self.area)
        ):
            self._braille_letto()
            return
        riga = self._riga_sotto_il_cursore()
        if riga.strip():
            self.al_braille(riga)
        if self.ripasso_del_braille.GetInterval() != RIPASSO_DEL_BRAILLE:
            self.ripasso_del_braille.Start(RIPASSO_DEL_BRAILLE)

    def _braille_letto(self):
        """Un tasto: NVDA rilegge l'area da se', il ripasso si ferma."""
        self.braille_indietro = False
        if self.ripasso_del_braille.IsRunning():
            self.ripasso_del_braille.Stop()

    def al_braille(self, testo):
        """Un messaggio solo alla barra, con lo screen reader degli annunci se
        ha il braille, altrimenti col primo attivo, anche con gli annunci
        spenti; le prove lo sostituiscono."""
        uscita = self.annunci["uscita"] if self.annunci["uscita"] in CON_IL_BRAILLE else AUTOMATICA
        self.sintesi.dici(testo, uscita, "braille")

    def _al_cursore(self):
        self._vai(self._riga_del_prompt(), self.terminale.colonna)

    def _manda(self, tasto):
        if self.attesa.tipo == "menu":
            # Il nucleo aspetta la plancia, non l'area.
            self.vai_alla_plancia()
            return
        if self._riga_e_colonna()[0] != self._riga_del_prompt():
            self._al_cursore()
        self.premi_nel_prompt(tasto)

    def premi_nel_prompt(self, tasto):
        """Un tasto al nucleo, come digitato, tenendo il conto dei caratteri
        della riga: Invio ed Esc la chiudono, Backspace ne toglie uno. Dove
        il nucleo legge un tasto solo, ogni tasto e' una risposta intera, e la
        riga resta vuota."""
        if tasto in ("\r", "\x1b") or self.attesa.tasto:
            self.digitati = 0
        elif tasto == "\x08":
            self.digitati = max(0, self.digitati - 1)
        elif tasto.isprintable():
            self.digitati += 1
        self.faccia.premi(tasto)

    def _carattere(self, evento):
        codice = evento.GetUnicodeKey()
        if codice == wx.WXK_SPACE and not evento.HasAnyModifiers() and self.si_apre_la_scacchiera():
            self.apri_la_scacchiera()
        elif codice == wx.WXK_RETURN:
            self._manda("\r")
        elif codice == wx.WXK_BACK:
            self._manda("\x08")
        elif codice != wx.WXK_NONE and codice >= 32 and not (evento.ControlDown() and not evento.AltDown()):
            self._manda(chr(codice))
        else:
            # Frecce, pagine, Home, Fine e il resto: all'area, per leggere.
            evento.Skip()

    def _tasto_giu(self, evento):
        codice = evento.GetKeyCode()
        # Esc nell'area non diventa mai un carattere: arrivano il gancio
        # della finestra e la pressione, ma EVT_CHAR no, e il nucleo non lo
        # riceveva in nessuna domanda (diario dei tasti, Gabriele, memoboard,
        # 23 novembre 2026). Si prende qui, alla pressione.
        if codice == wx.WXK_ESCAPE and not evento.HasAnyModifiers():
            self._manda("\x1b")
            return
        ctrl, shift = evento.ControlDown(), evento.ShiftDown()
        if (ctrl and codice == ord("V")) or (shift and codice == wx.WXK_INSERT):
            self._incolla()
            return
        # Tagliare, cancellare, annullare e ripetere cambierebbero l'area
        # alle spalle del nucleo.
        if codice in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) or (ctrl and codice in (ord("X"), ord("Z"), ord("Y"))):
            return
        evento.Skip()

    def _tasto_della_finestra(self, evento):
        """I tasti di tutta la finestra, plancia e area: Ctrl e virgola le
        impostazioni, come nelle altre applicazioni (Gabriele, S1), F5 la
        plancia, F6 l'area. Ogni tasto fa rileggere l'area a NVDA: il
        braille non va piu' rimandato."""
        self._braille_letto()
        codice = evento.GetKeyCode()
        if evento.GetModifiers() == wx.MOD_CONTROL and codice == ord(","):
            self.impostazioni(suono=True)
            return
        if not evento.HasAnyModifiers():
            if codice == wx.WXK_F5:
                self.vai_alla_plancia()
                return
            if codice == wx.WXK_F6:
                self.vai_all_area()
                return
        evento.Skip()

    def _incolla(self):
        """Gli appunti vanno al nucleo come tasti, fino al primo a capo."""
        if not wx.TheClipboard.Open():
            return
        try:
            dati = wx.TextDataObject()
            if wx.TheClipboard.GetData(dati) and dati.GetText():
                for carattere in dati.GetText().splitlines()[0]:
                    if carattere.isprintable():
                        self._manda(carattere)
        finally:
            wx.TheClipboard.Close()

    # Il testo.

    def _avvisa(self):
        wx.CallAfter(self._programma)

    def _programma(self):
        if not self.programmato:
            self.programmato = True
            wx.CallLater(15, self._applica)

    def _applica(self):
        """Il testo del nucleo nell'area, e l'annuncio di quello nuovo."""
        self.programmato = False
        pezzi = self.faccia.prendi_il_testo()
        if not pezzi or not self:
            return
        chiuse = []
        # Le righe chiuse che sono messaggi: non la riga del prompt in cui si
        # e' appena scritto, che nel cruscotto sta gia' fra le ultime mosse.
        messaggi = []
        da_dire = []
        dal_tasto = False
        ultima_causa = None
        # Il nucleo era gia' al prompt delle mosse, e se ci resta, senza
        # un'attesa nuova in mezzo, la riga in corso e' il prompt riscritto.
        al_prompt_delle_mosse = self._al_prompt_delle_mosse()
        attesa_cambiata = False
        for testo, causa in pezzi:
            if isinstance(testo, CambioDiForma):
                # Il testo arrivato prima va nella forma di prima.
                self._mostra_nella_forma(chiuse, messaggi)
                chiuse, messaggi = [], []
                self._cambia_forma(testo.fornitore, testo.comandi)
                continue
            if isinstance(testo, ApriOrologi):
                wx.CallAfter(self._orologi_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriPulizia):
                wx.CallAfter(self._pulizia_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriRicerca):
                wx.CallAfter(self._ricerca_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriArchivi):
                wx.CallAfter(self._archivi_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriAperture):
                wx.CallAfter(self._aperture_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriLettura):
                wx.CallAfter(self._lettura_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriNavigatore):
                wx.CallAfter(self._navigatore_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriEditor):
                wx.CallAfter(self._editor_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriDisegni):
                wx.CallAfter(self._disegni_dal_nucleo, testo)
                continue
            if isinstance(testo, ApriImpostazioni):
                wx.CallAfter(self._impostazioni_dal_nucleo, testo)
                continue
            if isinstance(testo, Attesa):
                self._mostra_nella_forma(chiuse, messaggi)
                chiuse, messaggi = [], []
                self._cambia_attesa(testo)
                attesa_cambiata = True
                continue
            ultima_causa = causa
            if causa == "tasto":
                dal_tasto = True
            # Il rinfresco periodico del prompt si scrive, ma non si dice e
            # non e' un messaggio.
            rinfresco = causa == "rinfresco"
            for riga in self.terminale.applica(testo):
                chiuse.append(riga)
                if not rinfresco and riga.strip() and riga.rstrip() != self.detta.rstrip():
                    messaggi.append(riga)
                nuovo = _parte_nuova(riga, self.detta)
                if nuovo and not rinfresco:
                    da_dire.append(nuovo)
                self.detta = ""
            # L'eco si aggiunge a cio' che e' gia' stato sentito pezzo per
            # pezzo: con i tasti rapidi l'eco e l'Invio arrivano insieme.
            if causa in ("eco", "rinfresco"):
                self.detta = self.terminale.visibile()
        visibile = self.terminale.visibile()
        # Il prompt delle mosse riscritto dopo una mossa o un messaggio: si
        # scrive e va alla barra, come il rinfresco, ma non si annuncia; le
        # mosse e i messaggi, righe chiuse, si dicono come sempre (Gabriele, 24
        # novembre 2026: su Lichess, con gli annunci accesi, il prompt si
        # risentiva intero a ogni mossa). Detta resta quella di prima, cosi'
        # se arriva un'attesa nuova, come una domanda, la riga si dice.
        riscritto = al_prompt_delle_mosse and not attesa_cambiata and self._al_prompt_delle_mosse()
        if visibile.strip() and not riscritto:
            # Con la scacchiera aperta la riga del prompt non si dice: la
            # scacchiera dice gia' cio' che serve, e il prompt si rinfresca.
            # Nemmeno il rinfresco periodico del prompt.
            if ultima_causa not in ("eco", "rinfresco") and self.dialogo_scacchiera is None:
                nuovo = _parte_nuova(visibile, self.detta)
                if nuovo:
                    da_dire.append(nuovo)
            self.detta = visibile
        self._mostra_nella_forma(chiuse, messaggi)
        self._di(da_dire, dal_tasto)

    def _al_prompt_delle_mosse(self):
        """Vero se il nucleo aspetta il prompt delle mosse di una partita."""
        return self.attesa.tipo == "area" and self.attesa.mosse

    def _mostra_nella_forma(self, chiuse, messaggi):
        """Le righe chiuse e la riga in corso, nella forma dell'area di adesso."""
        if self.fornitore is not None:
            self.righe.extend(chiuse)
            self._taglia_il_registro()
            self.messaggi.extend(messaggi)
            del self.messaggi[: -cruscotto.MESSAGGI_MOSTRATI]
            self._ridisegna()
        elif chiuse or self.area.GetLineText(len(self.righe)) != self.terminale.visibile():
            self._mostra(chiuse, self.terminale.visibile())

    def _taglia_il_registro(self):
        """Le righe piu' vecchie se ne vanno a gruppi, finche' restano le
        righe da tenere; restituisce quante."""
        tenute = self.righe_tenute
        if len(self.righe) <= tenute + max(10, tenute // 4):
            return 0
        tolte = len(self.righe) - tenute
        del self.righe[:tolte]
        if self.inizio_della_foglia is not None:
            riga, colonna = self.inizio_della_foglia
            riga -= tolte
            self.inizio_della_foglia = (riga, colonna) if riga >= 0 else (0, 0)
        return tolte

    def _mostra(self, chiuse, visibile):
        """Le righe chiuse prendono il posto della riga in corso, che va in
        fondo. Il cursore, se era nella riga in corso, va al cursore del
        nucleo; se l'utente rileggeva piu' su, resta dov'era."""
        riga, colonna = self._riga_e_colonna()
        sul_fondo = riga >= len(self.righe)
        prima = self._riga_sotto_il_cursore()
        ultima = len(self.righe)
        inizio = self.area.XYToPosition(0, ultima)
        fermo = self._sostituisci(inizio, inizio + self.area.GetLineLength(ultima), "\n".join([*chiuse, visibile]))
        self.righe.extend(chiuse)
        tolte = self._taglia_il_registro()
        if tolte:
            fermo = self._sostituisci(0, self.area.XYToPosition(0, tolte), "") and fermo
            riga -= tolte
        if sul_fondo:
            self._al_cursore()
        elif not fermo:
            # Col documento il cursore e' rimasto dov'era: rimetterlo
            # riporterebbe la barra di NVDA su di lui.
            self._vai(max(0, riga), colonna)
        self._braille_dopo_il_cambio(prima)

    # Il cruscotto.

    def _cambia_forma(self, fornitore, comandi=None):
        """Lo strato consegna chi da' i dati del cruscotto, con i comandi
        della modalita' per la plancia, o None a fine partita."""
        nuovi = comandi if fornitore is not None else None
        if nuovi != self.comandi:
            self.comandi = nuovi
            self._riscrivi_la_plancia()
        if fornitore is None:
            # A partita finita la scacchiera si chiude, e non si riapre.
            self.scacchiera_da_riaprire = False
            self._chiudi_la_scacchiera()
            if self.fornitore is None:
                return
            self.fornitore = None
            self.orologio.Stop()
            self.mostrate = []
            self.area.ChangeValue("\n".join([*self.righe, self.terminale.visibile()]))
            self._al_cursore()
            return
        nuova = self.fornitore is None
        self.fornitore = fornitore
        if nuova:
            self.messaggi = []
            self.mostrate = []
            self.orologio.Start(1000)
        self._ridisegna()

    def _ridisegna(self):
        """Riscrive solo le righe cambiate e rimette il cursore: sulla stessa
        riga della stessa sezione, alla stessa colonna; se era nel prompt e il
        prompt e' cambiato, al cursore del nucleo."""
        if not self or self.fornitore is None:
            return
        try:
            dati = self.fornitore()
            nuove = cruscotto.righe(dati, self.messaggi)
        # Lo stato appartiene al nucleo, che intanto puo' cambiarlo: si
        # riprova al prossimo secondo.
        except Exception:  # noqa: BLE001
            return
        nuove.append(("prompt", self.terminale.visibile()))
        if nuove == self.mostrate:
            return
        if self.mostrate:
            numero, colonna = self._riga_e_colonna()
            sezione = self.mostrate[numero][0]
            nella_sezione = sum(1 for s, _t in self.mostrate[:numero] if s == sezione)
            prompt_cambiato = self.mostrate[-1] != nuove[-1]
        else:
            numero, colonna, sezione, nella_sezione, prompt_cambiato = 0, 0, "prompt", 0, True
        prima = self._riga_sotto_il_cursore()
        if len(nuove) == len(self.mostrate) and all(a[0] == b[0] for a, b in zip(nuove, self.mostrate, strict=True)):
            # Stesse righe: si sostituiscono solo quelle cambiate, dal fondo,
            # senza toccare il cursore dove il documento c'e'. Di una riga si
            # riscrive solo il pezzo che cambia: il cursore fuori dal pezzo
            # non si muove, e NVDA non riporta il display sulla sua pagina.
            for indice in range(len(nuove) - 1, -1, -1):
                vecchia, nuova = self.mostrate[indice][1], nuove[indice][1]
                if nuova == vecchia:
                    continue
                inizio = self.area.XYToPosition(0, indice)
                if self.area.GetLineText(indice) == vecchia:
                    da, a, pezzo = richedit.tratto_cambiato(vecchia, nuova)
                    self._sostituisci(inizio + da, inizio + a, pezzo)
                else:
                    self._sostituisci(inizio, inizio + self.area.GetLineLength(indice), nuova)
        else:
            self.area.ChangeValue("\n".join(testo for _sezione, testo in nuove))
        self.mostrate = nuove
        if sezione == "prompt":
            self._vai(len(nuove) - 1, self.terminale.colonna if prompt_cambiato else colonna)
        else:
            righe_della_sezione = [i for i, (s, _t) in enumerate(nuove) if s == sezione]
            if righe_della_sezione:
                self._vai(righe_della_sezione[min(nella_sezione, len(righe_della_sezione) - 1)], colonna)
            else:
                self._al_cursore()
        self._braille_dopo_il_cambio(prima)

    def annuncia(self, righe):
        """Righe da annunciare per una finestra di dialogo, solo se gli
        annunci sono attivi, e sempre in coda: arrivano dopo la voce che lo
        screen reader sta leggendo, e non la interrompono (Gabriele,
        collaudo della finestra del prompt)."""
        if not self.annunci["attivi"]:
            return
        for riga in righe:
            self.sintesi.dici(riga, self.annunci["uscita"], self.annunci["destinazione"], interrompi=False)

    def alla_sintesi(self, testo, interrompi=True):
        """Un annuncio della scacchiera interattiva: sempre, e solo alla
        sintesi, perche' il braille resta a NVDA (Gabriele, specifiche della
        scacchiera)."""
        self.sintesi.dici(testo, self.annunci["uscita"], "sintesi", interrompi=interrompi)

    def _di(self, righe, dal_tasto):
        """Gli annunci, secondo le impostazioni: dal_tasto e' vero per la
        risposta a un tasto. Solo il primo puo' interrompere, gli altri lo
        seguono. Con la scacchiera aperta le risposte del nucleo si dicono
        sempre, alla sintesi e in coda agli annunci della scacchiera."""
        if self.dialogo_scacchiera is not None:
            for riga in righe:
                self.alla_sintesi(riga, interrompi=False)
            return
        if not self.annunci["attivi"]:
            return
        interrompi = annunci.interrompe(self.annunci, dal_tasto)
        for numero, riga in enumerate(righe):
            self.sintesi.dici(riga, self.annunci["uscita"], self.annunci["destinazione"], interrompi=interrompi and numero == 0)
        if righe and self.annunci["destinazione"] != "sintesi" and self.braille_indietro:
            # L'annuncio e' sulla barra: la riga del cursore torna fra un po',
            # per non coprirlo subito.
            self.ripasso_del_braille.Start(RIPASSO_DOPO_UN_ANNUNCIO)

    # La plancia e il fuoco.

    def _cambia_attesa(self, attesa):
        """Il nucleo aspetta altro: la plancia si riscrive, e il fuoco segue
        la domanda. Lungo una strada i menu di passaggio hanno subito la loro
        risposta."""
        self.attesa = attesa
        # Una domanda nuova comincia con la riga vuota.
        self.digitati = 0
        self._scacchiera_e_domande(attesa)
        if attesa.tipo == "menu":
            self.albero.menu(attesa.sito, attesa.voci, attesa.prompt, attesa.vuoto, attesa.alla_radice)
            if self._prosegui_la_strada():
                return
        elif attesa.tipo in ("area", "sino"):
            # Orologic chiede altro: la strada si ferma qui.
            self.meta = None
        elif self.meta is not None:
            return
        self._riscrivi_la_plancia()
        foglia = None
        if attesa.tipo in ("menu", "area", "sino"):
            # Una domanda vera: la foglia scelta ha finito di stampare.
            foglia, self.inizio_della_foglia = self.inizio_della_foglia, None
        if attesa.tipo == "menu" and self.primo_menu:
            # All'avvio il fuoco resta sull'area, all'inizio del benvenuto, e
            # alla plancia si va con F5 (Gabriele, collaudo del 21 novembre
            # 2026); dal menu dopo il fuoco segue la domanda.
            self.primo_menu = False
            self.area.SetInsertionPoint(0)
            self.area.ShowPosition(0)
        elif attesa.tipo == "menu":
            if not self._alla_risposta_della_foglia(foglia):
                self._sposta_il_fuoco("plancia")
        elif attesa.tipo in ("area", "sino"):
            if self.fornitore is None and wx.Window.FindFocus() is not self.area:
                # Il fuoco arriva all'area, dalla plancia: il cursore sulla
                # domanda, anche se era rimasto piu' su, per esempio sul
                # benvenuto dove lo lascia il primo menu (Gabriele, collaudo
                # del 22 novembre 2026). Chi e' gia' nell'area e rilegge piu'
                # su resta dov'e', e cosi' chi rilegge il cruscotto.
                self._al_cursore()
            self._sposta_il_fuoco("console")

    def _alla_risposta_della_foglia(self, inizio):
        """Dopo una foglia del menu, con gli annunci spenti, il fuoco va
        all'area, all'inizio di cio' che la voce ha stampato: dal ramo, senza
        annunci, non si sentirebbe niente (Gabriele, collaudo della T5). Con
        gli annunci accesi, o se la voce non ha stampato nulla, il fuoco
        resta alla plancia. Vero se e' andato all'area."""
        if inizio is None or self.annunci["attivi"] or self.fornitore is not None:
            return False
        riga, colonna = inizio
        ultima = self._riga_del_prompt()
        # La prima riga con del testo: Orologic apre spesso le sue risposte
        # con una riga vuota.
        while riga <= ultima:
            testo = self.area.GetLineText(riga)[colonna:]
            if testo.strip():
                break
            riga, colonna = riga + 1, 0
        else:
            return False
        self._vai(riga, colonna + len(testo) - len(testo.lstrip()))
        self.area.ShowPosition(self.area.GetInsertionPoint())
        self._sposta_il_fuoco("console")
        return True

    # La strada.

    def _prendi_la_strada(self, verso, finale, da_selezionare):
        """Verso il menu del percorso verso, e li' la voce finale, se c'e'."""
        if self.attesa.tipo != "menu":
            return
        self.meta = (tuple(verso), finale)
        self.passi = 0
        self.atteso = None
        self.da_selezionare = da_selezionare
        if not self._prosegui_la_strada():
            self._riscrivi_la_plancia()

    def _prosegui_la_strada(self):
        """Da' al menu di adesso la risposta della strada. Vero se l'ha data."""
        if self.meta is None:
            return False
        atteso, self.atteso = self.atteso, None
        livelli = len(self.albero.livelli)
        if atteso is not None and (
            (atteso[0] == "avanti" and livelli != atteso[1]) or (atteso[0] == "indietro" and livelli > atteso[1])
        ):
            # Il ramo non si e' aperto, o il menu non si e' chiuso, per
            # esempio arbitra senza orologi salvati: la strada si ferma qui.
            self.meta = None
            return False
        self.passi += 1
        verso, finale = self.meta
        cosa, valore = self.albero.strada(verso, finale)
        if cosa == "arrivato" or self.passi > PASSI_MASSIMI:
            self.meta = None
            return False
        if cosa == "finale":
            self.meta = None
            # La foglia scelta: cio' che stampa comincia in fondo all'area.
            self.inizio_della_foglia = (len(self.righe), len(self.terminale.visibile()))
        elif cosa == "avanti":
            self.atteso = ("avanti", livelli + 1)
        else:
            self.atteso = ("indietro", livelli - 1)
        self._rispondi(valore, avanti=cosa != "indietro")
        if cosa == "finale":
            self._riscrivi_la_plancia()
        return True

    def _rispondi(self, valore, avanti=True):
        """La risposta al menu che aspetta: una voce, o None come Esc."""
        livello = self.albero.adesso()
        if avanti and livello is not None:
            self.albero.scelto(valore)
            self.ultime_scelte[livello.sito] = valore
        self.attesa = Attesa(None)
        self.faccia.scegli(valore)

    def _percorso_fino(self, indice):
        return tuple(livello.scelta for livello in self.albero.livelli[:indice])

    def _aperto(self, indice, chiave):
        """Vero se la voce e' il ramo aperto del suo livello."""
        livelli = self.albero.livelli
        return indice < len(livelli) - 1 and livelli[indice].scelta == chiave

    def _entra(self, indice, chiave):
        self._prendi_la_strada(self._percorso_fino(indice) + (chiave,), None, (indice, chiave))

    def _esci(self, indice, chiave):
        self._prendi_la_strada(self._percorso_fino(indice), None, (indice, chiave))

    def _scegli(self, indice, chiave):
        self._prendi_la_strada(self._percorso_fino(indice), chiave, (indice, chiave))

    # L'albero.

    def _riscrivi_la_plancia(self):
        """Fuori dal gioco i menu: le voci del menu principale in cima, e
        dentro ogni ramo aperto le voci del suo menu; una domanda di
        enter_escape sotto la voce scelta, con INVIO ed ESC. In gioco i
        comandi della modalita'."""
        albero = self.plancia
        self.ricostruendo = True
        albero.Freeze()
        try:
            albero.DeleteAllItems()
            self.voci_della_plancia = {}
            radice = albero.AddRoot("")
            if self.comandi and self.attesa.tipo != "menu":
                nodi = plancia.comandi_della_partita(self.comandi)
                if self._scacchiera_disponibile():
                    # La voce dello spazio, in cima: chi non lo ricorda apre
                    # da qui la scacchiera interattiva (Gabriele, collaudo
                    # del 23 novembre 2026).
                    nodi.insert(0, plancia.Nodo(_("Spazio: per accedere alla scacchiera interattiva"), APRI_LA_SCACCHIERA))
                selezionata = self._metti_i_comandi(radice, nodi, ())
            else:
                selezionata = self._metti_i_menu(radice)
            if selezionata is not None and selezionata.IsOk():
                albero.SelectItem(selezionata)
                albero.EnsureVisible(selezionata)
        finally:
            albero.Thaw()
            self.ricostruendo = False

    def _metti_i_menu(self, radice):
        albero = self.plancia
        livelli = self.albero.livelli
        voluta = self.da_selezionare
        self.da_selezionare = None
        if voluta is None and livelli:
            adesso = len(livelli) - 1
            livello = livelli[adesso]
            if self.attesa.tipo == "menu":
                voluta = (adesso, self.ultime_scelte.get(livello.sito))
            else:
                voluta = (adesso, livello.scelta)
        selezionata = None
        prima_di_adesso = None
        genitore = radice
        ultima_scelta = None
        for indice, livello in enumerate(livelli):
            dentro = None
            for testo, valore, ramo in plancia.voci_del_menu(livello):
                voce = albero.AppendItem(genitore, testo)
                self.voci_della_plancia[voce] = ("menu", indice, valore, ramo)
                if ramo:
                    albero.SetItemHasChildren(voce, True)
                if indice == len(livelli) - 1 and prima_di_adesso is None:
                    prima_di_adesso = voce
                if valore is not None and valore == livello.scelta:
                    dentro = voce
                if voluta is not None and voluta == (indice, valore):
                    selezionata = voce
            if dentro is None:
                break
            ultima_scelta = dentro
            if indice < len(livelli) - 1:
                genitore = dentro
        if self.attesa.tipo == "sino":
            # La domanda sotto la voce che l'ha portata, con le sue risposte.
            sotto = ultima_scelta if ultima_scelta is not None and not self._sotto_un_ramo_aperto(ultima_scelta) else genitore
            domanda = albero.AppendItem(sotto, " ".join(self.attesa.prompt.split()) or "?")
            self.voci_della_plancia[domanda] = ("domanda",)
            prima = None
            for testo, tasto in plancia.voci_della_domanda():
                voce = albero.AppendItem(domanda, testo)
                self.voci_della_plancia[voce] = ("sino", tasto)
                prima = prima or voce
            selezionata = prima
        # I rami aperti, dalla cima.
        for voce, dati in list(self.voci_della_plancia.items()):
            if dati[0] == "menu" and self._aperto(dati[1], dati[2]):
                albero.Expand(voce)
        if self.attesa.tipo == "sino" and selezionata is not None:
            # Aperti i rami sopra la domanda, fino alla radice, che e' nascosta.
            sopra = albero.GetItemParent(selezionata)
            while sopra.IsOk() and sopra != radice:
                albero.Expand(sopra)
                sopra = albero.GetItemParent(sopra)
        return selezionata or prima_di_adesso

    def _sotto_un_ramo_aperto(self, voce):
        dati = self.voci_della_plancia.get(voce)
        return dati is not None and dati[0] == "menu" and self._aperto(dati[1], dati[2])

    def _metti_i_comandi(self, genitore, nodi, sopra):
        """I comandi, coi rami chiusi, tranne quelli che portano all'ultimo
        comando dato, che resta selezionato."""
        albero = self.plancia
        selezionata = None
        for nodo in nodi:
            voce = albero.AppendItem(genitore, nodo.etichetta)
            cammino = (*sopra, nodo.etichetta)
            self.voci_della_plancia[voce] = ("comando", nodo, cammino)
            if self.ultimo_comando == cammino or (selezionata is None and genitore == albero.GetRootItem() and self.ultimo_comando is None):
                selezionata = voce
            if nodo.figli:
                dentro = self._metti_i_comandi(voce, nodo.figli, cammino)
                if dentro is not None and self.ultimo_comando is not None and self.ultimo_comando[: len(cammino)] == cammino:
                    albero.Expand(voce)
                    selezionata = dentro
        return selezionata

    # I tasti e gli eventi della plancia.

    def _si_apre(self, evento):
        """Freccia destra o il clic su un ramo di menu: Orologic entra nel
        suo menu, e il ramo si apre quando arriva."""
        if self.ricostruendo:
            return
        dati = self.voci_della_plancia.get(evento.GetItem())
        if dati is None or dati[0] != "menu":
            return
        _tipo, indice, chiave, ramo = dati
        if self._aperto(indice, chiave):
            return
        evento.Veto()
        if ramo:
            wx.CallAfter(self._entra, indice, chiave)

    def _si_chiude(self, evento):
        """Freccia sinistra su un ramo aperto: Orologic torna al suo menu."""
        if self.ricostruendo:
            return
        dati = self.voci_della_plancia.get(evento.GetItem())
        if dati is None or dati[0] != "menu":
            return
        _tipo, indice, chiave, _ramo = dati
        if self._aperto(indice, chiave):
            evento.Veto()
            wx.CallAfter(self._esci, indice, chiave)

    def _voce_attivata(self, evento):
        voce = evento.GetItem()
        dati = self.voci_della_plancia.get(voce)
        if dati is None:
            return
        if dati[0] == "menu":
            _tipo, indice, chiave, ramo = dati
            if self._aperto(indice, chiave):
                self._esci(indice, chiave)
            elif ramo:
                self._entra(indice, chiave)
            else:
                self._scegli(indice, chiave)
        elif dati[0] == "sino" and self.attesa.tipo == "sino":
            self.faccia.premi(dati[1])
        elif dati[0] == "comando":
            _tipo, nodo, cammino = dati
            if nodo.figli:
                self.plancia.Toggle(voce)
                return
            if nodo.testo == APRI_LA_SCACCHIERA:
                if self.si_apre_la_scacchiera():
                    self.apri_la_scacchiera()
                else:
                    self.vai_all_area()
                return
            # Il comando si scrive nel prompt come se lo si digitasse; quelli
            # coi valori liberi, come l'Elo, aspettano il resto nell'area.
            self.ultimo_comando = cammino
            for carattere in nodo.testo:
                self.premi_nel_prompt(carattere)
            # Dove il nucleo legge un tasto solo, come l'esploratore di
            # Easyfish, il comando di una lettera e' gia' la risposta.
            if nodo.invio and not (self.attesa.tasto and len(nodo.testo) == 1):
                self.premi_nel_prompt("\r")
            else:
                self.vai_all_area()

    def _tasto_della_plancia(self, evento):
        """Esc nella plancia vale come Esc nel menu che aspetta, e come Esc
        nella domanda Invio o Esc, su qualunque voce sia il cursore: prima
        andava scelta la voce ESC (Gabriele, collaudo della scacchiera)."""
        if evento.GetKeyCode() == wx.WXK_ESCAPE and not evento.HasAnyModifiers():
            if self.attesa.tipo == "menu":
                self.meta = None
                self.attesa = Attesa(None)
                self.faccia.scegli(None)
                return
            if self.attesa.tipo == "sino":
                self.faccia.premi("\x1b")
                return
        evento.Skip()

    # Il fuoco.

    def vai_alla_plancia(self):
        self.fuoco_voluto = "plancia"
        self.plancia.SetFocus()

    def vai_all_area(self):
        self.fuoco_voluto = "console"
        self.area.SetFocus()

    def _sposta_il_fuoco(self, dove):
        """Il fuoco segue la domanda, ma non esce da una finestra di dialogo
        aperta sopra."""
        attuale = wx.Window.FindFocus()
        if attuale is not None and attuale.GetTopLevelParent() is not self:
            return
        if dove == "plancia":
            self.vai_alla_plancia()
        else:
            self.vai_all_area()

    def _attivata(self, evento):
        """La finestra torna in primo piano, anche la prima volta: il fuoco va
        dove lo vuole la domanda, non dove Windows lo aveva lasciato."""
        evento.Skip()
        if evento.GetActive():
            wx.CallAfter(self._rimetti_il_fuoco)

    def _rimetti_il_fuoco(self):
        if not self:
            return
        attuale = wx.Window.FindFocus()
        if attuale is not None and attuale.GetTopLevelParent() is not self:
            return
        (self.plancia if self.fuoco_voluto == "plancia" else self.area).SetFocus()

    def _fuoco_a(self, dove, evento):
        evento.Skip()
        self.fuoco_voluto = dove
        if dove != self.fuoco:
            self.fuoco = dove
            self.suona(SUONI_DEL_FUOCO[dove])

    def suona(self, preset):
        """Gli effetti sonori della finestra; le prove li sostituiscono."""
        Acusticator.play(preset, volume=config.VOLUME)

    # Le impostazioni.

    def impostazioni(self, suono=False):
        """La finestra delle impostazioni, il luogo unico di tutte (S1): con
        Ctrl e virgola, o dalla voce impostazioni del menu principale, che il
        suo tema lo suona gia'; con Ctrl e virgola lo suona qui. Il nucleo
        intanto continua: i tasti vanno alla finestra, e il testo che arriva
        si mostra e si annuncia come sempre."""
        if self.dialogo_impostazioni is not None:
            return
        if suono:
            from . import temi

            temi.suona("impostazioni")
        with dialoghi.FinestraImpostazioni(self, self.gestore.righe(), self.gestore.cambia) as dialogo:
            self.dialogo_impostazioni = dialogo
            try:
                dialogo.ShowModal()
            finally:
                self.dialogo_impostazioni = None
        self._rimetti_il_fuoco()

    def _impostazioni_dal_nucleo(self, richiesta):
        try:
            if self:
                self.impostazioni_del_nucleo = True
                self.impostazioni()
        finally:
            self.impostazioni_del_nucleo = False
            richiesta.chiuse.set()

    def motore_in_uso(self):
        """Vero quando il nucleo potrebbe usare il motore, e cambiarlo lo
        farebbe cadere: dentro una partita, o mentre lavora, cioe' sempre
        tranne quando aspetta una scelta della plancia o le impostazioni del
        menu principale. Con Ctrl e virgola le impostazioni si aprono in ogni
        momento; il motore si cambia solo a nucleo fermo. Chiesto da Gabriele
        il 22 novembre 2026, dal collaudo della T5."""
        if strato.dentro_una_partita():
            return True
        return not (self.attesa.tipo == "menu" or self.impostazioni_del_nucleo)

    def orologi(self):
        """La finestra degli orologi, dalla voce orologi del menu principale,
        che il suo tema lo suona gia'."""
        if self.dialogo_orologi is not None:
            return
        from . import finestra_orologi

        with finestra_orologi.FinestraOrologi(self, self.chiedi_conferma, self.avvisa) as dialogo:
            self.dialogo_orologi = dialogo
            try:
                dialogo.ShowModal()
            finally:
                self.dialogo_orologi = None
        self._rimetti_il_fuoco()

    def _orologi_dal_nucleo(self, richiesta):
        try:
            if self:
                self.orologi()
        finally:
            richiesta.chiuse.set()

    def pulizia(self, genitore=None):
        """La finestra della pulizia: dalla voce Pulizia delle impostazioni,
        o da sola all'avvio coi file vecchi."""
        if self.dialogo_pulizia is not None:
            return
        from . import finestra_pulizia

        with finestra_pulizia.FinestraPulizia(genitore or self, self.chiedi_conferma, self.avvisa) as dialogo:
            self.dialogo_pulizia = dialogo
            try:
                dialogo.ShowModal()
            finally:
                self.dialogo_pulizia = None
        if genitore is None:
            self._rimetti_il_fuoco()

    def _pulizia_dal_nucleo(self, richiesta):
        try:
            if self:
                self.pulizia()
        finally:
            richiesta.chiuse.set()

    def ricerca_pgn(self, ricerca):
        """La finestra della ricerca PGN, dalla voce ricerca del menu
        principale, che il suo tema lo suona gia': restituisce la partita
        scelta per Easyfish o per l'analisi, o None."""
        if self.dialogo_ricerca is not None:
            return None
        from . import finestra_ricerca

        with finestra_ricerca.FinestraRicerca(self, ricerca, self.chiedi_conferma, self.avvisa, self.annuncia) as dialogo:
            self.dialogo_ricerca = dialogo
            try:
                dialogo.ShowModal()
            finally:
                self.dialogo_ricerca = None
            uscita = dialogo.uscita
        self._rimetti_il_fuoco()
        return uscita

    def _ricerca_dal_nucleo(self, richiesta):
        try:
            if self:
                richiesta.uscita = self.ricerca_pgn(richiesta.ricerca)
        finally:
            richiesta.chiuse.set()

    def archivi_pgn(self):
        """PGN gestione archivi, dalla voce del menu principale, che il suo
        tema lo suona gia': pgn-extract cercato, scaricato o indicato, poi la
        sua finestra (issue 74)."""
        if self.dialogo_archivi is not None:
            return
        from . import finestra_archivi

        self.dialogo_archivi = True
        try:
            finestra_archivi.apri(self, self.chiedi_conferma, self.avvisa, self.annuncia, self.chiedi_valore, self.scegli, self.leggi_sopra, self.al_braille)
        finally:
            self.dialogo_archivi = None
        self._rimetti_il_fuoco()

    def leggi_sopra(self, genitore, titolo, righe):
        """Una finestra da leggere sopra il genitore, come la guida e il
        resoconto di pgn-extract; le prove la sostituiscono."""
        dialoghi.da_leggere(genitore, titolo, righe)

    def _archivi_dal_nucleo(self, richiesta):
        try:
            if self:
                self.archivi_pgn()
        finally:
            richiesta.chiuse.set()

    def albero_aperture(self, stato):
        """L'albero delle aperture, dalla voce del menu principale, che il
        suo tema lo suona gia': restituisce la linea scelta per l'analisi o
        per Easyfish, o None."""
        if self.dialogo_aperture is not None:
            return None
        from . import finestra_aperture

        with finestra_aperture.FinestraAperture(self, stato, self.annuncia) as dialogo:
            self.dialogo_aperture = dialogo
            try:
                dialogo.ShowModal()
            finally:
                self.dialogo_aperture = None
            uscita = dialogo.uscita
        self._rimetti_il_fuoco()
        return uscita

    def _aperture_dal_nucleo(self, richiesta):
        try:
            if self:
                richiesta.uscita = self.albero_aperture(richiesta.stato)
        finally:
            richiesta.chiuse.set()

    # Easyfish: le righe da leggere, il navigatore e l'editor. Si aprono
    # sopra la scacchiera, se e' aperta, perche' il fuoco vi torni.

    def _sopra(self):
        return self.dialogo_scacchiera or self

    def leggi(self, titolo, righe, verbosa=None, inizio=None):
        """Le righe in una finestra da leggere, con Chiudi, e Rendi verbosa
        se c'e' la forma verbosa."""
        genitore = self._sopra()
        dialoghi.da_leggere(genitore, titolo, righe, verbosa, inizio)
        if genitore is self:
            self._rimetti_il_fuoco()

    def _lettura_dal_nucleo(self, richiesta):
        try:
            if self:
                self.leggi(richiesta.titolo, richiesta.righe, richiesta.verbosa, richiesta.inizio)
        finally:
            richiesta.chiuse.set()

    def _navigatore_dal_nucleo(self, richiesta):
        try:
            if self:
                from . import finestra_navigatore

                genitore = self._sopra()
                richiesta.scelto, richiesta.modificata = finestra_navigatore.naviga(
                    genitore, richiesta.game, richiesta.nodo, self.chiedi_conferma, self.chiedi_valore, self.annuncia
                )
                if genitore is self:
                    self._rimetti_il_fuoco()
        finally:
            richiesta.chiuse.set()

    def _disegni_dal_nucleo(self, richiesta):
        try:
            if self:
                from . import finestra_disegni

                genitore = self._sopra()
                richiesta.modificata = finestra_disegni.disegna(genitore, richiesta.game, richiesta.nodo, self.chiedi_conferma, self.annuncia)
                if genitore is self:
                    self._rimetti_il_fuoco()
        finally:
            richiesta.chiuse.set()

    def _editor_dal_nucleo(self, richiesta):
        try:
            if self:
                from . import finestra_editor

                genitore = self._sopra()
                richiesta.nuova = finestra_editor.modifica(genitore, self, richiesta.fen)
                if genitore is self:
                    self._rimetti_il_fuoco()
        finally:
            richiesta.chiuse.set()

    # La scacchiera interattiva.

    def si_apre_la_scacchiera(self):
        """Vero se lo spazio apre la scacchiera: in partita, al prompt delle
        mosse ancora vuoto, con una posizione da mostrare."""
        return self.dialogo_scacchiera is None and not self.digitati and self._scacchiera_disponibile()

    def _scacchiera_disponibile(self):
        """Vero al prompt delle mosse, con una posizione da mostrare: qui la
        scacchiera interattiva si puo' aprire."""
        if self.fornitore is None or self.attesa.tipo != "area" or not self.attesa.gioco:
            return False
        try:
            dati = self.fornitore()
        # Lo stato appartiene al nucleo, che intanto puo' cambiarlo.
        except Exception:  # noqa: BLE001
            return False
        return bool(dati) and dati.get("board") is not None

    def apri_la_scacchiera(self):
        """La scacchiera interattiva, finche' Esc la chiude, la partita
        finisce o il nucleo fa una domanda che non e' il prompt delle mosse."""
        if self.dialogo_scacchiera is not None or self.fornitore is None:
            return
        from . import finestra_scacchiera

        self.scacchiera_da_riaprire = False
        with finestra_scacchiera.FinestraScacchiera(self) as dialogo:
            self.dialogo_scacchiera = dialogo
            try:
                dialogo.ShowModal()
            finally:
                self.dialogo_scacchiera = None
        if self:
            self._rimetti_il_fuoco()

    def _chiudi_la_scacchiera(self):
        if self.dialogo_scacchiera is not None:
            self.dialogo_scacchiera.chiudi()

    def _scacchiera_e_domande(self, attesa):
        """Una domanda del nucleo che non e' il prompt delle mosse chiude la
        scacchiera, perche' si risponda nell'area o nella plancia; al ritorno
        al prompt delle mosse la scacchiera si riapre."""
        di_gioco = attesa.tipo == "area" and attesa.gioco
        if self.dialogo_scacchiera is not None:
            if attesa.tipo is None or di_gioco:
                return
            if self.fornitore is not None:
                self.scacchiera_da_riaprire = True
            self.fuoco_voluto = "plancia" if attesa.tipo == "menu" else "console"
            self._chiudi_la_scacchiera()
        elif di_gioco and self.scacchiera_da_riaprire:
            self.scacchiera_da_riaprire = False
            if self.fornitore is not None:
                wx.CallAfter(self.apri_la_scacchiera)

    def chiedi_conferma(self, genitore, testo):
        """Una domanda con Si' e No, come quella del terminale; le prove la
        sostituiscono."""
        return wx.MessageBox(testo, "Orologic", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, genitore) == wx.YES

    def scegli(self, genitore, titolo, voci, scelta):
        """La scelta da una lista; le prove la sostituiscono."""
        return dialoghi.scegli(genitore, titolo, voci, scelta)

    def chiedi_valore(self, genitore, titolo, domanda, valore, tipo="testo", minimo=0, massimo=256):
        """Un numero o un testo in un campo; le prove lo sostituiscono."""
        return dialoghi.chiedi_valore(genitore, titolo, domanda, valore, tipo, minimo, massimo)

    def avvisa(self, genitore, testo):
        """Un avviso da leggere e chiudere; le prove lo sostituiscono."""
        wx.MessageBox(testo, "Orologic", wx.OK | wx.ICON_WARNING, genitore)

    def dopo_il_motore(self):
        """Dal filo del motore: le righe del motore si riscrivono negli
        elenchi ancora aperti."""
        wx.CallAfter(self._riscrivi_il_motore)

    def _riscrivi_il_motore(self):
        elenco = getattr(self.gestore, "elenco_del_motore", None)
        if elenco:
            self.gestore._aggiorna_il_motore(elenco)
        if self.dialogo_impostazioni:
            self.dialogo_impostazioni.aggiorna("motore", self.gestore.riga("motore"))

    # Il nucleo.

    def avvia_il_nucleo(self, corpo):
        def filo():
            errore = None
            try:
                corpo()
            except (KeyboardInterrupt, SystemExit):
                pass
            # Un errore del nucleo va nell'area, nel registro degli errori e
            # in una finestra da leggere prima di chiudere: prima la finestra
            # si chiudeva col traceback dentro, e nessuno lo leggeva (R15).
            except Exception:  # noqa: BLE001
                testo = traceback.format_exc()
                print(testo)
                errore = (testo, registro.scrivi(f"Nucleo:\n{testo}"))
            wx.CallAfter(self._nucleo_finito, errore)

        self.nucleo = threading.Thread(target=filo, name="nucleo di Orologic", daemon=True)
        self.nucleo.start()

    def _nucleo_finito(self, errore=None):
        if self:
            self._applica()
            if errore is not None:
                self.mostra_l_errore(*errore)
            if self.chiudi_alla_fine and self:
                self.Destroy()

    def mostra_l_errore(self, testo, file):
        """L'errore che ha fermato il nucleo, in una finestra da leggere, con
        il percorso del registro dove resta."""
        righe = [_("Orologic si e' fermato per un errore.")]
        if file:
            righe.append(_("Il testo resta nel registro degli errori: {file}").format(file=file))
        righe += testo.rstrip().splitlines()
        dialoghi.da_leggere(self, _("Errore di Orologic"), righe)

    def _chiudi(self, evento):
        """Alt+F4: il nucleo riceve l'interruzione, come Ctrl+C nel
        terminale, e ha qualche secondo per chiudersi da solo."""
        if self.nucleo is None or not self.nucleo.is_alive():
            evento.Skip()
            return
        if self.chiudendo:
            return
        # Una ricerca PGN con modifiche non ancora nel file, lasciata per
        # Easyfish o l'analisi: prima di chiudere si chiede se salvarle.
        from . import archivio_pgn, finestra_ricerca

        ricerca = archivio_pgn.ricerca_aperta()
        if ricerca is not None and self.dialogo_ricerca is None:
            finestra_ricerca.salva_all_uscita(self, ricerca, self.chiedi_conferma, self.avvisa)
        self.chiudendo = True
        self.faccia.chiudi()
        inizio = time.monotonic()

        def aspetta():
            if not self:
                return
            if self.nucleo.is_alive() and time.monotonic() - inizio < ATTESA_DELLA_CHIUSURA:
                wx.CallLater(100, aspetta)
                return
            if self.nucleo.is_alive():
                # Il nucleo e' fermo dove non legge tasti, per esempio in
                # rete: si chiude il motore e si esce comunque.
                from . import engine

                engine.CloseEngine()
                os._exit(0)
            self.Destroy()

        wx.CallLater(100, aspetta)


_SALVATI = {}


def prepara():
    """Crea la faccia e la finestra e collega il nucleo alla finestra: lo
    strato, la sorgente dei tasti di key, stdout, stdin e getpass. Serve una
    wx.App gia' nata. ripristina rimette tutto com'era."""
    faccia = FacciaFinestra()
    finestra = Finestra(faccia)
    _SALVATI.update(
        faccia=strato.imposta_faccia(faccia),
        sorgente=sorgente_dei_tasti(faccia.tasto_per_key),
        scelte=sorgente_delle_scelte(faccia.scelte_per_menu),
        stdout=sys.stdout,
        stdin=sys.stdin,
        getpass=getpass.getpass,
    )
    sys.stdout = UscitaFinestra(faccia)
    sys.stdin = IngressoFinestra(faccia)

    def password(prompt="Password: ", stream=None):
        sys.stdout.write(prompt)
        return faccia.leggi_riga(eco=False)

    getpass.getpass = password
    return finestra


def ripristina():
    """Scollega il nucleo dalla finestra, come prima di prepara."""
    if not _SALVATI:
        return
    strato.imposta_faccia(_SALVATI["faccia"])
    sorgente_dei_tasti(_SALVATI["sorgente"])
    sorgente_delle_scelte(_SALVATI["scelte"])
    sys.stdout = _SALVATI["stdout"]
    sys.stdin = _SALVATI["stdin"]
    getpass.getpass = _SALVATI["getpass"]
    _SALVATI.clear()


def avvia(corpo):
    """Apre la finestra e ci fa girare corpo, il programma di sempre, in un
    filo suo. Torna quando la finestra si chiude. La wx.App puo' essere gia'
    nata per la finestra della lingua del primo avvio."""
    app = wx.GetApp() or wx.App()
    finestra = prepara()
    finestra.Show()
    finestra.avvia_il_nucleo(corpo)
    app.MainLoop()
    # Il motore si chiude anche quando il nucleo e' rimasto fermo dove non
    # legge tasti, come in rete: il filo di SimpleEngine, che non e' daemon,
    # terrebbe vivo il processo senza finestra (R8).
    from . import engine

    engine.CloseEngine()
    ripristina()
