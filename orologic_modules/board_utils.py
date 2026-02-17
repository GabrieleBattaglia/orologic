import chess
import chess.pgn
import copy
import re
import os
import io
from GBUtils import polipo, Acusticator
from . import config

lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

def CalculateMaterial(board):
    w, b = 0, 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p:
            v = config.PIECE_VALUES.get(p.symbol().upper(), 0)
            if p.color == chess.WHITE: w += v
            else: b += v
    return w, b

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

def DescribeMove(move, board, annotation=None):
	L10N = config.L10N
	if board.is_castling(move):
		base_descr = L10N['moves']['short_castle'] if chess.square_file(move.to_square) > chess.square_file(move.from_square) else L10N['moves']['long_castle']
	else:
		san_base = ""
		try:
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
					if not file_disamb_needed: disambiguation = from_sq_str[0]
					else:
						rank_disamb_needed = False
						for sq in potential_origins:
							if sq != move.from_square and chess.square_rank(sq) == chess.square_rank(move.from_square):
								rank_disamb_needed = True
								break
						if not rank_disamb_needed: disambiguation = from_sq_str[1]
						else: disambiguation = from_sq_str
			promo_str = ""
			if is_promo:
				promo_piece_symbol = chess.piece_symbol(move.promotion).upper()
				promo_str = "={promo}".format(promo=promo_piece_symbol)
			capture_char = "x" if is_capture else ""
			if piece_symbol:
				san_base = "{symbol}{disambiguation}{capture}{to_sq}{promo}".format(symbol=piece_symbol, disambiguation=disambiguation, capture=capture_char, to_sq=to_sq_str, promo=promo_str)
			else:
				if is_capture: san_base = "{from_file}{capture}{to_sq}{promo}".format(from_file=from_sq_str[0], capture=capture_char, to_sq=to_sq_str, promo=promo_str)
				else: san_base = "{to_sq}{promo}".format(to_sq=to_sq_str, promo=promo_str)
		except:
			try:
				san_base = board.san(move).replace("!","").replace("?","")
			except:
				san_base = _("Mossa da {from_sq} a {to_sq}").format(from_sq=chess.square_name(move.from_square), to_sq=chess.square_name(move.to_square))
		
		pattern = re.compile(r'^([RNBQK])?([a-h1-8]{1,2})?(x)?([a-h][1-8])(=([RNBQ]))?$')
		pawn_pattern = re.compile(r'^([a-h])?(x)?([a-h][1-8])(=([RNBQ]))?$')
		m = pattern.match(san_base)
		if m and m.group(1):
			piece_letter = m.group(1); disamb = m.group(2) or ""; capture = m.group(3); dest = m.group(4); promo_letter = m.group(6)
			piece_type = chess.PIECE_SYMBOLS.index(piece_letter.lower())
		else:
			m = pawn_pattern.match(san_base)
			if m:
				piece_letter = ""; disamb = m.group(1) or ""; capture = m.group(2); dest = m.group(3); promo_letter = m.group(5); piece_type = chess.PAWN
			else: base_descr = san_base; piece_type = None

		if piece_type is not None:
			piece_type_key = chess.PIECE_NAMES[piece_type].lower()
			piece_name = L10N['pieces'][piece_type_key]['name']; descr = piece_name
			if disamb:
				if piece_type == chess.PAWN: descr += " {col}".format(col=L10N['columns'].get(disamb, disamb))
				else:
					parts = [L10N['columns'].get(ch, ch) if ch.isalpha() else ch for ch in disamb]
					descr += _(" di ") + "".join(parts)
			if capture:
				descr += " {capture_verb}".format(capture_verb=L10N['moves']['capture'])
				if board.is_en_passant(move):
					ep_square = move.to_square + (-8 if board.turn == chess.WHITE else 8)
					captured_piece = board.piece_at(ep_square); descr += " {ep}".format(ep=L10N['moves']['en_passant'])
				else: captured_piece = board.piece_at(move.to_square)
				if captured_piece and not board.is_en_passant(move):
					captured_type_key = chess.PIECE_NAMES[captured_piece.piece_type].lower()
					captured_name = L10N['pieces'][captured_type_key]['name']; descr += " {name}".format(name=captured_name)
				descr += " {prep} {file}{rank}".format(prep=L10N['moves']['capture_on'], file=L10N['columns'].get(dest[0], dest[0]), rank=dest[1])
			else: descr += " {prep} {file}{rank}".format(prep=L10N['moves']['move_to'], file=L10N['columns'].get(dest[0], dest[0]), rank=dest[1])
			if promo_letter:
				promo_type = chess.PIECE_SYMBOLS.index(promo_letter.lower()); promo_type_key = chess.PIECE_NAMES[promo_type].lower()
				descr += " {promo_verb} {promo_name}".format(promo_verb=L10N['moves']['promotes_to'], promo_name=L10N['pieces'][promo_type_key]['name'])
			base_descr = descr
	
	board_after = board.copy(); board_after.push(move); final_descr = base_descr
	if board_after.is_checkmate(): final_descr += " {checkmate}".format(checkmate=L10N['moves']['checkmate'])
	elif board_after.is_check(): final_descr += " {check}".format(check=L10N['moves']['check'])
	if annotation and annotation in L10N['annotations']: final_descr += " ({a})".format(a=L10N['annotations'][annotation])
	return final_descr

