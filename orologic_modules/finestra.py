# Orologic: la finestra, con l'area unica che fa da console.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra di Orologic, tappe T2 e T3 della GUI (Piano della GUI.txt).

Il nucleo di Orologic gira in un filo suo, esattamente come nel terminale:
scrive con print e sys.stdout, legge con key, menu, enter_escape e dgt di
GBUtils e con lo strato. La finestra gli fa da terminale con una grande area
di testo, uscita e ingresso insieme.

  FacciaFinestra   la tastiera e lo schermo del nucleo: una sola coda di
                   tasti, letta dallo strato (kbhit, getwch), da key con
                   sorgente_dei_tasti di GBUtils e da input e getpass con
                   leggi_riga; e il testo scritto, consegnato alla finestra a
                   pezzi, ognuno con la sua causa.
  UscitaFinestra   lo stdout del nucleo.
  IngressoFinestra lo stdin del nucleo, per input e quindi per dgt.
  Terminale        il terminale imitato: la riga in corso e la colonna del
                   cursore, con i ritorni carrello, i backspace e gli a capo.
  Finestra         l'area, i tasti e gli annunci con GBsintesi.

Gli annunci seguono le impostazioni di annunci.py: se si fanno, con quale
uscita e dove, e se interrompono quello in corso. F3 apre la finestra delle
impostazioni, finche' non c'e' la plancia della T4.

Le due forme dell'area. Fuori dal gioco scorre come un terminale. Durante una
partita, quando lo strato le consegna chi da' i dati, diventa il cruscotto di
cruscotto.py, che si riscrive da solo ogni secondo, col prompt in fondo: le
righe stampate diventano i messaggi, e restano anche nel registro della
console, che torna intero a fine partita. Nel cruscotto i rinfreschi lasciano
il cursore sulla stessa riga della stessa sezione e alla stessa colonna.

Le cause del testo. eco e' cio' che il nucleo scrive subito dopo un
carattere letto con getwch, cioe' l'eco del carattere nei cicli d'attesa, e
l'eco che leggi_riga fa da se': NVDA dice gia' i caratteri premuti, quindi
la riga in corso cambiata dall'eco non si annuncia. tasto e' cio' che segue
Invio, Esc o un tasto letto da key: e' la risposta a un tasto, e di partenza
interrompe la voce. None e' il testo che il nucleo scrive da se', per
l'orologio, per una mossa arrivata o da un altro filo, e di partenza si
accoda. Le righe chiuse si
annunciano sempre, tranne quella del prompt in cui si e' appena scritto.

Le lezioni della T0: riga e colonna si chiedono all'area, che non va a capo
da sola; frecce, pagine, Home e Fine passano all'area, per leggere liberi;
ogni altro tasto riporta il cursore al suo posto nella riga in corso.
"""

import getpass
import io
import os
import queue
import sys
import threading
import time
import traceback

import wx
from GBsintesi import Sintesi
from GBUtils import sorgente_dei_tasti

from . import annunci, cruscotto, dialoghi, strato, version
from .config import _

# L'eco e' solo cio' che il nucleo scrive entro questi secondi dal tasto: i
# cicli d'attesa guardano l'orologio prima di kbhit, e un rinfresco a tempo
# che cade al giro dopo un tasto non e' un eco.
ECO_MASSIMO = 0.015
# Le righe che l'area tiene; oltre, le piu' vecchie se ne vanno a gruppi.
RIGHE_TENUTE = 5000
RIGHE_TOLTE_ALLA_VOLTA = 200
# Quanti secondi il nucleo ha per chiudersi da solo, quando si chiude la finestra.
ATTESA_DELLA_CHIUSURA = 5.0
# La larghezza che lo strato dichiara: pulisci_riga scrive tanti spazi, che
# l'area non mostra.
COLONNE = 300


class CambioDiForma:
    """Nella fila del testo, il punto in cui l'area cambia forma: il
    fornitore dei dati del cruscotto, o None per tornare alla console. Sta
    nella stessa fila del testo perche' l'ordine non si perda: cio' che il
    nucleo scrive dopo l'inizio della partita va nel cruscotto."""

    def __init__(self, fornitore):
        self.fornitore = fornitore


