# Orologic, prove della finestra di PGN gestione archivi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra di pgn-extract come l'ha pensata Gabriele in PE-Piano.txt,
con le decisioni del 24 novembre 2026: il sorgente dagli appunti o dalla
finestra di Windows, la destinazione proposta, i due elenchi con Invio,
Canc e i ripetibili, il valore chiesto e validato, le lettere che cercano
nei disponibili, F1 e la guida intera, la destinazione che non puo' essere
il sorgente, il lavoro di pe con la copia di sicurezza e il riassunto, e la
ricerca di pe all'apertura. Le finestre di Windows, gli appunti e la rete
sono sostituiti; il lavoro vero parte solo se pgn-extract.exe c'e'."""

import os

import pytest
import wx
from conftest import pompa
from test_pgn_extract import AIUTO, ARCHIVIO, CATALOGO, GUIDA, PE_VERO, con_pe

from orologic_modules import config, finestra_archivi, finestra_ricerca, pgn_extract


class Prova:
    def __init__(self, monkeypatch, appunti="", file=None, pe="pe.exe", aiuto=AIUTO, catalogo=None):
        self.suoni = []
        self.domande = []
        self.avvisi = []
        self.detti = []
        self.letti = []
        self.valori = []
        self.risposte_dei_valori = []
        self.scelte = []
        self.risposta_della_lista = None
        self.risposta = True
        self.file_chiesti = 0
        self.destinazione_scelta = None
        self.file_del_valore = None

        def scegli_il_sorgente(_genitore):
            self.file_chiesti += 1
            return file

        # Gli appunti veri di chi lavora non entrano mai nelle prove.
        monkeypatch.setattr(finestra_ricerca.pyperclip, "paste", lambda: appunti)
        monkeypatch.setattr(finestra_archivi, "suona", self.suoni.append)
        monkeypatch.setattr(finestra_archivi, "scegli_il_sorgente", scegli_il_sorgente)
        monkeypatch.setattr(finestra_archivi, "scegli_la_destinazione", lambda _genitore, _iniziale: self.destinazione_scelta)
        monkeypatch.setattr(finestra_archivi, "scegli_un_file", lambda _genitore, _titolo, _nuovo, _iniziale=None: self.file_del_valore)
        monkeypatch.setattr(finestra_archivi, "controlla_in_sottofondo", lambda _finestra: None)
        if aiuto is not None:
            monkeypatch.setattr(pgn_extract, "testo_dell_aiuto", lambda _pe: aiuto)
            monkeypatch.setattr(pgn_extract, "leggi_la_guida", lambda _percorso: pgn_extract.sezioni_della_guida(GUIDA))
            # Il catalogo di David, solo quello della prova.
            self.catalogo = catalogo
            monkeypatch.setattr(pgn_extract, "leggi_il_catalogo", lambda _percorso: self.catalogo)
        self.dialogo = finestra_archivi.FinestraArchivi(
            None, pe, self._conferma, lambda _g, testo: self.avvisi.append(testo), self.detti.extend, self._valore, self._scegli, self._leggi
        )
        self.dialogo.Show()
        pompa(lambda: False, 0.1)

    def _conferma(self, _genitore, testo):
        self.domande.append(testo)
        return self.risposta

    def _valore(self, _genitore, titolo, domanda, valore, tipo="testo", minimo=0, massimo=256):
        self.valori.append((titolo, domanda, valore, tipo, minimo, massimo))
        return self.risposte_dei_valori.pop(0)

    def _scegli(self, _genitore, titolo, voci, scelta=0):
        self.scelte.append((titolo, list(voci), scelta))
        return self.risposta_della_lista

    def _leggi(self, _genitore, titolo, righe):
        self.letti.append((titolo, list(righe)))

    def scegli_fra_i_disponibili(self, voce):
        indice = [parametro.voce for parametro in self.dialogo.voci_disponibili()].index(voce)
        self.dialogo.disponibili.SetSelection(indice)
        return indice

    def aggiungi(self, voce):
        self.scegli_fra_i_disponibili(voce)
        self.dialogo.aggiungi()

    def nella_catena(self, indice):
        self.dialogo.catena.SetSelection(indice)


@pytest.fixture
def aperta(app, monkeypatch):
    aperte = []

    def apri(**opzioni):
        prova = Prova(monkeypatch, **opzioni)
        aperte.append(prova)
        return prova

    yield apri
    for prova in reversed(aperte):
        if prova.dialogo.filo is not None:
            prova.dialogo.filo.join(timeout=10)
        pompa(lambda: False, 0.05)
        prova.dialogo.Destroy()
        pompa(lambda: False, 0.05)


@pytest.fixture
def archivio(tmp_path):
    percorso = tmp_path / "Archivio di prova.pgn"
    percorso.write_text(ARCHIVIO, encoding="utf-8")
    return str(percorso)


def test_all_apertura_il_file_degli_appunti_e_la_destinazione(aperta, archivio):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    assert dialogo.sorgente.GetValue() == archivio and dialogo.appunti is None
    # Accanto al sorgente, col primo numero libero.
    assert dialogo.destinazione.GetValue() == os.path.join(os.path.dirname(archivio), "Archivio di prova (1).pgn")
    assert prova.file_chiesti == 0
    assert dialogo.FindFocus() is dialogo.disponibili
    comando = dialogo.comando.GetValue().split("\n")
    assert comando[0].startswith('Comando: pgn-extract "-o')
    assert comando[1] == f"Legge: {archivio}."


def test_il_testo_pgn_degli_appunti(aperta):
    prova = aperta(appunti=ARCHIVIO)
    dialogo = prova.dialogo
    # Gli appunti arrivano senza gli spazi e gli a capo ai bordi.
    assert dialogo.appunti == ARCHIVIO.strip()
    assert dialogo.sorgente.GetValue() == "Il PGN degli appunti, 3 partite"
    assert dialogo.destinazione.GetValue() == os.path.join(config.percorso_salvataggio("pgn"), "appunti (1).pgn")
    # Scritto a mano, il sorgente non e' piu' quello degli appunti; la
    # destinazione proposta lo segue quando e' un file che c'e'.
    dialogo.sorgente.SetValue("C:\\altro.pgn")
    assert dialogo.appunti is None and dialogo.percorso_del_sorgente() == "C:\\altro.pgn"
    assert dialogo.destinazione.GetValue().endswith("appunti (1).pgn")


def test_senza_appunti_si_sceglie_il_file(aperta, archivio):
    prova = aperta(file=archivio)
    assert prova.file_chiesti == 1
    assert prova.dialogo.sorgente.GetValue() == archivio
    vuota = aperta()
    assert vuota.dialogo.FindFocus() is vuota.dialogo.sorgente
    assert "Manca il file sorgente." in vuota.dialogo.comando.GetValue()


def test_i_due_elenchi_e_i_valori(aperta, archivio):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    disponibili = [parametro.voce for parametro in dialogo.voci_disponibili()]
    assert disponibili[0] == "Altro file sorgente" and "-C" in disponibili
    # -C se ne va dai disponibili; il fuoco resta sul vicino.
    indice = prova.scegli_fra_i_disponibili("-C")
    dialogo.aggiungi()
    assert "-C" not in [parametro.voce for parametro in dialogo.voci_disponibili()]
    assert dialogo.disponibili.GetSelection() == indice
    assert prova.detti[-1] == "Aggiunto: -C."
    # -Tw si ripete, e resta; senza valore lo dice.
    prova.aggiungi("-Tw")
    assert "-Tw" in [parametro.voce for parametro in dialogo.voci_disponibili()]
    assert dialogo.catena.GetString(1) == "-Tw (manca il valore)"
    assert "Manca il valore di -Tw." in dialogo.comando.GetValue()
    # Invio negli scelti chiede il valore, con la riga di pe nella domanda.
    prova.risposte_dei_valori = ["Carlsen"]
    prova.nella_catena(1)
    dialogo.imposta_il_valore()
    assert prova.valori[-1][1].startswith("-Tw: ")
    assert dialogo.catena.GetString(1) == "-Tw Carlsen"
    prova.aggiungi("--minmoves")
    prova.risposte_dei_valori = [20]
    prova.nella_catena(2)
    dialogo.imposta_il_valore()
    assert prova.valori[-1][3] == "intero"
    assert dialogo.catena.GetString(2) == "--minmoves 20"
    comando = dialogo.comando.GetValue().split("\n")
    assert comando[0].startswith('Comando: pgn-extract -C -TwCarlsen --minmoves 20 "-o')
    assert "-Tw Carlsen: " in dialogo.comando.GetValue()
    assert dialogo.problemi() == []
    # Un interruttore non vuole un valore.
    prova.nella_catena(0)
    dialogo.imposta_il_valore()
    assert prova.suoni[-1] == "no" and prova.detti[-1] == "-C non vuole un valore."
    # Canc lo rimette fra i disponibili, al suo posto; --minmoves, che non
    # si ripete, resta fuori finche' e' fra gli scelti.
    dialogo.rimuovi()
    assert [parametro.voce for parametro in dialogo.voci_disponibili()] == [voce for voce in disponibili if voce != "--minmoves"]
    assert [scelto.etichetta for scelto in dialogo.scelti] == ["-Tw Carlsen", "--minmoves 20"]


def test_le_catene_salvate(aperta, archivio, impostazioni_rimesse, tmp_path):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    assert dialogo.catene_salvate.GetCount() == 0
    # Senza scelti non c'e' niente da salvare.
    dialogo.salva_la_catena()
    assert prova.suoni[-1] == "no" and prova.detti[-1] == "Non ci sono parametri scelti da salvare."
    # Tre parametri, uno senza valore, salvati col nome.
    prova.aggiungi("-C")
    prova.aggiungi("-Tw")
    prova.risposte_dei_valori = ["Carlsen"]
    prova.nella_catena(1)
    dialogo.imposta_il_valore()
    prova.aggiungi("--minmoves")
    prova.risposte_dei_valori = [20, "Pulizia"]
    prova.nella_catena(2)
    dialogo.imposta_il_valore()
    dialogo.salva_la_catena()
    assert prova.valori[-1][:2] == ("Salva la catena", "Il nome della catena: ")
    assert prova.detti[-1] == "Salvata la catena Pulizia."
    assert dialogo.catene_salvate.GetString(0) == "Pulizia: -C, -Tw Carlsen, --minmoves 20"
    # Gli scelti tolti, Invio sulla catena li rimette, coi valori.
    for _volta in range(3):
        prova.nella_catena(0)
        dialogo.rimuovi()
    dialogo.catene_salvate.SetSelection(0)
    dialogo.usa_la_catena()
    assert [scelto.etichetta for scelto in dialogo.scelti] == ["-C", "-Tw Carlsen", "--minmoves 20"]
    assert prova.detti[-1] == "Catena Pulizia: 3 parametri fra gli scelti."
    # Lo stesso nome: si chiede, e solo col si' si sostituisce.
    prova.nella_catena(0)
    dialogo.rimuovi()
    prova.risposte_dei_valori = ["pulizia"]
    prova.risposta = False
    dialogo.salva_la_catena()
    assert prova.domande[-1] == "C'e' gia' una catena Pulizia: la sostituisco con quella di adesso?"
    assert pgn_extract.catene_salvate()[0]["nome"] == "Pulizia"
    prova.risposte_dei_valori = ["pulizia"]
    prova.risposta = True
    dialogo.salva_la_catena()
    assert [catena["nome"] for catena in pgn_extract.catene_salvate()] == ["pulizia"]
    assert dialogo.catene_salvate.GetString(0) == "pulizia: -Tw Carlsen, --minmoves 20"
    # Fino a dieci; l'undicesima no.
    for numero in range(2, 11):
        prova.risposte_dei_valori = [f"Catena {numero}"]
        dialogo.salva_la_catena()
    assert dialogo.catene_salvate.GetCount() == 10
    prova.risposte_dei_valori = ["Undicesima"]
    dialogo.salva_la_catena()
    assert prova.avvisi[-1] == "Le catene salvate sono gia' 10: per salvarne una nuova, cancellane una con Canc."
    assert len(pgn_extract.catene_salvate()) == 10
    # Canc la cancella dal disco.
    dialogo.catene_salvate.SetSelection(0)
    dialogo.cancella_la_catena()
    assert prova.detti[-1] == "Cancellata la catena pulizia."
    assert [catena["nome"] for catena in pgn_extract.catene_salvate()][:1] == ["Catena 2"]
    assert dialogo.catene_salvate.GetCount() == 9


def test_la_catena_con_quello_che_non_c_e_piu(aperta, archivio, impostazioni_rimesse, tmp_path):
    sparito = str(tmp_path / "sparito.pgn")
    pgn_extract.scrivi_le_catene([{"nome": "Vecchia", "parametri": [["-C", None], ["--antichissimo", None], [pgn_extract.ALTRO_SORGENTE, sparito]]}])
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    assert dialogo.catene_salvate.GetString(0) == f"Vecchia: -C, --antichissimo, Altro file sorgente: {sparito}"
    dialogo.catene_salvate.SetSelection(0)
    dialogo.usa_la_catena()
    assert [scelto.etichetta for scelto in dialogo.scelti] == ["-C", "Altro file sorgente (manca il file)"]
    assert prova.detti[-3:] == [
        "Catena Vecchia: 2 parametri fra gli scelti.",
        "Questo pgn-extract non ha: --antichissimo.",
        "Il valore non va piu' bene, e va riscritto: Altro file sorgente.",
    ]
    assert prova.suoni[-1] == "no"


def test_il_valore_rifiutato_si_riscrive(aperta, archivio):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    nuovissimo = next(parametro for parametro in dialogo.parametri if parametro.voce == "--nuovissimo")
    nuovissimo.regola = r"\d+"
    nuovissimo.esempio = "a number"
    prova.aggiungi("--nuovissimo")
    prova.risposte_dei_valori = ["tanti", "12"]
    prova.nella_catena(0)
    dialogo.imposta_il_valore()
    assert prova.avvisi == ["Il valore tanti non va bene per --nuovissimo. a number"]
    # Si riscrive partendo da quello rifiutato.
    assert prova.valori[1][2] == "tanti"
    assert dialogo.catena.GetString(0) == "--nuovissimo 12"


def test_altro_file_sorgente(aperta, archivio, tmp_path):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    prova.aggiungi("Altro file sorgente")
    # Si ripete: resta fra i disponibili.
    assert dialogo.voci_disponibili()[0].voce == "Altro file sorgente"
    assert dialogo.catena.GetString(0) == "Altro file sorgente (manca il file)"
    secondo = tmp_path / "secondo.pgn"
    secondo.write_text(ARCHIVIO, encoding="utf-8")
    prova.file_del_valore = str(secondo)
    prova.nella_catena(0)
    dialogo.imposta_il_valore()
    assert dialogo.catena.GetString(0) == f"Altro file sorgente: {secondo}"
    assert dialogo.comando_composto()[-2:] == [archivio, str(secondo)]
    assert f"Legge anche: {secondo}." in dialogo.comando.GetValue()


def test_la_destinazione_non_puo_essere_il_sorgente(aperta, archivio):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    prova.destinazione_scelta = archivio
    dialogo.scegli_la_destinazione()
    assert dialogo.destinazione.GetValue() == archivio
    dialogo.applica()
    assert prova.suoni == ["no"]
    assert prova.avvisi[-1].startswith("La destinazione non puo' essere un file sorgente")
    assert not dialogo.in_corso()


def test_i_file_che_pe_scrive_non_toccano_i_sorgenti(aperta, archivio, tmp_path, monkeypatch):
    """Rilievo R6 della revisione 2: -d e -n scrivono un file che pgn-extract
    azzera aprendolo. Non puo' essere un sorgente ne' la destinazione, e se
    c'e' gia' ha la copia di sicurezza prima del lavoro."""
    prova = aperta(appunti=archivio, aiuto=AIUTO + "-dfile -- write duplicate games to file.\n")
    dialogo = prova.dialogo
    prova.aggiungi("-d")
    prova.file_del_valore = archivio
    prova.nella_catena(0)
    dialogo.imposta_il_valore()
    assert dialogo.catena.GetString(0) == f"-d {archivio}"
    dialogo.applica()
    assert prova.suoni[-1] == "no"
    assert "Il file di -d non puo' essere un file sorgente: pgn-extract lo azzererebbe." in prova.avvisi[-1]
    assert not dialogo.in_corso()
    # Un altro file che c'e' gia': la copia prima del lavoro, che qui e' finto.
    doppioni = tmp_path / "doppioni.pgn"
    doppioni.write_text(ARCHIVIO, encoding="utf-8")
    prova.file_del_valore = str(doppioni)
    dialogo.imposta_il_valore()
    monkeypatch.setattr(pgn_extract, "lavora", lambda *_argomenti: pgn_extract.Esito(None, False, pgn_extract.Riassunto(), "", "finto"))
    dialogo.applica()
    righe = dialogo.uscita.GetValue().split("\n")
    assert righe[0].startswith(f"La copia di sicurezza di {doppioni} e' ")
    copia = righe[0].split(" e' ", 1)[1].rstrip(".")
    try:
        with open(copia, encoding="utf-8") as file:
            assert file.read() == ARCHIVIO
    finally:
        # La cartella pgn delle prove resta com'era, per la pulizia.
        os.remove(copia)


