# Orologic: lo strato unico fra il nucleo e chi gli fa da tastiera e schermo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Lo strato unico, tappa T1 della GUI di Orologic (Piano della GUI.txt).

Orologic legge i tasti e scrive il testo come un programma da terminale, e
cosi' resta: dalla 9.0.0 pero' gira anche dentro una finestra, dove la
console non c'e'. Quello che il nucleo chiedeva direttamente alla console,
fuori dalle funzioni di GBUtils, passa da qui: i tasti letti uno per uno nei
cicli d'attesa, lo svuotamento della tastiera prima di una domanda e la
larghezza della riga da ripulire.

Lo strato ha una faccia alla volta. La faccia del terminale, la sola fino
alla T2, fa esattamente quello che Orologic faceva prima, con msvcrt e con
la console di Windows; quella della finestra la registra la finestra con
imposta_faccia. Per il resto la finestra non ha bisogno dello strato: key,
menu ed enter_escape di GBUtils la seguono con sorgente_dei_tasti, print e
dgt con sys.stdout e sys.stdin.

Dalla T2 lo strato sa anche quando c'e' una partita in corso, per il
cruscotto della finestra (decisione C1 del Piano della GUI.txt): le funzioni di gioco
dichiarano la zona della partita con in_partita o partita, e i cicli d'attesa
consegnano con fornisci chi da' i dati del cruscotto, e dalla T4 anche i
comandi della modalita', per la plancia. Nel terminale tutto questo non fa
niente.

Dalla T4 una scelta della plancia si puo' interrompere con un evento, come
fa il menu di Orolichess quando arriva una sfida: scelta_interrompibile, e
menu restituisce SCELTA_INTERROTTA. con_la_plancia dice se c'e' la plancia.

Fuori da questo modulo nessuno importa msvcrt: lo controlla
tests/test_strato.py.
"""

import contextlib
import functools
import io
import os
import shutil

try:
    import msvcrt
except ImportError:  # fuori da Windows non c'e', e nemmeno i tasti singoli
    msvcrt = None


class FacciaTerminale:
    """La console, come Orologic l'ha sempre usata. getwch restituisce i
    tasti come msvcrt: i tasti speciali in due chiamate, la prima con
    \\x00 o \\xe0."""

    def kbhit(self):
        return bool(msvcrt and msvcrt.kbhit())

    def getwch(self):
        return msvcrt.getwch()

    def svuota_tastiera(self):
        """Butta i tasti rimasti nella console. Senza console non fa niente."""
        if os.name != "nt" or msvcrt is None:
            return
        try:
            import ctypes

            while msvcrt.kbhit():
                msvcrt.getwch()
            kernel32 = ctypes.windll.kernel32
            kernel32.FlushConsoleInputBuffer(kernel32.GetStdHandle(-10))
        except (OSError, AttributeError):
            pass

    def larghezza(self):
        """Le colonne della riga, chieste al terminale."""
        return shutil.get_terminal_size(fallback=(80, 24)).columns

    def cruscotto(self, fornitore, comandi=None):
        """Il terminale non ha cruscotto."""

    def con_la_plancia(self):
        return False

    def impostazioni(self):
        """Il terminale ha il suo sottomenu delle impostazioni."""

    def orologi(self):
        """Il terminale ha il suo sottomenu degli orologi."""

    def pulizia(self):
        """Il terminale ha il suo avviso dei file vecchi."""

    def ricerca_pgn(self, ricerca):
        """Il terminale ha la sua ricerca, coi tasti."""
        return None

    def interrompi_la_scelta_con(self, evento):
        """Il terminale non ha la plancia: menu legge i tasti da se'."""
        return None

    def di_gioco(self, valore):
        """Il terminale non ha la scacchiera interattiva."""
        return False

    def da_leggere(self, titolo, righe, verbosa=None, inizio=None):
        """Il terminale le ha gia' stampate."""

    def navigatore(self, game, nodo):
        """Il terminale non ha il navigatore: c'e' l'esploratore."""
        return None, False

    def editor_della_scacchiera(self, fen):
        """Il terminale ha il suo editor, a comandi."""
        return None

    def disegni(self, game, nodo):
        """Il terminale ha il menu .d."""
        return None


_faccia = FacciaTerminale()
# Cio' che menu restituisce quando la scelta della plancia e' interrotta.
SCELTA_INTERROTTA = object()
# Quante zone di partita sono aperte una dentro l'altra: una ripresa da
# salvataggio automatico apre la partita dentro il menu che l'ha chiesta.
_partite = 0
# Dentro da_leggere, nella finestra: la forma verbosa e la riga del cursore.
_lettura = None


def imposta_faccia(faccia):
    """Registra la faccia dello strato e restituisce quella di prima. Una
    faccia ha kbhit, getwch, svuota_tastiera e larghezza, con il contratto di
    FacciaTerminale."""
    global _faccia
    precedente = _faccia
    _faccia = faccia
    return precedente


def faccia():
    """La faccia registrata adesso."""
    return _faccia


def kbhit():
    """Vero se c'e' un tasto da leggere, senza aspettare."""
    return _faccia.kbhit()


def getwch():
    """Il prossimo tasto, aspettandolo se non c'e'."""
    return _faccia.getwch()


def svuota_tastiera():
    """Butta i tasti premuti e non ancora letti."""
    _faccia.svuota_tastiera()


def larghezza():
    """Quante colonne ha la riga che si ripulisce."""
    return _faccia.larghezza()


