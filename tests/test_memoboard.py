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
