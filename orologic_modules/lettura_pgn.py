# Orologic: la lettura delle partite PGN, anche con tutti i processori.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La lettura delle partite PGN per la ricerca: le schede dell'archivio e
le righe di testo che python-chess legge, senza le impostazioni, i suoni e
le traduzioni di Orologic.

Il modulo e' leggero di proposito: gli archivi grandi si leggono a pezzi
in processi paralleli, uno per processore, e ognuno carica soltanto questo
modulo e python-chess. Chiesto da Gabriele il 22 novembre 2026, dopo il
collaudo: GBChessDB.pgn, 38.662 partite, impiegava 37 secondi con un
processore solo dei 32 del suo computer. Leggere le mosse e' quasi tutto
il lavoro: python-chess interpreta ogni mossa e la gioca sulla scacchiera.

Le righe vuote in mezzo alle mosse non chiudono la partita: la chiude il
segno del risultato, come per pgn-extract e lo standard. Lo stesso giorno,
sull'archivio di Gabriele, 37 partite col commento iniziale staccato dalle
mosse diventavano due pezzi.
"""

import array
import bisect
import concurrent.futures
import itertools
import os
import re
import time

import chess
import chess.pgn

OGNI_QUANTO = 3.0
FINE_DELLA_PARTITA = frozenset(("1-0", "0-1", "1/2-1/2", "*"))
# Le date come le vuole il PGN.
DATA = re.compile(r"^(\d{4}|\?{4})\.(\d{2}|\?{2})\.(\d{2}|\?{2})$")
# Il messaggio di python-chess per una mossa che non va: la mossa e la
# posizione, col colore che muove e il numero della mossa in fondo.
MOSSA_SBAGLIATA = re.compile(r"san: '([^']*)' in \S+ ([wb]) \S+ \S+ \d+ (\d+)")
MASSIMI_ERRORI = 5
# In parallelo solo i testi grandi, a pezzi di mezzo milione di caratteri
# circa; sotto, il tempo per avviare i processi non vale il guadagno. Un
# processore resta libero, per la finestra e NVDA. Misurato su GBChessDB.pgn,
# 38.662 partite, sul computer da 32 processori: 36,6 secondi in fila, 5,5
# con 8 processi, 4,0 con 16, 3,1 con 31.
SOGLIA_IN_PARALLELO = 3_000_000
PEZZO = 500_000
PROCESSI_MASSIMI = 32


def pulita(testo):
    """Una riga del terminale per la finestra: senza i ritorni a capo e con
    uno spazio solo fra le parole, come le vuole il display braille."""
    return " ".join(testo.split())


class RighePGN:
    """Un testo PGN riga per riga, per chess.pgn.read_game e read_headers,
    senza copiarlo: tell() dice dove si e'.

    Per python-chess una riga vuota in mezzo alle mosse chiude la partita;
    per pgn-extract, ChessBase e lo standard la chiude il segno del
    risultato. Cosi' una partita col commento iniziale staccato dalle mosse
    da una riga vuota diventava due pezzi: le intestazioni col commento, e
    le mosse senza intestazioni. Qui le righe vuote di una partita che non
    ha ancora il suo segno si saltano, se dopo non comincia un'altra
    partita; quelle dentro un commento restano. Scoperto il 22 novembre
    2026 sull'archivio di Gabriele, con 37 partite fatte a pezzi."""

    def __init__(self, testo, posizione=0):
        self.testo = testo
        self.posizione = posizione
        self.nel_commento = False
        # fuori, intestazioni, mosse o chiusa: a che punto e' la partita.
        self.stato = "fuori"

    def tell(self):
        return self.posizione

    def _riga(self):
        fine = self.testo.find("\n", self.posizione)
        fine = len(self.testo) if fine < 0 else fine + 1
        riga = self.testo[self.posizione : fine]
        self.posizione = fine
        return riga

    def readline(self):
        riga = self._riga()
        if riga and riga.isspace() and not self.nel_commento and self.stato in ("intestazioni", "mosse"):
            ripresa = self.posizione
            seguente = self._riga()
            while seguente and seguente.isspace():
                seguente = self._riga()
            if not seguente or seguente.startswith(("[", "%")):
                self.posizione = ripresa
                return riga
            riga = seguente
        self._segui(riga)
        return riga

    def _segui(self, riga):
        """Lo stato della partita dopo la riga."""
        if not riga or riga.isspace():
            return
        if not self.nel_commento:
            if riga.startswith("["):
                self.stato = "intestazioni"
                return
            if riga.startswith("%"):
                return
        fuori = self._fuori_dai_commenti(riga).rsplit(None, 1)
        if fuori:
            self.stato = "chiusa" if fuori[-1] in FINE_DELLA_PARTITA else "mosse"
        elif self.stato in ("fuori", "intestazioni"):
            self.stato = "mosse"

    def _fuori_dai_commenti(self, riga):
        """La riga senza i commenti, fra graffe o dopo il punto e virgola."""
        if not self.nel_commento and "{" not in riga and ";" not in riga:
            return riga
        pezzi = []
        inizio = 0
        while inizio < len(riga):
            if self.nel_commento:
                chiusa = riga.find("}", inizio)
                if chiusa < 0:
                    break
                self.nel_commento = False
                inizio = chiusa + 1
                continue
            graffa = riga.find("{", inizio)
            punto = riga.find(";", inizio)
            if punto >= 0 and (graffa < 0 or punto < graffa):
                pezzi.append(riga[inizio:punto])
                break
            if graffa < 0:
                pezzi.append(riga[inizio:])
                break
            pezzi.append(riga[inizio:graffa])
            self.nel_commento = True
            inizio = graffa + 1
        return "".join(pezzi)


