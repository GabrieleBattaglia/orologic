# Orologic: l'editor della scacchiera di Easyfish nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'editor della scacchiera di Easyfish, il comando .be, come l'ha voluto
Gabriele il 22 novembre 2026: la scacchiera interattiva, coi suoi
spostamenti e i suoi salti, dove le lettere dei pezzi, R N B Q K P e le
minuscole, mettono quel pezzo sulla casa, e il Re vi si sposta; con Alt
davanti dicono dove sono quei pezzi, e Alt con W e w tutti i bianchi e
tutti i neri; lo spazio solleva un pezzo e Invio lo posa, senza le regole
del gioco; Canc svuota la casa, ma non quella di un Re.

Dopo la scacchiera, con Tab, i campi veri del resto della posizione: il
tratto, i quattro arrocchi, la casa dell'en passant e il numero della mossa;
poi Posizione iniziale, Svuota, che lascia i due Re, OK, che controlla la
posizione e dice cosa non va, e Annulla, che lascia la partita com'era.
"""

import chess
import wx

from .config import _
from .easyfish.interaction import errori_della_posizione
from .finestra_scacchiera import Aiuto, FinestraScacchiera, suona
from .scacchiera import nome_casa, nome_pezzo

COLONNE = "abcdefgh"


def righe_d_aiuto():
    """L'aiuto dei tasti dell'editor, una riga per tasto."""
    return [
        _("Frecce: una casa nelle quattro direzioni; al bordo si fermano."),
        _("Alt con le frecce: oltre il bordo, dall'altra parte."),
        _("Da a ad h, poi da 1 a 8: salta a quella casa."),
        _("Da 1 a 8: la traversa, nella colonna di adesso."),
        _("9: gira la scacchiera."),
        _("R N B Q K P, e in minuscolo: mette quel pezzo sulla casa, bianco o nero; il Re si sposta li'."),
        _("Alt con R N B Q K P, e in minuscolo: dove sono quei pezzi; Alt con W e w: tutti i bianchi e tutti i neri."),
        _("Spazio: solleva il pezzo; Invio lo posa sulla casa scelta, senza le regole del gioco."),
        _("Canc: svuota la casa, ma non quella di un Re."),
        _("Tab: il tratto, gli arrocchi, l'en passant, il numero della mossa e i pulsanti."),
        _("?: questo aiuto. Esc annulla."),
    ]


class _Ponte:
    """Quello che la scacchiera interattiva chiede alla finestra principale,
    per l'editor: la sintesi, le scelte e i valori; niente nucleo."""

    def __init__(self, finestra):
        self._finestra = finestra
        self.comandi = None
        self.fornitore = dict

    def alla_sintesi(self, testo, interrompi=True):
        self._finestra.alla_sintesi(testo, interrompi=interrompi)

    def scegli(self, genitore, titolo, voci, scelta):
        return self._finestra.scegli(genitore, titolo, voci, scelta)

    def chiedi_valore(self, genitore, titolo, domanda, valore, tipo="testo", minimo=0, massimo=256):
        return self._finestra.chiedi_valore(genitore, titolo, domanda, valore, tipo, minimo, massimo)

    def premi_nel_prompt(self, _tasto):
        """L'editor non scrive nel prompt."""


