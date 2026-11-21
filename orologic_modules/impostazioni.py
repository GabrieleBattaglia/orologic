# Orologic: le impostazioni della finestra, in un luogo solo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le impostazioni, tappa T5a della GUI (Piano della GUI.txt, S1, S2 e S4).

Nella finestra tutte le impostazioni stanno in un elenco solo, come in
MeTeOra, con il filtro: si apre con Ctrl e virgola, o con la voce
impostazioni del menu principale. Ogni riga e' Etichetta: valore, coi testi
che Orologic aveva gia', quelli del sottomenu impostazioni e delle sue
domande; i testi nuovi li ha approvati Gabriele il 21 novembre 2026. Invio
su una riga apre la sua scelta: una lista, un campo per un numero o un
testo, la finestra del prompt, o un secondo elenco, per il motore e per i
nomi. Le ultime tre voci sono Offrimi un caffè, Entra al PUB e Chiedi aiuto
al PUB.

Qui si legge e si scrive il database con le funzioni di storage, come fa il
terminale, e si mettono in uso i valori come fanno le funzioni del
terminale: il tempo e le linee dell'analisi, il volume, i nomi, il prompt.
Il motore si riavvia, o si scarica, in un filo a parte, perche' la finestra
non si fermi; le frasi del motore vanno nella console come sempre.