def test_le_lettere_cercano_nei_disponibili(aperta, archivio):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo

    def lettera(carattere):
        evento = wx.KeyEvent(wx.wxEVT_CHAR)
        evento.SetUnicodeKey(ord(carattere))
        dialogo._cerca(evento)
        return dialogo.voci_disponibili()[dialogo.disponibili.GetSelection()].voce

    assert lettera("m") == "--minmoves"
    # Di seguito si sommano: mi, poi min.
    assert lettera("i") == "--minmoves"
    dialogo._ultimo_tasto = 0.0
    # Le maiuscole come sono, prima: C e' -C.
    assert lettera("C") == "-C"
    dialogo._ultimo_tasto = 0.0
    lettera("z")
    assert prova.suoni[-1] == "no"


def test_f1_la_sezione_e_la_guida_intera(aperta, archivio):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    prova.aggiungi("--nuovissimo")
    dialogo.mostra_la_guida(next(parametro for parametro in dialogo.parametri if parametro.voce == "--nuovissimo"))
    assert prova.avvisi == ["La guida non ha una sezione per --nuovissimo."]
    a_mano = pgn_extract.Parametro(voce="-a", opzione="-a", prefisso="-a")
    dialogo.mostra_la_guida(a_mano)
    titolo, righe = prova.letti[-1]
    assert titolo == "-a: Output files (-o, --output, -a, --append)"
    assert righe[0] == "Output files (-o, --output, -a, --append)"
    dialogo.mostra_la_guida_intera()
    assert prova.letti[-1][0] == "Guida di pgn-extract"


