# Orologic, prove della pulizia dei file accumulati.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La pulizia chiesta da Gabriele il 21 novembre 2026: i file delle cartelle
pgn, txt e images nella cartella dell'app delle prove, che conftest.py tiene
lontana da quella vera; il cestino finto, che cancella e si segna cosa,
perche' le prove non tocchino il cestino di Windows."""

import os
import shutil
import time

import pytest
import wx
from conftest import pompa

from orologic_modules import cleaner, config, finestra_pulizia, storage

GIORNO = 86400


@pytest.fixture
def cartelle():
    """Crea un file con nome, cartella ed eta' in giorni; alla fine le tre
    cartelle spariscono, e il t salvato con loro."""

    def crea(cartella, nome, giorni, byte=100):
        percorso = config.percorso_salvataggio(cartella)
        os.makedirs(percorso, exist_ok=True)
        completo = os.path.join(percorso, nome)
        with open(completo, "wb") as file:
            file.write(b"x" * byte)
        data = time.time() - giorni * GIORNO
        os.utime(completo, (data, data))
        return completo

    yield crea
    for nome in cleaner.CARTELLE:
        shutil.rmtree(config.percorso_salvataggio(nome), ignore_errors=True)

    def togli(db):
        db.pop(cleaner.CHIAVE_GIORNI, None)

    storage.UpdateDB(togli)


def test_i_valori_di_t():
    assert len(cleaner.VALORI_DEI_GIORNI) == 18
    assert (cleaner.VALORI_DEI_GIORNI[0], cleaner.VALORI_DEI_GIORNI[-1]) == (61, 1095)
    assert 365 in cleaner.VALORI_DEI_GIORNI and 730 in cleaner.VALORI_DEI_GIORNI
    assert cleaner.durata_in_mesi(2) == "2 mesi"
    assert cleaner.durata_in_mesi(12) == "1 anno"
    assert cleaner.durata_in_mesi(14) == "1 anno e 2 mesi"
    assert cleaner.durata_in_mesi(36) == "3 anni"


def test_i_file_dal_piu_vecchio_e_il_t_salvato(cartelle):
    assert cleaner.giorni_salvati() == 365
    cartelle("txt", "resoconto.txt", 10)
    cartelle("pgn", "vecchia.pgn", 400)
    cartelle("images", "scacchiera.pdf", 800)
    files = cleaner.file_accumulati()
    assert [f["nome"] for f in files] == ["scacchiera.pdf", "vecchia.pgn", "resoconto.txt"]
    assert [f["nome"] for f in cleaner.vecchi(files, 365)] == ["scacchiera.pdf", "vecchia.pgn"]
    assert cleaner.ci_sono_vecchi(365)
    cleaner.salva_giorni(1095)
    assert cleaner.giorni_salvati() == 1095
    assert not cleaner.ci_sono_vecchi(1095)
    # Ripristina date: i file vecchi tornano a oggi.
    assert cleaner.ripristina_date(cleaner.vecchi(files, 365)) == 2
    assert not cleaner.ci_sono_vecchi(61)


class Prova:
    def __init__(self, monkeypatch):
        self.suoni = []
        self.domande = []
        self.avvisi = []
        self.nel_cestino = []
        self.risposta = True
        self.cestino_rotto = False
        monkeypatch.setattr(finestra_pulizia, "suona", self.suoni.append)
        monkeypatch.setattr(finestra_pulizia, "nel_cestino", self._cestino)
        self.dialogo = finestra_pulizia.FinestraPulizia(None, self._conferma, lambda _g, testo: self.avvisi.append(testo))
        self.dialogo.Show()
        pompa(lambda: wx.Window.FindFocus() is self.dialogo.riepilogo)

    def _cestino(self, percorso, _finestra=None):
        if self.cestino_rotto:
            return False
        os.remove(percorso)
        self.nel_cestino.append(os.path.basename(percorso))
        return True

    def _conferma(self, _genitore, testo):
        self.domande.append(testo)
        return self.risposta

    @staticmethod
    def voci(lista):
        return [lista.GetString(i) for i in range(lista.GetCount())]


