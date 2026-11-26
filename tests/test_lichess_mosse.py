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