def test_i_conflitti_si_dicono_e_i_gravi_fermano_applica(aperta, archivio):
    prova = aperta(appunti=archivio, catalogo=pgn_extract.catalogo_dai_dati(CATALOGO))
    dialogo = prova.dialogo
    prova.aggiungi("-7")
    assert prova.detti[-1] == "Aggiunto: -7."
    prova.aggiungi("-C")
    assert prova.suoni[-1] == "no"
    assert prova.detti[-2:] == ["Aggiunto: -C.", "-7 e -C non vanno insieme: pgn-extract si fermerebbe."]
    assert "-7 e -C non vanno insieme: pgn-extract si fermerebbe." in dialogo.problemi()
    # Il conflitto lieve si dice, ma non ferma.
    prova.aggiungi("--minmoves")
    assert prova.detti[-1].startswith("-7 e --minmoves insieme: pgn-extract ne ignorerebbe uno")
    assert not any("--minmoves insieme" in riga for riga in dialogo.problemi())
    # Tolto -C, Applica si puo'.
    prova.nella_catena(1)
    dialogo.rimuovi()
    prova.risposte_dei_valori = [20]
    prova.nella_catena(1)
    dialogo.imposta_il_valore()
    assert dialogo.problemi() == []


def test_il_catalogo_arrivato_vale_subito(aperta, archivio):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    prova.aggiungi("-C")
    assert dialogo.scelti[0].parametro.conflitti == ()
    prova.catalogo = pgn_extract.catalogo_dai_dati(CATALOGO)
    dialogo.proposta_di_aggiornamento(None, None, True)
    assert dialogo.uscita.GetValue() == "Scaricato arguments.json, il catalogo delle opzioni di pgn-extract: ora Orologic conosce anche i conflitti fra le opzioni."
    # Lo scelto resta, col catalogo.
    assert [scelto.parametro.voce for scelto in dialogo.scelti] == ["-C"]
    assert dialogo.scelti[0].parametro.conflitti == (pgn_extract.Conflitto("-7", True),)


