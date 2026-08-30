import datetime
import os

import chess

from GBUtils import Acusticator, dgt, key
from GBUtils import enter_escape as _enter_escape_gbutils

from . import board_utils, config, localizzazione, orologio, storage, tempo, version
from .board_utils import stampa_elenco
from .config import _

# Il dizionario dei termini vive in localizzazione: qui solo un rimando,
# aggiornato sul posto, cosi' tutti i moduli vedono le stesse parole.
L10N = localizzazione.L10N

# Volume gestito via config.VOLUME


# La conferma con INVIO o ESC e' un'utilita' di GBUtils: qui ne esisteva
# una seconda versione, e nello stesso file se ne usavano tutte e due.
enter_escape = _enter_escape_gbutils


def EditLocalization():
    print(_("Personalizzazione dei nomi e della grammatica di gioco"))
    print(
        _(
            "Per ogni voce, inserisci il nuovo testo o premi INVIO per mantenere il valore attuale."
        )
    )
    print(_("Digita un punto per chiudere subito, conservando le voci gia' riviste."))
    db = storage.LoadDB()
    # Carica i default e sovrascrivili con le personalizzazioni utente esistenti
    # Questo garantisce che le nuove chiavi (es. 'analysis') siano presenti anche se il DB è vecchio
    l10n_config = localizzazione.unisci(
        localizzazione.predefinito(), db.get("localization", {})
    )

    items_to_edit = [
        ("pieces", "pawn", ("name", _("Nome per 'Pedone'"))),
        ("pieces", "pawn", ("pname", _("Nome PLURALE per 'Pedone'"))),
        ("pieces", "knight", ("name", _("Nome per 'Cavallo'"))),
        ("pieces", "knight", ("pname", _("Nome PLURALE per 'Cavallo'"))),
        ("pieces", "bishop", ("name", _("Nome per 'Alfiere'"))),
        ("pieces", "bishop", ("pname", _("Nome PLURALE per 'Alfiere'"))),
        ("pieces", "rook", ("name", _("Nome per 'Torre'"))),
        ("pieces", "rook", ("pname", _("Nome PLURALE per 'Torre'"))),
        ("pieces", "queen", ("name", _("Nome per 'Donna'"))),
        ("pieces", "queen", ("pname", _("Nome PLURALE per 'Donna'"))),
        ("pieces", "king", ("name", _("Nome per 'Re'"))),
        ("pieces", "king", ("pname", _("Nome PLURALE per 'Re'"))),
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
        ("adjectives", "white", ("mp", _("Aggettivo 'bianco' (maschile plurale)"))),
        ("adjectives", "white", ("fp", _("Aggettivo 'bianco' (femminile plurale)"))),
        ("adjectives", "black", ("m", _("Aggettivo 'nero' (maschile)"))),
        ("adjectives", "black", ("f", _("Aggettivo 'nero' (femminile)"))),
        ("adjectives", "black", ("mp", _("Aggettivo 'nero' (maschile plurale)"))),
        ("adjectives", "black", ("fp", _("Aggettivo 'nero' (femminile plurale)"))),
        ("moves", "capture", _("Verbo per la cattura (es. 'prende')")),
        ("moves", "capture_on", _("Preposizione per la casa di cattura (es. 'in')")),
        ("moves", "move_to", _("Preposizione per la casa di destinazione (es. 'in')")),
        ("moves", "en_passant", _("Testo per 'en passant'")),
        ("moves", "short_castle", _("Testo per 'arrocco corto'")),
        ("moves", "long_castle", _("Testo per 'arrocco lungo'")),
        ("moves", "promotes_to", _("Testo per la promozione (es. 'e promuove a')")),
        ("moves", "move", _("Verbo di spostamento (es. 'va in')")),
        ("moves", "promotion", _("Testo breve per la promozione (es. 'promuove a')")),
        ("moves", "check", _("Testo per 'scacco'")),
        ("moves", "mate", _("Testo per 'scacco matto' senza esclamativo")),
        ("moves", "checkmate", _("Testo per 'scacco matto!'")),
        ("annotations", "!", _("Commento per la mossa forte")),
        ("annotations", "?", _("Commento per la mossa debole")),
        ("annotations", "!!", _("Commento per la mossa molto forte")),
        ("annotations", "??", _("Commento per la mossa molto debole")),
        ("annotations", "!?", _("Commento per la mossa interessante")),
        ("annotations", "?!", _("Commento per la mossa dubbia")),
        ("annotations", "=", _("Commento per la proposta di patta")),
        ("analysis", "blunder", _("Termine per 'Svarione'")),
        ("analysis", "mistake", _("Termine per 'Errore'")),
        ("analysis", "inaccuracy", _("Termine per 'Inesattezza'")),
        ("analysis", "good", _("Termine per 'Mossa Buona'")),
        ("analysis", "brilliant", _("Termine per 'Mossa Geniale'")),
        ("analysis", "normal", _("Termine per 'Mossa Normale'")),
        ("analysis", "book", _("Termine per 'Teoria'")),
    ]
    num_items = len(items_to_edit)
    # Calcolo dinamico frequenze
    start_freq = 130.81
    end_freq = 2093.00
    pitches = []
    for k in range(num_items):
        p = (
            start_freq * ((end_freq / start_freq) ** (k / (num_items - 1)))
            if num_items > 1
            else start_freq
        )
        pitches.append(p)

    interrompi = False
    for i, item in enumerate(items_to_edit):
        cat, key_item, details = item
        current_pitch = pitches[i]
        pan = -1 + (2 * i / (num_items - 1)) if num_items > 1 else 0

        if isinstance(details, tuple):
            sub_key, prompt_text = details
            current_val = l10n_config.get(cat, {}).get(key_item, {}).get(sub_key, "")
            new_val = dgt(
                f"{prompt_text} [{current_val}]: ",
                kind="s",
                default=current_val,
            )
            if new_val.strip() == ".":
                break
            if cat not in l10n_config:
                l10n_config[cat] = {}
            if key_item not in l10n_config[cat]:
                l10n_config[cat][key_item] = {}
            l10n_config[cat][key_item][sub_key] = new_val.strip()

            if cat == "pieces":
                # Suono di conferma per il nome del pezzo
                Acusticator(
                    [current_pitch, 0.08, pan, config.VOLUME],
                    kind=1,
                    adsr=[2, 5, 80, 10],
                )

                current_gender = l10n_config[cat][key_item].get("gender", "m")
                gender_prompt = _(
                    "Genere per '{new_val}', m, f oppure n [{current_gender}]: "
                ).format(new_val=new_val, current_gender=current_gender)
                while True:
                    new_gender = dgt(
                        gender_prompt, kind="s", default=current_gender
                    ).lower()
                    # Il punto chiude qui come nelle altre domande: senza questa
                    # via d'uscita si restava intrappolati nel ciclo.
                    if new_gender.strip() == ".":
                        interrompi = True
                        break
                    if new_gender in ["m", "f", "n"]:
                        l10n_config[cat][key_item]["gender"] = new_gender
                        # Suono di conferma per il genere
                        Acusticator(
                            [current_pitch * 1.2, 0.08, pan, config.VOLUME],
                            kind=1,
                            adsr=[2, 5, 80, 10],
                        )
                        break
                    print(
                        _(
                            "Risposta non valida. Scrivi m per maschile, f per femminile, n per neutro, oppure un punto per chiudere."
                        )
                    )
                if interrompi:
                    break
            else:
                # Suono di conferma standard (aggettivi)
                Acusticator(
                    [current_pitch, 0.08, pan, config.VOLUME],
                    kind=1,
                    adsr=[2, 5, 80, 10],
                )
        else:
            prompt_text = details
            current_val = l10n_config.get(cat, {}).get(key_item, "")
            new_val = dgt(
                f"{prompt_text} [{current_val}]: ",
                kind="s",
                default=current_val,
            )
            if new_val.strip() == ".":
                break
            if cat not in l10n_config:
                l10n_config[cat] = {}
            l10n_config[cat][key_item] = new_val.strip()
            # Suono di conferma standard
            Acusticator(
                [current_pitch, 0.08, pan, config.VOLUME], kind=1, adsr=[2, 5, 80, 10]
            )
    Acusticator(
        [
            "c7",
            0.05,
            0,
            config.VOLUME,
            "e7",
            0.05,
            0,
            config.VOLUME,
            "g7",
            0.15,
            0,
            config.VOLUME,
        ],
        kind=1,
        adsr=[2, 5, 90, 5],
    )
    storage.SetValue("localization", l10n_config)
    localizzazione.ricarica()
    print(_("\nImpostazioni di lingua salvate con successo!"))


