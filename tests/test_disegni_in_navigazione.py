# Orologic, prove dei disegni detti mentre ci si muove fra le mosse.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le frecce e i cerchi di una mossa si dicono dovunque ci si muova fra le
mosse: le righe del cruscotto di Easyfish e dell'esploratore, le voci del
navigatore, la radice della partita, l'esploratore e la modalita' analisi
della partita. Il commento si legge senza i comandi fra quadre del PGN, che
prima nell'esploratore e nell'analisi uscivano come codici (Gabriele, 23
novembre 2026)."""

import io

import chess.pgn

from orologic_modules.easyfish import posizione

PGN = (
    '[Event "Prova"]\n[White "Bianco"]\n[Black "Nero"]\n[Result "*"]\n\n'
    "{ Apertura [%csl Gd4] } 1. e4 { Bel colpo [%cal Ge2e4,Rd1d8] [%csl Yf6] [%clk 0:05:00] } e5 2. Nf3 *\n"
)
DISEGNI = (
    "Disegni: Freccia da Empoli 2 ad Empoli 4 (verde), Freccia da Domodossola 1 ad Domodossola 8 (rosso), "
    "Cerchio su Firenze 6 (giallo)"
)


def _partita():
    return chess.pgn.read_game(io.StringIO(PGN))


def test_i_disegni_di_una_mossa_a_parole():
    game = _partita()
    mossa = game.variations[0]
    assert posizione.testo_dei_disegni(mossa) == DISEGNI
    assert posizione.testo_dei_disegni(mossa.variations[0]) == ""


def test_il_cruscotto_dice_commento_e_disegni():
    game = _partita()
    mossa = game.variations[0]
    righe = posizione.righe_della_posizione(mossa, mossa.board())
    assert "Commento: Bel colpo" in righe
    assert righe[-1] == DISEGNI
    assert not any("%" in riga for riga in righe)


def test_il_navigatore_dice_i_disegni_nella_voce():
    game = _partita()
    mossa = game.variations[0]
    voce = posizione.voce_della_mossa(mossa, game.board())
    assert voce.endswith(". Commento: Bel colpo. " + DISEGNI)
    radice = posizione.voce_della_partita(game)
    assert radice.endswith(". Commento: Apertura. Disegni: Cerchio su Domodossola 4 (verde)")


def test_la_modalita_analisi_dice_i_disegni_e_non_i_codici(monkeypatch, capsys):
    from orologic_modules import engine

    game = _partita()
    tasti = iter(["d", "."])
    monkeypatch.setattr(engine, "key", lambda *_a, **_k: next(tasti))
    monkeypatch.setattr(engine, "Acusticator", lambda *_a, **_k: None)
    engine.AnalyzeGame(game)
    uscita = capsys.readouterr().out
    assert "Commento: Bel colpo" in uscita
    assert DISEGNI in uscita
    assert "[%" not in uscita
