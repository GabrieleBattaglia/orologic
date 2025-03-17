# Data di concepimento: 14/02/2025 by Gabriele Battaglia e ChatGPT o3-mini-high
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re, pyperclip, io, chess.engine
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator, key
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="3.10.4"
RELEASE_DATE=datetime.datetime(2025,3,17,13,28)
PROGRAMMER="Gabriele Battaglia & ChatGPT o3-mini-high"
DB_FILE="orologic_db.json"
ENGINE = None
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
analysis_time = 3
multipv = 2
cache_analysis = {}
SMART_COMMANDS = {
	"s": "Ir para a jogada anterior",
	"d": "Ir para a próxima jogada",
	"r": "Atualizar avaliação CP",
	"?": "Visualizar esta lista de comandos",
	".": "Sair do modo smart"
}
ANALYSIS_COMMAND = {
	"a": "Ir para o início ou nó pai (se em variante)",
	"s": "Voltar 1 jogada",
	"d": "Avançar 1 jogada e visualizar eventual comentário",
	"f": "Ir para o final ou nó do próximo ramo variante",
	"g": "Selecionar nó variante anterior",
	"h": "Selecionar nó variante seguinte",
	"j": "Lê os cabeçalhos da partida",
	"k": "Ir para a jogada",
	"l": "Carregar o PGN da área de transferência",
	"z": "Inserir a melhor linha como variante no PGN",
	"x": "Inserir a melhor jogada no PGN",
	"c": "Solicita um comentário ao utilizador e adiciona-o",
	"v": "Inserir a avaliação em centipawn no PGN",
	"b": "Visualizar novamente o comentário",
	"n": "Eliminar o comentário (ou permitir escolher se houver mais de um)",
	"q": "Calcular e adicionar a melhor jogada ao prompt",
	"w": "Calcular e visualizar a melhor linha, adicionando também a melhor jogada ao prompt",
	"e": "Visualizar as linhas de análise e permitir a sua inspeção smart",
	"r": "Calcular e adicionar a avaliação ao prompt",
	"t": "Visualizar as percentagens de Vitória Empate Derrota na posição atual",
	"y": "Adicionar o balanço material ao prompt",
	"u": "Visualizar o tabuleiro",
	"i": "Definir os segundos de análise para o motor",
	"o": "Definir o número de linhas de análise a visualizar",
	"?": "Mostrar esta lista de comandos",
	".": "Sair do modo de análise e guardar o PGN se diferente do original"
}
DOT_COMMANDS={
	".1":"Mostrar o tempo restante das brancas",
	".2":"Mostrar o tempo restante das pretas",
	".3":"Mostrar ambos os relógios",
	".4":"Comparar os tempos restantes e indicar a vantagem",
	".5":"Indicar qual relógio está em movimento ou a duração da pausa, se ativa",
	".l":"Visualizar a lista de jogadas realizadas",
	".m":"Mostrar o valor do material ainda em jogo",
	".p":"Pausar/reiniciar a contagem decrescente dos relógios",
	".q":"Anular a última jogada (apenas em pausa)",
	".b+":"Adicionar tempo às brancas (em pausa)",
	".b-":"Subtrair tempo às brancas (em pausa)",
	".n+":"Adicionar tempo às pretas (em pausa)",
	".n-":"Subtrair tempo às pretas (em pausa)",
	".s":"Visualizar o tabuleiro",
	".c":"Adicionar um comentário à jogada atual",
	".1-0":"Atribuir vitória às brancas (1-0) e concluir a partida",
	".0-1":"Atribuir vitória às pretas (0-1) e concluir a partida",
	".1/2":"Atribuir empate (1/2-1/2) e concluir a partida",
	".*":"Atribuir resultado indefinido (*) e concluir a partida",
	".?":"Visualizar a lista de comandos disponíveis",
	"/[coluna]":"Mostrar a diagonal superior-direita a partir da base da coluna dada",
	"\\[coluna]":"Mostrar a diagonal superior-esquerda a partir da base da coluna dada",
	"-[coluna|linha|casa]":"Mostrar as peças naquela coluna ou linha ou casa",
	",[NomePeça]":"Mostrar a(s) posição(ões) da peça indicada"}
MENU_CHOICES={
	"analisa":"Entrar no modo de análise de partida",
	"cria":"... um novo relógio para adicionar à coleção",
	"elimina":"... um dos relógios guardados",
	"joga":"Iniciar a partida",
	"manual":"Mostrar o guia da aplicação",
	"motor":"Configurar as definições para o motor de xadrez",
	"pgn":"Definir as informações padrão para o PGN",
	"vê":"... os relógios guardados",
	"volume":"Permite o ajuste do volume dos efeitos de áudio",
	".":"Sair da aplicação"}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}
LETTER_FILE_MAP={chr(ord("a")+i):FILE_NAMES.get(i,chr(ord("a")+i)) for i in range(8)}
PIECE_NAMES={chess.PAWN:"peão",chess.KNIGHT:"cavalo",chess.BISHOP:"bispo",chess.ROOK:"torre",chess.QUEEN:"dama",chess.KING:"Rei"}
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
			return "Destino não reconhecido."
		legal_moves=[]
		for move in board.legal_moves:
			if move.to_square==dest_square:
				if promotion is not None:
					if move.promotion==promotion:
						legal_moves.append(move)
				else:
					legal_moves.append(move)
	if not legal_moves:
		return "Nenhuma jogada legal encontrada para o destino indicado."
	result_lines=[]
	i=1
	for move in legal_moves:
		verbose_desc=DescribeMove(move,board.copy())
		result_lines.append(f"{i}º: {verbose_desc}")
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
	Retorna uma versão da string compatível com o sistema de arquivos,
	substituindo os caracteres inválidos (para Windows e outros sistemas) por um
	caractere de sublinhado.
	"""
	# Caracteres não permitidos no Windows: \ / : * ? " < > |
	# Além disso, eliminam-se os caracteres de controlo (ASCII 0-31)
	sanitized = re.sub(r'[\\/:*?"<>|]', '_', filename)
	sanitized = re.sub(r'[\0-\31]', '', sanitized)
	# Remove espaços e pontos no início e no fim
	sanitized = sanitized.strip().strip('. ')
	if not sanitized:
		sanitized = "default_filename"
	return sanitized
def SmartInspection(analysis_lines, board):
	print("Linhas disponíveis:")
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
		print(f"Linha {i}: {line_summary}")
	choice = dgt(f"Qual linha quer inspecionar? (1/{len(analysis_lines)} ", kind="i", imin=1, imax=len(analysis_lines),	default=1)
	line_index = int(choice) - 1
	chosen_info = analysis_lines[line_index]
	pv_moves = chosen_info.get("pv", [])
	if not pv_moves:
		print("Linha vazia, fim da inspeção.")
		return
	score = chosen_info.get("score")
	if score is not None and score.relative.is_mate():
		eval_str = f"Mate em {abs(score.relative.mate())}"
	elif score is not None:
		cp = score.white().score()
		eval_str = f"{cp/100:.2f}"
	else:
		eval_str = "0.00"
	total_moves = len(pv_moves)
	current_index = 1
	print("\nUtilize estes comandos:")
	menu(p=SMART_COMMANDS,show_only=True)
	while True:
		temp_board = board.copy()
		for move in pv_moves[:current_index-1]:
			temp_board.push(move)
		current_move = pv_moves[current_index-1]
		# Obtém a descrição verbosa da jogada atual, do ponto de vista do tabuleiro antes de executá-la
		move_verbose = DescribeMove(current_move, temp_board)
		smart_prompt=f"\nLinha {line_index+1}: ({current_index}/{total_moves}), CP: {eval_str}, {temp_board.fullmove_number}... {move_verbose}"
		cmd = key(smart_prompt).lower()
		if cmd == ".":
			break
		elif cmd == "s":
			if current_index > 1:
				current_index -= 1
			else:
				print("\nNão há jogadas anteriores.")
		elif cmd == "?":
			menu(p=SMART_COMMANDS,show_only=True)
		elif cmd == "r":
			# Atualiza a avaliação reconstruindo o tabuleiro até à jogada atual
			temp_board = board.copy()
			for move in pv_moves[:current_index]:
				temp_board.push(move)
			new_eval = CalculateEvaluation(temp_board)
			if new_eval is not None:
				if isinstance(new_eval, int):
					eval_str = f"{new_eval/100:.2f}"
				else:
					eval_str = str(new_eval)
				print("\nAvaliação atualizada.")
			else:
				print("\nImpossível atualizar a avaliação.")
		elif cmd == "d":
			if current_index < total_moves:
				current_index += 1
			else:
				print("\nNão há jogadas seguintes.")
		else:
			print("\nComando não reconhecido.")
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
					return [f"Mate em {mate_moves}, {descriptive_moves[0]}"]
				else:
					return [descriptive_moves[0]]
			else:
				if mate_found:
					descriptive_moves.insert(0, f"Mate em {mate_moves}:")
				return descriptive_moves
		else:
			if bestmove:
				return best_line[0]
			else:
				return best_line
	except Exception as e:
		print("Erro em CalculateBestLine:", e)
		return None
def CalculateEvaluation(board):
	"""
	Calcula e retorna a avaliação em centipawn para o tabuleiro dado.
	Se a avaliação for mate, retorna um valor especial.
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
		# Se o motor detetar uma situação de mate...
		if score.is_mate():
			# Se o tabuleiro estiver em xeque-mate, podemos usar board.outcome()
			if board.is_checkmate():
				outcome = board.outcome()
				if outcome is not None:
					# outcome.winner é True para as brancas, False para as pretas
					return 10000 if outcome.winner == chess.WHITE else -10000
			# Em outros casos (ex. mate em curso de análise) usamos score.white()
			return 10000 if score.white().mate() > 0 else -10000
		else:
			return score.white().score()
	except Exception as e:
		print("Erro em CalculateEvaluation:", e)
		return None
