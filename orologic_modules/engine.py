# Orologic, motore: analisi assistita e analisi automatica.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import contextlib
import datetime
import math
import os
import re
import statistics
import subprocess
import sys
import time

import chess
import chess.engine
import chess.pgn
import pyperclip
from GBUtils import Acusticator, dgt, key, menu

from . import board_utils, config, localizzazione, storage, strato, tempo, ui, version
from .config import _


def calculate_move_accuracy(w_before, w_after):
    """
    Calcola accuratezza mossa (0-100) basata su Delta W (perdita di probabilità).
    w_before: Probabilità vittoria PRIMA della mossa (dal punto di vista di chi muove).
    w_after: Probabilità vittoria DOPO la mossa (dal punto di vista di chi HA mosso).
    Come Lichess per intero (Gabriele, 23 novembre 2026): se la mossa non
    perde niente vale 100; altrimenti la formula della sua pagina
    sull'accuratezza, piu' un punto d'incertezza, fra 0 e 100. Li' Win% va
    da 0 a 100: per questo delta_w si moltiplica per cento.
    """
    if w_after >= w_before:
        return 100.0
    delta_w = w_before - w_after
    acc = 103.1668100711649 * math.exp(-0.04354415386753951 * delta_w * 100) - 3.166924740191411
    return max(0.0, min(100.0, acc + 1))


def percentuale_di_vittoria(punteggio):
    """La probabilita' di vittoria del Bianco in percento, come la calcola
    Lichess: i centesimi limitati a piu' o meno mille, il matto a mille."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * _centesimi(punteggio.white()))) - 1)


def _centesimi(punteggio):
    """I centesimi di un punteggio dal suo lato, limitati come fa Lichess a
    piu' o meno mille; un matto vale mille, per chi lo da'."""
    if punteggio.is_mate():
        return 1000 if punteggio > chess.engine.Cp(0) else -1000
    return max(-1000, min(1000, punteggio.score()))


def _vittoria_dal_lato(punteggio, colore):
    vittoria = percentuale_di_vittoria(punteggio)
    return vittoria if colore == chess.WHITE else 100 - vittoria


def precisione_della_partita(mosse):
    """La precisione di ogni giocatore come la calcola Lichess
    (AccuracyPercent.gameAccuracy): ogni mossa pesa quanto e' tesa la
    posizione, la deviazione standard della probabilita' di vittoria in una
    finestra di mosse, fra 0,5 e 12; poi la media pesata e la media
    armonica, e la media fra le due. mosse sono i risultati dell'analisi in
    ordine, con colore, vittoria_prima, vittoria_dopo e precisione. Prima la
    finestra guardava quanto oscillava la precisione del giocatore, e i
    numeri non erano quelli di Lichess (Gabriele, 23 novembre 2026).
    Restituisce {colore: precisione}, con None per chi non ha mosse."""
    risultato = {chess.WHITE: None, chess.BLACK: None}
    if not mosse:
        return risultato
    valori = [mosse[0]["vittoria_prima"]] + [mossa["vittoria_dopo"] for mossa in mosse]
    larghezza = max(2, min(8, len(mosse) // 10))
    if len(valori) >= larghezza:
        scorrevoli = [valori[inizio : inizio + larghezza] for inizio in range(len(valori) - larghezza + 1)]
    else:
        scorrevoli = [valori]
    finestre = [valori[:larghezza]] * max(0, min(larghezza, len(valori)) - 2) + scorrevoli
    pesi = [max(0.5, min(12.0, statistics.pstdev(finestra))) for finestra in finestre]
    for colore in chess.COLORS:
        coppie = [(mossa["precisione"], peso) for mossa, peso in zip(mosse, pesi, strict=False) if mossa["colore"] == colore]
        if not coppie:
            continue
        pesata = sum(valore * peso for valore, peso in coppie) / sum(peso for _valore, peso in coppie)
        # Come Lichess: una mossa a zero azzera la media armonica.
        armonica = 0.0 if any(valore <= 0 for valore, _peso in coppie) else len(coppie) / sum(1 / valore for valore, _peso in coppie)
        risultato[colore] = (pesata + armonica) / 2
    return risultato


def estimate_elo_poly(accuracy):
    """
    Stima ELO con polinomio di 3° grado.
    """
    acc = accuracy
    return 2.05 + 12.9 * acc - 0.256 * (acc**2) + 0.00401 * (acc**3)


# Quanto puo' cambiare la precisione dello stesso giocatore da una partita
# all'altra: l'Elo stimato da una partita sola e' un intervallo.
MARGINE_DELLA_PRECISIONE = 5


def intervallo_elo(precisione):
    """L'Elo stimato come intervallo, arrotondato alla decina: da una
    partita sola un numero secco diceva troppo (Gabriele, 23 novembre
    2026)."""
    basso = estimate_elo_poly(max(0.0, precisione - MARGINE_DELLA_PRECISIONE))
    alto = estimate_elo_poly(min(100.0, precisione + MARGINE_DELLA_PRECISIONE))
    return int(round(basso, -1)), int(round(alto, -1))


# Le fasi della partita, in ordine: una volta passati alla successiva non si torna.
FASI = ("apertura", "mediogioco", "finale")


def fase_della_posizione(board):
    """La fase della posizione, come il Divider di Lichess semplificato:
    finale con sei pezzi o meno fra donne, torri, alfieri e cavalli;
    mediogioco con dieci o meno, con una prima traversa sguarnita, cioe'
    con meno di quattro pezzi, o dalla sedicesima mossa; apertura
    altrimenti."""
    pezzi = sum(len(board.pieces(tipo, colore)) for tipo in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN) for colore in chess.COLORS)
    if pezzi <= 6:
        return "finale"
    sguarnita = (
        chess.popcount(board.occupied_co[chess.WHITE] & chess.BB_RANK_1) < 4
        or chess.popcount(board.occupied_co[chess.BLACK] & chess.BB_RANK_8) < 4
    )
    if pezzi <= 10 or sguarnita or board.fullmove_number > 15:
        return "mediogioco"
    return "apertura"


def _nome_della_fase(fase):
    return {"apertura": _("apertura"), "mediogioco": _("mediogioco"), "finale": _("finale")}[fase]


def _nome_della_mossa(nodo):
    """23. Qxf7 o 23... Qxf7."""
    prima = nodo.parent.board()
    return f"{prima.fullmove_number}{'.' if prima.turn == chess.WHITE else '...'} {prima.san(nodo.move)}"


def _tempi_delle_mosse(pgn_game):
    """{nodo: secondi spesi} dagli orologi del PGN, [%clk]: l'orologio di
    prima dello stesso giocatore, meno quello di adesso, piu' l'incremento.
    La prima mossa di ognuno parte dal tempo iniziale di TimeControl, se
    c'e'. Vuoto se il PGN non ha orologi."""
    base = None
    incremento = 0
    controllo = re.fullmatch(r"(\d+)(?:\+(\d+))?", pgn_game.headers.get("TimeControl", "").strip())
    if controllo:
        base = int(controllo.group(1))
        incremento = int(controllo.group(2) or 0)
    tempi = {}
    ultimo = {chess.WHITE: base, chess.BLACK: base}
    for nodo in pgn_game.mainline():
        orologio = nodo.clock()
        if orologio is None:
            continue
        chi = not nodo.turn()
        if ultimo[chi] is not None and ultimo[chi] - orologio + incremento >= 0:
            tempi[nodo] = ultimo[chi] - orologio + incremento
        ultimo[chi] = orologio
    return tempi


ERRORI = ("Inesattezza", "Errore", "Svarione")


def _statistiche_nuove(lines, pgn_game, analizzate, nomi):
    """Le statistiche nuove del riepilogo, volute da Gabriele il 23 novembre
    2026: le mosse come il motore, la precisione per fase, i momenti
    decisivi e, se il PGN ha gli orologi, l'uso del tempo. nomi e'
    {colore: nome}."""
    per_colore = {colore: [mossa for mossa in analizzate if mossa["colore"] == colore] for colore in chess.COLORS}
    ordine = (chess.WHITE, chess.BLACK)
    if analizzate:
        lines.append(_("Mosse come il motore:"))
        for colore in ordine:
            mosse = per_colore[colore]
            if mosse:
                prima = sum(1 for mossa in mosse if mossa["rango"] == 0) / len(mosse) * 100
                tre = sum(1 for mossa in mosse if mossa["rango"] is not None and mossa["rango"] < 3) / len(mosse) * 100
                lines.append(
                    _("  {nome}: prima scelta {p1:.0f}%, fra le prime tre {p3:.0f}%, su {n} mosse.").format(
                        nome=nomi[colore], p1=prima, p3=tre, n=len(mosse)
                    )
                )
        lines.append(_("Precisione per fase:"))
        for colore in ordine:
            for fase in FASI:
                mosse = [mossa for mossa in per_colore[colore] if mossa["fase"] == fase]
                if mosse:
                    lines.append(
                        _("  {nome}, {fase}: precisione media {acc:.1f}%, perdita media {acpl:.0f} centesimi, su {n} mosse.").format(
                            nome=nomi[colore],
                            fase=_nome_della_fase(fase),
                            acc=statistics.mean(mossa["precisione"] for mossa in mosse),
                            acpl=statistics.mean(min(mossa["centipawn_loss"], 1000) for mossa in mosse),
                            n=len(mosse),
                        )
                    )

        def calo(mossa):
            return _vittoria_dal_lato_dei_valori(mossa, "vittoria_prima") - _vittoria_dal_lato_dei_valori(mossa, "vittoria_dopo")

        momenti = sorted((mossa for mossa in analizzate if calo(mossa) >= 1), key=calo, reverse=True)[:3]
        if momenti:
            lines.append(_("Momenti decisivi:"))
            for mossa in momenti:
                lines.append(
                    _("  {mossa}, {nome}: la probabilità di vittoria del Bianco passa dal {prima:.0f}% al {dopo:.0f}%.").format(
                        mossa=_nome_della_mossa(mossa["node"]), nome=nomi[mossa["colore"]], prima=mossa["vittoria_prima"], dopo=mossa["vittoria_dopo"]
                    )
                )
    tempi = _tempi_delle_mosse(pgn_game)
    if not tempi:
        return
    giudizi = {mossa["node"]: mossa["classification"] for mossa in analizzate}
    lines.append(_("Uso del tempo:"))
    for colore in ordine:
        suoi = {nodo: secondi for nodo, secondi in tempi.items() if nodo.turn() != colore}
        if not suoi:
            continue
        totale = sum(suoi.values())
        lines.append(
            _("  {nome}: in media {media} per mossa, {totale} in tutto.").format(
                nome=nomi[colore], media=tempo.parlato(totale / len(suoi)), totale=tempo.parlato(totale)
            )
        )
        lunghe = sorted(suoi.items(), key=lambda voce: voce[1], reverse=True)[:3]
        elenco = "; ".join(_("{mossa} in {durata}").format(mossa=_nome_della_mossa(nodo), durata=tempo.parlato(secondi)) for nodo, secondi in lunghe)
        lines.append(_("  {nome}, le mosse più lunghe: {elenco}.").format(nome=nomi[colore], elenco=elenco))
        sugli_errori = sum(secondi for nodo, secondi in suoi.items() if giudizi.get(nodo) in ERRORI)
        if sugli_errori and totale:
            # Il percento sta nel valore e non nella frase: "% del" e "% of"
            # Babel li prendeva per i segnaposto %d e %o, e il controllo dei
            # cataloghi falliva (issue 75).
            percentuale = f"{sugli_errori / totale * 100:.0f}%"
            lines.append(
                _("  {nome}: {tempo} sulle mosse giudicate inesattezza, errore o svarione, il {percentuale} del suo tempo.").format(
                    nome=nomi[colore], tempo=tempo.parlato(sugli_errori), percentuale=percentuale
                )
            )


def _vittoria_dal_lato_dei_valori(mossa, chiave):
    """La probabilita' di vittoria di chi ha mosso, dai valori del Bianco."""
    return mossa[chiave] if mossa["colore"] == chess.WHITE else 100 - mossa[chiave]


# Globali Motore
ENGINE = None
ENGINE_NAME = "Nessuno"
analysis_time = 1.0
multipv = 3
cache_analysis = {}
oaa_analysis_cache = {}
# La forza con cui il motore gioca contro l'utente in Easyfish. Le opzioni
# UCI restano impostate da una partita all'altra finche' il motore non si
# riavvia, quindi lo stato sta qui, accanto al motore, e InitEngine lo
# riporta al livello della configurazione. tipo vale "livello" per .s,
# "elo" per .e e "lichess" per .f; profondita' e' il limite di .p.
forza = {"tipo": "livello", "valore": 20, "profondita": None}


