# Orologic, prove del cruscotto (tappa T2 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il cruscotto delle partite: prima le righe, dalle funzioni pure di
cruscotto.py, poi la finestra, sul desktop nascosto, che passa da console a
cruscotto e torna, senza spostare chi legge."""

import threading
import types

import chess
from conftest import pompa
from GBUtils import key

from orologic_modules import board_utils, cruscotto, strato


def _stato_d_arbitraggio(mosse=("e4", "e5", "Nf3")):
    """Uno stato d'arbitraggio vero, cinque minuti a testa, con le mosse
    giocate, i tempi spesi e gli orologi dopo ogni mossa."""
    stato = board_utils.GameState({"phases": [{"white_time": 300, "black_time": 300, "white_inc": 0, "black_inc": 0, "moves": 40}]})
    stato.white_player = "Gabriele"
    stato.black_player = "Stockfish"
    for numero, san in enumerate(mosse):
        stato.board.push_san(san)
        stato.move_history.append(san)
        speso = 3.0 + numero
        stato.move_times.append(speso)
        if numero % 2 == 0:
            stato.white_remaining -= speso
            stato.white_moves += 1
            stato.clocks_history.append(stato.white_remaining)
        else:
            stato.black_remaining -= speso
            stato.black_moves += 1
            stato.clocks_history.append(stato.black_remaining)
    stato.active_color = "white" if stato.board.turn == chess.WHITE else "black"
    return stato


def _testi(righe, sezione):
    return [testo for nome, testo in righe if nome == sezione]


def test_le_sezioni_del_cruscotto_nell_ordine():
    righe = cruscotto.righe(cruscotto.dati_di(_stato_d_arbitraggio()), ["un messaggio"])
    ordine = []
    for nome, _testo in righe:
        if not ordine or ordine[-1] != nome:
            ordine.append(nome)
    assert ordine == ["info", "scacchiera", "orologi", "mosse", "messaggi"]
    assert _testi(righe, "messaggi") == ["Messaggi:", "un messaggio"]


def test_le_informazioni_stanno_su_poche_righe():
    info = _testi(cruscotto.righe(cruscotto.dati_di(_stato_d_arbitraggio()), []), "info")
    assert info[0] == "Bianco: Gabriele. Nero: Stockfish."
    assert info[1].startswith("Mossa 2. Tocca al Nero.")
    assert "Materiale pari." in info[1]
    assert "Mosse al controllo: 39." in info[1]


def test_la_scacchiera_dal_lato_del_bianco_e_del_nero():
    board = chess.Board()
    bianco = cruscotto.scacchiera(board)
    assert bianco[0] == " abcdefgh"
    assert bianco[1] == "8rnbqkbnr8"
    assert bianco[-2] == "1RNBQKBNR1"
    nero = cruscotto.scacchiera(board, dal_nero=True)
    assert nero[0] == " hgfedcba"
    assert nero[1] == "1RNBKQBNR1"


def test_gli_orologi_su_una_riga_con_il_consumo():
    orologi = _testi(cruscotto.righe(cruscotto.dati_di(_stato_d_arbitraggio()), []), "orologi")
    assert len(orologi) == 1
    riga = orologi[0]
    assert riga.startswith("Bianco 4 minuti e 52 secondi, 3%.")
    assert "Nero 4 minuti e 56 secondi, 1%, in moto." in riga
    assert riga.endswith("Il Nero ha 4 secondi in più.")


def test_le_due_semimosse_sulla_stessa_riga():
    """Come l'esempio di Gabriele: la mossa a parole, poi il consumo
    dell'orologio dopo la mossa, poi il tempo speso."""
    mosse = _testi(cruscotto.righe(cruscotto.dati_di(_stato_d_arbitraggio()), []), "mosse")
    assert mosse[0] == "Ultime mosse:"
    assert len(mosse) == 3
    assert mosse[1].startswith("1. ")
    assert " 1% in 3 secondi; " in mosse[1]
    assert mosse[1].endswith(" 1% in 4 secondi.")
    assert mosse[2].startswith("2. ")
    assert mosse[2].endswith(" 3% in 5 secondi.")


def test_si_mostrano_le_ultime_sei_mosse():
    giocate = ["Nf3", "Nf6", "Ng1", "Ng8"] * 4
    mosse = _testi(cruscotto.righe(cruscotto.dati_di(_stato_d_arbitraggio(giocate)), []), "mosse")
    assert len(mosse) == 1 + cruscotto.MOSSE_MOSTRATE
    assert mosse[1].startswith("3. ")
    assert mosse[-1].startswith("8. ")


