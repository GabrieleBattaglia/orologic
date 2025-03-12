# Conception date: 14/02/2025 by Gabriele Battaglia e ChatGPT o3-mini-high
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re, pyperclip, io, chess.engine
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator, key
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="3.9.11"
RELEASE_DATE=datetime.datetime(2025,3,12,17,27)
PROGRAMMER="Gabriele Battaglia & ChatGPT o3-mini-high"
DB_FILE="orologic_db.json"
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
SMART_COMMANDS = {
	"s": "Go to the previous move",
	"d": "Go to the next move",
	"r": "Update CP evaluation",
	"?": "View this command list",
	".": "Exit smart mode"
}
ANALYSIS_COMMAND = {
	"a": "Go to the beginning or parent node (if in variation)",
	"s": "Back 1 move",
	"d": "Forward 1 move and display any comment",
	"f": "Go to the end or node of the next variation branch",
	"g": "Select previous variation node",
	"h": "Select next variation node",
	"j": "Reads the game headers",
	"k": "Go to move",
	"l": "Load PGN from clipboard",
	"z": "Inserts the bestline as a variation in the PGN",
	"x": "Inserts the bestmove in the PGN",
	"c": "Requests a comment from the user and adds it",
	"v": "Inserts the centipawn evaluation in the PGN",
	"b": "Displays the comment again",
	"n": "Deletes the comment (or allows you to choose it if there are more than one)",
	"q": "Calculate and add the bestmove to the prompt",
	"w": "Calculate and display the bestline, also adding the bestmove to the prompt",
	"e": "Display the analysis lines and allow their smart inspection",
	"r": "Calculate and add the evaluation to the prompt",
	"t": "Displays the Win Draw Lost percentages in the current position",
	"y": "Add the material balance to the prompt",
	"u": "Display the board",
	"i": "Set the engine analysis seconds",
	"o": "Set the number of analysis lines to display",
	"?": "Show this command list",
	".": "Exit analysis mode and save the PGN if different from the original"
}
DOT_COMMANDS={
	".1":"Show remaining time for white",
	".2":"Show remaining time for black",
	".3":"Show both clocks",
	".4":"Compare remaining times and indicate advantage",
	".5":"Reports which clock is running or the duration of the pause, if active",
	".l":"View the list of played moves",
	".m":"Show the value of the material still on the board",
	".p":"Pause/restart the clocks countdown",
	".q":"Undo the last move (only when paused)",
	".b+":"Add time to white (when paused)",
	".b-":"Subtract time from white (when paused)",
	".n+":"Add time to black (when paused)",
	".n-":"Subtract time from black (when paused)",
	".s":"Display the board",
	".c":"Add a comment to the current move",
	".1-0":"Assign victory to white (1-0) and end the game",
	".0-1":"Assign victory to black (0-1) and end the game",
	".1/2":"Assign draw (1/2-1/2) and end the game",
	".*":"Assign undefined result (*) and end the game",
	".?":"View the list of available commands",
	"/[column]":"Show the top-right diagonal starting from the base of the given column",
	"\\[column]":"Show the top-left diagonal starting from the base of the given column",
	"-[column|rank|square]":"Show the pieces on that column or rank or square",
	",[PieceName]":"Show the position(s) of the indicated piece"}
MENU_CHOICES={
	"analyze":"Enter game analysis mode",
	"create":"... a new clock to add to the collection",
	"delete":"... one of the saved clocks",
	"play":"Start the game",
	"guide":"Show the app guide",
	"engine":"Configure settings for the chess engine",
	"pgn":"Set default info for the PGN",
	"clocks":"... the saved clocks",
	"volume":"Allows volume adjustment of audio effects",
	".":"Exit the application"}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}
LETTER_FILE_MAP={chr(ord("a")+i):FILE_NAMES.get(i,chr(ord("a")+i)) for i in range(8)}
PIECE_NAMES={chess.PAWN:"pawn",chess.KNIGHT:"knight",chess.BISHOP:"bishop",chess.ROOK:"rook",chess.QUEEN:"queen",chess.KING:"King"}
PIECE_GENDER = {
	chess.PAWN: "m",
	chess.KNIGHT: "m",
	chess.BISHOP: "m",
	chess.ROOK: "f",
	chess.QUEEN: "f",
	chess.KING: "m"
}
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
		return "No legal moves found for the indicated destination."
	result_lines=[]
	i=1
	for move in legal_moves:
		verbose_desc=DescribeMove(move,board.copy())
		result_lines.append(f"{i}°: {verbose_desc}")
		i+=1
	return "\nHere are the possible moves\n:".join(result_lines)
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
	underscore.
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
	choice = dgt(f"Which line do you want to inspect? (1/{len(analysis_lines)} ", kind="i", imin=1, imax=len(analysis_lines),	default=1)
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves:
		print("Empty line, inspection terminated.")
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
		# Get the verbose description of the current move, from the point of view of the board before executing it
		move_verbose = DescribeMove(current_move, temp_board)
		smart_prompt=f"\nLine {line_index+1}: ({current_index}/{total_moves}), CP: {eval_str}, {temp_board.fullmove_number}... {move_verbose}"
		cmd = key(smart_prompt).lower()
		if cmd == ".":
			break
		elif cmd == "s":
			if current_index > 1:
				current_index -= 1
			else:
				print("\nThere are no previous moves.")
		elif cmd == "?":
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			# Update the evaluation by rebuilding the board up to the current move
			temp_board = board.copy()
			for move in pv_moves[:current_index]:
				temp_board.push(move)
			new_eval = CalculateEvaluation(temp_board)
			if new_eval is not None:
				if isinstance(new_eval, int):
					eval_str = f"{new_eval/100:.2f}"
				else:
					eval_str = str(new_eval)
				print("\nEvaluation updated.")
			else:
				print("\nUnable to update the evaluation.")
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				print("\nThere are no more moves.")
		else:
			print("\nUnrecognized command.")
def CalculateBest(board, bestmove=True, as_san=False):
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
			moves_with_numbers = []
			i = 0
			# Iterate over the list of moves in the PV, grouping them in pairs (white move and, if present, black move)
			while i < len(best_line):
				if temp_board.turn == chess.WHITE:
					move_num = temp_board.fullmove_number
					white_move = best_line[i]
					white_san = temp_board.san(white_move)
					temp_board.push(white_move)
					i += 1
					move_str = f"{move_num}. {white_san}"
					if i < len(best_line) and temp_board.turn == chess.BLACK:
						black_move = best_line[i]
						black_san = temp_board.san(black_move)
						temp_board.push(black_move)
						i += 1
						move_str += f" {black_san}"
					moves_with_numbers.append(move_str)
				else:
					# Case where the PV starts with a Black move (uncommon)
					move_num = temp_board.fullmove_number
					black_move = best_line[i]
					black_san = temp_board.san(black_move)
					temp_board.push(black_move)
					i += 1
					moves_with_numbers.append(f"{move_num}... {black_san}")
			moves_str = " ".join(moves_with_numbers)
			score = analysis[0].get("score")
			if score is not None and score.relative.is_mate():
				mate_moves = abs(score.relative.mate())
				moves_str = f"Mate in {mate_moves}, {moves_str}"
			if bestmove:
				return moves_with_numbers[0]
			else:
				return moves_str
		else:
			if bestmove:
				return best_line[0]
			else:
				return best_line
	except Exception as e:
		print("Error in CalculateBestLine:", e)
		return None
