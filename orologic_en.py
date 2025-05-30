# Conception date: 14/02/2025 by Gabriele Battaglia & AIs
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re, pyperclip, io, chess.engine
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator, key
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="3.16.13.EN"
RELEASE_DATE=datetime.datetime(2025,5,30,8,54)
PROGRAMMER="Gabriele Battaglia & AIs"
DB_FILE="orologic_db.json"
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
NAG_MAP = {
	"!": (1, "strong move"),
	"?": (2, "weak move"),
	"!!": (3, "very strong move"),
	"??": (4, "very weak move"),
	"!?": (5, "dubious move"),
	"?!": (6, "dubious move"), # "speculative move" could also be an option, but "dubious" is more common for ?!
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}
ANNOTATION_DESC = {
	"=": "draw offer",
	"?": "weak move",
	"!": "strong move",
	"??": "blunder", # "terrible move" is also possible
	"!!": "brilliant move!",
	"?!": "dubious move", # or "speculative move"
	"!?": "dubious move"  # or "interesting move"
}
# Regex Pattern to extract the annotation suffix (1 or 2 !?= characters) at the end of the string.
# The lookbehind (?<!=.) avoids capturing the equals of promotion (e.g., doesn't match '=Q').
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
# Specific Regex Pattern to handle suffixes AFTER a promotion (e.g., "d8=Q!")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")
SMART_COMMANDS = {
	"s": "Go to previous move",
	"d": "Go to next move",
	"r": "Refresh CP evaluation",
	"?": "Display this command list",
	".": "Exit smart mode"
}
ANALYSIS_COMMAND = {
	"a": "Go to beginning or parent node (if in variation)",
	"s": "Back 1 move",
	"d": "Forward 1 move and display comment if any",
	"f": "Go to end or next variation branch node",
	"g": "Select previous variation node",
	"h": "Select next variation node",
	"j": "Read game headers",
	"k": "Go to move",
	"l": "Load PGN from clipboard",
	"z": "Insert bestline as variation in PGN",
	"x": "Insert bestmove in PGN",
	"c": "Request a comment from the user and add it",
	"v": "Insert centipawn evaluation in PGN",
	"b": "Toggle automatic comment reading",
	"n": "Delete comment (or choose if multiple)",
	"q": "Calculate and add bestmove to prompt",
	"w": "Calculate and display bestline, also adding bestmove to prompt",
	"e": "Display analysis lines and allow smart inspection",
	"r": "Calculate and add evaluation to prompt",
	"t": "Display Win Draw Lost percentages in current position",
	"y": "Add material balance to prompt",
	"u": "Display the board",
	"i": "Set analysis seconds for the engine",
	"o": "Set number of analysis lines to display",
	"?": "Show this command list",
	".": "Exit analysis mode and save PGN if different from original"
}
DOT_COMMANDS={
	".1":"Show white's remaining time",
	".2":"Show black's remaining time",
	".3":"Show both clocks",
	".4":"Compare remaining times and indicate advantage",
	".5":"Report which clock is running or pause duration, if active",
	".l":"Display list of played moves",
	".m":"Show value of material still in play",
	".p":"Pause/resume clock countdown",
	".q":"Undo last move (only when paused)",
	".b+":"Add time to white (when paused)",
	".b-":"Subtract time from white (when paused)",
	".n+":"Add time to black (when paused)",
	".n-":"Subtract time from black (when paused)",
	".s":"Display the board",
	".c":"Add a comment to the current move",
	".1-0":"Assign victory to white (1-0) and end game",
	".0-1":"Assign victory to black (0-1) and end game",
	".1/2":"Assign draw (1/2-1/2) and end game",
	".*":"Assign undefined result (*) and end game",
	".?":"Display list of available commands",
	"/[column]":"Show top-right diagonal starting from base of given column",
	"\\[column]":"Show top-left diagonal starting from base of given column",
	"-[column|rank|square]":"Show pieces on that column, rank, or square",
	",[PieceName]":"Show position(s) of the indicated piece"}
MENU_CHOICES={
	"analizza":"Enter game analysis mode", # "analyze" is the verb
	"crea":"... a new clock to add to the collection",
	"elimina":"... one of the saved clocks", # "delete" is the verb
	"gioca":"Start the game", # "play" is the verb
	"manuale":"Show app guide", # "manual" or "help"
	"motore":"Configure chess engine settings", # "engine" is the noun
	"pgn":"Set default PGN info",
	"vedi":"... the saved clocks", # "view" or "see"
	"volume":"Adjust audio effects volume",
	".":"Exit application"}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"} # These seem to be internal, not for translation.
LETTER_FILE_MAP={chr(ord("a")+i):FILE_NAMES.get(i,chr(ord("a")+i)) for i in range(8)} # Internal
PIECE_NAMES={chess.PAWN:"pawn",chess.KNIGHT:"knight",chess.BISHOP:"bishop",chess.ROOK:"rook",chess.QUEEN:"queen",chess.KING:"King"} # "King" is often capitalized
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
			return "Destination not recognized."
		legal_moves=[]
		for move in board.legal_moves:
			if move.to_square==dest_square:
				if promotion is not None:
					if move.promotion==promotion:
						legal_moves.append(move)
				else:
					legal_moves.append(move)
	if not legal_moves:
		return "No legal move found for the indicated destination."
	result_lines=[]
	i=1
	for move in legal_moves:
		verbose_desc=DescribeMove(move,board.copy())
		result_lines.append(f"{i}: {verbose_desc}") # Using ':' instead of '°' for ordinal
		i+=1
	return "\n".join(result_lines)
def FormatClock(seconds):
	total = int(seconds)
	hours = total // 3600
	minutes = (total % 3600) // 60
	secs = total % 60
	return f"{hours:02d}:{minutes:02d}:{secs:02d}"
def sanitize_filename(filename: str) -> str:
	"""
	Returns a filesystem-compatible version of the string,
	replacing invalid characters (for Windows and other systems) with an
	underscore character.
	"""
	# Characters not allowed in Windows: \ / : * ? " < > |
	# Also, control characters (ASCII 0-31) are removed
	sanitized = re.sub(r'[\\/:*?"<>|]', '_', filename)
	sanitized = re.sub(r'[\0-\31]', '', sanitized)
	# Removes spaces and dots at the beginning and end
	sanitized = sanitized.strip().strip('. ')
	if not sanitized:
		sanitized = "default_filename"
	return sanitized
