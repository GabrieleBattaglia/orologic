# Orologic, prove del salvataggio all'uscita da Easyfish (rilievo R12 della
# revisione 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""All'uscita la partita modificata si salva guardando la partita, non la
scacchiera del momento: chi tornava all'inizio e poi usciva la perdeva."""

from conftest import pompa
from test_easyfish_finestra import _premi, partita

from orologic_modules import engine as orologic_engine
from orologic_modules import finestra_navigatore
from orologic_modules.easyfish import easyfish_app


def test_chi_torna_all_inizio_e_esce_salva_la_partita(finestra, monkeypatch):
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    salvate = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: salvate.append(g) or True)
    # Il navigatore riporta alla posizione iniziale, la radice della partita.
    monkeypatch.setattr(finestra_navigatore, "naviga", lambda _genitore, partita_navigata, _nodo, *_altro: (partita_navigata, False))
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, "_Bella\r")
    assert pompa(lambda: game.end().comment == "Bella")
    _premi(finestra, ".na\r")
    assert pompa(lambda: finestra.fornitore is not None and not finestra.fornitore()["board"].move_stack)
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert salvate == [game]


def test_il_matto_in_una_variante_non_cambia_il_risultato(monkeypatch):
    """R14: una variante che da' matto col Bianco, in una partita finita
    0-1, scriveva 1-0 nell'intestazione Result."""
    import io

    import chess.pgn

    monkeypatch.setattr(easyfish_app, "Acusticator", lambda *a, **k: None)
    game = chess.pgn.read_game(io.StringIO('[Result "0-1"]\n\n1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Nc3 Bc5 5. d3 0-1'))
    # Dopo 3...Nf6 la linea principale gioca 4.Nc3; la variante il matto.
    nf6 = game.variations[0].variations[0].variations[0].variations[0].variations[0].variations[0]
    matto = nf6.add_variation(chess.Move.from_uci("h5f7"))
    assert matto.board().is_checkmate() and not matto.is_mainline()
    easyfish_app.CheckGameOver(matto.board(), matto)
    assert game.headers["Result"] == "0-1"


def test_il_matto_alla_fine_della_linea_principale_si_segna(monkeypatch):
    import io

    import chess.pgn

    monkeypatch.setattr(easyfish_app, "Acusticator", lambda *a, **k: None)
    game = chess.pgn.read_game(io.StringIO("1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# *"))
    easyfish_app.CheckGameOver(game.end().board(), game.end())
    assert game.headers["Result"] == "1-0"


def test_la_tripla_ripetizione_che_arriverebbe_non_scrive_il_risultato(monkeypatch):
    """R14, con la regola di R9: la ripetizione che arriverebbe solo con la
    mossa dopo non e' una patta, e Result resta com'era. Quella avvenuta, in
    Easyfish, chiude: la prova e' in test_fine_partita."""
    import io

    import chess.pgn

    from orologic_modules import board_utils

    monkeypatch.setattr(board_utils, "suona_la_fine", lambda: None)
    game = chess.pgn.read_game(io.StringIO("1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 *"))
    assert game.end().board().can_claim_threefold_repetition()
    easyfish_app.CheckGameOver(game.end().board(), game.end())
    assert game.headers["Result"] == "*"


