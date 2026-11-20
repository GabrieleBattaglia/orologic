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

Fuori da questo modulo nessuno importa msvcrt: lo controlla
tests/test_strato.py.
"""

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


_faccia = FacciaTerminale()


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
