# Orologic: l'albero delle aperture di eco.pgn, la logica.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'albero delle aperture, voce aperture del menu principale, solo nella
finestra (Gabriele, 25 novembre 2026): le linee di eco.pgn, il file delle
aperture di pgn-extract, in un albero di mosse, come la ricerca PGN ma piu'
semplice.

Ogni mossa dice quante delle linee di eco.pgn passano di li', in
percentuale sul totale, e il nome dell'apertura: il codice ECO, l'apertura
e la variante della posizione, se una linea ci finisce, anche arrivandoci
per un'altra strada, come classifica pgn-extract; altrimenti quello della
mossa sopra piu' vicina che ce l'ha. Da una linea di almeno due semimosse
si passa all'analisi manuale o a Easyfish, per allenarsi; al ritorno
l'albero si riapre allo stesso punto.

Qui c'e' tutto quello che non e' finestra; la finestra e'
finestra_aperture.py.
"""

import dataclasses
import io

import chess
import chess.pgn

from . import board_utils, strato
from .config import _

# Da quante semimosse una linea si porta all'analisi o a Easyfish.
SEMIMOSSE_MINIME = 2


@dataclasses.dataclass(eq=False)
class Nodo:
    """Una mossa dell'albero: la mossa, quante linee ci passano, i figli in
    ordine di inserimento, e la voce di eco.pgn della posizione, o None."""

    mossa: object = None
    linee: int = 0
    figli: dict = dataclasses.field(default_factory=dict)
    voce: object = None
    genitore: object = None

    @property
    def semimosse(self):
        conto, nodo = 0, self
        while nodo.genitore is not None:
            conto, nodo = conto + 1, nodo.genitore
        return conto

    def percorso(self):
        """Le mosse dalla radice a qui."""
        mosse, nodo = [], self
        while nodo.genitore is not None:
            mosse.append(nodo.mossa)
            nodo = nodo.genitore
        return list(reversed(mosse))

    def figli_in_ordine(self):
        """I figli, prima quelli con piu' linee, poi per mossa."""
        return sorted(self.figli.values(), key=lambda figlio: (-figlio.linee, figlio.mossa.uci()))

    def voce_piu_vicina(self):
        """La voce di questa posizione, o quella della mossa sopra piu' vicina
        che ce l'ha; None alla radice o senza nessuna."""
        nodo = self
        while nodo is not None:
            if nodo.voce is not None:
                return nodo.voce
            nodo = nodo.genitore
        return None


def nome_della_voce(voce):
    """Il nome di una voce di eco.pgn: B90 Sicilian, Najdorf."""
    nome = " ".join(parte for parte in (voce.get("eco"), voce.get("opening")) if parte)
    if voce.get("variation"):
        nome = f"{nome}, {voce['variation']}"
    return nome


@dataclasses.dataclass
class Albero:
    radice: Nodo
    totale: int


def costruisci(eco_db):
    """L'albero delle linee di eco_db, come lo da' LoadEcoDatabaseWithFEN:
    ogni linea conta una volta in ogni mossa del suo cammino; la voce di un
    nodo e' la prima di eco.pgn che finisce nella sua posizione."""
    radice = Nodo()
    totale = 0
    for voci in eco_db.values():
        for voce in voci:
            board = chess.Board()
            nodo = radice
            try:
                giocate = []
                for san in voce["moves"]:
                    giocate.append(board.parse_san(san))
                    board.push(giocate[-1])
            # Una linea che non si gioca resta fuori.
            except ValueError:
                continue
            totale += 1
            board = chess.Board()
            for giocata in giocate:
                board.push(giocata)
                figlio = nodo.figli.get(giocata)
                if figlio is None:
                    figlio = Nodo(mossa=giocata, genitore=nodo)
                    voci_della_posizione = eco_db.get(board.epd())
                    figlio.voce = voci_della_posizione[0] if voci_della_posizione else None
                    nodo.figli[giocata] = figlio
                figlio.linee += 1
                nodo = figlio
    radice.linee = totale
    return Albero(radice, totale)


def carica():
    """L'albero di eco.pgn di Orologic, senza la riga che LoadEcoDatabase
    stampa nell'area principale."""
    with strato.raccogli(io.StringIO()):
        return costruisci(board_utils.LoadEcoDatabaseWithFEN("eco.pgn"))


def _numero(board):
    return f"{board.fullmove_number}." if board.turn == chess.WHITE else f"{board.fullmove_number}..."


def voce_del_nodo(nodo, totale):
    """La riga di una mossa dell'albero: la mossa descritta, la mossa col
    numero, la percentuale sul totale e il nome dell'apertura."""
    board = chess.Board()
    for giocata in nodo.percorso()[:-1]:
        board.push(giocata)
    san = board.san(nodo.mossa)
    try:
        descrizione = board_utils.DescribeMove(nodo.mossa, board)
    # Una descrizione che non riesce lascia la mossa com'e'.
    except Exception:  # noqa: BLE001
        descrizione = san
    pct = nodo.linee / totale * 100 if totale else 0
    riga = _("{descrizione} ({numero} {mossa}) = {pct:.1f}%").format(descrizione=descrizione, numero=_numero(board), mossa=san, pct=pct)
    voce = nodo.voce_piu_vicina()
    return f"{riga}, {nome_della_voce(voce)}" if voce else riga


def linea(nodo):
    """La linea fino al nodo, coi numeri: 1. e4 c5 2. Nf3."""
    board = chess.Board()
    return board.variation_san(nodo.percorso()) if nodo.genitore is not None else ""


def partita(nodo):
    """La linea come partita, con l'apertura nelle intestazioni, per
    l'analisi e per Easyfish."""
    game = chess.pgn.Game()
    game.headers["Event"] = _("Albero aperture")
    voce = nodo.voce_piu_vicina()
    if voce:
        game.headers["ECO"] = voce.get("eco") or "?"
        if voce.get("opening"):
            game.headers["Opening"] = voce["opening"]
        if voce.get("variation"):
            game.headers["Variation"] = voce["variation"]
    corrente = game
    for giocata in nodo.percorso():
        corrente = corrente.add_variation(giocata)
    return game


def trova(albero, mosse):
    """Il nodo dell'albero in fondo alle mosse, o il piu' profondo che c'e'."""
    nodo = albero.radice
    for giocata in mosse:
        figlio = nodo.figli.get(giocata)
        if figlio is None:
            break
        nodo = figlio
    return nodo


@dataclasses.dataclass
class Stato:
    """Quello che resta fra un'apertura e l'altra della finestra: l'albero e
    la linea scelta, per riaprire allo stesso punto."""

    albero: object = None
    mosse: list = dataclasses.field(default_factory=list)


def run():
    """La voce aperture del menu principale: la finestra dell'albero, e a
    ogni uscita verso l'analisi o Easyfish, al ritorno, di nuovo la finestra
    allo stesso punto."""
    from . import pgn_search

    stato = Stato()
    while True:
        uscita = strato.albero_aperture(stato)
        if uscita is None:
            return
        azione, game = uscita
        if azione == "easyfish":
            from .easyfish import easyfish_app

            easyfish_app.run(partita=board_utils.CopyPgnGame(game))
        else:
            pgn_search._avvia_analisi(game, automatica=False)
