# Orologic, prove del prompt delle mosse che si riscrive senza annunciarsi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Gabriele, 24 novembre 2026: su Lichess, con gli annunci accesi, a ogni
mossa fatta o ricevuta, e a ogni messaggio, il prompt si risentiva intero,
perche' Orologic lo riscrive con gli orologi aggiornati. Dalla 9.0.1, al
prompt delle mosse, quello delle partite che legge i tasti uno per uno, il
prompt riscritto si scrive e va alla barra, ma non si annuncia; le mosse e
i messaggi si dicono come sempre, il prompt si dice quando compare, e una
domanda che arriva dopo si dice. Il prompt di Easyfish, che legge righe
intere, resta com'era. Provato prima con la finestra vera e una partita
finta, E:\\git\\tmp\\prova_cruscotto, modo 2."""

import sys
import threading

import wx
from conftest import pompa

from orologic_modules import strato, ui


def _scrivi(testo):
    sys.stdout.write(testo)
    sys.stdout.flush()


def test_al_prompt_delle_mosse_si_dice_la_mossa_e_non_il_prompt_riscritto(finestra):
    passi = [threading.Event() for _ in range(3)]
    risposta = {}

    def nucleo():
        # Come Orolichess: il prompt, poi il ciclo che legge i tasti.
        _scrivi("Bianco 05:00, Nero 05:00 >")
        strato.kbhit()
        passi[0].wait(10)
        # Una mossa dell'avversario: la riga ripulita, la mossa, il prompt
        # riscritto, e il ciclo che riprende.
        ui.pulisci_riga()
        _scrivi("Avversario gioca: Cavallo in f6\n")
        ui.pulisci_riga()
        _scrivi("Bianco 04:58, Nero 04:57 >")
        strato.kbhit()
        passi[1].wait(10)
        # Un messaggio, e di nuovo il prompt riscritto.
        ui.pulisci_riga()
        _scrivi("L'avversario ha lasciato la partita.\n")
        ui.pulisci_riga()
        _scrivi("Bianco 04:55, Nero 04:57 >")
        strato.kbhit()
        passi[2].wait(10)
        # Una domanda, fuori dal prompt delle mosse: si dice.
        _scrivi("\nMessaggio per l'avversario: ")
        risposta["testo"] = sys.stdin.readline()

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: any("05:00" in detto for detto in finestra.sintesi.testi()))
    finestra.vai_all_area()
    assert pompa(lambda: wx.Window.FindFocus() is finestra.area)
    passi[0].set()
    assert pompa(lambda: any("Cavallo in f6" in detto for detto in finestra.sintesi.testi()))
    assert pompa(lambda: "04:58" in finestra.area.GetValue())
    pompa(lambda: False, 0.3)
    assert not any("04:58" in detto for detto in finestra.sintesi.testi())
    # Il prompt riscritto va alla barra, come il rinfresco.
    assert any("04:58" in mandato for mandato in finestra.al_braille_mandati)
    passi[1].set()
    assert pompa(lambda: any("lasciato la partita" in detto for detto in finestra.sintesi.testi()))
    assert pompa(lambda: "04:55" in finestra.area.GetValue())
    pompa(lambda: False, 0.3)
    assert not any("04:55" in detto for detto in finestra.sintesi.testi())
    passi[2].set()
    assert pompa(lambda: any("Messaggio per l'avversario" in detto for detto in finestra.sintesi.testi()))
    for tasto in "ciao\r":
        finestra.faccia.premi(tasto)
    assert pompa(lambda: risposta.get("testo") == "ciao\n")


def test_il_prompt_di_easyfish_si_dice_dopo_ogni_comando(finestra):
    risposte = []

    def nucleo():
        with strato.prompt_di_gioco():
            _scrivi("Easyfish, mossa 1 > ")
            risposte.append(sys.stdin.readline())
            _scrivi("Pedone in e4.\n")
            _scrivi("Easyfish, mossa 2 > ")
            risposte.append(sys.stdin.readline())

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: any("mossa 1" in detto for detto in finestra.sintesi.testi()))
    for tasto in "e4\r":
        finestra.faccia.premi(tasto)
    assert pompa(lambda: any("mossa 2" in detto for detto in finestra.sintesi.testi()))
    for tasto in "\r":
        finestra.faccia.premi(tasto)
    assert pompa(lambda: len(risposte) == 2)


def test_tornando_al_prompt_delle_mosse_dopo_una_domanda_il_prompt_si_dice(finestra):
    passi = [threading.Event() for _ in range(2)]

    def nucleo():
        _scrivi("Bianco 05:00 >")
        strato.kbhit()
        passi[0].wait(10)
        _scrivi("\nNome del file: ")
        sys.stdin.readline()
        _scrivi("Bianco 04:50 >")
        strato.kbhit()
        passi[1].wait(10)

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: any("05:00" in detto for detto in finestra.sintesi.testi()))
    passi[0].set()
    assert pompa(lambda: any("Nome del file" in detto for detto in finestra.sintesi.testi()))
    for tasto in "x\r":
        finestra.faccia.premi(tasto)
    # Il prompt delle mosse torna dopo la domanda: si dice.
    assert pompa(lambda: any("04:50" in detto for detto in finestra.sintesi.testi()))
    passi[1].set()
