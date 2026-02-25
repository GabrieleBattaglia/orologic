import os
import chess
# Import translator function
try:
    from ...config import _
except ImportError:
    # Fallback for standalone testing or if import fails
    def _(text): return text

# File paths
CONFIG_FILE = "easyfish.json"

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
MNMAIN={'.':_("Esci dall'applicazione"),
        '.?':_("Mostra questo menu"),
        '_[commento]':_("Aggiungi un commento alla mossa corrente"),
        '.a#':_("Analizza la posizione per # secondi"),
        '.b':_("Mostra la scacchiera"),
        '.be':_("Editor della scacchiera"),
        '.bm':_("Bilancio materiale"),
        '.e':_("Modalità esplorazione"),
        '.fg':_("FEN in Partita. Incolla dagli appunti"),
        '.g':_("Gioca contro il motore da questa posizione"),
        '.gf':_("Partita in FEN. Copia negli appunti"),
        '.gp':_("Partita in PGN. Copia negli appunti"),
        '.k#':_("Vai alla mossa numero #"),
        '.pg':_("PGN in Partita. Incolla dagli appunti"),
        '.l#':_("Vedi Linea/e di Analisi"),
        '.n':_("Nuova partita da zero"),
        '.pt':_("Imposta i Tag PGN per la partita corrente"),
        '.v':_("Inizia una nuova variante (al prossimo inserimento mossa)"),
        '.vm':_("Promuovi la variante corrente a linea principale"),
        ',[pezzo]':_("Nome di un pezzo per localizzarlo"),
        '-[pezzo_casa]':_("Pezzo e casa per vederne le mosse"),
        '-[colonna]':_("Colonna da A a H per vedere i pezzi presenti"),
        '-[riga]':_("Riga da 1 a 8 per vedere i pezzi presenti"),
        '[mossa]':_("Qualsiasi mossa legale in formato SAN, es. d4")}

MNEXPLORER={'a':_("Vai alla mossa precedente"),
            'd':_("Vai alla mossa successiva"),
            'w':_("Su (selezione variante)"),
            'x':_("Giù (selezione variante)"),
            'u':_("Elimina (taglia) la mossa/variante corrente"),
            'q':_("Salta alla prima mossa"),
            'e':_("Salta all'ultima mossa"),
            'z':_("Esci dalla variante corrente"),
            'b':_("Mostra la scacchiera corrente"),
            'c':_("Mostra di nuovo il commento"),
            's':_("Esegui analisi"),
            'r':_("Imposta i secondi per l'analisi"),
            't':_("Imposta numero di linee di analisi"),
            '?':_("Vedi questo aiuto"),
            '.':_("Torna al menu principale")}

MNEDITOR={'.':_("Fine editing e salva posizione"),
          '--':_("Svuota la scacchiera (lascia solo i Re)"),
          '.t':_("Cambia il turno (Bianco/Nero)"),
          '.c':_("Imposta diritti di arrocco (es. KQkq)"),
          '.e':_("Imposta casa en passant (es. e3)"),
          '.n':_("Imposta numero mossa"),
          '.h':_("Imposta orologio semimosse (halfmove)"),
          '.s':_("Mostra la scacchiera corrente"),
          '.?':_("Mostra questo menu"),
          'Ke4':_("Sposta il Re in e4 (stessa cosa per il nero k)"),
          'Pe4':_("Piazza un pedone in e4"),
          'e4':_("Svuota la casa e4 (se non contiene un Re)")}

MNGAME={'.':_("Abbandona la partita"),
        '.1':_("Mostra il tempo del Bianco"),
        '.2':_("Mostra il tempo del Nero"),
        '.a':_("Visualizza analisi posizione (CP, BestLine, WDL)"),
        '.b':_("Mostra la scacchiera"),
        '.u':_("Annulla ultima semimossa (Undo)"),
        '.v':_("Aggiunge variante suggerita dal motore all'albero"),
        '.s#':_("Imposta il livello di forza del motore da 1 a 20 (es. .s10)"),
        '.?':_("Mostra questo menu")}
