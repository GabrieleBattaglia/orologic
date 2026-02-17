import os
import json
import sys
import chess
import random
import re
import datetime
import pyperclip
from GBUtils import polipo, key, dgt, menu, Acusticator
from . import config
from . import board_utils
from . import clock
from . import storage
from . import version

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

# Variabile globale per la localizzazione dinamica
L10N = {}

# Recupero volume
try:
    db = storage.LoadDB()
    volume = db.get("volume", 1.0)
except:
    volume = 1.0

def enter_escape(prompt=""):
    """Ritorna vero su invio, falso su escape."""
    while True:
        k = key(prompt).strip()
        if k == "":
            return True
        elif k == "\x1b":
            return False
        print(_("Conferma con invio o annulla con escape"))

def get_default_localization():
    return {
        "pieces": {
            "pawn": {"name": _("pedone"), "gender": "m"},
            "knight": {"name": _("cavallo"), "gender": "m"},
            "bishop": {"name": _("alfiere"), "gender": "m"},
            "rook": {"name": _("torre"), "gender": "f"},
            "queen": {"name": _("regina"), "gender": "f"},
            "king": {"name": _("re"), "gender": "m"}
        },
        "adjectives": {
            "white": {"m": _("bianco"), "f": _("bianca")},
            "black": {"m": _("nero"), "f": _("nera")}
        },
        "columns": {
            "a": "a", "b": "b", "c": "c", "d": "d", "e": "e", "f": "f", "g": "g", "h": "h"
        },
        "moves": {
            "short_castle": _("arrocco corto"),
            "long_castle": _("arrocco lungo"),
            "capture": _("mangia"),
            "capture_on": _("in"),
            "move": _("va in"),
            "move_to": _("in"),
            "check": _("scacco"),
            "mate": _("scacco matto"),
            "checkmate": _("scacco matto!"),
            "promotion": _("promuove a"),
            "promotes_to": _("e promuove a"),
            "en_passant": _("en passant")
        },
        "annotations": {
            "!": _("mossa forte"),
            "?": _("mossa debole"),
            "!!": _("mossa molto forte"),
            "??": _("mossa molto debole"),
            "!?": _("mossa interessante"),
            "?!": _("mossa dubbia")
        }
    }

def LoadLocalization():
    path = config.percorso_salvataggio(os.path.join("locales", f"orologic_ui_{lingua_rilevata}.json"))
    default = get_default_localization()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                return loaded
        except Exception:
            return default
    else:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
        except: pass
        return default

def EditLocalization():
	print(_("\n--- Personalizzazione Lingua ---\n"))
	print(_("Per ogni voce, inserisci il nuovo testo o premi INVIO per mantenere il valore attuale."))
	db = storage.LoadDB()
	l10n_config = db.get("localization", get_default_localization())
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
	num_items = len(items_to_edit)
	notes = ['c3', 'd3', 'e3', 'f3', 'g3', 'a3', 'b3', 'c4', 'd4', 'e4', 'f4', 'g4', 'a4', 'b4', 'c5', 'd5', 'e5', 'f5', 'g5', 'a5', 'b5', 'c6', 'd6', 'e6', 'f6', 'g6', 'a6', 'b6', 'c7']
	for i, item in enumerate(items_to_edit):
		cat, key_item, details = item
		pitch = notes[i % len(notes)]
		pan = -1 + (2 * i / (num_items -1)) if num_items > 1 else 0 
		if isinstance(details, tuple):
			sub_key, prompt_text = details
			current_val = l10n_config[cat][key_item][sub_key]
			new_val = dgt("{prompt} [{current}]: ".format(prompt=prompt_text, current=current_val), kind="s", default=current_val)
			l10n_config[cat][key_item][sub_key] = new_val.strip()
			if cat == "pieces":
				current_gender = l10n_config[cat][key_item]['gender']
				gender_prompt = _("  Genere per '{new_val}' (m/f/n) [{current_gender}]: ").format(new_val=new_val, current_gender=current_gender)
				while True:
					new_gender = dgt(gender_prompt, kind="s", default=current_gender).lower()
					if new_gender in ['m', 'f', 'n']:
						l10n_config[cat][key_item]['gender'] = new_gender
						break
					else:
						print(_("Input non valido. Inserisci 'm' (maschile), 'f' (femminile) o 'n' (neutro)."))
		else: 
			prompt_text = details
			current_val = l10n_config[cat][key_item]
			new_val = dgt("{prompt} [{current}]: ".format(prompt=prompt_text, current=current_val), kind="s", default=current_val)
			l10n_config[cat][key_item] = new_val.strip()
		Acusticator([pitch, 0.08, pan, volume], kind=1, adsr=[2, 5, 80, 10])
	Acusticator(['c7', 0.05, 0, volume,'e7', 0.05, 0, volume,'g7', 0.15, 0, volume], kind=1, adsr=[2, 5, 90, 5])
	db["localization"] = l10n_config
	storage.SaveDB(db)
	global L10N
	L10N = LoadLocalization() 
	print(_("\nImpostazioni di lingua salvate con successo!"))

