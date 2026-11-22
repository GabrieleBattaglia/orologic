# Orologic, Easyfish: la posizione per la finestra e le parti comuni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le funzioni di Easyfish senza wx che servono alla finestra, come le ha
volute Gabriele il 22 novembre 2026, e quelle che il menu principale e
l'esploratore hanno in comune.

Lo stato del cruscotto: il menu principale e l'esploratore danno al
cruscotto la scacchiera della posizione, i giocatori dalle intestazioni, il
contesto per la scacchiera interattiva e le righe sulla posizione, cioe' la
linea, il seguito e il commento. Le voci del navigatore della partita: la
linea principale in fila, e ogni variante sotto la mossa che sostituisce.
Il commento scritto a mano prende il posto di quello di prima, ma tiene le
analisi e i disegni. La mossa digitata, coi ripieghi di sempre.
"""

import re

import chess
import chess.pgn

from ..board_utils import CustomBoard, DescribeMove, NormalizeMove
from ..config import _

# I comandi fra quadre del PGN, come i disegni e gli orologi: [%cal Ge2e4].
COMANDI_PGN = re.compile(r"\[%[^\]]*\]")
VALUTAZIONE_PGN = re.compile(r"\[%eval\s+([^\]\s]+)[^\]]*\]")
SIMBOLI_DEI_NAG = {
    chess.pgn.NAG_GOOD_MOVE: "!",
    chess.pgn.NAG_MISTAKE: "?",
    chess.pgn.NAG_BRILLIANT_MOVE: "!!",
    chess.pgn.NAG_BLUNDER: "??",
    chess.pgn.NAG_SPECULATIVE_MOVE: "!?",
    chess.pgn.NAG_DUBIOUS_MOVE: "?!",
}


def _annotazioni_di_orologic():
    """Le annotazioni che .ac scrive nel commento, [Val: ...], [BM: ...] e
    [Linea: ...], col principio tradotto come le scrive."""
    principi = [modello.split("{")[0] for modello in (_("[Val: {ev}]"), _("[BM: {bm}]"), _("[Linea: {linea}]"))]
    # Un modello tradotto senza un principio fisso non si riconosce: un
    # principio vuoto troverebbe dappertutto.
    return re.compile("|".join(re.escape(principio) + r"[^\]]*\]" for principio in principi if principio) or r"(?!)")


def testo_del_commento(commento):
    """Il commento da leggere: senza i comandi fra quadre del PGN, con la
    valutazione detta, e uno spazio solo fra le parole."""
    if not commento:
        return ""
    valutazione = VALUTAZIONE_PGN.search(commento)
    testo = " ".join(COMANDI_PGN.sub(" ", commento).split())
    if valutazione:
        testo = " ".join(filter(None, (testo, _("valutazione {v}").format(v=valutazione.group(1)))))
    return testo


def testo_libero(commento):
    """Il testo del commento scritto a mano, senza le analisi di .ac e i
    comandi fra quadre: quello che metti_il_testo sostituisce."""
    if not commento:
        return ""
    return " ".join(_annotazioni_di_orologic().sub(" ", COMANDI_PGN.sub(" ", commento)).split())


def metti_il_testo(nodo, testo):
    """Il commento scritto a mano: prende il posto del testo di prima, e
    tiene le analisi di .ac e i comandi fra quadre, come i disegni."""
    commento = nodo.comment or ""
    da_tenere = [trovata.group(0) for trovata in re.finditer(f"{COMANDI_PGN.pattern}|{_annotazioni_di_orologic().pattern}", commento)]
    nodo.comment = " ".join(filter(None, (testo.strip(), *da_tenere)))


def livello(nodo):
    """Quante volte la strada dall'inizio esce dalla linea principale."""
    conto = 0
    while nodo.parent is not None:
        if nodo.parent.variations[0] is not nodo:
            conto += 1
        nodo = nodo.parent
    return conto


def numero(board):
    """Il numero della mossa che sta per giocarsi: 12. o 12..."""
    return f"{board.fullmove_number}." if board.turn == chess.WHITE else f"{board.fullmove_number}..."


def _descrizione(mossa, board):
    try:
        return DescribeMove(mossa, board)
    # Una descrizione mancata non deve togliere la mossa.
    except Exception:  # noqa: BLE001
        return board.san(mossa)


