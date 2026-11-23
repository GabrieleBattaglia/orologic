# Orologic, prove dell'esercizio delle diagonali di MemoBoard.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La tabella delle diagonali era scritta a mano, ed era di 14 diagonali su
26: Prox poteva dare per no due case sulla stessa diagonale, il 3% delle
domande col no. Nella finestra Esc, alla prima domanda, non rispondeva: il
diario dei tasti ha mostrato che nell'area Esc arriva come pressione e mai
come carattere (Gabriele, collaudo del 23 novembre 2026)."""

import random

import wx
from conftest import attiva, pompa, rami_della_plancia

from orologic_modules import memoboard_app


def _stessa_diagonale(prima, seconda):
    return prima != seconda and abs(ord(prima[0]) - ord(seconda[0])) == abs(int(prima[1]) - int(seconda[1]))


def test_le_diagonali_sono_tutte_e_giuste():
    diagonali = memoboard_app.diagonals
    assert len(diagonali) == 26
    conosciute = {(a, b) for linea in diagonali.values() for a in linea for b in linea if a != b}
    vere = {(a, b) for a in memoboard_app.board for b in memoboard_app.board if _stessa_diagonale(a, b)}
    assert conosciute == vere
    assert diagonali["A1H8"] == ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8"]
    assert diagonali["H1A8"] == ["H1", "G2", "F3", "E4", "D5", "C6", "B7", "A8"]
    assert diagonali["A2G8"] == ["A2", "B3", "C4", "D5", "E6", "F7", "G8"]
    assert diagonali["H7G8"] == ["H7", "G8"]


def test_prox_non_da_mai_una_casa_sulla_stessa_diagonale(monkeypatch):
    monkeypatch.setattr(memoboard_app.random, "randint", random.Random(7).randint)
    for casa in memoboard_app.board:
        for _giro in range(40):
            vicina = memoboard_app.Prox(casa, "B", range_limit=7)
            assert vicina != casa
            assert not _stessa_diagonale(casa, vicina), (casa, vicina)


def test_nette_al_minuto():
    # 18 giuste e 2 sbagliate in un minuto: 16 nette.
    assert memoboard_app.nette_al_minuto(18, 20, 60) == 16
    # Chi tira a indovinare fa zero, e piu' sbagliate che giuste va sotto.
    assert memoboard_app.nette_al_minuto(10, 20, 30) == 0
    assert memoboard_app.nette_al_minuto(5, 20, 60) == -10
    assert memoboard_app.nette_al_minuto(5, 5, 0) == 0


def test_le_classifiche_salvate_si_ricalcolano_con_le_nette():
    """Le voci di prima, coi soli punti al minuto, prendono le nette da
    giuste, domande e durata, e la classifica si riordina con quelle."""
    dati = {
        "colors": [
            # Tanti punti al minuto, ma un terzo di sbagliate.
            {"username": "Veloce", "wins": 20, "repetitions": 30, "duration": 40.0, "score_per_minute": 500000},
            {"username": "Gabry", "wins": 13, "repetitions": 15, "duration": 35.02149820327759, "score_per_minute": 303070},
        ],
        "mixed": [{"username": "Gabry", "score": 1113424, "wins": 91, "repetitions": 100, "duration": 371.95}],
    }
    pulite = memoboard_app._deduplicate_scores(dati)
    colori = pulite["colors"]
    assert [voce["username"] for voce in colori] == ["Gabry", "Veloce"]
    assert round(colori[0]["net_per_minute"], 1) == 18.8
    assert colori[1]["net_per_minute"] == 15
    # La sfida mista resta ordinata per punti, senza nette.
    assert "net_per_minute" not in pulite["mixed"][0]


def test_statistiche_dei_tempi_con_mediana_giuste_e_sbagliate():
    tempi = [1.0, 1.2, 1.1, 9.0, 1.3]
    esiti = [True, True, False, True, False]
    stats = memoboard_app.compute_time_stats(tempi, esiti)
    assert stats["median"] == 1.2
    assert stats["giuste"] == [1.0, 1.2, 9.0]
    assert stats["sbagliate"] == [1.1, 1.3]
    # Con cinque domande niente quarti: sarebbero una domanda ciascuno.
    assert stats["quartiles"] == []
    testo = memoboard_app.format_time_stats_string(stats)
    assert "Media 2.7 secondi, mediana 1.2." in testo
    assert "Giuste 3, mediana 1.2 secondi; sbagliate 2, mediana 1.2 secondi." in testo
    assert "Andamento" not in testo
    # Tutte giuste: la riga delle giuste e delle sbagliate non serve.
    assert "Giuste" not in memoboard_app.format_time_stats_string(memoboard_app.compute_time_stats(tempi, [True] * 5))


def test_quarti_da_venti_domande_e_differenza_nulla_come_il_primo():
    tempi = [2.0] * 5 + [2.004] * 5 + [1.0] * 5 + [3.0] * 5
    stats = memoboard_app.compute_time_stats(tempi)
    assert [quarto["count"] for quarto in stats["quartiles"]] == [5, 5, 5, 5]
    testo = memoboard_app.format_time_stats_string(stats)
    assert "Quarto 2, domande da 6 a 10: media 2.0 secondi, come il primo." in testo
    assert "Quarto 3, domande da 11 a 15: media 1.0 secondi, cioe' 50% piu' rapido del primo." in testo
    assert "Quarto 4, domande da 16 a 20: media 3.0 secondi, cioe' 50% piu' lento del primo." in testo


def test_la_tastiera_si_svuota_alla_fine_della_pausa_di_lettura(monkeypatch):
    """Svuotata prima della domanda non bastava: il secondo Invio di una
    doppia pressione arrivava nella pausa di lettura e rispondeva alla
    domanda dopo (Gabriele, 23 novembre 2026). Si svuota quando parte il
    cronometro."""
    fatti = []
    monkeypatch.setattr(memoboard_app.strato, "svuota_tastiera", lambda: fatti.append("svuota"))

    def tasto():
        fatti.append("tasto")
        return "\r"

    monkeypatch.setattr(memoboard_app, "key", tasto)
    monkeypatch.setattr(memoboard_app.time, "sleep", lambda _secondi: fatti.append("pausa"))
    monkeypatch.setattr(memoboard_app, "Acusticator", lambda *_a, **_k: None)
    risultato = memoboard_app.ExColors(3)
    assert fatti == ["pausa", "svuota", "tasto"] * 3
    _punti, _elenco, durata, tempi, giuste, errori, esiti = risultato
    assert len(tempi) == len(esiti) == 3
    assert giuste == esiti.count(True)
    assert len(errori) == esiti.count(False)
    assert durata >= 0


def test_il_resoconto_dice_le_nette_e_la_classifica_le_usa(monkeypatch, capsys):
    monkeypatch.setattr(memoboard_app, "key", lambda *_a, **_k: "\r")
    monkeypatch.setattr(memoboard_app, "dgt", lambda *_a, **_k: "Gabry")
    monkeypatch.setattr(memoboard_app, "Acusticator", lambda *_a, **_k: None)
    salvati = []
    monkeypatch.setattr(memoboard_app, "save_scores", salvati.append)
    tutti = {"colors": [], "knights": [], "bishops": [], "mixed": []}
    registro = []
    memoboard_app.report_and_update_scores(
        tutti, "bishops", 20, 200000.0, 60.0, 18, registro, [], None, [1.0] * 20, [True] * 18 + [False] * 2
    )
    uscita = capsys.readouterr().out
    assert "Risposte esatte 90%, giuste nette al minuto 16.0." in uscita
    voce = tutti["bishops"][0]
    assert voce["net_per_minute"] == 16
    assert voce["username"] == "Gabry"
    assert salvati
    assert "giuste nette al minuto 16.0" in registro[0]


def _carattere(finestra, codice):
    evento = wx.KeyEvent(wx.wxEVT_CHAR)
    evento.SetUnicodeKey(codice)
    evento.SetKeyCode(codice)
    finestra._carattere(evento)


def _voce(finestra, inizio):
    return next(testo for _profondita, testo in rami_della_plancia(finestra) if testo.startswith(inizio))


def test_esc_alla_prima_domanda_delle_diagonali_dice_no(finestra, monkeypatch):
    import orologic
    from orologic_modules import engine

    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    monkeypatch.setattr(memoboard_app, "READING_TIME", 0.1)
    finestra.avvia_il_nucleo(lambda: orologic.esegui(con_la_finestra=True))
    assert pompa(lambda: finestra.attesa.tipo == "menu", 30)
    attiva(finestra, _voce(finestra, "memoboard"))
    assert pompa(lambda: finestra.attesa.tipo == "menu" and any(t.startswith("alfieri") for _p, t in rami_della_plancia(finestra)), 15)
    attiva(finestra, _voce(finestra, "alfieri"))
    assert pompa(lambda: finestra.attesa.tipo == "area", 15)
    for carattere in "5\r":
        _carattere(finestra, ord(carattere))
    assert pompa(lambda: finestra.area.GetValue().endswith("Pronto?"), 15)
    _carattere(finestra, 13)
    assert pompa(lambda: "Alfiere:" in finestra.area.GetValue(), 15)
    pompa(lambda: False, 0.3)
    # Il fuoco e' nell'area, e Esc da' la risposta: arriva la domanda dopo.
    # Come col tasto vero, arriva la pressione e non il carattere.
    assert wx.Window.FindFocus() is finestra.area
    evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    evento.SetKeyCode(wx.WXK_ESCAPE)
    finestra._tasto_giu(evento)
    assert pompa(lambda: finestra.area.GetValue().count("Alfiere:") == 2, 10)


def test_esc_nell_area_arriva_una_volta_sola(finestra):
    """Se un giorno Esc arrivasse anche come carattere, non deve contare
    due volte: il carattere va all'area, che non ne fa niente."""
    from GBUtils import key

    esiti = []

    def nucleo():
        esiti.append(key())
        esiti.append(key(attesa=0.5, alla_scadenza="niente"))

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.tasto)
    giu = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    giu.SetKeyCode(wx.WXK_ESCAPE)
    finestra._tasto_giu(giu)
    _carattere(finestra, wx.WXK_ESCAPE)
    assert pompa(lambda: len(esiti) == 2)
    assert esiti == ["\x1b", "niente"]
