# Orologic: l'archivio della ricerca PGN nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'archivio della ricerca PGN nella finestra, senza wx, come l'ha voluto
Gabriele nel collaudo del 22 novembre 2026.

Per reggere archivi da centinaia di migliaia di partite le partite non
restano in memoria come oggetti di python-chess: resta il testo del file, e
di ogni partita una scheda col suo pezzo di testo, le mosse della linea
principale e delle varianti come numeri da due byte, e i problemi trovati
leggendola. La partita intera si rilegge dal suo pezzo quando serve.

Il file si legge in UTF-8, e le righe che non lo sono in cp1252: sono le
partite coi caratteri illeggibili. Le partite da una posizione di studio, o
Chess960, entrano nell'archivio, fuori dall'albero delle mosse, fra le non
classificate.

L'albero ha le mosse giocate e, contate a parte, quelle delle varianti dei
commenti: le statistiche e le percentuali sono solo delle partite giocate.

Classifica e Ripara cambiano il testo delle partite con modifiche minime,
senza riscriverle: le intestazioni e il segno del risultato. Prima di
riscrivere il file se ne fa una copia di sicurezza nella cartella pgn; le
partite che non cambiano si copiano com'erano, anche quelle che la ricerca
non carica.
"""

import array
import bisect
import codecs
import contextlib
import io
import os
import re
import shutil
import time

import chess
import chess.pgn

from . import board_utils, config, pgn_search
from .config import _

# Le date come le vuole il PGN, e quelle che si sanno riscrivere.
DATA = re.compile(r"^(\d{4}|\?{4})\.(\d{2}|\?{2})\.(\d{2}|\?{2})$")
DATA_DA_RISCRIVERE = re.compile(r"^(\d{4})(?:[-/.](\d{1,2}|\?\?)(?:[-/.](\d{1,2}|\?\?))?)?$")
INTESTAZIONE = re.compile(r'^\[\s*([A-Za-z0-9][A-Za-z0-9_+#=:-]*)\s+"((?:[^"\\]|\\.)*)"\s*\]\s*$')
SEGNO = re.compile(r"(1-0|0-1|1/2-1/2|\*)(\s*)$")
# Il messaggio di python-chess per una mossa che non va: la mossa e la
# posizione, col colore che muove e il numero della mossa in fondo.
MOSSA_SBAGLIATA = re.compile(r"san: '([^']*)' in \S+ ([wb]) \S+ \S+ \d+ (\d+)")
MASSIMI_ERRORI = 5
# Le intestazioni obbligatorie che mancano si aggiungono con questi valori.
VALORI_IGNOTI = {"Date": "????.??.??", "Result": "*"}


def tipi_dei_problemi():
    """I sottorami del ramo Con errori, nell'ordine in cui si mostrano."""
    return (
        ("mosse", _("Mosse illegali o illeggibili")),
        ("intestazioni", _("Intestazioni obbligatorie mancanti")),
        ("risultato", _("Risultato che non torna")),
        ("data", _("Date malformate")),
        ("elo", _("Elo non numerici")),
        ("codifica", _("Caratteri illeggibili")),
        ("doppioni", _("Partite doppie")),
    )


# Le mosse come numeri da due byte: da, a e promozione.


def codice(mossa):
    return mossa.from_square | (mossa.to_square << 6) | ((mossa.promotion or 0) << 12)


def mossa(numero):
    return chess.Move(numero & 63, (numero >> 6) & 63, (numero >> 12) or None)


# La lettura.


def decodifica(dati):
    """I byte del file come testo: (testo, cattive, a_capo, bom). cattive
    sono i principi delle righe che non erano UTF-8, lette in cp1252; il
    testo va a capo con \\n, e a_capo dice come andava il file."""
    bom = dati.startswith(codecs.BOM_UTF8)
    if bom:
        dati = dati[len(codecs.BOM_UTF8):]
    a_capo = "\r\n" if b"\r\n" in dati[:65536] else "\n"
    try:
        return dati.decode("utf-8").replace("\r\n", "\n"), [], a_capo, bom
    except UnicodeDecodeError:
        pass
    parti, cattive, posizione = [], [], 0
    for riga in dati.splitlines(keepends=True):
        try:
            pezzo = riga.decode("utf-8")
        except UnicodeDecodeError:
            pezzo = riga.decode("cp1252", errors="replace")
            cattive.append(posizione)
        pezzo = pezzo.replace("\r\n", "\n")
        parti.append(pezzo)
        posizione += len(pezzo)
    return "".join(parti), cattive, a_capo, bom


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
        return pgn_search.pulita(str(errore))
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
    info = pgn_search.estrai_info([game.headers])[0]
    info["Mosse"] = (len(mosse) + 1) // 2
    info["Matto"] = scacchiera is not None and scacchiera.is_checkmate()
    info["Promozione"] = any(numero >> 12 for numero in mosse)
    return scheda, info