def report_all_pieces(game_state, color):
    cols_dict = L10N.get("columns", {})
    board = game_state.board
    pieces_map = {
        chess.PAWN: [],
        chess.KNIGHT: [],
        chess.BISHOP: [],
        chess.ROOK: [],
        chess.QUEEN: [],
        chess.KING: [],
    }

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == color:
            pieces_map[piece.piece_type].append(sq)

    color_str = get_color_adjective(color, gender="m", plural=True)
    print(_("Riepilogo pezzi {c}").format(c=color_str.capitalize()))

    found_any = False
    for p_type in [
        chess.KING,
        chess.QUEEN,
        chess.ROOK,
        chess.BISHOP,
        chess.KNIGHT,
        chess.PAWN,
    ]:
        squares = pieces_map[p_type]
        if squares:
            found_any = True
            piece_type_key = chess.PIECE_NAMES[p_type].lower()
            piece_info = L10N["pieces"].get(piece_type_key, {})
            # Usa il nome plurale se ci sono più pezzi dello stesso tipo, altrimenti il singolare
            name_key = "pname" if len(squares) > 1 else "name"
            display_name = piece_info.get(
                name_key, piece_info.get("name", chess.PIECE_NAMES[p_type])
            )

            positions = []
            for sq in squares:
                file_letter = chess.square_name(sq)[0]
                rank = chess.square_name(sq)[1]
                descriptive_file = cols_dict.get(file_letter, file_letter)
                positions.append(f"{descriptive_file} {rank}")

            stampa_elenco(positions, intestazione=display_name.capitalize() + ":")

    if not found_any:
        print(_("Nessun pezzo rimasto!"))


