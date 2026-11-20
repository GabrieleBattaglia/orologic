# Orologic, prove dello strato unico (tappa T1 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Lo strato unico: nessuno legge la console alle sue spalle, le funzioni
delegano alla faccia registrata, e i cicli d'attesa leggono i tasti da lui.
Le facce di queste prove sono finte: nessun tasto vero, nessuna console."""

import ast
import contextlib
import io
import os
import types

import pytest
from conftest import RADICE

from orologic_modules import game_flow, strato, ui


class FacciaFinta:
    """Una faccia con i tasti in fila e la larghezza scelta."""

    def __init__(self, tasti="", colonne=40):
        self.tasti = list(tasti)
        self.colonne = colonne
        self.svuotata = 0

    def kbhit(self):
        return bool(self.tasti)

    def getwch(self):
        return self.tasti.pop(0)

    def svuota_tastiera(self):
        self.svuotata += 1
        self.tasti.clear()

    def larghezza(self):
        return self.colonne


@pytest.fixture
def faccia_finta():
    finta = FacciaFinta()
    precedente = strato.imposta_faccia(finta)
    yield finta
    strato.imposta_faccia(precedente)


def _sorgenti():
    yield os.path.join(RADICE, "orologic.py")
    for cartella, _sottocartelle, nomi in os.walk(os.path.join(RADICE, "orologic_modules")):
        for nome in nomi:
            if nome.endswith(".py"):
                yield os.path.join(cartella, nome)


def _importa_msvcrt(nodo):
    if isinstance(nodo, ast.Import):
        return any(alias.name == "msvcrt" for alias in nodo.names)
    return isinstance(nodo, ast.ImportFrom) and nodo.module == "msvcrt"


def test_nessuno_legge_la_console_fuori_dallo_strato():
    """msvcrt si importa solo in strato.py: ogni altra lettura diretta della
    console resterebbe sorda nella finestra."""
    colpevoli = []
    for percorso in _sorgenti():
        if os.path.basename(percorso) == "strato.py":
            continue
        with open(percorso, encoding="utf-8") as file:
            albero = ast.parse(file.read(), filename=percorso)
        for nodo in ast.walk(albero):
            if _importa_msvcrt(nodo):
                colpevoli.append(f"{percorso}:{nodo.lineno}")
    assert colpevoli == []


def test_la_faccia_di_partenza_e_il_terminale():
    assert isinstance(strato.faccia(), strato.FacciaTerminale)


def test_imposta_faccia_restituisce_la_precedente():
    finta = FacciaFinta()
    precedente = strato.imposta_faccia(finta)
    try:
        assert strato.faccia() is finta
    finally:
        assert strato.imposta_faccia(precedente) is finta
    assert strato.faccia() is precedente


def test_le_funzioni_delegano_alla_faccia(faccia_finta):
    faccia_finta.tasti = ["a", "\r"]
    faccia_finta.colonne = 33
    assert strato.kbhit()
    assert strato.getwch() == "a"
    assert strato.larghezza() == 33
    strato.svuota_tastiera()
    assert faccia_finta.svuotata == 1
    assert not strato.kbhit()


def test_pulisci_riga_usa_la_larghezza_dello_strato(faccia_finta):
    faccia_finta.colonne = 12
    uscita = io.StringIO()
    with contextlib.redirect_stdout(uscita):
        ui.pulisci_riga()
    assert uscita.getvalue() == "\r" + " " * 11 + "\r"


def test_svuota_tastiera_di_ui_passa_dallo_strato(faccia_finta):
    faccia_finta.tasti = ["x"]
    ui.svuota_tastiera()
    assert faccia_finta.svuotata == 1


def _stato_di_gioco():
    return types.SimpleNamespace(flag_fallen=False, ignore_clock=False, refresh_interval=0, vista_ferma=False)


def test_il_ciclo_d_attesa_dell_arbitraggio_legge_dallo_strato(faccia_finta):
    """async_arbitration_input con i tasti della faccia finta: un tasto
    speciale in due parti si ignora, Backspace cancella, Invio consegna."""
    faccia_finta.tasti = ["N", "f", "\xe0", "H", "x", "\b", "3", "\r"]
    uscita = io.StringIO()
    with contextlib.redirect_stdout(uscita):
        mossa = game_flow.async_arbitration_input(_stato_di_gioco(), lambda: "1. e4 ")
    assert mossa == "Nf3"
    assert uscita.getvalue().endswith("\n")


def test_esc_nel_ciclo_d_attesa_da_il_punto(faccia_finta):
    faccia_finta.tasti = ["e", "\x1b"]
    with contextlib.redirect_stdout(io.StringIO()):
        assert game_flow.async_arbitration_input(_stato_di_gioco(), lambda: "> ") == "."
