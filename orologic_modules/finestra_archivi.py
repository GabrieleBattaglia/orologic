# Orologic: la finestra di PGN gestione archivi, con pgn-extract.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""PGN gestione archivi, la voce del menu principale della finestra che usa
pgn-extract di David J. Barnes (issue 74; piano di Gabriele in PE-Piano.txt,
con le decisioni del 24 novembre 2026). Il lavoro vero sta in
pgn_extract.py; qui c'e' la finestra.

All'apertura si cerca pe: se non c'e' si propone di scaricarlo, poi di
indicare dov'e'; senza, la funzione non e' disponibile e si torna al menu.
Se c'e', un filo guarda sul sito se ne e' uscita una versione nuova, o se
mancano i file che gli stanno accanto, e lo propone una volta per sessione.

I controlli, nell'ordine del Tab:
  Sorgente, il file PGN da leggere: all'apertura il percorso o il testo PGN
    degli appunti, come la ricerca PGN, altrimenti la finestra di Windows;
    accanto Seleziona il file e Dagli appunti;
  Disponibili, i parametri di pe con la loro riga di pe -h, in inglese:
    Invio mette il parametro fra gli scelti e lo toglie dai disponibili,
    tranne quelli che si ripetono; le lettere portano al parametro che
    comincia cosi', trattini esclusi; F1 apre la sua sezione della guida;
  Parametri scelti: Invio chiede il valore, col campo di testo, la scelta
    da un elenco o il selettore di file, e lo valida; Canc lo toglie; F1;
  Catene salvate, fino a dieci, nel database: Invio mette i parametri della
    catena, coi valori, al posto degli scelti; Canc la cancella dal disco
    (Gabriele, 25 novembre 2026);
  Destinazione, il file da scrivere, con Scegli la destinazione: Orologic
    propone il sorgente col primo numero libero, a1 (1).pgn, nella sua
    cartella, e dopo un lavoro riuscito il numero dopo; non puo' essere un
    file sorgente, e se c'e' gia' se ne fa prima la copia di sicurezza nella
    cartella pgn. A lavoro riuscito anche il sorgente ha la sua copia nella
    cartella pgn, una per versione (Gabriele, 24 novembre 2026);
  Comando, il comando composto e cosa fara';
  Uscita, durante il lavoro una riga che si aggiorna, poi il riassunto;
  Applica, Salva la catena, che chiede il nome e salva gli scelti, anche
    con Ctrl+S, Apri il resoconto, l'uscita completa di pe nella cartella
    txt, Guida di pgn-extract, la guida intera, ed Esci, che durante il
    lavoro ferma pe. Shift+F1 apre la guida intera da ogni controllo.
