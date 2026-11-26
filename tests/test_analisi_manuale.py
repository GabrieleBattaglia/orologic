# Orologic, prove dell'analisi manuale nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'analisi manuale portata alla versione 9 (9.4.1, Gabriele, 25 novembre
2026): nella finestra e' una zona di partita, come l'esploratore di
Easyfish. Il cruscotto mostra la posizione, la plancia i comandi
dell'analisi, e l'aiuto, la scacchiera e le intestazioni vanno in una
finestra da leggere. Il motore non serve: i comandi provati non lo usano."""

import io

import chess
import chess.pgn
from conftest import pompa

from orologic_modules import config, dialoghi, engine

PARTITA = """[White "Bianco di prova"]
[Black "Nero di prova"]
[Result "*"]

1. e4 e5 2. Nf3 { Bella } Nc6 *
"""


def _premi(finestra, testo):
    for carattere in testo:
        finestra.faccia.premi(carattere)


def test_l_analisi_manuale_nella_finestra(finestra, monkeypatch):
    game = chess.pgn.read_game(io.StringIO(PARTITA))
    letture = []
    monkeypatch.setattr(dialoghi, "da_leggere", lambda _genitore, titolo, righe, *_resto: letture.append((titolo, righe)))
    finestra.avvia_il_nucleo(lambda: engine.AnalyzeGame(game))
    # La zona di partita: il cruscotto e i comandi dell'analisi nella plancia.
    assert pompa(lambda: finestra.fornitore is not None and finestra.comandi == config.ANALYSIS_COMMANDS)
    dati = finestra.fornitore()
    assert dati["bianco_nome"] == "Bianco di prova" and dati["nero_nome"] == "Nero di prova"
    assert dati["board"].move_stack == [] and dati["in_piu"][0] == "Linea principale."
    # Avanti di due mosse: il cruscotto segue.
    _premi(finestra, "dd")
    assert pompa(lambda: len(finestra.fornitore()["board"].move_stack) == 2)
    _premi(finestra, "d")
    assert pompa(lambda: "Commento: Bella" in finestra.fornitore()["in_piu"])
    # L'aiuto, la scacchiera e le intestazioni in una finestra da leggere.
    _premi(finestra, "?")
    assert pompa(lambda: letture and letture[-1][0] == "Comandi dell'analisi")
    assert any("Indietro di 1 mossa" in riga for riga in letture[-1][1])
    _premi(finestra, "u")
    assert pompa(lambda: letture[-1][0] == "Scacchiera")
    _premi(finestra, "j")
    assert pompa(lambda: letture[-1][0] == "Header della partita")
    assert any("Bianco di prova" in riga for riga in letture[-1][1])
    # Si esce: il cruscotto se ne va, e la console torna.
    _premi(finestra, ".")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert finestra.fornitore is None and finestra.comandi is None



def test_k_senza_mosse_non_cade(finestra):
    """R42: con un PGN senza mosse k chiedeva a dgt un numero fra 1 e 0, e
    dgt sollevava ValueError."""
    game = chess.pgn.read_game(io.StringIO('[White "A"]\n[Black "B"]\n[Result "*"]\n\n*\n'))
    finestra.avvia_il_nucleo(lambda: engine.AnalyzeGame(game))
    assert pompa(lambda: finestra.fornitore is not None and finestra.comandi == config.ANALYSIS_COMMANDS)
    _premi(finestra, "k")
    assert pompa(lambda: "La partita non ha mosse." in finestra.area.GetValue())
    assert finestra.nucleo.is_alive()
    _premi(finestra, ".")
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_k_vede_le_mosse_aggiunte_con_z(finestra, monkeypatch):
    """R131: il conto delle mosse per k si faceva una volta, all'inizio, e
    non vedeva le mosse che z aggiunge in fondo alla linea principale."""
    game = chess.pgn.read_game(io.StringIO('[White "A"]\n[Black "B"]\n[Result "*"]\n\n*\n'))
    monkeypatch.setattr(engine, "CalculateBest", lambda *_a, **_k: [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")])
    finestra.avvia_il_nucleo(lambda: engine.AnalyzeGame(game))
    assert pompa(lambda: finestra.fornitore is not None and finestra.comandi == config.ANALYSIS_COMMANDS)
    _premi(finestra, "z")
    assert pompa(lambda: "Variante aggiunta." in finestra.area.GetValue())
    _premi(finestra, "k")
    assert pompa(lambda: "(Max 1)" in finestra.area.GetValue())
    assert "La partita non ha mosse." not in finestra.area.GetValue()
