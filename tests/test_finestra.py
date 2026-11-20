# Orologic, prove della finestra (tappa T2 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra con l'area unica: il terminale imitato, la faccia dello
strato, e poi la finestra vera, sul desktop nascosto di conftest.py, con un
nucleo finto e infine con Orologic intero. La voce e' sostituita da un
registro: niente sintesi, niente braille, niente suoni."""

import threading
import time

import pytest
from conftest import attiva, pompa, righe_dell_area
from GBUtils import dgt, key

from orologic_modules import game_flow, strato
from orologic_modules.finestra import FacciaFinestra, Terminale

# Il terminale imitato.


def test_il_terminale_chiude_le_righe_e_riscrive():
    terminale = Terminale()
    assert terminale.applica("uno\ndue") == ["uno"]
    assert terminale.visibile() == "due"
    assert terminale.applica("\rtre") == []
    assert terminale.visibile() == "tre"


def test_il_terminale_imita_pulisci_riga_e_il_cursore_dopo_la_mossa():
    terminale = Terminale()
    terminale.applica("1. e4 Nf 04:59 0%")
    terminale.applica("\r" + " " * 299 + "\r")
    assert terminale.visibile() == ""
    terminale.applica("1. e4  04:58 0%" + "\b" * 9)
    assert terminale.visibile() == "1. e4  04:58 0%"
    assert terminale.colonna == 6
    terminale.applica("N")
    assert terminale.visibile() == "1. e4 N04:58 0%"


def test_il_backspace_del_ciclo_d_attesa():
    terminale = Terminale()
    terminale.applica("> Nf3\b \b")
    assert terminale.visibile() == "> Nf"
    assert terminale.colonna == 4


# La faccia, senza finestra.


def _testo(faccia):
    """Il testo messo in fila, senza le attese della plancia."""
    return [(testo, causa) for testo, causa in faccia.prendi_il_testo() if isinstance(testo, str)]


def test_leggi_riga_fa_l_eco_cancella_e_svuota():
    faccia = FacciaFinestra()
    for tasto in ["a", "b", "\x08", "c", "\x1b", "d", "e", "\r"]:
        faccia.premi(tasto)
    assert faccia.leggi_riga() == "de"
    pezzi = _testo(faccia)
    assert "".join(testo for testo, _causa in pezzi) == "ab\b \bc\b \b\b \bde\n"
    assert all(causa == "eco" for testo, causa in pezzi if testo != "\n")
    assert pezzi[-1] == ("\n", "tasto")


def test_leggi_riga_senza_eco_per_le_password():
    faccia = FacciaFinestra()
    for tasto in "segreto\r":
        faccia.premi(tasto)
    assert faccia.leggi_riga(eco=False) == "segreto"
    assert [testo for testo, _causa in _testo(faccia)] == ["\n"]


def test_la_sorgente_di_key_scade_e_risponde():
    faccia = FacciaFinestra()
    inizio = time.monotonic()
    assert faccia.tasto_per_key(0.2) is None
    assert time.monotonic() - inizio < 1.0
    faccia.premi("x")
    assert faccia.tasto_per_key(None) == "x"
    faccia.scrivi("risposta")
    assert _testo(faccia) == [("risposta", "tasto")]


def test_l_eco_dei_cicli_dura_poco():
    faccia = FacciaFinestra()
    faccia.premi("N")
    assert faccia.getwch() == "N"
    faccia.scrivi("N")
    time.sleep(0.05)
    faccia.scrivi("rinfresco")
    assert _testo(faccia) == [("N", "eco"), ("rinfresco", None)]


def test_la_chiusura_interrompe_ogni_lettura():
    faccia = FacciaFinestra()
    faccia.chiudi()
    for lettura in (faccia.kbhit, faccia.getwch, faccia.leggi_riga, lambda: faccia.tasto_per_key(None)):
        with pytest.raises(KeyboardInterrupt):
            lettura()


# La finestra, con un nucleo finto.


def test_un_nucleo_finto_nella_finestra(finestra):
    """print, dgt, key e il ciclo d'attesa dell'arbitraggio, tutti dalla
    stessa area; gli annunci senza l'eco."""
    esiti = {}

    def nucleo():
        print("Benvenuto nella prova.")
        esiti["nome"] = dgt("Come ti chiami? ")
        esiti["tasto"] = key("Premi un tasto: ")
        print(f"Ciao {esiti['nome']}, hai premuto {esiti['tasto']}.")
        stato = type("Stato", (), {"flag_fallen": False, "ignore_clock": False, "refresh_interval": 0, "vista_ferma": False})()
        esiti["mossa"] = game_flow.async_arbitration_input(stato, lambda: "1. e4 ")
        print("Fine della prova.")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: "Come ti chiami?" in finestra.area.GetValue())
    for tasto in "Gabry\r":
        finestra.faccia.premi(tasto)
    assert pompa(lambda: "Premi un tasto:" in finestra.area.GetValue())
    finestra.faccia.premi("x")
    assert pompa(lambda: righe_dell_area(finestra)[-1].startswith("1. e4"))
    for tasto in "Nf3\r":
        finestra.faccia.premi(tasto)
    assert pompa(lambda: not finestra.nucleo.is_alive() and "Fine della prova." in finestra.area.GetValue())
    assert esiti == {"nome": "Gabry", "tasto": "x", "mossa": "Nf3"}
    # key non fa l'eco del tasto, come nel terminale: la risposta continua
    # la riga del prompt.
    assert righe_dell_area(finestra)[:5] == [
        "Benvenuto nella prova.",
        "Come ti chiami? Gabry",
        "Premi un tasto: Ciao Gabry, hai premuto x.",
        "1. e4 Nf3",
        "Fine della prova.",
    ]
    # Si dice il nuovo, mai l'eco di cio' che si scrive, che NVDA dice da
    # se'; di una riga che continua il prompt, solo la parte nuova; la
    # risposta a un tasto interrompe la voce.
    assert finestra.sintesi.detti == [
        ("Benvenuto nella prova.", False),
        ("Come ti chiami?", False),
        ("Premi un tasto:", True),
        ("Ciao Gabry, hai premuto x.", True),
        ("1. e4", False),
        ("Fine della prova.", True),
    ]