# Le intestazioni e le partite da tenere, come nella ricerca del terminale.


def estrai_info(games):
    """Estrae gli headers rilevanti da ogni partita.

    Accetta partite intere oppure le sole intestazioni lette con
    chess.pgn.read_headers: Easyfish, con .pa, filtra cosi' i file da
    molte partite senza leggerne le mosse.

    Returns:
        list[dict] con chiavi: White, Black, Result, WhiteElo, BlackElo,
                               Event, Date, Year, ECO
    """
    info_list = []
    for g in games:
        h = getattr(g, "headers", g)
        year = None
        date_str = h.get("Date", "????.??.??")
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except (ValueError, TypeError):
                pass

        w_elo = None
        b_elo = None
        try:
            w_elo = int(h.get("WhiteElo", ""))
        except (ValueError, TypeError):
            pass
        try:
            b_elo = int(h.get("BlackElo", ""))
        except (ValueError, TypeError):
            pass

        info_list.append(
            {
                "White": h.get("White", "?"),
                "Black": h.get("Black", "?"),
                "Result": h.get("Result", "*"),
                "WhiteElo": w_elo,
                "BlackElo": b_elo,
                "Event": h.get("Event", "?"),
                "Date": date_str,
                "Year": year,
                "ECO": h.get("ECO", ""),
                # Per la chiave dei doppioni: due studi con le stesse mosse e
                # intestazioni generiche non sono la stessa partita (R24).
                "Round": h.get("Round", "?"),
                "FEN": h.get("FEN", ""),
            }
        )
    return info_list


# I valori dell'intestazione Variant di una partita a scacchi normali; "from
# position" e' quello di Lichess per le partite da una posizione, che la FEN
# esclude se non e' quella di partenza.
VARIANTI_STANDARD = ("", "standard", "chess", "normal", "from position")


def _partita_da_tenere(game):
    """vuota, esclusa o buona: i record senza mosse ne' intestazioni vere si
    saltano, le partite che non partono dalla posizione standard si
    escludono."""
    has_real_headers = False
    for val in game.headers.values():
        if val not in ("?", "*", "????.??.??"):
            has_real_headers = True
            break
    has_moves = len(list(game.mainline_moves())) > 0
    if not has_real_headers and not has_moves:
        return "vuota"

    # Si escludono le partite che non partono dalla scacchiera standard: ogni
    # variante, non solo Chess960, e ogni FEN diversa da quella di partenza,
    # anche senza SetUp, perche' python-chess la usa lo stesso. Prima
    # crazyhouse, atomic e simili, e le FEN senza SetUp, entravano
    # nell'albero e ne inquinavano le statistiche (R26).
    if game.headers.get("Variant", "").strip().lower() not in VARIANTI_STANDARD:
        return "esclusa"
    fen = game.headers.get("FEN", "").strip()
    if fen and " ".join(fen.split()[:4]) != " ".join(chess.STARTING_FEN.split()[:4]):
        return "esclusa"
    return "buona"


