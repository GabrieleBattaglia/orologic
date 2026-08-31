# Orologic, configurazione: percorsi, costanti e localizzazione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import datetime
import json
import os
import re
import sys

from GBUtils import polipo

from . import version


# I nomi di giorni e mesi passano da gettext: scritti a mano restavano
# italiani anche con l'interfaccia in inglese o portoghese.
def _giorni():
    return [
        _("lunedì"),
        _("martedì"),
        _("mercoledì"),
        _("giovedì"),
        _("venerdì"),
        _("sabato"),
        _("domenica"),
    ]


def _mesi():
    return [
        "",
        _("gennaio"),
        _("febbraio"),
        _("marzo"),
        _("aprile"),
        _("maggio"),
        _("giugno"),
        _("luglio"),
        _("agosto"),
        _("settembre"),
        _("ottobre"),
        _("novembre"),
        _("dicembre"),
    ]


def format_date_italian(dt=None, include_time=True, include_day_name=True):
    """
    Data per esteso con il giorno della settimana, nella lingua attiva.
    Esempio: 'sabato 25 luglio 2026 - 17:20' oppure 'sabato 25 luglio 2026'.
    """
    if dt is None:
        dt = datetime.datetime.now()
    elif isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt)
        except Exception:
            return dt
    day_name = _giorni()[dt.weekday()] if include_day_name else ""
    day = dt.day
    month = _mesi()[dt.month]
    year = dt.year
    date_str = f"{day_name} {day} {month} {year}".strip()
    if include_time:
        return f"{date_str} - {dt.strftime('%H:%M')}"
    return date_str


# Radice dell'applicazione: la cartella che contiene orologic.py, cioe' quella
# sopra orologic_modules. Ricavarla dal file sorgente invece che dalla directory
# di lavoro fa si' che salvataggi e risorse si trovino sempre nella stessa
# cartella, da qualunque posto venga lanciato il programma.
RADICE_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path):
    """Percorso di una risorsa inclusa nel pacchetto (manuale, changelog, eco.db)."""
    base_path = getattr(sys, "_MEIPASS", None) or RADICE_APP
    return os.path.join(base_path, relative_path)


def percorso_salvataggio(relative_path):
    """Percorso di lettura e scrittura dei dati dell'utente (pgn, txt, settings)."""
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = RADICE_APP
    return os.path.join(base_path, relative_path)


# Cartelle passate a polipo in forma assoluta: senza di questo, GBUtils le
# risolve rispetto alla directory di lavoro, quindi lanciando il programma da
# un'altra cartella le traduzioni non verrebbero trovate e la lingua scelta
# verrebbe salvata altrove.
CARTELLA_LOCALES = resource_path("locales")
CARTELLA_SETTINGS = percorso_salvataggio("settings")

# Inizializzazione localizzazione base
lingua_rilevata, _ = polipo(
    source_language="it",
    localedir=CARTELLA_LOCALES,
    config_path=CARTELLA_SETTINGS,
)

STOCKFISH_DOWNLOAD_URL = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
VERSION = version.VERSION
PROGRAMMER = version.PROGRAMMER
RELEASE_DATE = version.RELEASE_DATE
DB_FILE = percorso_salvataggio(os.path.join("settings", "orologic_db.json"))

# Il volume si legge qui a mano, e non con storage.LoadDB, perche' storage
# importa config: chiamarlo da qui creerebbe un intreccio fra i due moduli
# per una lettura sola, di un file di pochi kilobyte, fatta una volta
# all'avvio. Misurato: e' l'unica lettura durante l'import.
try:
    with open(DB_FILE, encoding="utf-8") as f:
        _db_data = json.load(f)
        VOLUME = _db_data.get("volume", 1.0)
except Exception:
    VOLUME = 1.0

PIECE_VALUES = {
    "R": 5,
    "r": 5,
    "N": 3,
    "n": 3,
    "B": 3,
    "b": 3,
    "Q": 9,
    "q": 9,
    "P": 1,
    "p": 1,
    "K": 0,
    "k": 0,
}

# Mappe per i NAG (Numeric Annotation Glyphs)
NAG_MAP = {
    "!": (1, _("mossa forte")),
    "?": (2, _("mossa debole")),
    "!!": (3, _("mossa molto forte")),
    "??": (4, _("mossa molto debole")),
    "!?": (5, _("mossa interessante")),
    "?!": (6, _("mossa dubbia")),
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}

# Pattern Regex per estrarre il suffisso di annotazione (1 o 2 caratteri !?=) alla fine della stringa.
# Il lookbehind (?<!=.) evita di catturare l'uguale della promozione (es. non matcha '=Q').
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
# Pattern Regex specifico per gestire i suffissi DOPO una promozione (es. "d8=Q!")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")


SMART_COMMANDS = {
    "s": _("Vai alla mossa precedente"),
    "d": _("Vai alla mossa successiva"),
    "r": _("Aggiorna valutazione CP"),
    "?": _("Visualizza questa lista di comandi"),
    ".": _("Esci dalla modalita' smart"),
}