def test_chi_rilegge_piu_su_non_viene_spostato(finestra):
    via = threading.Event()

    def nucleo():
        print("Prima riga.")
        print("Seconda riga.")
        via.wait(10)
        print("Terza riga.")
        key("Ancora un tasto: ")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: "Seconda riga." in finestra.area.GetValue())
    finestra._vai(0, 3)
    via.set()
    assert pompa(lambda: "Ancora un tasto:" in finestra.area.GetValue())
    assert finestra._riga_e_colonna() == (0, 3)
    finestra._manda("z")
    assert finestra._riga_e_colonna()[0] == len(finestra.righe)
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_la_chiusura_ferma_il_nucleo(finestra):
    def nucleo():
        while True:
            key("Aspetto per sempre: ")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: "Aspetto per sempre:" in finestra.area.GetValue())
    finestra.faccia.chiudi()
    assert pompa(lambda: not finestra.nucleo.is_alive(), 3)


def test_lo_strato_e_collegato_alla_finestra(finestra):
    assert strato.faccia() is finestra.faccia


# Orologic intero, nella finestra.


def test_orologic_parte_e_si_chiude_nella_finestra(finestra, monkeypatch):
    """Il motore vero non parte, e con lui nessun controllo in rete degli
    aggiornamenti di Stockfish: la prova non deve toccare niente fuori."""
    import orologic
    from orologic_modules import engine

    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    finestra.avvia_il_nucleo(lambda: orologic.esegui(con_la_finestra=True))
    # Il menu principale e' nella plancia, non nell'area.
    assert pompa(lambda: finestra.attesa.tipo == "menu", 30)
    assert "Esci" not in finestra.area.GetValue()
    attiva(finestra, "Esci")
    assert pompa(lambda: "Premi un tasto per uscire" in finestra.area.GetValue(), 15)
    testo = finestra.area.GetValue()
    assert "Benvenuto, sono Orologic" in testo
    assert "Arrivederci da Orologic" in testo
    assert any("Arrivederci da Orologic" in detto for detto in finestra.sintesi.testi())
    # Nella finestra l'invito al caffe' non c'e': sta in un menu.
    finestra.faccia.premi("x")
    assert pompa(lambda: not finestra.nucleo.is_alive(), 10)
    # Finito il nucleo, la finestra si chiude da sola.
    assert pompa(lambda: not finestra, 2)
