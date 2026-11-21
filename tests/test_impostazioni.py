# Orologic, prove delle impostazioni della finestra (tappa T5a della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il luogo unico delle impostazioni: le righe coi testi di Orologic, e i
cambi voce per voce, con le scelte e i campi sostituiti da risposte scritte.
Il motore non parte mai: InitEngine e CloseEngine si segnano. I file delle
impostazioni della cartella delle prove si rimettono com'erano."""

import os
import shutil

import pytest
import wx
from conftest import pompa

from orologic_modules import (
    config,
    engine,
    impostazioni,
    localizzazione,
    modello_prompt,
    storage,
    strato,
)


@pytest.fixture
def gestore(finestra, monkeypatch):
    """Il gestore della finestra vera, con le risposte in fila e i file
    rimessi a posto."""
    cartella = os.path.dirname(config.DB_FILE)
    copia = cartella + ".copia"
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(cartella, copia)
    risposte = []
    chieste = []

    def rispondi(tipo):
        def risposta(_genitore, titolo, *argomenti):
            chieste.append((tipo, titolo, *argomenti))
            return risposte.pop(0)

        return risposta

    monkeypatch.setattr(finestra, "scegli", rispondi("scelta"))
    monkeypatch.setattr(finestra, "chiedi_valore", rispondi("valore"))
    monkeypatch.setattr(finestra, "avvisa", lambda _genitore, testo: chieste.append(("avviso", testo)))
    monkeypatch.setattr(impostazioni, "Acusticator", type("Muto", (), {"__call__": lambda *_a, **_o: None, "play": staticmethod(lambda *_a, **_o: None)})())
    motore = []
    monkeypatch.setattr(engine, "InitEngine", lambda: motore.append("avviato"))
    monkeypatch.setattr(engine, "CloseEngine", lambda: motore.append("chiuso"))
    volume = config.VOLUME
    finestra.gestore.risposte, finestra.gestore.chieste, finestra.gestore.motore = risposte, chieste, motore
    try:
        yield finestra.gestore
    finally:
        if finestra.gestore.lavoro is not None:
            finestra.gestore.lavoro.join(5)
        config.VOLUME = volume
        shutil.rmtree(cartella, ignore_errors=True)
        shutil.copytree(copia, cartella)
        shutil.rmtree(copia, ignore_errors=True)
        localizzazione.ricarica()
        modello_prompt._cache["modello"] = None


def test_le_righe_coi_testi_di_orologic(gestore):
    righe = dict(gestore.righe())
    assert list(righe) == list(impostazioni.VOCI)
    assert righe["analisi_tempo"] == "Tempo analisi default (sec): 1.0"
    assert righe["soglia_errore"] == "Soglia Errore: 100"
    assert righe["giocatore"] == "Il mio nome: non ancora scritto"
    assert righe["nomi"] == "Nomi dei pezzi, delle colonne e delle mosse"
    assert righe["scacchiera_attesa"] == "Tempo di attesa dei comandi della scacchiera (ms): 700"
    assert righe["salvataggio"] == "Salvataggio automatico: non attivo"
    assert righe["stile"] == "Stile dei menu: parole"
    assert righe["volume"] == "Volume dei suoni: 0%"
    assert righe["attivi"] == "Annunci: sì"
    assert righe["lingua"] == "Lingua: italiano"
    assert [righe[v] for v in ("caffe", "pub_entra", "pub_aiuto")] == ["Offrimi un caffè", "Entra al PUB", "Chiedi aiuto al PUB"]


def test_analisi_e_soglie(gestore):
    gestore.risposte.extend([2.5, 120, 40])
    gestore.cambia("analisi_tempo", None)
    gestore.cambia("soglia_errore", None)
    gestore.cambia("soglia_inesattezza", None)
    db = storage.LoadDB()
    assert db["default_analysis_time"] == 2.5
    assert engine.analysis_time == 2.5
    assert db["analysis_thresholds"]["errore"] == 120
    assert db["analysis_thresholds"]["inesattezza"] == 40
    # Le altre soglie restano.
    assert db["analysis_thresholds"]["mossa_geniale_gap"] == 180
    # I limiti come nel terminale: l'errore sopra l'inesattezza, sotto lo svarione.
    _tipo, titolo, domanda, _valore, genere, minimo, massimo = gestore.chieste[1]
    assert (titolo, domanda, genere, minimo, massimo) == ("Soglia Errore", "Soglia Errore [100]: ", "intero", 51, 249)
    assert gestore.chieste[2][-2:] == (10, 119)


