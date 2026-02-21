import chess
import chess.engine
import chess.pgn
import os
import time
import datetime
import pyperclip
import re
import io
import sys
import copy
from . import config
from . import storage
from . import ui
from . import board_utils
from . import version
from GBUtils import dgt, menu, Acusticator, key, polipo

lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

# Globali Motore
ENGINE = None
ENGINE_NAME = "Nessuno"
analysis_time = 1.0
multipv = 3
cache_analysis = {}
oaa_analysis_cache = {}

def percorso_salvataggio(file):
	"""Restituisce il percorso assoluto partendo dalla cartella dell'eseguibile/script."""
	app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
	return os.path.join(app_path, file)

def SetAnalysisTime(t):
	global analysis_time; analysis_time = t
	cache_analysis.clear()

def SetMultipv(m):
	global multipv; multipv = m
	cache_analysis.clear()

def SearchForEngine():
	"""Cerca il motore UCI nel sistema. Restituisce (path, exe, False)"""
	if sys.platform == "win32":
		appdata_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Orologic", "Engine", "stockfish")
		if os.path.exists(appdata_path):
			for f in os.listdir(appdata_path):
				if f.endswith(".exe"): return appdata_path, f, False
	local_dir = percorso_salvataggio("engine")
	if os.path.exists(local_dir):
		for f in os.listdir(local_dir):
			if f.endswith(".exe"): return local_dir, f, False
	return None, None, False

def InitEngine():
	global ENGINE, ENGINE_NAME, analysis_time, multipv
	CloseEngine() # Chiudiamo sempre eventuali istanze precedenti per evitare processi orfani
	db = storage.LoadDB()
	
	# Caricamento parametri analisi globali
	if "default_analysis_time" in db: analysis_time = db["default_analysis_time"]
	else: db["default_analysis_time"] = analysis_time
	
	if "default_multipv" in db: multipv = db["default_multipv"]
	else: db["default_multipv"] = multipv
	
	cfg = db.get("engine_config", {})
	if not cfg:
		p, e, unused_v = SearchForEngine()
		if p and e:
			cfg = {"engine_path": os.path.join(p, e), "engine_is_relative": False, "hash_size": 128, "num_cores": 1, "skill_level": 20, "move_overhead": 0}
			db["engine_config"] = cfg; storage.SaveDB(db)
		else: ENGINE = None; ENGINE_NAME = "Nessuno"; storage.SaveDB(db); return False
	else:
		# Assicuriamoci che i default di analisi siano salvati se non c'erano
		storage.SaveDB(db)

	path = percorso_salvataggio(cfg["engine_path"]) if cfg.get("engine_is_relative") else cfg["engine_path"]
	if os.path.exists(path):
		try:
			ENGINE = chess.engine.SimpleEngine.popen_uci(path)
			ENGINE.configure({"Hash": cfg.get("hash_size", 128), "Threads": cfg.get("num_cores", 1), "Skill Level": cfg.get("skill_level", 20)})
			ENGINE_NAME = ENGINE.id.get("name", "UCI Engine")
			print(_("Motore {n} pronto.").format(n=ENGINE_NAME))
			return True
		except Exception as e:
			print(_("Errore motore: {e}").format(e=e))
			ENGINE = None; return False
	return False

def CloseEngine():
	global ENGINE
	if ENGINE: ENGINE.quit(); ENGINE = None

def CalculateMaterial(board):
	w, b = 0, 0
	for sq in chess.SQUARES:
		p = board.piece_at(sq)
		if p:
			val = config.PIECE_VALUES.get(p.symbol().upper(), 0)
			if p.color == chess.WHITE: w += val
			else: b += val
	return w, b

def CalculateEvaluation(board):
	if ENGINE is None: return None
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result: return None
		return analysis_result[0].get("score")
	except: return None

def CalculateBest(board, bestmove=True, as_san=False):
	Acusticator(["e5",.008,-1,config.VOLUME]) 
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=multipv)
		analysis = cache_analysis[fen]
		best_line = analysis[0].get("pv", [])
		if not best_line: return None
		if as_san:
			temp_board = board.copy()
			descriptive_moves = []
			move_number = 1
			i = 0
			while i < len(best_line):
				if temp_board.turn == chess.WHITE:
					white_move = best_line[i]
					white_descr = board_utils.DescribeMove(white_move, temp_board)
					temp_board.push(white_move)
					i += 1
					move_descr = _("{num}.").format(num=move_number) + " " + white_descr
					if i < len(best_line) and temp_board.turn == chess.BLACK:
						black_move = best_line[i]
						black_descr = board_utils.DescribeMove(black_move, temp_board)
						temp_board.push(black_move)
						i += 1
						move_descr += ", " + black_descr
					descriptive_moves.append(move_descr)
					move_number += 1
				else:
					black_move = best_line[i]
					black_descr = board_utils.DescribeMove(black_move, temp_board)
					temp_board.push(black_move)
					i += 1
					descriptive_moves.append(_("{num}... {desc}").format(num=move_number, desc=black_descr))
					move_number += 1
			score = analysis[0].get("score")
			mate_found = False
			if score is not None and score.relative.is_mate():
				mate_moves = abs(score.relative.mate())
				mate_found = True
			if bestmove:
				if mate_found:
					Acusticator(["a6",.008,1,config.VOLUME]) 
					return [_("Matto in {moves}, {first_move}").format(moves=mate_moves, first_move=descriptive_moves[0])]
				else:
					Acusticator(["f6",.008,1,config.VOLUME]) 
					return [descriptive_moves[0]]
			else:
				if mate_found: descriptive_moves.insert(0, _("Matto in {moves}:").format(moves=mate_moves))
				Acusticator(["d6",.008,1,config.VOLUME]) 
				return descriptive_moves
		else:
			if bestmove:
				Acusticator(["g5",.008,1,config.VOLUME]) 
				return best_line[0]
			else: return best_line
	except: return None