def CalculateEvaluation(board):
	"""
	Calculates and returns the centipawn evaluation for the given board.
	If the evaluation is mate, it returns a special value.
	"""
	global ENGINE, analysis_time, multipv
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=multipv)
		analysis = cache_analysis[fen]
		score = analysis[0].get("score")
		if score is None:
			return None
		# If the engine detects a checkmate situation...
		if score.is_mate():
			# If the board is in checkmate, we can use board.outcome()
			if board.is_checkmate():
				outcome = board.outcome()
				if outcome is not None:
					# outcome.winner is True for white, False for black
					return 10000 if outcome.winner == chess.WHITE else -10000
			# In other cases (e.g. mate during analysis) we use score.white()
			return 10000 if score.white().mate() > 0 else -10000
		else:
			return score.white().score()
	except Exception as e:
		print("Error in CalculateEvaluation:", e)
		return None
def CalculateWDL(board):
	"""
	Calculates and returns the WDL (win/draw/loss) percentages provided by the engine.
	Returns a tuple (win, draw, loss) in percentages.
	"""
	global ENGINE, analysis_time, multipv
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=multipv)
			print(f"\nAnalysis saved in cache for position {len(cache_analysis)}.")
		analysis = cache_analysis[fen]
		# If the engine supports UCI_ShowWDL, the score dictionary will have a "wdl" key
		score = analysis[0].get("score")
		if score is None or not hasattr(score, "wdl"):
			return None
		wdl = score.wdl()
		# wdl is a tuple with values in tenths, convert them to percentages
		total = sum(wdl)
		if total == 0:
			return (0, 0, 0)
		return (wdl[0] * 10, wdl[1] * 10, wdl[2] * 10)
	except Exception as e:
		print("Error in CalculateWDL:", e)
		return None
def SetAnalysisTime(new_time):
	"""
	Allows setting the analysis time (in seconds) for the engine.
	"""
	global analysis_time
	try:
		new_time = float(new_time)
		if new_time <= 0:
			print("The analysis time must be positive.")
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
			print("The number of lines must be at least 1.")
		else:
			multipv = new_multipv
			print(f"Multipv set to {multipv}.")
	except Exception as e:
		print("Error in SetMultipv:", e)
def LoadPGNFromClipboard():
	"""
	Loads the PGN from the clipboard and returns it as a pgn_game object.
	"""
	try:
		clipboard_pgn = pyperclip.paste()
		if not clipboard_pgn:
			print("Clipboard empty.")
			return None
		pgn_io = io.StringIO(clipboard_pgn)
		game = chess.pgn.read_game(pgn_io)
		if game is None:
			print("Invalid PGN on clipboard.")
		return game
	except Exception as e:
		print("Error in LoadPGNFromClipboard:", e)
		return None
def InitEngine():
	global ENGINE
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config or not engine_config.get("engine_path"):
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
		print("\nEngine initialized correctly.")
		return True
	except Exception as e:
		print("\nError initializing the engine:", e)
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
	executable = dgt(prompt="Enter the name of the engine executable (e.g. stockfish_15_x64_popcnt.exe): ", kind="s", smin=5, smax=64)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print("The specified file does not exist. Check the path and the executable name.")
		return
	hash_size = dgt(prompt="Enter the hash table size (min: 1, max: 4096 MB): ", kind="i", imin=1, imax=4096)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=f"Enter the number of cores to use (min: 1, max: {max_cores}): ", kind="i", imin=1, imax=max_cores, default=4)
	skill_level = dgt(prompt="Enter the skill level (min: 0, max: 20): ", kind="i", imin=0, imax=20)
	move_overhead = dgt(prompt="Enter the move overhead in milliseconds (min: 0, max: 500): ", kind="i", imin=0, imax=500, default=0)
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
	print("Engine configuration saved in orologic_db.json.")
	InitEngine()
	return
