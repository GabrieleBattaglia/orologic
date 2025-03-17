# Data di concepimento: 14/02/2025 by Gabriele Battaglia e ChatGPT o3-mini-high
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re, pyperclip, io, chess.engine
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator, key
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="3.10.1"
RELEASE_DATE=datetime.datetime(2025,3,17,8,20)
PROGRAMMER="Gabriele Battaglia & ChatGPT o3-mini-high"
DB_FILE="orologic_db.json"
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
SMART_COMMANDS = {
	"s": "Vai alla mossa precedente",
	"d": "Vai alla mossa successiva",
	"r": "Aggiorna valutazione CP",
	"?": "Visualizza questa lista di comandi",
	".": "Esci dalla modalità smart"
}
ANALYSIS_COMMAND = {
	"a": "Vai all'inizio o nodo padre (se in variante)",
	"s": "Indietro di 1 mossa",
	"d": "Avanti di 1 mossa e visualizza eventuale commento",
	"f": "Vai alla fine o nodo del prossimo ramo variante",
	"g": "Seleziona nodo variante precedente",
	"h": "Seleziona nodo variante successivo",
	"j": "Legge gli headers della partita",
	"k": "Vai a mossa",
	"l": "Carica il PGN	dagli appunti",
	"z": "Inserisce la bestline come variante nel PGN",
	"x": "Inserisce la bestmove nel PGN",
	"c": "Richiede un commento all'utente e lo aggiunge",
	"v": "Inserisce la valutazione in centipawn nel PGN",
	"b": "Visualizza nuovamente il commento",
	"n": "Elimina il commento (o consente di sceglierlo se ce ne sono più di uno)",
	"q": "Calcola e aggiungi la bestmove al prompt",
	"w": "Calcola e visualizza la bestline, aggiungendo anche la bestmove al prompt",
	"e": "Visualizza le linee di analisi e ne permette l'ispezione smart",
	"r": "Calcola e aggiungi la valutazione al prompt",
	"t": "Visualizza le percentuali Win Draw Lost nella posizione corrente",
	"y": "Aggiungi il bilancio materiale al prompt",
	"u": "Visualizza la scacchiera",
	"i": "Imposta i secondi di analisi per il motore",
	"o": "Imposta il numero di linee di analisi da visualizzare",
	"?": "Mostra questa lista di comandi",
	".": "Esci dalla modalità analisi e salva il PGN se diverso dall'originale"
}
DOT_COMMANDS={
	".1":"Mostra il tempo rimanente del bianco",
	".2":"Mostra il tempo rimanente del nero",
	".3":"Mostra entrambe gli orologi",
	".4":"Confronta i tempi rimanenti e indica il vantaggio",
	".5":"Riporta quale orologio è in moto o la durata della pausa, se attiva",
	".l":"Visualizza la lista mosse giocate",
	".m":"Mostra il valore del materiale ancora in gioco",
	".p":"Pausa/riavvia il countdown degli orologi",
	".q":"Annulla l'ultima mossa (solo in pausa)",
	".b+":"Aggiunge tempo al bianco (in pausa)",
	".b-":"Sottrae tempo al bianco (in pausa)",
	".n+":"Aggiunge tempo al nero (in pausa)",
	".n-":"Sottrae tempo al nero (in pausa)",
	".s":"Visualizza la scacchiera",
	".c":"Aggiunge un commento alla mossa corrente",
	".1-0":"Assegna vittoria al bianco (1-0) e conclude la partita",
	".0-1":"Assegna vittoria al nero (0-1) e conclude la partita",
	".1/2":"Assegna patta (1/2-1/2) e conclude la partita",
	".*":"Assegna risultato non definito (*) e conclude la partita",
	".?":"Visualizza l'elenco dei comandi disponibili",
	"/[colonna]":"Mostra la diagonale alto-destra partendo dalla base della colonna data",
	"\\[colonna]":"Mostra la diagonale alto-sinistra partendo dalla base della colonna data",
	"-[colonna|traversa|casa]":"Mostra le figure su quella colonna o traversa o casa",
	",[NomePezzo]":"Mostra la/le posizione/i del pezzo indicato"}
MENU_CHOICES={
	"analizza":"Entra in modalità analisi partita",
	"crea":"... un nuovo orologio da aggiungere alla collezione",
	"elimina":"... uno degli orologi salvati",
	"gioca":"Inizia la partita",
	"manuale":"Mostra la guida dell'app",
	"motore":"Configura le impostazioni per il motore di scacchi",
	"pgn":"Imposta le info di default per il PGN",
	"vedi":"... gli orologi salvati",
	"volume":"Consente la regolazione del volume degli effetti audio",
	".":"Esci dall'applicazione"}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}
LETTER_FILE_MAP={chr(ord("a")+i):FILE_NAMES.get(i,chr(ord("a")+i)) for i in range(8)}
PIECE_NAMES={chess.PAWN:"pedone",chess.KNIGHT:"cavallo",chess.BISHOP:"alfiere",chess.ROOK:"torre",chess.QUEEN:"donna",chess.KING:"Re"}
PIECE_GENDER = {
	chess.PAWN: "m",    # pedone
	chess.KNIGHT: "m",  # cavallo
	chess.BISHOP: "m",  # alfiere
	chess.ROOK: "f",    # torre
	chess.QUEEN: "f",   # donna
	chess.KING: "m"     # re
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
			return "Destinazione non riconosciuta."
		legal_moves=[]
		for move in board.legal_moves:
			if move.to_square==dest_square:
				if promotion is not None:
					if move.promotion==promotion:
						legal_moves.append(move)
				else:
					legal_moves.append(move)
	if not legal_moves:
		return "Nessuna mossa legale trovata per la destinazione indicata."
	result_lines=[]
	i=1
	for move in legal_moves:
		verbose_desc=DescribeMove(move,board.copy())
		result_lines.append(f"{i}°: {verbose_desc}")
		i+=1
	return "\nEcco le mosse possibili\n:".join(result_lines)
def FormatClock(seconds):
	total = int(seconds)
	hours = total // 3600
	minutes = (total % 3600) // 60
	secs = total % 60
	return f"{hours:02d}:{minutes:02d}:{secs:02d}"
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
	print("Linee disponibili:")
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
		print(f"Linea {i}: {line_summary}")
	choice = dgt(f"Quale linea vuoi ispezionare? (1/{len(analysis_lines)} ", kind="i", imin=1, imax=len(analysis_lines),	default=1)
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves:
		print("Linea vuota, termine ispezione.")
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
	print("\nUtilizza questi comandi:")
	menu(p=SMART_COMMANDS,show_only=True)
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]:
			temp_board.push(move)
		current_move = pv_moves[current_index-1]
		# Ottieni la descrizione verbosa della mossa corrente, dal punto di vista della board prima di eseguirla
		move_verbose = DescribeMove(current_move, temp_board)
		smart_prompt=f"\nLinea {line_index+1}: ({current_index}/{total_moves}), CP: {eval_str}, {temp_board.fullmove_number}... {move_verbose}"
		cmd = key(smart_prompt).lower()
		if cmd == ".":
			break
		elif cmd == "s":
			if current_index > 1:
				current_index -= 1
			else:
				print("\nNon ci sono mosse precedenti.")
		elif cmd == "?":
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			# Aggiorna la valutazione ricostruendo la board fino alla mossa corrente
			temp_board = board.copy()
			for move in pv_moves[:current_index]:
				temp_board.push(move)
			new_eval = CalculateEvaluation(temp_board)
			if new_eval is not None:
				if isinstance(new_eval, int):
					eval_str = f"{new_eval/100:.2f}"
				else:
					eval_str = str(new_eval)
				print("\nValutazione aggiornata.")
			else:
				print("\nImpossibile aggiornare la valutazione.")
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				print("\nNon ci sono mosse successive.")
		else:
			print("\nComando non riconosciuto.")
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
			# Itera sulla lista delle mosse della PV, raggruppandole in coppie (mossa bianca e, se presente, mossa nera)
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
					# Caso in cui la PV inizi con una mossa del Nero (poco comune)
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
				moves_str = f"Matto in {mate_moves}, {moves_str}"
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
		print("Errore in CalculateBestLine:", e)
		return None