def SmartInspection(analysis_lines, board):
	print("Available lines:")
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
				move_str = f"{move_num}. {white_san}"
				if j + 1 < len(pv) and temp_board.turn == chess.BLACK:
					black_move = pv[j+1]
					black_san = temp_board.san(black_move)
					temp_board.push(black_move)
					move_str += f" {black_san}"
					j += 2
				else:
					j += 1
				moves_with_numbers.append(move_str)
			else:
				move_num = temp_board.fullmove_number
				black_move = pv[j]
				black_san = temp_board.san(black_move)
				temp_board.push(black_move)
				moves_with_numbers.append(f"{move_num}... {black_san}")
				j += 1
		line_summary = " ".join(moves_with_numbers)
		print(f"Line {i}: {line_summary}")
	choice = dgt(f"Which line do you want to inspect? (1/{len(analysis_lines)}) ", kind="i", imin=1, imax=len(analysis_lines),	default=1)
	Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves:
		print("Empty line, terminating inspection.")
		return
	score = chosen_info.get("score")
	if score is not None and score.relative.is_mate():
		eval_str = f"Mate in {abs(score.relative.mate())}"
	elif score is not None:
		cp = score.white().score()
		eval_str = f"{cp/100:.2f}"
	else:
		eval_str = "0.00"
	total_moves = len(pv_moves)
	current_index = 1
	print("\nUse these commands:")
	menu(p=SMART_COMMANDS,show_only=True)
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]:
			temp_board.push(move)
		current_move = pv_moves[current_index-1]
		# Get verbose description of the current move, from the board's perspective before executing it
		move_verbose = DescribeMove(current_move, temp_board)
		smart_prompt=f"\nLine {line_index+1}: ({current_index}/{total_moves}), CP: {eval_str}, {temp_board.fullmove_number}... {move_verbose}"
		cmd = key(smart_prompt).lower()
		if cmd == ".":
			break
		elif cmd == "s":
			if current_index > 1:
				current_index -= 1
			else:
				Acusticator(["c4", 0.1, -0.5, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nThere are no previous moves.")
		elif cmd == "?":
			Acusticator(["d5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			temp_board = board.copy()
			try:
				for move in pv_moves[:current_index]:
					temp_board.push(move)
			except Exception as push_err:
				print(f"\nInternal error during advancement for evaluation: {push_err}")
				eval_str = "ERR_NAV" # Update prompt string to indicate error
				continue # Return to the beginning of the while loop
			score_object_si = CalculateEvaluation(temp_board)
			Acusticator(["e5",.008,-1,volume]) # Sound after attempt
			if score_object_si is not None:
				new_eval_str = "N/A" # Default value for formatted string
				pov_score_si = score_object_si.pov(temp_board.turn)
				if pov_score_si.is_mate():
					mate_in_si = pov_score_si.mate()
					new_eval_str = f"M{abs(mate_in_si)}"
				else:
					cp_si = score_object_si.white().score(mate_score=30000)
					if cp_si is not None:
						new_eval_str = f"{cp_si/100:+.2f}" # Format absolute CP
					else:
						new_eval_str = "ERR"
				eval_str = new_eval_str
				Acusticator(["g5", 0.1, 0.3, volume], kind=1, adsr=[5,5,90,5]) # Success sound
				print("\nEvaluation updated.")
			else:
				Acusticator(["a3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]) # Error sound
				print("\nCould not update evaluation.")
				eval_str = "N/A"
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				Acusticator(["c4", 0.1, 0.5, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nThere are no subsequent moves.")
		else:
			Acusticator(["b3", 0.12, 0, volume], kind=2, adsr=[5, 15, 20, 60])
			print("\nCommand not recognized.")
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
					move_descr = f"{move_number}. {white_descr}" # Using '.' instead of '°'
					if i < len(best_line) and temp_board.turn == chess.BLACK:
						black_move = best_line[i]
						black_descr = DescribeMove(black_move, temp_board)
						temp_board.push(black_move)
						i += 1
						move_descr += f", {black_descr}"
					descriptive_moves.append(move_descr)
					move_number += 1
				else:
					black_move = best_line[i]
					black_descr = DescribeMove(black_move, temp_board)
					temp_board.push(black_move)
					i += 1
					descriptive_moves.append(f"{move_number}... {black_descr}") # Using '...' and '.'
					move_number += 1
			score = analysis[0].get("score")
			mate_found = False
			if score is not None and score.relative.is_mate():
				mate_moves = abs(score.relative.mate())
				mate_found = True
			if bestmove:
				if mate_found:
					Acusticator(["a6",.008,1,volume])
					return [f"Mate in {mate_moves}, {descriptive_moves[0]}"]
				else:
					Acusticator(["f6",.008,1,volume])
					return [descriptive_moves[0]]
			else:
				if mate_found:
					descriptive_moves.insert(0, f"Mate in {mate_moves}:")
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
		print("Error in CalculateBestLine:", e)
		return None
def CalculateEvaluation(board):
	global ENGINE, analysis_time, multipv, cache_analysis
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result:
			print(f"DEBUG: Analysis for FEN {fen} returned empty result.") # Optional Debug
			return None
		score = analysis_result[0].get("score")
		return score
	except Exception as e:
		print(f"Error in CalculateEvaluation for FEN {fen}: {e}")
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
			wdl_info = score.wdl() # Should be a PovWdl-like object but unpackable
		if wdl_info is None:
			return None # Engine did not provide WDL (common in case of mate)
		try:
			win_permille_pov, draw_permille_pov, loss_permille_pov = wdl_info
			if not all(isinstance(x, (int, float)) for x in [win_permille_pov, draw_permille_pov, loss_permille_pov]):
					print(f"Warning: WDL values after unpack are not numeric: W={win_permille_pov}, D={draw_permille_pov}, L={loss_permille_pov}")
					return None
			perspective = None
			if hasattr(wdl_info, "color"):
				perspective = wdl_info.color
			elif hasattr(wdl_info,"pov"): # Common alternative name
				perspective = wdl_info.pov
			else:
				 # If we can't determine the perspective, assume for safety
				# that it's already absolute (WHITE) as per UCI standard.
				print(f"Warning: Could not determine WDL perspective from {repr(wdl_info)}. Assuming WHITE.")
				perspective = chess.WHITE
			if perspective == chess.BLACK:
				win_permille_abs = loss_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = win_permille_pov
			else: # WHITE perspective (or unknown/assumed)
				win_permille_abs = win_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = loss_permille_pov
			win_pc = win_permille_abs / 10.0
			draw_pc = draw_permille_abs / 10.0
			loss_pc = loss_permille_abs / 10.0
			Acusticator(["b5",.008,1,volume])
			return (win_pc, draw_pc, loss_pc) # Returns tuple of percentages (W_white, Draw, L_white)
		except (TypeError, ValueError) as e_unpack:
			print(f"Warning: Failed to directly unpack WDL object {repr(wdl_info)}: {e_unpack}")
			return None
	except Exception as e:
		print(f"General error in CalculateWDL for FEN {fen}: {e}")
		return None
def SetAnalysisTime(new_time):
	"""
	Allows setting the analysis time (in seconds) for the engine.
	"""
	global analysis_time
	try:
		new_time = float(new_time)
		if new_time <= 0:
			print("Analysis time must be positive.")
		else:
			analysis_time = new_time
			print(f"Analysis time set to {analysis_time} seconds.")
	except Exception as e:
		print("Error in SetAnalysisTime:", e)
def SetMultipv(new_multipv):
	"""
	Allows setting the number of lines (multipv) to display.
	"""
	global multipv
	try:
		new_multipv = int(new_multipv)
		if new_multipv < 1:
			print("Number of lines must be at least 1.")
		else:
			multipv = new_multipv
			print(f"Multipv set to {multipv}.")
	except Exception as e:
		print("Error in SetMultipv:", e)
def LoadPGNFromClipboard():
	"""
	Loads PGN from clipboard and returns it as a pgn_game object.
	If the clipboard contains more than one game, a numbered menu is presented
	and the user is asked to choose the game to load.
	"""
	try:
		clipboard_pgn = pyperclip.paste()
		if not clipboard_pgn.strip():
			print("Clipboard empty.")
			return None
		pgn_io = io.StringIO(clipboard_pgn)
		games = []
		while True:
			game = chess.pgn.read_game(pgn_io)
			if game is None:
				break
			games.append(game)
		if len(games) == 0:
			print("Invalid PGN in clipboard.")
			return None
		elif len(games) == 1:
			return games[0]
		else:
			print(f"\nFound {len(games)} games in PGN.")
			partite={} # "games"
			for i, game in enumerate(games, start=1):
				white = game.headers.get("White", "Unknown")
				black = game.headers.get("Black", "Unknown")
				date = game.headers.get("Date", "Unknown date")
				partite[i]=f"{white} vs {black} - {date}"
			while True:
				choice = menu(d=partite,	prompt="Which game do you want to load? ",	show=True,ntf="Invalid number. Try again.")
				try:
					index = int(choice)
					if 1 <= index <= len(games):
						return games[index - 1]
					else:
						Acusticator(["a3", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
						print("Invalid number. Try again.")
				except ValueError:
					Acusticator(["g2", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
					print("Invalid input. Enter a number.")
	except Exception as e:
		print("Error in LoadPGNFromClipboard:", e)
		return None
def InitEngine():
	global ENGINE
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config or not engine_config.get("engine_path"):
		Acusticator(["d4", 0.5, -1, volume],kind=4, adsr=[.001,0,100,99.9])
		print("\nEngine not configured. Use the 'engine' command to set it up.")
		return False
	try:
		ENGINE = chess.engine.SimpleEngine.popen_uci(engine_config["engine_path"])
		ENGINE.configure({
			"Hash": engine_config.get("hash_size", 128),
			"Threads": engine_config.get("num_cores", 1),
			"Skill Level": engine_config.get("skill_level", 20),
			"Move Overhead": engine_config.get("move_overhead", 0)
		})
		print("\nEngine initialized successfully.")
		return True
	except Exception as e:
		print("\nError initializing engine:", e)
		return False
def EditEngineConfig():
	print("\nSet chess engine configuration\n")
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if engine_config:
		print("Current engine configuration:")
		for key, val in engine_config.items():
			print(f"  {key}: {val}")
	else:
		print("No configuration found.")
	path = dgt(prompt="Enter the path where the UCI engine is saved: ", kind="s", smin=3, smax=256)
	Acusticator(["g6", 0.025, -.75, volume,"c5", 0.025, -75, volume],kind=3)
	executable = dgt(prompt="Enter the engine executable name (e.g., stockfish_15_x64_popcnt.exe): ", kind="s", smin=5, smax=64)
	Acusticator(["g6", 0.025, -.5, volume,"c5", 0.025, -.5, volume],kind=3)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print("The specified file does not exist. Verify the path and executable name.")
		return
	hash_size = dgt(prompt="Enter hash table size (min: 1, max: 4096 MB): ", kind="i", imin=1, imax=4096)
	Acusticator(["g6", 0.025, -.25, volume,"c5", 0.025, -.25, volume],kind=3)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=f"Enter number of cores to use (min: 1, max: {max_cores}): ", kind="i", imin=1, imax=max_cores, default=4)
	Acusticator(["g6", 0.025, 0, volume,"c5", 0.025, 0, volume],kind=3)
	skill_level = dgt(prompt="Enter skill level (min: 0, max: 20): ", kind="i", imin=0, imax=20)
	Acusticator(["g6", 0.025, .25, volume,"c5", 0.025, .25, volume],kind=3)
	move_overhead = dgt(prompt="Enter move overhead in milliseconds (min: 0, max: 500): ", kind="i", imin=0, imax=500, default=0)
	Acusticator(["g6", 0.025, .5, volume,"c5", 0.025, .5, volume],kind=3)
	wdl_switch = True  # You can eventually make this configurable
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
	print("Engine configuration saved to orologic_db.json.")
	InitEngine()
	Acusticator(["a6", 0.5, 1, volume],kind=3, adsr=[.001,0,100,99.9])
	return
def AnalyzeGame(pgn_game):
	"""
	Game analysis function (PGN).
	Reads NAG annotations during navigation.
	"""
	if pgn_game is None:
		pgn_game = LoadPGNFromClipboard()
		if pgn_game:
			# Safe recursion because pgn_game is now defined or None
			AnalyzeGame(pgn_game)
		else:
			print("Clipboard does not contain a valid PGN. Returning to menu.")
		return

	print("\nAnalysis mode.\nGame headers:\n")
	for k, v in pgn_game.headers.items():
		print(f"{k}: {v}")
	move_list = list(pgn_game.mainline_moves())
	total_moves = len(move_list)
	print(f"Total number of moves: {(total_moves+1)//2}")

	if total_moves < 2:
		choice = key("\nInsufficient moves. [M] to return to menu or [L] to load a new PGN from clipboard: ").lower()
		Acusticator(["f5", 0.03, 0, volume], kind=1, adsr=[0,0,100,0])
		if choice == "l":
			new_pgn = LoadPGNFromClipboard()
			if new_pgn:
				AnalyzeGame(new_pgn)
			else:
				print("Clipboard does not contain a valid PGN. Returning to menu.")
		return
	print(f"Analysis time set to {analysis_time} seconds.\nEngine lines reported set to {multipv}.")
	print("\nPress '?' for the command list.\n")
	saved = False
	comment_auto_read=True
	current_filename = pgn_game.headers.get("Filename", None)
	current_node = pgn_game
	extra_prompt = ""
	while True:
		prompt_move_part = "Start"
		if current_node.move:
			move_san = current_node.san()
			fullmove = current_node.parent.board().fullmove_number if current_node.parent else 1
			move_indicator = f"{fullmove}. {move_san}" if current_node.board().turn == chess.BLACK else f"{fullmove}... {move_san}"

			if current_node.parent and len(current_node.parent.variations) > 1:
				siblings = current_node.parent.variations
				try: # Added try-except for robustness if node not in variations (?)
					idx = siblings.index(current_node)
					if idx == 0 and len(siblings) > 1:
						prompt_move_part = f"<{move_indicator}"
					elif idx > 0 and idx < len(siblings) - 1 :
						prompt_move_part = f"<{move_indicator}>"
					elif idx > 0 and idx == len(siblings) - 1:
						prompt_move_part = f"{move_indicator}>"
					else:
						prompt_move_part = move_indicator
				except ValueError:
					prompt_move_part = move_indicator # Fallback
			else:
				prompt_move_part = move_indicator

		if current_node.move and current_node.comment and not comment_auto_read:
			prompt_move_part += "-"
		prompt = f"\n{extra_prompt} {prompt_move_part}: "
		extra_prompt = "" # Reset extra prompt for the next cycle

		if current_node.comment and comment_auto_read:
			print("Comment:", current_node.comment)
		elif current_node.comment and not comment_auto_read:
			Acusticator(["c7",	0.024, 0, volume], kind=1, adsr=[0,0,100,0])

		cmd = key(prompt).lower().strip()
		# --- 3. Save Current Node and Process Command ---
		previous_node = current_node
		node_changed = False # Flag to track if the node changes

		if cmd == ".":
			break
		elif cmd == "a":
			node = current_node
			while node.parent is not None and node == node.parent.variations[0]:
				node = node.parent
			if node.parent is None:
				if node.variations and current_node != node.variations[0]:
					current_node = node.variations[0]
				else:
					Acusticator(["c4", 0.1, -0.5, volume], kind=2, adsr=[10, 10, 30, 50])
					print("\nAlready at the start of the game.")
			else:
				current_node = node
			node_changed = (current_node != previous_node)

		elif cmd == "s":
			if current_node.parent:
				current_node = current_node.parent
				Acusticator(["g5", .03, -.2, volume, "c5", .03, -.8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, -0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNo previous move.")
			node_changed = (current_node != previous_node)

		elif cmd == "d":
			if current_node.variations:
				current_node = current_node.variations[0]
				Acusticator(["c5", .03, .2, volume,"g5", .03, .8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, 0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNo subsequent moves.")
			node_changed = (current_node != previous_node)

		elif cmd == "f":
			start_node = current_node
			while current_node.variations:
				current_node = current_node.variations[0]
			node_changed = (current_node != start_node)
			if node_changed:
				Acusticator(["g5", 0.1, 0, volume,"p", 0.1, 0, volume,"c6", 0.05, 0, volume,"d6", 0.05, 0, volume,"g6", 0.2, 0, volume], kind=1, adsr=[5,5,90,5])
				print("You have reached the end of the main line.")
			else:
				print("Already at the end of the main line.")
		elif cmd == "g":
			if current_node.parent:
				vars = current_node.parent.variations
				try:
					index = vars.index(current_node)
					if index > 0:
						current_node = vars[index - 1]
						Acusticator(["d#5", 0.07, -0.4, volume], kind=1, adsr=[2,5,90,5])
					else:
						Acusticator(["c#4", 0.1, -0.6, volume], kind=2, adsr=[10, 10, 30, 50])
						print("No previous variations.")
				except ValueError:
					print("Error: current node not found in parent's variations.")
			else:
				print("No variation node available (you are at the root).")
			node_changed = (current_node != previous_node)

		elif cmd == "h":
			if current_node.parent:
				vars = current_node.parent.variations
				try:
					index = vars.index(current_node)
					if index < len(vars) - 1:
						current_node = vars[index + 1]
						Acusticator(["f5", 0.07, 0.4, volume], kind=1, adsr=[2,5,90,5])
					else:
						Acusticator(["c#4", 0.1, 0.6, volume], kind=2, adsr=[10, 10, 30, 50])
						print("No subsequent variations.")
				except ValueError:
					print("Error: current node not found in parent's variations.")
			else:
				print("No variation node available (you are at the root).")
			node_changed = (current_node != previous_node)

		elif cmd == "k":
			Acusticator(["g3", 0.06, 0, volume,"b3", 0.06, 0, volume,"a3", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			max_moves_num = (total_moves + 1) // 2
			target_fullmove = dgt(f"\nGo to move no.# (Max {max_moves_num}): ", kind="i", imin=1, imax=max_moves_num)
			target_ply = max(0, 2 * (target_fullmove - 1)) # White's half-move index
			temp_node = pgn_game # Start from the beginning again
			ply_count = 0
			found_node = pgn_game # Start with the root node

			# Navigate along the main line
			node_iterator = pgn_game.mainline() # Iterator on the main line
			for i, node in enumerate(node_iterator):
				 if i == target_ply:
						found_node = node
						break
			else:
				if target_ply > 0 : # If not looking for the start
					found_node = node # Go to the last available node
					print("\nReached end of line before requested move.")

			current_node = found_node
			Acusticator(["g6", 0.06, 0, volume,"b6", 0.06, 0, volume,"a6", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			node_changed = (current_node != previous_node)
			if node_changed and not current_node.move and target_ply > 0: # We went past the last move
				pass # Message printed in the loop above
			elif not node_changed:
				print("\nYou are already at this move/position.")
		elif cmd == "j":
			Acusticator(["d5", 0.08, 0, volume,"p", 0.08, 0, volume,"d6", 0.06, 0, volume], kind=1, adsr=[2,5,90,5])
			print("\nGame headers:")
			for k, v in pgn_game.headers.items():
				print(f"{k}: {v}")
		elif cmd == "l":
			try:
				# Use helper function to load one or more games
				new_game = LoadPGNFromClipboard() # Function handles output
				if new_game:
					pgn_game = new_game
					current_node = pgn_game # Reset to initial node
					previous_node = current_node # Update previous to avoid printing description
					node_changed = False # Node changed but not due to internal navigation
					move_list = list(pgn_game.mainline_moves())
					total_moves = len(move_list)
					Acusticator(["c6", 0.15, 0, volume], kind=1, adsr=[5, 10, 80, 5])
					print("\nNew PGN loaded from clipboard.")
					print("\nHeaders of the new game:\n")
					for k, v in pgn_game.headers.items():
						print(f"{k}: {v}")
					print(f"Total number of moves: {(total_moves+1)//2}")
				# else: LoadPGNFromClipboard already prints messages
			except Exception as e:
				print("\nError loading from clipboard:", e)
		elif cmd == "z":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculating bestline...")
			bestline_moves = CalculateBest(current_node.board(), bestmove=False, as_san=False)
			if bestline_moves:
				try:
					temp_node = current_node; first_new_node = None
					for i, move in enumerate(bestline_moves):
						found_existing = False
						for variation in temp_node.variations:
							if variation.move == move:
								temp_node = variation; found_existing = True
								if i == 0: first_new_node = temp_node
								break
						if not found_existing:
							new_variation_node = temp_node.add_variation(move)
							if i == 0: first_new_node = new_variation_node
							temp_node = new_variation_node
					if first_new_node:
						first_new_node.comment = ((first_new_node.comment or "") + " {Bestline added}").strip()
					saved = True; print("Bestline added/updated as variation.")
					Acusticator(["a5", 0.12, 0.3, volume,"b5", 0.12, 0.3, volume,"c6", 0.12, 0.3, volume,"d6", 0.12, 0.3, volume,"e6", 0.12, 0.3, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(f"\nError adding variation: {e}"); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nCould not calculate bestline.")
		elif cmd == "x":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculating bestmove...")
			bestmove_uci = CalculateBest(current_node.board(), bestmove=True, as_san=False)
			if bestmove_uci:
				try:
					san_move = current_node.board().san(bestmove_uci)
					current_node.comment = ((current_node.comment or "").strip() + f" {{BM: {san_move}}}").strip()
					saved = True; print(f"\nBestmove ({san_move}) added to comment.")
					Acusticator(["a5", 0.15, 0, volume,"d6", 0.15, 0, volume], kind=1, adsr=[3,7,88,2])
				except Exception as e: print(f"\nError getting SAN for bestmove: {e}"); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nCould not calculate bestmove.")
		elif cmd == "c":
			Acusticator(["d6", 0.012, 0, volume, "p", 0.15,0,0,"a6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			user_comment = dgt("\nEnter comment: ", kind="s").strip()
			if user_comment:
				if current_node.comment:
					current_node.comment += user_comment
				else:
					current_node.comment = user_comment
				saved = True; print("\nComment added/updated.")
				Acusticator(["a6", 0.012, 0, volume, "p", 0.15,0,0,"d6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			else: print("\nNo comment entered.")
		elif cmd == "v":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculating evaluation...")
			score_object = CalculateEvaluation(current_node.board())
			if score_object is not None:
				eval_val_str = "ERR"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_val_str = f"M{abs(mate_in)}"
				else:
					# --- USE ABSOLUTE SCORE ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_val_str = f"{cp/100:+.2f}" # Absolute value for comment
				eval_comment = f"{{Eval: {eval_val_str}}}" # "Val" changed to "Eval" for clarity
				current_node.comment = ((current_node.comment or "").strip() + f" {eval_comment}").strip()
				saved = True; print(f"\nEvaluation ({eval_val_str}) added to comment.")
				Acusticator(["g5", 0.07, 0, volume,"p", 0.04, 0, volume,"b5", 0.025, 0, volume], kind=1, adsr=[3,7,88,2])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nCould not calculate evaluation.")
		elif cmd == "b":
			if comment_auto_read:
				comment_auto_read = False
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b4", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print("\nAutomatic comment reading disabled.")
			else:
				comment_auto_read = True
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b6", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print("\nAutomatic comment reading enabled.")
		elif cmd == "n":
			if current_node.comment:
				Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
				confirm = key(f"\nDelete comment: '{current_node.comment}'? (y/n): ").lower() # "s/n" to "y/n"
				if confirm == "y": # "s" to "y"
					current_node.comment = ""; saved = True; print("Comment deleted.")
					Acusticator(["e4", 0.1, -0.4, volume], kind=1, adsr=[5,10,70,15])
				else: print("Deletion cancelled.")
			else: Acusticator(["b3", 0.12, -0.4, volume], kind=2, adsr=[5, 15, 20, 60]); print("\nNo comment to delete.")
		elif cmd == "q":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculating bestmove...")
			bestmove_uci = CalculateBest(current_node.board(), bestmove=True, as_san=False)
			if bestmove_uci:
				score_info_str = ""
				fen = current_node.board().fen()
				if fen in cache_analysis:
					analysis = cache_analysis[fen]
					if analysis:
						score_object = analysis[0].get("score")
						if score_object:
							pov_score = score_object.pov(current_node.board().turn)
							if pov_score.is_mate():
								mate_in = pov_score.mate()
								score_info_str = f"M{abs(mate_in)}"
							else:
								# --- USE ABSOLUTE SCORE ---
								cp = score_object.white().score(mate_score=30000)
								if cp is not None:
									score_info_str = f"{cp/100:+.2f}"
								else:
									score_info_str = "ERR"
				try:
					san_move = current_node.board().san(bestmove_uci)
					desc_move = DescribeMove(bestmove_uci, current_node.board(), annotation=None)
					print("\nBest move: "+desc_move)
					if score_info_str:
						extra_prompt = f" BM: {score_info_str} {san_move} "
					else:
						extra_prompt = f" BM: {san_move} "
					Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(f"\nError getting SAN/Descr for bestmove: {e}"); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); extra_prompt = " BM: Error "
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nCould not calculate bestmove."); extra_prompt = " BM: N/A "
		elif cmd == "w":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculating bestline...")
			bestline_list_descr = CalculateBest(current_node.board(), bestmove=False, as_san=True)
			if bestline_list_descr:
				Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume,"p", .15, 0, 0,"e7", 0.02, 0, volume,"p", .15, 0, 0,"g7", 0.02, 0, volume,"p", .15, 0, 0,"b7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				print("\nBest line:"); [print(line) for line in bestline_list_descr]
				score_info_str = ""
				san_move_w = "N/A"
				fen = current_node.board().fen()
				if fen in cache_analysis:
					analysis = cache_analysis[fen]
					if analysis:
						score_object = analysis[0].get("score")
						best_move_obj = analysis[0].get("pv", [None])[0]
						if score_object:
							pov_score = score_object.pov(current_node.board().turn)
							if pov_score.is_mate():
								mate_in = pov_score.mate()
								score_info_str = f"M{abs(mate_in)}"
							else:
								# --- USE ABSOLUTE SCORE ---
								cp = score_object.white().score(mate_score=30000)
								if cp is not None:
									score_info_str = f"{cp/100:+.2f}"
								else:
									score_info_str = "ERR"
						if best_move_obj:
							try: san_move_w = current_node.board().san(best_move_obj)
							except Exception: san_move_w = "Err"
						else: san_move_w = "N/A"
				if san_move_w != "N/A" and san_move_w != "Err":
					if score_info_str:
						extra_prompt = f" BM: {score_info_str} {san_move_w} "
					else:
						extra_prompt = f" BM: {san_move_w} "
				else:
					extra_prompt = f" BM: {san_move_w} "
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nCould not calculate bestline."); extra_prompt = " BM: N/A "
		elif cmd == "e":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculating analysis lines..."); fen = current_node.board().fen()
			cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
			analysis = cache_analysis[fen]
			if not analysis: print("No analysis results available."); continue
			main_info = analysis[0]; score = main_info.get("score"); wdl = None; wdl_str = "N/A"; score_str = "N/A"
			if score is not None:
				if hasattr(score, "wdl"): wdl_raw = score.wdl(); wdl = (wdl_raw[0]/10, wdl_raw[1]/10, wdl_raw[2]/10) if wdl_raw else None; wdl_str = f"{wdl[0]:.1f}%/{wdl[1]:.1f}%/{wdl[2]:.1f}%" if wdl else "N/A"
				if score.white().is_mate(): score_str = f"M{score.white().mate()}"
				else: score_cp = score.white().score(); score_str = f"{score_cp/100:+.2f}" if score_cp is not None else "N/A"
			depth = main_info.get("depth", "N/A"); seldepth = main_info.get("seldepth", "N/A"); nps = main_info.get("nps", "N/A"); hashfull = main_info.get("hashfull", "N/A"); hashfull_perc = f"{hashfull/10:.1f}%" if isinstance(hashfull, int) else "N/A"; debug_string = main_info.get("string", "N/A"); tbhits = main_info.get("tbhits", "N/A"); time_used = main_info.get("time", "N/A"); nodes = main_info.get("nodes", "N/A")
			Acusticator(["f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume], kind=1, adsr=[4,8,85,5])
			print(f"\nStats: Time: {time_used}s, Hash: {hashfull_perc}, TB: {tbhits}\nDebug: {debug_string}\nDepth: {depth}/{seldepth}, Eval: {score_str}, WDL: {wdl_str}\nNodes: {nodes}, NPS: {nps}\n\nAnalysis lines:")
			for i, info in enumerate(analysis, start=1):
				pv = info.get("pv", []); line_score = info.get("score"); line_score_str = "N/A"
				if line_score: line_score_str = f"M{line_score.white().mate()}" if line_score.white().is_mate() else f"{line_score.white().score()/100:+.2f}" if line_score.white().score() is not None else "N/A"
				if not pv: print(f"Line {i} ({line_score_str}): No moves found."); continue
				temp_board_pv = current_node.board().copy(); moves_san = []
				try:
					for move in pv: san_move = temp_board_pv.san(move).replace("!", "").replace("?",""); moves_san.append(san_move); temp_board_pv.push(move)
					print(f"Line {i} ({line_score_str}): {' '.join(moves_san)}")
				except Exception as e_pv: print(f"Line {i} ({line_score_str}): PV conversion error - {e_pv}")
			smart = key("\nDo you want to inspect lines in smart mode? (y/n): ").lower() # "s/n" to "y/n"
			if smart == "y": Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0]); SmartInspection(analysis, current_node.board()) # "s" to "y"
			else: Acusticator(["d4", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
		elif cmd == "r":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2]); extra_prompt = " CP: N/A "; continue
			print("\nCalculating evaluation...")
			score_object = CalculateEvaluation(current_node.board())
			Acusticator(["e5",.008,-1,volume])
			if score_object is not None:
				eval_str = "N/A"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_str = f"M{abs(mate_in)}"
				else:
					# --- USE ABSOLUTE SCORE ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_str = f"{cp/100:+.2f}"
					else:
						eval_str = "ERR"
				extra_prompt = f" CP: {eval_str} "
				Acusticator(["g3", 0.17, 0, volume,"g6",.012,0,volume], kind=1, adsr=[3,0,90,2])
			else:
				print("\nCould not calculate evaluation.")
				extra_prompt = " CP: N/A "
				Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2])
		elif cmd == "t":
			if ENGINE is None: print("\nEngine not initialized."); Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3]); extra_prompt = " WDL: N/A "; continue
			print("\nCalculating WDL..."); wdl_perc = CalculateWDL(current_node.board())
			if wdl_perc: adj_wdl=f"W{wdl_perc[0]:.1f}%/D{wdl_perc[1]:.1f}%/L{wdl_perc[2]:.1f}% "; extra_prompt=f"{adj_wdl} "; Acusticator(["g#5", 0.03, 0, volume,"c6", 0.03, 0, volume,"g#5", 0.03, 0, volume,"c6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
			else: print("\nCould not calculate WDL."); extra_prompt = " WDL: N/A "; Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "y":
			white_material, black_material = CalculateMaterial(current_node.board()); extra_prompt = f"Mtrl: {white_material}/{black_material} "
			Acusticator(["g#5", 0.03, 0, volume,"e5", 0.03, 0, volume,"d5", 0.03, 0, volume,"g6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "u":
			custom_board_view = CustomBoard(current_node.board().fen())
			if len(current_node.board().move_stack) > 0: custom_board_view.move_stack = current_node.board().move_stack
			custom_board_view.turn = current_node.board().turn; custom_board_view.fullmove_number = current_node.board().fullmove_number
			print("\n" + str(custom_board_view)); Acusticator(["d6", 0.03, 0, volume,"f6", 0.03, 0, volume,"g6", 0.03, 0, volume,"d7", 0.06, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "i":
			print(f"\nAnalysis time: {analysis_time}s. Cache: {len(cache_analysis)} positions.")
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_time_input = dgt("\nNew time (seconds) or ENTER: ", kind="f", fmin=0.1, fmax=300, default=analysis_time) # "INVIO" to "ENTER"
			if new_time_input != analysis_time: SetAnalysisTime(new_time_input); print("\nAnalysis time updated."); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print("\nAnalysis time not changed.")
		elif cmd == "o":
			print(f"\nAnalysis lines: {multipv}. Cache: {len(cache_analysis)} positions.")
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_lines = dgt("New number of lines or ENTER: ", kind="i",imin=1,imax=10, default=multipv) # "INVIO" to "ENTER"
			if new_lines != multipv: SetMultipv(new_lines); print("\nNumber of lines updated."); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print("\nNumber of lines not changed.")
		elif cmd == "?":
			print("\nAvailable commands in analysis mode:"); menu(ANALYSIS_COMMAND,show_only=True)
			Acusticator(["d5", .7, 0, volume], kind=3, adsr=[.02,0,100,99])
		else: # Unrecognized command
			Acusticator(["d3", 1.2, 0, volume], kind=3, adsr=[.02,0,100,99])
			print("Command not recognized.")
			node_changed = False # Ensure description is not printed

		# --- 4. Print Description if Node Changed ---
		if node_changed and current_node.move:
			annotation_suffix = None
			for nag_value, suffix in NAG_REVERSE_MAP.items():
				if nag_value in current_node.nags:
					annotation_suffix = suffix
					break
			# Print description of the move *we arrived at*
			print("\n" + DescribeMove(current_node.move,
									  current_node.parent.board() if current_node.parent else pgn_game.board(),
									  annotation=annotation_suffix))
	print("\nEnd of analysis")
	annotator_updated_flag = False
	if saved:
		new_annotator = f'Orologic V{VERSION} by {PROGRAMMER}'
		current_annotator = pgn_game.headers.get("Annotator", "")
		if current_annotator != new_annotator:
			pgn_game.headers["Annotator"] = new_annotator
			annotator_updated_flag = True
			print("\nAnnotator updated.")
	pgn_string_raw = ""
	try:
		pgn_string_raw = str(pgn_game)
		if not pgn_string_raw:
			print("!!!!!!!! WARNING: str(pgn_game) returned an empty string! !!!!!!!!")
	except Exception as e_str_export:
		print(f"!!!!!!!! DEBUG: EXCEPTION during str(pgn_game): {repr(e_str_export)} !!!!!!!!")
		pgn_string_raw = ""
	pgn_string_formatted = ""
	exception_occurred_format = False
	if pgn_string_raw and isinstance(pgn_string_raw, str):
		try:
			pgn_string_formatted = format_pgn_comments(pgn_string_raw)
		except Exception as e_format:
			exception_occurred_format = True
			print(f"!!!!!!!! DEBUG: EXCEPTION DURING format_pgn_comments: {repr(e_format)} !!!!!!!!")
			pgn_string_formatted = ""
	else:
		print("Warning: Raw PGN string empty or invalid, formatting skipped.")
	print(f"DEBUG: Exception during format? {exception_occurred_format}")
	if saved:
		if pgn_string_formatted:
			white_h = pgn_game.headers.get("White", "White").replace(" ", "_") # "Bianco" to "White"
			black_h = pgn_game.headers.get("Black", "Black").replace(" ", "_") # "Nero" to "Black"
			result_h = pgn_game.headers.get("Result", "*").replace("/", "-")
			new_default_file_name=f'{white_h}_vs_{black_h}_{result_h}'
			base_name = dgt(f"\nSave modified PGN.\nBase name (ENTER for '{new_default_file_name}'): ", kind="s",default=new_default_file_name).strip() # "INVIO" to "ENTER"
			if not base_name: base_name = new_default_file_name
			Acusticator(["f4", 0.05, 0, volume])
			new_filename_base = f"{base_name}-analyzed-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}" # "analizzato" to "analyzed"
			new_filename = sanitize_filename(new_filename_base) + ".pgn"
			try:
				with open(new_filename, "w", encoding="utf-8-sig") as f:
					f.write(pgn_string_formatted)
				print("Updated PGN saved as " + new_filename)
				if annotator_updated_flag: print("Annotator header has been updated in the file.")
			except Exception as e_save:
				print(f"Error saving PGN: {e_save}")
		else:
			print("Could not save PGN file due to errors during generation/formatting.")
	else:
		print("\nNo saveable changes made to PGN.")
	if pgn_string_formatted:
		try:
			pyperclip.copy(pgn_string_formatted)
			print("Current PGN (formatted) copied to clipboard.")
		except Exception as e_clip:
			print(f"Error copying PGN (formatted) to clipboard: {e_clip}")
	else:
		print("No formatted PGN to copy to clipboard.")
	print("Exiting analysis mode. Returning to main menu.")

def get_color_adjective(piece_color, gender): # Gender becomes less relevant for simple "white"/"black"
	# if gender == "m": # Not strictly needed for English "white"/"black"
	# 	return "white" if piece_color == chess.WHITE else "black"
	# else:
	# 	return "white" if piece_color == chess.WHITE else "black"
	return "white" if piece_color == chess.WHITE else "black"

def extended_piece_description(piece):
	piece_name = PIECE_NAMES.get(piece.piece_type, "piece").capitalize()
	color_adj = get_color_adjective(piece.color, "m") # "m" è un placeholder, get_color_adjective lo ignora.
	return f"{color_adj} {piece_name}"

def read_diagonal(game_state, base_column, direction_right):
	"""
	Reads the diagonal starting from the square on rank 1 of the base column.
	Parameter direction_right:
		- True: top-right direction (file +1, rank +1)
		- False: top-left direction (file -1, rank +1)
	"""
	base_column = base_column.lower()
	if base_column not in "abcdefgh":
		print("Invalid base column.")
		return
	file_index = ord(base_column) - ord("a")
	rank_index = 0  # Start from rank 1 (index 0)
	report = []
	base_descr = f"{LETTER_FILE_MAP.get(base_column, base_column)}1" # Removed space
	while 0 <= file_index < 8 and 0 <= rank_index < 8:
		square = chess.square(file_index, rank_index)
		piece = game_state.board.piece_at(square)
		if piece:
			current_file = chr(ord("a") + file_index)
			descriptive_file = LETTER_FILE_MAP.get(current_file, current_file)
			report.append(f"{descriptive_file}{rank_index+1}: {extended_piece_description(piece)}") # Removed space
		rank_index += 1
		file_index = file_index + 1 if direction_right else file_index - 1
	dir_str = "top-right" if direction_right else "top-left" # "alto-destra" to "top-right", "alto-sinistra" to "top-left"
	if report:
		print(f"Diagonal from {base_descr} in {dir_str} direction: " + ", ".join(report))
	else:
		print(f"Diagonal from {base_descr} in {dir_str} direction contains no pieces.")
def read_rank(game_state, rank_number):
	# Gets the set of squares for the rank (rank_number: 1-8)
	try:
		rank_bb = getattr(chess, f"BB_RANK_{rank_number}")
	except AttributeError:
		print("Invalid rank.") # "Traversa" to "rank"
		return
	squares = chess.SquareSet(rank_bb)
	report = []
	for square in squares:
		piece = game_state.board.piece_at(square)
		if piece:
			file_index = chess.square_file(square)
			file_letter = chr(ord("a") + file_index)
			descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
			# Use helper function for the piece
			report.append(f"{descriptive_file}{rank_number}: {extended_piece_description(piece)}") # Removed space
	if report:
		print(f"Rank {rank_number}: " + ", ".join(report))
	else:
		print(f"Rank {rank_number} is empty.")
def read_file(game_state, file_letter):
	# file_letter must be a letter from 'a' to 'h'
	file_letter = file_letter.lower()
	if file_letter not in "abcdefgh":
		print("Invalid column.") # "Colonna" to "column"
		return
	try:
		file_bb = getattr(chess, f"BB_FILE_{file_letter.upper()}")
	except AttributeError:
		print("Invalid column.")
		return
	squares = chess.SquareSet(file_bb)
	report = []
	for square in squares:
		piece = game_state.board.piece_at(square)
		if piece:
			rank = chess.square_rank(square) + 1
			file_index = chess.square_file(square)
			file_letter_descr = LETTER_FILE_MAP.get(chr(ord("a") + file_index), file_letter)
			report.append(f"{file_letter_descr}{rank}: {extended_piece_description(piece)}") # Removed space
	if report:
		print(f"File {LETTER_FILE_MAP.get(file_letter, file_letter)}: " + ", ".join(report)) # "Colonna" to "File"
	else:
		print(f"File {LETTER_FILE_MAP.get(file_letter, file_letter)} is empty.")
def read_square(game_state, square_str):
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print("Invalid square.") # "Casa" to "square"
		return
	# Calculate square color: (file+rank) even -> dark, otherwise light
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = "dark" # "scura" to "dark"
	else:
		color_descr = "light" # "chiara" to "light"
	piece = game_state.board.piece_at(square)
	if piece:
		base_msg = f"The square {square_str.upper()} is {color_descr} and contains {extended_piece_description(piece)}."
		# Calculate defenders and attackers for the occupied square
		defenders = game_state.board.attackers(piece.color, square)
		attackers = game_state.board.attackers(not piece.color, square)
		info_parts = []
		if defenders:
			count = len(defenders)
			word = "piece" if count == 1 else "pieces" # "pezzo"/"pezzi" to "piece"/"pieces"
			info_parts.append(f"defended by {count} { 'white' if piece.color == chess.WHITE else 'black' } {word}") # Adjusted order and color
		if attackers:
			count = len(attackers)
			word = "piece" if count == 1 else "pieces"
			info_parts.append(f"attacked by {count} { 'black' if piece.color == chess.WHITE else 'white' } {word}") # Adjusted order and color
		if info_parts:
			base_msg += " " + " and ".join(info_parts) + "." # " e " to " and "
		print(base_msg)
	else:
		base_msg = f"The square {square_str.upper()} is {color_descr} and is empty." # "risulta vuota" to "is empty"
		white_attackers = game_state.board.attackers(chess.WHITE, square)
		black_attackers = game_state.board.attackers(chess.BLACK, square)
		info_parts = []
		if white_attackers:
			count = len(white_attackers)
			word = "piece" if count == 1 else "pieces"
			info_parts.append(f"attacked by {count} white {word}") # Adjusted order
		if black_attackers:
			count = len(black_attackers)
			word = "piece" if count == 1 else "pieces"
			info_parts.append(f"attacked by {count} black {word}") # Adjusted order
		if info_parts:
			base_msg += " " + " and ".join(info_parts) + "."
		print(base_msg)
def report_piece_positions(game_state, piece_symbol):
	try:
		piece = chess.Piece.from_symbol(piece_symbol)
	except Exception as e:
		print("Not recognized: enter R N B Q K P, r n b q k p")
		return
	color_string = "White" if piece.color == chess.WHITE else "Black" # Capitalized "bianco"/"nero"
	full_name = PIECE_NAMES.get(piece.piece_type, "piece") # "pezzo" to "piece"
	squares = game_state.board.pieces(piece.piece_type, piece.color)
	positions = []
	for square in squares:
		# Get file and rank
		file_index = chess.square_file(square)
		rank = chess.square_rank(square) + 1
		file_letter = chr(ord("a") + file_index)
		descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
		positions.append(f"{descriptive_file}{rank}") # Removed space
	if positions:
		print(f"{color_string}: {full_name} on: " + ", ".join(positions)) # "in" to "on"
	else:
		print(f"No {color_string.lower()} {full_name} found.") # Adjusted for color
def report_white_time(game_state):
	initial_white = game_state.clock_config["phases"][game_state.white_phase]["white_time"]
	elapsed_white = initial_white - game_state.white_remaining
	if elapsed_white < 0:
		elapsed_white = 0
	perc_white = (elapsed_white / initial_white * 100) if initial_white > 0 else 0
	print("White time: " + FormatTime(game_state.white_remaining) + f" ({perc_white:.0f}%)") # "Tempo bianco" to "White time"
	return
def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	if elapsed_black < 0:
		elapsed_black = 0
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print("Black time: " + FormatTime(game_state.black_remaining) + f" ({perc_black:.0f}%)") # "Tempo nero" to "Black time"
	return
def format_pgn_comments(pgn_str):
	def repl(match):
		comment_text = match.group(1).strip()
		return "{\n" + comment_text + "\n}"
	return re.sub(r'\{(.*?)\}', repl, pgn_str, flags=re.DOTALL)
def generate_time_control_string(clock_config):
	phases = clock_config["phases"]
	tc_list = []
	for phase in phases:
		moves = phase["moves"]
		if clock_config["same_time"]:
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		else:
			base_time = int(phase["white_time"]) # This seems like it should be different for white/black if same_time is False
			inc = int(phase["white_inc"])       # Same here
		if moves == 0:
			# Sudden death: if increment is present, include it
			if inc > 0:
				tc = f"{base_time}+{inc}"
			else:
				tc = f"{base_time}"
		else:
			# Moves-based time control: include moves, time, and if present, increment
			if inc > 0:
				tc = f"{moves}/{base_time}+{inc}"
			else:
				tc = f"{moves}/{base_time}"
		tc_list.append(tc)
	return ", ".join(tc_list)
def seconds_to_mmss(seconds):
	m = int(seconds // 60)
	s = int(seconds % 60)
	return f"{m:02d} minutes and {s:02d} seconds!" # "minuti e" to "minutes and", "secondi!" to "seconds!"
def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print("Invalid time format. Expected mm:ss. Error:", e) # "Formato orario non valido. Atteso mm:ss. Errore:"
		return 0
def DescribeMove(move, board, annotation=None): # Added annotation parameter
	if board.is_castling(move):
		base_descr = "short castle" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "long castle" # "arrocco corto/lungo"
	else:
		san_base = ""
		try:
			uci_move = move.uci()
			piece_moved = board.piece_at(move.from_square)
			is_capture = board.is_capture(move) or board.is_en_passant(move)
			is_promo = move.promotion is not None
			piece_symbol = ""
			if piece_moved and piece_moved.piece_type != chess.PAWN:
				piece_symbol = piece_moved.symbol().upper()
			from_sq_str = chess.square_name(move.from_square)
			to_sq_str = chess.square_name(move.to_square)
			disambiguation = ""
			if piece_symbol: # Only for pieces, not pawns
				potential_origins = []
				for legal_move in board.legal_moves:
					lm_piece = board.piece_at(legal_move.from_square)
					if lm_piece and lm_piece.piece_type == piece_moved.piece_type and legal_move.to_square == move.to_square:
						potential_origins.append(legal_move.from_square)
				if len(potential_origins) > 1:
					file_disamb_needed = False
					for sq in potential_origins:
						if sq != move.from_square and chess.square_file(sq) == chess.square_file(move.from_square):
							file_disamb_needed = True
							break
					if not file_disamb_needed:
						disambiguation = from_sq_str[0] # Use only file
					else:
						# Check if rank is sufficient
						rank_disamb_needed = False
						for sq in potential_origins:
							if sq != move.from_square and chess.square_rank(sq) == chess.square_rank(move.from_square):
								rank_disamb_needed = True
								break
						if not rank_disamb_needed:
							disambiguation = from_sq_str[1] # Use only rank
						else:
							disambiguation = from_sq_str # Use file and rank
			promo_str = ""
			if is_promo:
				promo_piece_symbol = chess.piece_symbol(move.promotion).upper()
				promo_str = f"={promo_piece_symbol}"
			capture_char = "x" if is_capture else ""
			if piece_symbol: # Pieces
				san_base = f"{piece_symbol}{disambiguation}{capture_char}{to_sq_str}{promo_str}"
			else: # Pawns (disambiguation is implicit in file if capturing)
				if is_capture:
					san_base = f"{from_sq_str[0]}{capture_char}{to_sq_str}{promo_str}"
				else:
					san_base = f"{to_sq_str}{promo_str}" # Only destination and promotion
		except Exception as e:
			try:
				san_base = board.san(move)
				san_base = san_base.replace("!","").replace("?","") # Remove only base ! and ?
			except Exception:
				# Last fallback: UCI-based description
				san_base = f"Move from {chess.square_name(move.from_square)} to {chess.square_name(move.to_square)}" # "Mossa da...a..."
		pattern = re.compile(r'^([RNBQK])?([a-h1-8]{1,2})?(x)?([a-h][1-8])(=([RNBQ]))?$')
		pawn_pattern = re.compile(r'^([a-h])?(x)?([a-h][1-8])(=([RNBQ]))?$')
		m = pattern.match(san_base)
		if m and m.group(1): # Piece match
			piece_letter = m.group(1)
			disamb = m.group(2) or ""
			capture = m.group(3)
			dest = m.group(4)
			promo_letter = m.group(6)
			piece_type = chess.PIECE_SYMBOLS.index(piece_letter.lower())
		else:
			m = pawn_pattern.match(san_base) # Try pawn match
			if m:
				piece_letter = "" # Pawn
				# Pawn disambiguation is only starting file in case of capture
				disamb = m.group(1) or ""
				capture = m.group(2)
				dest = m.group(3)
				promo_letter = m.group(5)
				piece_type = chess.PAWN
			else:
				base_descr = san_base # Use fallback string
				piece_type = None # Unknown type
		if piece_type is not None: # If parsing worked
			piece_name = PIECE_NAMES.get(piece_type, "piece").lower() # "pezzo" to "piece"
			descr = piece_name.capitalize() # Capitalize first letter
			if disamb:
				if piece_type == chess.PAWN:
					descr += f" {LETTER_FILE_MAP.get(disamb, disamb)}"
				else: # For other pieces
					parts = [LETTER_FILE_MAP.get(ch, ch) if ch.isalpha() else ch for ch in disamb]
					descr += " on " + "".join(parts) # " di " to " on " (e.g. Knight on b1)
			if capture:
				descr += " takes" # " prende"
				captured_piece = None
				if board.is_en_passant(move):
					ep_square = move.to_square + (-8 if board.turn == chess.WHITE else 8) # Correct offset for en passant
					captured_piece = board.piece_at(ep_square)
					descr += " en passant"
				else:
					captured_piece = board.piece_at(move.to_square)
				if captured_piece and not board.is_en_passant(move):
					descr += " " + PIECE_NAMES.get(captured_piece.piece_type, "piece").lower()
				dest_file_info = dest[0]
				dest_rank_info = dest[1]
				dest_name_info = LETTER_FILE_MAP.get(dest_file_info, dest_file_info)
				descr += " on " + dest_name_info + dest_rank_info # " in " to " on ", removed space
			else:
				dest_file = dest[0]
				dest_rank = dest[1]
				dest_name = LETTER_FILE_MAP.get(dest_file, dest_file)
				descr += " to " + dest_name + dest_rank # " in " to " to ", removed space
			if promo_letter:
				promo_type = chess.PIECE_SYMBOLS.index(promo_letter.lower())
				promo_name = PIECE_NAMES.get(promo_type, "piece").lower()
				descr += " and promotes to " + promo_name # " e promuove a "
			base_descr = descr # Save base description
	board_after_move = board.copy()
	board_after_move.push(move)
	final_descr = base_descr
	if board_after_move.is_checkmate():
		final_descr += " checkmate!" # " scacco matto!"
	elif board_after_move.is_check():
		final_descr += " check" # " scacco"
	if annotation and annotation in ANNOTATION_DESC:
		final_descr += f" ({ANNOTATION_DESC[annotation]})"
	return final_descr

def GenerateMoveSummary(game_state):
	summary = []
	move_number = 1
	board_copy = CustomBoard()
	for i in range(0, len(game_state.move_history), 2):
		white_move_san = game_state.move_history[i]
		try:
			white_move = board_copy.parse_san(white_move_san)
			white_move_desc = DescribeMove(white_move, board_copy)
			board_copy.push(white_move)
		except Exception as e:
			white_move_desc = f"Error in white's move: {e}" # "Errore nella mossa del bianco:"
		if i + 1 < len(game_state.move_history):  # If black's move exists
			black_move_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_move_san)
				black_move_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except Exception as e:
				black_move_desc = f"Error in black's move: {e}" # "Errore nella mossa del nero:"
			summary.append(f"{move_number}. {white_move_desc}, {black_move_desc}")
		else:
			summary.append(f"{move_number}. {white_move_desc}")
		move_number += 1
	return summary
def CalculateMaterial(board):
	white_value=0
	black_value=0
	for square in chess.SQUARES:
		piece=board.piece_at(square)
		if piece is not None:
			piece_symbol=piece.symbol()
			if piece_symbol.isupper():
				white_value+=PIECE_VALUES[piece_symbol]
			else:
				black_value+=PIECE_VALUES[piece_symbol]
	return white_value,black_value
def NormalizeMove(m):
	m=m.strip()
	if m.lower().startswith("o-o-o") or m.lower().startswith("0-0-0"):
		suffix=m[len("o-o-o"):]
		return "O-O-O"+suffix
	elif m.lower().startswith("o-o") or m.lower().startswith("0-0"):
		suffix=m[len("o-o"):]
		return "O-O"+suffix
	elif m and m[0] in "rnkq" and m[0].islower(): # This part is fine for English too
		return m[0].upper()+m[1:]
	else:
		return m
def LoadDB():
	if not os.path.exists(DB_FILE):
		return {"clocks":[],"default_pgn":{}}
	with open(DB_FILE,"r") as f:
		return json.load(f)
def SaveDB(db):
	with open(DB_FILE,"w") as f:
		json.dump(db,f,indent="\t")
def LoadEcoDatabaseWithFEN(filename="eco.db"):
	"""
	Loads the ECO file, calculates the final FEN for each line
	and returns a list of dictionaries containing:
	"eco", "opening", "variation", "moves" (SAN list),
	"fen" (FEN of the final position), "ply" (number of half-moves).
	Uses node.board().san() for more robust SAN generation.
	"""
	eco_entries = []
	if not os.path.exists(filename):
		print(f"File {filename} not found.")
		return eco_entries
	try:
		with open(filename, "r", encoding="utf-8") as f:
			content = f.read()
	except Exception as e:
		print(f"Error reading {filename}: {e}")
		return eco_entries
	# Remove any comment blocks enclosed between { and }
	content = re.sub(r'\{[^}]*\}', '', content, flags=re.DOTALL)
	stream = io.StringIO(content)
	game_count = 0
	skipped_count = 0
	while True:
		# Save current stream position for seek
		stream_pos = stream.tell()
		try:
			headers = chess.pgn.read_headers(stream)
			if headers is None:
				break # End of file or stream

			# Reposition and read the complete game
			stream.seek(stream_pos) # Go back to the start of headers
			game = chess.pgn.read_game(stream)
			game_count += 1

			if game is None:
				# Could happen with malformed PGN entries after headers
				print(f"Warning: Could not read PGN game {game_count} after header.") # "Attenzione: Impossibile leggere..."
				skipped_count += 1
				# Try to read the next entry by skipping empty lines
				while True:
					line = stream.readline()
					if line is None: break # EOF
					if line.strip(): # Found a non-empty line
						stream.seek(stream.tell() - len(line.encode('utf-8'))) # Go back to read it as header next time
						break
				continue

			eco_code = game.headers.get("ECO", "")
			opening = game.headers.get("Opening", "")
			variation = game.headers.get("Variation", "")
			moves = []
			node = game
			last_valid_node = game # Track the last valid node to get final FEN
			parse_error = False

			while node.variations:
				next_node = node.variations[0]
				move = next_node.move
				try:
					# Use CURRENT node's board to generate SAN for NEXT move
					# This is generally more reliable
					san = node.board().san(move)
					moves.append(san)
				except Exception as e:
					parse_error = True
					break # Stop parsing this ECO line
				node = next_node
				last_valid_node = node # Update last successfully processed node

			if not parse_error and moves: # Only if we have valid moves and no errors
				# Get FEN from the board of the LAST valid node reached
				final_fen = last_valid_node.board().board_fen()
				ply_count = len(moves) # Number of half-moves
				eco_entries.append({
					"eco": eco_code,
					"opening": opening,
					"variation": variation,
					"moves": moves,
					"fen": final_fen,
					"ply": ply_count
				})
			elif parse_error:
				skipped_count += 1

		except ValueError as ve: # Specifically catch common PGN parsing errors
			print(f"Value error while parsing PGN game {game_count}: {ve}") # "Errore di valore..."
			skipped_count += 1
			# Try to recover by looking for the next PGN entry '['
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['): # Found a possible start of header
					stream.seek(stream.tell() - len(line.encode('utf-8'))) # Go back
					break
		except Exception as e:
			print(f"Generic error while parsing PGN game {game_count}: {e}") # "Errore generico..."
			skipped_count += 1
			# Similar recovery attempt as above
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['):
					stream.seek(stream.tell() - len(line.encode('utf-8')))
					break

	print(f"Loaded {len(eco_entries)} ECO opening lines.") # "Caricate ... linee di apertura ECO."
	if skipped_count > 0:
		print(f"Warning: {skipped_count} ECO lines were skipped due to parsing errors.") # "Attenzione: ... linee ECO sono state saltate..."
	return eco_entries
def DetectOpeningByFEN(current_board, eco_db_with_fen):
	"""
	Returns the opening entry corresponding to the current position.
	Handles transpositions by comparing position FENs.
	If there are multiple matches, it prefers the one with the same number of moves (ply),
	and among these, the one with the longest move sequence in the ECO database.
	"""
	current_fen = current_board.board_fen()
	current_ply = current_board.ply()
	possible_matches = []
	for entry in eco_db_with_fen:
		if entry["fen"] == current_fen:
			possible_matches.append(entry)
	if not possible_matches:
		return None # No match found for this position
	# Filter by matching number of moves (ply), if possible
	exact_ply_matches = [m for m in possible_matches if m["ply"] == current_ply]
	if exact_ply_matches:
		# If there are matches with the same number of moves, choose the most specific
		# (the one defined with more moves in the ECO db, though they should be equal if ply is equal)
		return max(exact_ply_matches, key=lambda x: len(x["moves"]))
	else:
		return None # No match found with the correct number of moves
def SecondsToHMS(seconds):
	h=int(seconds//3600)
	m=int((seconds%3600)//60)
	s=int(seconds%60)
	return "{:02d}:{:02d}:{:02d}".format(h,m,s)
def FormatTime(seconds):
	total=int(seconds)
	h=total//3600
	m=(total%3600)//60
	s=total%60
	parts=[]
	if h:
		parts.append(f"{h} {'hour' if h==1 else 'hours'}") # "ora"/"ore"
	if m:
		parts.append(f"{m} {'minute' if m==1 else 'minutes'}") # "minuto"/"minuti"
	if s:
		parts.append(f"{s} {'second' if s==1 else 'seconds'}") # "secondo"/"secondi"
	return ", ".join(parts) if parts else "0 seconds" # "0 secondi"
def ParseTime(prompt):
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":"))
		return h*3600+m*60+s
	except Exception as e:
		print("Invalid time format. Expected hh:mm:ss. Error:",e) # "Formato orario non valido. Atteso hh:mm:ss. Errore:"
		return 0
class ClockConfig:
	def __init__(self,name,same_time,phases,alarms,note):
		self.name=name
		self.same_time=same_time
		self.phases=phases
		self.alarms=alarms
		self.note=note
	def to_dict(self):
		return {"name":self.name,"same_time":self.same_time,"phases":self.phases,"alarms":self.alarms,"note":self.note}
	@staticmethod
	def from_dict(d):
		return ClockConfig(d["name"],d["same_time"],d["phases"],d.get("alarms",[]),d.get("note",""))
def CreateClock():
	print("\nCreate Clocks\n") # "Creazione orologi"
	name=dgt("Clock name: ",kind="s") # "Nome dell'orologio:"
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume],sync=True)
	db=LoadDB()
	if any(c["name"]==name for c in db["clocks"]):
		print("A clock with this name already exists.") # "Un orologio con questo nome esiste già."
		Acusticator(["a3",1,0,volume],kind=2,adsr=[0,0,100,100])
		return
	same=dgt("White and Black start with the same time? (ENTER for yes, 'n' for no): ",kind="s",smin=0,smax=1) # "Bianco e Nero partono con lo stesso tempo? (Invio per sì, 'n' per no): "
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(f"Time (hh:mm:ss) for phase {phase_count+1}: ") # "Tempo (hh:mm:ss) per fase..."
			inc=dgt(f"Increment in seconds for phase {phase_count+1}: ",kind="i") # "Incremento in secondi per fase..."
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(f"Time for White (hh:mm:ss) phase {phase_count+1}: ") # "Tempo per il bianco..."
			inc_w=dgt(f"Increment for White in phase {phase_count+1}: ",kind="i") # "Incremento per il bianco fase..."
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			total_seconds_b=ParseTime(f"Time for Black (hh:mm:ss) phase {phase_count+1}: ") # "Tempo per il nero..."
			inc_b=dgt(f"Increment for Black in phase {phase_count+1}: ",kind="i") # "Incremento per il nero fase..."
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(f"Number of moves for phase {phase_count+1} (0 to end): ",kind="i") # "Numero di mosse per fase... (0 per terminare): "
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt("Number of alarms to enter (max 5, 0 for none): ",kind="i",imax=5,default=0) # "Numero di allarmi da inserire (max 5, 0 per nessuno): "
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	for i in range(num_alarms):
		alarm_input = dgt(f"Enter time (mm:ss) for alarm {i+1}: ", kind="s") # "Inserisci il tempo (mm:ss) per l'allarme..."
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt("Enter a note for the clock (optional): ",kind="s",default="") # "Inserisci una nota per l'orologio (opzionale): "
	Acusticator(["f7", .09, 0, volume,"d5", .07, 0, volume,"p",.1,0,0,"d5", .07, 0, volume,"f7", .09, 0, volume])
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	db["clocks"].append(new_clock.to_dict())
	SaveDB(db)
	print("\nClock created and saved.") # "Orologio creato e salvato."
def ViewClocks():
	print("\nView Clocks\n") # "Visualizzazione orologi"
	db=LoadDB()
	if not db["clocks"]:
		print("No clocks saved.") # "Nessun orologio salvato."
		return
	for idx,c in enumerate(db["clocks"]):
		indicatore="W=B" if c["same_time"] else "W/B" # "B=N" to "W=B", "B/N" to "W/B" (White/Black)
		fasi="" # "phases"
		for i,phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str=SecondsToHMS(phase["white_time"])
				fasi+=f" P{i+1}:{time_str}+{phase['white_inc']}" # "F" to "P" (Phase)
			else:
				time_str_w=SecondsToHMS(phase["white_time"])
				time_str_b=SecondsToHMS(phase["black_time"])
				fasi+=f" P{i+1}: White:{time_str_w}+{phase['white_inc']}, Black:{time_str_b}+{phase['black_inc']}" # "Bianco" to "White", "Nero" to "Black"
		num_alarms = len(c.get("alarms", []))  # Count alarms
		alarms_str = f" Alarms ({num_alarms})" # "Allarmi"
		print(f"{idx+1}. {c['name']} - {indicatore}{fasi}{alarms_str}")
		if c.get("note",""):
			print(f"\tNote: {c['note']}") # "Nota:"
	Acusticator(["c5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
	attesa=key("Press any key to return to the main menu.") # "Premi un tasto per tornare al menu principale."
	Acusticator(["a4", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
def SelectClock(db):
	db = LoadDB()
	if not db["clocks"]:
		Acusticator(["c3", 0.72, 0, volume], kind=2, adsr=[0,0,100,100])
		print("No clocks saved.")
		return
	else:
		print(f"There are {len(db['clocks'])} clocks in the collection.") # "Ci sono ... orologi nella collezione."
	choices = {}
	for c in db["clocks"]:
		indicatore = "W=B" if c["same_time"] else "W/B"
		fasi = ""
		for j, phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str = SecondsToHMS(phase["white_time"])
				fasi += f" P{j+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w = SecondsToHMS(phase["white_time"])
				time_str_b = SecondsToHMS(phase["black_time"])
				fasi += f" P{j+1}: White:{time_str_w}+{phase['white_inc']}, Black:{time_str_b}+{phase['black_inc']}"
		num_alarms = len(c.get("alarms", []))
		alarms_str = f" Alarms ({num_alarms})"
		first_line = f"{indicatore}{fasi}{alarms_str}"
		note_line = c.get("note", "")
		description = first_line + "\n  " + note_line # Kept space for indentation
		choices[c["name"]] = description
	choice = menu(choices, show=True, keyslist=True, full_keyslist=False)
	Acusticator(["f7", .013, 0, volume])
	if choice:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == choice), None)
		if idx is not None:
			return db["clocks"][idx]
	else:
		print("No clock selected.") # "Nessun orologio selezionato."
def DeleteClock(db):
	print("\nDelete Saved Clocks\n") # "Eliminazione orologi salvati"
	Acusticator(["b4", .02, 0, volume,"d4",.2,0,volume])
	orologio = SelectClock(db) # "clock"
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			del db["clocks"][idx]
			Acusticator(["c4", 0.025, 0, volume])
			SaveDB(db)
			print(f"\nClock '{clock_name}' deleted, {len(db['clocks'])} remaining.") # "Orologio ... eliminato, ne rimangono..."
	return
def EditPGN():
	Acusticator(["d6", .02, 0, volume,"g4",.02,0,volume])
	print("\nEdit PGN Default Info\n") # "Modifica info default per PGN"
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	default_event = default_pgn.get("Event", "Orologic Game")
	event = dgt(f"Event [{default_event}]: ", kind="s", default=default_event) # "Evento"
	Acusticator(["d6", .02, -1, volume,"g4",.02,-1,volume])
	if event.strip() == "":
		event = default_event
	default_site = default_pgn.get("Site", "Unknown Venue") # "Sede sconosciuta"
	site = dgt(f"Site [{default_site}]: ", kind="s", default=default_site) # "Sede"
	Acusticator(["d6", .02, -.66, volume,"g4",.02,-.66,volume])
	if site.strip() == "":
		site = default_site
	default_round = default_pgn.get("Round", "Round 1")
	round_ = dgt(f"Round [{default_round}]: ", kind="s", default=default_round)
	Acusticator(["d6", .02, -.33, volume,"g4",.02,-.33,volume])
	if round_.strip() == "":
		round_ = default_round
	default_white = default_pgn.get("White", "White") # "Bianco"
	white = dgt(f"White's Name [{default_white}]: ", kind="s", default=default_white).strip().title() # "Nome del Bianco"
	Acusticator(["d6", .02, 0, volume,"g4",.02,0,volume])
	if white.strip() == "":
		white = default_white
	default_black = default_pgn.get("Black", "Black") # "Nero"
	black = dgt(f"Black's Name [{default_black}]: ", kind="s", default=default_black).strip().title() # "Nome del Nero"
	Acusticator(["d6", .02, .33, volume,"g4",.02,.33,volume])
	if black.strip() == "":
		black = default_black
	default_white_elo = default_pgn.get("WhiteElo", "1200")
	white_elo = dgt(f"White's Elo [{default_white_elo}]: ", kind="s", default=default_white_elo) # "Elo del Bianco"
	Acusticator(["d6", .02, .66, volume,"g4",.02,.66,volume])
	if white_elo.strip() == "":
		white_elo = default_white_elo
	default_black_elo = default_pgn.get("BlackElo", "1200")
	black_elo = dgt(f"Black's Elo [{default_black_elo}]: ", kind="s", default=default_black_elo) # "Elo del Nero"
	Acusticator(["d6", .02, 1, volume,"g4",.02,1,volume])
	if black_elo.strip() == "":
		black_elo = default_black_elo
	db["default_pgn"] = {
		"Event": event,
		"Site": site,
		"Round": round_,
		"White": white,
		"Black": black,
		"WhiteElo": white_elo,
		"BlackElo": black_elo
	}
	SaveDB(db)
	print("\nPGN default information updated.") # "Informazioni default per il PGN aggiornate."
class CustomBoard(chess.Board):
	def __str__(self):
		board_str = "FEN: " + str(self.fen()) + "\n"
		white_material, black_material = CalculateMaterial(self)
		ranks = range(8, 0, -1) if self.turn == chess.WHITE else range(1, 9)
		files = range(8) if self.turn == chess.WHITE else range(7, -1, -1)
		for rank in ranks:
			board_str += str(rank)
			for file in files:
				square = chess.square(file, rank - 1)
				piece = self.piece_at(square)
				if piece:
					symbol = piece.symbol()
					board_str += symbol.upper() if piece.color == chess.WHITE else symbol.lower()
				else:
					board_str += "-" if (rank + file) % 2 == 0 else "+"
			board_str += "\n"
		board_str += " abcdefgh" if self.turn == chess.WHITE else " hgfedcba"
		if self.fullmove_number == 1 and self.turn == chess.WHITE:
			last_move_info = "1.???"
		else:
			move_number = self.fullmove_number - (1 if self.turn == chess.WHITE else 0)
			if len(self.move_stack) > 0:
				temp_board = CustomBoard()
				for m in self.move_stack[:-1]:
					temp_board.push(m)
				last_move = self.move_stack[-1]
				try:
					last_move_san = temp_board.san(last_move)
				except Exception as e:
					last_move_san = "???"
			else:
				last_move_san = "???"
			if self.turn == chess.BLACK: # This means it's Black's turn, so White just moved
				last_move_info = f"{move_number}. {last_move_san}"
			else: # White's turn, Black just moved
				last_move_info = f"{move_number}... {last_move_san}"
		board_str += f" {last_move_info} Material: {white_material}/{black_material}" # "Materiale"
		return board_str
	def copy(self, stack=True):
		new_board = super().copy(stack=stack)
		new_board.__class__ = CustomBoard
		return new_board
	def __repr__(self):
		return self.__str__()
class GameState:
	def __init__(self,clock_config):
		self.board=CustomBoard()
		self.clock_config=clock_config
		if clock_config["same_time"]:
			self.white_remaining = clock_config["phases"][0]["white_time"]
			self.black_remaining = clock_config["phases"][0]["black_time"]  # Or equivalently, ["white_time"]
		else:
			self.white_remaining = clock_config["phases"][0]["white_time"]
			self.black_remaining = clock_config["phases"][0]["black_time"]
		self.white_phase=0
		self.black_phase=0
		self.white_moves=0
		self.black_moves=0
		# Initial turn remains "white" (white to move)
		self.active_color="white"
		self.paused=False
		self.game_over=False
		self.move_history=[]
		self.pgn_game = chess.pgn.Game.from_board(CustomBoard())
		self.pgn_game.headers["Event"]="Orologic Game"
		self.pgn_node=self.pgn_game
	def switch_turn(self):
		if self.active_color=="white":
			self.white_moves+=1
			if self.white_phase<len(self.clock_config["phases"])-1:
				if self.white_moves>=self.clock_config["phases"][self.white_phase]["moves"] and self.clock_config["phases"][self.white_phase]["moves"]!=0:
					self.white_phase+=1
					Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03,0, volume], kind=3, adsr=[20, 10, 75, 20])
					print(self.white_player + f" enters phase {self.white_phase+1}, phase time " + FormatTime(self.clock_config["phases"][self.white_phase]["white_time"])) # " entra in fase ... tempo fase "
					self.white_remaining=self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves+=1
			if self.black_phase<len(self.clock_config["phases"])-1:
				if self.black_moves>=self.clock_config["phases"][self.black_phase]["moves"] and self.clock_config["phases"][self.black_phase]["moves"]!=0:
					self.black_phase+=1
					Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03,0, volume], kind=3, adsr=[20, 10, 75, 20])
					print(self.black_player + f" enters phase {self.black_phase+1}, phase time " + FormatTime(self.clock_config["phases"][self.black_phase]["black_time"]))
					self.black_remaining=self.clock_config["phases"][self.black_phase]["black_time"]
		self.active_color="black" if self.active_color=="white" else "white"
def clock_thread(game_state):
	last_time=time.time()
	triggered_alarms_white = set()
	triggered_alarms_black = set()
	while not game_state.game_over:
		current_time=time.time()
		elapsed=current_time-last_time
		last_time=current_time
		if not game_state.paused:
			if game_state.active_color=="white":
				game_state.white_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_white and abs(game_state.white_remaining - alarm) < elapsed:
						print(f"\nAlarm: White's time reached {seconds_to_mmss(alarm)}",end="") # "Allarme: tempo del bianco raggiunto..."
						Acusticator(["c4",0.2,-0.75,volume])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(f"\nAlarm: Black's time reached {seconds_to_mmss(alarm)}",end="") # "Allarme: tempo del nero raggiunto..."
						Acusticator(["c4",0.2,0.75,volume])
						triggered_alarms_black.add(alarm)
		if game_state.white_remaining<=0 or game_state.black_remaining<=0:
			Acusticator(["e4", 0.2, -0.5, volume, "d4", 0.2, 0, volume, "c4", 0.2, 0.5, volume], kind=1, adsr=[10, 0, 90, 10])
			game_state.game_over=True
			print("Flag fallen!") # "Bandierina caduta!"
			if game_state.white_remaining <= 0:
				game_state.pgn_game.headers["Result"] = "0-1"  # Black wins
				print(f"White's time expired. {game_state.black_player} wins.") # "Tempo del Bianco scaduto. ... vince."
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			else:
				game_state.pgn_game.headers["Result"] = "1-0"  # White wins
				print(f"Black's time expired. {game_state.white_player} wins.") # "Tempo del Nero scaduto. ... vince."
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
		time.sleep(0.1)
def StartGame(clock_config):
	print("\nStarting game\n") # "Avvio partita"
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", "White") # "Bianco"
	black_default = default_pgn.get("Black", "Black") # "Nero"
	white_elo_default = default_pgn.get("WhiteElo", "1500")
	black_elo_default = default_pgn.get("BlackElo", "1500")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", "Unknown Venue") # "Sede sconosciuta"
	round_default = default_pgn.get("Round", "Round 1")
	eco_database = LoadEcoDatabaseWithFEN("eco.db")
	last_eco_msg = ""
	last_valid_eco_entry = None
	white_player = dgt(f"White's Name [{white_default}]: ", kind="s", default=white_default).strip().title() # "Nome del bianco"
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_player == "":
		white_player = white_default
	black_player = dgt(f"Black's Name [{black_default}]: ", kind="s", default=black_default).strip().title() # "Nome del nero"
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_player == "":
		black_player = black_default
	white_elo = dgt(f"White's Elo [{white_elo_default}]: ", kind="s", default=white_elo_default) # "Elo del bianco"
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_elo.strip() == "":
		white_elo = white_elo_default
	black_elo = dgt(f"Black's Elo [{black_elo_default}]: ", kind="s", default=black_elo_default) # "Elo del nero"
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_elo.strip() == "":
		black_elo = black_elo_default
	event = dgt(f"Event [{event_default}]: ", kind="s", default=event_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if event.strip() == "":
		event = event_default
	site = dgt(f"Site [{site_default}]: ", kind="s", default=site_default) # "Sede"
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	round_ = dgt(f"Round [{round_default}]: ", kind="s", default=round_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	db["default_pgn"] = {
		"Event": event,
		"Site": site,
		"Round": round_,
		"White": white_player,
		"Black": black_player,
		"WhiteElo": white_elo,
		"BlackElo": black_elo
	}
	SaveDB(db)
	key("Press any key to start the game when you are ready...",attesa=7200) # "Premi un tasto qualsiasi per iniziare la partita quando sei pronto..."
	Acusticator(["c6", .07, 0, volume, "p", .93, 0, .5, "c6", .07, 0, volume, "p", .93, 0, .5, "c6", .07, 0, volume, "p", .93, 0, .5, "c7", .5, 0, volume], kind=1, sync=True)
	game_state=GameState(clock_config)
	game_state.white_player=white_player
	game_state.black_player=black_player
	game_state.pgn_game.headers["White"]=white_player
	game_state.pgn_game.headers["Black"]=black_player
	game_state.pgn_game.headers["WhiteElo"]=white_elo
	game_state.pgn_game.headers["BlackElo"]=black_elo
	game_state.pgn_game.headers["Event"]=event
	game_state.pgn_game.headers["Site"]=site
	game_state.pgn_game.headers["Round"]=round_
	game_state.pgn_game.headers["TimeControl"] = generate_time_control_string(clock_config)
	game_state.pgn_game.headers["Date"]=datetime.datetime.now().strftime("%Y.%m.%d")
	game_state.pgn_game.headers["Annotator"]=f"Orologic V{VERSION} by {PROGRAMMER}"
	threading.Thread(target=clock_thread, args=(game_state,), daemon=True).start()
	paused_time_start=None
	while not game_state.game_over:
		if not game_state.move_history:
			prompt="\nStart, move 0. " # "Inizio, mossa 0."
		elif len(game_state.move_history)%2==1: # White just moved
			full_move=(len(game_state.move_history)+1)//2
			prompt=f"{full_move}. {game_state.move_history[-1]} " # White's move shown, Black to play
		else: # Black just moved
			full_move=(len(game_state.move_history))//2
			prompt=f"{full_move}... {game_state.move_history[-1]} " # Black's move shown, White to play
		if game_state.paused:
			prompt="["+prompt.strip()+"] "
		user_input=dgt(prompt,kind="s")
		# --- Special command handling ---
		if user_input.startswith("/"):
			Acusticator(["c5", 0.07, -1, volume,"d5", 0.07, -.75, volume,"e5", 0.07, -.5, volume,"f5", 0.07, -.25, volume,"g5", 0.07, 0, volume,"a5", 0.07, .25, volume,"b5", 0.07, .5, volume,"c6", 0.07, .75, volume], kind=3, adsr=[0, 0, 100, 100])
			base_column = user_input[1:2].strip()
			read_diagonal(game_state, base_column, True)
		elif user_input.startswith("\\"):
			Acusticator(["c5", 0.07, 1, volume,"d5", 0.07, 0.75, volume,"e5", 0.07, 0.5, volume,"f5", 0.07, 0.25, volume,"g5", 0.07, 0, volume,"a5", 0.07, -0.25, volume,"b5", 0.07, -0.5, volume,"c6", 0.07, -0.75, volume], kind=3, adsr=[0, 0, 100, 100])
			base_column = user_input[1:2].strip()
			read_diagonal(game_state, base_column, False)
		elif user_input.startswith("-"):
			param = user_input[1:].strip()
			if len(param) == 1 and param.isalpha():
				Acusticator(["c5", 0.07, 0, volume, "d5", 0.07, 0, volume, "e5", 0.07, 0, volume, "f5", 0.07, 0, volume, "g5", 0.07, 0, volume, "a5", 0.07, 0, volume, "b5", 0.07, 0, volume, "c6", 0.07, 0, volume], kind=3, adsr=[0, 0, 100, 100])
				read_file(game_state, param)
			elif len(param) == 1 and param.isdigit():
				rank_number = int(param)
				if 1 <= rank_number <= 8:
					Acusticator(["g5", 0.07, -1, volume,"g5", 0.07, -.75, volume,"g5", 0.07, -.5, volume,"g5", 0.07, -.25, volume,"g5", 0.07, 0, volume,"g5", 0.07, .25, volume,"g5", 0.07, .5, volume,"g5", 0.07, .75, volume], kind=3, adsr=[0, 0, 100, 100])
					read_rank(game_state, rank_number)
				else:
					print("Invalid rank.") # "Traversa non valida."
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				Acusticator(["d#4", .7, 0, volume], kind=1, adsr=[0, 0, 100, 100])
				read_square(game_state, param)
			else:
				print("Dash command not recognized.") # "Comando dash non riconosciuto."
		elif user_input.startswith(","):
			Acusticator(["a3", .06, -1, volume, "c4", .06, -0.5, volume, "d#4", .06, 0.5, volume, "f4", .06, 1, volume], kind=3, adsr=[20, 5, 70, 25])
			report_piece_positions(game_state, user_input[1:2])
		elif user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			if cmd==".?":
				Acusticator([440.0, 0.3, 0, 0.5, 880.0, 0.3, 0, 0.5], kind=1, adsr=[10, 0, 100, 20])
				menu(DOT_COMMANDS,show_only=True,p="Available commands:") # "Comandi disponibili:"
			elif cmd==".1":
				Acusticator(['a6', 0.14, -1, volume], kind=1, adsr=[0, 0, 100, 100])
				report_white_time(game_state)
			elif cmd==".2":
				Acusticator(['b6', 0.14, 1, volume], kind=1, adsr=[0, 0, 100, 100])
				report_black_time(game_state)
			elif	cmd==".3":
				Acusticator(['e7', 0.14, 0, volume], kind=1, adsr=[0, 0, 100, 100])
				report_white_time(game_state)
				report_black_time(game_state)
			elif cmd==".4":
				Acusticator(['f7', 0.14, 0, volume], kind=1, adsr=[0, 0, 100, 100])
				diff=abs(game_state.white_remaining-game_state.black_remaining)
				adv="White" if game_state.white_remaining>game_state.black_remaining else "Black" # "bianco"/"nero"
				print(f"{adv} has an advantage of "+FormatTime(diff)) # "... in vantaggio di "
			elif cmd==".5":
				if game_state.paused:
					Acusticator(['d4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					pause_duration = time.time() - paused_time_start if paused_time_start else 0
					hours = int(pause_duration // 3600)
					minutes = int((pause_duration % 3600) // 60)
					seconds = int(pause_duration % 60)
					ms = int((pause_duration - int(pause_duration)) * 1000)
					print(f"Paused for: {f'{hours:2d} hours, ' if hours else ''}{f'{minutes:2d} minutes, ' if minutes or hours else ''}{f'{seconds:2d} seconds and ' if seconds or minutes or hours else ''}{f'{ms:3d} ms' if ms else ''}") # "Tempo in pausa da:"
				else:
					Acusticator(['f4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					player = game_state.white_player if game_state.active_color=="white" else game_state.black_player
					print(f"{player}'s clock is running") # "Orologio di ... in moto"
			elif cmd==".m":
				Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
				white_material,black_material=CalculateMaterial(game_state.board)
				print(f"Material: {game_state.white_player} {white_material}, {game_state.black_player} {black_material}")
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					print("Clocks paused") # "Orologi in pausa"
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
					print("Pause lasted "+FormatTime(pause_duration)) # "Pausa durata "
			elif cmd==".q":
				if game_state.paused and game_state.move_history:
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
					undone_move_san = game_state.move_history.pop()
					game_state.board.pop()
					# Update PGN: move pointer to parent node
					current_node = game_state.pgn_node
					parent = current_node.parent
					if current_node in parent.variations:
						parent.variations.remove(current_node)
					game_state.pgn_node = parent
					# Save undone move (in SAN format) to a list
					if not hasattr(game_state, "cancelled_san_moves"):
						game_state.cancelled_san_moves = []
					game_state.cancelled_san_moves.insert(0, undone_move_san)
					# Rollback applied increment (removes only increment)
					if game_state.active_color == "black": # Means it was White's turn before pop
						game_state.white_remaining -= game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
						game_state.active_color = "white"
					else: # Black's turn before pop
						game_state.black_remaining -= game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
						game_state.active_color = "black"
					print("Last move undone: " + undone_move_san) # "Ultima mossa annullata:"
			elif cmd.startswith(".b+") or cmd.startswith(".b-") or cmd.startswith(".n+") or cmd.startswith(".n-"):
				if game_state.paused:
					try:
						adjust=float(cmd[3:])
						if cmd.startswith(".b+"):
							Acusticator(["d4", 0.15, -.5, volume, "f4", 0.15, -.5, volume, "a4", 0.15, -.5, volume, "c5", 0.15, -.5, volume], kind=1, adsr=[15, 0, 90, 5])
							game_state.white_remaining+=adjust
						elif cmd.startswith(".b-"):
							Acusticator(["c5", 0.15, -.5, volume, "a4", 0.15, -.5, volume, "f4", 0.15, -.5, volume, "d4", 0.15, -.5, volume], kind=1, adsr=[15, 0, 90, 5])
							game_state.white_remaining-=adjust
						elif cmd.startswith(".n+"): # 'n' usually for black
							Acusticator(["d4", 0.15, .5, volume, "f4", 0.15, .5, volume, "a4", 0.15, .5, volume, "c5", 0.15, .5, volume], kind=1, adsr=[15, 0, 90, 5])
							game_state.black_remaining+=adjust
						elif cmd.startswith(".n-"):
							Acusticator(["c5", 0.15, .5, volume, "a4", 0.15, .5, volume, "f4", 0.15, .5, volume, "d4", 0.15, .5, volume], kind=1, adsr=[15, 0, 90, 5])
							game_state.black_remaining-=adjust
						print("New white time: "+FormatTime(game_state.white_remaining)+", black: "+FormatTime(game_state.black_remaining)) # "Nuovo tempo bianco: ..., nero: ..."
					except:
						print("Invalid command.") # "Comando non valido."
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, volume, "g4", 0.2, -0.3, volume, "c5", 0.2, 0.3, volume, "e5", 0.2, 1, volume, "g5", 0.4, 0, volume], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				Acusticator([900.0, 0.1, 0, volume, 440.0, 0.3, 0, volume], kind=1, adsr=[1, 0, 80, 19])
				summary = GenerateMoveSummary(game_state)
				if summary:
					print("\nList of played moves:\n") # "Lista mosse giocate:"
					for line in summary:
						print(line)
				else:
					print("No moves played yet.") # "Nessuna mossa ancora giocata."
			elif cmd in [".1-0",".0-1",".1/2",".*"]:
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
				if cmd==".1-0":
					result="1-0"
				elif cmd==".0-1":
					result="0-1"
				elif cmd==".1/2":
					result="1/2-1/2"
				else:
					result="*"
				print("Result assigned: "+result) # "Risultato assegnato:"
				game_state.pgn_game.headers["Result"]=result
				game_state.game_over=True
			elif cmd.startswith(".c"):
				new_comment = cmd[2:].strip()
				if game_state.move_history:
					if game_state.pgn_node.comment:
						game_state.pgn_node.comment += "\n" + new_comment
					else:
						game_state.pgn_node.comment = new_comment
					Acusticator(["f5", 0.1, 0, volume,"p",0.04,0,0,"c5", 0.02, 0, volume], kind=1, adsr=[3,7,88,2])
					print("Comment recorded for move: " + game_state.move_history[-1]) # "Commento registrato per la mossa:"
				else:
					print("No move to comment on.") # "Nessuna mossa da commentare."
			else:
				Acusticator(["e3", 1, 0, volume,"a2", 1, 0, volume], kind=3, adsr=[1,7,100,92])
				print("Command not recognized.") # "Comando non riconosciuto."
		# --- Move handling ---
		else:
			if game_state.paused:
				print("Cannot enter new moves while time is paused. Resume time with .p") # "Non è possibile inserire nuove mosse..."
				Acusticator(["b3",.2,0,volume],kind=2)
				continue

			# --- START MODIFICATION ---
			raw_input = NormalizeMove(user_input) # Normalize before looking for suffix
			annotation_suffix = None
			move_san_only = raw_input # Default: input is just the move

			# Look for an annotation suffix
			match = ANNOTATION_SUFFIX_PATTERN.search(raw_input)
			if match:
				annotation_suffix = match.group(1)
				move_san_only = raw_input[:-len(annotation_suffix)].strip() # Remove suffix and extra spaces

			# Try to parse only the move part
			try:
				move = game_state.board.parse_san(move_san_only)
				# --- END MODIFICATION ---

				board_copy=game_state.board.copy()
				# --- MODIFICATION: Pass annotation to DescribeMove ---
				description=DescribeMove(move, board_copy, annotation=annotation_suffix)
				# --- END MODIFICATION ---

				Acusticator([1000.0, 0.01, 0, volume], kind=1, adsr=[0, 0, 100, 0])
				if game_state.active_color=="white":
					print(game_state.white_player+": "+description)
				else:
					print(game_state.black_player+": "+description)

				# Get base SAN for history (without suffixes)
				san_move_base = game_state.board.san(move)
				# Remove any !, ? automatically generated by board.san() if not intended
				san_move_base = san_move_base.replace("!","").replace("?","")

				game_state.board.push(move)
				game_state.move_history.append(san_move_base) # Use base SAN for simple history

				# Add new move as mainline to PGN
				new_node = game_state.pgn_node.add_variation(move)

				# --- START MODIFICATION: Add NAG/Comment to PGN ---
				if annotation_suffix:
					if annotation_suffix == "=":
						# Add standard comment for draw offer
						existing_comment = new_node.comment or ""
						if existing_comment:
							new_node.comment = existing_comment + " {Draw offer}" # "{Proposta di patta}"
						else:
							new_node.comment = "{Draw offer}"
					elif annotation_suffix in NAG_MAP:
						nag_value = NAG_MAP[annotation_suffix][0]
						new_node.nags.add(nag_value)
				# --- END MODIFICATION ---

				# If there are undone moves, add a comment to the new node
				if hasattr(game_state, "cancelled_san_moves") and game_state.cancelled_san_moves:
					undo_comment = "Cancelled moves: " + " ".join(game_state.cancelled_san_moves) # "Mosse annullate:"
					existing_comment = new_node.comment or ""
					if existing_comment:
						new_node.comment = existing_comment + " " + undo_comment
					else:
						new_node.comment = undo_comment
					# Empty the list for next operations
					del game_state.cancelled_san_moves

				# Update PGN pointer to new node
				game_state.pgn_node = new_node

				# ECO Logic (unchanged)
				if eco_database:
					current_board = game_state.board
					eco_entry = DetectOpeningByFEN(current_board, eco_database)
					new_eco_msg = ""
					current_entry_this_turn = eco_entry if eco_entry else None
					if eco_entry:
						new_eco_msg = f"{eco_entry['eco']} - {eco_entry['opening']}"
						if eco_entry['variation']:
							new_eco_msg += f" ({eco_entry['variation']})"
					if new_eco_msg and new_eco_msg != last_eco_msg:
						print("Opening detected: " + new_eco_msg) # "Apertura rilevata:"
						last_eco_msg = new_eco_msg
						last_valid_eco_entry = current_entry_this_turn
					elif not new_eco_msg and last_eco_msg: # If we were in an opening and now we are not
						last_eco_msg = "" # Reset message if no longer in a known opening

				# End of game checks (unchanged, but messages translated)
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "0-1" if game_state.board.turn == chess.WHITE else "1-0" # Corrected: if it's White's turn, Black delivered mate.
					game_state.pgn_game.headers["Result"] = result
					winner = game_state.black_player if result == "0-1" else game_state.white_player
					print(f"Checkmate! {winner} wins.") # "Scacco matto! Vince..."
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_stalemate():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by stalemate!") # "Patta per stallo!"
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_insufficient_material():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by insufficient material!") # "Patta per materiale insufficiente!"
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_seventyfive_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by 75-move rule!") # "Patta per la regola delle 75 mosse!"
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_fivefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by fivefold repetition!") # "Patta per ripetizione della posizione (5 volte)!"
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_fifty_moves(): # Python-chess handles the claim automatically if pushed.
					game_state.game_over = True # Consider claim automatic for simplicity
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by 50-move rule!") # "Patta per la regola delle 50 mosse!"
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition():
					game_state.game_over = True # Consider claim automatic for simplicity
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by threefold repetition!") # "Patta per triplice ripetizione della posizione!"
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break


				# Apply increment and switch turn (unchanged)
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()

			except Exception as e:
				illegal_result=verbose_legal_moves_for_san(game_state.board,move_san_only) # Use move_san_only here
				Acusticator([600.0, 0.6, 0, volume], adsr=[5, 0, 35, 90])
				print(f"Move '{move_san_only}' illegal or not recognized ({e}). On the indicated square, the following are possible:\n{illegal_result}") # "Mossa ... illegale o non riconosciuta...Sulla casa indicata sono possibili:"

	# --- Post-game logic (unchanged, messages translated) ---
	game_state.pgn_game.headers["WhiteClock"] = FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = FormatClock(game_state.black_remaining)
	print("Game ended.") # "Partita terminata."
	if last_valid_eco_entry:
		game_state.pgn_game.headers["ECO"] = last_valid_eco_entry["eco"]
		game_state.pgn_game.headers["Opening"] = last_valid_eco_entry["opening"]
		if last_valid_eco_entry["variation"]:
			game_state.pgn_game.headers["Variation"] = last_valid_eco_entry["variation"]
		else:
			if "Variation" in game_state.pgn_game.headers:
				del game_state.pgn_game.headers["Variation"]
	else: # Ensure no old ECO tags remain if game didn't match any
		if "ECO" in game_state.pgn_game.headers: del game_state.pgn_game.headers["ECO"]
		if "Opening" in game_state.pgn_game.headers: del game_state.pgn_game.headers["Opening"]
		if "Variation" in game_state.pgn_game.headers: del game_state.pgn_game.headers["Variation"]


	pgn_str=str(game_state.pgn_game)
	pgn_str = format_pgn_comments(pgn_str) # Format comments for readability
	filename = f"{white_player}-{black_player}-{game_state.pgn_game.headers.get('Result', '*')}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
	filename=sanitize_filename(filename)
	with open(filename, "w", encoding="utf-8") as f:
		f.write(pgn_str)
	print("PGN saved as "+filename+".") # "PGN salvato come ..."
	try:
		pyperclip.copy(pgn_str)
		print("PGN copied to clipboard.") # "PGN copiato negli appunti."
	except Exception as e:
		print(f"Error copying PGN to clipboard: {e}") # "Errore durante la copia del PGN negli appunti:"

	analyze_choice = key("Do you want to analyze the game? (y/n): ").lower() # "Vuoi analizzare la partita? (s/n):"
	if analyze_choice == "y": # "s" to "y"
		db = LoadDB()
		engine_config = db.get("engine_config", {})
		if not engine_config or not engine_config.get("engine_path"):
			print("Engine not configured. Returning to menu.") # "Motore non configurato. Ritorno al menù."
			return
		else:
			# Ensure engine is initialized before analyzing
			if ENGINE is None:
				if not InitEngine():
					print("Could not initialize engine. Analysis cancelled.") # "Impossibile inizializzare il motore. Analisi annullata."
					return
			# Clear cache if necessary before starting a new analysis
			cache_analysis.clear()
			AnalyzeGame(game_state.pgn_game)
	else:
		Acusticator([880.0, 0.2, 0, volume, 440.0, 0.2, 0, volume], kind=1, adsr=[25, 0, 50, 25])
def OpenManual():
	print("\nOpening manual\n") # "Apertura manuale"
	readme="readme_en.htm" # Changed from readme_it.htm
	if os.path.exists(readme):
		webbrowser.open(readme)
	else:
		# Try Italian readme as a fallback if English one not found
		readme_it="readme_it.htm"
		if os.path.exists(readme_it):
			print(f"English manual '{readme}' not found, opening Italian version '{readme_it}'.")
			webbrowser.open(readme_it)
		else:
			print(f"Manual file '{readme}' (and fallback '{readme_it}') does not exist.") # "Il file readme_it.htm non esiste."
def SchermataIniziale(): # Initial Screen
	now = datetime.datetime.now()
	diff1 = relativedelta(now, BIRTH_DATE)
	diff2 = relativedelta(now, RELEASE_DATE)
	parts1 = []
	if diff1.years:
		parts1.append(f"{diff1.years} years") # "anni"
	if diff1.months:
		parts1.append(f"{diff1.months} months") # "mesi"
	if diff1.days:
		parts1.append(f"{diff1.days} days") # "giorni"
	if diff1.hours:
		parts1.append(f"{diff1.hours} hours") # "ore"
	if diff1.minutes:
		parts1.append(f"and {diff1.minutes} minutes") # "e ... minuti"
	age_string = ", ".join(parts1) if parts1 else "less than a minute"

	parts2 = []
	if diff2.years:
		parts2.append(f"{diff2.years} years")
	if diff2.months:
		parts2.append(f"{diff2.months} months")
	if diff2.days:
		parts2.append(f"{diff2.days} days")
	if diff2.hours:
		parts2.append(f"{diff2.hours} hours")
	if diff2.minutes: # Only show minutes if no larger units, or if there are hours/days etc.
		if parts2: # If there are already years, months, days, or hours
			parts2.append(f"and {diff2.minutes} minutes")
		else: # Only minutes
			parts2.append(f"{diff2.minutes} minutes")

	release_string = ", ".join(parts2) if parts2 else "less than a minute" # Default if very recent

	print(f"\nHello! Welcome, I am Orologic and I am {age_string} old.") # "Ciao! Benvenuto, sono Orologic e ho..."
	print(f"The latest version is {VERSION} and was released on {RELEASE_DATE.strftime('%d/%m/%Y %H:%M')}.") # "L'ultima versione è la ... ed è stata rilasciata il..."
	if release_string != "less than a minute":
		print(f"\tthat is: {release_string} ago.") # "\tcioè: ... fa."
	else:
		print(f"\tthat is: just now.")

	print("\t\tAuthor: "+PROGRAMMER) # "Autore:"
	print("\t\t\tType '?' to display the menu.") # "Digita '?' per visualizzare il menù."
	Acusticator(['c4', 0.125, 0, volume, 'd4', 0.125, 0, volume, 'e4', 0.125, 0, volume, 'g4', 0.125, 0, volume, 'a4', 0.125, 0, volume, 'e5', 0.125, 0, volume, 'p', 0.125, 0, 0.5, 'a5', 0.125, 0, volume], kind=1, adsr=[0.01, 0, 100, 99])
def Main():
	global	volume
	db = LoadDB()
	volume = db.get("volume", 0.5)
	launch_count = db.get("launch_count", 0) + 1
	db["launch_count"] = launch_count
	SaveDB(db)
	SchermataIniziale()
	InitEngine()
	while True:
		scelta=menu(MENU_CHOICES, show=True, keyslist=True, full_keyslist=False) # "choice"
		if scelta == "analizza": # "analyze"
			Acusticator(["a5", .04, 0, volume, "e5", .04, 0, volume, "p",.08,0,0, "g5", .04, 0, volume, "e6", .120, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			AnalyzeGame(None)
		elif scelta=="crea": # "create"
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			CreateClock()
		elif scelta=="comandi": # "commands" - this key was not in MENU_CHOICES, assuming it was for DOT_COMMANDS
			Acusticator([500.0, 0.4, -1, volume, 800.0, 0.4, 1, volume], kind=3, adsr=[20, 10, 50, 20])
			menu(DOT_COMMANDS,show_only=True, p="Available dot commands:") # Added a title for clarity
		elif scelta=="motore": # "engine"
			Acusticator(["e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume])
			EditEngineConfig()
		elif scelta=="volume":
			Acusticator(["f6",.02,0,volume,"p",.04,0,volume,"a6",.02,0,volume])
			old_volume=volume
			volume = dgt(f"\nCurrent volume: {int(volume*100)}, new? (0-100): ", kind="i", imin=0, imax=100, default=50) # "Volume attuale: ..., nuovo?"
			volume/=100
			db = LoadDB()
			db["volume"] = volume
			SaveDB(db)
			Acusticator(["c5",.5,0,old_volume],adsr=[0,0,100,100],sync=True)
			Acusticator(["c5",.5,0,volume],adsr=[0,0,100,100])
		elif scelta=="vedi": # "view"
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			ViewClocks()
		elif scelta=="elimina": # "delete"
			DeleteClock(db)
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="pgn":
			EditPGN()
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="manuale": # "manual"
			OpenManual()
		elif scelta=="gioca": # "play"
			Acusticator(["c5", 0.1, 0, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0, volume, "c6", 0.3, 0, volume, "g5", 0.1, 0, volume, "e5", 0.1, 0, volume, "c5", 0.1, 0, volume], kind=1, adsr=[5, 5, 90, 10])
			print("\nStarting game\n") # "Avvio partita"
			db=LoadDB()
			if not db["clocks"]:
				Acusticator(["c5", 0.3, 0, volume, "g4", 0.3, 0, volume], kind=1, adsr=[30, 20, 80, 20])
				print("No clocks available. Create one first.") # "Nessun orologio disponibile. Creane uno prima."
			else:
				clock_config=SelectClock(db)
				if clock_config is not None:
					StartGame(clock_config)
				else:
					print("Invalid choice.") # "Scelta non valida."
		elif scelta==".": # Exit
			Acusticator(["g4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "a4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "p", 0.15, 0, 0, "b4", 0.15, -0.5, volume, "c5", 0.3, 0.5, volume], kind=1, adsr=[5, 0, 100, 5])
			if ENGINE is not None:
				ENGINE.quit()
				print("\nConnection with UCI engine closed") # "Connessione col motore UCI chiusa"
			break
if __name__=="__main__":
	time_start = datetime.datetime.now()
	board=CustomBoard()
	Main()
	time_end = datetime.datetime.now()
	delta = relativedelta(time_end, time_start)
	components = []
	if delta.days:
		components.append(f"{delta.days} days") # "giorni"
	if delta.hours:
		components.append(f"{delta.hours} hours") # "ore"
	if delta.minutes:
		components.append(f"{delta.minutes} minutes") # "minuti"
	if delta.seconds:
		components.append(f"{delta.seconds} seconds") # "secondi"
	ms = delta.microseconds // 1000
	if ms:
		components.append(f"{ms} milliseconds") # "millisecondi"
	result = ", ".join(components) if components else "0 milliseconds"
	final_db = LoadDB()
	final_launch_count = final_db.get("launch_count", "unknown") # "sconosciuto"
	# Constructing the ordinal suffix for launch_count
	s = str(final_launch_count)
	if s.endswith('11') or s.endswith('12') or s.endswith('13'):
		ordinal_suffix = 'th'
	elif s.endswith('1'):
		ordinal_suffix = 'st'
	elif s.endswith('2'):
		ordinal_suffix = 'nd'
	elif s.endswith('3'):
		ordinal_suffix = 'rd'
	else:
		ordinal_suffix = 'th'

	print(f"Goodbye from Orologic {VERSION}.\nThis was our {final_launch_count}{ordinal_suffix} time and we had fun together for: {result}") # "Arrivederci da Orologic ... Questa era la nostra ...a volta e ci siamo divertiti assieme per:"
	sys.exit(0)