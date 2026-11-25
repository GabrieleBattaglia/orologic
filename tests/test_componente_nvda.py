# Orologic, prove del dialogo col componente di NVDA per Orologic.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il componente di NVDA per Orologic (dalla 9.1.0, 25 novembre 2026): i
segni sulle aree, il segno di presenza del componente col suo processo, il
pacchetto .nvda-addon, la voce delle impostazioni che lo apre, la barra
lasciata al componente quando c'e', e la riga del cruscotto riscritta solo
nel pezzo che cambia, senza muovere il cursore."""

import ctypes
import os
import subprocess
import sys
import threading
import zipfile
from ctypes import wintypes

import pytest
import wx
from conftest import pompa

from orologic_modules import (
    componente_nvda,
    cruscotto,
    finestra_scacchiera,
    impostazioni,
)
from orologic_modules.richedit import tratto_cambiato

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="le proprieta' di finestra sono di Windows")

_user32 = ctypes.WinDLL("user32")
_user32.GetPropW.argtypes = (wintypes.HWND, wintypes.LPCWSTR)
_user32.GetPropW.restype = wintypes.HANDLE
_user32.SetPropW.argtypes = (wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE)
_user32.SetPropW.restype = wintypes.BOOL


def _segno(controllo, nome):
    return _user32.GetPropW(controllo.GetHandle(), nome)


@pytest.fixture
def area(app):
    cornice = wx.Frame(None)
    controllo = wx.TextCtrl(cornice, style=wx.TE_MULTILINE | wx.TE_RICH2)
    try:
        yield controllo
    finally:
        cornice.Destroy()
        pompa(lambda: False, 0.1)


def _processo_finito():
    """Il numero di un processo che c'era e non c'e' piu'."""
    processo = subprocess.Popen(["cmd.exe", "/c", "exit"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)  # noqa: S607
    processo.wait(10)
    return processo.pid


def test_il_pezzo_che_cambia():
    assert tratto_cambiato("Bianco 04:59 >", "Bianco 04:58 >") == (11, 12, "8")
    assert tratto_cambiato("uguale", "uguale") == (6, 6, "")
    assert tratto_cambiato("", "nuovo") == (0, 0, "nuovo")
    assert tratto_cambiato("abc", "") == (0, 3, "")
    # Un pezzo aggiunto in mezzo, e la fine che resta.
    assert tratto_cambiato("Tempo 9 >", "Tempo 10 >") == (6, 7, "10")
    # Le ripetizioni non fanno sovrapporre l'inizio e la fine.
    assert tratto_cambiato("aaa", "aaaa") == (3, 3, "a")


def test_segni_presenza_e_processo_di_nvda(area):
    assert not componente_nvda.attivo(area)
    componente_nvda.segna(area, componente_nvda.CONSOLE)
    assert _segno(area, componente_nvda.PROPRIETA) == componente_nvda.CONSOLE
    # Il segno del componente, col processo di NVDA: qui uno vivo, questo.
    _user32.SetPropW(area.GetHandle(), componente_nvda.PRESENZA, os.getpid())
    assert componente_nvda.attivo(area)
    # Un NVDA caduto lascia il segno, ma il suo processo non c'e' piu'.
    _user32.SetPropW(area.GetHandle(), componente_nvda.PRESENZA, _processo_finito())
    assert not componente_nvda.attivo(area)
    componente_nvda.avvisa(area)
    componente_nvda.togli_il_segno(area)
    assert _segno(area, componente_nvda.PROPRIETA) is None
    assert _segno(area, componente_nvda.PRESENZA) is None


def test_il_pacchetto_del_componente(tmp_path):
    pacchetto = componente_nvda.crea_il_pacchetto(str(tmp_path))
    versione = componente_nvda.versione()
    assert versione == "1.0.1"
    assert os.path.basename(pacchetto) == f"orologic-{versione}.nvda-addon"
    with zipfile.ZipFile(pacchetto) as archivio:
        nomi = archivio.namelist()
        manifesto = archivio.read("manifest.ini").decode("utf-8")
        codice = archivio.read("globalPlugins/orologic.py").decode("utf-8")
    assert sorted(nomi) == ["COPYING.txt", "globalPlugins/orologic.py", "manifest.ini"]
    assert "name = orologic" in manifesto
    # I segni del componente sono quelli di Orologic.
    for segno in (componente_nvda.PROPRIETA, componente_nvda.PRESENZA):
        assert f'"{segno}"' in codice
    compile(codice, "globalPlugins/orologic.py", "exec")


def test_la_voce_delle_impostazioni(finestra, monkeypatch):
    gestore = finestra.gestore
    assert dict(gestore.righe())["componente_nvda"] == "Installa il componente per NVDA"
    assert impostazioni.VOCI[-4:] == ("componente_nvda", "caffe", "pub_entra", "pub_aiuto")
    aperti = []
    monkeypatch.setattr(componente_nvda, "installa", lambda: aperti.append("aperto"))
    gestore.cambia("componente_nvda", None)
    assert aperti == ["aperto"]
    avvisi = []
    monkeypatch.setattr(finestra, "avvisa", lambda _genitore, testo: avvisi.append(testo))

    def senza_nvda():
        raise OSError("nessuna applicazione associata")

    monkeypatch.setattr(componente_nvda, "installa", senza_nvda)
    gestore.cambia("componente_nvda", None)
    assert avvisi == ["Non sono riuscito ad aprire il componente per NVDA: nessuna applicazione associata"]


def test_installa_apre_il_pacchetto(monkeypatch, tmp_path):
    aperti = []
    monkeypatch.setattr(componente_nvda.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(componente_nvda.os, "startfile", aperti.append, raising=False)
    pacchetto = componente_nvda.installa()
    assert aperti == [pacchetto]
    assert os.path.dirname(pacchetto) == os.path.join(str(tmp_path), "Orologic")
    assert zipfile.is_zipfile(pacchetto)


def test_le_aree_segnate(finestra, monkeypatch):
    assert _segno(finestra.area, componente_nvda.PROPRIETA) == componente_nvda.CONSOLE
    monkeypatch.setattr(finestra_scacchiera, "suona", lambda _preset: None)
    finestra.fornitore = lambda: {"board": None, "mio": None}
    try:
        dialogo = finestra_scacchiera.FinestraScacchiera(finestra)
        assert _segno(dialogo.area, componente_nvda.PROPRIETA) == componente_nvda.SCACCHIERA
        dialogo.Destroy()
    finally:
        finestra.fornitore = None


def test_col_componente_la_barra_e_sua(finestra, monkeypatch):
    avvisate = []
    monkeypatch.setattr(componente_nvda, "avvisa", avvisate.append)
    monkeypatch.setattr(componente_nvda, "attivo", lambda _area: True)
    passo = threading.Event()
    fine = threading.Event()

    def nucleo():
        sys.stdout.write("Tempo 05:00 >")
        sys.stdout.flush()
        passo.wait(10)
        sys.stdout.write("\rTempo 04:59 >")
        sys.stdout.flush()
        fine.wait(10)

    finestra.avvia_il_nucleo(nucleo)
    try:
        assert pompa(lambda: "Tempo 05:00 >" in finestra.area.GetValue())
        finestra.vai_all_area()
        assert pompa(lambda: wx.Window.FindFocus() is finestra.area)
        passo.set()
        assert pompa(lambda: "Tempo 04:59 >" in finestra.area.GetValue())
        assert pompa(lambda: finestra.area in avvisate)
        # La riga cambiata non va alla barra come messaggio, ne' ora ne' dopo.
        pompa(lambda: False, 1.5)
        assert finestra.al_braille_mandati == []
        assert not finestra.ripasso_del_braille.IsRunning()
    finally:
        passo.set()
        fine.set()


def test_il_cruscotto_riscrive_il_pezzo_senza_muovere_il_cursore(finestra, monkeypatch):
    righe = {"orologi": "Bianco 04:59, Nero 03:22"}
    monkeypatch.setattr(cruscotto, "righe", lambda _dati, _messaggi: [("info", "Partita di prova"), ("orologi", righe["orologi"])])
    monkeypatch.setattr(finestra, "fornitore", dict)
    finestra.mostrate = []
    finestra._ridisegna()
    assert finestra._documento() is not None
    # Il cursore in fondo alla riga degli orologi, fuori dal pezzo che cambia.
    finestra._vai(1, len(righe["orologi"]))
    posizione = finestra.area.GetInsertionPoint()
    spostamenti = []
    originale = finestra.area.SetInsertionPoint
    monkeypatch.setattr(finestra.area, "SetInsertionPoint", lambda dove: (spostamenti.append(dove), originale(dove)))
    righe["orologi"] = "Bianco 04:58, Nero 03:22"
    finestra._ridisegna()
    assert finestra.area.GetLineText(1) == "Bianco 04:58, Nero 03:22"
    assert finestra.area.GetInsertionPoint() == posizione
    assert spostamenti == []