@contextlib.contextmanager
def partita():
    """La zona di una partita: finche' e' aperta, i cicli d'attesa possono
    dare alla faccia i dati del cruscotto con fornisci. Alla chiusura
    dell'ultima zona il cruscotto se ne va."""
    global _partite
    _partite += 1
    try:
        yield
    finally:
        _partite -= 1
        if not _partite:
            _faccia.cruscotto(None)


def dentro_una_partita():
    """Vero dentro la zona di una partita."""
    return _partite > 0


def in_partita(funzione):
    """Il decoratore delle funzioni di gioco: tutta la funzione e' la zona
    di una partita."""

    @functools.wraps(funzione)
    def avvolta(*argomenti, **opzioni):
        with partita():
            return funzione(*argomenti, **opzioni)

    return avvolta


def fornisci(fornitore, comandi=None):
    """Dentro una partita, chi da' i dati del cruscotto: una funzione senza
    argomenti che restituisce i dati di cruscotto.dati_di; e i comandi della
    modalita', come il dizionario dell'aiuto, chiave e descrizione, per la
    plancia. Fuori da una partita non fa niente."""
    if _partite:
        _faccia.cruscotto(fornitore, comandi)


def impostazioni():
    """Nella finestra, la finestra delle impostazioni; il nucleo aspetta che
    si chiuda."""
    _faccia.impostazioni()


def orologi():
    """Nella finestra, la finestra degli orologi; il nucleo aspetta che si
    chiuda."""
    _faccia.orologi()


def pulizia():
    """Nella finestra, la finestra della pulizia; il nucleo aspetta che si
    chiuda."""
    _faccia.pulizia()


def ricerca_pgn(ricerca):
    """Nella finestra, la finestra della ricerca PGN, con lo stato di
    ricerca; il nucleo aspetta che si chiuda, e riceve la partita da
    passare a Easyfish o all'analisi, come (azione, indice), o None."""
    return _faccia.ricerca_pgn(ricerca)


def con_la_plancia():
    """Vero se le scelte di menu vanno alla plancia della finestra."""
    return _faccia.con_la_plancia()


@contextlib.contextmanager
def scelta_interrompibile(evento):
    """Finche' e' aperta, una scelta della plancia finisce quando l'evento
    si accende, e menu restituisce SCELTA_INTERROTTA."""
    precedente = _faccia.interrompi_la_scelta_con(evento)
    try:
        yield
    finally:
        _faccia.interrompi_la_scelta_con(precedente)


def fine_del_gioco():
    """Il gioco e' finito, anche se la funzione di gioco continua, per
    esempio col riepilogo: il cruscotto lascia il posto alla console."""
    _faccia.cruscotto(None)


@contextlib.contextmanager
def prompt_di_gioco():
    """Finche' e' aperta, le domande di dgt e di key valgono come il prompt
    delle mosse, che legge i tasti con kbhit e getwch: nella finestra lo
    spazio a riga vuota apre la scacchiera interattiva, e la scacchiera resta
    aperta. Serve a Easyfish, il cui menu legge una riga e l'esploratore un
    tasto."""
    precedente = _faccia.di_gioco(True)
    try:
        yield
    finally:
        _faccia.di_gioco(precedente)


@contextlib.contextmanager
def da_leggere(titolo):
    """Nella finestra, quello che si stampa qui dentro va in una finestra da
    leggere, col titolo, quando la zona si chiude: le analisi e gli aiuti,
    che nel cruscotto non ci stanno. Nel terminale si stampa come sempre."""
    global _lettura
    if not con_la_plancia():
        yield
        return
    raccolte = io.StringIO()
    precedente, _lettura = _lettura, {"verbosa": None, "inizio": None}
    try:
        with contextlib.redirect_stdout(raccolte):
            yield
        dettagli = _lettura
    finally:
        _lettura = precedente
    righe = [riga.rstrip() for riga in raccolte.getvalue().replace("\r", "\n").split("\n") if riga.strip()]
    if righe:
        _faccia.da_leggere(titolo, righe, **dettagli)


def lettura_verbosa(righe):
    """Dentro da_leggere, la forma verbosa di quello che si legge: la
    finestra ha il pulsante Rendi verbosa, che la mette al posto del testo.
    Fuori, e nel terminale, niente."""
    if _lettura is not None:
        _lettura["verbosa"] = list(righe)


def lettura_dalla_riga(testo):
    """Dentro da_leggere, la riga dove la finestra apre il cursore, come la
    prima linea di un'analisi; fuori, e nel terminale, niente."""
    if _lettura is not None and _lettura["inizio"] is None:
        _lettura["inizio"] = testo


def navigatore(game, nodo):
    """Nella finestra, il navigatore della partita, l'albero delle mosse e
    delle varianti, aperto su nodo; il nucleo aspetta che si chiuda, e
    riceve (nodo scelto o None, vero se la partita e' cambiata). Nel
    terminale (None, False)."""
    return _faccia.navigatore(game, nodo)


def disegni(game, nodo):
    """Nella finestra, la finestra dei disegni della partita, coi nuovi
    sulla mossa nodo; il nucleo aspetta, e riceve vero se la partita e'
    cambiata. Nel terminale None, e il nucleo usa il menu .d."""
    return _faccia.disegni(game, nodo)


def editor_della_scacchiera(fen):
    """Nella finestra, l'editor della scacchiera aperto sulla posizione fen;
    il nucleo aspetta, e riceve il FEN nuovo, o None se si e' annullato.
    Nel terminale None, e il nucleo usa il suo editor."""
    return _faccia.editor_della_scacchiera(fen)