L'ordine dei parametri nel comando lo decide Orologic (decisione del 24
novembre 2026): -S davanti e i file sorgente in fondo.
"""

import os
import threading
import time

import wx
from GBUtils import Acusticator
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto, config, dialoghi, finestra_ricerca, pgn_extract
from .config import _

# Fra un tasto e l'altro della ricerca nei disponibili, in secondi.
PAUSA_FRA_I_TASTI = 1.5
# Oltre questi byte il resoconto si apre col programma di Windows: la
# finestra da leggere con milioni di caratteri si fermerebbe a lungo.
LIMITE_DEL_RESOCONTO = 2_000_000
# Il controllo degli aggiornamenti si propone una volta per sessione.
_PROPOSTO = {"fatto": False}

SUONI = {
    # Come il no della ricerca PGN: un'azione che adesso non si puo' fare.
    "no": lambda: Acusticator(["e3", 0.2, 0, config.VOLUME], kind=2),
    # Il lavoro finito senza messaggi: tre note che salgono.
    "fatto": lambda: Acusticator(["c5", 0.06, 0, config.VOLUME, "e5", 0.06, 0, config.VOLUME, "g5", 0.12, 0, config.VOLUME], kind=1, adsr=[2, 5, 90, 3]),
    # Finito, ma con messaggi di pe da leggere: le stesse note che scendono.
    "problemi": lambda: Acusticator(["g5", 0.08, 0, config.VOLUME, "e5", 0.08, 0, config.VOLUME, "c5", 0.16, 0, config.VOLUME], kind=3, adsr=[2, 5, 90, 5]),
}


def suona(evento):
    """I suoni della finestra; le prove li sostituiscono."""
    SUONI[evento]()


def titolo():
    return _("PGN gestione archivi")


def _senza_acceleratore(testo):
    return wx.StripMenuCodes(testo)


# Le finestre di Windows: le prove le sostituiscono.


def scegli_il_sorgente(genitore):
    """La finestra standard di Windows per aprire un PGN."""
    with wx.FileDialog(genitore, titolo(), wildcard=_("Partite PGN (*.pgn)|*.pgn|Tutti i file (*.*)|*.*"), style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetPath()


def scegli_la_destinazione(genitore, iniziale):
    """La finestra standard di Windows per salvare; un file che c'e' gia' si
    sostituisce dopo la copia di sicurezza, e il comando lo dice."""
    cartella = os.path.dirname(iniziale) if iniziale else config.percorso_salvataggio("pgn")
    os.makedirs(cartella, exist_ok=True)
    with wx.FileDialog(genitore, _("Scegli la destinazione"), defaultDir=cartella, defaultFile=os.path.basename(iniziale or ""),
                       wildcard=_("Partite PGN (*.pgn)|*.pgn|Tutti i file (*.*)|*.*"), style=wx.FD_SAVE) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetPath()


def scegli_un_file(genitore, titolo_della_finestra, nuovo, iniziale=None):
    """Il file del valore di un parametro: da aprire, o da scrivere."""
    stile = wx.FD_SAVE if nuovo else wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    cartella = os.path.dirname(iniziale) if iniziale else config.percorso_salvataggio("pgn")
    with wx.FileDialog(genitore, titolo_della_finestra, defaultDir=cartella if os.path.isdir(cartella) else "", defaultFile=os.path.basename(iniziale or ""),
                       wildcard=_("Tutti i file (*.*)|*.*"), style=stile) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetPath()


def scegli_pe(genitore):
    """La finestra standard di Windows per indicare pgn-extract.exe."""
    with wx.FileDialog(genitore, _("Dov'e' pgn-extract.exe?"), wildcard=_("Programmi (*.exe)|*.exe|Tutti i file (*.*)|*.*"), style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetPath()


def controlla_in_sottofondo(finestra):
    """Il filo che guarda gli aggiornamenti di pe all'apertura, una volta per
    sessione; le prove lo sostituiscono."""
    if _PROPOSTO["fatto"]:
        return
    _PROPOSTO["fatto"] = True
    percorso = finestra.pe

    def nel_filo():
        catalogo_arrivato = pgn_extract.aggiorna_il_catalogo(percorso)
        domanda, motivo = pgn_extract.aggiornamento(percorso)
        wx.CallAfter(finestra.proposta_di_aggiornamento, domanda, motivo, catalogo_arrivato)

    threading.Thread(target=nel_filo, name="pgn-extract, aggiornamenti", daemon=True).start()


# Lo scaricamento.


class FinestraScaricamento(wx.Dialog):
    """Lo scaricamento di pe dal sito, in un filo: una riga che dice a che
    punto e', e Annulla, che lo ferma. versione ed errore dicono com'e'
    andata."""

    def __init__(self, genitore):
        super().__init__(genitore, title=_("Scaricamento di pgn-extract"), style=STILE_ADATTABILE)
        self.versione = None
        self.errore = None
        self._fermato = threading.Event()
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(pannello, label=_("Scaricamento di pgn-extract")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.stato = wx.TextCtrl(pannello, value=_("Collegamento al sito di pgn-extract..."), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.stato.SetName(_("Scaricamento di pgn-extract"))
        sizer.Add(self.stato, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.Button(pannello, wx.ID_CANCEL, _("Annulla")), 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        self.stato.SetMinSize(wx.Size(-1, self.stato.GetCharHeight() * 4))
        adatta_finestra(self, pannello, (480, 240))
        self.Maximize()
        self.Bind(wx.EVT_BUTTON, lambda _evento: self._fermato.set(), id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, lambda _evento: self._fermato.set())
        self.stato.SetFocus()
        threading.Thread(target=self._nel_filo, name="pgn-extract, scaricamento", daemon=True).start()

    def _nel_filo(self):
        try:
            versione, errore = pgn_extract.scarica(lambda riga: wx.CallAfter(self._a_che_punto, riga), self._fermato.is_set)
        # Il disco o la rete possono rifiutarsi in modi imprevisti: il filo
        # non deve morire in silenzio lasciando la finestra aperta.
        except Exception as eccezione:  # noqa: BLE001
            versione, errore = None, str(eccezione)
        wx.CallAfter(self._finito, versione, errore)

    def _a_che_punto(self, riga):
        if self:
            self.stato.ChangeValue(riga)

    def _finito(self, versione, errore):
        if not self:
            return
        self.versione, self.errore = versione, errore
        finestra_ricerca.finisci(self, wx.ID_OK if versione else wx.ID_CANCEL)


def scarica_con_la_finestra(genitore):
    """(versione, errore) dello scaricamento; le prove lo sostituiscono."""
    with FinestraScaricamento(genitore) as dialogo:
        dialogo.ShowModal()
        return dialogo.versione, dialogo.errore or _("Scaricamento fermato.")


def prepara_pe(genitore, chiedi_conferma, avvisa):
    """Il percorso di pe, cercato, scaricato o indicato a mano; None se non
    c'e', detto all'utente, e si torna al menu (piano di Gabriele)."""
    percorso = pgn_extract.eseguibile()
    if percorso:
        return percorso
    domanda = _("Per la gestione degli archivi Orologic usa pgn-extract, il programma libero di David J. Barnes, ma non c'e' ancora. Lo scarico dal suo sito, con la guida e la licenza?")
    if chiedi_conferma(genitore, domanda):
        versione, errore = scarica_con_la_finestra(genitore)
        if versione:
            percorso = pgn_extract.eseguibile()
            if percorso:
                return percorso
        else:
            avvisa(genitore, _("Scaricamento non riuscito: {motivo}").format(motivo=errore))
    if chiedi_conferma(genitore, _("Vuoi indicare tu dov'e' pgn-extract.exe sul tuo computer?")):
        scelto = scegli_pe(genitore)
        if scelto and pgn_extract.versione(scelto):
            pgn_extract.ricorda_il_percorso(scelto)
            return scelto
        if scelto:
            avvisa(genitore, _("Il file scelto non risponde come pgn-extract."))
    avvisa(genitore, _("Senza pgn-extract la gestione degli archivi non e' disponibile. Torno al menu principale."))
    return None


# La finestra.


