# Orologic, prove di Esc nei menu (correzione della 8.46.8).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Esc, o Invio a vuoto, vale come la voce punto nelle nove scelte che non lo
gestivano fino alla 8.46.7. menu di GBUtils restituisce None in quei casi:
qui risponde con una fila di risposte scritte, e rete, partite e profili
sono funzioni finte che si segnano le chiamate. Col codice della 8.46.7
cadevano tutte e nove. Nella finestra conta ancora di piu': nella plancia Esc
vale come Esc nel menu."""

import chess.pgn
import pytest

from orologic_modules import lichess_app, lichess_board, lichess_profiler
from orologic_modules.easyfish import game_mode

DB = {"menu_numerati": False}


class Risposte:
    def __init__(self, *risposte):
        self.risposte = list(risposte)

    def __call__(self, *_argomenti, **_opzioni):
        assert self.risposte, "menu chiamato una volta di troppo"
        return self.risposte.pop(0)


@pytest.fixture
def chiamate(monkeypatch):
    """Lichess finto: le funzioni che non devono partire si segnano."""
    segnate = []

    def segna(nome):
        def finta(*argomenti, **_opzioni):
            segnate.append((nome, argomenti[:2]))

        return finta

    monkeypatch.setattr(lichess_app, "load_secrets", lambda: {"lichess_token": "finto", "lichess_username": "gabry"})
    monkeypatch.setattr(lichess_app, "fetch_profile_info", lambda *_a, **_o: {"perfs": {"blitz": {"games": 5, "rating": 1500}}})
    monkeypatch.setattr(lichess_app, "fetch_following", lambda *_a, **_o: [{"username": "amico1", "id": "amico1", "online": True}])
    monkeypatch.setattr(
        lichess_app, "get_active_games", lambda *_a, **_o: [{"gameId": "abcd1234", "opponent": {"username": "x"}, "color": "white"}]
    )
    monkeypatch.setattr(lichess_app, "enter_escape", lambda *_a, **_o: False)
    monkeypatch.setattr(
        lichess_app.rete, "leggi_json", lambda *_a, **_o: ({"blitz": {"user": {"name": "y"}, "rating": 2000, "gameId": "tv123456"}}, None)
    )
    for nome in ("fetch_perf_info", "fetch_puzzle", "get_game_params", "sfida_e_aspetta", "watch_player"):
        monkeypatch.setattr(lichess_app, nome, segna(nome))
    monkeypatch.setattr(lichess_board, "play_game", segna("play_game"))
    monkeypatch.setattr(lichess_board, "spectate_game", segna("spectate_game"))
    monkeypatch.setattr(lichess_profiler, "show_player_menu", segna("show_player_menu"))
    return segnate


@pytest.mark.parametrize(
    ("funzione", "risposte"),
    [
        (lambda: lichess_app.menu_statistiche(DB), [None]),
        (lambda: lichess_app.menu_amici(DB), ["vedi", None, "."]),
        (lambda: lichess_app.menu_puzzle(DB), [None]),
        (lambda: lichess_app.menu_guarda(DB), ["amico", None, "."]),
        (lambda: lichess_app.menu_guarda(DB), ["tv", None, "."]),
        (lambda: lichess_app.menu_gioca(DB), ["amico", None, "."]),
        (lambda: lichess_app.menu_gioca(DB), ["riprendi", None, "."]),
    ],
    ids=["statistiche", "amici", "puzzle", "guarda un amico", "lichess tv", "sfida un amico", "riprendi"],
)
def test_esc_torna_indietro_in_orolichess(monkeypatch, chiamate, funzione, risposte):
    monkeypatch.setattr(lichess_app, "menu", Risposte(*risposte))
    funzione()
    assert chiamate == []


def test_esc_nella_partita_scaricata_da_analizzare(monkeypatch):
    monkeypatch.setattr(lichess_profiler, "menu", Risposte(None))
    partite = [{"pgn": "1. e4 *", "players": {"white": {"user": {"name": "a"}}, "black": {"user": {"name": "b"}}}}]
    lichess_profiler.choose_game_for_analysis(partite)


def test_esc_nella_modalita_di_easyfish_annulla_la_partita(monkeypatch):
    def colore(*_argomenti, **_opzioni):
        raise AssertionError("la partita e' partita con gli orologi a zero")

    monkeypatch.setattr(game_mode, "menu", Risposte(None))
    monkeypatch.setattr(game_mode, "_scegli_colore", colore)
    # Un motore finto: basta che ci sia, per arrivare al menu della modalita'.
    _nodo, stato = game_mode.StartEngineGame(chess.pgn.Game(), object())
    assert stato is None