# I percorsi passano tutti da config: una sola definizione per l'intero
# progetto, altrimenti moduli diversi salvano in cartelle diverse.
percorso_salvataggio = config.percorso_salvataggio


def SetAnalysisTime(t):
    global analysis_time
    analysis_time = t
    cache_analysis.clear()


def SetMultipv(m):
    global multipv
    multipv = m
    cache_analysis.clear()


def SearchForEngine():
    """Cerca il motore UCI nel sistema. Restituisce (path, exe, False)"""
    if sys.platform == "win32":
        # Cartella usata dalle versioni vecchie: nessuna parte del
        # programma la crea piu', ma chi aggiorna da lontano puo' averla
        # ancora, quindi si continua a guardarci dentro.
        appdata_path = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Orologic", "Engine", "stockfish"
        )
        if os.path.exists(appdata_path):
            for f in os.listdir(appdata_path):
                if f.endswith(".exe"):
                    return appdata_path, f, False
    local_dir = percorso_salvataggio("engine")
    if os.path.exists(local_dir):
        # Anche nelle sottocartelle: l'archivio di Stockfish si estrae in
        # engine/stockfish, quindi guardando solo in engine non si trovava
        # nulla e il motore andava configurato a mano dopo ogni scaricamento.
        for radice, _cartelle, file in os.walk(local_dir):
            for f in sorted(file):
                if f.lower().endswith(".exe"):
                    return radice, f, False
    return None, None, False


def _configura_opzioni(cfg):
    """Imposta le opzioni del motore, saltando quelle che non conosce.

    Skill Level e' un'opzione di Stockfish: un altro motore UCI, che pure
    funzionerebbe benissimo, faceva fallire la configurazione in blocco e
    veniva scartato con un generico errore.
    """
    desiderate = {
        "Hash": cfg.get("hash_size", 128),
        "Threads": cfg.get("num_cores", 1),
        "Skill Level": cfg.get("skill_level", 20),
        # Fino alla 8.46.8 si chiedeva e si salvava, ma al motore non arrivava.
        "Move Overhead": cfg.get("move_overhead", 0),
    }
    conosciute = {n: v for n, v in desiderate.items() if n in ENGINE.options}
    ignorate = sorted(set(desiderate) - set(conosciute))
    if conosciute:
        ENGINE.configure(conosciute)
    if ignorate:
        print(
            _(
                "Il motore non conosce queste opzioni, che restano com'erano: {elenco}"
            ).format(elenco=", ".join(ignorate))
        )
    # Vittoria, patta e sconfitta in ogni analisi, per le linee e per Rendi
    # verbosa: prima le chiedeva solo l'inizio di una partita contro il
    # motore in Easyfish, e .a le dava solo dopo una partita (Gabriele,
    # collaudo del 23 novembre 2026). Un motore che non le conosce non le
    # da', senza avvisi.
    if "UCI_ShowWDL" in ENGINE.options:
        ENGINE.configure({"UCI_ShowWDL": True})


def InitEngine():
    global ENGINE, ENGINE_NAME, analysis_time, multipv
    CloseEngine()  # Chiudiamo sempre eventuali istanze precedenti per evitare processi orfani
    db = storage.LoadDB()

    # Parametri di analisi: storage garantisce che le chiavi esistano.
    analysis_time = db["default_analysis_time"]
    multipv = db["default_multipv"]

    cfg = db.get("engine_config", {})
    if not cfg:
        p, e, _unused_v = SearchForEngine()
        if not (p and e):
            ENGINE = None
            ENGINE_NAME = "Nessuno"
            return False
        cfg = {
            "hash_size": 128,
            "num_cores": 1,
            "skill_level": 20,
            "move_overhead": 0,
        }
        # Relativo alla cartella di Orologic, quando ci sta: prima si
        # salvava sempre assoluto, e spostando la cartella il motore non si
        # trovava piu' (R49).
        cfg["engine_path"], cfg["engine_is_relative"] = percorso_da_salvare(percorso_assoluto(os.path.join(p, e)))
        storage.SetValue("engine_config", cfg)

    percorso_configurato = cfg.get("engine_path", "")
    path = (
        percorso_salvataggio(percorso_configurato)
        if cfg.get("engine_is_relative")
        else percorso_configurato
    )
    if not os.path.exists(path):
        # Prima si taceva, e restava "motore non configurato" senza una
        # spiegazione: ora lo si dice, e lo si cerca di nuovo (R49). Una
        # volta per sessione: le due righe tornavano a ogni avvio del
        # motore (R131).
        detto = path in _MOTORI_MANCANTI_DETTI
        _MOTORI_MANCANTI_DETTI.add(path)
        if not detto:
            print(_("Il motore configurato non si trova piu': {p}. Lo cerco.").format(p=path))
        p, e, _unused_v = SearchForEngine()
        if not (p and e):
            if not detto:
                print(_("Nessun motore trovato: puoi sceglierlo dalle impostazioni."))
            ENGINE = None
            ENGINE_NAME = "Nessuno"
            return False
        path = percorso_assoluto(os.path.join(p, e))
        cfg = dict(cfg)
        cfg["engine_path"], cfg["engine_is_relative"] = percorso_da_salvare(path)
        storage.SetValue("engine_config", cfg)
    try:
        # Senza la sua finestra: dal pacchetto senza console, su Windows,
        # Stockfish ne aprirebbe una nera tutta sua.
        opzioni = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        ENGINE = chess.engine.SimpleEngine.popen_uci(path, **opzioni)
        _configura_opzioni(cfg)
        forza.update(
            tipo="livello", valore=cfg.get("skill_level", 20), profondita=None
        )
        ENGINE_NAME = ENGINE.id.get("name", "UCI Engine")
        print(_("Motore {n} pronto.").format(n=ENGINE_NAME))
        return True
    except (
        chess.engine.EngineError,
        chess.engine.EngineTerminatedError,
        OSError,
    ) as e:
        print(_("Errore motore: {e}").format(e=e))
        # Il motore partito ma non configurato si chiude: prima si
        # azzerava senza chiuderlo, e restava acceso (R49).
        CloseEngine()
        ENGINE = None
        return False


def forza_della_configurazione():
    """Il motore torna alla forza della configurazione, quella con cui
    analizza: dopo una partita restava alla forza dell'avversario, in
    carriera limitato all'Elo del modello, e l'analisi automatica del 23
    novembre 2026 ne usciva con valutazioni sbagliate, per esempio
    un'alternativa a +0.00 in una posizione persa. Si chiama all'inizio
    di ogni analisi; la partita dopo rimette la sua forza da se'."""
    if ENGINE is None:
        return
    livello = storage.LoadDB().get("engine_config", {}).get("skill_level", 20)
    opzioni = getattr(ENGINE, "options", {})
    try:
        if "UCI_LimitStrength" in opzioni:
            ENGINE.configure({"UCI_LimitStrength": False})
        if "Skill Level" in opzioni:
            ENGINE.configure({"Skill Level": livello})
    # Il motore e' un processo separato che puo' non rispondere: si
    # analizza con la forza che ha.
    except Exception:  # noqa: BLE001
        return
    forza.update(tipo="livello", valore=livello, profondita=None)


# I motori configurati che non si trovano piu', gia' detti in questa
# sessione (R131).
_MOTORI_MANCANTI_DETTI = set()


def CloseEngine():
    """Chiude il motore: quit, e poi close comunque, che chiude il processo
    anche quando quit non ha risposto. Prima un motore che non rispondeva
    teneva il processo e poteva restare orfano (R131)."""
    global ENGINE
    if ENGINE:
        motore, ENGINE = ENGINE, None
        try:
            motore.quit()
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError, OSError, TimeoutError):
            pass
        finally:
            # close su un motore gia' chiuso non ha niente da fare; su uno
            # che non ha risposto lo chiude. Nessun suo errore deve fermare
            # l'uscita.
            with contextlib.suppress(Exception):
                motore.close()


def interroga(board, limit, **opzioni):
    """ENGINE.analyse, con una ripresa: se il motore e' morto lo si riavvia
    una volta, e lo si dice. Prima nessun punto distingueva il motore morto
    da "nessuna analisi": ENGINE restava non nullo e non ripartiva mai,
    l'analisi automatica arrivava a "completata" con dati vuoti, e
    nell'analisi manuale e e w facevano cadere il programma (R41). Se non
    riparte, ENGINE resta None e l'errore sale."""
    if ENGINE is None:
        raise chess.engine.EngineTerminatedError(_("Il motore non c'e'."))
    try:
        return ENGINE.analyse(board, limit, **opzioni)
    # Anche il motore vivo che non risponde: prima il suo TimeoutError non
    # lo prendeva nessuno, e i comandi e e w cadevano (R131).
    except (chess.engine.EngineTerminatedError, TimeoutError):
        if not _riavviato():
            print(_("Il motore non riparte: niente analisi."))
            raise
        return ENGINE.analyse(board, limit, **opzioni)


def _riavviato():
    """Il motore morto si chiude e si riavvia, una volta, dicendolo: vero se
    e' ripartito; se no ENGINE resta None. Il tempo d'analisi e le linee
    restano quelli scelti: InitEngine li rimetteva ai predefiniti (R131)."""
    global ENGINE, analysis_time, multipv
    tempo, linee = analysis_time, multipv
    print(_("Il motore si e' fermato: lo riavvio."))
    CloseEngine()
    ENGINE = None
    if not InitEngine() or ENGINE is None:
        ENGINE = None
        return False
    analysis_time, multipv = tempo, linee
    return True


def motore_vivo():
    """Vero se il motore c'e' e risponde. Un motore morto resta non nullo, e
    la partita dopo cadeva sulla sua proprieta' id (R111)."""
    if ENGINE is None:
        return False
    try:
        ENGINE.ping()
    except (chess.engine.EngineError, TimeoutError, OSError):
        return False
    return True


def gioca_la_mossa(board, limit, rimetti_la_forza=None, **opzioni):
    """ENGINE.play con la ripresa di interroga: se il motore e' morto lo si
    riavvia una volta, e rimetti_la_forza(motore), se c'e', gli ridà la
    forza della partita prima di riprovare. Prima la partita contro il
    motore non passava da qui: usciva Errore motore, e la partita dopo
    cadeva (R111)."""
    if ENGINE is None:
        raise chess.engine.EngineTerminatedError(_("Il motore non c'e'."))
    try:
        return ENGINE.play(board, limit, **opzioni)
    except (chess.engine.EngineTerminatedError, TimeoutError):
        if not _riavviato():
            print(_("Il motore non riparte: la partita si ferma."))
            raise
        if rimetti_la_forza is not None:
            rimetti_la_forza(ENGINE)
        return ENGINE.play(board, limit, **opzioni)


class _MotoreVivo:
    """Il motore di Orologic per chi lo tiene a lungo, come Easyfish: ogni
    uso va al motore del momento, e analyse passa da interroga, che lo
    riavvia se e' morto. Prima Easyfish teneva il motore di quando era
    partito, anche morto (R41)."""

    def __bool__(self):
        return ENGINE is not None

    @staticmethod
    def analyse(board, limit, **opzioni):
        return interroga(board, limit, **opzioni)

    def __getattr__(self, nome):
        return getattr(ENGINE, nome)


MOTORE = _MotoreVivo()


# Il conteggio del materiale sta in board_utils: era ricopiato qui e in
# Easyfish, con tre tabelle di valori da tenere allineate.
CalculateMaterial = board_utils.CalculateMaterial


def _analizza_con_cache(board, linee):
    """Interroga il motore tenendo il risultato in cache.

    La chiave comprende il numero di linee richieste: indicizzando sul solo
    FEN, una valutazione a una linea gia' in cache faceva restituire una sola
    linea anche a chi ne aveva chieste tre, e le altre sparivano senza
    spiegazione. Tempo di analisi e numero di linee azzerano comunque la
    cache quando cambiano, quindi qui basta distinguere le linee.
    """
    if ENGINE is None:
        return None
    chiave = (board.fen(), linee)
    if chiave not in cache_analysis:
        try:
            cache_analysis[chiave] = interroga(board, chess.engine.Limit(time=analysis_time), multipv=linee)
        # Il motore morto, o che non risponde, e non ripartito l'ha gia'
        # detto interroga (R41, R131).
        except (chess.engine.EngineError, TimeoutError):
            return None
    return cache_analysis[chiave]


