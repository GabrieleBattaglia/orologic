# Orologic: la finestra della scacchiera interattiva.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra della scacchiera interattiva (Piano della GUI.txt, specifiche
di Gabriele del 21 novembre 2026): la apre lo spazio su un prompt di gioco
ancora vuoto, la chiude Esc. La logica sta in scacchiera.py; qui i tasti, gli
annunci e i suoni.

Il nucleo non si tocca: la mossa la scrive la finestra nel prompt, come se la
si digitasse, e cosi' i comandi, da .1 a .5, il trattino con la casa per Tab,
la virgola coi pezzi, il meno e il piu' per tutti i pezzi di un colore, il
commento; il nucleo risponde come sempre, e la finestra principale lo
annuncia. La posizione arriva dal cruscotto, a ogni giro dell'orologio della
finestra.

Qui gli annunci sono sempre attivi e vanno solo alla sintesi, con la
priorita' su NVDA, che tiene il braille: partono poco dopo il tasto,
interrompendo quello che NVDA dice del cursore. Le domande del nucleo che non
sono il prompt delle mosse, come quelle dei comandi del menu, chiudono la
scacchiera; quando il nucleo torna al prompt delle mosse, la finestra
principale la riapre.
"""

import chess
import wx
from GBUtils import Acusticator
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto, config, localizzazione, plancia, storage
from .config import _
from .scacchiera import (
    DESTRA,
    GIU,
    GIU_DESTRA,
    GIU_SINISTRA,
    SINISTRA,
    SU,
    SU_DESTRA,
    SU_SINISTRA,
    Scacchiera,
    nome_pezzo,
)

# I millisecondi fra il tasto e l'annuncio: NVDA dice prima quello che vede
# sotto il cursore, e l'annuncio lo interrompe.
RITARDO_DELL_ANNUNCIO = 100
# Quanto un tasto che fa coppia aspetta il secondo: una lettera da a ad h il
# numero della casa, l'1 e lo 0 l'altra cifra del risultato. Si sceglie nelle
# impostazioni, in millisecondi (Gabriele, collaudo della scacchiera).
CHIAVE_ATTESA = "scacchiera_attesa_ms"
ATTESA_PREDEFINITA = 700
ATTESA_MINIMA = 200
ATTESA_MASSIMA = 3000
# I risultati rapidi, dove la modalita' li ha, come nell'arbitraggio: le due
# cifre, o l'asterisco, e il comando che li assegna.
RISULTATI = {"10": ".1-0", "01": ".0-1", "12": ".1/2", "*": ".*"}
# Ogni quanto si rilegge la posizione dal cruscotto.
GIRO_DELLA_POSIZIONE = 150
# Il codice con cui la scacchiera si chiude per una domanda del nucleo: la
# finestra principale la riaprira'.
CHIUSA_PER_UNA_DOMANDA = wx.ID_HIGHEST + 71
PROMOZIONI = (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)

# I suoni della scacchiera, un preset per evento, dalla collezione di GBUtils,
# scelti da Gabriele all'ascolto alla cieca del 21 novembre 2026,
# strumenti/ascolto_scacchiera.py: sollevare e posare la coppia votata 5,
# rimettere la meta' che posa della coppia votata 4, subito sotto; al bordo
# uno dei due votati 5, e per passare dall'altra parte, uno per lato, gli
# altri del gruppo del bordo, in ordine di voto. I suoni del no, uno per
# evento, dalla seconda parte dell'ascolto.
SUONI = {
    "apri": "due_ante_che_si_aprono",
    "solleva": "casella_ritirati_spuntata",
    "posa": "casella_ritirati_tolta",
    "rimetti": "filtro_comune",
    "bordo": "filtro_provincia",
    "giro_giu": "filtro_classe_peggiore",
    "giro_destra": "filtro_tratto_indifferente",
    "giro_sinistra": "filtro_posto_attuale",
    "giro_su": "filtro_visus",
    "mossa_non_vale": "casella_in_vendita_tolta",
    "casa_vuota": "casella_del_computer_tolta",
    "niente_in_mano": "casella_senza_prelazione_tolta",
    "comando_assente": "filtro_stipendio_massimo",
    "da_guardare": "orecchio_che_cerca",
    "nessuna_mossa": "filtro_eta_minima",
    "risultato": "casella_liberi_spuntata",
}
GIRI = {SU: "giro_su", GIU: "giro_giu", SINISTRA: "giro_sinistra", DESTRA: "giro_destra"}
# Le azioni che fanno suonare ogni evento, per suoni_della_scacchiera.txt,
# l'elenco che Gabriele usa con Acu_Maker: lo scrive strumenti/elenco_suoni.py.
AZIONI = {
    "apri": "La scacchiera interattiva si apre, con lo spazio al prompt delle mosse a riga vuota",
    "solleva": "Lo spazio solleva il pezzo della casa, o, con un pezzo già in mano, rimette quello a posto e solleva questo",
    "posa": "Invio posa il pezzo sollevato sulla casa scelta, e la mossa va a Orologic",
    "rimetti": "Lo spazio sulla casa del pezzo sollevato lo rimette giù, senza muovere",
    "bordo": "Una freccia al bordo della scacchiera: il cursore si ferma",
    "giro_su": "Alt e freccia su, oltre il bordo di sopra: il cursore passa in fondo",
    "giro_giu": "Alt e freccia giù, oltre il bordo di sotto: il cursore passa in cima",
    "giro_sinistra": "Alt e freccia sinistra, oltre il bordo sinistro: il cursore passa a destra",
    "giro_destra": "Alt e freccia destra, oltre il bordo destro: il cursore passa a sinistra",
    "mossa_non_vale": "Invio con una mossa che non vale, o una promozione impossibile: si dice perché",
    "casa_vuota": "Lo spazio su una casa vuota, senza niente da sollevare",
    "niente_in_mano": "Invio senza un pezzo in mano",
    "comando_assente": "Un tasto per un comando che la modalità non ha: da F1 a F5 senza orologi, C senza commenti, Backspace senza comandi",
    "da_guardare": "Spazio o Invio nella partita osservata su Lichess, dove la scacchiera è solo da guardare",
    "nessuna_mossa": "u quando non c'è ancora nessuna mossa giocata",
    "risultato": "1 e 0, 0 e 1, 1 e 2, o l'asterisco, dove si assegna il risultato: si apre la conferma",
}


def suona(evento):
    """I suoni della scacchiera; le prove li sostituiscono."""
    Acusticator.play(SUONI[evento], volume=config.VOLUME)


def attesa_dei_comandi():
    """I millisecondi che un tasto aspetta il secondo, dalle impostazioni."""
    try:
        valore = int(storage.LoadDB().get(CHIAVE_ATTESA, ATTESA_PREDEFINITA))
    except (TypeError, ValueError):
        valore = ATTESA_PREDEFINITA
    return min(max(valore, ATTESA_MINIMA), ATTESA_MASSIMA)


def domanda_del_risultato(codice):
    return {
        "10": _("Vince il Bianco, 1-0: assegno il risultato?"),
        "01": _("Vince il Nero, 0-1: assegno il risultato?"),
        "12": _("Patta, 1/2: assegno il risultato?"),
        "*": _("Risultato non specificato, *: lo assegno?"),
    }[codice]


class ConfermaDelRisultato(wx.Dialog):
    """La conferma del risultato: Invio lo assegna, Esc continua la partita.
    La domanda e' anche il titolo, che NVDA legge all'apertura."""

    def __init__(self, genitore, domanda):
        super().__init__(genitore, title=domanda, style=STILE_ADATTABILE)
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(pannello, label=domanda), 0, wx.ALL, 5)
        pulsanti = wx.BoxSizer(wx.HORIZONTAL)
        self.assegna = wx.Button(pannello, wx.ID_YES, _("Assegna"))
        continua = wx.Button(pannello, wx.ID_NO, _("Continua la partita"))
        pulsanti.Add(self.assegna, 0, wx.ALL, 5)
        pulsanti.Add(continua, 0, wx.ALL, 5)
        sizer.Add(pulsanti, 0, wx.ALIGN_RIGHT)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        adatta_finestra(self, pannello, (480, 200))
        self.Maximize()
        self.SetAffirmativeId(wx.ID_YES)
        self.SetEscapeId(wx.ID_NO)
        self.assegna.SetDefault()
        self.Bind(wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_YES), self.assegna)
        self.Bind(wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_NO), continua)
        self.assegna.SetFocus()


def chiedi_il_risultato(genitore, domanda):
    """Vero se il risultato va assegnato; le prove la sostituiscono."""
    with ConfermaDelRisultato(genitore, domanda) as dialogo:
        return dialogo.ShowModal() == wx.ID_YES


def _e_nero(colore):
    if isinstance(colore, str):
        return colore == "black"
    return colore is not None and colore == chess.BLACK


def chiavi_dei_comandi(comandi):
    """Le chiavi dei comandi della modalita', dal dizionario o dalle coppie,
    con le forme separate: .s oppure .b da' .s e .b."""
    if not comandi:
        return set()
    chiavi = comandi if isinstance(comandi, dict) else [chiave for chiave, _riga in comandi]
    forme = set()
    for chiave in chiavi:
        testo = str(chiave).replace(" oppure ", " ").replace(" / ", " ")
        forme.update(testo.split())
    return forme


