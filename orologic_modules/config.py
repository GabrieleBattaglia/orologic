import sys
import os
import chess
from GBUtils import polipo

def resource_path(relative_path):
    """
    Restituisce il percorso assoluto a una risorsa, funzionante sia in sviluppo
    che per un eseguibile compilato con PyInstaller (anche con la cartella _internal).
    """
    try:
        # PyInstaller crea una cartella temporanea e ci salva il percorso in _MEIPASS
        # Questo è il percorso base per le risorse quando l'app è "congelata"
        base_path = sys._MEIPASS
    except Exception:
        # Se _MEIPASS non esiste, non siamo in un eseguibile PyInstaller
        # o siamo in una build onedir, il percorso base è la cartella dello script
        # Nota: in sviluppo orologic_modules è una sottocartella, quindi dobbiamo salire di un livello
        # se questo file è eseguito direttamente, ma qui stiamo definendo una funzione usata altrove.
        # Per coerenza con l'originale che assumeva esecuzione dalla root:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def percorso_salvataggio(relative_path):
    """
    Restituisce un percorso scrivibile vicino allo script .py o all'eseguibile .exe.
    Ideale per salvare impostazioni, PGN e altri file utente.
    """
    if getattr(sys, 'frozen', False):
        # Siamo in un eseguibile compilato (es. .exe).
        # os.path.dirname(sys.executable) ci dà la cartella che contiene l'eseguibile.
        base_path = os.path.dirname(sys.executable)
    else:
        # Non siamo compilati, quindi siamo in modalità sviluppo.
        # os.path.abspath(".") ci dà la cartella dove si trova lo script principale.
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Inizializzazione localizzazione base per le stringhe statiche
# (Nota: la lingua effettiva potrebbe essere ricaricata, ma serve per le stringhe qui sotto se usano _())
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

STOCKFISH_DOWNLOAD_URL = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
ENGINE_NAME = "Nessuno" 
STILE_MENU_NUMERICO = False
DB_FILE = percorso_salvataggio(os.path.join("settings", "orologic_db.json"))
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
oaa_analysis_cache = {}
NAG_MAP = {
    "!": (1, _("mossa forte")),
    "?": (2, _("mossa debole")),
    "!!": (3, _("mossa molto forte")),
    "??": (4, _("mossa molto debole")),
    "!?": (5, _("mossa dubbia")),
    "?!": (6, _("mossa dubbia")),
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}
L10N = {}

# Pattern Regex
import re
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")

SMART_COMMANDS = {
    "s": _("Vai alla mossa precedente"),
    "d": _("Vai alla mossa successiva"),
    "r": _("Aggiorna valutazione CP"),
    "?": _("Visualizza questa lista di comandi"),
    ".": _("Esci dalla modalità smart")
}

ANALYSIS_COMMAND = {
    "a": _("Vai all'inizio o nodo padre (se in variante)"),
    "s": _("Indietro di 1 mossa"),
    "d": _("Avanti di 1 mossa e visualizza eventuale commento"),
    "f": _("Vai alla fine o nodo del prossimo ramo variante"),
    "g": _("Seleziona nodo variante precedente"),
    "h": _("Seleziona nodo variante successivo"),
    "j": _("Legge gli headers della partita"),
    "k": _("Vai a mossa"),
    "l": _("Carica il PGN  dagli appunti"),
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
    ".": _("Esci dalla modalità analisi e salva il PGN se diverso dall'originale")
}

DOT_COMMANDS={
    ".1":_("Mostra il tempo rimanente del bianco"),
    ".2":_("Mostra il tempo rimanente del nero"),
    ".3":_("Mostra entrambe gli orologi"),
    ".4":_("Confronta i tempi rimanenti e indica il vantaggio"),
    ".5":_("Riporta quale orologio è in moto o la durata della pausa, se attiva"),
    ".l":_("Visualizza la lista mosse giocate"),
    ".m":_("Mostra il valore del materiale ancora in gioco"),
    ".p":_("Pausa/riavvia il countdown degli orologi"),
    ".q":_("Annulla l'ultima mossa (solo in pausa)"),
    ".b+":_("Aggiunge tempo al bianco (in pausa)"),
    ".b-":_("Sottrae tempo al bianco (in pausa)"),
    ".n+":_("Aggiunge tempo al nero (in pausa)"),
    ".n-":_("Sottrae tempo al nero (in pausa)"),
    ".s":_("Visualizza la scacchiera"),
    ".c":_("Aggiunge un commento alla mossa corrente"),
    ".1-0":_("Assegna vittoria al bianco (1-0) e conclude la partita"),
    ".0-1":_("Assegna vittoria al nero (0-1) e conclude la partita"),
    ".1/2":_("Assegna patta (1/2-1/2) e conclude la partita"),
    ".*":_("Assegna risultato non definito (*) e conclude la partita"),
    ".?":_("Visualizza l'elenco dei comandi disponibili"),
    "/[colonna]":_("Mostra la diagonale alto-destra partendo dalla base della colonna data"),
    r"\[colonna]":_("Mostra la diagonale alto-sinistra partendo dalla base della colonna data"),
    "-[colonna|traversa|casa]":_("Mostra le figure su quella colonna o traversa o casa"),
    ",[NomePezzo]":_("Mostra la/le posizione/i del pezzo indicato")
}

MENU_CHOICES={
    "analizza":_("Entra in modalità analisi partita"),
    "crea":_("Aggiungi un nuovo orologio alla collezione"),
    "elimina":_("Cancella uno degli orologi salvati"),
    "gioca":_("Inizia la partita"),
    "manuale":_("Mostra la guida dell'app"),
    "motore":_("Configura le impostazioni per il motore di scacchi"),
    "nomi":_("Personalizza i nomi dei pezzi e delle colonne"),
    "impostazioni":_("Varie ed eventuali"),
    "vedi":_("Mostra gli orologi salvati"),
    "volume":_("Consente la regolazione del volume degli effetti audio"),
    ".":_("Esci dall'applicazione")
}

FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}

def sanitize_filename(filename: str) -> str:
    """
    Restituisce una versione della stringa compatibile con il filesystem,
    sostituendo i caratteri non validi (per Windows e altri sistemi) con un
    carattere di sottolineatura.
    """
    # Caratteri non consentiti in Windows: \ / : * ? " < > |
    # Inoltre, si eliminano i caratteri di controllo (ASCII 0-31)
    sanitized = re.sub(r'[\\/:*?"<>|]', '_', filename)
    sanitized = re.sub(r'[\0-\31]', '', sanitized)
    # Rimuove spazi e punti all'inizio e alla fine
    sanitized = sanitized.strip().strip('. ')
    if not sanitized:
        sanitized = _("default_filename")
    return sanitized