def CalculateWDL(board):
	"""
	Calcula e retorna as percentagens WDL (win/draw/loss) fornecidas pelo motor.
	Retorna uma tupla (win, draw, loss) em percentagens.
	"""
	global ENGINE, analysis_time, multipv
	try:
		fen = board.fen()
		if fen not in cache_analysis:
			cache_analysis[fen] = ENGINE.analyse(board, chess.engine.Limit(time=analysis_time), multipv=multipv)
			print(f"\nAnálise guardada em cache para a posição {len(cache_analysis)}.")
		analysis = cache_analysis[fen]
		# Se o motor suportar UCI_ShowWDL, o dicionário score terá uma chave "wdl"
		score = analysis[0].get("score")
		if score is None or not hasattr(score, "wdl"):
			return None
		wdl = score.wdl()
		# wdl é uma tupla com valores em décimos, converte-os em percentagens
		total = sum(wdl)
		if total == 0:
			return (0, 0, 0)
		return (wdl[0] * 10, wdl[1] * 10, wdl[2] * 10)
	except Exception as e:
		print("Erro em CalculateWDL:", e)
		return None
def SetAnalysisTime(new_time):
	"""
	Permite definir o tempo de análise (em segundos) para o motor.
	"""
	global analysis_time
	try:
		new_time = float(new_time)
		if new_time <= 0:
			print("O tempo de análise deve ser positivo.")
		else:
			analysis_time = new_time
			print(f"Tempo de análise definido para {analysis_time} segundos.")
	except Exception as e:
		print("Erro em SetAnalysisTime:", e)
def SetMultipv(new_multipv):
	"""
	Permite definir o número de linhas (multipv) a visualizar.
	"""
	global multipv
	try:
		new_multipv = int(new_multipv)
		if new_multipv < 1:
			print("O número de linhas deve ser pelo menos 1.")
		else:
			multipv = new_multipv
			print(f"Multipv definido para {multipv}.")
	except Exception as e:
		print("Erro em SetMultipv:", e)
def LoadPGNFromClipboard():
	"""
	Carrega o PGN da área de transferência e retorna-o como objeto pgn_game.
	Se a área de transferência contiver mais de uma partida, é apresentado um menu numerado e
	é pedido ao utilizador para escolher a partida a carregar.
	"""
	try:
		clipboard_pgn = pyperclip.paste()
		if not clipboard_pgn.strip():
			print("Área de transferência vazia.")
			return None
		pgn_io = io.StringIO(clipboard_pgn)
		games = []
		while True:
			game = chess.pgn.read_game(pgn_io)
			if game is None:
				break
			games.append(game)
		if len(games) == 0:
			print("PGN inválido na área de transferência.")
			return None
		elif len(games) == 1:
			return games[0]
		else:
			print(f"\nForam encontradas {len(games)} partidas nos PGNs.")
			partite={}
			for i, game in enumerate(games, start=1):
				white = game.headers.get("White", "Desconhecido")
				black = game.headers.get("Black", "Desconhecido")
				date = game.headers.get("Date", "Data desconhecida")
				partite[i]=f"{white} vs {black} - {date}"
			while True:
				choice = menu(d=partite,	prompt="Qual partida quer carregar? ",	show=True,ntf="Número inválido. Tente novamente.")
				try:
					index = int(choice)
					if 1 <= index <= len(games):
						return games[index - 1]
					else:
						print("Número inválido. Tente novamente.")
				except ValueError:
					print("Entrada inválida. Insira um número.")
	except Exception as e:
		print("Erro em LoadPGNFromClipboard:", e)
		return None
def InitEngine():
	global ENGINE
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if not engine_config or not engine_config.get("engine_path"):
		print("\nMotor não configurado. Use o comando 'motor' para configurá-lo.")
		return False
	try:
		ENGINE = chess.engine.SimpleEngine.popen_uci(engine_config["engine_path"])
		ENGINE.configure({
			"Hash": engine_config.get("hash_size", 128),
			"Threads": engine_config.get("num_cores", 1),
			"Skill Level": engine_config.get("skill_level", 20),
			"Move Overhead": engine_config.get("move_overhead", 0)
		})
		print("\nMotor inicializado corretamente.")
		return True
	except Exception as e:
		print("\nErro na inicialização do motor:", e)
		return False