def test_se_il_salvataggio_fallisce_la_partita_resta(finestra, monkeypatch):
    """R52: SaveGameToFile non diceva se era riuscita, e .n, .pa, .fg e gli
    altri buttavano subito la partita."""
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    tentativi = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: tentativi.append(g) and False)
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, "_Bella\r")
    assert pompa(lambda: game.end().comment == "Bella")
    _premi(finestra, ".n\r")
    assert pompa(lambda: "resta aperta" in finestra.area.GetValue())
    assert tentativi == [game]
    assert len(finestra.fornitore()["board"].move_stack) == 5
    # All'uscita la domanda: Invio esce lo stesso.
    _premi(finestra, ".\r")
    assert pompa(lambda: finestra.attesa.tipo == "sino" or "Esco lo stesso" in finestra.area.GetValue())
    _premi(finestra, "\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_save_game_to_file_dice_se_e_riuscita(monkeypatch):
    import chess.pgn

    from orologic_modules import game_flow
    from orologic_modules.easyfish import pgn_handler

    monkeypatch.setattr(pgn_handler.pyperclip, "copy", lambda testo: None)
    monkeypatch.setattr(game_flow, "salva_pgn_partita", lambda testo, nome: None)
    assert pgn_handler.SaveGameToFile(chess.pgn.Game()) is False
    monkeypatch.setattr(game_flow, "salva_pgn_partita", lambda testo, nome: "C:/x.pgn")
    assert pgn_handler.SaveGameToFile(chess.pgn.Game()) is True


def test_gli_appunti_occupati_non_fanno_cadere(monkeypatch, capsys):
    """R53: le letture degli appunti di Easyfish stavano fuori da ogni
    protezione."""
    import pyperclip

    from orologic_modules import ui

    def occupati():
        raise pyperclip.PyperclipException("occupati")

    monkeypatch.setattr(ui.pyperclip, "paste", occupati)
    assert ui.leggi_dagli_appunti() is None
    assert "Impossibile accedere agli appunti" in capsys.readouterr().out


def test_fg_rifiuta_una_posizione_senza_re(finestra, monkeypatch):
    """R54: .fg controllava solo la sintassi del FEN."""
    from orologic_modules import ui

    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: True)
    monkeypatch.setattr(ui.pyperclip, "paste", lambda: "8/8/8/8/8/8/8/4k3 w - - 0 1")
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, ".fg\r")
    assert pompa(lambda: "Manca il Re bianco." in finestra.area.GetValue())
    assert len(finestra.fornitore()["board"].move_stack) == 5
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_chiudere_il_navigatore_non_aspetta_l_analisi(finestra, monkeypatch):
    """R85: chiudendo il navigatore mentre Analizza lavora, il filo della
    finestra aspettava la fine dell'analisi, anche mezz'ora."""
    import threading
    import time

    sblocca = threading.Event()
    fili = []

    def analizza_lenta(_board):
        fili.append(threading.current_thread())
        sblocca.wait(10)
        return (["1. +0.30 e5"], None, None)

    monkeypatch.setattr(finestra_navigatore, "analizza", analizza_lenta)

    def modale(dialogo):
        dialogo.analizza()
        return 0

    monkeypatch.setattr(finestra_navigatore.Navigatore, "ShowModal", modale)
    game = partita()
    inizio = time.monotonic()
    finestra_navigatore.naviga(finestra, game, game.end(), lambda *_a: True, lambda *_a, **_k: None, lambda _righe: None)
    assert time.monotonic() - inizio < 2
    sblocca.set()
    assert pompa(lambda: fili and not fili[0].is_alive())
    pompa(lambda: False, 0.1)


def test_i_comandi_con_lo_spazio_arrivano_al_loro_ramo(finestra, monkeypatch):
    """R95: ".cso on", ".a 5" e ".k 12" tenevano lo spazio e la parola nel
    comando ripulito, e non arrivavano al loro ramo."""
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: True)
    monkeypatch.setattr(easyfish_app, "show_output_on_board", False)
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, ".cso on\r")
    assert pompa(lambda: easyfish_app.show_output_on_board is True)
    _premi(finestra, ".k 2\r")
    assert pompa(lambda: len(finestra.fornitore()["board"].move_stack) == 2)
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_chiudere_orologic_salva_la_partita_modificata(finestra, monkeypatch):
    """R11: in Easyfish la partita modificata si salvava solo col punto, e
    chiudendo la finestra mosse, varianti e commenti si perdevano."""
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    salvate = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: salvate.append(g) or True)
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, "_Bella\r")
    assert pompa(lambda: game.end().comment == "Bella")
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    finestra.faccia.chiudi()
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert salvate == [game]