def AnalyzeGame(pgn_game):
	"""
	Game analysis function (PGN).
	At the entrance the header and the total number of moves are shown.
	If the moves are less than 2, the user is invited to return to the menu
	or to load a new PGN from the clipboard.
	"""
	if pgn_game	is None:
		pgn_game	= LoadPGNFromClipboard()
		if pgn_game:
			AnalyzeGame(pgn_game)
		else:
			print("The clipboard does not contain a valid PGN. Returning to the menu.")
		return
	print("\nAnalysis mode.\nGame headers:\n")
	for k, v in pgn_game.headers.items():
		print(f"{k}: {v}")
	move_list = list(pgn_game.mainline_moves())
	total_moves = len(move_list)
	print(f"Total number of moves: {(total_moves+1)//2}")
	if total_moves < 2:
		choice = key("\nInsufficient moves. [M] to return to the menu or [L] to load a new PGN from the clipboard: ").lower()
		if choice == "l":
			new_pgn = LoadPGNFromClipboard()
			if new_pgn:
				AnalyzeGame(new_pgn)
			else:
				print("The clipboard does not contain a valid PGN. Returning to the menu.")
		return
	print(f"Analysis time set to {analysis_time} seconds.\nLines reported by the engine set to {multipv}.")
	print("\nPress '?' for the command list.\n")
	saved = False
	current_filename = pgn_game.headers.get("Filename", None)
	current_node = pgn_game
	extra_prompt=""
	while True:
		# Prompt construction
		if current_node.move:
			move_san = current_node.san()
			fullmove = current_node.parent.board().fullmove_number if current_node.parent else 1
			# If the current node has a parent with more than one variation, we show symbols indicating the presence of branches
			if current_node.parent and len(current_node.parent.variations) > 1:
				siblings = current_node.parent.variations
				idx = siblings.index(current_node)
				# If it is the first branch (I am the first child), I only show the prefix "<"
				if idx == 0:
					prompt = f"\n{extra_prompt} <{fullmove}. {move_san}"
				# If it is the last branch, I only show the suffix ">"
				elif idx == len(siblings) - 1:
					prompt = f"\n{extra_prompt} {fullmove}. {move_san}>"
				# If it is intermediate, I show both the prefix and the suffix
				else:
					prompt = f"\n{extra_prompt} <{fullmove}. {move_san}>"
			else:
				# If there are no variations, use the standard notation
				if current_node.board().turn == chess.WHITE:
					prompt = f"\n{extra_prompt} {fullmove}... {move_san}"
				else:
					prompt = f"\n{extra_prompt} {fullmove}. {move_san}"
		else:
			prompt = f"\n{extra_prompt} Start: "
		cmd = key(prompt)
		if cmd == ".":
			break
		elif cmd == "a":
			node = current_node
			# Go up until the node is the first of its branch
			while node.parent is not None and node == node.parent.variations[0]:
				node = node.parent
			if node.parent is None:
				# We are in the mainline: set the first move of the game
				if node.variations and current_node != node.variations[0]:
					current_node = node.variations[0]
					extra_prompt = ""
				else:
					print("\nAlready at the beginning of the game.")
			else:
				# We are in a variation: go back to the first node of the current branch
				current_node = node
				extra_prompt = ""
		elif cmd == "s":
			if current_node.parent:
				current_node = current_node.parent
				extra_prompt = ""
				if current_node.move:
					print("\n" + DescribeMove(current_node.move, current_node.parent.board() if current_node.parent else pgn_game.board()))
			else:
				print("\nNo previous move.")
		elif cmd == "d":
			if current_node.variations:
				extra_prompt = ""
				current_node = current_node.variations[0]
				if current_node.move:
					print("\n" + DescribeMove(current_node.move, current_node.parent.board() if current_node.parent else pgn_game.board()))
				if current_node.comment:
					print("Comment:", current_node.comment)
			else:
				print("\nThere are no more moves.")
		elif cmd == "f":
			while current_node.variations:
				extra_prompt = ""
				current_node = current_node.variations[0]
			print("You have reached the end of the game.")
		elif cmd == "g":
			if current_node.parent:
				vars = current_node.parent.variations
				index = vars.index(current_node)
				if index > 0:
					extra_prompt	= ""
					current_node = vars[index - 1]
				else:
					print("There are no previous variations.")
			else:
				print("No variation node available.")
		elif cmd == "h":
			if current_node.parent:
				vars = current_node.parent.variations
				index = vars.index(current_node)
				if index < len(vars) - 1:
					extra_prompt	= ""
					current_node = vars[index + 1]
				else:
					print("There are no more variations.")
			else:
				print("No variation node available.")
		elif cmd == "j":
			print("\nGame header:")
			for k, v in pgn_game.headers.items():
				print(f"{k}: {v}")
		elif cmd == "k":
			move_target = dgt(f"\nGo to move n.#: Max({int(total_moves/2)}) ", kind="i", imin=1, imax=int(total_moves/2))*2-1
			current_node = pgn_game
			for i in range(move_target):
				if current_node.variations:
					current_node = current_node.variations[0]
				else:
					break
			extra_prompt = ""
		elif cmd == "l":
			try:
				clipboard_pgn = pyperclip.paste()
				extra_prompt	= ""
				new_game = chess.pgn.read_game(io.StringIO(clipboard_pgn))
				if new_game:
					pgn_game = new_game
					current_node = pgn_game
					print("\nPGN loaded from clipboard.")
				else:
					print("\nThe clipboard does not contain a valid PGN.")
			except Exception as e:
				print("\nError loading from clipboard:", e)
		elif cmd == "z":
			bestline = CalculateBest(current_node.board())
			if bestline:
				current_node.add_variation(bestline)
				saved = True
				print("\nBestline added as a variation.")
			else:
				print("\nUnable to calculate the bestline.")
		elif cmd == "x":
			bestmove = CalculateBest(current_node.board())
			if bestmove:
				san_move = current_node.board().san(bestmove)
				current_node.comment = (current_node.comment or "") + " Bestmove: " + san_move
				saved = True
				print("\nBestmove added to the comment.")
			else:
				print("\nUnable to calculate the bestmove.")
		elif cmd == "c":
			user_comment = dgt("\nEnter the comment: ", kind="s")
			if user_comment:
				current_node.comment = (current_node.comment or "") + " " + user_comment
				saved = True
				print("\nComment added.")
		elif cmd == "v":
			eval_cp = CalculateEvaluation(current_node.board())
			if eval_cp is not None:
				current_node.comment = (current_node.comment or "") + f" Evaluation CP: {eval_cp/100:.2f}"
				saved = True
				print("\nEvaluation added to the comment.")
			else:
				print("\nUnable to calculate the evaluation.")
		elif cmd == "b":
			print("\nCurrent comment:", current_node.comment)
		elif cmd == "n":
			if current_node.comment:
				confirm = key(f"\nDelete: {current_node.comment}? (y/n): ").lower()
				if confirm == "s" or confirm == 'y':
					current_node.comment = ""
					saved = True
					print("Comment deleted.")
			else:
				print("\nNo comment to delete.")
		elif cmd == "q":
			bestmove = CalculateBest(current_node.board(),	bestmove=True)
			if bestmove:
				extra_prompt = f" BM: {current_node.board().san(bestmove)} "
			else:
				print("\nUnable to calculate the bestmove.")
		elif cmd == "w":
			bestline_san = CalculateBest(current_node.board(), bestmove=False, as_san=True)
			if bestline_san:
				print(f"\nBestLine: {bestline_san}")
				bestmove=bestline_san.split()
				if bestmove[0] ==	"Mate":  # Changed "Matto" to "Mate"
					extra_prompt = f" BM:{bestmove[4]} "
				else:
					extra_prompt = f" BM:{bestmove[1]} "
			else:
				print("\nUnable to calculate the bestline.")
		elif cmd == "e":
			print("\nAnalysis lines:\n")
			fen = current_node.board().fen()
			if fen not in cache_analysis:
				cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
				print(f"\nAnalysis saved in cache for position {len(cache_analysis)}.")
			analysis = cache_analysis[fen]
			main_info = analysis[0]
			score = main_info.get("score")
			if score is not None and hasattr(score, "wdl"):
				wdl = score.wdl()
			else:
				wdl = None
			if wdl is None:
				wdl_str = "N/A"
			else:
				wdl_str = f"{wdl[0]/10:.1f}%/{wdl[1]/10:.1f}%/{wdl[2]/10:.1f}%"
			depth = main_info.get("depth")
			seldepth = main_info.get("seldepth")
			nps = main_info.get("nps")
			pv = main_info.get("pv")
			hashfull = main_info.get("hashfull")
			debug_string = main_info.get("string", "N/A")
			tbhits = main_info.get("tbhits")
			time_used = main_info.get("time")
			nodes = main_info.get("nodes")
			if score is not None:
				score_cp = score.white().score(mate_score=10000)
				score_str = f"{score_cp/100:+.2f}"
			else:
				score_str = "N/A"
			print(f"Statistics: time {time_used} s, Hash {hashfull}, TB {tbhits},\nNetwork: {debug_string},"
									f"\nDepth {depth}/{seldepth}, Eval. CP. {score_str}, WDL: {wdl_str},\nNodes {nodes}, NPS {nps}")
			for i, info in enumerate(analysis, start=1):
				pv = info.get("pv", [])
				if not pv:
					print(f"Line {i}: No move found.")
					continue
				temp_board = current_node.board().copy()
				moves_san = []
				for move in pv:
					try:
						san_move = temp_board.san(move)
					except AssertionError as e:
						print(f"\nError converting move {move} to SAN: {e}")
						break
					moves_san.append(san_move)
					temp_board.push(move)
				else:
					moves_str = " ".join(moves_san)
					score_line = info.get("score")
					if score_line is not None and score_line.relative.is_mate():
						mate_moves = abs(score_line.relative.mate())
						moves_str = f"Mate in {mate_moves}, {moves_str}"
					print(f"Line {i}: {moves_str}")
			smart = key("\nDo you want to inspect the lines in smart mode? (y/n): ").lower()
			if smart == "s" or smart == 'y':
				SmartInspection(analysis, current_node.board())
		elif cmd == "r":
			eval_cp = CalculateEvaluation(current_node.board())
			if eval_cp is not None:
				extra_prompt = f" CP: {eval_cp/100:.2f} "
			else:
				print("\nUnable to calculate the evaluation.")
		elif cmd == "t":
			wdl = CalculateWDL(current_node.board())
			if wdl:
				adj_wdl=f"W{wdl[0]/100:.1f}%/D{wdl[1]/100:.1f}%/L{wdl[2]/100:.1f}% "
				extra_prompt=f"{adj_wdl} "
			else:
				print("\nUnable to calculate the WDL percentages.")
		elif cmd == "y":
			white_material, black_material = CalculateMaterial(current_node.board())
			extra_prompt = f"Mtrl: {white_material}/{black_material} "
		elif cmd == "u":
			moves = []
			node = current_node
			while node.parent is not None:
				moves.append(node.move)
				node = node.parent
			moves.reverse()
			starting_fen = pgn_game.headers.get("FEN", chess.STARTING_FEN)
			b = CustomBoard(starting_fen)
			for m in moves:
				b.push(m)
			print("\n" + str(b))
		elif cmd == "i":
			print(f"\nCurrent analysis time: {analysis_time} seconds.\nCached positions: {len(cache_analysis)}")
			new_time = dgt("\nSet the new value or ENTER to keep it: ", kind="i",	imin=1,	imax=300, default=analysis_time)
			if new_time != analysis_time:
				SetAnalysisTime(new_time)
				cache_analysis.clear()
				print("\nAnalysis time updated and cache cleared.")
		elif cmd == "o":
			print(f"\nCurrent number of analysis lines: {multipv},\nCached positions: {len(cache_analysis)}")
			new_lines = dgt("Set the new value or ENTER to keep it: ", kind="i",imin=2,imax=10, default=multipv)
			if new_lines != multipv:
				SetMultipv(new_lines)
				cache_analysis.clear()
				print("\nNumber of analysis lines updated and cache cleared.")
		elif	cmd == "?":
			print("\nCommands available in analysis mode:")
			menu(ANALYSIS_COMMAND,show_only=True)
		else:
			print("Unrecognized command.")
	if saved:
		if "Annotator" not in pgn_game.headers or not pgn_game.headers["Annotator"].strip():
			pgn_game.headers["Annotator"] = f'Orologic V{VERSION} by {PROGRAMMER}'
		new_default_file_name=f'{pgn_game.headers.get("White")}-{pgn_game.headers.get("Black")}-{pgn_game.headers.get("Result", "-")}'
		base_name = dgt(f"New name of the commented file: ENTER to accept {new_default_file_name}", kind="s",default=new_default_file_name)
		new_filename = f"{base_name}-commented-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
		new_filename	= sanitize_filename(new_filename)
		with open(new_filename, "w", encoding="utf-8") as f:
			f.write(str(pgn_game))
		print("Updated PGN saved as " + new_filename)
		saved = False
	else:
		print("No changes were made to the PGN.")
	print("Exiting analysis mode. Returning to the main menu.")