def EditEngineConfig():
	print("\nDefinir configuração do motor de xadrez\n")
	db = LoadDB()
	engine_config = db.get("engine_config", {})
	if engine_config:
		print("Configuração atual do motor:")
		for key, val in engine_config.items():
			print(f"  {key}: {val}")
	else:
		print("Nenhuma configuração encontrada.")
	path = dgt(prompt="Insira o caminho onde o motor UCI está guardado: ", kind="s", smin=3, smax=256)
	executable = dgt(prompt="Insira o nome do executável do motor (ex. stockfish_15_x64_popcnt.exe): ", kind="s", smin=5, smax=64)
	full_engine_path = os.path.join(path, executable)
	if not os.path.isfile(full_engine_path):
		print("O arquivo especificado não existe. Verifique o caminho e o nome do executável.")
		return
	hash_size = dgt(prompt="Insira o tamanho da tabela hash (min: 1, max: 4096 MB): ", kind="i", imin=1, imax=4096)
	max_cores = os.cpu_count()
	num_cores = dgt(prompt=f"Insira o número de núcleos a utilizar (min: 1, max: {max_cores}): ", kind="i", imin=1, imax=max_cores, default=4)
	skill_level = dgt(prompt="Insira o nível de habilidade (min: 0, max: 20): ", kind="i", imin=0, imax=20)
	move_overhead = dgt(prompt="Insira o overhead de movimento em milissegundos (min: 0, max: 500): ", kind="i", imin=0, imax=500, default=0)
	wdl_switch = True  # Pode eventualmente torná-lo configurável
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
	print("Configuração do motor guardada em orologic_db.json.")
	InitEngine()
	return
def AnalyzeGame(pgn_game):
	"""
	Função de análise da partida (PGN).
	Na entrada, é mostrado o cabeçalho e o número total de jogadas.
	Se as jogadas forem inferiores a 2, o utilizador é convidado a voltar ao menu
	ou a carregar um novo PGN da área de transferência.
	"""
	if pgn_game	is None:
		pgn_game	= LoadPGNFromClipboard()
		if pgn_game:
			AnalyzeGame(pgn_game)
		else:
			print("A área de transferência não contém um PGN válido. Retornando ao menu.")
		return
	print("\nModo de análise.\nCabeçalhos da partida:\n")
	for k, v in pgn_game.headers.items():
		print(f"{k}: {v}")
	move_list = list(pgn_game.mainline_moves())
	total_moves = len(move_list)
	print(f"Número total de jogadas: {(total_moves+1)//2}")
	if total_moves < 2:
		choice = key("\nJogadas insuficientes. [M] para voltar ao menu ou [L] para carregar um novo PGN da área de transferência: ").lower()
		if choice == "l":
			new_pgn = LoadPGNFromClipboard()
			if new_pgn:
				AnalyzeGame(new_pgn)
			else:
				print("A área de transferência não contém um PGN válido. Retornando ao menu.")
		return
	print(f"Tempo de análise definido para {analysis_time} segundos.\nLinhas reportadas pelo motor definidas para {multipv}.")
	print("\nPressione '?' para a lista de comandos.\n")
	saved = False
	current_filename = pgn_game.headers.get("Filename", None)
	current_node = pgn_game
	extra_prompt=""
	while True:
		# Construção do prompt
		if current_node.move:
			move_san = current_node.san()
			fullmove = current_node.parent.board().fullmove_number if current_node.parent else 1
			# Se o nó atual tiver um pai com mais de uma variação, mostramos símbolos que indicam a presença de ramos
			if current_node.parent and len(current_node.parent.variations) > 1:
				siblings = current_node.parent.variations
				idx = siblings.index(current_node)
				# Se for o primeiro ramo (sou o primeiro filho), mostro apenas o prefixo "<"
				if idx == 0:
					prompt = f"\n{extra_prompt} <{fullmove}. {move_san}"
				# Se for o último ramo, mostro apenas o sufixo ">"
				elif idx == len(siblings) - 1:
					prompt = f"\n{extra_prompt} {fullmove}. {move_san}>"
				# Se for intermédio, mostro tanto o prefixo como o sufixo
				else:
					prompt = f"\n{extra_prompt} <{fullmove}. {move_san}>"
			else:
				# Se não houver variações, usa a notação padrão
				if current_node.board().turn == chess.WHITE:
					prompt = f"\n{extra_prompt} {fullmove}... {move_san}"
				else:
					prompt = f"\n{extra_prompt} {fullmove}. {move_san}"
		else:
			prompt = f"\n{extra_prompt} Início: "
		cmd = key(prompt)
		if cmd == ".":
			break
		elif cmd == "a":
			node = current_node
			# Sobe até que o nó seja o primeiro do seu ramo
			while node.parent is not None and node == node.parent.variations[0]:
				node = node.parent
			if node.parent is None:
				# Estamos na linha principal: define a primeira jogada da partida
				if node.variations and current_node != node.variations[0]:
					current_node = node.variations[0]
					extra_prompt = ""
				else:
					print("\nJá no início da partida.")
			else:
				# Estamos numa variante: volta ao primeiro nó do ramo atual
				current_node = node
				extra_prompt = ""
		elif cmd == "s":
			if current_node.parent:
				current_node = current_node.parent
				extra_prompt = ""
				if current_node.move:
					print("\n" + DescribeMove(current_node.move, current_node.parent.board() if current_node.parent else pgn_game.board()))
			else:
				print("\nNenhuma jogada anterior.")
		elif cmd == "d":
			if current_node.variations:
				extra_prompt = ""
				current_node = current_node.variations[0]
				if current_node.move:
					print("\n" + DescribeMove(current_node.move, current_node.parent.board() if current_node.parent else pgn_game.board()))
				if current_node.comment:
					print("Comentário:", current_node.comment)
			else:
				print("\nNão há jogadas seguintes.")
		elif cmd == "f":
			while current_node.variations:
				extra_prompt = ""
				current_node = current_node.variations[0]
			print("Você chegou ao fim da partida.")
		elif cmd == "g":
			if current_node.parent:
				vars = current_node.parent.variations
				index = vars.index(current_node)
				if index > 0:
					extra_prompt	= ""
					current_node = vars[index - 1]
				else:
					print("Não há variantes anteriores.")
			else:
				print("Nenhum nó variante disponível.")
		elif cmd == "h":
			if current_node.parent:
				vars = current_node.parent.variations
				index = vars.index(current_node)
				if index < len(vars) - 1:
					extra_prompt	= ""
					current_node = vars[index + 1]
				else:
					print("Não há variantes seguintes.")
			else:
				print("Nenhum nó variante disponível.")
		elif cmd == "j":
			print("\nCabeçalho da partida:")
			for k, v in pgn_game.headers.items():
				print(f"{k}: {v}")
		elif cmd == "k":
			move_target = dgt(f"\nIr para a jogada n.º: Max({int(total_moves/2)}) ", kind="i", imin=1, imax=int(total_moves/2))*2-1
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
					print("\nPGN carregado da área de transferência.")
				else:
					print("\nA área de transferência não contém um PGN válido.")
			except Exception as e:
				print("\nErro ao carregar da área de transferência:", e)
		elif cmd == "z":
			bestline = CalculateBest(current_node.board())
			if bestline:
				current_node.add_variation(bestline)
				saved = True
				print("\nMelhor linha adicionada como variante.")
			else:
				print("\nImpossível calcular a melhor linha.")
		elif cmd == "x":
			bestmove = CalculateBest(current_node.board())
			if bestmove:
				san_move = current_node.board().san(bestmove)
				current_node.comment = (current_node.comment or "") + " Melhor jogada: " + san_move
				saved = True
				print("\nMelhor jogada adicionada ao comentário.")
			else:
				print("\nImpossível calcular a melhor jogada.")
		elif cmd == "c":
			user_comment = dgt("\nInsira o comentário: ", kind="s")
			if user_comment:
				current_node.comment = (current_node.comment or "") + " " + user_comment
				saved = True
				print("\nComentário adicionado.")
		elif cmd == "v":
			eval_cp = CalculateEvaluation(current_node.board())
			if eval_cp is not None:
				current_node.comment = (current_node.comment or "") + f" Avaliação CP: {eval_cp/100:.2f}"
				saved = True
				print("\nAvaliação adicionada ao comentário.")
			else:
				print("\nImpossível calcular a avaliação.")
		elif cmd == "b":
			print("\nComentário atual:", current_node.comment)
		elif cmd == "n":
			if current_node.comment:
				confirm = key(f"\nEliminar: {current_node.comment}? (s/n): ").lower()
				if confirm == "s":
					current_node.comment = ""
					saved = True
					print("Comentário eliminado.")
			else:
				print("\nNenhum comentário para eliminar.")
		elif cmd == "q":
			bestmove = CalculateBest(current_node.board(),	bestmove=True)
			if bestmove:
				print("\nMelhor jogada: "+DescribeMove(bestmove,current_node.board()))
				extra_prompt = f" BM: {current_node.board().san(bestmove)} "
			else:
				print("\nImpossível calcular a melhor jogada.")
		elif cmd == "w":
			bestline_list = CalculateBest(current_node.board(), bestmove=False, as_san=True)
			if bestline_list:
				print(f"\nMelhor linha:")
				for line in bestline_list:
					print(line)
			else:
				print("\nImpossível calcular a melhor linha.")
		elif cmd == "e":
			print("\nLinhas de análise:\n")
			fen = current_node.board().fen()
			if fen not in cache_analysis:
				cache_analysis[fen] = ENGINE.analyse(current_node.board(), chess.engine.Limit(time=analysis_time), multipv=multipv)
				print(f"\nAnálise guardada em cache para a posição {len(cache_analysis)}.")
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
			print(f"Estatísticas: tempo {time_used} s, Hash {hashfull}, TB {tbhits},\nRede: {debug_string},"
									f"\nProfundidade {depth}/{seldepth}, val. CP. {score_str}, WDL: {wdl_str},\nnós {nodes}, NPS {nps}")
			for i, info in enumerate(analysis, start=1):
				pv = info.get("pv", [])
				if not pv:
					print(f"Linha {i}: Nenhuma jogada encontrada.")
					continue
				temp_board = current_node.board().copy()
				moves_san = []
				for move in pv:
					try:
						san_move = temp_board.san(move)
					except AssertionError as e:
						print(f"\nErro na conversão da jogada {move} em SAN: {e}")
						break
					moves_san.append(san_move)
					temp_board.push(move)
				else:
					moves_str = " ".join(moves_san)
					score_line = info.get("score")
					if score_line is not None and score_line.relative.is_mate():
						mate_moves = abs(score_line.relative.mate())
						moves_str = f"Mate em {mate_moves}, {moves_str}"
					print(f"Linha {i}: {moves_str}")
			smart = key("\nQuer inspecionar as linhas no modo smart? (s/n): ").lower()
			if smart == "s":
				SmartInspection(analysis, current_node.board())
		elif cmd == "r":
			eval_cp = CalculateEvaluation(current_node.board())
			if eval_cp is not None:
				extra_prompt = f" CP: {eval_cp/100:.2f} "
			else:
				print("\nImpossível calcular a avaliação.")
		elif cmd == "t":
			wdl = CalculateWDL(current_node.board())
			if wdl:
				adj_wdl=f"W{wdl[0]/100:.1f}%/D{wdl[1]/100:.1f}%/L{wdl[2]/100:.1f}% " 
				extra_prompt=f"{adj_wdl} "
			else:
				print("\nImpossível calcular as percentagens WDL.")
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
			print(f"\nTempo de análise atual: {analysis_time} segundos.\nPosições guardadas em cache: {len(cache_analysis)}")
			new_time = dgt("\nDefina o novo valor ou ENTER para manter: ", kind="i",	imin=1,	imax=300, default=analysis_time)
			if new_time != analysis_time:
				SetAnalysisTime(new_time)
				cache_analysis.clear()
				print("\nTempo de análise atualizado e cache limpa.")
		elif cmd == "o":
			print(f"\nNúmero de linhas de análise atual: {multipv},\nPosições guardadas em cache: {len(cache_analysis)}")
			new_lines = dgt("Defina o novo valor ou ENTER para manter: ", kind="i",imin=2,imax=10, default=multipv)
			if new_lines != multipv:
				SetMultipv(new_lines)
				cache_analysis.clear()
				print("\nNúmero de linhas de análise atualizado e cache limpa.")
		elif	cmd == "?":
			print("\nComandos disponíveis no modo de análise:")
			menu(ANALYSIS_COMMAND,show_only=True)
		else:
			print("Comando não reconhecido.")
	if saved:
		if "Annotator" not in pgn_game.headers or not pgn_game.headers["Annotator"].strip():
			pgn_game.headers["Annotator"] = f'Orologic V{VERSION} by {PROGRAMMER}'
		new_default_file_name=f'{pgn_game.headers.get("White")}-{pgn_game.headers.get("Black")}-{pgn_game.headers.get("Result", "-")}'
		base_name = dgt(f"Novo nome do arquivo comentado: ENTER para aceitar {new_default_file_name}", kind="s",default=new_default_file_name)
		new_filename = f"{base_name}-comentado-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
		new_filename	= sanitize_filename(new_filename)
		with open(new_filename, "w", encoding="utf-8") as f:
			f.write(str(pgn_game))
		print("PGN atualizado guardado como " + new_filename)
		saved = False
	else:
		print("Não foram feitas alterações ao PGN.")
	print("Saída do modo de análise. Retornando ao menu principal.")
