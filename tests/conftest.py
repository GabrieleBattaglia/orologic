# Orologic, preparazione delle prove automatiche.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le prove non toccano mai i dati veri e non disturbano chi lavora.

I dati: prima di importare qualunque modulo di Orologic, la cartella dei
salvataggi, quella che percorsi.py chiede a cartella_applicazione di
GBUtils, diventa una cartella temporanea, con la sola lingua scelta copiata
dalla cartella vera, cosi' polipo non la chiede, e un database col volume a
zero, cosi' i suoni non si sentono. Le risorse in sola lettura, come i
cataloghi delle traduzioni, restano quelle vere.

Le finestre: il filo principale passa a un desktop di Windows nascosto prima
che wx nasca, come in Tornello tests/conftest.py, perche' una finestra mai
mostrata che riceve il fuoco prenderebbe il primo piano sullo schermo di
Gabriele, e NVDA ne leggerebbe il titolo. Un sorvegliante guarda il primo
piano ogni decimo di secondo, e la suite fallisce se una finestra di questo
processo ci e' arrivata.

Nate con la tappa T1 della GUI, il 20 novembre 2026; il desktop nascosto con
la T2.
"""

import json
import os
import shutil
import sys
import tempfile
import threading

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

import percorsi  # noqa: E402

CARTELLA_DELLE_PROVE = tempfile.mkdtemp(prefix="orologic_prove_")
os.makedirs(os.path.join(CARTELLA_DELLE_PROVE, "settings"))
_LINGUA = os.path.join(RADICE, "settings", "selected_language.json")
if os.path.exists(_LINGUA):
    shutil.copy2(_LINGUA, os.path.join(CARTELLA_DELLE_PROVE, "settings"))
with open(os.path.join(CARTELLA_DELLE_PROVE, "settings", "orologic_db.json"), "w", encoding="utf-8") as _file:
    json.dump({"volume": 0.0}, _file)
percorsi.cartella_applicazione = lambda: CARTELLA_DELLE_PROVE

NOME_DEL_DESKTOP = f"orologic_prove_{os.getpid()}"
GENERIC_ALL = 0x10000000
DESKTOP_DELLE_PROVE = {}
PRIMO_PIANO = {"rubato": [], "ferma": threading.Event()}


def _user32():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    user32.SetThreadDesktop.restype = wintypes.BOOL
    user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    return user32


def _sorveglia(user32):
    """Il primo piano ogni decimo di secondo: se e' una finestra di questo
    processo, se lo segna."""
    import ctypes
    from ctypes import wintypes

    while not PRIMO_PIANO["ferma"].wait(0.1):
        finestra = user32.GetForegroundWindow()
        if not finestra:
            continue
        processo = wintypes.DWORD()
        user32.GetWindowThreadProcessId(finestra, ctypes.byref(processo))
        if processo.value == os.getpid():
            PRIMO_PIANO["rubato"].append(finestra)


def pytest_configure(config):
    if sys.platform != "win32" or DESKTOP_DELLE_PROVE:
        return
    import ctypes

    user32 = _user32()
    desktop = user32.CreateDesktopW(NOME_DEL_DESKTOP, None, None, 0, GENERIC_ALL, None)
    if not desktop:
        raise pytest.UsageError(f"Il desktop nascosto delle prove non si crea: errore di Windows {ctypes.get_last_error()}.")
    if not user32.SetThreadDesktop(desktop):
        codice = ctypes.get_last_error()
        user32.CloseDesktop(desktop)
        raise pytest.UsageError(f"Le prove non passano al desktop nascosto: errore di Windows {codice}. Il filo ha gia' delle finestre?")
    DESKTOP_DELLE_PROVE["nascosto"] = desktop
    threading.Thread(target=_sorveglia, args=(user32,), name="sorvegliante del primo piano", daemon=True).start()


def pytest_sessionfinish(session, exitstatus):
    PRIMO_PIANO["ferma"].set()
    if PRIMO_PIANO["rubato"]:
        print(f"\nATTENZIONE: {len(PRIMO_PIANO['rubato'])} volte una finestra delle prove era in primo piano sullo schermo vero.")
        session.exitstatus = 1


def pytest_unconfigure(config):
    shutil.rmtree(CARTELLA_DELLE_PROVE, ignore_errors=True)