def get_color_adjective(piece_color, gender):
	if gender == "m":
		return "white" if piece_color == chess.WHITE else "black"
	else:
		return "white" if piece_color == chess.WHITE else "black"
def extended_piece_description(piece):
	piece_name = PIECE_NAMES.get(piece.piece_type, "piece").capitalize()
	gender = PIECE_GENDER.get(piece.piece_type, "m")
	color_adj = get_color_adjective(piece.color, gender)
	return f"{piece_name} {color_adj}"
def read_diagonal(game_state, base_column, direction_right):
	"""
	Reads the diagonal starting from the square on rank 1 of the base column.
	The direction_right parameter:
		- True: top-right direction (file +1, rank +1)
		- False: top-left direction (file -1, rank +1)
	"""
	base_column = base_column.lower()
	if base_column not in "abcdefgh":
		print("Invalid base column.")
		return
	file_index = ord(base_column) - ord("a")
	rank_index = 0  # start from rank 1 (index 0)
	report = []
	base_descr = f"{LETTER_FILE_MAP.get(base_column, base_column)} 1"
	while 0 <= file_index < 8 and 0 <= rank_index < 8:
		square = chess.square(file_index, rank_index)
		piece = game_state.board.piece_at(square)
		if piece:
			current_file = chr(ord("a") + file_index)
			descriptive_file = LETTER_FILE_MAP.get(current_file, current_file)
			report.append(f"{descriptive_file} {rank_index+1}: {extended_piece_description(piece)}")
		rank_index += 1
		file_index = file_index + 1 if direction_right else file_index - 1
	dir_str = "top-right" if direction_right else "top-left"
	if report:
		print(f"Diagonal from {base_descr} in direction {dir_str}: " + ", ".join(report))
	else:
		print(f"Diagonal from {base_descr} in direction {dir_str} contains no pieces.")
def read_rank(game_state, rank_number):
	# Gets the set of squares of the rank (rank_number: 1-8)
	try:
		rank_bb = getattr(chess, f"BB_RANK_{rank_number}")
	except AttributeError:
		print("Invalid rank.")
		return
	squares = chess.SquareSet(rank_bb)
	report = []
	for square in squares:
		piece = game_state.board.piece_at(square)
		if piece:
			file_index = chess.square_file(square)
			file_letter = chr(ord("a") + file_index)
			descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
			# Use the helper function for the piece
			report.append(f"{descriptive_file} {rank_number}: {extended_piece_description(piece)}")
	if report:
		print(f"Rank {rank_number}: " + ", ".join(report))
	else:
		print(f"Rank {rank_number} is empty.")
def read_file(game_state, file_letter):
	# file_letter must be a letter from 'a' to 'h'
	file_letter = file_letter.lower()
	if file_letter not in "abcdefgh":
		print("Invalid column.")
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
			report.append(f"{file_letter_descr} {rank}: {extended_piece_description(piece)}")
	if report:
		print(f"Column {LETTER_FILE_MAP.get(file_letter, file_letter)}: " + ", ".join(report))
	else:
		print(f"Column {LETTER_FILE_MAP.get(file_letter, file_letter)} is empty.")
def read_square(game_state, square_str):
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print("Invalid square.")
		return
	# Calculate the color of the square: (file+rank) even -> dark, otherwise light
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = "dark"
	else:
		color_descr = "light"
	piece = game_state.board.piece_at(square)
	if piece:
		base_msg = f"Square {square_str.upper()} is {color_descr} and contains {extended_piece_description(piece)}."
		# Calculate defenders and attackers for the occupied square
		defenders = game_state.board.attackers(piece.color, square)
		attackers = game_state.board.attackers(not piece.color, square)
		info_parts = []
		if defenders:
			count = len(defenders)
			word = "piece" if count == 1 else "pieces"
			info_parts.append(f"defended by {count} {word} { 'white' if piece.color == chess.WHITE else 'black' }")
		if attackers:
			count = len(attackers)
			word = "piece" if count == 1 else "pieces"
			info_parts.append(f"attacked by {count} {word} { 'black' if piece.color == chess.WHITE else 'white' }")
		if info_parts:
			base_msg += " " + " and ".join(info_parts) + "."
		print(base_msg)
	else:
		base_msg = f"Square {square_str.upper()} is {color_descr} and is empty."
		white_attackers = game_state.board.attackers(chess.WHITE, square)
		black_attackers = game_state.board.attackers(chess.BLACK, square)
		info_parts = []
		if white_attackers:
			count = len(white_attackers)
			word = "piece" if count == 1 else "pieces"
			info_parts.append(f"attacked by {count} {word} white")
		if black_attackers:
			count = len(black_attackers)
			word = "piece" if count == 1 else "pieces"
			info_parts.append(f"attacked by {count} {word} black")
		if info_parts:
			base_msg += " " + " and ".join(info_parts) + "."
		print(base_msg)
def report_piece_positions(game_state, piece_symbol):
	try:
		piece = chess.Piece.from_symbol(piece_symbol)
	except Exception as e:
		print("Unrecognized: enter R N B Q K P, r n b q k p")
		return
	color_string = "white" if piece.color == chess.WHITE else "black"
	full_name = PIECE_NAMES.get(piece.piece_type, "piece")
	squares = game_state.board.pieces(piece.piece_type, piece.color)
	positions = []
	for square in squares:
		# Get file and rank
		file_index = chess.square_file(square)
		rank = chess.square_rank(square) + 1
		file_letter = chr(ord("a") + file_index)
		descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
		positions.append(f"{descriptive_file} {rank}")
	if positions:
		print(f"{color_string}: {full_name} in: " + ", ".join(positions))
	else:
		print(f"No {full_name} {color_string} found.")
