# OROLOGIC (IT) - Data di concepimento: 14/02/2025 by Gabriele Battaglia & AIs
import sys, os, time, json, threading, datetime, chess, webbrowser, chess.pgn, re, pyperclip, io, chess.engine, random, gettext

from dateutil.relativedelta import relativedelta
from GBUtils import dgt, menu, Acusticator, key, Donazione
# --- Inizio Sezione Internazionalizzazione ---
# Determina la directory dello script e la cartella delle traduzioni
APP_NAME = "orologic"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALE_DIR = os.path.join(APP_DIR, 'locale')
SELECTED_LANG_FILE = os.path.join(APP_DIR, 'selected_language.json')

def prompt_for_language():
    """Chiede all'utente di scegliere una lingua e salva la scelta."""
    print("Please select your language / Per favore, seleziona la tua lingua / Por favor, seleccione su idioma / Por favor, selecione o seu idioma:")
    
    languages = {
        "1": ("en", "English"),
        "2": ("it", "Italiano"),
        "3": ("es", "Español"),
        "4": ("pt", "Português")
    }
    
    for key, (code, name) in languages.items():
        print("{key}: {name}".format(key=key, name=name))

    choice = ""
    while choice not in languages:
        choice = input("> ")

    lang_code = languages[choice][0]
    try:
        with open(SELECTED_LANG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'language': lang_code}, f)
        return lang_code
    except IOError as e:
        print("Error saving language settings: {error}".format(error=e))
        return "en" # Default to English on error