def leggi(testo, cattive=(), avanzamento=None, interrotta=None, fermato=None):
    """Le partite del testo: (pezzi, schede, info). pezzi e' tutto il testo
    a pezzi, (inizio, fine, scheda o None), anche quello che non e' una
    partita, perche' il file si possa riscrivere senza perdere niente.
    avanzamento(n), interrotta(e) e fermato() come in leggi_le_partite."""
    righe = board_utils.RighePGN(testo)
    pezzi, schede, info = [], [], []
    letture_fallite = 0
    contate = 0
    ultima = 0.0
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
        esito = pgn_search._partita_da_tenere(game)
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
        if adesso - ultima >= pgn_search.OGNI_QUANTO:
            if avanzamento is not None:
                avanzamento(contate)
            ultima = adesso
    # Quello che resta, letto o no, si tiene com'e'.
    if righe.tell() < len(testo) or inizio < len(testo):
        pezzi.append((inizio, len(testo), None))
    return pezzi, schede, info


def _scarica(indirizzo, righe, avanzamento=None, fermato=None):
    """I byte dell'indirizzo, a blocchi: Esc, cioe' fermato, e il limite
    dei sessanta minuti tengono quello che e' arrivato, come nel terminale."""
    pulita = pgn_search.pulita
    data = []
    downloaded = 0
    start_time = time.time()
    last_print = start_time
    with pgn_search._apri_indirizzo(indirizzo) as resp:
        while True:
            if fermato is not None and fermato():
                righe.append(pulita(_("Scaricamento interrotto dall'utente. Elaborazione delle partite caricate finora...")))
                break
            chunk = resp.read(pgn_search.BLOCCO)
            if not chunk:
                break
            data.append(chunk)
            downloaded += len(chunk)
            now = time.time()
            elapsed = now - start_time
            if elapsed > pgn_search.LIMITE_DELLO_SCARICAMENTO:
                righe.append(pulita(_("Tempo massimo di scaricamento (60 minuti) raggiunto. Elaborazione delle partite caricate finora...")))
                break
            if now - last_print >= pgn_search.OGNI_QUANTO and avanzamento is not None:
                mb = downloaded / (1024 * 1024)
                avanzamento(pulita(_("\rScaricamento in corso: {mb:.2f} MB ({elapsed:.0f}s)...\r").format(mb=mb, elapsed=elapsed)))
                last_print = now
    return b"".join(data)


def carica(tipo, sorgente, avanzamento=None, fermato=None):
    """L'archivio da un file, da un indirizzo o da un testo, come
    pgn_search.tipo_di_sorgente; restituisce (Archivio o None, righe). Le
    righe dell'avanzamento vanno ad avanzamento, al piu' ogni tre secondi;
    fermato(), vero, ferma lo scaricamento o la lettura e tiene quello che
    e' arrivato. Gira in un filo: non tocca la finestra."""
    pulita = pgn_search.pulita
    righe = []
    percorso = None
    dati = None
    if tipo == "file":
        righe.append(pulita(_("Rilevato percorso file: {path}").format(path=sorgente)))
        try:
            with open(sorgente, "rb") as file:
                dati = file.read()
        except OSError as e:
            righe.append(pulita(_("Errore nella lettura del file: {e}").format(e=e)))
            return None, righe
        percorso = sorgente
    elif tipo == "url":
        righe.append(pulita(_("Rilevato URL: {url}").format(url=sorgente)))
        try:
            dati = _scarica(sorgente, righe, avanzamento, fermato)
        # Gli archivi PGN arrivano da fuori e possono essere malformati
        # in modi imprevedibili.
        except Exception as e:  # noqa: BLE001
            if hasattr(e, "code") and hasattr(e, "reason"):
                righe.append(pulita(_("Errore HTTP durante il download: {code} {reason}").format(code=e.code, reason=e.reason)))
            else:
                righe.append(pulita(_("Errore nel download: {e}").format(e=e)))
            return None, righe
    else:
        testo = sorgente.strip()
        if not testo:
            righe.append(_("Gli appunti sono vuoti."))
            return None, righe
        if "[" not in testo and "1." not in testo:
            righe.append(_("Il testo negli appunti non sembra contenere dati PGN validi."))
            return None, righe
    if dati is not None:
        testo, cattive, a_capo, bom = decodifica(dati)
    else:
        testo, cattive, a_capo, bom = testo.replace("\r\n", "\n") + "\n", [], "\n", False
    if not testo.strip():
        righe.append(_("Nessun contenuto PGN trovato."))
        return None, righe

    def letti(contate):
        if avanzamento is not None:
            avanzamento(pulita(_("\rPartite caricate: {n}...").format(n=contate)))

    def interrotta(e):
        righe.append(pulita(_("Lettura interrotta: il PGN non e' leggibile da questo punto in poi. {errore}").format(errore=e)))

    pezzi, schede, info = leggi(testo, cattive, letti, interrotta, fermato)
    if fermato is not None and fermato() and schede:
        righe.append(_("Lettura fermata: tengo le partite lette finora."))
    righe.extend(pulita(riga) for riga in pgn_search.righe_dell_esito(len(schede), 0))
    if not schede:
        return None, righe
    return Archivio(testo, pezzi, schede, info, percorso, a_capo, bom), righe