I suoni sono quelli del terminale, con le stesse funzioni: il tema della
voce del sottomenu quando si apre il suo elenco, il bip dopo un valore
dell'analisi o un interruttore, la nota che sale di ogni nome e l'arpeggio
quando l'elenco dei nomi si chiude, i bip delle domande del motore coi loro
lati e la nota del motore salvato, la nota bassa di un prompt sbagliato.
Il nome del giocatore, come nel terminale, non suona.
"""

import os
import sys
import threading
import time

import wx
from GBUtils import Acusticator

from . import (
    annunci,
    aspetto,
    avvio,
    config,
    dialoghi,
    engine,
    gioca,
    localizzazione,
    modello_prompt,
    pub,
    storage,
    temi,
    ui,
    version,
)
from .config import _

VOCI = (
    "analisi_tempo",
    "analisi_linee",
    "soglia_inesattezza",
    "soglia_errore",
    "soglia_svarione",
    "giocatore",
    "motore",
    "nomi",
    "prompt",
    "scacchiera_attesa",
    "salvataggio",
    "stile",
    "colori",
    "volume",
    *annunci.VOCI,
    "lingua",
    "pulizia",
    "caffe",
    "pub_entra",
    "pub_aiuto",
)
VOCI_DEL_MOTORE = ("cerca", "scarica", "manuale", "percorso", "eseguibile", "hash", "core", "skill", "overhead")
# Le soglie dell'analisi, coi loro limiti come nel terminale: ognuna sta
# sopra quella di prima.
SOGLIE = {"soglia_inesattezza": ("inesattezza", 10, 200), "soglia_errore": ("errore", None, 500), "soglia_svarione": ("svarione", None, 2000)}
# I suoni delle voci, gli stessi delle altre app per le stesse funzioni.
SUONI = {"caffe": "donazione", "caffe_paypal": "ciechino_caffe_paypal", "pub_entra": "mess_pub_entra", "pub_aiuto": "mess_pub_aiuto"}


def _riga(etichetta, valore):
    # Il formato delle righe degli annunci, Etichetta: valore.
    return _("{etichetta}: {valore}").format(etichetta=etichetta, valore=valore)


def _bip():
    """Il suono di un valore cambiato, quello delle domande del terminale."""
    Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])


class Impostazioni:
    """Le righe e i cambi dell'elenco. finestra da' le scelte, scegli e
    chiedi_valore, che le prove sostituiscono, gli annunci in uso e i suoni."""

    def __init__(self, finestra):
        self.finestra = finestra
        # La lingua scelta in questa sessione, che vale dal riavvio.
        self.prossima_lingua = None
        # Il lavoro sul motore in corso, nel suo filo.
        self.lavoro = None
        # La finestra dei colori e quella del prompt, mentre sono aperte: le
        # prove le guidano.
        self.finestra_dei_colori = None
        self.finestra_del_prompt = None

    # L'elenco principale.

    def righe(self):
        return [(voce, self.riga(voce)) for voce in VOCI]

    def riga(self, voce):
        db = storage.LoadDB()
        if voce == "analisi_tempo":
            return _riga(_("Tempo analisi default (sec)"), db.get("default_analysis_time", 1.0))
        if voce == "analisi_linee":
            return _riga(_("Linee analisi default (multipv)"), db.get("default_multipv", 3))
        if voce in SOGLIE:
            return _riga(self._nome_della_soglia(voce), self._soglie(db)[SOGLIE[voce][0]])
        if voce == "giocatore":
            return _("Il mio nome: {nome}").format(nome=db.get(gioca.CHIAVE_NOME) or _("non ancora scritto"))
        if voce == "motore":
            return _("Motore scacchistico: {nome}").format(nome=engine.ENGINE_NAME)
        if voce == "nomi":
            return _("Nomi dei pezzi, delle colonne e delle mosse")
        if voce == "prompt":
            return _("Prompt di gioco: {modello}").format(modello=modello_prompt.modello())
        if voce == "scacchiera_attesa":
            from . import finestra_scacchiera

            return _riga(_("Tempo di attesa dei comandi della scacchiera (ms)"), finestra_scacchiera.attesa_dei_comandi())
        if voce == "salvataggio":
            return _("Salvataggio automatico: {stato}").format(stato=_("attivo") if db.get("autosave_enabled") else _("non attivo"))
        if voce == "stile":
            return _("Stile dei menu: {stato}").format(stato=_("numeri") if db.get("menu_numerati") else _("parole"))
        if voce == "colori":
            return _("Colori e dimensioni")
        if voce == "volume":
            return _("Volume dei suoni: {vol}%").format(vol=round(config.VOLUME * 100))
        if voce in annunci.VOCI:
            return annunci.riga(voce, self.finestra.annunci)
        if voce == "lingua":
            return _riga(_("Lingua"), self._lingua())
        if voce == "pulizia":
            return _("Pulizia")
        return {"caffe": _("Offrimi un caffè"), "pub_entra": _("Entra al PUB"), "pub_aiuto": _("Chiedi aiuto al PUB")}[voce]

    def cambia(self, voce, dialogo):
        """Invio su una riga dell'elenco principale."""
        azioni = {
            "analisi_tempo": self._tempo,
            "analisi_linee": self._linee,
            "giocatore": self._giocatore,
            "motore": self._motore,
            "nomi": self._nomi,
            "prompt": self._prompt,
            "scacchiera_attesa": self._attesa_della_scacchiera,
            "salvataggio": lambda d: self._interruttore("autosave_enabled", _("Salvataggio automatico"), (_("attivo"), _("non attivo")), d),
            "stile": lambda d: self._interruttore("menu_numerati", _("Stile dei menu"), (_("numeri"), _("parole")), d),
            "colori": self._colori,
            "volume": self._volume,
            "lingua": self._scegli_la_lingua,
            "pulizia": self.finestra.pulizia,
            "caffe": self._caffe,
            "pub_entra": self._entra_al_pub,
            "pub_aiuto": self._chiedi_aiuto_al_pub,
        }
        if voce in SOGLIE:
            self._soglia(voce, dialogo)
        elif voce in annunci.VOCI:
            self._annuncio(voce, dialogo)
        else:
            azioni[voce](dialogo)
        if voce in VOCI and dialogo:
            dialogo.aggiorna(voce, self.riga(voce))

    # L'analisi.

    def _tempo(self, dialogo):
        attuale = storage.LoadDB().get("default_analysis_time", 1.0)
        nuovo = self.finestra.chiedi_valore(
            dialogo, _("Tempo analisi default (sec)"), _("Tempo analisi default (sec) [{cur}]: ").format(cur=attuale), attuale, "decimale", 0.1, 300
        )
        if nuovo is not None and nuovo != attuale:
            storage.SetValue("default_analysis_time", nuovo)
            engine.SetAnalysisTime(nuovo)
            _bip()

    def _linee(self, dialogo):
        attuale = storage.LoadDB().get("default_multipv", 3)
        nuovo = self.finestra.chiedi_valore(
            dialogo, _("Linee analisi default (multipv)"), _("Linee analisi default (multipv) [{cur}]: ").format(cur=attuale), attuale, "intero", 1, 20
        )
        if nuovo is not None and nuovo != attuale:
            storage.SetValue("default_multipv", nuovo)
            engine.SetMultipv(nuovo)
            _bip()

    def _attesa_della_scacchiera(self, dialogo):
        """I millisecondi che nella scacchiera interattiva un tasto aspetta il
        secondo, la lettera il numero della casa e l'1 o lo 0 l'altra cifra
        del risultato (Gabriele, collaudo della scacchiera)."""
        from . import finestra_scacchiera

        attuale = finestra_scacchiera.attesa_dei_comandi()
        titolo = _("Tempo di attesa dei comandi della scacchiera (ms)")
        nuovo = self.finestra.chiedi_valore(
            dialogo,
            titolo,
            _("Tempo di attesa dei comandi della scacchiera (ms) [{cur}]: ").format(cur=attuale),
            attuale,
            "intero",
            finestra_scacchiera.ATTESA_MINIMA,
            finestra_scacchiera.ATTESA_MASSIMA,
        )
        if nuovo is not None and nuovo != attuale:
            storage.SetValue(finestra_scacchiera.CHIAVE_ATTESA, nuovo)
            _bip()

    @staticmethod
    def _soglie(db):
        return {**storage.DEFAULT_DB["analysis_thresholds"], **db.get("analysis_thresholds", {})}

    @staticmethod
    def _nome_della_soglia(voce):
        return {"soglia_inesattezza": _("Soglia Inesattezza"), "soglia_errore": _("Soglia Errore"), "soglia_svarione": _("Soglia Svarione")}[voce]

    def _soglia(self, voce, dialogo):
        soglie = self._soglie(storage.LoadDB())
        chiave, minimo, massimo = SOGLIE[voce]
        # Ognuna sta sopra quella di prima e sotto quella dopo.
        if chiave == "inesattezza":
            massimo = min(massimo, soglie["errore"] - 1)
        elif chiave == "errore":
            minimo, massimo = soglie["inesattezza"] + 1, min(massimo, soglie["svarione"] - 1)
        else:
            minimo = soglie["errore"] + 1
        domande = {
            "inesattezza": _("Soglia Inesattezza [{cur}]: "),
            "errore": _("Soglia Errore [{cur}]: "),
            "svarione": _("Soglia Svarione [{cur}]: "),
        }
        attuale = soglie[chiave]
        nuovo = self.finestra.chiedi_valore(
            dialogo, self._nome_della_soglia(voce), domande[chiave].format(cur=attuale), min(max(attuale, minimo), massimo), "intero", minimo, massimo
        )
        if nuovo is None or nuovo == attuale:
            return

        def modifica(db):
            db["analysis_thresholds"] = {**self._soglie(db), chiave: nuovo}

        storage.UpdateDB(modifica)
        _bip()

    # Il nome, gli interruttori e il volume.

    def _giocatore(self, dialogo):
        attuale = storage.LoadDB().get(gioca.CHIAVE_NOME) or ""
        nuovo = self.finestra.chiedi_valore(dialogo, _("Il mio nome: {nome}").format(nome=attuale or _("non ancora scritto")),
                                            _("Il tuo nome, INVIO per lasciarlo com'e': "), attuale, "testo", 0, 60)
        if nuovo is None or nuovo == attuale:
            return

        def modifica(db):
            # Nella finestra il nome si puo' anche togliere, lasciando il campo vuoto.
            if nuovo:
                db[gioca.CHIAVE_NOME] = nuovo
            else:
                db.pop(gioca.CHIAVE_NOME, None)

        storage.UpdateDB(modifica)

    def _interruttore(self, chiave, titolo, nomi, dialogo):
        acceso = bool(storage.LoadDB().get(chiave))
        indice = self.finestra.scegli(dialogo, titolo, list(nomi), 0 if acceso else 1)
        if indice is None or (indice == 0) == acceso:
            return
        storage.SetValue(chiave, indice == 0)
        _bip()

    def _volume(self, dialogo):
        prima = config.VOLUME
        nuovo = self.finestra.chiedi_valore(dialogo, _("Volume dei suoni: {vol}%").format(vol=round(prima * 100)),
                                            _("Inserisci nuovo volume (0-100): "), round(prima * 100), "intero", 0, 100)
        if nuovo is None:
            return
        config.VOLUME = nuovo / 100.0
        storage.SetValue("volume", config.VOLUME)
        # Come nel terminale: il suono col volume di prima, poi con quello nuovo.
        Acusticator(["c5", 0.2, 0, prima], sync=True)
        time.sleep(0.3)
        Acusticator(["c6", 0.2, 0, config.VOLUME])

    # Gli annunci e la lingua.

    def _annuncio(self, voce, dialogo):
        f = self.finestra
        scelte = annunci.SCELTE[voce]
        nomi = [annunci.nome_della_scelta(voce, scelta) for scelta in scelte]
        indice = f.scegli(dialogo, annunci.etichetta(voce), nomi, scelte.index(f.annunci[voce]))
        if indice is None:
            return
        f.annunci = annunci.normalizza({**f.annunci, voce: scelte[indice]})
        annunci.salva(f.annunci)

    def _lingua(self):
        adesso = avvio.nome(config.lingua_rilevata)
        if self.prossima_lingua:
            # Traduttori: la voce Lingua dopo un cambio, come italiano; dal riavvio English.
            return _("{adesso}; dal riavvio {prossima}").format(adesso=adesso, prossima=avvio.nome(self.prossima_lingua))
        return adesso

    def _scegli_la_lingua(self, dialogo):
        codici = avvio.lingue() or [config.lingua_rilevata]
        attuale = self.prossima_lingua or config.lingua_rilevata
        indice = self.finestra.scegli(dialogo, _("Lingua"), [avvio.nome(c) for c in codici], codici.index(attuale) if attuale in codici else 0)
        if indice is None:
            return
        avvio.salva(codici[indice])
        self.prossima_lingua = None if codici[indice] == config.lingua_rilevata else codici[indice]

    # Colori e dimensioni.

    def _colori(self, dialogo):
        """La finestra dei colori e delle dimensioni: OK salva, Annulla o
        Esc rimettono quello che c'era se Invio su Applica a l'aveva gia'
        messo in uso."""
        prima = aspetto.carica()

        def chiedi_nome(genitore):
            return self.finestra.chiedi_valore(genitore, _("Salva colore"), _("Nome del colore:"), "", "testo", 0, aspetto.LUNGHEZZA_DEL_NOME)

        with dialoghi.FinestraColori(dialogo, prima, chiedi_nome, self._suono_dei_colori) as finestra_dei_colori:
            self.finestra_dei_colori = finestra_dei_colori
            try:
                esito = finestra_dei_colori.ShowModal()
            finally:
                self.finestra_dei_colori = None
            nuove, applicate = finestra_dei_colori.impostazioni, finestra_dei_colori.applicate
        if esito == wx.ID_OK:
            aspetto.salva(nuove)
        elif applicate:
            aspetto.applica_a_tutte(prima)

    @staticmethod
    def _suono_dei_colori(evento):
        """Invio su Applica a: il suono di un valore cambiato; Invio su un
        colore, che va nei cursori: due note brevi che salgono."""
        if evento == "applicato":
            _bip()
        else:
            Acusticator(["c6", 0.04, 0, config.VOLUME, "g6", 0.06, 0, config.VOLUME], kind=1)

    # Il caffè e il PUB.

    def _caffe(self, dialogo):
        from GBUtils import Donazione

        invito = Donazione(lang=config.lingua_rilevata, probabilita=100, stampa=False) or _("Grazie se vorrai offrire un caffè all'autore.")
        self.finestra.suona(SUONI["caffe"])
        with dialoghi.Caffe(dialogo, invito, lambda evento: self.finestra.suona(SUONI[evento])) as finestra_del_caffe:
            finestra_del_caffe.ShowModal()

    def _mail(self, dialogo, mail):
        from GBwx import finestra_mail

        finestra_mail(dialogo, mail["titolo"], mail["destinatario"], mail["oggetto"], mail["corpo"], mail["spiegazione"], mail["passi"],
                      pub.PULSANTI, pub.SENZA_POSTA)

    def _entra_al_pub(self, dialogo):
        self.finestra.suona(SUONI["pub_entra"])
        self._mail(dialogo, pub.mail_d_iscrizione())

    def _chiedi_aiuto_al_pub(self, dialogo):
        from GBUtils import informazioni_di_sistema

        self.finestra.suona(SUONI["pub_aiuto"])
        self._mail(dialogo, pub.mail_d_aiuto(version.VERSION, bool(getattr(sys, "frozen", False)), informazioni_di_sistema(",")))

    # Il prompt.

    def _prompt(self, dialogo):
        """La finestra di composizione del prompt: i testi liberi si
        scrivono in un campo, e la spiegazione dei simboli si annuncia se
        gli annunci sono attivi."""
        prima = modello_prompt.modello()

        def chiedi_testo(genitore, valore):
            return self.finestra.chiedi_valore(genitore, _("Testo libero"), _("Testo libero"), valore, "testo", 0, modello_prompt.LUNGHEZZA_MASSIMA)

        with dialoghi.FinestraPrompt(dialogo, prima, chiedi_testo, self.finestra.annuncia, modello_prompt._errore) as finestra_del_prompt:
            self.finestra_del_prompt = finestra_del_prompt
            try:
                esito = finestra_del_prompt.ShowModal()
            finally:
                self.finestra_del_prompt = None
            nuovo = finestra_del_prompt.modello or modello_prompt.PREDEFINITO
        if esito == wx.ID_OK:
            self.salva_il_prompt(prima, nuovo)

    @staticmethod
    def salva_il_prompt(prima, nuovo):
        if nuovo == prima:
            return
        modello_prompt.salva(nuovo)
        if nuovo == modello_prompt.PREDEFINITO:
            Acusticator.play("orologic_prompt_predefinito", volume=config.VOLUME)
        else:
            Acusticator.play("orologic_prompt_salvato", volume=config.VOLUME)

    # I nomi.

    def voci_dei_nomi(self):
        """Le voci dell'elenco dei nomi: (chiave, domanda), dove chiave e' il
        percorso nel dizionario dei nomi; dopo il plurale di ogni pezzo, il
        suo genere."""
        voci = []
        for gruppo, chiave, resto in ui.voci_dei_nomi():
            if gruppo == "pieces":
                campo, domanda = resto
                voci.append(((gruppo, chiave, campo), domanda))
                if campo == "pname":
                    voci.append(((gruppo, chiave, "gender"), None))
            else:
                voci.append(((gruppo, chiave), resto))
        return voci

    @staticmethod
    def _nomi_in_uso():
        return localizzazione.unisci(localizzazione.predefinito(), storage.LoadDB().get("localization", {}))

    @staticmethod
    def _valore_del_nome(nomi, chiave):
        valore = nomi
        for parte in chiave:
            valore = valore.get(parte, "") if isinstance(valore, dict) else ""
        return valore

    def riga_del_nome(self, chiave, domanda, nomi=None):
        nomi = nomi or self._nomi_in_uso()
        if chiave[-1] == "gender":
            nome = self._valore_del_nome(nomi, (*chiave[:2], "name"))
            # Traduttori: la voce del genere di un pezzo, come Genere per 'pedone'.
            return _riga(_("Genere per '{nome}'").format(nome=nome), self._valore_del_nome(nomi, chiave) or "m")
        return _riga(domanda, self._valore_del_nome(nomi, chiave))

    def _nomi(self, dialogo):
        domande = dict(self.voci_dei_nomi())
        nomi = self._nomi_in_uso()
        righe = [(chiave, self.riga_del_nome(chiave, domanda, nomi)) for chiave, domanda in domande.items()]

        def al_cambio(chiave, elenco):
            self.cambia_un_nome(chiave, domande[chiave], elenco)
            elenco.aggiorna(chiave, self.riga_del_nome(chiave, domande[chiave]))
            if chiave[-1] == "name":
                genere = (*chiave[:2], "gender")
                elenco.aggiorna(genere, self.riga_del_nome(genere, None))

        temi.suona("nomi")
        with dialoghi.FinestraImpostazioni(dialogo, righe, al_cambio, _("Nomi dei pezzi, delle colonne e delle mosse")) as elenco:
            elenco.ShowModal()
        # Come il terminale quando salva i nomi in fondo alle domande.
        ui.arpeggio_dei_nomi()

    @staticmethod
    def _indice_del_nome(chiave):
        """La posizione della voce fra le domande del terminale, che da' la
        nota; il genere ha quella del nome al plurale, la domanda dopo la
        quale il terminale lo chiede."""
        cercata = (*chiave[:2], "pname") if chiave[-1] == "gender" else chiave
        voci = ui.voci_dei_nomi()
        for indice, (gruppo, chiave_della_voce, resto) in enumerate(voci):
            percorso = (gruppo, chiave_della_voce, resto[0]) if gruppo == "pieces" else (gruppo, chiave_della_voce)
            if percorso == cercata:
                return indice, len(voci)
        return 0, len(voci)

    def cambia_un_nome(self, chiave, domanda, dialogo):
        nomi = self._nomi_in_uso()
        attuale = self._valore_del_nome(nomi, chiave)
        if chiave[-1] == "gender":
            generi = ["m", "f", "n"]
            nome = self._valore_del_nome(nomi, (*chiave[:2], "name"))
            indice = self.finestra.scegli(dialogo, _("Genere per '{nome}'").format(nome=nome), generi, generi.index(attuale) if attuale in generi else 0)
            nuovo = None if indice is None else generi[indice]
        else:
            nuovo = self.finestra.chiedi_valore(dialogo, domanda, f"{domanda} [{attuale}]: ", attuale, "testo", 0, 256)
        if nuovo is None:
            return
        # La nota di ogni risposta, anche se il nome resta com'era, come nel terminale.
        indice, totale = self._indice_del_nome(chiave)
        ui.nota_del_nome(indice, totale, genere=chiave[-1] == "gender")
        # Come nel terminale, un campo vuoto lascia il nome com'era.
        if not nuovo or nuovo == attuale:
            return
        sopra = nomi
        for parte in chiave[:-1]:
            sopra = sopra.setdefault(parte, {})
        sopra[chiave[-1]] = nuovo
        storage.SetValue("localization", nomi)
        localizzazione.ricarica()

    # Il motore.

    @staticmethod
    def _configurazione():
        return dict(storage.LoadDB().get("engine_config", {}) or {})

    def _percorso_attuale(self):
        return engine.percorso_assoluto(self._configurazione().get("engine_path", ""))

    def riga_del_motore(self, voce):
        cfg = self._configurazione()
        percorso = self._percorso_attuale()
        testi = {
            "cerca": lambda: _("cercare un motore nel tuo pc"),
            "scarica": lambda: _("scaricare Stockfish"),
            "manuale": lambda: _("modificare manualmente la configurazione"),
            "percorso": lambda: _riga(_("Percorso del motore"), os.path.dirname(percorso)),
            "eseguibile": lambda: _riga(_("Eseguibile del motore"), os.path.basename(percorso)),
            "hash": lambda: _riga(_("Hash table (MB)"), cfg.get("hash_size", 128)),
            "core": lambda: _riga(_("Core da utilizzare"), cfg.get("num_cores", 1)),
            "skill": lambda: _riga(_("Livello di skill"), cfg.get("skill_level", 20)),
            "overhead": lambda: _riga(_("Move overhead (ms)"), cfg.get("move_overhead", 0)),
        }
        return testi[voce]()

    def _motore(self, dialogo):
        righe = [(voce, self.riga_del_motore(voce)) for voce in VOCI_DEL_MOTORE]
        temi.suona("motore")
        with dialoghi.FinestraImpostazioni(dialogo, righe, self.cambia_il_motore, self.riga("motore")) as elenco:
            self.elenco_del_motore = elenco
            try:
                elenco.ShowModal()
            finally:
                self.elenco_del_motore = None

    def cambia_il_motore(self, voce, dialogo):
        if voce == "cerca":
            self._cerca_il_motore()
        elif voce == "scarica":
            self._scarica_stockfish()
        elif voce == "manuale":
            self.cambia_il_motore("percorso", dialogo)
            return
        elif voce in ("percorso", "eseguibile"):
            self._percorso(voce, dialogo)
        else:
            self._opzione(voce, dialogo)
        self._aggiorna_il_motore(dialogo)

    def _aggiorna_il_motore(self, dialogo):
        if dialogo:
            for voce in VOCI_DEL_MOTORE:
                dialogo.aggiorna(voce, self.riga_del_motore(voce))

    def _percorso(self, voce, dialogo):
        percorso = self._percorso_attuale()
        cartella, eseguibile = os.path.dirname(percorso), os.path.basename(percorso)
        if voce == "percorso":
            nuovo = self.finestra.chiedi_valore(dialogo, _("Percorso del motore"),
                                                _("Inserisci il percorso dove e' salvato il motore UCI [{default}]: ").format(default=cartella),
                                                cartella, "testo", 0, 256)
            if nuovo is None or nuovo == cartella:
                return
            cartella = nuovo
        else:
            nuovo = self.finestra.chiedi_valore(dialogo, _("Eseguibile del motore"),
                                                _("Inserisci il nome dell'eseguibile del motore [{default}]: ").format(default=eseguibile),
                                                eseguibile, "testo", 0, 64)
            if nuovo is None or nuovo == eseguibile:
                return
            eseguibile = nuovo
        if voce == "percorso":
            engine.bip_della_domanda(*engine.LATI_DELLE_DOMANDE["percorso"])
        completo = engine.percorso_assoluto(os.path.join(cartella, eseguibile))
        if not os.path.isfile(completo):
            self.finestra.avvisa(dialogo, _("Il file specificato non esiste. Verifica il percorso e il nome dell'eseguibile."))
            return
        self.salva_il_motore(completo)

    def _opzione(self, voce, dialogo):
        cfg = self._configurazione()
        massimo_dei_core = os.cpu_count() or 1
        opzioni = {
            "hash": ("hash_size", 128, 1, 4096, _("Hash table (MB)"), _("Inserisci la dimensione della hash table (min: 1, max: 4096 MB): ")),
            "core": ("num_cores", 1, 1, massimo_dei_core, _("Core da utilizzare"),
                     _("Inserisci il numero di core da utilizzare (min: 1, max: {max_cores}): ").format(max_cores=massimo_dei_core)),
            "skill": ("skill_level", 20, 0, 20, _("Livello di skill"), _("Inserisci il livello di skill (min: 0, max: 20): ")),
            "overhead": ("move_overhead", 0, 0, 500, _("Move overhead (ms)"), _("Inserisci il move overhead in millisecondi (min: 0, max: 500): ")),
        }
        chiave, predefinito, minimo, massimo, titolo, domanda = opzioni[voce]
        attuale = cfg.get(chiave, predefinito)
        nuovo = self.finestra.chiedi_valore(dialogo, titolo, domanda, min(max(attuale, minimo), massimo), "intero", minimo, massimo)
        if nuovo is None:
            return
        engine.bip_della_domanda(*engine.LATI_DELLE_DOMANDE[voce])
        if nuovo == attuale:
            return
        self.salva_il_motore(None, **{chiave: nuovo})

    def salva_il_motore(self, percorso_assoluto=None, **valori):
        """Scrive la configurazione del motore e lo riavvia, nel suo filo."""

        def modifica(db):
            cfg = dict(db.get("engine_config", {}) or {})
            if percorso_assoluto:
                cfg["engine_path"], cfg["engine_is_relative"] = engine.percorso_da_salvare(percorso_assoluto)
            cfg.update(valori)
            db["engine_config"] = cfg

        storage.UpdateDB(modifica)
        self.in_disparte(self._riavvia_il_motore)

    @staticmethod
    def _riavvia_il_motore():
        """Come in fondo alla configurazione del terminale: il motore riparte,
        poi la nota del motore salvato."""
        engine.InitEngine()
        engine.suono_del_motore_salvato()

    def _cerca_il_motore(self):
        cartella, eseguibile, _usato = engine.SearchForEngine()
        if cartella and eseguibile:
            self.salva_il_motore(engine.percorso_assoluto(os.path.join(cartella, eseguibile)))

    def _scarica_stockfish(self):
        from . import stockfish_installer

        def lavoro():
            # Il motore in uso si chiude prima: Windows non sposta una cartella
            # con dentro un eseguibile aperto.
            engine.CloseEngine()
            cartella, eseguibile = stockfish_installer.DownloadAndInstallEngine()
            if cartella and eseguibile:

                def modifica(db):
                    cfg = dict(db.get("engine_config", {}) or {})
                    cfg["engine_path"], cfg["engine_is_relative"] = engine.percorso_da_salvare(os.path.join(cartella, eseguibile))
                    db["engine_config"] = cfg

                storage.UpdateDB(modifica)
            self._riavvia_il_motore()

        self.in_disparte(lavoro)

    def in_disparte(self, lavoro):
        """Il lavoro sul motore in un filo suo; finito, si riscrivono le righe
        del motore negli elenchi ancora aperti. Uno alla volta."""
        if self.lavoro is not None and self.lavoro.is_alive():
            return
        self.lavoro = threading.Thread(target=self._lavora, args=(lavoro,), name="motore di Orologic", daemon=True)
        self.lavoro.start()

    def _lavora(self, lavoro):
        try:
            lavoro()
        except Exception as errore:  # noqa: BLE001 - l'errore del motore si dice nella console
            print(_("Errore motore: {e}").format(e=errore))
        finally:
            self.finestra.dopo_il_motore()
