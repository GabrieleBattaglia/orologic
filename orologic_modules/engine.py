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
	global ENGINE, ENGINE_NAME
	db = storage.LoadDB()
	cfg = db.get("engine_config", {})
	if not cfg:
		p, e, unused_v = SearchForEngine()
		if p and e:
			cfg = {"engine_path": os.path.join(p, e), "engine_is_relative": False, "hash_size": 128, "num_cores": 1, "skill_level": 20, "move_overhead": 0}
			db["engine_config"] = cfg; storage.SaveDB(db)
		else: ENGINE = None; ENGINE_NAME = "Nessuno"; return False
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
						eval_str = "M{m}".format(m=abs(score.mate())) if score.is_mate() else "{cp:+.2f}".format(cp=score.score()/100) if score.score() is not None else "N/A"
						print(_("Linea {i} ({score}):").format(i=i, score=eval_str))
						print(board_utils.format_pv_descriptively(current_node.board(), pv))
					
					if analysis[0].get("pv"):
						bm_san = current_node.board().san(analysis[0]["pv"][0])
						score = analysis[0].get("score").pov(current_node.board().turn)
						eval_str = "M{m}".format(m=abs(score.mate())) if score.is_mate() else "{cp:+.2f}".format(cp=score.score()/100) if score.score() is not None else "N/A"
						extra_prompt = " BM: {score} {san} ".format(score=eval_str, san=bm_san)
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
				current_node.comment = (current_node.comment or "").strip() + f" {{BM: {bm[0]}}}"
				saved = True; print(_("\nCommento aggiunto.")); Acusticator(["a5", 0.1, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
		elif cmd == "c": # Commento manuale
			Acusticator(["d6", 0.012, 0, config.VOLUME, "p", 0.15, 0, 0, "a6", 0.012, 0, config.VOLUME], kind=1, adsr=[0.01,0,100,0.01])
			comm = dgt(_("\nInserisci il commento: "), kind="s").strip()
			if comm: current_node.comment = (current_node.comment or "").strip() + " " + comm; saved = True; Acusticator(["a6", 0.012, 0, config.VOLUME, "p", 0.15, 0, 0, "d6", 0.012, 0, config.VOLUME], kind=1, adsr=[0.01,0,100,0.01])
		elif cmd == "v": # Commento valutazione
			score = CalculateEvaluation(current_node.board())
			if score:
				ev = score.white().score(mate_score=30000)
				current_node.comment = (current_node.comment or "").strip() + f" {{Val: {ev/100:+.2f}}}"
				saved = True; print(_("\nValutazione commentata.")); Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
		elif cmd == "r": # Valutazione prompt
			score = CalculateEvaluation(current_node.board())
			if score:
				ev = score.white().score(mate_score=30000)
				extra_prompt = f" CP: {ev/100:+.2f} "; Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1, adsr=[2,5,90,5])
		elif cmd == "t": # WDL prompt
			wdl = CalculateWDL(current_node.board())
			if wdl: extra_prompt = f" W:{wdl[0]}% D:{wdl[1]}% L:{wdl[2]}% "; Acusticator(["g#5", 0.03, 0, config.VOLUME], kind=1)
		elif cmd == "y": # Materiale prompt
			w, b = CalculateMaterial(current_node.board()); extra_prompt = f" Mtrl: {w}/{b} "; Acusticator(["g#5", 0.03, 0, config.VOLUME], kind=1)
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
		try: pyperclip.copy(str(pgn_game)); print(_("PGN aggiornato negli appunti."))
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

def AnalisiAutomatica(pgn_game):
	if ENGINE is None: print(_("Motore non pronto.")); return
	print(_("\n--- Analisi Automatica ---"))
	mode = menu({"t": _("Tempo"), "p": _("Profondita'"), "n": _("Nodi")}, show=True, keyslist=True)
	limit = None
	if mode == 't': limit = chess.engine.Limit(time=dgt(_("Secondi [1]: "), kind="f", default=1))
	elif mode == 'p': limit = chess.engine.Limit(depth=dgt(_("Profondita' [18]: "), kind="i", default=18))
	elif mode == 'n': limit = chess.engine.Limit(nodes=dgt(_("Nodi (k) [25]: "), kind="i", default=25)*1000)
	else: return
	s_ines = dgt(_("Soglia Inesattezza [50]: "), kind="i", default=50)
	s_err = dgt(_("Soglia Errore [100]: "), kind="i", default=100)
	s_blund = dgt(_("Soglia Svarione [250]: "), kind="i", default=250)
	n_var = dgt(_("Varianti [1]: "), kind="i", imin=1, imax=5, default=1)
	skip = 0
	if ui.enter_escape(_("Salta apertura? (INVIO si'): ")):
		eco = board_utils.LoadEcoDatabaseWithFEN("eco.db")
		if eco:
			temp_b = pgn_game.board().copy()
			for m in pgn_game.mainline_moves():
				temp_b.push(m)
				if board_utils.DetectOpeningByFEN(temp_b, eco): skip = temp_b.ply()
				else: break
	print(_("Analisi in corso... (ESC per interrompere)"))
	start = time.time(); oaa_analysis_cache.clear()
	mainline = list(pgn_game.mainline()); results = []
	stats = {k: {'w': 0, 'b': 0} for k in ["Svarione", "Errore", "Inesattezza", "Mossa Buona", "Mossa Geniale"]}
	cpl_d = {'w': [], 'b': []}; prev_analysis = None
	for idx, node in enumerate(mainline):
		if key(attesa=0.002) == '\x1b': break
		ply = idx + 1
		if ply <= skip: results.append({'node': node, 'classification': _("Teoria")}); continue
		pb, cb = node.parent.board(), node.board(); turn = pb.turn; ck = 'w' if turn == chess.WHITE else 'b'
		print(f"\rPLY {ply}/{len(mainline)} {pb.san(node.move):<12} | {time.time()-start:.0f}s", end="")
		before = analyze_position_deep(pb, limit, max(3, n_var)) if not prev_analysis else prev_analysis
		after = analyze_position_deep(cb, limit, 1)
		if not before or not after: continue
		prev_analysis = analyze_position_deep(cb, limit, max(3, n_var))
		s_b = before[0]['score'].pov(turn).score(mate_score=30000)
		s_a = after[0]['score'].pov(turn).score(mate_score=30000)
		cpl = max(0, s_b - s_a); cl = "Mossa Normale"
		if node.move == before[0]['move']:
			cl = "Mossa Buona"
			if len(before) > 1:
				s2 = before[1]['score'].pov(turn).score(mate_score=30000)
				if s_b - s2 >= 180: cl = "Mossa Geniale"
		else:
			if cpl >= s_blund: cl = "Svarione"
			elif cpl >= s_err: cl = "Errore"
			elif cpl >= s_ines: cl = "Inesattezza"
		if cl in stats: stats[cl][ck] += 1
		cpl_d[ck].append(min(cpl, 1000))
		node.comment = (node.comment.strip() + f" {{OAA: {cl}. Perdita: {cpl/100:+.2f}}}").strip()
		results.append({"node": node, "classification": cl})
	print(_("\nCompletato.")); pgn_game.headers["Annotator"] = f"Orologic V{version.VERSION} (Auto)"
	try: pyperclip.copy(board_utils.format_pgn_comments(str(pgn_game))); print(_("PGN copiato."))
	except: pass

def _stampa_albero_pgn(node, data_map, lines, w_name, b_name, num_var, indent_level=0):
	for i, variation in enumerate(node.variations):
		m_str = board_utils.DescribeMove(variation.move, node.board())
		res = data_map.get(variation, {})
		classif = res.get('classification', '')
		prefix = "  " * indent_level
		lines.append(f"{prefix}{m_str} [{classif}]" if classif else f"{prefix}{m_str}")
		if i == 0: _stampa_albero_pgn(variation, data_map, lines, w_name, b_name, num_var, indent_level)
		else: _stampa_albero_pgn(variation, data_map, lines, w_name, b_name, num_var, indent_level + 1)

def genera_sommario_analitico_txt(pgn_game, base_f, results, stats, cpl_d, eco, skip, n_var):
	lines = [f"Riepilogo Orologic V.{version.VERSION}", "="*40]
	for k, v in pgn_game.headers.items(): lines.append(f"{k}: {v}")
	lines.append("="*40)
	w_n = pgn_game.headers.get("White", "W"); b_n = pgn_game.headers.get("Black", "B")
	for t in ["Mossa Geniale", "Mossa Buona", "Inesattezza", "Errore", "Svarione"]:
		s = stats[t]; lines.append(f"{t}: {w_n} {s['w']}, {b_n} {s['b']}")
	lines.append("="*40); _stampa_albero_pgn(pgn_game, {r['node']: r for r in results}, lines, w_n, b_n, n_var)
	f_p = percorso_salvataggio(os.path.join("txt", config.sanitize_filename(base_f) + ".txt"))
	try:
		with open(f_p, "w", encoding="utf-8") as f: f.write("\n".join(lines))
		print(_("Riepilogo salvato: {p}").format(p=f_p))
	except: pass
