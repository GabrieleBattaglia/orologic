# Orologic, prove del braille del testo che cambia da solo nell'area.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""NVDA rilegge l'area solo dopo un tasto: la riga sotto il cursore, se e'
cambiata dopo l'ultimo tasto, va alla barra come messaggio, rimandato ogni
secondo finche' non se ne preme uno. Il testo cambia col documento del
RichEdit, senza toccare il cursore: chi legge piu' su resta dov'e', e alla
barra non arriva niente (Gabriele, 23 novembre 2026, prova del braille)."""

import sys
import threading

import wx
from conftest import pompa


def _tasto(finestra, codice):
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(codice)
    finestra._tasto_della_finestra(evento)


def test_il_prompt_che_cambia_va_alla_barra_e_chi_legge_su_resta_dov_e(finestra):
    passi = [threading.Event() for _ in range(3)]

    def nucleo():
        print("Riga fissa da leggere")
        sys.stdout.write("Tempo 05:00 >")
        sys.stdout.flush()
        for numero, testo in enumerate(("\rTempo 04:59 >", "\rTempo 04:58 >")):
            passi[numero].wait(10)
            sys.stdout.write(testo)
            sys.stdout.flush()
        passi[2].wait(10)

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: "Tempo 05:00 >" in finestra.area.GetValue())
    finestra.vai_all_area()
    assert pompa(lambda: wx.Window.FindFocus() is finestra.area)
    assert finestra._documento() is not None
    passi[0].set()
    assert pompa(lambda: "Tempo 04:59 >" in finestra.al_braille_mandati)
    # Finche' non si preme, la riga torna alla barra ogni secondo, anche ferma.
    mandati = len(finestra.al_braille_mandati)
    assert pompa(lambda: len(finestra.al_braille_mandati) > mandati, 3)
    assert finestra.al_braille_mandati[-1] == "Tempo 04:59 >"
    # Un tasto, anche una freccia: NVDA rilegge da se', il ripasso si ferma.
    _tasto(finestra, wx.WXK_LEFT)
    mandati = len(finestra.al_braille_mandati)
    pompa(lambda: False, 1.5)
    assert len(finestra.al_braille_mandati) == mandati
    # Chi legge piu' su: il prompt cambia, ma il cursore non si muove, e
    # alla barra non arriva niente.
    finestra.area.SetInsertionPoint(finestra.area.XYToPosition(5, 0))
    posizione = finestra.area.GetInsertionPoint()
    passi[1].set()
    assert pompa(lambda: "Tempo 04:58 >" in finestra.area.GetValue())
    pompa(lambda: False, 0.5)
    assert finestra.area.GetInsertionPoint() == posizione
    assert len(finestra.al_braille_mandati) == mandati
    passi[2].set()
