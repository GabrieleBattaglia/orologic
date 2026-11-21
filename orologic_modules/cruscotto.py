# Orologic: il cruscotto delle partite nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il cruscotto, tappa T2 della GUI (Piano della GUI.txt, decisione C1).

Durante una partita, nell'arbitraggio, in Tempo, contro il motore e su
Lichess, l'area della finestra non scorre come un terminale: e' un cruscotto
fisso che si riscrive da solo, col prompt in fondo. Dall'alto: i giocatori e
lo stato della partita, la scacchiera, gli orologi a parole, le ultime mosse
a parole con il consumo dell'orologio e il tempo speso, gli ultimi messaggi.

Qui ci sono solo funzioni pure, che si provano senza finestra:
  dati_di   i dati del cruscotto da uno stato di partita di qualunque
            modalita', con i nomi che ognuna usa;
  righe     le righe del cruscotto, come coppie (sezione, testo), senza il
            prompt, che aggiunge la finestra.
Il consumo dopo ogni semimossa e' quello dell'orologio di chi l'ha giocata,
come %bp e %np del prompt (Gabriele, 20 novembre 2026).
"""

import chess

from . import board_utils, tempo
from .config import _

MOSSE_MOSTRATE = 6
MESSAGGI_MOSTRATI = 4


def _colore(valore):
    """chess.WHITE o chess.BLACK da come le modalita' scrivono il tratto."""
    if valore in ("white", chess.WHITE):
        return chess.WHITE
    if valore in ("black", chess.BLACK):
        return chess.BLACK
    return None


def dati_di(stato, board=None):
    """I dati del cruscotto da uno stato di partita. board serve dove la
    scacchiera non sta nello stato, come in Easyfish. Ogni lettura e' prudente:
    lo stato appartiene al nucleo, che intanto puo' cambiarlo."""
    if hasattr(stato, "get_clocks"):
        bianco, nero = stato.get_clocks()
    else:
        bianco = getattr(stato, "white_remaining", None)
        nero = getattr(stato, "black_remaining", None)
    if board is None:
        board = getattr(stato, "scacchiera_del_cruscotto", None)
    if board is None and not getattr(stato, "senza_scacchiera", False):
        board = getattr(stato, "board", None)
    if hasattr(stato, "_tempo_fase"):
        iniziale_bianco = stato._tempo_fase(stato.white_phase, "white")
        iniziale_nero = stato._tempo_fase(stato.black_phase, "black")
    else:
        iniziale_bianco = getattr(stato, "iniziale_bianco", None)
        iniziale_nero = getattr(stato, "iniziale_nero", None)
    mio = getattr(stato, "human_color", None)
    if mio is None and hasattr(stato, "my_color"):
        mio = stato.my_color
    tratto = board.turn if board is not None else _colore(getattr(stato, "active_color", None))
    mancano = None
    if hasattr(stato, "clock_config"):
        try:
            mancano = board_utils.mosse_al_controllo(stato)
        except (AttributeError, KeyError, IndexError, TypeError):
            mancano = None
    return {
        "bianco_nome": getattr(stato, "white_player", "") or _("Bianco"),
        "nero_nome": getattr(stato, "black_player", "") or _("Nero"),
        "mio": mio,
        "board": board.copy() if board is not None else None,
        "mosse": list(getattr(stato, "move_history", []) or []),
        "bianco": bianco,
        "nero": nero,
        "iniziale_bianco": iniziale_bianco,
        "iniziale_nero": iniziale_nero,
        "tratto": tratto,
        "pausa": bool(getattr(stato, "paused", False)),
        "senza_orologio": bool(getattr(stato, "ignore_clock", False)),
        "spesi": list(getattr(stato, "move_times", []) or []),
        "residui": list(getattr(stato, "clocks_history", []) or []),
        "mosse_al_controllo": mancano,
        # Per la scacchiera interattiva: la scacchiera di .s che aspetta un
        # tasto, e la partita che si osserva soltanto.
        "vista_ferma": bool(getattr(stato, "vista_ferma", False)),
        "da_guardare": bool(getattr(stato, "solo_da_guardare", False)),
    }