def report_white_time(game_state):
	initial_white = game_state.clock_config["phases"][game_state.white_phase]["white_time"]
	elapsed_white = initial_white - game_state.white_remaining
	if elapsed_white < 0:
		elapsed_white = 0
	perc_white = (elapsed_white / initial_white * 100) if initial_white > 0 else 0
	print("White time: " + FormatTime(game_state.white_remaining) + f" ({perc_white:.0f}%)")
	return
def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	if elapsed_black < 0:
		elapsed_black = 0
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print("Black time: " + FormatTime(game_state.black_remaining) + f" ({perc_black:.0f}%)")
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
		# If the clock is symmetrical, the white time is used
		if clock_config["same_time"]:
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		else:
			# In case of asymmetrical clocks, a reference is chosen for PGN (here white)
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		# If moves == 0, we consider the phase as "sudden death"
		if moves == 0:
			tc = f"{base_time}"
		else:
			if inc > 0:
				tc = f"{moves}/{base_time}:{inc}"
			else:
				tc = f"{moves}/{base_time}"
		tc_list.append(tc)
	return ", ".join(tc_list)
def seconds_to_mmss(seconds):
	m = int(seconds // 60)
	s = int(seconds % 60)
	return f"{m:02d} minutes and {s:02d} seconds!"
def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print("Invalid time format. Expected mm:ss. Error:", e)
		return 0
def DescribeMove(move, board):
	# Castling management
	if board.is_castling(move):
		if chess.square_file(move.to_square) > chess.square_file(move.from_square):
			return "kingside castling"
		else:
			return "queenside castling"
	# Get the SAN notation of the move
	try:
		san_str = board.san(move)
	except Exception as e:
		san_str = ""
	# Pattern to analyze the SAN move:
	# Groups: 1=piece (optional), 2=disambiguation (0-2 characters), 3='x' (capture), 4=destination, 5=promotion (optional), 6=promotion piece, 7=check or checkmate (optional)
	pattern = re.compile(r'^([RNBQK])?([a-h1-8]{0,2})(x)?([a-h][1-8])(=([RNBQ]))?([+#])?$')
	m = pattern.match(san_str)
	if not m:
		# Fallback in case of failed analysis
		return "Move not analyzable"
	piece_letter = m.group(1)
	disamb = m.group(2)
	capture = m.group(3)
	dest = m.group(4)
	promo_letter = m.group(6)
	check_mark = m.group(7)
	# Determine the name of the moving piece
	if piece_letter:
		mapping = {
			"K": chess.KING,
			"Q": chess.QUEEN,
			"R": chess.ROOK,
			"B": chess.BISHOP,
			"N": chess.KNIGHT
		}
		piece_type = mapping.get(piece_letter.upper(), chess.PAWN)
		piece_name = PIECE_NAMES.get(piece_type, "").lower()
	else:
		piece_name = "pawn"
	# Start composing the description
	descr = ""
	# For the pawn we include the article
	descr += piece_name
	# If there is disambiguation, we add it (translating letters into names if possible)
	if disamb:
		parts = []
		for ch in disamb:
			if ch.isalpha():
				parts.append(LETTER_FILE_MAP.get(ch, ch))
			else:
				parts.append(ch)
		descr += " from " + " ".join(parts)  # Changed "di" to "from"
	# Capture management
	if capture:
		descr += " takes " # Changed
		captured_piece = board.piece_at(move.to_square)
		if not captured_piece and piece_letter=="" and chess.square_file(move.from_square) != chess.square_file(move.to_square):
			captured_sq = move.to_square + (8 if board.turn==chess.BLACK else -8)
			captured_piece = board.piece_at(captured_sq)
		if captured_piece:
			descr += PIECE_NAMES.get(captured_piece.piece_type, "").lower()
	# Destination description
	dest_file = dest[0]
	dest_rank = dest[1]
	dest_name = LETTER_FILE_MAP.get(dest_file, dest_file)
	descr += " to " + dest_name + " " + dest_rank # Changed
	# Promotion
	if promo_letter:
		promo_mapping = {
			"Q": chess.QUEEN,
			"R": chess.ROOK,
			"B": chess.BISHOP,
			"N": chess.KNIGHT
		}
		promo_piece_type = promo_mapping.get(promo_letter.upper(), None)
		promo_piece_name = PIECE_NAMES.get(promo_piece_type, "").lower() if promo_piece_type is not None else ""
		descr += " and promotes to " + promo_piece_name # Changed
	# Check or checkmate
	if check_mark:
		if check_mark=="+":
			descr += " check" # Changed
		elif check_mark=="#":
			descr += " checkmate!" # Changed
	return descr
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
			white_move_desc = f"Error in white move: {e}"
		if i + 1 < len(game_state.move_history):  # If the black move exists
			black_move_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_move_san)
				black_move_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except Exception as e:
				black_move_desc = f"Error in black move: {e}"
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
	elif m and m[0] in "rnkq" and m[0].islower():
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
def LoadEcoDatabase(filename="eco.db"):
	"""
	Loads the ECO file and returns a list of dictionaries,
	each containing "eco", "opening", "variation" and "moves" (list of moves in SAN).
	"""
	eco_entries = []
	if not os.path.exists(filename):
		print("File eco.db not found.")
		return eco_entries
	with open(filename, "r", encoding="utf-8") as f:
		content = f.read()
	# Remove any comment blocks enclosed in { and }
	content = re.sub(r'\{[^}]*\}', '', content)
	# Use StringIO to make the "cleaned" content readable by the PGN parser
	stream = io.StringIO(content)
	while True:
		game = chess.pgn.read_game(stream)
		if game is None:
			break
		eco_code = game.headers.get("ECO", "")
		opening = game.headers.get("Opening", "")
		variation = game.headers.get("Variation", "")
		moves = []
		node = game
		while node.variations:
			next_node = node.variations[0]
			try:
				san = node.board().san(next_node.move)
			except Exception as e:
				san = "?"
			moves.append(san)
			node = next_node
		eco_entries.append({
			"eco": eco_code,
			"opening": opening,
			"variation": variation,
			"moves": moves
		})
	return eco_entries
def DetectOpening(move_history, eco_db):
	"""
	Given the list of played moves (move_history, list of strings in SAN)
	and the ECO database (list of dict), returns the opening entry
	with the longest prefix corresponding to the played moves.
	If no moves match, returns None.
	"""
	best_match = None
	best_match_length = 0
	for entry in eco_db:
		eco_moves = entry["moves"]
		match_length = 0
		# Compare element by element the move_history list and the entry list
		for m1, m2 in zip(move_history, eco_moves):
			if m1 == m2:
				match_length += 1
			else:
				break
		if match_length > best_match_length:
			best_match = entry
			best_match_length = match_length
	return best_match
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
		parts.append(f"{h} {'hour' if h==1 else 'hours'}") # Changed
	if m:
		parts.append(f"{m} {'minute' if m==1 else 'minutes'}") # Changed
	if s:
		parts.append(f"{s} {'second' if s==1 else 'seconds'}") # Changed
	return ", ".join(parts) if parts else "0 seconds" # Changed