def test_la_proposta_di_aggiornamento(aperta, archivio, monkeypatch):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    dialogo.proposta_di_aggiornamento(None, "nessuna rete")
    assert dialogo.uscita.GetValue() == "Aggiornamenti di pgn-extract non verificati: nessuna rete"
    prova.risposta = False
    scaricati = []
    monkeypatch.setattr(finestra_archivi, "scarica_con_la_finestra", lambda genitore: scaricati.append(genitore) or ("26-07", None))
    dialogo.proposta_di_aggiornamento("Scarico la 26-07?", None)
    assert prova.domande == ["Scarico la 26-07?"] and scaricati == []
    prova.risposta = True
    dialogo.proposta_di_aggiornamento("Scarico la 26-07?", None)
    assert scaricati == [dialogo]
    assert dialogo.uscita.GetValue().endswith("Scaricato pgn-extract 26-07.")


def test_senza_pe_si_propone_lo_scaricamento_poi_il_percorso(app, monkeypatch, tmp_path):
    domande = []
    avvisi = []
    risposte = [False, False]
    monkeypatch.setattr(pgn_extract, "eseguibile", lambda: None)

    def conferma(_genitore, testo):
        domande.append(testo)
        return risposte.pop(0)

    assert finestra_archivi.prepara_pe(None, conferma, lambda _g, testo: avvisi.append(testo)) is None
    assert domande[0].startswith("Per la gestione degli archivi Orologic usa pgn-extract")
    assert domande[1] == "Vuoi indicare tu dov'e' pgn-extract.exe sul tuo computer?"
    assert avvisi == ["Senza pgn-extract la gestione degli archivi non e' disponibile. Torno al menu principale."]
    # Lo scaricamento riuscito.
    scaricato = str(tmp_path / "pgn-extract.exe")
    percorsi = iter([None, scaricato])
    monkeypatch.setattr(pgn_extract, "eseguibile", lambda: next(percorsi))
    monkeypatch.setattr(finestra_archivi, "scarica_con_la_finestra", lambda _genitore: ("26-04", None))
    assert finestra_archivi.prepara_pe(None, lambda _g, _t: True, lambda _g, testo: avvisi.append(testo)) == scaricato
    # Scaricamento fallito, poi il pe indicato a mano, che risponde.
    monkeypatch.setattr(pgn_extract, "eseguibile", lambda: None)
    monkeypatch.setattr(finestra_archivi, "scarica_con_la_finestra", lambda _genitore: (None, "il sito non risponde"))
    monkeypatch.setattr(finestra_archivi, "scegli_pe", lambda _genitore: scaricato)
    monkeypatch.setattr(pgn_extract, "versione", lambda _percorso: "26-04")
    ricordati = []
    monkeypatch.setattr(pgn_extract, "ricorda_il_percorso", ricordati.append)
    avvisi.clear()
    assert finestra_archivi.prepara_pe(None, lambda _g, _t: True, lambda _g, testo: avvisi.append(testo)) == scaricato
    assert avvisi == ["Scaricamento non riuscito: il sito non risponde"] and ricordati == [scaricato]


