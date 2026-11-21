# Orologic, le prove che prendono il posto delle voci del collaudo a mano (T5).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Quello che il collaudo chiedeva a Gabriele e che una prova sa vedere da
sola: la finestra del caffè e il suo PayPal, la lingua cambiata che al
riavvio parla davvero, i campi dei numeri che stanno nei loro limiti, le
lingue dell'installatore, e i rami della plancia, che devono essere voci
vere dei menu di Orologic. A Gabriele restano NVDA, le orecchie e Lichess."""

import ast
import os
import re
import shutil
import time

import pytest
import wx
from conftest import pompa

from orologic_modules import avvio, dialoghi, plancia

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tasto(codice, oggetto):
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(codice)
    evento.SetEventObject(oggetto)
    return evento


# Il caffè.


def test_il_caffe_dona_con_paypal(app, monkeypatch):
    aperti = []
    suonati = []
    monkeypatch.setattr(dialoghi.webbrowser, "open", aperti.append)
    caffe = dialoghi.Caffe(None, "Offrimi un caffè, se ti va.", suonati.append)
    chiuso = []
    monkeypatch.setattr(caffe, "EndModal", chiuso.append)
    try:
        assert caffe.IsMaximized()
        assert caffe.testo.GetValue() == "Offrimi un caffè, se ti va."
        assert [b.GetLabel() for b in caffe.GetChildren()[0].GetChildren() if isinstance(b, wx.Button)] == ["Dona con &PayPal", "&Chiudi"]
        caffe.dona()
        assert aperti == [dialoghi.INDIRIZZO_PAYPAL]
        assert suonati == ["caffe_paypal"]
        assert chiuso == [wx.ID_OK]
    finally:
        caffe.Destroy()


def test_l_invio_rimandato_non_chiude_il_caffe(app, monkeypatch):
    """L'Invio della voce che apre il caffè, rimandato da NVDA, non lo chiude;
    quello di dopo la grazia si'."""
    caffe = dialoghi.Caffe(None, "Grazie.")
    chiuso = []
    monkeypatch.setattr(caffe, "EndModal", chiuso.append)
    try:
        caffe._tasto(_tasto(wx.WXK_RETURN, caffe.testo))
        assert chiuso == []
        caffe.ultimo_invio = time.monotonic() - dialoghi.GRAZIA_INVIO - 0.1
        caffe._tasto(_tasto(wx.WXK_RETURN, caffe.testo))
        assert chiuso == [wx.ID_OK]
    finally:
        caffe.Destroy()


# La lingua.


@pytest.fixture
def lingua_rimessa():
    file = os.path.join(avvio.cartella_delle_impostazioni(), "selected_language.json")
    copia = file + ".copia"
    shutil.copy2(file, copia)
    try:
        yield
    finally:
        shutil.move(copia, file)


def test_la_lingua_cambiata_parla_al_riavvio(lingua_rimessa):
    """Come la voce Lingua, poi come config al prossimo avvio: polipo legge la
    scelta, e le frasi arrivano dal catalogo inglese."""
    from GBUtils import polipo

    avvio.salva("en")
    codice, traduci = polipo(source_language="it", localedir=avvio.cartella_dei_cataloghi(), config_path=avvio.cartella_delle_impostazioni(), interattivo=False)
    assert codice == "en"
    assert traduci("Impostazioni") == "Settings"
    assert traduci("Offrimi un caffè") != "Offrimi un caffè"


# I campi dei numeri e dei testi.


def test_i_campi_stanno_nei_loro_limiti(app):
    intero = dialoghi.FinestraValore(None, "Volume dei suoni: 40%", "Inserisci nuovo volume (0-100): ", 40, "intero", 0, 100)
    decimale = dialoghi.FinestraValore(None, "Tempo", "Tempo analisi default (sec) [1.0]: ", 1.0, "decimale", 0.1, 300)
    testo = dialoghi.FinestraValore(None, "Il mio nome", "Il tuo nome: ", "Gabriele", "testo", 0, 5)
    try:
        assert intero.campo.GetName() == "Inserisci nuovo volume (0-100):"
        intero.campo.SetValue(150)
        assert intero.valore == 100
        intero.campo.SetValue(-3)
        assert intero.valore == 0
        decimale.campo.SetValue(0.0)
        assert decimale.valore == 0.1
        decimale.campo.SetValue(2.46)
        assert decimale.valore == 2.5
        assert testo.campo.GetValue() == "Gabriele"
        testo.campo.SetValue("  Gab  ")
        assert testo.valore == "Gab"
    finally:
        for dialogo in (intero, decimale, testo):
            dialogo.Destroy()
    pompa(lambda: False, 0.05)


# L'installatore.


def test_l_installatore_parla_le_cinque_lingue():
    with open(os.path.join(RADICE, "Orologic.iss"), encoding="utf-8-sig") as file:
        testo = file.read()
    lingue = re.findall(r'^Name: "(\w+)"; MessagesFile:', testo, re.MULTILINE)
    assert lingue == ["italiano", "english", "espanol", "francais", "portugues"]
    for lingua in lingue:
        for messaggio in ("Terminale", "CancelloIDati"):
            assert re.search(rf"^{lingua}\.{messaggio}=\S", testo, re.MULTILINE), (lingua, messaggio)
    assert "PrivilegesRequired=lowest" in testo
    assert 'Parameters: "--cli"' in testo


# I rami della plancia.


def _chiavi_del_modulo(file, funzione):
    """Le stringhe che il modulo del menu scrive come chiavi di dizionario,
    nei dizionari scritti per intero e in quelli riempiti una voce alla
    volta: il menu principale di Orolichess lo costruisce run, non la
    funzione che chiama menu."""
    with open(file, encoding="utf-8") as sorgente:
        albero = ast.parse(sorgente.read())
    assert any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == funzione for n in ast.walk(albero)), f"in {file} non c'e' {funzione}"
    chiavi = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Dict):
            chiavi |= {k.value for k in nodo.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        elif isinstance(nodo, ast.Subscript) and isinstance(nodo.slice, ast.Constant) and isinstance(nodo.slice.value, str):
            chiavi.add(nodo.slice.value)
    return chiavi


def test_i_rami_sono_voci_vere_dei_menu():
    """Ogni voce che RAMI segna come ramo e' una chiave di un menu della sua
    funzione: se un giorno una voce cambia nome, la prova lo dice prima che
    la plancia smetta di aprire il ramo."""
    from orologic_modules import config

    cartelle = {"orologic.py": RADICE}
    for (nome, funzione), rami in plancia.RAMI.items():
        if callable(rami):
            continue
        file = os.path.join(cartelle.get(nome, os.path.join(RADICE, "orologic_modules")), nome)
        chiavi = _chiavi_del_modulo(file, funzione)
        if funzione == "Main":
            chiavi = set(config.MENU_CHOICES)
        elif funzione == "menu_orologi":
            chiavi = set(config.MENU_OROLOGI)
        assert set(rami) <= chiavi, (nome, funzione, set(rami) - chiavi)