def get_color_adjective(piece_color, gender):
	if gender == "m":
		return "branco" if piece_color == chess.WHITE else "preto"
	else:
		return "branca" if piece_color == chess.WHITE else "preta"
def extended_piece_description(piece):
	piece_name = PIECE_NAMES.get(piece.piece_type, "peça").capitalize()
	gender = PIECE_GENDER.get(piece.piece_type, "m")
	color_adj = get_color_adjective(piece.color, gender)
	return f"{piece_name} {color_adj}"
def read_diagonal(game_state, base_column, direction_right):
	"""
	Lê a diagonal a partir da casa na linha 1 da coluna base.
	O parâmetro direction_right:
		- True: direção superior-direita (coluna +1, linha +1)
		- False: direção superior-esquerda (coluna -1, linha +1)
	"""
	base_column = base_column.lower()
	if base_column not in "abcdefgh":
		print("Coluna base inválida.")
		return
	file_index = ord(base_column) - ord("a")
	rank_index = 0  # partimos da linha 1 (índice 0)
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
	dir_str = "superior-direita" if direction_right else "superior-esquerda"
	if report:
		print(f"Diagonal de {base_descr} na direção {dir_str}: " + ", ".join(report))
	else:
		print(f"Diagonal de {base_descr} na direção {dir_str} não contém peças.")
def read_rank(game_state, rank_number):
	# Obtém o conjunto de casas da linha (rank_number: 1-8)
	try:
		rank_bb = getattr(chess, f"BB_RANK_{rank_number}")
	except AttributeError:
		print("Linha inválida.")
		return
	squares = chess.SquareSet(rank_bb)
	report = []
	for square in squares:
		piece = game_state.board.piece_at(square)
		if piece:
			file_index = chess.square_file(square)
			file_letter = chr(ord("a") + file_index)
			descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
			# Usa a função helper para a peça
			report.append(f"{descriptive_file} {rank_number}: {extended_piece_description(piece)}")
	if report:
		print(f"Linha {rank_number}: " + ", ".join(report))
	else:
		print(f"A linha {rank_number} está vazia.")
