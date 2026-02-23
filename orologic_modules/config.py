import sys
import os
import json
import chess
import re
from GBUtils import polipo
from . import version

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def percorso_salvataggio(relative_path):
    if getattr(sys, 'frozen', False): base_path = os.path.dirname(sys.executable)
    else: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Inizializzazione localizzazione base
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

STOCKFISH_DOWNLOAD_URL = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
VERSION = version.VERSION
PROGRAMMER = version.PROGRAMMER
DB_FILE = percorso_salvataggio(os.path.join("settings", "orologic_db.json"))

# Caricamento Volume
try:
    with open(DB_FILE, "r", encoding="utf-8") as f:
        _db_data = json.load(f); VOLUME = _db_data.get("volume", 1.0)
except: VOLUME = 1.0

PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}

# Mappe per i NAG (Numeric Annotation Glyphs)
NAG_MAP = {
	"!": (1, _("mossa forte")),
	"?": (2, _("mossa debole")),
	"!!": (3, _("mossa molto forte")),
	"??": (4, _("mossa molto debole")),
	"!?": (5, _("mossa dubbia")),
	"?!": (6, _("mossa dubbia")),
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}

# Pattern Regex per estrarre il suffisso di annotazione (1 o 2 caratteri !?=) alla fine della stringa.
# Il lookbehind (?<!=.) evita di catturare l'uguale della promozione (es. non matcha '=Q').
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
# Pattern Regex specifico per gestire i suffissi DOPO una promozione (es. "d8=Q!")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")

def get_default_localization():
	return {
		"pieces": {
			"pawn": {"name": "pedone", "gender": "m"},
			"knight": {"name": "cavallo", "gender": "m"},
			"bishop": {"name": "alfiere", "gender": "m"},
			"rook": {"name": "torre", "gender": "f"},
			"queen": {"name": "donna", "gender": "f"},
			"king": {"name": "Re", "gender": "m"}
		},
		"columns": {
			"a": "Ancona", "b": "Bologna", "c": "Como", "d": "Domodossola",
			"e": "Empoli", "f": "Firenze", "g": "Genova", "h": "Hotel"
		},
		"adjectives": {
			"white": {"m": "bianco", "f": "bianca"},
			"black": {"m": "nero", "f": "nera"}
		},
		"moves": {
			"capture": "prende",
			"capture_on": "in",
			"move_to": "in",
			"en_passant": "en passant",
			"short_castle": "arrocco corto",
			"long_castle": "arrocco lungo",
			"promotes_to": "e promuove a",
			"check": "scacco",
			"checkmate": "scacco matto!"
		},
		"annotations": {
			"=": "proposta di patta",
			"?": "mossa debole",
			"!": "mossa forte",
			"??": "mossa pessima",
			"!!": "mossa geniale!",
			"?!": "mossa dubbia",
			"!?": "mossa dubbia"
		}
	}

def recursive_merge(base, user):
    for k, v in user.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict): recursive_merge(base[k], v)
        else: base[k] = v
    return base

def LoadLocalization():
    l10n = get_default_localization()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f); user_l10n = db.get("localization", {})
            if user_l10n: l10n = recursive_merge(l10n, user_l10n)
    except: pass
    return l10n

L10N = LoadLocalization()

SMART_COMMANDS = {
	"s": _("Vai alla mossa precedente"),
	"d": _("Vai alla mossa successiva"),
	"r": _("Aggiorna valutazione CP"),
	"?": _("Visualizza questa lista di comandi"),
	".": _("Esci dalla modalita' smart")
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
	"l": _("Carica il PGN	dagli appunti"),
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
	".5":_("Stato orologi/pausa"),
	".l":_("Visualizza la lista mosse giocate"),
	".m":_("Mostra il valore del materiale ancora in gioco"),
	".p":_("Pausa/Ripresa"),
	".q":_("Annulla mossa (in pausa)"),
	".b+":_("Aggiunge tempo al bianco (in pausa)"),
	".b-":_("Sottrae tempo al bianco (in pausa)"),
	".n+":_("Aggiunge tempo al nero (in pausa)"),
	".n-":_("Sottrae tempo al nero (in pausa)"),
	".s":_("Scacchiera"),
	".c":_("Commento mossa"),
	".?":_("Aiuto")
}

MENU_CHOICES={
    "analizza":_("Modalita' analisi partita"),
    "crea":_("Nuovo orologio"),
    "easyfish":_("Easyfish (Interfaccia Accessibile)"),
    "elimina":_("Elimina orologio"),
    "arbitra":_("Inizia partita (Arbitraggio)"),
    "manuale":_("Guida app"),
    "motore":_("Configurazione motore"),
    "nomi":_("Personalizzazione nomi"),
    "impostazioni":_("Impostazioni varie"),
    "vedi":_("Vedi orologi"),
    "volume":_("Regolazione volume"),
    ".":_("Esci")
}

FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}

def sanitize_filename(filename):
    s = re.sub(r'[\\/:*?"<>|]', '_', filename)
    s = re.sub(r'[\0-\31]', '', s)
    return s.strip().strip('. ') or "default"