class FacciaFinestra:
    """La faccia dello strato per la finestra, e la sorgente dei tasti di key."""

    def __init__(self):
        self._tasti = queue.Queue()
        self._lucchetto = threading.Lock()
        self._pezzi = []
        self._causa = None
        self._quando = 0.0
        self._chiusura = threading.Event()
        self.avvisa = None

    # Il lato del nucleo.

    def _controlla_chiusura(self):
        if self._chiusura.is_set():
            raise KeyboardInterrupt

    def _prendi(self, attesa=None):
        """Il prossimo tasto, o None se l'attesa scade. Con la finestra che
        si chiude solleva KeyboardInterrupt, come Ctrl+C nel terminale."""
        scadenza = None if attesa is None else time.monotonic() + max(0.0, attesa)
        while True:
            self._controlla_chiusura()
            passo = 0.05 if scadenza is None else min(0.05, max(0.0, scadenza - time.monotonic()))
            try:
                return self._tasti.get(timeout=passo)
            except queue.Empty:
                if scadenza is not None and time.monotonic() >= scadenza:
                    return None

    def kbhit(self):
        self._controlla_chiusura()
        self._causa = None
        return not self._tasti.empty()

    def getwch(self):
        tasto = self._prendi()
        self._causa = "tasto" if tasto in ("\r", "\x1b") else "eco"
        self._quando = time.monotonic()
        return tasto

    def tasto_per_key(self, attesa):
        """La sorgente di key: key non fa l'eco, quindi quello che segue e'
        sempre una risposta."""
        tasto = self._prendi(attesa)
        if tasto is not None:
            self._causa = "tasto"
            self._quando = time.monotonic()
        return tasto

    def leggi_riga(self, eco=True):
        """Una riga, come la console la da' a input: i caratteri con l'eco
        se eco e' vero, Backspace cancella, Esc svuota la riga, Invio la
        consegna."""
        scritti = []
        while True:
            tasto = self._prendi()
            if tasto == "\r":
                self.scrivi("\n", "tasto")
                self._causa = "tasto"
                self._quando = time.monotonic()
                return "".join(scritti)
            if tasto == "\x08":
                if scritti:
                    scritti.pop()
                    if eco:
                        self.scrivi("\b \b", "eco")
            elif tasto == "\x1b":
                if scritti and eco:
                    self.scrivi("\b \b" * len(scritti), "eco")
                scritti.clear()
            elif tasto.isprintable():
                scritti.append(tasto)
                if eco:
                    self.scrivi(tasto, "eco")

    def svuota_tastiera(self):
        while True:
            try:
                self._tasti.get_nowait()
            except queue.Empty:
                return

    def larghezza(self):
        return COLONNE

    def cruscotto(self, fornitore):
        with self._lucchetto:
            primo = not self._pezzi
            self._pezzi.append((CambioDiForma(fornitore), None))
        if primo and self.avvisa is not None:
            self.avvisa()

    def scrivi(self, testo, causa=None):
        if causa is None:
            causa = self._causa
            if causa == "eco" and time.monotonic() - self._quando > ECO_MASSIMO:
                causa = None
        with self._lucchetto:
            primo = not self._pezzi
            self._pezzi.append((testo, causa))
        if primo and self.avvisa is not None:
            self.avvisa()

    # Il lato della finestra.

    def premi(self, tasto):
        self._tasti.put(tasto)

    def prendi_il_testo(self):
        with self._lucchetto:
            pezzi, self._pezzi = self._pezzi, []
        return pezzi

    def chiudi(self):
        self._chiusura.set()


class UscitaFinestra(io.TextIOBase):
    """Lo stdout del nucleo: tutto quello che scrive va alla faccia."""

    def __init__(self, faccia):
        super().__init__()
        self._faccia = faccia

    def writable(self):
        return True

    def write(self, testo):
        if testo:
            self._faccia.scrivi(testo)
        return len(testo)

    def flush(self):
        pass

    def isatty(self):
        return False

    @property
    def encoding(self):
        return "utf-8"


class IngressoFinestra(io.TextIOBase):
    """Lo stdin del nucleo: input lo legge una riga alla volta."""

    def __init__(self, faccia):
        super().__init__()
        self._faccia = faccia

    def readable(self):
        return True

    def readline(self, size=-1):
        return self._faccia.leggi_riga() + "\n"

    def isatty(self):
        return False

    @property
    def encoding(self):
        return "utf-8"