def read_file(game_state, file_letter):
	# file_letter deve ser uma letra de 'a' a 'h'
	file_letter = file_letter.lower()
	if file_letter not in "abcdefgh":
		print("Coluna inválida.")
		return
	try:
		file_bb = getattr(chess, f"BB_FILE_{file_letter.upper()}")
	except AttributeError:
		print("Coluna inválida.")
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
		print(f"Coluna {LETTER_FILE_MAP.get(file_letter, file_letter)}: " + ", ".join(report))
	else:
		print(f"A coluna {LETTER_FILE_MAP.get(file_letter, file_letter)} está vazia.")
def read_square(game_state, square_str):
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print("Casa inválida.")
		return
	# Calcula a cor da casa: (coluna+linha) par -> escura, senão clara
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = "escura"
	else:
		color_descr = "clara"
	piece = game_state.board.piece_at(square)
	if piece:
		base_msg = f"A casa {square_str.upper()} é {color_descr} e contém {extended_piece_description(piece)}."
		# Calcula defensores e atacantes para a casa ocupada
		defenders = game_state.board.attackers(piece.color, square)
		attackers = game_state.board.attackers(not piece.color, square)
		info_parts = []
		if defenders:
			count = len(defenders)
			word = "peça" if count == 1 else "peças"
			info_parts.append(f"defendida por {count} {word} {'brancas' if piece.color == chess.WHITE else 'pretas' }")
		if attackers:
			count = len(attackers)
			word = "peça" if count == 1 else "peças"
			info_parts.append(f"atacada por {count} {word} {'pretas' if piece.color == chess.WHITE else 'brancas' }")
		if info_parts:
			base_msg += " " + " e ".join(info_parts) + "."
		print(base_msg)
	else:
		base_msg = f"A casa {square_str.upper()} é {color_descr} e está vazia."
		white_attackers = game_state.board.attackers(chess.WHITE, square)
		black_attackers = game_state.board.attackers(chess.BLACK, square)
		info_parts = []
		if white_attackers:
			count = len(white_attackers)
			word = "peça" if count == 1 else "peças"
			info_parts.append(f"atacada por {count} {word} brancas")
		if black_attackers:
			count = len(black_attackers)
			word = "peça" if count == 1 else "peças"
			info_parts.append(f"atacada por {count} {word} pretas")
		if info_parts:
			base_msg += " " + " e ".join(info_parts) + "."
		print(base_msg)
def report_piece_positions(game_state, piece_symbol):
	try:
		piece = chess.Piece.from_symbol(piece_symbol)
	except Exception as e:
		print("Não reconhecido: insira R N B Q K P, r n b q k p")
		return
	color_string = "branco" if piece.color == chess.WHITE else "preto"
	full_name = PIECE_NAMES.get(piece.piece_type, "peça")
	squares = game_state.board.pieces(piece.piece_type, piece.color)
	positions = []
	for square in squares:
		# Obtém coluna e linha
		file_index = chess.square_file(square)
		rank = chess.square_rank(square) + 1
		file_letter = chr(ord("a") + file_index)
		descriptive_file = LETTER_FILE_MAP.get(file_letter, file_letter)
		positions.append(f"{descriptive_file} {rank}")
	if positions:
		print(f"{color_string}: {full_name} em: " + ", ".join(positions))
	else:
		print(f"Nenhum {full_name} {color_string} encontrado.")
def report_white_time(game_state):
	initial_white = game_state.clock_config["phases"][game_state.white_phase]["white_time"]
	elapsed_white = initial_white - game_state.white_remaining
	if elapsed_white < 0:
		elapsed_white = 0
	perc_white = (elapsed_white / initial_white * 100) if initial_white > 0 else 0
	print("Tempo brancas: " + FormatTime(game_state.white_remaining) + f" ({perc_white:.0f}%)")
	return
def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	if elapsed_black < 0:
		elapsed_black = 0
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print("Tempo pretas: " + FormatTime(game_state.black_remaining) + f" ({perc_black:.0f}%)")
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
		# Se o relógio for simétrico, usa-se o tempo das brancas
		if clock_config["same_time"]:
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		else:
			# Em caso de relógios assimétricos, para PGN escolhe-se uma referência (aqui as brancas)
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		# Se moves == 0, consideramos a fase como "sudden death"
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
	return f"{m:02d} minutos e {s:02d} segundos!"
def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print("Formato de hora inválido. Esperado mm:ss. Erro:", e)
		return 0
