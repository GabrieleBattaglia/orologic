# Orologic, prove dei puzzle di Lichess nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""I puzzle di Orolichess nella finestra (Piano della GUI.txt, righe 138 e
141; Gabriele, 22 novembre 2026): la descrizione in una finestra da leggere,
il cruscotto con la scacchiera dal lato di chi risolve e le righe del
puzzle, il prompt di gioco, le mosse giuste ed errate, e il risultato.
Lichess e le finestre da leggere sono sostituiti."""

import chess
from conftest import pompa

from orologic_modules import dialoghi, lichess_app

PUZZLE = {
    "puzzle": {"id": "abc12", "rating": 1500, "themes": ["fork"], "fen": chess.STARTING_FEN, "solution": ["e2e4", "e7e5", "g1f3"]},
    "game": {"players": [{"color": "white", "name": "Uno"}, {"color": "black", "name": "Due"}]},
}


def _premi(finestra, testo):
    for carattere in testo:
        finestra.faccia.premi(carattere)


def test_il_puzzle_nella_finestra(finestra, monkeypatch):
    mandati = []
    monkeypatch.setattr(lichess_app, "send_puzzle_result", lambda _token, _id, win: mandati.append(win))
    letture = []
    monkeypatch.setattr(dialoghi, "da_leggere", lambda _genitore, titolo, righe: letture.append((titolo, righe)))
    finestra.avvia_il_nucleo(lambda: lichess_app.risolvi_il_puzzle(None, PUZZLE))
    assert pompa(lambda: finestra.fornitore is not None and finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    # La descrizione, da leggere; nel cruscotto le righe del puzzle.
    assert letture[0][0] == "Puzzle abc12"
    assert letture[0][1][:3] == ["Puzzle abc12", "Difficolta' (Rating Lichess): 1500", "Tema: fork"]
    dati = finestra.fornitore()
    assert dati["in_piu"] == ["Puzzle abc12", "Difficolta' (Rating Lichess): 1500", "Tema: fork", "Mosse trovate: 0 di 2."]
    assert dati["bianco_nome"] == "Uno" and dati["mio"] == chess.WHITE and dati["contesto"] is None
    assert "s" in finestra.comandi and finestra.si_apre_la_scacchiera()
    # Una mossa errata, poi le due giuste.
    _premi(finestra, "d4\r")
    assert pompa(lambda: any("Mossa errata" in messaggio for messaggio in finestra.messaggi))
    _premi(finestra, "e4\r")
    assert pompa(lambda: finestra.fornitore is not None and len(finestra.fornitore()["board"].move_stack) == 2)
    assert finestra.fornitore()["in_piu"][-1] == "Mosse trovate: 1 di 2."
    _premi(finestra, "Nf3\r")
    # Risolto: il cruscotto se ne va, e si aspetta Invio.
    assert pompa(lambda: finestra.attesa.tipo == "sino" and finestra.fornitore is None)
    assert "Congratulazioni! Hai risolto il puzzle!" in finestra.area.GetValue()
    _premi(finestra, "\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    # La mossa errata ha gia' mandato la sconfitta: la vittoria no.
    assert mandati == [False]