def CalculateEvaluation(board):
    if ENGINE is None:
        return None
    try:
        analysis_result = _analizza_con_cache(board, 1)
        if not analysis_result:
            return None
        return analysis_result[0].get("score")
    except chess.engine.EngineError:
        return None


def CalculateBest(board, bestmove=True, as_san=False):
    Acusticator(["e5", 0.008, -1, config.VOLUME])
    try:
        analysis = _analizza_con_cache(board, multipv)
        if not analysis:
            return None
        best_line = analysis[0].get("pv", [])
        if not best_line:
            return None
        if as_san:
            temp_board = board.copy()
            descriptive_moves = []
            move_number = 1
            i = 0
            while i < len(best_line):
                if temp_board.turn == chess.WHITE:
                    white_move = best_line[i]
                    white_descr = board_utils.DescribeMove(white_move, temp_board)
                    temp_board.push(white_move)
                    i += 1
                    move_descr = _("{num}.").format(num=move_number) + " " + white_descr
                    if i < len(best_line) and temp_board.turn == chess.BLACK:
                        black_move = best_line[i]
                        black_descr = board_utils.DescribeMove(black_move, temp_board)
                        temp_board.push(black_move)
                        i += 1
                        move_descr += ", " + black_descr
                    descriptive_moves.append(move_descr)
                    move_number += 1
                else:
                    black_move = best_line[i]
                    black_descr = board_utils.DescribeMove(black_move, temp_board)
                    temp_board.push(black_move)
                    i += 1
                    descriptive_moves.append(
                        _("{num}... {desc}").format(num=move_number, desc=black_descr)
                    )
                    move_number += 1
            score = analysis[0].get("score")
            mate_found = False
            subito = False
            if score is not None and score.relative.is_mate():
                mate_moves = abs(score.relative.mate())
                mate_found = True
                # Chi ha il tratto subisce il matto: lo si dice, invece
                # dello stesso "Matto in" di chi lo da' (R55).
                subito = score.relative.mate() < 0
            if bestmove:
                if mate_found:
                    Acusticator(["a6", 0.008, 1, config.VOLUME])
                    frase = _("Matto subito in {moves}, {first_move}") if subito else _("Matto in {moves}, {first_move}")
                    return [frase.format(moves=mate_moves, first_move=descriptive_moves[0])]
                else:
                    Acusticator(["f6", 0.008, 1, config.VOLUME])
                    return [descriptive_moves[0]]
            else:
                if mate_found:
                    frase = _("Matto subito in {moves}:") if subito else _("Matto in {moves}:")
                    descriptive_moves.insert(0, frase.format(moves=mate_moves))
                Acusticator(["d6", 0.008, 1, config.VOLUME])
                return descriptive_moves
        elif bestmove:
            Acusticator(["g5", 0.008, 1, config.VOLUME])
            return best_line[0]
        else:
            return best_line
    # L'analisi mette insieme motore, cache e calcoli: se qualcosa
    # non riesce si rinuncia alla linea migliore, senza fermare tutto.
    except Exception:  # noqa: BLE001
        return None


def CalculateWDL(board):
    if ENGINE is None:
        return None
    try:
        analysis_result = _analizza_con_cache(board, 1)
        if not analysis_result:
            return None
        score = analysis_result[0].get("score")
        if score and hasattr(score, "wdl"):
            wdl = score.wdl()
            return (wdl[0] / 10, wdl[1] / 10, wdl[2] / 10)
    # Come sopra: senza valutazione si prosegue lo stesso.
    except Exception:  # noqa: BLE001, S110
        pass
    return None


def SmartInspection(analysis_lines, board):
    print(_("Linee disponibili:"))
    for i, info in enumerate(analysis_lines, start=1):
        temp_board = board.copy()
        moves_with_numbers = []
        pv = info.get("pv", [])
        j = 0
        while j < len(pv):
            if temp_board.turn == chess.WHITE:
                move_num = temp_board.fullmove_number
                white_move = pv[j]
                white_san = temp_board.san(white_move)
                temp_board.push(white_move)
                move_str = f"{move_num}. {white_san}"
                if j + 1 < len(pv) and temp_board.turn == chess.BLACK:
                    black_move = pv[j + 1]
                    black_san = temp_board.san(black_move)
                    temp_board.push(black_move)
                    move_str += f" {black_san}"
                    j += 2
                else:
                    j += 1
                moves_with_numbers.append(move_str)
            else:
                move_num = temp_board.fullmove_number
                black_move = pv[j]
                black_san = temp_board.san(black_move)
                temp_board.push(black_move)
                moves_with_numbers.append(f"{move_num}... {black_san}")
                j += 1
        line_summary = " ".join(moves_with_numbers)
        print(_("Linea {num}: {summary}").format(num=i, summary=line_summary))
    choice = dgt(
        _("Quale linea vuoi ispezionare? (1/{num_lines}) ").format(
            num_lines=len(analysis_lines)
        ),
        kind="i",
        imin=1,
        imax=len(analysis_lines),
        default=1,
    )
    Acusticator(["e5", 0.06, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0])
    line_index = int(choice) - 1
    chosen_info = analysis_lines[line_index]
    pv_moves = chosen_info.get("pv", [])
    if not pv_moves:
        print(_("Linea vuota, termine ispezione."))
        return
    score = chosen_info.get("score")
    # Il matto subito col segno, -M3, come nel resto di Orologic: prima
    # usciva come quello dato (R55, R133).
    if score is not None and score.relative.is_mate():
        eval_str = board_utils.testo_del_matto(score.relative.mate())
    elif score is not None:
        cp = score.white().score()
        eval_str = f"{cp / 100:.2f}"
    else:
        eval_str = "0.00"
    total_moves = len(pv_moves)
    current_index = 1
    if not strato.con_la_plancia():
        print(_("\nUtilizza questi comandi:"))
        menu(config.SMART_COMMANDS, show_only=True, ordered=False)
    print(_("\nIspezione Linea {n}").format(n=line_index + 1))
    from . import cruscotto
    from .easyfish import posizione

    stato = posizione.Stato("analisi")
    stato.righe_in_piu = [_("Ispezione della linea {n}.").format(n=line_index + 1)]
    while True:
        temp_board = board.copy()
        for move in pv_moves[: current_index - 1]:
            temp_board.push(move)
        # Nella finestra: la posizione della linea e i comandi dell'ispezione.
        stato.scacchiera_del_cruscotto = temp_board.copy()
        strato.fornisci(lambda: cruscotto.dati_di(stato), config.SMART_COMMANDS)
        current_move = pv_moves[current_index - 1]
        move_verbose = board_utils.DescribeMove(current_move, temp_board)
        m_num = (
            f"{temp_board.fullmove_number}."
            if temp_board.turn == chess.WHITE
            else f"{temp_board.fullmove_number}..."
        )
        smart_prompt = _(
            "\n({current}/{total}) {move_num} {move_desc} CP: {cp}"
        ).format(
            current=current_index,
            total=total_moves,
            cp=eval_str,
            move_num=m_num,
            move_desc=move_verbose,
        )
        cmd = key(smart_prompt).lower().strip()
        if cmd == ".":
            break
        elif cmd == "s":
            if current_index > 1:
                current_index -= 1
            else:
                Acusticator(
                    ["c4", 0.1, -0.5, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]
                )
                print(_("\nNon ci sono mosse precedenti."))
        elif cmd == "?":
            Acusticator(["d5", 0.08, 0, config.VOLUME], kind=1, adsr=[2, 5, 90, 5])
            with strato.da_leggere(_("Comandi dell'ispezione smart")):
                menu(config.SMART_COMMANDS, show_only=True, ordered=False, pager=0 if strato.con_la_plancia() else 20)
        elif cmd == "r":
            temp_board = board.copy()
            try:
                for move in pv_moves[:current_index]:
                    temp_board.push(move)
            except (ValueError, AssertionError) as push_err:
                print(_("\nErrore: {error}").format(error=push_err))
                eval_str = "ERR_NAV"
                continue
            score_object_si = CalculateEvaluation(temp_board)
            Acusticator(["e5", 0.008, -1, config.VOLUME])
            if score_object_si is not None:
                new_eval_str = "N/A"
                pov_score_si = score_object_si.pov(temp_board.turn)
                if pov_score_si.is_mate():
                    new_eval_str = board_utils.testo_del_matto(pov_score_si.mate())
                else:
                    cp_si = score_object_si.white().score(mate_score=30000)
                    if cp_si is not None:
                        new_eval_str = f"{cp_si / 100:+.2f}"
                    else:
                        new_eval_str = "ERR"
                eval_str = new_eval_str
                Acusticator(["g5", 0.1, 0.3, config.VOLUME], kind=1, adsr=[5, 5, 90, 5])
                print(_("\nValutazione aggiornata."))
            else:
                Acusticator(["a3", 0.15, 0, config.VOLUME], kind=2, adsr=[5, 20, 0, 75])
                print(_("\nImpossibile aggiornare."))
                eval_str = "N/A"
        elif cmd == "d":
            if current_index < total_moves:
                current_index += 1
            else:
                Acusticator(
                    ["c4", 0.1, 0.5, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]
                )
                print(_("\nNon ci sono mosse successive."))
        else:
            Acusticator(["b3", 0.12, 0, config.VOLUME], kind=2, adsr=[5, 15, 20, 60])
            print(_("\nComando non riconosciuto."))


def LoadPGNFromClipboard():
    try:
        text = pyperclip.paste()
        if not text.strip():
            return None

        games, is_corrupted, is_corrected, err_msg, cleaned_text = (
            board_utils.validate_and_clean_pgn(text)
        )

        if is_corrupted:
            Acusticator(["d3", 0.5, 0, config.VOLUME], kind=3)
            print(_("\n[Errore] PGN non valido:"))
            print(err_msg)
            return None

        if is_corrected:
            pyperclip.copy(cleaned_text)
            print(
                _(
                    "\n[Info] Il PGN presentava lievi imperfezioni di layout ed e' stato corretto e aggiornato negli appunti."
                )
            )
            Acusticator(
                ["c5", 0.1, 0, config.VOLUME, "e5", 0.1, 0, config.VOLUME], kind=1
            )

        if not games:
            return None

        if len(games) == 1:
            return games[0], is_corrected

        partite = {
            i + 1: f"{g.headers.get('White')} vs {g.headers.get('Black')}"
            for i, g in enumerate(games)
        }
        c = menu(partite, p=_("Scegli partita: "), show=True, numbered=True)
        return (games[int(c) - 1], is_corrected) if c else None
    # Il PGN da analizzare arriva dagli appunti e puo' essere
    # qualsiasi cosa: si rinuncia e si torna al menu.
    except Exception:  # noqa: BLE001
        return None


_ANNOTAZIONI = ("z", "x", "c", "v", "n")
_INFORMATIVI = ("e", "u", "i", "o", "?")
_VALUTAZIONI = ("q", "w", "r", "t", "y")


