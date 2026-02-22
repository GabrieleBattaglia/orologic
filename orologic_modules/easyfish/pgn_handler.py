import chess
import chess.pgn
import os
import io
import pyperclip
from datetime import datetime
from GBUtils import dgt, key
from ..config import _
from .constants import (
    DEFAULT_EVENT, DEFAULT_SITE, DEFAULT_ROUND, 
    DEFAULT_WHITE_SURENAME, DEFAULT_WHITE_FIRSTNAME, 
    DEFAULT_BLACK_SURENAME, DEFAULT_BLACK_FIRSTNAME
)

def CopyPGNToClipboard(game):
    """Copia la partita corrente negli appunti in formato PGN."""
    pgn_io = io.StringIO()
    exporter = chess.pgn.StringExporter(pgn_io)
    game.accept(exporter)
    pgn_string = pgn_io.getvalue()
    pyperclip.copy(pgn_string)
    print(_("PGN game copied to clipboard."))
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

def NewGame():
    """Inizializza una nuova partita con header di default."""
    game = chess.pgn.Game()
    game.headers["Event"] = DEFAULT_EVENT
    game.headers["Site"] = DEFAULT_SITE
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = DEFAULT_ROUND
    game.headers["White"] = DEFAULT_WHITE_SURENAME+", "+DEFAULT_WHITE_FIRSTNAME
    game.headers["Black"] = DEFAULT_BLACK_SURENAME+", "+DEFAULT_BLACK_FIRSTNAME
    game.headers["Result"] = "*"
    node = game
    return game, node

def AddingPGNTAGS(game):
    """Permette all'utente di modificare i tag PGN."""
    print(_("Set this game PGN Tags.\\nJust press enter to accept the default value."))
    e=_("Event: Having fun with Easyfish? ")
    event = dgt(prompt=e,kind="s",smax=128,default=DEFAULT_EVENT)
    s=_("Site: ")+os.getenv('COMPUTERNAME')+"'s PC? "
    site = dgt(prompt=s,kind="s",smax=128,default=DEFAULT_SITE)
    round_number = dgt(_("Enter round number: default= - "),kind="s",smin=1,smax=5,default=DEFAULT_ROUND)
    w1=dgt(prompt=_("White player's surename? "),kind="s",smin=2,smax=64,default=DEFAULT_WHITE_SURENAME).title()
    w2=dgt(prompt=_("White player's first name? "),kind="s",smin=2,smax=64,default=DEFAULT_WHITE_FIRSTNAME).title()
    w3=dgt(prompt=_("Black player's surename? "),kind="s",smin=2,smax=64,default=DEFAULT_BLACK_SURENAME).title()
    w4=dgt(prompt=_("Black player's first name? "),kind="s",smin=2,smax=64,default=DEFAULT_BLACK_FIRSTNAME).title()
    white_player = f"{w1}, {w2}"
    black_player = f"{w3}, {w4}"
    result_prompt=_("Choose result: W for White, B for Black, D for draw and U for unknown.")
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
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = round_number
    game.headers["White"] = white_player
    game.headers["Black"] = black_player
    game.headers["Result"] = result
    return

def LoadGamesFromPGN(PGN_PATH_FILE):
    """Carica tutte le partite da un file PGN."""
    games = []
    # Assicurati che il file esista
    if not os.path.exists(PGN_PATH_FILE):
        with open(PGN_PATH_FILE, "w", encoding="utf-8") as f:
            pass
        return games
    
    with open(PGN_PATH_FILE, "r", encoding="utf-8") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            games.append(game)
    return games

def SaveGamesToPGN(file_path, games):
    """Salva una lista di partite su file PGN."""
    with open(file_path, "w",encoding="utf-8") as pgn_file:
        for i, game in enumerate(games):
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            game.accept(exporter)
            pgn_file.write(str(exporter))
            if i < len(games) - 1:
                pgn_file.write("\\n\\n")
    return

def AppendGameToPGN(file_path, new_game, board):
    """Aggiunge una nuova partita al file PGN esistente."""
    if board.fen() == chess.STARTING_FEN and len(board.move_stack)==0:
        print(_("No game to save"))
        return
    games = LoadGamesFromPGN(file_path)
    games.append(new_game)
    SaveGamesToPGN(file_path, games)
    return