def test_la_voce_del_menu_principale_solo_nella_finestra(monkeypatch):
    import orologic
    from orologic_modules import strato

    monkeypatch.setattr(strato, "con_la_plancia", lambda: True)
    # menu di GBUtils ordina per chiave: archivi viene dopo arbitra, al
    # quarto posto col punto (collaudo di Gabriele del 24 novembre 2026);
    # dal 25 novembre aperture, l'albero delle aperture, sta dopo analizza.
    ordinate = sorted(orologic._voci_del_menu_principale(), key=str.lower)
    assert ordinate[:5] == [".", "analizza", "aperture", "arbitra", "archivi"]
    assert orologic._voci_del_menu_principale()["archivi"] == "PGN gestione archivi (pgn-extract)"
    assert orologic._voci_del_menu_principale()["aperture"] == "Albero aperture"
    monkeypatch.setattr(strato, "con_la_plancia", lambda: False)
    assert "archivi" not in orologic._voci_del_menu_principale()
    assert "aperture" not in orologic._voci_del_menu_principale()


def test_la_destinazione_proposta_segue_il_sorgente_ma_non_quella_scritta(aperta, archivio, tmp_path):
    prova = aperta(appunti=archivio)
    dialogo = prova.dialogo
    altro = tmp_path / "Secondo (3).pgn"
    altro.write_text(ARCHIVIO, encoding="utf-8")
    dialogo.sorgente.SetValue(str(altro))
    # Il numero del sorgente si toglie: si riparte dal primo libero.
    assert dialogo.destinazione.GetValue() == str(tmp_path / "Secondo (1).pgn")
    dialogo.destinazione.SetValue(str(tmp_path / "scelta da me.pgn"))
    dialogo.sorgente.SetValue(archivio)
    assert dialogo.destinazione.GetValue() == str(tmp_path / "scelta da me.pgn")