def get_color_adjective(piece_color, gender, plural=False):
    white_adj = L10N.get("adjectives", {}).get("white", {})
    black_adj = L10N.get("adjectives", {}).get("black", {})
    if piece_color == chess.WHITE:
        if plural:
            return (
                white_adj.get("fp", _("bianche"))
                if gender == "f"
                else white_adj.get("mp", _("bianchi"))
            )
        return (
            white_adj.get("f", _("bianca"))
            if gender == "f"
            else white_adj.get("m", _("bianco"))
        )
    else:
        if plural:
            return (
                black_adj.get("fp", _("nere"))
                if gender == "f"
                else black_adj.get("mp", _("neri"))
            )
        return (
            black_adj.get("f", _("nera"))
            if gender == "f"
            else black_adj.get("m", _("nero"))
        )


def extended_piece_description(piece):
    if not piece:
        return _("casa vuota")
    piece_type_key = chess.PIECE_NAMES[piece.piece_type].lower()
    pieces_dict = L10N.get("pieces", {})
    piece_info = pieces_dict.get(
        piece_type_key, {"name": piece.symbol(), "gender": "m"}
    )
    piece_name = piece_info.get("name", piece.symbol()).capitalize()
    piece_gender = piece_info.get("gender", "m")
    color_adj = get_color_adjective(piece.color, piece_gender)
    return f"{piece_name} {color_adj}"


# La variante principale si descrive con la funzione di board_utils: qui
# ce n'era una seconda, che indentava con tabulazioni e spezzava le mosse.
format_pv_descriptively = board_utils.format_pv_descriptively


def read_diagonal(game_state, base_column, direction_right):
    base_column = base_column.lower()
    if base_column not in "abcdefgh":
        print(_("Colonna base non valida."))
        return
    file_index = ord(base_column) - ord("a")
    rank_index = 0
    report = []
    cols_dict = L10N.get("columns", {})
    base_descr = f"{cols_dict.get(base_column, base_column)} 1"
    while 0 <= file_index < 8 and 0 <= rank_index < 8:
        square = chess.square(file_index, rank_index)
        piece = game_state.board.piece_at(square)
        if piece:
            current_file = chr(ord("a") + file_index)
            descriptive_file = cols_dict.get(current_file, current_file)
            report.append(
                f"{descriptive_file} {rank_index + 1}: {extended_piece_description(piece)}"
            )
        rank_index += 1
        file_index = file_index + 1 if direction_right else file_index - 1
    dir_str = _("alto-destra") if direction_right else _("alto-sinistra")
    if report:
        stampa_elenco(
            report,
            intestazione=_("Diagonale da {base} verso {direction}:").format(
                base=base_descr, direction=dir_str
            ),
        )
    else:
        print(
            _(
                "Diagonale da {base} in direzione {direction} non contiene pezzi."
            ).format(base=base_descr, direction=dir_str)
        )