class Terminale:
    """Il terminale imitato: le righe si chiudono con l'a capo, il ritorno
    carrello riporta il cursore a inizio riga, il backspace lo sposta indietro
    di uno, ogni altro carattere scrive sopra o in fondo."""

    def __init__(self):
        self.riga = []
        self.colonna = 0

    def applica(self, testo):
        """Applica il testo e restituisce le righe chiuse, senza spazi in fondo."""
        chiuse = []
        for carattere in testo:
            if carattere == "\n":
                chiuse.append(self.visibile().rstrip())
                self.riga, self.colonna = [], 0
            elif carattere == "\r":
                self.colonna = 0
            elif carattere == "\b":
                self.colonna = max(0, self.colonna - 1)
            elif carattere == "\t" or carattere >= " ":
                if self.colonna < len(self.riga):
                    self.riga[self.colonna] = carattere
                else:
                    self.riga.extend(" " * (self.colonna - len(self.riga)))
                    self.riga.append(carattere)
                self.colonna += 1
        return chiuse

    def visibile(self):
        """La riga in corso, senza gli spazi in fondo che stanno oltre il cursore."""
        testo = "".join(self.riga)
        return testo[: max(self.colonna, len(testo.rstrip()))]


def _parte_nuova(riga, detta):
    """Cio' che di una riga va annunciato, sapendo che detta e' gia' stata
    sentita: niente se e' la stessa, la sola coda se la riga la continua,
    come dice NVDA nel terminale, altrimenti la riga intera."""
    riga, detta = riga.rstrip(), detta.rstrip()
    if not riga.strip() or riga == detta:
        return ""
    if detta.strip() and riga.startswith(detta):
        return riga[len(detta):].strip()
    return riga.strip()


