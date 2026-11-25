# Orologic: il dialogo col componente di NVDA per Orologic.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il componente di NVDA per Orologic, nella cartella nvda_addon del
progetto (dalla 9.1.0, 25 novembre 2026, dai prototipi collaudati da
Gabriele). Qui la parte di Orologic.

  segna            mette sull'area la proprieta' di finestra Orologic.area:
                   1 la scacchiera interattiva, 2 la console. Il componente
                   guarda solo le aree segnate.
  togli_il_segno   la toglie quando l'area si chiude, col segno del
                   componente.
  avvisa           l'evento di Windows valueChange dopo ogni cambio del
                   testo: col componente la barra braille rilegge la riga.
  attivo           vero se il componente ha messo sull'area il suo segno,
                   Orologic.nvda col numero del processo di NVDA, e quel
                   processo c'e' ancora: allora la riga non va alla barra
                   come messaggio.
  installa         fa il pacchetto .nvda-addon dalla cartella nvda_addon e lo
                   apre: NVDA chiede se installarlo.

Fuori da Windows non si fa niente, e ogni errore lascia Orologic com'era:
senza componente la barra si aggiorna coi messaggi, come prima.
"""

import os
import re
import sys
import tempfile
import zipfile

import percorsi

PROPRIETA = "Orologic.area"
PRESENZA = "Orologic.nvda"
SCACCHIERA = 1
CONSOLE = 2
CARTELLA = "nvda_addon"
EVENT_OBJECT_VALUECHANGE = 0x800E
OBJID_CLIENT = -4
CHILDID_SELF = 0
SYNCHRONIZE = 0x00100000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WAIT_TIMEOUT = 0x102
ERROR_ACCESS_DENIED = 5

_funzioni = {}


def _windows():
    """Le funzioni di Windows, con una copia propria di user32 e kernel32:
    i tipi degli argomenti cambiati su ctypes.windll varrebbero per tutto il
    processo. None fuori da Windows."""
    if sys.platform != "win32":
        return None
    if not _funzioni:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        firme = (
            (user32, "SetPropW", (wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE), wintypes.BOOL),
            (user32, "GetPropW", (wintypes.HWND, wintypes.LPCWSTR), wintypes.HANDLE),
            (user32, "RemovePropW", (wintypes.HWND, wintypes.LPCWSTR), wintypes.HANDLE),
            (user32, "NotifyWinEvent", (wintypes.DWORD, wintypes.HWND, wintypes.LONG, wintypes.LONG), None),
            (kernel32, "OpenProcess", (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD), wintypes.HANDLE),
            (kernel32, "WaitForSingleObject", (wintypes.HANDLE, wintypes.DWORD), wintypes.DWORD),
            (kernel32, "CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
        )
        for libreria, nome, argomenti, risultato in firme:
            funzione = getattr(libreria, nome)
            funzione.argtypes = argomenti
            funzione.restype = risultato
            _funzioni[nome] = funzione
        _funzioni["ultimo_errore"] = ctypes.get_last_error
    return _funzioni


def _handle(controllo):
    try:
        return controllo.GetHandle() or None
    # Un controllo gia' distrutto non ha piu' la sua finestra.
    except RuntimeError:
        return None


def segna(controllo, area):
    """L'area di Orologic, SCACCHIERA o CONSOLE, per il componente."""
    funzioni, finestra = _windows(), _handle(controllo)
    if funzioni and finestra:
        funzioni["SetPropW"](finestra, PROPRIETA, area)


def togli_il_segno(controllo):
    """Prima che l'area si chiuda: il segno di Orologic e quello del
    componente."""
    funzioni, finestra = _windows(), _handle(controllo)
    if funzioni and finestra:
        funzioni["RemovePropW"](finestra, PROPRIETA)
        funzioni["RemovePropW"](finestra, PRESENZA)


def avvisa(controllo):
    """Il testo dell'area e' cambiato: valueChange per il componente. Senza
    componente NVDA lo riceve e non fa niente."""
    funzioni, finestra = _windows(), _handle(controllo)
    if funzioni and finestra:
        funzioni["NotifyWinEvent"](EVENT_OBJECT_VALUECHANGE, finestra, OBJID_CLIENT, CHILDID_SELF)


def attivo(controllo):
    """Vero se il componente ha segnato l'area e il suo NVDA c'e' ancora: un
    segno rimasto da un NVDA caduto non conta."""
    funzioni, finestra = _windows(), _handle(controllo)
    if not funzioni or not finestra:
        return False
    processo = funzioni["GetPropW"](finestra, PRESENZA)
    return bool(processo) and _vivo(funzioni, processo)


def _vivo(funzioni, processo):
    maniglia = funzioni["OpenProcess"](SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, processo)
    if not maniglia:
        # Un processo che non si lascia aprire c'e'.
        return funzioni["ultimo_errore"]() == ERROR_ACCESS_DENIED
    try:
        return funzioni["WaitForSingleObject"](maniglia, 0) == WAIT_TIMEOUT
    finally:
        funzioni["CloseHandle"](maniglia)


# Il pacchetto.


def sorgente():
    """La cartella del componente: accanto ai sorgenti, o dentro il
    pacchetto compilato."""
    return percorsi.resource_path(CARTELLA)


def versione(cartella=None):
    """La versione del componente, dal suo manifesto."""
    with open(os.path.join(cartella or sorgente(), "manifest.ini"), encoding="utf-8") as file:
        trovata = re.search(r"^version\s*=\s*(\S+)", file.read(), re.MULTILINE)
    return trovata.group(1) if trovata else "0"


def crea_il_pacchetto(destinazione, cartella=None):
    """Il file .nvda-addon, uno zip col manifesto nella radice, nella
    cartella destinazione; restituisce il suo percorso."""
    cartella = cartella or sorgente()
    os.makedirs(destinazione, exist_ok=True)
    pacchetto = os.path.join(destinazione, f"orologic-{versione(cartella)}.nvda-addon")
    with zipfile.ZipFile(pacchetto, "w", zipfile.ZIP_DEFLATED) as archivio:
        for radice, sottocartelle, file_presenti in os.walk(cartella):
            sottocartelle[:] = sorted(nome for nome in sottocartelle if nome != "__pycache__")
            for nome in sorted(file_presenti):
                percorso = os.path.join(radice, nome)
                archivio.write(percorso, os.path.relpath(percorso, cartella).replace(os.sep, "/"))
    return pacchetto


def installa():
    """Il pacchetto, nella cartella temporanea, aperto col programma che
    Windows gli associa: NVDA, se e' installato, chiede se installarlo.
    Restituisce il percorso; OSError se Windows non sa aprirlo."""
    pacchetto = crea_il_pacchetto(os.path.join(tempfile.gettempdir(), "Orologic"))
    # Il pacchetto l'ha appena fatto Orologic, dalla sua cartella.
    os.startfile(pacchetto)
    return pacchetto
