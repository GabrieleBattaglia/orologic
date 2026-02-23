import time
import threading
import json
import os
import chess
import chess.pgn
import datetime
import copy
import pyperclip
import io
from GBUtils import dgt, Acusticator, key, polipo, menu
from . import config
from . import board_utils
from . import clock
from . import ui
from . import engine
from . import storage
from . import version

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

# Volume ora gestito via config.VOLUME

def clock_thread(game_state):
	last_time = time.time()
	triggered_alarms_white = set()
	triggered_alarms_black = set()
	while not game_state.game_over:
		current_time = time.time()
		elapsed = current_time - last_time
		last_time = current_time
		if not game_state.paused and not game_state.ignore_clock:
			if game_state.active_color == "white":
				game_state.white_remaining -= elapsed
				for alarm in game_state.clock_config.get("alarms", []):
					if alarm not in triggered_alarms_white and abs(game_state.white_remaining - alarm) < elapsed:
						print(_("\nAllarme: tempo del bianco raggiunto {time}").format(time=board_utils.seconds_to_mmss(alarm)), end="")
						Acusticator(["c4", 0.2, -0.75, config.VOLUME])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining -= elapsed
				for alarm in game_state.clock_config.get("alarms", []):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(_("\nAllarme: tempo del nero raggiunto {time}").format(time=board_utils.seconds_to_mmss(alarm)), end="")
						Acusticator(["c4", 0.2, 0.75, config.VOLUME])
						triggered_alarms_black.add(alarm)
		
		if not game_state.ignore_clock and (game_state.white_remaining <= 0 or game_state.black_remaining <= 0):
			if not game_state.flag_fallen:
				Acusticator(["e4", 0.2, -0.5, config.VOLUME, "d4", 0.2, 0, config.VOLUME, "c4", 0.2, 0.5, config.VOLUME], kind=1, adsr=[10, 0, 90, 10])
				game_state.flag_fallen = True
				game_state.paused = True
				print(_("\nBandierina caduta! Premi INVIO per gestire l'evento..."))
				if game_state.white_remaining <= 0:
					print(_("Tempo del Bianco scaduto."))
				else:
					print(_("Tempo del Nero scaduto."))
				Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
		time.sleep(0.1)