def get_color_adjective(piece_color, gender):
    white_adj = L10N.get('adjectives', {}).get('white', {})
    black_adj = L10N.get('adjectives', {}).get('black', {})
    
    if piece_color == chess.WHITE:
        return white_adj.get('f', _('bianca')) if gender == 'f' else white_adj.get('m', _('bianco'))
    else:
        return black_adj.get('f', _('nera')) if gender == 'f' else black_adj.get('m', _('nero'))

def extended_piece_description(piece):
    if not piece: return _("casa vuota")
    
    piece_type_key = chess.PIECE_NAMES[piece.piece_type].lower() 
    pieces_dict = L10N.get('pieces', {})
    piece_info = pieces_dict.get(piece_type_key, {"name": piece.symbol(), "gender": "m"})
    
    piece_name = piece_info.get('name', piece.symbol()).capitalize()
    piece_gender = piece_info.get('gender', 'm')
    
    color_adj = get_color_adjective(piece.color, piece_gender)
    return "{piece} {color}".format(piece=piece_name, color=color_adj)

def DescribeMove(move, board, annotation=None):
	if board.is_castling(move):
		base_descr = L10N['moves']['short_castle'] if chess.square_file(move.to_square) > chess.square_file(move.from_square) else L10N['moves']['long_castle']
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
		
		# Logica parsing SAN e costruzione descrizione verbosa (recuperata da backup)
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
			piece_type_key = chess.PIECE_NAMES[piece_type].lower()
			piece_name = L10N['pieces'][piece_type_key]['name']
			descr = piece_name
			if disamb:
				if piece_type == chess.PAWN:
					descr += " {col}".format(col=L10N['columns'].get(disamb, disamb))
				else:
					parts = [L10N['columns'].get(ch, ch) if ch.isalpha() else ch for ch in disamb]
					descr += _(" di ") + "".join(parts)
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
	
	if annotation and annotation in L10N.get('annotations', {}):
		final_descr += " ({annotation})".format(annotation=L10N['annotations'][annotation])
		
	return final_descr

def format_pv_descriptively(board, pv):
	if not pv:
		return ""
	
	temp_board = board.copy()
	output_lines = []
	
	for i, move in enumerate(pv):
		move_num = temp_board.fullmove_number
		if temp_board.turn == chess.WHITE:
			line_prefix = f"{move_num}."
		else:
			line_prefix = f"{move_num}..."

		descriptive_move = DescribeMove(move, temp_board)
		output_lines.append(f"\t\t\t{line_prefix} {descriptive_move}")
		temp_board.push(move)
		
	return "\n".join(output_lines)

def read_diagonal(game_state, base_column, direction_right):
    base_column = base_column.lower()
    if base_column not in "abcdefgh":
        print(_("Colonna base non valida."))
        return
    file_index = ord(base_column) - ord("a")
    rank_index = 0
    report = []
    
    cols_dict = L10N.get('columns', {})
    base_descr = "{col} 1".format(col=cols_dict.get(base_column, base_column))
    
    while 0 <= file_index < 8 and 0 <= rank_index < 8:
        square = chess.square(file_index, rank_index)
        piece = game_state.board.piece_at(square)
        if piece:
            current_file = chr(ord("a") + file_index)
            descriptive_file = cols_dict.get(current_file, current_file)
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
        rank_int = int(rank_number)
        if not (1 <= rank_int <= 8): raise ValueError
        rank_idx = rank_int - 1
    except ValueError:
        print(_("Traversa non valida."))
        return

    report = []
    cols_dict = L10N.get('columns', {})
    
    for file_idx in range(8):
        square = chess.square(file_idx, rank_idx)
        piece = game_state.board.piece_at(square)
        if piece:
            file_letter = chr(ord("a") + file_idx)
            descriptive_file = cols_dict.get(file_letter, file_letter)
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
        
    report = []
    file_idx = ord(file_letter) - ord('a')
    cols_dict = L10N.get('columns', {})
    descriptive_file = cols_dict.get(file_letter, file_letter)
    
    for rank_idx in range(8):
        square = chess.square(file_idx, rank_idx)
        piece = game_state.board.piece_at(square)
        if piece:
            report.append("{file} {rank}: {piece_desc}".format(file=descriptive_file, rank=rank_idx+1, piece_desc=extended_piece_description(piece)))

    if report:
        print(_("Colonna {file}: ").format(file=descriptive_file) + ", ".join(report))
    else:
        print(_("La colonna {file} è vuota.").format(file=descriptive_file))

def _get_piece_descriptions_from_squareset(board, squareset):
	descriptions = []
	for sq in squareset:
		piece = board.piece_at(sq)
		if piece:
			piece_desc = extended_piece_description(piece)
			sq_name = chess.square_name(sq)
			col_name = L10N['columns'].get(sq_name[0].lower(), sq_name[0])
			rank_name = sq_name[1]
			descriptions.append(_("{piece_desc} in {col_name} {rank_name}").format(piece_desc=piece_desc, col_name=col_name, rank_name=rank_name))
	return descriptions