class EditorDellaScacchiera(FinestraScacchiera):
    """L'editor: finestra e' la finestra principale, per la sintesi e le
    domande; fen la posizione di partenza. fen, dopo OK, e' quella nuova."""

    def __init__(self, genitore, finestra, fen):
        self._iniziale = chess.Board(fen)
        self.fen = None
        super().__init__(_Ponte(finestra), genitore)
        self.SetTitle(_("Editor della scacchiera"))
        self.area.SetName(_("Editor della scacchiera"))
        pannello = self.area.GetParent()
        sizer = pannello.GetSizer()
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        griglia = wx.FlexGridSizer(cols=2, vgap=5, hgap=5)
        griglia.Add(wx.StaticText(pannello, label=_("Tratto")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.tratto = wx.Choice(pannello, choices=[_("Bianco"), _("Nero")])
        self.tratto.SetName(_("Tratto"))
        griglia.Add(self.tratto)
        sizer.Add(griglia, 0, wx.ALL, 5)
        self.arrocchi = {}
        for simbolo, etichetta in (("K", _("Arrocco corto del Bianco")), ("Q", _("Arrocco lungo del Bianco")),
                                   ("k", _("Arrocco corto del Nero")), ("q", _("Arrocco lungo del Nero"))):
            casella = wx.CheckBox(pannello, label=etichetta)
            self.arrocchi[simbolo] = casella
            sizer.Add(casella, 0, wx.LEFT | wx.RIGHT, 5)
        griglia = wx.FlexGridSizer(cols=2, vgap=5, hgap=5)
        griglia.Add(wx.StaticText(pannello, label=_("Casa dell'en passant")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.en_passant = wx.Choice(pannello)
        self.en_passant.SetName(_("Casa dell'en passant"))
        griglia.Add(self.en_passant)
        griglia.Add(wx.StaticText(pannello, label=_("Numero della mossa")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.numero = wx.SpinCtrl(pannello, min=1, max=999, initial=1)
        self.numero.SetName(_("Numero della mossa"))
        griglia.Add(self.numero)
        sizer.Add(griglia, 0, wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_iniziale = wx.Button(pannello, label=_("Posizione &iniziale"))
        self.pulsante_svuota = wx.Button(pannello, label=_("S&vuota"))
        ok = wx.Button(pannello, wx.ID_OK, _("OK"))
        annulla = wx.Button(pannello, wx.ID_CANCEL, _("Annulla"))
        for pulsante in (self.pulsante_iniziale, self.pulsante_svuota, ok):
            riga.Add(pulsante, 0, wx.RIGHT, 5)
        riga.Add(annulla, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        self.metti_il_resto(self._iniziale)
        self.tratto.Bind(wx.EVT_CHOICE, lambda _evento: self._case_dell_en_passant())
        self.pulsante_iniziale.Bind(wx.EVT_BUTTON, lambda _evento: self.da_capo(chess.Board()))
        self.pulsante_svuota.Bind(wx.EVT_BUTTON, lambda _evento: self.svuota())
        ok.Bind(wx.EVT_BUTTON, lambda _evento: self.conferma())
        annulla.Bind(wx.EVT_BUTTON, lambda _evento: self.chiudi())
        pannello.Layout()
        self.Layout()
        self.area.SetFocus()

    # La posizione.

    def _dati(self):
        board = self.scacchiera.board if hasattr(self, "scacchiera") else self._iniziale
        return {"board": board}

    def _controlla(self):
        """La posizione e' tutta qui: non c'e' un nucleo da rileggere."""

    def metti_il_resto(self, board):
        """Il tratto, gli arrocchi, l'en passant e il numero dalla posizione."""
        self.tratto.SetSelection(0 if board.turn == chess.WHITE else 1)
        arrocchi = board.castling_xfen()
        for simbolo, casella in self.arrocchi.items():
            casella.SetValue(simbolo in arrocchi)
        self._case_dell_en_passant(board.ep_square)
        self.numero.SetValue(board.fullmove_number)

    def _case_dell_en_passant(self, scelta=None):
        """Le case dell'en passant per chi ha il tratto: la sesta traversa se
        muove il Bianco, la terza se muove il Nero."""
        traversa = 6 if self.tratto.GetSelection() == 0 else 3
        self._case = [None, *(chess.parse_square(f"{colonna}{traversa}") for colonna in COLONNE)]
        self.en_passant.Set([_("Nessuna"), *(nome_casa(casa) for casa in self._case[1:])])
        self.en_passant.SetSelection(self._case.index(scelta) if scelta in self._case else 0)

    def posizione(self):
        """La posizione dei pezzi con il resto dei campi."""
        board = self.scacchiera.board.copy(stack=False)
        board.turn = chess.WHITE if self.tratto.GetSelection() == 0 else chess.BLACK
        arrocchi = "".join(simbolo for simbolo, casella in self.arrocchi.items() if casella.GetValue())
        board.set_castling_fen(arrocchi or "-")
        board.ep_square = self._case[max(self.en_passant.GetSelection(), 0)]
        board.fullmove_number = self.numero.GetValue()
        board.halfmove_clock = 0
        return board

    def da_capo(self, board):
        """Posizione iniziale, o Svuota: la scacchiera e i campi da capo."""
        self.scacchiera.board = board
        self.scacchiera.sollevato = None
        self.metti_il_resto(board)
        self.disegna()
        suona("da_capo")
        self.area.SetFocus()
        self.annuncia(_("Scacchiera reimpostata alla posizione iniziale standard.") if board.fen() == chess.STARTING_FEN
                      else _("Scacchiera svuotata. Re posizionati in case di partenza."))

    def svuota(self):
        board = chess.Board(None)
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        self.da_capo(board)

    def conferma(self):
        """OK: la posizione, se e' legale; altrimenti si dice cosa non va, e
        si resta."""
        board = self.posizione()
        errori = errori_della_posizione(board)
        if errori:
            suona("posizione_illegale")
            self.annuncia(" ".join([_("Posizione illegale:"), *errori]))
            return
        self.fen = board.fen()
        self.chiusa = True
        self._ferma()
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    # I tasti.

    def _tasto(self, evento):
        """Sulla scacchiera i suoi tasti, piu' Alt coi pezzi e Canc; Tab va
        ai campi. Negli altri controlli i tasti di sempre."""
        if evento.GetEventObject() is not self.area:
            evento.Skip()
            return
        codice = evento.GetKeyCode()
        modificatori = evento.GetModifiers()
        if codice == wx.WXK_TAB:
            evento.Skip()
            return
        if codice in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and modificatori == wx.MOD_NONE:
            self._chiudi_la_lettera()
            self.togli()
            return
        if modificatori in (wx.MOD_ALT, wx.MOD_ALT | wx.MOD_SHIFT) and ord("A") <= codice <= ord("Z"):
            lettera = chr(codice) if modificatori & wx.MOD_SHIFT else chr(codice).lower()
            if lettera in "RNBQKPrnbqkpWw":
                self._chiudi_la_lettera()
                self.di_qui({"W": "-", "w": "+"}.get(lettera, "," + lettera))
                return
            evento.Skip()
            return
        super()._tasto(evento)

    def contesto(self):
        return "editor"

    def chiedi(self, comando):
        self.di_qui(comando)

    def alt(self, _lettera):
        return False

    def _dopo_la_lettera(self, lettera):
        """La b da sola, passata l'attesa, mette l'Alfiere nero; l'1 va alla
        prima traversa."""
        if lettera == "b":
            self.metti("b")
        elif lettera == "1":
            self._carattere_della_scacchiera("1")

    def _carattere_della_scacchiera(self, carattere):
        if carattere in "RNBQKPrnbqkp":
            self.metti(carattere)
        elif carattere == "?":
            with Aiuto(self, righe_d_aiuto()) as aiuto:
                aiuto.ShowModal()
            self.area.SetFocus()
        elif carattere not in "WwC":
            super()._carattere_della_scacchiera(carattere)

    # I pezzi.

    def _re_sulla_casa(self, casa):
        pezzo = self.scacchiera.board.piece_at(casa)
        return pezzo is not None and pezzo.piece_type == chess.KING

    def _rifiuta_il_re(self):
        suona("re_da_spostare")
        self.annuncia(_("Li' c'e' un Re: spostalo prima."))

    def metti(self, simbolo):
        """Una lettera: quel pezzo sulla casa scelta; il Re di quel colore vi
        si sposta. La casa di un Re non si copre."""
        pezzo = chess.Piece.from_symbol(simbolo)
        board = self.scacchiera.board
        casa = self.scacchiera.cursore
        if pezzo.piece_type == chess.KING:
            if self._re_sulla_casa(casa) and board.piece_at(casa) != pezzo:
                self._rifiuta_il_re()
                return
            for vecchia in list(board.pieces(chess.KING, pezzo.color)):
                board.remove_piece_at(vecchia)
        elif self._re_sulla_casa(casa):
            self._rifiuta_il_re()
            return
        board.set_piece_at(casa, pezzo)
        if self.scacchiera.sollevato == casa:
            self.scacchiera.sollevato = None
        suona("metti")
        self._mostra_la_casa()

    def togli(self):
        """Canc: la casa si svuota, ma non quella di un Re."""
        casa = self.scacchiera.cursore
        if self.scacchiera.board.piece_at(casa) is None:
            suona("casa_vuota")
            self.annuncia(self.scacchiera.descrivi())
            return
        if self._re_sulla_casa(casa):
            self._rifiuta_il_re()
            return
        self.scacchiera.board.remove_piece_at(casa)
        if self.scacchiera.sollevato == casa:
            self.scacchiera.sollevato = None
        suona("togli")
        self._mostra_la_casa()

    def invio(self):
        """Invio: il pezzo sollevato sulla casa scelta, senza le regole del
        gioco; la casa di un altro Re non si copre."""
        partenza = self.scacchiera.sollevato
        if partenza is None:
            suona("niente_in_mano")
            self.annuncia(self.scacchiera.in_mano())
            return
        arrivo = self.scacchiera.cursore
        board = self.scacchiera.board
        pezzo = board.piece_at(partenza)
        if arrivo != partenza and self._re_sulla_casa(arrivo):
            self._rifiuta_il_re()
            return
        board.remove_piece_at(partenza)
        board.set_piece_at(arrivo, pezzo)
        self.scacchiera.sollevato = None
        suona("posa")
        self.disegna()
        self.annuncia(_("Posato: {pezzo}").format(pezzo=f"{nome_pezzo(pezzo)}, {nome_casa(arrivo)}"))


def modifica(genitore, finestra, fen):
    """L'editor sulla posizione fen: la posizione nuova, o None se si
    annulla; le prove lo sostituiscono."""
    with EditorDellaScacchiera(genitore, finestra, fen) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.fen

