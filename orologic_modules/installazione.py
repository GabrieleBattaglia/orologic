# Orologic: l'installazione fatta con il setup, la versione in App installate e il mutex.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'installazione, tappa T5c della GUI (Piano della GUI.txt; issue 73).

L'installatore di Inno Setup, Orologic.iss, scrive la voce della
disinstallazione in HKCU, con la versione installata. L'aggiornamento
automatico pero' sostituisce i file senza passare dall'installatore, e la
voce resterebbe ferma alla versione di partenza. All'avvio, dal programma
compilato, aggiorna_la_versione la corregge, come installazione.py di
MeTeOra, ma solo se la voce e' quella di questa cartella: una copia
portatile, da zip, accanto a una installata non la tocca.

Il mutex: Orologic aperto tiene un mutex di nome Orologic, che
l'installatore cerca con AppMutex, per chiedere di chiudere Orologic prima
di installare o disinstallare. Non e' un'istanza unica: due Orologic aperti
insieme restano possibili, come sempre.
"""

import ctypes
import os
import winreg

# AppId di Orologic.iss, con il suffisso che Inno Setup aggiunge. Non cambia mai.
CHIAVE = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{2F02E0E5-F793-4397-A56B-B2BC5D0B4CEC}_is1"
NOME_DEL_MUTEX = "Orologic"
# La maniglia del mutex, tenuta per tutta la vita del programma.
_MUTEX = None


def tieni_il_mutex(nome=NOME_DEL_MUTEX):
    """Apre il mutex di Orologic, o quello che un altro Orologic ha gia'
    aperto, e lo tiene fino all'uscita."""
    global _MUTEX
    if _MUTEX is None:
        try:
            _MUTEX = ctypes.WinDLL("kernel32").CreateMutexW(None, False, nome) or None
        except (OSError, AttributeError):
            _MUTEX = None
    return _MUTEX


def _stessa_cartella(una, altra):
    return os.path.normcase(os.path.normpath(una)) == os.path.normcase(os.path.normpath(altra))


def aggiorna_la_versione(versione, cartella, reg=winreg):
    """Scrive versione nella voce di App installate, se Orologic e' installato
    in cartella e la voce dice un'altra versione. Torna vero se l'ha scritta.
    Ogni problema del registro si tace: e' solo un'etichetta."""
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, CHIAVE, 0, reg.KEY_READ | reg.KEY_WRITE) as chiave:
            luogo, _tipo = reg.QueryValueEx(chiave, "InstallLocation")
            if not _stessa_cartella(luogo, cartella):
                return False
            try:
                attuale, _tipo = reg.QueryValueEx(chiave, "DisplayVersion")
            except OSError:
                attuale = None
            if attuale == versione:
                return False
            reg.SetValueEx(chiave, "DisplayVersion", 0, reg.REG_SZ, versione)
            return True
    except OSError:
        return False