# Le mosse come numeri da due byte: da, a e promozione.


def codice(mossa):
    return mossa.from_square | (mossa.to_square << 6) | ((mossa.promotion or 0) << 12)


def mossa(numero):
    return chess.Move(numero & 63, (numero >> 6) & 63, (numero >> 12) or None)


# Le schede.


class _Costruttore(chess.pgn.GameBuilder):
    """Il costruttore di python-chess, che in piu' ricorda le intestazioni
    scritte davvero, la posizione finale della linea principale e il segno
    del risultato in fondo alle mosse. Gli errori vanno nella partita, non
    nel registro: finiscono nel ramo Con errori."""

    def begin_game(self):
        super().begin_game()
        self.game = self.Game.without_tag_roster()
        self.variation_stack = [self.game]
        self.presenti = set()
        self.scacchiera = None
        self.segno = None

    def visit_header(self, tagname, tagvalue):
        self.presenti.add(tagname)
        super().visit_header(tagname, tagvalue)

    def visit_board(self, board):
        # La prima e' la scacchiera della linea principale, che poi va avanti
        # mossa dopo mossa: alla fine e' la posizione finale.
        if self.scacchiera is None:
            self.scacchiera = board

    def visit_result(self, result):
        self.segno = result
        super().visit_result(result)

    def handle_error(self, error):
        self.game.errors.append(error)

    def result(self):
        return self.game, self.presenti, self.scacchiera, self.segno


class Scheda:
    """Una partita dell'archivio: dove sta nel testo, le mosse della linea
    principale, le linee delle varianti dalla prima mossa, se sta fuori
    dall'albero, il matto e la promozione per i filtri, e i problemi come
    {tipo: valore}, o None."""

    __slots__ = ("fine", "fuori", "inizio", "linee", "mosse", "problemi")

    def __init__(self, inizio, fine, mosse, linee, fuori, problemi):
        self.inizio = inizio
        self.fine = fine
        self.mosse = mosse
        self.linee = linee
        self.fuori = fuori
        self.problemi = problemi

    def spostata(self, inizio, fine):
        return Scheda(inizio, fine, self.mosse, self.linee, self.fuori, self.problemi)


def _linee(game):
    """Le linee delle varianti, ognuna dalla prima mossa fino alla sua fine,
    senza la ricorsione: le partite lunghe non hanno limiti."""
    linee = []
    percorso = []
    pila = [(game, 0, True)]
    while pila:
        nodo, profondita, principale = pila.pop()
        if profondita:
            del percorso[profondita - 1 :]
            percorso.append(codice(nodo.move))
        figli = nodo.variations
        if not figli:
            if not principale:
                linee.append(array.array("H", percorso))
            continue
        for numero in range(len(figli) - 1, -1, -1):
            pila.append((figli[numero], profondita + 1, principale and numero == 0))
    return linee or ()


def risultato_della_posizione(scacchiera):
    """Il risultato che la posizione finale impone: il matto o lo stallo."""
    if scacchiera is None:
        return None
    if scacchiera.is_checkmate():
        return "0-1" if scacchiera.turn == chess.WHITE else "1-0"
    if scacchiera.is_stalemate():
        return "1/2-1/2"
    return None


def _mossa_sbagliata(errore):
    """La mossa che non va, come 23... Qxf7, o il messaggio di python-chess."""
    trovata = MOSSA_SBAGLIATA.search(str(errore))
    if trovata is None:
        return pulita(str(errore))
    san, colore, numero = trovata.groups()
    return f"{numero}. {san}" if colore == "w" else f"{numero}... {san}"


def _problemi(game, presenti, scacchiera, segno):
    trovati = {}
    if game.errors:
        trovati["mosse"] = _mossa_sbagliata(game.errors[0])
    mancanti = tuple(tag for tag in chess.pgn.TAG_ROSTER if tag not in presenti)
    if mancanti:
        trovati["intestazioni"] = mancanti
    risultato = game.headers.get("Result", "*")
    atteso = risultato_della_posizione(scacchiera)
    if atteso is not None and risultato != atteso:
        trovati["risultato"] = ("posizione", atteso)
    elif segno is not None and "Result" in presenti and segno != risultato:
        trovati["risultato"] = ("segno", segno)
    data = game.headers.get("Date")
    if data is not None and not DATA.match(data):
        trovati["data"] = data
    elo = [f"{tag} {valore}" for tag in ("WhiteElo", "BlackElo") if (valore := game.headers.get(tag)) not in (None, "", "?", "-") and not valore.isdigit()]
    if elo:
        trovati["elo"] = ", ".join(elo)
    return trovati or None


