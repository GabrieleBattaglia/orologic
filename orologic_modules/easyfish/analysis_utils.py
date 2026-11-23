# Orologic, Easyfish: linee di analisi del motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import chess
import chess.engine

from .. import board_utils, strato
from ..config import _
from .posizione import righe_dell_analisi


def GetPrincipalVariationSan(board, pv):
    """Restituisce una lista di mosse SAN a partire da una variante principale (PV)."""
    temp_board = board.copy()
    san_moves = []
    for move in pv:
        try:
            san_moves.append(temp_board.san(move))
            temp_board.push(move)
        # Il motore e' un processo separato che puo' non rispondere:
        # senza analisi si prosegue.
        except Exception:  # noqa: BLE001
            break
    return san_moves


def FormatAnalysisInfo(board, info):
    """Formatta un singolo dizionario di info analisi in una stringa leggibile."""
    pv = info.get("pv", [])
    if not pv:
        return None

    score_val = info.get("score").pov(board.turn)
    if score_val.is_mate():
        eval_str = f"M{abs(score_val.mate())}"
    else:
        eval_str = f"{score_val.score(mate_score=10000) / 100:+.2f}"

    wdl = info.get("wdl")
    wdl_str = ""
    if wdl:
        wdl_pov = wdl.pov(board.turn) if hasattr(wdl, "pov") else wdl
        try:
            # supporta sia wdl object che list
            w = wdl_pov.wins / 10 if hasattr(wdl_pov, "wins") else wdl_pov[0] / 10
            d = wdl_pov.draws / 10 if hasattr(wdl_pov, "draws") else wdl_pov[1] / 10
            loss = (
                wdl_pov.losses / 10 if hasattr(wdl_pov, "losses") else wdl_pov[2] / 10
            )
            wdl_str = f" WDL:{w:.0f}%-{d:.0f}%-{loss:.0f}%"
        # Il motore e' un processo separato che puo' non rispondere:
        # senza analisi si prosegue.
        except Exception:  # noqa: BLE001, S110
            pass

    line_san = " ".join(GetPrincipalVariationSan(board, pv))
    time_spent = info.get("time", 0.0)
    depth = info.get("depth", 0)
    seldepth = info.get("seldepth", 0)

    return f"{time_spent:.0f}S Prof:{depth}/{seldepth} CP: {eval_str}{wdl_str}\nBL: {line_san}"


def opzioni_del_motore(engine):
    """Le opzioni del motore col valore in uso, una riga ciascuna: quelle
    scelte da Orologic, o quelle di partenza del motore. I pulsanti, come
    Clear Hash, non hanno un valore e restano fuori."""
    try:
        opzioni = engine.options
    # Un motore finto, o che non risponde, non ha opzioni da dire.
    except Exception:  # noqa: BLE001
        return []
    in_uso = getattr(getattr(engine, "protocol", None), "config", None) or {}
    righe = []
    for nome, opzione in opzioni.items():
        if getattr(opzione, "type", None) in ("button", "reset"):
            continue
        valore = in_uso.get(nome, getattr(opzione, "default", None))
        if isinstance(valore, bool):
            valore = _("sì") if valore else _("no")
        elif valore in (None, "", "<empty>"):
            # Stockfish scrive <empty> per le stringhe vuote.
            valore = _("vuota")
        righe.append(_("{opzione}: {valore}").format(opzione=nome, valore=valore))
    return righe


def righe_del_motore(engine, analisi, chieste):
    """L'intestazione dell'analisi, una riga per dato: il motore, il tempo,
    la profondita', i nodi, l'hash occupata, le tablebase, il carico della
    CPU, il fattore di ramificazione, il messaggio del motore, le linee
    chieste e avute, e le opzioni in uso. I dati della ricerca sono quelli
    della linea migliore; quelli che il motore non da' non si dicono."""
    elenco = analisi if isinstance(analisi, list) else [analisi]
    prima = elenco[0] if elenco else {}
    righe = []
    try:
        identita = engine.id
    # Un motore finto, o che non risponde, non dice chi e'.
    except Exception:  # noqa: BLE001
        identita = {}
    nome = identita.get("name")
    if nome:
        autore = identita.get("author")
        righe.append(_("Motore: {nome}, di {autore}.").format(nome=nome, autore=autore) if autore else _("Motore: {nome}.").format(nome=nome))
    if prima.get("time") is not None:
        righe.append(_("Tempo: {s:.2f} secondi.").format(s=prima["time"]))
    if prima.get("depth") is not None:
        if prima.get("seldepth") is not None:
            righe.append(_("Profondita': {p}, selettiva {s}.").format(p=prima["depth"], s=prima["seldepth"]))
        else:
            righe.append(_("Profondita': {p}.").format(p=prima["depth"]))
    if prima.get("nodes") is not None:
        righe.append(_("Nodi: {n}.").format(n=prima["nodes"]))
    if prima.get("nps") is not None:
        righe.append(_("Nodi al secondo: {n}.").format(n=prima["nps"]))
    if prima.get("hashfull") is not None:
        righe.append(_("Hash occupata: {p:.1f}%.").format(p=prima["hashfull"] / 10))
    if prima.get("tbhits") is not None:
        righe.append(_("Posizioni trovate nelle tablebase: {n}.").format(n=prima["tbhits"]))
    if prima.get("cpuload") is not None:
        righe.append(_("Carico della CPU: {p:.1f}%.").format(p=prima["cpuload"] / 10))
    if prima.get("ebf") is not None:
        righe.append(_("Fattore di ramificazione: {f:.2f}.").format(f=prima["ebf"]))
    if prima.get("string"):
        righe.append(_("Messaggio del motore: {testo}").format(testo=prima["string"]))
    avute = sum(1 for info in elenco if info.get("pv"))
    righe.append(_("Linee: {chieste} chieste, {avute} avute.").format(chieste=chieste, avute=avute))
    opzioni = opzioni_del_motore(engine)
    if opzioni:
        righe.append(_("Opzioni del motore:"))
        righe.extend(opzioni)
    return righe


