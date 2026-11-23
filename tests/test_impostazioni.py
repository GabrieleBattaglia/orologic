# Orologic, prove delle impostazioni della finestra (tappa T5a della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il luogo unico delle impostazioni: le righe coi testi di Orologic, e i
cambi voce per voce, con le scelte e i campi sostituiti da risposte scritte.
Il motore non parte mai: InitEngine e CloseEngine si segnano. I file delle
impostazioni della cartella delle prove si rimettono com'erano."""


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
def gestore(finestra, monkeypatch, impostazioni_rimesse):
    """Il gestore della finestra vera, con le risposte in fila e i file
    rimessi a posto."""
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
    # Il nucleo fermo in un menu: il motore si puo' cambiare.
    monkeypatch.setattr(finestra, "motore_in_uso", lambda: False)
    monkeypatch.setattr(impostazioni, "Acusticator", type("Muto", (), {"__call__": lambda *_a, **_o: None, "play": staticmethod(lambda *_a, **_o: None)})())
    motore = []
    monkeypatch.setattr(engine, "InitEngine", lambda: motore.append("avviato"))
    monkeypatch.setattr(engine, "CloseEngine", lambda: motore.append("chiuso"))
    finestra.gestore.risposte, finestra.gestore.chieste, finestra.gestore.motore = risposte, chieste, motore
    try:
        yield finestra.gestore
    finally:
        if finestra.gestore.lavoro is not None:
            finestra.gestore.lavoro.join(5)


def test_le_righe_coi_testi_di_orologic(gestore):
    righe = dict(gestore.righe())
    assert list(righe) == list(impostazioni.VOCI)
    assert righe["analisi_tempo"] == "Tempo analisi default (sec): 1.0"
    assert righe["soglia_errore"] == "Soglia Errore: 10%"
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
    # Le soglie sono punti di calo della probabilita' di vittoria, 5, 10 e 15.
    gestore.risposte.extend([2.5, 12, 4])
    gestore.cambia("analisi_tempo", None)
    gestore.cambia("soglia_errore", None)
    gestore.cambia("soglia_inesattezza", None)
    db = storage.LoadDB()
    assert db["default_analysis_time"] == 2.5
    assert engine.analysis_time == 2.5
    assert db["analysis_thresholds"]["calo_errore"] == 12
    assert db["analysis_thresholds"]["calo_inesattezza"] == 4
    # Le altre soglie restano.
    assert db["analysis_thresholds"]["mossa_geniale_gap"] == 180
    # I limiti come nel terminale: l'errore sopra l'inesattezza, sotto lo svarione.
    _tipo, titolo, domanda, _valore, genere, minimo, massimo = gestore.chieste[1]
    assert (titolo, domanda, genere, minimo, massimo) == ("Soglia Errore", "Soglia Errore [10]: ", "intero", 6, 14)
    assert gestore.chieste[2][-2:] == (1, 11)


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


def test_il_motore_in_uso_non_si_cambia(gestore, monkeypatch):
    prima = storage.LoadDB().get("engine_config")
    monkeypatch.setattr(gestore.finestra, "motore_in_uso", lambda: True)
    for voce in ("cerca", "scarica", "manuale", "percorso", "eseguibile", "hash", "core", "skill", "overhead"):
        gestore.cambia_il_motore(voce, None)
    avviso = ("avviso", "Il motore e' in uso: si puo' cambiare da un menu, a partita o analisi finita.")
    assert gestore.chieste == [avviso] * 9
    assert gestore.lavoro is None and gestore.motore == []
    assert storage.LoadDB().get("engine_config") == prima
    # Le righe del motore si guardano lo stesso.
    assert gestore.riga_del_motore("hash").startswith("Hash table (MB): ")


def test_quando_il_motore_e_in_uso(finestra):
    from orologic_modules.finestra import Attesa

    prima = finestra.attesa
    try:
        finestra.attesa = Attesa("menu")
        assert not finestra.motore_in_uso()
        # Dentro una partita no, anche a un menu, come quelli di Easyfish.
        with strato.partita():
            assert finestra.motore_in_uso()
        # Mentre il nucleo lavora, o aspetta una mossa, un testo, un tasto o
        # un si' o no, no.
        for tipo in (None, "area", "sino"):
            finestra.attesa = Attesa(tipo)
            assert finestra.motore_in_uso(), tipo
        # Le impostazioni della voce del menu principale: il nucleo aspetta.
        finestra.attesa = Attesa(None)
        finestra.impostazioni_del_nucleo = True
        assert not finestra.motore_in_uso()
    finally:
        finestra.attesa = prima
        finestra.impostazioni_del_nucleo = False


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


def test_le_righe_dell_area_principale(gestore):
    """Gabriele, collaudo del 22 novembre 2026: di serie 200 righe; il
    valore nuovo vale subito, e l'area tiene solo quelle."""
    from orologic_modules import finestra as modulo_finestra

    assert gestore.riga("righe_area") == "Quante righe conservo nell'area principale? 200"
    gestore.risposte.append(50)
    gestore.cambia("righe_area", None)
    assert storage.LoadDB()[modulo_finestra.CHIAVE_DELLE_RIGHE] == 50
    assert gestore.riga("righe_area") == "Quante righe conservo nell'area principale? 50"
    _tipo, titolo, domanda, valore, genere, minimo, massimo = gestore.chieste[0]
    assert titolo == "Quante righe conservo nell'area principale?"
    assert (domanda, valore, genere, minimo, massimo) == ("Quante righe conservo nell'area principale? [200]: ", 200, "intero", 20, 10000)
    finestra = gestore.finestra
    assert finestra.righe_tenute == 50
    di_prima = finestra.righe
    try:
        finestra.righe = [f"riga {numero}" for numero in range(70)]
        assert finestra._taglia_il_registro() == 20
        assert len(finestra.righe) == 50 and finestra.righe[0] == "riga 20"
        # Fino a un quarto in piu' restano tutte.
        finestra.righe.extend(["altra"] * 12)
        assert finestra._taglia_il_registro() == 0
    finally:
        finestra.righe = di_prima