def GenerateMoveSummary(game_state):
	summary = []; move_number = 1; board_copy = CustomBoard()
	for i in range(0, len(game_state.move_history), 2):
		white_move_san = game_state.move_history[i]
		try:
			white_move = board_copy.parse_san(white_move_san)
			white_move_desc = DescribeMove(white_move, board_copy)
			board_copy.push(white_move)
		except Exception as e: white_move_desc = _("Errore bianco: {e}").format(e=e)
		if i + 1 < len(game_state.move_history):
			black_move_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_move_san)
				black_move_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except Exception as e: black_move_desc = _("Errore nero: {e}").format(e=e)
			summary.append("{num}. {w}, {b}".format(num=move_number, w=white_move_desc, b=black_move_desc))
		else: summary.append("{num}. {w}".format(num=move_number, w=white_move_desc))
		move_number += 1
	return summary

def format_pgn_comments(pgn_str):
    def repl(match): return "{\n" + match.group(1).strip() + "\n}"
    return re.sub(r'\{(.*?)\}', repl, pgn_str, flags=re.DOTALL)

class CustomBoard(chess.Board):
    def __str__(self):
        res = f"FEN: {self.fen()}\n"
        w, b = CalculateMaterial(self)
        rs = range(8, 0, -1) if self.turn == chess.WHITE else range(1, 9)
        fs = range(8) if self.turn == chess.WHITE else range(7, -1, -1)
        for r in rs:
            res += str(r)
            for f in fs:
                p = self.piece_at(chess.square(f, r-1))
                if p: res += p.symbol().upper() if p.color == chess.WHITE else p.symbol().lower()
                else: res += "-" if (r+f)%2==0 else "+"
            res += "\n"
        res += " abcdefgh" if self.turn == chess.WHITE else " hgfedcba"
        return res

    def copy(self, stack=True):
        nb = super().copy(stack=stack); nb.__class__ = CustomBoard; return nb

class GameState:
	def __init__(self, clock_config):
		self.board = CustomBoard()
		self.clock_config = clock_config
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
		self.white_player = ""
		self.black_player = ""

	def switch_turn(self):
		if self.active_color == "white":
			self.white_moves += 1
			if self.white_phase < len(self.clock_config["phases"]) - 1:
				phase_moves = self.clock_config["phases"][self.white_phase]["moves"]
				if phase_moves != 0 and self.white_moves >= phase_moves:
					self.white_phase += 1
					Acusticator(['d2', .8, 0, config.VOLUME, 'd7', .03, 0, config.VOLUME, 'a#6', .03, 0, config.VOLUME], kind=3, adsr=[20, 10, 75, 20])
					print(self.white_player + _(" entra in fase ") + str(self.white_phase + 1) + _(" tempo fase ") + FormatTime(self.clock_config["phases"][self.white_phase]["white_time"]))
					self.white_remaining = self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves += 1
			if self.black_phase < len(self.clock_config["phases"]) - 1:
				phase_moves = self.clock_config["phases"][self.black_phase]["moves"]
				if phase_moves != 0 and self.black_moves >= phase_moves:
					self.black_phase += 1
					Acusticator(['d2', .8, 0, config.VOLUME, 'd7', .03, 0, config.VOLUME, 'a#6', .03, 0, config.VOLUME], kind=3, adsr=[20, 10, 75, 20])
					print(self.black_player + _(" entra in fase ") + str(self.black_phase + 1) + _(" tempo fase ") + FormatTime(self.clock_config["phases"][self.black_phase]["black_time"]))
					self.black_remaining = self.clock_config["phases"][self.black_phase]["black_time"]
		self.active_color = "black" if self.active_color == "white" else "white"