def DescribeMove(move, board):
	# Gestão do roque
	if board.is_castling(move):
		if chess.square_file(move.to_square) > chess.square_file(move.from_square):
			return "roque pequeno"
		else:
			return "roque grande"
	# Obtemos a notação SAN da jogada
	try:
		san_str = board.san(move)
	except Exception as e:
		san_str = ""
	# Padrão para analisar a jogada SAN:
	# Grupos: 1=peça (opcional), 2=desambiguação (0-2 caracteres), 3='x' (captura), 4=destino, 5=promoção (opcional), 6=peça promoção, 7=xeque ou xeque-mate (opcional)
	pattern = re.compile(r'^([RNBQK])?([a-h1-8]{0,2})(x)?([a-h][1-8])(=([RNBQ]))?([+#])?$')
	m = pattern.match(san_str)
	if not m:
		# Fallback em caso de análise falhada
		return "Jogada não analisável"
	piece_letter = m.group(1)
	disamb = m.group(2)
	capture = m.group(3)
	dest = m.group(4)
	promo_letter = m.group(6)
	check_mark = m.group(7)
	# Determinamos o nome da peça que se move
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
		piece_name = "peão"
	# Começamos a compor a descrição
	descr = ""
	# Para o peão incluímos o artigo
	descr += piece_name
	# Se houver desambiguação, adicionamo-la (traduzindo letras em nomes se possível)
	if disamb:
		parts = []
		for ch in disamb:
			if ch.isalpha():
				parts.append(LETTER_FILE_MAP.get(ch, ch))
			else:
				parts.append(ch)
		descr += " de " + " ".join(parts)
	# Gestão da captura
	if capture:
		descr += " toma "
		captured_piece = board.piece_at(move.to_square)
		if not captured_piece and piece_letter=="" and chess.square_file(move.from_square) != chess.square_file(move.to_square):
			captured_sq = move.to_square + (8 if board.turn==chess.BLACK else -8)
			captured_piece = board.piece_at(captured_sq)
		if captured_piece:
			descr += PIECE_NAMES.get(captured_piece.piece_type, "").lower()
	# Descrição do destino
	dest_file = dest[0]
	dest_rank = dest[1]
	dest_name = LETTER_FILE_MAP.get(dest_file, dest_file)
	descr += " em " + dest_name + " " + dest_rank
	# Promoção
	if promo_letter:
		promo_mapping = {
			"Q": chess.QUEEN,
			"R": chess.ROOK,
			"B": chess.BISHOP,
			"N": chess.KNIGHT
		}
		promo_piece_type = promo_mapping.get(promo_letter.upper(), None)
		promo_piece_name = PIECE_NAMES.get(promo_piece_type, "").lower() if promo_piece_type is not None else ""
		descr += " e promove a " + promo_piece_name
	# Xeque ou xeque-mate
	if check_mark:
		if check_mark=="+":
			descr += " xeque"
		elif check_mark=="#":
			descr += " xeque-mate!"
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
			white_move_desc = f"Erro na jogada das brancas: {e}"
		if i + 1 < len(game_state.move_history):  # Se existe a jogada das pretas
			black_move_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_move_san)
				black_move_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except Exception as e:
				black_move_desc = f"Erro na jogada das pretas: {e}"
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
	Carrega o arquivo ECO e retorna uma lista de dicionários,
	cada um contendo "eco", "opening", "variation" e "moves" (lista de jogadas em SAN).
	"""
	eco_entries = []
	if not os.path.exists(filename):
		print("Arquivo eco.db não encontrado.")
		return eco_entries
	with open(filename, "r", encoding="utf-8") as f:
		content = f.read()
	# Remove eventuais blocos de comentário entre { e }
	content = re.sub(r'\{[^}]*\}', '', content)
	# Utiliza StringIO para fazer o parser PGN ler o conteúdo "limpo"
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
	Dada a lista de jogadas realizadas (move_history, lista de strings em SAN)
	e o banco de dados ECO (lista de dict), retorna a entrada da abertura
	com o maior prefixo correspondente às jogadas realizadas.
	Se nenhuma jogada corresponder, retorna None.
	"""
	best_match = None
	best_match_length = 0
	for entry in eco_db:
		eco_moves = entry["moves"]
		match_length = 0
		# Compara elemento por elemento a lista move_history e a da entrada
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
		print("Formato de hora inválido. Esperado hh:mm:ss. Erro:",e)
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
	print("\nCriação de relógios\n")
	name=dgt("Nome do relógio: ",kind="s")
	db=LoadDB()
	if any(c["name"]==name for c in db["clocks"]):
		print("Um relógio com este nome já existe.")
		return
	same=dgt("Brancas e Pretas começam com o mesmo tempo? (Enter para sim, 'n' para não): ",kind="s",smin=0,smax=1)
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(f"Tempo (hh:mm:ss) para fase {phase_count+1}: ")
			inc=dgt(f"Incremento em segundos para fase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(f"Tempo para as brancas (hh:mm:ss) fase {phase_count+1}: ")
			inc_w=dgt(f"Incremento para as brancas fase {phase_count+1}: ",kind="i")
			total_seconds_b=ParseTime(f"Tempo para as pretas (hh:mm:ss) fase {phase_count+1}: ")
			inc_b=dgt(f"Incremento para as pretas fase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(f"Número de jogadas para fase {phase_count+1} (0 para terminar): ",kind="i")
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt("Número de alarmes a inserir (max 5, 0 para nenhum): ",kind="i",imax=5,default=0)
	for i in range(num_alarms):
		alarm_input = dgt(f"Insira o tempo (mm:ss) para o alarme {i+1}: ", kind="s")
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt("Insira uma nota para o relógio (opcional): ",kind="s",default="")
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	db["clocks"].append(new_clock.to_dict())
	SaveDB(db)
	print("\nRelógio criado e guardado.")
def ViewClocks():
	print("\nVisualização de relógios\n")
	db=LoadDB()
	if not db["clocks"]:
		print("Nenhum relógio guardado.")
		return
	for idx,c in enumerate(db["clocks"]):
		indicatore="B=P" if c["same_time"] else "B/P"
		fasi=""
		for i,phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str=SecondsToHMS(phase["white_time"])
				fasi+=f" F{i+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w=SecondsToHMS(phase["white_time"])
				time_str_b=SecondsToHMS(phase["black_time"])
				fasi+=f" F{i+1}: Brancas:{time_str_w}+{phase['white_inc']}, Pretas:{time_str_b}+{phase['black_inc']}"
		num_alarms = len(c.get("alarms", []))  # Conta os alarmes
		alarms_str = f" Alarmes ({num_alarms})"
		print(f"{idx+1}. {c['name']} - {indicatore}{fasi}{alarms_str}")
		if c.get("note",""):
			print(f"\tNota: {c['note']}")
	attesa=key("Pressione uma tecla para voltar ao menu principal.")
def SelectClock(db):
	db = LoadDB()
	if not db["clocks"]:
		print("Nenhum relógio guardado.")
		return
	else:
		print(f"Há {len(db['clocks'])} relógios na coleção.")
	choices = {}
	for c in db["clocks"]:
		indicatore = "B=P" if c["same_time"] else "B/P"
		fasi = ""
		for j, phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str = SecondsToHMS(phase["white_time"])
				fasi += f" F{j+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w = SecondsToHMS(phase["white_time"])
				time_str_b = SecondsToHMS(phase["black_time"])
				fasi += f" F{j+1}: Brancas:{time_str_w}+{phase['white_inc']}, Pretas:{time_str_b}+{phase['black_inc']}"
		num_alarms = len(c.get("alarms", []))
		alarms_str = f" Alarmes ({num_alarms})"
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
		print("Nenhum relógio selecionado.")
def DeleteClock(db):
	print("\nEliminação de relógios guardados\n")
	orologio = SelectClock(db)
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			del db["clocks"][idx]
			SaveDB(db)
			print(f"\nRelógio '{clock_name}' eliminado, restam {len(db['clocks'])}.")
	return
def EditPGN():
	print("\nEditar informações padrão para PGN\n")
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	default_event = default_pgn.get("Event", "Orologic Game")
	event = dgt(f"Evento [{default_event}]: ", kind="s", default=default_event)
	if event.strip() == "":
		event = default_event
	default_site = default_pgn.get("Site", "Local desconhecido")
	site = dgt(f"Local [{default_site}]: ", kind="s", default=default_site)
	if site.strip() == "":
		site = default_site
	default_round = default_pgn.get("Round", "Round 1")
	round_ = dgt(f"Round [{default_round}]: ", kind="s", default=default_round)
	if round_.strip() == "":
		round_ = default_round
	default_white = default_pgn.get("White", "Brancas")
	white = dgt(f"Nome das Brancas [{default_white}]: ", kind="s", default=default_white)
	if white.strip() == "":
		white = default_white
	default_black = default_pgn.get("Black", "Pretas")
	black = dgt(f"Nome das Pretas [{default_black}]: ", kind="s", default=default_black)
	if black.strip() == "":
		black = default_black
	default_white_elo = default_pgn.get("WhiteElo", "1200")
	white_elo = dgt(f"Elo das Brancas [{default_white_elo}]: ", kind="s", default=default_white_elo)
	if white_elo.strip() == "":
		white_elo = default_white_elo
	default_black_elo = default_pgn.get("BlackElo", "1200")
	black_elo = dgt(f"Elo das Pretas [{default_black_elo}]: ", kind="s", default=default_black_elo)
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
	print("\nInformações padrão para o PGN atualizadas.")
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
			self.black_remaining = clock_config["phases"][0]["black_time"]  # Ou equivalentemente, ["white_time"]
		else:
			self.white_remaining = clock_config["phases"][0]["white_time"]
			self.black_remaining = clock_config["phases"][0]["black_time"]		
		self.white_phase=0
		self.black_phase=0
		self.white_moves=0
		self.black_moves=0
		# A vez inicial permanece "white" (brancas a jogar)
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
					print(self.white_player + " entra na fase " + str(self.white_phase+1) + " tempo da fase " + FormatTime(self.clock_config["phases"][self.white_phase]["white_time"]))
					self.white_remaining=self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves+=1
			if self.black_phase<len(self.clock_config["phases"])-1:
				if self.black_moves>=self.clock_config["phases"][self.black_phase]["moves"] and self.clock_config["phases"][self.black_phase]["moves"]!=0:
					self.black_phase+=1
					Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03,0, volume], kind=3, adsr=[20, 10, 75, 20])
					print(self.black_player + " entra na fase " + str(self.black_phase+1) + " tempo da fase " + FormatTime(self.clock_config["phases"][self.black_phase]["black_time"]))
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
						print(f"Alarme: tempo das brancas atingido {seconds_to_mmss(alarm)}")
						Acusticator(["c4",0.2,-0.75,volume])
						triggered_alarms_white.add(alarm)
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if alarm not in triggered_alarms_black and abs(game_state.black_remaining - alarm) < elapsed:
						print(f"Alarme: tempo das pretas atingido {seconds_to_mmss(alarm)}")
						Acusticator(["c4",0.2,0.75,volume])
						triggered_alarms_black.add(alarm)
		if game_state.white_remaining<=0 or game_state.black_remaining<=0:
			Acusticator(["e4", 0.2, -0.5, volume, "d4", 0.2, 0, volume, "c4", 0.2, 0.5, volume], kind=1, adsr=[10, 0, 90, 10])
			game_state.game_over=True
			print("Bandeira caída!")
			if game_state.white_remaining <= 0:
				game_state.pgn_game.headers["Result"] = "0-1"  # Pretas vencem
				print(f"Tempo das Brancas esgotado. {game_state.black_player} vence.")
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			else:
				game_state.pgn_game.headers["Result"] = "1-0"  # Brancas vencem
				print(f"Tempo das Pretas esgotado. {game_state.white_player} vence.")
				Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
		time.sleep(0.1)