def RiprendiPartita(dati_partita):
	print(_("Ricostruzione dello stato della partita..."))
	game_state = board_utils.GameState(dati_partita["clock_config"])
	game_state.board = board_utils.CustomBoard(dati_partita["board_fen"])
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
			print(_("Attenzione: PGN non valido nel file di salvataggio. Ne creo uno nuovo."))
			game_state.pgn_game = chess.pgn.Game.from_board(game_state.board)
		else:
			game_state.pgn_node = game_state.pgn_game.end()
	except Exception as e:
		print(_("Errore nella lettura del PGN salvato: {error}. La partita riprendera' senza cronologia PGN.").format(error=e))
		game_state.pgn_game = chess.pgn.Game.from_board(game_state.board)
	game_state.paused = True
	threading.Thread(target=clock_thread, args=(game_state,), daemon=True).start()
	db = storage.LoadDB()
	autosave_is_on = db.get("autosave_enabled", False)
	eco_database = board_utils.LoadEcoDatabaseWithFEN("eco.db")
	print("\n" + "--- Riepilogo Partita ---")
	print(_("Bianco: {player} - Tempo: {time}").format(player=game_state.white_player, time=board_utils.FormatTime(game_state.white_remaining)))
	print(_("Nero: {player} - Tempo: {time}").format(player=game_state.black_player, time=board_utils.FormatTime(game_state.black_remaining)))
	if game_state.move_history:
		last_move_san = game_state.move_history[-1]
		if game_state.active_color == "black":
			move_num = (len(game_state.move_history) + 1) // 2
			last_move_str = "{num}. {san}".format(num=move_num, san=last_move_san)
		else:
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
	AUTOSAVE_FILENAME = "autosave.json"
	full_path = config.percorso_salvataggio(os.path.join("settings", AUTOSAVE_FILENAME))
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
	last_eco_msg = ""
	last_valid_eco_entry = None
	paused_time_start=None
	while not game_state.game_over:
		
		# --- GESTIONE BANDIERINA CADUTA (Thread-Safe ish) ---
		if game_state.flag_fallen and not game_state.ignore_clock:
			# Il clock_thread ha settato il flag. Ora chiediamo all'utente.
			print(_("\nTempo scaduto!"))
			print(_("Premere INVIO per continuare la partita senza orologio, oppure ESC per terminare e assegnare la vittoria."))
			# Usiamo key per un input secco
			choice = key(">>> ")
			if choice == '\x1b': # ESC
				game_state.game_over = True
				# Assegna risultato
				if game_state.white_remaining <= 0:
					game_state.pgn_game.headers["Result"] = "0-1"
					print(_("Vince il Nero per tempo."))
				else:
					game_state.pgn_game.headers["Result"] = "1-0"
					print(_("Vince il Bianco per tempo."))
				break # Esce dal loop
			else:
				# Continua
				game_state.ignore_clock = True
				game_state.paused = False # Sblocca (ma il tempo non scenderà più grazie a ignore_clock nel thread)
				print(_("Partita continuata senza limiti di tempo. Usa i comandi .1-0, .0-1, .1/2, .* per terminare."))
				game_state.flag_fallen = False # Reset flag per non rientrare qui
				continue # Riavvia il loop per stampare il prompt corretto

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
		elif game_state.ignore_clock:
			prompt="(NoClock) " + prompt.strip() + " "
			
		user_input=dgt(prompt,kind="s")
		
		# Rilevamento bandierina immediato dopo input (nel caso sia caduta mentre scrivevo)
		if game_state.flag_fallen and not game_state.ignore_clock:
			continue # Torna su a gestire il flag

		if user_input.startswith("/"):
			Acusticator(["c5", 0.07, -1, config.VOLUME,"d5", 0.07, -.75, config.VOLUME,"e5", 0.07, -.5, config.VOLUME,"f5", 0.07, -.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"a5", 0.07, .25, config.VOLUME,"b5", 0.07, .5, config.VOLUME,"c6", 0.07, .75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
			base_column = user_input[1:2].strip()
			ui.read_diagonal(game_state, base_column, True)
		elif user_input.startswith("\\"):
			Acusticator(["c5", 0.07, 1, config.VOLUME,"d5", 0.07, 0.75, config.VOLUME,"e5", 0.07, 0.5, config.VOLUME,"f5", 0.07, 0.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"a5", 0.07, -0.25, config.VOLUME,"b5", 0.07, -0.5, config.VOLUME,"c6", 0.07, -0.75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
			base_column = user_input[1:2].strip()
			ui.read_diagonal(game_state, base_column, False)
		elif user_input.startswith("-"):
			param = user_input[1:].strip()
			if len(param) == 1 and param.isalpha():
				Acusticator(["c5", 0.07, 0, config.VOLUME, "d5", 0.07, 0, config.VOLUME, "e5", 0.07, 0, config.VOLUME, "f5", 0.07, 0, config.VOLUME, "g5", 0.07, 0, config.VOLUME, "a5", 0.07, 0, config.VOLUME, "b5", 0.07, 0, config.VOLUME, "c6", 0.07, 0, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
				ui.read_file(game_state, param)
			elif len(param) == 1 and param.isdigit():
				rank_number = int(param)
				if 1 <= rank_number <= 8:
					Acusticator(["g5", 0.07, -1, config.VOLUME,"g5", 0.07, -.75, config.VOLUME,"g5", 0.07, -.5, config.VOLUME,"g5", 0.07, -.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"g5", 0.07, .25, config.VOLUME,"g5", 0.07, .5, config.VOLUME,"g5", 0.07, .75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
					ui.read_rank(game_state, rank_number)
				else:
					print(_("Traversa non valida."))
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				Acusticator(["d#4", .7, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
				ui.read_square(game_state, param)
			else:
				print(_("Comando dash non riconosciuto."))
		elif user_input.startswith(","):
			Acusticator(["a3", .06, -1, config.VOLUME, "c4", .06, -0.5, config.VOLUME, "d#4", .06, 0.5, config.VOLUME, "f4", .06, 1, config.VOLUME], kind=3, adsr=[20, 5, 70, 25])
			ui.report_piece_positions(game_state, user_input[1:2])
		elif user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			
			# Comandi inibiti se ignore_clock è True
			clock_commands = [".1", ".2", ".3", ".4", ".5", ".p", ".b+", ".b-", ".n+", ".n-"]
			if game_state.ignore_clock and any(cmd.startswith(c) for c in clock_commands):
				print(_("Comando non disponibile: orologio disabilitato."))
				continue

			if cmd==".?":
				Acusticator([440.0, 0.3, 0, config.VOLUME, 880.0, 0.3, 0, config.VOLUME], kind=1, adsr=[10, 0, 100, 20])
				menu(config.DOT_COMMANDS,show_only=True,p=_("Comandi disponibili:"), ordered=False)
			elif cmd==".1":
				Acusticator(['a6', 0.14, -1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
				ui.report_white_time(game_state)
			elif cmd==".2":
				Acusticator(['b6', 0.14, 1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
				ui.report_black_time(game_state)
			elif	cmd==".3":
				Acusticator(['e7', 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
				ui.report_white_time(game_state)
				ui.report_black_time(game_state)
			elif cmd==".4":
				Acusticator(['f7', 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
				diff=abs(game_state.white_remaining-game_state.black_remaining)
				adv=_("bianco") if game_state.white_remaining>game_state.black_remaining else _("nero")
				print(_("{player} in vantaggio di ").format(player=adv)+board_utils.FormatTime(diff))
			elif cmd==".5":
				if game_state.paused:
					Acusticator(['d4', 0.54, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
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
					Acusticator(['f4', 0.54, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
					player = game_state.white_player if game_state.active_color=="white" else game_state.black_player
					print(_("Orologio di {player} in moto").format(player=player))
			elif cmd==".m":
				Acusticator(["c4", 0.1, -1, config.VOLUME, "e4", 0.1, -0.3, config.VOLUME, "g4", 0.1, 0.3, config.VOLUME, "c5", 0.1, 1, config.VOLUME], kind=1, adsr=[2, 8, 80, 10])
				white_material,black_material=board_utils.CalculateMaterial(game_state.board)
				print(_("Materiale: {white_player} {white_mat}, {black_player} {black_mat}").format(white_player=game_state.white_player, white_mat=white_material, black_player=game_state.black_player, black_mat=black_material))
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					print(_("Orologi in pausa"))
					Acusticator(["c5", 0.1, 1, config.VOLUME, "g4", 0.1, 0.3, config.VOLUME, "e4", 0.1, -0.3, config.VOLUME, "c4", 0.1, -1, config.VOLUME], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, config.VOLUME, "e4", 0.1, -0.3, config.VOLUME, "g4", 0.1, 0.3, config.VOLUME, "c5", 0.1, 1, config.VOLUME], kind=1, adsr=[2, 8, 80, 10])
					print(_("Pausa durata ")+board_utils.FormatTime(pause_duration))
			elif cmd==".q":
				if game_state.paused and game_state.move_history:
					Acusticator(["c5", 0.1, 1, config.VOLUME, "g4", 0.1, 0.3, config.VOLUME, "e4", 0.1, -0.3, config.VOLUME, "c4", 0.1, -1, config.VOLUME], kind=1, adsr=[2, 8, 80, 10])
					undone_move_san = game_state.move_history.pop()
					game_state.board.pop()
					current_node = game_state.pgn_node
					parent = current_node.parent
					if current_node in parent.variations:
						parent.variations.remove(current_node)
					game_state.pgn_node = parent
					if not hasattr(game_state, "cancelled_san_moves"):
						game_state.cancelled_san_moves = []
					game_state.cancelled_san_moves.insert(0, undone_move_san)
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
							Acusticator(["d4", 0.15, -.5, config.VOLUME, "f4", 0.15, -.5, config.VOLUME, "a4", 0.15, -.5, config.VOLUME, "c5", 0.15, -.5, config.VOLUME], kind=1, adsr=[15, 0, 90, 5])
							game_state.white_remaining+=adjust
						elif cmd.startswith(".b-"):
							Acusticator(["c5", 0.15, -.5, config.VOLUME, "a4", 0.15, -.5, config.VOLUME, "f4", 0.15, -.5, config.VOLUME, "d4", 0.15, -.5, config.VOLUME], kind=1, adsr=[15, 0, 90, 5])
							game_state.white_remaining-=adjust
						elif cmd.startswith(".n+"):
							Acusticator(["d4", 0.15, .5, config.VOLUME, "f4", 0.15, .5, config.VOLUME, "a4", 0.15, .5, config.VOLUME, "c5", 0.15, .5, config.VOLUME], kind=1, adsr=[15, 0, 90, 5])
							game_state.black_remaining+=adjust
						elif cmd.startswith(".n-"):
							Acusticator(["c5", 0.15, .5, config.VOLUME, "a4", 0.15, .5, config.VOLUME, "f4", 0.15, .5, config.VOLUME, "d4", 0.15, .5, config.VOLUME], kind=1, adsr=[15, 0, 90, 5])
							game_state.black_remaining-=adjust
						print(_("Nuovo tempo bianco: {white_time}, nero: {black_time}").format(white_time=board_utils.FormatTime(game_state.white_remaining), black_time=board_utils.FormatTime(game_state.black_remaining)))
					except:
						print(_("Comando non valido."))
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, config.VOLUME, "g4", 0.2, -0.3, config.VOLUME, "c5", 0.2, 0.3, config.VOLUME, "e5", 0.2, 1, config.VOLUME, "g5", 0.4, 0, config.VOLUME], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				Acusticator([900.0, 0.1, 0, config.VOLUME, 440.0, 0.3, 0, config.VOLUME], kind=1, adsr=[1, 0, 80, 19])
				summary = ui.GenerateMoveSummary(game_state)
				if summary:
					print(_("\nLista mosse giocate:\n"))
					for line in summary:
						print(line)
				else:
					print(_("Nessuna mossa ancora giocata."))
			elif cmd in [".1-0",".0-1",".1/2",".*"]:
				Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
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
				if new_comment:
					if game_state.move_history:
						if game_state.pgn_node.comment:
							game_state.pgn_node.comment += "\n" + new_comment
						else:
							game_state.pgn_node.comment = new_comment
						Acusticator(["f5", 0.1, 0, config.VOLUME,"p",0.04,0,0,"c5", 0.02, 0, config.VOLUME], kind=1, adsr=[3,7,88,2])
						print(_("Commento registrato per la mossa: ") + game_state.move_history[-1])
					else:
						print(_("Nessuna mossa da commentare."))
			else:
				Acusticator(["e3", 1, 0, config.VOLUME,"a2", 1, 0, config.VOLUME], kind=3, adsr=[1,7,100,92])
				print(_("Comando non riconosciuto."))
		else:
			if game_state.paused:
				print(_("Non e' possibile inserire nuove mosse mentre il tempo e' in pausa. Riavvia il tempo con .p"))
				Acusticator(["b3",.2,0,config.VOLUME],kind=2)
				continue
			raw_input = board_utils.NormalizeMove(user_input)
			annotation_suffix = None
			move_san_only = raw_input
			match = config.ANNOTATION_SUFFIX_PATTERN.search(raw_input)
			if match:
				annotation_suffix = match.group(1)
				move_san_only = raw_input[:-len(annotation_suffix)].strip()
			try:
				move = game_state.board.parse_san(move_san_only)
				board_copy=game_state.board.copy()
				description=board_utils.DescribeMove(move, board_copy, annotation=annotation_suffix)
				game_state.descriptive_move_history.append(description)
				Acusticator([1000.0, 0.01, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0])
				if game_state.active_color=="white":
					print(game_state.white_player+": "+description)
				else:
					print(game_state.black_player+": "+description)
				san_move_base = game_state.board.san(move)
				san_move_base = san_move_base.replace("!","").replace("?","")
				game_state.board.push(move)
				game_state.move_history.append(san_move_base)
				new_node = game_state.pgn_node.add_variation(move)
				if annotation_suffix:
					if annotation_suffix == "=":
						existing_comment = new_node.comment or ""
						if existing_comment:
							new_node.comment = existing_comment + _(" {Proposta di patta}")
						else:
							new_node.comment = _("{Proposta di patta}")
					elif annotation_suffix in config.NAG_MAP:
						nag_value = config.NAG_MAP[annotation_suffix][0]
						new_node.nags.add(nag_value)
				if hasattr(game_state, "cancelled_san_moves") and game_state.cancelled_san_moves:
					undo_comment = _("Mosse annullate: ") + " ".join(game_state.cancelled_san_moves)
					existing_comment = new_node.comment or ""
					if existing_comment:
						new_node.comment = existing_comment + " " + undo_comment
					else:
						new_node.comment = undo_comment
					del game_state.cancelled_san_moves
				game_state.pgn_node = new_node
				if eco_database:
					current_board = game_state.board
					eco_entry = board_utils.DetectOpeningByFEN(current_board, eco_database)
					new_eco_msg = ""
					current_entry_this_turn = eco_entry if eco_entry else None
					if eco_entry:
						new_eco_msg = "{eco} - {opening}".format(eco=eco_entry['eco'], opening=eco_entry['opening'])
						if eco_entry['variation']:
							new_eco_msg += " ({variation})".format(variation=eco_entry['variation'])
					if new_eco_msg and new_eco_msg != last_eco_msg:
						print(_("Apertura rilevata: ") + new_eco_msg)
						Acusticator(["f7", 0.018, 0, config.VOLUME])
						last_eco_msg = new_eco_msg
						last_valid_eco_entry = current_entry_this_turn
					elif not new_eco_msg and last_eco_msg:
						last_eco_msg = ""
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "1-0" if game_state.active_color == "white" else "0-1"
					game_state.pgn_game.headers["Result"] = result
					winner = game_state.black_player if result == "0-1" else game_state.white_player
					print(_("Scacco matto! Vince {winner}.").format(winner=winner))
					Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_stalemate():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per stallo!"))
					Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_insufficient_material():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per materiale insufficiente!"))
					Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_seventyfive_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per la regola delle 75 mosse!"))
					Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_fivefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per ripetizione della posizione (5 volte)!"))
					Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_fifty_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per la regola delle 50 mosse!"))
					Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print(_("Patta per triplice ripetizione della posizione!"))
					Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
					break
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()
				if autosave_is_on:
					EseguiAutosave(game_state)
					Acusticator(["f3", 0.012, 0, config.VOLUME], sync=True)
			except Exception:
				illegal_result=ui.verbose_legal_moves_for_san(game_state.board,move_san_only)
				Acusticator([600.0, 0.6, 0, config.VOLUME], adsr=[5, 0, 35, 90])
				print(_("Mossa '{move}' non valida. Alternative:\n{alternatives}").format(move=move_san_only, alternatives=illegal_result))
	return last_valid_eco_entry

def _finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on):
	game_state.pgn_game.headers["WhiteClock"] = board_utils.FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = board_utils.FormatClock(game_state.black_remaining)
	print(_("Partita terminata."))
	if last_valid_eco_entry:
		game_state.pgn_game.headers["ECO"] = last_valid_eco_entry["eco"]
		game_state.pgn_game.headers["Opening"] = last_valid_eco_entry["opening"]
		if last_valid_eco_entry["variation"]:
			game_state.pgn_game.headers["Variation"] = last_valid_eco_entry["variation"]
	pgn_str=str(game_state.pgn_game)
	pgn_str = board_utils.format_pgn_comments(pgn_str)
	base_filename = "{white}-{black}-{result}-{timestamp}.pgn".format(white=game_state.pgn_game.headers.get("White"), black=game_state.pgn_game.headers.get("Black"), result=game_state.pgn_game.headers.get('Result', '*'), timestamp=datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
	sanitized_name = config.sanitize_filename(base_filename)
	full_path = config.percorso_salvataggio(os.path.join("pgn", sanitized_name))
	with open(full_path, "w", encoding="utf-8") as f:
		f.write(pgn_str)
	print(_("PGN salvato come ")+full_path+".")
	ui.save_text_summary(game_state, game_state.descriptive_move_history, last_valid_eco_entry)
	try:
		pyperclip.copy(pgn_str)
		print(_("PGN copiato negli appunti."))
	except Exception as e:
		print(_("Errore durante la copia del PGN negli appunti: {error}").format(error=e))
	if autosave_is_on:
		try:
			autosave_file_path = config.percorso_salvataggio(os.path.join("settings", "autosave.json"))
			if os.path.exists(autosave_file_path):
				os.remove(autosave_file_path)
				print(_("File di salvataggio automatico eliminato."))
		except Exception as e:
			print(_("\n[Attenzione: impossibile eliminare il file di autosave: {error}]").format(error=e))
	if len(game_state.move_history) >= 8:
		if ui.enter_escape(_("Vuoi analizzare la partita? (INVIO per si', ESC per no): ")):
			db = storage.LoadDB()
			engine_config = db.get("engine_config", {})
			if not engine_config or not engine_config.get("engine_path"):
				print(_("Motore non configurato. Ritorno al menu'."))
				return
			if engine.ENGINE is None and not engine.InitEngine():
				print(_("Impossibile inizializzare il motore. Analisi annullata."))
				return
			engine.cache_analysis.clear()
			if ui.enter_escape(_("Desideri l'analisi automatica? (INVIO per si', ESC per manuale): ")):
				engine.AnalisiAutomatica(copy.deepcopy(game_state.pgn_game))
			else:
				engine.AnalyzeGame(game_state.pgn_game)
		else:
			Acusticator([880.0, 0.2, 0, config.VOLUME, 440.0, 0.2, 0, config.VOLUME], kind=1, adsr=[25, 0, 50, 25])
	return

def StartGame(clock_config):
	print(_("\nAvvio partita\n"))
	game_mode_choice = ''
	while game_mode_choice not in ['s', 'f']:
		game_mode_choice = key(_("Scegli la modalita': [S]tandard o [F]ischer Random 960? (S/F) ")).lower()
	Acusticator(["c4", 0.05, 0, config.VOLUME, "e4", 0.05, 0, config.VOLUME, "g4", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	is_fischer_random = (game_mode_choice == 'f')
	starting_board = None
	starting_fen = None
	if is_fischer_random:
		starting_board, starting_fen = ui.setup_fischer_random_board()
		if starting_board is None:
			return
	db = storage.LoadDB()
	autosave_is_on = db.get("autosave_enabled", False)
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", _("Bianco"))
	black_default = default_pgn.get("Black", _("Nero"))
	white_elo_default = default_pgn.get("WhiteElo", "1399")
	black_elo_default = default_pgn.get("BlackElo", "1399")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", _("Sede sconosciuta"))
	round_default = default_pgn.get("Round", "Round 1")
	eco_database = board_utils.LoadEcoDatabaseWithFEN("eco.db")
	white_player = dgt(_("Nome del bianco [{default}]: ").format(default=white_default), kind="s", default=white_default).strip().title()
	Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	if white_player == "":
		white_player = white_default
	black_player = dgt(_("Nome del nero [{default}]: ").format(default=black_default), kind="s", default=black_default).strip().title()
	Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	if black_player == "":
		black_player = black_default
	white_elo = dgt(_("Elo del bianco [{default}]: ").format(default=white_elo_default), kind="s", default=white_elo_default)
	Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	if white_elo.strip() == "":
		white_elo = white_elo_default
	black_elo = dgt(_("Elo del nero [{default}]: ").format(default=black_elo_default), kind="s", default=black_elo_default)
	Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	if black_elo.strip() == "":
		black_elo = black_elo_default
	event = dgt(_("Evento [{default}]: ").format(default=event_default), kind="s", default=event_default)
	Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	if event.strip() == "":
		event = event_default
	site = dgt(_("Sede [{default}]: ").format(default=site_default), kind="s", default=site_default)
	Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	round_ = dgt(_("Round [{default}]: ").format(default=round_default), kind="s", default=round_default)
	Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
	db["default_pgn"] = {
		"Event": event,
		"Site": site,
		"Round": round_,
		"White": white_player,
		"Black": black_player,
		"WhiteElo": white_elo,
		"BlackElo": black_elo
	}
	storage.SaveDB(db)
	key(_("Premi un tasto qualsiasi per iniziare la partita quando sei pronto..."),attesa=7200)
	Acusticator(["c6", .07, 0, config.VOLUME, "p", .93, 0, .5, "c6", .07, 0, config.VOLUME, "p", .93, 0, .5, "c6", .07, 0, config.VOLUME, "p", .93, 0, .5, "c7", .5, 0, config.VOLUME], kind=1, sync=True)
	game_state=board_utils.GameState(clock_config)
	if is_fischer_random:
		game_state.board = starting_board
		game_state.pgn_game.headers["Variant"] = "Chess960"
		game_state.pgn_game.headers["FEN"] = starting_fen
		game_state.pgn_game.setup(game_state.board)
	game_state.white_player=white_player
	game_state.black_player=black_player
	game_state.pgn_game.headers["White"]=white_player
	game_state.pgn_game.headers["Black"]=black_player
	game_state.pgn_game.headers["WhiteElo"]=white_elo
	game_state.pgn_game.headers["BlackElo"]=black_elo
	game_state.pgn_game.headers["Event"]=event
	game_state.pgn_game.headers["Site"]=site
	game_state.pgn_game.headers["Round"]=round_
	game_state.pgn_game.headers["TimeControl"] = clock.generate_time_control_string(clock_config)
	game_state.pgn_game.headers["Date"]=datetime.datetime.now().strftime("%Y.%m.%d")
	game_state.pgn_game.headers["Annotator"]="Orologic V{version} by {programmer}".format(version=version.VERSION, programmer=version.PROGRAMMER)
	threading.Thread(target=clock_thread, args=(game_state,), daemon=True).start()
	last_valid_eco_entry = _loop_principale_partita(game_state, eco_database, autosave_is_on)
	_finalizza_partita(game_state, last_valid_eco_entry, autosave_is_on)
	return
