# OROLOGIC (IT) - Data di concepimento: 14/02/2025 by Gabriele Battaglia & AIs
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re, pyperclip, io, chess.engine, random
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator, key, Donazione
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="3.20.2"
RELEASE_DATE=datetime.datetime(2025,6,22,7,36)
PROGRAMMER="Gabriele Battaglia & AIs"
DB_FILE="orologic_db.json"
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
NAG_MAP = {
	"!": (1, "mossa forte"),
	"?": (2, "mossa debole"),
	"!!": (3, "mossa molto forte"),
	"??": (4, "mossa molto debole"),
	"!?": (5, "mossa dubbia"),
	"?!": (6, "mossa dubbia"),
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}
L10N = {}
# Pattern Regex per estrarre il suffisso di annotazione (1 o 2 caratteri !?=) alla fine della stringa.
# Il lookbehind (?<!=.) evita di catturare l'uguale della promozione (es. non matcha '=Q').
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
# Pattern Regex specifico per gestire i suffissi DOPO una promozione (es. "d8=Q!")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")
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
	"b": "Attiva/disattiva la lettura automatica dei commenti",
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
	"nomi":"Personalizza i nomi dei pezzi e delle colonne",
	"pgn":"Imposta le info di default per il PGN",
	"vedi":"... gli orologi salvati",
	"volume":"Consente la regolazione del volume degli effetti audio",
	".":"Esci dall'applicazione"}
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
	return "\n".join(result_lines)
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
	Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
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
				Acusticator(["c4", 0.1, -0.5, volume], kind=2, adsr=[10, 10, 30, 50]) 
				print("\nNon ci sono mosse precedenti.")
		elif cmd == "?":
			Acusticator(["d5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			temp_board = board.copy()
			try:
				for move in pv_moves[:current_index]:
					temp_board.push(move)
			except Exception as push_err:
				print(f"\nErrore interno durante avanzamento per valutazione: {push_err}")
				eval_str = "ERR_NAV" # Aggiorna la stringa del prompt per indicare l'errore
				continue # Torna all'inizio del loop while
			score_object_si = CalculateEvaluation(temp_board)
			Acusticator(["e5",.008,-1,volume]) # Suono dopo il tentativo
			if score_object_si is not None:
				new_eval_str = "N/A" # Valore di default per la stringa formattata
				pov_score_si = score_object_si.pov(temp_board.turn)
				if pov_score_si.is_mate():
					mate_in_si = pov_score_si.mate()
					new_eval_str = f"M{abs(mate_in_si)}"
				else:
					cp_si = score_object_si.white().score(mate_score=30000)
					if cp_si is not None:
						new_eval_str = f"{cp_si/100:+.2f}" # Formatta CP assoluto
					else:
						new_eval_str = "ERR"
				eval_str = new_eval_str
				Acusticator(["g5", 0.1, 0.3, volume], kind=1, adsr=[5,5,90,5]) # Suono successo
				print("\nValutazione aggiornata.")
			else:
				Acusticator(["a3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]) # Suono errore
				print("\nImpossibile aggiornare la valutazione.")
				eval_str = "N/A"
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				Acusticator(["c4", 0.1, 0.5, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNon ci sono mosse successive.")
		else:
			Acusticator(["b3", 0.12, 0, volume], kind=2, adsr=[5, 15, 20, 60])
			print("\nComando non riconosciuto.")
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
					move_descr = f"{move_number}°. {white_descr}"
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
					descriptive_moves.append(f"{move_number}°... {black_descr}")
					move_number += 1
			score = analysis[0].get("score")
			mate_found = False
			if score is not None and score.relative.is_mate():
				mate_moves = abs(score.relative.mate())
				mate_found = True
			if bestmove:
				if mate_found:
					Acusticator(["a6",.008,1,volume]) 
					return [f"Matto in {mate_moves}, {descriptive_moves[0]}"]
				else:
					Acusticator(["f6",.008,1,volume]) 
					return [descriptive_moves[0]]
			else:
				if mate_found:
					descriptive_moves.insert(0, f"Matto in {mate_moves}:")
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
		print("Errore in CalculateBestLine:", e)
		return None
def CalculateEvaluation(board):
	global ENGINE, analysis_time, multipv, cache_analysis
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result:
			print(f"DEBUG: Analisi per FEN {fen} ha restituito risultato vuoto.") # Debug opzionale
			return None
		score = analysis_result[0].get("score")
		return score
	except Exception as e:
		print(f"Errore in CalculateEvaluation per FEN {fen}: {e}")
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
					print(f"Warning: Valori WDL dopo unpack non numerici: W={win_permille_pov}, D={draw_permille_pov}, L={loss_permille_pov}")
					return None
			perspective = None
			if hasattr(wdl_info, "color"):
				perspective = wdl_info.color
			elif hasattr(wdl_info,"pov"): # Nome alternativo comune
				perspective = wdl_info.pov
			else:
				 # Se non riusciamo a determinare la prospettiva, assumiamo per sicurezza
				# che sia già assoluta (WHITE) come da standard UCI.
				print(f"Warning: Impossibile determinare prospettiva WDL da {repr(wdl_info)}. Assumo WHITE.")
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
			print(f"Warning: Fallito unpack diretto oggetto WDL {repr(wdl_info)}: {e_unpack}")
			return None
	except Exception as e:
		print(f"Errore generale in CalculateWDL per FEN {fen}: {e}")
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
						Acusticator(["a3", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
						print("Numero non valido. Riprova.")
				except ValueError:
					Acusticator(["g2", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
					print("Input non valido. Inserisci un numero.")
	except Exception as e:
		print("Errore in LoadPGNFromClipboard:", e)
		return None
def InitEngine():
	global ENGINE
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config or not engine_config.get("engine_path"):
		Acusticator(["d4", 0.5, -1, volume],kind=4, adsr=[.001,0,100,99.9])
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
	Acusticator(["g6", 0.025, -.75, volume,"c5", 0.025, -75, volume],kind=3)
	executable = dgt(prompt="Inserisci il nome dell'eseguibile del motore (es. stockfish_15_x64_popcnt.exe): ", kind="s", smin=5, smax=64)
	Acusticator(["g6", 0.025, -.5, volume,"c5", 0.025, -.5, volume],kind=3)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print("Il file specificato non esiste. Verifica il percorso e il nome dell'eseguibile.")
		return
	hash_size = dgt(prompt="Inserisci la dimensione della hash table (min: 1, max: 4096 MB): ", kind="i", imin=1, imax=4096)
	Acusticator(["g6", 0.025, -.25, volume,"c5", 0.025, -.25, volume],kind=3)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=f"Inserisci il numero di core da utilizzare (min: 1, max: {max_cores}): ", kind="i", imin=1, imax=max_cores, default=4)
	Acusticator(["g6", 0.025, 0, volume,"c5", 0.025, 0, volume],kind=3)
	skill_level = dgt(prompt="Inserisci il livello di skill (min: 0, max: 20): ", kind="i", imin=0, imax=20)
	Acusticator(["g6", 0.025, .25, volume,"c5", 0.025, .25, volume],kind=3)
	move_overhead = dgt(prompt="Inserisci il move overhead in millisecondi (min: 0, max: 500): ", kind="i", imin=0, imax=500, default=0)
	Acusticator(["g6", 0.025, .5, volume,"c5", 0.025, .5, volume],kind=3)
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
	Acusticator(["a6", 0.5, 1, volume],kind=3, adsr=[.001,0,100,99.9])
	return

def EditLocalization():
	"""
	Crea un'interfaccia per permettere all'utente di personalizzare
	le stringhe usate nel programma (localizzazione).
	"""
	print("\n--- Personalizzazione Lingua ---\n")
	print("Per ogni voce, inserisci il nuovo testo o premi INVIO per mantenere il valore attuale.")
	db = LoadDB()
	# Usiamo una copia per le modifiche, per poi salvarla tutta in una volta
	l10n_config = db.get("localization", get_default_localization())
	# Definiamo le voci da personalizzare e i relativi prompt
	# Struttura: [ (chiave_cat, chiave_voce, prompt_utente), ... ]
	# Per voci complesse (dizionari), usiamo una tupla: (chiave_cat, chiave_voce, (chiave_sub, prompt_sub))
	items_to_edit = [
		("pieces", "pawn", ("name", "Nome per 'Pedone'")),
		("pieces", "knight", ("name", "Nome per 'Cavallo'")),
		("pieces", "bishop", ("name", "Nome per 'Alfiere'")),
		("pieces", "rook", ("name", "Nome per 'Torre'")),
		("pieces", "queen", ("name", "Nome per 'Donna'")),
		("pieces", "king", ("name", "Nome per 'Re'")),
		("columns", "a", "Nome per colonna 'a' (Ancona)"),
		("columns", "b", "Nome per colonna 'b' (Bologna)"),
		("columns", "c", "Nome per colonna 'c' (Como)"),
		("columns", "d", "Nome per colonna 'd' (Domodossola)"),
		("columns", "e", "Nome per colonna 'e' (Empoli)"),
		("columns", "f", "Nome per colonna 'f' (Firenze)"),
		("columns", "g", "Nome per colonna 'g' (Genova)"),
		("columns", "h", "Nome per colonna 'h' (Hotel)"),
		("adjectives", "white", ("m", "Aggettivo 'bianco' (maschile)")),
		("adjectives", "white", ("f", "Aggettivo 'bianco' (femminile)")),
		("adjectives", "black", ("m", "Aggettivo 'nero' (maschile)")),
		("adjectives", "black", ("f", "Aggettivo 'nero' (femminile)")),
		("moves", "capture", "Verbo per la cattura (es. 'prende')"),
		("moves", "capture_on", "Preposizione per la casa di cattura (es. 'in')"),
		("moves", "move_to", "Preposizione per la casa di destinazione (es. 'in')"),
		("moves", "en_passant", "Testo per 'en passant'"),
		("moves", "short_castle", "Testo per 'arrocco corto'"),
		("moves", "long_castle", "Testo per 'arrocco lungo'"),
		("moves", "promotes_to", "Testo per la promozione (es. 'e promuove a')"),
		("moves", "check", "Testo per 'scacco'"),
		("moves", "checkmate", "Testo per 'scacco matto!'")
	]
	# Logica per audio elegante
	num_items = len(items_to_edit)
	notes = ['c3', 'd3', 'e3', 'f3', 'g3', 'a3', 'b3', 'c4', 'd4', 'e4', 'f4', 'g4', 'a4', 'b4', 'c5', 'd5', 'e5', 'f5', 'g5', 'a5', 'b5', 'c6', 'd6', 'e6', 'f6', 'g6', 'a6', 'b6', 'c7']
	for i, item in enumerate(items_to_edit):
		cat, key, details = item
		pitch = notes[i % len(notes)]
		pan = -1 + (2 * i / (num_items -1)) if num_items > 1 else 0 # Da -1 (sx) a 1 (dx)
		if isinstance(details, tuple): # Voce complessa (es. pezzi, aggettivi)
			sub_key, prompt_text = details
			current_val = l10n_config[cat][key][sub_key]
			new_val = dgt(f"{prompt_text} [{current_val}]: ", kind="s", default=current_val)
			l10n_config[cat][key][sub_key] = new_val.strip()
			# Se abbiamo appena modificato un pezzo, chiediamo il genere
			if cat == "pieces":
				current_gender = l10n_config[cat][key]['gender']
				gender_prompt = f"  Genere per '{new_val}' (m/f/n) [{current_gender}]: "
				while True:
					new_gender = dgt(gender_prompt, kind="s", default=current_gender).lower()
					if new_gender in ['m', 'f', 'n']:
						l10n_config[cat][key]['gender'] = new_gender
						break
					else:
						print("Input non valido. Inserisci 'm' (maschile), 'f' (femminile) o 'n' (neutro).")
		else: # Voce semplice (es. colonne, mosse)
			prompt_text = details
			current_val = l10n_config[cat][key]
			new_val = dgt(f"{prompt_text} [{current_val}]: ", kind="s", default=current_val)
			l10n_config[cat][key] = new_val.strip()
		Acusticator([pitch, 0.08, pan, volume], kind=1, adsr=[2, 5, 80, 10])
	Acusticator(['c7', 0.05, 0, volume,'e7', 0.05, 0, volume,'g7', 0.15, 0, volume], kind=1, adsr=[2, 5, 90, 5])
	# Salvataggio finale
	db["localization"] = l10n_config
	SaveDB(db)
	LoadLocalization() # Ricarica le impostazioni per renderle subito attive
	print("\nImpostazioni di lingua salvate con successo!")

def AnalyzeGame(pgn_game):
	"""
	Funzione di analisi della partita (PGN).
	Legge le annotazioni NAG durante la navigazione.
	"""
	if pgn_game is None:
		pgn_game = LoadPGNFromClipboard()
		if pgn_game:
			# Ricorsione sicura perché pgn_game è ora definito o None
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
		Acusticator(["f5", 0.03, 0, volume], kind=1, adsr=[0,0,100,0])
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
				try: # Aggiunto try-except per robustezza se il nodo non è nelle varianti (?)
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
		extra_prompt = "" # Resetta extra prompt per il prossimo ciclo

		if current_node.comment and comment_auto_read:
			print("Commento:", current_node.comment)
		elif current_node.comment and not comment_auto_read:
			Acusticator(["c7",	0.024, 0, volume], kind=1, adsr=[0,0,100,0])

		cmd = key(prompt).lower().strip()
		# --- 3. Salva Nodo Attuale e Processa Comando ---
		previous_node = current_node
		node_changed = False # Flag per tracciare se il nodo cambia

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
					print("\nGià all'inizio della partita.")
			else:
				current_node = node
			node_changed = (current_node != previous_node)

		elif cmd == "s":
			if current_node.parent:
				current_node = current_node.parent
				Acusticator(["g5", .03, -.2, volume, "c5", .03, -.8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, -0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNessuna mossa precedente.")
			node_changed = (current_node != previous_node)

		elif cmd == "d":
			if current_node.variations:
				current_node = current_node.variations[0]
				Acusticator(["c5", .03, .2, volume,"g5", .03, .8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, 0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNon ci sono mosse successive.")
			node_changed = (current_node != previous_node)

		elif cmd == "f":
			start_node = current_node
			while current_node.variations:
				current_node = current_node.variations[0]
			node_changed = (current_node != start_node)
			if node_changed:
				Acusticator(["g5", 0.1, 0, volume,"p", 0.1, 0, volume,"c6", 0.05, 0, volume,"d6", 0.05, 0, volume,"g6", 0.2, 0, volume], kind=1, adsr=[5,5,90,5])
				print("Sei arrivato alla fine della linea principale.")
			else:
				print("Già alla fine della linea principale.")
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
						print("Non ci sono varianti precedenti.")
				except ValueError:
					print("Errore: nodo corrente non trovato nelle varianti del genitore.")
			else:
				print("Nessun nodo variante disponibile (sei alla radice).")
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
						print("Non ci sono varianti successive.")
				except ValueError:
					print("Errore: nodo corrente non trovato nelle varianti del genitore.")
			else:
				print("Nessun nodo variante disponibile (sei alla radice).")
			node_changed = (current_node != previous_node)

		elif cmd == "k":
			Acusticator(["g3", 0.06, 0, volume,"b3", 0.06, 0, volume,"a3", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			max_moves_num = (total_moves + 1) // 2
			target_fullmove = dgt(f"\nVai a mossa n.# (Max {max_moves_num}): ", kind="i", imin=1, imax=max_moves_num)
			target_ply = max(0, 2 * (target_fullmove - 1)) # Indice semimossa Bianco
			# target_ply = max(0, 2 * target_fullmove -1) # Indice semimossa Nero
			temp_node = pgn_game # Ripartiamo dall'inizio
			ply_count = 0
			found_node = pgn_game # Inizia con il nodo radice

			# Naviga lungo la linea principale
			node_iterator = pgn_game.mainline() # Iteratore sulla linea principale
			for i, node in enumerate(node_iterator):
				 if i == target_ply:
						found_node = node
						break
			else:
				if target_ply > 0 : # Se non si cercava l'inizio
					found_node = node # Vai all'ultimo nodo disponibile
					print("\nRaggiunta la fine della linea prima della mossa richiesta.")

			current_node = found_node
			Acusticator(["g6", 0.06, 0, volume,"b6", 0.06, 0, volume,"a6", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			node_changed = (current_node != previous_node)
			if node_changed and not current_node.move and target_ply > 0: # Siamo andati oltre l'ultima mossa
				pass # Messaggio stampato nel loop sopra
			elif not node_changed:
				print("\nSei già a questa mossa/posizione.")
		elif cmd == "j":
			Acusticator(["d5", 0.08, 0, volume,"p", 0.08, 0, volume,"d6", 0.06, 0, volume], kind=1, adsr=[2,5,90,5])
			print("\nHeader della partita:")
			for k, v in pgn_game.headers.items():
				print(f"{k}: {v}")
		elif cmd == "l":
			try:
				# Usa la funzione helper per caricare una o più partite
				new_game = LoadPGNFromClipboard() # Funzione gestisce output
				if new_game:
					pgn_game = new_game
					current_node = pgn_game # Resetta al nodo iniziale
					previous_node = current_node # Aggiorna previous per evitare stampa descrizione
					node_changed = False # Nodo cambiato ma non per navigazione interna
					move_list = list(pgn_game.mainline_moves())
					total_moves = len(move_list)
					Acusticator(["c6", 0.15, 0, volume], kind=1, adsr=[5, 10, 80, 5])
					print("\nNuovo PGN caricato dagli appunti.")
					print("\nHeaders della nuova partita:\n")
					for k, v in pgn_game.headers.items():
						print(f"{k}: {v}")
					print(f"Numero totale di mosse: {(total_moves+1)//2}")
				# else: LoadPGNFromClipboard stampa già i messaggi
			except Exception as e:
				print("\nErrore nel caricamento dagli appunti:", e)
		elif cmd == "z":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalcolo bestline...")
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
						first_new_node.comment = ((first_new_node.comment or "") + " {Bestline aggiunta}").strip()
					saved = True; print("Bestline aggiunta/aggiornata come variante.")
					Acusticator(["a5", 0.12, 0.3, volume,"b5", 0.12, 0.3, volume,"c6", 0.12, 0.3, volume,"d6", 0.12, 0.3, volume,"e6", 0.12, 0.3, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(f"\nErrore durante l'aggiunta della variante: {e}"); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nImpossibile calcolare la bestline.")
		elif cmd == "x":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalcolo bestmove...")
			bestmove_uci = CalculateBest(current_node.board(), bestmove=True, as_san=False)
			if bestmove_uci:
				try:
					san_move = current_node.board().san(bestmove_uci)
					current_node.comment = ((current_node.comment or "").strip() + f" {{BM: {san_move}}}").strip()
					saved = True; print(f"\nBestmove ({san_move}) aggiunta al commento.")
					Acusticator(["a5", 0.15, 0, volume,"d6", 0.15, 0, volume], kind=1, adsr=[3,7,88,2])
				except Exception as e: print(f"\nErrore nell'ottenere SAN per bestmove: {e}"); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nImpossibile calcolare la bestmove.")
		elif cmd == "c":
			Acusticator(["d6", 0.012, 0, volume, "p", 0.15,0,0,"a6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			user_comment = dgt("\nInserisci il commento: ", kind="s").strip()
			if user_comment:
				if current_node.comment:
					current_node.comment += user_comment
				else:
					current_node.comment = user_comment
				saved = True; print("\nCommento aggiunto/aggiornato.")
				Acusticator(["a6", 0.012, 0, volume, "p", 0.15,0,0,"d6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			else: print("\nNessun commento inserito.")
		elif cmd == "v":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalcolo valutazione...")
			score_object = CalculateEvaluation(current_node.board())
			if score_object is not None:
				eval_val_str = "ERR"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_val_str = f"M{abs(mate_in)}"
				else:
					# --- USA SCORE ASSOLUTO ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_val_str = f"{cp/100:+.2f}" # Valore assoluto per il commento
				eval_comment = f"{{Val: {eval_val_str}}}"
				current_node.comment = ((current_node.comment or "").strip() + f" {eval_comment}").strip()
				saved = True; print(f"\nValutazione ({eval_val_str}) aggiunta al commento.")
				Acusticator(["g5", 0.07, 0, volume,"p", 0.04, 0, volume,"b5", 0.025, 0, volume], kind=1, adsr=[3,7,88,2])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nImpossibile calcolare la valutazione.")		
		elif cmd == "b":
			if comment_auto_read:
				comment_auto_read = False
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b4", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print("\nLettura automatica dei commenti disabilitata.")
			else:
				comment_auto_read = True
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b6", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print("\nLettura automatica dei commenti abilitata.")
		elif cmd == "n":
			if current_node.comment:
				Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
				confirm = key(f"\nEliminare il commento: '{current_node.comment}'? (s/n): ").lower()
				if confirm == "s":
					current_node.comment = ""; saved = True; print("Commento eliminato.")
					Acusticator(["e4", 0.1, -0.4, volume], kind=1, adsr=[5,10,70,15])
				else: print("Eliminazione annullata.")
			else: Acusticator(["b3", 0.12, -0.4, volume], kind=2, adsr=[5, 15, 20, 60]); print("\nNessun commento da eliminare.")
		elif cmd == "q":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalcolo bestmove...")
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
								# --- USA SCORE ASSOLUTO ---
								cp = score_object.white().score(mate_score=30000)
								if cp is not None:
									score_info_str = f"{cp/100:+.2f}"
								else:
									score_info_str = "ERR"
				try:
					san_move = current_node.board().san(bestmove_uci)
					desc_move = DescribeMove(bestmove_uci, current_node.board(), annotation=None)
					print("\nMossa migliore: "+desc_move)
					if score_info_str:
						extra_prompt = f" BM: {score_info_str} {san_move} "
					else:
						extra_prompt = f" BM: {san_move} "
					Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(f"\nErrore nell'ottenere SAN/Descr per bestmove: {e}"); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); extra_prompt = " BM: Errore "
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nImpossibile calcolare la bestmove."); extra_prompt = " BM: N/A "		
		elif cmd == "w":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalcolo bestline...")
			bestline_list_descr = CalculateBest(current_node.board(), bestmove=False, as_san=True)
			if bestline_list_descr:
				Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume,"p", .15, 0, 0,"e7", 0.02, 0, volume,"p", .15, 0, 0,"g7", 0.02, 0, volume,"p", .15, 0, 0,"b7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				print("\nLinea migliore:"); [print(line) for line in bestline_list_descr]
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
								# --- USA SCORE ASSOLUTO ---
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
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nImpossibile calcolare la bestline."); extra_prompt = " BM: N/A "		
		elif cmd == "e":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalcolo linee di analisi..."); fen = current_node.board().fen()
			cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
			analysis = cache_analysis[fen]
			if not analysis: print("Nessun risultato di analisi disponibile."); continue
			main_info = analysis[0]; score = main_info.get("score"); wdl = None; wdl_str = "N/A"; score_str = "N/A"
			if score is not None:
				if hasattr(score, "wdl"): wdl_raw = score.wdl(); wdl = (wdl_raw[0]/10, wdl_raw[1]/10, wdl_raw[2]/10) if wdl_raw else None; wdl_str = f"{wdl[0]:.1f}%/{wdl[1]:.1f}%/{wdl[2]:.1f}%" if wdl else "N/A"
				if score.white().is_mate(): score_str = f"M{score.white().mate()}"
				else: score_cp = score.white().score(); score_str = f"{score_cp/100:+.2f}" if score_cp is not None else "N/A"
			depth = main_info.get("depth", "N/A"); seldepth = main_info.get("seldepth", "N/A"); nps = main_info.get("nps", "N/A"); hashfull = main_info.get("hashfull", "N/A"); hashfull_perc = f"{hashfull/10:.1f}%" if isinstance(hashfull, int) else "N/A"; debug_string = main_info.get("string", "N/A"); tbhits = main_info.get("tbhits", "N/A"); time_used = main_info.get("time", "N/A"); nodes = main_info.get("nodes", "N/A")
			Acusticator(["f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume], kind=1, adsr=[4,8,85,5])
			print(f"\nStatistiche: Tempo: {time_used}s, Hash: {hashfull_perc}, TB: {tbhits}\nDebug: {debug_string}\nProfondità: {depth}/{seldepth}, Val: {score_str}, WDL: {wdl_str}\nNodi: {nodes}, NPS: {nps}\n\nLinee di analisi:")
			for i, info in enumerate(analysis, start=1):
				pv = info.get("pv", []); line_score = info.get("score"); line_score_str = "N/A"
				if line_score: line_score_str = f"M{line_score.white().mate()}" if line_score.white().is_mate() else f"{line_score.white().score()/100:+.2f}" if line_score.white().score() is not None else "N/A"
				if not pv: print(f"Linea {i} ({line_score_str}): Nessuna mossa trovata."); continue
				temp_board_pv = current_node.board().copy(); moves_san = []
				try:
					for move in pv: san_move = temp_board_pv.san(move).replace("!", "").replace("?",""); moves_san.append(san_move); temp_board_pv.push(move)
					print(f"Linea {i} ({line_score_str}): {' '.join(moves_san)}")
				except Exception as e_pv: print(f"Linea {i} ({line_score_str}): Errore conversione PV - {e_pv}")
			smart = key("\nVuoi ispezionare le linee in modalità smart? (s/n): ").lower()
			if smart == "s": Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0]); SmartInspection(analysis, current_node.board())
			else: Acusticator(["d4", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
		elif cmd == "r":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2]); extra_prompt = " CP: N/A "; continue
			print("\nCalcolo valutazione...")
			score_object = CalculateEvaluation(current_node.board())
			Acusticator(["e5",.008,-1,volume])
			if score_object is not None:
				eval_str = "N/A"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_str = f"M{abs(mate_in)}"
				else:
					# --- USA SCORE ASSOLUTO ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_str = f"{cp/100:+.2f}"
					else:
						eval_str = "ERR"
				extra_prompt = f" CP: {eval_str} "
				Acusticator(["g3", 0.17, 0, volume,"g6",.012,0,volume], kind=1, adsr=[3,0,90,2])
			else:
				print("\nImpossibile calcolare la valutazione.")
				extra_prompt = " CP: N/A "
				Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2])		
		elif cmd == "t":
			if ENGINE is None: print("\nMotore non inizializzato."); Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3]); extra_prompt = " WDL: N/A "; continue
			print("\nCalcolo WDL..."); wdl_perc = CalculateWDL(current_node.board())
			if wdl_perc: adj_wdl=f"W{wdl_perc[0]:.1f}%/D{wdl_perc[1]:.1f}%/L{wdl_perc[2]:.1f}% "; extra_prompt=f"{adj_wdl} "; Acusticator(["g#5", 0.03, 0, volume,"c6", 0.03, 0, volume,"g#5", 0.03, 0, volume,"c6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
			else: print("\nImpossibile calcolare WDL."); extra_prompt = " WDL: N/A "; Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "y":
			white_material, black_material = CalculateMaterial(current_node.board()); extra_prompt = f"Mtrl: {white_material}/{black_material} "
			Acusticator(["g#5", 0.03, 0, volume,"e5", 0.03, 0, volume,"d5", 0.03, 0, volume,"g6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "u":
			custom_board_view = CustomBoard(current_node.board().fen())
			if len(current_node.board().move_stack) > 0: custom_board_view.move_stack = current_node.board().move_stack
			custom_board_view.turn = current_node.board().turn; custom_board_view.fullmove_number = current_node.board().fullmove_number
			print("\n" + str(custom_board_view)); Acusticator(["d6", 0.03, 0, volume,"f6", 0.03, 0, volume,"g6", 0.03, 0, volume,"d7", 0.06, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "i":
			print(f"\nTempo analisi: {analysis_time}s. Cache: {len(cache_analysis)} posizioni.")
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_time_input = dgt("\nNuovo tempo (secondi) o INVIO: ", kind="f", fmin=0.1, fmax=300, default=analysis_time)
			if new_time_input != analysis_time: SetAnalysisTime(new_time_input); print("\nTempo di analisi aggiornato."); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print("\nTempo di analisi non modificato.")
		elif cmd == "o":
			print(f"\nLinee analisi: {multipv}. Cache: {len(cache_analysis)} posizioni.")
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_lines = dgt("Nuovo numero linee o INVIO: ", kind="i",imin=1,imax=10, default=multipv)
			if new_lines != multipv: SetMultipv(new_lines); print("\nNumero di linee aggiornato."); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print("\nNumero di linee non modificato.")
		elif cmd == "?":
			print("\nComandi disponibili in modalità analisi:"); menu(ANALYSIS_COMMAND,show_only=True)
			Acusticator(["d5", .7, 0, volume], kind=3, adsr=[.02,0,100,99])
		else: # Comando non riconosciuto
			Acusticator(["d3", 1.2, 0, volume], kind=3, adsr=[.02,0,100,99])
			print("Comando non riconosciuto.")
			node_changed = False # Assicura che non venga stampata descrizione

		# --- 4. Stampa Descrizione se Nodo Cambiato ---
		if node_changed and current_node.move:
			annotation_suffix = None
			for nag_value, suffix in NAG_REVERSE_MAP.items():
				if nag_value in current_node.nags:
					annotation_suffix = suffix
					break
			# Stampa la descrizione della mossa *su cui siamo arrivati*
			print("\n" + DescribeMove(current_node.move,
									   current_node.parent.board() if current_node.parent else pgn_game.board(),
									   annotation=annotation_suffix))
	print("\nFine analisi")
	annotator_updated_flag = False
	if saved:
		new_annotator = f'Orologic V{VERSION} by {PROGRAMMER}'
		current_annotator = pgn_game.headers.get("Annotator", "")
		if current_annotator != new_annotator:
			pgn_game.headers["Annotator"] = new_annotator
			annotator_updated_flag = True
			print("\nAnnotator aggiornato.")
	pgn_string_raw = ""
	try:
		pgn_string_raw = str(pgn_game)
		if not pgn_string_raw:
			print("!!!!!!!! ATTENZIONE: str(pgn_game) ha restituito una stringa vuota! !!!!!!!!")
	except Exception as e_str_export:
		print(f"!!!!!!!! DEBUG: ECCEZIONE durante str(pgn_game): {repr(e_str_export)} !!!!!!!!")
		pgn_string_raw = ""
	pgn_string_formatted = ""
	exception_occurred_format = False
	if pgn_string_raw and isinstance(pgn_string_raw, str):
		try:
			pgn_string_formatted = format_pgn_comments(pgn_string_raw)
		except Exception as e_format:
			exception_occurred_format = True
			print(f"!!!!!!!! DEBUG: ECCEZIONE DURANTE format_pgn_comments: {repr(e_format)} !!!!!!!!")
			pgn_string_formatted = ""
	else:
		print("Attenzione: Stringa PGN grezza vuota o non valida, formattazione saltata.")
	print(f"DEBUG: Eccezione durante format? {exception_occurred_format}")
	if saved:
		if pgn_string_formatted:
			white_h = pgn_game.headers.get("White", "Bianco").replace(" ", "_")
			black_h = pgn_game.headers.get("Black", "Nero").replace(" ", "_")
			result_h = pgn_game.headers.get("Result", "*").replace("/", "-")
			new_default_file_name=f'{white_h}_vs_{black_h}_{result_h}'
			base_name = dgt(f"\nSalva PGN modificato.\nNome base (INVIO per '{new_default_file_name}'): ", kind="s",default=new_default_file_name).strip()
			if not base_name: base_name = new_default_file_name
			Acusticator(["f4", 0.05, 0, volume])
			new_filename_base = f"{base_name}-analizzato-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
			new_filename = sanitize_filename(new_filename_base) + ".pgn"
			try:
				with open(new_filename, "w", encoding="utf-8-sig") as f:
					f.write(pgn_string_formatted)
				print("PGN aggiornato salvato come " + new_filename)
				if annotator_updated_flag: print("Header Annotator è stato aggiornato nel file.")
			except Exception as e_save:
				print(f"Errore durante il salvataggio del PGN: {e_save}")
		else:
			print("Impossibile salvare il file PGN a causa di errori durante la generazione/formattazione.")
	else:
		print("\nNon sono state apportate modifiche salvabili al PGN.")
	if pgn_string_formatted:
		try:
			pyperclip.copy(pgn_string_formatted)
			print("PGN attuale (formattato) copiato negli appunti.")
		except Exception as e_clip:
			print(f"Errore durante la copia del PGN (formattato) negli appunti: {e_clip}")
	else:
		print("Nessun PGN formattato da copiare negli appunti.")
	print("Uscita dalla modalità analisi. Ritorno al menù principale.")

def get_color_adjective(piece_color, gender):
	# NUOVA LOGICA: Cerca le forme maschili/femminili degli aggettivi in L10N
	white_adj = L10N['adjectives']['white']
	black_adj = L10N['adjectives']['black']
	
	if piece_color == chess.WHITE:
		# Se il genere è 'f', usa la forma femminile, altrimenti usa la maschile (anche per neutro 'n')
		return white_adj.get('f') if gender == 'f' else white_adj.get('m')
	else:
		return black_adj.get('f') if gender == 'f' else black_adj.get('m')

def extended_piece_description(piece):
	# NUOVA LOGICA: Cerca il nome del pezzo e il suo genere in L10N
	piece_type_key = chess.PIECE_NAMES[piece.piece_type].lower() # es. 'pawn', 'knight'
	piece_info = L10N['pieces'][piece_type_key]
	piece_name = piece_info['name'].capitalize()
	piece_gender = piece_info['gender']
	
	color_adj = get_color_adjective(piece.color, piece_gender)
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
	# NUOVA LOGICA
	base_descr = f"{L10N['columns'].get(base_column, base_column)} 1"
	while 0 <= file_index < 8 and 0 <= rank_index < 8:
		square = chess.square(file_index, rank_index)
		piece = game_state.board.piece_at(square)
		if piece:
			current_file = chr(ord("a") + file_index)
			# NUOVA LOGICA
			descriptive_file = L10N['columns'].get(current_file, current_file)
			report.append(f"{descriptive_file} {rank_index+1}: {extended_piece_description(piece)}")
		rank_index += 1
		file_index = file_index + 1 if direction_right else file_index - 1
	dir_str = "alto-destra" if direction_right else "alto-sinistra"
	if report:
		print(f"Diagonale da {base_descr} in direzione {dir_str}: " + ", ".join(report))
	else:
		print(f"Diagonale da {base_descr} in direzione {dir_str} non contiene pezzi.")

def read_rank(game_state, rank_number):
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
			# NUOVA LOGICA
			descriptive_file = L10N['columns'].get(file_letter, file_letter)
			report.append(f"{descriptive_file} {rank_number}: {extended_piece_description(piece)}")
	if report:
		print(f"Traversa {rank_number}: " + ", ".join(report))
	else:
		print(f"La traversa {rank_number} è vuota.")

def read_file(game_state, file_letter):
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
			# NUOVA LOGICA
			file_letter_descr = L10N['columns'].get(chr(ord("a") + file_index), file_letter)
			report.append(f"{file_letter_descr} {rank}: {extended_piece_description(piece)}")
	# NUOVA LOGICA
	col_name = L10N['columns'].get(file_letter, file_letter)
	if report:
		print(f"Colonna {col_name}: " + ", ".join(report))
	else:
		print(f"La colonna {col_name} è vuota.")

def _get_piece_descriptions_from_squareset(board, squareset):
	"""
	Funzione helper interna.
	Dato un insieme di case, restituisce una lista di descrizioni complete
	per ogni pezzo che si trova su quelle case.
	Es: ["Cavallo bianco in Firenze 3", "Donna nera in Domodossola 8"]
	"""
	descriptions = []
	for sq in squareset:
		piece = board.piece_at(sq)
		if piece:
			# Riutilizza la nostra funzione esistente per descrivere il pezzo
			piece_desc = extended_piece_description(piece)
			
			# Riutilizza L10N per descrivere la casa
			sq_name = chess.square_name(sq)
			col_name = L10N['columns'].get(sq_name[0].lower(), sq_name[0])
			rank_name = sq_name[1]
			
			descriptions.append(f"{piece_desc} in {col_name} {rank_name}")
	return descriptions

def read_square(game_state, square_str):
	"""
	Fornisce una descrizione dettagliata di una casa, elencando i pezzi
	che la occupano, la difendono o la attaccano.
	"""
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print("Casa non valida.")
		return
	# La logica per il colore della casa rimane invariata
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = "scura"
	else:
		color_descr = "chiara"
	piece = game_state.board.piece_at(square)
	
	final_parts = []
	if piece:
		# --- Logica per casa occupata ---
		base_msg = f"La casa {square_str.upper()} è {color_descr} e contiene {extended_piece_description(piece)}."
		final_parts.append(base_msg)
		defenders_squares = game_state.board.attackers(piece.color, square)
		if defenders_squares:
			defender_descs = _get_piece_descriptions_from_squareset(game_state.board, defenders_squares)
			final_parts.append(f"difesa da: {', '.join(defender_descs)}")
		attackers_squares = game_state.board.attackers(not piece.color, square)
		if attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, attackers_squares)
			final_parts.append(f"attaccata da: {', '.join(attacker_descs)}")
	else:
		# --- Logica per casa vuota ---
		base_msg = f"La casa {square_str.upper()} è {color_descr} e risulta vuota."
		final_parts.append(base_msg)
		white_attackers_squares = game_state.board.attackers(chess.WHITE, square)
		if white_attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, white_attackers_squares)
			final_parts.append(f"attaccata dal Bianco con: {', '.join(attacker_descs)}")
		black_attackers_squares = game_state.board.attackers(chess.BLACK, square)
		if black_attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, black_attackers_squares)
			final_parts.append(f"attaccata dal Nero con: {', '.join(attacker_descs)}")
	# Assembla la frase finale
	print(" ".join(final_parts).replace(" .", ".").strip() + ".")

def report_piece_positions(game_state, piece_symbol):
	try:
		piece = chess.Piece.from_symbol(piece_symbol)
	except Exception as e:
		print("Non riconosciuto: inserisci R N B Q K P, r n b q k p")
		return
	piece_type_key = chess.PIECE_NAMES[piece.piece_type].lower()
	full_name = L10N['pieces'][piece_type_key]['name']
	gender = L10N['pieces'][piece_type_key]['gender']
	color_string = get_color_adjective(piece.color, gender)
	squares = game_state.board.pieces(piece.piece_type, piece.color)
	positions = []
	for square in squares:
		file_index = chess.square_file(square)
		rank = chess.square_rank(square) + 1
		file_letter = chr(ord("a") + file_index)
		# NUOVA LOGICA: Usa L10N per i nomi delle colonne
		descriptive_file = L10N['columns'].get(file_letter, file_letter)
		positions.append(f"{descriptive_file} {rank}")
	if positions:
		print(f"{color_string.capitalize()}: {full_name} in: " + ", ".join(positions))
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

def save_text_summary(game_state, descriptive_moves, eco_entry):
	"""
	Genera e salva un riepilogo testuale della partita.
	"""
	headers = game_state.pgn_game.headers
	# 1. Intestazioni (Headers) leggibili
	header_text = f"Riepilogo Partita di Orologic\n"
	header_text += "--------------------------------\n"
	header_text += f"Evento: {headers.get('Event', 'N/D')}\n"
	header_text += f"Sede: {headers.get('Site', 'N/D')}\n"
	header_text += f"Data: {headers.get('Date', 'N/D')}\n"
	header_text += f"Round: {headers.get('Round', 'N/D')}\n"
	header_text += f"Bianco: {headers.get('White', 'N/D')} ({headers.get('WhiteElo', 'N/A')})\n"
	header_text += f"Nero: {headers.get('Black', 'N/D')} ({headers.get('BlackElo', 'N/A')})\n"
	header_text += f"Controllo del Tempo: {headers.get('TimeControl', 'N/D')}\n"
	# 2. Informazioni sull'apertura
	if eco_entry:
		opening_text = f"Apertura: {eco_entry.get('eco', '')} - {eco_entry.get('opening', '')}"
		if eco_entry.get('variation'):
			opening_text += f" ({eco_entry.get('variation')})\n"
		else:
			opening_text += "\n"
	else:
		opening_text = "Apertura: non rilevata\n"
	header_text += opening_text
	header_text += "--------------------------------\n\n"
	# 3. Lista delle mosse
	move_list_text = "Lista Mosse:\n"
	move_number = 1
	i = 0
	while i < len(descriptive_moves):
		white_move_desc = descriptive_moves[i]
		if i + 1 < len(descriptive_moves):
			black_move_desc = descriptive_moves[i+1]
			move_list_text += f"{move_number}. {white_move_desc}, {black_move_desc}\n"
			i += 2
		else:
			move_list_text += f"{move_number}. {white_move_desc}\n"
			i += 1
		move_number += 1
	# 4. Risultato e data di generazione
	footer_text = f"\nRisultato finale: {headers.get('Result', '*')}\n"
	footer_text += "--------------------------------\n"
	footer_text += f"File generato il: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
	footer_text += f"Report generato da Orologic V{VERSION} - {PROGRAMMER}\n"
	# Combinazione di tutte le parti
	full_text = header_text + move_list_text + footer_text
	# Creazione del nome del file (riutilizzando la logica del PGN)
	base_filename = f"{headers.get('White', 'Bianco')}-{headers.get('Black', 'Nero')}-{headers.get('Result', '*')}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
	filename = sanitize_filename(base_filename) + ".txt"
	# Salvataggio su file
	try:
		with open(filename, "w", encoding="utf-8") as f:
			f.write(full_text)
		print(f"Riepilogo partita salvato come {filename}.")
	except Exception as e:
		print(f"Errore durante il salvataggio del riepilogo testuale: {e}")
		Acusticator(["a3", 1, 0, volume], kind=2, adsr=[0, 0, 100, 100])

def setup_fischer_random_board():
	"""
	Gestisce il processo di setup per una partita Fischer Random (Chess960).
	L'utente può inserire una sequenza, richiederne una casuale ('?'), o annullare ('.').
	Restituisce (None, None) se l'utente annulla.
	"""
	print("\n--- Configurazione Fischer Random (Chess960) ---")
	
	while True:
		prompt = "\nInserisci la sequenza di 8 pezzi, '?' per una casuale, o '.' per annullare: "
		user_input = dgt(prompt, kind="s").upper()
		if user_input == '?':
			# --- NUOVA LOGICA PER LA POSIZIONE CASUALE ---
			pos_number = random.randint(0, 959)
			print(f"Generazione posizione casuale numero {pos_number}...")
			# Crea la scacchiera direttamente dal numero di posizione 960
			board_to_return = CustomBoard.from_chess960_pos(pos_number)
			starting_fen = board_to_return.fen()
			# Ricaviamo la sequenza dei pezzi per mostrarla all'utente
			piece_sequence = ""
			for i in range(8):
				piece = board_to_return.piece_at(i)
				if piece:
					piece_sequence += piece.symbol().upper()
			Acusticator(["c5", 0.1, -0.8, volume, "e5", 0.1, 0, volume, "g5", 0.2, 0.8, volume], kind=1, adsr=[2, 8, 90, 0])
			print(f"Posizione generata: {piece_sequence} (Numero: {pos_number})")
			return board_to_return, starting_fen
		elif user_input == '.':
			print("Configurazione annullata.")
			return None, None
		elif len(user_input) != 8:
			print(f"Errore: la sequenza deve contenere 8 caratteri. Tu ne hai inseriti {len(user_input)}.")
			Acusticator(["b3", .2, 0, volume], kind=2)
			continue
		# La logica per l'input manuale rimane la stessa
		else:
			fen_to_try = f"{user_input.lower()}/pppppppp/8/8/8/8/PPPPPPPP/{user_input} w - - 0 1"
			try:
				board_to_return = CustomBoard(fen_to_try, chess960=True)
				pos_number = board_to_return.chess960_pos()
				Acusticator(["c5", 0.1, -0.8, volume, "e5", 0.1, 0, volume, "g5", 0.2, 0.8, volume], kind=1, adsr=[2, 8, 90, 0])
				print(f"Posizione valida! Numero di riferimento Chess960: {pos_number}")
				return board_to_return, fen_to_try
			except ValueError as e:
				print(f"Errore: Posizione non valida. La libreria riporta: '{e}'")
				Acusticator(["a3", .3, 0, volume], kind=2, adsr=[5, 15, 0, 80])
				continue

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
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		if moves == 0:
			# Sudden death: se è presente l'incremento, lo includiamo
			if inc > 0:
				tc = f"{base_time}+{inc}"
			else:
				tc = f"{base_time}"
		else:
			# Time control a mosse: includiamo moves, tempo e, se presente, l'incremento
			if inc > 0:
				tc = f"{moves}/{base_time}+{inc}"
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

def DescribeMove(move, board, annotation=None):
	if board.is_castling(move):
		base_descr = L10N['moves']['short_castle'] if chess.square_file(move.to_square) > chess.square_file(move.from_square) else L10N['moves']['long_castle']
	else:
		san_base = ""
		try:
			# La logica per ricavare il SAN base rimane invariata
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
			if piece_symbol:
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
						disambiguation = from_sq_str[0]
					else:
						rank_disamb_needed = False
						for sq in potential_origins:
							if sq != move.from_square and chess.square_rank(sq) == chess.square_rank(move.from_square):
								rank_disamb_needed = True
								break
						if not rank_disamb_needed:
							disambiguation = from_sq_str[1]
						else:
							disambiguation = from_sq_str
			promo_str = ""
			if is_promo:
				promo_piece_symbol = chess.piece_symbol(move.promotion).upper()
				promo_str = f"={promo_piece_symbol}"
			capture_char = "x" if is_capture else ""
			if piece_symbol:
				san_base = f"{piece_symbol}{disambiguation}{capture_char}{to_sq_str}{promo_str}"
			else:
				if is_capture:
					san_base = f"{from_sq_str[0]}{capture_char}{to_sq_str}{promo_str}"
				else:
					san_base = f"{to_sq_str}{promo_str}"
		except Exception as e:
			try:
				san_base = board.san(move)
				san_base = san_base.replace("!","").replace("?","")
			except Exception:
				san_base = f"Mossa da {chess.square_name(move.from_square)} a {chess.square_name(move.to_square)}"
		
		# La logica di parsing del SAN rimane la stessa
		pattern = re.compile(r'^([RNBQK])?([a-h1-8]{1,2})?(x)?([a-h][1-8])(=([RNBQ]))?$')
		pawn_pattern = re.compile(r'^([a-h])?(x)?([a-h][1-8])(=([RNBQ]))?$')
		m = pattern.match(san_base)
		if m and m.group(1):
			piece_letter = m.group(1)
			disamb = m.group(2) or ""
			capture = m.group(3)
			dest = m.group(4)
			promo_letter = m.group(6)
			piece_type = chess.PIECE_SYMBOLS.index(piece_letter.lower())
		else:
			m = pawn_pattern.match(san_base)
			if m:
				piece_letter = ""
				disamb = m.group(1) or ""
				capture = m.group(2)
				dest = m.group(3)
				promo_letter = m.group(5)
				piece_type = chess.PAWN
			else:
				base_descr = san_base
				piece_type = None

		if piece_type is not None:
			# NUOVA LOGICA: Costruzione della descrizione usando L10N
			piece_type_key = chess.PIECE_NAMES[piece_type].lower()
			piece_name = L10N['pieces'][piece_type_key]['name']
			descr = piece_name
			if disamb:
				if piece_type == chess.PAWN:
					descr += f" {L10N['columns'].get(disamb, disamb)}"
				else:
					parts = [L10N['columns'].get(ch, ch) if ch.isalpha() else ch for ch in disamb]
					descr += " di " + "".join(parts) # "di" potrebbe essere localizzato, ma è un caso più complesso
			if capture:
				descr += f" {L10N['moves']['capture']}"
				captured_piece = None
				if board.is_en_passant(move):
					ep_square = move.to_square + (-8 if board.turn == chess.WHITE else 8)
					captured_piece = board.piece_at(ep_square)
					descr += f" {L10N['moves']['en_passant']}"
				else:
					captured_piece = board.piece_at(move.to_square)
				if captured_piece and not board.is_en_passant(move):
					captured_type_key = chess.PIECE_NAMES[captured_piece.piece_type].lower()
					captured_name = L10N['pieces'][captured_type_key]['name']
					descr += f" {captured_name}"
				dest_file_info = dest[0]
				dest_rank_info = dest[1]
				dest_name_info = L10N['columns'].get(dest_file_info, dest_file_info)
				descr += f" {L10N['moves']['capture_on']} {dest_name_info}{dest_rank_info}"
			else:
				dest_file = dest[0]
				dest_rank = dest[1]
				dest_name = L10N['columns'].get(dest_file, dest_file)
				descr += f" {L10N['moves']['move_to']} {dest_name}{dest_rank}"
			if promo_letter:
				promo_type = chess.PIECE_SYMBOLS.index(promo_letter.lower())
				promo_type_key = chess.PIECE_NAMES[promo_type].lower()
				promo_name = L10N['pieces'][promo_type_key]['name']
				descr += f" {L10N['moves']['promotes_to']} {promo_name}"
			base_descr = descr
	
	board_after_move = board.copy()
	board_after_move.push(move)
	final_descr = base_descr
	if board_after_move.is_checkmate():
		final_descr += f" {L10N['moves']['checkmate']}"
	elif board_after_move.is_check():
		final_descr += f" {L10N['moves']['check']}"
	
	# NUOVA LOGICA: Usa L10N per le annotazioni
	if annotation and annotation in L10N['annotations']:
		final_descr += f" ({L10N['annotations'][annotation]})"
		
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

def get_default_localization():
	"""
	Restituisce un dizionario con tutte le stringhe di default in italiano.
	"""
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

def LoadLocalization():
	"""
	Carica le impostazioni di localizzazione dal DB.
	Se non esistono o sono incomplete, crea i default italiani e li salva.
	"""
	global L10N
	db = LoadDB()
	
	# CONTROLLO MIGLIORATO:
	# Controlla non solo se 'localization' esiste, ma anche se non è vuota o corrotta
	# (verificando la presenza di una sotto-chiave fondamentale come 'pieces').
	if "localization" not in db or not db["localization"].get("pieces"):
		print("Configurazione lingua non trovata o incompleta, imposto la localizzazione italiana di default.")
		db["localization"] = get_default_localization()
		SaveDB(db)
	
	L10N = db["localization"]

def LoadEcoDatabaseWithFEN(filename="eco.db"):
	"""
	Carica il file ECO, calcola il FEN finale per ogni linea
	e restituisce una lista di dizionari contenenti:
	"eco", "opening", "variation", "moves" (lista SAN),
	"fen" (FEN della posizione finale), "ply" (numero di semimosse).
	Utilizza node.board().san() per una generazione SAN più robusta.
	"""
	eco_entries = []
	if not os.path.exists(filename):
		print(f"File {filename} non trovato.")
		return eco_entries
	try:
		with open(filename, "r", encoding="utf-8") as f:
			content = f.read()
	except Exception as e:
		print(f"Errore durante la lettura di {filename}: {e}")
		return eco_entries
	# Rimuovi eventuali blocchi di commento racchiusi tra { e }
	content = re.sub(r'\{[^}]*\}', '', content, flags=re.DOTALL)
	stream = io.StringIO(content)
	game_count = 0
	skipped_count = 0
	while True:
		# Salva la posizione corrente dello stream per il seek
		stream_pos = stream.tell()
		try:
			headers = chess.pgn.read_headers(stream)
			if headers is None:
				break # Fine del file o stream

			# Riposizionati e leggi il game completo
			stream.seek(stream_pos) # Torna all'inizio degli header
			game = chess.pgn.read_game(stream)
			game_count += 1

			if game is None:
				# Potrebbe accadere con entry PGN malformate dopo gli header
				print(f"Attenzione: Impossibile leggere il game PGN {game_count} dopo l'header.")
				skipped_count += 1
				# Prova a leggere la prossima entry saltando righe vuote
				while True:
					line = stream.readline()
					if line is None: break # EOF
					if line.strip(): # Trovata una riga non vuota
						stream.seek(stream.tell() - len(line.encode('utf-8'))) # Torna indietro per leggerla come header la prossima volta
						break
				continue

			eco_code = game.headers.get("ECO", "")
			opening = game.headers.get("Opening", "")
			variation = game.headers.get("Variation", "")
			moves = []
			node = game
			last_valid_node = game # Traccia l'ultimo nodo valido per ottenere il FEN finale
			parse_error = False

			while node.variations:
				next_node = node.variations[0]
				move = next_node.move
				try:
					# Usa la board del NODO CORRENTE per generare il SAN della PROSSIMA mossa
					# Questo è generalmente più affidabile
					san = node.board().san(move)
					moves.append(san)
				except Exception as e:
					parse_error = True
					break # Interrompi il parsing di questa linea ECO
				node = next_node
				last_valid_node = node # Aggiorna l'ultimo nodo processato con successo

			if not parse_error and moves: # Solo se abbiamo mosse valide e nessun errore
				# Ottieni il FEN dalla board dell'ULTIMO nodo valido raggiunto
				final_fen = last_valid_node.board().board_fen()
				ply_count = len(moves) # Numero di semimosse
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

		except ValueError as ve: # Cattura specificamente errori comuni di parsing PGN
			print(f"Errore di valore durante il parsing del game PGN {game_count}: {ve}")
			skipped_count += 1
			# Prova a recuperare cercando la prossima entry PGN '['
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['): # Trovato un possibile inizio di header
					stream.seek(stream.tell() - len(line.encode('utf-8'))) # Torna indietro
					break
		except Exception as e:
			print(f"Errore generico durante il parsing del game PGN {game_count}: {e}")
			skipped_count += 1
			# Tentativo di recupero simile a sopra
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['):
					stream.seek(stream.tell() - len(line.encode('utf-8')))
					break

	print(f"Caricate {len(eco_entries)} linee di apertura ECO.")
	if skipped_count > 0:
		print(f"Attenzione: {skipped_count} linee ECO sono state saltate a causa di errori di parsing.")
	return eco_entries
def DetectOpeningByFEN(current_board, eco_db_with_fen):
	"""
	restituisce l'entry dell'apertura corrispondente alla posizione attuale.
	Gestisce le trasposizioni confrontando i FEN delle posizioni.
	Se ci sono più match, preferisce quello con lo stesso numero di mosse (ply),
	e tra questi, quello con la sequenza di mosse più lunga nel database ECO.
	"""
	current_fen = current_board.board_fen()
	current_ply = current_board.ply()
	possible_matches = []
	for entry in eco_db_with_fen:
		if entry["fen"] == current_fen:
			possible_matches.append(entry)
	if not possible_matches:
		return None # Nessuna corrispondenza trovata per questa posizione
	# Filtra per numero di mosse (ply) corrispondente, se possibile
	exact_ply_matches = [m for m in possible_matches if m["ply"] == current_ply]
	if exact_ply_matches:
		# Se ci sono match con lo stesso numero di mosse, scegli il più specifico
		# (quello definito con più mosse nel db ECO, anche se dovrebbero essere uguali se ply è uguale)
		return max(exact_ply_matches, key=lambda x: len(x["moves"]))
	else:
		return None # Nessun match trovato con il numero di mosse corretto
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
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume],sync=True)
	db=LoadDB()
	if any(c["name"]==name for c in db["clocks"]):
		print("Un orologio con questo nome esiste già.")
		Acusticator(["a3",1,0,volume],kind=2,adsr=[0,0,100,100])
		return
	same=dgt("Bianco e Nero partono con lo stesso tempo? (Invio per sì, 'n' per no): ",kind="s",smin=0,smax=1)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(f"Tempo (hh:mm:ss) per fase {phase_count+1}: ")
			inc=dgt(f"Incremento in secondi per fase {phase_count+1}: ",kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(f"Tempo per il bianco (hh:mm:ss) fase {phase_count+1}: ")
			inc_w=dgt(f"Incremento per il bianco fase {phase_count+1}: ",kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			total_seconds_b=ParseTime(f"Tempo per il nero (hh:mm:ss) fase {phase_count+1}: ")
			inc_b=dgt(f"Incremento per il nero fase {phase_count+1}: ",kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(f"Numero di mosse per fase {phase_count+1} (0 per terminare): ",kind="i")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt("Numero di allarmi da inserire (max 5, 0 per nessuno): ",kind="i",imax=5,default=0)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	for i in range(num_alarms):
		alarm_input = dgt(f"Inserisci il tempo (mm:ss) per l'allarme {i+1}: ", kind="s")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt("Inserisci una nota per l'orologio (opzionale): ",kind="s",default="")
	Acusticator(["f7", .09, 0, volume,"d5", .07, 0, volume,"p",.1,0,0,"d5", .07, 0, volume,"f7", .09, 0, volume])
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
	Acusticator(["c5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
	attesa=key("Premi un tasto per tornare al menu principale.")
	Acusticator(["a4", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
def SelectClock(db):
	db = LoadDB()
	if not db["clocks"]:
		Acusticator(["c3", 0.72, 0, volume], kind=2, adsr=[0,0,100,100])
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
	Acusticator(["f7", .013, 0, volume])
	if choice:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == choice), None)
		if idx is not None:
			return db["clocks"][idx]
	else:
		print("Nessun orologio selezionato.")
def DeleteClock(db):
	print("\nEliminazione orologi salvati\n")
	Acusticator(["b4", .02, 0, volume,"d4",.2,0,volume]) 
	orologio = SelectClock(db)
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			del db["clocks"][idx]
			Acusticator(["c4", 0.025, 0, volume])
			SaveDB(db)
			print(f"\nOrologio '{clock_name}' eliminato, ne rimangono {len(db['clocks'])}.")
	return
def EditPGN():
	Acusticator(["d6", .02, 0, volume,"g4",.02,0,volume]) 
	print("\nModifica info default per PGN\n")
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	default_event = default_pgn.get("Event", "Orologic Game")
	event = dgt(f"Evento [{default_event}]: ", kind="s", default=default_event)
	Acusticator(["d6", .02, -1, volume,"g4",.02,-1,volume]) 
	if event.strip() == "":
		event = default_event
	default_site = default_pgn.get("Site", "Sede sconosciuta")
	site = dgt(f"Sede [{default_site}]: ", kind="s", default=default_site)
	Acusticator(["d6", .02, -.66, volume,"g4",.02,-.66,volume]) 
	if site.strip() == "":
		site = default_site
	default_round = default_pgn.get("Round", "Round 1")
	round_ = dgt(f"Round [{default_round}]: ", kind="s", default=default_round)
	Acusticator(["d6", .02, -.33, volume,"g4",.02,-.33,volume]) 
	if round_.strip() == "":
		round_ = default_round
	default_white = default_pgn.get("White", "Bianco")
	white = dgt(f"Nome del Bianco [{default_white}]: ", kind="s", default=default_white).strip().title()
	Acusticator(["d6", .02, 0, volume,"g4",.02,0,volume]) 
	if white.strip() == "":
		white = default_white
	default_black = default_pgn.get("Black", "Nero")
	black = dgt(f"Nome del Nero [{default_black}]: ", kind="s", default=default_black).strip().title()
	Acusticator(["d6", .02, .33, volume,"g4",.02,.33,volume]) 
	if black.strip() == "":
		black = default_black
	default_white_elo = default_pgn.get("WhiteElo", "1200")
	white_elo = dgt(f"Elo del Bianco [{default_white_elo}]: ", kind="s", default=default_white_elo)
	Acusticator(["d6", .02, .66, volume,"g4",.02,.66,volume]) 
	if white_elo.strip() == "":
		white_elo = default_white_elo
	default_black_elo = default_pgn.get("BlackElo", "1200")
	black_elo = dgt(f"Elo del Nero [{default_black_elo}]: ", kind="s", default=default_black_elo)
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
		self.descriptive_move_history = []
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
						print(f"\nAllarme: tempo del bianco raggiunto {seconds_to_mmss(alarm)}",end="")
						Acusticator(["c4",0.2,-0.75,volume])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(f"\nAllarme: tempo del nero raggiunto {seconds_to_mmss(alarm)}",end="")
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
	game_mode_choice = ''
	while game_mode_choice not in ['s', 'f']:
		game_mode_choice = key("Scegli la modalità: [S]tandard o [F]ischer Random 960? (S/F) ").lower()
	Acusticator(["c4", 0.05, 0, volume, "e4", 0.05, 0, volume, "g4", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	is_fischer_random = (game_mode_choice == 'f')
	starting_board = None
	starting_fen = None
	if is_fischer_random:
		starting_board, starting_fen = setup_fischer_random_board()
		if starting_board is None: # L'utente ha annullato
			return # Esce dalla funzione StartGame e torna al menù
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", "Bianco")
	black_default = default_pgn.get("Black", "Nero")
	white_elo_default = default_pgn.get("WhiteElo", "1500")
	black_elo_default = default_pgn.get("BlackElo", "1500")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", "Sede sconosciuta")
	round_default = default_pgn.get("Round", "Round 1")
	eco_database = LoadEcoDatabaseWithFEN("eco.db")
	last_eco_msg = ""
	last_valid_eco_entry = None
	white_player = dgt(f"Nome del bianco [{white_default}]: ", kind="s", default=white_default).strip().title()
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_player == "":
		white_player = white_default
	black_player = dgt(f"Nome del nero [{black_default}]: ", kind="s", default=black_default).strip().title()
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_player == "":
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
	key("Premi un tasto qualsiasi per iniziare la partita quando sei pronto...",attesa=7200)
	Acusticator(["c6", .07, 0, volume, "p", .93, 0, .5, "c6", .07, 0, volume, "p", .93, 0, .5, "c6", .07, 0, volume, "p", .93, 0, .5, "c7", .5, 0, volume], kind=1, sync=True)
	game_state=GameState(clock_config)
	if is_fischer_random:
		game_state.board = starting_board
		game_state.pgn_game.headers["Variant"] = "Chess960"
		game_state.pgn_game.headers["FEN"] = starting_fen
		game_state.pgn_game.setup(game_state.board) # Sincronizza il PGN con la scacchiera custom
	# Se la partita è standard, non c'è bisogno di fare nulla, game_state si inizializza già correttamente.
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
			prompt="\nInizio, mossa 0. "
		elif len(game_state.move_history)%2==1:
			full_move=(len(game_state.move_history)+1)//2
			prompt=f"{full_move}. {game_state.move_history[-1]} "
		else:
			full_move=(len(game_state.move_history))//2
			prompt=f"{full_move}... {game_state.move_history[-1]} "
		if game_state.paused:
			prompt="["+prompt.strip()+"] "
		user_input=dgt(prompt,kind="s")
		# --- Gestione comandi speciali ---
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
					print("Traversa non valida.")
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				Acusticator(["d#4", .7, 0, volume], kind=1, adsr=[0, 0, 100, 100])
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
				Acusticator([440.0, 0.3, 0, 0.5, 880.0, 0.3, 0, 0.5], kind=1, adsr=[10, 0, 100, 20])
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
				Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
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
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
					undone_move_san = game_state.move_history.pop()
					game_state.board.pop()
					# Aggiorna il PGN: riportiamo il puntatore al nodo padre
					current_node = game_state.pgn_node
					parent = current_node.parent
					if current_node in parent.variations:
						parent.variations.remove(current_node)
					game_state.pgn_node = parent
					# Salva la mossa annullata (in formato SAN) in una lista
					if not hasattr(game_state, "cancelled_san_moves"):
						game_state.cancelled_san_moves = []
					game_state.cancelled_san_moves.insert(0, undone_move_san)
					# Rollback dell'incremento applicato (rimuove solo l'incremento)
					if game_state.active_color == "black":
						game_state.white_remaining -= game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
						game_state.active_color = "white"
					else:
						game_state.black_remaining -= game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
						game_state.active_color = "black"
					print("Ultima mossa annullata: " + undone_move_san)
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
						elif cmd.startswith(".n+"):
							Acusticator(["d4", 0.15, .5, volume, "f4", 0.15, .5, volume, "a4", 0.15, .5, volume, "c5", 0.15, .5, volume], kind=1, adsr=[15, 0, 90, 5])
							game_state.black_remaining+=adjust
						elif cmd.startswith(".n-"):
							Acusticator(["c5", 0.15, .5, volume, "a4", 0.15, .5, volume, "f4", 0.15, .5, volume, "d4", 0.15, .5, volume], kind=1, adsr=[15, 0, 90, 5])
							game_state.black_remaining-=adjust
						print("Nuovo tempo bianco: "+FormatTime(game_state.white_remaining)+", nero: "+FormatTime(game_state.black_remaining))
					except:
						print("Comando non valido.")
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, volume, "g4", 0.2, -0.3, volume, "c5", 0.2, 0.3, volume, "e5", 0.2, 1, volume, "g5", 0.4, 0, volume], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				Acusticator([900.0, 0.1, 0, volume, 440.0, 0.3, 0, volume], kind=1, adsr=[1, 0, 80, 19])
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
					Acusticator(["f5", 0.1, 0, volume,"p",0.04,0,0,"c5", 0.02, 0, volume], kind=1, adsr=[3,7,88,2])
					print("Commento registrato per la mossa: " + game_state.move_history[-1])
				else:
					print("Nessuna mossa da commentare.")
			else:
				Acusticator(["e3", 1, 0, volume,"a2", 1, 0, volume], kind=3, adsr=[1,7,100,92])
				print("Comando non riconosciuto.")
		# --- Gestione mosse ---
		else:
			if game_state.paused:
				print("Non è possibile inserire nuove mosse mentre il tempo è in pausa. Riavvia il tempo con .p")
				Acusticator(["b3",.2,0,volume],kind=2)
				continue

			# --- INIZIO MODIFICA ---
			raw_input = NormalizeMove(user_input) # Normalizza prima di cercare il suffisso
			annotation_suffix = None
			move_san_only = raw_input # Default: input è solo la mossa

			# Cerca un suffisso di annotazione
			match = ANNOTATION_SUFFIX_PATTERN.search(raw_input)
			if match:
				annotation_suffix = match.group(1)
				move_san_only = raw_input[:-len(annotation_suffix)].strip() # Rimuovi suffisso e spazi extra

			# Prova a parsare solo la parte della mossa
			try:
				move = game_state.board.parse_san(move_san_only)
				# --- FINE MODIFICA ---

				board_copy=game_state.board.copy()
				# --- MODIFICA: Passa l'annotazione a DescribeMove ---
				description=DescribeMove(move, board_copy, annotation=annotation_suffix)
				game_state.descriptive_move_history.append(description)
				Acusticator([1000.0, 0.01, 0, volume], kind=1, adsr=[0, 0, 100, 0])
				if game_state.active_color=="white":
					print(game_state.white_player+": "+description)
				else:
					print(game_state.black_player+": "+description)

				# Ottieni la SAN base per la history (senza suffissi)
				san_move_base = game_state.board.san(move)
				# Rimuovi eventuali !, ? generati automaticamente da board.san() se non voluti
				san_move_base = san_move_base.replace("!","").replace("?","")

				game_state.board.push(move)
				game_state.move_history.append(san_move_base) # Usa SAN base per la history semplice

				# Aggiungi la nuova mossa come mainline al PGN
				new_node = game_state.pgn_node.add_variation(move)

				# --- INIZIO MODIFICA: Aggiungi NAG/Commento al PGN ---
				if annotation_suffix:
					if annotation_suffix == "=":
						# Aggiungi un commento standard per la proposta di patta
						existing_comment = new_node.comment or ""
						if existing_comment:
							new_node.comment = existing_comment + " {Proposta di patta}"
						else:
							new_node.comment = "{Proposta di patta}"
					elif annotation_suffix in NAG_MAP:
						nag_value = NAG_MAP[annotation_suffix][0]
						new_node.nags.add(nag_value)
				# --- FINE MODIFICA ---

				# Se esistono mosse annullate, aggiungi un commento al nuovo nodo
				if hasattr(game_state, "cancelled_san_moves") and game_state.cancelled_san_moves:
					undo_comment = "Mosse annullate: " + " ".join(game_state.cancelled_san_moves)
					existing_comment = new_node.comment or ""
					if existing_comment:
						new_node.comment = existing_comment + " " + undo_comment
					else:
						new_node.comment = undo_comment
					# Svuota la lista per le prossime operazioni
					del game_state.cancelled_san_moves

				# Aggiorna il puntatore PGN al nuovo nodo
				game_state.pgn_node = new_node

				# Logica ECO (invariata)
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
						print("Apertura rilevata: " + new_eco_msg)
						last_eco_msg = new_eco_msg
						last_valid_eco_entry = current_entry_this_turn
					elif not new_eco_msg and last_eco_msg:
						last_eco_msg = ""

				# Controlli di fine partita (invariati)
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "1-0" if game_state.active_color == "white" else "0-1" # Nota: il turno è già cambiato qui
					game_state.pgn_game.headers["Result"] = result
					winner = game_state.black_player if result == "0-1" else game_state.white_player
					print(f"Scacco matto! Vince {winner}.")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
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
				elif game_state.board.can_claim_fifty_moves():
					game_state.game_over = True # Consideriamo la richiesta automatica per semplicità
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per la regola delle 50 mosse!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition():
					game_state.game_over = True # Consideriamo la richiesta automatica per semplicità
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Patta per triplice ripetizione della posizione!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break

				# Applica incremento e cambia turno (invariato)
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()

			except Exception as e:
				illegal_result=verbose_legal_moves_for_san(game_state.board,move_san_only) # Usa move_san_only qui
				Acusticator([600.0, 0.6, 0, volume], adsr=[5, 0, 35, 90])
				print(f"Mossa '{move_san_only}' illegale o non riconosciuta ({e}). Sulla casa indicata sono possibili:\n{illegal_result}")

	# --- Logica post-partita (invariata) ---
	game_state.pgn_game.headers["WhiteClock"] = FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = FormatClock(game_state.black_remaining)
	print("Partita terminata.")
	if last_valid_eco_entry:
		game_state.pgn_game.headers["ECO"] = last_valid_eco_entry["eco"]
		game_state.pgn_game.headers["Opening"] = last_valid_eco_entry["opening"]
		if last_valid_eco_entry["variation"]:
			game_state.pgn_game.headers["Variation"] = last_valid_eco_entry["variation"]
		else:
			if "Variation" in game_state.pgn_game.headers:
				del game_state.pgn_game.headers["Variation"]
	else:
		if "ECO" in game_state.pgn_game.headers:
			del game_state.pgn_game.headers["ECO"]
		if "Opening" in game_state.pgn_game.headers:
			del game_state.pgn_game.headers["Opening"]
		if "Variation" in game_state.pgn_game.headers:
			del game_state.pgn_game.headers["Variation"]

	pgn_str=str(game_state.pgn_game)
	pgn_str = format_pgn_comments(pgn_str) # Formatta commenti per leggibilità
	filename = f"{white_player}-{black_player}-{game_state.pgn_game.headers.get('Result', '*')}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
	filename=sanitize_filename(filename)
	with open(filename, "w", encoding="utf-8") as f:
		f.write(pgn_str)
	print("PGN salvato come "+filename+".")
	save_text_summary(game_state, game_state.descriptive_move_history, last_valid_eco_entry)
	try:
		pyperclip.copy(pgn_str)
		print("PGN copiato negli appunti.")
	except Exception as e:
		print(f"Errore durante la copia del PGN negli appunti: {e}")
	if len(game_state.move_history) >= 8:
		analyze_choice = key("Vuoi analizzare la partita? (s/n): ").lower()
		if analyze_choice == "s":
			db = LoadDB()
			engine_config = db.get("engine_config", {})
			if not engine_config or not engine_config.get("engine_path"):
				print("Motore non configurato. Ritorno al menù.")
				return
			else:
				# Assicurati che il motore sia inizializzato prima di analizzare
				if ENGINE is None:
					if not InitEngine():
						print("Impossibile inizializzare il motore. Analisi annullata.")
						return
				# Pulisci la cache se necessario prima di iniziare una nuova analisi
				cache_analysis.clear()
				AnalyzeGame(game_state.pgn_game)
		else:
			Acusticator([880.0, 0.2, 0, volume, 440.0, 0.2, 0, volume], kind=1, adsr=[25, 0, 50, 25])
	# Se la partita ha meno di 8 semimosse, la funzione termina senza chiedere nulla.

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
	launch_count = db.get("launch_count", 0) + 1
	db["launch_count"] = launch_count
	SaveDB(db)
	SchermataIniziale()
	InitEngine()
	LoadLocalization()
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
			old_volume=volume
			volume = dgt(f"\nVolume attuale: {int(volume*100)}, nuovo? (0-100): ", kind="i", imin=0, imax=100, default=50)
			volume/=100
			db = LoadDB()
			db["volume"] = volume
			SaveDB(db)
			Acusticator(["c5",.5,0,old_volume],adsr=[0,0,100,100],sync=True)
			Acusticator(["c5",.5,0,volume],adsr=[0,0,100,100])
		elif scelta=="vedi":
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			ViewClocks()
		elif scelta=="elimina":
			DeleteClock(db)
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="pgn":
			EditPGN()
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="nomi": # <-- BLOCCO NUOVO DA AGGIUNGERE
			EditLocalization()		
			Acusticator([1200.0, 0.05, 0, volume, "p", 0.05, 0, 0, 1100.0, 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="manuale":
			OpenManual()
		elif scelta=="gioca":
			Acusticator(["c5", 0.1, 0, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0, volume, "c6", 0.3, 0, volume, "g5", 0.1, 0, volume, "e5", 0.1, 0, volume, "c5", 0.1, 0, volume], kind=1, adsr=[5, 5, 90, 10])
			print("\nAvvio partita\n")
			db=LoadDB()
			if not db["clocks"]:
				Acusticator(["c5", 0.3, 0, volume, "g4", 0.3, 0, volume], kind=1, adsr=[30, 20, 80, 20])
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
	final_db = LoadDB()
	final_launch_count = final_db.get("launch_count", "sconosciuto") # Legge il contatore salvato	
	print(f"Arrivederci da Orologic {VERSION}.\nQuesta era la nostra {final_launch_count}a volta e ci siamo divertiti assieme per: {result}")
	Donazione()
	sys.exit(0)