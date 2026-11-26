# Orologic, un'arbitraggio vero nella finestra (tappa T2 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""StartGame di game_flow, come lo lancia la voce Arbitra del menu, con un
orologio pronto: Invio a ogni domanda, poi cinque mosse. Il cruscotto deve
arrivare da solo, con le mosse a parole, gli orologi e i messaggi. Il motore
vero non parte."""

from conftest import pompa

from orologic_modules import engine, game_flow


def _fermo(finestra, secondi=0.3):
    """Aspetta che l'area smetta di cambiare."""
    prima = None
    for _ in range(40):
        pompa(lambda: False, secondi)
        adesso = finestra.area.GetValue()
        if adesso == prima:
            return
        prima = adesso


def test_un_arbitraggio_vero_nel_cruscotto(finestra, monkeypatch):
    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    orologio = {"name": "Prova", "same_time": True, "phases": [{"white_time": 300, "black_time": 300, "white_inc": 0, "black_inc": 0, "moves": 0}], "alarms": []}
    finestra.avvia_il_nucleo(lambda: game_flow.StartGame(orologio))
    for _domanda in range(15):
        _fermo(finestra)
        if finestra.fornitore is not None:
            break
        finestra.faccia.premi("\r")
    assert finestra.fornitore is not None
    _fermo(finestra, 0.6)
    for mossa in ("e4", "e5", "Nf3", "Nc6", "Bb5"):
        for tasto in mossa + "\r":
            finestra.faccia.premi(tasto)
        _fermo(finestra)
    righe = finestra.mostrate
    sezioni = [nome for nome, _testo in righe]
    assert sezioni.count("scacchiera") == 10
    mosse = [testo for nome, testo in righe if nome == "mosse"]
    assert mosse[0] == "Ultime mosse:"
    assert mosse[-1].startswith("3. alfiere in ")
    assert sum(1 for riga in mosse if "; " in riga) >= 2
    messaggi = [testo for nome, testo in righe if nome == "messaggi"]
    assert messaggi[0] == "Messaggi:"
    assert any("Ruy Lopez" in testo for testo in messaggi)
    # La riga del prompt con la mossa scritta non e' un messaggio.
    assert not any(testo.startswith(("2... Nc6 ", "2. Nf3 ")) for testo in messaggi)
    assert righe[-1] == ("prompt", "3. Bb5 ")
    detti = [testo for testo, _interrompi in finestra.sintesi.detti]
    assert any(testo.startswith("Bianco: alfiere in ") for testo in detti)


def _scrivi(finestra, testo):
    for tasto in testo + "\r":
        finestra.faccia.premi(tasto)
    _fermo(finestra)


def _arbitraggio_avviato(finestra, monkeypatch):
    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    orologio = {"name": "Prova", "same_time": True, "phases": [{"white_time": 300, "black_time": 300, "white_inc": 0, "black_inc": 0, "moves": 0}], "alarms": []}
    finestra.avvia_il_nucleo(lambda: game_flow.StartGame(orologio))
    for _domanda in range(15):
        _fermo(finestra)
        if finestra.fornitore is not None:
            break
        finestra.faccia.premi("\r")
    assert finestra.fornitore is not None
    _fermo(finestra, 0.6)


def test_due_annullamenti_nella_stessa_partita(finestra, monkeypatch):
    """Rilievo R3 della revisione 2: dopo il primo .q e una mossa nuova, che
    scrive nel PGN il commento delle mosse annullate, il secondo .q faceva
    cadere la partita."""
    _arbitraggio_avviato(finestra, monkeypatch)
    for passo in ("e4", "e5", ".p", ".q", ".p", "e6", ".p", ".q"):
        _scrivi(finestra, passo)
    assert finestra.nucleo.is_alive()
    assert [mossa.uci() for mossa in finestra.fornitore()["board"].move_stack] == ["e2e4"]


def test_la_scacchiera_della_partita_ripresa_ha_le_sue_mosse():
    """Rilievo R4 della revisione 2: la partita ripresa dal salvataggio
    automatico rigioca la linea del PGN, e .q trova la mossa da togliere."""
    import io

    import chess
    import chess.pgn

    giocata = chess.Board()
    for san in ("e4", "e5", "Nf3"):
        giocata.push_san(san)
    pgn = chess.pgn.read_game(io.StringIO(str(chess.pgn.Game.from_board(giocata))))
    ripresa = game_flow.scacchiera_ripresa(pgn, giocata.fen())
    assert [mossa.uci() for mossa in ripresa.move_stack] == ["e2e4", "e7e5", "g1f3"]
    ripresa.pop()
    assert ripresa.fen() == chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2").fen()
    # Se la linea non arriva al FEN salvato, vale il FEN, come prima.
    altra = game_flow.scacchiera_ripresa(pgn, chess.Board().fen())
    assert altra.move_stack == [] and altra.fen() == chess.Board().fen()
    assert game_flow.scacchiera_ripresa(None, giocata.fen()).fen() == giocata.fen()


def test_il_q_senza_mosse_nella_pila_lo_dice(monkeypatch):
    from orologic_modules import board_utils

    monkeypatch.setattr(game_flow, "Acusticator", lambda *_a, **_o: None)
    stato = board_utils.GameState({"phases": [{"white_time": 300, "black_time": 300, "white_inc": 0, "black_inc": 0, "moves": 40}]})
    stato.move_history = ["e4"]
    stato.paused = True
    assert game_flow.annulla_ultima_mossa(stato) is False
    assert stato.move_history == ["e4"]


def test_la_ripresa_mette_da_parte_il_file_rotto_e_non_cancella_quello_buono(tmp_path, monkeypatch):
    """Rilievo R5 della revisione 2: un file di ripresa che non si legge si
    mette da parte; un errore della partita ripresa non lo cancella piu'."""
    import json

    import pytest

    import orologic

    rotto = tmp_path / "autosave.json"
    rotto.write_text("{ rotto", encoding="utf-8")
    orologic.riprendi_dal_salvataggio(str(rotto))
    assert not rotto.exists()
    assert [percorso.name.startswith("autosave.json.danneggiato-") for percorso in tmp_path.iterdir()] == [True]
    buono = tmp_path / "buono.json"
    buono.write_text(json.dumps({"qualcosa": 1}), encoding="utf-8")
    monkeypatch.setattr(game_flow, "prepara_la_ripresa", lambda _dati: ("stato", None, False))

    def partita_che_cade(*_ripresa):
        raise RuntimeError("errore della partita")

    monkeypatch.setattr(game_flow, "gioca_la_ripresa", partita_che_cade)
    with pytest.raises(RuntimeError):
        orologic.riprendi_dal_salvataggio(str(buono))
    assert buono.exists()



def test_il_commento_resta_come_l_ha_scritto_l_arbitro(finestra, monkeypatch):
    """R48: il commento .c arrivava in minuscolo e senza i punti finali."""
    commenti = []
    monkeypatch.setattr(game_flow, "commenta_mossa", lambda testo, _stato: commenti.append(testo))
    _arbitraggio_avviato(finestra, monkeypatch)
    for passo in ("e4", ".p", ".c Rossi propone patta.", ".p"):
        _scrivi(finestra, passo)
    assert commenti == [".c Rossi propone patta."]
