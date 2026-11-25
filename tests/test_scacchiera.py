# Orologic, prove della scacchiera interattiva, la logica.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La logica della scacchiera interattiva, senza finestra, coi casi delle
specifiche di Gabriele: il testo delle traverse, il cursore, i bordi e il
passaggio dall'altra parte, le diagonali, sollevare, posare e scambiare, le
mosse giudicate, l'arrocco col Re, la promozione, le parole."""

import chess

from orologic_modules import localizzazione
from orologic_modules.scacchiera import (
    DESTRA,
    GIU,
    GIU_DESTRA,
    SINISTRA,
    SU,
    SU_DESTRA,
    Scacchiera,
    nome_casa,
)


def _posizione(*mosse):
    board = chess.Board()
    for san in mosse:
        board.push_san(san)
    return board


def test_le_traverse_nei_due_versi():
    dal_bianco = Scacchiera(chess.Board())
    righe = dal_bianco.righe()
    assert righe[0] == "8| r | n | b | q | k | b | n | r |8"
    assert righe[4] == "4| - | + | - | + | - | + | - | + |4"
    assert righe[7] == "1| R | N | B | Q | K | B | N | R |1"
    dal_nero = Scacchiera(chess.Board(), dal_nero=True)
    assert dal_nero.righe()[0] == "1| R | N | B | K | Q | B | N | R |1"
    assert dal_nero.righe()[7] == "8| r | n | b | k | q | b | n | r |8"
    # Il 9 la gira.
    dal_nero.gira()
    assert dal_nero.righe() == righe


def test_il_cursore_nel_testo_e_il_pezzo_sollevato():
    s = Scacchiera(chess.Board())
    assert s.cursore == chess.E1
    riga, colonna = s.posto_del_cursore()
    assert s.righe()[riga][colonna] == "K"
    s.sposta(SINISTRA)
    assert s.spazio() == "sollevato"
    assert s.righe()[7] == "1| R | N | B |[Q]| K | B | N | R |1"


def test_l_ultimo_pezzo_mosso_fra_tonde():
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    s = Scacchiera(board)
    righe = s.righe()
    # Solo l'ultimo mosso, dell'avversario o mio, sulla casa d'arrivo.
    assert righe[3] == "5| + | - | + | - |(p)| - | + | - |5"
    assert righe[4] == "4| - | + | - | + | P | + | - | + |4"
    # Sollevato, vincono le quadre; sollevato un altro, tornano le tonde.
    assert s.cursore == chess.E5
    assert s.spazio() == "sollevato"
    assert s.righe()[3] == "5| + | - | + | - |[p]| - | + | - |5"
    s.sposta(GIU)
    assert s.spazio() == "scambiato"
    assert s.righe()[3] == "5| + | - | + | - |(p)| - | + | - |5"
    assert s.righe()[4] == "4| - | + | - | + |[P]| + | - | + |4"
    # Senza mosse niente tonde.
    assert "(" not in "".join(Scacchiera(chess.Board()).righe())


def test_bordi_passaggi_e_diagonali():
    s = Scacchiera(chess.Board())
    s.vai("f", 8)
    assert s.sposta(SU) == "fermo"
    assert s.cursore == chess.F8
    # Con Alt si passa dall'altra parte: f8 e su va a f1, a4 e sinistra a h4.
    assert s.sposta(SU, avvolgi=True) == "giro"
    assert s.cursore == chess.F1
    s.vai("a", 4)
    assert s.sposta(SINISTRA, avvolgi=True) == "giro"
    assert s.cursore == chess.H4
    # Lontano dal bordo, con Alt, e' un passo come gli altri.
    assert s.sposta(SINISTRA, avvolgi=True) == "passo"
    assert s.cursore == chess.G4
    s.vai("c", 1)
    assert s.sposta(SU_DESTRA) == "passo"
    assert s.cursore == chess.D2
    s.sposta(GIU_DESTRA)
    assert s.cursore == chess.E1
    assert s.sposta(GIU_DESTRA) == "fermo"
    # Dal Nero su va verso la traversa 1, destra verso la colonna a.
    n = Scacchiera(chess.Board(), dal_nero=True)
    n.vai("e", 8)
    n.sposta(SU)
    n.sposta(DESTRA)
    assert n.cursore == chess.D7
    n.vai(traversa=3)
    assert n.cursore == chess.D3


