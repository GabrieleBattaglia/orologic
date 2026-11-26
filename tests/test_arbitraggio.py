# Orologic, un'arbitraggio vero nella finestra (tappa T2 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""StartGame di game_flow, come lo lancia la voce Arbitra del menu, con un
orologio pronto: Invio a ogni domanda, poi cinque mosse. Il cruscotto deve
arrivare da solo, con le mosse a parole, gli orologi e i messaggi. Il motore
vero non parte."""

import os

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


def test_chiudere_orologic_a_partita_in_corso_salva_il_pgn(finestra, monkeypatch):
    """R11: in arbitraggio il PGN si scriveva solo dopo le domande di fine
    partita; chiudendo per sbaglio, col salvataggio automatico spento, si
    perdeva tutto."""
    salvati = []
    monkeypatch.setattr(game_flow, "salva_pgn_partita", lambda testo, nome: salvati.append((testo, nome)))
    _arbitraggio_avviato(finestra, monkeypatch)
    for passo in ("e4", "e5"):
        _scrivi(finestra, passo)
    finestra.faccia.chiudi()
    assert pompa(lambda: not finestra.nucleo.is_alive(), 10)
    assert len(salvati) == 1 and "1. e4 e5" in salvati[0][0] and "interrotta" in salvati[0][1]


def _pgn_nuovi(prima):
    """I PGN nati nella cartella pgn delle prove dopo prima."""
    from orologic_modules import config

    cartella = config.percorso_salvataggio("pgn")
    return [os.path.join(cartella, nome) for nome in sorted(set(os.listdir(cartella)) - prima)] if os.path.isdir(cartella) else []


def _pgn_di_adesso():
    from orologic_modules import config

    cartella = config.percorso_salvataggio("pgn")
    return set(os.listdir(cartella)) if os.path.isdir(cartella) else set()


def test_un_errore_a_partita_in_corso_salva_il_pgn(finestra, monkeypatch):
    """R107: il salvataggio d'emergenza scattava solo all'interruzione, e un
    errore qualunque del nucleo a partita in corso non salvava niente. Qui il
    salvataggio e' quello vero, nella cartella pgn delle prove."""

    def guasto(_testo, _stato):
        raise RuntimeError("guasto di prova")

    monkeypatch.setattr(game_flow, "commenta_mossa", guasto)
    prima = _pgn_di_adesso()
    _arbitraggio_avviato(finestra, monkeypatch)
    try:
        for passo in ("e4", "e5", ".c Un commento."):
            _scrivi(finestra, passo)
        assert pompa(lambda: not finestra.nucleo.is_alive(), 10)
        assert finestra.errori_mostrati and "guasto di prova" in finestra.errori_mostrati[0][0]
        nuovi = _pgn_nuovi(prima)
        assert len(nuovi) == 1 and "interrotta" in os.path.basename(nuovi[0])
        with open(nuovi[0], encoding="utf-8") as file:
            assert "1. e4 e5" in file.read()
    finally:
        for percorso in _pgn_nuovi(prima):
            os.remove(percorso)


def test_il_nucleo_fermo_alla_chiusura_salva_il_pgn(finestra, monkeypatch):
    """R107: se il nucleo non legge tasti per piu' di cinque secondi, per
    esempio in un'analisi lunga, la finestra usciva con os._exit e saltava
    ogni salvataggio. Ora prima chiama i salvataggi d'emergenza delle
    partite aperte."""
    import threading

    from orologic_modules import finestra as modulo_finestra

    fermo = threading.Event()
    dentro = threading.Event()

    def lungo(_testo, _stato):
        dentro.set()
        fermo.wait(20)

    monkeypatch.setattr(game_flow, "commenta_mossa", lungo)
    monkeypatch.setattr(modulo_finestra, "ATTESA_DELLA_CHIUSURA", 0.3)
    monkeypatch.setattr(engine, "CloseEngine", lambda: None)
    uscite = []
    monkeypatch.setattr(os, "_exit", uscite.append)
    prima = _pgn_di_adesso()
    _arbitraggio_avviato(finestra, monkeypatch)
    try:
        for passo in ("e4", "e5"):
            _scrivi(finestra, passo)
        for tasto in ".c Fermo qui.\r":
            finestra.faccia.premi(tasto)
        assert dentro.wait(10)
        finestra.Close()
        assert pompa(lambda: uscite, 10)
        nuovi = _pgn_nuovi(prima)
        assert len(nuovi) == 1 and "interrotta" in os.path.basename(nuovi[0])
        with open(nuovi[0], encoding="utf-8") as file:
            assert "1. e4 e5" in file.read()
    finally:
        fermo.set()
        if finestra:
            assert pompa(lambda: not finestra.nucleo.is_alive(), 10)
        for percorso in _pgn_nuovi(prima):
            os.remove(percorso)


