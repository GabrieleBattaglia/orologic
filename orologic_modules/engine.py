import chess
import chess.engine
import chess.pgn
import requests
import zipfile
import io
import os
import sys
import time
import threading
import copy
import re
import datetime
import pyperclip
import ctypes
from GBUtils import dgt, menu, Acusticator, polipo, key
from . import config
from . import board_utils
from . import ui
from . import clock
from . import storage
from . import version

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

# Variabili globali
ENGINE = None
ENGINE_NAME = "Nessuno"
analysis_time = 3
multipv = 2
cache_analysis = {}
oaa_analysis_cache = {}

# Recupero configurazione globale
try:
    db_config = storage.LoadDB()
    STILE_MENU_NUMERICO = db_config.get("menu_numerati", False)
    volume = db_config.get("volume", 1.0)
except:
    STILE_MENU_NUMERICO = False
    volume = 1.0

def InitEngine():
	global ENGINE, ENGINE_NAME
	db = storage.LoadDB()
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
		path_da_usare = config.percorso_salvataggio(saved_path)
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

def get_available_drives():
	drives = []
	if sys.platform == 'win32':
		bitmask = ctypes.windll.kernel32.GetLogicalDrives()
		for i in range(26):
			if (bitmask >> i) & 1:
				drive_letter = chr(ord('A') + i)
				drives.append(f"{drive_letter}:\\")
	elif sys.platform == 'darwin':
		drives.append('/')
		try:
			drives.extend([os.path.join('/Volumes', d) for d in os.listdir('/Volumes')])
		except FileNotFoundError: pass
	else:
		drives.append('/')
	return drives

def get_app_data_path():
	path = os.path.join(os.getenv('LOCALAPPDATA'), "Orologic", "Engine")
	os.makedirs(path, exist_ok=True)
	return path

def SearchForEngine():
	print(_("\nNessuna configurazione trovata. Avvio ricerca avanzata del motore..."))
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
		while True:
			with lock:
				if shared_state["search_complete"]: break
				path = shared_state["current_path"]
				path_str = f"{path[:15]}...{path[-15:]}" if len(path) > 30 else path
			print(f"\rScanning: {path_str:<40}", end="")
			time.sleep(5)
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
				exclude_dirs = ["windows", "$recycle.bin", "programdata", "system volume information", "filehistory", "library", "system", "private"]
				dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs]
				for file in files:
					file_lower = file.lower()
					if file_lower.endswith(executable_extensions):
						is_match = False
						for keyword in all_keywords:
							if len(keyword) <= 2:
								if file_lower == keyword + ".exe":
									is_match = True
									break
							elif file_lower.startswith(keyword):
								is_match = True
								break
						if is_match:
							with lock:
								shared_state["engines_found"].append((root, file))
								found_count = len(shared_state["engines_found"])
								print(f"\r{' ' * 60}\r 🔍 Trovati finora: {found_count}. La scansione continua...", end="")
		except Exception: continue
	with lock: shared_state["search_complete"] = True
	reporter_thread.join()
	end_time = time.time()
	print(f"\r{' ' * 60}\r", end="")
	print("\n--- Report della Ricerca ---")
	print(_("Tempo impiegato: {duration:.2f} secondi").format(duration=end_time - start_time))
	print(_("Cartelle scansionate: {folders}").format(folders=shared_state['folders_scanned']))
	print(_("File scansionati: {files}").format(files=shared_state['files_scanned']))
	found_engines = shared_state["engines_found"]
	if not found_engines:
		print(_("\nRisultato: Nessun motore trovato."))
		return None, None, False
	print(_("\nSono stati trovati {num} eseguibili che potrebbero essere motori compatibili\n\tVerifica che lo siano davvero e scegline uno da usare:").format(num=len(found_engines)))
	for i, (root, file) in enumerate(found_engines, 1):
		print(f" {i}. Eseguibile: {file}\n    Percorso: {root}")
	if len(found_engines) == 1:
		prompt_text = _("\nTrovato un solo motore. Vuoi usarlo? (Invio per sì, 0 per no, 's' per scaricare): ")
		scelta_str = key(prompt_text).lower().strip()
		if scelta_str == '0':
			print(_("Nessun motore selezionato."))
			return None, None, False
		elif scelta_str == 's':
			return None, None, True
		else:
			root, file = found_engines[0]
			print(_("Hai selezionato: {file}").format(file=file))
			return root, file, False
	else:
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