def righe_d_aiuto():
    """L'aiuto dei tasti della scacchiera, una riga per tasto."""
    return [
        _("Frecce: una casa nelle quattro direzioni; al bordo si fermano."),
        _("Alt con le frecce: oltre il bordo, dall'altra parte."),
        _("Maiuscolo con sinistra e destra: le diagonali che salgono; Ctrl con sinistra e destra: quelle che scendono."),
        _("Spazio: solleva il pezzo; sulla sua casa lo posa, su un'altra piena prende quello."),
        _("Invio: posa il pezzo sollevato, se la mossa vale."),
        _("Ctrl con spazio: il pezzo in mano."),
        _("Da a ad h, poi da 1 a 8: salta a quella casa."),
        _("Da 1 a 8: la traversa, nella colonna di adesso."),
        _("1 e 0, 0 e 1, 1 e 2, asterisco: dove si assegna il risultato, 1-0, 0-1, patta o non specificato, con la conferma."),
        _("9: gira la scacchiera."),
        _("R N B Q K P, e in minuscolo: dove sono quei pezzi, bianchi e neri."),
        _("W: tutti i pezzi bianchi; w: tutti i neri."),
        _("Tab: la casa, coi pezzi che la difendono e la attaccano."),
        _("l: l'ultima mossa; L: le ultime due; u: alla casa d'arrivo dell'ultima mossa."),
        _("m: le mosse possibili del pezzo sollevato, o di quello sulla casa."),
        _("Da F1 a F5: gli orologi, come da .1 a .5."),
        _("C: un commento alla mossa."),
        _("Backspace: la pausa e il menu dei comandi; nel menu, Backspace fa ripartire il tempo."),
        _("?: questo aiuto. Esc chiude la scacchiera."),
    ]


