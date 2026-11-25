# Orologic: la scacchiera interattiva, la logica.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La scacchiera interattiva della finestra (Piano della GUI.txt, specifiche
di Gabriele del 21 novembre 2026), senza wx: la posizione, il cursore, il
pezzo sollevato, il verso, il testo delle otto traverse, gli spostamenti e
i giudizi sulle mosse. La finestra, finestra_scacchiera.py, ci mette i tasti,
gli annunci e i suoni.

Il testo e' quello di Gabriele: per ogni traversa il numero, le otto case
fra barre verticali, e di nuovo il numero, 1| R | - | q | - | N | K | + | b |1;
i pezzi come in .s, maiuscole il Bianco e minuscole il Nero, trattino le
case chiare vuote e piu' le scure; il pezzo sollevato fra parentesi quadre,
e l'ultimo pezzo mosso, del giocatore o dell'avversario, fra tonde, come
(n) (Gabriele, 25 novembre 2026).

Gli spostamenti sono quelli di chi guarda: su verso il lato di la', destra
e sinistra come si vede; il verso si sceglie all'apertura, dal proprio
colore quando si gioca e dal Bianco quando si arbitra o si analizza, e il 9
lo gira.
"""

import chess

from . import board_utils, localizzazione
from .config import _

# Le coppie di spostamento delle frecce e delle diagonali, in colonne e righe
# di chi guarda: destra e' piu' uno, giu' e' piu' uno.
SU, GIU, SINISTRA, DESTRA = (0, -1), (0, 1), (-1, 0), (1, 0)
SU_SINISTRA, SU_DESTRA, GIU_SINISTRA, GIU_DESTRA = (-1, -1), (1, -1), (-1, 1), (1, 1)


def nome_casa(casa):
    """La casa coi nomi di Orologic, per esempio Empoli 4."""
    nome = chess.square_name(casa)
    return f"{localizzazione.colonna(nome[0])} {nome[1]}"


def nome_pezzo(pezzo):
    """Il pezzo col suo colore, per esempio Donna nera."""
    from .ui import extended_piece_description

    return extended_piece_description(pezzo)


class Scacchiera:
    """La scacchiera interattiva: board e' la posizione, di python-chess,
    dal_nero il verso. cursore e' la casa scelta, sollevato quella del pezzo
    in mano, o None."""

    def __init__(self, board, dal_nero=False):
        self.board = board.copy()
        self.dal_nero = dal_nero
        self.sollevato = None
        ultima = self.board.peek() if self.board.move_stack else None
        if ultima is not None:
            self.cursore = ultima.to_square
        else:
            # In basso al centro, dal lato di chi guarda.
            self.cursore = chess.E8 if dal_nero else chess.E1

    # La posizione.

    def aggiorna(self, board):
        """Una posizione nuova, dal nucleo: il cursore resta; il pezzo in
        mano cade se la sua casa non ha piu' lo stesso pezzo."""
        prima = self.board.piece_at(self.sollevato) if self.sollevato is not None else None
        self.board = board.copy()
        if self.sollevato is not None and self.board.piece_at(self.sollevato) != prima:
            self.sollevato = None

    def gira(self):
        self.dal_nero = not self.dal_nero

    # Il testo.

    def _in_vista(self, casa):
        """Colonna e riga di chi guarda, da 0 a 7, da sinistra e dall'alto."""
        colonna, traversa = chess.square_file(casa), chess.square_rank(casa)
        if self.dal_nero:
            return 7 - colonna, traversa
        return colonna, 7 - traversa

    def _dalla_vista(self, colonna, riga):
        if self.dal_nero:
            return chess.square(7 - colonna, riga)
        return chess.square(colonna, 7 - riga)

    def _cella(self, casa, ultima=None):
        """Il segno della casa: fra quadre il pezzo sollevato, fra tonde
        l'ultimo pezzo mosso, sulla casa d'arrivo dell'ultima mossa;
        sollevato, vincono le quadre."""
        pezzo = self.board.piece_at(casa)
        if pezzo is not None:
            segno = pezzo.symbol()
        else:
            # Come .s: trattino le case chiare, piu' le scure.
            segno = "+" if (chess.square_file(casa) + chess.square_rank(casa)) % 2 == 0 else "-"
        if casa == self.sollevato:
            return f"[{segno}]"
        if casa == ultima:
            return f"({segno})"
        return f" {segno} "

    def righe(self):
        """Le otto traverse come le vede chi guarda, dall'alto."""
        ultima = self.casa_dell_ultima_mossa()
        righe = []
        for riga in range(8):
            traversa = chess.square_rank(self._dalla_vista(0, riga)) + 1
            celle = [self._cella(self._dalla_vista(colonna, riga), ultima) for colonna in range(8)]
            righe.append(f"{traversa}|" + "|".join(celle) + f"|{traversa}")
        return righe

    def posto_del_cursore(self):
        """La riga e la colonna, nel testo, del segno della casa scelta: li'
        sta il cursore dell'area, che il display braille segue."""
        colonna, riga = self._in_vista(self.cursore)
        return riga, 2 + 4 * colonna + 1

    # Le parole.

    def descrivi(self, casa=None):
        """La casa e il suo pezzo: Empoli 4, Donna nera; Empoli 4, vuota."""
        casa = self.cursore if casa is None else casa
        pezzo = self.board.piece_at(casa)
        return _("{casa}, {pezzo}").format(casa=nome_casa(casa), pezzo=nome_pezzo(pezzo) if pezzo else _("vuota"))

    def in_mano(self):
        if self.sollevato is None:
            return _("Nessun pezzo in mano.")
        return _("In mano: {pezzo}, da {casa}.").format(pezzo=nome_pezzo(self.board.piece_at(self.sollevato)), casa=nome_casa(self.sollevato))

    def ultime_mosse(self, quante):
        """Le ultime mosse a parole, col loro numero: 12. Cavallo in Firenze 3."""
        if not self.board.move_stack:
            return _("Nessuna mossa ancora giocata.")
        copia = self.board.copy()
        mosse = []
        for _volta in range(min(quante, len(copia.move_stack))):
            mossa = copia.pop()
            numero = f"{copia.fullmove_number}." if copia.turn == chess.WHITE else f"{copia.fullmove_number}..."
            mosse.append(f"{numero} {board_utils.DescribeMove(mossa, copia)}")
        return "; ".join(reversed(mosse))

    def mosse_possibili(self, casa=None):
        """Le case dove puo' andare il pezzo sollevato, o quello della casa
        scelta; anche dell'avversario, che si studia."""
        casa = self.sollevato if self.sollevato is not None else (self.cursore if casa is None else casa)
        pezzo = self.board.piece_at(casa)
        if pezzo is None:
            return _("{casa}, vuota").format(casa=nome_casa(casa))
        prova = self.board.copy(stack=False)
        prova.turn = pezzo.color
        # In ordine di colonna e poi di traversa, come si leggono.
        case = sorted(
            {_arrivo_del_re(prova, mossa) for mossa in prova.legal_moves if mossa.from_square == casa},
            key=lambda arrivo: (chess.square_file(arrivo), chess.square_rank(arrivo)),
        )
        arrivi = [nome_casa(arrivo) for arrivo in case]
        if not arrivi:
            return _("{pezzo} in {casa} non ha mosse.").format(pezzo=nome_pezzo(pezzo), casa=nome_casa(casa))
        return _("{pezzo} in {casa}: {mosse}.").format(pezzo=nome_pezzo(pezzo), casa=nome_casa(casa), mosse=", ".join(arrivi))

    # Gli spostamenti.

    def sposta(self, passo, avvolgi=False):
        """Il cursore di un passo. Restituisce passo; al bordo fermo, e il
        cursore resta; con avvolgi, al bordo giro, e il cursore passa
        dall'altra parte."""
        colonna, riga = self._in_vista(self.cursore)
        colonna, riga = colonna + passo[0], riga + passo[1]
        esito = "passo"
        if not (0 <= colonna < 8 and 0 <= riga < 8):
            if not avvolgi:
                return "fermo"
            colonna, riga = colonna % 8, riga % 8
            esito = "giro"
        self.cursore = self._dalla_vista(colonna, riga)
        return esito

    def vai(self, colonna=None, traversa=None):
        """Alla colonna, una lettera, e alla traversa, un numero da 1 a 8; quella che manca resta."""
        nuova_colonna = "abcdefgh".index(colonna) if colonna else chess.square_file(self.cursore)
        nuova_traversa = traversa - 1 if traversa else chess.square_rank(self.cursore)
        self.cursore = chess.square(nuova_colonna, nuova_traversa)

    def casa_dell_ultima_mossa(self):
        return self.board.peek().to_square if self.board.move_stack else None

    # I pezzi.

    def spazio(self):
        """Lo spazio: solleva il pezzo della casa scelta, qualunque; con un
        pezzo gia' in mano, sulla sua casa lo posa, su un'altra piena lo
        rimette a posto e solleva quello. Restituisce sollevato, posato,
        scambiato o vuota."""
        if self.sollevato == self.cursore:
            self.sollevato = None
            return "posato"
        if self.board.piece_at(self.cursore) is None:
            return "vuota"
        scambio = self.sollevato is not None
        self.sollevato = self.cursore
        return "scambiato" if scambio else "sollevato"

    def mossa(self, promozione=None):
        """La mossa del pezzo in mano verso la casa scelta, come Move; per
        il Re che va in colonna g o c dalla sua casa, l'arrocco, anche negli
        scacchi 960. None se non c'e' un pezzo in mano."""
        if self.sollevato is None:
            return None
        partenza, arrivo = self.sollevato, self.cursore
        pezzo = self.board.piece_at(partenza)
        if pezzo is not None and pezzo.piece_type == chess.KING and pezzo.color == self.board.turn:
            for candidata in self.board.legal_moves:
                if (
                    candidata.from_square == partenza
                    and self.board.is_castling(candidata)
                    and _arrivo_del_re(self.board, candidata) == arrivo
                ):
                    return candidata
        return chess.Move(partenza, arrivo, promotion=promozione)

    def promozione(self):
        """Vero se la mossa del pezzo in mano porta un pedone in fondo."""
        if self.sollevato is None:
            return False
        pezzo = self.board.piece_at(self.sollevato)
        return (
            pezzo is not None
            and pezzo.piece_type == chess.PAWN
            and chess.square_rank(self.cursore) in (0, 7)
            and chess.square_rank(self.cursore) == (7 if pezzo.color == chess.WHITE else 0)
        )

    def giudica(self, mossa):
        """None se la mossa e' legale, altrimenti perche' non lo e'."""
        if mossa in self.board.legal_moves:
            return None
        pezzo = self.board.piece_at(mossa.from_square)
        if mossa.from_square == mossa.to_square:
            return _("Il pezzo e' gia' su quella casa.")
        if pezzo is None:
            return _("Non c'e' un pezzo da muovere.")
        if pezzo.color != self.board.turn:
            return _("Tocca al Bianco.") if self.board.turn == chess.WHITE else _("Tocca al Nero.")
        if self.board.is_pseudo_legal(mossa):
            if self.board.is_check():
                return _("Il re e' sotto scacco, e cosi' ci resta.")
            return _("La mossa lascerebbe il re sotto scacco.")
        return _("{pezzo} non puo' andare in {casa}.").format(pezzo=nome_pezzo(pezzo), casa=nome_casa(mossa.to_square))

    def san(self, mossa):
        """La mossa come la scrive chi la digita, nella notazione che il
        nucleo accetta sempre."""
        return self.board.san(mossa)


def _arrivo_del_re(board, mossa):
    """La casa dove arriva il pezzo: per gli arrocchi quella del Re, in
    colonna g o c, anche negli scacchi 960, dove python-chess scrive la
    mossa del Re verso la casa della Torre."""
    if not board.is_castling(mossa):
        return mossa.to_square
    traversa = chess.square_rank(mossa.from_square)
    return chess.square(6 if board.is_kingside_castling(mossa) else 2, traversa)
