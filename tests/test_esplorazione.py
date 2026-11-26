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


# R44: la bandierina caduta e l'articolo 6.9.


@pytest.mark.parametrize(
    ("fen", "bianco_scaduto", "atteso"),
    [
        # Al Nero resta il Re solo: non puo' dare matto, e' patta.
        ("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", True, "1/2-1/2"),
        # Il Nero ha una Donna: vince lui.
        ("4k3/8/8/8/8/8/3qP3/4K3 w - - 0 1", True, "0-1"),
        # Al Bianco restano Re e Cavallo contro il Re solo: patta.
        ("4k3/8/8/8/8/8/8/4KN2 b - - 0 1", False, "1/2-1/2"),
        # Col pedone nero il matto di Cavallo e' possibile, e vince il Bianco.
        ("4k3/8/8/8/8/8/4p3/4KN2 b - - 0 1", False, "1-0"),
        ("4k3/8/8/8/8/8/4p3/R3K3 b - - 0 1", False, "1-0"),
    ],
)
def test_il_risultato_per_tempo(fen, bianco_scaduto, atteso):
    from orologic_modules import board_utils

    assert board_utils.risultato_per_tempo(chess.Board(fen), bianco_scaduto) == atteso


# R45: il riepilogo delle mosse dalla posizione iniziale della partita.


def test_il_riepilogo_da_una_posizione_fen_col_nero_che_comincia():
    from orologic_modules import board_utils

    scacchiera = chess.Board("4k3/8/8/8/8/8/4P3/4K3 b - - 0 10")
    mosse = []
    for uci in ("e8d7", "e2e4", "d7e6"):
        mossa = chess.Move.from_uci(uci)
        mosse.append(scacchiera.san(mossa))
        scacchiera.push(mossa)
    righe = board_utils.riepilogo_mosse(mosse, board_utils.scacchiera_iniziale(scacchiera, mosse))
    assert len(righe) == 2 and righe[0].startswith("10... ") and righe[1].startswith("11. ")
    assert not any("Errore" in riga for riga in righe)


def test_il_riepilogo_di_una_partita_fischer_random():
    from orologic_modules import board_utils

    scacchiera = chess.Board.from_chess960_pos(518 - 100)
    mosse = []
    for mossa in list(scacchiera.legal_moves)[:1]:
        mosse.append(scacchiera.san(mossa))
        scacchiera.push(mossa)
    risposta = next(iter(scacchiera.legal_moves))
    mosse.append(scacchiera.san(risposta))
    scacchiera.push(risposta)
    righe = board_utils.riepilogo_mosse(mosse, board_utils.scacchiera_iniziale(scacchiera, mosse))
    assert len(righe) == 1 and "Errore" not in righe[0]
    # Senza pila che torni, la posizione standard, come prima.
    assert board_utils.scacchiera_iniziale(chess.Board(), ["e4"]) is None


def test_le_descrizioni_vengono_dal_pgn_coi_segni():
    """R46: il riepilogo di fine partita dal PGN, anche dopo una ripresa."""
    import chess.pgn

    from orologic_modules import board_utils

    partita = chess.pgn.read_game(io.StringIO("1. e4! e5 2. Nf3?! Nc6 *"))
    descrizioni = board_utils.descrizioni_della_partita(partita)
    assert len(descrizioni) == 4
    scacchiera = chess.Board()
    attesa = board_utils.DescribeMove(chess.Move.from_uci("e2e4"), scacchiera, annotation="!")
    assert descrizioni[0] == attesa
