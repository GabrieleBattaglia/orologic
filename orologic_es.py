# Data di concepimento: 14/02/2025 by Gabriele Battaglia & AIs
# Versione Spagnola: 09/06/2025 by Gemini
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re, pyperclip, io, chess.engine
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator, key
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="3.16.13-es"
RELEASE_DATE=datetime.datetime(2025,5,18,14,51)
PROGRAMMER="Gabriele Battaglia & AIs"
DB_FILE="orologic_db.json"
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
NAG_MAP = {
	"!": (1, "jugada fuerte"),
	"?": (2, "jugada débil"),
	"!!": (3, "jugada muy fuerte"),
	"??": (4, "jugada muy débil"),
	"!?": (5, "jugada dudosa"),
	"?!": (6, "jugada dudosa"),
}
NAG_REVERSE_MAP = {v[0]: k for k, v in NAG_MAP.items()}
ANNOTATION_DESC = {
	"=": "propuesta de tablas",
	"?": "jugada débil",
	"!": "jugada fuerte",
	"??": "jugada pésima",
	"!!": "¡jugada genial!",
	"?!": "jugada dudosa",
	"!?": "jugada dudosa"
}
# Pattern Regex per estrarre il suffisso di annotazione (1 o 2 caratteri !?=) alla fine della stringa.
# Il lookbehind (?<!=.) evita di catturare l'uguale della promozione (es. non matcha '=Q').
ANNOTATION_SUFFIX_PATTERN = re.compile(r"([!?=]{1,2}$)(?<!=.)")
# Pattern Regex specifico per gestire i suffissi DOPO una promozione (es. "d8=Q!")
PROMOTION_PATTERN_WITH_SUFFIX = re.compile(r"(=[RNBQ])([!?=]{1,2})?$")
SMART_COMMANDS = {
	"s": "Ir a la jugada anterior",
	"d": "Ir a la jugada siguiente",
	"r": "Actualizar evaluación CP",
	"?": "Mostrar esta lista de comandos",
	".": "Salir del modo inteligente"
}
ANALYSIS_COMMAND = {
	"a": "Ir al inicio o nodo padre (si está en variante)",
	"s": "Retroceder 1 jugada",
	"d": "Avanzar 1 jugada y ver comentario si existe",
	"f": "Ir al final o al nodo de la siguiente rama de variante",
	"g": "Seleccionar nodo de variante anterior",
	"h": "Seleccionar nodo de variante siguiente",
	"j": "Leer las cabeceras de la partida",
	"k": "Ir a la jugada",
	"l": "Cargar PGN desde el portapapeles",
	"z": "Insertar la mejor línea como variante en el PGN",
	"x": "Insertar la mejor jugada en el PGN",
	"c": "Solicitar un comentario al usuario y añadirlo",
	"v": "Insertar la evaluación en centipeones en el PGN",
	"b": "Activar/desactivar la lectura automática de comentarios",
	"n": "Eliminar el comentario (o permite elegirlo si hay más de uno)",
	"q": "Calcular y añadir la mejor jugada al prompt",
	"w": "Calcular y mostrar la mejor línea, añadiendo también la mejor jugada al prompt",
	"e": "Mostrar las líneas de análisis y permitir su inspección inteligente",
	"r": "Calcular y añadir la evaluación al prompt",
	"t": "Mostrar los porcentajes de Victoria/Tablas/Derrota en la posición actual",
	"y": "Añadir el balance de material al prompt",
	"u": "Mostrar el tablero",
	"i": "Establecer los segundos de análisis para el motor",
	"o": "Establecer el número de líneas de análisis a mostrar",
	"?": "Mostrar esta lista de comandos",
	".": "Salir del modo de análisis y guardar el PGN si es diferente del original"
}
DOT_COMMANDS={
	".1":"Mostrar el tiempo restante de las blancas",
	".2":"Mostrar el tiempo restante de las negras",
	".3":"Mostrar ambos relojes",
	".4":"Comparar los tiempos restantes e indicar la ventaja",
	".5":"Informa qué reloj está en marcha o la duración de la pausa, si está activa",
	".l":"Mostrar la lista de jugadas realizadas",
	".m":"Mostrar el valor del material aún en juego",
	".p":"Pausar/reanudar la cuenta atrás de los relojes",
	".q":"Anular la última jugada (solo en pausa)",
	".b+":"Añadir tiempo a las blancas (en pausa)",
	".b-":"Restar tiempo a las blancas (en pausa)",
	".n+":"Añadir tiempo a las negras (en pausa)",
	".n-":"Restar tiempo a las negras (en pausa)",
	".s":"Mostrar el tablero",
	".c":"Añadir un comentario a la jugada actual",
	".1-0":"Asignar victoria a las blancas (1-0) y concluir la partida",
	".0-1":"Asignar victoria a las negras (0-1) y concluir la partida",
	".1/2":"Asignar tablas (1/2-1/2) y concluir la partida",
	".*":"Asignar resultado no definido (*) y concluir la partida",
	".?":"Mostrar la lista de comandos disponibles",
	"/[columna]":"Mostrar la diagonal superior-derecha partiendo de la base de la columna dada",
	"\\[columna]":"Mostrar la diagonal superior-izquierda partiendo de la base de la columna dada",
	"-[columna|fila|casilla]":"Mostrar las piezas en esa columna, fila o casilla",
	",[NombrePieza]":"Mostrar la(s) posición(es) de la pieza indicada"}
MENU_CHOICES={
	"analiza":"Entrar en modo de análisis de partida",
	"crea":"... un nuevo reloj para añadir a la colección",
	"elimina":"... uno de los relojes guardados",
	"gioca":"Empezar la partida",
	"manuale":"Mostrar la guía de la aplicación",
	"motore":"Configurar los ajustes para el motor de ajedrez",
	"pgn":"Establecer la información por defecto para el PGN",
	"vedi":"... los relojes guardados",
	"volume":"Permite ajustar el volumen de los efectos de sonido",
	".":"Salir de la aplicación"}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}