@con_pe
def test_il_lavoro_vero_numera_e_copia_il_sorgente_una_volta(aperta, archivio):
    prova = aperta(appunti=archivio, pe=PE_VERO, aiuto=None)
    dialogo = prova.dialogo
    prova.aggiungi("-D")
    copie = []
    for numero in (1, 2):
        destinazione = os.path.join(os.path.dirname(archivio), f"Archivio di prova ({numero}).pgn")
        assert dialogo.destinazione.GetValue() == destinazione
        dialogo.applica()
        assert pompa(lambda: not dialogo.in_corso(), 20)
        righe = dialogo.uscita.GetValue().split("\n")
        assert righe[0] == f"Scritto: {destinazione}."
        copie.append(righe[1])
        os.remove(dialogo.resoconto)
    # La prima volta la copia nasce, la seconda c'e' gia', uguale.
    copia = copie[0].removeprefix("La copia di sicurezza del sorgente e' ").removesuffix(".")
    assert os.path.dirname(copia) == config.percorso_salvataggio("pgn")
    assert copie[1] == f"Il sorgente ha gia' la sua copia di sicurezza, uguale: {copia}."
    with open(copia, encoding="utf-8") as file:
        assert file.read() == ARCHIVIO
    # Il terzo lavoro avra' il numero dopo.
    assert dialogo.destinazione.GetValue().endswith("Archivio di prova (3).pgn")
    os.remove(copia)