def LoadEcoDatabaseWithFEN(filename="eco.db"):
    eco_entries = []
    db_path = config.resource_path(os.path.join("resources", filename))
    if not os.path.exists(db_path):
        print(_("File {filename} non trovato.").format(filename=db_path))
        return eco_entries
    try:
        with open(db_path, "r", encoding="utf-8") as f: content = f.read()
    except Exception as e:
        print(_("Errore durante la lettura di {filename}: {error}").format(filename=db_path, error=e))
        return eco_entries
    content = re.sub(r'\{[^}]*\}', '', content, flags=re.DOTALL)
    stream = io.StringIO(content); game_count = 0; skipped_count = 0
    while True:
        stream_pos = stream.tell()
        try:
            headers = chess.pgn.read_headers(stream)
            if headers is None: break
            stream.seek(stream_pos); game = chess.pgn.read_game(stream); game_count += 1
            if game is None:
                skipped_count += 1
                while True:
                    line = stream.readline()
                    if not line: break
                    if line.strip(): stream.seek(stream.tell() - len(line.encode('utf-8'))); break
                continue
            eco_code = game.headers.get("ECO", ""); opening = game.headers.get("Opening", ""); variation = game.headers.get("Variation", "")
            moves = []; node = game; last_valid_node = game; parse_error = False
            while node.variations:
                next_node = node.variations[0]; move = next_node.move
                try: san = node.board().san(move); moves.append(san)
                except: parse_error = True; break
                node = next_node; last_valid_node = node
            if not parse_error and moves:
                final_fen = last_valid_node.board().board_fen(); ply_count = len(moves)
                eco_entries.append({"eco": eco_code, "opening": opening, "variation": variation, "moves": moves, "fen": final_fen, "ply": ply_count})
            elif parse_error: skipped_count += 1
        except:
            skipped_count += 1
            while True:
                line = stream.readline()
                if not line: break
                if line.strip().startswith('['): stream.seek(stream.tell() - len(line.encode('utf-8'))); break
    if eco_entries: print(_("Caricate {num_entries} linee di apertura ECO.").format(num_entries=len(eco_entries)))
    return eco_entries

def format_pv_descriptively(board, pv):
	if not pv: return ""
	temp_board = board.copy(); output_lines = []
	i = 0
	while i < len(pv):
		move_num = temp_board.fullmove_number
		if temp_board.turn == chess.WHITE:
			white_move = pv[i]
			white_desc = DescribeMove(white_move, temp_board)
			line_str = "  {num}. {desc}".format(num=move_num, desc=white_desc)
			temp_board.push(white_move)
			i += 1
			if i < len(pv):
				black_move = pv[i]
				black_desc = DescribeMove(black_move, temp_board)
				line_str += ", {desc}".format(desc=black_desc)
				temp_board.push(black_move)
				i += 1
			output_lines.append(line_str)
		else:
			black_move = pv[i]
			black_desc = DescribeMove(black_move, temp_board)
			line_str = "  {num}... {desc}".format(num=move_num, desc=black_desc)
			output_lines.append(line_str)
			temp_board.push(black_move)
			i += 1
	return "\n".join(output_lines)

def DetectOpeningByFEN(current_board, eco_db_with_fen):
    current_fen = current_board.board_fen(); current_ply = current_board.ply()
    possible_matches = [e for e in eco_db_with_fen if e["fen"] == current_fen]
    if not possible_matches: return None
    exact_ply_matches = [m for m in possible_matches if m["ply"] == current_ply]
    if exact_ply_matches: return max(exact_ply_matches, key=lambda x: len(x["moves"]))
    return None

def FormatTime(seconds):
    total = int(seconds); h = total // 3600; m = (total % 3600) // 60; s = total % 60
    parts = []
    if h: parts.append(_("{num} ora").format(num=h) if h==1 else _("{num} ore").format(num=h))
    if m: parts.append(_("{num} minuto").format(num=m) if m==1 else _("{num} minuti").format(num=m))
    if s: parts.append(_("{num} secondo").format(num=s) if s==1 else _("{num} secondi").format(num=s))
    return ", ".join(parts) if parts else _("0 secondi")

def ParseTime(prompt):
	from GBUtils import dgt
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":")); return h*3600+m*60+s
	except Exception as e:
		print(_("Formato orario non valido. Atteso hh:mm:ss. Errore:"),e); return 0

def SecondsToHMS(seconds):
    h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = int(seconds % 60)
    return "{:02d}:{:02d}:{:02d}".format(h, m, s)

def FormatClock(seconds):
	total = int(seconds); hours = total // 3600; minutes = (total % 3600) // 60; secs = total % 60
	return "{hours:02d}:{minutes:02d}:{secs:02d}".format(hours=hours, minutes=minutes, secs=secs)

def seconds_to_mmss(seconds):
	m = int(seconds // 60); s = int(seconds % 60)
	return _("{minutes:02d} minuti e {seconds:02d} secondi!").format(minutes=m, seconds=s)

def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print(_("Formato orario non valido. Atteso mm:ss. Errore:"), e); return 0