def read_rank(game_state, rank_number):
    try:
        rank_int = int(rank_number)
        if not (1 <= rank_int <= 8):
            raise ValueError
        rank_idx = rank_int - 1
    except ValueError:
        print(_("Traversa non valida."))
        return
    report = []
    cols_dict = L10N.get("columns", {})
    for file_idx in range(8):
        square = chess.square(file_idx, rank_idx)
        piece = game_state.board.piece_at(square)
        if piece:
            file_letter = chr(ord("a") + file_idx)
            descriptive_file = cols_dict.get(file_letter, file_letter)
            report.append(
                f"{descriptive_file} {rank_number}: {extended_piece_description(piece)}"
            )
    if report:
        stampa_elenco(
            report, intestazione=_("Traversa {rank}:").format(rank=rank_number)
        )
    else:
        print(_("La traversa {rank} e' vuota.").format(rank=rank_number))


def read_file(game_state, file_letter):
    file_letter = file_letter.lower()
    if file_letter not in "abcdefgh":
        print(_("Colonna non valida."))
        return
    report = []
    file_idx = ord(file_letter) - ord("a")
    cols_dict = L10N.get("columns", {})
    descriptive_file = cols_dict.get(file_letter, file_letter)
    for rank_idx in range(8):
        square = chess.square(file_idx, rank_idx)
        piece = game_state.board.piece_at(square)
        if piece:
            report.append(
                f"{descriptive_file} {rank_idx + 1}: {extended_piece_description(piece)}"
            )
    if report:
        stampa_elenco(
            report, intestazione=_("Colonna {file}:").format(file=descriptive_file)
        )
    else:
        print(_("La colonna {file} e' vuota.").format(file=descriptive_file))


# Sequenze sonore dell'esplorazione, raccolte qui una volta sola: prima
# erano ricopiate per intero in ognuno dei tre punti che gestivano questi
# comandi.
def _scala(pan_iniziale, pan_finale):
    """Arpeggio che scorre da un lato all'altro, per le diagonali."""
    note = ["c5", "d5", "e5", "f5", "g5", "a5", "b5", "c6"]
    passo = (pan_finale - pan_iniziale) / (len(note) - 1)
    sequenza = []
    for indice, nota in enumerate(note):
        sequenza += [nota, 0.07, pan_iniziale + passo * indice, config.VOLUME]
    return sequenza


def _colonna_sonora():
    """Arpeggio fermo al centro, per le colonne."""
    sequenza = []
    for nota in ["c5", "d5", "e5", "f5", "g5", "a5", "b5", "c6"]:
        sequenza += [nota, 0.07, 0, config.VOLUME]
    return sequenza


def _traversa_sonora():
    """Stessa nota che attraversa lo stereo, per le traverse."""
    sequenza = []
    for indice in range(8):
        sequenza += ["g5", 0.07, -1 + indice * 0.25, config.VOLUME]
    return sequenza