def read_square(game_state, square_str):
	try:
		square = chess.parse_square(square_str)
	except Exception as e:
		print(_("Casa non valida."))
		return
	if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
		color_descr = _("scura")
	else:
		color_descr = _("chiara")
	piece = game_state.board.piece_at(square)
	
	final_parts = []
	if piece:
		base_msg = _("La casa {square} ├¿ {color} e contiene {piece_desc}.").format(square=square_str.upper(), color=color_descr, piece_desc=extended_piece_description(piece))
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
		base_msg = _("La casa {square} ├¿ {color} e risulta vuota.").format(square=square_str.upper(), color=color_descr)
		final_parts.append(base_msg)
		white_attackers_squares = game_state.board.attackers(chess.WHITE, square)
		if white_attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, white_attackers_squares)
			final_parts.append(_("attaccata dal Bianco con: {attackers}").format(attackers=', '.join(attacker_descs)))
		black_attackers_squares = game_state.board.attackers(chess.BLACK, square)
		if black_attackers_squares:
			attacker_descs = _get_piece_descriptions_from_squareset(game_state.board, black_attackers_squares)
			final_parts.append(_("attaccata dal Nero con: {attackers}").format(attackers=', '.join(attacker_descs)))
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
	print(_("Tempo bianco: ") + clock.FormatTime(game_state.white_remaining) + " ({perc:.0f}%)".format(perc=perc_white))
	return

def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	if elapsed_black < 0:
		elapsed_black = 0
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print(_("Tempo nero: ") + clock.FormatTime(game_state.black_remaining) + " ({perc:.0f}%)".format(perc=perc_black))
	return

def save_text_summary(game_state, descriptive_moves, eco_entry):
	headers = game_state.pgn_game.headers
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
	footer_text = _("\nRisultato finale: {result}\n").format(result=headers.get('Result', '*'))
	footer_text += "--------------------------------\n"
	footer_text += _("File generato il: {datetime}\n").format(datetime=datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
	footer_text += _("Report generato da Orologic V{version} - {programmer}\n").format(version=version.VERSION, programmer=version.PROGRAMMER)
	full_text = header_text + move_list_text + footer_text
	base_filename = "{white}-{black}-{result}-{timestamp}".format(white=headers.get('White', _('Bianco')), black=headers.get('Black', _('Nero')), result=headers.get('Result', '*'), timestamp=datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
	sanitized_name = config.sanitize_filename(base_filename) + ".txt"
	full_path = config.percorso_salvataggio(os.path.join("txt", sanitized_name))
	try:
		with open(full_path, "w", encoding="utf-8") as f:
			f.write(full_text)
		print(_("Riepilogo partita salvato come {filename}.").format(filename=full_path))
	except Exception as e:
		print(_("Errore durante il salvataggio del riepilogo testuale: {error}").format(error=e))
		Acusticator(["a3", 1, 0, volume], kind=2, adsr=[0, 0, 100, 100])

def setup_fischer_random_board():
    print(_("\n--- Configurazione Fischer Random (Chess960) ---"))
    while True:
        prompt = _("\nInserisci la sequenza di 8 pezzi, '?' per una casuale, o '.' per annullare: ")
        user_input = dgt(prompt, kind="s").upper()
        if user_input == '?':
            pos_number = random.randint(0, 959)
            print(_("Generazione posizione casuale numero {pos_num}...").format(pos_num=pos_number))
            board_to_return = board_utils.CustomBoard.from_chess960_pos(pos_number)
            starting_fen = board_to_return.fen()
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
        else:
            fen_to_try = "{sequence}/pppppppp/8/8/8/8/PPPPPPPP/{sequence_upper} w - - 0 1".format(sequence=user_input.lower(), sequence_upper=user_input)
            try:
                board_to_return = board_utils.CustomBoard(fen_to_try, chess960=True)
                pos_number = board_to_return.chess960_pos()
                Acusticator(["c5", 0.1, -0.8, volume, "e5", 0.1, 0, volume, "g5", 0.2, 0.8, volume], kind=1, adsr=[2, 8, 90, 0])
                print(_("Posizione valida! Numero di riferimento Chess960: {number}").format(number=pos_number))
                return board_to_return, fen_to_try
            except ValueError as e:
                print(_("Errore: Posizione non valida. La libreria riporta: '{error}'").format(error=e))
                Acusticator(["a3", .3, 0, volume], kind=2, adsr=[5, 15, 0, 80])
                continue

def GenerateMoveSummary(game_state):
	summary = []
	move_number = 1
	board_copy = board_utils.CustomBoard()
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
		result_lines.append(_("{i}┬░: {desc}").format(i=i, desc=verbose_desc))
		i+=1
	return "\n".join(result_lines)

def Impostazioni(db):
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
    storage.SaveDB(db)
    print(_("Salvataggio completato. Impostazioni aggiornate"))
    return

# Inizializza L10N all'importazione
L10N = LoadLocalization()