def CalculateEvaluation(board):
	"""
	Calcola e restituisce la valutazione in centipawn per la board data.
	Se la valutazione è mate, restituisce un valore speciale.
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
		# Se l'engine rileva una situazione di matto...
		if score.is_mate():
			# Se la board è in checkmate, possiamo usare board.outcome()
			if board.is_checkmate():
				outcome = board.outcome()
				if outcome is not None:
					# outcome.winner è True per il bianco, False per il nero
					return 10000 if outcome.winner == chess.WHITE else -10000
			# In altri casi (es. mate in corso di analisi) usiamo score.white()
			return 10000 if score.white().mate() > 0 else -10000
		else:
			return score.white().score()
	except Exception as e:
		print("Errore in CalculateEvaluation:", e)
		return None
def CalculateWDL(board):
	"""
	Calcola e restituisce le percentuali WDL (win/draw/loss) fornite dal motore.
	Restituisce una tupla (win, draw, loss) in percentuali.
	"""
	global ENGINE, analysis_time, multipv
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=multipv)
			print(f"\nAnalisi salvata in cache per la posizione {len(cache_analysis)}.")
		analysis = cache_analysis[fen]
		# Se il motore supporta UCI_ShowWDL, il dizionario score avrà una chiave "wdl"
		score = analysis[0].get("score")
		if score is None or not hasattr(score, "wdl"):
			return None
		wdl = score.wdl()
		# wdl è una tupla con valori in decimi, convertili in percentuali
		total = sum(wdl)
		if total == 0:
			return (0, 0, 0)
		return (wdl[0] * 10, wdl[1] * 10, wdl[2] * 10)
	except Exception as e:
		print("Errore in CalculateWDL:", e)
		return None
def SetAnalysisTime(new_time):
	"""
	Permette di impostare il tempo di analisi (in secondi) per il motore.
	"""
	global analysis_time
	try:
		new_time = float(new_time)
		if new_time <= 0:
			print("Il tempo di analisi deve essere positivo.")
		else:
			analysis_time = new_time
			print(f"Tempo di analisi impostato a {analysis_time} secondi.")
	except Exception as e:
		print("Errore in SetAnalysisTime:", e)
def SetMultipv(new_multipv):
	"""
	Permette di impostare il numero di linee (multipv) da visualizzare.
	"""
	global multipv
	try:
		new_multipv = int(new_multipv)
		if new_multipv < 1:
			print("Il numero di linee deve essere almeno 1.")
		else:
			multipv = new_multipv
			print(f"Multipv impostato a {multipv}.")
	except Exception as e:
		print("Errore in SetMultipv:", e)
def LoadPGNFromClipboard():
	"""
	Carica il PGN dagli appunti e lo restituisce come oggetto pgn_game.
	Se gli appunti contengono più di una partita, viene presentato un menù numerato e
	viene chiesto all'utente di scegliere la partita da caricare.
	"""
	try:
		clipboard_pgn = pyperclip.paste()
		if not clipboard_pgn.strip():
			print("Appunti vuoti.")
			return None
		pgn_io = io.StringIO(clipboard_pgn)
		games = []
		while True:
			game = chess.pgn.read_game(pgn_io)
			if game is None:
				break
			games.append(game)
		if len(games) == 0:
			print("PGN non valido negli appunti.")
			return None
		elif len(games) == 1:
			return games[0]
		else:
			print(f"\nSono state trovate {len(games)} partite nei PGN.")
			partite={}
			for i, game in enumerate(games, start=1):
				white = game.headers.get("White", "Sconosciuto")
				black = game.headers.get("Black", "Sconosciuto")
				date = game.headers.get("Date", "Data sconosciuta")
				partite[i]=f"{white} vs {black} - {date}"
			while True:
				choice = menu(d=partite,	prompt="Quale partita vuoi caricare? ",	show=True,ntf="Numero non valido. Riprova.")
				try:
					index = int(choice)
					if 1 <= index <= len(games):
						return games[index - 1]
					else:
						print("Numero non valido. Riprova.")
				except ValueError:
					print("Input non valido. Inserisci un numero.")
	except Exception as e:
		print("Errore in LoadPGNFromClipboard:", e)
		return None
def InitEngine():
	global ENGINE
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config or not engine_config.get("engine_path"):
		print("\nMotore non configurato. Usa il comando 'motore' per impostarlo.")
		return False
	try:
		ENGINE = chess.engine.SimpleEngine.popen_uci(engine_config["engine_path"])
		ENGINE.configure({
			"Hash": engine_config.get("hash_size", 128),
			"Threads": engine_config.get("num_cores", 1),
			"Skill Level": engine_config.get("skill_level", 20),
			"Move Overhead": engine_config.get("move_overhead", 0)
		})
		print("\nMotore inizializzato correttamente.")
		return True
	except Exception as e:
		print("\nErrore nell'inizializzazione del motore:", e)
		return False
def EditEngineConfig():
	print("\nImposta configurazione del motore scacchistico\n")
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if engine_config:
		print("Configurazione attuale del motore:")
		for key, val in engine_config.items():
			print(f"  {key}: {val}")
	else:
		print("Nessuna configurazione trovata.")
	path = dgt(prompt="Inserisci il percorso dove è salvato il motore UCI: ", kind="s", smin=3, smax=256)
	executable = dgt(prompt="Inserisci il nome dell'eseguibile del motore (es. stockfish_15_x64_popcnt.exe): ", kind="s", smin=5, smax=64)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print("Il file specificato non esiste. Verifica il percorso e il nome dell'eseguibile.")
		return
	hash_size = dgt(prompt="Inserisci la dimensione della hash table (min: 1, max: 4096 MB): ", kind="i", imin=1, imax=4096)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=f"Inserisci il numero di core da utilizzare (min: 1, max: {max_cores}): ", kind="i", imin=1, imax=max_cores, default=4)
	skill_level = dgt(prompt="Inserisci il livello di skill (min: 0, max: 20): ", kind="i", imin=0, imax=20)
	move_overhead = dgt(prompt="Inserisci il move overhead in millisecondi (min: 0, max: 500): ", kind="i", imin=0, imax=500, default=0)
	wdl_switch = True  # Puoi eventualmente renderlo configurabile
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
	print("Configurazione del motore salvata in orologic_db.json.")
	InitEngine()
	return
def AnalyzeGame(pgn_game):
	"""
	Funzione di analisi della partita (PGN).
	All'entrata viene mostrato l'header e il numero totale di mosse.
	Se le mosse sono inferiori a 2, si invita l'utente a tornare al menù
	oppure a caricare un nuovo PGN dagli appunti.
	"""
	if pgn_game	is None:
		pgn_game	= LoadPGNFromClipboard()
		if pgn_game:
			AnalyzeGame(pgn_game)
		else:
			print("Gli appunti non contengono un PGN valido. Ritorno al menù.")
		return
	print("\nModalità analisi.\nHeaders della partita:\n")
	for k, v in pgn_game.headers.items():
		print(f"{k}: {v}")
	move_list = list(pgn_game.mainline_moves())
	total_moves = len(move_list)
	print(f"Numero totale di mosse: {(total_moves+1)//2}")
	if total_moves < 2:
		choice = key("\nMosse insufficienti. [M] per tornare al menù o [L] per caricare un nuovo PGN dagli appunti: ").lower()
		if choice == "l":
			new_pgn = LoadPGNFromClipboard()
			if new_pgn:
				AnalyzeGame(new_pgn)
			else:
				print("Gli appunti non contengono un PGN valido. Ritorno al menù.")
		return
	print(f"Tempo analisi impostato a {analysis_time} secondi.\nLinee riportate dal motore impostate a {multipv}.")
	print("\nPremi '?' per la lista dei comandi.\n")
	saved = False
	current_filename = pgn_game.headers.get("Filename", None)
	current_node = pgn_game
	extra_prompt=""
	while True:
		# Costruzione del prompt
		if current_node.move:
			move_san = current_node.san()
			fullmove = current_node.parent.board().fullmove_number if current_node.parent else 1
			# Se il nodo corrente ha un padre con più di una variazione, mostriamo simboli indicanti la presenza di rami
			if current_node.parent and len(current_node.parent.variations) > 1:
				siblings = current_node.parent.variations
				idx = siblings.index(current_node)
				# Se è il primo ramo (sono il primo figlio), mostro solo il prefisso "<"
				if idx == 0:
					prompt = f"\n{extra_prompt} <{fullmove}. {move_san}"
				# Se è l'ultimo ramo, mostro solo il suffisso ">"
				elif idx == len(siblings) - 1:
					prompt = f"\n{extra_prompt} {fullmove}. {move_san}>"
				# Se è intermedio, mostro sia il prefisso che il suffisso
				else:
					prompt = f"\n{extra_prompt} <{fullmove}. {move_san}>"
			else:
				# Se non ci sono varianti, usa la notazione standard
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
			# Risale finché il nodo è il primo della sua branca
			while node.parent is not None and node == node.parent.variations[0]:
				node = node.parent
			if node.parent is None:
				# Siamo nella mainline: imposta la prima mossa della partita
				if node.variations and current_node != node.variations[0]:
					current_node = node.variations[0]
					extra_prompt = ""
				else:
					print("\nGià all'inizio della partita.")
			else:
				# Siamo in una variante: torna al primo nodo del ramo corrente
				current_node = node
				extra_prompt = ""
		elif cmd == "s":
			if current_node.parent:
				current_node = current_node.parent
				extra_prompt = ""
				if current_node.move:
					print("\n" + DescribeMove(current_node.move, current_node.parent.board() if current_node.parent else pgn_game.board()))
			else:
				print("\nNessuna mossa precedente.")
		elif cmd == "d":
			if current_node.variations:
				extra_prompt = ""
				current_node = current_node.variations[0]
				if current_node.move:
					print("\n" + DescribeMove(current_node.move, current_node.parent.board() if current_node.parent else pgn_game.board()))
				if current_node.comment:
					print("Commento:", current_node.comment)
			else:
				print("\nNon ci sono mosse successive.")
		elif cmd == "f":
			while current_node.variations:
				extra_prompt = ""
				current_node = current_node.variations[0]
			print("Sei arrivato alla fine della partita.")
		elif cmd == "g":
			if current_node.parent:
				vars = current_node.parent.variations
				index = vars.index(current_node)
				if index > 0:
					extra_prompt	= ""
					current_node = vars[index - 1]
				else:
					print("Non ci sono varianti precedenti.")
			else:
				print("Nessun nodo variante disponibile.")
		elif cmd == "h":
			if current_node.parent:
				vars = current_node.parent.variations
				index = vars.index(current_node)
				if index < len(vars) - 1:
					extra_prompt	= ""
					current_node = vars[index + 1]
				else:
					print("Non ci sono varianti successive.")
			else:
				print("Nessun nodo variante disponibile.")
		elif cmd == "j":
			print("\nHeader della partita:")
			for k, v in pgn_game.headers.items():
				print(f"{k}: {v}")
		elif cmd == "k":
			move_target = dgt(f"\nVai a mossa n.#: Max({int(total_moves/2)}) ", kind="i", imin=1, imax=int(total_moves/2))*2-1
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
					print("\nPGN caricato dagli appunti.")
				else:
					print("\nGli appunti non contengono un PGN valido.")
			except Exception as e:
				print("\nErrore nel caricamento dagli appunti:", e)
		elif cmd == "z":
			bestline = CalculateBest(current_node.board())
			if bestline:
				current_node.add_variation(bestline)
				saved = True
				print("\nBestline aggiunta come variante.")
			else:
				print("\nImpossibile calcolare la bestline.")
		elif cmd == "x":
			bestmove = CalculateBest(current_node.board())
			if bestmove:
				san_move = current_node.board().san(bestmove)
				current_node.comment = (current_node.comment or "") + " Bestmove: " + san_move
				saved = True
				print("\nBestmove aggiunta al commento.")
			else:
				print("\nImpossibile calcolare la bestmove.")
		elif cmd == "c":
			user_comment = dgt("\nInserisci il commento: ", kind="s")
			if user_comment:
				current_node.comment = (current_node.comment or "") + " " + user_comment
				saved = True
				print("\nCommento aggiunto.")
		elif cmd == "v":
			eval_cp = CalculateEvaluation(current_node.board())
			if eval_cp is not None:
				current_node.comment = (current_node.comment or "") + f" Valutazione CP: {eval_cp/100:.2f}"
				saved = True
				print("\nValutazione aggiunta al commento.")
			else:
				print("\nImpossibile calcolare la valutazione.")
		elif cmd == "b":
			print("\nCommento corrente:", current_node.comment)
		elif cmd == "n":
			if current_node.comment:
				confirm = key(f"\nEliminare: {current_node.comment}? (s/n): ").lower()
				if confirm == "s":
					current_node.comment = ""
					saved = True
					print("Commento eliminato.")
			else:
				print("\nNessun commento da eliminare.")
		elif cmd == "q":
			bestmove = CalculateBest(current_node.board(),	bestmove=True)
			if bestmove:
				extra_prompt = f" BM: {current_node.board().san(bestmove)} "
			else:
				print("\nImpossibile calcolare la bestmove.")
		elif cmd == "w":
			bestline_san = CalculateBest(current_node.board(), bestmove=False, as_san=True)
			if bestline_san:
				print(f"\nBestLine: {bestline_san}")
				bestmove=bestline_san.split()
				if bestmove[0] ==	"Matto":
					extra_prompt = f" BM:{bestmove[4]} "
				else:
					extra_prompt = f" BM:{bestmove[1]} "
			else:
				print("\nImpossibile calcolare la bestline.")
		elif cmd == "e":
			print("\nLinee di analisi:\n")
			fen = current_node.board().fen()
			if fen not in cache_analysis:
				cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
				print(f"\nAnalisi salvata in cache per la posizione {len(cache_analysis)}.")
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
			print(f"Statistiche: tempo {time_used} s, Hash {hashfull}, TB {tbhits},\nRete: {debug_string},"
									f"\nProfondità {depth}/{seldepth}, val. CP. {score_str}, WDL: {wdl_str},\nnodi {nodes}, NPS {nps}")
			for i, info in enumerate(analysis, start=1):
				pv = info.get("pv", [])
				if not pv:
					print(f"Linea {i}: Nessuna mossa trovata.")
					continue
				temp_board = current_node.board().copy()
				moves_san = []
				for move in pv:
					try:
						san_move = temp_board.san(move)
					except AssertionError as e:
						print(f"\nErrore nella conversione della mossa {move} in SAN: {e}")
						break
					moves_san.append(san_move)
					temp_board.push(move)
				else:
					moves_str = " ".join(moves_san)
					score_line = info.get("score")
					if score_line is not None and score_line.relative.is_mate():
						mate_moves = abs(score_line.relative.mate())
						moves_str = f"Matto in {mate_moves}, {moves_str}"
					print(f"Linea {i}: {moves_str}")
			smart = key("\nVuoi ispezionare le linee in modalità smart? (s/n): ").lower()
			if smart == "s":
				SmartInspection(analysis, current_node.board())
		elif cmd == "r":
			eval_cp = CalculateEvaluation(current_node.board())
			if eval_cp is not None:
				extra_prompt = f" CP: {eval_cp/100:.2f} "
			else:
				print("\nImpossibile calcolare la valutazione.")
		elif cmd == "t":
			wdl = CalculateWDL(current_node.board())
			if wdl:
				adj_wdl=f"W{wdl[0]/100:.1f}%/D{wdl[1]/100:.1f}%/L{wdl[2]/100:.1f}% " 
				extra_prompt=f"{adj_wdl} "
			else:
				print("\nImpossibile calcolare le percentuali WDL.")
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
			print(f"\nTempo di analisi attuale: {analysis_time} secondi.\nPosizioni salvate in cache: {len(cache_analysis)}")
			new_time = dgt("\nImposta il nuovo valore o INVIO per mantenerlo: ", kind="i",	imin=1,	imax=300, default=analysis_time)
			if new_time != analysis_time:
				SetAnalysisTime(new_time)
				cache_analysis.clear()
				print("\nTempo di analisi aggiornato e	cache svuotata.")
		elif cmd == "o":
			print(f"\nNumero di linee di analisi attuale: {multipv},\nPosizioni salvate in cache: {len(cache_analysis)}")
			new_lines = dgt("Imposta il nuovo valore o INVIO per mantenerlo: ", kind="i",imin=2,imax=10, default=multipv)
			if new_lines != multipv:
				SetMultipv(new_lines)
				cache_analysis.clear()
				print("\nNumero di linee di analisi aggiornato e cache svuotata.")
		elif	cmd == "?":
			print("\nComandi disponibili in modalità analisi:")
			menu(ANALYSIS_COMMAND,show_only=True)
		else:
			print("Comando non riconosciuto.")
	if saved:
		if "Annotator" not in pgn_game.headers or not pgn_game.headers["Annotator"].strip():
			pgn_game.headers["Annotator"] = f'Orologic V{VERSION} by {PROGRAMMER}'
		new_default_file_name=f'{pgn_game.headers.get("White")}-{pgn_game.headers.get("Black")}-{pgn_game.headers.get("Result", "-")}'
		base_name = dgt(f"Nuovo nome del file commentato: INVIO per accettare {new_default_file_name}", kind="s",default=new_default_file_name)
		new_filename = f"{base_name}-commentato-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
		new_filename	= sanitize_filename(new_filename)
		with open(new_filename, "w", encoding="utf-8") as f:
			f.write(str(pgn_game))
		print("PGN aggiornato salvato come " + new_filename)
		saved = False
	else:
		print("Non sono state apportate modifiche al PGN.")
	print("Uscita dalla modalità analisi. Ritorno al menù principale.")
def get_color_adjective(piece_color, gender):
	if gender == "m":
		return "bianco" if piece_color == chess.WHITE else "nero"
	else:
		return "bianca" if piece_color == chess.WHITE else "nera"
def extended_piece_description(piece):
	piece_name = PIECE_NAMES.get(piece.piece_type, "pezzo").capitalize()
	gender = PIECE_GENDER.get(piece.piece_type, "m")
	color_adj = get_color_adjective(piece.color, gender)
	return f"{piece_name} {color_adj}"
def read_diagonal(game_state, base_column, direction_right):
	"""
	Legge la diagonale a partire dalla casa sulla traversa 1 della colonna base.
	Il parametro direction_right:
		- True: direzione alto-destra (file +1, traversa +1)
		- False: direzione alto-sinistra (file -1, traversa +1)
	"""
	base_column = base_column.lower()
	if base_column not in "abcdefgh":
		print("Colonna base non valida.")
		return
	file_index = ord(base_column) - ord("a")
	rank_index = 0  # partiamo da traversa 1 (indice 0)
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
	dir_str = "alto-destra" if direction_right else "alto-sinistra"
	if report:
		print(f"Diagonale da {base_descr} in direzione {dir_str}: " + ", ".join(report))
	else:
		print(f"Diagonale da {base_descr} in direzione {dir_str} non contiene pezzi.")
def read_rank(game_state, rank_number):
	# Ottiene l'insieme delle case della traversa (rank_number: 1-8)
	try:
		rank_bb = getattr(chess, f"BB_RANK_{rank_number}")
	except AttributeError:
		print("Traversa non valida.")
		return
	squares = chess.SquareSet(rank_bb)
	report = []
	for square in squares:
		piece = game_state.board.piece_at(square)
		if piece:
			file_index = chess.square_file(square)
			file_letter = chr(ord("a") + file_index)
			descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
			# Usa la funzione helper per il pezzo
			report.append(f"{descriptive_file} {rank_number}: {extended_piece_description(piece)}")
	if report:
		print(f"Traversa {rank_number}: " + ", ".join(report))
	else:
		print(f"La traversa {rank_number} è vuota.")
def read_file(game_state, file_letter):
	# file_letter deve essere una lettera da 'a' ad 'h'
	file_letter = file_letter.lower()
	if file_letter not in "abcdefgh":
		print("Colonna non valida.")
		return
	try:
		file_bb = getattr(chess, f"BB_FILE_{file_letter.upper()}")
	except AttributeError:
		print("Colonna non valida.")
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
		print(f"Colonna {LETTER_FILE_MAP.get(file_letter, file_letter)}: " + ", ".join(report))
	else:
		print(f"La colonna {LETTER_FILE_MAP.get(file_letter, file_letter)} è vuota.")
def read_square(game_state, square_str):
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print("Casa non valida.")
		return
	# Calcola il colore della casa: (file+rank) pari -> scura, altrimenti chiara
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = "scura"
	else:
		color_descr = "chiara"
	piece = game_state.board.piece_at(square)
	if piece:
		base_msg = f"La casa {square_str.upper()} è {color_descr} e contiene {extended_piece_description(piece)}."
		# Calcola difensori e attaccanti per la casa occupata
		defenders = game_state.board.attackers(piece.color, square)
		attackers = game_state.board.attackers(not piece.color, square)
		info_parts = []
		if defenders:
			count = len(defenders)
			word = "pezzo" if count == 1 else "pezzi"
			info_parts.append(f"difesa da {count} {word} { 'bianchi' if piece.color == chess.WHITE else 'neri' }")
		if attackers:
			count = len(attackers)
			word = "pezzo" if count == 1 else "pezzi"
			info_parts.append(f"attaccata da {count} {word} { 'neri' if piece.color == chess.WHITE else 'bianchi' }")
		if info_parts:
			base_msg += " " + " e ".join(info_parts) + "."
		print(base_msg)
	else:
		base_msg = f"La casa {square_str.upper()} è {color_descr} e risulta vuota."
		white_attackers = game_state.board.attackers(chess.WHITE, square)
		black_attackers = game_state.board.attackers(chess.BLACK, square)
		info_parts = []
		if white_attackers:
			count = len(white_attackers)
			word = "pezzo" if count == 1 else "pezzi"
			info_parts.append(f"attaccata da {count} {word} bianchi")
		if black_attackers:
			count = len(black_attackers)
			word = "pezzo" if count == 1 else "pezzi"
			info_parts.append(f"attaccata da {count} {word} neri")
		if info_parts:
			base_msg += " " + " e ".join(info_parts) + "."
		print(base_msg)
def report_piece_positions(game_state, piece_symbol):
	try:
		piece = chess.Piece.from_symbol(piece_symbol)
	except Exception as e:
		print("Non riconosciuto: inserisci R N B Q K P, r n b q k p")
		return
	color_string = "bianco" if piece.color == chess.WHITE else "nero"
	full_name = PIECE_NAMES.get(piece.piece_type, "pezzo")
	squares = game_state.board.pieces(piece.piece_type, piece.color)
	positions = []
	for square in squares:
		# Ottieni file e traversa
		file_index = chess.square_file(square)
		rank = chess.square_rank(square) + 1
		file_letter = chr(ord("a") + file_index)
		descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
		positions.append(f"{descriptive_file} {rank}")
	if positions:
		print(f"{color_string}: {full_name} in: " + ", ".join(positions))
	else:
		print(f"Nessun {full_name} {color_string} trovato.")
def report_white_time(game_state):
	initial_white = game_state.clock_config["phases"][game_state.white_phase]["white_time"]
	elapsed_white = initial_white - game_state.white_remaining
	if elapsed_white < 0:
		elapsed_white = 0
	perc_white = (elapsed_white / initial_white * 100) if initial_white > 0 else 0
	print("Tempo bianco: " + FormatTime(game_state.white_remaining) + f" ({perc_white:.0f}%)")
	return
def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	if elapsed_black < 0:
		elapsed_black = 0
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print("Tempo nero: " + FormatTime(game_state.black_remaining) + f" ({perc_black:.0f}%)")
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
		# Se l'orologio è simmetrico, si usa il tempo del bianco
		if clock_config["same_time"]:
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		else:
			# In caso di orologi asimmetrici, per PGN si sceglie un riferimento (qui il bianco)
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		# Se moves == 0, consideriamo la fase come "sudden death"
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
	return f"{m:02d} minuti e {s:02d} secondi!"
def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print("Formato orario non valido. Atteso mm:ss. Errore:", e)
		return 0
def DescribeMove(move, board):
	# Gestione arrocco
	if board.is_castling(move):
		if chess.square_file(move.to_square) > chess.square_file(move.from_square):
			return "arrocco corto"
		else:
			return "arrocco lungo"
	# Otteniamo la notazione SAN della mossa
	try:
		san_str = board.san(move)
	except Exception as e:
		san_str = ""
	# Pattern per analizzare la mossa SAN:
	# Gruppi: 1=pezzo (opzionale), 2=disambiguazione (0-2 caratteri), 3='x' (cattura), 4=destinazione, 5=promozione (opzionale), 6=pezzo promozione, 7=check o checkmate (opzionale)
	pattern = re.compile(r'^([RNBQK])?([a-h1-8]{0,2})(x)?([a-h][1-8])(=([RNBQ]))?([+#])?$')
	m = pattern.match(san_str)
	if not m:
		# Fallback in caso di analisi fallita
		return "Mossa non analizzabile"
	piece_letter = m.group(1)
	disamb = m.group(2)
	capture = m.group(3)
	dest = m.group(4)
	promo_letter = m.group(6)
	check_mark = m.group(7)
	# Determiniamo il nome del pezzo che si muove
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
		piece_name = "pedone"
	# Iniziamo a comporre la descrizione
	descr = ""
	# Per il pedone includiamo l'articolo
	descr += piece_name
	# Se c'è disambiguazione, la aggiungiamo (traducendo lettere in nomi se possibile)
	if disamb:
		parts = []
		for ch in disamb:
			if ch.isalpha():
				parts.append(LETTER_FILE_MAP.get(ch, ch))
			else:
				parts.append(ch)
		descr += " di " + " ".join(parts)
	# Gestione cattura
	if capture:
		descr += " prende "
		captured_piece = board.piece_at(move.to_square)
		if not captured_piece and piece_letter=="" and chess.square_file(move.from_square) != chess.square_file(move.to_square):
			captured_sq = move.to_square + (8 if board.turn==chess.BLACK else -8)
			captured_piece = board.piece_at(captured_sq)
		if captured_piece:
			descr += PIECE_NAMES.get(captured_piece.piece_type, "").lower()
	# Descrizione destinazione
	dest_file = dest[0]
	dest_rank = dest[1]
	dest_name = LETTER_FILE_MAP.get(dest_file, dest_file)
	descr += " in " + dest_name + " " + dest_rank
	# Promozione
	if promo_letter:
		promo_mapping = {
			"Q": chess.QUEEN,
			"R": chess.ROOK,
			"B": chess.BISHOP,
			"N": chess.KNIGHT
		}
		promo_piece_type = promo_mapping.get(promo_letter.upper(), None)
		promo_piece_name = PIECE_NAMES.get(promo_piece_type, "").lower() if promo_piece_type is not None else ""
		descr += " e promuove a " + promo_piece_name
	# Check o scacco matto
	if check_mark:
		if check_mark=="+":
			descr += " scacco"
		elif check_mark=="#":
			descr += " scacco matto!"
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
			white_move_desc = f"Errore nella mossa del bianco: {e}"
		if i + 1 < len(game_state.move_history):  # Se esiste la mossa del nero
			black_move_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_move_san)
				black_move_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except Exception as e:
				black_move_desc = f"Errore nella mossa del nero: {e}"
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
	Carica il file ECO e restituisce una lista di dizionari,
	ciascuno contenente "eco", "opening", "variation" e "moves" (lista di mosse in SAN).
	"""
	eco_entries = []
	if not os.path.exists(filename):
		print("File eco.db non trovato.")
		return eco_entries
	with open(filename, "r", encoding="utf-8") as f:
		content = f.read()
	# Rimuovi eventuali blocchi di commento racchiusi tra { e }
	content = re.sub(r'\{[^}]*\}', '', content)
	# Utilizza StringIO per far leggere il contenuto "pulito" al parser PGN
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
	Dato l'elenco delle mosse giocate (move_history, lista di stringhe in SAN)
	e il database ECO (lista di dict), restituisce l'entry dell'apertura
	con il più lungo prefisso corrispondente alle mosse giocate.
	Se nessuna mossa corrisponde, restituisce None.
	"""
	best_match = None
	best_match_length = 0
	for entry in eco_db:
		eco_moves = entry["moves"]
		match_length = 0
		# Confronta elemento per elemento la lista move_history e quella dell'entry
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
		parts.append(f"{h} {'ora' if h==1 else 'ore'}")
	if m:
		parts.append(f"{m} {'minuto' if m==1 else 'minuti'}")
	if s:
		parts.append(f"{s} {'secondo' if s==1 else 'secondi'}")
	return ", ".join(parts) if parts else "0 secondi"
def ParseTime(prompt):
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":"))
		return h*3600+m*60+s
	except Exception as e:
		print("Formato orario non valido. Atteso hh:mm:ss. Errore:",e)
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
	print("\nCreazione orologi\n")
	name=dgt("Nome dell'orologio: ",kind="s")
	db=LoadDB()
	if any(c["name"]==name for c in db["clocks"]):
		print("Un orologio con questo nome esiste già.")
		return
	same=dgt("Bianco e Nero partono con lo stesso tempo? (Invio per sì, 'n' per no): ",kind="s",smin=0,smax=1)
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(f"Tempo (hh:mm:ss) per fase {phase_count+1}: ")
			inc=dgt(f"Incremento in secondi per fase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(f"Tempo per il bianco (hh:mm:ss) fase {phase_count+1}: ")
			inc_w=dgt(f"Incremento per il bianco fase {phase_count+1}: ",kind="i")
			total_seconds_b=ParseTime(f"Tempo per il nero (hh:mm:ss) fase {phase_count+1}: ")
			inc_b=dgt(f"Incremento per il nero fase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(f"Numero di mosse per fase {phase_count+1} (0 per terminare): ",kind="i")
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt("Numero di allarmi da inserire (max 5, 0 per nessuno): ",kind="i",imax=5,default=0)
	for i in range(num_alarms):
		alarm_input = dgt(f"Inserisci il tempo (mm:ss) per l'allarme {i+1}: ", kind="s")
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt("Inserisci una nota per l'orologio (opzionale): ",kind="s",default="")
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	db["clocks"].append(new_clock.to_dict())
	SaveDB(db)
	print("\nOrologio creato e salvato.")
def ViewClocks():
	print("\nVisualizzazione orologi\n")
	db=LoadDB()
	if not db["clocks"]:
		print("Nessun orologio salvato.")
		return
	for idx,c in enumerate(db["clocks"]):
		indicatore="B=N" if c["same_time"] else "B/N"
		fasi=""
		for i,phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str=SecondsToHMS(phase["white_time"])
				fasi+=f" F{i+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w=SecondsToHMS(phase["white_time"])
				time_str_b=SecondsToHMS(phase["black_time"])
				fasi+=f" F{i+1}: Bianco:{time_str_w}+{phase['white_inc']}, Nero:{time_str_b}+{phase['black_inc']}"
		num_alarms = len(c.get("alarms", []))  # Conta gli allarmi
		alarms_str = f" Allarmi ({num_alarms})"
		print(f"{idx+1}. {c['name']} - {indicatore}{fasi}{alarms_str}")
		if c.get("note",""):
			print(f"\tNota: {c['note']}")
	attesa=key("Premi un tasto per tornare al menu principale.")
def SelectClock(db):
	db = LoadDB()
	if not db["clocks"]:
		print("Nessun orologio salvato.")
		return
	else:
		print(f"Ci sono {len(db['clocks'])} orologi nella collezione.")
	choices = {}
	for c in db["clocks"]:
		indicatore = "B=N" if c["same_time"] else "B/N"
		fasi = ""
		for j, phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str = SecondsToHMS(phase["white_time"])
				fasi += f" F{j+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w = SecondsToHMS(phase["white_time"])
				time_str_b = SecondsToHMS(phase["black_time"])
				fasi += f" F{j+1}: Bianco:{time_str_w}+{phase['white_inc']}, Nero:{time_str_b}+{phase['black_inc']}"
		num_alarms = len(c.get("alarms", []))
		alarms_str = f" Allarmi ({num_alarms})"
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
		print("Nessun orologio selezionato.")
def DeleteClock(db):
	print("\nEliminazione orologi salvati\n")
	orologio = SelectClock(db)
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			del db["clocks"][idx]
			SaveDB(db)
			print(f"\nOrologio '{clock_name}' eliminato, ne rimangono {len(db['clocks'])}.")
	return
def EditPGN():
	print("\nModifica info default per PGN\n")
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	default_event = default_pgn.get("Event", "Orologic Game")
	event = dgt(f"Evento [{default_event}]: ", kind="s", default=default_event)
	if event.strip() == "":
		event = default_event
	default_site = default_pgn.get("Site", "Sede sconosciuta")
	site = dgt(f"Sede [{default_site}]: ", kind="s", default=default_site)
	if site.strip() == "":
		site = default_site
	default_round = default_pgn.get("Round", "Round 1")
	round_ = dgt(f"Round [{default_round}]: ", kind="s", default=default_round)
	if round_.strip() == "":
		round_ = default_round
	default_white = default_pgn.get("White", "Bianco")
	white = dgt(f"Nome del Bianco [{default_white}]: ", kind="s", default=default_white)
	if white.strip() == "":
		white = default_white
	default_black = default_pgn.get("Black", "Nero")
	black = dgt(f"Nome del Nero [{default_black}]: ", kind="s", default=default_black)
	if black.strip() == "":
		black = default_black
	default_white_elo = default_pgn.get("WhiteElo", "1200")
	white_elo = dgt(f"Elo del Bianco [{default_white_elo}]: ", kind="s", default=default_white_elo)
	if white_elo.strip() == "":
		white_elo = default_white_elo
	default_black_elo = default_pgn.get("BlackElo", "1200")
	black_elo = dgt(f"Elo del Nero [{default_black_elo}]: ", kind="s", default=default_black_elo)
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
	print("\nInformazioni default per il PGN aggiornate.")
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
		board_str += f" {last_move_info} Materiale: {white_material}/{black_material}"
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
			self.black_remaining = clock_config["phases"][0]["black_time"]  # O equivalentemente, ["white_time"]
		else:
			self.white_remaining = clock_config["phases"][0]["white_time"]
			self.black_remaining = clock_config["phases"][0]["black_time"]		
		self.white_phase=0
		self.black_phase=0
		self.white_moves=0
		self.black_moves=0
		# Il turno iniziale resta "white" (bianco a muovere)
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
					print(self.white_player + " entra in fase " + str(self.white_phase+1) + " tempo fase " + FormatTime(self.clock_config["phases"][self.white_phase]["white_time"]))
					self.white_remaining=self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves+=1
			if self.black_phase<len(self.clock_config["phases"])-1:
				if self.black_moves>=self.clock_config["phases"][self.black_phase]["moves"] and self.clock_config["phases"][self.black_phase]["moves"]!=0:
					self.black_phase+=1
					Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03,0, volume], kind=3, adsr=[20, 10, 75, 20])
					print(self.black_player + " entra in fase " + str(self.black_phase+1) + " tempo fase " + FormatTime(self.clock_config["phases"][self.black_phase]["black_time"]))
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
						print(f"Allarme: tempo del bianco raggiunto {seconds_to_mmss(alarm)}")
						Acusticator(["c4",0.2,-0.75,volume])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(f"Allarme: tempo del nero raggiunto {seconds_to_mmss(alarm)}")
						Acusticator(["c4",0.2,0.75,volume])
						triggered_alarms_black.add(alarm)
		if game_state.white_remaining<=0 or game_state.black_remaining<=0:
			Acusticator(["e4", 0.2, -0.5, volume, "d4", 0.2, 0, volume, "c4", 0.2, 0.5, volume], kind=1, adsr=[10, 0, 90, 10])
			game_state.game_over=True
			print("Bandierina caduta!")
			if game_state.white_remaining <= 0:
				game_state.pgn_game.headers["Result"] = "0-1"  # Nero vince
				print(f"Tempo del Bianco scaduto. {game_state.black_player} vince.")
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			else:
				game_state.pgn_game.headers["Result"] = "1-0"  # Bianco vince
				print(f"Tempo del Nero scaduto. {game_state.white_player} vince.")
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
		time.sleep(0.1)
def StartGame(clock_config):
	print("\nAvvio partita\n")
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", "Bianco")
	black_default = default_pgn.get("Black", "Nero")
	white_elo_default = default_pgn.get("WhiteElo", "1500")
	black_elo_default = default_pgn.get("BlackElo", "1500")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", "Sede sconosciuta")
	round_default = default_pgn.get("Round", "Round 1")
	eco_db = LoadEcoDatabase("eco.db")
	last_eco_msg = None 
	white_player = dgt(f"Nome del bianco [{white_default}]: ", kind="s", default=white_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_player.strip() == "":
		white_player = white_default
	black_player = dgt(f"Nome del nero [{black_default}]: ", kind="s", default=black_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_player.strip() == "":
		black_player = black_default
	white_elo = dgt(f"Elo del bianco [{white_elo_default}]: ", kind="s", default=white_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_elo.strip() == "":
		white_elo = white_elo_default
	black_elo = dgt(f"Elo del nero [{black_elo_default}]: ", kind="s", default=black_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_elo.strip() == "":
		black_elo = black_elo_default
	event = dgt(f"Evento [{event_default}]: ", kind="s", default=event_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if event.strip() == "":
		event = event_default
	site = dgt(f"Sede [{site_default}]: ", kind="s", default=site_default)
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
	key("Premi un tasto qualsiasi per iniziare la partita quando sei pronto...",attesa=1800)
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
					print("Traversa non valida.")
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				read_square(game_state, param)
			else:
				print("Comando dash non riconosciuto.")
		elif user_input.startswith(","):
			Acusticator(["a3", .06, -1, volume, "c4", .06, -0.5, volume, "d#4", .06, 0.5, volume, "f4", .06, 1, volume], kind=3, adsr=[20, 5, 70, 25])
			report_piece_positions(game_state, user_input[1:2])
		elif user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			if cmd==".?":
				menu(DOT_COMMANDS,show_only=True,p="Comandi disponibili:")
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
				adv="bianco" if game_state.white_remaining>game_state.black_remaining else "nero"
				print(f"{adv} in vantaggio di "+FormatTime(diff))
			elif cmd==".5":
				if game_state.paused:
					Acusticator(['d4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					pause_duration = time.time() - paused_time_start if paused_time_start else 0
					hours = int(pause_duration // 3600)
					minutes = int((pause_duration % 3600) // 60)
					seconds = int(pause_duration % 60)
					ms = int((pause_duration - int(pause_duration)) * 1000)
					print(f"Tempo in pausa da: {f'{hours:2d} ore, ' if hours else ''}{f'{minutes:2d} minuti, ' if minutes or hours else ''}{f'{seconds:2d} secondi e ' if seconds or minutes or hours else ''}{f'{ms:3d} ms' if ms else ''}")
				else:
					Acusticator(['f4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					player = game_state.white_player if game_state.active_color=="white" else game_state.black_player
					print(f"Orologio di {player} in moto")
			elif cmd==".m":
				white_material,black_material=CalculateMaterial(game_state.board)
				print(f"Materiale: {game_state.white_player} {white_material}, {game_state.black_player} {black_material}")
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					print("Orologi in pausa")
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
					print("Pausa durata "+FormatTime(pause_duration))
			elif cmd==".q":
				if game_state.paused and game_state.move_history:
					game_state.board.pop()
					game_state.pgn_node=game_state.pgn_node.parent
					last_move=game_state.move_history.pop()
					print("Ultima mossa annullata: "+last_move)
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
						print("Nuovo tempo bianco: "+FormatTime(game_state.white_remaining)+", nero: "+FormatTime(game_state.black_remaining))
					except:
						print("Comando non valido.")
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, volume, "g4", 0.2, -0.3, volume, "c5", 0.2, 0.3, volume, "e5", 0.2, 1, volume, "g5", 0.4, 0, volume], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				summary = GenerateMoveSummary(game_state)
				if summary:
					print("\nLista mosse giocate:\n")
					for line in summary:
						print(line)
				else:
					print("Nessuna mossa ancora giocata.")
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
				print("Risultato assegnato: "+result)
				game_state.pgn_game.headers["Result"]=result
				game_state.game_over=True
			elif cmd.startswith(".c"):
				new_comment = cmd[2:].strip()
				if game_state.move_history:
					if game_state.pgn_node.comment:
						game_state.pgn_node.comment += "\n" + new_comment
					else:
						game_state.pgn_node.comment = new_comment
					print("Commento registrato per la mossa: " + game_state.move_history[-1])
				else:
					print("Nessuna mossa da commentare.")
			else:
				print("Comando non riconosciuto.")
		else:
			if game_state.paused:
				print("Non è possibile inserire nuove mosse mentre il tempo è in pausa. Riavvia il tempo con .p")
				Acusticator(["b3",.2,0,volume],kind=2)
				continue
			user_input=NormalizeMove(user_input)
			try:
				move = game_state.board.parse_san(user_input)
				board_copy=game_state.board.copy()
				description=DescribeMove(move,board_copy)
				Acusticator([1000.0, 0.01, 0, volume], kind=1, adsr=[0, 0, 100, 0])
				# Stampa la mossa preceduta dal nome del giocatore in base al turno
				if game_state.active_color=="white":
					print(game_state.white_player+": "+description)
				else:
					print(game_state.black_player+": "+description)
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
							print("Apertura rilevata: " + new_eco_msg)
							last_eco_msg = new_eco_msg
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "1-0" if game_state.active_color == "white" else "0-1"
					game_state.pgn_game.headers["Result"] = result
					print(f"Scacco matto! Vince {game_state.white_player if game_state.active_color == 'white' else game_state.black_player}.")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break  # Esci dal ciclo
				elif game_state.board.is_stalemate():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per stallo!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_insufficient_material():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per materiale insufficiente!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_seventyfive_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per la regola delle 75 mosse!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_fivefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per ripetizione della posizione (5 volte)!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_fifty_moves():  # Controllo per la *richiesta* delle 50 mosse
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per la regola delle 50 mosse (su richiesta)!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition(): # Controllo per la *richiesta* della triplice ripetizione.
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per triplice ripetizione della posizione (su richiesta)!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()
			except Exception as e:
				illegal_result=verbose_legal_moves_for_san(game_state.board,user_input)
				print("Mossa illegale:\n"+illegal_result)
	game_state.pgn_game.headers["WhiteClock"] = FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = FormatClock(game_state.black_remaining)
	print("Partita terminata.")
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
	print("PGN salvato come "+filename+".")
	analyze_choice = key("Vuoi analizzare la partita? (s/n): ").lower()
	if analyze_choice == "s":
		db = LoadDB()
		engine_config = db.get("engine_config", {})
		if not engine_config or not engine_config.get("engine_path"):
			print("Motore non configurato. Ritorno al menù.")
			return
		else:
			AnalyzeGame(game_state.pgn_game)
def OpenManual():
	print("\nApertura manuale\n")
	readme="readme_it.htm"
	if os.path.exists(readme):
		webbrowser.open(readme)
	else:
		print("Il file readme_it.htm non esiste.")
def SchermataIniziale():
	now = datetime.datetime.now()
	diff1 = relativedelta(now, BIRTH_DATE)
	diff2 = relativedelta(now, RELEASE_DATE)
	parts1 = []
	if diff1.years:
		parts1.append(f"{diff1.years} anni")
	if diff1.months:
		parts1.append(f"{diff1.months} mesi")
	if diff1.days:
		parts1.append(f"{diff1.days} giorni")
	if diff1.hours:
		parts1.append(f"{diff1.hours} ore")
	if diff1.minutes:
		parts1.append(f"e {diff1.minutes} minuti")
	age_string = ", ".join(parts1)
	parts2 = []
	if diff2.years:
		parts2.append(f"{diff2.years} anni")
	if diff2.months:
		parts2.append(f"{diff2.months} mesi")
	if diff2.days:
		parts2.append(f"{diff2.days} giorni")
	if diff2.hours:
		parts2.append(f"{diff2.hours} ore")
	if diff2.minutes:
		parts2.append(f"{diff2.minutes} minuti")
	release_string = ", ".join(parts2)
	print(f"\nCiao! Benvenuto, sono Orologic e ho {age_string}.")
	print(f"L'ultima versione è la {VERSION} ed è stata rilasciata il {RELEASE_DATE.strftime('%d/%m/%Y %H:%M')}.")
	print(f"\tcioè: {release_string} fa.")
	print("\t\tAutore: "+PROGRAMMER)
	print("\t\t\tDigita '?' per visualizzare il menù.")
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
		elif scelta=="comandi":
			Acusticator([500.0, 0.4, -1, volume, 800.0, 0.4, 1, volume], kind=3, adsr=[20, 10, 50, 20])
			menu(DOT_COMMANDS,show_only=True)
		elif scelta=="motore":
			Acusticator(["e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume])
			EditEngineConfig()
		elif scelta=="volume":
			Acusticator(["f6",.02,0,volume,"p",.04,0,volume,"a6",.02,0,volume])
			volume = dgt(f"\nVolume attuale: {int(volume*100)}, nuovo? (0-100): ", kind="i", imin=0, imax=100, default=50)
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
			print("\nAvvio partita\n")
			db=LoadDB()
			if not db["clocks"]:
				print("Nessun orologio disponibile. Creane uno prima.")
			else:
				clock_config=SelectClock(db)
				if clock_config is not None:
					StartGame(clock_config)
				else:
					print("Scelta non valida.")
		elif scelta==".":
			Acusticator(["g4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "a4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "p", 0.15, 0, 0, "b4", 0.15, -0.5, volume, "c5", 0.3, 0.5, volume], kind=1, adsr=[5, 0, 100, 5])
			if ENGINE is not None:
				ENGINE.quit()
				print("\nConnessione col motore UCI chiusa")
			break
if __name__=="__main__":
	time_start = datetime.datetime.now()
	board=CustomBoard()
	Main()
	time_end = datetime.datetime.now()
	delta = relativedelta(time_end, time_start)
	components = []
	if delta.days:
		components.append(f"{delta.days} giorni")
	if delta.hours:
		components.append(f"{delta.hours} ore")
	if delta.minutes:
		components.append(f"{delta.minutes} minuti")
	if delta.seconds:
		components.append(f"{delta.seconds} secondi")
	ms = delta.microseconds // 1000
	if ms:
		components.append(f"{ms} millisecondi")
	result = ", ".join(components) if components else "0 millisecondi"
	print(f"Arrivederci da Orologic {VERSION}.\nCi siamo divertiti assieme per: {result}")
	sys.exit(0)