def CalculateWDL(board):
	if ENGINE is None: return None
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result: return None
		score = analysis_result[0].get("score")
		if score and hasattr(score, "wdl"):
			wdl = score.wdl()
			return (wdl[0]/10, wdl[1]/10, wdl[2]/10)
	except: pass
	return None

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
					black_move = pv[j+1]; black_san = temp_board.san(black_move)
					temp_board.push(black_move); move_str += " {san}".format(san=black_san); j += 2
				else: j += 1
				moves_with_numbers.append(move_str)
			else:
				move_num = temp_board.fullmove_number; black_move = pv[j]; black_san = temp_board.san(black_move)
				temp_board.push(black_move); moves_with_numbers.append("{num}... {san}".format(num=move_num, san=black_san)); j += 1
		line_summary = " ".join(moves_with_numbers)
		print(_("Linea {num}: {summary}").format(num=i, summary=line_summary))
	choice = dgt(_("Quale linea vuoi ispezionare? (1/{num_lines}) ").format(num_lines=len(analysis_lines)), kind="i", imin=1, imax=len(analysis_lines), default=1)
	Acusticator(["e5", 0.06, 0, config.VOLUME], kind=1, adsr=[0,0,100,0])
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves: print(_("Linea vuota, termine ispezione.")); return
	score = chosen_info.get("score")
	if score is not None and score.relative.is_mate(): eval_str = _("Mate in {moves}").format(moves=abs(score.relative.mate()))
	elif score is not None:
		cp = score.white().score()
		eval_str = "{cp:.2f}".format(cp=cp/100)
	else: eval_str = "0.00"
	total_moves = len(pv_moves); current_index = 1
	print(_("\nUtilizza questi comandi:"))
	menu(config.SMART_COMMANDS, show_only=True, ordered=False)
	print(_("\nIspezione Linea {n}").format(n=line_index+1))
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]: temp_board.push(move)
		current_move = pv_moves[current_index-1]
		move_verbose = board_utils.DescribeMove(current_move, temp_board)
		m_num = "{n}.".format(n=temp_board.fullmove_number) if temp_board.turn == chess.WHITE else "{n}...".format(n=temp_board.fullmove_number)
		smart_prompt = _("\n({current}/{total}) {move_num} {move_desc} CP: {cp}").format(current=current_index, total=total_moves, cp=eval_str, move_num=m_num, move_desc=move_verbose)
		cmd = key(smart_prompt).lower().strip()
		if cmd == ".": break
		elif cmd == "s":
			if current_index > 1: current_index -= 1
			else: Acusticator(["c4", 0.1, -0.5, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]); print(_("\nNon ci sono mosse precedenti."))
		elif cmd == "?":
			Acusticator(["d5", 0.08, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
			menu(config.SMART_COMMANDS, show_only=True, ordered=False)
		elif cmd == "r":
			temp_board = board.copy()
			try:
				for move in pv_moves[:current_index]: temp_board.push(move)
			except Exception as push_err: print(_("\nErrore: {error}").format(error=push_err)); eval_str = "ERR_NAV"; continue
			score_object_si = CalculateEvaluation(temp_board)
			Acusticator(["e5",.008,-1,config.VOLUME]) 
			if score_object_si is not None:
				new_eval_str = "N/A"; pov_score_si = score_object_si.pov(temp_board.turn)
				if pov_score_si.is_mate(): new_eval_str = _("M{moves}").format(moves=abs(pov_score_si.mate()))
				else:
					cp_si = score_object_si.white().score(mate_score=30000)
					if cp_si is not None: new_eval_str = "{cp:+.2f}".format(cp=cp_si/100)
					else: new_eval_str = "ERR"
				eval_str = new_eval_str; Acusticator(["g5", 0.1, 0.3, config.VOLUME], kind=1, adsr=[5,5,90,5]); print(_("\nValutazione aggiornata."))
			else: Acusticator(["a3", 0.15, 0, config.VOLUME], kind=2, adsr=[5, 20, 0, 75]); print(_("\nImpossibile aggiornare.")); eval_str = "N/A"
		elif cmd == "d":
			if current_index < total_moves: current_index += 1
			else: Acusticator(["c4", 0.1, 0.5, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]); print(_("\nNon ci sono mosse successive."))
		else: Acusticator(["b3", 0.12, 0, config.VOLUME], kind=2, adsr=[5, 15, 20, 60]); print(_("\nComando non riconosciuto."))

def LoadPGNFromClipboard():
	try:
		text = pyperclip.paste()
		if not text.strip(): return None
		pgn_io = io.StringIO(text); games = []
		while True:
			g = chess.pgn.read_game(pgn_io)
			if not g: break
			games.append(g)
		if not games: return None
		if len(games) == 1: return games[0]
		partite = {i+1: f"{g.headers.get('White')} vs {g.headers.get('Black')}" for i, g in enumerate(games)}
		c = menu(partite, p=_("Scegli partita: "), show=True, numbered=True)
		return games[int(c)-1] if c else None
	except: return None

def AnalyzeGame(pgn_game):
	print(_("\nModalita' analisi.\nHeaders della partita:\n"))
	for k, v in pgn_game.headers.items(): print(f"  {k}: {v}")
	current_node = pgn_game; extra_prompt = ""; comment_auto_read = True; saved = False
	total_moves = len(list(pgn_game.mainline_moves()))
	
	while True:
		prompt_move_part = _("Start")
		if current_node.move:
			move_san = current_node.san()
			parent_board = current_node.parent.board()
			fullmove = parent_board.fullmove_number
			move_indicator = "{num}. {san}".format(num=fullmove, san=move_san) if parent_board.turn == chess.WHITE else "{num}... {san}".format(num=fullmove, san=move_san)
			
			if current_node.parent and len(current_node.parent.variations) > 1:
				siblings = current_node.parent.variations
				try:
					idx = siblings.index(current_node)
					if idx == 0 and len(siblings) > 1: prompt_move_part = "<{indicator}".format(indicator=move_indicator)
					elif idx > 0 and idx < len(siblings) - 1: prompt_move_part = "<{indicator}>".format(indicator=move_indicator)
					elif idx > 0 and idx == len(siblings) - 1: prompt_move_part = "{indicator}>".format(indicator=move_indicator)
					else: prompt_move_part = move_indicator
				except ValueError: prompt_move_part = move_indicator
			else: prompt_move_part = move_indicator

		if current_node.move and current_node.comment and not comment_auto_read: prompt_move_part += "-"
		
		prompt = "\n{extra} {move_part}: ".format(extra=extra_prompt, move_part=prompt_move_part)
		extra_prompt = ""

		if current_node.comment and comment_auto_read: print(_("Commento:"), current_node.comment)
		elif current_node.comment and not comment_auto_read: Acusticator(["c7", 0.024, 0, config.VOLUME], kind=1, adsr=[0,0,100,0])
		
		cmd = key(prompt).lower().strip()
		previous_node = current_node; node_changed = False

		if cmd == ".": break
		elif cmd == "a": # Inizio o nodo padre
			node = current_node
			while node.parent is not None and node == node.parent.variations[0]: node = node.parent
			if node.parent is None:
				if node.variations and current_node != node.variations[0]: current_node = node.variations[0]
				else: Acusticator(["c4", 0.1, -0.5, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]); print(_("\nGia' all'inizio della partita."))
			else: current_node = node
			node_changed = (current_node != previous_node)
		elif cmd == "s": # Indietro
			if current_node.parent:
				current_node = current_node.parent
				Acusticator(["g5", .03, -.2, config.VOLUME, "c5", .03, -.8, config.VOLUME], kind=1, adsr=[2,5,90,5])
			else: Acusticator(["c4", 0.1, -0.7, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]); print(_("\nNessuna mossa precedente."))
			node_changed = (current_node != previous_node)
		elif cmd == "d": # Avanti
			if current_node.variations:
				current_node = current_node.variations[0]
				Acusticator(["c5", .03, .2, config.VOLUME, "g5", .03, .8, config.VOLUME], kind=1, adsr=[2,5,90,5])
			else: Acusticator(["c4", 0.1, 0.7, config.VOLUME], kind=2, adsr=[10, 10, 30, 50]); print(_("\nNon ci sono mosse successive."))
			node_changed = (current_node != previous_node)
		elif cmd == "f": # Fine linea
			start = current_node
			while current_node.variations: current_node = current_node.variations[0]
			node_changed = (current_node != start)
			if node_changed:
				Acusticator(["g5", 0.1, 0, config.VOLUME, "p", 0.1, 0, 0, "c6", 0.05, 0, config.VOLUME, "d6", 0.05, 0, config.VOLUME, "g6", 0.2, 0, config.VOLUME], kind=1, adsr=[5,5,90,5])
				print(_("Sei arrivato alla fine della linea principale."))
			else: print(_("Gia' alla fine della linea principale."))
		elif cmd == "g": # Variante precedente
			if current_node.parent:
				vars = current_node.parent.variations
				try:
					idx = vars.index(current_node)
					if idx > 0:
						current_node = vars[idx - 1]
						Acusticator(["d#5", 0.07, -0.4, config.VOLUME], kind=1, adsr=[2,5,90,5])
					else:
						Acusticator(["c#4", 0.1, -0.6, config.VOLUME], kind=2, adsr=[10, 10, 30, 50])
						print(_("Non ci sono varianti precedenti."))
				except ValueError: print(_("Errore: nodo corrente non trovato."))
			else: print(_("Nessun nodo variante disponibile (sei alla radice)."))
			node_changed = (current_node != previous_node)
		elif cmd == "h": # Variante successiva
			if current_node.parent:
				vars = current_node.parent.variations
				try:
					idx = vars.index(current_node)
					if idx < len(vars) - 1:
						current_node = vars[idx + 1]
						Acusticator(["f5", 0.07, 0.4, config.VOLUME], kind=1, adsr=[2,5,90,5])
					else:
						Acusticator(["c#4", 0.1, 0.6, config.VOLUME], kind=2, adsr=[10, 10, 30, 50])
						print(_("Non ci sono varianti successive."))
				except ValueError: print(_("Errore: nodo corrente non trovato."))
			else: print(_("Nessun nodo variante disponibile (sei alla radice)."))
			node_changed = (current_node != previous_node)
		elif cmd == "j": # Headers
			Acusticator(["d5", 0.08, 0, config.VOLUME, "p", 0.08, 0, 0, "d6", 0.06, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
			print(_("\nHeader della partita:"))
			for k, v in pgn_game.headers.items(): print(f"  {k}: {v}")
		elif cmd == "k": # Vai a mossa
			Acusticator(["g3", 0.06, 0, config.VOLUME, "b3", 0.06, 0, config.VOLUME, "a3", 0.06, 0, config.VOLUME], kind=1, adsr=[0,0,100,0])
			max_m = (total_moves + 1) // 2
			target = dgt(_("\nVai a mossa n.# (Max {m}): ").format(m=max_m), kind="i", imin=1, imax=max_m)
			target_ply = max(0, 2 * (target - 1))
			found = pgn_game
			for i, node in enumerate(pgn_game.mainline()):
				if i == target_ply: found = node; break
			else:
				if target_ply > 0: print(_("\nRaggiunta la fine della linea prima della mossa richiesta."))
			current_node = found
			Acusticator(["g6", 0.06, 0, config.VOLUME, "b6", 0.06, 0, config.VOLUME, "a6", 0.06, 0, config.VOLUME], kind=1, adsr=[0,0,100,0])
			node_changed = (current_node != previous_node)
		elif cmd == "l": # Carica
			new = LoadPGNFromClipboard()
			if new:
				pgn_game = new; current_node = pgn_game; node_changed = False
				total_moves = len(list(pgn_game.mainline_moves()))
				Acusticator(["c6", 0.15, 0, config.VOLUME], kind=1, adsr=[5, 10, 80, 5])
				print(_("\nNuovo PGN caricato.")); [print(f"  {k}: {v}") for k, v in pgn_game.headers.items()]
		elif cmd == "q": # Bestmove prompt
			res = CalculateBest(current_node.board(), as_san=True)
			if res: extra_prompt = f" BM: {res[0]} "; Acusticator(["f6", 0.02, 0, config.VOLUME], kind=1)
		elif cmd == "w": # Bestline display
			if ENGINE:
				print(_("\nCalcolo bestline...")); fen = current_node.board().fen()
				if fen not in cache_analysis: cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
				analysis = cache_analysis[fen]
				if analysis:
					Acusticator(["f6", 0.02, 0, config.VOLUME, "p", .15, 0, 0, "a6", 0.02, 0, config.VOLUME, "p", .15, 0, 0, "c7", 0.02, 0, config.VOLUME, "p", .15, 0, 0, "e7", 0.02, 0, config.VOLUME, "p", .15, 0, 0, "g7", 0.02, 0, config.VOLUME, "p", .15, 0, 0, "b7", 0.02, 0, config.VOLUME], kind=1)
					print(_("\nLinee migliori:"))
					for i, info in enumerate(analysis, start=1):
						pv = info.get("pv", [])
						score = info.get("score").pov(current_node.board().turn)
						eval_str = _("M{m}").format(m=abs(score.mate())) if score.is_mate() else "{cp:+.2f}".format(cp=score.score()/100) if score.score() is not None else _("N/A")
						print(_("Linea {i} ({score}):").format(i=i, score=eval_str))
						print(board_utils.format_pv_descriptively(current_node.board(), pv))
					
					if analysis[0].get("pv"):
						bm_san = current_node.board().san(analysis[0]["pv"][0])
						score = analysis[0].get("score").pov(current_node.board().turn)
						eval_str = _("M{m}").format(m=abs(score.mate())) if score.is_mate() else "{cp:+.2f}".format(cp=score.score()/100) if score.score() is not None else _("N/A")
						extra_prompt = _(" BM: {score} {san} ").format(score=eval_str, san=bm_san)
				else:
					Acusticator(["a#3", 0.15, 0.5, config.VOLUME], kind=2, adsr=[5, 20, 0, 75]); print(_("\nImpossibile calcolare la bestline.")); extra_prompt = _(" BM: N/A ")
			else: print(_("\nMotore non inizializzato.")); Acusticator(["a#3", 0.15, 0.5, config.VOLUME], kind=2, adsr=[5, 20, 0, 75])
		elif cmd == "e": # Deep analysis
			if ENGINE:
				print(_("\nAnalisi in corso...")); fen = current_node.board().fen()
				if fen not in cache_analysis: cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
				analysis = cache_analysis[fen]
				for i, info in enumerate(analysis):
					pv = info.get("pv", []); score = info.get("score").pov(current_node.board().turn)
					san_moves = []
					temp_board = current_node.board().copy()
					for m in pv:
						san_moves.append(temp_board.san(m))
						temp_board.push(m)
					san_pv = " ".join(san_moves)
					print(_("Linea {i} ({s}): {pv}").format(i=i+1, s=score, pv=san_pv))
				if ui.enter_escape(_("\nIspezione smart? (INVIO si', ESC no): ")): SmartInspection(analysis, current_node.board())
		elif cmd == "z": # Variante bestline
			pv = CalculateBest(current_node.board(), bestmove=False, as_san=False)
			if pv:
				current_node.add_variation(pv[0]).add_line(pv[1:])
				saved = True; print(_("\nVariante aggiunta.")); Acusticator(["a5", 0.12, 0.3, config.VOLUME,"b5", 0.12, 0.3, config.VOLUME,"c6", 0.12, 0.3, config.VOLUME,"d6", 0.12, 0.3, config.VOLUME,"e6", 0.12, 0.3, config.VOLUME], kind=1, adsr=[4,8,85,5])
		elif cmd == "x": # Commento BM
			bm = CalculateBest(current_node.board(), as_san=True)
			if bm:
				current_node.comment = (current_node.comment or "").strip() + _(" {{BM: {bm}}}").format(bm=bm[0])
				saved = True; print(_("\nCommento aggiunto.")); Acusticator(["a5", 0.1, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
		elif cmd == "c": # Commento manuale
			Acusticator(["d6", 0.012, 0, config.VOLUME, "p", 0.15, 0, 0, "a6", 0.012, 0, config.VOLUME], kind=1, adsr=[0.01,0,100,0.01])
			comm = dgt(_("\nInserisci il commento: "), kind="s").strip()
			if comm: current_node.comment = (current_node.comment or "").strip() + " " + comm; saved = True; Acusticator(["a6", 0.012, 0, config.VOLUME, "p", 0.15, 0, 0, "d6", 0.012, 0, config.VOLUME], kind=1, adsr=[0.01,0,100,0.01])
		elif cmd == "v": # Commento valutazione
			score = CalculateEvaluation(current_node.board())
			if score:
				ev = score.white().score(mate_score=30000)
				current_node.comment = (current_node.comment or "").strip() + _(" {{Val: {ev:+.2f}}}").format(ev=ev/100)
				saved = True; print(_("\nValutazione commentata.")); Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
		elif cmd == "r": # Valutazione prompt
			score = CalculateEvaluation(current_node.board())
			if score:
				ev = score.white().score(mate_score=30000)
				extra_prompt = _(" CP: {ev:+.2f} ").format(ev=ev/100); Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
		elif cmd == "t": # WDL prompt
			wdl = CalculateWDL(current_node.board())
			if wdl: extra_prompt = _(" W:{w:.1f}% D:{d:.1f}% L:{l:.1f}% ").format(w=wdl[0], d=wdl[1], l=wdl[2]); Acusticator(["g#5", 0.03, 0, config.VOLUME], kind=1)
		elif cmd == "y": # Materiale prompt
			w, b = CalculateMaterial(current_node.board()); extra_prompt = _(" Mtrl: {w}/{b} ").format(w=w, b=b); Acusticator(["g#5", 0.03, 0, config.VOLUME], kind=1)
		elif cmd == "u": # Scacchiera
			print("\n" + str(board_utils.CustomBoard(current_node.board().fen()))); Acusticator(["d6", 0.03, 0, config.VOLUME], kind=1)
		elif cmd == "i": # Tempo
			new_t = dgt(_("\nTempo analisi (s): "), kind="f", default=analysis_time); SetAnalysisTime(new_t)
		elif cmd == "o": # Linee
			new_m = dgt(_("\nLinee analisi: "), kind="i", default=multipv); SetMultipv(new_m)

		elif cmd == "b": # Toggle commenti
			comment_auto_read = not comment_auto_read
			if comment_auto_read: Acusticator(["g5", 0.025, 0, config.VOLUME, "p", 0.04, 0, 0, "b6", 0.035, 0, config.VOLUME], kind=1); print(_("\nLettura automatica abilitata."))
			else: Acusticator(["g5", 0.025, 0, config.VOLUME, "p", 0.04, 0, 0, "b4", 0.035, 0, config.VOLUME], kind=1); print(_("\nLettura automatica disabilitata."))
		elif cmd == "n": # Elimina commento
			if current_node.comment:
				if ui.enter_escape(_("\nEliminare il commento? (INVIO si', ESC no): ")):
					current_node.comment = ""; saved = True; print(_("\nCommento eliminato."))
					Acusticator(["e4", 0.1, -0.4, config.VOLUME], kind=1, adsr=[5, 10, 70, 15])
		elif cmd == "?":
			print(_("\nComandi disponibili:")); menu(config.ANALYSIS_COMMANDS, show_only=True, ordered=False)
		else: Acusticator(["d3", 0.5, 0, config.VOLUME], kind=3)

		if node_changed and current_node.move:
			print("\n" + board_utils.DescribeMove(current_node.move, current_node.parent.board()))
	
	if saved:
		try: 
			formatted_pgn = board_utils.format_pgn_comments(str(pgn_game))
			pyperclip.copy(formatted_pgn)
			print(_("PGN aggiornato negli appunti."))
		except: pass

def analyze_position_deep(board, limit, multipv_count=3):
	global oaa_analysis_cache
	fen = board.fen()
	cache_key = f"{fen}_{limit.time}_{limit.depth}_{limit.nodes}_{multipv_count}"
	if cache_key in oaa_analysis_cache: return oaa_analysis_cache[cache_key]
	try:
		info = ENGINE.analyse(board, limit, multipv=multipv_count)
		results = []
		for i, analysis in enumerate(info):
			score = analysis.get("score"); pv = analysis.get("pv")
			if score is not None and pv:
				results.append({"rank": i + 1, "move": pv[0], "score": score, "pv": pv})
		oaa_analysis_cache[cache_key] = results
		return results
	except: return None

def _stampa_albero_pgn(node, data_map, lines, w_name, b_name, num_var, classification_labels, indent_level=0):
	"""
	Funzione ricorsiva per stampare l'albero delle varianti nel file TXT.
	Output verboso, accessibile e con valutazioni ASSOLUTE (dal punto di vista del Bianco).
	"""
	if not node.variations:
		return

	# La prima variazione è sempre la mossa principale
	main_move_node = node.variations[0]
	
	# --- FORMATTAZIONE MOSSA PRINCIPALE ---
	move_desc = board_utils.DescribeMove(main_move_node.move, node.board())
	
	res = data_map.get(main_move_node, {})
	classif = res.get('classification', '')
	eval_val = res.get('eval_after_move', '') # Score object
	cpl = res.get('centipawn_loss', 0)
	
	# 3. Formattazione Valutazione (ASSOLUTA: Riferita al BIANCO)
	eval_str = ""
	if eval_val:
		# Usa score.white() per avere sempre la valutazione dal punto di vista del bianco
		white_score = eval_val.white()
		if white_score.is_mate(): 
			eval_str = _("Matto in {m}").format(m=white_score.mate()) # Mate positivo = vince bianco, negativo = vince nero
		else: 
			cp_val = white_score.score(mate_score=30000)
			if cp_val is not None: 
				eval_str = f"{cp_val/100:+.2f}" # Es. +0.33 (vantaggio bianco), -0.50 (vantaggio nero)

	# 4. Costruzione Riga
	prefix = " " * (indent_level * 2)
	move_num = node.board().fullmove_number
	dot = "." if node.board().turn == chess.WHITE else "..."
	
	line_content = f"{move_num}{dot} {move_desc}"
	
	details = []
	if eval_str: details.append(_("Val: {v}").format(v=eval_str))
	if cpl > 0: details.append(_("CPL: {c:.2f}").format(c=cpl/100))
	
	if details:
		line_content += " ({0})".format(', '.join(details))

	if classif: 
		label = classification_labels.get(classif, classif)
		line_content += f" [{label}]"
	
	lines.append(f"{prefix}{line_content}")
	
	# Commenti
	raw_comment = main_move_node.comment
	if raw_comment:
		clean_comment = re.sub(r'\[OAA:.*?\]', '', raw_comment).strip()
		if clean_comment:
			lines.append(_("{p}  Note: {c}").format(p=prefix, c=clean_comment))

	# --- GESTIONE VARIANTI ALTERNATIVE ---
	if len(node.variations) > 1:
		for i, variation in enumerate(node.variations[1:], start=1):
			var_prefix = " " * ((indent_level + 1) * 2)
			lines.append(_("{p}(Variante {i}):").format(p=var_prefix, i=i))
			
			var_move_desc = board_utils.DescribeMove(variation.move, node.board())
			var_move_num = node.board().fullmove_number
			var_dot = "." if node.board().turn == chess.WHITE else "..."
			
			var_info = ""
			if variation.comment and "[OAA:" in variation.comment:
				match = re.search(r'\[OAA: (.*?)\]', variation.comment)
				if match: var_info = f" [{match.group(1)}]"
			
			lines.append(f"{var_prefix}  {var_move_num}{var_dot} {var_move_desc}{var_info}")
			
			_stampa_albero_pgn(variation, data_map, lines, w_name, b_name, num_var, classification_labels, indent_level + 2)

	# --- CONTINUAZIONE MAINLINE ---
	_stampa_albero_pgn(main_move_node, data_map, lines, w_name, b_name, num_var, classification_labels, indent_level)

def genera_sommario_analitico_txt(pgn_game, base_f, results, stats, cpl_d, eco, skip, n_var, duration, engine_metadata=None):
	l10n_analysis = ui.L10N.get("analysis", {})
	classification_labels = {
		"Svarione": l10n_analysis.get("blunder", _("Svarione")),
		"Errore": l10n_analysis.get("mistake", _("Errore")),
		"Inesattezza": l10n_analysis.get("inaccuracy", _("Inesattezza")),
		"Mossa Buona": l10n_analysis.get("good", _("Mossa Buona")),
		"Mossa Geniale": l10n_analysis.get("brilliant", _("Mossa Geniale")),
		"Mossa Normale": l10n_analysis.get("normal", _("Mossa Normale")),
		"Teoria": l10n_analysis.get("book", _("Teoria"))
	}
	now_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
	lines = [
		_("Orologic Analisi Automatica [OAA] V.{v}").format(v=version.VERSION),
		_("Generato il: {d}").format(d=now_str),
		""
	]

	if engine_metadata:
		lines.append(_("Motore utilizzato:"))
		lines.append(_("  Nome: {n}").format(n=engine_metadata.get('name', _('N/A'))))
		lines.append(_("  Autore: {a}").format(a=engine_metadata.get('author', _('N/A'))))
		if 'options' in engine_metadata:
			opts = engine_metadata['options']
			lines.append(_("  Configurazione: Hash={h}MB, Threads={t}, Livello={s}").format(h=opts.get('Hash', '?'), t=opts.get('Threads', '?'), s=opts.get('Skill Level', '?')))
		lines.append("")
	
	# Dati Partita (Tutti gli headers)
	for key, val in pgn_game.headers.items():
		lines.append(f"{key}: {val}")
	
	# Risultato esplicito (per accessibilità rapida)
	res = pgn_game.headers.get("Result", "*")
	if res == "1-0": lines.append(_("Esito: Vince il Bianco"))
	elif res == "0-1": lines.append(_("Esito: Vince il Nero"))
	elif res == "1/2-1/2": lines.append(_("Esito: Patta"))
	
	lines.append("")
	
	# Info Analisi
	if skip > 0:
		lines.append(_("Nota: Le prime {s} semimosse (apertura) sono state escluse dall'analisi.").format(s=skip))
	lines.append(_("Durata Analisi: {m}m {s}s").format(m=int(duration // 60), s=int(duration % 60)))
	
	lines.append("")
	lines.append(_("Statistiche:"))
	w_n = pgn_game.headers.get("White", _("Bianco"))
	b_n = pgn_game.headers.get("Black", _("Nero"))
	
	def calc_avg(l): return sum(l)/len(l) if l else 0
	
	lines.append(_("Precisione (ACPL - piu' basso e' meglio):"))
	lines.append(f"  {w_n}: {calc_avg(cpl_d['w']):.2f}")
	lines.append(f"  {b_n}: {calc_avg(cpl_d['b']):.2f}")
	
	lines.append(_("Errori commessi:"))
	for t in ["Mossa Geniale", "Mossa Buona", "Inesattezza", "Errore", "Svarione"]:
		s = stats.get(t, {'w':0, 'b':0})
		if s['w'] > 0 or s['b'] > 0:
			lines.append(_("  {t}: {w_name}={w_val}, {b_name}={b_val}").format(t=classification_labels[t], w_name=w_n, w_val=s['w'], b_name=b_n, b_val=s['b']))
	
	lines.append("")
	lines.append(_("Dettaglio Analisi:"))
	
	# Mappa i risultati
	data_map = {r['node']: r for r in results if 'node' in r}
	
	# Stampa Albero
	_stampa_albero_pgn(pgn_game, data_map, lines, w_n, b_n, n_var, classification_labels)
	
	# Footer
	lines.append("")
	lines.append(_("Fine Analisi Orologic V.{v}").format(v=version.VERSION))
	
	# Salvataggio
	f_p = percorso_salvataggio(os.path.join("txt", config.sanitize_filename(base_f) + ".txt"))
	try:
		full_text = "\n".join(lines)
		with open(f_p, "w", encoding="utf-8") as f: f.write(full_text)
		print(_("Riepilogo testuale salvato in: {p}").format(p=f_p))
		try: 
			pyperclip.copy(full_text)
			print(_("Riepilogo copiato negli appunti."))
		except: pass
	except Exception as e:
		print(_("Errore salvataggio TXT: {e}").format(e=e))

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
		if not score_obj: return _("N/A")
		pov_score = score_obj.pov(pov_color)
		if pov_score.is_mate():
			return _("M{m}").format(m=abs(pov_score.mate()))
		else:
			# La valutazione e' sempre dal punto di vista del bianco, quindi la adattiamo
			cp = score_obj.white().score(mate_score=30000)
			if cp is None: return _("N/A")
			final_cp = cp if pov_color == chess.WHITE else -cp
			return f"{final_cp/100:+.2f}"

	print(_("\n--- Analisi Automatica della Partita ---"))
	
	# Caricamento configurazione soglie da DB
	db = storage.LoadDB()
	thresholds = db.get("analysis_thresholds", {"inesattezza": 50, "errore": 100, "svarione": 250})
	soglia_inesattezza = thresholds["inesattezza"]
	soglia_errore = thresholds["errore"]
	soglia_svarione = thresholds["svarione"]
	
	# Parametri fissi per ora
	soglia_mossa_buona = 20
	soglia_mossa_geniale_gap = 180
	num_varianti = dgt(_("Varianti [{v}]: ").format(v=multipv), kind="i", imin=1, imax=10, default=multipv)

	print(_("\nImpostazione dei parametri di analisi:"))
	analysis_mode_map = {
		"t": _("Tempo per mossa (secondi)"),
		"p": _("Profondita' fissa (ply)"),
		"n": _("Numero di nodi per mossa")
	}
	analysis_mode = menu(analysis_mode_map, show=True, keyslist=True, ntf=_("Scelta non valida: "))
	limit = None
	if analysis_mode == 't':
		value = dgt(_("Inserisci i secondi per mossa: [INVIO per 1] "), kind="f", fmin=0.1, fmax=60, default=1)
		limit = chess.engine.Limit(time=value)
	elif analysis_mode == 'p':
		value = dgt(_("Inserisci la profondita' di analisi: [INVIO per 18] "), kind="i", imin=5, imax=50, default=18)
		limit = chess.engine.Limit(depth=value)
	elif analysis_mode == 'n':
		value = dgt(_("Inserisci il numero di nodi da analizzare (in migliaia): [INVIO per 25] "), kind="i", imin=5, imax=99999, default=25)
		limit = chess.engine.Limit(nodes=value * 1000)
	else:
		print(_("Scelta non valida. Analisi annullata."))
		return

	truncate_length = dgt(_("Tronca varianti a (0=intere) [0]: "), kind="i", imin=0, imax=50, default=0)

	mosse_da_saltare = 0
	last_valid_eco_entry = None
	if ui.enter_escape(_("Vuoi saltare automaticamente le mosse di apertura note? (INVIO per si', ESC per specificare manualmente): ")):
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
			print(_("L'analisi saltera' le prime {n} semimosse.").format(n=mosse_da_saltare))
	else:
		mosse_da_saltare = dgt(_("Quante semimosse (ply) iniziali vuoi saltare? (INVIO per {n}) ".format(n=mosse_da_saltare)), kind="i", imin=0, imax=40, default=mosse_da_saltare)
	
	# Dati Motore per Report
	engine_metadata = {}
	if ENGINE:
		engine_metadata['name'] = ENGINE.id.get('name', _('Sconosciuto'))
		engine_metadata['author'] = ENGINE.id.get('author', _('Sconosciuto'))
		
		cfg = db.get("engine_config", {})
		engine_metadata['options'] = {
			'Hash': cfg.get('hash_size', '?'),
			'Threads': cfg.get('num_cores', '?'),
			'Skill Level': cfg.get('skill_level', '?')
		}

	print("\n" + "="*40 + _("\nInizio analisi... (Premi ESC per interrompere)") + "\n" + "="*40)
	start_time = time.time()
	
	global oaa_analysis_cache
	oaa_analysis_cache.clear()

	# Assicuriamoci di essere alla radice
	pgn_game = pgn_game.root()
	mainline_nodes = list(pgn_game.mainline())
	
	analysis_results = []
	l10n_analysis = ui.L10N.get("analysis", {})
	classification_labels = {
		"Svarione": l10n_analysis.get("blunder", _("Svarione")),
		"Errore": l10n_analysis.get("mistake", _("Errore")),
		"Inesattezza": l10n_analysis.get("inaccuracy", _("Inesattezza")),
		"Mossa Buona": l10n_analysis.get("good", _("Mossa Buona")),
		"Mossa Geniale": l10n_analysis.get("brilliant", _("Mossa Geniale")),
		"Mossa Normale": l10n_analysis.get("normal", _("Mossa Normale")),
		"Teoria": l10n_analysis.get("book", _("Teoria"))
	}
	imprecision_stats = { "Svarione": {'w': 0, 'b': 0}, "Errore": {'w': 0, 'b': 0}, "Inesattezza": {'w': 0, 'b': 0}, "Mossa Buona": {'w': 0, 'b': 0}, "Mossa Geniale": {'w': 0, 'b': 0}, "Mossa Normale": {'w':0, 'b':0} }
	cpl_data = {'w': [], 'b': []}

	# NOTA: Rimosso analysis_after per forzare ricalcolo preciso
	for i, node in enumerate(mainline_nodes):
		if key(attesa=0.002) == '\x1b':
			Acusticator(["c3", 0.3, 0.5, config.VOLUME], kind=2)
			print(_("\nAnalisi interrotta dall'utente."))
			break
		
		ply = i + 1
		if ply <= mosse_da_saltare:
			analysis_results.append({
				'node': node,
				'classification': "Teoria",
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
		print(_("\rPLY {ply}/{total} {san:<12} | Tempo: {t}").format(ply=ply, total=total_plys, san=san_str, t=time_str), end="")

		multipv_needed = max(3, num_varianti)
		
		# 1. Analisi "BEFORE" (sulla posizione di partenza, per trovare la best move e alternative)
		analysis_before = analyze_position_deep(parent_board, limit, multipv_needed)
		
		if not analysis_before: continue
		if truncate_length > 0:
			for info in analysis_before:
				if 'pv' in info: info['pv'] = info['pv'][:truncate_length]

		best_alternative = analysis_before[0]

		# 2. Analisi "AFTER" (valutazione precisa della mossa giocata)
		analysis_after = analyze_position_deep(current_board, limit, multipv_count=1)
		
		if not analysis_after: continue
		if truncate_length > 0:
			for info in analysis_after:
				if 'pv' in info: info['pv'] = info['pv'][:truncate_length]

		eval_after_move = analysis_after[0]['score']
		best_alternative_move = best_alternative['move']
		centipawn_loss = 0
		classification = ""

		CPL_STATISTICS_CAP = 1000

		# 3. Confronto e Classificazione
		if node.move.uci() == best_alternative_move.uci():
			eval_after_move = best_alternative['score']
			
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
			best_pov_score = best_alternative['score'].pov(turn)
			played_pov_score = eval_after_move.pov(turn)

			if best_pov_score.is_mate() and best_pov_score.mate() > 0:
				classification = "Svarione"
				centipawn_loss = 5000 
			else:
				score_best = best_pov_score.score(mate_score=30000)
				score_played = played_pov_score.score(mate_score=30000)
				
				if score_best is not None and score_played is not None:
					centipawn_loss = max(0, score_best - score_played)
				else:
					centipawn_loss = 0 
				
				if centipawn_loss >= soglia_svarione: classification = "Svarione"
				elif centipawn_loss >= soglia_errore: classification = "Errore"
				elif centipawn_loss >= soglia_inesattezza: classification = "Inesattezza"
				elif centipawn_loss <= soglia_mossa_buona: classification = "Mossa Buona"
				else: classification = "Mossa Normale"

		if not classification: classification = "Mossa Normale"

		if classification in imprecision_stats:
			imprecision_stats[classification][color_key] += 1

		capped_loss = min(centipawn_loss, CPL_STATISTICS_CAP)
		cpl_data[color_key].append(capped_loss)

		if eval_after_move.pov(turn).is_mate():
			mate_val = abs(eval_after_move.pov(turn).mate())
			comment_str = _("[OAA: {cl}. Matto in {m}]").format(cl=classification_labels[classification], m=mate_val)
			
			if classification not in ["Svarione", "Errore", "Inesattezza"]:
				pv = analysis_after[0].get('pv')
				if pv:
					next_game_move = None
					if node.variations:
						next_game_move = node.variations[0].move
					
					first_pv_move = pv[0]
					
					if not next_game_move or next_game_move != first_pv_move:
						var_node = node.add_variation(first_pv_move)
						if len(pv) > 1: var_node.add_line(pv[1:])
						
						var_node.comment = _("[OAA: Segue Matto in {m}]").format(m=mate_val)
						
		else:
			comment_str = _("[OAA: {cl}. Perdita: {cpl:+.2f}]").format(cl=classification_labels[classification], cpl=centipawn_loss/100)
		
		node.comment = (node.comment.strip() + " " + comment_str).strip() if node.comment else comment_str
		
		# Aggiunta Varianti al PGN
		if classification in ["Svarione", "Errore", "Inesattezza"] and num_varianti > 0:
			varianti_da_aggiungere = analysis_before[:num_varianti]

			for var_info in varianti_da_aggiungere:
				pv = var_info.get('pv')
				if not isinstance(pv, list) or not pv: continue

				prima_mossa_variante = pv[0]
				if prima_mossa_variante.uci() != node.move.uci():
					# Controlla duplicati
					exists = any(v.move.uci() == prima_mossa_variante.uci() for v in node.parent.variations)
					if not exists:
						var_node = node.parent.add_variation(prima_mossa_variante)
						score_obj = var_info.get('score')
						commento_variante = ""

						if score_obj and score_obj.pov(turn).is_mate():
							mate_in = abs(score_obj.pov(turn).mate())
							commento_variante = _("[OAA: Alt: Matto in {m}]").format(m=mate_in)
						else:
							var_score_str = _format_score(score_obj, turn)
							commento_variante = _("[OAA: Alt: {s}]").format(s=var_score_str)

						var_node.comment = commento_variante
						if len(pv) > 1: var_node.add_line(pv[1:])
		
		analysis_results.append({
						"node": node,
						"classification": classification,
						"centipawn_loss": centipawn_loss,
						"alternatives_info": analysis_before,
						"eval_after_move": eval_after_move
			})

	print(f"\n\n{'='*40}\n" + _("Analisi automatica completata.") + f"\n{'='*40}")
	pgn_game.headers["Annotator"] = _("Orologic V{v} (Auto)").format(v=version.VERSION)
	duration = time.time() - start_time
	
	try:
		pgn_string_formatted = board_utils.format_pgn_comments(str(pgn_game))
		base_name = _("{w}_vs_{b}_auto_{d}").format(w=pgn_game.headers.get("White", "B"), b=pgn_game.headers.get("Black", "N"), d=datetime.datetime.now().strftime("%Y%m%d"))
		sanitized_pgn_name = config.sanitize_filename(base_name) + ".pgn"
		full_pgn_path = percorso_salvataggio(os.path.join("pgn", sanitized_pgn_name))
		with open(full_pgn_path, "w", encoding="utf-8-sig") as f:
			f.write(pgn_string_formatted)
		print(_("PGN analizzato salvato come: {path}").format(path=full_pgn_path))
		
		# Genera TXT con durata
		genera_sommario_analitico_txt(pgn_game, sanitized_pgn_name.replace('.pgn',''), analysis_results, imprecision_stats, cpl_data, last_valid_eco_entry, mosse_da_saltare, num_varianti, duration, engine_metadata)
		
	except Exception as e:
		print(_("Errore durante il salvataggio: {e}").format(e=e))

	print(_("Ritorno al menu principale."))
	Acusticator(["c5", 0.1, 0, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.4, 0, config.VOLUME], kind=1)

def EditEngineConfig(initial_path=None, initial_executable=None):
	CloseEngine() # Importante: rilascia il file exe se in uso
	print(_("\nImposta configurazione del motore scacchistico\n"))
	db = storage.LoadDB()
	engine_config = db.get("engine_config", {})
	if engine_config:
		print(_("Configurazione attuale del motore:"))
		for key, val in engine_config.items():
			print("  {key}: {val}".format(key=key, val=val))
	else:
		print(_("Nessuna configurazione trovata."))

	default_path = initial_path if initial_path else ""
	path = dgt(_("Inserisci il percorso dove e' salvato il motore UCI [{default}]: ").format(default=default_path), kind="s", smin=3, smax=256, default=default_path)
	Acusticator(["g6", 0.025, -.75, config.VOLUME,"c5", 0.025, -75, config.VOLUME],kind=3)

	default_exe = initial_executable if initial_executable else ""
	executable = dgt(_("Inserisci il nome dell'eseguibile del motore [{default}]: ").format(default=default_exe), kind="s", smin=5, smax=64, default=default_exe)
	
	full_engine_path = os.path.join(path, executable)
	
	if not os.path.isfile(full_engine_path):
		print(_("Il file specificato non esiste. Verifica il percorso e il nome dell'eseguibile."))
		return

	app_path = percorso_salvataggio('')
	app_drive = os.path.splitdrive(app_path)[0]
	engine_drive = os.path.splitdrive(full_engine_path)[0]
	
	path_to_save = ""
	is_relative = False
	
	if app_drive.lower() == engine_drive.lower() and app_drive != "":
		try:
			path_to_save = os.path.relpath(full_engine_path, app_path)
			is_relative = True
			print(_("Info: il motore si trova sullo stesso drive, verra' salvato un percorso relativo per la portabilita'."))
		except ValueError:
			path_to_save = full_engine_path
			is_relative = False
	else:
		path_to_save = full_engine_path
		is_relative = False
		print(_("Info: il motore si trova su un drive diverso, verra' salvato un percorso assoluto (configurazione non portatile)."))	
	
	hash_size = dgt(_("Inserisci la dimensione della hash table (min: 1, max: 4096 MB): "), kind="i", imin=1, imax=4096, default=128)
	Acusticator(["g6", 0.025, -.25, config.VOLUME,"c5", 0.025, -.25, config.VOLUME],kind=3)
	
	max_cores = os.cpu_count() or 1
	num_cores = dgt(_("Inserisci il numero di core da utilizzare (min: 1, max: {max_cores}): ").format(max_cores=max_cores), kind="i", imin=1, imax=max_cores, default=min(4, max_cores))
	Acusticator(["g6", 0.025, 0, config.VOLUME,"c5", 0.025, 0, config.VOLUME],kind=3)
	
	skill_level = dgt(_("Inserisci il livello di skill (min: 0, max: 20): "), kind="i", imin=0, imax=20, default=20)
	Acusticator(["g6", 0.025, .25, config.VOLUME,"c5", 0.025, .25, config.VOLUME],kind=3)
	
	move_overhead = dgt(_("Inserisci il move overhead in millisecondi (min: 0, max: 500): "), kind="i", imin=0, imax=500, default=0)
	Acusticator(["g6", 0.025, .5, config.VOLUME,"c5", 0.025, .5, config.VOLUME],kind=3)
	
	engine_config = {
		"engine_path": path_to_save,
		"engine_is_relative": is_relative,
		"hash_size": hash_size,
		"num_cores": num_cores,
		"skill_level": skill_level,
		"move_overhead": move_overhead
	}
	db["engine_config"] = engine_config
	storage.SaveDB(db)
	print(_("Configurazione del motore salvata."))
	InitEngine()
	Acusticator(["a6", 0.5, 1, config.VOLUME],kind=3, adsr=[.001,0,100,99.9])
	return