def test_la_triplice_ripetizione_in_arbitraggio_la_assegna_l_arbitro(finestra, monkeypatch):
    """R9: in arbitraggio la triplice ripetizione chiudeva la partita
    d'ufficio, anche quando sarebbe arrivata solo con la mossa dopo. Ora
    Orologic dice che la patta si puo' richiedere, una volta, e la partita
    continua finche' l'arbitro non la assegna con .1/2."""
    _arbitraggio_avviato(finestra, monkeypatch)
    for passo in ("Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1"):
        _scrivi(finestra, passo)
    assert "Partita terminata." not in finestra.area.GetValue()
    assert "Patta" not in finestra.area.GetValue()
    _scrivi(finestra, "Ng8")
    testo = finestra.area.GetValue()
    assert testo.count("Patta richiedibile per triplice ripetizione") == 1
    assert "Partita terminata." not in testo
    _scrivi(finestra, "e4")
    assert "Partita terminata." not in finestra.area.GetValue()
    assert finestra.nucleo.is_alive()
    _scrivi(finestra, ".1/2")
    assert "Risultato assegnato: 1/2-1/2" in finestra.area.GetValue()


def test_le_mosse_annullate_due_volte_restano_nel_commento(finestra, monkeypatch):
    """R132: il commento Mosse annullate sta sulla mossa giocata dopo
    l'annullamento, e annullando anche quella si perdeva."""
    salvati = []
    monkeypatch.setattr(game_flow, "salva_pgn_partita", lambda testo, nome: salvati.append(testo))
    _arbitraggio_avviato(finestra, monkeypatch)
    for passo in ("e4", "e5", ".p", ".q", ".p", "d5", ".p", ".q", ".p", "c5", ".1/2"):
        _scrivi(finestra, passo)
    assert pompa(lambda: salvati, 10)
    assert "Mosse annullate: e5 d5" in salvati[0]


def test_la_ripresa_che_non_torna_riparte_dal_fen_anche_nel_pgn():
    """R132: se la linea rigiocata non arrivava al FEN salvato, la
    scacchiera nasceva dal FEN ma il PGN restava quello che non tornava."""
    import io

    import chess
    import chess.pgn

    pgn = chess.pgn.read_game(io.StringIO('[White "A"]\n[Black "B"]\n\n1. e4 e5 *\n'))
    fen = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2").fen()
    board, partita = game_flow.ripresa_coerente(pgn, fen)
    assert board.fen() == fen
    assert partita.headers["White"] == "A"
    assert partita.board().fen() == fen and not list(partita.mainline_moves())


def test_la_ripresa_fa_partire_l_orologio_solo_quando_si_gioca(monkeypatch):
    """R132: il filo dell'orologio partiva dentro la preparazione della
    ripresa, prima dei passi che possono cadere."""
    import chess

    orologio_di_prova = {"name": "Prova", "same_time": True, "phases": [{"white_time": 300, "black_time": 300, "white_inc": 0, "black_inc": 0, "moves": 0}], "alarms": []}
    dati = {
        "clock_config": orologio_di_prova, "board_fen": chess.Board().fen(), "white_remaining": 300, "black_remaining": 300,
        "white_phase": 0, "black_phase": 0, "white_moves": 0, "black_moves": 0, "active_color": "white", "move_history": [],
        "white_player": "A", "black_player": "B", "pgn_string": '[White "A"]\n[Black "B"]\n\n*\n',
    }
    avviati = []
    monkeypatch.setattr(game_flow.orologio, "avvia", avviati.append)
    monkeypatch.setattr(game_flow.board_utils, "LoadEcoDatabaseWithFEN", lambda _nome: {})
    ripresa = game_flow.prepara_la_ripresa(dati)
    assert avviati == []
    monkeypatch.setattr(game_flow, "_gioca_e_finalizza", lambda *_argomenti: None)
    game_flow.gioca_la_ripresa(*ripresa)
    assert avviati == [ripresa[0]]
