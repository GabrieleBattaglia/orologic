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

# Volume gestito via config.VOLUME

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

def recursive_merge(base_dict, user_dict):
    for key, value in user_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            recursive_merge(base_dict[key], value)
        else:
            base_dict[key] = value
    return base_dict

def LoadLocalization():
    path = config.percorso_salvataggio(os.path.join("locales", f"orologic_ui_{lingua_rilevata}.json"))
    default = get_default_localization()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                merged = recursive_merge(default, loaded)
        except Exception:
            merged = default
    else:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
        except: pass
        merged = default
    try:
        db = storage.LoadDB()
        user_l10n = db.get("localization", {})
        if user_l10n:
             merged = recursive_merge(merged, user_l10n)
    except: pass
    return merged

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
		Acusticator([pitch, 0.08, pan, config.VOLUME], kind=1, adsr=[2, 5, 80, 10])
	Acusticator(['c7', 0.05, 0, config.VOLUME,'e7', 0.05, 0, config.VOLUME,'g7', 0.15, 0, config.VOLUME], kind=1, adsr=[2, 5, 90, 5])
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

def format_pv_descriptively(board, pv):
	if not pv: return ""
	temp_board = board.copy()
	output_lines = []
	for i, move in enumerate(pv):
		move_num = temp_board.fullmove_number
		line_prefix = f"{move_num}." if temp_board.turn == chess.WHITE else f"{move_num}..."
		descriptive_move = board_utils.DescribeMove(move, temp_board)
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
        print(_("La traversa {rank} e' vuota.").format(rank=rank_number))

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
        print(_("La colonna {file} e' vuota.").format(file=descriptive_file))

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
	except Exception:
		print(_("Casa non valida."))
		return
	color_descr = _("scura") if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0 else _("chiara")
	piece = game_state.board.piece_at(square)
	final_parts = []
	if piece:
		base_msg = _("La casa {square} e' {color} e contiene {piece_desc}.").format(square=square_str.upper(), color=color_descr, piece_desc=extended_piece_description(piece))
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
		base_msg = _("La casa {square} e' {color} e risulta vuota.").format(square=square_str.upper(), color=color_descr)
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
	except Exception:
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
	perc_white = (elapsed_white / initial_white * 100) if initial_white > 0 else 0
	print(_("Tempo bianco: ") + clock.FormatTime(game_state.white_remaining) + " ({perc:.0f}%)".format(perc=perc_white))