def test_sollevare_posare_scambiare():
    s = Scacchiera(chess.Board())
    s.vai("e", 4)
    assert s.spazio() == "vuota"
    s.vai("e", 2)
    assert s.spazio() == "sollevato"
    assert s.spazio() == "posato"
    assert s.sollevato is None
    s.spazio()
    s.vai("d", 7)
    # Qualunque pezzo, anche dell'avversario, per lo studio.
    assert s.spazio() == "scambiato"
    assert s.sollevato == chess.D7


def test_le_mosse_giudicate():
    s = Scacchiera(chess.Board())
    s.vai("e", 2)
    s.spazio()
    s.vai("e", 4)
    assert s.giudica(s.mossa()) is None
    assert s.san(s.mossa()) == "e4"
    s.vai("e", 5)
    assert s.giudica(s.mossa()) == f"Pedone bianco non puo' andare in {nome_casa(chess.E5)}."
    s.vai("d", 7)
    s.spazio()
    s.vai("d", 5)
    assert s.giudica(s.mossa()) == "Tocca al Bianco."
    # Un pezzo inchiodato.
    inchiodato = Scacchiera(_posizione("e4", "e5", "d4", "Bb4+"))
    inchiodato.vai("c", 2)
    inchiodato.spazio()
    inchiodato.vai("c", 3)
    assert inchiodato.giudica(inchiodato.mossa()) is None
    inchiodato.vai("c", 4)
    assert inchiodato.giudica(inchiodato.mossa()) == "Il re e' sotto scacco, e cosi' ci resta."


def test_l_arrocco_col_re_e_la_promozione():
    arrocco = Scacchiera(_posizione("e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"))
    arrocco.vai("e", 1)
    arrocco.spazio()
    arrocco.vai("g", 1)
    mossa = arrocco.mossa()
    assert arrocco.giudica(mossa) is None
    assert arrocco.san(mossa) == "O-O"
    # Negli scacchi 960 il Re va in g anche se python-chess scrive la mossa verso la Torre.
    board = chess.Board("rkr5/8/8/8/8/8/8/RK2R3 w KQkq - 0 1", chess960=True)
    s960 = Scacchiera(board)
    s960.vai("b", 1)
    s960.spazio()
    s960.vai("g", 1)
    assert s960.san(s960.mossa()) == "O-O"
    promozione = Scacchiera(chess.Board("8/4P2k/8/8/8/8/8/4K3 w - - 0 1"))
    promozione.vai("e", 7)
    promozione.spazio()
    promozione.vai("e", 8)
    assert promozione.promozione()
    mossa = promozione.mossa(chess.KNIGHT)
    assert promozione.giudica(mossa) is None
    assert promozione.san(mossa) == "e8=N"


def test_le_parole():
    colonna_e = localizzazione.colonna("e")
    s = Scacchiera(_posizione("e4", "e5", "Nf3"))
    # Il cursore parte dalla casa d'arrivo dell'ultima mossa.
    assert s.cursore == chess.F3
    assert s.casa_dell_ultima_mossa() == chess.F3
    s.vai("e", 4)
    assert s.descrivi() == f"{colonna_e} 4, Pedone bianco"
    s.vai("e", 3)
    assert s.descrivi() == f"{colonna_e} 3, vuota"
    assert s.in_mano() == "Nessun pezzo in mano."
    s.vai("g", 8)
    s.spazio()
    assert s.in_mano() == f"In mano: Cavallo nero, da {nome_casa(chess.G8)}."
    assert s.mosse_possibili() == f"Cavallo nero in {nome_casa(chess.G8)}: {nome_casa(chess.E7)}, {nome_casa(chess.F6)}, {nome_casa(chess.H6)}."
    assert s.ultime_mosse(1).startswith("2. ")
    assert s.ultime_mosse(2).startswith("1... ")
    assert Scacchiera(chess.Board()).ultime_mosse(1) == "Nessuna mossa ancora giocata."
    # La posizione nuova fa cadere il pezzo in mano, se la sua casa e' cambiata.
    s.aggiorna(_posizione("e4", "e5", "Nf3", "Nf6"))
    assert s.sollevato is None