def test_il_nome_si_scrive_e_si_toglie(gestore):
    gestore.risposte.extend(["Gabry", ""])
    gestore.cambia("giocatore", None)
    assert gestore.riga("giocatore") == "Il mio nome: Gabry"
    gestore.cambia("giocatore", None)
    assert "nome_utente" not in storage.LoadDB()


def test_interruttori_volume_e_annunci(gestore):
    gestore.risposte.extend([0, 0, 40, 2])
    gestore.cambia("salvataggio", None)
    gestore.cambia("stile", None)
    gestore.cambia("volume", None)
    gestore.cambia("destinazione", None)
    db = storage.LoadDB()
    assert db["autosave_enabled"] is True
    assert db["menu_numerati"] is True
    assert config.VOLUME == 0.4
    assert db["volume"] == 0.4
    assert gestore.finestra.annunci["destinazione"] == "braille"
    assert gestore.chieste[0][:3] == ("scelta", "Salvataggio automatico", ["attivo", "non attivo"])


def test_la_lingua_vale_dal_riavvio(gestore):
    gestore.risposte.append(0)
    gestore.cambia("lingua", None)
    assert gestore.chieste[0][1] == "Lingua"
    assert gestore.riga("lingua").startswith("Lingua: italiano; dal riavvio ")
    from orologic_modules import avvio

    assert avvio.lingua_salvata() == "en"


def test_il_motore(gestore, tmp_path):
    gestore.risposte.extend([256, str(tmp_path), "manca.exe"])
    gestore.cambia_il_motore("hash", None)
    gestore.lavoro.join(5)
    assert storage.LoadDB()["engine_config"]["hash_size"] == 256
    assert gestore.motore == ["avviato"]
    # Un percorso senza l'eseguibile non si salva: lo dice l'avviso originale.
    gestore.cambia_il_motore("percorso", None)
    gestore.cambia_il_motore("eseguibile", None)
    assert gestore.chieste[-1] == ("avviso", "Il file specificato non esiste. Verifica il percorso e il nome dell'eseguibile.")
    vero = tmp_path / "stockfish.exe"
    vero.write_bytes(b"")
    gestore.salva_il_motore(str(vero))
    gestore.lavoro.join(5)
    cfg = storage.LoadDB()["engine_config"]
    assert engine.percorso_assoluto(cfg["engine_path"]) == str(vero)
    assert gestore.riga_del_motore("eseguibile") == "Eseguibile del motore: stockfish.exe"
    assert [gestore.riga_del_motore(v) for v in ("cerca", "scarica", "manuale")] == [
        "cercare un motore nel tuo pc",
        "scaricare Stockfish",
        "modificare manualmente la configurazione",
    ]


def test_scaricare_stockfish_chiude_prima_il_motore(gestore, monkeypatch):
    from orologic_modules import stockfish_installer

    monkeypatch.setattr(stockfish_installer, "DownloadAndInstallEngine", lambda: (gestore.motore.append("scaricato"), (None, None))[1])
    gestore.cambia_il_motore("scarica", None)
    gestore.lavoro.join(5)
    assert gestore.motore == ["chiuso", "scaricato", "avviato"]


def test_i_nomi(gestore):
    voci = gestore.voci_dei_nomi()
    assert len(voci) == 60
    assert voci[0] == (("pieces", "pawn", "name"), "Nome per 'Pedone'")
    assert voci[2] == (("pieces", "pawn", "gender"), None)
    assert gestore.riga_del_nome(("pieces", "pawn", "gender"), None) == "Genere per 'pedone': m"
    gestore.risposte.extend(["Asti", "", 1])
    gestore.cambia_un_nome(("columns", "a"), "Nome per colonna 'a' (Ancona)", None)
    assert gestore.chieste[0][2] == "Nome per colonna 'a' (Ancona) [Ancona]: "
    assert localizzazione.colonna("a") == "Asti"
    # Vuoto lascia il nome com'era.
    gestore.cambia_un_nome(("columns", "b"), "Nome per colonna 'b' (Bologna)", None)
    assert localizzazione.colonna("b") == "Bologna"
    gestore.cambia_un_nome(("pieces", "rook", "gender"), None, None)
    assert localizzazione.genere_pezzo("rook") == "f"