def _scheda(letta, inizio, fine, fuori):
    """(scheda, info) di una partita letta col costruttore."""
    game, presenti, scacchiera, segno = letta
    mosse = array.array("H", (codice(m) for m in game.mainline_moves()))
    scheda = Scheda(inizio, fine, mosse, _linee(game), fuori, _problemi(game, presenti, scacchiera, segno))
    info = estrai_info([game.headers])[0]
    info["Mosse"] = (len(mosse) + 1) // 2
    info["Matto"] = scacchiera is not None and scacchiera.is_checkmate()
    info["Promozione"] = any(numero >> 12 for numero in mosse)
    return scheda, info


# La lettura, in fila o in parallelo.


def leggi(testo, cattive=(), avanzamento=None, interrotta=None, fermato=None, processi=None):
    """Le partite del testo: (pezzi, schede, info). pezzi e' tutto il testo
    a pezzi, (inizio, fine, scheda o None), anche quello che non e' una
    partita, perche' il file si possa riscrivere senza perdere niente.
    avanzamento(n), interrotta(e) e fermato() come in leggi_le_partite.
    processi, quanti ne usa la lettura in parallelo: None li sceglie da
    soli, 1 legge in fila; i testi piccoli si leggono sempre in fila."""
    if processi is None:
        processi = min(PROCESSI_MASSIMI, _processori() - 1)
    tagli = _tagli(testo) if processi > 1 and len(testo) >= SOGLIA_IN_PARALLELO else []
    if len(tagli) > 2:
        try:
            return _leggi_in_parallelo(testo, cattive, tagli, processi, avanzamento, interrotta, fermato)
        # Un computer che non lascia avviare i processi legge in fila,
        # come prima; BrokenProcessPool e' un RuntimeError.
        except (OSError, RuntimeError):
            pass
    return _leggi_in_fila(testo, cattive, avanzamento, interrotta, fermato)


def _processori():
    contare = getattr(os, "process_cpu_count", os.cpu_count)
    return contare() or 1


def _leggi_in_fila(testo, cattive=(), avanzamento=None, interrotta=None, fermato=None):
    righe = RighePGN(testo)
    pezzi, schede, info = [], [], []
    letture_fallite = 0
    contate = 0
    ultima = 0.0
    inizio = 0
    while True:
        inizio = righe.tell()
        if fermato is not None and fermato():
            break
        try:
            letta = chess.pgn.read_game(righe, Visitor=_Costruttore)
        # Gli archivi PGN arrivano da fuori e possono essere malformati
        # in modi imprevedibili.
        except Exception as e:  # noqa: BLE001
            if righe.tell() > inizio:
                pezzi.append((inizio, righe.tell(), None))
                continue
            letture_fallite += 1
            if letture_fallite >= MASSIMI_ERRORI:
                if interrotta is not None:
                    interrotta(e)
                break
            continue
        letture_fallite = 0
        fine = righe.tell()
        if letta is None:
            break
        contate += 1
        game = letta[0]
        esito = _partita_da_tenere(game)
        if esito == "vuota":
            pezzi.append((inizio, fine, None))
            continue
        scheda, dati = _scheda(letta, inizio, fine, esito == "esclusa")
        primo = bisect.bisect_left(cattive, inizio)
        if primo < len(cattive) and cattive[primo] < fine:
            scheda.problemi = {**(scheda.problemi or {}), "codifica": True}
        pezzi.append((inizio, fine, len(schede)))
        schede.append(scheda)
        info.append(dati)
        adesso = time.time()
        if adesso - ultima >= OGNI_QUANTO:
            if avanzamento is not None:
                avanzamento(contate)
            ultima = adesso
    # Quello che resta, letto o no, si tiene com'e'.
    if righe.tell() < len(testo) or inizio < len(testo):
        pezzi.append((inizio, len(testo), None))
    return pezzi, schede, info