def scacchiera(board, dal_nero=False):
    """La scacchiera: lettere sopra e sotto, numeri ai due lati; maiuscoli i
    pezzi bianchi, minuscoli i neri; meno le case nere e piu' le bianche, come
    il .s di Orologic. Dal lato di chi gioca col Nero, se dal_nero."""
    colonne = range(7, -1, -1) if dal_nero else range(8)
    traverse = range(8) if dal_nero else range(7, -1, -1)
    lettere = " " + "".join(chess.FILE_NAMES[c] for c in colonne)
    righe = [lettere]
    for traversa in traverse:
        riga = str(traversa + 1)
        for colonna in colonne:
            pezzo = board.piece_at(chess.square(colonna, traversa))
            riga += pezzo.symbol() if pezzo else "-" if (traversa + colonna) % 2 == 0 else "+"
        righe.append(riga + str(traversa + 1))
    righe.append(lettere)
    return righe


def _consumo(residuo, iniziale):
    if residuo is None or not iniziale:
        return None
    return (iniziale - max(0.0, residuo)) / iniziale * 100


def _dal_fondo(valori, indice, totale):
    """Il valore della semimossa indice in una storia che copre le ultime
    semimosse della partita: in Easyfish si puo' partire da una posizione con
    mosse gia' giocate, e la storia comincia da li'."""
    posto = indice - (totale - len(valori))
    return valori[posto] if 0 <= posto < len(valori) else None


def _semimossa(descrizione, indice, totale, dati):
    """Una semimossa: la descrizione, il consumo dell'orologio dopo la
    mossa e il tempo speso, quando si sanno."""
    bianca = indice % 2 == 0
    iniziale = dati["iniziale_bianco"] if bianca else dati["iniziale_nero"]
    parti = [descrizione]
    consumo = _consumo(_dal_fondo(dati["residui"], indice, totale), iniziale)
    if consumo is not None:
        parti.append(f"{consumo:.0f}%")
    speso = _dal_fondo(dati["spesi"], indice, totale)
    if speso is not None:
        parti.append(_("in {tempo}").format(tempo=tempo.parlato(speso)))
    return " ".join(parti)