class FinestraArchivi(wx.Dialog):
    """pe e' il percorso di pgn-extract. chiedi_conferma(genitore, testo),
    avvisa(genitore, testo), annuncia(righe), chiedi_valore e scegli sono
    quelli della finestra principale; leggi(genitore, titolo, righe) apre
    una finestra da leggere; al_braille(testo), se c'e', manda una riga alla
    barra braille."""

    def __init__(self, genitore, pe, chiedi_conferma, avvisa, annuncia, chiedi_valore, scegli, leggi, al_braille=None):
        super().__init__(genitore, title=titolo(), style=STILE_ADATTABILE)
        self.pe = pe
        self._chiedi_conferma = chiedi_conferma
        self._avvisa = avvisa
        self._annuncia = annuncia
        self._chiedi_valore = chiedi_valore
        self._scegli = scegli
        self._leggi = leggi
        self._al_braille = al_braille
        self.parametri = []
        self.sezioni = []
        self.scelti = []
        # Il testo PGN degli appunti, quando il sorgente e' quello.
        self.appunti = None
        # La destinazione che Orologic ha proposto: finche' e' quella, segue
        # il sorgente e, dopo un lavoro riuscito, il numero dopo.
        self._proposta = None
        self._cercato = ""
        self._ultimo_tasto = 0.0
        self._fermato = None
        self._chiudi_alla_fine = False
        self._occupata = 0
        self.filo = None
        self.esito = None
        self.resoconto = None
        self.ultimo_invio = time.monotonic()
        self._carica_pe()
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende il
        # nome del testo creato subito prima.
        etichetta = _("&Sorgente")
        sizer.Add(wx.StaticText(pannello, label=etichetta), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.sorgente = wx.TextCtrl(pannello)
        self.sorgente.SetName(_senza_acceleratore(etichetta))
        self.pulsante_file = wx.Button(pannello, label=_("Se&leziona il file"))
        self.pulsante_appunti = wx.Button(pannello, label=_("Dagli &appunti"))
        riga.Add(self.sorgente, 1, wx.EXPAND | wx.RIGHT, 5)
        riga.Add(self.pulsante_file, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_appunti, 0)
        sizer.Add(riga, 0, wx.EXPAND | wx.ALL, 5)
        elenchi = wx.BoxSizer(wx.HORIZONTAL)
        self.disponibili = self._elenco(pannello, elenchi, _("&Disponibili"))
        self.catena = self._elenco(pannello, elenchi, _("Parametri sc&elti"))
        self.catene_salvate = self._elenco(pannello, elenchi, _("Catene sal&vate"))
        sizer.Add(elenchi, 2, wx.EXPAND)
        etichetta = _("Des&tinazione")
        sizer.Add(wx.StaticText(pannello, label=etichetta), 0, wx.LEFT | wx.RIGHT, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.destinazione = wx.TextCtrl(pannello)
        self.destinazione.SetName(_senza_acceleratore(etichetta))
        self.pulsante_destinazione = wx.Button(pannello, label=_("Scegli la desti&nazione"))
        riga.Add(self.destinazione, 1, wx.EXPAND | wx.RIGHT, 5)
        riga.Add(self.pulsante_destinazione, 0)
        sizer.Add(riga, 0, wx.EXPAND | wx.ALL, 5)
        self.comando = self._area(pannello, sizer, _("C&omando"))
        self.uscita = self._area(pannello, sizer, _("&Uscita"))
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_applica = wx.Button(pannello, label=_("A&pplica"))
        # Le lettere libere non ci sono nel suo nome: lo chiama Ctrl+S.
        self.pulsante_salva = wx.Button(pannello, label=_("Salva la catena"))
        self.pulsante_resoconto = wx.Button(pannello, label=_("Apri il reso&conto"))
        self.pulsante_guida = wx.Button(pannello, label=_("&Guida di pgn-extract"))
        esci = wx.Button(pannello, wx.ID_CANCEL, _("Esci"))
        for pulsante in (self.pulsante_applica, self.pulsante_salva, self.pulsante_resoconto, self.pulsante_guida):
            riga.Add(pulsante, 0, wx.RIGHT, 5)
        riga.Add(esci, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        for area, righe in ((self.comando, 6), (self.uscita, 6)):
            area.SetMinSize(wx.Size(-1, area.GetCharHeight() * righe))
        # Gli elenchi si misurano vuoti, come nella finestra del prompt,
        # perche' la voce piu' lunga non allarghi la finestra.
        for lista in (self.disponibili, self.catena, self.catene_salvate):
            lista.SetMinSize(lista.GetEffectiveMinSize())
        adatta_finestra(self, pannello, (800, 600))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.Bind(wx.EVT_BUTTON, lambda _evento: self.esci(), id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, lambda _evento: self.esci())
        self.pulsante_file.Bind(wx.EVT_BUTTON, lambda _evento: self.seleziona_il_file())
        self.pulsante_appunti.Bind(wx.EVT_BUTTON, lambda _evento: self.dagli_appunti())
        self.pulsante_destinazione.Bind(wx.EVT_BUTTON, lambda _evento: self.scegli_la_destinazione())
        self.pulsante_applica.Bind(wx.EVT_BUTTON, lambda _evento: self.applica())
        self.pulsante_salva.Bind(wx.EVT_BUTTON, lambda _evento: self.salva_la_catena())
        self.catene_salvate.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: self.usa_la_catena())
        self.pulsante_resoconto.Bind(wx.EVT_BUTTON, lambda _evento: self.apri_il_resoconto())
        self.pulsante_guida.Bind(wx.EVT_BUTTON, lambda _evento: self.mostra_la_guida_intera())
        self.sorgente.Bind(wx.EVT_TEXT, self._sorgente_scritto)
        self.destinazione.Bind(wx.EVT_TEXT, lambda _evento: self.aggiorna())
        self.disponibili.Bind(wx.EVT_CHAR, self._cerca)
        self.disponibili.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: self.aggiungi())
        self.catena.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: self.imposta_il_valore())
        self._riempi(0, 0)
        self._riempi_le_catene(0)
        self.aggiorna()
        self.sorgente.SetFocus()
        wx.CallAfter(self._all_ingresso)

    @staticmethod
    def _elenco(pannello, elenchi, etichetta):
        colonna = wx.BoxSizer(wx.VERTICAL)
        colonna.Add(wx.StaticText(pannello, label=etichetta), 0, wx.BOTTOM, 5)
        lista = wx.ListBox(pannello, style=wx.LB_SINGLE)
        lista.SetName(_senza_acceleratore(etichetta))
        colonna.Add(lista, 1, wx.EXPAND)
        elenchi.Add(colonna, 1, wx.EXPAND | wx.ALL, 5)
        return lista

    @staticmethod
    def _area(pannello, sizer, etichetta):
        sizer.Add(wx.StaticText(pannello, label=etichetta), 0, wx.LEFT | wx.RIGHT, 5)
        area = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        area.SetName(_senza_acceleratore(etichetta))
        sizer.Add(area, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        return area

    def _carica_pe(self):
        """I parametri da pe -h col catalogo di David, se c'e', e le sezioni
        della guida."""
        catalogo = pgn_extract.leggi_il_catalogo(pgn_extract.percorso_del_catalogo(self.pe))
        self.parametri = pgn_extract.parametri(pgn_extract.testo_dell_aiuto(self.pe) or "", catalogo)
        self.sezioni = pgn_extract.leggi_la_guida(pgn_extract.percorso_della_guida(self.pe))

    def _ricarica_i_parametri(self):
        """I parametri di nuovo, dopo uno scaricamento: gli scelti restano,
        se il pe nuovo li ha ancora."""
        voci = [scelto.parametro.voce for scelto in self.scelti]
        self._carica_pe()
        per_voce = {parametro.voce: parametro for parametro in self.parametri}
        self.scelti = [pgn_extract.Scelto(per_voce[voce], scelto.valore) for voce, scelto in zip(voci, self.scelti, strict=True) if voce in per_voce]
        self._riempi()
        self.aggiorna()

    # L'ingresso e gli aggiornamenti.

    def _all_ingresso(self):
        """Prima gli appunti, come la ricerca PGN: un percorso o un testo PGN
        diventano il sorgente, altrimenti si sceglie il file. Poi il filo
        degli aggiornamenti."""
        if not self:
            return
        sorgente = finestra_ricerca.sorgente_negli_appunti()
        if sorgente is None:
            self.seleziona_il_file()
        else:
            self._metti_il_sorgente(*sorgente)
            self.disponibili.SetFocus()
        controlla_in_sottofondo(self)

    def proposta_di_aggiornamento(self, domanda, motivo, catalogo_arrivato=False):
        """Dal filo degli aggiornamenti: la domanda, se c'e' da scaricare, o
        il motivo, se il sito non ha risposto; e, se e' arrivato da solo, il
        catalogo delle opzioni, che vale subito. Con una finestra di Windows
        aperta sopra, aspetta che si chiuda."""
        if not self:
            return
        if self._occupata or self.in_corso():
            wx.CallLater(500, self.proposta_di_aggiornamento, domanda, motivo, catalogo_arrivato)
            return
        if catalogo_arrivato:
            self._ricarica_i_parametri()
            self._aggiungi_all_uscita(_("Scaricato {nome}, il catalogo delle opzioni di pgn-extract: ora Orologic conosce anche i conflitti fra le opzioni.").format(nome=pgn_extract.CATALOGO))
        if motivo:
            self._aggiungi_all_uscita(_("Aggiornamenti di pgn-extract non verificati: {motivo}").format(motivo=motivo))
            return
        if not domanda:
            return
        with self._dialogo():
            if not self._chiedi_conferma(self, domanda):
                return
            versione, errore = scarica_con_la_finestra(self)
        if not versione:
            suona("no")
            self._aggiungi_all_uscita(_("Scaricamento non riuscito: {motivo}").format(motivo=errore))
            return
        self.pe = pgn_extract.eseguibile() or self.pe
        self._ricarica_i_parametri()
        self._aggiungi_all_uscita(_("Scaricato pgn-extract {versione}.").format(versione=versione))

    def _aggiungi_all_uscita(self, riga):
        testo = self.uscita.GetValue()
        self.uscita.ChangeValue(f"{testo}\n{riga}" if testo else riga)

    class _Occupata:
        def __init__(self, finestra):
            self.finestra = finestra

        def __enter__(self):
            self.finestra._occupata += 1

        def __exit__(self, *_dettagli):
            self.finestra._occupata -= 1

    def _dialogo(self):
        """Mentre una finestra di Windows o una domanda e' aperta sopra:
        la proposta di aggiornamento aspetta."""
        return self._Occupata(self)

    # Il sorgente e la destinazione.

    def _metti_il_sorgente(self, tipo, sorgente):
        if tipo == "testo":
            self.appunti = sorgente
            self.sorgente.ChangeValue(self._descrizione_degli_appunti())
        else:
            self.appunti = None
            self.sorgente.ChangeValue(sorgente)
        self._proponi_la_destinazione()
        self.aggiorna()

    def _proponi_la_destinazione(self):
        """La destinazione accanto al sorgente col primo numero libero, se
        e' vuota o e' ancora quella proposta: una scritta a mano resta."""
        attuale = self.destinazione.GetValue().strip()
        if attuale and attuale != self._proposta:
            return
        sorgente = self.percorso_del_sorgente()
        if self.appunti is None and not (sorgente and os.path.isfile(sorgente)):
            return
        self._proposta = pgn_extract.destinazione_proposta(sorgente)
        self.destinazione.ChangeValue(self._proposta)

    def _descrizione_degli_appunti(self):
        partite = self.appunti.count("[Event ") or 1
        return _("Il PGN degli appunti, {n} partite").format(n=partite)

    def _sorgente_scritto(self, evento):
        """Scritto a mano: il testo degli appunti non vale piu', e la
        destinazione proposta segue il file, se c'e'."""
        evento.Skip()
        self.appunti = None
        self._proponi_la_destinazione()
        self.aggiorna()

    def percorso_del_sorgente(self):
        return None if self.appunti is not None else self.sorgente.GetValue().strip().strip('"')

    def sorgente_descritto(self):
        return self._descrizione_degli_appunti() if self.appunti is not None else self.percorso_del_sorgente()

    def percorso_della_destinazione(self):
        testo = self.destinazione.GetValue().strip().strip('"')
        return os.path.abspath(testo) if testo else ""

    def seleziona_il_file(self):
        if self.in_corso():
            suona("no")
            return
        with self._dialogo():
            percorso = scegli_il_sorgente(self)
        if percorso:
            self._metti_il_sorgente("file", percorso)
            self.disponibili.SetFocus()
        else:
            self.sorgente.SetFocus()

    def dagli_appunti(self):
        if self.in_corso():
            suona("no")
            return
        sorgente = finestra_ricerca.sorgente_negli_appunti()
        if sorgente is None:
            suona("no")
            with self._dialogo():
                self._avvisa(self, _("Negli appunti non c'e' ne' il percorso di un file PGN ne' un testo PGN."))
            return
        self._metti_il_sorgente(*sorgente)
        self.sorgente.SetFocus()

    def scegli_la_destinazione(self):
        if self.in_corso():
            suona("no")
            return
        with self._dialogo():
            percorso = scegli_la_destinazione(self, self.percorso_della_destinazione())
        if percorso:
            self.destinazione.ChangeValue(percorso)
            self.aggiorna()
        self.destinazione.SetFocus()

    # Gli elenchi.

    def voci_disponibili(self):
        """I parametri fra i disponibili: tutti meno gli scelti, tranne quelli
        che si ripetono."""
        usati = {id(scelto.parametro) for scelto in self.scelti}
        return [parametro for parametro in self.parametri if parametro.ripetibile or id(parametro) not in usati]

    def _riempi(self, nei_disponibili=None, nella_catena=None):
        if nei_disponibili is None:
            nei_disponibili = max(self.disponibili.GetSelection(), 0)
        if nella_catena is None:
            nella_catena = max(self.catena.GetSelection(), 0)
        self.disponibili.Set([parametro.etichetta for parametro in self.voci_disponibili()])
        self.catena.Set([scelto.etichetta for scelto in self.scelti])
        dialoghi._seleziona(self.disponibili, nei_disponibili)
        dialoghi._seleziona(self.catena, nella_catena)

    def parametro_scelto(self, lista):
        """Il parametro della voce scelta nell'elenco, o None."""
        indice = lista.GetSelection()
        if indice == wx.NOT_FOUND:
            return None
        if lista is self.disponibili:
            voci = self.voci_disponibili()
            return voci[indice] if indice < len(voci) else None
        return self.scelti[indice].parametro if indice < len(self.scelti) else None

    def aggiungi(self):
        """Invio nei disponibili: il parametro in fondo agli scelti; il fuoco
        resta sul vicino."""
        indice = self.disponibili.GetSelection()
        voci = self.voci_disponibili()
        if indice == wx.NOT_FOUND or indice >= len(voci):
            return
        scelto = pgn_extract.Scelto(voci[indice])
        self.scelti.append(scelto)
        self._riempi(indice, len(self.scelti) - 1)
        # I conflitti del catalogo col parametro nuovo si dicono subito; i
        # gravi senza condizioni fermano poi Applica.
        contrari = [
            pgn_extract.spiega_il_conflitto(primo, secondo, conflitto)
            for primo, secondo, conflitto in pgn_extract.conflitti(self.scelti)
            if scelto.parametro is primo or scelto.parametro is secondo
        ]
        if contrari:
            suona("no")
        self._annuncia([_("Aggiunto: {voce}.").format(voce=scelto.etichetta), *contrari])
        self.aggiorna()

    def rimuovi(self):
        """Canc negli scelti: il parametro torna fra i disponibili; il fuoco
        va al vicino, o ai disponibili se non ne restano."""
        indice = self.catena.GetSelection()
        if indice == wx.NOT_FOUND or indice >= len(self.scelti):
            return
        tolto = self.scelti.pop(indice)
        self._riempi(None, indice)
        if not self.scelti:
            self.disponibili.SetFocus()
        self._annuncia([_("Tolto: {voce}.").format(voce=tolto.parametro.voce)])
        self.aggiorna()

    # Le catene salvate.

    def _riempi_le_catene(self, selezione=None):
        if selezione is None:
            selezione = max(self.catene_salvate.GetSelection(), 0)
        self.catene_salvate.Set([pgn_extract.voce_della_catena(catena) for catena in pgn_extract.catene_salvate()])
        dialoghi._seleziona(self.catene_salvate, selezione)

    def usa_la_catena(self):
        """Invio sulle catene salvate: i suoi parametri, coi valori, prendono
        il posto degli scelti. Quelli che questo pe non ha si lasciano, quelli
        il cui valore non va piu' restano senza, e si dice."""
        catene = pgn_extract.catene_salvate()
        indice = self.catene_salvate.GetSelection()
        if indice == wx.NOT_FOUND or indice >= len(catene):
            suona("no")
            return
        catena = catene[indice]
        self.scelti, mancanti, da_riscrivere = pgn_extract.scelti_dalla_catena(catena, self.parametri)
        self._riempi(None, 0)
        righe = [_("Catena {nome}: {n} parametri fra gli scelti.").format(nome=catena["nome"], n=len(self.scelti))]
        if mancanti:
            righe.append(_("Questo pgn-extract non ha: {voci}.").format(voci=", ".join(mancanti)))
        if da_riscrivere:
            righe.append(_("Il valore non va piu' bene, e va riscritto: {voci}.").format(voci=", ".join(da_riscrivere)))
        if mancanti or da_riscrivere:
            suona("no")
        self._annuncia(righe)
        self.aggiorna()

    def salva_la_catena(self):
        """Salva la catena: i parametri scelti, coi valori, sotto il nome che
        si scrive; lo stesso nome la sostituisce, se si conferma. Oltre le
        dieci catene no: prima se ne cancella una."""
        if not self.scelti:
            suona("no")
            self._annuncia([_("Non ci sono parametri scelti da salvare.")])
            return
        with self._dialogo():
            nome = self._chiedi_valore(self, wx.StripMenuCodes(_("Salva la catena")), _("Il nome della catena: "), "", "testo", 0, 60)
        nome = (nome or "").strip()
        if not nome:
            return
        catene = pgn_extract.catene_salvate()
        nuova = pgn_extract.catena_da_salvare(nome, self.scelti)
        uguale = next((indice for indice, catena in enumerate(catene) if catena["nome"].casefold() == nome.casefold()), None)
        if uguale is not None:
            with self._dialogo():
                if not self._chiedi_conferma(self, _("C'e' gia' una catena {nome}: la sostituisco con quella di adesso?").format(nome=catene[uguale]["nome"])):
                    return
            catene[uguale] = nuova
            posto = uguale
        elif len(catene) >= pgn_extract.MASSIMO_DELLE_CATENE:
            suona("no")
            with self._dialogo():
                self._avvisa(self, _("Le catene salvate sono gia' {n}: per salvarne una nuova, cancellane una con Canc.").format(n=pgn_extract.MASSIMO_DELLE_CATENE))
            return
        else:
            catene.append(nuova)
            posto = len(catene) - 1
        pgn_extract.scrivi_le_catene(catene)
        self._riempi_le_catene(posto)
        self._annuncia([_("Salvata la catena {nome}.").format(nome=nome)])

    def cancella_la_catena(self):
        """Canc sulle catene salvate: la catena se ne va dal disco."""
        catene = pgn_extract.catene_salvate()
        indice = self.catene_salvate.GetSelection()
        if indice == wx.NOT_FOUND or indice >= len(catene):
            suona("no")
            return
        tolta = catene.pop(indice)
        pgn_extract.scrivi_le_catene(catene)
        self._riempi_le_catene(min(indice, max(len(catene) - 1, 0)))
        self._annuncia([_("Cancellata la catena {nome}.").format(nome=tolta["nome"])])

    def imposta_il_valore(self):
        """Invio negli scelti: il valore, col selettore di file, la scelta da
        un elenco, il numero o il testo, validato; rifiutato, si dice perche'
        e si riscrive."""
        indice = self.catena.GetSelection()
        if indice == wx.NOT_FOUND or indice >= len(self.scelti):
            return
        scelto = self.scelti[indice]
        parametro = scelto.parametro
        if not parametro.vuole_un_valore:
            suona("no")
            self._annuncia([_("{voce} non vuole un valore.").format(voce=parametro.voce)])
            return
        with self._dialogo():
            valore = self._chiedi_il_valore(parametro, scelto.valore)
        if valore is None:
            return
        scelto.valore = valore
        self._riempi(None, indice)
        self.aggiorna()

    def _domanda(self, parametro):
        domanda = f"{parametro.voce}: {parametro.riga}" if parametro.riga else parametro.voce
        return f"{domanda} {parametro.esempio}" if parametro.esempio else domanda

    def _chiedi_il_valore(self, parametro, attuale):
        """Il valore valido, o None se si annulla."""
        if parametro.valore in ("file", "file_nuovo"):
            percorso = scegli_un_file(self, self._domanda(parametro), parametro.valore == "file_nuovo", attuale)
            if percorso is None:
                return None
            valore, motivo = pgn_extract.valida(parametro, percorso)
            if motivo:
                suona("no")
                self._avvisa(self, motivo)
                return None
            return valore
        if parametro.valore == "scelta":
            valori = [valore for valore, _spiegazione in parametro.scelte]
            voci = [f"{valore or _('(senza valore)')}: {spiegazione}" for valore, spiegazione in parametro.scelte]
            indice = self._scegli(self, self._domanda(parametro), voci, valori.index(attuale) if attuale in valori else 0)
            return None if indice is None else valori[indice]
        if parametro.valore == "intero":
            minimo = parametro.minimo if parametro.minimo is not None else 0
            massimo = parametro.massimo if parametro.massimo is not None else 999_999_999
            iniziale = int(attuale) if attuale else minimo
            numero = self._chiedi_valore(self, parametro.voce, self._domanda(parametro), iniziale, "intero", minimo, massimo)
            if numero is None:
                return None
            valore, motivo = pgn_extract.valida(parametro, str(numero))
            if motivo:
                suona("no")
                self._avvisa(self, motivo)
                return None
            return valore
        testo = attuale or ""
        while True:
            testo = self._chiedi_valore(self, parametro.voce, self._domanda(parametro), testo, "testo", 0, 4096)
            if testo is None:
                return None
            valore, motivo = pgn_extract.valida(parametro, testo)
            if motivo is None:
                return valore
            suona("no")
            self._avvisa(self, motivo)

    # La ricerca nei disponibili.

    def _cerca(self, evento):
        """Le lettere nei disponibili: il primo parametro che comincia cosi',
        senza i trattini, prima con le maiuscole come sono, poi senza; le
        lettere scritte di seguito si sommano."""
        carattere = chr(evento.GetUnicodeKey()) if evento.GetUnicodeKey() not in (wx.WXK_NONE, 0) else ""
        if not carattere or not carattere.isprintable() or carattere.isspace() or evento.ControlDown() or evento.AltDown():
            evento.Skip()
            return
        adesso = time.monotonic()
        self._cercato = (self._cercato if adesso - self._ultimo_tasto < PAUSA_FRA_I_TASTI else "") + carattere
        self._ultimo_tasto = adesso
        voci = self.voci_disponibili()
        nomi = [parametro.voce.lstrip("-") for parametro in voci]
        trovato = next((indice for indice, nome in enumerate(nomi) if nome.startswith(self._cercato)), None)
        if trovato is None:
            cercato = self._cercato.casefold()
            trovato = next((indice for indice, nome in enumerate(nomi) if nome.casefold().startswith(cercato)), None)
        if trovato is None:
            suona("no")
            return
        self.disponibili.SetSelection(trovato)

    # Il comando.

    def problemi(self):
        """Cosa manca per applicare, in righe; [] se si puo'."""
        righe = []
        sorgente = self.percorso_del_sorgente()
        if self.appunti is None and not sorgente:
            righe.append(_("Manca il file sorgente."))
        elif self.appunti is None and not os.path.isfile(sorgente):
            righe.append(_("Il file sorgente {percorso} non c'e'.").format(percorso=sorgente))
        for scelto in self.scelti:
            if scelto.manca_il_valore or (scelto.parametro.opzione == pgn_extract.ALTRO_SORGENTE and not scelto.valore):
                righe.append(_("Manca il valore di {voce}.").format(voce=scelto.parametro.voce))
        for primo, secondo, conflitto in pgn_extract.conflitti(self.scelti):
            if pgn_extract.blocca(conflitto):
                righe.append(pgn_extract.spiega_il_conflitto(primo, secondo, conflitto))
        destinazione = self.percorso_della_destinazione()
        if pgn_extract.serve_la_destinazione(self.scelti):
            if not destinazione:
                righe.append(_("Manca la destinazione."))
            elif not os.path.isdir(os.path.dirname(destinazione)):
                righe.append(_("La cartella {cartella} non c'e'.").format(cartella=os.path.dirname(destinazione)))
            else:
                sorgenti = [sorgente] + [scelto.valore for scelto in self.scelti if scelto.parametro.opzione == pgn_extract.ALTRO_SORGENTE]
                if any(pgn_extract.stesso_file(destinazione, altro) for altro in sorgenti if altro):
                    righe.append(_("La destinazione non puo' essere un file sorgente: pgn-extract lo leggerebbe e lo scriverebbe insieme, rovinandolo."))
        return righe

    def comando_composto(self, sorgente=None, uscita=None):
        return pgn_extract.argomenti(self.pe, self.scelti, sorgente or self.percorso_del_sorgente() or _("appunti.pgn"), uscita or self.percorso_della_destinazione())

    def aggiorna(self):
        """L'area del comando: il comando, cosa fara', e cosa manca."""
        if not hasattr(self, "comando"):
            return
        righe = pgn_extract.spiegazione(self.scelti, self.sorgente_descritto() or _("manca"), self.percorso_della_destinazione(), self.comando_composto())
        self.comando.ChangeValue("\n".join([*self.problemi(), *righe]))

    def in_corso(self):
        return self._fermato is not None

    def applica(self):
        """pe al lavoro nel filo, se non manca niente; altrimenti si dice
        cosa manca."""
        if self.in_corso():
            suona("no")
            return
        problemi = self.problemi()
        if problemi:
            suona("no")
            with self._dialogo():
                self._avvisa(self, "\n".join(problemi))
            return
        provvisorio = pgn_extract.file_degli_appunti(self.appunti) if self.appunti is not None else None
        sorgente = provvisorio or self.percorso_del_sorgente()
        destinazione = self.percorso_della_destinazione()
        uscita = None
        if pgn_extract.scrive_la_destinazione(self.scelti):
            uscita = pgn_extract.uscita_provvisoria(destinazione)
            cartella = os.path.dirname(destinazione)
        elif pgn_extract.serve_la_destinazione(self.scelti):
            cartella = destinazione if os.path.isdir(destinazione) else os.path.dirname(destinazione)
        else:
            cartella = os.path.dirname(os.path.abspath(sorgente))
        comando = pgn_extract.argomenti(self.pe, self.scelti, sorgente, uscita)
        # Gli archivi veri da copiare a lavoro riuscito: non il file
        # provvisorio degli appunti.
        sorgenti = [] if provvisorio else [sorgente]
        sorgenti += [scelto.valore for scelto in self.scelti if scelto.parametro.opzione == pgn_extract.ALTRO_SORGENTE and scelto.valore]
        self.resoconto = pgn_extract.percorso_del_resoconto(self.sorgente_descritto() if self.appunti is None else "appunti")
        fermato = self._fermato = threading.Event()
        self.pulsante_applica.Disable()
        riga = _("pgn-extract al lavoro...")
        self.uscita.ChangeValue(riga)
        self._annuncia([riga])

        def nel_filo():
            try:
                esito = pgn_extract.lavora(comando, cartella, self.resoconto, lambda partite: wx.CallAfter(self._avanzamento, partite), fermato.is_set)
            # pe e il disco possono fallire in modi imprevisti: il filo non
            # deve morire in silenzio con la finestra in attesa.
            except Exception as eccezione:  # noqa: BLE001
                esito = pgn_extract.Esito(None, False, pgn_extract.Riassunto(), self.resoconto, str(eccezione))
            wx.CallAfter(self._finito, esito, uscita, destinazione, provvisorio, sorgenti)

        self.filo = threading.Thread(target=nel_filo, name="pgn-extract", daemon=True)
        self.filo.start()

    def _avanzamento(self, partite):
        if not self or not self.in_corso():
            return
        riga = _("pgn-extract al lavoro: {n} partite riportate.").format(n=partite)
        self.uscita.ChangeValue(riga)
        # Col cursore sull'uscita la barra non si rinfresca da se'.
        if self._al_braille is not None and self.FindFocus() is self.uscita:
            self._al_braille(riga)

    def _finito(self, esito, uscita, destinazione, provvisorio, sorgenti=()):
        if not self:
            return
        self._fermato = None
        self.esito = esito
        if provvisorio:
            try:
                os.remove(provvisorio)
            except OSError:
                pass
        righe = []
        problemi = bool(esito.errore or esito.riassunto.tipi or esito.codice)
        if esito.errore:
            righe.append(_("pgn-extract non e' partito: {motivo}").format(motivo=esito.errore))
        elif esito.fermato:
            righe.append(_("Fermato: la destinazione non e' cambiata."))
        else:
            if esito.codice:
                righe.append(_("pgn-extract ha finito col codice {codice}.").format(codice=esito.codice))
            riuscito = esito.codice == 0
            if uscita:
                scritte, riuscito = self._sostituisci(uscita, destinazione, riuscito)
                righe.extend(scritte)
            if riuscito and pgn_extract.serve_la_destinazione(self.scelti):
                righe.extend(self._copie_dei_sorgenti(sorgenti))
                # La prossima proposta: il numero dopo, per non sovrascrivere.
                self._proponi_la_destinazione()
            righe.append(_("Finito in {secondi:.1f} secondi.").format(secondi=esito.secondi))
            righe.extend(esito.riassunto.righe())
        if uscita and os.path.exists(uscita):
            try:
                os.remove(uscita)
            except OSError:
                pass
        righe.append(_("Il resoconto completo e' in {percorso}.").format(percorso=esito.resoconto))
        self.uscita.ChangeValue("\n".join(righe))
        self.uscita.SetInsertionPoint(0)
        self.pulsante_applica.Enable()
        self.aggiorna()
        suona("problemi" if problemi or esito.fermato else "fatto")
        if self._chiudi_alla_fine:
            finestra_ricerca.finisci(self, wx.ID_CANCEL)
            return
        self.uscita.SetFocus()

    def _sostituisci(self, uscita, destinazione, riuscito):
        """(righe, scritta): la destinazione scritta, con la copia di quella
        di prima se c'era, o lasciata com'era."""
        if not riuscito or not os.path.exists(uscita):
            return [_("La destinazione non e' cambiata.")], False
        try:
            copia = pgn_extract.sostituisci(uscita, destinazione)
        except OSError as errore:
            return [_("La destinazione non si scrive: {motivo}").format(motivo=errore)], False
        righe = [_("Scritto: {destinazione}.").format(destinazione=destinazione)]
        if copia:
            righe.append(_("La copia di sicurezza del file di prima e' {copia}.").format(copia=copia))
        return righe, True

    @staticmethod
    def _copie_dei_sorgenti(sorgenti):
        """Le copie di sicurezza dei sorgenti nella cartella pgn, una per
        versione, e le righe che le dicono."""
        righe = []
        for sorgente in sorgenti:
            try:
                copia, nuova = pgn_extract.copia_del_sorgente(sorgente)
            except OSError as errore:
                righe.append(_("La copia di sicurezza di {sorgente} non si fa: {motivo}").format(sorgente=sorgente, motivo=errore))
                continue
            if nuova:
                righe.append(_("La copia di sicurezza del sorgente e' {copia}.").format(copia=copia))
            else:
                righe.append(_("Il sorgente ha gia' la sua copia di sicurezza, uguale: {copia}.").format(copia=copia))
        return righe

    # Il resoconto e la guida.

    def apri_il_resoconto(self):
        if not self.resoconto or not os.path.isfile(self.resoconto):
            suona("no")
            self._annuncia([_("Il resoconto c'e' dopo il primo lavoro.")])
            return
        if os.path.getsize(self.resoconto) > LIMITE_DEL_RESOCONTO and hasattr(os, "startfile"):
            os.startfile(self.resoconto)
            return
        with open(self.resoconto, encoding="utf-8", errors="replace") as file:
            righe = file.read().splitlines()
        with self._dialogo():
            self._leggi(self, _("Resoconto di pgn-extract"), righe)

    def mostra_la_guida(self, parametro):
        """F1: la sezione della guida che spiega il parametro."""
        if parametro is None:
            return
        with self._dialogo():
            if parametro.opzione == pgn_extract.ALTRO_SORGENTE:
                self._avvisa(self, parametro.etichetta)
                return
            if not self.sezioni:
                self._avvisa(self, _("La guida di pgn-extract non c'e': si scarica insieme a pgn-extract."))
                return
            sezione = pgn_extract.sezione_del_parametro(self.sezioni, parametro)
            if sezione is None:
                self._avvisa(self, _("La guida non ha una sezione per {voce}.").format(voce=parametro.voce))
                return
            self._leggi(self, f"{parametro.voce}: {sezione.titolo}", [sezione.titolo, *sezione.righe])

    def mostra_la_guida_intera(self):
        with self._dialogo():
            if not self.sezioni:
                self._avvisa(self, _("La guida di pgn-extract non c'e': si scarica insieme a pgn-extract."))
                return
            self._leggi(self, _("Guida di pgn-extract"), pgn_extract.guida_intera(self.sezioni))

    # I tasti e l'uscita.

    def _tasto(self, evento):
        codice = evento.GetKeyCode()
        oggetto = evento.GetEventObject()
        if codice == wx.WXK_F1 and evento.GetModifiers() == wx.MOD_SHIFT:
            self.mostra_la_guida_intera()
            return
        if codice == wx.WXK_F1 and not evento.HasAnyModifiers() and oggetto in (self.disponibili, self.catena):
            self.mostra_la_guida(self.parametro_scelto(oggetto))
            return
        if oggetto is self.catena and codice in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and not evento.HasAnyModifiers():
            self.rimuovi()
            return
        if oggetto is self.catene_salvate and codice in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and not evento.HasAnyModifiers():
            self.cancella_la_catena()
            return
        # Ctrl+S, da ogni controllo: Salva la catena.
        if codice in (ord("S"), ord("s")) and evento.GetModifiers() == wx.MOD_CONTROL:
            self.salva_la_catena()
            return
        if oggetto in (self.disponibili, self.catena, self.catene_salvate) and dialoghi.premuto_invio(evento):
            adesso = time.monotonic()
            precedente, self.ultimo_invio = self.ultimo_invio, adesso
            # Un Invio tenuto giu', o rimandato da NVDA, non conta due volte.
            if evento.IsAutoRepeat() or adesso - precedente < dialoghi.GRAZIA_INVIO:
                return
            if oggetto is self.disponibili:
                self.aggiungi()
            elif oggetto is self.catene_salvate:
                self.usa_la_catena()
            else:
                self.imposta_il_valore()
            return
        evento.Skip()

    def esci(self):
        """Esci, Esc o la chiusura: durante il lavoro pe si ferma e la
        finestra si chiude quando ha finito."""
        if self.in_corso():
            self._chiudi_alla_fine = True
            self._fermato.set()
            return
        finestra_ricerca.finisci(self, wx.ID_CANCEL)


def apri(genitore, chiedi_conferma, avvisa, annuncia, chiedi_valore, scegli, leggi, al_braille=None):
    """La gestione degli archivi dal menu principale: pe, poi la finestra."""
    pe = prepara_pe(genitore, chiedi_conferma, avvisa)
    if pe is None:
        return
    with FinestraArchivi(genitore, pe, chiedi_conferma, avvisa, annuncia, chiedi_valore, scegli, leggi, al_braille) as dialogo:
        dialogo.ShowModal()