def _tagli(testo):
    """Dove tagliare il testo per i processi: [0, ..., len(testo)], ogni
    taglio all'inizio delle intestazioni di una partita, dopo una riga
    vuota, fuori dai commenti e non dopo altre intestazioni, perche' per
    python-chess una riga vuota fra due intestazioni non chiude la partita.
    Cosi' ogni pezzo si legge da solo come si leggerebbe tutto di fila."""
    tagli = [0]
    cerca = PEZZO
    while cerca < len(testo):
        trovato = testo.find("\n\n[", cerca)
        if trovato < 0:
            break
        taglio = trovato + 2
        cerca = taglio + 1
        precedente = tagli[-1]
        if testo.rfind("{", precedente, taglio) > testo.rfind("}", precedente, taglio):
            continue
        fine_di_prima = trovato
        while fine_di_prima > precedente and testo[fine_di_prima - 1] in "\n\r \t":
            fine_di_prima -= 1
        if testo.startswith("[", testo.rfind("\n", precedente, fine_di_prima) + 1):
            continue
        tagli.append(taglio)
        cerca = taglio + PEZZO
    tagli.append(len(testo))
    return tagli


def _leggi_un_pezzo(testo, cattive):
    """Nel processo: (pezzi, schede, info, errore) del pezzo di testo."""
    errori = []
    pezzi, schede, info = _leggi_in_fila(testo, cattive, interrotta=lambda e: errori.append(str(e)))
    return pezzi, schede, info, errori[0] if errori else None


def _leggi_in_parallelo(testo, cattive, tagli, processi, avanzamento, interrotta, fermato):
    pezzi, schede, info = [], [], []
    contate = 0
    ultima = time.time()
    esecutore = concurrent.futures.ProcessPoolExecutor(max_workers=min(processi, len(tagli) - 1))
    try:
        coppie = list(itertools.pairwise(tagli))
        # I pezzi si sottomettono a finestra scorrevole, due per processo:
        # tutti insieme, ognuno con la sua copia del testo, la lettura di un
        # archivio da un giga teneva in memoria tre o quattro volte il file
        # (R63).
        finestra = max(2, 2 * processi)
        lavori = {}

        def sottometti(numero):
            inizio, fine = coppie[numero]
            primo, ultimo = bisect.bisect_left(cattive, inizio), bisect.bisect_left(cattive, fine)
            lavori[numero] = esecutore.submit(_leggi_un_pezzo, testo[inizio:fine], [posizione - inizio for posizione in cattive[primo:ultimo]])

        for numero in range(min(finestra, len(coppie))):
            sottometti(numero)
        # I pezzi si uniscono in ordine: l'archivio e' lo stesso della
        # lettura in fila. Fermata, o interrotta da un pezzo illeggibile, la
        # lettura tiene i pezzi arrivati, e il resto del testo com'e'.
        for numero in range(len(coppie)):
            lavoro = lavori.pop(numero)
            if numero + finestra < len(coppie):
                sottometti(numero + finestra)
            while True:
                if fermato is not None and fermato():
                    pezzi.append((tagli[numero], len(testo), None))
                    return pezzi, schede, info
                try:
                    suoi_pezzi, sue_schede, sue_info, errore = lavoro.result(timeout=0.2)
                    break
                except concurrent.futures.TimeoutError:
                    continue
            spostamento, base = tagli[numero], len(schede)
            for inizio, fine, indice in suoi_pezzi:
                pezzi.append((inizio + spostamento, fine + spostamento, None if indice is None else indice + base))
            for scheda in sue_schede:
                scheda.inizio += spostamento
                scheda.fine += spostamento
            schede.extend(sue_schede)
            info.extend(sue_info)
            contate += len(sue_schede)
            adesso = time.time()
            if avanzamento is not None and adesso - ultima >= OGNI_QUANTO:
                avanzamento(contate)
                ultima = adesso
            if errore is not None:
                if interrotta is not None:
                    interrotta(errore)
                if tagli[numero + 1] < len(testo):
                    pezzi.append((tagli[numero + 1], len(testo), None))
                return pezzi, schede, info
        return pezzi, schede, info
    finally:
        # Senza aspettare i pezzi che non servono piu'.
        esecutore.shutdown(wait=False, cancel_futures=True)