@pytest.fixture
def prova(app, cartelle, monkeypatch):
    aperte = []

    def apri():
        aperta = Prova(monkeypatch)
        aperte.append(aperta)
        return aperta

    yield apri
    for aperta in aperte:
        aperta.dialogo.Destroy()
    pompa(lambda: False, 0.1)


def test_la_finestra_della_pulizia(prova, cartelle):
    cartelle("pgn", "vecchia.pgn", 400, 2048)
    cartelle("pgn", "nuova.pgn", 5, 1024)
    cartelle("images", "scacchiera.pdf", 800, 100)
    p = prova()
    d = p.dialogo
    assert d.riepilogo.GetValue().split("\n") == [
        "pgn: 2 file, 3,0 KB",
        "txt: nessun file",
        "images: 1 file, 100 B",
        "In tutto: 3 file, 3,1 KB",
        "Piu' vecchi di 1 anno: 2 file, 2,1 KB",
    ]
    assert p.voci(d.elenco) == ["scacchiera.pdf, images, 800 giorni, 100 B", "vecchia.pgn, pgn, 400 giorni, 2,0 KB", "nuova.pgn, pgn, 5 giorni, 1,0 KB"]
    # Canc: il file nel cestino, senza domande.
    d.elenco.SetSelection(0)
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(wx.WXK_DELETE)
    evento.SetEventObject(d.elenco)
    d._tasto(evento)
    assert p.nel_cestino == ["scacchiera.pdf"]
    assert p.suoni == ["eliminato"]
    assert p.domande == []
    # t a due mesi: si salva, e la situazione lo dice.
    d.scelta_dei_giorni.SetSelection(0)
    d.scelta_dei_giorni.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_CHOICE, d.scelta_dei_giorni.GetId()))
    assert cleaner.giorni_salvati() == 61
    assert d.riepilogo.GetValue().split("\n")[-1] == "Piu' vecchi di 2 mesi: 1 file, 2,0 KB"
    # Elimina piu' vecchi di: la domanda, poi il cestino.
    p.risposta = False
    d.elimina_i_vecchi()
    assert p.domande[-1] == "Mando nel cestino il file piu' vecchio di 2 mesi, 2,0 KB?"
    assert p.nel_cestino == ["scacchiera.pdf"]
    p.risposta = True
    d.elimina_i_vecchi()
    assert p.nel_cestino == ["scacchiera.pdf", "vecchia.pgn"]
    # Ripristina date: niente di vecchio, la nota del no.
    d.ripristina_le_date()
    assert p.suoni[-1] == "no"
    # Un cestino che non prende il file: il file resta, e lo si dice.
    p.cestino_rotto = True
    d.elimina_tutto()
    assert p.avvisi == ["Non sono andati nel cestino: nuova.pgn."]
    assert p.voci(d.elenco) == ["nuova.pgn, pgn, 5 giorni, 1,0 KB"]
    p.cestino_rotto = False
    d.elimina_tutto()
    assert p.voci(d.elenco) == ["Nessun file."]


def test_ripristina_date(prova, cartelle):
    cartelle("txt", "vecchio.txt", 500)
    p = prova()
    p.dialogo.ripristina_le_date()
    assert p.suoni == ["ripristinate"]
    assert p.dialogo.riepilogo.GetValue().split("\n")[-1] == "Piu' vecchi di 1 anno: 0 file, 0 B"


def test_si_apre_dal_nucleo_e_dalle_impostazioni(finestra, cartelle):
    from orologic_modules import strato

    finiti = []

    def nucleo():
        strato.pulizia()
        finiti.append(True)

    def chiudi():
        if finestra.dialogo_pulizia is not None and finestra.dialogo_pulizia.IsModal():
            finestra.dialogo_pulizia.EndModal(wx.ID_CANCEL)
            return
        wx.CallLater(30, chiudi)

    wx.CallLater(30, chiudi)
    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finiti == [True])
    # Dalla voce Pulizia delle impostazioni.
    assert finestra.gestore.riga("pulizia") == "Pulizia"
    wx.CallLater(30, chiudi)
    finestra.gestore.cambia("pulizia", None)
    assert finestra.dialogo_pulizia is None