def esplora_scacchiera(comando, game_state):
    """Esegue i comandi di esplorazione della scacchiera.

    Restituisce vero se il comando e' stato riconosciuto. Prima questo blocco
    era ricopiato in tre file, arbitraggio, Orolichess e partita su Lichess,
    per circa seicento righe complessive: ogni correzione andava fatta tre
    volte e le tre copie erano gia' divergenti.
    """
    if comando.startswith("/"):
        Acusticator(_scala(-1, 0.75), kind=3, adsr=[0, 0, 100, 100])
        read_diagonal(game_state, comando[1:2].strip(), True)
        return True

    if comando.startswith("\\"):
        Acusticator(_scala(1, -0.75), kind=3, adsr=[0, 0, 100, 100])
        read_diagonal(game_state, comando[1:2].strip(), False)
        return True

    if comando == "+":
        Acusticator(["c4", 0.07, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        report_all_pieces(game_state, chess.BLACK)
        return True

    if comando.startswith(","):
        Acusticator(
            [
                "a3",
                0.06,
                -1,
                config.VOLUME,
                "c4",
                0.06,
                -0.5,
                config.VOLUME,
                "d#4",
                0.06,
                0.5,
                config.VOLUME,
                "f4",
                0.06,
                1,
                config.VOLUME,
            ],
            kind=3,
            adsr=[20, 5, 70, 25],
        )
        report_piece_positions(game_state, comando[1:2])
        return True

    if comando.startswith("-"):
        parametro = comando[1:].strip()
        if not parametro:
            Acusticator(["c5", 0.07, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            report_all_pieces(game_state, chess.WHITE)
        elif len(parametro) == 1 and parametro.isalpha():
            Acusticator(_colonna_sonora(), kind=3, adsr=[0, 0, 100, 100])
            read_file(game_state, parametro)
        elif len(parametro) == 1 and parametro.isdigit():
            traversa = int(parametro)
            if 1 <= traversa <= 8:
                Acusticator(_traversa_sonora(), kind=3, adsr=[0, 0, 100, 100])
                read_rank(game_state, traversa)
            else:
                print(_("Traversa non valida: usa un numero da 1 a 8."))
        elif len(parametro) == 2 and parametro[0].isalpha() and parametro[1].isdigit():
            Acusticator(["d#4", 0.7, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            read_square(game_state, parametro)
        else:
            print(_("Dopo il meno serve una colonna, una traversa o una casa."))
        return True

    return False


def _get_piece_descriptions_from_squareset(board, squareset):
    descriptions = []
    for sq in squareset:
        piece = board.piece_at(sq)
        if piece:
            piece_desc = extended_piece_description(piece)
            sq_name = chess.square_name(sq)
            col_name = L10N["columns"].get(sq_name[0].lower(), sq_name[0])
            rank_name = sq_name[1]
            descriptions.append(
                _("{piece_desc} in {col_name} {rank_name}").format(
                    piece_desc=piece_desc, col_name=col_name, rank_name=rank_name
                )
            )
    return descriptions


def read_square(game_state, square_str):
    try:
        square = chess.parse_square(square_str)
    except Exception:
        print(_("Casa non valida."))
        return
    color_descr = (
        _("scura")
        if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0
        else _("chiara")
    )
    piece = game_state.board.piece_at(square)
    final_parts = []
    if piece:
        base_msg = _("La casa {square} e' {color} e contiene {piece_desc}.").format(
            square=square_str.upper(),
            color=color_descr,
            piece_desc=extended_piece_description(piece),
        )
        final_parts.append(base_msg)
        defenders_squares = game_state.board.attackers(piece.color, square)
        if defenders_squares:
            defender_descs = _get_piece_descriptions_from_squareset(
                game_state.board, defenders_squares
            )
            final_parts.append(
                _("difesa da: {defenders}").format(defenders=", ".join(defender_descs))
            )
        attackers_squares = game_state.board.attackers(not piece.color, square)
        if attackers_squares:
            attacker_descs = _get_piece_descriptions_from_squareset(
                game_state.board, attackers_squares
            )
            final_parts.append(
                _("attaccata da: {attackers}").format(
                    attackers=", ".join(attacker_descs)
                )
            )
    else:
        base_msg = _("La casa {square} e' {color} e risulta vuota.").format(
            square=square_str.upper(), color=color_descr
        )
        final_parts.append(base_msg)
        white_attackers_squares = game_state.board.attackers(chess.WHITE, square)
        if white_attackers_squares:
            attacker_descs = _get_piece_descriptions_from_squareset(
                game_state.board, white_attackers_squares
            )
            final_parts.append(
                _("attaccata dal Bianco con: {attackers}").format(
                    attackers=", ".join(attacker_descs)
                )
            )
        black_attackers_squares = game_state.board.attackers(chess.BLACK, square)
        if black_attackers_squares:
            attacker_descs = _get_piece_descriptions_from_squareset(
                game_state.board, black_attackers_squares
            )
            final_parts.append(
                _("attaccata dal Nero con: {attackers}").format(
                    attackers=", ".join(attacker_descs)
                )
            )
    print(" ".join(final_parts).replace(" .", ".").strip() + ".")


def report_piece_positions(game_state, piece_symbol):
    try:
        piece = chess.Piece.from_symbol(piece_symbol)
    except Exception:
        print(_("Non riconosciuto: inserisci R N B Q K P, r n b q k p"))
        return
    piece_type_key = chess.PIECE_NAMES[piece.piece_type].lower()
    full_name = L10N["pieces"][piece_type_key]["name"]
    gender = L10N["pieces"][piece_type_key]["gender"]
    color_string = get_color_adjective(piece.color, gender)
    squares = game_state.board.pieces(piece.piece_type, piece.color)
    positions = []
    for square in squares:
        file_index = chess.square_file(square)
        rank = chess.square_rank(square) + 1
        file_letter = chr(ord("a") + file_index)
        descriptive_file = L10N["columns"].get(file_letter, file_letter)
        positions.append(f"{descriptive_file} {rank}")
    if positions:
        stampa_elenco(
            positions,
            intestazione=_("{name} {color} in:").format(
                name=full_name.capitalize(), color=color_string
            ),
        )
    else:
        print(
            _("Nessun {name} {color} trovato.").format(
                name=full_name, color=color_string
            )
        )


def _report_tempo(game_state, bianco):
    """Annuncia il tempo che resta a un giocatore e quanto ne ha speso."""
    fase = game_state.white_phase if bianco else game_state.black_phase
    campo = "white_time" if bianco else "black_time"
    iniziale = game_state.clock_config["phases"][fase][campo]
    residuo = game_state.white_remaining if bianco else game_state.black_remaining
    speso = iniziale - residuo
    percentuale = (speso / iniziale * 100) if iniziale > 0 else 0
    etichetta = _("Tempo bianco: ") if bianco else _("Tempo nero: ")
    print(
        etichetta
        + tempo.parlato(residuo)
        + _(", consumato il {p:.0f} per cento").format(p=percentuale)
    )


def report_white_time(game_state):
    _report_tempo(game_state, True)


def report_black_time(game_state):
    _report_tempo(game_state, False)


def comandi_orologio(comando, game_state):
    """Comandi che riguardano solo gli orologi, uguali in partita e in Tempo.

    Sono i tempi dei due giocatori, il confronto e le correzioni manuali in
    pausa. Restituisce vero se il comando e' stato riconosciuto: prima questo
    blocco viveva in due copie, nell'arbitraggio e nella modalita' Tempo.
    """
    if comando == ".1":
        Acusticator(["a6", 0.14, -1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        report_white_time(game_state)
        return True

    if comando == ".2":
        Acusticator(["b6", 0.14, 1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        report_black_time(game_state)
        return True

    if comando == ".3":
        Acusticator(["e7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        report_white_time(game_state)
        report_black_time(game_state)
        return True

    if comando == ".4":
        Acusticator(["f7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        differenza = abs(game_state.white_remaining - game_state.black_remaining)
        if differenza < 1:
            print(_("I due orologi sono pari."))
            return True
        avanti = (
            _("Il bianco")
            if game_state.white_remaining > game_state.black_remaining
            else _("Il nero")
        )
        print(
            _("{chi} e' in vantaggio di {quanto}").format(
                chi=avanti, quanto=tempo.parlato(differenza)
            )
        )
        return True

    if comando.startswith((".b+", ".b-", ".n+", ".n-")):
        if not game_state.paused:
            print(
                _("Le correzioni di tempo si fanno in pausa, con il comando punto p.")
            )
            return True
        secondi = tempo.da_testo(comando[3:].strip())
        if secondi is None:
            print(_("Dopo il comando serve un tempo, per esempio punto b piu' 30."))
            return True
        bianco = comando[1] == "b"
        segno = 1 if comando[2] == "+" else -1
        nuovo = orologio.aggiungi(game_state, bianco, segno * secondi)
        chi = _("Il bianco") if bianco else _("Il nero")
        if segno > 0:
            Acusticator(["c6", 0.12, 0, config.VOLUME], kind=1)
            print(
                _("{chi} ha ricevuto {quanto}, ora ha {totale}").format(
                    chi=chi, quanto=tempo.parlato(secondi), totale=tempo.parlato(nuovo)
                )
            )
        else:
            Acusticator(["c4", 0.12, 0, config.VOLUME], kind=1)
            print(
                _("{chi} ha perso {quanto}, ora ha {totale}").format(
                    chi=chi, quanto=tempo.parlato(secondi), totale=tempo.parlato(nuovo)
                )
            )
        return True

    return False


def save_text_summary(game_state, descriptive_moves, eco_entry):
    headers = game_state.pgn_game.headers
    header_text = _("Riepilogo Partita di Orologic\n")
    header_text += _("Evento: {event}\n").format(event=headers.get("Event", _("N/D")))
    header_text += _("Sede: {site}\n").format(site=headers.get("Site", _("N/D")))
    header_text += _("Data: {date}\n").format(date=headers.get("Date", _("N/D")))
    header_text += _("Round: {round}\n").format(round=headers.get("Round", _("N/D")))
    header_text += _("Bianco: {white} ({elo})\n").format(
        white=headers.get("White", _("N/D")), elo=headers.get("WhiteElo", _("N/A"))
    )
    header_text += _("Nero: {black} ({elo})\n").format(
        black=headers.get("Black", _("N/D")), elo=headers.get("BlackElo", _("N/A"))
    )
    header_text += _("Tempo finale Bianco: {clock}\n").format(
        clock=headers.get("WhiteClock", _("N/D"))
    )
    header_text += _("Tempo finale Nero: {clock}\n").format(
        clock=headers.get("BlackClock", _("N/D"))
    )
    header_text += _("Controllo del Tempo: {tc}\n").format(
        tc=headers.get("TimeControl", _("N/D"))
    )
    opening_text = (
        _("Apertura: {eco} - {opening}").format(
            eco=eco_entry.get("eco", ""), opening=eco_entry.get("opening", "")
        )
        if eco_entry
        else _("Apertura: non rilevata\n")
    )
    if eco_entry and eco_entry.get("variation"):
        opening_text += " ({variation})\n".format(variation=eco_entry.get("variation"))
    header_text += opening_text
    move_list_text = _("Lista Mosse:\n")
    for num, i in enumerate(range(0, len(descriptive_moves), 2), 1):
        white = descriptive_moves[i]
        black = descriptive_moves[i + 1] if i + 1 < len(descriptive_moves) else ""
        move_list_text += f"{num}. {white}" + (f", {black}\n" if black else "\n")
    footer_text = _("\nRisultato finale: {result}\n").format(
        result=headers.get("Result", "*")
    )
    footer_text += _("File generato il: {datetime}\n").format(
        datetime=config.format_date_italian()
    )
    footer_text += _("Report generato da Orologic V{version} - {programmer}\n").format(
        version=version.VERSION, programmer=version.PROGRAMMER
    )
    full_text = header_text + move_list_text + footer_text
    base_filename = (
        config.sanitize_filename(
            "{white}-{black}-{result}-{timestamp}".format(
                white=headers.get("White", _("Bianco")),
                black=headers.get("Black", _("Nero")),
                result=headers.get("Result", "*"),
                timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            )
        )
        + ".txt"
    )
    full_path = config.percorso_salvataggio(os.path.join("txt", base_filename))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(
            _("Riepilogo partita salvato come {filename}.").format(filename=full_path)
        )
    except Exception as e:
        print(
            _("Errore durante il salvataggio del riepilogo testuale: {error}").format(
                error=e
            )
        )
        Acusticator(["a3", 1, 0, config.VOLUME], kind=2, adsr=[0, 0, 100, 100])


def setup_fischer_random_board():
    """Wrapper per compatibilità: delega a chess960_utils e restituisce (board, fen)."""
    from . import chess960_utils

    board, fen, _pos = chess960_utils.setup_fischer_random_board_interactive()
    return board, fen


GenerateMoveSummary = board_utils.GenerateMoveSummary


def verbose_legal_moves_for_san(board, san_str):
    if san_str in ["O-O", "0-0", "O-O-O", "0-0-0"]:
        legal_moves = [m for m in board.legal_moves if board.is_castling(m)]
    else:
        s = san_str.replace("+", "").replace("#", "").strip()
        promotion = None
        if "=" in s:
            parts = s.split("=")
            s = parts[0]
            promo_char = parts[1].strip().upper()
            promotion = {
                "Q": chess.QUEEN,
                "R": chess.ROOK,
                "B": chess.BISHOP,
                "N": chess.KNIGHT,
            }.get(promo_char)
        try:
            dest_square = chess.parse_square(s[-2:])
            legal_moves = [
                m
                for m in board.legal_moves
                if m.to_square == dest_square
                and (m.promotion == promotion if promotion else True)
            ]
        except Exception:
            return _("Destinazione non riconosciuta.")
    if not legal_moves:
        return _("Nessuna mossa legale trovata.")
    return "\n".join(
        [
            _("{i}. {desc}").format(
                i=i + 1, desc=board_utils.DescribeMove(m, board.copy())
            )
            for i, m in enumerate(legal_moves)
        ]
    )


def Impostazioni():
    from . import engine

    # Il database si carica qui e si salva in coda: durante le domande nulla
    # altro puo' scriverlo, quindi la copia in memoria resta quella buona.
    db = storage.LoadDB()
    print(_("\nModifica impostazioni varie di Orologic\n"))
    autosave_enabled = db.get("autosave_enabled", False)
    if (
        key(
            _("Salvataggio automatico: [{status}]. Premi Invio per cambiare: ").format(
                status=_("Attivo") if autosave_enabled else _("Non attivo")
            )
        ).strip()
        == ""
    ):
        db["autosave_enabled"] = not autosave_enabled
    menu_numerati = db.get("menu_numerati", False)
    if (
        key(
            _("Stile menu: [{status}]. Premi Invio per cambiare: ").format(
                status=_("Numeri") if menu_numerati else _("Parole")
            )
        ).strip()
        == ""
    ):
        db["menu_numerati"] = not menu_numerati

    # Impostazioni Analisi Default
    cur_time = db.get("default_analysis_time", 1.0)
    new_time = dgt(
        _("Tempo analisi default (sec) [{cur}]: ").format(cur=cur_time),
        kind="f",
        fmin=0.1,
        fmax=300,
        default=cur_time,
    )
    Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])
    if new_time != cur_time:
        db["default_analysis_time"] = new_time
        engine.SetAnalysisTime(new_time)

    cur_pv = db.get("default_multipv", 3)
    new_pv = dgt(
        _("Linee analisi default (multipv) [{cur}]: ").format(cur=cur_pv),
        kind="i",
        imin=1,
        imax=20,
        default=cur_pv,
    )
    Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])
    if new_pv != cur_pv:
        db["default_multipv"] = new_pv
        engine.SetMultipv(new_pv)

    # Impostazioni Soglie Analisi
    thresholds = db.get(
        "analysis_thresholds", {"inesattezza": 50, "errore": 100, "svarione": 250}
    )
    print(
        _(
            "\nSoglie Analisi Attuali: Inesattezza {i}cp, Errore {e}cp, Svarione {s}cp"
        ).format(
            i=thresholds["inesattezza"],
            e=thresholds["errore"],
            s=thresholds["svarione"],
        )
    )
    if enter_escape(
        _(
            "Vuoi modificare le soglie di analisi? (INVIO per modificare, ESC per mantenere): "
        )
    ):
        print(_("Inserisci le nuove soglie in centipawn (cp)."))
        t_ines = dgt(
            _("Soglia Inesattezza [{cur}]: ").format(cur=thresholds["inesattezza"]),
            kind="i",
            imin=10,
            imax=200,
            default=thresholds["inesattezza"],
        )
        t_err = dgt(
            _("Soglia Errore [{cur}]: ").format(cur=thresholds["errore"]),
            kind="i",
            imin=t_ines + 1,
            imax=500,
            default=thresholds["errore"],
        )
        t_svar = dgt(
            _("Soglia Svarione [{cur}]: ").format(cur=thresholds["svarione"]),
            kind="i",
            imin=t_err + 1,
            imax=2000,
            default=thresholds["svarione"],
        )

        db["analysis_thresholds"] = {
            "inesattezza": t_ines,
            "errore": t_err,
            "svarione": t_svar,
        }
        print(_("Soglie analisi aggiornate."))
        Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])

    storage.SaveDB(db)
    print(_("Impostazioni aggiornate"))
