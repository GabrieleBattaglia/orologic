# OROLOGIC - DEV - Data di concepimento: 14/02/2025 by Gabriele Battaglia & AIs
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re, pyperclip, io, chess.engine, random, zipfile, requests, copy, traceback
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator, key, Donazione, polipo
def resource_path(relative_path):
				"""
				Restituisce il percorso assoluto a una risorsa, funzionante sia in sviluppo
				che per un eseguibile compilato con PyInstaller (anche con la cartella _internal).
				"""
				try:
								# PyInstaller crea una cartella temporanea e ci salva il percorso in _MEIPASS
								# Questo è il percorso base per le risorse quando l'app è "congelata"
								base_path = sys._MEIPASS
				except Exception:
								# Se _MEIPASS non esiste, non siamo in un eseguibile PyInstaller
								# o siamo in una build onedir, il percorso base è la cartella dello script
								base_path = os.path.abspath(".")

				return os.path.join(base_path, relative_path)

def percorso_salvataggio(relative_path):
	"""
	Restituisce un percorso scrivibile vicino allo script .py o all'eseguibile .exe.
	Ideale per salvare impostazioni, PGN e altri file utente.
	"""
	if getattr(sys, 'frozen', False):
		# Siamo in un eseguibile compilato (es. .exe).
		# os.path.dirname(sys.executable) ci dà la cartella che contiene l'eseguibile.
		base_path = os.path.dirname(sys.executable)
	else:
		# Non siamo compilati, quindi siamo in modalità sviluppo.
		# os.path.abspath(".") ci dà la cartella dove si trova lo script .py.
		base_path = os.path.abspath(".")
	return os.path.join(base_path, relative_path)

lingua_rilevata, _ = polipo(source_language="it", config_path="settings")
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="4.10.28"
RELEASE_DATE=datetime.datetime(2025,7,19,20,27)
PROGRAMMER="Gabriele Battaglia & AIs"
STOCKFISH_DOWNLOAD_URL = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
ENGINE_NAME = "Nessuno" 
STILE_MENU_NUMERICO = False
DB_FILE = percorso_salvataggio(os.path.join("settings", "orologic_db.json"))
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
NAG_MAP = {
	"!": (1, _("mossa forte")),
	"?": (2, _("mossa debole")),
	"!!": (3, _("mossa molto forte")),
	"??": (4, _("mossa molto debole")),
	"!?": (5, _("mossa dubbia")),
	"?!": (6, _("mossa dubbia")),
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}
L10N = {}
# Pattern Regex per estrarre il suffisso di annotazione (1 o 2 caratteri !?=) alla fine della stringa.
# Il lookbehind (?<!=.) evita di catturare l'uguale della promozione (es. non matcha '=Q').
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
# Pattern Regex specifico per gestire i suffissi DOPO una promozione (es. "d8=Q!")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")
SMART_COMMANDS = {
	"s": _("Vai alla mossa precedente"),
	"d": _("Vai alla mossa successiva"),
	"r": _("Aggiorna valutazione CP"),
	"?": _("Visualizza questa lista di comandi"),
	".": _("Esci dalla modalità smart")
}
ANALYSIS_COMMAND = {
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
	".5":_("Riporta quale orologio è in moto o la durata della pausa, se attiva"),
	".l":_("Visualizza la lista mosse giocate"),
	".m":_("Mostra il valore del materiale ancora in gioco"),
	".p":_("Pausa/riavvia il countdown degli orologi"),
	".q":_("Annulla l'ultima mossa (solo in pausa)"),
	".b+":_("Aggiunge tempo al bianco (in pausa)"),
	".b-":_("Sottrae tempo al bianco (in pausa)"),
	".n+":_("Aggiunge tempo al nero (in pausa)"),
	".n-":_("Sottrae tempo al nero (in pausa)"),
	".s":_("Visualizza la scacchiera"),
	".c":_("Aggiunge un commento alla mossa corrente"),
	".1-0":_("Assegna vittoria al bianco (1-0) e conclude la partita"),
	".0-1":_("Assegna vittoria al nero (0-1) e conclude la partita"),
	".1/2":_("Assegna patta (1/2-1/2) e conclude la partita"),
	".*":_("Assegna risultato non definito (*) e conclude la partita"),
	".?":_("Visualizza l'elenco dei comandi disponibili"),
	"/[colonna]":_("Mostra la diagonale alto-destra partendo dalla base della colonna data"),
	"\\[colonna]":_("Mostra la diagonale alto-sinistra partendo dalla base della colonna data"),
	"-[colonna|traversa|casa]":_("Mostra le figure su quella colonna o traversa o casa"),
	",[NomePezzo]":_("Mostra la/le posizione/i del pezzo indicato")}
MENU_CHOICES={
	"analizza":_("Entra in modalità analisi partita"),
	"crea":_("Aggiungi un nuovo orologio alla collezione"),
	"elimina":_("Cancella uno degli orologi salvati"),
	"gioca":_("Inizia la partita"),
	"manuale":_("Mostra la guida dell'app"),
	"motore":_("Configura le impostazioni per il motore di scacchi"),
	"nomi":_("Personalizza i nomi dei pezzi e delle colonne"),
	"impostazioni":_("Varie ed eventuali"),
	"vedi":_("Mostra gli orologi salvati"),
	"volume":_("Consente la regolazione del volume degli effetti audio"),
	".":_("Esci dall'applicazione")}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}
#qf
def enter_escape(prompt=""):
	'''Ritorna vero su invio, falso su escape'''
	while True:
		k=key(prompt).strip()
		if k == "":
			return True
		elif k == "\x1b":
			return False
		print(_("Conferma con invio o annulla con escape"))

if sys.platform == 'win32':
	import ctypes

def SearchForEngine():
	"""
	Cerca motori UCI in tutte le unità, salva tutti i risultati, e chiede all'utente quale usare.
	Mostra progresso e statistiche finali.
	"""
	print(_("\nNessuna configurazione trovata. Avvio ricerca avanzata del motore..."))
	# --- Setup Iniziale ---
	stockfish_keywords = ["stockfish", "sf", "cfish", "sugar", "berserk", "shashchess", "dragon", "corchess"]
	other_engine_keywords = ["lc0", "ethereal", "slow"]
	all_keywords = stockfish_keywords + other_engine_keywords
	executable_extensions = (".exe",) if sys.platform == "win32" else ("",)
	search_paths = get_available_drives()
	shared_state = {
		"current_path": "", "folders_scanned": 0, "files_scanned": 0,
		"search_complete": False, "engines_found": []
	}
	lock = threading.Lock()
	def reporter():
		"""Stampa lo stato ogni 5 secondi."""
		while True:
			with lock:
				if shared_state["search_complete"]: break
				path = shared_state["current_path"]
				path_str = f"{path[:15]}...{path[-15:]}" if len(path) > 30 else path
			print(f"\rScanning: {path_str:<40}", end="")
			time.sleep(5)
	# --- Inizio Ricerca (Questa parte era già corretta) ---
	start_time = time.time()
	print(_("Avvio ricerca su: {paths}").format(paths=', '.join(search_paths)))
	reporter_thread = threading.Thread(target=reporter, daemon=True)
	reporter_thread.start()
	for path in search_paths:
		if not os.path.exists(path): continue
		try:
			for root, dirs, files in os.walk(path, topdown=True):
				with lock:
					shared_state["current_path"] = root
					shared_state["folders_scanned"] += 1
					shared_state["files_scanned"] += len(files)
				exclude_dirs = [
					"windows", "$recycle.bin", "programdata",
					"system volume information", "filehistory", "library", "system", "private"
				]
				dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs]
				for file in files:
					file_lower = file.lower()
					if file_lower.endswith(executable_extensions):
						# Logica di controllo migliorata
						is_match = False
						for keyword in all_keywords:
							# Per keyword ambigue come "sf", vogliamo un match esatto
							if len(keyword) <= 2:
								if file_lower == keyword + ".exe":
									is_match = True
									break
							# Per le altre, "startswith" va bene
							elif file_lower.startswith(keyword):
								is_match = True
								break
						if is_match:
							with lock:
								shared_state["engines_found"].append((root, file))
								found_count = len(shared_state["engines_found"])
								print(f"\r{' ' * 60}\r🎉 Trovati finora: {found_count}. La scansione continua...", end="")
		except Exception:
			continue
	with lock:
		shared_state["search_complete"] = True
	reporter_thread.join()
	end_time = time.time()
	duration = end_time - start_time
	print(f"\r{' ' * 60}\r", end="")
	print("\n--- Report della Ricerca ---")
	print(_("Tempo impiegato: {duration:.2f} secondi").format(duration=duration))
	print(_("Cartelle scansionate: {folders}").format(folders=shared_state['folders_scanned']))
	print(_("File scansionati: {files}").format(files=shared_state['files_scanned']))
	# --- Blocco Scelta Utente (CORRETTO E PULITO) ---
	found_engines = shared_state["engines_found"]
	if not found_engines:
		print(_("\nRisultato: Nessun motore trovato."))
		return None, None, False
	print(_("\nSono stati trovati {num} eseguibili che potrebbero essere motori compatibili\n\tVerifica che lo siano davvero e scegline uno da usare:").format(num=len(found_engines)))
	for i, (root, file) in enumerate(found_engines, 1):
		print(f" {i}. Eseguibile: {file}\n    Percorso: {root}")
	if len(found_engines) == 1:
		# Logica per un solo motore trovato
		prompt_text = _("\nTrovato un solo motore. Vuoi usarlo? (Invio per sì, 0 per no, 's' per scaricare): ")
		scelta_str = key(prompt_text).lower().strip()
		if scelta_str == '0':
			print(_("Nessun motore selezionato."))
			return None, None, False
		elif scelta_str == 's':
			return None, None, True
		else: # L'utente ha premuto Invio o qualsiasi altra cosa
			root, file = found_engines[0]
			print(_("Hai selezionato: {file}").format(file=file))
			return root, file, False
	else:
		# Logica per motori multipli (il tuo 'while' loop era già corretto)
		while True:
			prompt_text = _("\nQuale motore vuoi usare? (1-{max_num}, 0 per nessuno, 's' per scaricare Stockfish): ").format(max_num=len(found_engines))
			scelta_str = dgt(prompt_text,kind="s",smin=1,smax=3)
			if scelta_str == 's':
				return None, None, True
			if scelta_str == '0':
				print(_("Nessun motore selezionato."))
				return None, None, False
			try:
				scelta_num = int(scelta_str)
				if 1 <= scelta_num <= len(found_engines):
					root, file = found_engines[scelta_num - 1]
					print(_("Hai selezionato: {file}").format(file=file))
					return root, file, False
				else:
					print(_("Scelta non valida. Riprova."))
			except ValueError:
				print(_("Input non valido. Riprova."))

def get_available_drives():
	"""
	Restituisce una lista di tutte le unità disco disponibili nel sistema.
	Funziona su Windows, macOS e Linux.
	"""
	drives = []
	if sys.platform == 'win32':
		# Metodo per Windows: usa le API per trovare le lettere dei drive
		bitmask = ctypes.windll.kernel32.GetLogicalDrives()
		for i in range(26):
			if (bitmask >> i) & 1:
				drive_letter = chr(ord('A') + i)
				drives.append(f"{drive_letter}:\\")
	elif sys.platform == 'darwin':
		# Metodo per macOS: i dischi sono montati sotto /Volumes
		drives.append('/') # Cerca anche nella root principale
		try:
			drives.extend([os.path.join('/Volumes', d) for d in os.listdir('/Volumes')])
		except FileNotFoundError:
			pass
	else: # Metodo per Linux
		drives.append('/') # Cerca semplicemente dalla root
	return drives

def get_app_data_path():
	"""Restituisce un percorso affidabile nella cartella AppData dell'utente per salvare il motore."""
	# AppData\Local\Orologic\Engine
	path = os.path.join(os.getenv('LOCALAPPDATA'), "Orologic", "Engine")
	os.makedirs(path, exist_ok=True) # Crea la cartella se non esiste
	return path

def DownloadAndInstallEngine():
	"""
	Scarica Stockfish, lo estrae in una cartella locale e restituisce il percorso all'eseguibile.
	"""
	try:
		install_path = get_app_data_path()
		zip_filename = os.path.join(install_path, "stockfish.zip")
		# 1. Download
		print(_("\n📥 Sto scaricando Stockfish da {url}...").format(url=STOCKFISH_DOWNLOAD_URL))
		response = requests.get(STOCKFISH_DOWNLOAD_URL, stream=True)
		response.raise_for_status() # Controlla se ci sono stati errori HTTP
		with open(zip_filename, "wb") as f:
			total_length = int(response.headers.get('content-length'))
			downloaded = 0
			for chunk in response.iter_content(chunk_size=4096):
				downloaded += len(chunk)
				f.write(chunk)
				done = int(50 * downloaded / total_length)
				sys.stdout.write("\r[{}{}] {:.1f}%".format('=' * done, ' ' * (50-done), (downloaded/total_length)*100))
				sys.stdout.flush()
		print("\nDownload completato.")
		# 2. Estrazione
		print(_("...sto estraendo i file..."))
		with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
			zip_ref.extractall(install_path)
		print(_("Estrazione completata."))
		os.remove(zip_filename) # Rimuoviamo il file zip dopo l'estrazione
		# 3. Trova l'eseguibile dentro la cartella appena estratta
		for root, dirs, files in os.walk(install_path):
			for file in files:
				if file.lower().startswith("stockfish") and file.lower().endswith(".exe"):
					print(_("Installazione di Stockfish completata con successo!"))
					return root, file # Trovato!
	except requests.exceptions.RequestException as e:
		print(_("\nErrore di rete durante il download: {error}").format(error=e))
		return None, None
	except zipfile.BadZipFile:
		print(_("\nErrore: Il file scaricato non è uno zip valido."))
		return None, None
	except Exception as e:
		print(_("\nSi è verificato un errore imprevisto durante l'installazione: {error}").format(error=e))
		return None, None
	return None, None # Se non trova l'eseguibile dopo l'estrazione

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
			return _("Destinazione non riconosciuta.")
		legal_moves=[]
		for move in board.legal_moves:
			if move.to_square==dest_square:
				if promotion is not None:
					if move.promotion==promotion:
						legal_moves.append(move)
				else:
					legal_moves.append(move)
	if not legal_moves:
		return _("Nessuna mossa legale trovata per la destinazione indicata.")
	result_lines=[]
	i=1
	for move in legal_moves:
		verbose_desc=DescribeMove(move,board.copy())
		result_lines.append(_("{i}°: {desc}").format(i=i, desc=verbose_desc))
		i+=1
	return "\n".join(result_lines)
def FormatClock(seconds):
	total = int(seconds)
	hours = total // 3600
	minutes = (total % 3600) // 60
	secs = total % 60
	return "{hours:02d}:{minutes:02d}:{secs:02d}".format(hours=hours, minutes=minutes, secs=secs)
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
		sanitized = _("default_filename")
	return sanitized