class Finestra(wx.Frame):
    def __init__(self, faccia):
        super().__init__(None, title=_("Orologic {versione}").format(versione=version.VERSION))
        self.faccia = faccia
        pannello = wx.Panel(self)
        self.area = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL | wx.TE_DONTWRAP)
        self.area.SetName(_("Console"))
        dimensionatore = wx.BoxSizer(wx.VERTICAL)
        dimensionatore.Add(self.area, 1, wx.EXPAND)
        pannello.SetSizer(dimensionatore)
        self.terminale = Terminale()
        # Le righe chiuse della console; la riga in corso viene dopo. Durante
        # il cruscotto continuano a raccogliersi, e tornano a fine partita.
        self.righe = []
        # Il cruscotto: chi da' i dati, i messaggi della partita, le righe
        # mostrate come coppie (sezione, testo), l'orologio che lo rinfresca.
        self.fornitore = None
        self.messaggi = []
        self.mostrate = []
        self.orologio = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _evento: self._ridisegna(), self.orologio)
        # La riga in corso come l'utente l'ha gia' sentita o scritta.
        self.detta = ""
        self.programmato = False
        self.sintesi = Sintesi()
        self.annunci = annunci.carica()
        self.nucleo = None
        self.chiudendo = False
        # Finito il nucleo la finestra si chiude; le prove la tengono aperta
        # per leggerla.
        self.chiudi_alla_fine = True
        self.area.Bind(wx.EVT_CHAR, self._carattere)
        self.area.Bind(wx.EVT_KEY_DOWN, self._tasto_giu)
        self.Bind(wx.EVT_CLOSE, self._chiudi)
        faccia.avvisa = self._avvisa
        self.Maximize()
        self.area.SetFocus()

    # I tasti.

    def _riga_del_prompt(self):
        """La riga in corso, l'ultima dell'area, nelle due forme."""
        if self.fornitore is not None and self.mostrate:
            return len(self.mostrate) - 1
        return len(self.righe)

    def _riga_e_colonna(self):
        trovata, colonna, riga = self.area.PositionToXY(self.area.GetInsertionPoint())
        if not trovata:
            return self._riga_del_prompt(), 0
        return min(riga, self._riga_del_prompt()), colonna

    def _vai(self, riga, colonna):
        lunghezza = self.area.GetLineLength(riga)
        self.area.SetInsertionPoint(self.area.XYToPosition(max(0, min(colonna, lunghezza)), riga))

    def _al_cursore(self):
        self._vai(self._riga_del_prompt(), self.terminale.colonna)

    def _manda(self, tasto):
        if self._riga_e_colonna()[0] != self._riga_del_prompt():
            self._al_cursore()
        self.faccia.premi(tasto)

    def _carattere(self, evento):
        codice = evento.GetUnicodeKey()
        if codice == wx.WXK_RETURN:
            self._manda("\r")
        elif codice == wx.WXK_BACK:
            self._manda("\x08")
        elif codice == wx.WXK_ESCAPE:
            self._manda("\x1b")
        elif codice != wx.WXK_NONE and codice >= 32 and not (evento.ControlDown() and not evento.AltDown()):
            self._manda(chr(codice))
        else:
            # Frecce, pagine, Home, Fine e il resto: all'area, per leggere.
            evento.Skip()

    def _tasto_giu(self, evento):
        codice = evento.GetKeyCode()
        ctrl, shift = evento.ControlDown(), evento.ShiftDown()
        if codice == wx.WXK_F3 and not ctrl and not shift and not evento.AltDown():
            self.impostazioni()
            return
        if (ctrl and codice == ord("V")) or (shift and codice == wx.WXK_INSERT):
            self._incolla()
            return
        # Tagliare, cancellare, annullare e ripetere cambierebbero l'area
        # alle spalle del nucleo.
        if codice in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) or (ctrl and codice in (ord("X"), ord("Z"), ord("Y"))):
            return
        evento.Skip()

    def _incolla(self):
        """Gli appunti vanno al nucleo come tasti, fino al primo a capo."""
        if not wx.TheClipboard.Open():
            return
        try:
            dati = wx.TextDataObject()
            if wx.TheClipboard.GetData(dati) and dati.GetText():
                for carattere in dati.GetText().splitlines()[0]:
                    if carattere.isprintable():
                        self._manda(carattere)
        finally:
            wx.TheClipboard.Close()

    # Il testo.

    def _avvisa(self):
        wx.CallAfter(self._programma)

    def _programma(self):
        if not self.programmato:
            self.programmato = True
            wx.CallLater(15, self._applica)

    def _applica(self):
        """Il testo del nucleo nell'area, e l'annuncio di quello nuovo."""
        self.programmato = False
        pezzi = self.faccia.prendi_il_testo()
        if not pezzi or not self:
            return
        chiuse = []
        # Le righe chiuse che sono messaggi: non la riga del prompt in cui si
        # e' appena scritto, che nel cruscotto sta gia' fra le ultime mosse.
        messaggi = []
        da_dire = []
        dal_tasto = False
        ultima_causa = None
        for testo, causa in pezzi:
            if isinstance(testo, CambioDiForma):
                # Il testo arrivato prima va nella forma di prima.
                self._mostra_nella_forma(chiuse, messaggi)
                chiuse, messaggi = [], []
                self._cambia_forma(testo.fornitore)
                continue
            ultima_causa = causa
            if causa == "tasto":
                dal_tasto = True
            for riga in self.terminale.applica(testo):
                chiuse.append(riga)
                if riga.strip() and riga.rstrip() != self.detta.rstrip():
                    messaggi.append(riga)
                nuovo = _parte_nuova(riga, self.detta)
                if nuovo:
                    da_dire.append(nuovo)
                self.detta = ""
            # L'eco si aggiunge a cio' che e' gia' stato sentito pezzo per
            # pezzo: con i tasti rapidi l'eco e l'Invio arrivano insieme.
            if causa == "eco":
                self.detta = self.terminale.visibile()
        visibile = self.terminale.visibile()
        if visibile.strip():
            if ultima_causa != "eco":
                nuovo = _parte_nuova(visibile, self.detta)
                if nuovo:
                    da_dire.append(nuovo)
            self.detta = visibile
        self._mostra_nella_forma(chiuse, messaggi)
        self._di(da_dire, dal_tasto)

    def _mostra_nella_forma(self, chiuse, messaggi):
        """Le righe chiuse e la riga in corso, nella forma dell'area di adesso."""
        if self.fornitore is not None:
            self.righe.extend(chiuse)
            self._taglia_il_registro()
            self.messaggi.extend(messaggi)
            del self.messaggi[: -cruscotto.MESSAGGI_MOSTRATI]
            self._ridisegna()
        elif chiuse or self.area.GetLineText(len(self.righe)) != self.terminale.visibile():
            self._mostra(chiuse, self.terminale.visibile())

    def _taglia_il_registro(self):
        """Le righe piu' vecchie se ne vanno a gruppi; restituisce quante."""
        if len(self.righe) <= RIGHE_TENUTE + RIGHE_TOLTE_ALLA_VOLTA:
            return 0
        del self.righe[:RIGHE_TOLTE_ALLA_VOLTA]
        return RIGHE_TOLTE_ALLA_VOLTA

    def _mostra(self, chiuse, visibile):
        """Le righe chiuse prendono il posto della riga in corso, che va in
        fondo. Il cursore, se era nella riga in corso, va al cursore del
        nucleo; se l'utente rileggeva piu' su, resta dov'era."""
        riga, colonna = self._riga_e_colonna()
        sul_fondo = riga >= len(self.righe)
        ultima = len(self.righe)
        inizio = self.area.XYToPosition(0, ultima)
        self.area.Replace(inizio, inizio + self.area.GetLineLength(ultima), "\n".join([*chiuse, visibile]))
        self.righe.extend(chiuse)
        tolte = self._taglia_il_registro()
        if tolte:
            self.area.Remove(0, self.area.XYToPosition(0, tolte))
            riga -= tolte
        if sul_fondo:
            self._al_cursore()
        else:
            self._vai(max(0, riga), colonna)

    # Il cruscotto.

    def _cambia_forma(self, fornitore):
        """Lo strato consegna chi da' i dati del cruscotto, o None a fine
        partita."""
        if fornitore is None:
            if self.fornitore is None:
                return
            self.fornitore = None
            self.orologio.Stop()
            self.mostrate = []
            self.area.ChangeValue("\n".join([*self.righe, self.terminale.visibile()]))
            self._al_cursore()
            return
        nuova = self.fornitore is None
        self.fornitore = fornitore
        if nuova:
            self.messaggi = []
            self.mostrate = []
            self.orologio.Start(1000)
        self._ridisegna()

    def _ridisegna(self):
        """Riscrive solo le righe cambiate e rimette il cursore: sulla stessa
        riga della stessa sezione, alla stessa colonna; se era nel prompt e il
        prompt e' cambiato, al cursore del nucleo."""
        if not self or self.fornitore is None:
            return
        try:
            dati = self.fornitore()
            nuove = cruscotto.righe(dati, self.messaggi)
        # Lo stato appartiene al nucleo, che intanto puo' cambiarlo: si
        # riprova al prossimo secondo.
        except Exception:  # noqa: BLE001
            return
        nuove.append(("prompt", self.terminale.visibile()))
        if nuove == self.mostrate:
            return
        if self.mostrate:
            numero, colonna = self._riga_e_colonna()
            sezione = self.mostrate[numero][0]
            nella_sezione = sum(1 for s, _t in self.mostrate[:numero] if s == sezione)
            prompt_cambiato = self.mostrate[-1] != nuove[-1]
        else:
            numero, colonna, sezione, nella_sezione, prompt_cambiato = 0, 0, "prompt", 0, True
        if len(nuove) == len(self.mostrate) and all(a[0] == b[0] for a, b in zip(nuove, self.mostrate, strict=True)):
            # Stesse righe: si sostituiscono solo quelle cambiate, dal fondo.
            for indice in range(len(nuove) - 1, -1, -1):
                if nuove[indice][1] != self.mostrate[indice][1]:
                    inizio = self.area.XYToPosition(0, indice)
                    self.area.Replace(inizio, inizio + self.area.GetLineLength(indice), nuove[indice][1])
        else:
            self.area.ChangeValue("\n".join(testo for _sezione, testo in nuove))
        self.mostrate = nuove
        if sezione == "prompt":
            self._vai(len(nuove) - 1, self.terminale.colonna if prompt_cambiato else colonna)
        else:
            righe_della_sezione = [i for i, (s, _t) in enumerate(nuove) if s == sezione]
            if righe_della_sezione:
                self._vai(righe_della_sezione[min(nella_sezione, len(righe_della_sezione) - 1)], colonna)
            else:
                self._al_cursore()

    def _di(self, righe, dal_tasto):
        """Gli annunci, secondo le impostazioni: dal_tasto e' vero per la
        risposta a un tasto. Solo il primo puo' interrompere, gli altri lo
        seguono."""
        if not self.annunci["attivi"]:
            return
        interrompi = annunci.interrompe(self.annunci, dal_tasto)
        for numero, riga in enumerate(righe):
            self.sintesi.dici(riga, self.annunci["uscita"], self.annunci["destinazione"], interrompi=interrompi and numero == 0)

    # Le impostazioni.

    def impostazioni(self):
        """La finestra delle impostazioni, per ora quelle degli annunci. Il
        nucleo intanto continua: i tasti vanno alla finestra, e il testo che
        arriva si mostra e si annuncia come sempre."""
        voci = [(voce, annunci.riga(voce, self.annunci)) for voce in annunci.VOCI]
        with dialoghi.FinestraImpostazioni(self, voci, self._cambia_impostazione) as dialogo:
            dialogo.ShowModal()
        self.area.SetFocus()

    def _cambia_impostazione(self, voce, dialogo):
        scelte = annunci.SCELTE[voce]
        nomi = [annunci.nome_della_scelta(voce, scelta) for scelta in scelte]
        indice = self.scegli(dialogo, annunci.etichetta(voce), nomi, scelte.index(self.annunci[voce]))
        if indice is None:
            return
        self.annunci = annunci.normalizza({**self.annunci, voce: scelte[indice]})
        annunci.salva(self.annunci)
        dialogo.aggiorna(voce, annunci.riga(voce, self.annunci))

    def scegli(self, genitore, titolo, voci, scelta):
        """La scelta da una lista; le prove la sostituiscono."""
        return dialoghi.scegli(genitore, titolo, voci, scelta)

    # Il nucleo.

    def avvia_il_nucleo(self, corpo):
        def filo():
            try:
                corpo()
            except (KeyboardInterrupt, SystemExit):
                pass
            except Exception:  # noqa: BLE001 - l'errore va letto nell'area, poi si chiude
                print(traceback.format_exc())
            wx.CallAfter(self._nucleo_finito)

        self.nucleo = threading.Thread(target=filo, name="nucleo di Orologic", daemon=True)
        self.nucleo.start()

    def _nucleo_finito(self):
        if self:
            self._applica()
            if self.chiudi_alla_fine:
                self.Destroy()

    def _chiudi(self, evento):
        """Alt+F4: il nucleo riceve l'interruzione, come Ctrl+C nel
        terminale, e ha qualche secondo per chiudersi da solo."""
        if self.nucleo is None or not self.nucleo.is_alive():
            evento.Skip()
            return
        if self.chiudendo:
            return
        self.chiudendo = True
        self.faccia.chiudi()
        inizio = time.monotonic()

        def aspetta():
            if not self:
                return
            if self.nucleo.is_alive() and time.monotonic() - inizio < ATTESA_DELLA_CHIUSURA:
                wx.CallLater(100, aspetta)
                return
            if self.nucleo.is_alive():
                # Il nucleo e' fermo dove non legge tasti, per esempio in
                # rete: si chiude il motore e si esce comunque.
                from . import engine

                engine.CloseEngine()
                os._exit(0)
            self.Destroy()

        wx.CallLater(100, aspetta)


