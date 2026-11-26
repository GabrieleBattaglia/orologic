# Orologic, prove del registro degli errori (rilievo R15 della revisione 2).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Un errore che ferma il nucleo resta nel registro, settings/errori.log
nella cartella temporanea delle prove, e si legge in una finestra prima che
la finestra di Orologic si chiuda; gli errori degli altri fili e di
sys.excepthook finiscono nello stesso file."""

import os
import sys
import threading

from conftest import pompa

from orologic_modules import dialoghi, registro
from orologic_modules.finestra import Finestra


def _testo_del_registro():
    with open(registro.percorso(), encoding="utf-8") as file:
        return file.read()


def test_l_errore_del_nucleo_resta_nel_registro_e_si_mostra(finestra):
    def nucleo():
        raise RuntimeError("guasto di prova del nucleo")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.errori_mostrati)
    testo, file = finestra.errori_mostrati[0]
    assert "RuntimeError: guasto di prova del nucleo" in testo
    assert file == registro.percorso()
    assert "RuntimeError: guasto di prova del nucleo" in _testo_del_registro()
    # L'area ha ancora il traceback, come prima.
    assert "guasto di prova del nucleo" in finestra.area.GetValue()


def test_la_finestra_dell_errore_dice_dove_sta_il_registro(finestra, monkeypatch):
    letti = []
    monkeypatch.setattr(dialoghi, "da_leggere", lambda genitore, titolo, righe, *a, **k: letti.append((titolo, righe)))
    Finestra.mostra_l_errore(finestra, "Traceback\nValueError: x\n", "C:\\registro.log")
    titolo, righe = letti[0]
    assert titolo
    assert "C:\\registro.log" in righe[1]
    assert righe[-1] == "ValueError: x"


def test_gli_errori_degli_altri_fili_vanno_nel_registro(monkeypatch):
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", lambda argomenti: None)
    registro.installa()

    def guasto():
        raise ValueError("guasto di prova di un filo")

    filo = threading.Thread(target=guasto, name="filo di prova")
    filo.start()
    filo.join()
    testo = _testo_del_registro()
    assert "Filo filo di prova:" in testo
    assert "ValueError: guasto di prova di un filo" in testo


def test_stderr_sul_registro_e_il_registro_che_riparte(monkeypatch):
    stderr = registro.SulRegistro()
    stderr.write("una riga di stderr\n")
    assert "una riga di stderr" in _testo_del_registro()
    monkeypatch.setattr(registro, "MASSIMO", 10)
    registro.scrivi("dopo il limite")
    assert os.path.isfile(registro.percorso() + ".1")
    assert "una riga di stderr" not in _testo_del_registro()
    assert "dopo il limite" in _testo_del_registro()


def test_a_nucleo_finito_si_chiude_prima_il_dialogo_aperto(finestra):
    """R87: a nucleo finito la finestra si distruggeva anche con sopra un
    dialogo aperto con Ctrl e virgola. Un ciclo modale vero, e un paracadute
    su un filo a parte."""
    import wx

    esiti = []
    paracadute = []

    def salva():
        for dialogo in wx.GetTopLevelWindows():
            if isinstance(dialogo, wx.Dialog) and dialogo.IsModal():
                paracadute.append(True)
                dialogo.EndModal(wx.ID_ABORT)

    def impostazioni():
        dialogo = wx.Dialog(finestra, title="Impostazioni di prova")
        wx.CallAfter(finestra._distruggi_alla_fine)
        esiti.append(dialogo.ShowModal())
        dialogo.Destroy()

    soccorso = threading.Timer(3, lambda: wx.CallAfter(salva))
    soccorso.start()
    try:
        wx.CallAfter(impostazioni)
        assert pompa(lambda: esiti and not finestra, 6)
    finally:
        soccorso.cancel()
    assert esiti == [wx.ID_CANCEL] and paracadute == []


def test_la_raccolta_di_da_leggere_e_del_solo_filo_del_nucleo(finestra, monkeypatch):
    """R84: da_leggere scambiava sys.stdout per tutti i fili: le righe degli
    altri finivano nella finestra da leggere, o si perdevano."""
    import sys

    from orologic_modules import dialoghi, strato

    letture = []
    monkeypatch.setattr(dialoghi, "da_leggere", lambda _genitore, titolo, righe, *a, **k: letture.append((titolo, righe)))
    dentro = threading.Event()
    via = threading.Event()

    def nucleo():
        with strato.partita(), strato.da_leggere("Prova"):
            print("Riga del nucleo.")
            dentro.set()
            via.wait(5)

    finestra.avvia_il_nucleo(nucleo)
    assert dentro.wait(5)
    sys.stdout.write("Riga di un altro filo.\n")
    via.set()
    assert pompa(lambda: letture)
    assert letture == [("Prova", ["Riga del nucleo."])]
    assert pompa(lambda: "Riga di un altro filo." in finestra.area.GetValue())