ANALYSIS_COMMANDS = {
    "a": _("Vai all'inizio o nodo padre (se in variante)"),
    "s": _("Indietro di 1 mossa"),
    "d": _("Avanti di 1 mossa e visualizza eventuale commento"),
    "f": _("Vai alla fine o nodo del prossimo ramo variante"),
    "g": _("Seleziona nodo variante precedente"),
    "h": _("Seleziona nodo variante successivo"),
    "j": _("Legge gli headers della partita"),
    "k": _("Vai a mossa"),
    "l": _("Carica il PGN dagli appunti"),
    "z": _("Inserisce la bestline come variante nel PGN"),
    "x": _("Inserisce la bestmove nel PGN"),
    "c": _("Richiede un commento all'utente e lo aggiunge"),
    "v": _("Inserisce la valutazione in centipawn nel PGN"),
    "b": _("Attiva/disattiva la lettura automatica dei commenti"),
    "n": _("Elimina il commento (o consente di sceglierlo se ce ne sono più di uno)"),
    "q": _("Calcola e aggiungi la bestmove al prompt"),
    "w": _("Calcola e visualizza la bestline, aggiungendo anche la bestmove al prompt"),
    "e": _("Visualizza le linee di analisi e ne permette l'ispezione smart"),
    "r": _("Calcola e aggiungi la valutazione al prompt"),
    "t": _("Visualizza le percentuali Win Draw Lost nella posizione corrente"),
    "y": _("Aggiungi il bilancio materiale al prompt"),
    "u": _("Visualizza la scacchiera"),
    "i": _("Imposta i secondi di analisi per il motore"),
    "o": _("Imposta il numero di linee di analisi da visualizzare"),
    "?": _("Mostra questa lista di comandi"),
    ".": _("Esci dalla modalità analisi e salva il PGN se diverso dall'originale"),
}

DOT_COMMANDS = {
    ".1": _("Mostra il tempo rimanente del bianco"),
    ".2": _("Mostra il tempo rimanente del nero"),
    ".3": _("Mostra entrambi gli orologi"),
    ".4": _("Confronta i tempi rimanenti e indica il vantaggio"),
    ".5": _("Stato orologi/pausa"),
    ".6": _("Modifica timing aggiornamento orologio"),
    ".l": _("Visualizza la lista mosse giocate"),
    ".m": _("Mostra il valore del materiale ancora in gioco"),
    ".p": _("Pausa/Ripresa"),
    ".q": _("Annulla mossa (in pausa)"),
    ".b+": _("Aggiunge tempo al bianco (in pausa)"),
    ".b-": _("Sottrae tempo al bianco (in pausa)"),
    ".n+": _("Aggiunge tempo al nero (in pausa)"),
    ".n-": _("Sottrae tempo al nero (in pausa)"),
    ".s oppure .b": _("Scacchiera testuale"),
    ".c": _("Commento mossa"),
    "-": _("Riepilogo dei pezzi Bianchi"),
    "+": _("Riepilogo dei pezzi Neri"),
    "/[col]": _("Esplora diagonale alto-destra"),
    "\\[col]": _("Esplora diagonale alto-sinistra"),
    "-[col|trv|casa]": _("Esplora colonna, traversa o casa"),
    ",[P,N,B,R,Q,K]": _("Posizioni di un pezzo specifico"),
    ".?": _("Aiuto"),
}

MENU_CHOICES = {
    "analizza": _("Modalita' analisi partita"),
    "crea": _("Nuovo orologio"),
    "easyfish": _("Easyfish (Interfaccia Accessibile)"),
    "lichess": _("Orolichess (Integrazione Lichess)"),
    "memoboard": _("Memoboard (Allenamento alla cieca)"),
    "elimina": _("Elimina orologio"),
    "arbitra": _("Inizia partita (Arbitraggio)"),
    "tempo": _("Tempo (Orologio nudo e crudo)"),
    "manuale": _("Guida app"),
    "novita": _("Novita' (changelog)"),
    "motore": _("Configurazione motore"),
    "nomi": _("Personalizzazione nomi"),
    "ricerca": _("Ricerca PGN"),
    "impostazioni": _("Impostazioni varie"),
    "vedi": _("Vedi orologi"),
    "volume": _("Regolazione volume"),
    ".": _("Esci"),
}

FILE_NAMES = {
    0: "ancona",
    1: "bologna",
    2: "como",
    3: "domodossola",
    4: "empoli",
    5: "firenze",
    6: "genova",
    7: "hotel",
}


def maiuscole_nomi(testo):
    """Sistema le maiuscole di un nome solo se serve davvero.

    Chi scrive tutto in minuscolo si vede correggere, chi ha gia' usato
    le maiuscole viene lasciato in pace: title() trasformava IZ4APU in
    Iz4Apu e McDonald in Mcdonald.
    """
    pulito = (testo or "").strip()
    return pulito.title() if pulito.islower() else pulito


def sanitize_filename(filename):
    """Ripulisce un nome di file da tutto cio' che Windows rifiuta.

    I caratteri di controllo si scrivono in esadecimale: la forma ottale
    usata prima copriva da 0 a 25, quindi ne lasciava passare sei, e il
    nome veniva poi rifiutato dal sistema.
    """
    s = re.sub(r'[\\/:*?"<>|]', "_", filename)
    s = re.sub(r"[\x00-\x1f]", "", s)
    return s.strip().strip(". ") or "default"