# L'archivio e l'albero.


class Archivio:
    """Le partite caricate: il testo, i pezzi, le schede, le intestazioni
    di estrai_info, e il giocatore principale. percorso e' il file, o None
    per gli appunti e gli indirizzi."""

    def __init__(self, testo, pezzi, schede, info, percorso=None, a_capo="\n", bom=False):
        self.testo = testo
        self.pezzi = pezzi
        self.schede = schede
        self.info = info
        self.percorso = percorso
        self.a_capo = a_capo
        self.bom = bom
        self.giocatore_comune = pgn_search._trova_giocatore_comune(info)
        # Il filo dei doppioni li segna qui, quando ha finito.
        self.doppioni_cercati = False

    def __len__(self):
        return len(self.schede)

    def testo_della_partita(self, indice):
        scheda = self.schede[indice]
        return self.testo[scheda.inizio : scheda.fine]

    def partita_intera(self, indice):
        """La partita come la legge python-chess, con varianti e commenti."""
        return chess.pgn.read_game(board_utils.RighePGN(self.testo_della_partita(indice)))

    def nell_albero(self, indice):
        scheda = self.schede[indice]
        return not scheda.fuori and len(scheda.mosse) > 0

    def linee_di(self, indici):
        """Le linee delle varianti delle partite: [(partita, linea)]."""
        return [(indice, numero) for indice in indici for numero in range(len(self.schede[indice].linee))]

    def figli(self, indici, linee, profondita):
        """Dopo tante mosse quante profondita: [(mossa, partite, linee,
        varianti)], dalla piu' giocata, a parita' nell'ordine dell'archivio;
        partite sono quelle che l'hanno giocata, varianti [(partita, linea)]
        quelle che ci arrivano solo da una variante. Poi le partite che
        finiscono li', e quelle che ci finiscono con una variante."""
        gruppi = {}
        finite = []
        for indice in indici:
            mosse = self.schede[indice].mosse
            if len(mosse) > profondita:
                gruppi.setdefault(mosse[profondita], []).append(indice)
            else:
                finite.append(indice)
        dalle_varianti = {}
        finite_varianti = {}
        presenti = set(indici)
        for indice, numero in linee:
            linea = self.schede[indice].linee[numero]
            if len(linea) > profondita:
                dalle_varianti.setdefault(linea[profondita], []).append((indice, numero))
            elif indice not in presenti:
                finite_varianti.setdefault(indice, (indice, numero))
        rami = []
        for codice_della_mossa in [*gruppi, *(c for c in dalle_varianti if c not in gruppi)]:
            partite = gruppi.get(codice_della_mossa, [])
            coppie = dalle_varianti.get(codice_della_mossa, [])
            giocata = set(partite)
            varianti = {}
            for indice, numero in coppie:
                if indice not in giocata:
                    varianti.setdefault(indice, (indice, numero))
            rami.append((mossa(codice_della_mossa), partite, coppie, list(varianti.values())))
        rami.sort(key=lambda ramo: (len(ramo[1]), len(ramo[3])), reverse=True)
        return rami, finite, list(finite_varianti.values())

    def non_classificate(self, indici):
        """I gruppi delle non classificate: senza mosse, da una posizione di
        studio, nell'albero senza codice ECO."""
        senza_mosse, studio, senza_eco = [], [], []
        for indice in indici:
            scheda = self.schede[indice]
            if scheda.fuori:
                studio.append(indice)
            elif not len(scheda.mosse):
                senza_mosse.append(indice)
            elif not self.info[indice]["ECO"]:
                senza_eco.append(indice)
        return senza_mosse, studio, senza_eco

    def problemi(self, indici):
        """{tipo: [partite]} delle partite di indici coi problemi."""
        trovati = {}
        for indice in indici:
            for tipo in self.schede[indice].problemi or ():
                trovati.setdefault(tipo, []).append(indice)
        return trovati

    def con_problemi(self, indici):
        return [indice for indice in indici if self.schede[indice].problemi]

    def statistiche(self, indici, filtri):
        return pgn_search._formato_statistiche(self.info, indici, filtri, self.giocatore_comune)

    def partita(self, indice):
        """Bianco vs Nero, risultato."""
        info = self.info[indice]
        return _("{bianco} vs {nero}, {risultato}").format(bianco=info["White"], nero=info["Black"], risultato=info["Result"])

    def continuazione(self, scacchiera, mosse, profondita, quante=5):
        """Le mosse che seguono il ramo, come nel terminale: 2... Nc6 3. Bb5 a6."""
        board = scacchiera.copy(stack=False)
        parti = []
        for numero in mosse[profondita : profondita + quante]:
            giocata = mossa(numero)
            san = board.san(giocata)
            if board.turn == chess.WHITE:
                parti.append(f"{board.fullmove_number}. {san}")
            elif not parti:
                parti.append(f"{board.fullmove_number}... {san}")
            else:
                parti.append(san)
            board.push(giocata)
        return " ".join(parti)

    def voce_della_lista(self, scacchiera, indice, profondita, numero, linea=None):
        """Una riga delle partite del ramo, come le stampava il terminale;
        con linea, il numero di una variante, la partita ci arriva da li'."""
        info = self.info[indice]
        valore = info["Result"]
        scheda = self.schede[indice]
        if linea is not None:
            valore += ", " + _("variante")
        if not scheda.fuori:
            mosse = scheda.mosse if linea is None else scheda.linee[linea]
            continuazione = self.continuazione(scacchiera, mosse, profondita)
            if continuazione:
                valore += ", " + continuazione
        return "{w} vs {b} ({num}): {valore}".format(w=info["White"], b=info["Black"], num=numero, valore=valore)