class Aiuto(wx.Dialog):
    """L'aiuto dei tasti, in un testo navigabile; Esc lo chiude."""

    def __init__(self, genitore):
        super().__init__(genitore, title=_("Aiuto della scacchiera"), style=STILE_ADATTABILE)
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.testo = wx.TextCtrl(pannello, value="\n".join(righe_d_aiuto()), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.testo.SetName(_("Aiuto della scacchiera"))
        sizer.Add(self.testo, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.Button(pannello, wx.ID_CANCEL, _("Chiudi")), 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        adatta_finestra(self, pannello, (560, 420))
        self.Maximize()
        self.testo.SetInsertionPoint(0)
        self.testo.SetFocus()


class MenuDellaPartita(wx.Dialog):
    """Il menu dei comandi della partita, dalla scacchiera con Backspace: un
    elenco dei comandi della plancia. Invio ne sceglie uno, o apre i suoi
    valori; Backspace fa ripartire il tempo; Esc chiude. scelto e' il nodo
    scelto, e ripresa vero se si e' chiesto di far ripartire il tempo."""

    def __init__(self, genitore, nodi):
        super().__init__(genitore, title=_("Comandi della partita"), style=STILE_ADATTABILE)
        self.nodi = list(nodi)
        self.scelto = None
        self.ripresa = False
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.elenco = wx.ListBox(pannello, choices=[nodo.etichetta for nodo in self.nodi], style=wx.LB_SINGLE)
        self.elenco.SetName(_("Comandi della partita"))
        if self.nodi:
            self.elenco.SetSelection(0)
        sizer.Add(self.elenco, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.Button(pannello, wx.ID_CANCEL, _("Chiudi")), 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        adatta_finestra(self, pannello, (560, 420))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.elenco.SetFocus()

    def _tasto(self, evento):
        codice = evento.GetKeyCode()
        if codice == wx.WXK_BACK and not evento.HasAnyModifiers():
            self.ripresa = True
            self.EndModal(wx.ID_OK)
            return
        if codice in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not evento.HasAnyModifiers():
            indice = self.elenco.GetSelection()
            if 0 <= indice < len(self.nodi):
                nodo = self.nodi[indice]
                if nodo.figli:
                    with MenuDellaPartita(self, nodo.figli) as valori:
                        if valori.ShowModal() != wx.ID_OK:
                            return
                        if valori.ripresa:
                            self.ripresa = True
                            self.EndModal(wx.ID_OK)
                            return
                        if valori.scelto is None:
                            return
                        nodo = valori.scelto
                self.scelto = nodo
                self.EndModal(wx.ID_OK)
            return
        evento.Skip()


class FinestraScacchiera(wx.Dialog):
    """La scacchiera interattiva sopra la finestra principale, finestra, che
    da' il cruscotto, i comandi della modalita', la faccia per scrivere nel
    prompt, la sintesi e le domande."""

    def __init__(self, finestra):
        super().__init__(finestra, title=_("Scacchiera"), style=STILE_ADATTABILE)
        self.finestra = finestra
        dati = self._dati() or {}
        board = dati.get("board") or chess.Board()
        self.scacchiera = Scacchiera(board, dal_nero=_e_nero(dati.get("mio")))
        self._vista = self._impronta(board)
        self._annuncio = None
        self._lettera = None
        self._attesa_della_lettera = None
        self.attesa_dei_comandi = attesa_dei_comandi()
        # Vero quando si chiude: da li' non scrive piu' nel prompt, perche' il
        # nucleo puo' gia' fare un'altra domanda.
        self.chiusa = False
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.area = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP)
        self.area.SetName(_("Scacchiera"))
        sizer.Add(self.area, 1, wx.EXPAND | wx.ALL, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        adatta_finestra(self, pannello, (560, 420))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.area.Bind(wx.EVT_CHAR, self._carattere)
        self.orologio = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _evento: self._controlla(), self.orologio)
        self.orologio.Start(GIRO_DELLA_POSIZIONE)
        self.disegna()
        self.area.SetFocus()
        suona("apri")
        self.annuncia(self.scacchiera.descrivi())

    # La posizione e il testo.

    def _dati(self):
        fornitore = self.finestra.fornitore
        if fornitore is None:
            return None
        try:
            return fornitore()
        # Lo stato appartiene al nucleo, che intanto puo' cambiarlo.
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _impronta(board):
        return board.fen(), len(board.move_stack)

    def _controlla(self):
        """A ogni giro: la posizione nuova, se il nucleo l'ha cambiata; a
        partita finita la scacchiera si chiude."""
        if not self:
            return
        if self.finestra.fornitore is None:
            self.chiudi()
            return
        dati = self._dati()
        board = (dati or {}).get("board")
        if board is None or self._impronta(board) == self._vista:
            return
        self._vista = self._impronta(board)
        self.scacchiera.aggiorna(board)
        self.disegna()

    def chiudi(self):
        """Chiude la scacchiera: con Esc, a partita finita, o per una domanda
        del nucleo."""
        self.chiusa = True
        self._ferma()
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)

    def _ferma(self):
        """Ferma l'orologio e le attese, prima che la finestra se ne vada."""
        self.orologio.Stop()
        self._chiudi_la_lettera()
        if self._annuncio is not None:
            self._annuncio.Stop()
            self._annuncio = None

    def Destroy(self):
        self._ferma()
        return super().Destroy()

    def disegna(self):
        """Le otto traverse nell'area, col cursore sul segno della casa
        scelta; il testo si riscrive solo se cambia, perche' NVDA non lo
        rilegga a ogni passo."""
        testo = "\n".join(self.scacchiera.righe())
        if self.area.GetValue() != testo:
            self.area.ChangeValue(testo)
        riga, colonna = self.scacchiera.posto_del_cursore()
        self.area.SetInsertionPoint(self.area.XYToPosition(colonna, riga))

    # Gli annunci.

    def annuncia(self, testo):
        """L'annuncio parte poco dopo il tasto e interrompe quello che NVDA
        sta dicendo del cursore; uno nuovo prende il posto di quello in attesa."""
        if self._annuncio is not None:
            self._annuncio.Stop()
        self._annuncio = wx.CallLater(RITARDO_DELL_ANNUNCIO, self._annuncia_ora, testo)

    def _annuncia_ora(self, testo):
        self._annuncio = None
        if self:
            self.finestra.alla_sintesi(testo, interrompi=True)

    # Il nucleo.

    def scrivi(self, testo):
        """Scrive nel prompt del nucleo, come digitato, e preme Invio. Con la
        scacchiera di .s ferma, il nucleo aspetta un tasto per tornare al
        prompt: lo spazio, che non entra nella riga."""
        if self.chiusa:
            return
        if (self._dati() or {}).get("vista_ferma"):
            self.finestra.premi_nel_prompt(" ")
        for carattere in testo:
            self.finestra.premi_nel_prompt(carattere)
        self.finestra.premi_nel_prompt("\r")

    def da_guardare(self):
        """Vero dove la scacchiera e' solo da guardare, come nella partita
        osservata su Lichess: lo dice, con il suono del no."""
        if not (self._dati() or {}).get("da_guardare"):
            return False
        suona("da_guardare")
        self.annuncia(_("Qui la scacchiera e' solo da guardare."))
        return True

    def _ha(self, chiave):
        return chiave in chiavi_dei_comandi(self.finestra.comandi)

    def comando(self, testo, chiave=None):
        """Un comando della modalita', se la modalita' ce l'ha."""
        if chiave is not None and not self._ha(chiave):
            suona("comando_assente")
            return
        self.scrivi(testo)

    # I tasti.

    def _tasto(self, evento):
        codice = evento.GetKeyCode()
        modificatori = evento.GetModifiers()
        frecce = {wx.WXK_UP: SU, wx.WXK_DOWN: GIU, wx.WXK_LEFT: SINISTRA, wx.WXK_RIGHT: DESTRA}
        if codice == wx.WXK_ESCAPE and modificatori == wx.MOD_NONE:
            self.chiudi()
            return
        if codice in frecce:
            self._chiudi_la_lettera()
            self._freccia(codice, frecce[codice], modificatori)
            return
        if codice == wx.WXK_SPACE and modificatori in (wx.MOD_NONE, wx.MOD_CONTROL):
            self._chiudi_la_lettera()
            if modificatori == wx.MOD_CONTROL:
                self.annuncia(self.scacchiera.in_mano())
            else:
                self.spazio()
            return
        if codice in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and modificatori == wx.MOD_NONE:
            self._chiudi_la_lettera()
            self.invio()
            return
        if codice == wx.WXK_BACK and modificatori == wx.MOD_NONE:
            self._chiudi_la_lettera()
            self.menu()
            return
        if codice == wx.WXK_TAB and modificatori == wx.MOD_NONE:
            self._chiudi_la_lettera()
            self.scrivi("-" + chess.square_name(self.scacchiera.cursore))
            return
        if wx.WXK_F1 <= codice <= wx.WXK_F5 and modificatori == wx.MOD_NONE:
            self._chiudi_la_lettera()
            numero = codice - wx.WXK_F1 + 1
            self.comando(f".{numero}", f".{numero}")
            return
        evento.Skip()

    def _freccia(self, codice, passo, modificatori):
        if modificatori == wx.MOD_SHIFT and codice in (wx.WXK_LEFT, wx.WXK_RIGHT):
            passo = SU_SINISTRA if codice == wx.WXK_LEFT else SU_DESTRA
        elif modificatori == wx.MOD_CONTROL and codice in (wx.WXK_LEFT, wx.WXK_RIGHT):
            passo = GIU_SINISTRA if codice == wx.WXK_LEFT else GIU_DESTRA
        elif modificatori not in (wx.MOD_NONE, wx.MOD_ALT):
            return
        esito = self.scacchiera.sposta(passo, avvolgi=modificatori == wx.MOD_ALT)
        if esito == "fermo":
            suona("bordo")
            return
        if esito == "giro":
            # Dall'altra parte: il suono del lato oltrepassato.
            suona(GIRI[passo])
        self._mostra_la_casa()

    def _mostra_la_casa(self):
        self.disegna()
        self.annuncia(self.scacchiera.descrivi())

    def _carattere(self, evento):
        codice = evento.GetUnicodeKey()
        if codice == wx.WXK_NONE or codice < 32 or evento.AltDown() or evento.ControlDown():
            evento.Skip()
            return
        carattere = chr(codice)
        if self._lettera is not None:
            lettera = self._lettera
            self._chiudi_la_lettera()
            if self._coppia(lettera, carattere):
                return
            self._dopo_la_lettera(lettera)
        # Le lettere aspettano il numero della casa; l'1 e lo 0, dove si
        # assegna il risultato, l'altra cifra.
        if carattere in "abcdefgh" or (carattere in "10" and self.risultati()):
            self._lettera = carattere
            self._attesa_della_lettera = wx.CallLater(self.attesa_dei_comandi, self._lettera_scaduta)
            return
        if carattere == "*":
            self.risultato("*")
            return
        self._carattere_della_scacchiera(carattere)

    def _coppia(self, primo, secondo):
        """Il secondo tasto di una coppia: la casa, o un risultato. Vero se
        la coppia vale."""
        if primo in "abcdefgh" and secondo in "12345678":
            self.scacchiera.vai(primo, int(secondo))
            self._mostra_la_casa()
            return True
        if primo + secondo in RISULTATI:
            self.risultato(primo + secondo)
            return True
        return False

    def _chiudi_la_lettera(self):
        if self._attesa_della_lettera is not None:
            self._attesa_della_lettera.Stop()
        self._attesa_della_lettera = None
        self._lettera = None

    def _lettera_scaduta(self):
        lettera = self._lettera
        self._attesa_della_lettera = None
        self._lettera = None
        if self and lettera:
            self._dopo_la_lettera(lettera)

    def _dopo_la_lettera(self, lettera):
        """Un tasto rimasto senza il secondo fa quello che fa da solo: la b
        dice gli alfieri neri, l'1 va alla prima traversa; lo 0 e le altre
        lettere non hanno altro."""
        if lettera == "b":
            self.scrivi(",b")
        elif lettera == "1":
            self._carattere_della_scacchiera("1")

    def _carattere_della_scacchiera(self, carattere):
        if carattere in "12345678":
            self.scacchiera.vai(traversa=int(carattere))
            self._mostra_la_casa()
        elif carattere == "9":
            self.scacchiera.gira()
            self.disegna()
            self.annuncia(_("Dal Nero") if self.scacchiera.dal_nero else _("Dal Bianco"))
        elif carattere in "RNBQKPrnbqkp":
            self.scrivi("," + carattere)
        elif carattere == "W":
            self.scrivi("-")
        elif carattere == "w":
            self.scrivi("+")
        elif carattere in "lL":
            self.annuncia(self.scacchiera.ultime_mosse(1 if carattere == "l" else 2))
        elif carattere == "u":
            casa = self.scacchiera.casa_dell_ultima_mossa()
            if casa is None:
                suona("nessuna_mossa")
                self.annuncia(self.scacchiera.ultime_mosse(1))
                return
            self.scacchiera.cursore = casa
            self._mostra_la_casa()
        elif carattere == "m":
            self.annuncia(self.scacchiera.mosse_possibili())
        elif carattere == "C":
            self.commento()
        elif carattere == "?":
            with Aiuto(self) as aiuto:
                aiuto.ShowModal()
            self.area.SetFocus()

    # I pezzi.

    def spazio(self):
        if self.da_guardare():
            return
        esito = self.scacchiera.spazio()
        if esito == "vuota":
            suona("casa_vuota")
            self.annuncia(self.scacchiera.descrivi())
            return
        if esito == "posato":
            suona("rimetti")
            self.annuncia(_("Posato: {pezzo}").format(pezzo=nome_pezzo(self.scacchiera.board.piece_at(self.scacchiera.cursore))))
        else:
            suona("solleva")
            self.annuncia(_("Sollevato: {pezzo}").format(pezzo=nome_pezzo(self.scacchiera.board.piece_at(self.scacchiera.sollevato))))
        self.disegna()

    def invio(self):
        """Posa il pezzo sollevato sulla casa scelta: la mossa va al nucleo, o
        si dice perche' non vale. La promozione chiede il pezzo."""
        if self.da_guardare():
            return
        mossa = self.scacchiera.mossa()
        if mossa is None:
            suona("niente_in_mano")
            self.annuncia(self.scacchiera.in_mano())
            return
        if self.scacchiera.promozione():
            motivo = self.scacchiera.giudica(self.scacchiera.mossa(chess.QUEEN))
            if motivo:
                suona("mossa_non_vale")
                self.annuncia(motivo)
                return
            nomi = [localizzazione.nome_pezzo(pezzo).capitalize() for pezzo in PROMOZIONI]
            indice = self.finestra.scegli(self, _("Promozione"), nomi, 0)
            self.area.SetFocus()
            if indice is None:
                return
            mossa = self.scacchiera.mossa(PROMOZIONI[indice])
        motivo = self.scacchiera.giudica(mossa)
        if motivo:
            suona("mossa_non_vale")
            self.annuncia(motivo)
            return
        san = self.scacchiera.san(mossa)
        self.scacchiera.sollevato = None
        suona("posa")
        self.scrivi(san)
        self.disegna()

    # Il risultato.

    def risultati(self):
        """Vero dove la modalita' assegna i risultati, come nell'arbitraggio."""
        return self._ha(RISULTATI["10"])

    def risultato(self, codice):
        """1 e 0, 0 e 1, 1 e 2, o l'asterisco: la conferma, e con Invio il
        risultato va al nucleo; con Esc la partita continua."""
        if not self.risultati():
            suona("comando_assente")
            return
        suona("risultato")
        if chiedi_il_risultato(self, domanda_del_risultato(codice)):
            self.scrivi(RISULTATI[codice])
        if self:
            self.area.SetFocus()

    # Il commento e il menu.

    def commento(self):
        if not self._ha(".c"):
            suona("comando_assente")
            return
        testo = self.finestra.chiedi_valore(self, _("Commento mossa"), _("Commento mossa"), "", "testo", 0, 500)
        self.area.SetFocus()
        if testo:
            self.scrivi(".c " + testo)

    def menu(self):
        """Backspace: la pausa, dove c'e', e il menu dei comandi della
        partita; un comando scelto va al nucleo, e la scacchiera torna. Nel
        menu Backspace fa ripartire il tempo."""
        if not self.finestra.comandi:
            suona("comando_assente")
            return
        dati = self._dati() or {}
        pausa = self._ha(".p") and not dati.get("senza_orologio")
        if pausa and not dati.get("pausa"):
            self.scrivi(".p")
        with MenuDellaPartita(self, plancia.comandi_della_partita(self.finestra.comandi)) as menu:
            esito = menu.ShowModal()
            scelto, ripresa = menu.scelto, menu.ripresa
        self.area.SetFocus()
        if esito != wx.ID_OK:
            return
        if ripresa:
            if pausa:
                self.scrivi(".p")
            return
        if scelto is None or not scelto.testo:
            return
        if scelto.invio:
            self.scrivi(scelto.testo)
            return
        # Un comando col seguito, come un valore: lo si chiede qui.
        valore = self.finestra.chiedi_valore(self, scelto.etichetta, scelto.etichetta, "", "testo", 0, 200)
        self.area.SetFocus()
        if valore:
            self.scrivi(scelto.testo + valore)
