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


# R18: l'esito degli invii.


def _esito(monkeypatch, riuscito, errore=None, **argomenti):
    import queue

    monkeypatch.setattr(lichess_board.rete, "invia", lambda *a, **k: (riuscito, errore))
    coda = queue.Queue()
    lichess_board.invia_e_riferisci(coda, "abcd1234", "token", "move", "e2e4", **argomenti)
    return coda.get(timeout=5) if (not riuscito or argomenti.get("riuscita")) else coda


def test_la_mossa_che_non_arriva_si_dice(monkeypatch):
    messaggio = _esito(monkeypatch, False, "Lichess ha risposto con l'errore 400.", fallita="La mossa e4 non e' arrivata a Lichess.")
    assert messaggio == {
        "type": "esito_invio",
        "testo": "La mossa e4 non e' arrivata a Lichess. Lichess ha risposto con l'errore 400.",
        "riuscito": False,
    }


def test_la_conferma_arriva_dopo_l_invio(monkeypatch):
    messaggio = _esito(monkeypatch, True, riuscita="Offerta di patta inviata.", fallita="no")
    assert messaggio["riuscito"] and messaggio["testo"] == "Offerta di patta inviata."


def test_la_mossa_riuscita_non_dice_niente(monkeypatch):
    import time

    coda = _esito(monkeypatch, True, fallita="no")
    time.sleep(0.2)
    assert coda.empty()


# R19: la riconnessione finche' la partita e' in corso.


class _Flusso:
    def __init__(self, righe):
        self.righe = [r.encode("utf-8") for r in righe]

    def __enter__(self):
        return iter(self.righe)

    def __exit__(self, *errore):
        return False


def _messaggi_del_filo(monkeypatch, risposte, tentativi=lichess_board.TENTATIVI_DI_FILA):
    import queue
    import threading

    risposte = list(risposte)
    monkeypatch.setattr(lichess_board, "PAUSA_INIZIALE", 0)
    monkeypatch.setattr(lichess_board.rete, "apri", lambda *a, **k: risposte.pop(0) if risposte else (None, "senza rete"))
    coda = queue.Queue()
    lichess_board._play_worker("url", "token", coda, threading.Event(), tentativi)
    messaggi = []
    while not coda.empty():
        messaggi.append(coda.get())
    return messaggi


def test_il_conto_dei_tentativi_riparte_a_ogni_riga(monkeypatch):
    in_corso = '{"type": "gameState", "moves": "e2e4", "status": "started"}\n'
    finita = '{"type": "gameState", "moves": "e2e4 e7e5", "status": "resign"}\n'
    risposte = [(None, "senza rete"), (None, "senza rete"), (_Flusso([in_corso]), None), (None, "senza rete"), (_Flusso([finita]), None)]
    messaggi = _messaggi_del_filo(monkeypatch, risposte, tentativi=3)
    tipi = [m["type"] for m in messaggi]
    # Due cadute, la riga, il flusso chiuso e un'altra caduta: con tre
    # tentativi in tutta la partita, al quarto la partita era persa.
    assert tipi == ["riconnessione", "riconnessione", "gameState", "riconnessione", "riconnessione", "gameState", "eof"]
    assert [m["tentativo"] for m in messaggi if m["type"] == "riconnessione"] == [1, 2, 1, 2]


def test_a_partita_finita_il_flusso_non_si_riprende(monkeypatch):
    finita = '{"type": "gameFull", "state": {"moves": "", "status": "aborted"}}\n'
    messaggi = _messaggi_del_filo(monkeypatch, [(_Flusso([finita]), None)])
    assert [m["type"] for m in messaggi] == ["gameFull", "eof"]


def test_senza_rete_per_troppo_ci_si_arrende(monkeypatch):
    messaggi = _messaggi_del_filo(monkeypatch, [], tentativi=4)
    assert [m["type"] for m in messaggi] == ["riconnessione"] * 3 + ["error", "eof"]


# R72: le offerte dell'avversario.


def test_le_offerte_dell_avversario_si_dicono_una_volta():
    stato = _stato()
    stato.my_color = chess.WHITE
    assert lichess_board.offerte_dell_avversario(stato, {"type": "gameState", "bdraw": True}) == ["L'avversario offre patta: draw accetta, nodraw rifiuta."]
    # La stessa offerta, al gameState dopo, non si ripete.
    assert lichess_board.offerte_dell_avversario(stato, {"type": "gameState", "bdraw": True}) == []
    # La propria offerta non si annuncia come dell'avversario.
    assert lichess_board.offerte_dell_avversario(stato, {"type": "gameState", "wdraw": True}) == []
    righe = lichess_board.offerte_dell_avversario(stato, {"type": "gameState", "btakeback": True, "bdraw": True})
    assert righe == ["L'avversario offre patta: draw accetta, nodraw rifiuta.", "L'avversario chiede di ritirare la mossa: takeback accetta, notakeback rifiuta."]
    assert any(riga.startswith("nodraw :") for riga in lichess_board._righe_del_gioco(stato))