LETTER_FILE_MAP={chr(ord("a")+i):FILE_NAMES.get(i,chr(ord("a")+i)) for i in range(8)}
PIECE_NAMES={chess.PAWN:"peón",chess.KNIGHT:"caballo",chess.BISHOP:"alfil",chess.ROOK:"torre",chess.QUEEN:"dama",chess.KING:"rey"}
PIECE_GENDER = {
	chess.PAWN: "m",    # peón
	chess.KNIGHT: "m",  # caballo
	chess.BISHOP: "m",  # alfil
	chess.ROOK: "f",    # torre
	chess.QUEEN: "f",   # dama
	chess.KING: "m"     # rey
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
			return "Destino no reconocido."
		legal_moves=[]
		for move in board.legal_moves:
			if move.to_square==dest_square:
				if promotion is not None:
					if move.promotion==promotion:
						legal_moves.append(move)
				else:
					legal_moves.append(move)
	if not legal_moves:
		return "No se encontraron jugadas legales para el destino indicado."
	result_lines=[]
	i=1
	for move in legal_moves:
		verbose_desc=DescribeMove(move,board.copy())
		result_lines.append(f"{i}ª: {verbose_desc}")
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
	Devuelve una versión de la cadena compatible con el sistema de archivos,
	reemplazando los caracteres no válidos (para Windows y otros sistemas) con un
	guión bajo.
	"""
	# Caracteres no permitidos en Windows: \ / : * ? " < > |
	# Además, se eliminan los caracteres de control (ASCII 0-31)
	sanitized = re.sub(r'[\\/:*?"<>|]', '_', filename)
	sanitized = re.sub(r'[\0-\31]', '', sanitized)
	# Elimina espacios y puntos al principio y al final
	sanitized = sanitized.strip().strip('. ')
	if not sanitized:
		sanitized = "nombre_archivo_defecto"
	return sanitized
def SmartInspection(analysis_lines, board):
	print("Líneas disponibles:")
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
		print(f"Línea {i}: {line_summary}")
	choice = dgt(f"¿Qué línea quieres inspeccionar? (1/{len(analysis_lines)}) ", kind="i", imin=1, imax=len(analysis_lines), default=1)
	Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves:
		print("Línea vacía, fin de la inspección.")
		return
	score = chosen_info.get("score")
	if score is not None and score.relative.is_mate():
		eval_str = f"Mate en {abs(score.relative.mate())}"
	elif score is not None:
		cp = score.white().score()
		eval_str = f"{cp/100:.2f}"
	else:
		eval_str = "0.00"
	total_moves = len(pv_moves)
	current_index = 1
	print("\nUtiliza estos comandos:")
	menu(p=SMART_COMMANDS,show_only=True)
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]:
			temp_board.push(move)
		current_move = pv_moves[current_index-1]
		# Obtener la descripción detallada de la jugada actual, desde el punto de vista del tablero antes de ejecutarla
		move_verbose = DescribeMove(current_move, temp_board)
		smart_prompt=f"\nLínea {line_index+1}: ({current_index}/{total_moves}), CP: {eval_str}, {temp_board.fullmove_number}... {move_verbose}"
		cmd = key(smart_prompt).lower()
		if cmd == ".":
			break
		elif cmd == "s":
			if current_index > 1:
				current_index -= 1
			else:
				Acusticator(["c4", 0.1, -0.5, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNo hay jugadas anteriores.")
		elif cmd == "?":
			Acusticator(["d5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			temp_board = board.copy()
			try:
				for move in pv_moves[:current_index]:
					temp_board.push(move)
			except Exception as push_err:
				print(f"\nError interno durante el avance para la evaluación: {push_err}")
				eval_str = "ERR_NAV" # Actualiza la cadena del prompt para indicar el error
				continue # Vuelve al inicio del bucle while
			score_object_si = CalculateEvaluation(temp_board)
			Acusticator(["e5",.008,-1,volume]) # Sonido después del intento
			if score_object_si is not None:
				new_eval_str = "N/D" # Valor por defecto para la cadena formateada
				pov_score_si = score_object_si.pov(temp_board.turn)
				if pov_score_si.is_mate():
					mate_in_si = pov_score_si.mate()
					new_eval_str = f"M{abs(mate_in_si)}"
				else:
					cp_si = score_object_si.white().score(mate_score=30000)
					if cp_si is not None:
						new_eval_str = f"{cp_si/100:+.2f}" # Formatea CP absoluto
					else:
						new_eval_str = "ERR"
				eval_str = new_eval_str
				Acusticator(["g5", 0.1, 0.3, volume], kind=1, adsr=[5,5,90,5]) # Sonido de éxito
				print("\nEvaluación actualizada.")
			else:
				Acusticator(["a3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]) # Sonido de error
				print("\nNo se pudo actualizar la evaluación.")
				eval_str = "N/D"
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				Acusticator(["c4", 0.1, 0.5, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNo hay jugadas posteriores.")
		else:
			Acusticator(["b3", 0.12, 0, volume], kind=2, adsr=[5, 15, 20, 60])
			print("\nComando no reconocido.")
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
					move_descr = f"{move_number}º. {white_descr}"
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
					descriptive_moves.append(f"{move_number}º... {black_descr}")
					move_number += 1
			score = analysis[0].get("score")
			mate_found = False
			if score is not None and score.relative.is_mate():
				mate_moves = abs(score.relative.mate())
				mate_found = True
			if bestmove:
				if mate_found:
					Acusticator(["a6",.008,1,volume])
					return [f"Mate en {mate_moves}, {descriptive_moves[0]}"]
				else:
					Acusticator(["f6",.008,1,volume])
					return [descriptive_moves[0]]
			else:
				if mate_found:
					descriptive_moves.insert(0, f"Mate en {mate_moves}:")
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
		print("Error en CalculateBestLine:", e)
		return None
def CalculateEvaluation(board):
	global ENGINE, analysis_time, multipv, cache_analysis
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=1)
		analysis_result = cache_analysis[fen]
		if not analysis_result:
			print(f"DEBUG: El análisis para FEN {fen} devolvió un resultado vacío.") # Debug opcional
			return None
		score = analysis_result[0].get("score")
		return score
	except Exception as e:
		print(f"Error en CalculateEvaluation para FEN {fen}: {e}")
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
			wdl_info = score.wdl() # Debería ser un objeto tipo PovWdl pero desempaquetable
		if wdl_info is None:
			return None # El motor no proporcionó WDL (común en caso de mate)
		try:
			win_permille_pov, draw_permille_pov, loss_permille_pov = wdl_info
			if not all(isinstance(x, (int, float)) for x in [win_permille_pov, draw_permille_pov, loss_permille_pov]):
					print(f"Advertencia: Valores WDL después de desempaquetar no numéricos: V={win_permille_pov}, T={draw_permille_pov}, D={loss_permille_pov}")
					return None
			perspective = None
			if hasattr(wdl_info, "color"):
				perspective = wdl_info.color
			elif hasattr(wdl_info,"pov"): # Nombre alternativo común
				perspective = wdl_info.pov
			else:
				 # Si no podemos determinar la perspectiva, asumimos por seguridad
				# que ya es absoluta (BLANCAS) como estándar UCI.
				print(f"Advertencia: No se pudo determinar la perspectiva VTD desde {repr(wdl_info)}. Asumiendo BLANCAS.")
				perspective = chess.WHITE
			if perspective == chess.BLACK:
				win_permille_abs = loss_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = win_permille_pov
			else: # Perspectiva BLANCA (o desconocida/asumida)
				win_permille_abs = win_permille_pov
				draw_permille_abs = draw_permille_pov
				loss_permille_abs = loss_permille_pov
			win_pc = win_permille_abs / 10.0
			draw_pc = draw_permille_abs / 10.0
			loss_pc = loss_permille_abs / 10.0
			Acusticator(["b5",.008,1,volume])
			return (win_pc, draw_pc, loss_pc) # Devuelve tupla de porcentajes (V_blancas, Tablas, D_blancas)
		except (TypeError, ValueError) as e_unpack:
			print(f"Advertencia: Falló el desempaquetado directo del objeto VTD {repr(wdl_info)}: {e_unpack}")
			return None
	except Exception as e:
		print(f"Error general en CalculateWDL para FEN {fen}: {e}")
		return None
def SetAnalysisTime(new_time):
	"""
	Permite establecer el tiempo de análisis (en segundos) para el motor.
	"""
	global analysis_time
	try:
		new_time = float(new_time)
		if new_time <= 0:
			print("El tiempo de análisis debe ser positivo.")
		else:
			analysis_time = new_time
			print(f"Tiempo de análisis establecido en {analysis_time} segundos.")
	except Exception as e:
		print("Error en SetAnalysisTime:", e)
def SetMultipv(new_multipv):
	"""
	Permite establecer el número de líneas (multipv) a mostrar.
	"""
	global multipv
	try:
		new_multipv = int(new_multipv)
		if new_multipv < 1:
			print("El número de líneas debe ser al menos 1.")
		else:
			multipv = new_multipv
			print(f"Multipv establecido en {multipv}.")
	except Exception as e:
		print("Error en SetMultipv:", e)
def LoadPGNFromClipboard():
	"""
	Carga el PGN desde el portapapeles y lo devuelve como objeto pgn_game.
	Si el portapapeles contiene más de una partida, se presenta un menú numerado y
	se le pide al usuario que elija la partida a cargar.
	"""
	try:
		clipboard_pgn = pyperclip.paste()
		if not clipboard_pgn.strip():
			print("Portapapeles vacío.")
			return None
		pgn_io = io.StringIO(clipboard_pgn)
		games = []
		while True:
			game = chess.pgn.read_game(pgn_io)
			if game is None:
				break
			games.append(game)
		if len(games) == 0:
			print("PGN no válido en el portapapeles.")
			return None
		elif len(games) == 1:
			return games[0]
		else:
			print(f"\nSe han encontrado {len(games)} partidas en el PGN.")
			partite={}
			for i, game in enumerate(games, start=1):
				white = game.headers.get("White", "Desconocido")
				black = game.headers.get("Black", "Desconocido")
				date = game.headers.get("Date", "Fecha desconocida")
				partite[i]=f"{white} vs {black} - {date}"
			while True:
				choice = menu(d=partite,	prompt="¿Qué partida quieres cargar? ",	show=True,ntf="Número no válido. Inténtalo de nuevo.")
				try:
					index = int(choice)
					if 1 <= index <= len(games):
						return games[index - 1]
					else:
						Acusticator(["a3", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
						print("Número no válido. Inténtalo de nuevo.")
				except ValueError:
					Acusticator(["g2", .8, 0, volume],	kind=3, adsr=[.02, 0, 100, 99])
					print("Entrada no válida. Introduce un número.")
	except Exception as e:
		print("Error en LoadPGNFromClipboard:", e)
		return None
def InitEngine():
	global ENGINE
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config or not engine_config.get("engine_path"):
		Acusticator(["d4", 0.5, -1, volume],kind=4, adsr=[.001,0,100,99.9])
		print("\nMotor no configurado. Usa el comando 'motor' para configurarlo.")
		return False
	try:
		ENGINE = chess.engine.SimpleEngine.popen_uci(engine_config["engine_path"])
		ENGINE.configure({
			"Hash": engine_config.get("hash_size", 128),
			"Threads": engine_config.get("num_cores", 1),
			"Skill Level": engine_config.get("skill_level", 20),
			"Move Overhead": engine_config.get("move_overhead", 0)
		})
		print("\nMotor inicializado correctamente.")
		return True
	except Exception as e:
		print("\nError al inicializar el motor:", e)
		return False
def EditEngineConfig():
	print("\nEstablecer configuración del motor de ajedrez\n")
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if engine_config:
		print("Configuración actual del motor:")
		for key, val in engine_config.items():
			print(f"  {key}: {val}")
	else:
		print("No se ha encontrado ninguna configuración.")
	path = dgt(prompt="Introduce la ruta donde está guardado el motor UCI: ", kind="s", smin=3, smax=256)
	Acusticator(["g6", 0.025, -.75, volume,"c5", 0.025, -75, volume],kind=3)
	executable = dgt(prompt="Introduce el nombre del ejecutable del motor (ej. stockfish_15_x64_popcnt.exe): ", kind="s", smin=5, smax=64)
	Acusticator(["g6", 0.025, -.5, volume,"c5", 0.025, -.5, volume],kind=3)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print("El archivo especificado no existe. Verifica la ruta y el nombre del ejecutable.")
		return
	hash_size = dgt(prompt="Introduce el tamaño de la tabla hash (mín: 1, máx: 4096 MB): ", kind="i", imin=1, imax=4096)
	Acusticator(["g6", 0.025, -.25, volume,"c5", 0.025, -.25, volume],kind=3)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=f"Introduce el número de núcleos a utilizar (mín: 1, máx: {max_cores}): ", kind="i", imin=1, imax=max_cores, default=4)
	Acusticator(["g6", 0.025, 0, volume,"c5", 0.025, 0, volume],kind=3)
	skill_level = dgt(prompt="Introduce el nivel de habilidad (mín: 0, máx: 20): ", kind="i", imin=0, imax=20)
	Acusticator(["g6", 0.025, .25, volume,"c5", 0.025, .25, volume],kind=3)
	move_overhead = dgt(prompt="Introduce el move overhead en milisegundos (mín: 0, máx: 500): ", kind="i", imin=0, imax=500, default=0)
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
	print("Configuración del motor guardada en orologic_db.json.")
	InitEngine()
	Acusticator(["a6", 0.5, 1, volume],kind=3, adsr=[.001,0,100,99.9])
	return
def AnalyzeGame(pgn_game):
	"""
	Función de análisis de la partida (PGN).
	Lee las anotaciones NAG durante la navegación.
	"""
	if pgn_game is None:
		pgn_game = LoadPGNFromClipboard()
		if pgn_game:
			# Recursión segura porque pgn_game ahora está definido o es None
			AnalyzeGame(pgn_game)
		else:
			print("El portapapeles no contiene un PGN válido. Volviendo al menú.")
		return

	print("\nModo análisis.\nCabeceras de la partida:\n")
	for k, v in pgn_game.headers.items():
		print(f"{k}: {v}")
	move_list = list(pgn_game.mainline_moves())
	total_moves = len(move_list)
	print(f"Número total de jugadas: {(total_moves+1)//2}")

	if total_moves < 2:
		choice = key("\nJugadas insuficientes. [M] para volver al menú o [L] para cargar un nuevo PGN desde el portapapeles: ").lower()
		Acusticator(["f5", 0.03, 0, volume], kind=1, adsr=[0,0,100,0])
		if choice == "l":
			new_pgn = LoadPGNFromClipboard()
			if new_pgn:
				AnalyzeGame(new_pgn)
			else:
				print("El portapapeles no contiene un PGN válido. Volviendo al menú.")
		return
	print(f"Tiempo de análisis establecido en {analysis_time} segundos.\nLíneas reportadas por el motor establecidas en {multipv}.")
	print("\nPresiona '?' para ver la lista de comandos.\n")
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
				try: # Añadido try-except por robustez si el nodo no está en las variantes (?)
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
		extra_prompt = "" # Resetea extra prompt para el próximo ciclo

		if current_node.comment and comment_auto_read:
			print("Comentario:", current_node.comment)
		elif current_node.comment and not comment_auto_read:
			Acusticator(["c7",	0.024, 0, volume], kind=1, adsr=[0,0,100,0])

		cmd = key(prompt).lower().strip()
		# --- 3. Guardar Nodo Actual y Procesar Comando ---
		previous_node = current_node
		node_changed = False # Flag para rastrear si el nodo cambia

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
					print("\nYa estás al principio de la partida.")
			else:
				current_node = node
			node_changed = (current_node != previous_node)

		elif cmd == "s":
			if current_node.parent:
				current_node = current_node.parent
				Acusticator(["g5", .03, -.2, volume, "c5", .03, -.8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, -0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNo hay jugadas anteriores.")
			node_changed = (current_node != previous_node)

		elif cmd == "d":
			if current_node.variations:
				current_node = current_node.variations[0]
				Acusticator(["c5", .03, .2, volume,"g5", .03, .8, volume], kind=1, adsr=[2,5,90,5])
			else:
				Acusticator(["c4", 0.1, 0.7, volume], kind=2, adsr=[10, 10, 30, 50])
				print("\nNo hay jugadas posteriores.")
			node_changed = (current_node != previous_node)

		elif cmd == "f":
			start_node = current_node
			while current_node.variations:
				current_node = current_node.variations[0]
			node_changed = (current_node != start_node)
			if node_changed:
				Acusticator(["g5", 0.1, 0, volume,"p", 0.1, 0, volume,"c6", 0.05, 0, volume,"d6", 0.05, 0, volume,"g6", 0.2, 0, volume], kind=1, adsr=[5,5,90,5])
				print("Has llegado al final de la línea principal.")
			else:
				print("Ya estás al final de la línea principal.")
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
						print("No hay variantes anteriores.")
				except ValueError:
					print("Error: nodo actual no encontrado en las variantes del padre.")
			else:
				print("No hay nodos de variante disponibles (estás en la raíz).")
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
						print("No hay variantes posteriores.")
				except ValueError:
					print("Error: nodo actual no encontrado en las variantes del padre.")
			else:
				print("No hay nodos de variante disponibles (estás en la raíz).")
			node_changed = (current_node != previous_node)

		elif cmd == "k":
			Acusticator(["g3", 0.06, 0, volume,"b3", 0.06, 0, volume,"a3", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			max_moves_num = (total_moves + 1) // 2
			target_fullmove = dgt(f"\nIr a la jugada n.º (Máx {max_moves_num}): ", kind="i", imin=1, imax=max_moves_num)
			target_ply = max(0, 2 * (target_fullmove - 1)) # Índice de semijugada de las Blancas
			# target_ply = max(0, 2 * target_fullmove -1) # Índice de semijugada de las Negras
			temp_node = pgn_game # Empezamos desde el principio
			ply_count = 0
			found_node = pgn_game # Empieza con el nodo raíz

			# Navega por la línea principal
			node_iterator = pgn_game.mainline() # Iterador sobre la línea principal
			for i, node in enumerate(node_iterator):
				 if i == target_ply:
						found_node = node
						break
			else:
				if target_ply > 0 : # Si no se buscaba el inicio
					found_node = node # Va al último nodo disponible
					print("\nSe alcanzó el final de la línea antes de la jugada solicitada.")

			current_node = found_node
			Acusticator(["g6", 0.06, 0, volume,"b6", 0.06, 0, volume,"a6", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			node_changed = (current_node != previous_node)
			if node_changed and not current_node.move and target_ply > 0: # Hemos ido más allá de la última jugada
				pass # Mensaje impreso en el bucle de arriba
			elif not node_changed:
				print("\nYa estás en esta jugada/posición.")
		elif cmd == "j":
			Acusticator(["d5", 0.08, 0, volume,"p", 0.08, 0, volume,"d6", 0.06, 0, volume], kind=1, adsr=[2,5,90,5])
			print("\nCabeceras de la partida:")
			for k, v in pgn_game.headers.items():
				print(f"{k}: {v}")
		elif cmd == "l":
			try:
				# Usa la función auxiliar para cargar una o más partidas
				new_game = LoadPGNFromClipboard() # La función gestiona la salida
				if new_game:
					pgn_game = new_game
					current_node = pgn_game # Resetea al nodo inicial
					previous_node = current_node # Actualiza previous para evitar la impresión de la descripción
					node_changed = False # Nodo cambiado pero no por navegación interna
					move_list = list(pgn_game.mainline_moves())
					total_moves = len(move_list)
					Acusticator(["c6", 0.15, 0, volume], kind=1, adsr=[5, 10, 80, 5])
					print("\nNuevo PGN cargado desde el portapapeles.")
					print("\nCabeceras de la nueva partida:\n")
					for k, v in pgn_game.headers.items():
						print(f"{k}: {v}")
					print(f"Número total de jugadas: {(total_moves+1)//2}")
				# else: LoadPGNFromClipboard ya imprime los mensajes
			except Exception as e:
				print("\nError al cargar desde el portapapeles:", e)
		elif cmd == "z":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculando mejor línea...")
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
						first_new_node.comment = ((first_new_node.comment or "") + " {Mejor línea añadida}").strip()
					saved = True; print("Mejor línea añadida/actualizada como variante.")
					Acusticator(["a5", 0.12, 0.3, volume,"b5", 0.12, 0.3, volume,"c6", 0.12, 0.3, volume,"d6", 0.12, 0.3, volume,"e6", 0.12, 0.3, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(f"\nError al añadir la variante: {e}"); Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0.3, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nNo se pudo calcular la mejor línea.")
		elif cmd == "x":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculando mejor jugada...")
			bestmove_uci = CalculateBest(current_node.board(), bestmove=True, as_san=False)
			if bestmove_uci:
				try:
					san_move = current_node.board().san(bestmove_uci)
					current_node.comment = ((current_node.comment or "").strip() + f" {{MJ: {san_move}}}").strip()
					saved = True; print(f"\nMejor jugada ({san_move}) añadida al comentario.")
					Acusticator(["a5", 0.15, 0, volume,"d6", 0.15, 0, volume], kind=1, adsr=[3,7,88,2])
				except Exception as e: print(f"\nError al obtener el SAN para la mejor jugada: {e}"); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nNo se pudo calcular la mejor jugada.")
		elif cmd == "c":
			Acusticator(["d6", 0.012, 0, volume, "p", 0.15,0,0,"a6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			user_comment = dgt("\nIntroduce el comentario: ", kind="s").strip()
			if user_comment:
				if current_node.comment:
					current_node.comment += user_comment
				else:
					current_node.comment = user_comment
				saved = True; print("\nComentario añadido/actualizado.")
				Acusticator(["a6", 0.012, 0, volume, "p", 0.15,0,0,"d6",0.012,0,volume], kind=1, adsr=[0.01,0,100,0.01])
			else: print("\nNo se ha introducido ningún comentario.")
		elif cmd == "v":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculando evaluación...")
			score_object = CalculateEvaluation(current_node.board())
			if score_object is not None:
				eval_val_str = "ERR"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_val_str = f"M{abs(mate_in)}"
				else:
					# --- USA PUNTUACIÓN ABSOLUTA ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_val_str = f"{cp/100:+.2f}" # Valor absoluto para el comentario
				eval_comment = f"{{Eval: {eval_val_str}}}"
				current_node.comment = ((current_node.comment or "").strip() + f" {eval_comment}").strip()
				saved = True; print(f"\nEvaluación ({eval_val_str}) añadida al comentario.")
				Acusticator(["g5", 0.07, 0, volume,"p", 0.04, 0, volume,"b5", 0.025, 0, volume], kind=1, adsr=[3,7,88,2])
			else: Acusticator(["a#3", 0.15, 0, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nNo se pudo calcular la evaluación.")		
		elif cmd == "b":
			if comment_auto_read:
				comment_auto_read = False
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b4", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print("\nLectura automática de comentarios desactivada.")
			else:
				comment_auto_read = True
				Acusticator(["g5", 0.025, 0, volume,"p", 0.04, 0, volume,"b6", 0.035, 0, volume], kind=1, adsr=[3,7,88,2])
				print("\nLectura automática de comentarios activada.")
		elif cmd == "n":
			if current_node.comment:
				Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
				confirm = key(f"\n¿Eliminar el comentario: '{current_node.comment}'? (s/n): ").lower()
				if confirm == "s":
					current_node.comment = ""; saved = True; print("Comentario eliminado.")
					Acusticator(["e4", 0.1, -0.4, volume], kind=1, adsr=[5,10,70,15])
				else: print("Eliminación cancelada.")
			else: Acusticator(["b3", 0.12, -0.4, volume], kind=2, adsr=[5, 15, 20, 60]); print("\nNo hay comentarios que eliminar.")
		elif cmd == "q":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculando mejor jugada...")
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
								# --- USA PUNTUACIÓN ABSOLUTA ---
								cp = score_object.white().score(mate_score=30000)
								if cp is not None:
									score_info_str = f"{cp/100:+.2f}"
								else:
									score_info_str = "ERR"
				try:
					san_move = current_node.board().san(bestmove_uci)
					desc_move = DescribeMove(bestmove_uci, current_node.board(), annotation=None)
					print("\nMejor jugada: "+desc_move)
					if score_info_str:
						extra_prompt = f" MJ: {score_info_str} {san_move} "
					else:
						extra_prompt = f" MJ: {san_move} "
					Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				except Exception as e: print(f"\nError al obtener SAN/Descr para la mejor jugada: {e}"); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); extra_prompt = " MJ: Error "
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nNo se pudo calcular la mejor jugada."); extra_prompt = " MJ: N/D "
		elif cmd == "w":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculando mejor línea...")
			bestline_list_descr = CalculateBest(current_node.board(), bestmove=False, as_san=True)
			if bestline_list_descr:
				Acusticator(["f6", 0.02, 0, volume,"p", .15, 0, 0,"a6", 0.02, 0, volume,"p", .15, 0, 0,"c7", 0.02, 0, volume,"p", .15, 0, 0,"e7", 0.02, 0, volume,"p", .15, 0, 0,"g7", 0.02, 0, volume,"p", .15, 0, 0,"b7", 0.02, 0, volume], kind=1, adsr=[4,8,85,5])
				print("\nMejor línea:"); [print(line) for line in bestline_list_descr]
				score_info_str = ""
				san_move_w = "N/D"
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
								# --- USA PUNTUACIÓN ABSOLUTA ---
								cp = score_object.white().score(mate_score=30000)
								if cp is not None:
									score_info_str = f"{cp/100:+.2f}"
								else:
									score_info_str = "ERR"
						if best_move_obj:
							try: san_move_w = current_node.board().san(best_move_obj)
							except Exception: san_move_w = "Err"
						else: san_move_w = "N/D"
				if san_move_w != "N/D" and san_move_w != "Err":
					if score_info_str:
						extra_prompt = f" MJ: {score_info_str} {san_move_w} "
					else:
						extra_prompt = f" MJ: {san_move_w} "
				else:
					extra_prompt = f" MJ: {san_move_w} "
			else: Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); print("\nNo se pudo calcular la mejor línea."); extra_prompt = " MJ: N/D "
		elif cmd == "e":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["a#3", 0.15, 0.5, volume], kind=2, adsr=[5, 20, 0, 75]); continue
			print("\nCalculando líneas de análisis..."); fen = current_node.board().fen()
			cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
			analysis = cache_analysis[fen]
			if not analysis: print("No hay resultados de análisis disponibles."); continue
			main_info = analysis[0]; score = main_info.get("score"); wdl = None; wdl_str = "N/D"; score_str = "N/D"
			if score is not None:
				if hasattr(score, "wdl"): wdl_raw = score.wdl(); wdl = (wdl_raw[0]/10, wdl_raw[1]/10, wdl_raw[2]/10) if wdl_raw else None; wdl_str = f"V{wdl[0]:.1f}%/T{wdl[1]:.1f}%/D{wdl[2]:.1f}%" if wdl else "N/D"
				if score.white().is_mate(): score_str = f"M{score.white().mate()}"
				else: score_cp = score.white().score(); score_str = f"{score_cp/100:+.2f}" if score_cp is not None else "N/D"
			depth = main_info.get("depth", "N/D"); seldepth = main_info.get("seldepth", "N/D"); nps = main_info.get("nps", "N/D"); hashfull = main_info.get("hashfull", "N/D"); hashfull_perc = f"{hashfull/10:.1f}%" if isinstance(hashfull, int) else "N/D"; debug_string = main_info.get("string", "N/D"); tbhits = main_info.get("tbhits", "N/D"); time_used = main_info.get("time", "N/D"); nodes = main_info.get("nodes", "N/D")
			Acusticator(["f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume,"p", .05, 0, 0,"f6", .013, 0, volume,"p", .05, 0, 0,"a6", .013, 0, volume,"p", .05, 0, 0,"c7", .013, 0, volume,"p", .05, 0, 0,"e7", .013, 0, volume,"p", .05, 0, 0,"g7", .013, 0, volume,"p", .05, 0, 0,"b7", .013, 0, volume], kind=1, adsr=[4,8,85,5])
			print(f"\nEstadísticas: Tiempo: {time_used}s, Hash: {hashfull_perc}, TB: {tbhits}\nDepuración: {debug_string}\nProfundidad: {depth}/{seldepth}, Eval: {score_str}, VTD: {wdl_str}\nNodos: {nodes}, NPS: {nps}\n\nLíneas de análisis:")
			for i, info in enumerate(analysis, start=1):
				pv = info.get("pv", []); line_score = info.get("score"); line_score_str = "N/D"
				if line_score: line_score_str = f"M{line_score.white().mate()}" if line_score.white().is_mate() else f"{line_score.white().score()/100:+.2f}" if line_score.white().score() is not None else "N/D"
				if not pv: print(f"Línea {i} ({line_score_str}): No se encontraron jugadas."); continue
				temp_board_pv = current_node.board().copy(); moves_san = []
				try:
					for move in pv: san_move = temp_board_pv.san(move).replace("!", "").replace("?",""); moves_san.append(san_move); temp_board_pv.push(move)
					print(f"Línea {i} ({line_score_str}): {' '.join(moves_san)}")
				except Exception as e_pv: print(f"Línea {i} ({line_score_str}): Error de conversión PV - {e_pv}")
			smart = key("\n¿Quieres inspeccionar las líneas en modo inteligente? (s/n): ").lower()
			if smart == "s": Acusticator(["d5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0]); SmartInspection(analysis, current_node.board())
			else: Acusticator(["d4", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
		elif cmd == "r":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2]); extra_prompt = " CP: N/D "; continue
			print("\nCalculando evaluación...")
			score_object = CalculateEvaluation(current_node.board())
			Acusticator(["e5",.008,-1,volume])
			if score_object is not None:
				eval_str = "N/D"
				pov_score = score_object.pov(current_node.board().turn)
				if pov_score.is_mate():
					mate_in = pov_score.mate()
					eval_str = f"M{abs(mate_in)}"
				else:
					# --- USA PUNTUACIÓN ABSOLUTA ---
					cp = score_object.white().score(mate_score=30000)
					if cp is not None:
						eval_str = f"{cp/100:+.2f}"
					else:
						eval_str = "ERR"
				extra_prompt = f" CP: {eval_str} "
				Acusticator(["g3", 0.17, 0, volume,"g6",.012,0,volume], kind=1, adsr=[3,0,90,2])
			else:
				print("\nNo se pudo calcular la evaluación.")
				extra_prompt = " CP: N/D "
				Acusticator(["g5", 0.17, 0, volume,"g3",.012,0,volume], kind=1, adsr=[3,0,90,2])
		elif cmd == "t":
			if ENGINE is None: print("\nMotor no inicializado."); Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3]); extra_prompt = " VTD: N/D "; continue
			print("\nCalculando VTD..."); wdl_perc = CalculateWDL(current_node.board())
			if wdl_perc: adj_wdl=f"V{wdl_perc[0]:.1f}%/T{wdl_perc[1]:.1f}%/D{wdl_perc[2]:.1f}% "; extra_prompt=f"{adj_wdl} "; Acusticator(["g#5", 0.03, 0, volume,"c6", 0.03, 0, volume,"g#5", 0.03, 0, volume,"c6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
			else: print("\nNo se pudo calcular VTD."); extra_prompt = " VTD: N/D "; Acusticator(["g#4", 0.05, 0, volume,"c5", 0.05, 0, volume,"g#4", 0.05, 0, volume,"c5", 0.05, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "y":
			white_material, black_material = CalculateMaterial(current_node.board()); extra_prompt = f"Material: {white_material}/{black_material} "
			Acusticator(["g#5", 0.03, 0, volume,"e5", 0.03, 0, volume,"d5", 0.03, 0, volume,"g6", 0.03, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "u":
			custom_board_view = CustomBoard(current_node.board().fen())
			if len(current_node.board().move_stack) > 0: custom_board_view.move_stack = current_node.board().move_stack
			custom_board_view.turn = current_node.board().turn; custom_board_view.fullmove_number = current_node.board().fullmove_number
			print("\n" + str(custom_board_view)); Acusticator(["d6", 0.03, 0, volume,"f6", 0.03, 0, volume,"g6", 0.03, 0, volume,"d7", 0.06, 0, volume], kind=1, adsr=[.4,0,88,.3])
		elif cmd == "i":
			print(f"\nTiempo de análisis: {analysis_time}s. Caché: {len(cache_analysis)} posiciones.")
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_time_input = dgt("\nNuevo tiempo (segundos) o ENTER: ", kind="f", fmin=0.1, fmax=300, default=analysis_time)
			if new_time_input != analysis_time: SetAnalysisTime(new_time_input); print("\nTiempo de análisis actualizado."); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print("\nTiempo de análisis no modificado.")
		elif cmd == "o":
			print(f"\nLíneas de análisis: {multipv}. Caché: {len(cache_analysis)} posiciones.")
			Acusticator(["e5", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			new_lines = dgt("Nuevo número de líneas o ENTER: ", kind="i",imin=1,imax=10, default=multipv)
			if new_lines != multipv: SetMultipv(new_lines); print("\nNúmero de líneas actualizado."); Acusticator(["e7", 0.06, 0, volume], kind=1, adsr=[0,0,100,0])
			else: print("\nNúmero de líneas no modificado.")
		elif cmd == "?":
			print("\nComandos disponibles en modo de análisis:"); menu(ANALYSIS_COMMAND,show_only=True)
			Acusticator(["d5", .7, 0, volume], kind=3, adsr=[.02,0,100,99])
		else: # Comando no reconocido
			Acusticator(["d3", 1.2, 0, volume], kind=3, adsr=[.02,0,100,99])
			print("Comando no reconocido.")
			node_changed = False # Asegura que no se imprima la descripción

		# --- 4. Imprimir Descripción si el Nodo ha Cambiado ---
		if node_changed and current_node.move:
			annotation_suffix = None
			for nag_value, suffix in NAG_REVERSE_MAP.items():
				if nag_value in current_node.nags:
					annotation_suffix = suffix
					break
			# Imprime la descripción de la jugada *a la que hemos llegado*
			print("\n" + DescribeMove(current_node.move,
									  current_node.parent.board() if current_node.parent else pgn_game.board(),
									  annotation=annotation_suffix))
	print("\nFin del análisis")
	annotator_updated_flag = False
	if saved:
		new_annotator = f'Orologic V{VERSION} by {PROGRAMMER}'
		current_annotator = pgn_game.headers.get("Annotator", "")
		if current_annotator != new_annotator:
			pgn_game.headers["Annotator"] = new_annotator
			annotator_updated_flag = True
			print("\nAnotador actualizado.")
	pgn_string_raw = ""
	try:
		pgn_string_raw = str(pgn_game)
		if not pgn_string_raw:
			print("!!!!!!!! ATENCIÓN: ¡str(pgn_game) ha devuelto una cadena vacía! !!!!!!!!")
	except Exception as e_str_export:
		print(f"!!!!!!!! DEBUG: EXCEPCIÓN durante str(pgn_game): {repr(e_str_export)} !!!!!!!!")
		pgn_string_raw = ""
	pgn_string_formatted = ""
	exception_occurred_format = False
	if pgn_string_raw and isinstance(pgn_string_raw, str):
		try:
			pgn_string_formatted = format_pgn_comments(pgn_string_raw)
		except Exception as e_format:
			exception_occurred_format = True
			print(f"!!!!!!!! DEBUG: EXCEPCIÓN DURANTE format_pgn_comments: {repr(e_format)} !!!!!!!!")
			pgn_string_formatted = ""
	else:
		print("Atención: Cadena PGN sin procesar vacía o no válida, se omite el formato.")
	print(f"DEBUG: ¿Excepción durante el formato? {exception_occurred_format}")
	if saved:
		if pgn_string_formatted:
			white_h = pgn_game.headers.get("White", "Blancas").replace(" ", "_")
			black_h = pgn_game.headers.get("Black", "Negras").replace(" ", "_")
			result_h = pgn_game.headers.get("Result", "*").replace("/", "-")
			new_default_file_name=f'{white_h}_vs_{black_h}_{result_h}'
			base_name = dgt(f"\nGuardar PGN modificado.\nNombre base (ENTER para '{new_default_file_name}'): ", kind="s",default=new_default_file_name).strip()
			if not base_name: base_name = new_default_file_name
			Acusticator(["f4", 0.05, 0, volume])
			new_filename_base = f"{base_name}-analizado-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
			new_filename = sanitize_filename(new_filename_base) + ".pgn"
			try:
				with open(new_filename, "w", encoding="utf-8-sig") as f:
					f.write(pgn_string_formatted)
				print("PGN actualizado guardado como " + new_filename)
				if annotator_updated_flag: print("La cabecera del Anotador ha sido actualizada en el archivo.")
			except Exception as e_save:
				print(f"Error al guardar el PGN: {e_save}")
		else:
			print("No se puede guardar el archivo PGN debido a errores durante la generación/formato.")
	else:
		print("\nNo se realizaron cambios guardables en el PGN.")
	if pgn_string_formatted:
		try:
			pyperclip.copy(pgn_string_formatted)
			print("PGN actual (formateado) copiado en el portapapeles.")
		except Exception as e_clip:
			print(f"Error al copiar el PGN (formateado) en el portapapeles: {e_clip}")
	else:
		print("No hay PGN formateado para copiar en el portapapeles.")
	print("Saliendo del modo de análisis. Volviendo al menú principal.")

def get_color_adjective(piece_color, gender):
	if gender == "m":
		return "blanco" if piece_color == chess.WHITE else "negro"
	else:
		return "blanca" if piece_color == chess.WHITE else "negra"
def extended_piece_description(piece):
	piece_name = PIECE_NAMES.get(piece.piece_type, "pieza").capitalize()
	gender = PIECE_GENDER.get(piece.piece_type, "m")
	color_adj = get_color_adjective(piece.color, gender)
	return f"{piece_name} {color_adj}"
def read_diagonal(game_state, base_column, direction_right):
	"""
	Lee la diagonal a partir de la casilla en la fila 1 de la columna base.
	El parámetro direction_right:
		- True: dirección superior-derecha (columna +1, fila +1)
		- False: dirección superior-izquierda (columna -1, fila +1)
	"""
	base_column = base_column.lower()
	if base_column not in "abcdefgh":
		print("Columna base no válida.")
		return
	file_index = ord(base_column) - ord("a")
	rank_index = 0  # partimos de la fila 1 (índice 0)
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
	dir_str = "superior-derecha" if direction_right else "superior-izquierda"
	if report:
		print(f"Diagonal desde {base_descr} en dirección {dir_str}: " + ", ".join(report))
	else:
		print(f"La diagonal desde {base_descr} en dirección {dir_str} no contiene piezas.")
def read_rank(game_state, rank_number):
	# Obtiene el conjunto de casillas de la fila (rank_number: 1-8)
	try:
		rank_bb = getattr(chess, f"BB_RANK_{rank_number}")
	except AttributeError:
		print("Fila no válida.")
		return
	squares = chess.SquareSet(rank_bb)
	report = []
	for square in squares:
		piece = game_state.board.piece_at(square)
		if piece:
			file_index = chess.square_file(square)
			file_letter = chr(ord("a") + file_index)
			descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
			# Usa la función auxiliar para la pieza
			report.append(f"{descriptive_file} {rank_number}: {extended_piece_description(piece)}")
	if report:
		print(f"Fila {rank_number}: " + ", ".join(report))
	else:
		print(f"La fila {rank_number} está vacía.")
def read_file(game_state, file_letter):
	# file_letter debe ser una letra de 'a' a 'h'
	file_letter = file_letter.lower()
	if file_letter not in "abcdefgh":
		print("Columna no válida.")
		return
	try:
		file_bb = getattr(chess, f"BB_FILE_{file_letter.upper()}")
	except AttributeError:
		print("Columna no válida.")
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
		print(f"Columna {LETTER_FILE_MAP.get(file_letter, file_letter)}: " + ", ".join(report))
	else:
		print(f"La columna {LETTER_FILE_MAP.get(file_letter, file_letter)} está vacía.")
def read_square(game_state, square_str):
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print("Casilla no válida.")
		return
	# Calcula el color de la casilla: (columna+fila) par -> oscura, si no clara
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = "oscura"
	else:
		color_descr = "clara"
	piece = game_state.board.piece_at(square)
	if piece:
		base_msg = f"La casilla {square_str.upper()} es {color_descr} y contiene {extended_piece_description(piece)}."
		# Calcula defensores y atacantes para la casilla ocupada
		defenders = game_state.board.attackers(piece.color, square)
		attackers = game_state.board.attackers(not piece.color, square)
		info_parts = []
		if defenders:
			count = len(defenders)
			word = "pieza" if count == 1 else "piezas"
			info_parts.append(f"defendida por {count} {word} { 'blancas' if piece.color == chess.WHITE else 'negras' }")
		if attackers:
			count = len(attackers)
			word = "pieza" if count == 1 else "piezas"
			info_parts.append(f"atacada por {count} {word} { 'negras' if piece.color == chess.WHITE else 'blancas' }")
		if info_parts:
			base_msg += " y ".join(info_parts) + "."
		print(base_msg)
	else:
		base_msg = f"La casilla {square_str.upper()} es {color_descr} y está vacía."
		white_attackers = game_state.board.attackers(chess.WHITE, square)
		black_attackers = game_state.board.attackers(chess.BLACK, square)
		info_parts = []
		if white_attackers:
			count = len(white_attackers)
			word = "pieza" if count == 1 else "piezas"
			info_parts.append(f"atacada por {count} {word} blancas")
		if black_attackers:
			count = len(black_attackers)
			word = "pieza" if count == 1 else "piezas"
			info_parts.append(f"atacada por {count} {word} negras")
		if info_parts:
			base_msg += " y ".join(info_parts) + "."
		print(base_msg)
def report_piece_positions(game_state, piece_symbol):
	try:
		piece = chess.Piece.from_symbol(piece_symbol)
	except Exception as e:
		print("No reconocido: ingrese R N B Q K P, r n b q k p")
		return
	color_string = "blancas" if piece.color == chess.WHITE else "negras"
	full_name = PIECE_NAMES.get(piece.piece_type, "pieza")
	squares = game_state.board.pieces(piece.piece_type, piece.color)
	positions = []
	for square in squares:
		# Obtener columna y fila
		file_index = chess.square_file(square)
		rank = chess.square_rank(square) + 1
		file_letter = chr(ord("a") + file_index)
		descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
		positions.append(f"{descriptive_file}{rank}")
	if positions:
		print(f"{color_string.capitalize()}: {full_name} en: " + ", ".join(positions))
	else:
		print(f"No se ha encontrado ningún {full_name} {color_string}.")
def report_white_time(game_state):
	initial_white = game_state.clock_config["phases"][game_state.white_phase]["white_time"]
	elapsed_white = initial_white - game_state.white_remaining
	if elapsed_white < 0:
		elapsed_white = 0
	perc_white = (elapsed_white / initial_white * 100) if initial_white > 0 else 0
	print("Tiempo de las blancas: " + FormatTime(game_state.white_remaining) + f" ({perc_white:.0f}%)")
	return
def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	if elapsed_black < 0:
		elapsed_black = 0
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print("Tiempo de las negras: " + FormatTime(game_state.black_remaining) + f" ({perc_black:.0f}%)")
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
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		if moves == 0:
			# Sudden death: si hay incremento, lo incluimos
			if inc > 0:
				tc = f"{base_time}+{inc}"
			else:
				tc = f"{base_time}"
		else:
			# Control de tiempo por jugadas: incluimos jugadas, tiempo y, si existe, el incremento
			if inc > 0:
				tc = f"{moves}/{base_time}+{inc}"
			else:
				tc = f"{moves}/{base_time}"
		tc_list.append(tc)
	return ", ".join(tc_list)
def seconds_to_mmss(seconds):
	m = int(seconds // 60)
	s = int(seconds % 60)
	return f"{m:02d} minutos y {s:02d} segundos"
def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print("Formato de hora no válido. Se esperaba mm:ss. Error:", e)
		return 0
def DescribeMove(move, board, annotation=None): # Añadido parámetro annotation
	if board.is_castling(move):
		base_descr = "enroque corto" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "enroque largo"
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
			if piece_symbol: # Solo para piezas, no peones
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
						disambiguation = from_sq_str[0] # Usa solo la columna
					else:
						# Comprueba si la fila es suficiente
						rank_disamb_needed = False
						for sq in potential_origins:
							if sq != move.from_square and chess.square_rank(sq) == chess.square_rank(move.from_square):
								rank_disamb_needed = True
								break
						if not rank_disamb_needed:
							disambiguation = from_sq_str[1] # Usa solo la fila
						else:
							disambiguation = from_sq_str # Usa columna y fila
			promo_str = ""
			if is_promo:
				promo_piece_symbol = chess.piece_symbol(move.promotion).upper()
				promo_str = f"={promo_piece_symbol}"
			capture_char = "x" if is_capture else ""
			if piece_symbol: # Piezas
				san_base = f"{piece_symbol}{disambiguation}{capture_char}{to_sq_str}{promo_str}"
			else: # Peones (la desambiguación es implícita en la columna si captura)
				if is_capture:
					san_base = f"{from_sq_str[0]}{capture_char}{to_sq_str}{promo_str}"
				else:
					san_base = f"{to_sq_str}{promo_str}" # Solo destino y promoción
		except Exception as e:
			try:
				san_base = board.san(move)
				san_base = san_base.replace("!","").replace("?","") # Elimina solo ! y ? base
			except Exception:
				# Último recurso: descripción basada en UCI
				san_base = f"Jugada de {chess.square_name(move.from_square)} a {chess.square_name(move.to_square)}"
		pattern = re.compile(r'^([RNBQK])?([a-h1-8]{1,2})?(x)?([a-h][1-8])(=([RNBQ]))?$')
		pawn_pattern = re.compile(r'^([a-h])?(x)?([a-h][1-8])(=([RNBQ]))?$')
		m = pattern.match(san_base)
		if m and m.group(1): # Coincidencia de pieza
			piece_letter = m.group(1)
			disamb = m.group(2) or ""
			capture = m.group(3)
			dest = m.group(4)
			promo_letter = m.group(6)
			piece_type = chess.PIECE_SYMBOLS.index(piece_letter.lower())
		else:
			m = pawn_pattern.match(san_base) # Intenta coincidencia de peón
			if m:
				piece_letter = "" # Peón
				# La desambiguación para el peón es solo la columna de origen en caso de captura
				disamb = m.group(1) or ""
				capture = m.group(2)
				dest = m.group(3)
				promo_letter = m.group(5)
				piece_type = chess.PAWN
			else:
				base_descr = san_base # Usa la cadena de respaldo
				piece_type = None # Tipo desconocido
		if piece_type is not None: # Si el análisis funcionó
			piece_name = PIECE_NAMES.get(piece_type, "pieza").lower()
			descr = piece_name
			if disamb:
				if piece_type == chess.PAWN:
					descr += f" {LETTER_FILE_MAP.get(disamb, disamb)}"
				else: # Para las otras piezas
					parts = [LETTER_FILE_MAP.get(ch, ch) if ch.isalpha() else ch for ch in disamb]
					descr += " de " + "".join(parts)
			if capture:
				descr += " captura"
				captured_piece = None
				if board.is_en_passant(move):
					ep_square = move.to_square + (-8 if board.turn == chess.WHITE else 8) # Desplazamiento correcto para al paso
					captured_piece = board.piece_at(ep_square)
					descr += " al paso"
				else:
					captured_piece = board.piece_at(move.to_square)
				if captured_piece and not board.is_en_passant(move):
					descr += " " + PIECE_NAMES.get(captured_piece.piece_type, "pieza").lower()
				dest_file_info = dest[0]
				dest_rank_info = dest[1]
				dest_name_info = LETTER_FILE_MAP.get(dest_file_info, dest_file_info)
				descr += " en " + dest_name_info + "" + dest_rank_info
			else:
				dest_file = dest[0]
				dest_rank = dest[1]
				dest_name = LETTER_FILE_MAP.get(dest_file, dest_file)
				descr += " en " + dest_name + "" + dest_rank
			if promo_letter:
				promo_type = chess.PIECE_SYMBOLS.index(promo_letter.lower())
				promo_name = PIECE_NAMES.get(promo_type, "pieza").lower()
				descr += " y promociona a " + promo_name
			base_descr = descr # Guarda la descripción base
	board_after_move = board.copy()
	board_after_move.push(move)
	final_descr = base_descr
	if board_after_move.is_checkmate():
		final_descr += " ¡jaque mate!"
	elif board_after_move.is_check():
		final_descr += " jaque"
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
			white_move_desc = f"Error en la jugada de las blancas: {e}"
		if i + 1 < len(game_state.move_history):  # Si existe la jugada de las negras
			black_move_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_move_san)
				black_move_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except Exception as e:
				black_move_desc = f"Error en la jugada de las negras: {e}"
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
def LoadEcoDatabaseWithFEN(filename="eco.db"):
	"""
	Carga el archivo ECO, calcula el FEN final para cada línea
	y devuelve una lista de diccionarios que contienen:
	"eco", "opening", "variation", "moves" (lista SAN),
	"fen" (FEN de la posición final), "ply" (número de semijugadas).
	Utiliza node.board().san() para una generación de SAN más robusta.
	"""
	eco_entries = []
	if not os.path.exists(filename):
		print(f"Archivo {filename} no encontrado.")
		return eco_entries
	try:
		with open(filename, "r", encoding="utf-8") as f:
			content = f.read()
	except Exception as e:
		print(f"Error al leer {filename}: {e}")
		return eco_entries
	# Elimina cualquier bloque de comentario encerrado entre { y }
	content = re.sub(r'\{[^}]*\}', '', content, flags=re.DOTALL)
	stream = io.StringIO(content)
	game_count = 0
	skipped_count = 0
	while True:
		# Guarda la posición actual del stream para el seek
		stream_pos = stream.tell()
		try:
			headers = chess.pgn.read_headers(stream)
			if headers is None:
				break # Fin del archivo o stream

			# Reposiciónate y lee la partida completa
			stream.seek(stream_pos) # Vuelve al inicio de las cabeceras
			game = chess.pgn.read_game(stream)
			game_count += 1

			if game is None:
				# Podría ocurrir con entradas PGN malformadas después de las cabeceras
				print(f"Atención: No se puede leer la partida PGN {game_count} después de la cabecera.")
				skipped_count += 1
				# Intenta leer la siguiente entrada saltando líneas vacías
				while True:
					line = stream.readline()
					if line is None: break # EOF
					if line.strip(): # Encontrada una línea no vacía
						stream.seek(stream.tell() - len(line.encode('utf-8'))) # Retrocede para leerla como cabecera la próxima vez
						break
				continue

			eco_code = game.headers.get("ECO", "")
			opening = game.headers.get("Opening", "")
			variation = game.headers.get("Variation", "")
			moves = []
			node = game
			last_valid_node = game # Rastrea el último nodo válido para obtener el FEN final
			parse_error = False

			while node.variations:
				next_node = node.variations[0]
				move = next_node.move
				try:
					# Usa el tablero del NODO ACTUAL para generar el SAN de la PRÓXIMA jugada
					# Esto es generalmente más fiable
					san = node.board().san(move)
					moves.append(san)
				except Exception as e:
					parse_error = True
					break # Interrumpe el análisis de esta línea ECO
				node = next_node
				last_valid_node = node # Actualiza el último nodo procesado con éxito

			if not parse_error and moves: # Solo si tenemos jugadas válidas y ningún error
				# Obtén el FEN del tablero del ÚLTIMO nodo válido alcanzado
				final_fen = last_valid_node.board().board_fen()
				ply_count = len(moves) # Número de semijugadas
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

		except ValueError as ve: # Captura específicamente errores comunes de análisis de PGN
			print(f"Error de valor durante el análisis de la partida PGN {game_count}: {ve}")
			skipped_count += 1
			# Intenta recuperarse buscando la próxima entrada PGN '['
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['): # Encontrado un posible inicio de cabecera
					stream.seek(stream.tell() - len(line.encode('utf-8'))) # Retrocede
					break
		except Exception as e:
			print(f"Error genérico durante el análisis de la partida PGN {game_count}: {e}")
			skipped_count += 1
			# Intento de recuperación similar al anterior
			while True:
				line = stream.readline()
				if line is None: break # EOF
				if line.strip().startswith('['):
					stream.seek(stream.tell() - len(line.encode('utf-8')))
					break

	print(f"Cargadas {len(eco_entries)} líneas de apertura ECO.")
	if skipped_count > 0:
		print(f"Atención: se han omitido {skipped_count} líneas ECO debido a errores de análisis.")
	return eco_entries
def DetectOpeningByFEN(current_board, eco_db_with_fen):
	"""
	devuelve la entrada de la apertura correspondiente a la posición actual.
	Maneja las transposiciones comparando los FEN de las posiciones.
	Si hay múltiples coincidencias, prefiere la que tiene el mismo número de jugadas (ply),
	y entre estas, la que tiene la secuencia de jugadas más larga en la base de datos ECO.
	"""
	current_fen = current_board.board_fen()
	current_ply = current_board.ply()
	possible_matches = []
	for entry in eco_db_with_fen:
		if entry["fen"] == current_fen:
			possible_matches.append(entry)
	if not possible_matches:
		return None # No se encontró ninguna coincidencia para esta posición
	# Filtra por número de jugadas (ply) correspondiente, si es posible
	exact_ply_matches = [m for m in possible_matches if m["ply"] == current_ply]
	if exact_ply_matches:
		# Si hay coincidencias con el mismo número de jugadas, elige la más específica
		# (la definida con más jugadas en la bd ECO, aunque deberían ser iguales si ply es igual)
		return max(exact_ply_matches, key=lambda x: len(x["moves"]))
	else:
		return None # No se encontró ninguna coincidencia con el número de jugadas correcto
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
		parts.append(f"{h} {'hora' if h==1 else 'horas'}")
	if m:
		parts.append(f"{m} {'minuto' if m==1 else 'minutos'}")
	if s:
		parts.append(f"{s} {'segundo' if s==1 else 'segundos'}")
	return ", ".join(parts) if parts else "0 segundos"
def ParseTime(prompt):
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":"))
		return h*3600+m*60+s
	except Exception as e:
		print("Formato de hora no válido. Se esperaba hh:mm:ss. Error:",e)
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
	print("\nCreación de relojes\n")
	name=dgt("Nombre del reloj: ",kind="s")
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume],sync=True)
	db=LoadDB()
	if any(c["name"]==name for c in db["clocks"]):
		print("Ya existe un reloj con este nombre.")
		Acusticator(["a3",1,0,volume],kind=2,adsr=[0,0,100,100])
		return
	same=dgt("¿Las blancas y las negras empiezan con el mismo tiempo? (Enter para sí, 'n' para no): ",kind="s",smin=0,smax=1)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(f"Tiempo (hh:mm:ss) para la fase {phase_count+1}: ")
			inc=dgt(f"Incremento en segundos para la fase {phase_count+1}: ",kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(f"Tiempo para las blancas (hh:mm:ss) fase {phase_count+1}: ")
			inc_w=dgt(f"Incremento para las blancas en la fase {phase_count+1}: ",kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			total_seconds_b=ParseTime(f"Tiempo para las negras (hh:mm:ss) fase {phase_count+1}: ")
			inc_b=dgt(f"Incremento para las negras en la fase {phase_count+1}: ",kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(f"Número de jugadas por fase {phase_count+1} (0 para terminar): ",kind="i")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt("Número de alarmas a introducir (máx 5, 0 para ninguna): ",kind="i",imax=5,default=0)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	for i in range(num_alarms):
		alarm_input = dgt(f"Introduce el tiempo (mm:ss) para la alarma {i+1}: ", kind="s")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt("Introduce una nota para el reloj (opcional): ",kind="s",default="")
	Acusticator(["f7", .09, 0, volume,"d5", .07, 0, volume,"p",.1,0,0,"d5", .07, 0, volume,"f7", .09, 0, volume])
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	db["clocks"].append(new_clock.to_dict())
	SaveDB(db)
	print("\nReloj creado y guardado.")
def ViewClocks():
	print("\nVisualización de relojes\n")
	db=LoadDB()
	if not db["clocks"]:
		print("No hay relojes guardados.")
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
				fasi+=f" F{i+1}: Blancas:{time_str_w}+{phase['white_inc']}, Negras:{time_str_b}+{phase['black_inc']}"
		num_alarms = len(c.get("alarms", []))
		alarms_str = f" Alarmas ({num_alarms})"
		print(f"{idx+1}. {c['name']} - {indicatore}{fasi}{alarms_str}")
		if c.get("note",""):
			print(f"\tNota: {c['note']}")
	Acusticator(["c5", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
	attesa=key("Presiona una tecla para volver al menú principal.")
	Acusticator(["a4", 0.08, 0, volume], kind=1, adsr=[2,5,90,5])
def SelectClock(db):
	db = LoadDB()
	if not db["clocks"]:
		Acusticator(["c3", 0.72, 0, volume], kind=2, adsr=[0,0,100,100])
		print("No hay relojes guardados.")
		return
	else:
		print(f"Hay {len(db['clocks'])} relojes en la colección.")
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
				fasi += f" F{j+1}: Blancas:{time_str_w}+{phase['white_inc']}, Negras:{time_str_b}+{phase['black_inc']}"
		num_alarms = len(c.get("alarms", []))
		alarms_str = f" Alarmas ({num_alarms})"
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
		print("Ningún reloj seleccionado.")
def DeleteClock(db):
	print("\nEliminación de relojes guardados\n")
	Acusticator(["b4", .02, 0, volume,"d4",.2,0,volume])
	orologio = SelectClock(db)
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			del db["clocks"][idx]
			Acusticator(["c4", 0.025, 0, volume])
			SaveDB(db)
			print(f"\nReloj '{clock_name}' eliminado, quedan {len(db['clocks'])}.")
	return
def EditPGN():
	Acusticator(["d6", .02, 0, volume,"g4",.02,0,volume])
	print("\nEditar información por defecto para PGN\n")
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	default_event = default_pgn.get("Event", "Orologic Game")
	event = dgt(f"Evento [{default_event}]: ", kind="s", default=default_event)
	Acusticator(["d6", .02, -1, volume,"g4",.02,-1,volume])
	if event.strip() == "":
		event = default_event
	default_site = default_pgn.get("Site", "Lugar desconocido")
	site = dgt(f"Lugar [{default_site}]: ", kind="s", default=default_site)
	Acusticator(["d6", .02, -.66, volume,"g4",.02,-.66,volume])
	if site.strip() == "":
		site = default_site
	default_round = default_pgn.get("Round", "Ronda 1")
	round_ = dgt(f"Ronda [{default_round}]: ", kind="s", default=default_round)
	Acusticator(["d6", .02, -.33, volume,"g4",.02,-.33,volume])
	if round_.strip() == "":
		round_ = default_round
	default_white = default_pgn.get("White", "Blancas")
	white = dgt(f"Nombre de las Blancas [{default_white}]: ", kind="s", default=default_white).strip().title()
	Acusticator(["d6", .02, 0, volume,"g4",.02,0,volume])
	if white.strip() == "":
		white = default_white
	default_black = default_pgn.get("Black", "Negras")
	black = dgt(f"Nombre de las Negras [{default_black}]: ", kind="s", default=default_black).strip().title()
	Acusticator(["d6", .02, .33, volume,"g4",.02,.33,volume])
	if black.strip() == "":
		black = default_black
	default_white_elo = default_pgn.get("WhiteElo", "1200")
	white_elo = dgt(f"Elo de las Blancas [{default_white_elo}]: ", kind="s", default=default_white_elo)
	Acusticator(["d6", .02, .66, volume,"g4",.02,.66,volume])
	if white_elo.strip() == "":
		white_elo = default_white_elo
	default_black_elo = default_pgn.get("BlackElo", "1200")
	black_elo = dgt(f"Elo de las Negras [{default_black_elo}]: ", kind="s", default=default_black_elo)
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
	print("\nInformación por defecto para el PGN actualizada.")
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
			self.black_remaining = clock_config["phases"][0]["black_time"]  # O equivalentemente, ["white_time"]
		else:
			self.white_remaining = clock_config["phases"][0]["white_time"]
			self.black_remaining = clock_config["phases"][0]["black_time"]
		self.white_phase=0
		self.black_phase=0
		self.white_moves=0
		self.black_moves=0
		# El turno inicial sigue siendo "white" (mueven las blancas)
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
					print(self.white_player + " entra en la fase " + str(self.white_phase+1) + " tiempo de fase " + FormatTime(self.clock_config["phases"][self.white_phase]["white_time"]))
					self.white_remaining=self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves+=1
			if self.black_phase<len(self.clock_config["phases"])-1:
				if self.black_moves>=self.clock_config["phases"][self.black_phase]["moves"] and self.clock_config["phases"][self.black_phase]["moves"]!=0:
					self.black_phase+=1
					Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03,0, volume], kind=3, adsr=[20, 10, 75, 20])
					print(self.black_player + " entra en la fase " + str(self.black_phase+1) + " tiempo de fase " + FormatTime(self.clock_config["phases"][self.black_phase]["black_time"]))
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
						print(f"\nAlarma: tiempo de las blancas alcanzado {seconds_to_mmss(alarm)}",end="")
						Acusticator(["c4",0.2,-0.75,volume])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(f"\nAlarma: tiempo de las negras alcanzado {seconds_to_mmss(alarm)}",end="")
						Acusticator(["c4",0.2,0.75,volume])
						triggered_alarms_black.add(alarm)
		if game_state.white_remaining<=0 or game_state.black_remaining<=0:
			Acusticator(["e4", 0.2, -0.5, volume, "d4", 0.2, 0, volume, "c4", 0.2, 0.5, volume], kind=1, adsr=[10, 0, 90, 10])
			game_state.game_over=True
			print("¡Bandera caída!")
			if game_state.white_remaining <= 0:
				game_state.pgn_game.headers["Result"] = "0-1"  # Ganan las Negras
				print(f"Tiempo de las Blancas agotado. {game_state.black_player} gana.")
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			else:
				game_state.pgn_game.headers["Result"] = "1-0"  # Ganan las Blancas
				print(f"Tiempo de las Negras agotado. {game_state.white_player} gana.")
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
		time.sleep(0.1)
def StartGame(clock_config):
	print("\nIniciar partida\n")
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", "Blancas")
	black_default = default_pgn.get("Black", "Negras")
	white_elo_default = default_pgn.get("WhiteElo", "1500")
	black_elo_default = default_pgn.get("BlackElo", "1500")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", "Lugar desconocido")
	round_default = default_pgn.get("Round", "Ronda 1")
	eco_database = LoadEcoDatabaseWithFEN("eco.db")
	last_eco_msg = ""
	last_valid_eco_entry = None
	white_player = dgt(f"Nombre de las blancas [{white_default}]: ", kind="s", default=white_default).strip().title()
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_player == "":
		white_player = white_default
	black_player = dgt(f"Nombre de las negras [{black_default}]: ", kind="s", default=black_default).strip().title()
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_player == "":
		black_player = black_default
	white_elo = dgt(f"Elo de las blancas [{white_elo_default}]: ", kind="s", default=white_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_elo.strip() == "":
		white_elo = white_elo_default
	black_elo = dgt(f"Elo de las negras [{black_elo_default}]: ", kind="s", default=black_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_elo.strip() == "":
		black_elo = black_elo_default
	event = dgt(f"Evento [{event_default}]: ", kind="s", default=event_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if event.strip() == "":
		event = event_default
	site = dgt(f"Lugar [{site_default}]: ", kind="s", default=site_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	round_ = dgt(f"Ronda [{round_default}]: ", kind="s", default=round_default)
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
	key("Presiona cualquier tecla para empezar la partida cuando estés listo...",attesa=7200)
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
			prompt="\nInicio, jugada 0. "
		elif len(game_state.move_history)%2==1:
			full_move=(len(game_state.move_history)+1)//2
			prompt=f"{full_move}. {game_state.move_history[-1]} "
		else:
			full_move=(len(game_state.move_history))//2
			prompt=f"{full_move}... {game_state.move_history[-1]} "
		if game_state.paused:
			prompt="["+prompt.strip()+"] "
		user_input=dgt(prompt,kind="s")
		# --- Gestión de comandos especiales ---
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
					print("Fila no válida.")
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				Acusticator(["d#4", .7, 0, volume], kind=1, adsr=[0, 0, 100, 100])
				read_square(game_state, param)
			else:
				print("Comando dash no reconocido.")
		elif user_input.startswith(","):
			Acusticator(["a3", .06, -1, volume, "c4", .06, -0.5, volume, "d#4", .06, 0.5, volume, "f4", .06, 1, volume], kind=3, adsr=[20, 5, 70, 25])
			report_piece_positions(game_state, user_input[1:2])
		elif user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			if cmd==".?":
				Acusticator([440.0, 0.3, 0, 0.5, 880.0, 0.3, 0, 0.5], kind=1, adsr=[10, 0, 100, 20])
				menu(DOT_COMMANDS,show_only=True,p="Comandos disponibles:")
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
				adv="blancas" if game_state.white_remaining>game_state.black_remaining else "negras"
				print(f"Las {adv} con ventaja de "+FormatTime(diff))
			elif cmd==".5":
				if game_state.paused:
					Acusticator(['d4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					pause_duration = time.time() - paused_time_start if paused_time_start else 0
					hours = int(pause_duration // 3600)
					minutes = int((pause_duration % 3600) // 60)
					seconds = int(pause_duration % 60)
					ms = int((pause_duration - int(pause_duration)) * 1000)
					print(f"Tiempo en pausa desde: {f'{hours:2d} horas, ' if hours else ''}{f'{minutes:2d} minutos, ' if minutes or hours else ''}{f'{seconds:2d} segundos y ' if seconds or minutes or hours else ''}{f'{ms:3d} ms' if ms else ''}")
				else:
					Acusticator(['f4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					player = game_state.white_player if game_state.active_color=="white" else game_state.black_player
					print(f"Reloj de {player} en marcha")
			elif cmd==".m":
				Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
				white_material,black_material=CalculateMaterial(game_state.board)
				print(f"Material: {game_state.white_player} {white_material}, {game_state.black_player} {black_material}")
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					print("Relojes en pausa")
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
					print("Pausa de duración "+FormatTime(pause_duration))
			elif cmd==".q":
				if game_state.paused and game_state.move_history:
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
					undone_move_san = game_state.move_history.pop()
					game_state.board.pop()
					# Actualiza el PGN: devolvemos el puntero al nodo padre
					current_node = game_state.pgn_node
					parent = current_node.parent
					if current_node in parent.variations:
						parent.variations.remove(current_node)
					game_state.pgn_node = parent
					# Guarda la jugada anulada (en formato SAN) en una lista
					if not hasattr(game_state, "cancelled_san_moves"):
						game_state.cancelled_san_moves = []
					game_state.cancelled_san_moves.insert(0, undone_move_san)
					# Revierte el incremento aplicado (elimina solo el incremento)
					if game_state.active_color == "black":
						game_state.white_remaining -= game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
						game_state.active_color = "white"
					else:
						game_state.black_remaining -= game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
						game_state.active_color = "black"
					print("Última jugada anulada: " + undone_move_san)
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
						print("Nuevo tiempo de las blancas: "+FormatTime(game_state.white_remaining)+", negras: "+FormatTime(game_state.black_remaining))
					except:
						print("Comando no válido.")
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, volume, "g4", 0.2, -0.3, volume, "c5", 0.2, 0.3, volume, "e5", 0.2, 1, volume, "g5", 0.4, 0, volume], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				Acusticator([900.0, 0.1, 0, volume, 440.0, 0.3, 0, volume], kind=1, adsr=[1, 0, 80, 19])
				summary = GenerateMoveSummary(game_state)
				if summary:
					print("\nLista de jugadas realizadas:\n")
					for line in summary:
						print(line)
				else:
					print("Ninguna jugada realizada todavía.")
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
				print("Resultado asignado: "+result)
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
					print("Comentario registrado para la jugada: " + game_state.move_history[-1])
				else:
					print("No hay jugadas que comentar.")
			else:
				Acusticator(["e3", 1, 0, volume,"a2", 1, 0, volume], kind=3, adsr=[1,7,100,92])
				print("Comando no reconocido.")
		# --- Gestión de jugadas ---
		else:
			if game_state.paused:
				print("No es posible introducir nuevas jugadas mientras el tiempo está en pausa. Reanuda el tiempo con .p")
				Acusticator(["b3",.2,0,volume],kind=2)
				continue

			# --- INICIO MODIFICACIÓN ---
			raw_input = NormalizeMove(user_input) # Normaliza antes de buscar el sufijo
			annotation_suffix = None
			move_san_only = raw_input # Por defecto: la entrada es solo la jugada

			# Busca un sufijo de anotación
			match = ANNOTATION_SUFFIX_PATTERN.search(raw_input)
			if match:
				annotation_suffix = match.group(1)
				move_san_only = raw_input[:-len(annotation_suffix)].strip() # Elimina el sufijo y los espacios extra

			# Intenta analizar solo la parte de la jugada
			try:
				move = game_state.board.parse_san(move_san_only)
				# --- FIN MODIFICACIÓN ---

				board_copy=game_state.board.copy()
				# --- MODIFICACIÓN: Pasa la anotación a DescribeMove ---
				description=DescribeMove(move, board_copy, annotation=annotation_suffix)
				# --- FIN MODIFICACIÓN ---

				Acusticator([1000.0, 0.01, 0, volume], kind=1, adsr=[0, 0, 100, 0])
				if game_state.active_color=="white":
					print(game_state.white_player+": "+description)
				else:
					print(game_state.black_player+": "+description)

				# Obtiene la SAN base para el historial (sin sufijos)
				san_move_base = game_state.board.san(move)
				# Elimina cualquier !, ? generado automáticamente por board.san() si no se desea
				san_move_base = san_move_base.replace("!","").replace("?","")

				game_state.board.push(move)
				game_state.move_history.append(san_move_base) # Usa SAN base para el historial simple

				# Añade la nueva jugada como línea principal al PGN
				new_node = game_state.pgn_node.add_variation(move)

				# --- INICIO MODIFICACIÓN: Añade NAG/Comentario al PGN ---
				if annotation_suffix:
					if annotation_suffix == "=":
						# Añade un comentario estándar para la propuesta de tablas
						existing_comment = new_node.comment or ""
						if existing_comment:
							new_node.comment = existing_comment + " {Propuesta de tablas}"
						else:
							new_node.comment = "{Propuesta de tablas}"
					elif annotation_suffix in NAG_MAP:
						nag_value = NAG_MAP[annotation_suffix][0]
						new_node.nags.add(nag_value)
				# --- FIN MODIFICACIÓN ---

				# Si existen jugadas anuladas, añade un comentario al nuevo nodo
				if hasattr(game_state, "cancelled_san_moves") and game_state.cancelled_san_moves:
					undo_comment = "Jugadas anuladas: " + " ".join(game_state.cancelled_san_moves)
					existing_comment = new_node.comment or ""
					if existing_comment:
						new_node.comment = existing_comment + " " + undo_comment
					else:
						new_node.comment = undo_comment
					# Vacía la lista para las próximas operaciones
					del game_state.cancelled_san_moves

				# Actualiza el puntero PGN al nuevo nodo
				game_state.pgn_node = new_node

				# Lógica ECO (sin cambios)
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
						print("Apertura detectada: " + new_eco_msg)
						last_eco_msg = new_eco_msg
						last_valid_eco_entry = current_entry_this_turn
					elif not new_eco_msg and last_eco_msg:
						last_eco_msg = ""

				# Controles de fin de partida (sin cambios)
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "1-0" if game_state.active_color == "white" else "0-1" # Nota: el turno ya ha cambiado aquí
					game_state.pgn_game.headers["Result"] = result
					winner = game_state.black_player if result == "0-1" else game_state.white_player
					print(f"¡Jaque mate! Gana {winner}.")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_stalemate():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("¡Tablas por ahogado!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_insufficient_material():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("¡Tablas por material insuficiente!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_seventyfive_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("¡Tablas por la regla de las 75 jugadas!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_fivefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("¡Tablas por repetición de posición (5 veces)!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_fifty_moves():
					game_state.game_over = True # Consideramos la reclamación automática por simplicidad
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("¡Tablas por la regla de las 50 jugadas!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition():
					game_state.game_over = True # Consideramos la reclamación automática por simplicidad
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("¡Tablas por triple repetición de posición!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break

				# Aplica incremento y cambia de turno (sin cambios)
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()

			except Exception as e:
				illegal_result=verbose_legal_moves_for_san(game_state.board,move_san_only) # Usa move_san_only aquí
				Acusticator([600.0, 0.6, 0, volume], adsr=[5, 0, 35, 90])
				print(f"Jugada '{move_san_only}' ilegal o no reconocida ({e}). En la casilla indicada son posibles:\n{illegal_result}")

	# --- Lógica post-partida (sin cambios) ---
	game_state.pgn_game.headers["WhiteClock"] = FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = FormatClock(game_state.black_remaining)
	print("Partida terminada.")
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
	pgn_str = format_pgn_comments(pgn_str) # Formatea los comentarios para mayor legibilidad
	filename = f"{white_player}-{black_player}-{game_state.pgn_game.headers.get('Result', '*')}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
	filename=sanitize_filename(filename)
	with open(filename, "w", encoding="utf-8") as f:
		f.write(pgn_str)
	print("PGN guardado como "+filename+".")
	try:
		pyperclip.copy(pgn_str)
		print("PGN copiado en el portapapeles.")
	except Exception as e:
		print(f"Error al copiar el PGN en el portapapeles: {e}")

	analyze_choice = key("¿Quieres analizar la partida? (s/n): ").lower()
	if analyze_choice == "s":
		db = LoadDB()
		engine_config = db.get("engine_config", {})
		if not engine_config or not engine_config.get("engine_path"):
			print("Motor no configurado. Volviendo al menú.")
			return
		else:
			# Asegúrate de que el motor esté inicializado antes de analizar
			if ENGINE is None:
				if not InitEngine():
					print("No se pudo inicializar el motor. Análisis cancelado.")
					return
			# Limpia la caché si es necesario antes de iniciar un nuevo análisis
			cache_analysis.clear()
			AnalyzeGame(game_state.pgn_game)
	else:
		Acusticator([880.0, 0.2, 0, volume, 440.0, 0.2, 0, volume], kind=1, adsr=[25, 0, 50, 25])
def OpenManual():
	print("\nAbrir manual\n")
	readme="readme_es.htm"
	if os.path.exists(readme):
		webbrowser.open(readme)
	else:
		print(f"El archivo {readme} no existe.")
def SchermataIniziale():
	now = datetime.datetime.now()
	diff1 = relativedelta(now, BIRTH_DATE)
	diff2 = relativedelta(now, RELEASE_DATE)
	parts1 = []
	if diff1.years:
		parts1.append(f"{diff1.years} años")
	if diff1.months:
		parts1.append(f"{diff1.months} meses")
	if diff1.days:
		parts1.append(f"{diff1.days} días")
	if diff1.hours:
		parts1.append(f"{diff1.hours} horas")
	if diff1.minutes:
		parts1.append(f"y {diff1.minutes} minutos")
	age_string = ", ".join(parts1)
	parts2 = []
	if diff2.years:
		parts2.append(f"{diff2.years} años")
	if diff2.months:
		parts2.append(f"{diff2.months} meses")
	if diff2.days:
		parts2.append(f"{diff2.days} días")
	if diff2.hours:
		parts2.append(f"{diff2.hours} horas")
	if diff2.minutes:
		parts2.append(f"{diff2.minutes} minutos")
	release_string = ", ".join(parts2)
	print(f"\n¡Hola! Bienvenido, soy Orologic y tengo {age_string}.")
	print(f"La última versión es la {VERSION} y fue lanzada el {RELEASE_DATE.strftime('%d/%m/%Y %H:%M')}.")
	print(f"\tes decir: hace {release_string}.")
	print("\t\tAutor: "+PROGRAMMER)
	print("\t\t\tEscribe '?' para ver el menú.")
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
		scelta=menu(MENU_CHOICES, show=True, keyslist=True, full_keyslist=False)
		if scelta == "analiza":
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
			volume = dgt(f"\nVolumen actual: {int(volume*100)}, ¿nuevo? (0-100): ", kind="i", imin=0, imax=100, default=50)
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
		elif scelta=="manuale":
			OpenManual()
		elif scelta=="gioca":
			Acusticator(["c5", 0.1, 0, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0, volume, "c6", 0.3, 0, volume, "g5", 0.1, 0, volume, "e5", 0.1, 0, volume, "c5", 0.1, 0, volume], kind=1, adsr=[5, 5, 90, 10])
			print("\nIniciar partida\n")
			db=LoadDB()
			if not db["clocks"]:
				Acusticator(["c5", 0.3, 0, volume, "g4", 0.3, 0, volume], kind=1, adsr=[30, 20, 80, 20])
				print("No hay relojes disponibles. Crea uno primero.")
			else:
				clock_config=SelectClock(db)
				if clock_config is not None:
					StartGame(clock_config)
				else:
					print("Opción no válida.")
		elif scelta==".":
			Acusticator(["g4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "a4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "p", 0.15, 0, 0, "b4", 0.15, -0.5, volume, "c5", 0.3, 0.5, volume], kind=1, adsr=[5, 0, 100, 5])
			if ENGINE is not None:
				ENGINE.quit()
				print("\nConexión con el motor UCI cerrada")
			break
if __name__=="__main__":
	time_start = datetime.datetime.now()
	board=CustomBoard()
	Main()
	time_end = datetime.datetime.now()
	delta = relativedelta(time_end, time_start)
	components = []
	if delta.days:
		components.append(f"{delta.days} días")
	if delta.hours:
		components.append(f"{delta.hours} horas")
	if delta.minutes:
		components.append(f"{delta.minutes} minutos")
	if delta.seconds:
		components.append(f"{delta.seconds} segundos")
	ms = delta.microseconds // 1000
	if ms:
		components.append(f"{ms} milisegundos")
	result = ", ".join(components) if components else "0 milisegundos"
	final_db = LoadDB()
	final_launch_count = final_db.get("launch_count", "desconocido") # Lee el contador guardado
	print(f"Hasta luego de parte de Orologic {VERSION}.\nEsta ha sido nuestra {final_launch_count}ª vez y nos hemos divertido juntos durante: {result}")
	sys.exit(0)