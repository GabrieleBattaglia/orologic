# Orologic, prove dei comandi di esplorazione della scacchiera.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le diagonali e le colonne con un argomento sbagliato: / o \\ da soli, o
due lettere, facevano cadere il nucleo con ord di una stringa vuota
(rilievo R10 della revisione 2, 26 novembre 2026)."""

import contextlib
import io

import chess
import pytest

from orologic_modules import ui


@pytest.fixture(autouse=True)
def muto(monkeypatch):
    monkeypatch.setattr(ui, "Acusticator", lambda *a, **k: None)


def _uscita(comando, origine):
    testo = io.StringIO()
    with contextlib.redirect_stdout(testo):
        assert ui.esplora_scacchiera(comando, origine)
    return testo.getvalue()


@pytest.mark.parametrize("comando", ["/", "\\", "/ ", "\\ "])
def test_la_diagonale_senza_colonna_non_cade(comando):
    assert "Colonna base non valida." in _uscita(comando, chess.Board())


def test_le_funzioni_rifiutano_piu_di_una_lettera():
    testo = io.StringIO()
    with contextlib.redirect_stdout(testo):
        ui.read_diagonal(chess.Board(), "ab", True)
        ui.read_file(chess.Board(), "")
        ui.read_file(chess.Board(), "ab")
    assert testo.getvalue().count("non valida") == 3


def test_la_diagonale_giusta_si_legge_ancora():
    assert "non valida" not in _uscita("/a", chess.Board())