def scacchiera_del_nodo(game, nodo):
    """La CustomBoard della posizione del nodo, con le mosse dalla partenza
    della partita, anche da una posizione data o negli scacchi 960."""
    partenza = game.board()
    board = CustomBoard(partenza.fen(), chess960=partenza.chess960)
    for mossa in mosse_del_nodo(nodo):
        board.push(mossa)
    return board


def mosse_del_nodo(nodo):
    """Le mosse dalla radice al nodo."""
    mosse = []
    while nodo.parent is not None:
        mosse.append(nodo.move)
        nodo = nodo.parent
    mosse.reverse()
    return mosse


def ancora_nella_partita(nodo):
    """Il nodo, se e' ancora nella partita, altrimenti il piu' vicino dei
    suoi antenati che c'e': dopo un taglio nel navigatore."""
    catena = []
    passo = nodo
    while passo.parent is not None:
        catena.append(passo)
        passo = passo.parent
    valido = passo
    for passo in reversed(catena):
        if passo not in valido.variations:
            break
        valido = passo
    return valido


def semimosse_dopo(nodo):
    """Quante semimosse, varianti comprese, vengono dopo questo nodo."""
    conto = 0
    da_visitare = list(nodo.variations)
    while da_visitare:
        figlio = da_visitare.pop()
        conto += 1
        da_visitare.extend(figlio.variations)
    return conto


def domanda_del_taglio(seguito):
    """La conferma del taglio di una mossa col suo seguito."""
    if seguito == 1:
        return _(
            "La mossa ha un seguito di 1 semimossa, che sparira' "
            "con lei. Confermi? (INVIO per si', ESC per no): "
        )
    return _(
        "La mossa ha un seguito di {n} semimosse, che "
        "spariranno con lei. Confermi? (INVIO per si', "
        "ESC per no): "
    ).format(n=seguito)


def leggi_la_mossa(board, testo):
    """La mossa digitata, o None: la notazione normalizzata, poi i ripieghi
    di sempre, ed5 per exd5 e la b minuscola per l'Alfiere."""
    move_san = NormalizeMove(testo)
    try:
        return board.parse_san(move_san)
    except ValueError:
        pass
    if len(move_san) == 3 and move_san[0].islower() and move_san[1].islower() and move_san[2].isdigit():
        try:
            return board.parse_san(move_san[0] + "x" + move_san[1:])
        except ValueError:
            pass
    if move_san and move_san[0] == "b":
        try:
            return board.parse_san("B" + move_san[1:])
        except ValueError:
            if len(move_san) == 3:
                try:
                    return board.parse_san("Bx" + move_san[1:])
                except ValueError:
                    pass
    return None


# Lo stato del cruscotto.


class Stato:
    """Lo stato che il menu principale e l'esploratore danno al cruscotto
    con cruscotto.dati_di: contesto e' easyfish o esploratore."""

    def __init__(self, contesto):
        self.contesto_della_scacchiera = contesto
        self.white_player = ""
        self.black_player = ""
        self.scacchiera_del_cruscotto = None
        self.righe_in_piu = []

    def aggiorna(self, game, board, nodo, scelta=None):
        intestazioni = game.headers
        self.white_player = intestazioni.get("White", "") if intestazioni.get("White", "?") != "?" else ""
        self.black_player = intestazioni.get("Black", "") if intestazioni.get("Black", "?") != "?" else ""
        self.scacchiera_del_cruscotto = board.copy()
        self.righe_in_piu = righe_della_posizione(nodo, board, scelta)


def righe_della_posizione(nodo, board, scelta=None):
    """Le righe del cruscotto sulla posizione: la linea, il seguito con le
    sue varianti, la variante scelta nell'esploratore e il commento."""
    quale = livello(nodo)
    righe = [_("Linea principale.") if not quale else _("Variante, livello {n}.").format(n=quale)]
    if nodo.variations:
        seguito = nodo.variations[0]
        mossa = f"{numero(board)} {_descrizione(seguito.move, board)}"
        altre = [board.san(variante.move) for variante in nodo.variations[1:]]
        if altre:
            righe.append(_("Seguito: {mossa}; varianti: {altre}.").format(mossa=mossa, altre=", ".join(altre)))
        else:
            righe.append(_("Seguito: {mossa}.").format(mossa=mossa))
        if scelta is not None and len(nodo.variations) > 1:
            righe.append(_("Scelta: {n} di {tot}, {mossa}.").format(
                n=scelta + 1, tot=len(nodo.variations), mossa=board.san(nodo.variations[scelta].move)))
    else:
        righe.append(_("Fine della linea."))
    commento = testo_del_commento(nodo.comment)
    if commento:
        righe.append(_("Commento: {testo}").format(testo=commento))
    return righe