def analizza(board, engine, secondi, linee):
    """L'analisi della posizione, uguale in tutte le modalita': (analisi, o
    None se non c'e', righe), con l'intestazione di righe_del_motore e poi
    le linee, tante quante linee."""
    if not engine:
        return None, [_("Motore non disponibile.")]
    try:
        analisi = engine.analyse(board, chess.engine.Limit(time=secondi), multipv=linee)
    # Il motore e' un processo separato che puo' non rispondere:
    # senza analisi si prosegue.
    except Exception as e:  # noqa: BLE001
        return None, [_("Analisi fallita: {e}").format(e=e)]
    if not isinstance(analisi, list):
        analisi = [analisi]
    righe = righe_del_motore(engine, analisi, linee)
    trovate = righe_dell_analisi(board, analisi)
    if trovate:
        righe.append(_("Le linee:"))
        righe.extend(trovate)
    else:
        righe.append(_("Nessuna linea trovata."))
    # Nella finestra da leggere: Rendi verbosa, e il cursore sulla prima
    # linea (Gabriele, collaudo del 23 novembre 2026).
    verbosa, inizio = dettagli_della_lettura(board, analisi, righe)
    strato.lettura_verbosa(verbosa)
    strato.lettura_dalla_riga(inizio)
    return analisi, righe


def dettagli_della_lettura(board, analisi, righe):
    """(forma verbosa o None, la riga della prima linea o None) di
    un'analisi, per la finestra da leggere."""
    verbosa = forma_verbosa(board, analisi) or None
    trovate = righe_dell_analisi(board, analisi)
    inizio = trovate[0] if trovate and trovate[0] in righe else None
    return verbosa, inizio


def _percentuali(wdl, colore):
    """Vittoria, patta e sconfitta in millesimi, dal lato di colore."""
    if hasattr(wdl, "pov"):
        wdl = wdl.pov(colore)
    return tuple(getattr(wdl, nome, None) for nome in ("wins", "draws", "losses")) if hasattr(wdl, "wins") else tuple(wdl[:3])


def forma_verbosa(board, analisi):
    """Le linee a parole, per Rendi verbosa, senza l'intestazione del
    motore: Linea 1: +0.35, vittoria 52%, patta 40%, sconfitta 8%; sotto,
    una riga per mossa, come la descrive Orologic, 34. pedone domodossola
    cattura en passant in como 6, Alfiere firenze 4."""
    righe = []
    for indice, info in enumerate(analisi if isinstance(analisi, list) else [analisi]):
        pv = info.get("pv", [])
        if not pv or info.get("score") is None:
            continue
        punteggio = info.get("score").pov(board.turn)
        if punteggio.is_mate():
            matto = punteggio.mate()
            valutazione = (_("matto in {n}") if matto > 0 else _("matto subito in {n}")).format(n=abs(matto))
        else:
            valutazione = f"{punteggio.score(mate_score=10000) / 100:+.2f}"
        testa = _("Linea {n}: {valutazione}").format(n=indice + 1, valutazione=valutazione)
        wdl = info.get("wdl")
        if wdl:
            vittoria, patta, sconfitta = _percentuali(wdl, board.turn)
            testa += _(", vittoria {v}%, patta {p}%, sconfitta {s}%").format(v=round(vittoria / 10), p=round(patta / 10), s=round(sconfitta / 10))
        righe.append(testa)
        # Solo le mosse legali: una linea vecchia non fa cadere la finestra.
        legali = []
        prova = board.copy()
        for mossa in pv:
            if not prova.is_legal(mossa):
                break
            legali.append(mossa)
            prova.push(mossa)
        righe.extend(riga for riga in board_utils.format_pv_descriptively(board, legali).split("\n") if riga)
    return righe


def RunAnalysis(board, engine, time_limit, multipv_count):
    """
    Esegue un'analisi della posizione corrente.
    Restituisce una lista di stringhe formattate.
    """
    if not engine:
        return [_("Motore non disponibile.")]

    results = []
    try:
        limit = chess.engine.Limit(time=time_limit)
        info_list = engine.analyse(board, limit, multipv=multipv_count)

        if isinstance(info_list, dict) or not isinstance(info_list, list):
            info_list = [info_list]

        for i, info in enumerate(info_list):
            formatted = FormatAnalysisInfo(board, info)
            if formatted:
                if len(info_list) > 1:
                    lines = formatted.split("\n")
                    lines[0] = f"{i + 1}. " + lines[0]
                    results.append("\n".join(lines))
                else:
                    results.append(formatted)

    # Il motore e' un processo separato che puo' non rispondere:
    # senza analisi si prosegue.
    except Exception as e:  # noqa: BLE001
        results.append(_("Analisi fallita: {e}").format(e=e))

    return results