@con_pe
def test_il_lavoro_vero_con_la_copia_di_sicurezza(aperta, archivio, tmp_path):
    prova = aperta(appunti=archivio, pe=PE_VERO, aiuto=None)
    dialogo = prova.dialogo
    destinazione = tmp_path / "Pulito.pgn"
    destinazione.write_text("il file di prima", encoding="utf-8")
    dialogo.destinazione.ChangeValue(str(destinazione))
    prova.aggiungi("-D")
    dialogo.aggiorna()
    assert "che c'e' gia': prima la copia di sicurezza" in dialogo.comando.GetValue()
    dialogo.applica()
    assert dialogo.in_corso() and not dialogo.pulsante_applica.IsEnabled()
    assert pompa(lambda: not dialogo.in_corso(), 20)
    righe = dialogo.uscita.GetValue().split("\n")
    assert righe[0] == f"Scritto: {destinazione}."
    copia = righe[1].removeprefix("La copia di sicurezza del file di prima e' ").removesuffix(".")
    with open(copia, encoding="utf-8") as file:
        assert file.read() == "il file di prima"
    os.remove(copia)
    # E la copia del sorgente, a lavoro riuscito.
    del_sorgente = righe[2].removeprefix("La copia di sicurezza del sorgente e' ").removesuffix(".")
    assert os.path.isfile(del_sorgente)
    os.remove(del_sorgente)
    # Una destinazione scritta a mano resta quella.
    assert dialogo.destinazione.GetValue() == str(destinazione)
    assert "Partite lette: 3; accettate dai criteri: 1." in righe
    assert righe[-1].startswith("Il resoconto completo e' in ")
    assert "[Event " in destinazione.read_text(encoding="utf-8")
    assert not os.path.exists(pgn_extract.uscita_provvisoria(str(destinazione)))
    # pe ha detto della mossa illegale: il suono dei messaggi.
    assert prova.suoni[-1] == "problemi"
    assert dialogo.FindFocus() is dialogo.uscita and dialogo.pulsante_applica.IsEnabled()
    dialogo.apri_il_resoconto()
    titolo, resoconto = prova.letti[-1]
    assert titolo == "Resoconto di pgn-extract" and resoconto[0].startswith("Comando: pgn-extract -D")
    os.remove(dialogo.resoconto)