def report_black_time(game_state):
	initial_black = game_state.clock_config["phases"][game_state.black_phase]["black_time"]
	elapsed_black = initial_black - game_state.black_remaining
	perc_black = (elapsed_black / initial_black * 100) if initial_black > 0 else 0
	print(_("Tempo nero: ") + clock.FormatTime(game_state.black_remaining) + " ({perc:.0f}%)".format(perc=perc_black))

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
	header_text += _("Tempo finale Bianco: {clock}\n").format(clock=headers.get('WhiteClock', _('N/D')))
	header_text += _("Tempo finale Nero: {clock}\n").format(clock=headers.get('BlackClock', _('N/D')))
	header_text += _("Controllo del Tempo: {tc}\n").format(tc=headers.get('TimeControl', _('N/D')))
	opening_text = _("Apertura: {eco} - {opening}").format(eco=eco_entry.get('eco', ''), opening=eco_entry.get('opening', '')) if eco_entry else _("Apertura: non rilevata\n")
	if eco_entry and eco_entry.get('variation'): opening_text += " ({variation})\n".format(variation=eco_entry.get('variation'))
	header_text += opening_text + "--------------------------------\n\n"
	move_list_text = _("Lista Mosse:\n")
	for num, i in enumerate(range(0, len(descriptive_moves), 2), 1):
		white = descriptive_moves[i]
		black = descriptive_moves[i+1] if i+1 < len(descriptive_moves) else ""
		move_list_text += f"{num}. {white}" + (f", {black}\n" if black else "\n")
	footer_text = _("\nRisultato finale: {result}\n").format(result=headers.get('Result', '*'))
	footer_text += "--------------------------------\n"
	footer_text += _("File generato il: {datetime}\n").format(datetime=datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
	footer_text += _("Report generato da Orologic V{version} - {programmer}\n").format(version=version.VERSION, programmer=version.PROGRAMMER)
	full_text = header_text + move_list_text + footer_text
	base_filename = config.sanitize_filename("{white}-{black}-{result}-{timestamp}".format(white=headers.get('White', _('Bianco')), black=headers.get('Black', _('Nero')), result=headers.get('Result', '*'), timestamp=datetime.datetime.now().strftime('%Y%m%d%H%M%S'))) + ".txt"
	full_path = config.percorso_salvataggio(os.path.join("txt", base_filename))
	try:
		with open(full_path, "w", encoding="utf-8") as f: f.write(full_text)
		print(_("Riepilogo partita salvato come {filename}.").format(filename=full_path))
	except Exception as e:
		print(_("Errore durante il salvataggio del riepilogo testuale: {error}").format(error=e))
		Acusticator(["a3", 1, 0, config.VOLUME], kind=2, adsr=[0, 0, 100, 100])

def setup_fischer_random_board():
    print(_("\n--- Configurazione Fischer Random (Chess960) ---"))
    while True:
        prompt = _("\nInserisci la sequenza di 8 pezzi, '?' per una casuale, o '.' per annullare: ")
        user_input = dgt(prompt, kind="s").upper()
        if user_input == '?':
            pos_number = random.randint(0, 959)
            board_to_return = board_utils.CustomBoard.from_chess960_pos(pos_number)
            starting_fen = board_to_return.fen()
            piece_sequence = "".join([board_to_return.piece_at(i).symbol().upper() for i in range(8)])
            Acusticator(["c5", 0.1, -0.8, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.2, 0.8, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
            print(_("Posizione generata: {sequence} (Numero: {number})").format(sequence=piece_sequence, number=pos_number))
            return board_to_return, starting_fen
        elif user_input == '.': return None, None
        elif len(user_input) != 8:
            print(_("Errore: la sequenza deve contenere 8 caratteri."))
            Acusticator(["b3", .2, 0, config.VOLUME], kind=2); continue
        else:
            fen_to_try = "{sequence}/pppppppp/8/8/8/8/PPPPPPPP/{sequence_upper} w - - 0 1".format(sequence=user_input.lower(), sequence_upper=user_input)
            try:
                board_to_return = board_utils.CustomBoard(fen_to_try, chess960=True)
                Acusticator(["c5", 0.1, -0.8, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.2, 0.8, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
                print(_("Posizione valida! Numero Chess960: {number}").format(number=board_to_return.chess960_pos()))
                return board_to_return, fen_to_try
            except: Acusticator(["a3", .3, 0, config.VOLUME], kind=2); continue

def GenerateMoveSummary(game_state):
	summary = []
	board_copy = board_utils.CustomBoard()
	for i in range(0, len(game_state.move_history), 2):
		white_san = game_state.move_history[i]
		try:
			white_move = board_copy.parse_san(white_san)
			white_desc = DescribeMove(white_move, board_copy)
			board_copy.push(white_move)
		except: white_desc = "Err"
		black_desc = ""
		if i + 1 < len(game_state.move_history):
			black_san = game_state.move_history[i + 1]
			try:
				black_move = board_copy.parse_san(black_san)
				black_desc = DescribeMove(black_move, board_copy)
				board_copy.push(black_move)
			except: black_desc = "Err"
		summary.append(f"{i//2 + 1}. {white_desc}" + (f", {black_desc}" if black_desc else ""))
	return summary

def verbose_legal_moves_for_san(board,san_str):
	if san_str in ["O-O","0-0","O-O-O","0-0-0"]:
		legal_moves=[m for m in board.legal_moves if board.is_castling(m)]
	else:
		s=san_str.replace("+","").replace("#","").strip()
		promotion=None
		if "=" in s:
			parts=s.split("="); s=parts[0]
			promo_char=parts[1].strip().upper()
			promotion = {"Q":chess.QUEEN, "R":chess.ROOK, "B":chess.BISHOP, "N":chess.KNIGHT}.get(promo_char)
		try: dest_square=chess.parse_square(s[-2:]); legal_moves=[m for m in board.legal_moves if m.to_square==dest_square and (m.promotion==promotion if promotion else True)]
		except: return _("Destinazione non riconosciuta.")
	if not legal_moves: return _("Nessuna mossa legale trovata.")
	return "\n".join([_("{i}. {desc}").format(i=i+1, desc=DescribeMove(m, board.copy())) for i, m in enumerate(legal_moves)])

def Impostazioni(db):
    from . import engine
    print(_("\nModifica impostazioni varie di Orologic\n"))
    autosave_enabled = db.get("autosave_enabled", False)
    if key(_("Salvataggio automatico: [{status}]. Premi Invio per cambiare: ").format(status=_("Attivo") if autosave_enabled else _("Non attivo"))).strip() == "":
        db["autosave_enabled"] = not autosave_enabled
    menu_numerati = db.get("menu_numerati", False)
    if key(_("Stile menu: [{status}]. Premi Invio per cambiare: ").format(status=_("Numeri") if menu_numerati else _("Parole"))).strip() == "":
        db["menu_numerati"] = not menu_numerati
    
    # Impostazioni Analisi Default
    cur_time = db.get("default_analysis_time", 1.0)
    new_time = dgt(_("Tempo analisi default (sec) [{cur}]: ").format(cur=cur_time), kind="f", fmin=0.1, fmax=300, default=cur_time)
    Acusticator(["f7", .09, 0, config.VOLUME, "d4", .07, 0, config.VOLUME])
    if new_time != cur_time:
        db["default_analysis_time"] = new_time
        engine.SetAnalysisTime(new_time)

    cur_pv = db.get("default_multipv", 3)
    new_pv = dgt(_("Linee analisi default (multipv) [{cur}]: ").format(cur=cur_pv), kind="i", imin=1, imax=20, default=cur_pv)
    Acusticator(["f7", .09, 0, config.VOLUME, "d4", .07, 0, config.VOLUME])
    if new_pv != cur_pv:
        db["default_multipv"] = new_pv
        engine.SetMultipv(new_pv)

    # Impostazioni Soglie Analisi
    thresholds = db.get("analysis_thresholds", {"inesattezza": 50, "errore": 100, "svarione": 250})
    print(_("\nSoglie Analisi Attuali: Inesattezza {i}cp, Errore {e}cp, Svarione {s}cp").format(i=thresholds["inesattezza"], e=thresholds["errore"], s=thresholds["svarione"]))
    if enter_escape(_("Vuoi modificare le soglie di analisi? (INVIO per modificare, ESC per mantenere): ")):
        print(_("Inserisci le nuove soglie in centipawn (cp)."))
        t_ines = dgt(_("Soglia Inesattezza [{cur}]: ").format(cur=thresholds["inesattezza"]), kind="i", imin=10, imax=200, default=thresholds["inesattezza"])
        t_err = dgt(_("Soglia Errore [{cur}]: ").format(cur=thresholds["errore"]), kind="i", imin=t_ines + 1, imax=500, default=thresholds["errore"])
        t_svar = dgt(_("Soglia Svarione [{cur}]: ").format(cur=thresholds["svarione"]), kind="i", imin=t_err + 1, imax=2000, default=thresholds["svarione"])
        
        db["analysis_thresholds"] = {"inesattezza": t_ines, "errore": t_err, "svarione": t_svar}
        print(_("Soglie analisi aggiornate."))
        Acusticator(["f7", .09, 0, config.VOLUME, "d4", .07, 0, config.VOLUME])

    storage.SaveDB(db)
    print(_("Impostazioni aggiornate"))

L10N = LoadLocalization()
