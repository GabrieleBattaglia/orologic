import os
import chess
# Import translator function
try:
    from ...config import _
except ImportError:
    # Fallback for standalone testing or if import fails
    def _(text): return text

# Version info
VER="0.22.0, Feb 22nd, 2026"  # Updated version for refactoring start

# File paths
CONFIG_FILE = "easyfish.json"
PGN_FILE_PATH = "Easyfish games collection.pgn"

# Defaults
DEFAULT_EVENT=_("Divertimento con Easyfish")
DEFAULT_SITE=os.getenv('COMPUTERNAME')+"'s PC"
DEFAULT_ROUND="-"
DEFAULT_WHITE_SURENAME=_("Bianco")
DEFAULT_WHITE_FIRSTNAME="Gabe"
DEFAULT_BLACK_SURENAME=_("Nero")
DEFAULT_BLACK_FIRSTNAME="Ginny"

# Chess conversion maps
COLUMN_TO_NATO = {
    'a': "alpha",
    'b': "bravo",
    'c': "charlie",
    'd': "delta",
    'e': "echo",
    'f': "foxtrot",
    'g': "golf",
    'h': "hotel"}

CHESSPIECE_TO_NAME = {
    chess.PAWN: _("Pedone"),
    chess.KNIGHT: _("Cavallo"),
    chess.BISHOP: _("Alfiere"),
    chess.ROOK: _("Torre"),
    chess.QUEEN: _("Donna"),
    chess.KING: _("Re")}

PIECE_VALUES={
    'R':5,
    'r':5,
    'N':3,
    'n':3,
    'B':3,
    'b':3,
    'Q':9,
    'q':9,
    'P':1,
    'p':1,
    'K':0,
    'k':0}

SAN_CHESSPIECES = {
    'P': chess.PAWN, 'N': chess.KNIGHT, 'B': chess.BISHOP,
    'R': chess.ROOK, 'Q': chess.QUEEN, 'K': chess.KING,
    'p': chess.PAWN, 'n': chess.KNIGHT, 'b': chess.BISHOP,
    'r': chess.ROOK, 'q': chess.QUEEN, 'k': chess.KING}

SYMBOLS_TO_NAME={
    'R':_('Torre bianca'),
    'r':_('Torre nera'),
    'N':_('Cavallo bianco'),
    'n':_('Cavallo nero'),
    'B':_('Alfiere bianco'),
    'b':_('Alfiere nero'),
    'Q':_('Donna bianca'),
    'q':_('Donna nera'),
    'K':_('Re bianco'),
    'k':_('Re nero'),
    'P':_('Pedone bianco'),
    'p':_('Pedone nero')}

# Menus
MNMAIN={'.q':_("Esci dall'applicazione"),
        '.?':_("Mostra questo menu"),
        '_[comment]':_("Aggiungi un commento alla mossa corrente"),
        '.a#':_("Analizza la posizione per # secondi"),
        '.b':_("Mostra la scacchiera"),
        '.be':_("Editor della scacchiera"),
        '.bm':_("Bilancio materiale"),
        '.e':_("Modalità esplorazione"),
        '.fg':_("FEN in Partita. Incolla dagli appunti"),
        '.gf':_("Partita in FEN. Copia negli appunti"),
        '.gp':_("Partita in PGN. Copia negli appunti"),
        '.pg':_("PGN in Partita. Incolla dagli appunti"),
        '.l#':_("Vedi Linea/e di Analisi"),
        '.n':_("Nuova partita da zero"),
        '.pt':_("Imposta i Tag PGN per la partita corrente"),
        '.snl':_("Imposta il numero di linee di analisi"),
        '.ssf':_("Mostra il file delle impostazioni"),
        ',[piece]':_("Nome di un pezzo per localizzarlo"),
        '-[piecesquare]':_("Pezzo e casa per vederne le mosse"),
        '-[column]':_("Colonna da A a H per vedere i pezzi presenti"),
        '-[row]':_("Riga da 1 a 8 per vedere i pezzi presenti"),
        '[move]':_("Qualsiasi mossa legale in formato SAN, es. d4")}

MNEXPLORER={'a':_("Vai alla mossa precedente"),
            'd':_("Vai alla mossa successiva"),
            'w':_("Su (selezione variante)"),
            'x':_("Giù (selezione variante)"),
            'q':_("Salta alla prima mossa"),
            'e':_("Salta all'ultima mossa"),
            'z':_("Esci dalla variante corrente"),
            'c':_("Mostra di nuovo il commento"),
            's':_("Esegui analisi"),
            'r':_("Imposta i secondi per l'analisi"),
            '?':_("Vedi questo aiuto"),
            '[esc]':_("Torna al menu principale")}