def StartGame(clock_config):
	print("\nInício da partida\n")
	db = LoadDB()
	default_pgn = db.get("default_pgn", {})
	white_default = default_pgn.get("White", "Brancas")
	black_default = default_pgn.get("Black", "Pretas")
	white_elo_default = default_pgn.get("WhiteElo", "1500")
	black_elo_default = default_pgn.get("BlackElo", "1500")
	event_default = default_pgn.get("Event", "Orologic Game")
	site_default = default_pgn.get("Site", "Local desconhecido")
	round_default = default_pgn.get("Round", "Round 1")
	eco_db = LoadEcoDatabase("eco.db")
	last_eco_msg = None 
	white_player = dgt(f"Nome das brancas [{white_default}]: ", kind="s", default=white_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_player.strip() == "":
		white_player = white_default
	black_player = dgt(f"Nome das pretas [{black_default}]: ", kind="s", default=black_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_player.strip() == "":
		black_player = black_default
	white_elo = dgt(f"Elo das brancas [{white_elo_default}]: ", kind="s", default=white_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if white_elo.strip() == "":
		white_elo = white_elo_default
	black_elo = dgt(f"Elo das pretas [{black_elo_default}]: ", kind="s", default=black_elo_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if black_elo.strip() == "":
		black_elo = black_elo_default
	event = dgt(f"Evento [{event_default}]: ", kind="s", default=event_default)
	Acusticator(["c5", 0.05, 0, volume, "e5", 0.05, 0, volume, "g5", 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 5])
	if event.strip() == "":
		event = event_default
	site = dgt(f"Local [{site_default}]: ", kind="s", default=site_default)
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
	key("Pressione uma tecla qualquer para iniciar a partida quando estiver pronto...",attesa=1800)
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
					print("Linha inválida.")
			elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
				read_square(game_state, param)
			else:
				print("Comando dash não reconhecido.")
		elif user_input.startswith(","):
			Acusticator(["a3", .06, -1, volume, "c4", .06, -0.5, volume, "d#4", .06, 0.5, volume, "f4", .06, 1, volume], kind=3, adsr=[20, 5, 70, 25])
			report_piece_positions(game_state, user_input[1:2])
		elif user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			if cmd==".?":
				menu(DOT_COMMANDS,show_only=True,p="Comandos disponíveis:")
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
				adv="brancas" if game_state.white_remaining>game_state.black_remaining else "pretas"
				print(f"{adv} em vantagem de "+FormatTime(diff))
			elif cmd==".5":
				if game_state.paused:
					Acusticator(['d4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					pause_duration = time.time() - paused_time_start if paused_time_start else 0
					hours = int(pause_duration // 3600)
					minutes = int((pause_duration % 3600) // 60)
					seconds = int(pause_duration % 60)
					ms = int((pause_duration - int(pause_duration)) * 1000)
					print(f"Tempo em pausa há: {f'{hours:2d} horas, ' if hours else ''}{f'{minutes:2d} minutos, ' if minutes or hours else ''}{f'{seconds:2d} segundos e ' if seconds or minutes or hours else ''}{f'{ms:3d} ms' if ms else ''}")
				else:
					Acusticator(['f4', 0.54, 0, volume], kind=1, adsr=[0, 0, 100, 100])
					player = game_state.white_player if game_state.active_color=="white" else game_state.black_player
					print(f"Relógio de {player} em andamento")
			elif cmd==".m":
				white_material,black_material=CalculateMaterial(game_state.board)
				print(f"Material: {game_state.white_player} {white_material}, {game_state.black_player} {black_material}")
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					print("Relógios em pausa")
					Acusticator(["c5", 0.1, 1, volume, "g4", 0.1, 0.3, volume, "e4", 0.1, -0.3, volume, "c4", 0.1, -1, volume], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, volume, "e4", 0.1, -0.3, volume, "g4", 0.1, 0.3, volume, "c5", 0.1, 1, volume], kind=1, adsr=[2, 8, 80, 10])
					print("Pausa durou "+FormatTime(pause_duration))
			elif cmd==".q":
				if game_state.paused and game_state.move_history:
					game_state.board.pop()
					game_state.pgn_node=game_state.pgn_node.parent
					last_move=game_state.move_history.pop()
					print("Última jogada anulada: "+last_move)
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
						print("Novo tempo brancas: "+FormatTime(game_state.white_remaining)+", pretas: "+FormatTime(game_state.black_remaining))
					except:
						print("Comando inválido.")
			elif cmd==".s":
				Acusticator(["c4", 0.2, -1, volume, "g4", 0.2, -0.3, volume, "c5", 0.2, 0.3, volume, "e5", 0.2, 1, volume, "g5", 0.4, 0, volume], kind=1, adsr=[10, 5, 80, 5])
				print(game_state.board)
			elif cmd==".l":
				summary = GenerateMoveSummary(game_state)
				if summary:
					print("\nLista de jogadas realizadas:\n")
					for line in summary:
						print(line)
				else:
					print("Nenhuma jogada realizada ainda.")
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
				print("Resultado atribuído: "+result)
				game_state.pgn_game.headers["Result"]=result
				game_state.game_over=True
			elif cmd.startswith(".c"):
				new_comment = cmd[2:].strip()
				if game_state.move_history:
					if game_state.pgn_node.comment:
						game_state.pgn_node.comment += "\n" + new_comment
					else:
						game_state.pgn_node.comment = new_comment
					print("Comentário registado para a jogada: " + game_state.move_history[-1])
				else:
					print("Nenhuma jogada para comentar.")
			else:
				print("Comando não reconhecido.")
		else:
			if game_state.paused:
				print("Não é possível inserir novas jogadas enquanto o tempo está em pausa. Reinicie o tempo com .p")
				Acusticator(["b3",.2,0,volume],kind=2)
				continue
			user_input=NormalizeMove(user_input)
			try:
				move = game_state.board.parse_san(user_input)
				board_copy=game_state.board.copy()
				description=DescribeMove(move,board_copy)
				Acusticator([1000.0, 0.01, 0, volume], kind=1, adsr=[0, 0, 100, 0])
				# Imprime a jogada precedida pelo nome do jogador com base na vez
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
							print("Abertura detetada: " + new_eco_msg)
							last_eco_msg = new_eco_msg
				if game_state.board.is_checkmate():
					game_state.game_over = True
					result = "1-0" if game_state.active_color == "white" else "0-1"
					game_state.pgn_game.headers["Result"] = result
					print(f"Xeque-mate! Vence {game_state.white_player if game_state.active_color == 'white' else game_state.black_player}.")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break  # Sai do ciclo
				elif game_state.board.is_stalemate():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Empate por afogamento!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_insufficient_material():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Empate por material insuficiente!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_seventyfive_moves():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Empate pela regra das 75 jogadas!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.is_fivefold_repetition():
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Empate por repetição da posição (5 vezes)!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_fifty_moves():  # Controlo para a *solicitação* das 50 jogadas
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Empate pela regra das 50 jogadas (a pedido)!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				elif game_state.board.can_claim_threefold_repetition(): # Controlo para a *solicitação* da tripla repetição.
					game_state.game_over = True
					game_state.pgn_game.headers["Result"] = "1/2-1/2"
					print("Empate por tripla repetição da posição (a pedido)!")
					Acusticator(["c5", 0.1, -0.5, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0.5, volume, "c6", 0.2, 0, volume], kind=1, adsr=[2, 8, 90, 0])
					break
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()
			except Exception as e:
				illegal_result=verbose_legal_moves_for_san(game_state.board,user_input)
				print("Jogada ilegal, na casa indicada são possíveis:\n"+illegal_result)
	game_state.pgn_game.headers["WhiteClock"] = FormatClock(game_state.white_remaining)
	game_state.pgn_game.headers["BlackClock"] = FormatClock(game_state.black_remaining)
	print("Partida terminada.")
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
	print("PGN guardado como "+filename+".")
	analyze_choice = key("Quer analisar a partida? (s/n): ").lower()
	if analyze_choice == "s":
		db = LoadDB()
		engine_config = db.get("engine_config", {})
		if not engine_config or not engine_config.get("engine_path"):
			print("Motor não configurado. Retornando ao menu.")
			return
		else:
			AnalyzeGame(game_state.pgn_game)
def OpenManual():
	print("\nAbrindo manual\n")
	readme="readme_pt.htm"
	if os.path.exists(readme):
		webbrowser.open(readme)
	else:
		print("O arquivo readme_it.htm não existe.")
def SchermataIniziale():
	now = datetime.datetime.now()
	diff1 = relativedelta(now, BIRTH_DATE)
	diff2 = relativedelta(now, RELEASE_DATE)
	parts1 = []
	if diff1.years:
		parts1.append(f"{diff1.years} anos")
	if diff1.months:
		parts1.append(f"{diff1.months} meses")
	if diff1.days:
		parts1.append(f"{diff1.days} dias")
	if diff1.hours:
		parts1.append(f"{diff1.hours} horas")
	if diff1.minutes:
		parts1.append(f"e {diff1.minutes} minutos")
	age_string = ", ".join(parts1)
	parts2 = []
	if diff2.years:
		parts2.append(f"{diff2.years} anos")
	if diff2.months:
		parts2.append(f"{diff2.months} meses")
	if diff2.days:
		parts2.append(f"{diff2.days} dias")
	if diff2.hours:
		parts2.append(f"{diff2.hours} horas")
	if diff2.minutes:
		parts2.append(f"{diff2.minutes} minutos")
	release_string = ", ".join(parts2)
	print(f"\nOlá! Bem-vindo, sou o Orologic e tenho {age_string}.")
	print(f"A última versão é a {VERSION} e foi lançada em {RELEASE_DATE.strftime('%d/%m/%Y %H:%M')}.")
	print(f"\tisto é: {release_string} atrás.")
	print("\t\tAutor: "+PROGRAMMER)
	print("\t\t\tDigite '?' para visualizar o menu.")
	Acusticator(['c4', 0.125, 0, volume, 'd4', 0.125, 0, volume, 'e4', 0.125, 0, volume, 'g4', 0.125, 0, volume, 'a4', 0.125, 0, volume, 'e5', 0.125, 0, volume, 'p', 0.125, 0, 0.5, 'a5', 0.125, 0, volume], kind=1, adsr=[0.01, 0, 100, 99])
def Main():
	global	volume
	db = LoadDB()
	volume = db.get("volume", 0.5)
	SchermataIniziale()
	InitEngine()
	while True:
		scelta=menu(MENU_CHOICES, show=True, keyslist=True, full_keyslist=False)
		if scelta == "analisa":
			Acusticator(["a5", .04, 0, volume, "e5", .04, 0, volume, "p",.08,0,0, "g5", .04, 0, volume, "e6", .120, 0, volume], kind=1, adsr=[2, 8, 90, 0])
			AnalyzeGame(None)
		elif scelta=="cria":
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			CreateClock()
		elif scelta=="comandos":
			Acusticator([500.0, 0.4, -1, volume, 800.0, 0.4, 1, volume], kind=3, adsr=[20, 10, 50, 20])
			menu(DOT_COMMANDS,show_only=True)
		elif scelta=="motor":
			Acusticator(["e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume])
			EditEngineConfig()
		elif scelta=="volume":
			Acusticator(["f6",.02,0,volume,"p",.04,0,volume,"a6",.02,0,volume])
			volume = dgt(f"\nVolume atual: {int(volume*100)}, novo? (0-100): ", kind="i", imin=0, imax=100, default=50)
			volume/=100
			db = LoadDB()
			db["volume"] = volume
			SaveDB(db)
			Acusticator(["c5",1,0,volume])
		elif scelta=="vê":
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
			ViewClocks()
		elif scelta=="elimina":
			DeleteClock(db)
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="pgn":
			EditPGN()
			Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
		elif scelta=="manual":
			OpenManual()
		elif scelta=="joga":
			Acusticator(["c5", 0.1, 0, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0, volume, "c6", 0.3, 0, volume, "g5", 0.1, 0, volume, "e5", 0.1, 0, volume, "c5", 0.1, 0, volume], kind=1, adsr=[5, 5, 90, 10])
			print("\nInício da partida\n")
			db=LoadDB()
			if not db["clocks"]:
				print("Nenhum relógio disponível. Crie um primeiro.")
			else:
				clock_config=SelectClock(db)
				if clock_config is not None:
					StartGame(clock_config)
				else:
					print("Escolha inválida.")
		elif scelta==".":
			Acusticator(["g4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "a4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "p", 0.15, 0, 0, "b4", 0.15, -0.5, volume, "c5", 0.3, 0.5, volume], kind=1, adsr=[5, 0, 100, 5])
			if ENGINE is not None:
				ENGINE.quit()
				print("\nConexão com o motor UCI fechada")
			break
if __name__=="__main__":
	time_start = datetime.datetime.now()
	board=CustomBoard()
	Main()
	time_end = datetime.datetime.now()
	delta = relativedelta(time_end, time_start)
	components = []
	if delta.days:
		components.append(f"{delta.days} dias")
	if delta.hours:
		components.append(f"{delta.hours} horas")
	if delta.minutes:
		components.append(f"{delta.minutes} minutos")
	if delta.seconds:
		components.append(f"{delta.seconds} segundos")
	ms = delta.microseconds // 1000
	if ms:
		components.append(f"{ms} milissegundos")
	result = ", ".join(components) if components else "0 milissegundos"
	print(f"Adeus do Orologic {VERSION}.\nNós nos divertimos juntos por: {result}")
	sys.exit(0)