def _comandi_annotazione(cmd, current_node):
    """Comandi che annotano il nodo: variante, commenti, valutazione.

    Restituisce vero se il nodo e' stato modificato, cioe' se c'e' qualcosa
    da salvare.
    """
    saved = False
    if cmd == "z":
        pv = CalculateBest(current_node.board(), bestmove=False, as_san=False)
        if pv:
            current_node.add_variation(pv[0]).add_line(pv[1:])
            saved = True
            print(_("\nVariante aggiunta."))
            Acusticator(
                [
                    "a5",
                    0.12,
                    0.3,
                    config.VOLUME,
                    "b5",
                    0.12,
                    0.3,
                    config.VOLUME,
                    "c6",
                    0.12,
                    0.3,
                    config.VOLUME,
                    "d6",
                    0.12,
                    0.3,
                    config.VOLUME,
                    "e6",
                    0.12,
                    0.3,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[4, 8, 85, 5],
            )
    elif cmd == "x":
        bm = CalculateBest(current_node.board(), as_san=True)
        if bm:
            board_utils.accoda_commento(
                current_node, _("[BM: {bm}]").format(bm=bm[0])
            )
            saved = True
            print(_("\nCommento aggiunto."))
            Acusticator(["a5", 0.1, 0, config.VOLUME], kind=1, adsr=[2, 5, 90, 5])
    elif cmd == "c":
        Acusticator(
            [
                "d6",
                0.012,
                0,
                config.VOLUME,
                "p",
                0.15,
                0,
                0,
                "a6",
                0.012,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[0.01, 0, 100, 0.01],
        )
        comm = dgt(_("\nInserisci il commento: "), kind="s").strip()
        if comm:
            current_node.comment = (current_node.comment or "").strip() + " " + comm
            saved = True
            Acusticator(
                [
                    "a6",
                    0.012,
                    0,
                    config.VOLUME,
                    "p",
                    0.15,
                    0,
                    0,
                    "d6",
                    0.012,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[0.01, 0, 100, 0.01],
            )
    elif cmd == "v":
        score = CalculateEvaluation(current_node.board())
        if score:
            board_utils.accoda_commento(
                current_node,
                _("[Val: {ev}]").format(ev=board_utils.testo_valutazione(score)),
            )
            saved = True
            print(_("\nValutazione commentata."))
            Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1, adsr=[2, 5, 90, 5])
    elif cmd == "n":
        if current_node.comment:
            if ui.enter_escape(_("\nEliminare il commento? (INVIO si', ESC no): ")):
                current_node.comment = ""
                saved = True
                print(_("\nCommento eliminato."))
                Acusticator(
                    ["e4", 0.1, -0.4, config.VOLUME], kind=1, adsr=[5, 10, 70, 15]
                )
    return saved


def _comandi_informativi(cmd, current_node):
    """Comandi che si limitano a mostrare qualcosa o a regolare il motore.

    Non toccano ne' la partita ne' lo stato del ciclo.
    """
    if cmd == "e":
        if ENGINE:
            print(_("\nAnalisi in corso..."))
            analysis = _analizza_con_cache(current_node.board(), multipv)
            with strato.da_leggere(_("Linee di analisi")):
                for i, info in enumerate(analysis or []):
                    pv = info.get("pv", [])
                    valutazione = info.get("score")
                    if valutazione is None:
                        continue
                    score = valutazione.pov(current_node.board().turn)
                    san_moves = []
                    temp_board = current_node.board().copy()
                    for m in pv:
                        san_moves.append(temp_board.san(m))
                        temp_board.push(m)
                    san_pv = " ".join(san_moves)
                    print(_("Linea {i} ({s}): {pv}").format(i=i + 1, s=score, pv=san_pv))
            if not analysis:
                print(_("\nNessuna linea di analisi."))
            elif ui.enter_escape(_("\nIspezione smart? (INVIO si', ESC no): ")):
                SmartInspection(analysis, current_node.board())
    elif cmd == "u":
        with strato.da_leggere(_("Scacchiera")):
            print("\n" + str(board_utils.CustomBoard(current_node.board().fen())))
        Acusticator(["d6", 0.03, 0, config.VOLUME], kind=1)
    elif cmd == "i":
        new_t = dgt(_("\nTempo analisi (s): "), kind="f", default=analysis_time)
        SetAnalysisTime(new_t)
    elif cmd == "o":
        new_m = dgt(_("\nLinee analisi: "), kind="i", default=multipv)
        SetMultipv(new_m)
    elif cmd == "?":
        with strato.da_leggere(_("Comandi dell'analisi")):
            print(_("\nComandi disponibili:"))
            menu(config.ANALYSIS_COMMANDS, show_only=True, ordered=False, pager=0 if strato.con_la_plancia() else 20)


def _comandi_valutazione(cmd, current_node):
    """Comandi che scrivono la valutazione nel prompt.

    Restituisce il testo da anteporre al prompt, vuoto se non c'e' nulla da
    mostrare. Il ciclo azzera comunque il prompt supplementare a ogni giro.
    """
    extra_prompt = ""
    if cmd == "q":
        res = CalculateBest(current_node.board(), as_san=True)
        if res:
            extra_prompt = f" BM: {res[0]} "
            Acusticator(["f6", 0.02, 0, config.VOLUME], kind=1)
    elif cmd == "w":
        if ENGINE:
            print(_("\nCalcolo bestline..."))
            analysis = _analizza_con_cache(current_node.board(), multipv)
            if analysis:
                Acusticator(
                    [
                        "f6",
                        0.02,
                        0,
                        config.VOLUME,
                        "p",
                        0.15,
                        0,
                        0,
                        "a6",
                        0.02,
                        0,
                        config.VOLUME,
                        "p",
                        0.15,
                        0,
                        0,
                        "c7",
                        0.02,
                        0,
                        config.VOLUME,
                        "p",
                        0.15,
                        0,
                        0,
                        "e7",
                        0.02,
                        0,
                        config.VOLUME,
                        "p",
                        0.15,
                        0,
                        0,
                        "g7",
                        0.02,
                        0,
                        config.VOLUME,
                        "p",
                        0.15,
                        0,
                        0,
                        "b7",
                        0.02,
                        0,
                        config.VOLUME,
                    ],
                    kind=1,
                )
                with strato.da_leggere(_("Linee migliori")):
                    print(_("\nLinee migliori:"))
                    for i, info in enumerate(analysis, start=1):
                        pv = info.get("pv", [])
                        valutazione = info.get("score")
                        if valutazione is None:
                            continue
                        score = valutazione.pov(current_node.board().turn)
                        eval_str = (
                            board_utils.testo_del_matto(score.mate())
                            if score.is_mate()
                            else f"{score.score() / 100:+.2f}"
                            if score.score() is not None
                            else _("N/A")
                        )
                        print(_("Linea {i} ({score}):").format(i=i, score=eval_str))
                        print(board_utils.format_pv_descriptively(current_node.board(), pv))

                if analysis[0].get("pv"):
                    bm_san = current_node.board().san(analysis[0]["pv"][0])
                    score = analysis[0].get("score").pov(current_node.board().turn)
                    eval_str = (
                        board_utils.testo_del_matto(score.mate())
                        if score.is_mate()
                        else f"{score.score() / 100:+.2f}"
                        if score.score() is not None
                        else _("N/A")
                    )
                    extra_prompt = _(" BM: {score} {san} ").format(
                        score=eval_str, san=bm_san
                    )
            else:
                Acusticator(
                    ["a#3", 0.15, 0.5, config.VOLUME], kind=2, adsr=[5, 20, 0, 75]
                )
                print(_("\nImpossibile calcolare la bestline."))
                extra_prompt = _(" BM: N/A ")
        else:
            print(_("\nMotore non inizializzato."))
            Acusticator(["a#3", 0.15, 0.5, config.VOLUME], kind=2, adsr=[5, 20, 0, 75])
    elif cmd == "r":
        score = CalculateEvaluation(current_node.board())
        if score:
            ev = score.white().score(mate_score=30000)
            extra_prompt = _(" CP: {ev:+.2f} ").format(ev=ev / 100)
            Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1, adsr=[2, 5, 90, 5])
    elif cmd == "t":
        wdl = CalculateWDL(current_node.board())
        if wdl:
            extra_prompt = _(" W:{w:.1f}% D:{d:.1f}% L:{l:.1f}% ").format(
                w=wdl[0], d=wdl[1], l=wdl[2]
            )
            Acusticator(["g#5", 0.03, 0, config.VOLUME], kind=1)
    elif cmd == "y":
        w, b = CalculateMaterial(current_node.board())
        extra_prompt = _(" Mtrl: {w}/{b} ").format(w=w, b=b)
        Acusticator(["g#5", 0.03, 0, config.VOLUME], kind=1)
    return extra_prompt


def AnalyzeGame(pgn_game, is_corrected=False):
    forza_della_configurazione()
    print(_("\nModalita' analisi.\nHeaders della partita:\n"))
    for k, v in pgn_game.headers.items():
        print(f"  {k}: {v}")
    _analisi_manuale(pgn_game, is_corrected)


@strato.in_partita
def _analisi_manuale(pgn_game, is_corrected):
    """Il ciclo dell'analisi manuale. Nella finestra e' una zona di partita,
    come l'esploratore di Easyfish (9.4.1, 25 novembre 2026: era rimasta
    fuori dalla versione 9): il cruscotto con la posizione, i comandi
    nella plancia, e i testi lunghi in una finestra da leggere. Nel
    terminale tutto come prima."""
    from . import cruscotto
    from .easyfish import posizione

    stato = posizione.Stato("analisi")
    current_node = pgn_game
    extra_prompt = ""
    comment_auto_read = True
    saved = is_corrected
    total_moves = len(list(pgn_game.mainline_moves()))

    while True:
        prompt_move_part = _("Start")
        if current_node.move:
            move_san = current_node.san()
            parent_board = current_node.parent.board()
            fullmove = parent_board.fullmove_number
            move_indicator = (
                f"{fullmove}. {move_san}"
                if parent_board.turn == chess.WHITE
                else f"{fullmove}... {move_san}"
            )

            if current_node.parent and len(current_node.parent.variations) > 1:
                siblings = current_node.parent.variations
                try:
                    idx = siblings.index(current_node)
                    if idx == 0 and len(siblings) > 1:
                        prompt_move_part = f"<{move_indicator}"
                    elif idx > 0 and idx < len(siblings) - 1:
                        prompt_move_part = f"<{move_indicator}>"
                    elif idx > 0 and idx == len(siblings) - 1:
                        prompt_move_part = f"{move_indicator}>"
                    else:
                        prompt_move_part = move_indicator
                except ValueError:
                    prompt_move_part = move_indicator
            else:
                prompt_move_part = move_indicator

        if current_node.move and current_node.comment and not comment_auto_read:
            prompt_move_part += "-"

        prompt = f"\n{extra_prompt} {prompt_move_part}: "
        extra_prompt = ""

        if current_node.comment and comment_auto_read:
            # Il commento senza i comandi fra quadre del PGN, e i disegni
            # detti a parole: prima uscivano i codici, come [%cal Ge2e4]
            # (Gabriele, 23 novembre 2026).
            from .easyfish import posizione

            commento = posizione.testo_del_commento(current_node.comment)
            if commento:
                print(_("Commento:"), commento)
            disegni = posizione.testo_dei_disegni(current_node)
            if disegni:
                print(disegni)
        elif current_node.comment and not comment_auto_read:
            Acusticator(["c7", 0.024, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0])

        # Nella finestra: la posizione nel cruscotto, i comandi nella plancia.
        stato.aggiorna(pgn_game, current_node.board(), current_node)
        strato.fornisci(lambda: cruscotto.dati_di(stato), config.ANALYSIS_COMMANDS)
        cmd = key(prompt).lower().strip()
        previous_node = current_node
        node_changed = False

        if cmd == ".":
            break
        elif cmd == "a":  # Inizio o nodo padre
            node = current_node
            while node.parent is not None and node == node.parent.variations[0]:
                node = node.parent
            if node.parent is None:
                if node.variations and current_node != node.variations[0]:
                    current_node = node.variations[0]
                else:
                    Acusticator(
                        ["c4", 0.1, -0.5, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]
                    )
                    print(_("\nGia' all'inizio della partita."))
            else:
                current_node = node
            node_changed = current_node != previous_node
        elif cmd == "s":  # Indietro
            if current_node.parent:
                current_node = current_node.parent
                Acusticator(
                    ["g5", 0.03, -0.2, config.VOLUME, "c5", 0.03, -0.8, config.VOLUME],
                    kind=1,
                    adsr=[2, 5, 90, 5],
                )
            else:
                Acusticator(
                    ["c4", 0.1, -0.7, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]
                )
                print(_("\nNessuna mossa precedente."))
            node_changed = current_node != previous_node
        elif cmd == "d":  # Avanti
            if current_node.variations:
                current_node = current_node.variations[0]
                Acusticator(
                    ["c5", 0.03, 0.2, config.VOLUME, "g5", 0.03, 0.8, config.VOLUME],
                    kind=1,
                    adsr=[2, 5, 90, 5],
                )
            else:
                Acusticator(
                    ["c4", 0.1, 0.7, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]
                )
                print(_("\nNon ci sono mosse successive."))
            node_changed = current_node != previous_node
        elif cmd == "f":  # Fine linea
            start = current_node
            while current_node.variations:
                current_node = current_node.variations[0]
            node_changed = current_node != start
            if node_changed:
                Acusticator(
                    [
                        "g5",
                        0.1,
                        0,
                        config.VOLUME,
                        "p",
                        0.1,
                        0,
                        0,
                        "c6",
                        0.05,
                        0,
                        config.VOLUME,
                        "d6",
                        0.05,
                        0,
                        config.VOLUME,
                        "g6",
                        0.2,
                        0,
                        config.VOLUME,
                    ],
                    kind=1,
                    adsr=[5, 5, 90, 5],
                )
                print(_("Sei arrivato alla fine della linea principale."))
            else:
                print(_("Gia' alla fine della linea principale."))
        elif cmd == "g":  # Variante precedente
            if current_node.parent:
                vars = current_node.parent.variations
                try:
                    idx = vars.index(current_node)
                    if idx > 0:
                        current_node = vars[idx - 1]
                        Acusticator(
                            ["d#5", 0.07, -0.4, config.VOLUME],
                            kind=1,
                            adsr=[2, 5, 90, 5],
                        )
                    else:
                        Acusticator(
                            ["c#4", 0.1, -0.6, config.VOLUME],
                            kind=2,
                            adsr=[10, 10, 30, 50],
                        )
                        print(_("Non ci sono varianti precedenti."))
                except ValueError:
                    print(_("Errore: nodo corrente non trovato."))
            else:
                print(_("Nessun nodo variante disponibile (sei alla radice)."))
            node_changed = current_node != previous_node
        elif cmd == "h":  # Variante successiva
            if current_node.parent:
                vars = current_node.parent.variations
                try:
                    idx = vars.index(current_node)
                    if idx < len(vars) - 1:
                        current_node = vars[idx + 1]
                        Acusticator(
                            ["f5", 0.07, 0.4, config.VOLUME], kind=1, adsr=[2, 5, 90, 5]
                        )
                    else:
                        Acusticator(
                            ["c#4", 0.1, 0.6, config.VOLUME],
                            kind=2,
                            adsr=[10, 10, 30, 50],
                        )
                        print(_("Non ci sono varianti successive."))
                except ValueError:
                    print(_("Errore: nodo corrente non trovato."))
            else:
                print(_("Nessun nodo variante disponibile (sei alla radice)."))
            node_changed = current_node != previous_node
        elif cmd == "j":  # Headers
            Acusticator(
                [
                    "d5",
                    0.08,
                    0,
                    config.VOLUME,
                    "p",
                    0.08,
                    0,
                    0,
                    "d6",
                    0.06,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 5, 90, 5],
            )
            with strato.da_leggere(_("Header della partita")):
                print(_("\nHeader della partita:"))
                for k, v in pgn_game.headers.items():
                    print(f"  {k}: {v}")
        elif cmd == "k":  # Vai a mossa
            Acusticator(
                [
                    "g3",
                    0.06,
                    0,
                    config.VOLUME,
                    "b3",
                    0.06,
                    0,
                    config.VOLUME,
                    "a3",
                    0.06,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[0, 0, 100, 0],
            )
            # Le mosse di adesso: z puo' averne aggiunte in fondo alla linea
            # principale, e il conto fatto all'inizio non le vedeva (R131).
            total_moves = len(list(pgn_game.mainline_moves()))
            max_m = (total_moves + 1) // 2
            # Senza mosse dgt riceveva un intervallo da 1 a 0 e cadeva (R42).
            if max_m < 1:
                print(_("\nLa partita non ha mosse."))
                continue
            target = dgt(
                _("\nVai a mossa n.# (Max {m}): ").format(m=max_m),
                kind="i",
                imin=1,
                imax=max_m,
            )
            target_ply = max(0, 2 * (target - 1))
            found = pgn_game
            for i, node in enumerate(pgn_game.mainline()):
                if i == target_ply:
                    found = node
                    break
            else:
                if target_ply > 0:
                    print(
                        _(
                            "\nRaggiunta la fine della linea prima della mossa richiesta."
                        )
                    )
            current_node = found
            Acusticator(
                [
                    "g6",
                    0.06,
                    0,
                    config.VOLUME,
                    "b6",
                    0.06,
                    0,
                    config.VOLUME,
                    "a6",
                    0.06,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[0, 0, 100, 0],
            )
            node_changed = current_node != previous_node
        elif cmd == "l":  # Carica
            res = LoadPGNFromClipboard()
            if res:
                new_game, is_corrected = res
                pgn_game = new_game
                current_node = pgn_game
                node_changed = False
                saved = is_corrected
                total_moves = len(list(pgn_game.mainline_moves()))
                Acusticator(["c6", 0.15, 0, config.VOLUME], kind=1, adsr=[5, 10, 80, 5])
                print(_("\nNuovo PGN caricato."))
                [print(f"  {k}: {v}") for k, v in pgn_game.headers.items()]

        elif cmd in _ANNOTAZIONI:
            saved = _comandi_annotazione(cmd, current_node) or saved
        elif cmd in _INFORMATIVI:
            _comandi_informativi(cmd, current_node)
        elif cmd in _VALUTAZIONI:
            extra_prompt = _comandi_valutazione(cmd, current_node)
        elif cmd == "b":  # Toggle commenti
            comment_auto_read = not comment_auto_read
            if comment_auto_read:
                Acusticator(
                    [
                        "g5",
                        0.025,
                        0,
                        config.VOLUME,
                        "p",
                        0.04,
                        0,
                        0,
                        "b6",
                        0.035,
                        0,
                        config.VOLUME,
                    ],
                    kind=1,
                )
                print(_("\nLettura automatica abilitata."))
            else:
                Acusticator(
                    [
                        "g5",
                        0.025,
                        0,
                        config.VOLUME,
                        "p",
                        0.04,
                        0,
                        0,
                        "b4",
                        0.035,
                        0,
                        config.VOLUME,
                    ],
                    kind=1,
                )
                print(_("\nLettura automatica disabilitata."))
        else:
            Acusticator(["d3", 0.5, 0, config.VOLUME], kind=3)

        if node_changed and current_node.move:
            print(
                "\n"
                + board_utils.DescribeMove(
                    current_node.move, current_node.parent.board()
                )
            )

    if saved:
        try:
            formatted_pgn = board_utils.format_pgn_comments(str(pgn_game))
            pyperclip.copy(formatted_pgn)
            print(_("PGN aggiornato negli appunti."))
        except (pyperclip.PyperclipException, OSError):
            pass


def analyze_position_deep(board, limit, multipv_count=3):
    fen = board.fen()
    cache_key = f"{fen}_{limit.time}_{limit.depth}_{limit.nodes}_{multipv_count}"
    if cache_key in oaa_analysis_cache:
        return oaa_analysis_cache[cache_key]
    try:
        info = interroga(board, limit, multipv=multipv_count)
        results = []
        for i, analysis in enumerate(info):
            score = analysis.get("score")
            pv = analysis.get("pv")
            if score is not None and pv:
                results.append({"rank": i + 1, "move": pv[0], "score": score, "pv": pv})
        oaa_analysis_cache[cache_key] = results
        return results
    # L'interrogazione del motore puo' fallire in molti modi, e in
    # mezzo c'e' anche la conversione delle linee: senza analisi si prosegue.
    except Exception:  # noqa: BLE001
        return None


def _stampa_albero_pgn(
    node,
    data_map,
    lines,
    w_name,
    b_name,
    num_var,
    classification_labels,
    indent_level=0,
):
    """
    Funzione ricorsiva per stampare l'albero delle varianti nel file TXT.
    Output verboso, accessibile e con valutazioni ASSOLUTE (dal punto di vista del Bianco).
    """
    if not node.variations:
        return

    # La prima variazione è sempre la mossa principale
    main_move_node = node.variations[0]

    # --- FORMATTAZIONE MOSSA PRINCIPALE ---
    move_desc = board_utils.DescribeMove(main_move_node.move, node.board())

    res = data_map.get(main_move_node, {})
    classif = res.get("classification", "")
    eval_val = res.get("eval_after_move", "")  # Score object
    cpl = res.get("centipawn_loss", 0)

    # 3. Formattazione Valutazione (ASSOLUTA: Riferita al BIANCO). Il matto
    # si conta dopo la mossa e dice chi lo da': prima usciva Matto in -3.
    eval_str = ""
    if eval_val:
        matto = _matto_dopo(eval_val, node.board().turn)
        if matto is not None:
            eval_str = _maiuscola(matto)
        else:
            cp_val = eval_val.white().score(mate_score=30000)
            if cp_val is not None:
                eval_str = f"{cp_val / 100:+.2f}"  # Es. +0.33 (vantaggio bianco), -0.50 (vantaggio nero)

    # 4. Costruzione Riga
    prefix = " " * (indent_level * 2)
    move_num = node.board().fullmove_number
    dot = "." if node.board().turn == chess.WHITE else "..."

    line_content = f"{move_num}{dot} {move_desc}"

    details = []
    if eval_str:
        details.append(_("Val: {v}").format(v=eval_str))
    if cpl > 0:
        details.append(_("CPL: {c:.2f}").format(c=cpl / 100))

    if details:
        line_content += " ({})".format(", ".join(details))

    if classif:
        label = classification_labels.get(classif, classif)
        line_content += f" [{label}]"

    lines.append(f"{prefix}{line_content}")

    # Commenti
    raw_comment = main_move_node.comment
    if raw_comment:
        clean_comment = re.sub(r"\[OAA\s*:.*?\]", "", raw_comment).strip()
        if clean_comment:
            lines.append(_("{p}  Note: {c}").format(p=prefix, c=clean_comment))

    # --- GESTIONE VARIANTI ALTERNATIVE ---
    if len(node.variations) > 1:
        for i, variation in enumerate(node.variations[1:], start=1):
            var_prefix = " " * ((indent_level + 1) * 2)
            lines.append(_("{p}(Variante {i}):").format(p=var_prefix, i=i))

            var_move_desc = board_utils.DescribeMove(variation.move, node.board())
            var_move_num = node.board().fullmove_number
            var_dot = "." if node.board().turn == chess.WHITE else "..."

            var_info = ""
            # Il marcatore anche alla francese, [OAA : ...] con lo spazio.
            if variation.comment:
                match = re.search(r"\[OAA\s*:\s*(.*?)\]", variation.comment)
                if match:
                    var_info = f" [{match.group(1)}]"

            lines.append(
                f"{var_prefix}  {var_move_num}{var_dot} {var_move_desc}{var_info}"
            )

            _stampa_albero_pgn(
                variation,
                data_map,
                lines,
                w_name,
                b_name,
                num_var,
                classification_labels,
                indent_level + 2,
            )

        # Stella: Se torniamo alla mainline (indentazione 0), aggiungiamo un avviso per l'accessibilità
        if indent_level == 0 and main_move_node.variations:
            lines.append(_("Linea principale:"))

    # --- CONTINUAZIONE MAINLINE ---
    _stampa_albero_pgn(
        main_move_node,
        data_map,
        lines,
        w_name,
        b_name,
        num_var,
        classification_labels,
        indent_level,
    )


def genera_sommario_analitico_txt(
    pgn_game,
    base_f,
    results,
    stats,
    cpl_d,
    eco,
    skip,
    n_var,
    duration,
    engine_metadata=None,
    accuracies=None,
):
    l10n_analysis = localizzazione.L10N.get("analysis", {})
    classification_labels = {
        "Svarione": l10n_analysis.get("blunder", _("Svarione")),
        "Errore": l10n_analysis.get("mistake", _("Errore")),
        "Inesattezza": l10n_analysis.get("inaccuracy", _("Inesattezza")),
        "Mossa Buona": l10n_analysis.get("good", _("Mossa Buona")),
        "Mossa Geniale": l10n_analysis.get("brilliant", _("Mossa Geniale")),
        "Mossa Normale": l10n_analysis.get("normal", _("Mossa Normale")),
        "Teoria": l10n_analysis.get("book", _("Teoria")),
    }
    now_str = config.format_date_italian()
    lines = [
        _("Orologic Analisi Automatica [OAA] V.{v}").format(v=version.VERSION),
        _("Generato il: {d}").format(d=now_str),
        "",
    ]

    if engine_metadata:
        lines.append(_("Motore utilizzato:"))
        lines.append(_("  Nome: {n}").format(n=engine_metadata.get("name", _("N/A"))))
        lines.append(
            _("  Autore: {a}").format(a=engine_metadata.get("author", _("N/A")))
        )
        if "options" in engine_metadata:
            opts = engine_metadata["options"]
            lines.append(
                _("  Configurazione: Hash={h}MB, Threads={t}, Livello={s}").format(
                    h=opts.get("Hash", "?"),
                    t=opts.get("Threads", "?"),
                    s=opts.get("Skill Level", "?"),
                )
            )
        lines.append("")

    # Dati Partita (Tutti gli headers)
    for h_key, val in pgn_game.headers.items():
        lines.append(f"{h_key}: {val}")

    # Risultato esplicito (per accessibilità rapida)
    res = pgn_game.headers.get("Result", "*")
    esito_str = _("Sconosciuto")
    if res == "1-0":
        esito_str = _("Vince il Bianco")
    elif res == "0-1":
        esito_str = _("Vince il Nero")
    elif res == "1/2-1/2":
        esito_str = _("Patta")
    lines.append(_("Esito: {e}").format(e=esito_str))

    lines.append("")

    # Info Analisi
    if skip > 0:
        lines.append(
            _(
                "Nota: Le prime {s} semimosse (apertura) sono state escluse dall'analisi."
            ).format(s=skip)
        )
    lines.append(
        _("Durata Analisi: {m}m {s}s").format(
            m=int(duration // 60), s=int(duration % 60)
        )
    )

    lines.append("")
    lines.append(_("Statistiche:"))
    w_n = pgn_game.headers.get("White", _("Bianco"))
    b_n = pgn_game.headers.get("Black", _("Nero"))

    def calc_avg(val_list):
        return sum(val_list) / len(val_list) if val_list else 0

    lines.append(_("Precisione (ACPL - piu' basso e' meglio):"))
    lines.append(f"  {w_n}: {calc_avg(cpl_d['w']):.2f}")
    lines.append(f"  {b_n}: {calc_avg(cpl_d['b']):.2f}")

    # La precisione come Lichess, dalle mosse analizzate: la teoria no.
    analizzate = [risultato for risultato in results if "precisione" in risultato]
    precisioni = precisione_della_partita(analizzate)
    acc_w, acc_b = precisioni[chess.WHITE], precisioni[chess.BLACK]
    if analizzate:
        lines.append(_("Precisione Stimata (0-100%):"))
        for nome, precisione in ((w_n, acc_w), (b_n, acc_b)):
            if precisione is not None:
                da, a = intervallo_elo(precisione)
                lines.append(_("  {nome}: {acc:.1f}%, Elo stimato fra {da} e {a}").format(nome=nome, acc=precisione, da=da, a=a))

    lines.append(_("Errori commessi:"))
    for t in ["Mossa Geniale", "Mossa Buona", "Inesattezza", "Errore", "Svarione"]:
        s = stats.get(t, {"w": 0, "b": 0})
        if s["w"] > 0 or s["b"] > 0:
            lines.append(
                _("  {t}: {w_name}={w_val}, {b_name}={b_val}").format(
                    t=classification_labels[t],
                    w_name=w_n,
                    w_val=s["w"],
                    b_name=b_n,
                    b_val=s["b"],
                )
            )

    _statistiche_nuove(lines, pgn_game, analizzate, {chess.WHITE: w_n, chess.BLACK: b_n})

    lines.append("")
    lines.append(_("Dettaglio Analisi:"))

    # Mappa i risultati
    data_map = {r["node"]: r for r in results if "node" in r}

    # Stampa Albero
    _stampa_albero_pgn(
        pgn_game, data_map, lines, w_n, b_n, n_var, classification_labels
    )

    # Footer
    lines.append("")
    lines.append(_("Riepilogo Partita"))
    lines.append(_("Esito Finale: {e}").format(e=esito_str))
    if acc_w is not None and acc_b is not None:
        lines.append(
            _("Precisione: {w} ({a_w:.1f}%) vs {b} ({a_b:.1f}%)").format(
                w=w_n, a_w=acc_w, b=b_n, a_b=acc_b
            )
        )
    lines.append(_("Fine Analisi Orologic V.{v}").format(v=version.VERSION))

    # Salvataggio
    f_p = percorso_salvataggio(
        os.path.join("txt", config.sanitize_filename(base_f) + ".txt")
    )
    os.makedirs(os.path.dirname(f_p), exist_ok=True)
    try:
        full_text = "\n".join(lines)
        with open(f_p, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(_("Riepilogo testuale salvato in: {p}").format(p=f_p))
        try:
            pyperclip.copy(full_text)
            print(_("Riepilogo copiato negli appunti."))
        # La copia negli appunti e' un di piu': se non riesce, pazienza.
        except Exception:  # noqa: BLE001, S110
            pass
    # Il riepilogo testuale e' un di piu' rispetto al PGN gia' salvato.
    except Exception as e:  # noqa: BLE001
        print(_("Errore salvataggio TXT: {e}").format(e=e))
        return None
    return f_p


def _parametri_analisi_automatica(pgn_game, db):
    """Chiede all'utente i parametri dell'analisi automatica.

    Restituisce varianti, limite, troncamento, semimosse da saltare e
    l'ultima apertura riconosciuta. Restituisce nulla se la modalita'
    scelta non e' valida, cioe' se l'analisi va annullata.
    """
    num_varianti = dgt(
        _("Varianti [{v}]: ").format(v=multipv),
        kind="i",
        imin=1,
        imax=10,
        default=multipv,
    )

    print(_("\nImpostazione dei parametri di analisi:"))
    analysis_mode_map = {
        "t": _("Tempo per mossa (secondi)"),
        "p": _("Profondita' fissa (ply)"),
        "n": _("Numero di nodi per mossa"),
    }
    analysis_mode = menu(
        analysis_mode_map,
        show=True,
        keyslist=True,
        ntf=_("Scelta non valida: "),
        numbered=db.get("menu_numerati", False),
    )
    limit = None
    if analysis_mode == "t":
        value = dgt(
            _("Inserisci i secondi per mossa: [INVIO per 1] "),
            kind="f",
            fmin=0.1,
            fmax=60,
            default=1,
        )
        limit = chess.engine.Limit(time=value)
    elif analysis_mode == "p":
        value = dgt(
            _("Inserisci la profondita' di analisi: [INVIO per 18] "),
            kind="i",
            imin=5,
            imax=50,
            default=18,
        )
        limit = chess.engine.Limit(depth=value)
    elif analysis_mode == "n":
        value = dgt(
            _(
                "Inserisci il numero di nodi da analizzare (in migliaia): [INVIO per 25] "
            ),
            kind="i",
            imin=5,
            imax=99999,
            default=25,
        )
        limit = chess.engine.Limit(nodes=value * 1000)
    else:
        print(_("Scelta non valida. Analisi annullata."))
        return

    truncate_length = dgt(
        _("Tronca varianti a (0=intere) [0]: "), kind="i", imin=0, imax=50, default=0
    )

    mosse_da_saltare = 0
    last_valid_eco_entry = None
    if ui.enter_escape(
        _(
            "Vuoi saltare automaticamente le mosse di apertura note? (INVIO per si', ESC per specificare manualmente): "
        )
    ):
        print(_("Rilevo la fine della teoria d'apertura..."))
        eco_db = board_utils.LoadEcoDatabaseWithFEN("eco.pgn")
        if eco_db:
            # La ricerca guarda tutta l'apertura e tiene la linea piu'
            # specifica: prima si fermava alla prima posizione mancante e
            # assegnava un codice piu' generico del dovuto.
            last_valid_eco_entry, mosse_da_saltare = board_utils.rileva_apertura(
                list(pgn_game.mainline_moves()), eco_db
            )
            if isinstance(last_valid_eco_entry, dict):
                opening_name = last_valid_eco_entry.get(
                    "opening", _("Nome non trovato")
                )
                print(_("Trovata apertura: {name}").format(name=opening_name))
            print(
                _("L'analisi saltera' le prime {n} semimosse.").format(
                    n=mosse_da_saltare
                )
            )
    else:
        mosse_da_saltare = dgt(
            _("Quante semimosse iniziali vuoi saltare? (INVIO per {n}) ").format(
                n=mosse_da_saltare
            ),
            kind="i",
            imin=0,
            imax=40,
            default=mosse_da_saltare,
        )
    return (
        num_varianti,
        limit,
        truncate_length,
        mosse_da_saltare,
        last_valid_eco_entry,
    )


def _dati_motore(db):
    """Nome, autore e opzioni del motore, per il rapporto finale."""
    engine_metadata = {}
    if ENGINE:
        engine_metadata["name"] = ENGINE.id.get("name", _("Sconosciuto"))
        engine_metadata["author"] = ENGINE.id.get("author", _("Sconosciuto"))

        cfg = db.get("engine_config", {})
        engine_metadata["options"] = {
            "Hash": cfg.get("hash_size", "?"),
            "Threads": cfg.get("num_cores", "?"),
            "Skill Level": cfg.get("skill_level", "?"),
        }
    return engine_metadata


# Il valore dei pezzi per riconoscere un sacrificio; il re non si sacrifica.
VALORE_DEI_PEZZI = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def _e_un_sacrificio(board, mossa):
    """Vero se la mossa lascia il pezzo mosso dove l'avversario puo'
    prenderlo guadagnando materiale: attaccato da un pezzo che vale meno, o
    attaccato e non difeso, e la presa fatta, se c'e', vale meno di lui.
    Sotto scacco non e' un sacrificio, si risponde per forza, e nemmeno col
    re. Serve alla Mossa Geniale: prima bastava staccare la seconda mossa,
    e su 547 mosse di sei partite le geniali erano 78, 34 delle quali
    semplici riprese di un pezzo appena catturato (Gabriele, 23 novembre
    2026)."""
    if board.is_check():
        return False
    pezzo = board.piece_at(mossa.from_square)
    if pezzo is None or pezzo.piece_type == chess.KING:
        return False
    if board.is_en_passant(mossa):
        presa = VALORE_DEI_PEZZI[chess.PAWN]
    else:
        catturato = board.piece_at(mossa.to_square)
        presa = VALORE_DEI_PEZZI[catturato.piece_type] if catturato else 0
    dopo = board.copy(stack=False)
    dopo.push(mossa)
    valore = VALORE_DEI_PEZZI[dopo.piece_type_at(mossa.to_square)]
    if presa >= valore:
        return False
    difeso = bool(dopo.attackers(pezzo.color, mossa.to_square))
    for casa in dopo.attackers(not pezzo.color, mossa.to_square):
        tipo = dopo.piece_type_at(casa)
        if tipo == chess.KING:
            # Il re prende solo un pezzo non difeso.
            if not difeso:
                return True
        elif not difeso or VALORE_DEI_PEZZI[tipo] < valore:
            return True
    return False


def _matto_dopo(punteggio, turno):
    """Il matto dopo la mossa, a parole, o None se non c'e'. punteggio e'
    la valutazione della mossa dalla posizione prima, come la da' il motore,
    e conta anche la mossa stessa: dopo, chi da' matto ha una mossa in
    meno, e se e' la mossa che da' matto e' scacco matto. Prima il conto
    cambiava di uno fra la mossa migliore e le altre, e il commento non
    diceva chi dava matto (Gabriele, 23 novembre 2026)."""
    if punteggio is None:
        return None
    dal_lato = punteggio.pov(turno)
    if not dal_lato.is_mate():
        return None
    mosse = dal_lato.mate()
    if mosse > 0:
        mosse -= 1
        vincitore = turno
    else:
        mosse = -mosse
        vincitore = not turno
    if mosse == 0:
        return _("scacco matto")
    if vincitore == chess.WHITE:
        return _("il Bianco dà matto in {m}").format(m=mosse)
    return _("il Nero dà matto in {m}").format(m=mosse)


def _maiuscola(testo):
    return testo[:1].upper() + testo[1:]


def _analizza_la_mossa(board, mossa, limit):
    """La mossa giocata analizzata dalla stessa posizione e con lo stesso
    limite delle alternative, con root_moves: prima si analizzava la
    posizione dopo, con un'altra ricerca a un'altra profondita', e parte
    della perdita era rumore. Restituisce una voce come quelle di
    analyze_position_deep, con move, score e pv, o None."""
    chiave = f"{board.fen()}_{mossa.uci()}_{limit.time}_{limit.depth}_{limit.nodes}"
    if chiave in oaa_analysis_cache:
        return oaa_analysis_cache[chiave]
    try:
        info = interroga(board, limit, root_moves=[mossa])
    # L'interrogazione del motore puo' fallire in molti modi: senza
    # analisi la mossa si salta.
    except Exception:  # noqa: BLE001
        return None
    if isinstance(info, list):
        info = info[0] if info else {}
    score = info.get("score")
    if score is None:
        return None
    risultato = {"rank": None, "move": mossa, "score": score, "pv": info.get("pv") or [mossa]}
    oaa_analysis_cache[chiave] = risultato
    return risultato


def _classifica_mossa(
    node, analysis_before, best_alternative, eval_after_move, turn, soglie
):
    """Giudica la mossa giocata confrontandola con la migliore trovata.

    eval_after_move e' la valutazione della mossa giocata dalla posizione
    prima, come quella delle alternative, quindi i matti si confrontano con
    lo stesso conto. Il giudizio guarda quanto cala la probabilita' di
    vittoria, come Lichess, coi punti delle soglie calo_*: in una partita
    gia' decisa un pedone in meno non e' uno svarione (Gabriele, 23
    novembre 2026). Restituisce la classificazione, i centesimi di pedone
    persi, limitati come fa Lichess a piu' o meno mille, e la valutazione
    della mossa, che il ramo della mossa migliore prende dalla linea
    migliore.
    """
    soglia_mossa_buona = soglie["mossa_buona"]
    soglia_mossa_geniale_gap = soglie["mossa_geniale_gap"]
    best_alternative_move = best_alternative["move"]
    centipawn_loss = 0
    classification = ""
    # 3. Confronto e Classificazione
    if node.move.uci() == best_alternative_move.uci():
        eval_after_move = best_alternative["score"]

        classification = "Mossa Buona"
        if len(analysis_before) > 1:
            score_best = analysis_before[0]["score"].pov(turn).score(mate_score=30000)
            score_second_best = (
                analysis_before[1]["score"].pov(turn).score(mate_score=30000)
            )
            # Geniale e' la mossa unica che sacrifica materiale: senza il
            # sacrificio e' una mossa buona, per esempio una ripresa.
            if (
                score_best is not None
                and score_second_best is not None
                and (score_best - score_second_best) >= soglia_mossa_geniale_gap
                and _e_un_sacrificio(node.parent.board(), node.move)
            ):
                classification = "Mossa Geniale"
    else:
        best_pov_score = best_alternative["score"].pov(turn)
        played_pov_score = eval_after_move.pov(turn)
        centipawn_loss = max(0, _centesimi(best_pov_score) - _centesimi(played_pov_score))

        matto_disponibile = best_pov_score.is_mate() and best_pov_score.mate() > 0
        matto_conservato = played_pov_score.is_mate() and played_pov_score.mate() > 0
        matto_subito = played_pov_score.is_mate() and played_pov_score.mate() < 0
        matto_gia_subito = best_pov_score.is_mate() and best_pov_score.mate() < 0
        if matto_disponibile and matto_conservato:
            # Un altro matto, magari piu' lungo, resta comunque vincente. I
            # due matti si contano dalla stessa posizione, quella prima: uno
            # piu' lento anche di una mossa e' un'inesattezza.
            mosse_migliore = abs(best_pov_score.mate())
            mosse_giocata = abs(played_pov_score.mate())
            if mosse_giocata > mosse_migliore:
                classification = "Inesattezza"
            else:
                classification = "Mossa Buona"
            centipawn_loss = 0
        elif matto_disponibile:
            # Il matto lasciato andare, come Lichess: inesattezza se si
            # resta sopra di dieci pedoni, errore sopra sette, svarione
            # altrimenti.
            resta = played_pov_score.score(mate_score=100000)
            classification = "Inesattezza" if resta > 999 else "Errore" if resta > 700 else "Svarione"
        elif matto_subito and not matto_gia_subito:
            # Il matto che si subisce, come Lichess: inesattezza se si era
            # gia' sotto di dieci pedoni, errore di sette, svarione altrimenti.
            prima = best_pov_score.score(mate_score=100000)
            classification = "Inesattezza" if prima < -999 else "Errore" if prima < -700 else "Svarione"
        else:
            calo = _vittoria_dal_lato(best_alternative["score"], turn) - _vittoria_dal_lato(eval_after_move, turn)
            if calo >= soglie["calo_svarione"]:
                classification = "Svarione"
            elif calo >= soglie["calo_errore"]:
                classification = "Errore"
            elif calo >= soglie["calo_inesattezza"]:
                classification = "Inesattezza"
            elif centipawn_loss <= soglia_mossa_buona:
                classification = "Mossa Buona"
            else:
                classification = "Mossa Normale"

    if not classification:
        classification = "Mossa Normale"
    return classification, centipawn_loss, eval_after_move


def AnalisiAutomatica(pgn_game):
    """
    Esegue un'analisi automatica completa della partita, aggiungendo commenti
    sugli errori e varianti migliori direttamente nel PGN.
    """
    # Fase 1: Controllo motore e raccolta parametri
    if ENGINE is None:
        print(
            _("\nMotore non inizializzato. Impossibile avviare l'analisi automatica.")
        )
        return

    def _format_score(score_obj, pov_color):
        if not score_obj:
            return _("N/A")
        pov_score = score_obj.pov(pov_color)
        if pov_score.is_mate():
            return board_utils.testo_del_matto(pov_score.mate())
        else:
            # La valutazione e' sempre dal punto di vista del bianco, quindi la adattiamo
            cp = score_obj.white().score(mate_score=30000)
            if cp is None:
                return _("N/A")
            final_cp = cp if pov_color == chess.WHITE else -cp
            return f"{final_cp / 100:+.2f}"

    print(_("Analisi Automatica della Partita"))
    forza_della_configurazione()

    # Caricamento configurazione soglie da DB
    db = storage.LoadDB()
    thresholds = db.get(
        "analysis_thresholds", storage.DEFAULT_DB["analysis_thresholds"]
    )
    # Tutte le soglie dal database, coi valori predefiniti di storage:
    # quelle della mossa buona e della geniale erano scritte qui una seconda
    # volta.
    predefinite = storage.DEFAULT_DB["analysis_thresholds"]
    soglie = {chiave: thresholds.get(chiave, valore) for chiave, valore in predefinite.items()}
    parametri = _parametri_analisi_automatica(pgn_game, db)
    if parametri is None:
        return
    (
        num_varianti,
        limit,
        truncate_length,
        mosse_da_saltare,
        last_valid_eco_entry,
    ) = parametri
    engine_metadata = _dati_motore(db)

    # Senza le righe di uguali attorno: niente separatori grafici (R90).
    print(_("\nInizio analisi... (Premi ESC per interrompere)"))
    start_time = time.time()

    oaa_analysis_cache.clear()

    # Assicuriamoci di essere alla radice
    pgn_game = pgn_game.root()
    mainline_nodes = list(pgn_game.mainline())

    analysis_results = []
    l10n_analysis = localizzazione.L10N.get("analysis", {})
    classification_labels = {
        "Svarione": l10n_analysis.get("blunder", _("Svarione")),
        "Errore": l10n_analysis.get("mistake", _("Errore")),
        "Inesattezza": l10n_analysis.get("inaccuracy", _("Inesattezza")),
        "Mossa Buona": l10n_analysis.get("good", _("Mossa Buona")),
        "Mossa Geniale": l10n_analysis.get("brilliant", _("Mossa Geniale")),
        "Mossa Normale": l10n_analysis.get("normal", _("Mossa Normale")),
        "Teoria": l10n_analysis.get("book", _("Teoria")),
    }
    imprecision_stats = {
        "Svarione": {"w": 0, "b": 0},
        "Errore": {"w": 0, "b": 0},
        "Inesattezza": {"w": 0, "b": 0},
        "Mossa Buona": {"w": 0, "b": 0},
        "Mossa Geniale": {"w": 0, "b": 0},
        "Mossa Normale": {"w": 0, "b": 0},
    }
    cpl_data = {"w": [], "b": []}
    accuracies = {"w": [], "b": []}

    # Ogni mossa si giudica dalla posizione prima: le alternative con
    # multipv, e la mossa giocata dalla stessa ricerca, se e' fra le linee,
    # o con root_moves alla stessa profondita'. Prima la mossa giocata si
    # valutava da un'altra ricerca, sulla posizione dopo, e il matto si
    # contava in due modi (Gabriele, 23 novembre 2026).
    fase = FASI[0]
    interrotta = False
    for i, node in enumerate(mainline_nodes):
        if key(attesa=0.002) in ("\x1b", "esc"):
            Acusticator(["c3", 0.3, 0.5, config.VOLUME], kind=2)
            print(_("\nAnalisi interrotta dall'utente."))
            interrotta = True
            break

        ply = i + 1
        if ply <= mosse_da_saltare:
            # La teoria non entra nella precisione: col 100% gonfiava la
            # precisione e l'Elo stimato, mentre il riepilogo la dice esclusa.
            analysis_results.append(
                {
                    "node": node,
                    "classification": "Teoria",
                    "centipawn_loss": 0,
                    "alternatives_info": [],
                    "eval_after_move": None,
                }
            )
            continue

        parent_board = node.parent.board()
        turn = parent_board.turn
        color_key = "w" if turn == chess.WHITE else "b"

        total_plys = len(mainline_nodes)
        san = parent_board.san(node.move)
        san_str = san if ply % 2 != 0 else f"...{san}"
        elapsed_time = time.time() - start_time
        time_str = f"{int(elapsed_time // 60):02d}:{int(elapsed_time % 60):02d}"
        # La riga di prima si pulisce: una riga piu' corta ne lasciava la
        # coda in fondo, come tempo 00:1800:17 (R126).
        ui.pulisci_riga()
        print(
            # Senza la barra verticale, e senza gli spazi di riempimento
            # (R90).
            _("\rSemimossa {ply} di {total}: {san}, tempo {t}").format(
                ply=ply, total=total_plys, san=san_str, t=time_str
            ),
            end="",
        )

        multipv_needed = max(3, num_varianti)
        analysis_before = analyze_position_deep(parent_board, limit, multipv_needed)
        if not analysis_before:
            # Il motore morto e non ripartito ferma l'analisi, invece di
            # saltare tutte le mosse fino a "completata" (R41).
            if ENGINE is None:
                print(_("\nAnalisi interrotta: il motore non risponde."))
                interrotta = True
                break
            continue
        best_alternative = analysis_before[0]
        giocata = next((info for info in analysis_before if info["move"] == node.move), None)
        if giocata is None:
            giocata = _analizza_la_mossa(parent_board, node.move, limit)
        if giocata is None:
            continue

        # La probabilita' di vittoria del Bianco prima e dopo la mossa, come
        # la calcola Lichess, dalla stessa posizione: la mossa migliore vale
        # il 100%.
        vittoria_prima = percentuale_di_vittoria(best_alternative["score"])
        vittoria_dopo = percentuale_di_vittoria(giocata["score"])
        precisione = calculate_move_accuracy(
            _vittoria_dal_lato(best_alternative["score"], turn) / 100, _vittoria_dal_lato(giocata["score"], turn) / 100
        )
        accuracies[color_key].append(precisione)
        rango = next((indice for indice, info in enumerate(analysis_before) if info["move"] == node.move), None)
        fase = max(fase, fase_della_posizione(parent_board), key=FASI.index)
        CPL_STATISTICS_CAP = 1000
        classification, centipawn_loss, eval_after_move = _classifica_mossa(
            node,
            analysis_before,
            best_alternative,
            giocata["score"],
            turn,
            soglie,
        )

        if classification in imprecision_stats:
            imprecision_stats[classification][color_key] += 1

        capped_loss = min(centipawn_loss, CPL_STATISTICS_CAP)
        cpl_data[color_key].append(capped_loss)

        matto = _matto_dopo(eval_after_move, turn)
        if matto is not None:
            comment_str = _("[OAA: {cl}. {matto}]").format(
                cl=classification_labels[classification], matto=_maiuscola(matto)
            )
            # Il seguito dopo la mossa, intero: troncata, una linea di
            # matto si fermerebbe prima del matto.
            seguito = giocata["pv"][1:]
            if classification not in ["Svarione", "Errore", "Inesattezza"] and seguito:
                if not node.variations:
                    # La partita finisce qui: una variante diventerebbe la
                    # linea principale, e la partita si allungherebbe con
                    # mosse mai giocate. La linea va nel commento.
                    comment_str += " " + _("[OAA: Linea: {linea}]").format(
                        linea=node.board().variation_san(seguito)
                    )
                elif node.variations[0].move != seguito[0]:
                    var_node = node.add_variation(seguito[0])
                    if len(seguito) > 1:
                        var_node.add_line(seguito[1:])
                    var_node.comment = _("[OAA: Segue: {matto}]").format(matto=matto)
        else:
            comment_str = _("[OAA: {cl}. Perdita: {cpl:+.2f}]").format(
                cl=classification_labels[classification], cpl=centipawn_loss / 100
            )

        # La confutazione dell'errore: dopo la mossa sbagliata, la risposta
        # migliore dell'avversario col suo seguito (Gabriele, 23 novembre
        # 2026). Una linea di matto resta intera; a fine partita la linea va
        # nel commento, per non allungare la partita.
        if classification in ERRORI:
            confutazione = giocata["pv"][1:]
            if matto is None and truncate_length > 0:
                confutazione = confutazione[:truncate_length]
            if confutazione:
                if not node.variations:
                    comment_str += " " + _("[OAA: Confutazione: {linea}]").format(
                        linea=node.board().variation_san(confutazione)
                    )
                elif node.variations[0].move != confutazione[0]:
                    var_node = node.add_variation(confutazione[0])
                    if len(confutazione) > 1:
                        var_node.add_line(confutazione[1:])
                    var_node.comment = _("[OAA: Confutazione]")

        node.comment = (
            (node.comment.strip() + " " + comment_str).strip()
            if node.comment
            else comment_str
        )

        # Aggiunta Varianti al PGN
        if classification in ["Svarione", "Errore", "Inesattezza"] and num_varianti > 0:
            varianti_da_aggiungere = analysis_before[:num_varianti]

            for var_info in varianti_da_aggiungere:
                pv = var_info.get("pv")
                if not isinstance(pv, list) or not pv:
                    continue

                prima_mossa_variante = pv[0]
                if prima_mossa_variante != node.move:
                    # Controlla duplicati
                    exists = any(
                        v.move == prima_mossa_variante
                        for v in node.parent.variations
                    )
                    if not exists:
                        var_node = node.parent.add_variation(prima_mossa_variante)
                        score_obj = var_info.get("score")
                        matto_alternativo = _matto_dopo(score_obj, turn)
                        if matto_alternativo is not None:
                            commento_variante = _("[OAA: Alt: {matto}]").format(
                                matto=matto_alternativo
                            )
                            # Una linea di matto resta intera.
                            resto = pv[1:]
                        else:
                            # Dal lato del Bianco, come [Val:] e il riepilogo.
                            commento_variante = _("[OAA: Alt: {s}]").format(
                                s=_format_score(score_obj, chess.WHITE)
                            )
                            resto = pv[1:truncate_length] if truncate_length > 0 else pv[1:]

                        var_node.comment = commento_variante
                        if resto:
                            var_node.add_line(resto)

        analysis_results.append(
            {
                "node": node,
                "classification": classification,
                "centipawn_loss": centipawn_loss,
                "alternatives_info": analysis_before,
                "eval_after_move": eval_after_move,
                "colore": turn,
                "vittoria_prima": vittoria_prima,
                "vittoria_dopo": vittoria_dopo,
                "precisione": precisione,
                "rango": rango,
                "fase": fase,
            }
        )

    # Dopo un'interruzione non si dice completata (R131).
    if interrotta:
        print("\n" + _("Analisi automatica fermata: il PGN tiene le mosse analizzate fin qui."))
    else:
        print("\n" + _("Analisi automatica completata."))
    pgn_game.headers["Annotator"] = _("Orologic V{v} (Auto)").format(v=version.VERSION)
    duration = time.time() - start_time

    percorso_txt = None
    try:
        pgn_string_formatted = board_utils.format_pgn_comments(str(pgn_game))
        base_name = _("{w}_vs_{b}_auto_{d}").format(
            w=pgn_game.headers.get("White", "B"),
            b=pgn_game.headers.get("Black", "N"),
            # Con l'ora: due analisi nello stesso giorno fra gli stessi nomi
            # si sovrascrivevano (R47).
            d=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
        )
        sanitized_pgn_name = config.sanitize_filename(base_name) + ".pgn"
        full_pgn_path = percorso_salvataggio(os.path.join("pgn", sanitized_pgn_name))
        os.makedirs(os.path.dirname(full_pgn_path), exist_ok=True)
        # utf-8 semplice come tutti gli altri PGN del programma: il BOM
        # dava fastidio ad alcuni lettori di partite.
        with open(full_pgn_path, "w", encoding="utf-8") as f:
            f.write(pgn_string_formatted)
        print(_("PGN analizzato salvato come: {path}").format(path=full_pgn_path))

        # Genera TXT con durata
        percorso_txt = genera_sommario_analitico_txt(
            pgn_game,
            sanitized_pgn_name.replace(".pgn", ""),
            analysis_results,
            imprecision_stats,
            cpl_data,
            last_valid_eco_entry,
            mosse_da_saltare,
            num_varianti,
            duration,
            engine_metadata,
            accuracies,
        )

    # Il salvataggio finale dice all'utente cosa non ha funzionato,
    # invece di cadere dopo un'analisi che puo' essere durata minuti.
    except Exception as e:  # noqa: BLE001
        print(_("Errore durante il salvataggio: {e}").format(e=e))

    # Nella finestra l'analisi si legge in una finestra sua, intera, dalla
    # prima riga, con Chiudi (Gabriele, collaudo del 23 novembre 2026, sera:
    # nell'area l'inizio si perdeva).
    from . import strato

    if percorso_txt and strato.con_la_plancia() and ui.enter_escape(_("Vuoi leggere l'analisi in una finestra? (INVIO per si', ESC per no): ")):
        with open(percorso_txt, encoding="utf-8") as file:
            strato.leggi_in_una_finestra(_("Analisi Automatica della Partita"), file.read().rstrip("\n").split("\n"))
    print(_("Ritorno al menu principale."))
    Acusticator(
        [
            "c5",
            0.1,
            0,
            config.VOLUME,
            "e5",
            0.1,
            0,
            config.VOLUME,
            "g5",
            0.4,
            0,
            config.VOLUME,
        ],
        kind=1,
    )


# I lati dei bip delle domande del motore, nell'ordine del terminale: il
# percorso, la hash, i core, il livello di skill e il move overhead. Il primo
# ha la seconda nota a -75, com'e' sempre stato.
LATI_DELLE_DOMANDE = {"percorso": (-0.75, -75), "hash": (-0.25,), "core": (0,), "skill": (0.25,), "overhead": (0.5,)}


def bip_della_domanda(lato, lato_della_seconda=None):
    """Il bip breve dopo una domanda della configurazione del motore."""
    seconda = lato if lato_della_seconda is None else lato_della_seconda
    Acusticator(["g6", 0.025, lato, config.VOLUME, "c5", 0.025, seconda, config.VOLUME], kind=3)


def suono_del_motore_salvato():
    """La nota della configurazione del motore salvata, col motore riavviato."""
    Acusticator(["a6", 0.5, 1, config.VOLUME], kind=3, adsr=[0.001, 0, 100, 99.9])


def percorso_da_salvare(percorso_assoluto):
    """Il percorso del motore come va salvato: relativo alla cartella di
    Orologic se sta sullo stesso disco, per la portabilita', altrimenti
    assoluto. Restituisce (percorso, relativo)."""
    app_path = os.path.abspath(percorso_salvataggio(""))
    app_drive = os.path.splitdrive(app_path)[0]
    engine_drive = os.path.splitdrive(percorso_assoluto)[0]
    if app_drive and app_drive.lower() == engine_drive.lower():
        try:
            return os.path.relpath(percorso_assoluto, app_path), True
        except ValueError:
            pass
    return percorso_assoluto, False


def percorso_assoluto(percorso_salvato):
    """Il percorso assoluto del motore da quello salvato nella
    configurazione."""
    if not percorso_salvato:
        return ""
    if os.path.isabs(percorso_salvato):
        return os.path.abspath(percorso_salvato)
    return os.path.abspath(percorso_salvataggio(percorso_salvato))


def MenuMotore():
    from GBUtils import key

    from . import stockfish_installer

    print(_("\nAzioni per il motore scacchistico:"))
    scelta_azione = (
        key(
            _(
                "Vuoi [c] cercare un motore nel tuo pc, [s] scaricare Stockfish, o [m] per modificare manualmente la configurazione? (c/s/m): "
            )
        )
        .lower()
        .strip()
    )
    if scelta_azione == "c":
        p, e, _u = SearchForEngine()
        if p and e:
            EditEngineConfig(initial_path=p, initial_executable=e)
    elif scelta_azione == "s":
        # Il motore in uso si chiude prima: Windows non sposta una cartella
        # con dentro un eseguibile aperto, e la sostituzione falliva.
        CloseEngine()
        p, e = stockfish_installer.DownloadAndInstallEngine()
        if p and e:
            EditEngineConfig(initial_path=p, initial_executable=e)
    elif scelta_azione == "m":
        EditEngineConfig()


def EditEngineConfig(initial_path=None, initial_executable=None):
    CloseEngine()  # Importante: rilascia il file exe se in uso
    print(_("\nImposta configurazione del motore scacchistico\n"))
    db = storage.LoadDB()
    engine_config = db.get("engine_config", {})
    if engine_config:
        print(_("Configurazione attuale del motore:"))
        for key, val in engine_config.items():
            print(f"  {key}: {val}")
    else:
        print(_("Nessuna configurazione trovata."))

    default_path = initial_path if initial_path else ""
    path = dgt(
        _("Inserisci il percorso dove e' salvato il motore UCI [{default}]: ").format(
            default=default_path
        ),
        kind="s",
        smin=3,
        smax=256,
        default=default_path,
    )
    bip_della_domanda(-0.75, -75)

    default_exe = initial_executable if initial_executable else ""
    executable = dgt(
        _("Inserisci il nome dell'eseguibile del motore [{default}]: ").format(
            default=default_exe
        ),
        kind="s",
        smin=5,
        smax=64,
        default=default_exe,
    )

    raw_engine_path = os.path.join(path, executable)
    if os.path.isabs(raw_engine_path):
        abs_engine_path = os.path.abspath(raw_engine_path)
    else:
        abs_engine_path = os.path.abspath(percorso_salvataggio(raw_engine_path))

    if not os.path.isfile(abs_engine_path):
        print(
            _(
                "Il file specificato non esiste. Verifica il percorso e il nome dell'eseguibile."
            )
        )
        return

    app_path = os.path.abspath(percorso_salvataggio(""))
    app_drive = os.path.splitdrive(app_path)[0]
    engine_drive = os.path.splitdrive(abs_engine_path)[0]

    path_to_save = ""
    is_relative = False

    if app_drive.lower() == engine_drive.lower() and app_drive != "":
        try:
            path_to_save = os.path.relpath(abs_engine_path, app_path)
            is_relative = True
            print(
                _(
                    "Info: il motore si trova sullo stesso drive, verra' salvato un percorso relativo per la portabilita'."
                )
            )
        except ValueError:
            path_to_save = abs_engine_path
            is_relative = False
    else:
        path_to_save = abs_engine_path
        is_relative = False
        print(
            _(
                "Info: il motore si trova su un drive diverso, verra' salvato un percorso assoluto (configurazione non portatile)."
            )
        )

    hash_size = dgt(
        _("Inserisci la dimensione della hash table (min: 1, max: 4096 MB): "),
        kind="i",
        imin=1,
        imax=4096,
        default=128,
    )
    bip_della_domanda(-0.25)

    max_cores = os.cpu_count() or 1
    num_cores = dgt(
        _(
            "Inserisci il numero di core da utilizzare (min: 1, max: {max_cores}): "
        ).format(max_cores=max_cores),
        kind="i",
        imin=1,
        imax=max_cores,
        default=min(4, max_cores),
    )
    bip_della_domanda(0)

    skill_level = dgt(
        _("Inserisci il livello di skill (min: 0, max: 20): "),
        kind="i",
        imin=0,
        imax=20,
        default=20,
    )
    bip_della_domanda(0.25)

    move_overhead = dgt(
        _("Inserisci il move overhead in millisecondi (min: 0, max: 500): "),
        kind="i",
        imin=0,
        imax=500,
        default=0,
    )
    bip_della_domanda(0.5)

    engine_config = {
        "engine_path": path_to_save,
        "engine_is_relative": is_relative,
        "hash_size": hash_size,
        "num_cores": num_cores,
        "skill_level": skill_level,
        "move_overhead": move_overhead,
    }
    storage.SetValue("engine_config", engine_config)
    print(_("Configurazione del motore salvata."))
    InitEngine()
    suono_del_motore_salvato()
    return