def SmartInspection(analysis_lines, board):
	print(_("Linee disponibili:"))
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
		print(_("Linea {num}: {summary}").format(num=i, summary=line_summary))
	choice = dgt(_("Quale linea vuoi ispezionare? (1/{num_lines}) ").format(num_lines=len(analysis_lines)), kind="i", imin=1, imax=len(analysis_lines),	default=1)
	Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves:
		print(_("Linea vuota, termine ispezione."))
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
	print(_("\nUtilizza questi comandi:"))
	menu(p=SMART_COMMANDS,show_only=True)
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]:
			temp_board.push(move)
		current_move = pv_moves[current_index-1]
		# Ottieni la descrizione verbosa della mossa corrente, dal punto di vista della board prima di eseguirla
		move_verbose = DescribeMove(current_move, temp_board)
		smart_prompt=_("\nLinea {line_num}: ({current}/{total}), CP: {cp}, {move_num}... {move_desc}").format(line_num=line_index+1, current=current_index, total=total_moves, cp=eval_str, move_num=temp_board.fullmove_number, move_desc=move_verbose)
		cmd = key(smart_prompt).lower()
		if cmd == ".":
			break
		elif cmd == "s":
			if current_index > 1:
				current_index -= 1
			else:
				Acusticator(["c4", 0.1, -0.5, volume], kind=2, adsr=[10, 10, 30, 50]) 
				print(_("\nNon ci sono mosse precedenti."))
		elif cmd == "?":
			Acusticator(["d5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			temp_board = board.copy()
			try:
				for move in pv_moves[:current_index]:
					temp_board.push(move)
			except Exception as push_err:
				print(_("\nErrore interno durante avanzamento per valutazione: {error}").format(error=push_err))
				eval_str = "ERR_NAV" # Aggiorna la stringa del prompt per indicare l'errore
				continue # Torna all'inizio del loop while
			score_object_si = CalculateEvaluation(temp_board)
			Acusticator(["e5",.008,-1,volume]) # Suono dopo il tentativo
			if score_object_si is not None:
				new_eval_str = "N/A" # Valore di default per la stringa formattata
				pov_score_si = score_object_si.pov(temp_board.turn)
				if pov_score_si.is_mate():
					mate_in_si = pov_score_si.mate()
					new_eval_str = _("M{moves}").format(moves=abs(mate_in_si))
				else:
					cp_si = score_object_si.white().score(mate_score=30000)
					if cp_si is not None:
						new_eval_str = "{cp:+.2f}".format(cp=cp_si/100) # Formatta CP assoluto
					else:
						new_eval_str = "ERR"
				eval_str = new_eval_str
				Acusticator(["g5", 0.1, 0.3, volume], kind=1, adsr=[5,5,90,5]) # Suono successo
				print(_("\nValutazione aggiornata."))
			else:
				Acusticator(["a3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]) # Suono errore
				print(_("\nImpossibile aggiornare la valutazione."))
				eval_str = "N/A"
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				Acusticator(["c4", 0.1, 0.5, volume], kind=2, adsr=[10, 10, 30, 50])
				print(_("\nNon ci sono mosse successive."))
		else:
			Acusticator(["b3", 0.12, 0, volume], kind=2, adsr=[5, 15, 20, 60])
			print(_("\nComando non riconosciuto."))
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
					move_descr = _("{num}°.").format(num=move_number) + " " + white_descr
					if i < len(best_line) and temp_board.turn == chess.BLACK:
						black_move = best_line[i]
						black_descr = DescribeMove(black_move, temp_board)
						temp_board.push(black_move)
						i += 1
						move_descr += ", " + black_descr
					descriptive_moves.append(move_descr)
					move_number += 1
				else:
					black_move = best_line[i]
					black_descr = DescribeMove(black_move, temp_board)
					temp_board.push(black_move)
					i += 1
					descriptive_moves.append(_("{num}°... {desc}").format(num=move_number, desc=black_descr))
					move_number += 1
			score = analysis[0].get("score")
			mate_found = False
			if score is not None and score.relative.is_mate():
				mate_moves = abs(score.relative.mate())
				mate_found = True
			if bestmove:
				if mate_found:
					Acusticator(["a6",.008,1,volume]) 
					return [_("Matto in {moves}, {first_move}").format(moves=mate_moves, first_move=descriptive_moves[0])]
				else:
					Acusticator(["f6",.008,1,volume]) 
					return [descriptive_moves[0]]
			else:
				if mate_found:
					descriptive_moves.insert(0, _("Matto in {moves}:").format(moves=mate_moves))
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
		print(_("Errore in CalculateBestLine:"), e)
		return None
def CalculateEvaluation(board):
	global ENGINE, analysis_time, multipv, cache_analysis
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result:
			return None
		score = analysis_result[0].get("score")
		return score
	except Exception as e:
		print(_("Errore in CalculateEvaluation per FEN {fen}: {error}").format(fen=fen, error=e))
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
					print(_("Warning: Valori WDL dopo unpack non numerici: W={win}, D={draw}, L={loss}").format(win=win_permille_pov, draw=draw_permille_pov, loss=loss_permille_pov))
					return None
			perspective = None
			if hasattr(wdl_info, "color"):
				perspective = wdl_info.color
			elif hasattr(wdl_info,"pov"): # Nome alternativo comune
				perspective = wdl_info.pov
			else:
					# Se non riusciamo a determinare la prospettiva, assumiamo per sicurezza
				# che sia già assoluta (WHITE) come da standard UCI.
				print(_("Warning: Impossibile determinare prospettiva WDL da {info}. Assumo WHITE.").format(info=repr(wdl_info)))
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
			print(_("Warning: Fallito unpack diretto oggetto WDL {info}: {error}").format(info=repr(wdl_info), error=e_unpack))
			return None
	except Exception as e:
		print(_("Errore generale in CalculateWDL per FEN {fen}: {error}").format(fen=fen, error=e))
		return None
def SetAnalysisTime(new_time):
	"""
	Permette di impostare il tempo di analisi (in secondi) per il motore.
	"""
	global analysis_time
	try:
		new_time = float(new_time)
		if new_time <= 0:
			print(_("Il tempo di analisi deve essere positivo."))
		else:
			analysis_time = new_time
			print(_("Tempo di analisi impostato a {seconds} secondi.").format(seconds=analysis_time))
	except Exception as e:
		print(_("Errore in SetAnalysisTime:"), e)
def SetMultipv(new_multipv):
	"""
	Permette di impostare il numero di linee (multipv) da visualizzare.
	"""
	global multipv
	try:
		new_multipv = int(new_multipv)
		if new_multipv < 1:
			print(_("Il numero di linee deve essere almeno 1."))
		else:
			multipv = new_multipv
			print(_("Multipv impostato a {multipv}.").format(multipv=multipv))
	except Exception as e:
		print(_("Errore in SetMultipv:"), e)
def LoadPGNFromClipboard():
	"""
	Carica il PGN dagli appunti e lo restituisce come oggetto pgn_game.
	Se gli appunti contengono più di una partita, viene presentato un menù numerato e
	viene chiesto all'utente di scegliere la partita da caricare.
	"""
	try:
		clipboard_pgn = pyperclip.paste()
		if not clipboard_pgn.strip():
			print(_("Appunti vuoti."))
			return None
		pgn_io = io.StringIO(clipboard_pgn)
		games = []
		while True:
			game = chess.pgn.read_game(pgn_io)
			if game is None:
				break
			games.append(game)
		if len(games) == 0:
			print(_("PGN non valido negli appunti."))
			return None
		elif len(games) == 1:
			return games[0]
		else:
			print(_("\nSono state trovate {num_games} partite nei PGN.").format(num_games=len(games)))
			partite={}
			for i, game in enumerate(games, start=1):
				white = game.headers.get("White", _("Sconosciuto"))
				black = game.headers.get("Black", _("Sconosciuto"))
				date = game.headers.get("Date", _("Data sconosciuta"))
				partite[i]="{white} vs {black} - {date}".format(white=white, black=black, date=date)
			while True:
				choice = menu(d=partite,	p=_("Quale partita vuoi caricare? "),	show=True,ntf=_("Numero non valido. Riprova."))
				try:
					index = int(choice)
					if 1 <= index <= len(games):
						return games[index - 1]
					else:
						Acusticator(["a3", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
						print(_("Numero non valido. Riprova."))
				except ValueError:
					Acusticator(["g2", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
					print(_("Input non valido. Inserisci un numero."))
	except Exception as e:
		print(_("Errore in LoadPGNFromClipboard:"), e)
		return None
def InitEngine():
	global ENGINE, ENGINE_NAME
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config:
		return False
	path_da_usare = ""
	# Leggiamo il nuovo flag. Se non c'è, consideriamo il percorso assoluto per retrocompatibilità.
	is_relative = engine_config.get("engine_is_relative", False)
	saved_path = engine_config.get("engine_path")
	if not saved_path:
		return False
	# Se il percorso salvato è relativo, lo combiniamo con il percorso attuale dell'app
	if is_relative:
		path_da_usare = percorso_salvataggio(saved_path)
	# Altrimenti, è un percorso assoluto e lo usiamo così com'è
	else:
		path_da_usare = saved_path
	if os.path.exists(path_da_usare):
		try:
			ENGINE = chess.engine.SimpleEngine.popen_uci(path_da_usare)
			ENGINE.configure({
				"Hash": engine_config.get("hash_size", 128),
				"Threads": engine_config.get("num_cores", 1),
				"Skill Level": engine_config.get("skill_level", 20),
				"Move Overhead": engine_config.get("move_overhead", 0)
			})
			ENGINE_NAME = ENGINE.id.get("name", _("Nome Sconosciuto"))
			return True
		except Exception as e:
			# Se il motore esiste ma non parte, avvisa l'utente
			print(_("\n⚠️ Errore durante l'avvio del motore: {error}").format(error=e))
			ENGINE = None
			ENGINE_NAME = "Nessuno"
			return False
	# Se il percorso (assoluto o ricostruito) non esiste più...
	else:
		# Non stampiamo nulla per non disturbare l'avvio pulito del programma
		ENGINE = None
		ENGINE_NAME = "Nessuno"
		return False

def EditEngineConfig(initial_path=None, initial_executable=None):
	print(_("\nImposta configurazione del motore scacchistico\n"))
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if engine_config:
		print(_("Configurazione attuale del motore:"))
		for key, val in engine_config.items():
			print("  {key}: {val}".format(key=key, val=val))
	else:
		print(_("Nessuna configurazione trovata."))
	path_prompt = _("Inserisci il percorso dove è salvato il motore UCI [{default}]: ").format(default=initial_path or "")
	path = dgt(prompt=path_prompt, kind="s", smin=3, smax=256, default=initial_path)
	Acusticator(["g6", 0.025, -.75, volume,"c5", 0.025, -75, volume],kind=3)
	executable_prompt = _("Inserisci il nome dell'eseguibile del motore [{default}]: ").format(default=initial_executable or "")
	executable = dgt(prompt=executable_prompt, kind="s", smin=5, smax=64, default=initial_executable)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print(_("Il file specificato non esiste. Verifica il percorso e il nome dell'eseguibile."))
		return
	app_path = percorso_salvataggio('')
	app_drive = os.path.splitdrive(app_path)[0]
	engine_drive = os.path.splitdrive(full_engine_path)[0]
	path_to_save = ""
	is_relative = False
	if app_drive.lower() == engine_drive.lower():
		path_to_save = os.path.relpath(full_engine_path, app_path)
		is_relative = True
		print(_("Info: il motore si trova sullo stesso drive, verrà salvato un percorso relativo per la portabilità."))
	else:
		path_to_save = full_engine_path
		is_relative = False
		print(_("Info: il motore si trova su un drive diverso, verrà salvato un percorso assoluto (configurazione non portatile)."))	
	hash_size = dgt(prompt=_("Inserisci la dimensione della hash table (min: 1, max: 4096 MB): "), kind="i", imin=1, imax=4096)
	Acusticator(["g6", 0.025, -.25, volume,"c5", 0.025, -.25, volume],kind=3)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=_("Inserisci il numero di core da utilizzare (min: 1, max: {max_cores}): ").format(max_cores=max_cores), kind="i", imin=1, imax=max_cores, default=4)
	Acusticator(["g6", 0.025, 0, volume,"c5", 0.025, 0, volume],kind=3)
	skill_level = dgt(prompt=_("Inserisci il livello di skill (min: 0, max: 20): "), kind="i", imin=0, imax=20)
	Acusticator(["g6", 0.025, .25, volume,"c5", 0.025, .25, volume],kind=3)
	move_overhead = dgt(prompt=_("Inserisci il move overhead in millisecondi (min: 0, max: 500): "), kind="i", imin=0, imax=500, default=0)
	Acusticator(["g6", 0.025, .5, volume,"c5", 0.025, .5, volume],kind=3)
	wdl_switch = True  # Puoi eventualmente renderlo configurabile
	engine_config = {
		"engine_path": path_to_save,
		"engine_is_relative": is_relative, # Aggiungiamo il nostro nuovo flag
		"hash_size": hash_size,
		"num_cores": num_cores,
		"skill_level": skill_level,
		"move_overhead": move_overhead,
		"wdl_switch": wdl_switch
	}
	db["engine_config"] = engine_config
	SaveDB(db)
	print(_("Configurazione del motore salvata."))
	InitEngine()
	Acusticator(["a6", 0.5, 1, volume],kind=3, adsr=[.001,0,100,99.9])
	return

def EditLocalization():
	"""
	Crea un'interfaccia per permettere all'utente di personalizzare
	le stringhe usate nel programma (localizzazione).
	"""
	print(_("\n--- Personalizzazione Lingua ---\n"))
	print(_("Per ogni voce, inserisci il nuovo testo o premi INVIO per mantenere il valore attuale."))
	db = LoadDB()
	# Usiamo una copia per le modifiche, per poi salvarla tutta in una volta
	l10n_config = db.get("localization", get_default_localization())
	# Definiamo le voci da personalizzare e i relativi prompt
	# Struttura: [ (chiave_cat, chiave_voce, prompt_utente), ... ]
	# Per voci complesse (dizionari), usiamo una tupla: (chiave_cat, chiave_voce, (chiave_sub, prompt_sub))
	items_to_edit = [
		("pieces", "pawn", ("name", _("Nome per 'Pedone'"))),
		("pieces", "knight", ("name", _("Nome per 'Cavallo'"))),
		("pieces", "bishop", ("name", _("Nome per 'Alfiere'"))),
		("pieces", "rook", ("name", _("Nome per 'Torre'"))),
		("pieces", "queen", ("name", _("Nome per 'Donna'"))),
		("pieces", "king", ("name", _("Nome per 'Re'"))),
		("columns", "a", _("Nome per colonna 'a' (Ancona)")),
		("columns", "b", _("Nome per colonna 'b' (Bologna)")),
		("columns", "c", _("Nome per colonna 'c' (Como)")),
		("columns", "d", _("Nome per colonna 'd' (Domodossola)")),
		("columns", "e", _("Nome per colonna 'e' (Empoli)")),
		("columns", "f", _("Nome per colonna 'f' (Firenze)")),
		("columns", "g", _("Nome per colonna 'g' (Genova)")),
		("columns", "h", _("Nome per colonna 'h' (Hotel)")),
		("adjectives", "white", ("m", _("Aggettivo 'bianco' (maschile)"))),
		("adjectives", "white", ("f", _("Aggettivo 'bianco' (femminile)"))),
		("adjectives", "black", ("m", _("Aggettivo 'nero' (maschile)"))),
		("adjectives", "black", ("f", _("Aggettivo 'nero' (femminile)"))),
		("moves", "capture", _("Verbo per la cattura (es. 'prende')")),
		("moves", "capture_on", _("Preposizione per la casa di cattura (es. 'in')")),
		("moves", "move_to", _("Preposizione per la casa di destinazione (es. 'in')")),
		("moves", "en_passant", _("Testo per 'en passant'")),
		("moves", "short_castle", _("Testo per 'arrocco corto'")),
		("moves", "long_castle", _("Testo per 'arrocco lungo'")),
		("moves", "promotes_to", _("Testo per la promozione (es. 'e promuove a')")),
		("moves", "check", _("Testo per 'scacco'")),
		("moves", "checkmate", _("Testo per 'scacco matto!'"))
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
			new_val = dgt("{prompt} [{current}]: ".format(prompt=prompt_text, current=current_val), kind="s", default=current_val)
			l10n_config[cat][key][sub_key] = new_val.strip()
			# Se abbiamo appena modificato un pezzo, chiediamo il genere
			if cat == "pieces":
				current_gender = l10n_config[cat][key]['gender']
				gender_prompt = _("  Genere per '{new_val}' (m/f/n) [{current_gender}]: ").format(new_val=new_val, current_gender=current_gender)
				while True:
					new_gender = dgt(gender_prompt, kind="s", default=current_gender).lower()
					if new_gender in ['m', 'f', 'n']:
						l10n_config[cat][key]['gender'] = new_gender
						break
					else:
						print(_("Input non valido. Inserisci 'm' (maschile), 'f' (femminile) o 'n' (neutro)."))
		else: # Voce semplice (es. colonne, mosse)
			prompt_text = details
			current_val = l10n_config[cat][key]
			new_val = dgt("{prompt} [{current}]: ".format(prompt=prompt_text, current=current_val), kind="s", default=current_val)
			l10n_config[cat][key] = new_val.strip()
		Acusticator([pitch, 0.08, pan, volume], kind=1, adsr=[2, 5, 80, 10])
	Acusticator(['c7', 0.05, 0, volume,'e7', 0.05, 0, volume,'g7', 0.15, 0, volume], kind=1, adsr=[2, 5, 90, 5])
	# Salvataggio finale
	db["localization"] = l10n_config
	SaveDB(db)
	LoadLocalization() # Ricarica le impostazioni per renderle subito attive
	print(_("\nImpostazioni di lingua salvate con successo!"))

def AnalisiAutomatica(pgn_game):
	"""
	Esegue un'analisi automatica completa della partita, aggiungendo commenti
	sugli errori e varianti migliori direttamente nel PGN.
	"""
	# Fase 1: Controllo motore e raccolta parametri
	if ENGINE is None:
		print(_("\nMotore non inizializzato. Impossibile avviare l'analisi automatica."))
		return
	def _format_score(score_obj, pov_color):
		if not score_obj: return "N/A"
		pov_score = score_obj.pov(pov_color)
		if pov_score.is_mate():
			return f"M{abs(pov_score.mate())}"
		else:
			cp = score_obj.white().score(mate_score=30000)
			if cp is None: return "N/A"
			# Per la visualizzazione, il segno è relativo a chi ha il tratto
			final_cp = cp if pov_color == chess.WHITE else -cp
			return f"{final_cp/100:+.2f}"
	print(_("\n--- Analisi Automatica della Partita ---"))
	print(_("\nImpostazione dei parametri di analisi:"))
	analysis_mode_map = {
		"t": _("Tempo per mossa (secondi)"),
		"p": _("Profondità fissa (ply)"),
		"n": _("Numero di nodi per mossa")
	}
	analysis_mode = menu(analysis_mode_map, show=True, keyslist=True, numbered=STILE_MENU_NUMERICO, ntf=_("Scelta non valida: "))
	limit = None
	if analysis_mode == 't':
		value = dgt(_("Inserisci i secondi per mossa: [INVIO per 1] "), kind="f", fmin=0.2, fmax=60, default=1)
		limit = chess.engine.Limit(time=value)
	elif analysis_mode == 'p':
		value = dgt(_("Inserisci la profondità di analisi: [INVIO per 18] "), kind="i", imin=5, imax=50, default=18)
		limit = chess.engine.Limit(depth=value)
	elif analysis_mode == 'n':
		value = dgt(_("Inserisci il numero di nodi da analizzare (in migliaia): [INVIO per 25] "), kind="i", imin=5, imax=99999, default=25)
		limit = chess.engine.Limit(nodes=value * 1000)
	else:
		print(_("Scelta non valida. Analisi annullata."))
		return
	print(_("\nDefinisci le soglie di valutazione semimosse (in centipawn):"))
	soglia_miglioramento = dgt(_("Alternativa Migliore (es. 10-20 cp): [INVIO per 20] "), kind="i", imin=1, imax=1000, default=20)
	soglia_inesattezza = dgt(_("Inesattezza (es. 25-50 cp): [INVIO per 38] "), kind="i", imin=1, imax=1000, default=38)
	soglia_errore = dgt(_("Errore (es. 51-100 cp): [INVIO per 75] "), kind="i", imin=soglia_inesattezza + 1, imax=2000, default=75)
	soglia_svarione = dgt(_("Svarione (Blunder, > Errore): [INVIO per 200] "), kind="i", imin=soglia_errore + 1, imax=6000, default=200)
	num_varianti = dgt(_("Quante varianti alternative calcolare per le mosse deboli? (1-5): [INVIO per 1] "), kind="i", imin=1, imax=5, default=1)
	mosse_da_saltare = 0
	last_valid_eco_entry = None # Inizializziamo la variabile che conterrà i dati dell'apertura
	if enter_escape(_("Vuoi saltare automaticamente le mosse di apertura note? (INVIO per sì, ESC per specificare manualmente): ")):
		print(_("Rilevo la fine della teoria d'apertura..."))
		eco_db = LoadEcoDatabaseWithFEN("eco.db")
		if eco_db:
			temp_board = pgn_game.board().copy()
			for move in pgn_game.mainline_moves():
				temp_board.push(move)
				# Eseguiamo la ricerca dell'apertura per la posizione corrente
				detected_opening = DetectOpeningByFEN(temp_board, eco_db)
				if detected_opening:
					# Se troviamo una corrispondenza, aggiorniamo le nostre variabili
					mosse_da_saltare = temp_board.ply()
					last_valid_eco_entry = detected_opening
				else:
					# Alla prima mossa non trovata, usciamo dal ciclo
					break
			# FIX DEFINITIVO: Controlliamo che 'last_valid_eco_entry' sia un dizionario prima di usarlo
			if isinstance(last_valid_eco_entry, dict):
				opening_name = last_valid_eco_entry.get('opening', _('Nome non trovato'))
				print(_("Trovata apertura: {name}").format(name=opening_name))
			print(_("L'analisi salterà le prime {n} semimosse.").format(n=mosse_da_saltare))
	else:
		mosse_da_saltare = dgt(_("Quante semimosse (ply) iniziali vuoi saltare? (INVIO per {n}) ".format(n=mosse_da_saltare)), kind="i", imin=0, imax=40, default=mosse_da_saltare)
	# Fase 2 e 3: Ciclo di Analisi e Commento
	print("\n" + "="*40 + _("\nInizio analisi...\n\tPremi escape per interrompere.") + "\n" + "="*40)
	start_time = time.time()
	mainline_nodes = list(pgn_game.mainline())
	imprecision_stats = {
		"Svarione": {'w': 0, 'b': 0},
		"Errore": {'w': 0, 'b': 0},
		"Inesattezza": {'w': 0, 'b': 0}
	}
	cpl_data = {'w': [], 'b': []} # Memorizza i CPL di ogni mossa per l'analisi a 3 fasi
	last_valid_eco_entry = None
	for i, node in enumerate(mainline_nodes):
		if key(attesa=0.002)=='\x1b':		# Se l'utente preme ESC, interrompi l'analisi
			Acusticator(["c3", 0.3, 0.5, volume], kind=2, adsr=[10, 10, 30, 50])
			print(_("\nAnalisi interrotta dall'utente."))
			break
		ply = i + 1
		if ply <= mosse_da_saltare:
			continue
		total_plys = len(mainline_nodes)
		san = node.parent.board().san(node.move)
		san_str = san if ply % 2 != 0 else f"...{san}"
		elapsed_time = time.time() - start_time
		time_str = f"{int(elapsed_time // 60):02d}:{int(elapsed_time % 60):02d}"
		print(f"\r{' ' * 79}\rPLY {ply}/{total_plys} {san_str:<12} | Tempo: {time_str}", end="")		
		num_mosse_da_analizzare = total_plys - mosse_da_saltare
		if num_mosse_da_analizzare > 0:
			progressione = (ply - mosse_da_saltare) / num_mosse_da_analizzare
		else:
			progressione = 0
		pan = -1 + (progressione * 2)
		# Calcola il pitch in modo lineare tra le frequenze di C2 e C8
		freq_iniziale = 65.4  # Frequenza (Hz) di C2
		freq_finale = 4186.0  # Frequenza (Hz) di C8
		freq_corrente = freq_iniziale + (progressione * (freq_finale - freq_iniziale))
		Acusticator([freq_corrente, 0.06, pan, volume], kind=1, adsr=[35, 0, 70, 35])
		try:
			# --- LOGICA DEFINITIVA: Utilizzo esplicito del FEN ---
			parent_board = node.parent.board()
			current_board = node.board()

			# 1. Analisi Multi-PV passando il FEN della posizione.
			info_lines = ENGINE.analyse(parent_board.fen(), limit, multipv=(num_varianti + 1))

			if not info_lines:
				print(f"\n! Attenzione: L'analisi principale per la mossa {ply} è fallita. Salto.")
				continue
			
			score_best_possible_obj = info_lines[0].get('score')

			# 2. Cerchiamo la mossa giocata tra le linee.
			actual_move_info = None
			for line in info_lines:
				if line.get('pv') and line['pv'][0] == node.move:
					actual_move_info = line
					break
			
			score_actual_obj = None
			if actual_move_info:
				score_actual_obj = actual_move_info.get('score')
			else:
				# 3. Analisi di ripiego, passando sempre il FEN.
				info_actual_move = ENGINE.analyse(current_board.fen(), limit)
				
				# Come da tua corretta analisi, il risultato è un dizionario.
				if info_actual_move:
					score_actual_obj = info_actual_move.get('score')
			
			# 4. Controllo finale di sicurezza.
			if not score_best_possible_obj or not score_actual_obj:
				print(f"\n! Attenzione: Impossibile ottenere la valutazione completa per la mossa {ply}. Salto.")
				continue

			# 5. Calcolo del CPL e generazione dei commenti.
			cp_best_possible = score_best_possible_obj.white().score(mate_score=30000)
			cp_actual = score_actual_obj.white().score(mate_score=30000)
			if cp_best_possible is None or cp_actual is None: continue
			loss = (cp_best_possible - cp_actual) if parent_board.turn == chess.WHITE else (cp_actual - cp_best_possible)
			
			# (Il resto della logica per commenti e varianti rimane qui, è già corretta)
			original_comment = node.comment or ""
			error_type, improvement_type = "", ""
			
			if score_best_possible_obj.pov(parent_board.turn).is_mate() and not score_actual_obj.pov(parent_board.turn).is_mate():
				error_type = _("Matto mancato")
			elif loss >= soglia_svarione: error_type = _("Svarione")
			elif loss >= soglia_errore: error_type = _("Errore")
			elif loss >= soglia_inesattezza: error_type = _("Inesattezza")
			elif loss >= soglia_miglioramento and info_lines[0]['pv'][0] != node.move:
				improvement_type = _("Opportunità")

			color_key = 'w' if parent_board.turn == chess.WHITE else 'b'
			if error_type: 
				imprecision_stats.setdefault(error_type, {'w': 0, 'b': 0})[color_key] += 1
			cpl_data[color_key].append(loss)

			new_comment_str = ""
			if error_type:
				new_comment_str = f"{{[OAA] {error_type}. Perdita: {loss/100:+.2f}}}"
			elif improvement_type:
				best_move_eval_str = _format_score(score_best_possible_obj, parent_board.turn)
				new_comment_str = f"{{[OAA] {improvement_type}. C'era: {best_move_eval_str}}}"

			if new_comment_str:
				node.comment = (original_comment.strip() + " " + new_comment_str).strip()

			is_mate_missed = score_best_possible_obj.pov(parent_board.turn).is_mate() and info_lines[0]['pv'][0] != node.move

			if (is_mate_missed or error_type or improvement_type) and num_varianti > 0:
				varianti_aggiunte = 0
				for line_info in info_lines:
					if varianti_aggiunte >= num_varianti: break
					if 'pv' not in line_info or not line_info['pv'] or line_info['pv'][0] == node.move: continue
					
					var_node = node.parent.add_variation(line_info['pv'][0])
					line_score_obj = line_info.get('score')
					if line_score_obj:
						var_node.comment = f"{{Alternativa: {_format_score(line_score_obj, parent_board.turn)}}}"
					
					temp_node = var_node
					for move_in_line in line_info['pv'][1:]:
						temp_node = temp_node.add_variation(move_in_line)
					
					varianti_aggiunte += 1
					Acusticator(['e4', 0.01, 0, volume], kind=1, adsr=[2, 5, 80, 10])

				if varianti_aggiunte > 0:
					msg_varianti = _("Aggiunta {n} variante").format(n=varianti_aggiunte) if varianti_aggiunte == 1 else _("Aggiunte {n} varianti").format(n=varianti_aggiunte)
					print(f"\r{' ' * 79}\rPLY {ply}/{total_plys} {san_str:<12} | Tempo: {time_str} | {msg_varianti}", end="")

		except chess.engine.EngineError as e:
			print(f"\n! Errore del motore alla mossa {ply}, analisi interrotta. Errore: {e}")
			continue
		except Exception:
			import traceback
			print(f"\n! Si è verificato un errore imprevisto alla mossa {ply}. Dettagli:")
			traceback.print_exc()
			continue
	print(f"\n\n{'='*40}\n" + _("Analisi automatica completata.") + f"\n{'='*40}")
	pgn_game.headers["Annotator"] = f'Orologic V{VERSION} (Analisi Automatica)'
	pgn_string_formatted = format_pgn_comments(str(pgn_game))
	base_name = f'{pgn_game.headers.get("White", "B")}_vs_{pgn_game.headers.get("Black", "N")}_auto_{datetime.datetime.now().strftime("%Y%m%d")}'
	sanitized_pgn_name = sanitize_filename(base_name) + ".pgn"
	full_pgn_path = percorso_salvataggio(os.path.join("pgn", sanitized_pgn_name))
	try:
		with open(full_pgn_path, "w", encoding="utf-8-sig") as f:
			f.write(pgn_string_formatted)
		print(_("PGN analizzato salvato come: {path}").format(path=full_pgn_path))
	except Exception as e:
		print(_("Errore durante il salvataggio del PGN: {e}").format(e=e))
	genera_sommario_analitico_txt(pgn_game, base_name, imprecision_stats, cpl_data, last_valid_eco_entry)
	print(_("Ritorno al menù principale."))

def AnalyzeGame(pgn_game):
	"""
	Funzione di analisi della partita (PGN).
	Legge le annotazioni NAG durante la navigazione.
	"""
	print(_("\nModalità analisi.\nHeaders della partita:\n"))
	for k, v in pgn_game.headers.items():
		print("{key}: {value}".format(key=k, value=v))
	move_list = list(pgn_game.mainline_moves())
	total_moves = len(move_list)
	print(_("Numero totale di mosse: {num_moves}").format(num_moves=(total_moves+1)//2))

	if total_moves < 2:
		choice = key(_("\nMosse insufficienti. [M] per tornare al menù o [L] per caricare un nuovo PGN dagli appunti: ")).lower()
		Acusticator(["f5", 0.03, 0, volume], kind=1, adsr=[0,0,100,0])
		if choice == "l":
			new_pgn = LoadPGNFromClipboard()
			if new_pgn:
				AnalyzeGame(new_pgn)
			else:
				print(_("Gli appunti non contengono un PGN valido. Ritorno al menù."))
		return
	print(_("Tempo analisi impostato a {time} secondi.\nLinee riportate dal motore impostate a {multipv}.").format(time=analysis_time, multipv=multipv))
	print(_("\nPremi '?' per la lista dei comandi.\n"))
	saved = False
	comment_auto_read=True
	current_filename = pgn_game.headers.get("Filename", None)
	current_node = pgn_game
	extra_prompt = ""
	while True:
		prompt_move_part = _("Start")
		if current_node.move:
			move_san = current_node.san()
			fullmove = current_node.parent.board().fullmove_number if current_node.parent else 1
			move_indicator = "{move_num}. {san}".format(move_num=fullmove, san=move_san) if current_node.board().turn == chess.BLACK else "{move_num}... {san}".format(move_num=fullmove, san=move_san)

			if current_node.parent and len(current_node.parent.variations) > 1:
				siblings = current_node.parent.variations
				try: # Aggiunto try-except per robustezza se il nodo non è nelle varianti (?)
					idx = siblings.index(current_node)
					if idx == 0 and len(siblings) > 1:
						prompt_move_part = "<{indicator}".format(indicator=move_indicator)
					elif idx > 0 and idx < len(siblings) - 1 :
						prompt_move_part = "<{indicator}>".format(indicator=move_indicator)
					elif idx > 0 and idx == len(siblings) - 1:
						prompt_move_part = "{indicator}>".format(indicator=move_indicator)
					else:
						prompt_move_part = move_indicator
				except ValueError:
					prompt_move_part = move_indicator # Fallback
			else:
				prompt_move_part = move_indicator

		if current_node.move and current_node.comment and not comment_auto_read:
			prompt_move_part += "-"
		prompt = "\n{extra} {move_part}: ".format(extra=extra_prompt, move_part=prompt_move_part)
		extra_prompt = "" # Resetta extra prompt per il prossimo ciclo

		if current_node.comment and comment_auto_read:
			print(_("Commento:"), current_node.comment)
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
					print(_("\nGià all'inizio della partita."))
			else:
				current_node = node
			node_changed = (current_node != previous_node)

		elif cmd == "s":
			if current_node.parent:
				current_node = current_node.parent
				Acusticator(["g5", .03, -.2, volume, "c5", .03, -.8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, -0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print(_("\nNessuna mossa precedente."))
			node_changed = (current_node != previous_node)

		elif cmd == "d":
			if current_node.variations:
				current_node = current_node.variations[0]
				Acusticator(["c5", .03, .2, volume,"g5", .03, .8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, 0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print(_("\nNon ci sono mosse successive."))
			node_changed = (current_node != previous_node)

		elif cmd == "f":
			start_node = current_node
			while current_node.variations:
				current_node = current_node.variations[0]
			node_changed = (current_node != start_node)
			if node_changed:
				Acusticator(["g5", 0.1, 0, volume,"p", 0.1, 0, volume,"c6", 0.05, 0, volume,"d6", 0.05, 0, volume,"g6", 0.2, 0, volume], kind=1, adsr=[5,5,90,5])
				print(_("Sei arrivato alla fine della linea principale."))
			else:
				print(_("Già alla fine della linea principale."))
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
						print(_("Non ci sono varianti precedenti."))
				except ValueError:
					print(_("Errore: nodo corrente non trovato nelle varianti del genitore."))
			else:
				print(_("Nessun nodo variante disponibile (sei alla radice)."))
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
						print(_("Non ci sono varianti successive."))
				except ValueError:
					print(_("Errore: nodo corrente non trovato nelle varianti del genitore."))
			else:
				print(_("Nessun nodo variante disponibile (sei alla radice)."))
			node_changed = (current_node != previous_node)

		elif cmd == "k":
			Acusticator(["g3", 0.06, 0, volume,"b3", 0.06, 0, volume,"a3", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			max_moves_num = (total_moves + 1) // 2
			target_fullmove = dgt(_("\nVai a mossa n.# (Max {max_moves}): ").format(max_moves=max_moves_num), kind="i", imin=1, imax=max_moves_num)
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
					print(_("\nRaggiunta la fine della linea prima della mossa richiesta."))

			current_node = found_node
			Acusticator(["g6", 0.06, 0, volume,"b6", 0.06, 0, volume,"a6", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			node_changed = (current_node != previous_node)
			if node_changed and not current_node.move and target_ply > 0: # Siamo andati oltre l'ultima mossa
				pass # Messaggio stampato nel loop sopra
			elif not node_changed:
				print(_("\nSei già a questa mossa/posizione."))
		elif cmd == "j":
			Acusticator(["d5", 0.08, 0, volume,"p", 0.08, 0, volume,"d6", 0.06, 0, volume], kind=1, adsr=[2,5,90,5])
			print(_("\nHeader della partita:"))
			for k, v in pgn_game.headers.items():
				print("{key}: {value}".format(key=k, value=v))
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
					print(_("\nNuovo PGN caricato dagli appunti."))
					print(_("\nHeaders della nuova partita:\n"))
					for k, v in pgn_game.headers.items():
						print("{key}: {value}".format(key=k, value=v))
					print(_("Numero totale di mosse: {num_moves}").format(num_moves=(total_moves+1)//2))
				# else: LoadPGNFromClipboard stampa già i messaggi
			except Exception as e:
				print(_("\nErrore nel caricamento dagli appunti:"), e)
		elif cmd == "z":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print(_("\nCalcolo bestline..."))
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
						first_new_node.comment = ((first_new_node.comment or "") + _(" {Bestline aggiunta}")).strip()
					saved = True; print(_("Bestline aggiunta/aggiornata come variante."))
					Acusticator(["a5", 0.12, 0.3, volume,"b5", 0.12, 0.3, volume,"c6", 0.12, 0.3, volume,"d6", 0.12, 0.3, volume,"e6", 0.12, 0.3, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(_("\nErrore durante l'aggiunta della variante: {error}").format(error=e)); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); print(_("\nImpossibile calcolare la bestline."))
		elif cmd == "x":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print(_("\nCalcolo bestmove..."))
			bestmove_uci = CalculateBest(current_node.board(), bestmove=True, as_san=False)
			if bestmove_uci:
				try:
					san_move = current_node.board().san(bestmove_uci)
					current_node.comment = ((current_node.comment or "").strip() + " {{BM: {san}}}".format(san=san_move)).strip()
					saved = True; print(_("\nBestmove ({san}) aggiunta al commento.").format(san=san_move))
					Acusticator(["a5", 0.15, 0, volume,"d6", 0.15, 0, volume], kind=1, adsr=[3,7,88,2])
				except Exception as e: print(_("\nErrore nell'ottenere SAN per bestmove: {error}").format(error=e)); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print(_("\nImpossibile calcolare la bestmove."))
		elif cmd == "c":
			Acusticator(["d6", 0.012, 0, volume, "p", 0.15,0,0,"a6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			user_comment = dgt(_("\nInserisci il commento: "), kind="s").strip()
			if user_comment:
				if current_node.comment:
					current_node.comment += user_comment
				else:
					current_node.comment = user_comment
				saved = True; print(_("\nCommento aggiunto/aggiornato."))
				Acusticator(["a6", 0.012, 0, volume, "p", 0.15,0,0,"d6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			else: print(_("\nNessun commento inserito."))
		elif cmd == "v":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print(_("\nCalcolo valutazione..."))
			score_object = CalculateEvaluation(current_node.board())
			if score_object is not None:
				eval_val_str = "ERR"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_val_str = "M{moves}".format(moves=abs(mate_in))
				else:
					# --- USA SCORE ASSOLUTO ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_val_str = "{cp:+.2f}".format(cp=cp/100) # Valore assoluto per il commento
				eval_comment = "{{Val: {eval_str}}}".format(eval_str=eval_val_str)
				current_node.comment = ((current_node.comment or "").strip() + " {comment}".format(comment=eval_comment)).strip()
				saved = True; print(_("\nValutazione ({eval_str}) aggiunta al commento.").format(eval_str=eval_val_str))
				Acusticator(["g5", 0.07, 0, volume,"p", 0.04, 0, volume,"b5", 0.025, 0, volume], kind=1, adsr=[3,7,88,2])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print(_("\nImpossibile calcolare la valutazione."))		
		elif cmd == "b":
			if comment_auto_read:
				comment_auto_read = False
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b4", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print(_("\nLettura automatica dei commenti disabilitata."))
			else:
				comment_auto_read = True
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b6", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print(_("\nLettura automatica dei commenti abilitata."))
		elif cmd == "n":
			if current_node.comment:
				Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
				confirm = key(_("\nEliminare il commento: '{comment}'? (s/n): ").format(comment=current_node.comment)).lower()
				if confirm == "s":
					current_node.comment = ""; saved = True; print(_("Commento eliminato."))
					Acusticator(["e4", 0.1, -0.4, volume], kind=1, adsr=[5,10,70,15])
				else: print(_("Eliminazione annullata."))
			else: Acusticator(["b3", 0.12, -0.4, volume], kind=2, adsr=[5, 15, 20, 60]); print(_("\nNessun commento da eliminare."))
		elif cmd == "q":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print(_("\nCalcolo bestmove..."))
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
								score_info_str = "M{moves}".format(moves=abs(mate_in))
							else:
								# --- USA SCORE ASSOLUTO ---
								cp = score_object.white().score(mate_score=30000)
								if cp is not None:
									score_info_str = "{cp:+.2f}".format(cp=cp/100)
								else:
									score_info_str = "ERR"
				try:
					san_move = current_node.board().san(bestmove_uci)
					desc_move = DescribeMove(bestmove_uci, current_node.board(), annotation=None)
					print(_("\nMossa migliore: ")+desc_move)
					if score_info_str:
						extra_prompt = " BM: {score} {san} ".format(score=score_info_str, san=san_move)
					else:
						extra_prompt = " BM: {san} ".format(san=san_move)
					Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(_("\nErrore nell'ottenere SAN/Descr per bestmove: {error}").format(error=e)); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); extra_prompt = _(" BM: Errore ")
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print(_("\nImpossibile calcolare la bestmove.")); extra_prompt = _(" BM: N/A ")		
		elif cmd == "w":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print(_("\nCalcolo bestline..."))
			bestline_list_descr = CalculateBest(current_node.board(), bestmove=False, as_san=True)
			if bestline_list_descr:
				Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume,"p", .15, 0, 0,"e7", 0.02, 0, volume,"p", .15, 0, 0,"g7", 0.02, 0, volume,"p", .15, 0, 0,"b7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				print(_("\nLinea migliore:")); [print(line) for line in bestline_list_descr]
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
								score_info_str = "M{moves}".format(moves=abs(mate_in))
							else:
								# --- USA SCORE ASSOLUTO ---
								cp = score_object.white().score(mate_score=30000)
								if cp is not None:
									score_info_str = "{cp:+.2f}".format(cp=cp/100)
								else:
									score_info_str = "ERR"
						if best_move_obj:
							try: san_move_w = current_node.board().san(best_move_obj)
							except Exception: san_move_w = "Err"
						else: san_move_w = "N/A"
				if san_move_w != "N/A" and san_move_w != "Err":
					if score_info_str:
						extra_prompt = " BM: {score} {san} ".format(score=score_info_str, san=san_move_w)
					else:
						extra_prompt = " BM: {san} ".format(san=san_move_w)
				else:
					extra_prompt = " BM: {san} ".format(san=san_move_w)
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print(_("\nImpossibile calcolare la bestline.")); extra_prompt = _(" BM: N/A ")		
		elif cmd == "e":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print(_("\nCalcolo linee di analisi...")); fen = current_node.board().fen()
			cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
			analysis = cache_analysis[fen]
			if not analysis: print(_("Nessun risultato di analisi disponibile.")); continue
			main_info = analysis[0]; score = main_info.get("score"); wdl = None; wdl_str = "N/A"; score_str = "N/A"
			if score is not None:
				if hasattr(score, "wdl"): wdl_raw = score.wdl(); wdl = (wdl_raw[0]/10, wdl_raw[1]/10, wdl_raw[2]/10) if wdl_raw else None; wdl_str = "{win:.1f}%/{draw:.1f}%/{loss:.1f}%".format(win=wdl[0], draw=wdl[1], loss=wdl[2]) if wdl else "N/A"
				if score.white().is_mate(): score_str = "M{mate}".format(mate=score.white().mate())
				else: score_cp = score.white().score(); score_str = "{cp:+.2f}".format(cp=score_cp/100) if score_cp is not None else "N/A"
			depth = main_info.get("depth", "N/A"); seldepth = main_info.get("seldepth", "N/A"); nps = main_info.get("nps", "N/A"); hashfull = main_info.get("hashfull", "N/A"); hashfull_perc = "{perc:.1f}%".format(perc=hashfull/10) if isinstance(hashfull, int) else "N/A"; debug_string = main_info.get("string", "N/A"); tbhits = main_info.get("tbhits", "N/A"); time_used = main_info.get("time", "N/A"); nodes = main_info.get("nodes", "N/A")
			Acusticator(["f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume], kind=1, adsr=[4,8,85,5])
			print(_("\nStatistiche: Tempo: {time}s, Hash: {hash}, TB: {tb}\nDebug: {debug}\nProfondità: {depth}/{seldepth}, Val: {score}, WDL: {wdl}\nNodi: {nodes}, NPS: {nps}\n\nLinee di analisi:").format(time=time_used, hash=hashfull_perc, tb=tbhits, debug=debug_string, depth=depth, seldepth=seldepth, score=score_str, wdl=wdl_str, nodes=nodes, nps=nps))
			for i, info in enumerate(analysis, start=1):
				pv = info.get("pv", []); line_score = info.get("score"); line_score_str = "N/A"
				if line_score: line_score_str = "M{mate}".format(mate=line_score.white().mate()) if line_score.white().is_mate() else "{cp:+.2f}".format(cp=line_score.white().score()/100) if line_score.white().score() is not None else "N/A"
				if not pv: print(_("Linea {i} ({score}): Nessuna mossa trovata.").format(i=i, score=line_score_str)); continue
				temp_board_pv = current_node.board().copy(); moves_san = []
				try:
					for move in pv: san_move = temp_board_pv.san(move).replace("!", "").replace("?",""); moves_san.append(san_move); temp_board_pv.push(move)
					print(_("Linea {i} ({score}): {moves}").format(i=i, score=line_score_str, moves=' '.join(moves_san)))
				except Exception as e_pv: print(_("Linea {i} ({score}): Errore conversione PV - {error}").format(i=i, score=line_score_str, error=e_pv))
			smart = key(_("\nVuoi ispezionare le linee in modalità smart? (s/n): ")).lower()
			if smart == "s": Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0]); SmartInspection(analysis, current_node.board())
			else: Acusticator(["d4", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
		elif cmd == "r":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2]); extra_prompt = _(" CP: N/A "); continue
			print(_("\nCalcolo valutazione..."))
			score_object = CalculateEvaluation(current_node.board())
			Acusticator(["e5",.008,-1,volume])
			if score_object is not None:
				eval_str = "N/A"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_str = "M{moves}".format(moves=abs(mate_in))
				else:
					# --- USA SCORE ASSOLUTO ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_str = "{cp:+.2f}".format(cp=cp/100)
					else:
						eval_str = "ERR"
				extra_prompt = " CP: {eval} ".format(eval=eval_str)
				Acusticator(["g3", 0.17, 0, volume,"g6",.012,0,volume], kind=1, adsr=[3,0,90,2])
			else:
				print(_("\nImpossibile calcolare la valutazione."))
				extra_prompt = _(" CP: N/A ")
				Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2])		
		elif cmd == "t":
			if ENGINE is None: print(_("\nMotore non inizializzato.")); Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3]); extra_prompt = _(" WDL: N/A "); continue
			print(_("\nCalcolo WDL...")); wdl_perc = CalculateWDL(current_node.board())
			if wdl_perc: adj_wdl="W{win:.1f}%/D{draw:.1f}%/L{loss:.1f}% ".format(win=wdl_perc[0], draw=wdl_perc[1], loss=wdl_perc[2]); extra_prompt="{wdl} ".format(wdl=adj_wdl); Acusticator(["g#5", 0.03, 0, volume,"c6", 0.03, 0, volume,"g#5", 0.03, 0, volume,"c6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
			else: print(_("\nImpossibile calcolare WDL.")); extra_prompt = _(" WDL: N/A "); Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "y":
			white_material, black_material = CalculateMaterial(current_node.board()); extra_prompt = "Mtrl: {white}/{black} ".format(white=white_material, black=black_material)
			Acusticator(["g#5", 0.03, 0, volume,"e5", 0.03, 0, volume,"d5", 0.03, 0, volume,"g6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "u":
			custom_board_view = CustomBoard(current_node.board().fen())
			if len(current_node.board().move_stack) > 0: custom_board_view.move_stack = current_node.board().move_stack
			custom_board_view.turn = current_node.board().turn; custom_board_view.fullmove_number = current_node.board().fullmove_number
			print("\n" + str(custom_board_view)); Acusticator(["d6", 0.03, 0, volume,"f6", 0.03, 0, volume,"g6", 0.03, 0, volume,"d7", 0.06, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "i":
			print(_("\nTempo analisi: {time}s. Cache: {cache_len} posizioni.").format(time=analysis_time, cache_len=len(cache_analysis)))
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_time_input = dgt(_("\nNuovo tempo (secondi) o INVIO: "), kind="f", fmin=0.1, fmax=300, default=analysis_time)
			if new_time_input != analysis_time: SetAnalysisTime(new_time_input); print(_("\nTempo di analisi aggiornato.")); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print(_("\nTempo di analisi non modificato."))
		elif cmd == "o":
			print(_("\nLinee analisi: {multipv}. Cache: {cache_len} posizioni.").format(multipv=multipv, cache_len=len(cache_analysis)))
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_lines = dgt(_("Nuovo numero linee o INVIO: "), kind="i",imin=1,imax=10, default=multipv)
			if new_lines != multipv: SetMultipv(new_lines); print(_("\nNumero di linee aggiornato.")); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print(_("\nNumero di linee non modificato."))
		elif cmd == "?":
			print(_("\nComandi disponibili in modalità analisi:")); menu(ANALYSIS_COMMAND,show_only=True)
			Acusticator(["d5", .7, 0, volume], kind=3, adsr=[.02,0,100,99])
		else: # Comando non riconosciuto
			Acusticator(["d3", 1.2, 0, volume], kind=3, adsr=[.02,0,100,99])
			print(_("Comando non riconosciuto."))
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
	print(_("\nFine analisi"))
	annotator_updated_flag = False
	if saved:
		new_annotator = 'Orologic V{version} by {programmer}'.format(version=VERSION, programmer=PROGRAMMER)
		current_annotator = pgn_game.headers.get("Annotator", "")
		if current_annotator != new_annotator:
			pgn_game.headers["Annotator"] = new_annotator
			annotator_updated_flag = True
			print(_("\nAnnotator aggiornato."))
	pgn_string_raw = ""
	try:
		pgn_string_raw = str(pgn_game)
		if not pgn_string_raw:
			print(_("!!!!!!!! ATTENZIONE: str(pgn_game) ha restituito una stringa vuota! !!!!!!!!"))
	except Exception as e_str_export:
		pgn_string_raw = ""
	pgn_string_formatted = ""
	exception_occurred_format = False
	if pgn_string_raw and isinstance(pgn_string_raw, str):
		try:
			pgn_string_formatted = format_pgn_comments(pgn_string_raw)
		except Exception as e_format:
			exception_occurred_format = True
			pgn_string_formatted = ""
	else:
		print(_("Attenzione: Stringa PGN grezza vuota o non valida, formattazione saltata."))
	if saved:
		if pgn_string_formatted:
			white_h = pgn_game.headers.get("White", _("Bianco")).replace(" ", "_")
			black_h = pgn_game.headers.get("Black", _("Nero")).replace(" ", "_")
			result_h = pgn_game.headers.get("Result", "*").replace("/", "-")
			new_default_file_name='{white}_vs_{black}_{result}'.format(white=white_h, black=black_h, result=result_h)
			base_name = dgt(_("\nSalva PGN modificato.\nNome base (INVIO per '{default_name}'): ").format(default_name=new_default_file_name), kind="s",default=new_default_file_name).strip()
			if not base_name: base_name = new_default_file_name
			Acusticator(["f4", 0.05, 0, volume])
			new_filename_base = "{base}-analizzato-{timestamp}".format(base=base_name, timestamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
			sanitized_name = sanitize_filename(new_filename_base) + ".pgn"
			full_path = percorso_salvataggio(os.path.join("pgn", sanitized_name))
			try:
				with open(full_path, "w", encoding="utf-8-sig") as f:
					f.write(pgn_string_formatted)
				print(_("PGN aggiornato salvato come ") + full_path)
				if annotator_updated_flag: print(_("Header Annotator è stato aggiornato nel file."))
			except Exception as e_save:
				print(_("Errore durante il salvataggio del PGN: {error}").format(error=e_save))
		else:
			print(_("Impossibile salvare il file PGN a causa di errori durante la generazione/formattazione."))
	else:
		print(_("\nNon sono state apportate modifiche salvabili al PGN."))
	if pgn_string_formatted:
		try:
			pyperclip.copy(pgn_string_formatted)
			print(_("PGN attuale (formattato) copiato negli appunti."))
		except Exception as e_clip:
			print(_("Errore durante la copia del PGN (formattato) negli appunti: {error}").format(error=e_clip))
	else:
		print(_("Nessun PGN formattato da copiare negli appunti."))
	print(_("Uscita dalla modalità analisi. Ritorno al menù principale."))

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
	return "{piece} {color}".format(piece=piece_name, color=color_adj)

def read_diagonal(game_state, base_column, direction_right):
	"""
	Legge la diagonale a partire dalla casa sulla traversa 1 della colonna base.
	Il parametro direction_right:
		- True: direzione alto-destra (file +1, traversa +1)
		- False: direzione alto-sinistra (file -1, traversa +1)
	"""
	base_column = base_column.lower()
	if base_column not in "abcdefgh":
		print(_("Colonna base non valida."))
		return
	file_index = ord(base_column) - ord("a")
	rank_index = 0  # partiamo da traversa 1 (indice 0)
	report = []
	# NUOVA LOGICA
	base_descr = "{col} 1".format(col=L10N['columns'].get(base_column, base_column))
	while 0 <= file_index < 8 and 0 <= rank_index < 8:
		square = chess.square(file_index, rank_index)
		piece = game_state.board.piece_at(square)
		if piece:
			current_file = chr(ord("a") + file_index)
			# NUOVA LOGICA
			descriptive_file = L10N['columns'].get(current_file, current_file)
			report.append("{file} {rank}: {piece_desc}".format(file=descriptive_file, rank=rank_index+1, piece_desc=extended_piece_description(piece)))
		rank_index += 1
		file_index = file_index + 1 if direction_right else file_index - 1
	dir_str = _("alto-destra") if direction_right else _("alto-sinistra")
	if report:
		print(_("Diagonale da {base} in direzione {direction}: ").format(base=base_descr, direction=dir_str) + ", ".join(report))
	else:
		print(_("Diagonale da {base} in direzione {direction} non contiene pezzi.").format(base=base_descr, direction=dir_str))

def read_rank(game_state, rank_number):
	try:
		rank_bb = getattr(chess, "BB_RANK_{rank}".format(rank=rank_number))
	except AttributeError:
		print(_("Traversa non valida."))
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
			report.append("{file} {rank}: {piece_desc}".format(file=descriptive_file, rank=rank_number, piece_desc=extended_piece_description(piece)))
	if report:
		print(_("Traversa {rank}: ").format(rank=rank_number) + ", ".join(report))
	else:
		print(_("La traversa {rank} è vuota.").format(rank=rank_number))

def read_file(game_state, file_letter):
	file_letter = file_letter.lower()
	if file_letter not in "abcdefgh":
		print(_("Colonna non valida."))
		return
	try:
		file_bb = getattr(chess, "BB_FILE_{file}".format(file=file_letter.upper()))
	except AttributeError:
		print(_("Colonna non valida."))
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
			report.append("{file} {rank}: {piece_desc}".format(file=file_letter_descr, rank=rank, piece_desc=extended_piece_description(piece)))
	# NUOVA LOGICA
	col_name = L10N['columns'].get(file_letter, file_letter)
	if report:
		print(_("Colonna {col_name}: ").format(col_name=col_name) + ", ".join(report))
	else:
		print(_("La colonna {col_name} è vuota.").format(col_name=col_name))

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
			
			descriptions.append(_("{piece_desc} in {col_name} {rank_name}").format(piece_desc=piece_desc, col_name=col_name, rank_name=rank_name))
	return descriptions

def read_square(game_state, square_str):
	"""
	Fornisce una descrizione dettagliata di una casa, elencando i pezzi
	che la occupano, la difendono o la attaccano.
	"""
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print(_("Casa non valida."))
		return
	# La logica per il colore della casa rimane invariata
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = _("scura")
	else:
		color_descr = _("chiara")
	piece = game_state.board.piece_at(square)
	
	final_parts = []
	if piece:
		# --- Logica per casa occupata ---
		base_msg = _("La casa {square} è {color} e contiene {piece_desc}.").format(square=square_str.upper(), color=color_descr, piece_desc=extended_piece_description(piece))
		final_parts.append(base_msg)
		defenders_squares = game_state.board.attackers(piece.color, square)
		if defenders_squares:
			defender_descs = _get_piece_descriptions_from_squareset(game_state.board, defenders_squares)
			final_parts.append(_("difesa da: {defenders}").format(defenders=', '.join(defender_descs)))
		attackers_squares = game_state.board.attackers(not piece.color, square)
		if attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, attackers_squares)
			final_parts.append(_("attaccata da: {attackers}").format(attackers=', '.join(attacker_descs)))
	else:
		# --- Logica per casa vuota ---
		base_msg = _("La casa {square} è {color} e risulta vuota.").format(square=square_str.upper(), color=color_descr)
		final_parts.append(base_msg)
		white_attackers_squares = game_state.board.attackers(chess.WHITE, square)
		if white_attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, white_attackers_squares)
			final_parts.append(_("attaccata dal Bianco con: {attackers}").format(attackers=', '.join(attacker_descs)))
		black_attackers_squares = game_state.board.attackers(chess.BLACK, square)
		if black_attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, black_attackers_squares)
			final_parts.append(_("attaccata dal Nero con: {attackers}").format(attackers=', '.join(attacker_descs)))
	# Assembla la frase finale
	print(" ".join(final_parts).replace(" .", ".").strip() + ".")

def report_piece_positions(game_state, piece_symbol):
	try:
		piece = chess.Piece.from_symbol(piece_symbol)
	except Exception as e:
		print(_("Non riconosciuto: inserisci R N B Q K P, r n b q k p"))
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
		positions.append("{file} {rank}".format(file=descriptive_file, rank=rank))
	if positions:
		print("{color}: {name} in: ".format(color=color_string.capitalize(), name=full_name) + ", ".join(positions))
	else:
		print(_("Nessun {name} {color} trovato.").format(name=full_name, color=color_string))

def report_white_time(game_state):
	initial_white = game_state.clock_config["phases"][game_state.white_phase]["white_time"]
	elapsed_white = initial_white - game_state.white_remaining
	if elapsed_white < 0:
		elapsed_white = 0
	perc_white = (elapsed_white / initial_white * 100) if initial_white > 0 else 0
	print(_("Tempo bianco: ") + FormatTime(game_state.white_remaining) + " ({perc:.0f}%)".format(perc=perc_white))
	return

def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	if elapsed_black < 0:
		elapsed_black = 0
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print(_("Tempo nero: ") + FormatTime(game_state.black_remaining) + " ({perc:.0f}%)".format(perc=perc_black))
	return

def save_text_summary(game_state, descriptive_moves, eco_entry):
	"""
	Genera e salva un riepilogo testuale della partita.
	"""
	headers = game_state.pgn_game.headers
	# 1. Intestazioni (Headers) leggibili
	header_text = _("Riepilogo Partita di Orologic\n")
	header_text += "--------------------------------\n"
	header_text += _("Evento: {event}\n").format(event=headers.get('Event', _('N/D')))
	header_text += _("Sede: {site}\n").format(site=headers.get('Site', _('N/D')))
	header_text += _("Data: {date}\n").format(date=headers.get('Date', _('N/D')))
	header_text += _("Round: {round}\n").format(round=headers.get('Round', _('N/D')))
	header_text += _("Bianco: {white} ({elo})\n").format(white=headers.get('White', _('N/D')), elo=headers.get('WhiteElo', _('N/A')))
	header_text += _("Nero: {black} ({elo})\n").format(black=headers.get('Black', _('N/D')), elo=headers.get('BlackElo', _('N/A')))
	white_clock = headers.get('WhiteClock', _('N/D'))
	black_clock = headers.get('BlackClock', _('N/D'))
	header_text += _("Tempo finale Bianco: {clock}\n").format(clock=white_clock)
	header_text += _("Tempo finale Nero: {clock}\n").format(clock=black_clock)
	header_text += _("Controllo del Tempo: {tc}\n").format(tc=headers.get('TimeControl', _('N/D')))
	# 2. Informazioni sull'apertura
	if eco_entry:
		opening_text = _("Apertura: {eco} - {opening}").format(eco=eco_entry.get('eco', ''), opening=eco_entry.get('opening', ''))
		if eco_entry.get('variation'):
			opening_text += " ({variation})\n".format(variation=eco_entry.get('variation'))
		else:
			opening_text += "\n"
	else:
		opening_text = _("Apertura: non rilevata\n")
	header_text += opening_text
	header_text += "--------------------------------\n\n"
	# 3. Lista delle mosse
	move_list_text = _("Lista Mosse:\n")
	move_number = 1
	i = 0
	while i < len(descriptive_moves):
		white_move_desc = descriptive_moves[i]
		if i + 1 < len(descriptive_moves):
			black_move_desc = descriptive_moves[i+1]
			move_list_text += "{num}. {white_move}, {black_move}\n".format(num=move_number, white_move=white_move_desc, black_move=black_move_desc)
			i += 2
		else:
			move_list_text += "{num}. {white_move}\n".format(num=move_number, white_move=white_move_desc)
			i += 1
		move_number += 1
	# 4. Risultato e data di generazione
	footer_text = _("\nRisultato finale: {result}\n").format(result=headers.get('Result', '*'))
	footer_text += "--------------------------------\n"
	footer_text += _("File generato il: {datetime}\n").format(datetime=datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
	footer_text += _("Report generato da Orologic V{version} - {programmer}\n").format(version=VERSION, programmer=PROGRAMMER)
	# Combinazione di tutte le parti
	full_text = header_text + move_list_text + footer_text
	# Creazione del nome del file (riutilizzando la logica del PGN)
	base_filename = "{white}-{black}-{result}-{timestamp}".format(white=headers.get('White', _('Bianco')), black=headers.get('Black', _('Nero')), result=headers.get('Result', '*'), timestamp=datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
	sanitized_name = sanitize_filename(base_filename) + ".txt"
	full_path = percorso_salvataggio(os.path.join("txt", sanitized_name))
	try:
		with open(full_path, "w", encoding="utf-8") as f:
			f.write(full_text)
		print(_("Riepilogo partita salvato come {filename}.").format(filename=full_path))
	except Exception as e:
		print(_("Errore durante il salvataggio del riepilogo testuale: {error}").format(error=e))
		Acusticator(["a3", 1, 0, volume], kind=2, adsr=[0, 0, 100, 100])

def genera_sommario_analitico_txt(pgn_game, base_filename, imprecision_stats, cpl_data, eco_entry):
	"""
	Legge un PGN analizzato e produce un file di testo descrittivo con formattazione avanzata.
	"""
	summary_lines = []
	headers = pgn_game.headers
	white_name = headers.get("White", "Bianco").replace(',', ' ').split()[-1]
	black_name = headers.get("Black", "Nero").replace(',', ' ').split()[-1]
	summary_lines.append(_("Riepilogo Analisi Automatica di Orologic V.{version}").format(version=VERSION))
	summary_lines.append("="*40)
	for key, value in headers.items():
		if key in ["WhiteClock", "BlackClock"]:
			continue # Salta questi header
		if key == "TimeControl":
			try:
				# Formatta il TimeControl da secondi a stringa descrittiva
				summary_lines.append(f"{key}: {FormatTime(int(value))}")
			except:
				summary_lines.append(f"{key}: {value}") # Fallback
		else:
			summary_lines.append(f"{key}: {value}")
	summary_lines.append("="*40)
	if eco_entry:
		opening_line = f"{eco_entry.get('eco', '')} - {eco_entry.get('opening', '')}"
		if eco_entry.get('variation'):
			opening_line += f", {eco_entry.get('variation')}"
		summary_lines.append(_("Apertura: ") + opening_line)
	summary_lines.append(_("Nota: [OAA] (Orologic Analisi Automatica) indica un commento generato dall'app in base ai parametri forniti."))
	summary_lines.append("="*40)
	summary_lines.append(_("Quadro Riepilogativo delle Imprecisioni"))
	summary_lines.append("-"*48)
	header_fmt = "| {:<12} | {:^10} | {:^10} | {:^10} |".format(_("Tipo"), white_name, black_name, _("Diff."))
	summary_lines.append(header_fmt)
	summary_lines.append("-"*48)
	for err_type in ["Svarione", "Errore", "Inesattezza"]:
		w_count = imprecision_stats[err_type]['w']
		b_count = imprecision_stats[err_type]['b']
		diff = w_count - b_count
		row_fmt = "| {:<12} | {:^10} | {:^10} | {:^+10} |".format(
			_(err_type), w_count, b_count, diff
		)
		summary_lines.append(row_fmt)
	summary_lines.append("-"*48)
	
	# Tabella ACPL
	# **BUG FIX**: La moltiplicazione per 100 era un errore, i 'loss' sono già in centipawn. La rimuovo.
	summary_lines.append(_("\nAverage Centipawn Loss (ACPL) per Fase"))
	summary_lines.append("-"*48)
	header_acpl_fmt = "| {:<12} | {:^10} | {:^10} | {:^10} |".format(_("Fase Partita"), white_name, black_name, _("Diff."))
	summary_lines.append(header_acpl_fmt)
	summary_lines.append("-"*48)

	# Calcolo valori ACPL per entrambi i giocatori
	w_cpls = cpl_data.get('w', [])
	b_cpls = cpl_data.get('b', [])
	w_num_moves = len(w_cpls)
	b_num_moves = len(b_cpls)

	fasi = []
	if w_num_moves > 2 and b_num_moves > 2:
		# Calcolo per 3 fasi
		w_s1, w_s2 = w_num_moves // 3, 2 * (w_num_moves // 3)
		b_s1, b_s2 = b_num_moves // 3, 2 * (b_num_moves // 3)
		fasi.append( (f"Mosse 1-{w_s1}", w_cpls[:w_s1], b_cpls[:b_s1]) )
		fasi.append( (f"Mosse {w_s1+1}-{w_s2}", w_cpls[w_s1:w_s2], b_cpls[b_s1:b_s2]) )
		fasi.append( (f"Mosse {w_s2+1}-{w_num_moves}", w_cpls[w_s2:], b_cpls[b_s2:]) )
	else:
		# Calcolo totale per partite brevi
		fasi.append( ("Totale", w_cpls, b_cpls) )
	
	for nome_fase, w_fase_cpls, b_fase_cpls in fasi:
		w_avg = sum(w_fase_cpls) / len(w_fase_cpls) if w_fase_cpls else 0
		b_avg = sum(b_fase_cpls) / len(b_fase_cpls) if b_fase_cpls else 0
		diff_acpl = w_avg - b_avg
		row_acpl_fmt = "| {:<12} | {:^10.2f} | {:^10.2f} | {:^+10.2f} |".format(
			nome_fase, w_avg, b_avg, diff_acpl
		)
		summary_lines.append(row_acpl_fmt)
	summary_lines.append("-"*48)
	summary_lines.append("="*40)

	# --- TITOLO LISTA MOSSE ---
	summary_lines.append("\n" + _("--- Lista Mosse ---"))
	summary_lines.append("="*40)
	def _format_variations(node_with_variations, indent_level=1):
		if len(node_with_variations.variations) <= 1:
			return
		indent = "\t" * indent_level
		variant_counter = 1
		for variation_node in node_with_variations.variations[1:]:
			line_parts = []
			line_parts.append(DescribeMove(variation_node.move, variation_node.parent.board()))
			if variation_node.comment:
				comment = variation_node.comment.replace("{", "").replace("}", "").strip()
				line_parts.append(f"({comment})")
			
			temp_node = variation_node
			for i in range(5):
				if not temp_node.variations: break
				temp_node = temp_node.variations[0]
				line_parts.append(DescribeMove(temp_node.move, temp_node.parent.board()))
			summary_lines.append(f"{indent}↳ {_('Variante')} {variant_counter}: " + ", ".join(line_parts))
			# Chiamata ricorsiva per le sotto-varianti del nodo appena stampato
			_format_variations(variation_node, indent_level + 1)
			variant_counter += 1
	# Ciclo principale
	mainline_nodes = list(pgn_game.mainline())
	i = 0
	while i < len(mainline_nodes):
		white_node = mainline_nodes[i]
		black_node = mainline_nodes[i+1] if (i + 1) < len(mainline_nodes) else None
		
		has_annotations = (white_node.comment or (black_node and black_node.comment) or
						   len(white_node.parent.variations) > 1 or
						   (black_node and len(black_node.parent.variations) > 1))

		white_desc = DescribeMove(white_node.move, white_node.parent.board())
		move_num_str = f"{white_node.board().fullmove_number}."

		if not has_annotations and black_node:
			black_desc = DescribeMove(black_node.move, black_node.parent.board())
			# --- MODIFICA 1 ---
			summary_lines.append(f"{move_num_str} {white_name}: {white_desc}, {black_name}: {black_desc}")
			i += 2
		else:
			# --- MODIFICA 2 ---
			summary_lines.append(f"\n{move_num_str} {white_name}: {white_desc}")
			# Passa il NODO PADRE alla funzione, che ne analizzerà i figli (le varianti)
			_format_variations(white_node.parent)
			
			if black_node:
				black_desc = DescribeMove(black_node.move, black_node.parent.board())
				# --- MODIFICA 3 ---
				summary_lines.append(f"{move_num_str}... {black_name}: {black_desc}")
				_format_variations(black_node.parent)
			i += 2 if black_node else 1
	# --- Riepilogo Finale ---
	summary_lines.append("\n" + "="*40)
	result = headers.get("Result", "*")
	result_desc = f"Risultato finale: {result}" # Default
	if result == "1-0":
		result_desc = f"Vince {white_name} (1-0)."
	elif result == "0-1":
		result_desc = f"Vince {black_name} (0-1)."
	elif result == "1/2-1/2":
		result_desc = "Partita patta (1/2-1/2)."
	summary_lines.append(result_desc)
	try:
		# I tempi sono salvati come stringa HH:MM:SS, li parsiamo in secondi per ri-formattarli
		white_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], headers.get("WhiteClock", "0:0:0").split(":")))
		black_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], headers.get("BlackClock", "0:0:0").split(":")))
		summary_lines.append(_("Tempo finale {name}: {time}").format(name=white_name, time=FormatTime(white_seconds)))
		summary_lines.append(_("Tempo finale {name}: {time}").format(name=black_name, time=FormatTime(black_seconds)))
	except:
		# Fallback se il parsing fallisce
		summary_lines.append(_("Tempo finale {name}: {time}").format(name=white_name, time=headers.get("WhiteClock", "N/D")))
		summary_lines.append(_("Tempo finale {name}: {time}").format(name=black_name, time=headers.get("BlackClock", "N/D")))
	summary_lines.append("="*40)
	# Salvataggio del file
	full_text = "\n".join(summary_lines)
	sanitized_txt_name = sanitize_filename(base_filename) + ".txt"
	full_txt_path = percorso_salvataggio(os.path.join("txt", sanitized_txt_name))
	
	try:
		with open(full_txt_path, "w", encoding="utf-8") as f:
			f.write(full_text)
		print(_("Riepilogo testuale salvato come: {path}").format(path=full_txt_path))
	except Exception as e:
		print(_("Errore durante il salvataggio del riepilogo testuale: {e}").format(e=e))

def setup_fischer_random_board():
	"""
	Gestisce il processo di setup per una partita Fischer Random (Chess960).
	L'utente può inserire una sequenza, richiederne una casuale ('?'), o annullare ('.').
	Restituisce (None, None) se l'utente annulla.
	"""
	print(_("\n--- Configurazione Fischer Random (Chess960) ---"))
	
	while True:
		prompt = _("\nInserisci la sequenza di 8 pezzi, '?' per una casuale, o '.' per annullare: ")
		user_input = dgt(prompt, kind="s").upper()
		if user_input == '?':
			# --- NUOVA LOGICA PER LA POSIZIONE CASUALE ---
			pos_number = random.randint(0, 959)
			print(_("Generazione posizione casuale numero {pos_num}...").format(pos_num=pos_number))
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
			print(_("Posizione generata: {sequence} (Numero: {number})").format(sequence=piece_sequence, number=pos_number))
			return board_to_return, starting_fen
		elif user_input == '.':
			print(_("Configurazione annullata."))
			return None, None
		elif len(user_input) != 8:
			print(_("Errore: la sequenza deve contenere 8 caratteri. Tu ne hai inseriti {num_chars}.").format(num_chars=len(user_input)))
			Acusticator(["b3", .2, 0, volume], kind=2)
			continue
		# La logica per l'input manuale rimane la stessa
		else:
			fen_to_try = "{sequence}/pppppppp/8/8/8/8/PPPPPPPP/{sequence_upper} w - - 0 1".format(sequence=user_input.lower(), sequence_upper=user_input)
			try:
				board_to_return = CustomBoard(fen_to_try, chess960=True)
				pos_number = board_to_return.chess960_pos()
				Acusticator(["c5", 0.1, -0.8, volume, "e5", 0.1, 0, volume, "g5", 0.2, 0.8, volume], kind=1, adsr=[2, 8, 90, 0])
				print(_("Posizione valida! Numero di riferimento Chess960: {number}").format(number=pos_number))
				return board_to_return, fen_to_try
			except ValueError as e:
				print(_("Errore: Posizione non valida. La libreria riporta: '{error}'").format(error=e))
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
				tc = "{base}+{inc}".format(base=base_time, inc=inc)
			else:
				tc = "{base}".format(base=base_time)
		else:
			# Time control a mosse: includiamo moves, tempo e, se presente, l'incremento
			if inc > 0:
				tc = "{moves}/{base}+{inc}".format(moves=moves, base=base_time, inc=inc)
			else:
				tc = "{moves}/{base}".format(moves=moves, base=base_time)
		tc_list.append(tc)
	return ", ".join(tc_list)
def seconds_to_mmss(seconds):
	m = int(seconds // 60)
	s = int(seconds % 60)
	return _("{minutes:02d} minuti e {seconds:02d} secondi!").format(minutes=m, seconds=s)
def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print(_("Formato orario non valido. Atteso mm:ss. Errore:"), e)
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
				promo_str = "={promo}".format(promo=promo_piece_symbol)
			capture_char = "x" if is_capture else ""
			if piece_symbol:
				san_base = "{symbol}{disambiguation}{capture}{to_sq}{promo}".format(symbol=piece_symbol, disambiguation=disambiguation, capture=capture_char, to_sq=to_sq_str, promo=promo_str)
			else:
				if is_capture:
					san_base = "{from_file}{capture}{to_sq}{promo}".format(from_file=from_sq_str[0], capture=capture_char, to_sq=to_sq_str, promo=promo_str)
				else:
					san_base = "{to_sq}{promo}".format(to_sq=to_sq_str, promo=promo_str)
		except Exception as e:
			try:
				san_base = board.san(move)
				san_base = san_base.replace("!","").replace("?","")
			except Exception:
				san_base = _("Mossa da {from_sq} a {to_sq}").format(from_sq=chess.square_name(move.from_square), to_sq=chess.square_name(move.to_square))
		
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
					descr += " {col}".format(col=L10N['columns'].get(disamb, disamb))
				else:
					parts = [L10N['columns'].get(ch, ch) if ch.isalpha() else ch for ch in disamb]
					descr += _(" di ") + "".join(parts) # "di" potrebbe essere localizzato, ma è un caso più complesso
			if capture:
				descr += " {capture_verb}".format(capture_verb=L10N['moves']['capture'])
				captured_piece = None
				if board.is_en_passant(move):
					ep_square = move.to_square + (-8 if board.turn == chess.WHITE else 8)
					captured_piece = board.piece_at(ep_square)
					descr += " {ep}".format(ep=L10N['moves']['en_passant'])
				else:
					captured_piece = board.piece_at(move.to_square)
				if captured_piece and not board.is_en_passant(move):
					captured_type_key = chess.PIECE_NAMES[captured_piece.piece_type].lower()
					captured_name = L10N['pieces'][captured_type_key]['name']
					descr += " {name}".format(name=captured_name)
				dest_file_info = dest[0]
				dest_rank_info = dest[1]
				dest_name_info = L10N['columns'].get(dest_file_info, dest_file_info)
				descr += " {prep} {file}{rank}".format(prep=L10N['moves']['capture_on'], file=dest_name_info, rank=dest_rank_info)
			else:
				dest_file = dest[0]
				dest_rank = dest[1]
				dest_name = L10N['columns'].get(dest_file, dest_file)
				descr += " {prep} {file}{rank}".format(prep=L10N['moves']['move_to'], file=dest_name, rank=dest_rank)
			if promo_letter:
				promo_type = chess.PIECE_SYMBOLS.index(promo_letter.lower())
				promo_type_key = chess.PIECE_NAMES[promo_type].lower()
				promo_name = L10N['pieces'][promo_type_key]['name']
				descr += " {promo_verb} {promo_name}".format(promo_verb=L10N['moves']['promotes_to'], promo_name=promo_name)
			base_descr = descr
	
	board_after_move = board.copy()
	board_after_move.push(move)
	final_descr = base_descr
	if board_after_move.is_checkmate():
		final_descr += " {checkmate}".format(checkmate=L10N['moves']['checkmate'])
	elif board_after_move.is_check():
		final_descr += " {check}".format(check=L10N['moves']['check'])
	
	# NUOVA LOGICA: Usa L10N per le annotazioni
	if annotation and annotation in L10N['annotations']:
		final_descr += " ({annotation})".format(annotation=L10N['annotations'][annotation])
		
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
			white_move_desc = _("Errore nella mossa del bianco: {error}").format(error=e)
		if i + 1 < len(game_state.move_history):  # Se esiste la mossa del nero
			black_move_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_move_san)
				black_move_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except Exception as e:
				black_move_desc = _("Errore nella mossa del nero: {error}").format(error=e)
			summary.append("{num}. {white_desc}, {black_desc}".format(num=move_number, white_desc=white_move_desc, black_desc=black_move_desc))
		else:
			summary.append("{num}. {white_desc}".format(num=move_number, white_desc=white_move_desc))
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
		print(_("Configurazione lingua non trovata o incompleta, imposto la localizzazione italiana di default."))
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
	db_path = resource_path(os.path.join("resources", filename))
	if not os.path.exists(db_path):
		print(_("File {filename} non trovato.").format(filename=db_path))
		return eco_entries
	try:
		with open(db_path, "r", encoding="utf-8") as f:
			content = f.read()
	except Exception as e:
		print(_("Errore durante la lettura di {filename}: {error}").format(filename=db_path, error=e))
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
				print(_("Attenzione: Impossibile leggere il game PGN {game_num} dopo l'header.").format(game_num=game_count))
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
			print(_("Errore di valore durante il parsing del game PGN {game_num}: {error}").format(game_num=game_count, error=ve))
			skipped_count += 1
			# Prova a recuperare cercando la prossima entry PGN '['
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['): # Trovato un possibile inizio di header
					stream.seek(stream.tell() - len(line.encode('utf-8'))) # Torna indietro
					break
		except Exception as e:
			print(_("Errore generico durante il parsing del game PGN {game_num}: {error}").format(game_num=game_count, error=e))
			skipped_count += 1
			# Tentativo di recupero simile a sopra
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['):
					stream.seek(stream.tell() - len(line.encode('utf-8')))
					break
	print(_("Caricate {num_entries} linee di apertura ECO.").format(num_entries=len(eco_entries)))
	if skipped_count > 0:
		print(_("Attenzione: {num_skipped} linee ECO sono state saltate a causa di errori di parsing.").format(num_skipped=skipped_count))
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
		parts.append("{num} {label}".format(num=h, label=_('ora') if h==1 else _('ore')))
	if m:
		parts.append("{num} {label}".format(num=m, label=_('minuto') if m==1 else _('minuti')))
	if s:
		parts.append("{num} {label}".format(num=s, label=_('secondo') if s==1 else _('secondi')))
	return ", ".join(parts) if parts else _("0 secondi")
def ParseTime(prompt):
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":"))
		return h*3600+m*60+s
	except Exception as e:
		print(_("Formato orario non valido. Atteso hh:mm:ss. Errore:"),e)
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
	print(_("\nCreazione orologi\n"))
	name=dgt(_("Nome dell'orologio: "),kind="s")
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume],sync=True)
	db=LoadDB()
	if any(c["name"]==name for c in db["clocks"]):
		print(_("Un orologio con questo nome esiste già."))
		Acusticator(["a3",1,0,volume],kind=2,adsr=[0,0,100,100])
		return
	same=dgt(_("Bianco e Nero partono con lo stesso tempo? (Invio per sì, 'n' per no): "),kind="s",smin=0,smax=1)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(_("Tempo (hh:mm:ss) per fase {num}: ").format(num=phase_count+1))
			inc=dgt(_("Incremento in secondi per fase {num}: ").format(num=phase_count+1),kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(_("Tempo per il bianco (hh:mm:ss) fase {num}: ").format(num=phase_count+1))
			inc_w=dgt(_("Incremento per il bianco fase {num}: ").format(num=phase_count+1),kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			total_seconds_b=ParseTime(_("Tempo per il nero (hh:mm:ss) fase {num}: ").format(num=phase_count+1))
			inc_b=dgt(_("Incremento per il nero fase {num}: ").format(num=phase_count+1),kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(_("Numero di mosse per fase {num} (0 per terminare): ").format(num=phase_count+1),kind="i")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt(_("Numero di allarmi da inserire (max 5, 0 per nessuno): "),kind="i",imax=5,default=0)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	for i in range(num_alarms):
		alarm_input = dgt(_("Inserisci il tempo (mm:ss) per l'allarme {num}: ").format(num=i+1), kind="s")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt(_("Inserisci una nota per l'orologio (opzionale): "),kind="s",default="")
	Acusticator(["f7", .09, 0, volume,"d5", .07, 0, volume,"p",.1,0,0,"d5", .07, 0, volume,"f7", .09, 0, volume])
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	db["clocks"].append(new_clock.to_dict())
	SaveDB(db)
	print(_("\nOrologio creato e salvato."))
def ViewClocks():
	print(_("\nVisualizzazione orologi\n"))
	db=LoadDB()
	if not db["clocks"]:
		print(_("Nessun orologio salvato."))
		return
	for idx,c in enumerate(db["clocks"]):
		indicatore="B=N" if c["same_time"] else "B/N"
		fasi=""
		for i,phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str=SecondsToHMS(phase["white_time"])
				fasi+=" F{num}:{time}+{inc}".format(num=i+1, time=time_str, inc=phase['white_inc'])
			else:
				time_str_w=SecondsToHMS(phase["white_time"])
				time_str_b=SecondsToHMS(phase["black_time"])
				fasi+=" F{num}: Bianco:{time_w}+{inc_w}, Nero:{time_b}+{inc_b}".format(num=i+1, time_w=time_str_w, inc_w=phase['white_inc'], time_b=time_str_b, inc_b=phase['black_inc'])
		num_alarms = len(c.get("alarms", []))  # Conta gli allarmi
		alarms_str = _(". Allarmi: ({num})").format(num=num_alarms)
		print("{idx}. {name} - {indicator}{phases}{alarms}".format(idx=idx+1, name=c['name'], indicator=indicatore, phases=fasi, alarms=alarms_str))
		if c.get("note",""):
			print("\t{label}: {note}".format(label=_("Nota"), note=c['note']))
	Acusticator(["c5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
	attesa=key(_("Premi un tasto per tornare al menu principale."))
	Acusticator(["a4", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
def SelectClock(db):
	if not db["clocks"]:
		Acusticator(["c3", 0.72, 0, volume], kind=2, adsr=[0,0,100,100])
		print(_("Nessun orologio salvato."))
		return None
	print(_("Ci sono {num_clocks} orologi nella collezione.").format(num_clocks=len(db['clocks'])))
	choices = {}
	for c in db["clocks"]:
		indicatore = "B=N" if c["same_time"] else "B/N"
		fasi = ""
		for j, phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str = SecondsToHMS(phase["white_time"])
				fasi += " F{num}:{time}+{inc}".format(num=j+1, time=time_str, inc=phase['white_inc'])
			else:
				time_str_w = SecondsToHMS(phase["white_time"])
				time_str_b = SecondsToHMS(phase["black_time"])
				fasi += " F{num}: Bianco:{time_w}+{inc_w}, Nero:{time_b}+{inc_b}".format(num=j+1, time_w=time_str_w, inc_w=phase['white_inc'], time_b=time_str_b, inc_b=phase['black_inc'])
		num_alarms = len(c.get("alarms", []))
		alarms_str = _(". Allarmi: ({num})").format(num=num_alarms)
		details_line = "{indicator}{phases}{alarms}".format(indicator=indicatore, phases=fasi, alarms=alarms_str)
		note_line = c.get("note", "")
		display_string = ""
		if STILE_MENU_NUMERICO:
			# Se il menù è NUMERATO, includiamo il nome nel valore da visualizzare.
			display_string = "'{name}' -- {details}".format(name=c["name"], details=details_line)
		else:
			# Se il menù è a PAROLE, NON includiamo il nome, perché verrà mostrato
			# automaticamente dalla funzione menu (che usa la chiave del dizionario).
			display_string = details_line
		# Aggiungiamo la nota alla fine, in entrambi i casi.
		if note_line:
			display_string += "\n  " + note_line
		choices[c["name"]] = display_string
	choice = menu(choices, show=True, keyslist=True, full_keyslist=False, numbered=STILE_MENU_NUMERICO)
	Acusticator(["f7", .013, 0, volume])
	if choice:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == choice), None)
		if idx is not None:
			return db["clocks"][idx]
	print(_("Nessun orologio selezionato o scelta non valida."))
	return None

def DeleteClock(db):
	print(_("\nEliminazione orologi salvati\n"))
	Acusticator(["b4", .02, 0, volume,"d4",.2,0,volume]) 
	orologio = SelectClock(db)
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			prompt_conferma = _("sei sicuro di voler eliminare {nomeorologio}?\nL'azione è irreversibile. Premi invio per sì, qualsiasi altro tasto per no: ").format(nomeorologio=clock_name)
			conferma = key(prompt_conferma).strip()
			if conferma == "":
				del db["clocks"][idx]
				Acusticator(["c4", 0.025, 0, volume])
				SaveDB(db)
				print(_("\nOrologio '{clock_name}' eliminato, ne rimangono {remaining}.").format(clock_name=clock_name, remaining=len(db['clocks'])))
	return

def Impostazioni(db):
	global STILE_MENU_NUMERICO
	prompt_newline = "\n"
	print(_("\nModifica impostazioni varie di Orologic\n"))
	autosave_enabled = db.get("autosave_enabled", False)
	status_autosave = _("Attivo") if autosave_enabled else _("Non attivo")
	prompt_autosave = _("Salvataggio automatico: [{status}]. Premi Invio per cambiare, altro per confermare: ").format(status=status_autosave)
	scelta_autosave = key(prompt_autosave).strip()
	if scelta_autosave == "":
		db["autosave_enabled"] = not autosave_enabled
	# --- Blocco per lo Stile Menu ---
	menu_numerati_attivi = db.get("menu_numerati", False)
	status_menu = _("Numeri") if menu_numerati_attivi else _("Parole")
	prompt_menu = _("Stile menu: [{status}]. Premi Invio per cambiare, altro per confermare: ").format(status=status_menu)
	scelta_menu = key(prompt_menu).strip()
	if scelta_menu == "":
		db["menu_numerati"] = not menu_numerati_attivi
	# --- Aggiornamento e Salvataggio ---
	STILE_MENU_NUMERICO = db.get("menu_numerati", False)
	SaveDB(db)
	print(_("Salvataggio completato. Impostazioni aggiornate"))
	return

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
				last_move_info = "{num}. {san}".format(num=move_number, san=last_move_san)
			else:
				last_move_info = "{num}... {san}".format(num=move_number, san=last_move_san)
		board_str += " {move_info} Materiale: {white_mat}/{black_mat}".format(move_info=last_move_info, white_mat=white_material, black_mat=black_material)
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
					print(self.white_player + _(" entra in fase ") + str(self.white_phase+1) + _(" tempo fase ") + FormatTime(self.clock_config["phases"][self.white_phase]["white_time"]))
					self.white_remaining=self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves+=1
			if self.black_phase<len(self.clock_config["phases"])-1:
				if self.black_moves>=self.clock_config["phases"][self.black_phase]["moves"] and self.clock_config["phases"][self.black_phase]["moves"]!=0:
					self.black_phase+=1
					Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03,0, volume], kind=3, adsr=[20, 10, 75, 20])
					print(self.black_player + _(" entra in fase ") + str(self.black_phase+1) + _(" tempo fase ") + FormatTime(self.clock_config["phases"][self.black_phase]["black_time"]))
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
						print(_("\nAllarme: tempo del bianco raggiunto {time}").format(time=seconds_to_mmss(alarm)),end="")
						Acusticator(["c4",0.2,-0.75,volume])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(_("\nAllarme: tempo del nero raggiunto {time}").format(time=seconds_to_mmss(alarm)),end="")
						Acusticator(["c4",0.2,0.75,volume])
						triggered_alarms_black.add(alarm)
		if game_state.white_remaining<=0 or game_state.black_remaining<=0:
			Acusticator(["e4", 0.2, -0.5, volume, "d4", 0.2, 0, volume, "c4", 0.2, 0.5, volume], kind=1, adsr=[10, 0, 90, 10])
			game_state.game_over=True
			print(_("Bandierina caduta!"))
			if game_state.white_remaining <= 0:
				game_state.pgn_game.headers["Result"] = "0-1"  # Nero vince
				print(_("Tempo del Bianco scaduto. {player} vince.").format(player=game_state.black_player))
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			else:
				game_state.pgn_game.headers["Result"] = "1-0"  # Bianco vince
				print(_("Tempo del Nero scaduto. {player} vince.").format(player=game_state.white_player))
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
		time.sleep(0.1)

def RiprendiPartita(dati_partita):
	"""
	Ricostruisce lo stato di una partita dal dizionario dei dati caricati
	e avvia il loop di gioco per continuarla.
	"""
	print(_("Ricostruzione dello stato della partita..."))
	game_state = GameState(dati_partita["clock_config"])
	game_state.board = CustomBoard(dati_partita["board_fen"])
	game_state.white_remaining = dati_partita["white_remaining"]
	game_state.black_remaining = dati_partita["black_remaining"]
	game_state.white_phase = dati_partita["white_phase"]
	game_state.black_phase = dati_partita["black_phase"]
	game_state.white_moves = dati_partita["white_moves"]
	game_state.black_moves = dati_partita["black_moves"]
	game_state.active_color = dati_partita["active_color"]
	game_state.move_history = dati_partita["move_history"]
	game_state.white_player = dati_partita["white_player"]
	game_state.black_player = dati_partita["black_player"]
	try:
		pgn_io = io.StringIO(dati_partita["pgn_string"])
		game_state.pgn_game = chess.pgn.read_game(pgn_io)
		if game_state.pgn_game is None:
			# Fallback se il PGN è corrotto o vuoto
			print(_("Attenzione: PGN non valido nel file di salvataggio. Ne creo uno nuovo."))
			game_state.pgn_game = chess.pgn.Game.from_board(game_state.board)
		else:
			# Assicura che il puntatore al nodo corrente sia sull'ultima mossa
			game_state.pgn_node = game_state.pgn_game.end()
	except Exception as e:
		print(_("Errore nella lettura del PGN salvato: {error}. La partita riprenderà senza cronologia PGN.").format(error=e))
		game_state.pgn_game = chess.pgn.Game.from_board(game_state.board)
	game_state.paused = True
	threading.Thread(target=clock_thread, args=(game_state,), daemon=True).start()
	db = LoadDB()
	autosave_is_on = db.get("autosave_enabled", False)
	eco_database = LoadEcoDatabaseWithFEN("eco.db")
	print("\n" + "--- Riepilogo Partita ---")
	print(_("Bianco: {player} - Tempo: {time}").format(player=game_state.white_player, time=FormatTime(game_state.white_remaining)))
	print(_("Nero: {player} - Tempo: {time}").format(player=game_state.black_player, time=FormatTime(game_state.black_remaining)))
	if game_state.move_history:
		last_move_san = game_state.move_history[-1]
		# Determina il numero della mossa e chi l'ha fatta
		if game_state.active_color == "black": # La mossa precedente era del bianco
			move_num = (len(game_state.move_history) + 1) // 2
			last_move_str = "{num}. {san}".format(num=move_num, san=last_move_san)
		else: # La mossa precedente era del nero
			move_num = len(game_state.move_history) // 2
			last_move_str = "{num}... {san}".format(num=move_num, san=last_move_san)
		print(_("Ultima mossa: {move}").format(move=last_move_str))
	tocca_a_player = game_state.white_player if game_state.active_color == "white" else game_state.black_player
	print(_("Tocca a: {player}").format(player=tocca_a_player))
	print("-------------------------" + "\n")
	last_valid_eco_entry = _loop_principale_partita(game_state, eco_database, autosave_is_on)
	_finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on)
	return

def EseguiAutosave(game_state):
	"""
	Salva lo stato corrente della partita su un file JSON di autosave.
	Questa funzione viene chiamata dopo ogni mossa se l'opzione è attiva.
	"""
	AUTOSAVE_FILENAME = "autosave.json"
	full_path = percorso_salvataggio(os.path.join("settings", AUTOSAVE_FILENAME))
	# Creiamo un dizionario con tutti i dati necessari per la ripresa
	dati_partita = {
		"board_fen": game_state.board.fen(),
		"clock_config": game_state.clock_config,
		"white_remaining": game_state.white_remaining,
		"black_remaining": game_state.black_remaining,
		"white_phase": game_state.white_phase,
		"black_phase": game_state.black_phase,
		"white_moves": game_state.white_moves,
		"black_moves": game_state.black_moves,
		"active_color": game_state.active_color,
		"move_history": game_state.move_history,
		"pgn_string": str(game_state.pgn_game),
		"white_player": game_state.white_player,
		"black_player": game_state.black_player
	}
	try:
		with open(full_path, "w", encoding="utf-8") as f:
			json.dump(dati_partita, f, indent="\t")
	except Exception as e:
		print(_("\n[Errore durante il salvataggio automatico: {error}]").format(error=e))

def _loop_principale_partita(game_state, eco_database, autosave_is_on):
	"""
	Contiene il ciclo di gioco principale. Gestisce l'input dell'utente,
	le mosse e i comandi fino alla fine della partita.
	Questo loop viene usato sia per le partite nuove che per quelle riprese.
	"""
	last_eco_msg = ""
	last_valid_eco_entry = None
	paused_time_start=None
	while not game_state.game_over:
		if not game_state.move_history:
			prompt=_("\nInizio, mossa 0. ")
		elif len(game_state.move_history)%2==1:
			full_move=(len(game_state.move_history)+1)//2
			prompt="{num}. {last_move} ".format(num=full_move, last_move=game_state.move_history[-1])
		else:
			full_move=(len(game_state.move_history))//2
			prompt="{num}... {last_move} ".format(num=full_move, last_move=game_state.move_history[-1])
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
					print(_("Traversa non valida."))
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				Acusticator(["d#4", .7, 0, volume], kind=1, adsr=[0, 0, 100, 100])
				read_square(game_state, param)
			else:
				print(_("Comando dash non riconosciuto."))
		elif user_input.startswith(","):
			Acusticator(["a3", .06, -1, volume, "c4", .06, -0.5, volume, "d#4", .06, 0.5, volume, "f4", .06, 1, volume], kind=3, adsr=[20, 5, 70, 25])
			report_piece_positions(game_state, user_input[1:2])
		elif user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			if cmd==".?":
				Acusticator([440.0, 0.3, 0, 0.5, 880.0, 0.3, 0, 0.5], kind=1, adsr=[10, 0, 100, 20])
				menu(DOT_COMMANDS,show_only=True,p=_("Comandi disponibili:"))
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
				adv=_("bianco") if game_state.white_remaining>game_state.black_remaining else _("nero")
				print(_("{player} in vantaggio di ").format(player=adv)+FormatTime(diff))
			elif cmd==".5":
				if game_state.paused:
					Acusticator(['d4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					pause_duration = time.time() - paused_time_start if paused_time_start else 0
					hours = int(pause_duration // 3600)
					minutes = int((pause_duration % 3600) // 60)
					seconds = int(pause_duration % 60)
					ms = int((pause_duration - int(pause_duration)) * 1000)
					print(_("Tempo in pausa da: {duration}").format(duration="{h_str}{m_str}{s_str}{ms_str}".format(
						h_str=_('{h} ore, ').format(h=hours) if hours else '',
						m_str=_('{m} minuti, ').format(m=minutes) if minutes or hours else '',
						s_str=_('{s} secondi e ').format(s=seconds) if seconds or minutes or hours else '',
						ms_str=_('{ms} ms').format(ms=ms) if ms else ''
					)))
				else:
					Acusticator(['f4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					player = game_state.white_player if game_state.active_color=="white" else game_state.black_player
					print(_("Orologio di {player} in moto").format(player=player))
			elif cmd==".m":
				Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
				white_material,black_material=CalculateMaterial(game_state.board)
				print(_("Materiale: {white_player} {white_mat}, {black_player} {black_mat}").format(white_player=game_state.white_player, white_mat=white_material, black_player=game_state.black_player, black_mat=black_material))
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					print(_("Orologi in pausa"))
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
					print(_("Pausa durata ")+FormatTime(pause_duration))
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
					print(_("Ultima mossa annullata: ") + undone_move_san)
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
						print(_("Nuovo tempo bianco: {white_time}, nero: {black_time}").format(white_time=FormatTime(game_state.white_remaining), black_time=FormatTime(game_state.black_remaining)))
					except:
						print(_("Comando non valido."))
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, volume, "g4", 0.2, -0.3, volume, "c5", 0.2, 0.3, volume, "e5", 0.2, 1, volume, "g5", 0.4, 0, volume], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				Acusticator([900.0, 0.1, 0, volume, 440.0, 0.3, 0, volume], kind=1, adsr=[1, 0, 80, 19])
				summary = GenerateMoveSummary(game_state)
				if summary:
					print(_("\nLista mosse giocate:\n"))
					for line in summary:
						print(line)
				else:
					print(_("Nessuna mossa ancora giocata."))
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
				print(_("Risultato assegnato: ")+result)
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
					print(_("Commento registrato per la mossa: ") + game_state.move_history[-1])
				else:
					print(_("Nessuna mossa da commentare."))
			else:
				Acusticator(["e3", 1, 0, volume,"a2", 1, 0, volume], kind=3, adsr=[1,7,100,92])
				print(_("Comando non riconosciuto."))
		# --- Gestione mosse ---
		else:
			if game_state.paused:
				print(_("Non è possibile inserire nuove mosse mentre il tempo è in pausa. Riavvia il tempo con .p"))
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
							new_node.comment = existing_comment + _(" {Proposta di patta}")
						else:
							new_node.comment = _("{Proposta di patta}")
					elif annotation_suffix in NAG_MAP:
						nag_value = NAG_MAP[annotation_suffix][0]
						new_node.nags.add(nag_value)
				# --- FINE MODIFICA ---

				# Se esistono mosse annullate, aggiungi un commento al nuovo nodo
				if hasattr(game_state, "cancelled_san_moves") and game_state.cancelled_san_moves:
					undo_comment = _("Mosse annullate: ") + " ".join(game_state.cancelled_san_moves)
					existing_comment = new_node.comment or ""
					if existing_comment:
						new_node.comment = existing_comment + " " + undo_comment
					else:
						new_node.comment = undo_comment
					# Svuota la lista per le prossime operazioni
					del game_state.cancelled_san_moves

				# Aggiorna il puntatore PGN al nuovo nodo
				game_state.pgn_node = new_node
				if eco_database:
					current_board = game_state.board
					eco_entry = DetectOpeningByFEN(current_board, eco_database)
					new_eco_msg = ""
					current_entry_this_turn = eco_entry if eco_entry else None
					if eco_entry:
						new_eco_msg = "{eco} - {opening}".format(eco=eco_entry['eco'], opening=eco_entry['opening'])
						if eco_entry['variation']:
							new_eco_msg += " ({variation})".format(variation=eco_entry['variation'])
					if new_eco_msg and new_eco_msg != last_eco_msg:
						print(_("Apertura rilevata: ") + new_eco_msg)
						Acusticator(["f7", 0.018, 0, volume])
						last_eco_msg = new_eco_msg
						last_valid_eco_entry = current_entry_this_turn
					elif not new_eco_msg and last_eco_msg:
						last_eco_msg = ""
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "1-0" if game_state.active_color == "white" else "0-1" # Nota: il turno è già cambiato qui
					game_state.pgn_game.headers["Result"] = result
					winner = game_state.black_player if result == "0-1" else game_state.white_player
					print(_("Scacco matto! Vince {winner}.").format(winner=winner))
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_stalemate():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per stallo!"))
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_insufficient_material():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per materiale insufficiente!"))
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_seventyfive_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per la regola delle 75 mosse!"))
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_fivefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per ripetizione della posizione (5 volte)!"))
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_fifty_moves():
					game_state.game_over = True # Consideriamo la richiesta automatica per semplicità
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per la regola delle 50 mosse!"))
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition():
					game_state.game_over = True # Consideriamo la richiesta automatica per semplicità
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per triplice ripetizione della posizione!"))
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()
				if autosave_is_on:
					EseguiAutosave(game_state)
					Acusticator(["f3", 0.012, 0, volume], sync=True)
			except Exception as e:
				illegal_result=verbose_legal_moves_for_san(game_state.board,move_san_only) # Usa move_san_only qui
				Acusticator([600.0, 0.6, 0, volume], adsr=[5, 0, 35, 90])
				print(_("Mossa '{move}' illegale o non riconosciuta ({error}). Sulla casa indicata sono possibili:\n{alternatives}").format(move=move_san_only, error=e, alternatives=illegal_result))
	return

def _finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on):
	game_state.pgn_game.headers["WhiteClock"] = FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = FormatClock(game_state.black_remaining)
	print(_("Partita terminata."))
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
	base_filename = "{white}-{black}-{result}-{timestamp}.pgn".format(white=game_state.pgn_game.headers.get("White"), black=game_state.pgn_game.headers.get("Black"), result=game_state.pgn_game.headers.get('Result', '*'), timestamp=datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
	sanitized_name = sanitize_filename(base_filename)
	full_path = percorso_salvataggio(os.path.join("pgn", sanitized_name))
	with open(full_path, "w", encoding="utf-8") as f:
		f.write(pgn_str)
	print(_("PGN salvato come ")+full_path+".")
	save_text_summary(game_state, game_state.descriptive_move_history, last_valid_eco_entry)
	try:
		pyperclip.copy(pgn_str)
		print(_("PGN copiato negli appunti."))
	except Exception as e:
		print(_("Errore durante la copia del PGN negli appunti: {error}").format(error=e))
	if autosave_is_on:
		try:
			autosave_file_path = percorso_salvataggio("settings", "autosave.json")
			if os.path.exists(autosave_file_path):
				os.remove(autosave_file_path)
				print(_("File di salvataggio automatico eliminato."))
		except Exception as e:
			print(_("\n[Attenzione: impossibile eliminare il file di autosave: {error}]").format(error=e))
	if len(game_state.move_history) >= 8:
		if enter_escape(_("Vuoi analizzare la partita? (INVIO per sì, ESC per no): ")):
			db = LoadDB()
			engine_config = db.get("engine_config", {})
			if not engine_config or not engine_config.get("engine_path"):
				print(_("Motore non configurato. Ritorno al menù."))
				return
			if ENGINE is None and not InitEngine():
				print(_("Impossibile inizializzare il motore. Analisi annullata."))
				return
			cache_analysis.clear()
			if enter_escape(_("Desideri l'analisi automatica? (INVIO per sì, ESC per manuale): ")):
				AnalisiAutomatica(copy.deepcopy(game_state.pgn_game))
			else:
				AnalyzeGame(game_state.pgn_game)
		else:
			Acusticator([880.0, 0.2, 0, volume, 440.0, 0.2, 0, volume], kind=1, adsr=[25, 0, 50, 25])
	return

def StartGame(clock_config):
	print(_("\nAvvio partita\n"))
	game_mode_choice = ''
	while game_mode_choice not in ['s', 'f']:
		game_mode_choice = key(_("Scegli la modalità: [S]tandard o [F]ischer Random 960? (S/F) ")).lower()
	Acusticator(["c4", 0.05, 0, volume, "e4", 0.05, 0, volume, "g4", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	is_fischer_random = (game_mode_choice == 'f')
	starting_board = None
	starting_fen = None
	if is_fischer_random:
		starting_board, starting_fen = setup_fischer_random_board()
		if starting_board is None: # L'utente ha annullato
			return # Esce dalla funzione StartGame e torna al menù
	db = LoadDB()
	autosave_is_on = db.get("autosave_enabled", False)
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", _("Bianco"))
	black_default = default_pgn.get("Black", _("Nero"))
	white_elo_default = default_pgn.get("WhiteElo", "1399")
	black_elo_default = default_pgn.get("BlackElo", "1399")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", _("Sede sconosciuta"))
	round_default = default_pgn.get("Round", "Round 1")
	eco_database = LoadEcoDatabaseWithFEN("eco.db")
	white_player = dgt(_("Nome del bianco [{default}]: ").format(default=white_default), kind="s", default=white_default).strip().title()
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_player == "":
		white_player = white_default
	black_player = dgt(_("Nome del nero [{default}]: ").format(default=black_default), kind="s", default=black_default).strip().title()
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_player == "":
		black_player = black_default
	white_elo = dgt(_("Elo del bianco [{default}]: ").format(default=white_elo_default), kind="s", default=white_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_elo.strip() == "":
		white_elo = white_elo_default
	black_elo = dgt(_("Elo del nero [{default}]: ").format(default=black_elo_default), kind="s", default=black_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_elo.strip() == "":
		black_elo = black_elo_default
	event = dgt(_("Evento [{default}]: ").format(default=event_default), kind="s", default=event_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if event.strip() == "":
		event = event_default
	site = dgt(_("Sede [{default}]: ").format(default=site_default), kind="s", default=site_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	round_ = dgt(_("Round [{default}]: ").format(default=round_default), kind="s", default=round_default)
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
	key(_("Premi un tasto qualsiasi per iniziare la partita quando sei pronto..."),attesa=7200)
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
	game_state.pgn_game.headers["Annotator"]="Orologic V{version} by {programmer}".format(version=VERSION, programmer=PROGRAMMER)
	threading.Thread(target=clock_thread, args=(game_state,), daemon=True).start()
	last_valid_eco_entry = _loop_principale_partita(game_state, eco_database, autosave_is_on)
	_finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on)
	return

def OpenManual():
	print(_("\nApertura manuale\n"))
	readme_path = resource_path(os.path.join("resources", "readme.htm"))
	if os.path.exists(readme_path):
		webbrowser.open("file://" + os.path.realpath(readme_path))
	else:
		print(_("Il file {path} non esiste.").format(path=readme_path))

def SchermataIniziale():
	now = datetime.datetime.now()
	diff1 = relativedelta(now, BIRTH_DATE)
	diff2 = relativedelta(now, RELEASE_DATE)
	parts1 = []
	if diff1.years:
		parts1.append(_("{num} anni").format(num=diff1.years))
	if diff1.months:
		parts1.append(_("{num} mesi").format(num=diff1.months))
	if diff1.days:
		parts1.append(_("{num} giorni").format(num=diff1.days))
	if diff1.hours:
		parts1.append(_("{num} ore").format(num=diff1.hours))
	if diff1.minutes:
		parts1.append(_("e {num} minuti").format(num=diff1.minutes))
	age_string = ", ".join(parts1)
	parts2 = []
	if diff2.years:
		parts2.append(_("{num} anni").format(num=diff2.years))
	if diff2.months:
		parts2.append(_("{num} mesi").format(num=diff2.months))
	if diff2.days:
		parts2.append(_("{num} giorni").format(num=diff2.days))
	if diff2.hours:
		parts2.append(_("{num} ore").format(num=diff2.hours))
	if diff2.minutes:
		parts2.append(_("{num} minuti").format(num=diff2.minutes))
	release_string = ", ".join(parts2)
	print(_("\nCiao! Benvenuto, sono Orologic e ho {age}.").format(age=age_string))
	print(_("L'ultima versione è la {version} ed è stata rilasciata il {release_date}.").format(version=VERSION, release_date=RELEASE_DATE.strftime('%d/%m/%Y %H:%M')))
	print(_("\tcioè: {release_ago} fa.").format(release_ago=release_string))
	print("\t\t" + _("Autore: ") + PROGRAMMER)
	print("\t\t\t" + _("Digita '?' per visualizzare il menù."))
	Acusticator(['c4', 0.125, 0, volume, 'd4', 0.125, 0, volume, 'e4', 0.125, 0, volume, 'g4', 0.125, 0, volume, 'a4', 0.125, 0, volume, 'e5', 0.125, 0, volume, 'p', 0.125, 0, 0.5, 'a5', 0.125, 0, volume], kind=1, adsr=[0.01, 0, 100, 99])
def Main():
	global	volume, STILE_MENU_NUMERICO
	os.makedirs(percorso_salvataggio("pgn"), exist_ok=True)
	os.makedirs(percorso_salvataggio("txt"), exist_ok=True)
	os.makedirs(percorso_salvataggio("settings"), exist_ok=True)
	db = LoadDB()
	volume = db.get("volume", 0.5)
	STILE_MENU_NUMERICO = db.get("menu_numerati", False)
	launch_count = db.get("launch_count", 0) + 1
	db["launch_count"] = launch_count
	SaveDB(db)
	SchermataIniziale()
	InitEngine()
	if ENGINE is not None:
		print(_("✅ Motore attivo: {engine_name}").format(engine_name=ENGINE_NAME))
	LoadLocalization()
	# --- Inizio Blocco Autosave ---
	AUTOSAVE_FILE = "autosave.json"
	autosave_path = percorso_salvataggio(os.path.join("settings", AUTOSAVE_FILE))
	if os.path.exists(autosave_path):
		print("\n" + "="*40)
		print("⚠️ " + _("Trovata una partita non conclusa!"))
		print("="*40)
		scelta_ripresa = key(_("Vuoi riprenderla? (Invio per Sì / 'n' per No): ")).lower().strip()
		if scelta_ripresa != 'n':
			try:
				with open(autosave_path, 'r', encoding='utf-8') as f:
					dati_caricati = json.load(f)
				print(_("Partita caricata. Avvio in corso..."))
				Acusticator(["c5", 0.1, -0.8, volume, "e5", 0.1, 0, volume, "g5", 0.2, 0.8, volume], kind=1, adsr=[2, 8, 90, 0])
				RiprendiPartita(dati_caricati)
				# Dopo che la partita ripresa finisce, il programma continuerà normalmente
				# mostrando il menu principale.
			except Exception as e:
				print(_("Errore critico durante il caricamento della partita: {error}").format(error=e))
				print(_("Il file di salvataggio potrebbe essere corrotto. Verrà ignorato per questa sessione."))
				Acusticator(["a3", .3, 0, volume], kind=2, adsr=[5, 15, 0, 80])
		else:
			print(_("Ok, la partita salvata verrà ignorata."))
	while True:
		scelta=menu(MENU_CHOICES, show=True, keyslist=True, full_keyslist=False, numbered=STILE_MENU_NUMERICO)
		if scelta == "analizza":
			Acusticator(["a5", .04, 0, volume, "e5", .04, 0, volume, "p",.08,0,0, "g5", .04, 0, volume, "e6", .120, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			print(_("\nCaricamento partita dagli appunti..."))
			pgn_da_analizzare = LoadPGNFromClipboard()
			if pgn_da_analizzare:
				if ENGINE is None and not InitEngine():
					print(_("Impossibile inizializzare il motore. Analisi annullata."))
				else:
					cache_analysis.clear()
					if enter_escape(_("Desideri l'analisi automatica? (INVIO per sì, ESC per manuale): ")):
						AnalisiAutomatica(copy.deepcopy(pgn_da_analizzare))
					else:
						AnalyzeGame(pgn_da_analizzare)
			else:
				pass
		elif scelta=="crea":
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			CreateClock()
		elif scelta=="comandi":
			Acusticator([500.0, 0.4, -1, volume, 800.0, 0.4, 1, volume], kind=3, adsr=[20, 10, 50, 20])
			menu(DOT_COMMANDS,show_only=True)
		elif scelta=="motore":
			Acusticator(["e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume])
			print(_("\nAzioni per il motore scacchistico:"))
			scelta_azione = key(_("Vuoi [c] cercare un motore nel tuo pc, [s] scaricare Stockfish, o [m] per modificare manualmente la configurazione? (c/s/m): ")).lower().strip()
			if scelta_azione == 'c':
				engine_path, engine_exe, wants_download = SearchForEngine()
				if wants_download:
					# L'utente ha scelto 's' durante la ricerca, quindi avviamo il download
					e_path, e_exe = DownloadAndInstallEngine()
					if e_path and e_exe: EditEngineConfig(initial_path=e_path, initial_executable=e_exe)
				elif engine_path and engine_exe:
					EditEngineConfig(initial_path=engine_path, initial_executable=engine_exe)
			elif scelta_azione == 's':
				engine_path, engine_exe = DownloadAndInstallEngine()
				if engine_path and engine_exe: EditEngineConfig(initial_path=engine_path, initial_executable=engine_exe)
			elif scelta_azione == 'm':
				EditEngineConfig()
		elif scelta=="volume":
			Acusticator(["f6",.02,0,volume,"p",.04,0,volume,"a6",.02,0,volume])
			old_volume=volume
			volume = dgt(_("\nVolume attuale: {vol}, nuovo? (0-100): ").format(vol=int(volume*100)), kind="i", imin=0, imax=100, default=50)
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
		elif scelta=="impostazioni":
			Impostazioni(db)
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="nomi": # <-- BLOCCO NUOVO DA AGGIUNGERE
			EditLocalization()		
			Acusticator([1200.0, 0.05, 0, volume, "p", 0.05, 0, 0, 1100.0, 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="manuale":
			OpenManual()
		elif scelta=="gioca":
			Acusticator(["c5", 0.1, 0, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0, volume, "c6", 0.3, 0, volume, "g5", 0.1, 0, volume, "e5", 0.1, 0, volume, "c5", 0.1, 0, volume], kind=1, adsr=[5, 5, 90, 10])
			print(_("\nAvvio partita\n"))
			db=LoadDB()
			if not db["clocks"]:
				Acusticator(["c5", 0.3, 0, volume, "g4", 0.3, 0, volume], kind=1, adsr=[30, 20, 80, 20])
				print(_("Nessun orologio disponibile. Creane uno prima."))
			else:
				clock_config=SelectClock(db)
				if clock_config is not None:
					StartGame(clock_config)
				else:
					print(_("Scelta non valida."))
		elif scelta==".":
			Acusticator(["g4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "a4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "p", 0.15, 0, 0, "b4", 0.15, -0.5, volume, "c5", 0.3, 0.5, volume], kind=1, adsr=[5, 0, 100, 5])
			if ENGINE is not None:
				ENGINE.quit()
				print(_("\nConnessione col motore UCI chiusa"))
			break
if __name__=="__main__":
	time_start = datetime.datetime.now()
	board=CustomBoard()
	Main()
	time_end = datetime.datetime.now()
	delta = relativedelta(time_end, time_start)
	components = []
	if delta.days:
		components.append(_("{num} giorni").format(num=delta.days))
	if delta.hours:
		components.append(_("{num} ore").format(num=delta.hours))
	if delta.minutes:
		components.append(_("{num} minuti").format(num=delta.minutes))
	if delta.seconds:
		components.append(_("{num} secondi").format(num=delta.seconds))
	ms = delta.microseconds // 1000
	if ms:
		components.append(_("{num} millisecondi").format(num=ms))
	result = ", ".join(components) if components else _("0 millisecondi")
	final_db = LoadDB()
	final_launch_count = final_db.get("launch_count", _("sconosciuto")) # Legge il contatore salvato	
	print(_("Arrivederci da Orologic {version}.\nQuesta era la nostra {launch_count}a volta e ci siamo divertiti assieme per: {duration}").format(version=VERSION, launch_count=final_launch_count, duration=result))
	Donazione()
	key(prompt=_("\nPremi un tasto per uscire..."), attesa=300)
	sys.exit(0)