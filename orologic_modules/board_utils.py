import chess
import chess.pgn
import copy
import re
import os
import io
from GBUtils import polipo, Acusticator
from . import config
from . import clock
from . import storage

lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

try:
    db = storage.LoadDB()
    volume = db.get("volume", 1.0)
except:
    volume = 1.0

def CalculateMaterial(board):
    white_material = 0
    black_material = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            value = config.PIECE_VALUES.get(piece.symbol(), 0)
            if piece.color == chess.WHITE:
                white_material += value
            else:
                black_material += value
    return white_material, black_material

def NormalizeMove(m):
    return m.replace("+", "").replace("#", "")

def LoadEcoDatabaseWithFEN(filename="eco.db"):
	"""
	Carica il file ECO, calcola il FEN finale per ogni linea
	e restituisce una lista di dizionari contenenti:
	"eco", "opening", "variation", "moves" (lista SAN),
	"fen" (FEN della posizione finale), "ply" (numero di semimosse).
	Utilizza node.board().san() per una generazione SAN pi├╣ robusta.
	"""
	eco_entries = []
	db_path = config.resource_path(os.path.join("resources", filename))
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
					# Questo ├¿ generalmente pi├╣ affidabile
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
	Se ci sono pi├╣ match, preferisce quello con lo stesso numero di mosse (ply),
	e tra questi, quello con la sequenza di mosse pi├╣ lunga nel database ECO.
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
		# Se ci sono match con lo stesso numero di mosse, scegli il pi├╣ specifico
		# (quello definito con pi├╣ mosse nel db ECO, anche se dovrebbero essere uguali se ply ├¿ uguale)
		return max(exact_ply_matches, key=lambda x: len(x["moves"]))
	else:
		return None # Nessun match trovato con il numero di mosse corretto

def format_pgn_comments(pgn_str):
    def repl(match):
        comment_text = match.group(1).strip()
        return "{\n" + comment_text + "\n}"
    return re.sub(r'\{(.*?)\}', repl, pgn_str, flags=re.DOTALL)

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
                except Exception:
                    last_move_san = "???"
            else:
                last_move_san = "???"
                
            if self.turn == chess.BLACK:
                last_move_info = "{num}. {san}".format(num=move_number, san=last_move_san)
            else:
                last_move_info = "{num}... {san}".format(num=move_number, san=last_move_san)
                
        board_str += " {move_info} Materiale: {white_mat}/{black_mat}".format(
            move_info=last_move_info, white_mat=white_material, black_mat=black_material)
        return board_str

    def copy(self, stack=True):
        new_board = super().copy(stack=stack)
        new_board.__class__ = CustomBoard
        return new_board
    
    @classmethod
    def from_chess960_pos(cls, pos_number):
        board = super().from_chess960_pos(pos_number)
        board.__class__ = CustomBoard
        return board
        
    def __repr__(self):
        return self.__str__()

class GameState:
    def __init__(self, clock_config):
        self.board = CustomBoard()
        self.clock_config = clock_config
        if clock_config.get("same_time", True):
            self.white_remaining = clock_config["phases"][0]["white_time"]
            self.black_remaining = clock_config["phases"][0]["black_time"]
        else:
            self.white_remaining = clock_config["phases"][0]["white_time"]
            self.black_remaining = clock_config["phases"][0]["black_time"]
            
        self.white_phase = 0
        self.black_phase = 0
        self.white_moves = 0
        self.black_moves = 0
        self.active_color = "white"
        self.paused = False
        self.game_over = False
        self.descriptive_move_history = []
        self.move_history = []
        self.pgn_game = chess.pgn.Game.from_board(CustomBoard())
        self.pgn_game.headers["Event"] = "Orologic Game"
        self.pgn_node = self.pgn_game
        
        self.white_player = _("Il Bianco")
        self.black_player = _("Il Nero")

    def switch_turn(self):
        if self.active_color == "white":
            self.white_moves += 1
            phases = self.clock_config["phases"]
            if self.white_phase < len(phases) - 1:
                current_phase_moves = phases[self.white_phase]["moves"]
                if self.white_moves >= current_phase_moves and current_phase_moves != 0:
                    self.white_phase += 1
                    Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03, 0, volume], kind=3, adsr=[20, 10, 75, 20])
                    print(self.white_player + _(" entra in fase ") + str(self.white_phase+1) + _(" tempo fase ") + clock.FormatTime(phases[self.white_phase]["white_time"]))
                    self.white_remaining = phases[self.white_phase]["white_time"]
        else:
            self.black_moves += 1
            phases = self.clock_config["phases"]
            if self.black_phase < len(phases) - 1:
                current_phase_moves = phases[self.black_phase]["moves"]
                if self.black_moves >= current_phase_moves and current_phase_moves != 0:
                    self.black_phase += 1
                    Acusticator(['d2', .8, 0, volume, 'd7', .03, 0, volume, 'a#6', .03, 0, volume], kind=3, adsr=[20, 10, 75, 20])
                    print(self.black_player + _(" entra in fase ") + str(self.black_phase+1) + _(" tempo fase ") + clock.FormatTime(phases[self.black_phase]["black_time"]))
                    self.black_remaining = phases[self.black_phase]["black_time"]
                    
        self.active_color = "black" if self.active_color == "white" else "white"