_SALVATI = {}


def prepara():
    """Crea la faccia e la finestra e collega il nucleo alla finestra: lo
    strato, la sorgente dei tasti di key, stdout, stdin e getpass. Serve una
    wx.App gia' nata. ripristina rimette tutto com'era."""
    faccia = FacciaFinestra()
    finestra = Finestra(faccia)
    _SALVATI.update(
        faccia=strato.imposta_faccia(faccia),
        sorgente=sorgente_dei_tasti(faccia.tasto_per_key),
        stdout=sys.stdout,
        stdin=sys.stdin,
        getpass=getpass.getpass,
    )
    sys.stdout = UscitaFinestra(faccia)
    sys.stdin = IngressoFinestra(faccia)

    def password(prompt="Password: ", stream=None):
        sys.stdout.write(prompt)
        return faccia.leggi_riga(eco=False)

    getpass.getpass = password
    return finestra


def ripristina():
    """Scollega il nucleo dalla finestra, come prima di prepara."""
    if not _SALVATI:
        return
    strato.imposta_faccia(_SALVATI["faccia"])
    sorgente_dei_tasti(_SALVATI["sorgente"])
    sys.stdout = _SALVATI["stdout"]
    sys.stdin = _SALVATI["stdin"]
    getpass.getpass = _SALVATI["getpass"]
    _SALVATI.clear()


def avvia(corpo):
    """Apre la finestra e ci fa girare corpo, il programma di sempre, in un
    filo suo. Torna quando la finestra si chiude."""
    app = wx.App()
    finestra = prepara()
    finestra.Show()
    finestra.avvia_il_nucleo(corpo)
    app.MainLoop()
    ripristina()