def test_il_sorgente_scritto_a_mano_diventa_assoluto(aperta):
    """R71: un sorgente relativo si controllava rispetto a una cartella, e
    pgn-extract lo cercava rispetto a un'altra."""
    prova = aperta()
    prova.dialogo.sorgente.SetValue("partite.pgn")
    assert prova.dialogo.percorso_del_sorgente() == os.path.abspath("partite.pgn")
    prova.dialogo.sorgente.SetValue("")
    assert prova.dialogo.percorso_del_sorgente() == ""


def test_annulla_chiude_subito_lo_scaricamento(app, monkeypatch):
    """R67: Annulla accendeva solo il segnale, e con la rete ferma si
    aspettava fino a due minuti, in silenzio."""
    import threading

    rete_ferma = threading.Event()

    def scarica(_avanzamento, fermato):
        # La rete non risponde finche' non la si sblocca.
        rete_ferma.wait(5)
        return None, "fermato" if fermato() else None

    monkeypatch.setattr(finestra_archivi.pgn_extract, "scarica", scarica)
    dialogo = finestra_archivi.FinestraScaricamento(None)
    try:
        dialogo.Show()
        dialogo._annulla()
        assert not dialogo.IsShown() and dialogo.errore == "Scaricamento fermato."
        # Il filo e' ancora li' ad aspettare la rete: un altro scaricamento aspetta.
        versione, errore = finestra_archivi.scarica_con_la_finestra(None)
        assert versione is None and errore.startswith("Lo scaricamento di prima si sta ancora fermando")
    finally:
        rete_ferma.set()
        finestra_archivi._SCARICAMENTO["filo"].join(5)
        pompa(lambda: False, 0.1)
        dialogo.Destroy()


@con_pe
def test_le_copie_a_lavoro_finito_si_fanno_nel_filo_del_lavoro(aperta, archivio, monkeypatch):
    """R65: copia di sicurezza, confronto e copia dei sorgenti avvenivano nel
    filo della finestra, che con archivi grandi restava ferma a lavoro
    finito."""
    import threading

    fili = []
    vera = finestra_archivi.FinestraArchivi._copie_dei_sorgenti

    def copie(sorgenti):
        fili.append(threading.current_thread() is threading.main_thread())
        return vera(sorgenti)

    monkeypatch.setattr(finestra_archivi.FinestraArchivi, "_copie_dei_sorgenti", staticmethod(copie))
    prova = aperta(appunti=archivio, pe=PE_VERO, aiuto=None)
    dialogo = prova.dialogo
    prova.aggiungi("-D")
    dialogo.applica()
    assert pompa(lambda: not dialogo.in_corso(), 20)
    assert fili == [False]
    assert dialogo.uscita.GetValue().startswith("Scritto: ")
    copia = dialogo.uscita.GetValue().split("\n")[1].removeprefix("La copia di sicurezza del sorgente e' ").removesuffix(".")
    os.remove(dialogo.resoconto)
    if os.path.isfile(copia):
        os.remove(copia)
