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


def test_il_punto_b_del_puzzle_legge_la_scacchiera_nuda(monkeypatch):
    """R21: il puzzle di Lichess passa la scacchiera, non uno stato di
    partita, e .b ci cercava game_state.board."""
    from orologic_modules import lichess_app

    monkeypatch.setattr(lichess_app, "Acusticator", lambda *a, **k: None)
    testo = io.StringIO()
    with contextlib.redirect_stdout(testo):
        assert lichess_app.handle_exploration_command(".b", chess.Board())
    assert str(chess.Board()) in testo.getvalue()


@pytest.mark.parametrize(
    "indirizzo",
    ["https://lichess.org/AbCd1234/black", "https://lichess.org/AbCd1234", "https://lichess.org/AbCd1234wxyz/white", "lichess.org/AbCd1234?x=1"],
)
def test_l_id_della_partita_dal_campo_playing(indirizzo):
    """R22: il campo playing di Lichess finisce col colore, e l'id si
    prendeva dall'ultimo pezzo."""
    from orologic_modules import lichess_app

    assert lichess_app.id_della_partita(indirizzo) == "AbCd1234"


def test_la_richiesta_per_corrispondenza_si_manda_una_volta(monkeypatch, capsys):
    """R23: la richiesta di avversario per corrispondenza non e' un flusso,
    e il ciclo la ripubblicava ogni secondo."""
    from orologic_modules import lichess_app

    inviate = []
    monkeypatch.setattr(lichess_app.rete, "invia", lambda url, **k: inviate.append((url, k["dati"])) or (True, None))
    monkeypatch.setattr(lichess_app.rete, "apri", lambda *a, **k: pytest.fail("nessun flusso per corrispondenza"))
    parametri = {"color": "random", "variant": "standard", "rated": False, "clock_limit": None, "clock_increment": None, "days": 3}
    assert lichess_app.seek_game("token", parametri) is None
    assert len(inviate) == 1 and inviate[0][1]["days"] == 3
    assert "corrispondenza pubblicata" in capsys.readouterr().out