def ParseTime(prompt):
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":"))
		return h*3600+m*60+s
	except Exception as e:
		print("Invalid time format. Expected hh:mm:ss. Error:",e)
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
	print("\nClock creation\n") # Changed
	name=dgt("Clock name: ",kind="s") # Changed
	db=LoadDB()
	if any(c["name"]==name for c in db["clocks"]):
		print("A clock with this name already exists.") # Changed
		return
	same=dgt("Do White and Black start with the same time? (Enter for yes, 'n' for no): ",kind="s",smin=0,smax=1) # Changed
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(f"Time (hh:mm:ss) for phase {phase_count+1}: ")
			inc=dgt(f"Increment in seconds for phase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(f"Time for white (hh:mm:ss) phase {phase_count+1}: ")
			inc_w=dgt(f"Increment for white phase {phase_count+1}: ",kind="i")
			total_seconds_b=ParseTime(f"Time for black (hh:mm:ss) phase {phase_count+1}: ")
			inc_b=dgt(f"Increment for black phase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(f"Number of moves for phase {phase_count+1} (0 to finish): ",kind="i") # Changed
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt("Number of alarms to insert (max 5, 0 for none): ",kind="i",imax=5,default=0) # Changed
	for i in range(num_alarms):
		alarm_input = dgt(f"Enter the time (mm:ss) for alarm {i+1}: ", kind="s")
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt("Enter a note for the clock (optional): ",kind="s",default="")# Changed
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	db["clocks"].append(new_clock.to_dict())
	SaveDB(db)
	print("\nClock created and saved.") # Changed
def ViewClocks():
	print("\nClock visualization\n") # Changed
	db=LoadDB()
	if not db["clocks"]:
		print("No clocks saved.") # Changed
		return
	for idx,c in enumerate(db["clocks"]):
		indicatore="W=B" if c["same_time"] else "W/B"  # Changed indicators
		fasi=""
		for i,phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str=SecondsToHMS(phase["white_time"])
				fasi+=f" F{i+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w=SecondsToHMS(phase["white_time"])
				time_str_b=SecondsToHMS(phase["black_time"])
				fasi+=f" F{i+1}: White:{time_str_w}+{phase['white_inc']}, Black:{time_str_b}+{phase['black_inc']}" # Changed
		num_alarms = len(c.get("alarms", []))  # Counts the alarms
		alarms_str = f" Alarms ({num_alarms})"  # Changed
		print(f"{idx+1}. {c['name']} - {indicatore}{fasi}{alarms_str}")
		if c.get("note",""):
			print(f"\tNote: {c['note']}") # Changed
	attesa=key("Press a key to return to the main menu.") # Changed
def SelectClock(db):
	db = LoadDB()
	if not db["clocks"]:
		print("No clocks saved.") # Changed
		return
	else:
		print(f"There are {len(db['clocks'])} clocks in the collection.") # Changed
	choices = {}
	for c in db["clocks"]:
		indicatore = "W=B" if c["same_time"] else "W/B" # Changed
		fasi = ""
		for j, phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str = SecondsToHMS(phase["white_time"])
				fasi += f" F{j+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w = SecondsToHMS(phase["white_time"])
				time_str_b = SecondsToHMS(phase["black_time"])
				fasi += f" F{j+1}: White:{time_str_w}+{phase['white_inc']}, Black:{time_str_b}+{phase['black_inc']}"  # Changed
		num_alarms = len(c.get("alarms", []))
		alarms_str = f" Alarms ({num_alarms})" # Changed
		first_line = f"{indicatore}{fasi}{alarms_str}"
		note_line = c.get("note", "")
		description = first_line + "\n  " + note_line
		choices[c["name"]] = description
	choice = menu(choices, show=True, keyslist=True, full_keyslist=False)
	if choice:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == choice), None)
		if idx is not None:
			return db["clocks"][idx]
	else:
		print("No clock selected.") # Changed
def DeleteClock(db):
	print("\nDeleting saved clocks\n")  # Changed
	orologio = SelectClock(db)
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			del db["clocks"][idx]
			SaveDB(db)
			print(f"\nClock '{clock_name}' deleted, {len(db['clocks'])} remaining.") # Changed
	return
def EditPGN():
	print("\nEdit default info for PGN\n") # Changed
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	default_event = default_pgn.get("Event", "Orologic Game")
	event = dgt(f"Event [{default_event}]: ", kind="s", default=default_event)
	if event.strip() == "":
		event = default_event
	default_site = default_pgn.get("Site", "Unknown Venue") # Changed
	site = dgt(f"Venue [{default_site}]: ", kind="s", default=default_site) # Changed
	if site.strip() == "":
		site = default_site
	default_round = default_pgn.get("Round", "Round 1")
	round_ = dgt(f"Round [{default_round}]: ", kind="s", default=default_round)
	if round_.strip() == "":
		round_ = default_round
	default_white = default_pgn.get("White", "White") # Changed
	white = dgt(f"White player name [{default_white}]: ", kind="s", default=default_white) # Changed
	if white.strip() == "":
		white = default_white
	default_black = default_pgn.get("Black", "Black") # Changed
	black = dgt(f"Black player name [{default_black}]: ", kind="s", default=default_black) # Changed
	if black.strip() == "":
		black = default_black
	default_white_elo = default_pgn.get("WhiteElo", "1200")
	white_elo = dgt(f"White Elo [{default_white_elo}]: ", kind="s", default=default_white_elo)
	if white_elo.strip() == "":
		white_elo = default_white_elo
	default_black_elo = default_pgn.get("BlackElo", "1200")
	black_elo = dgt(f"Black Elo [{default_black_elo}]: ", kind="s", default=default_black_elo)
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
	print("\nDefault information for the PGN updated.") # Changed
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
			if self.turn == chess.BLACK:
				last_move_info = f"{move_number}. {last_move_san}"
			else:
				last_move_info = f"{move_number}... {last_move_san}"
		board_str += f" {last_move_info} Material: {white_material}/{black_material}"
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
		# The initial turn remains "white" (white to move)
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
					print(self.white_player + " enters phase " + str(self.white_phase+1) + " phase time " + FormatTime(self.clock_config["phases"][self.white_phase]["white_time"])) # Changed
					self.white_remaining=self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves+=1
			if self.black_phase<len(self.clock_config["phases"])-1:
				if self.black_moves>=self.clock_config["phases"][self.black_phase]["moves"] and self.clock_config["phases"][self.black_phase]["moves"]!=0:
					self.black_phase+=1
					Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03,0, volume], kind=3, adsr=[20, 10, 75, 20])
					print(self.black_player + " enters phase " + str(self.black_phase+1) + " phase time " + FormatTime(self.clock_config["phases"][self.black_phase]["black_time"]))  # Changed
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
						print(f"Alarm: white time reached {seconds_to_mmss(alarm)}")  # Changed
						Acusticator(["c4",0.2,-0.75,volume])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(f"Alarm: black time reached {seconds_to_mmss(alarm)}")  # Changed
						Acusticator(["c4",0.2,0.75,volume])
						triggered_alarms_black.add(alarm)
		if game_state.white_remaining<=0 or game_state.black_remaining<=0:
			Acusticator(["e4", 0.2, -0.5, volume, "d4", 0.2, 0, volume, "c4", 0.2, 0.5, volume], kind=1, adsr=[10, 0, 90, 10])
			game_state.game_over=True
			print("Flag fallen!")  # Changed
			if game_state.white_remaining <= 0:
				game_state.pgn_game.headers["Result"] = "0-1"  # Black wins
				print(f"White time expired. {game_state.black_player} wins.")  # Changed
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			else:
				game_state.pgn_game.headers["Result"] = "1-0"  # White wins
				print(f"Black time expired. {game_state.white_player} wins.")  # Changed
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
		time.sleep(0.1)