def DownloadAndInstallEngine():
	global ENGINE
	if ENGINE:
		print(_("Arresto il motore attivo per consentire l'aggiornamento..."))
		try:
			ENGINE.quit()
		except: pass
		ENGINE = None
		time.sleep(1.0) # Attesa tecnica per rilascio file handle

	try:
		install_path = get_app_data_path()
		zip_filename = os.path.join(install_path, "stockfish.zip")
		print(_("\n📥 Sto scaricando Stockfish da {url}...").format(url=config.STOCKFISH_DOWNLOAD_URL))
		response = requests.get(config.STOCKFISH_DOWNLOAD_URL, stream=True)
		response.raise_for_status()
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
		print(_("...sto estraendo i file..."))
		with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
			zip_ref.extractall(install_path)
		print(_("Estrazione completata."))
		os.remove(zip_filename)
		for root, dirs, files in os.walk(install_path):
			for file in files:
				if file.lower().startswith("stockfish") and file.lower().endswith(".exe"):
					print(_("Installazione di Stockfish completata con successo!"))
					return root, file
	except requests.exceptions.RequestException as e:
		print(_("\nErrore di rete durante il download: {error}").format(error=e))
		return None, None
	except zipfile.BadZipFile:
		print(_("\nErrore: Il file scaricato non è uno zip valido."))
		return None, None
	except Exception as e:
		print(_("\nSi è verificato un errore imprevisto durante l'installazione: {error}").format(error=e))
		return None, None
	return None, None

def EditEngineConfig(initial_path=None, initial_executable=None):
	print(_("\nImposta configurazione del motore scacchistico\n"))
	db = storage.LoadDB()
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
	app_path = config.percorso_salvataggio('')
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
	wdl_switch = True
	engine_config = {
		"engine_path": path_to_save,
		"engine_is_relative": is_relative,
		"hash_size": hash_size,
		"num_cores": num_cores,
		"skill_level": skill_level,
		"move_overhead": move_overhead,
		"wdl_switch": wdl_switch
	}
	db["engine_config"] = engine_config
	storage.SaveDB(db)
	print(_("Configurazione del motore salvata."))
	InitEngine()
	Acusticator(["a6", 0.5, 1, volume],kind=3, adsr=[.001,0,100,99.9])
	return

def LoadPGNFromClipboard():
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

def SetAnalysisTime(new_time):
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
	global multipv
	try:
		new_multipv = int(new_multipv)
		if new_multipv < 1:
			print(_("Il numero di linee deve essere almeno 1."))
		else:
			multipv = new_multipv
	except Exception as e:
		print(_("Errore in SetMultipv:"), e)

def CalculateBest(board, bestmove=True, as_san=False):
	Acusticator(["e5",.008,-1,volume]) 
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=multipv)
		analysis = cache_analysis[fen]
		# Gestione python-chess wrapper: se analysis è una lista di info dicts
		if isinstance(analysis, list):
			best_line = analysis[0].get("pv", [])
			score = analysis[0].get("score")
		else: # Fallback se è un singolo dict
			best_line = analysis.get("pv", [])
			score = analysis.get("score")

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
					white_descr = ui.DescribeMove(white_move, temp_board)
					temp_board.push(white_move)
					i += 1
					move_descr = _("{num}.").format(num=move_number) + " " + white_descr
					if i < len(best_line) and temp_board.turn == chess.BLACK:
						black_move = best_line[i]
						black_descr = ui.DescribeMove(black_move, temp_board)
						temp_board.push(black_move)
						i += 1
						move_descr += ", " + black_descr
					descriptive_moves.append(move_descr)
					move_number += 1
				else:
					black_move = best_line[i]
					black_descr = ui.DescribeMove(black_move, temp_board)
					temp_board.push(black_move)
					i += 1
					descriptive_moves.append(_("{num}... {desc}").format(num=move_number, desc=black_descr))
					move_number += 1
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
			wdl_info = score.wdl() 
		if wdl_info is None:
			return None
		try:
			win_permille_pov, draw_permille_pov, loss_permille_pov = wdl_info
			perspective = None
			if hasattr(wdl_info, "color"):
				perspective = wdl_info.color
			elif hasattr(wdl_info,"pov"):
				perspective = wdl_info.pov
			else:
				perspective = chess.WHITE
			if perspective == chess.BLACK:
				win_permille_abs = loss_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = win_permille_pov
			else:
				win_permille_abs = win_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = loss_permille_pov
			win_pc = win_permille_abs / 10.0
			draw_pc = draw_permille_abs / 10.0
			loss_pc = loss_permille_abs / 10.0
			Acusticator(["b5",.008,1,volume])
			return (win_pc, draw_pc, loss_pc)
		except (TypeError, ValueError) as e_unpack:
			print(_("Warning: Fallito unpack diretto oggetto WDL {info}: {error}").format(info=repr(wdl_info), error=e_unpack))
			return None
	except Exception as e:
		print(_("Errore generale in CalculateWDL per FEN {fen}: {error}").format(fen=fen, error=e))
		return None

