# Orologic, prove della ricostruzione delle mosse di una partita su Lichess
# (rilievi R16 e R17 della revisione 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Alla riconnessione Lichess rimanda gameFull con tutte le mosse, e dopo un
ritiro accettato gameState ne ha meno: scacchiera e storia si ricostruiscono
dall'elenco completo, invece di accodare o di tenere le mosse ritirate."""

import chess

from orologic_modules import lichess_board

MOSSE = ["e2e4", "e7e5", "g1f3", "b8c6"]


def _stato():
    return lichess_board.GamePlayState(chess.Board(), "prova")


def test_la_riconnessione_non_accoda_le_mosse():
    stato = _stato()
    lichess_board.ricostruisci_le_mosse(stato, MOSSE[:2])
    stato.move_times = [3.0, 4.0]
    # La riconnessione: gameFull con tutte le mosse.
    lichess_board.ricostruisci_le_mosse(stato, MOSSE)
    assert stato.move_history == ["e4", "e5", "Nf3", "Nc6"]
    assert len(stato.board.move_stack) == 4
    assert stato.move_times == [3.0, 4.0, 0.0, 0.0]
    assert len(stato.clocks_history) == 4
    # Da qui gameState prolunga l'elenco, e la mossa nuova si gioca.
    assert lichess_board.prolunga(stato, [*MOSSE, "f1b5"])


def test_il_ritiro_accettato_non_prolunga_e_si_ricostruisce():
    stato = _stato()
    lichess_board.ricostruisci_le_mosse(stato, MOSSE)
    assert not lichess_board.prolunga(stato, MOSSE[:2])
    lichess_board.ricostruisci_le_mosse(stato, MOSSE[:2])
    assert stato.move_history == ["e4", "e5"]
    assert stato.board.fen() == chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2").fen()
    # La mossa dopo il ritiro si gioca sulla posizione giusta.
    assert stato.board.parse_uci("d2d4")


def test_un_elenco_diverso_della_stessa_lunghezza_si_ricostruisce():
    stato = _stato()
    lichess_board.ricostruisci_le_mosse(stato, MOSSE)
    assert not lichess_board.prolunga(stato, ["e2e4", "e7e5", "g1f3", "g8f6", "f3e5"])


def test_la_posizione_di_partenza_da_fen():
    stato = _stato()
    stato.initial_fen = "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"
    lichess_board.ricostruisci_le_mosse(stato, ["e2e4"])
    assert stato.board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert stato.move_history == ["e4"]