def scacchiera_del_percorso(percorso):
    board = chess.Board()
    for giocata in percorso:
        board.push(giocata)
    return board


def voce_della_radice(archivio, indici, filtri):
    return _("{ramo} ({n} partite) | {statistiche}").format(ramo=_("(radice)"), n=len(indici), statistiche=archivio.statistiche(indici, filtri))


def voce_del_ramo(archivio, scacchiera, giocata, partite, varianti, totale, filtri):
    """La voce di una mossa, con le statistiche del terminale delle sole
    partite giocate e quelle delle varianti contate a parte; con una partita
    sola e' la foglia, e dice la partita."""
    san = scacchiera.san(giocata)
    try:
        descrizione = board_utils.DescribeMove(giocata, scacchiera)
    # Gli archivi PGN arrivano da fuori e possono essere malformati
    # in modi imprevedibili.
    except Exception:  # noqa: BLE001
        descrizione = san
    n, v = len(partite), len(varianti)
    if n == 1 and not v:
        return _("{descrizione} ({mossa}): {partita}").format(descrizione=descrizione, mossa=san, partita=archivio.partita(partite[0]))
    if not n and v == 1:
        return _("{descrizione} ({mossa}): {partita}, in una variante").format(descrizione=descrizione, mossa=san, partita=archivio.partita(varianti[0][0]))
    if not n:
        return _("{descrizione} ({mossa}) ({v} partite dalle varianti)").format(descrizione=descrizione, mossa=san, v=v)
    pct = n / totale * 100 if totale else 0
    statistiche = archivio.statistiche(partite, filtri)
    if v:
        return _("{descrizione} ({mossa}) ({n} partite, piu' {v} dalle varianti) = {pct:.1f}% | {statistiche}").format(
            descrizione=descrizione, mossa=san, n=n, v=v, pct=pct, statistiche=statistiche)
    return _("{descrizione} ({mossa}) ({n} partite) = {pct:.1f}% | {statistiche}").format(
        descrizione=descrizione, mossa=san, n=n, pct=pct, statistiche=statistiche)


