# Orologic, prove delle tipologie del controllo del tempo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il motore di controlli.py, tipologia per tipologia, coi conti dei
manuali DGT: lo stato della partita vero, il tempo che corre dato a mano
con scorri, le mosse con a_mossa_fatta, il cambio di tratto e
a_turno_passato, l'annullamento dell'arbitro. In fondo il filo
dell'orologio vero, per la bandierina e il conta in su."""

import time

import pytest

from orologic_modules import board_utils, controlli, orologio


def _partita(*fasi):
    """Una partita con le fasi date come (secondi, tipologia, valori, mosse)."""
    config = {"name": "prova", "phases": []}
    for secondi, codice, valori, mosse in fasi:
        fase = {"white_time": secondi, "black_time": secondi, "moves": mosse, "tipo": codice}
        for chiave, numero in valori.items():
            fase[f"white_{chiave}"] = fase[f"black_{chiave}"] = numero
        config["phases"].append(controlli.completa(fase))
    stato = board_utils.GameState(config)
    controlli.inizio_partita(stato)
    return stato


def _corre(stato, secondi):
    with orologio.blocco():
        return controlli.scorri(stato, stato.active_color == "white", secondi)


def _mossa(stato):
    """La mossa di chi ha il tratto, come la fa l'arbitraggio."""
    registro = controlli.a_mossa_fatta(stato, stato.active_color == "white")
    stato.switch_turn()
    return controlli.a_turno_passato(stato, registro)


@pytest.fixture(autouse=True)
def senza_suoni(monkeypatch):
    monkeypatch.setattr(controlli, "suona", lambda _evento: None)
    monkeypatch.setattr(board_utils, "Acusticator", lambda *_a, **_o: None)


def test_incremento_dopo_la_mossa_come_sempre():
    stato = _partita((60, "dopo", {"inc": 5}, 0))
    assert (stato.white_remaining, stato.black_remaining) == (60, 60)
    _corre(stato, 10)
    assert _mossa(stato) == 55
    # L'arbitro annulla: via l'incremento, il tempo speso resta speso.
    stato.active_color = "white"
    assert controlli.annulla(stato, True) == 5
    assert stato.white_remaining == 50


def test_incremento_prima_della_mossa_fischer():
    stato = _partita((60, "prima", {"inc": 5}, 1), (30, "prima", {"inc": 10}, 0))
    # L'incremento c'e' gia' alla partenza, per i due colori.
    assert (stato.white_remaining, stato.black_remaining) == (65, 65)
    _corre(stato, 10)
    # Prima mossa del Bianco: fase 2, piu' i 30 secondi e l'incremento
    # della fase in cui giochera' la prossima.
    assert _mossa(stato) == 55 + 30 + 10
    _corre(stato, 4)
    assert _mossa(stato) == 61 + 30 + 10


def test_ritardo_bronstein():
    stato = _partita((60, "bronstein", {"ritardo": 5}, 0))
    assert stato.white_remaining == 65
    _corre(stato, 3)
    # Torna il tempo usato fino al ritardo, mai oltre l'inizio del turno.
    assert _mossa(stato) == 65
    _corre(stato, 8)
    assert _mossa(stato) == 62


def test_ritardo_semplice():
    stato = _partita((60, "ritardo", {"ritardo": 5}, 0))
    assert stato.white_remaining == 60
    _corre(stato, 3)
    assert stato.white_remaining == 60
    _corre(stato, 4)
    assert stato.white_remaining == 58
    _mossa(stato)
    # Il turno del Nero comincia col ritardo intero.
    assert stato.controllo["black"]["ritardo"] == 5
    _corre(stato, 2)
    assert stato.black_remaining == 60


def test_clessidra():
    stato = _partita((60, "clessidra", {}, 0))
    _corre(stato, 10)
    assert (stato.white_remaining, stato.black_remaining) == (50, 70)


def test_byo_yomi_giapponese():
    stato = _partita((10, "byoyomi", {"periodo": 5, "periodi": 3}, 0))
    avvisi = _corre(stato, 12)
    assert stato.white_remaining == 13
    assert avvisi[0][1] == "byoyomi"
    avvisi = _corre(stato, 4)
    assert stato.white_remaining == 9
    assert avvisi == [("Bianco: periodo consumato, ne restano 2.", "periodo")]
    # La mossa dentro il periodo lo fa ripartire intero.
    assert _mossa(stato) == 10
    # Annullata, il periodo torna com'era, e il byo-yomi resta.
    stato.active_color = "white"
    controlli.annulla(stato, True)
    assert stato.white_remaining == 9
    assert stato.controllo["white"]["oltre"] == "byoyomi"
    _corre(stato, 9.5)
    assert controlli.scaduto(stato, True)


def test_byo_yomi_canadese():
    stato = _partita((10, "canadese", {"minuti_periodo": 2, "mosse_periodo": 3}, 0))
    avvisi = _corre(stato, 12)
    assert stato.white_remaining == 118
    assert avvisi[0][1] == "canadese"
    # La mossa in corso e' la prima del periodo; alla terza, il periodo riparte.
    for mosse_restanti in (2, 1):
        _mossa(stato)
        assert stato.controllo["white"]["mosse_periodo"] == mosse_restanti
        _corre(stato, 1)
        _mossa(stato)
        _corre(stato, 10)
    assert _mossa(stato) == 120
    assert stato.controllo["white"]["mosse_periodo"] == 3


def test_conta_in_su():
    stato = _partita((5, "contasu", {}, 0))
    avvisi = _corre(stato, 7)
    assert stato.white_remaining == 2
    assert avvisi[0][1] == "contasu"
    assert not controlli.scaduto(stato, True)
    _corre(stato, 3)
    assert stato.white_remaining == 5


def test_gli_errori_delle_fasi():
    fase = controlli.completa({"white_time": 0, "black_time": 0, "moves": 0, "tipo": "byoyomi"})
    assert controlli.errori_della_fase(fase, "white", 1) == []
    fase = controlli.completa({"white_time": 0, "black_time": 0, "moves": 0, "tipo": "prima", "white_inc": 5})
    assert controlli.errori_della_fase(fase, "white", 1) == []
    fase = controlli.completa({"white_time": 1, "black_time": 1, "moves": 0, "tipo": "dopo"})
    assert controlli.errori_della_fase(fase, "white", 1)
    fasi = [controlli.completa({"white_time": 60, "moves": 40, "tipo": "contasu"}), controlli.completa({"white_time": 60, "moves": 0})]
    assert controlli.errori_delle_fasi(fasi) == ["Fase 1: Conta in su sta solo nell'ultima fase."]


def test_il_tag_timecontrol():
    from orologic_modules import clock

    assert clock.generate_time_control_string({"phases": [{"white_time": 5400, "white_inc": 30, "moves": 40}, {"white_time": 1800, "white_inc": 30, "moves": 0}]}) == "40/5400+30, 1800+30"
    assert clock.generate_time_control_string({"phases": [{"white_time": 180, "moves": 0, "tipo": "clessidra"}]}) == "*180"


def test_il_filo_dell_orologio(monkeypatch):
    monkeypatch.setattr(orologio, "_suona_bandierina", lambda: None)
    monkeypatch.setattr(orologio, "PASSO", 0.02)
    cade = _partita((0.2, "dopo", {}, 0))
    conta = _partita((0.2, "contasu", {}, 0))
    for stato in (cade, conta):
        orologio.avvia(stato)
    time.sleep(0.6)
    for stato in (cade, conta):
        stato.game_over = True
    assert cade.flag_fallen and cade.bianco_scaduto
    assert not conta.flag_fallen
    assert conta.white_remaining > 0.2