def test_i_secondi_al_reclamo_scendono():
    """R83: claim guardava i secondi iniziali, mentre il prompt mostrava
    gia' RECLAMA."""
    import time

    stato = _stato()
    stato.claim_win_in_seconds = 30
    stato.opponent_gone_time = time.time() - 40
    assert lichess_board.secondi_al_reclamo(stato) == 0
    stato.opponent_gone_time = time.time() - 10
    assert 19 <= lichess_board.secondi_al_reclamo(stato) <= 20
    stato.claim_win_in_seconds = None
    assert lichess_board.secondi_al_reclamo(stato) == 0


def test_gli_orologi_e_la_prima_mossa():
    """R76: l'orologio locale scendeva dal primo istante, e il tempo per la
    prima mossa non si diceva."""
    import time

    stato = _stato()
    stato.my_color = chess.BLACK
    stato.started = True
    stato.white_time = stato.black_time = 60
    stato.last_clock_sync = time.time() - 5
    assert stato.get_clocks() == (60, 60)
    lichess_board.ricostruisci_le_mosse(stato, ["e2e4"])
    avviso = lichess_board.avviso_della_prima_mossa(stato, {"expiration": {"idleMillis": 5000, "millisToMove": 30000}})
    assert avviso == "Hai 25 secondi per la prima mossa: dopo, Lichess annulla la partita."
    assert lichess_board.avviso_della_prima_mossa(stato, {"expiration": {"idleMillis": 6000, "millisToMove": 30000}}) is None
    lichess_board.ricostruisci_le_mosse(stato, ["e2e4", "e7e5"])
    bianco, nero = stato.get_clocks()
    assert bianco < 60 and nero == 60



def _partita_di_dodici_semimosse():
    stato = _stato()
    stato.game_id = "abcd1234"
    stato.white_player = "Bianco (1500)"
    stato.black_player = "Nero (1500)"
    for san in ("e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7", "Re1", "b5"):
        stato.move_history.append(san)
    return stato


def _pgn_nuovi(prima):
    import os

    from orologic_modules import config

    cartella = config.percorso_salvataggio("pgn")
    return [os.path.join(cartella, nome) for nome in sorted(set(os.listdir(cartella)) - prima)] if os.path.isdir(cartella) else []


def _pgn_di_adesso():
    import os

    from orologic_modules import config

    cartella = config.percorso_salvataggio("pgn")
    return set(os.listdir(cartella)) if os.path.isdir(cartella) else set()


def test_la_ricostruzione_locale_si_salva_prima_della_rete(monkeypatch):
    """R107: il salvataggio di fine partita scaricava per primo il PGN
    ufficiale, e chiudendo Orologic durante lo scaricamento non si salvava
    niente. Ora la ricostruzione locale c'e' gia' quando si chiede la rete,
    e il PGN ufficiale, se arriva, ne prende il posto nello stesso file."""
    import os
    import pathlib

    from orologic_modules import rete
    from orologic_modules.easyfish import pgn_handler

    monkeypatch.setattr(pgn_handler.pyperclip, "copy", lambda _testo: None)
    prima = _pgn_di_adesso()
    stato = _partita_di_dodici_semimosse()
    alla_rete = []

    def leggi(_indirizzo, token=None):
        alla_rete.append([pathlib.Path(percorso).read_text(encoding="utf-8") for percorso in _pgn_nuovi(prima)])
        return '[Event "Rated blitz game"]\n[White "Bianco"]\n[Black "Nero"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n', None

    monkeypatch.setattr(rete, "leggi", leggi)
    try:
        lichess_board.save_lichess_game(stato, "white")
        assert len(alla_rete) == 1 and len(alla_rete[0]) == 1
        assert "6. Re1 b5" in alla_rete[0][0]
        nuovi = _pgn_nuovi(prima)
        assert len(nuovi) == 1
        with open(nuovi[0], encoding="utf-8") as file:
            assert '[Event "Rated blitz game"]' in file.read()
    finally:
        for percorso in _pgn_nuovi(prima):
            os.remove(percorso)


def test_un_errore_a_partita_in_corso_salva_la_ricostruzione(monkeypatch):
    """R107: play_game registra il salvataggio d'emergenza; un errore del
    nucleo a partita in corso salva la ricostruzione locale, senza rete."""
    import os

    import pytest

    from orologic_modules import rete
    from orologic_modules.easyfish import pgn_handler

    monkeypatch.setattr(pgn_handler.pyperclip, "copy", lambda _testo: None)
    monkeypatch.setattr(rete, "leggi", lambda *_argomenti, **_opzioni: pytest.fail("la rete non serve"))
    prima = _pgn_di_adesso()

    def gioca(_game_id, _token, _username, aperta=None):
        aperta["stato"] = _partita_di_dodici_semimosse()
        raise RuntimeError("guasto di prova")

    monkeypatch.setattr(lichess_board, "_gioca_partita", gioca)
    try:
        with pytest.raises(RuntimeError):
            lichess_board.play_game("abcd1234", "token", "prova")
        nuovi = _pgn_nuovi(prima)
        assert len(nuovi) == 1
        with open(nuovi[0], encoding="utf-8") as file:
            assert "6. Re1 b5" in file.read()
    finally:
        for percorso in _pgn_nuovi(prima):
            os.remove(percorso)