def analyze_position_deep(board, limit, multipv_count=3):
    global oaa_analysis_cache
    fen = board.fen()
    cache_key = f"{fen}_{limit.time}_{limit.depth}_{limit.nodes}_{multipv_count}"
    
    if cache_key in oaa_analysis_cache:
        return oaa_analysis_cache[cache_key]

    try:
        info = ENGINE.analyse(board, limit, multipv=multipv_count)
        
        results = []
        for i, analysis in enumerate(info):
            score = analysis.get("score")
            pv = analysis.get("pv")
            if score is not None and pv:
                results.append({
                    "rank": i + 1,
                    "move": pv[0],
                    "score": score,
                    "pv": pv
                })
        
        oaa_analysis_cache[cache_key] = results
        return results
    except Exception as e:
        print(f"\n! Errore in analyze_position_deep per FEN {fen}: {e}")
        return []

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
		eval_str = "{cp:.2f}".format(cp=cp/100) if cp is not None else "0.00"
	else:
		eval_str = "0.00"
	total_moves = len(pv_moves)
	current_index = 1
	print(_("\nUtilizza questi comandi:"))
	menu(p=config.SMART_COMMANDS,show_only=True)
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]:
			temp_board.push(move)
		current_move = pv_moves[current_index-1]
		move_verbose = ui.DescribeMove(current_move, temp_board)
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
			menu(p=config.SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			temp_board = board.copy()
			try:
				for move in pv_moves[:current_index]:
					temp_board.push(move)
			except Exception as push_err:
				print(_("\nErrore interno durante avanzamento per valutazione: {error}").format(error=push_err))
				eval_str = "ERR_NAV" 
				continue 
			score_object_si = CalculateEvaluation(temp_board)
			Acusticator(["e5",.008,-1,volume]) 
			if score_object_si is not None:
				new_eval_str = "N/A" 
				pov_score_si = score_object_si.pov(temp_board.turn)
				if pov_score_si.is_mate():
					mate_in_si = pov_score_si.mate()
					new_eval_str = _("M{moves}").format(moves=abs(mate_in_si))
				else:
					cp_si = score_object_si.white().score(mate_score=30000)
					if cp_si is not None:
						new_eval_str = "{cp:+.2f}".format(cp=cp_si/100) 
					else:
						new_eval_str = "ERR"
				eval_str = new_eval_str
				Acusticator(["g5", 0.1, 0.3, volume], kind=1, adsr=[5,5,90,5]) 
				print(_("\nValutazione aggiornata."))
			else:
				Acusticator(["a3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]) 
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

def _stampa_albero_pgn(node, analysis_data_map, summary_lines, white_name, black_name, num_varianti, indent_level=0):
    if node.move:
        indent = "\t" * indent_level
        board_before = node.parent.board()
        turn = board_before.turn
        player_name = white_name if turn == chess.WHITE else black_name
        analysis_info = analysis_data_map.get(node)
        
        move_san = ui.DescribeMove(node.move, board_before)
        move_num_str = f"{board_before.fullmove_number}."
        if turn == chess.BLACK:
            move_num_str += ".. "

        if analysis_info:
            eval_str = ""
            eval_obj = analysis_info.get('eval_after_move')
            if eval_obj:
                white_score = eval_obj.white()
                if white_score.is_mate():
                    eval_str = f"(M{white_score.mate()}) "
                else:
                    cp = white_score.score()
                    if cp is not None:
                        eval_str = f"({cp/100:+.2f}) "

            summary_lines.append(f"{indent}{move_num_str} {eval_str}{player_name} gioca: {move_san}: {analysis_info['classification']}")

            original_comment = node.comment
            if original_comment:
                cleaned_comment = re.sub(r'\{OAA:.*?\}', '', original_comment, flags=re.DOTALL).strip()
                if cleaned_comment:
                    summary_lines.append(f"{indent}\t[Commento originale]: {cleaned_comment}")

            if analysis_info['classification'] in ["Svarione", "Errore", "Inesattezza"]:
                alternatives = analysis_info.get('alternatives_info')
                if alternatives:
                    summary_lines.append(f"{indent}\t(OAA: Meglio era:")
                    for idx, line_info in enumerate(alternatives[:num_varianti]):
                        pv, score_obj = line_info.get('pv'), line_info.get('score')
                        if not pv or not score_obj: 
                            continue
                        score_pov = score_obj.pov(turn)
                        val_str = f"Matto in {abs(score_pov.mate())}" if score_pov.is_mate() else f"{score_pov.score(mate_score=30000)/100:+.2f}" if score_pov.score(mate_score=30000) is not None else "N/A"
                        line_label = "Bestline" if idx == 0 else f"Linea {idx+1}"
                        summary_lines.append(f"{indent}\t\t{line_label} (Val: {val_str}):")
                        descriptive_line = ui.format_pv_descriptively(board_before, pv)
                        summary_lines.append(descriptive_line.replace("\t\t\t", f"{indent}\t\t\t"))
                    summary_lines.append(f"{indent}\t)")
        else:
            summary_lines.append(f"{indent}{move_num_str} {player_name} gioca: {move_san}")
            if node.comment:
                summary_lines.append(f"{indent}\t[Commento]: {node.comment.strip()}")

    for i, variation in enumerate(node.variations):
        if i == 0:
            _stampa_albero_pgn(variation, analysis_data_map, summary_lines, white_name, black_name, num_varianti, indent_level + 1)
        else:
            variant_header_indent = "\t" * indent_level
            summary_lines.append(f"\n{variant_header_indent}\tVariante {i + 1} (")
            _stampa_albero_pgn(variation, analysis_data_map, summary_lines, white_name, black_name, num_varianti, indent_level + 1)
            summary_lines.append(f"{variant_header_indent}\t) /Variante {i + 1}")

def genera_sommario_analitico_txt(pgn_game, base_filename, analysis_results, imprecision_stats, cpl_data, eco_entry, mosse_da_saltare, num_varianti):
	summary_lines = []
	headers = pgn_game.headers
	white_name = headers.get("White", "Bianco").replace(',', ' ').split()[-1]
	black_name = headers.get("Black", "Nero").replace(',', ' ').split()[-1]

	summary_lines.append(_("Riepilogo Analisi Automatica di Orologic V.{version}").format(version=version.VERSION))
	summary_lines.append("="*56)
	for key, value in headers.items():
		if key not in ["White", "Black", "Result"]:
			summary_lines.append(f"{key}: {value}")
	summary_lines.append("="*56)

	if eco_entry:
		opening_line = f"{eco_entry.get('eco', '')} - {eco_entry.get('opening', '')}"
		if eco_entry.get('variation'):
			opening_line += f", {eco_entry.get('variation')}"
		summary_lines.append(_("Apertura: ") + opening_line)
	
	summary_lines.append("\n" + _("Quadro Riepilogativo delle Imprecisioni"))
	summary_lines.append("-"*56)
	header_fmt = "| {:<15} | {:^12} | {:^12} | {:^10} |".format(_("Tipo"), white_name, black_name, _("Diff."))
	summary_lines.append(header_fmt)
	summary_lines.append("-"*56)
	
	tipi_mossa = ["Mossa Geniale", "Mossa Buona", "Inesattezza", "Errore", "Svarione"]
	for err_type in tipi_mossa:
		if err_type in imprecision_stats:
			w_count = imprecision_stats[err_type]['w']
			b_count = imprecision_stats[err_type]['b']
			diff = w_count - b_count
			row_fmt = "| {:<15} | {:^12} | {:^12} | {:^+10} |".format(
				_(err_type), w_count, b_count, diff
			)
			summary_lines.append(row_fmt)
	summary_lines.append("-"*56)

	summary_lines.append(_("\nAverage Centipawn Loss (ACPL) per Fase"))
	summary_lines.append("-"*56)
	header_acpl_fmt = "| {:<15} | {:^12} | {:^12} | {:^10} |".format(_("Fase Partita"), white_name, black_name, _("Diff."))
	summary_lines.append(header_acpl_fmt)
	summary_lines.append("-"*56)

	w_cpls = cpl_data.get('w', [])
	b_cpls = cpl_data.get('b', [])
	fasi = []
	if len(w_cpls) > 5 and len(b_cpls) > 5:
		if mosse_da_saltare > 0:
			w_mid = len(w_cpls) // 2
			b_mid = len(b_cpls) // 2
			fasi.append( (_("Mediogioco"), w_cpls[:w_mid], b_cpls[:b_mid]) )
			fasi.append( (_("Finale"), w_cpls[w_mid:], b_cpls[b_mid:]) )
		else:
			w_s1, w_s2 = len(w_cpls) // 3, 2 * (len(w_cpls) // 3)
			b_s1, b_s2 = len(b_cpls) // 3, 2 * (len(b_cpls) // 3)
			fasi.append( (_("Apertura"), w_cpls[:w_s1], b_cpls[:b_s1]) )
			fasi.append( (_("Mediogioco"), w_cpls[w_s1:w_s2], b_cpls[b_s1:b_s2]) )
			fasi.append( (_("Finale"), w_cpls[w_s2:], b_cpls[b_s2:]) )
	else:
		fasi.append( (_("Totale Partita"), w_cpls, b_cpls) )	
	for nome_fase, w_fase_cpls, b_fase_cpls in fasi:
		w_avg = (sum(w_fase_cpls) / len(w_fase_cpls)) / 100 if w_fase_cpls else 0
		b_avg = (sum(b_fase_cpls) / len(b_fase_cpls)) / 100 if b_fase_cpls else 0
		diff_acpl = w_avg - b_avg
		row_acpl_fmt = "| {:<15} | {:^12.2f} | {:^12.2f} | {:^+10.2f} |".format(
			nome_fase, w_avg, b_avg, diff_acpl
		)
		summary_lines.append(row_acpl_fmt)
	summary_lines.append("-"*56)
	summary_lines.append("="*56)

	summary_lines.append(_("\n--- Analisi Mossa per Mossa ---"))
	analysis_data_map = {result['node']: result for result in analysis_results}
	summary_lines.append("Mainline (")
	# Singola chiamata alla nuova funzione ricorsiva, partendo dal nodo radice.
	_stampa_albero_pgn(pgn_game, analysis_data_map, summary_lines, white_name, black_name, num_varianti, indent_level=1)
	summary_lines.append(") /Mainline")
	summary_lines.append("\n" + "="*56)
	result = headers.get("Result", "*")
	white = headers.get("White", "Il Bianco")
	black = headers.get("Black", "Il Nero")
	white_clock = headers.get("WhiteClock")
	black_clock = headers.get("BlackClock")
	winner, loser = (None, None)
	if result == "1-0":
		winner, loser = white, black
	elif result == "0-1":
		winner, loser = black, white
	if winner and white_clock and black_clock:
		winner_clock = white_clock if winner == white else black_clock
		loser_clock = black_clock if loser == black else white_clock
		if loser_clock == "00:00:00":
			summary_lines.append(f"{winner} vince per tempo esaurito dell'avversario con ancora {winner_clock} sull'orologio.")
		else:
			summary_lines.append(f"{winner} vince la partita. Tempo finale: {winner} [{winner_clock}] - {loser} [{loser_clock}].")
	elif winner:
		summary_lines.append(f"{winner} vince la partita.")
	elif result == "1/2-1/2":
		summary_lines.append(f"La partita termina in parità.")
	else:
		summary_lines.append(f"La partita termina con un risultato non definito ({result}).")
	summary_lines.append(_("File generato da Orologic il {date}").format(date=datetime.datetime.now().strftime('%d/%m/%Y %H:%M')))
	full_text = "\n".join(summary_lines)
	sanitized_txt_name = config.sanitize_filename(base_filename) + ".txt"
	full_txt_path = config.percorso_salvataggio(os.path.join("txt", sanitized_txt_name))
	
	try:
		with open(full_txt_path, "w", encoding="utf-8") as f:
			f.write(full_text)
		print(_("Riepilogo testuale salvato come: {path}").format(path=full_txt_path))
	except Exception as e:
		print(_("Errore durante il salvataggio del riepilogo testuale: {e}").format(e=e))

def AnalisiAutomatica(pgn_game):
	if ENGINE is None:
		print(_("\nMotore non inizializzato. Impossibile avviare l'analisi automatica."))
		return
	def _format_score(score_obj, pov_color):
		if not score_obj: return "N/A"
		pov_score = score_obj.pov(pov_color)
		if pov_score.is_mate():
			return f"M{abs(pov_score.mate())}"
		else:
			# La valutazione è sempre dal punto di vista del bianco, quindi la adattiamo
			cp = score_obj.white().score(mate_score=30000)
			if cp is None: return "N/A"
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
	soglia_inesattezza = dgt(_("Inesattezza (es. 25-50 cp): [INVIO per 50] "), kind="i", imin=15, imax=200, default=50)
	soglia_errore = dgt(_("Errore (es. 51-100 cp): [INVIO per 100] "), kind="i", imin=soglia_inesattezza + 1, imax=500, default=100)
	soglia_svarione = dgt(_("Svarione (Blunder, > Errore): [INVIO per 250] "), kind="i", imin=soglia_errore + 1, imax=3000, default=250)
	print(_("\nDefinisci le soglie per le mosse di qualità (in centipawn):"))
	soglia_mossa_buona = dgt(_("Perdita massima per una 'Mossa Buona' (es. < 25 cp): [INVIO per 20] "), kind="i", imin=15, imax=soglia_inesattezza -1, default=20)
	soglia_mossa_geniale_gap = dgt(_("Vantaggio minimo di una 'Mossa Geniale' sulla seconda migliore (es. > 180 cp): [INVIO per 180] "), kind="i", imin=15, imax=4000, default=180)
	num_varianti = dgt(_("Quante varianti alternative calcolare per le mosse deboli? (1-5): [INVIO per 1] "), kind="i", imin=1, imax=5, default=1)
	mosse_da_saltare = 0
	last_valid_eco_entry = None
	if ui.enter_escape(_("Vuoi saltare automaticamente le mosse di apertura note? (INVIO per sì, ESC per specificare manualmente): ")):
		print(_("Rilevo la fine della teoria d'apertura..."))
		eco_db = board_utils.LoadEcoDatabaseWithFEN("eco.db")
		if eco_db:
			temp_board = pgn_game.board().copy()
			for move in pgn_game.mainline_moves():
				temp_board.push(move)
				detected_opening = board_utils.DetectOpeningByFEN(temp_board, eco_db)
				if detected_opening:
					mosse_da_saltare = temp_board.ply()
					last_valid_eco_entry = detected_opening
				else:
					break
			if isinstance(last_valid_eco_entry, dict):
				opening_name = last_valid_eco_entry.get('opening', _('Nome non trovato'))
				print(_("Trovata apertura: {name}").format(name=opening_name))
			print(_("L'analisi salterà le prime {n} semimosse.").format(n=mosse_da_saltare))
	else:
		mosse_da_saltare = dgt(_("Quante semimosse (ply) iniziali vuoi saltare? (INVIO per {n}) ".format(n=mosse_da_saltare)), kind="i", imin=0, imax=40, default=mosse_da_saltare)
	
	print("\n" + "="*40 + _("\nInizio analisi... (Premi ESC per interrompere)") + "\n" + "="*40)
	start_time = time.time()
	
	global oaa_analysis_cache
	oaa_analysis_cache.clear()

	mainline_nodes = list(pgn_game.mainline())
	analysis_results = []
	imprecision_stats = { "Svarione": {'w': 0, 'b': 0}, "Errore": {'w': 0, 'b': 0}, "Inesattezza": {'w': 0, 'b': 0}, "Mossa Buona": {'w': 0, 'b': 0}, "Mossa Geniale": {'w': 0, 'b': 0} }
	cpl_data = {'w': [], 'b': []}
	analysis_after = None

	for i, node in enumerate(mainline_nodes):
		if key(attesa=0.002) == '\x1b':
			Acusticator(["c3", 0.3, 0.5, volume], kind=2)
			print(_("\nAnalisi interrotta dall'utente."))
			break
		
		ply = i + 1
		if ply <= mosse_da_saltare:
			analysis_results.append({
				'node': node,
				'classification': _("Teoria"),
				'centipawn_loss': 0,
				'alternatives_info': [],
				'eval_after_move': None
			})
			continue

		parent_board = node.parent.board()
		current_board = node.board()
		turn = parent_board.turn
		color_key = 'w' if turn == chess.WHITE else 'b'
		
		total_plys = len(mainline_nodes)
		san = node.parent.board().san(node.move)
		san_str = san if ply % 2!= 0 else f"...{san}"
		elapsed_time = time.time() - start_time
		time_str = f"{int(elapsed_time // 60):02d}:{int(elapsed_time % 60):02d}"
		print(f"\r{' ' * 79}\rPLY {ply}/{total_plys} {san_str:<12} | Tempo: {time_str}", end="")

		multipv_needed = max(3, num_varianti)
		if analysis_after:
			analysis_before = analysis_after
		else:
			# Esegui l'analisi "prima" solo per la primissima mossa del ciclo
			analysis_before = analyze_position_deep(parent_board, limit, multipv_needed)
		if not analysis_before:
			continue
		best_alternative = analysis_before[0]
		analysis_after = analyze_position_deep(current_board, limit, multipv_count=1)
		if not analysis_after:
			continue

		eval_after_move = analysis_after[0]['score']
		best_alternative_move = best_alternative['move']
		centipawn_loss = 0
		classification = ""

		# Definiamo un tetto massimo per la perdita da usare nelle statistiche ACPL
		# 1000cp (valore di una Donna) è uno standard comune.
		CPL_STATISTICS_CAP = 1000

		# PRIMO CONTROLLO: La mossa giocata è la migliore in assoluto?
		if node.move.uci() == best_alternative_move.uci():
			if len(analysis_before) > 1:
				score_best = analysis_before[0]['score'].pov(turn).score(mate_score=30000)
				score_second_best = analysis_before[1]['score'].pov(turn).score(mate_score=30000)
				if score_best is not None and score_second_best is not None:
					if (score_best - score_second_best) >= soglia_mossa_geniale_gap:
						classification = "Mossa Geniale"
					else:
						classification = "Mossa Buona"
				else:
					classification = "Mossa Buona"
			else:
				classification = "Mossa Buona"
		else:
			# La mossa giocata NON è la migliore. Calcoliamo la perdita e classifichiamo l'errore.
			best_pov_score = best_alternative['score'].pov(turn)
			played_pov_score = eval_after_move.pov(turn)

			# Caso A: La mossa migliore era un matto che abbiamo mancato.
			if best_pov_score.is_mate() and best_pov_score.mate() > 0:
				classification = "Svarione"
				centipawn_loss = 5000  # Valore simbolico alto per il report testuale
			else:
				# Caso B: Calcolo standard della perdita in centipedoni (versione corretta).
				score_best = best_pov_score.score(mate_score=30000)
				score_played = played_pov_score.score(mate_score=30000)
				
				if score_best is not None and score_played is not None:
					# La perdita è la differenza tra la valutazione che avevamo e quella che abbiamo ottenuto.
					centipawn_loss = score_best - score_played
				else:
					centipawn_loss = 0 # Fallback
				
				# Classifichiamo l'errore in base alla perdita calcolata
				if centipawn_loss >= soglia_svarione:
					classification = "Svarione"
				elif centipawn_loss >= soglia_errore:
					classification = "Errore"
				elif centipawn_loss >= soglia_inesattezza:
					classification = "Inesattezza"
				elif centipawn_loss <= soglia_mossa_buona:
					classification = "Mossa Buona"
				else:
					classification = "Mossa Normale"

		if not classification:
			classification = "Mossa Normale"

		# Popoliamo le statistiche
		if classification in imprecision_stats:
			imprecision_stats[classification][color_key] += 1

		# Usiamo un valore "capped" (con un tetto massimo) per le statistiche ACPL,
		# per evitare che un singolo svarione enorme distorca completamente la media.
		capped_loss = min(centipawn_loss, CPL_STATISTICS_CAP)
		cpl_data[color_key].append(capped_loss)

		comment_str = f"{{OAA: {classification}. Perdita: {centipawn_loss/100:+.2f}}}"
		node.comment = (node.comment.strip() + " " + comment_str).strip() if node.comment else comment_str
		if classification in ["Svarione", "Errore", "Inesattezza"] and num_varianti > 0:
			varianti_da_aggiungere = analysis_before[:num_varianti]

			for var_info in varianti_da_aggiungere:
				pv = var_info.get('pv')
				if not isinstance(pv, list) or not pv:
					continue

				prima_mossa_variante = pv[0]
				if prima_mossa_variante.uci() != node.move.uci():
					var_node = node.parent.add_variation(prima_mossa_variante)

					# --- NUOVA LOGICA PER IL COMMENTO ---
					score_obj = var_info.get('score')
					commento_variante = ""

					# Controlliamo se la variante è una linea di matto
					if score_obj and score_obj.pov(turn).is_mate():
						mate_in = abs(score_obj.pov(turn).mate())

						# Costruiamo la linea di mosse descrittiva
						temp_board = parent_board.copy()
						mosse_descrizione = []
						for mossa in pv:
							mosse_descrizione.append(board_utils.DescribeMove(mossa, temp_board))
							temp_board.push(mossa)

						linea_completa = ", ".join(mosse_descrizione)
						commento_variante = f"{{OAA: Alternativa: Matto in {mate_in}: {linea_completa}}}"
					else:
						# Se non è matto, usiamo il formato standard con la valutazione
						var_score_str = _format_score(score_obj, turn)
						commento_variante = f"{{OAA: Alternativa: {var_score_str}}}"

					var_node.comment = commento_variante
					# --- FINE NUOVA LOGICA ---

					# Aggiungiamo il resto della linea al PGN (questo rimane uguale)
					if len(pv) > 1:
						var_node.add_line(pv[1:])
		analysis_results.append({
						"node": node,
						"classification": classification,
						"centipawn_loss": centipawn_loss,
						"alternatives_info": analysis_before,
						"eval_after_move": eval_after_move
			})
	print(f"\n\n{'='*40}\n" + _("Analisi automatica completata.") + f"\n{'='*40}")
	pgn_game.headers["Annotator"] = f'Orologic V{version.VERSION} (Analisi Automatica)'
	pgn_string_formatted = board_utils.format_pgn_comments(str(pgn_game))
	base_name = f'{pgn_game.headers.get("White", "B")}_vs_{pgn_game.headers.get("Black", "N")}_auto_{datetime.datetime.now().strftime("%Y%m%d")}'
	sanitized_pgn_name = config.sanitize_filename(base_name) + ".pgn"
	full_pgn_path = config.percorso_salvataggio(os.path.join("pgn", sanitized_pgn_name))
	try:
		with open(full_pgn_path, "w", encoding="utf-8-sig") as f:
			f.write(pgn_string_formatted)
		print(_("PGN analizzato salvato come: {path}").format(path=full_pgn_path))
	except Exception as e:
		print(_("Errore durante il salvataggio del PGN: {e}").format(e=e))
	genera_sommario_analitico_txt(pgn_game, sanitized_pgn_name.replace('.pgn',''), analysis_results, imprecision_stats, cpl_data, last_valid_eco_entry, mosse_da_saltare, num_varianti)
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
					desc_move = board_utils.DescribeMove(bestmove_uci, current_node.board(), annotation=None)
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
			white_material, black_material = board_utils.CalculateMaterial(current_node.board()); extra_prompt = "Mtrl: {white}/{black} ".format(white=white_material, black=black_material)
			Acusticator(["g#5", 0.03, 0, volume,"e5", 0.03, 0, volume,"d5", 0.03, 0, volume,"g6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "u":
			custom_board_view = board_utils.CustomBoard(current_node.board().fen())
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
			print(_("\nComandi disponibili in modalità analisi:")); menu(config.ANALYSIS_COMMAND,show_only=True)
			Acusticator(["d5", .7, 0, volume], kind=3, adsr=[.02,0,100,99])
		else: # Comando non riconosciuto
			Acusticator(["d3", 1.2, 0, volume], kind=3, adsr=[.02,0,100,99])
			print(_("Comando non riconosciuto."))
			node_changed = False # Assicura che non venga stampata descrizione

		# --- 4. Stampa Descrizione se Nodo Cambiato ---
		if node_changed and current_node.move:
			annotation_suffix = None
			for nag_value, suffix in config.NAG_REVERSE_MAP.items():
				if nag_value in current_node.nags:
					annotation_suffix = suffix
					break
			# Stampa la descrizione della mossa *su cui siamo arrivati*
			print("\n" + board_utils.DescribeMove(current_node.move,
												current_node.parent.board() if current_node.parent else pgn_game.board(),
												annotation=annotation_suffix))
	print(_("\nFine analisi"))
	annotator_updated_flag = False
	if saved:
		new_annotator = 'Orologic V{version} by {programmer}'.format(version=version.VERSION, programmer=version.PROGRAMMER)
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
			pgn_string_formatted = board_utils.format_pgn_comments(pgn_string_raw)
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
			sanitized_name = config.sanitize_filename(new_filename_base) + ".pgn"
			full_path = config.percorso_salvataggio(os.path.join("pgn", sanitized_name))
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