def test_la_partita_che_comincia_col_nero():
    board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
    for san in ("e5", "Nf3"):
        board.push_san(san)
    stato = types.SimpleNamespace(board=board, move_history=["e5", "Nf3"], white_remaining=60.0, black_remaining=60.0)
    mosse = _testi(cruscotto.righe(cruscotto.dati_di(stato), []), "mosse")
    assert mosse[1].startswith("1... ")
    assert mosse[2].startswith("2. ")


def test_tempo_senza_scacchiera():
    stato = types.SimpleNamespace(senza_scacchiera=True, board=chess.Board(), move_history=["e4", "c5", "Nf3"], white_remaining=100.0, black_remaining=90.0, active_color="black")
    righe = cruscotto.righe(cruscotto.dati_di(stato), [])
    assert not _testi(righe, "scacchiera")
    assert _testi(righe, "mosse")[1:] == ["1. e4; c5.", "2. Nf3."]
    assert "Tocca al Nero." in _testi(righe, "info")[1]


def test_la_scacchiera_lasciata_da_easyfish():
    board = chess.Board()
    board.push_san("d4")
    stato = types.SimpleNamespace(scacchiera_del_cruscotto=board, move_history=["d4"], white_remaining=50.0, black_remaining=50.0, human_color=chess.BLACK)
    dati = cruscotto.dati_di(stato)
    assert dati["board"].move_stack == board.move_stack
    assert _testi(cruscotto.righe(dati, []), "scacchiera")[0] == " hgfedcba"


def test_fuori_dalla_partita_fornisci_non_fa_niente(monkeypatch):
    chiamate = []
    monkeypatch.setattr(strato.faccia(), "cruscotto", lambda fornitore, comandi=None: chiamate.append(fornitore))
    strato.fornisci(dict)
    assert chiamate == []
    with strato.partita():
        strato.fornisci(len)
        with strato.partita():
            pass
    assert chiamate == [len, None]


# La finestra.


def test_la_finestra_passa_al_cruscotto_e_torna(finestra):
    stato = _stato_d_arbitraggio()
    via = threading.Event()
    fine = threading.Event()

    def nucleo():
        print("Prima della partita.")
        with strato.partita():
            strato.fornisci(lambda: cruscotto.dati_di(stato))
            print("La partita comincia.")
            via.wait(10)
            stato.white_remaining -= 7
            print("Un messaggio a meta' partita.")
            key("Mossa: ")
        print("Dopo la partita.")
        fine.wait(10)

    finestra.avvia_il_nucleo(nucleo)
    try:
        _segue_la_partita(finestra, via, fine)
    finally:
        via.set()
        fine.set()


def _segue_la_partita(finestra, via, fine):
    assert pompa(lambda: finestra.fornitore is not None and ("messaggi", "La partita comincia.") in finestra.mostrate)
    sezioni = {nome for nome, _testo in finestra.mostrate}
    assert sezioni == {"info", "scacchiera", "orologi", "mosse", "messaggi", "prompt"}
    assert "Prima della partita." not in finestra.area.GetValue()
    # Il cursore sulla terza riga della scacchiera: i rinfreschi non lo spostano.
    riga = [i for i, (nome, _t) in enumerate(finestra.mostrate) if nome == "scacchiera"][3]
    finestra._vai(riga, 4)
    via.set()
    assert pompa(lambda: finestra.mostrate[-1][1] == "Mossa: ")
    assert ("messaggi", "Un messaggio a meta' partita.") in finestra.mostrate
    assert pompa(lambda: False, 1.3) is False
    assert finestra._riga_e_colonna() == (riga, 4)
    assert finestra.area.GetValue() == "\n".join(testo for _n, testo in finestra.mostrate)
    # Il tasto riporta al prompt e chiude la partita: torna la console intera.
    finestra._manda("x")
    assert pompa(lambda: finestra.fornitore is None and "Dopo la partita." in finestra.area.GetValue())
    testo = finestra.area.GetValue()
    for riga_attesa in ("Prima della partita.", "La partita comincia.", "Un messaggio a meta' partita.", "Mossa: Dopo la partita."):
        assert riga_attesa in testo
    assert "Ultime mosse:" not in testo
    fine.set()
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_il_ciclo_d_attesa_vero_porta_il_cruscotto(finestra):
    stato = _stato_d_arbitraggio()
    stato.flag_fallen = False
    stato.ignore_clock = False
    stato.refresh_interval = 0
    esito = {}

    def nucleo():
        from orologic_modules import game_flow

        with strato.partita():
            esito["mossa"] = game_flow.async_arbitration_input(stato, lambda: board_utils.prompt_partita(stato))

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.fornitore is not None and len(finestra.mostrate) > 10)
    for tasto in "Nc6\r":
        finestra.faccia.premi(tasto)
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert esito["mossa"] == "Nc6"
    assert pompa(lambda: finestra.fornitore is None)
