import chess
import chess.pgn
import os
import io
import pyperclip
import datetime
from GBUtils import dgt, key, Acusticator
from ..config import _, sanitize_filename, percorso_salvataggio
from ..board_utils import format_pgn_comments
from .constants import (
    DEFAULT_EVENT, DEFAULT_SITE, DEFAULT_ROUND, 
    DEFAULT_WHITE_SURENAME, DEFAULT_WHITE_FIRSTNAME, 
    DEFAULT_BLACK_SURENAME, DEFAULT_BLACK_FIRSTNAME
)

def CopyPGNToClipboard(game):
    """Copia la partita corrente negli appunti in formato PGN."""
    pgn_io = io.StringIO()
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    game.accept(exporter)
    pgn_string = str(exporter)
    pyperclip.copy(pgn_string)
    print(_("PGN copiato negli appunti."))
    return

def PastePGNFromClipboard():
    """Incolla una partita dagli appunti in formato PGN."""
    pgn_string = pyperclip.paste()
    if not pgn_string:
        return None
    try:
        pgn_io = io.StringIO(pgn_string)
        game = chess.pgn.read_game(pgn_io)
        return game
    except Exception:
        return None

def InitNewPGN(board=None, tags=None):
    """Inizializza una nuova partita PGN con header di default e posizione iniziale."""
    game = chess.pgn.Game()
    
    # Se board è specificata e non è la posizione standard, impostiamo FEN e SetUp
    if board and board.fen() != chess.STARTING_FEN:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = board.fen()
        # Se stiamo iniziando una partita da una posizione personalizzata, la board deve essere passata a setup
        game.setup(board)
        
    game.headers["Event"] = DEFAULT_EVENT
    game.headers["Site"] = DEFAULT_SITE
    game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = DEFAULT_ROUND
    
    # Se tags personalizzati sono passati (es. nomi giocatori), usali
    if tags:
        for k, v in tags.items():
            game.headers[k] = v
    else:
        game.headers["White"] = DEFAULT_WHITE_SURENAME+", "+DEFAULT_WHITE_FIRSTNAME
        game.headers["Black"] = DEFAULT_BLACK_SURENAME+", "+DEFAULT_BLACK_FIRSTNAME
        
    game.headers["Result"] = "*"
    
    # Il nodo corrente per le variazioni è l'inizio del gioco
    node = game
    return game, node

def AddingPGNTAGS(game):
    """Permette all'utente di modificare i tag PGN."""
    print(_("Modifica i tag della partita corrente. Premi Invio per accettare i valori attuali."))
    
    current_event = game.headers.get("Event", DEFAULT_EVENT)
    event = dgt(prompt=_("Evento [{d}]: ").format(d=current_event), kind="s", smax=128, default=current_event)
    
    current_site = game.headers.get("Site", DEFAULT_SITE)
    site = dgt(prompt=_("Luogo [{d}]: ").format(d=current_site), kind="s", smax=128, default=current_site)
    
    current_round = game.headers.get("Round", DEFAULT_ROUND)
    round_number = dgt(prompt=_("Round [{d}]: ").format(d=current_round), kind="s", smin=1, smax=5, default=current_round)
    
    current_white = game.headers.get("White", DEFAULT_WHITE_SURENAME+", "+DEFAULT_WHITE_FIRSTNAME)
    white_player = dgt(prompt=_("Giocatore Bianco [{d}]: ").format(d=current_white), kind="s", smin=2, smax=64, default=current_white).title()
    
    current_black = game.headers.get("Black", DEFAULT_BLACK_SURENAME+", "+DEFAULT_BLACK_FIRSTNAME)
    black_player = dgt(prompt=_("Giocatore Nero [{d}]: ").format(d=current_black), kind="s", smin=2, smax=64, default=current_black).title()
    
    result_prompt=_("Risultato: [W]Bianco, [B]Nero, [D]Patta, [U]Sconosciuto.")
    print(result_prompt)
    while True:
        select_result=key().lower()
        if select_result in "wbdu": break
        else: print(result_prompt)
    
    if select_result=="w": result="1-0"
    elif select_result=="b": result="0-1"
    elif select_result=="d": result="1/2-1/2"
    elif select_result=="u": result="*"
    
    game.headers["Event"] = event
    game.headers["Site"] = site
    game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = round_number
    game.headers["White"] = white_player
    game.headers["Black"] = black_player
    game.headers["Result"] = result
    
    print(_("Tag aggiornati."))
    return

def SaveGameToFile(game):
    """Salva la partita corrente su un file PGN singolo nella cartella pgn/."""
    # Aggiorna data salvataggio
    game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
    
    pgn_io = io.StringIO()
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    game.accept(exporter)
    pgn_str = str(exporter)
    pgn_str = format_pgn_comments(pgn_str)
    
    # Generazione Nome File
    white = game.headers.get("White", "White")
    black = game.headers.get("Black", "Black")
    result = game.headers.get("Result", "*")
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    base_filename = f"{white}-{black}-{result}-{timestamp}.pgn"
    sanitized_name = sanitize_filename(base_filename)
    
    # Percorso: usa config.percorso_salvataggio per garantire la cartella corretta
    full_path = percorso_salvataggio(os.path.join("pgn", sanitized_name))
    
    # Assicuriamoci che la cartella pgn esista (dovrebbe, ma per sicurezza)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(pgn_str)
        print(_("Partita salvata in: {path}").format(path=full_path))
        
        # Copia negli appunti (filosofia Orologic)
        try:
            pyperclip.copy(pgn_str)
            print(_("PGN copiato automaticamente negli appunti."))
        except Exception:
            pass
            
    except Exception as e:
        print(_("Errore durante il salvataggio del file PGN: {e}").format(e=e))
    
    return