def setup_language():
    """Imposta la lingua per l'applicazione usando gettext."""
    lang_code = None
    if os.path.exists(SELECTED_LANG_FILE):
        try:
            with open(SELECTED_LANG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                lang_code = config.get('language')
        except (IOError, json.JSONDecodeError) as e:
            print("Error reading language settings, prompting for new selection: {error}".format(error=e))
            os.remove(SELECTED_LANG_FILE) # Rimuove file corrotto
            lang_code = None

    if not lang_code:
        lang_code = prompt_for_language()

    try:
        language = gettext.translation(APP_NAME, localedir=LOCALE_DIR, languages=[lang_code])
        language.install()
        # La funzione install() mette _ nel namespace built-in
        global _
        _ = language.gettext
    except FileNotFoundError:
        print("Language file for '{lang}' not found. Falling back to default messages.".format(lang=lang_code))
        # Se non trova il file, gettext non viene installato, usiamo un _ di fallback
        _ = lambda s: s

# Imposta la lingua all'avvio
setup_language()

# --- Fine Sezione Internazionalizzazione ---

#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="3.20.1"
RELEASE_DATE=datetime.datetime(2025,6,18,8,51)
PROGRAMMER="Gabriele Battaglia & AIs"
DB_FILE="orologic_db.json"
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
NAG_MAP = {
	"!": (1, _("strong move")),
	"?": (2, _("weak move")),
	"!!": (3, _("very strong move")),
	"??": (4, _("very weak move")),
	"!?": (5, _("dubious move")),
	"?!": (6, _("speculative move")),
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}
L10N = {}
# Pattern Regex per estrarre il suffisso di annotazione (1 o 2 caratteri !?=) alla fine della stringa.
# Il lookbehind (?<!=.) evita di catturare l'uguale della promozione (es. non matcha '=Q').
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
# Pattern Regex specifico per gestire i suffissi DOPO una promozione (es. "d8=Q!")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")
SMART_COMMANDS = {
	"s": _("Go to previous move"),
	"d": _("Go to next move"),
	"r": _("Refresh CP evaluation"),
	"?": _("Display this command list"),
	".": _("Exit smart mode")
}
ANALYSIS_COMMAND = {
	"a": _("Go to beginning or parent node (if in variation)"),
	"s": _("Back 1 move"),
	"d": _("Forward 1 move and display comment if any"),
	"f": _("Go to end or next variation branch node"),
	"g": _("Select previous variation node"),
	"h": _("Select next variation node"),
	"j": _("Read game headers"),
	"k": _("Go to move"),
	"l": _("Load PGN from clipboard"),
	"z": _("Insert bestline as variation in PGN"),
	"x": _("Insert bestmove in PGN"),
	"c": _("Request a comment from the user and add it"),
	"v": _("Insert centipawn evaluation in PGN"),
	"b": _("Toggle automatic comment reading"),
	"n": _("Delete comment (or choose if multiple)"),
	"q": _("Calculate and add bestmove to prompt"),
	"w": _("Calculate and display bestline, also adding bestmove to prompt"),
	"e": _("Display analysis lines and allow smart inspection"),
	"r": _("Calculate and add evaluation to prompt"),
	"t": _("Display Win Draw Lost percentages in current position"),
	"y": _("Add material balance to prompt"),
	"u": _("Display the board"),
	"i": _("Set analysis seconds for the engine"),
	"o": _("Set number of analysis lines to display"),
	"?": _("Show this command list"),
	".": _("Exit analysis mode and save PGN if different from original")
}
DOT_COMMANDS={
	".1":_("Show white's remaining time"),
	".2":_("Show black's remaining time"),
	".3":_("Show both clocks"),
	".4":_("Compare remaining times and indicate advantage"),
	".5":_("Report which clock is running or pause duration, if active"),
	".l":_("Display list of played moves"),
	".m":_("Show value of material still in play"),
	".p":_("Pause/resume clock countdown"),
	".q":_("Undo last move (only when paused)"),
	".b+":_("Add time to white (when paused)"),
	".b-":_("Subtract time from white (when paused)"),
	".n+":_("Add time to black (when paused)"),
	".n-":_("Subtract time from black (when paused)"),
	".s":_("Display the board"),
	".c":_("Add a comment to the current move"),
	".1-0":_("Assign victory to white (1-0) and end game"),
	".0-1":_("Assign victory to black (0-1) and end game"),
	".1/2":_("Assign draw (1/2-1/2) and end game"),
	".*":_("Assign undefined result (*) and end game"),
	".?":_("Display list of available commands"),
	"/[colonna]":_("Show top-right diagonal starting from base of given column"),
	"\\[colonna]":_("Show top-left diagonal starting from base of given column"),
	"-[colonna|traversa|casa]":_("Show pieces on that column, rank, or square"),
	",[NomePezzo]":_("Show position(s) of the indicated piece")}
MENU_CHOICES={
	"analizza":_("Enter game analysis mode"),
	"crea":_("... a new clock to add to the collection"),
	"elimina":_("... one of the saved clocks"),
	"gioca":_("Start the game"),
	"manuale":_("Show app guide"),
	"motore":_("Configure chess engine settings"),
	"nomi":_("Customize piece and column names"),
	"pgn":_("Set default PGN info"),
	"vedi":_("... the saved clocks"),
	"volume":_("Adjust audio effects volume"),
	".":_("Exit application")}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}
#qf
def verbose_legal_moves_for_san(board,san_str):
	if san_str in ["O-O","0-0","O-O-O","0-0-0"]:
		legal_moves=[]
		for move in board.legal_moves:
			if board.is_castling(move):
				legal_moves.append(move)
	else:
		s=san_str.replace("+","").replace("#","").strip()
		promotion=None
		if "=" in s:
			parts=s.split("=")
			s=parts[0]
			promo_char=parts[1].strip().upper()
			if promo_char=="Q":
				promotion=chess.QUEEN
			elif promo_char=="R":
				promotion=chess.ROOK
			elif promo_char=="B":
				promotion=chess.BISHOP
			elif promo_char=="N":
				promotion=chess.KNIGHT
		dest_str=s[-2:]
		try:
			dest_square=chess.parse_square(dest_str)
		except Exception:
			return _("Destination not recognized.")
		legal_moves=[]
		for move in board.legal_moves:
			if move.to_square==dest_square:
				if promotion is not None:
					if move.promotion==promotion:
						legal_moves.append(move)
				else:
					legal_moves.append(move)
	if not legal_moves:
		return _("No legal move found for the indicated destination.")
	result_lines=[]
	i=1
	for move in legal_moves:
		verbose_desc=DescribeMove(move,board.copy())
		result_lines.append(_("{i_ord}: {desc}").format(i_ord=i, desc=verbose_desc))
		i+=1
	return "\n".join(result_lines)