def test_il_commento_scritto_nell_esploratore_si_salva_alla_chiusura(finestra, monkeypatch):
    """R107: la bandiera della partita modificata si rinfrescava solo in
    testa al ciclo di Easyfish, e un commento scritto nell'esploratore, in
    una partita fin li' non modificata, non si salvava chiudendo Orologic
    dall'esploratore. Il salvataggio e' quello vero, con gli appunti finti."""
    import os

    from orologic_modules import config
    from orologic_modules.easyfish import pgn_handler

    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    copiati = []
    monkeypatch.setattr(pgn_handler.pyperclip, "copy", copiati.append)
    cartella = config.percorso_salvataggio("pgn")
    prima = set(os.listdir(cartella)) if os.path.isdir(cartella) else set()

    def contesto():
        dati = finestra.fornitore() if finestra.fornitore is not None else None
        return dati and dati["contesto"]

    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    try:
        assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
        _premi(finestra, ".e\r")
        assert pompa(lambda: finestra.attesa.tasto and contesto() == "esploratore")
        _premi(finestra, "_")
        assert pompa(lambda: not finestra.attesa.tasto)
        _premi(finestra, "Bella\r")
        assert pompa(lambda: game.end().comment == "Bella")
        assert pompa(lambda: finestra.attesa.tasto and contesto() == "esploratore")
        finestra.faccia.chiudi()
        assert pompa(lambda: not finestra.nucleo.is_alive())
        nuovi = sorted(set(os.listdir(cartella)) - prima)
        assert len(nuovi) == 1
        with open(os.path.join(cartella, nuovi[0]), encoding="utf-8") as file:
            assert "Bella" in file.read()
        assert copiati and "Bella" in copiati[-1]
    finally:
        for nome in sorted(set(os.listdir(cartella)) - prima) if os.path.isdir(cartella) else ():
            os.remove(os.path.join(cartella, nome))


def test_un_errore_in_easyfish_salva_la_partita_modificata(finestra, monkeypatch):
    """R107: in Easyfish il salvataggio d'emergenza scattava solo
    all'interruzione; un errore del nucleo con la partita modificata la
    perdeva."""
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    salvate = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: salvate.append(g) or True)

    def guasto(*_argomenti, **_opzioni):
        raise RuntimeError("guasto di prova")

    monkeypatch.setattr(easyfish_app, "AddingPGNTAGS", guasto)
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, "_Bella\r")
    assert pompa(lambda: game.end().comment == "Bella")
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, ".pt\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert finestra.errori_mostrati and "guasto di prova" in finestra.errori_mostrati[0][0]
    assert salvate == [game]


def _partita_dal_testo(testo):
    import io

    import chess.pgn

    return chess.pgn.read_game(io.StringIO(testo))


def test_la_variante_col_matto_promossa_scrive_il_risultato(finestra, monkeypatch):
    """R112: dopo .vm, che promuove a linea principale una variante finita
    col matto, Result restava quello di prima, perche' la posizione non
    cambiava e il controllo della fine partita non rigirava."""
    game = _partita_dal_testo('[Result "0-1"]\n\n1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. d3 (4. Qxf7#) 0-1\n')
    matto = game.variations[0].variations[0].variations[0].variations[0].variations[0].variations[0].variations[1]
    assert matto.san() == "Qxf7#"
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    salvate = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: salvate.append(g) or True)
    monkeypatch.setattr(finestra_navigatore, "naviga", lambda _genitore, _partita, _nodo, *_altro: (matto, False))
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, ".na\r")
    assert pompa(lambda: finestra.fornitore is not None and finestra.fornitore()["board"].is_checkmate())
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, ".vm\r")
    assert pompa(lambda: game.headers["Result"] == "1-0")
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert salvate == [game] and game.headers["Result"] == "1-0"


def test_tolto_il_matto_il_risultato_torna_l_asterisco(finestra, monkeypatch):
    """R112: dopo .u dal matto alla fine della linea principale Result
    restava quello del matto, scritto da Orologic: la partita salvata e il
    nome del file avevano un esito che la partita non ha piu'."""
    game = _partita_dal_testo("1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# *\n")
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    salvate = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda g: salvate.append(g) or True)
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: game.headers["Result"] == "1-0")
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    _premi(finestra, ".u\r")
    assert pompa(lambda: game.headers["Result"] == "*")
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert salvate == [game] and game.headers["Result"] == "*"