def test_il_prompt(gestore):
    gestore.salva_il_prompt(modello_prompt.modello(), "%b %n %4 %m")
    assert modello_prompt.modello() == "%b %n %4 %m"
    assert gestore.riga("prompt") == "Prompt di gioco: %b %n %4 %m"


def test_la_finestra_del_prompt(app):
    from orologic_modules import dialoghi

    dialogo = dialoghi.FinestraPrompt(None, "%b %n %m", lambda *_argomenti: None)
    try:
        assert dialogo.esempio.GetValue() == modello_prompt.componi(modello_prompt.esempio(), "%b %n %m")
        assert dialogo.prompt.GetString(0) == "%b tempo del Bianco"
        assert dialogo.modello == "%b %n %m"
    finally:
        dialogo.Destroy()


def test_la_voce_impostazioni_del_menu_principale(finestra):
    """Il nucleo chiede le impostazioni e aspetta che si chiudano."""
    esiti = []
    viste = []

    def chiudi():
        if finestra.dialogo_impostazioni:
            viste.append(finestra.dialogo_impostazioni.GetTitle())
            finestra.dialogo_impostazioni.EndModal(wx.ID_CANCEL)
            return
        wx.CallLater(50, chiudi)

    def nucleo():
        strato.impostazioni()
        esiti.append("chiuse")

    wx.CallLater(50, chiudi)
    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: esiti == ["chiuse"])
    assert viste == ["Impostazioni"]


def test_caffe_e_pub(gestore, monkeypatch):
    import GBwx

    mail = []
    monkeypatch.setattr(GBwx, "finestra_mail", lambda _genitore, titolo, destinatario, oggetto, *_altro, **_opzioni: mail.append((titolo, destinatario, oggetto)))
    suonati = gestore.finestra.suonati
    gestore.cambia("pub_entra", None)
    gestore.cambia("pub_aiuto", None)
    assert mail[0] == ("Entra al PUB, il gruppo di supporto", "prg-user-blind+subscribe@googlegroups.com", "Iscrizione al PUB")
    assert mail[1][:2] == ("Chiedi aiuto al PUB", "prg-user-blind@googlegroups.com")
    assert mail[1][2].startswith("Chiedo per Orologic ")
    viste = []

    def chiudi():
        for aperta in wx.GetTopLevelWindows():
            if isinstance(aperta, wx.Dialog) and aperta.IsModal():
                viste.append((aperta.GetTitle(), aperta.IsMaximized()))
                aperta.EndModal(wx.ID_OK)
                return
        wx.CallLater(50, chiudi)

    wx.CallLater(50, chiudi)
    gestore.cambia("caffe", None)
    assert viste == [("Offrimi un caffè", True)]
    assert suonati[-3:] == ["mess_pub_entra", "mess_pub_aiuto", "donazione"]


def test_l_attesa_dei_comandi_della_scacchiera(gestore):
    from orologic_modules import finestra_scacchiera

    gestore.risposte.append(1200)
    gestore.cambia("scacchiera_attesa", None)
    assert storage.LoadDB()[finestra_scacchiera.CHIAVE_ATTESA] == 1200
    assert finestra_scacchiera.attesa_dei_comandi() == 1200
    assert gestore.riga("scacchiera_attesa") == "Tempo di attesa dei comandi della scacchiera (ms): 1200"
    _tipo, titolo, domanda, valore, genere, minimo, massimo = gestore.chieste[0]
    assert titolo == "Tempo di attesa dei comandi della scacchiera (ms)"
    assert (domanda, valore, genere, minimo, massimo) == ("Tempo di attesa dei comandi della scacchiera (ms) [700]: ", 700, "intero", 200, 3000)