def voce_della_variante_finita(archivio, indice):
    return _("{partita}, in una variante").format(partita=archivio.partita(indice))


def voce_del_gruppo(nome, n):
    """Le voci dei rami fuori dalle mosse: Non classificate (3 partite)."""
    return _("{ramo} ({n} partite)").format(ramo=nome, n=n)


def voce_dei_problemi(n, avanzamento=None):
    """La voce del ramo Con errori; avanzamento, la percentuale della ricerca
    dei doppioni, finche' non e' finita."""
    if avanzamento is None:
        return voce_del_gruppo(_("Con errori"), n)
    return _("{ramo} ({n} partite), ricerca dei doppioni al {pct}%").format(ramo=_("Con errori"), n=n, pct=avanzamento)


def dettaglio(tipo, valore):
    """Cosa non va, per la foglia di un problema; None se il tipo basta."""
    if tipo in ("mosse", "data", "elo"):
        return valore
    if tipo == "intestazioni":
        return ", ".join(valore)
    if tipo == "risultato":
        come, risultato = valore
        if come == "posizione":
            return _("la posizione dice {risultato}").format(risultato=risultato)
        return _("in fondo alle mosse {segno}").format(segno=risultato)
    if tipo == "doppioni":
        return _("uguale alla partita {n}").format(n=valore + 1)
    return None


def voce_del_problema(archivio, indice, tipo):
    valore = dettaglio(tipo, archivio.schede[indice].problemi[tipo])
    if valore is None:
        return archivio.partita(indice)
    return _("{partita}: {dettaglio}").format(partita=archivio.partita(indice), dettaglio=valore)


def sequenza_del_percorso(percorso):
    """La linea dalla prima mossa: 1. e4 e5 2. Nf3, o (radice)."""
    board = chess.Board()
    mosse = []
    for giocata in percorso:
        mosse.append(board.san(giocata))
        board.push(giocata)
    return pgn_search._formatta_sequenza_mosse(mosse)


def righe_dell_archivio(archivio):
    """Le statistiche generali del terminale, per l'area in cima alla
    finestra."""
    pulita = pgn_search.pulita
    righe = [pulita(riga) for riga in pgn_search.righe_delle_statistiche(len(archivio), archivio.info)]
    if archivio.giocatore_comune:
        righe.extend(pulita(riga) for riga in pgn_search.righe_del_giocatore_comune(archivio.giocatore_comune))
    if len(archivio) < 20:
        righe.append(pulita(_("\nAttenzione: l'archivio contiene solo {n} partite (minimo consigliato: 20).").format(n=len(archivio))))
    return [riga for riga in righe if riga]


def testo_delle_partite(archivio, indici):
    """Le partite di indici com'erano nel testo, una dopo l'altra, divise
    da una riga vuota."""
    parti = []
    for indice in indici:
        pezzo = archivio.testo_della_partita(indice).strip("\n")
        parti.append(pezzo + "\n\n")
    return "".join(parti)


def scrivi_pgn(percorso, archivio, indici):
    """Le partite di indici nel file, con varianti e commenti, com'erano."""
    with open(percorso, "w", encoding="utf-8") as file:
        file.write(testo_delle_partite(archivio, indici))


# I doppioni, nel filo, mentre si naviga.