def FormatClock(seconds):
	total = int(seconds)
	hours = total // 3600
	minutes = (total % 3600) // 60
	secs = total % 60
	return "{h:02d}:{m:02d}:{s:02d}".format(h=hours, m=minutes, s=secs)
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
		sanitized = "default_filename"
	return sanitized
def SmartInspection(analysis_lines, board):
	print(_("Available lines:"))
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
				move_str = "{num}. {san}".format(num=move_num, san=white_san)
				if j + 1 < len(pv) and temp_board.turn == chess.BLACK:
					black_move = pv[j+1]
					black_san = temp_board.san(black_move)
					temp_board.push(black_move)
					move_str += " {san}".format(san=black_san)
					j += 2
				else:
					j += 1
				moves_with_numbers.append(move_str)
			else:
				move_num = temp_board.fullmove_number
				black_move = pv[j]
				black_san = temp_board.san(black_move)
				temp_board.push(black_move)
				moves_with_numbers.append("{num}... {san}".format(num=move_num, san=black_san))
				j += 1
		line_summary = " ".join(moves_with_numbers)
		print(_("Line {i}: {summary}").format(i=i, summary=line_summary))
	choice = dgt(_("Which line do you want to inspect? (1/{count}) ").format(count=len(analysis_lines)), kind="i", imin=1, imax=len(analysis_lines), default=1)
	Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves:
		print(_("Empty line, terminating inspection."))
		return
	score = chosen_info.get("score")
	if score is not None and score.relative.is_mate():
		eval_str = _("Mate in {moves}").format(moves=abs(score.relative.mate()))
	elif score is not None:
		cp = score.white().score()
		eval_str = "{cp:.2f}".format(cp=cp/100)
	else:
		eval_str = "0.00"
	total_moves = len(pv_moves)
	current_index = 1
	print(_("\nUse these commands:"))
	menu(p=SMART_COMMANDS,show_only=True)
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]:
			temp_board.push(move)
		current_move = pv_moves[current_index-1]
		# Ottieni la descrizione verbosa della mossa corrente, dal punto di vista della board prima di eseguirla
		move_verbose = DescribeMove(current_move, temp_board)
		smart_prompt=_("\nLine {line_num}: ({current}/{total}), CP: {eval}, {move_num}... {move_desc}").format(line_num=line_index+1, current=current_index, total=total_moves, eval=eval_str, move_num=temp_board.fullmove_number, move_desc=move_verbose)
		cmd = key(smart_prompt).lower()
		if cmd == ".":
			break
		elif cmd == "s":
			if current_index > 1:
				current_index -= 1
			else:
				Acusticator(["c4", 0.1, -0.5, volume], kind=2, adsr=[10, 10, 30, 50]) 
				print(_("\nThere are no previous moves."))
		elif cmd == "?":
			Acusticator(["d5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			temp_board = board.copy()
			try:
				for move in pv_moves[:current_index]:
					temp_board.push(move)
			except Exception as push_err:
				print(_("\nInternal error during advancement for evaluation: {error}").format(error=push_err))
				eval_str = "ERR_NAV" # Aggiorna la stringa del prompt per indicare l'errore
				continue # Torna all'inizio del loop while
			score_object_si = CalculateEvaluation(temp_board)
			Acusticator(["e5",.008,-1,volume]) # Suono dopo il tentativo
			if score_object_si is not None:
				new_eval_str = "N/A" # Valore di default per la stringa formattata
				pov_score_si = score_object_si.pov(temp_board.turn)
				if pov_score_si.is_mate():
					mate_in_si = pov_score_si.mate()
					new_eval_str = "M{moves}".format(moves=abs(mate_in_si))
				else:
					cp_si = score_object_si.white().score(mate_score=30000)
					if cp_si is not None:
						new_eval_str = "{cp:+.2f}".format(cp=cp_si/100) # Formatta CP assoluto
					else:
						new_eval_str = "ERR"
				eval_str = new_eval_str
				Acusticator(["g5", 0.1, 0.3, volume], kind=1, adsr=[5,5,90,5]) # Suono successo
				print(_("\nEvaluation updated."))
			else:
				Acusticator(["a3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]) # Suono errore
				print(_("\nCould not update evaluation."))
				eval_str = "N/A"
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				Acusticator(["c4", 0.1, 0.5, volume], kind=2, adsr=[10, 10, 30, 50])
				print(_("\nThere are no subsequent moves."))
		else:
			Acusticator(["b3", 0.12, 0, volume], kind=2, adsr=[5, 15, 20, 60])
			print(_("\nCommand not recognized."))
def CalculateBest(board, bestmove=True, as_san=False):
	Acusticator(["e5",.008,-1,volume]) 
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=multipv)
		analysis = cache_analysis[fen]
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
					white_descr = DescribeMove(white_move, temp_board)
					temp_board.push(white_move)
					i += 1
					move_descr = _("{num_ord}. {desc}").format(num_ord=move_number, desc=white_descr)
					if i < len(best_line) and temp_board.turn == chess.BLACK:
						black_move = best_line[i]
						black_descr = DescribeMove(black_move, temp_board)
						temp_board.push(black_move)
						i += 1
						move_descr += ", {desc}".format(desc=black_descr)
					descriptive_moves.append(move_descr)
					move_number += 1
				else:
					black_move = best_line[i]
					black_descr = DescribeMove(black_move, temp_board)
					temp_board.push(black_move)
					i += 1
					descriptive_moves.append(_("{num_ord}... {desc}").format(num_ord=move_number, desc=black_descr))
					move_number += 1
			score = analysis[0].get("score")
			mate_found = False
			if score is not None and score.relative.is_mate():
				mate_moves = abs(score.relative.mate())
				mate_found = True
			if bestmove:
				if mate_found:
					Acusticator(["a6",.008,1,volume]) 
					return [_("Mate in {moves}, {desc}").format(moves=mate_moves, desc=descriptive_moves[0])]
				else:
					Acusticator(["f6",.008,1,volume]) 
					return [descriptive_moves[0]]
			else:
				if mate_found:
					descriptive_moves.insert(0, _("Mate in {moves}:").format(moves=mate_moves))
				Acusticator(["d6",.008,1,volume]) 
				return descriptive_moves
		else:
			if bestmove:
				Acusticator(["g5",.008,1,volume]) 
				return best_line[0]
			else:
				Acusticator(["b5",.008,1,volume]) 
				return best_line
	except Exception as e:
		print(_("Error in CalculateBestLine: {error}").format(error=e))
		return None
def CalculateEvaluation(board):
	global ENGINE, analysis_time, multipv, cache_analysis
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result:
			print(_("DEBUG: Analysis for FEN {fen} returned empty result.").format(fen=fen)) # Debug opzionale
			return None
		score = analysis_result[0].get("score")
		return score
	except Exception as e:
		print(_("Error in CalculateEvaluation for FEN {fen}: {error}").format(fen=fen, error=e))
		return None
def CalculateWDL(board):
	global ENGINE, analysis_time, multipv, cache_analysis
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result:
			return None
		score = analysis_result[0].get("score")
		if score is None:
			return None
		wdl_info = None
		if hasattr(score, "wdl"):
			wdl_info = score.wdl() # Dovrebbe essere un oggetto tipo PovWdl ma unpackable
		if wdl_info is None:
			return None # L'engine non ha fornito WDL (comune in caso di matto)
		try:
			win_permille_pov, draw_permille_pov, loss_permille_pov = wdl_info
			if not all(isinstance(x, (int, float)) for x in [win_permille_pov, draw_permille_pov, loss_permille_pov]):
					print(_("Warning: WDL values after unpack are not numeric: W={win}, D={draw}, L={loss}").format(win=win_permille_pov, draw=draw_permille_pov, loss=loss_permille_pov))
					return None
			perspective = None
			if hasattr(wdl_info, "color"):
				perspective = wdl_info.color
			elif hasattr(wdl_info,"pov"): # Nome alternativo comune
				perspective = wdl_info.pov
			else:
				 # Se non riusciamo a determinare la prospettiva, assumiamo per sicurezza
				# che sia già assoluta (WHITE) come da standard UCI.
				print(_("Warning: Could not determine WDL perspective from {wdl_repr}. Assuming WHITE.").format(wdl_repr=repr(wdl_info)))
				perspective = chess.WHITE
			if perspective == chess.BLACK:
				win_permille_abs = loss_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = win_permille_pov
			else: # Prospettiva BIANCA (o sconosciuta/assunta)
				win_permille_abs = win_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = loss_permille_pov
			win_pc = win_permille_abs / 10.0
			draw_pc = draw_permille_abs / 10.0
			loss_pc = loss_permille_abs / 10.0
			Acusticator(["b5",.008,1,volume])
			return (win_pc, draw_pc, loss_pc) # Ritorna tuple percentuali (W_bianco, Pareggio, L_bianco)
		except (TypeError, ValueError) as e_unpack:
			print(_("Warning: Failed to directly unpack WDL object {wdl_repr}: {error}").format(wdl_repr=repr(wdl_info), error=e_unpack))
			return None
	except Exception as e:
		print(_("General error in CalculateWDL for FEN {fen}: {error}").format(fen=fen, error=e))
		return None
def SetAnalysisTime(new_time):
	"""
	Permette di impostare il tempo di analisi (in secondi) per il motore.
	"""
	global analysis_time
	try:
		new_time = float(new_time)
		if new_time <= 0:
			print(_("Analysis time must be positive."))
		else:
			analysis_time = new_time
			print(_("Analysis time set to {time} seconds.").format(time=analysis_time))
	except Exception as e:
		print(_("Error in SetAnalysisTime: {error}").format(error=e))
def SetMultipv(new_multipv):
	"""
	Permette di impostare il numero di linee (multipv) da visualizzare.
	"""
	global multipv
	try:
		new_multipv = int(new_multipv)
		if new_multipv < 1:
			print(_("Number of lines must be at least 1."))
		else:
			multipv = new_multipv
			print(_("Multipv set to {multipv}.").format(multipv=multipv))
	except Exception as e:
		print(_("Error in SetMultipv: {error}").format(error=e))
def LoadPGNFromClipboard():
	"""
	Carica il PGN dagli appunti e lo restituisce come oggetto pgn_game.
	Se gli appunti contengono più di una partita, viene presentato un menù numerato e
	viene chiesto all'utente di scegliere la partita da caricare.
	"""
	try:
		clipboard_pgn = pyperclip.paste()
		if not clipboard_pgn.strip():
			print(_("Clipboard empty."))
			return None
		pgn_io = io.StringIO(clipboard_pgn)
		games = []
		while True:
			game = chess.pgn.read_game(pgn_io)
			if game is None:
				break
			games.append(game)
		if len(games) == 0:
			print(_("Invalid PGN in clipboard."))
			return None
		elif len(games) == 1:
			return games[0]
		else:
			print(_("\nFound {count} games in PGN.").format(count=len(games)))
			partite={}
			for i, game in enumerate(games, start=1):
				white = game.headers.get("White", _("Unknown"))
				black = game.headers.get("Black", _("Unknown"))
				date = game.headers.get("Date", _("Unknown date"))
				partite[i]="{white} vs {black} - {date}".format(white=white, black=black, date=date)
			while True:
				choice = menu(d=partite,	prompt=_("Which game do you want to load? "),	show=True,ntf=_("Invalid number. Try again."))
				try:
					index = int(choice)
					if 1 <= index <= len(games):
						return games[index - 1]
					else:
						Acusticator(["a3", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
						print(_("Invalid number. Try again."))
				except ValueError:
					Acusticator(["g2", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
					print(_("Invalid input. Enter a number."))
	except Exception as e:
		print(_("Error in LoadPGNFromClipboard: {error}").format(error=e))
		return None
def InitEngine():
	global ENGINE
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config or not engine_config.get("engine_path"):
		Acusticator(["d4", 0.5, -1, volume],kind=4, adsr=[.001,0,100,99.9])
		print(_("\nEngine not configured. Use the 'motore' command to set it up."))
		return False
	try:
		ENGINE = chess.engine.SimpleEngine.popen_uci(engine_config["engine_path"])
		ENGINE.configure({
			"Hash": engine_config.get("hash_size", 128),
			"Threads": engine_config.get("num_cores", 1),
			"Skill Level": engine_config.get("skill_level", 20),
			"Move Overhead": engine_config.get("move_overhead", 0)
		})
		print(_("\nEngine initialized successfully."))
		return True
	except Exception as e:
		print(_("\nError initializing engine: {error}").format(error=e))
		return False
def EditEngineConfig():
	print(_("\nSet chess engine configuration\n"))
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if engine_config:
		print(_("Current engine configuration:"))
		for key, val in engine_config.items():
			print("  {key}: {val}".format(key=key, val=val))
	else:
		print(_("No configuration found."))
	path = dgt(prompt=_("Enter the path where the UCI engine is saved: "), kind="s", smin=3, smax=256)
	Acusticator(["g6", 0.025, -.75, volume,"c5", 0.025, -75, volume],kind=3)
	executable = dgt(prompt=_("Enter the engine executable name (e.g., stockfish_15_x64_popcnt.exe): "), kind="s", smin=5, smax=64)
	Acusticator(["g6", 0.025, -.5, volume,"c5", 0.025, -.5, volume],kind=3)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print(_("The specified file does not exist. Verify the path and executable name."))
		return
	hash_size = dgt(prompt=_("Enter hash table size (min: 1, max: 4096 MB): "), kind="i", imin=1, imax=4096)
	Acusticator(["g6", 0.025, -.25, volume,"c5", 0.025, -.25, volume],kind=3)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=_("Enter number of cores to use (min: 1, max: {max_cores}): ").format(max_cores=max_cores), kind="i", imin=1, imax=max_cores, default=4)
	Acusticator(["g6", 0.025, 0, volume,"c5", 0.025, 0, volume],kind=3)
	skill_level = dgt(prompt=_("Enter skill level (min: 0, max: 20): "), kind="i", imin=0, imax=20)
	Acusticator(["g6", 0.025, .25, volume,"c5", 0.025, .25, volume],kind=3)
	move_overhead = dgt(prompt=_("Enter move overhead in milliseconds (min: 0, max: 500): "), kind="i", imin=0, imax=500, default=0)
	Acusticator(["g6", 0.025, .5, volume,"c5", 0.025, .5, volume],kind=3)
	wdl_switch = True
	engine_config = {
		"engine_path": full_engine_path,
		"hash_size": hash_size,
		"num_cores": num_cores,
		"skill_level": skill_level,
		"move_overhead": move_overhead,
		"wdl_switch": wdl_switch
	}
	db["engine_config"] = engine_config
	SaveDB(db)
	print(_("Engine configuration saved to orologic_db.json."))
	InitEngine()
	Acusticator(["a6", 0.5, 1, volume],kind=3, adsr=[.001,0,100,99.9])
	return

def EditLocalization():
    """
    Crea un'interfaccia per permettere all'utente di personalizzare
    le stringhe usate nel programma (localizzazione).
    """
    print(_("\n--- Language Customization ---\n"))
    print(_("For each item, enter the new text or press ENTER to keep the current value."))
    db = LoadDB()
    # Usiamo una copia per le modifiche, per poi salvarla tutta in una volta
    l10n_config = db.get("localization", get_default_localization())
    
    items_to_edit = [
        ("pieces", "pawn", ("name", _("Name for 'Pawn'"))),
        ("pieces", "knight", ("name", _("Name for 'Knight'"))),
        ("pieces", "bishop", ("name", _("Name for 'Bishop'"))),
        ("pieces", "rook", ("name", _("Name for 'Rook'"))),
        ("pieces", "queen", ("name", _("Name for 'Queen'"))),
        ("pieces", "king", ("name", _("Name for 'King'"))),
        ("columns", "a", _("Name for column 'a' (e.g., Ancona)")),
        ("columns", "b", _("Name for column 'b' (e.g., Bologna)")),
        ("columns", "c", _("Name for column 'c' (e.g., Como)")),
        ("columns", "d", _("Name for column 'd' (e.g., Domodossola)")),
        ("columns", "e", _("Name for column 'e' (e.g., Empoli)")),
        ("columns", "f", _("Name for column 'f' (e.g., Firenze)")),
        ("columns", "g", _("Name for column 'g' (e.g., Genova)")),
        ("columns", "h", _("Name for column 'h' (e.g., Hotel)")),
        ("adjectives", "white", ("m", _("Adjective 'white' (masculine)"))),
        ("adjectives", "white", ("f", _("Adjective 'white' (feminine)"))),
        ("adjectives", "black", ("m", _("Adjective 'black' (masculine)"))),
        ("adjectives", "black", ("f", _("Adjective 'black' (feminine)"))),
        ("moves", "capture", _("Verb for capture (e.g., 'takes')")),
        ("moves", "capture_on", _("Preposition for capture square (e.g., 'on')")),
        ("moves", "move_to", _("Preposition for destination square (e.g., 'to')")),
        ("moves", "en_passant", _("Text for 'en passant'")),
        ("moves", "short_castle", _("Text for 'short castle'")),
        ("moves", "long_castle", _("Text for 'long castle'")),
        ("moves", "promotes_to", _("Text for promotion (e.g., 'and promotes to')")),
        ("moves", "check", _("Text for 'check'")),
        ("moves", "checkmate", _("Text for 'checkmate!'"))
    ]
    
    num_items = len(items_to_edit)
    notes = ['c3', 'd3', 'e3', 'f3', 'g3', 'a3', 'b3', 'c4', 'd4', 'e4', 'f4', 'g4', 'a4', 'b4', 'c5', 'd5', 'e5', 'f5', 'g5', 'a5', 'b5', 'c6', 'd6', 'e6', 'f6', 'g6', 'a6', 'b6', 'c7']
    for i, item in enumerate(items_to_edit):
        cat, key, details = item
        pitch = notes[i % len(notes)]
        pan = -1 + (2 * i / (num_items - 1)) if num_items > 1 else 0
        
        if isinstance(details, tuple):
            sub_key, prompt_text = details
            current_val = l10n_config[cat][key][sub_key]
            new_val = dgt("{prompt} [{current}]: ".format(prompt=prompt_text, current=current_val), kind="s", default=current_val)
            l10n_config[cat][key][sub_key] = new_val.strip()
            
            if cat == "pieces":
                current_gender = l10n_config[cat][key]['gender']
                gender_prompt = _("  Gender for '{name}' (m/f/n) [{gender}]: ").format(name=new_val, gender=current_gender)
                while True:
                    new_gender = dgt(gender_prompt, kind="s", default=current_gender).lower()
                    if new_gender in ['m', 'f', 'n']:
                        l10n_config[cat][key]['gender'] = new_gender
                        break
                    else:
                        print(_("Invalid input. Enter 'm' (masculine), 'f' (feminine), or 'n' (neutral)."))
        else:
            prompt_text = details
            current_val = l10n_config[cat][key]
            new_val = dgt("{prompt} [{current}]: ".format(prompt=prompt_text, current=current_val), kind="s", default=current_val)
            l10n_config[cat][key] = new_val.strip()
        
        Acusticator([pitch, 0.08, pan, volume], kind=1, adsr=[2, 5, 80, 10])
        
    Acusticator(['c7', 0.05, 0, volume,'e7', 0.05, 0, volume,'g7', 0.15, 0, volume], kind=1, adsr=[2, 5, 90, 5])
    
    db["localization"] = l10n_config
    SaveDB(db)
    LoadLocalization()
    print(_("\nLanguage settings saved successfully!"))