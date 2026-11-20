# Orologic: lo strato unico fra il nucleo e chi gli fa da tastiera e schermo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Lo strato unico, tappa T1 della GUI di Orologic (punto 74 di idee.txt).

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
cruscotto della finestra (decisione C1 del punto 74): le funzioni di gioco
dichiarano la zona della partita con in_partita o partita, e i cicli d'attesa
consegnano con fornisci chi da' i dati del cruscotto. Nel terminale tutto
questo non fa niente.

Fuori da questo modulo nessuno importa msvcrt: lo controlla
tests/test_strato.py.
"""

import contextlib
import functools
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

    def cruscotto(self, fornitore):
        """Il terminale non ha cruscotto."""


_faccia = FacciaTerminale()
# Quante zone di partita sono aperte una dentro l'altra: una ripresa da
# salvataggio automatico apre la partita dentro il menu che l'ha chiesta.
_partite = 0


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


def in_partita(funzione):
    """Il decoratore delle funzioni di gioco: tutta la funzione e' la zona
    di una partita."""

    @functools.wraps(funzione)
    def avvolta(*argomenti, **opzioni):
        with partita():
            return funzione(*argomenti, **opzioni)

    return avvolta


def fornisci(fornitore):
    """Dentro una partita, chi da' i dati del cruscotto: una funzione senza
    argomenti che restituisce i dati di cruscotto.dati_di. Fuori da una
    partita non fa niente."""
    if _partite:
        _faccia.cruscotto(fornitore)


def fine_del_gioco():
    """Il gioco e' finito, anche se la funzione di gioco continua, per
    esempio col riepilogo: il cruscotto lascia il posto alla console."""
    _faccia.cruscotto(None)