def _semimosse(board, mosse, quante):
    """Le ultime quante semimosse come terne (numero, bianca, descrizione),
    a parole come le dice Orologic. Numero e colore vengono dalla
    scacchiera, che puo' partire da una posizione col Nero al tratto; senza
    scacchiera, come in Tempo, le mosse restano come sono state scritte, e
    la prima e' del Bianco."""
    if board is None or not board.move_stack:
        primo = max(0, len(mosse) - quante)
        return [(indice // 2 + 1, indice % 2 == 0, mosse[indice]) for indice in range(primo, len(mosse))]
    radice = board.root()
    pila = board.move_stack
    primo = max(0, len(pila) - quante)
    for mossa in pila[:primo]:
        radice.push(mossa)
    semimosse = []
    for mossa in pila[primo:]:
        try:
            descrizione = board_utils.DescribeMove(mossa, radice)
        # Una descrizione mancata non deve togliere il cruscotto.
        except Exception:  # noqa: BLE001
            descrizione = radice.san(mossa)
        semimosse.append((radice.fullmove_number, radice.turn == chess.WHITE, descrizione))
        radice.push(mossa)
    return semimosse


def _righe_delle_mosse(dati):
    """Le ultime mosse, le due semimosse di un numero sulla stessa riga."""
    board = dati["board"]
    totale = len(board.move_stack) if board is not None and board.move_stack else len(dati["mosse"])
    if not totale:
        return [("mosse", _("Ultime mosse: nessuna."))]
    # Una semimossa in piu', perche' la prima riga non resti a meta' quando
    # comincia col Nero.
    semimosse = _semimosse(board, dati["mosse"], MOSSE_MOSTRATE * 2 + 1)
    primo = totale - len(semimosse)
    righe_numerate = []
    for posto, (numero, bianca, descrizione) in enumerate(semimosse):
        testo = _semimossa(descrizione, primo + posto, totale, dati)
        if bianca or not righe_numerate or righe_numerate[-1][0] != numero:
            righe_numerate.append((numero, [f"{numero}. {testo}" if bianca else f"{numero}... {testo}"]))
        else:
            righe_numerate[-1][1].append(testo)
    righe = [("mosse", _("Ultime mosse:"))]
    for _numero, pezzi in righe_numerate[-MOSSE_MOSTRATE:]:
        righe.append(("mosse", "; ".join(pezzi) + "."))
    return righe


def _righe_delle_informazioni(dati):
    board = dati["board"]
    righe = [("info", _("Bianco: {bianco}. Nero: {nero}.").format(bianco=dati["bianco_nome"], nero=dati["nero_nome"]))]
    parti = []
    if board is not None:
        parti.append(_("Mossa {n}.").format(n=board.fullmove_number))
    if dati["tratto"] is not None:
        parti.append(_("Tocca al Bianco.") if dati["tratto"] == chess.WHITE else _("Tocca al Nero."))
    if dati["pausa"]:
        parti.append(_("Orologi in pausa."))
    elif dati["senza_orologio"]:
        parti.append(_("Senza orologio."))
    if board is not None:
        bianco, nero = board_utils.CalculateMaterial(board)
        scarto = bianco - nero
        if not scarto:
            parti.append(_("Materiale pari."))
        elif scarto > 0:
            parti.append(_("Materiale: il Bianco ha {n} in più.").format(n=scarto))
        else:
            parti.append(_("Materiale: il Nero ha {n} in più.").format(n=-scarto))
    if dati["mosse_al_controllo"]:
        parti.append(_("Mosse al controllo: {n}.").format(n=dati["mosse_al_controllo"]))
    if parti:
        righe.append(("info", " ".join(parti)))
    return righe


def _riga_degli_orologi(dati):
    bianco, nero = dati["bianco"], dati["nero"]
    if bianco is None or nero is None:
        return []
    parti = []
    for nome, residuo, iniziale, colore in (
        (_("Bianco"), bianco, dati["iniziale_bianco"], chess.WHITE),
        (_("Nero"), nero, dati["iniziale_nero"], chess.BLACK),
    ):
        pezzo = f"{nome} {tempo.parlato(max(0.0, residuo))}"
        consumo = _consumo(residuo, iniziale)
        if consumo is not None:
            pezzo += f", {consumo:.0f}%"
        if dati["tratto"] == colore and not dati["pausa"] and not dati["senza_orologio"]:
            pezzo += ", " + _("in moto")
        parti.append(pezzo + ".")
    scarto = int(bianco) - int(nero)
    if not scarto:
        parti.append(_("Orologi pari."))
    elif scarto > 0:
        parti.append(_("Il Bianco ha {tempo} in più.").format(tempo=tempo.parlato(scarto)))
    else:
        parti.append(_("Il Nero ha {tempo} in più.").format(tempo=tempo.parlato(-scarto)))
    return [("orologi", " ".join(parti))]


def righe(dati, messaggi):
    """Le righe del cruscotto, come coppie (sezione, testo), senza il prompt."""
    risultato = _righe_delle_informazioni(dati)
    if dati["board"] is not None:
        risultato.extend(("scacchiera", riga) for riga in scacchiera(dati["board"], dati["mio"] == chess.BLACK))
    risultato.extend(_riga_degli_orologi(dati))
    risultato.extend(_righe_delle_mosse(dati))
    risultato.append(("messaggi", _("Messaggi:")))
    risultato.extend(("messaggi", testo) for testo in messaggi[-MESSAGGI_MOSTRATI:])
    return risultato
