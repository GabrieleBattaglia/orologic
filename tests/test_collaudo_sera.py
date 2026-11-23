# Orologic, prove del collaudo della sera del 23 novembre 2026.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le note di Gabriele: il rinfresco periodico del prompt non si annuncia,
ma va alla barra; a fine partita prima Easyfish, e l'analisi automatica
solo a chi risponde no; l'analisi gira con la forza della configurazione,
non con quella del motore indebolito della partita."""

import sys
import threading

import chess
import chess.pgn
import wx
from conftest import pompa

from orologic_modules import engine, gioca, strato


def test_il_rinfresco_del_prompt_si_scrive_e_va_alla_barra_ma_non_si_dice(finestra):
    passi = [threading.Event() for _ in range(3)]

    def nucleo():
        sys.stdout.write("Tempo 05:00 >")
        sys.stdout.flush()
        passi[0].wait(10)
        with strato.rinfresco():
            sys.stdout.write("\rTempo 04:59 >")
            sys.stdout.flush()
        passi[1].wait(10)
        sys.stdout.write("\rTempo 04:58 >")
        sys.stdout.flush()
        passi[2].wait(10)

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: "Tempo 05:00 >" in finestra.area.GetValue())
    finestra.vai_all_area()
    assert pompa(lambda: wx.Window.FindFocus() is finestra.area)
    passi[0].set()
    assert pompa(lambda: "Tempo 04:59 >" in finestra.area.GetValue())
    pompa(lambda: False, 0.3)
    assert "Tempo 04:59 >" in finestra.al_braille_mandati
    assert not any("04:59" in detto for detto in finestra.sintesi.testi())
    # Il resto si annuncia come sempre.
    passi[1].set()
    assert pompa(lambda: any("04:58" in detto for detto in finestra.sintesi.testi()))
    passi[2].set()


class MotoreConForza:
    def __init__(self):
        self.options = {"UCI_LimitStrength": None, "UCI_Elo": None, "Skill Level": None}
        self.configurate = []

    def configure(self, opzioni):
        self.configurate.append(opzioni)


def test_l_analisi_torna_alla_forza_della_configurazione(monkeypatch):
    motore = MotoreConForza()
    monkeypatch.setattr(engine, "ENGINE", motore)
    monkeypatch.setitem(engine.forza, "tipo", "elo")
    monkeypatch.setitem(engine.forza, "valore", 1320)
    engine.forza_della_configurazione()
    assert {"UCI_LimitStrength": False} in motore.configurate
    assert {"Skill Level": 20} in motore.configurate
    assert engine.forza["tipo"] == "livello" and engine.forza["valore"] == 20


def _fine_partita(monkeypatch, risposte):
    chieste = []

    def domanda(testo):
        chieste.append(testo)
        return risposte.pop(0)

    fatti = []
    monkeypatch.setattr(gioca, "enter_escape", domanda)
    monkeypatch.setattr(gioca.ui, "svuota_tastiera", lambda: None)
    monkeypatch.setattr(gioca, "_classifica_apertura", lambda _partita: None)
    monkeypatch.setattr(gioca.pyperclip, "copy", lambda *_a: None)
    monkeypatch.setattr(gioca.chess960_utils, "verifica_motore_chess960", lambda *_a: None)
    monkeypatch.setattr(gioca.engine, "AnalisiAutomatica", lambda _partita: fatti.append("oaa"))
    from orologic_modules import game_flow
    from orologic_modules.easyfish import easyfish_app

    monkeypatch.setattr(game_flow, "salva_pgn_partita", lambda *_a: None)
    monkeypatch.setattr(easyfish_app, "run", lambda _partita: fatti.append("easyfish"))
    partita = chess.pgn.Game()
    nodo = partita
    for mossa in ("e4", "e5", "Nf3", "Nc6", "Bb5"):
        nodo = nodo.add_variation(nodo.board().parse_san(mossa))
    stato = type("Stato", (), {"move_history": list(range(5)), "modalita": "0"})()
    gioca._dopo_la_partita(partita, stato)
    return chieste, fatti


def test_a_fine_partita_prima_easyfish_poi_l_analisi(monkeypatch):
    chieste, fatti = _fine_partita(monkeypatch, [True])
    assert len(chieste) == 1 and "Easyfish" in chieste[0]
    assert fatti == ["easyfish"]
    chieste, fatti = _fine_partita(monkeypatch, [False, True])
    assert "Easyfish" in chieste[0] and "OAA" in chieste[1]
    assert fatti == ["oaa"]


assert chess


def test_la_finestra_da_leggere_riceve_tutte_le_righe(finestra, monkeypatch):
    from orologic_modules import finestra as modulo_finestra

    lette = []
    monkeypatch.setattr(modulo_finestra.dialoghi, "da_leggere", lambda _genitore, titolo, righe, *_resto: lette.append((titolo, righe)))
    fatto = []

    def nucleo():
        strato.leggi_in_una_finestra("Analisi Automatica della Partita", ["Orologic Analisi Automatica", "", "Statistiche:"])
        fatto.append(True)

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: fatto == [True])
    assert lette == [("Analisi Automatica della Partita", ["Orologic Analisi Automatica", "", "Statistiche:"])]