def StartGame(clock_config):
	print("\nStarting game\n")  # Changed
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", "White")  # Changed
	black_default = default_pgn.get("Black", "Black")  # Changed
	white_elo_default = default_pgn.get("WhiteElo", "1500")
	black_elo_default = default_pgn.get("BlackElo", "1500")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", "Unknown Venue")  # Changed
	round_default = default_pgn.get("Round", "Round 1")
	eco_db = LoadEcoDatabase("eco.db")
	last_eco_msg = None
	white_player = dgt(f"White player name [{white_default}]: ", kind="s", default=white_default)  # Changed
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_player.strip() == "":
		white_player = white_default
	black_player = dgt(f"Black player name [{black_default}]: ", kind="s", default=black_default)  # Changed
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_player.strip() == "":
		black_player = black_default
	white_elo = dgt(f"White Elo [{white_elo_default}]: ", kind="s", default=white_elo_default)  # Changed
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_elo.strip() == "":
		white_elo = white_elo_default
	black_elo = dgt(f"Black Elo [{black_elo_default}]: ", kind="s", default=black_elo_default)  # Changed
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_elo.strip() == "":
		black_elo = black_elo_default
	event = dgt(f"Event [{event_default}]: ", kind="s", default=event_default)  # Changed
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if event.strip() == "":
		event = event_default
	site = dgt(f"Venue [{site_default}]: ", kind="s", default=site_default)  # Changed
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	round_ = dgt(f"Round [{round_default}]: ", kind="s", default=round_default) # Changed
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
	key("Press any key to start the game when you are ready...",attesa=1800)  # Changed
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
			prompt="0. "
		elif len(game_state.move_history)%2==1:
			full_move=(len(game_state.move_history)+1)//2
			prompt=f"{full_move}. {game_state.move_history[-1]} "
		else:
			full_move=(len(game_state.move_history))//2
			prompt=f"{full_move}... {game_state.move_history[-1]} "
		if game_state.paused:
			prompt="["+prompt.strip()+"] "
		user_input=dgt(prompt,kind="s")
		if user_input.startswith("/"):
			base_column = user_input[1:2].strip()
			read_diagonal(game_state, base_column, True)
		elif user_input.startswith("\\"):
			base_column = user_input[1:2].strip()
			read_diagonal(game_state, base_column, False)
		elif user_input.startswith("-"):
			param = user_input[1:].strip()
			if len(param) == 1 and param.isalpha():
				read_file(game_state, param)
			elif len(param) == 1 and param.isdigit():
				rank_number = int(param)
				if 1 <= rank_number <= 8:
					read_rank(game_state, rank_number)
				else:
					print("Invalid rank.")  # Changed
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				read_square(game_state, param)
			else:
				print("Unrecognized dash command.")  # Changed
		elif user_input.startswith(","):
			Acusticator(["a3", .06, -1, volume, "c4", .06, -0.5, volume, "d#4", .06, 0.5, volume, "f4", .06, 1, volume], kind=3, adsr=[20, 5, 70, 25])
			report_piece_positions(game_state, user_input[1:2])
		elif user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			if cmd==".?":
				menu(DOT_COMMANDS,show_only=True,p="Available commands:")  # Changed
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
				adv="white" if game_state.white_remaining>game_state.black_remaining else "black"  # Changed
				print(f"{adv} ahead by "+FormatTime(diff))  # Changed
			elif cmd==".5":
				if game_state.paused:
					Acusticator(['d4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					pause_duration = time.time() - paused_time_start if paused_time_start else 0
					hours = int(pause_duration // 3600)
					minutes = int((pause_duration % 3600) // 60)
					seconds = int(pause_duration % 60)
					ms = int((pause_duration - int(pause_duration)) * 1000)
					print(f"Time paused for: {f'{hours:2d} hours, ' if hours else ''}{f'{minutes:2d} minutes, ' if minutes or hours else ''}{f'{seconds:2d} seconds and ' if seconds or minutes or hours else ''}{f'{ms:3d} ms' if ms else ''}")  # Changed
				else:
					Acusticator(['f4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					player = game_state.white_player if game_state.active_color=="white" else game_state.black_player
					print(f"{player}'s clock running")  # Changed
			elif cmd==".m":
				white_material,black_material=CalculateMaterial(game_state.board)
				print(f"Material: {game_state.white_player} {white_material}, {game_state.black_player} {black_material}")  # Changed
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					print("Clocks paused")  # Changed
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
					print("Pause lasted "+FormatTime(pause_duration))  # Changed
			elif cmd==".q":
				if game_state.paused and game_state.move_history:
					game_state.board.pop()
					game_state.pgn_node=game_state.pgn_node.parent
					last_move=game_state.move_history.pop()
					print("Last move undone: "+last_move) # Changed
			elif cmd.startswith(".b+") or cmd.startswith(".b-") or cmd.startswith(".n+") or cmd.startswith(".n-"):
				if game_state.paused:
					try:
						adjust=float(cmd[3:])
						if cmd.startswith(".b+"):
							game_state.white_remaining+=adjust
						elif cmd.startswith(".b-"):
							game_state.white_remaining-=adjust
						elif cmd.startswith(".n+"):
							game_state.black_remaining+=adjust
						elif cmd.startswith(".n-"):
							game_state.black_remaining-=adjust
						print("New white time: "+FormatTime(game_state.white_remaining)+", black: "+FormatTime(game_state.black_remaining))  # Changed
					except:
						print("Invalid command.")  # Changed
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, volume, "g4", 0.2, -0.3, volume, "c5", 0.2, 0.3, volume, "e5", 0.2, 1, volume, "g5", 0.4, 0, volume], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				summary = GenerateMoveSummary(game_state)
				if summary:
					print("\nList of played moves:\n") # Changed
					for line in summary:
						print(line)
				else:
					print("No moves played yet.")  # Changed
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
				print("Result assigned: "+result) # Changed
				game_state.pgn_game.headers["Result"]=result
				game_state.game_over=True
			elif cmd.startswith(".c"):
				new_comment = cmd[2:].strip()
				if game_state.move_history:
					if game_state.pgn_node.comment:
						game_state.pgn_node.comment += "\n" + new_comment
					else:
						game_state.pgn_node.comment = new_comment
					print("Comment recorded for move: " + game_state.move_history[-1]) # Changed
				else:
					print("No move to comment.")  # Changed
			else:
				print("Unrecognized command.")  # Changed
		else:
			if game_state.paused:
				print("You cannot enter new moves while the time is paused. Restart the time with .p")  # Changed
				Acusticator(["b3",.2,0,volume],kind=2)
				continue
			user_input=NormalizeMove(user_input)
			try:
				move = game_state.board.parse_san(user_input)
				board_copy=game_state.board.copy()
				description=DescribeMove(move,board_copy)
				Acusticator([1000.0, 0.01, 0, volume], kind=1, adsr=[0, 0, 100, 0])
				# Print the move preceded by the player's name based on the turn
				if game_state.active_color=="white":
					print(game_state.white_player+": "+description)  # Changed
				else:
					print(game_state.black_player+": "+description)  # Changed
				san_move=game_state.board.san(move)
				game_state.board.push(move)
				game_state.move_history.append(san_move)
				game_state.pgn_node=game_state.pgn_node.add_variation(move)
				if eco_db:
					eco_entry = DetectOpening(game_state.move_history, eco_db)
					if eco_entry:
						new_eco_msg = f"{eco_entry['eco']} - {eco_entry['opening']}"
						if eco_entry['variation']:
							new_eco_msg += f" ({eco_entry['variation']})"
						if new_eco_msg != last_eco_msg:
							print("Opening detected: " + new_eco_msg)  # Changed
							last_eco_msg = new_eco_msg
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "1-0" if game_state.active_color == "white" else "0-1"
					game_state.pgn_game.headers["Result"] = result
					print(f"Checkmate! {game_state.white_player if game_state.active_color == 'white' else game_state.black_player} wins.")  # Changed
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break  # Exit the loop
				elif game_state.board.is_stalemate():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Stalemate!")  # Changed
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_insufficient_material():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by insufficient material!")  # Changed
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_seventyfive_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by the seventy-five move rule!")  # Changed
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_fivefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by fivefold repetition!")  # Changed
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_fifty_moves():  # Check for the *claim* of the 50 moves
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by the fifty-move rule (upon claim)!")  # Changed
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition(): # Check for the *claim* of the threefold repetition.
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Draw by threefold repetition (upon claim)!")  # Changed
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()
			except Exception as e:
				illegal_result=verbose_legal_moves_for_san(game_state.board,user_input)
				print("Illegal move:\n"+illegal_result)  # Changed
	game_state.pgn_game.headers["WhiteClock"] = FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = FormatClock(game_state.black_remaining)
	print("Game over.")  # Changed
	if eco_db:
		eco_entry = DetectOpening(game_state.move_history, eco_db)
		if eco_entry:
			game_state.pgn_game.headers["ECO"] = eco_entry["eco"]
			game_state.pgn_game.headers["Opening"] = eco_entry["opening"]
			if eco_entry["variation"]:
				game_state.pgn_game.headers["Variation"] = eco_entry["variation"]
	pgn_str=str(game_state.pgn_game)
	pgn_str = format_pgn_comments(pgn_str)
	filename = f"{white_player}-{black_player}-{game_state.pgn_game.headers.get('Result', '*')}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
	filename=sanitize_filename(filename)
	with open(filename, "w", encoding="utf-8") as f:
		f.write(pgn_str)
	print("PGN saved as "+filename+".")  # Changed
	analyze_choice = key("Do you want to analyze the game? (y/n): ").lower()  # Changed
	if analyze_choice == "s" or analyze_choice == 'y':
		db = LoadDB()
		engine_config = db.get("engine_config", {})
		if not engine_config or not engine_config.get("engine_path"):
			print("Engine not configured. Returning to the menu.")  # Changed
			return
		else:
			AnalyzeGame(game_state.pgn_game)
def OpenManual():
	print("\nOpening manual\n")  # Changed
	readme="readme_en.htm"  # Changed to English readme
	if os.path.exists(readme):
		webbrowser.open(readme)
	else:
		print("The file readme_en.htm does not exist.")  # Changed
def SchermataIniziale():
	now = datetime.datetime.now()
	diff1 = relativedelta(now, BIRTH_DATE)
	diff2 = relativedelta(now, RELEASE_DATE)
	parts1 = []
	if diff1.years:
		parts1.append(f"{diff1.years} years")  # Changed
	if diff1.months:
		parts1.append(f"{diff1.months} months")  # Changed
	if diff1.days:
		parts1.append(f"{diff1.days} days")  # Changed
	if diff1.hours:
		parts1.append(f"{diff1.hours} hours")  # Changed
	if diff1.minutes:
		parts1.append(f"and {diff1.minutes} minutes")  # Changed
	age_string = ", ".join(parts1)
	parts2 = []
	if diff2.years:
		parts2.append(f"{diff2.years} years")  # Changed
	if diff2.months:
		parts2.append(f"{diff2.months} months")  # Changed
	if diff2.days:
		parts2.append(f"{diff2.days} days")  # Changed
	if diff2.hours:
		parts2.append(f"{diff2.hours} hours")  # Changed
	if diff2.minutes:
		parts2.append(f"{diff2.minutes} minutes")  # Changed
	release_string = ", ".join(parts2)
	print(f"\nHello! Welcome, I am Orologic and I am {age_string} old.")  # Changed
	print(f"The latest version is {VERSION} and was released on {RELEASE_DATE.strftime('%d/%m/%Y %H:%M')}.")  # Changed
	print(f"\tthat is: {release_string} ago.")  # Changed
	print("\t\tAuthor: "+PROGRAMMER)  # Changed
	print("\t\t\tType '?' to display the menu.")  # Changed
	Acusticator(['c4', 0.125, 0, volume, 'd4', 0.125, 0, volume, 'e4', 0.125, 0, volume, 'g4', 0.125, 0, volume, 'a4', 0.125, 0, volume, 'e5', 0.125, 0, volume, 'p', 0.125, 0, 0.5, 'a5', 0.125, 0, volume], kind=1, adsr=[0.01, 0, 100, 99])
def Main():
	global	volume
	db = LoadDB()
	volume = db.get("volume", 0.5)
	SchermataIniziale()
	InitEngine()
	while True:
		scelta=menu(MENU_CHOICES, show=True, keyslist=True, full_keyslist=False)
		if scelta == "analizza":
			Acusticator(["a5", .04, 0, volume, "e5", .04, 0, volume, "p",.08,0,0, "g5", .04, 0, volume, "e6", .120, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			AnalyzeGame(None)
		elif scelta=="crea":
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			CreateClock()
		elif scelta=="comandi":  # This option is not in the English menu
			Acusticator([500.0, 0.4, -1, volume, 800.0, 0.4, 1, volume], kind=3, adsr=[20, 10, 50, 20])
			menu(DOT_COMMANDS,show_only=True)
		elif scelta=="motore":
			Acusticator(["e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume])
			EditEngineConfig()
		elif scelta=="volume":
			Acusticator(["f6",.02,0,volume,"p",.04,0,volume,"a6",.02,0,volume])
			volume = dgt(f"\nCurrent volume: {int(volume*100)}, new? (0-100): ", kind="i", imin=0, imax=100, default=50)  # Changed
			volume/=100
			db = LoadDB()
			db["volume"] = volume
			SaveDB(db)
			Acusticator(["c5",1,0,volume])
		elif scelta=="vedi":
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			ViewClocks()
		elif scelta=="elimina":
			DeleteClock(db)
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="pgn":
			EditPGN()
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="manuale":
			OpenManual()
		elif scelta=="gioca":
			Acusticator(["c5", 0.1, 0, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0, volume, "c6", 0.3, 0, volume, "g5", 0.1, 0, volume, "e5", 0.1, 0, volume, "c5", 0.1, 0, volume], kind=1, adsr=[5, 5, 90, 10])
			print("\nStarting game\n")  # Changed
			db=LoadDB()
			if not db["clocks"]:
				print("No clocks available. Create one first.")  # Changed
			else:
				clock_config=SelectClock(db)
				if clock_config is not None:
					StartGame(clock_config)
				else:
					print("Invalid choice.")  # Changed
		elif scelta==".":
			Acusticator(["g4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "a4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "p", 0.15, 0, 0, "b4", 0.15, -0.5, volume, "c5", 0.3, 0.5, volume], kind=1, adsr=[5, 0, 100, 5])
			if ENGINE is not None:
				ENGINE.quit()
				print("\nConnection with the UCI engine closed")  # Changed
			break
if __name__=="__main__":
	time_start = datetime.datetime.now()
	board=CustomBoard()
	Main()
	time_end = datetime.datetime.now()
	delta = relativedelta(time_end, time_start)
	components = []
	if delta.days:
		components.append(f"{delta.days} days")  # Changed
	if delta.hours:
		components.append(f"{delta.hours} hours")  # Changed
	if delta.minutes:
		components.append(f"{delta.minutes} minutes")  # Changed
	if delta.seconds:
		components.append(f"{delta.seconds} seconds")  # Changed
	ms = delta.microseconds // 1000
	if ms:
		components.append(f"{ms} milliseconds")  # Changed
	result = ", ".join(components) if components else "0 milliseconds"  # Changed
	print(f"Goodbye from Orologic {VERSION}.\nWe had fun together for: {result}")  # Changed
	sys.exit(0)