# Il navigatore della partita.


def voce_della_mossa(nodo, board):
    """La voce di una mossa nel navigatore: il numero, la mossa, la sua
    descrizione, i segni, il commento. board e' la posizione prima."""
    voce = _("{numero} {mossa}, {descrizione}").format(numero=numero(board), mossa=board.san(nodo.move), descrizione=_descrizione(nodo.move, board))
    segni = "".join(SIMBOLI_DEI_NAG[nag] for nag in sorted(nodo.nags) if nag in SIMBOLI_DEI_NAG)
    if segni:
        voce += " " + segni
    commento = testo_del_commento(nodo.comment)
    if commento:
        voce += ". " + _("Commento: {testo}").format(testo=commento)
    return voce


def voce_della_variante(nodo, board):
    return _("Variante: {mossa}").format(mossa=voce_della_mossa(nodo, board))


def voce_della_partita(game):
    intestazioni = game.headers
    voce = _("{bianco} vs {nero}, {risultato}").format(
        bianco=intestazioni.get("White", "?"), nero=intestazioni.get("Black", "?"), risultato=intestazioni.get("Result", "*"))
    commento = testo_del_commento(game.comment)
    if commento:
        voce += ". " + _("Commento: {testo}").format(testo=commento)
    return voce


def linea(primo, board):
    """La linea che comincia col nodo primo, board la posizione prima:
    [(nodo, voce, varianti)], dove varianti sono le alternative a quella
    mossa, [(nodo, voce, linea che segue)]. Ricorsiva solo nelle varianti,
    non nelle mosse: le partite lunghe non hanno limiti."""
    passi = []
    board = board.copy()
    nodo = primo
    while nodo is not None:
        varianti = []
        genitore = nodo.parent
        if genitore.variations[0] is nodo:
            for alternativa in genitore.variations[1:]:
                dopo = board.copy()
                dopo.push(alternativa.move)
                seguito = linea(alternativa.variations[0], dopo) if alternativa.variations else []
                varianti.append((alternativa, voce_della_variante(alternativa, board), seguito))
        passi.append((nodo, voce_della_mossa(nodo, board), varianti))
        board.push(nodo.move)
        nodo = nodo.variations[0] if nodo.variations else None
    return passi


def albero(game):
    """Le voci del navigatore: la linea principale dalla prima mossa."""
    if not game.variations:
        return []
    return linea(game.variations[0], game.board())


def inizio_della_variante(nodo):
    """La prima mossa della variante dove sta il nodo, o None se il nodo e'
    sulla linea principale."""
    while nodo.parent is not None:
        if nodo.parent.variations[0] is not nodo:
            return nodo
        nodo = nodo.parent
    return None


def righe_dell_analisi(board, analisi):
    """Le righe di un'analisi a piu' linee, come le stampa l'esploratore:
    1. +0.35 (52.0/40.0/8.0) e4 e5 Nf3."""
    righe = []
    for indice, info in enumerate(analisi if isinstance(analisi, list) else [analisi]):
        pv = info.get("pv", [])
        if not pv or info.get("score") is None:
            continue
        punteggio = info.get("score").pov(board.turn)
        valutazione = f"M{abs(punteggio.mate())}" if punteggio.is_mate() else f"{punteggio.score(mate_score=10000) / 100:+.2f}"
        wdl = info.get("wdl")
        probabilita = f"({wdl[0] / 10:.1f}/{wdl[1] / 10:.1f}/{wdl[2] / 10:.1f}) " if wdl else ""
        mosse = []
        prova = board.copy()
        for mossa in pv:
            try:
                mosse.append(prova.san(mossa))
            except (ValueError, AssertionError):
                break
            prova.push(mossa)
        righe.append(f"{indice + 1}. {valutazione} {probabilita}{' '.join(mosse)}")
    return righe