def cerca_i_doppioni(archivio, avanzamento=None, fermato=None):
    """{partita: prima uguale} per le copie di una partita gia' vista:
    stesse mosse, stessa partenza, stessi giocatori, evento, data e
    risultato. avanzamento(percentuale) ogni tre secondi; fermato(), vero,
    ferma la ricerca e restituisce None."""
    viste = {}
    doppioni = {}
    ultima = time.time()
    totale = len(archivio)
    for indice, scheda in enumerate(archivio.schede):
        if indice % 1000 == 0:
            if fermato is not None and fermato():
                return None
            adesso = time.time()
            if avanzamento is not None and adesso - ultima >= pgn_search.OGNI_QUANTO:
                avanzamento(indice * 100 // totale)
                ultima = adesso
        info = archivio.info[indice]
        chiave = (scheda.mosse.tobytes(), scheda.fuori, info["White"], info["Black"], info["Event"], info["Date"], info["Result"])
        primo = viste.setdefault(chiave, indice)
        if primo != indice:
            doppioni[indice] = primo
    return doppioni


def segna_i_doppioni(archivio, doppioni):
    """I doppioni trovati dal filo nelle schede, dal filo della finestra."""
    for indice, primo in doppioni.items():
        scheda = archivio.schede[indice]
        scheda.problemi = {**(scheda.problemi or {}), "doppioni": primo}
    archivio.doppioni_cercati = True


# Le modifiche al testo delle partite.


def _valore(testo):
    return testo.replace("\\", "\\\\").replace('"', '\\"')


def _testa(righe):
    """Dove finiscono le intestazioni: (prima, dopo l'ultima), o la prima
    riga delle mosse due volte, se non ce ne sono."""
    prima = None
    ultima = None
    for numero, riga in enumerate(righe):
        pulita = riga.strip()
        if not pulita and prima is None:
            continue
        if pulita.startswith("%") and prima is None:
            continue
        if pulita.startswith("["):
            prima = numero if prima is None else prima
            ultima = numero
            continue
        if prima is None:
            return numero, numero
        break
    if prima is None:
        return len(righe), len(righe)
    return prima, ultima + 1


def metti_le_intestazioni(testo, valori):
    """Il testo di una partita con le intestazioni di valori, {tag: valore}:
    quelle che ci sono cambiano valore, le altre si aggiungono dopo
    l'ultima, nell'ordine di valori. Il resto resta com'era."""
    righe = testo.split("\n")
    prima, dopo = _testa(righe)
    da_mettere = dict(valori)
    for numero in range(prima, dopo):
        trovata = INTESTAZIONE.match(righe[numero].strip())
        if trovata and trovata.group(1) in da_mettere:
            righe[numero] = f'[{trovata.group(1)} "{_valore(da_mettere.pop(trovata.group(1)))}"]'
    nuove = [f'[{tag} "{_valore(valore)}"]' for tag, valore in da_mettere.items()]
    if nuove:
        if prima == dopo:
            # Senza intestazioni: in cima, con la riga vuota prima delle mosse.
            nuove.append("")
        righe[dopo:dopo] = nuove
    return "\n".join(righe)


def metti_il_segno(testo, risultato):
    """Il testo di una partita col segno del risultato in fondo alle mosse:
    quello che c'e' cambia, se manca si aggiunge."""
    corpo = testo.rstrip()
    coda = testo[len(corpo) :]
    righe = corpo.split("\n")
    _prima, dopo = _testa(righe)
    if dopo >= len(righe):
        return corpo + "\n\n" + risultato + coda
    trovato = SEGNO.search(corpo)
    if trovato is not None and trovato.start() >= sum(len(riga) + 1 for riga in righe[:dopo]):
        return corpo[: trovato.start()] + risultato + coda
    return corpo + " " + risultato + coda


def data_riscritta(data):
    """2024-05-03, 2024/5/3 e 2024 come le vuole il PGN; None per quelle
    che non si possono capire, come 03.05.2024."""
    trovata = DATA_DA_RISCRIVERE.match(data.strip())
    if trovata is None:
        return None
    anno, mese, giorno = trovata.groups()

    def due(parte):
        if parte is None or parte == "??":
            return "??"
        return parte.zfill(2)

    return f"{anno}.{due(mese)}.{due(giorno)}"


def ripara(archivio, indici, tipi):
    """Le riparazioni dei problemi di tipi nelle partite di indici:
    (cambi, tolte, conti). cambi e' {partita: testo nuovo}, tolte i
    doppioni, conti {voce: numero} per il resoconto."""
    cambi = {}
    tolte = set()
    conti = dict.fromkeys(("intestazioni", "risultato", "data", "doppioni", "codifica", "mosse", "risultato_lasciato", "data_lasciata", "elo"), 0)
    for indice in indici:
        problemi = archivio.schede[indice].problemi or {}
        if "doppioni" in problemi and "doppioni" in tipi:
            tolte.add(indice)
            conti["doppioni"] += 1
            continue
        valori = {}
        segno = None
        risultato = problemi.get("risultato")
        atteso = risultato[1] if risultato and risultato[0] == "posizione" else None
        if "intestazioni" in problemi and "intestazioni" in tipi:
            for tag in problemi["intestazioni"]:
                if tag == "Result":
                    valori[tag] = atteso or archivio.info[indice]["Result"] or "*"
                else:
                    valori[tag] = VALORI_IGNOTI.get(tag, "?")
            conti["intestazioni"] += 1
        if risultato and "risultato" in tipi:
            if atteso is not None:
                valori["Result"] = segno = atteso
                conti["risultato"] += 1
            else:
                conti["risultato_lasciato"] += 1
        if "data" in problemi and "data" in tipi:
            nuova = data_riscritta(problemi["data"])
            if nuova is None:
                conti["data_lasciata"] += 1
            else:
                valori["Date"] = nuova
                conti["data"] += 1
        if "elo" in problemi and "elo" in tipi:
            conti["elo"] += 1
        if "mosse" in problemi and "mosse" in tipi:
            conti["mosse"] += 1
        if "codifica" in problemi and "codifica" in tipi:
            conti["codifica"] += 1
        if valori or segno:
            testo = archivio.testo_della_partita(indice)
            if valori:
                testo = metti_le_intestazioni(testo, valori)
            if segno:
                testo = metti_il_segno(testo, segno)
            cambi[indice] = testo
    return cambi, tolte, conti


def righe_della_riparazione(conti):
    """Il resoconto di Ripara, una riga per voce che c'e'."""
    voci = (
        ("intestazioni", _("Intestazioni aggiunte: {n} partite.")),
        ("risultato", _("Risultati corretti: {n}.")),
        ("data", _("Date riscritte: {n}.")),
        ("doppioni", _("Doppioni tolti: {n}.")),
        ("codifica", _("Partite coi caratteri riletti: {n}.")),
        ("mosse", _("Mosse illegali, da sistemare a mano: {n} partite.")),
        ("risultato_lasciato", _("Risultati da verificare a mano: {n}.")),
        ("data_lasciata", _("Date da riscrivere a mano: {n}.")),
        ("elo", _("Elo non numerici, da sistemare a mano: {n} partite.")),
    )
    return [testo.format(n=conti[voce]) for voce, testo in voci if conti.get(voce)]


def carica_le_aperture():
    """eco.db, senza le righe che stampa nell'area principale."""
    with contextlib.redirect_stdout(io.StringIO()):
        return board_utils.LoadEcoDatabaseWithFEN("eco.db")


def classifica(archivio, indici, aperture, avanzamento=None, fermato=None):
    """Le intestazioni ECO, Opening e Variation da eco.db per le partite di
    indici che le mosse fanno riconoscere: (cambi, riconosciute).
    avanzamento(percentuale) ogni tre secondi; fermato() ferma il lavoro e
    tiene quello che e' fatto."""
    cambi = {}
    ultima = time.time()
    for numero, indice in enumerate(indici):
        if fermato is not None and fermato():
            break
        adesso = time.time()
        if avanzamento is not None and adesso - ultima >= pgn_search.OGNI_QUANTO:
            avanzamento(numero * 100 // len(indici))
            ultima = adesso
        mosse = [mossa(numero_della_mossa) for numero_della_mossa in archivio.schede[indice].mosse]
        voce, _semimosse = board_utils.rileva_apertura(mosse, aperture)
        if voce is None or not voce.get("eco"):
            continue
        valori = {"ECO": voce["eco"]}
        if voce.get("opening"):
            valori["Opening"] = voce["opening"]
        if voce.get("variation"):
            valori["Variation"] = voce["variation"]
        cambi[indice] = metti_le_intestazioni(archivio.testo_della_partita(indice), valori)
    return cambi


# La riscrittura.


def copia_di_sicurezza(percorso):
    """Il file com'era, nella cartella pgn, col nome e l'ora: il percorso."""
    cartella = config.percorso_salvataggio("pgn")
    os.makedirs(cartella, exist_ok=True)
    nome, estensione = os.path.splitext(os.path.basename(percorso))
    radice = "{nome} {copia} {quando}".format(nome=nome, copia=_("copia"), quando=time.strftime("%Y%m%d-%H%M%S"))
    copia = os.path.join(cartella, radice + (estensione or ".pgn"))
    # Due copie nello stesso secondo non si sovrascrivono: la prima e'
    # l'originale.
    numero = 2
    while os.path.exists(copia):
        copia = os.path.join(cartella, f"{radice} {numero}{estensione or '.pgn'}")
        numero += 1
    shutil.copy2(percorso, copia)
    return copia


def scrivi_il_file(percorso, testo, a_capo="\n", bom=False):
    """Il testo nel file, in UTF-8, coi ritorni a capo del file: prima in un
    file accanto, poi al posto dell'originale."""
    if a_capo != "\n":
        testo = testo.replace("\n", a_capo)
    temporaneo = percorso + ".orologic"
    with open(temporaneo, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as file:
        file.write(testo)
    os.replace(temporaneo, percorso)


def riscritto(archivio, cambi, tolte=()):
    """L'archivio col testo nuovo: le partite di cambi col loro testo, senza
    quelle di tolte, tutto il resto com'era. Le partite cambiate si
    rileggono; i caratteri illeggibili non ci sono piu', perche' il testo e'
    gia' decodificato e si riscrive in UTF-8. I doppioni si cercano di
    nuovo."""
    parti = []
    posizione = 0
    pezzi, schede, info = [], [], []
    da_rileggere = []
    for inizio, fine, indice in archivio.pezzi:
        if indice is not None and indice in tolte:
            continue
        pezzo = cambi[indice] if indice in cambi else archivio.testo[inizio:fine]
        nuovo_inizio = posizione
        parti.append(pezzo)
        posizione += len(pezzo)
        if indice is None:
            pezzi.append((nuovo_inizio, posizione, None))
            continue
        pezzi.append((nuovo_inizio, posizione, len(schede)))
        if indice in cambi:
            da_rileggere.append(len(schede))
            schede.append(None)
            info.append(None)
            continue
        scheda = archivio.schede[indice].spostata(nuovo_inizio, posizione)
        scheda.problemi = _senza(scheda.problemi, ("codifica", "doppioni"))
        schede.append(scheda)
        info.append(archivio.info[indice])
    testo = "".join(parti)
    for nuovo in da_rileggere:
        inizio, fine, _indice = next(pezzo for pezzo in pezzi if pezzo[2] == nuovo)
        letta = chess.pgn.read_game(board_utils.RighePGN(testo[inizio:fine]), Visitor=_Costruttore)
        scheda, dati = _scheda(letta, inizio, fine, pgn_search._partita_da_tenere(letta[0]) == "esclusa")
        scheda.problemi = _senza(scheda.problemi, ("codifica",))
        schede[nuovo] = scheda
        info[nuovo] = dati
    return Archivio(testo, pezzi, schede, info, archivio.percorso, archivio.a_capo, archivio.bom)


def _senza(problemi, tipi):
    if not problemi:
        return None
    rimasti = {tipo: valore for tipo, valore in problemi.items() if tipo not in tipi}
    return rimasti or None


def applica_le_modifiche(archivio, cambi, tolte=(), riscrivi_comunque=False):
    """Le modifiche, nel file se l'archivio ne ha uno, dopo la copia di
    sicurezza: (archivio nuovo, righe del resoconto). Senza file restano
    nell'archivio aperto. riscrivi_comunque riscrive il file anche senza
    cambi, per i caratteri."""
    righe = []
    if not cambi and not tolte and not riscrivi_comunque:
        return archivio, righe
    nuovo = riscritto(archivio, cambi, tolte)
    if archivio.percorso is None:
        righe.append(_("Le modifiche restano nell'archivio aperto: per tenerle, Salva il PGN."))
        return nuovo, righe
    copia = copia_di_sicurezza(archivio.percorso)
    righe.append(pgn_search.pulita(_("Copia di sicurezza: {percorso}").format(percorso=copia)))
    scrivi_il_file(archivio.percorso, nuovo.testo, archivio.a_capo, archivio.bom)
    righe.append(pgn_search.pulita(_("File riscritto: {percorso}").format(percorso=archivio.percorso)))
    return nuovo, righe


class Ricerca:
    """Lo stato della ricerca nella finestra, che resta fra un'apertura e
    l'altra: dopo Easyfish o l'analisi si torna allo stesso punto.
    indirizzo e' quello del profilatore, da caricare alla prima apertura;
    posizione la voce dell'albero, come le chiavi delle voci dalla radice."""

    def __init__(self, indirizzo=None):
        self.indirizzo = indirizzo
        self.archivio = None
        self.righe = []
        self.filtri = {}
        self.posizione = None
