# Orologic, Easyfish: editor della scacchiera ed esplorazione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import chess
import chess.engine
from GBUtils import dgt, enter_escape, key, menu

from .. import cruscotto, strato
from .. import engine as orologic_engine
from ..board_utils import CustomBoard, DescribeMove
from ..config import _
from . import analysis_utils, posizione
from .constants import MNEDITOR, MNEXPLORER
from .utils import InsertedCounter, suona_annulla


def errori_della_posizione(board):
    """Perche' la posizione non e' legale, una riga per motivo: l'editor
    a comandi del terminale e quello della finestra."""
    status = board.status()
    voci = (
        (chess.STATUS_NO_WHITE_KING, _("- Manca il Re bianco.")),
        (chess.STATUS_NO_BLACK_KING, _("- Manca il Re nero.")),
        (chess.STATUS_TOO_MANY_KINGS, _("- Troppi Re sulla scacchiera.")),
        (chess.STATUS_TOO_MANY_WHITE_PIECES, _("- Troppi pezzi bianchi.")),
        (chess.STATUS_TOO_MANY_BLACK_PIECES, _("- Troppi pezzi neri.")),
        (chess.STATUS_TOO_MANY_WHITE_PAWNS, _("- Troppi pedoni bianchi.")),
        (chess.STATUS_TOO_MANY_BLACK_PAWNS, _("- Troppi pedoni neri.")),
        (chess.STATUS_PAWNS_ON_BACKRANK, _("- Pedoni in prima o ottava traversa.")),
        (chess.STATUS_OPPOSITE_CHECK, _("- Il giocatore che non ha il turno è sotto scacco.")),
        (chess.STATUS_TOO_MANY_CHECKERS, _("- Troppi scacchi simultanei.")),
        (chess.STATUS_IMPOSSIBLE_CHECK, _("- Posizione di scacco impossibile.")),
        (chess.STATUS_BAD_CASTLING_RIGHTS, _("- Diritti di arrocco non validi.")),
        (chess.STATUS_INVALID_EP_SQUARE, _("- Casa en passant non valida.")),
    )
    return [testo for bandiera, testo in voci if status & bandiera]


def BoardEditor(starting_fen=None, sharing_window=None):
    """Editor della scacchiera con gestione intelligente dei Re e menu a comandi.
    Se starting_fen è fornito, l'editor inizia da quella posizione.
    """

    tmp_board = CustomBoard()
    if starting_fen:
        try:
            tmp_board.set_fen(starting_fen)
            print(_("\nEditor avviato dalla posizione corrente."))
        except ValueError:
            print(_("\nErrore FEN posizione iniziale, reset scacchiera."))
            tmp_board.clear()
            tmp_board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
            tmp_board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    else:
        print(_("\nEditor avviato con scacchiera standard."))
        tmp_board.clear()
        # Inserimento Re di default
        tmp_board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        tmp_board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))

    print(
        _(
            "Comandi principali: Pe4 per piazzare, e4 per svuotare, .v per svuotare tutto, .i per posizione iniziale, .? per menu."
        )
    )

    while True:
        if sharing_window and sharing_window.is_active():
            sharing_window.update_board(tmp_board)
        prompt = InsertedCounter(tmp_board)
        wherewho = dgt(prompt=prompt, kind="s", smin=1, smax=100).strip()

        # Gestione Comandi
        if wherewho.startswith("."):
            if wherewho == ".v":
                tmp_board.clear()
                tmp_board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
                tmp_board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
                print(_("Scacchiera svuotata. Re posizionati in case di partenza."))
                continue

            elif wherewho == ".i":
                tmp_board.reset()
                print(_("Scacchiera reimpostata alla posizione iniziale standard."))
                continue

            elif wherewho == ".":
                if tmp_board.is_valid():
                    break
                else:
                    print(_("Posizione illegale:"))
                    for riga in errori_della_posizione(tmp_board):
                        print(riga)
                    print(
                        _(
                            "\nCorreggi la posizione per poter uscire o usa '.i' / '.v' per resettare."
                        )
                    )
                    continue

            elif wherewho == ".?":
                menu(d=MNEDITOR, show_only=True)
                continue

            elif wherewho == ".s":
                print("\n" + str(tmp_board))
                continue

            elif wherewho == ".t":
                tmp_board.turn = not tmp_board.turn
                color = _("Bianco") if tmp_board.turn == chess.WHITE else _("Nero")
                print(_("Turno impostato al: {c}").format(c=color))

            elif wherewho == ".c" or wherewho.startswith(".c "):
                if wherewho.startswith(".c "):
                    rights = wherewho[3:].strip()
                else:
                    rights = dgt(
                        prompt=_("Modifica diritti arrocco (es. KQkq o -): "),
                        kind="s",
                        default="",
                    ).strip()

                if not rights:
                    continue

                if rights == "-":
                    tmp_board.castling_rights = 0
                    print(_("Tutti i diritti di arrocco sono stati rimossi."))
                else:
                    invalid_chars = [c for c in rights if c not in "KQkq"]
                    if invalid_chars:
                        print(_("Formato non valido. Usa combinazioni di KQkq o -."))
                    else:
                        feedback = []
                        for char in rights:
                            if char == "K":
                                tmp_board.castling_rights ^= chess.BB_H1
                                has_it = bool(tmp_board.castling_rights & chess.BB_H1)
                                status = _("attivo") if has_it else _("disattivato")
                                feedback.append(
                                    _("Arrocco corto Bianco (K): {status}").format(
                                        status=status
                                    )
                                )
                            elif char == "Q":
                                tmp_board.castling_rights ^= chess.BB_A1
                                has_it = bool(tmp_board.castling_rights & chess.BB_A1)
                                status = _("attivo") if has_it else _("disattivato")
                                feedback.append(
                                    _("Arrocco lungo Bianco (Q): {status}").format(
                                        status=status
                                    )
                                )
                            elif char == "k":
                                tmp_board.castling_rights ^= chess.BB_H8
                                has_it = bool(tmp_board.castling_rights & chess.BB_H8)
                                status = _("attivo") if has_it else _("disattivato")
                                feedback.append(
                                    _("Arrocco corto Nero (k): {status}").format(
                                        status=status
                                    )
                                )
                            elif char == "q":
                                tmp_board.castling_rights ^= chess.BB_A8
                                has_it = bool(tmp_board.castling_rights & chess.BB_A8)
                                status = _("attivo") if has_it else _("disattivato")
                                feedback.append(
                                    _("Arrocco lungo Nero (q): {status}").format(
                                        status=status
                                    )
                                )

                        print("\n".join(feedback))

            elif wherewho == ".e":
                sq_str = dgt(
                    prompt=_("Casa en passant (es. e3 o invio): "), kind="s", default=""
                ).strip()
                if not sq_str:
                    tmp_board.ep_square = None
                else:
                    try:
                        tmp_board.ep_square = chess.parse_square(sq_str.lower())
                        print(_("Casa en passant impostata."))
                    except ValueError:
                        print(_("Casa non valida."))

            elif wherewho == ".n":
                n = dgt(
                    prompt=_("Numero mossa: "),
                    kind="i",
                    imin=1,
                    imax=500,
                    default=tmp_board.fullmove_number,
                )
                tmp_board.fullmove_number = n

            elif wherewho == ".h":
                h = dgt(
                    prompt=_("Orologio semimosse (halfmove): "),
                    kind="i",
                    imin=0,
                    imax=100,
                    default=tmp_board.halfmove_clock,
                )
                tmp_board.halfmove_clock = h

            continue
        # Gestione Inserimento Pezzi / Svuotamento Case
        try:
            parts = [p.strip() for p in wherewho.split(",")]
            if not parts or parts[0] == "":
                print(_("Input non riconosciuto."))
                continue

            first_part = parts[0]
            if len(first_part) == 2:
                piece_name = None
                first_square_str = first_part.lower()
            elif len(first_part) == 3:
                piece_name = first_part[0]
                first_square_str = first_part[1:].lower()
            else:
                print(_("Formato non valido. Usa Pe4 o e4 o Pe4,f4."))
                continue

            # Se ci sono più parti, e il pezzo è un Re (K o k), non è consentito
            if len(parts) > 1 and piece_name and piece_name.upper() == "K":
                print(
                    _(
                        "I Re sono unici, non puoi specificare più case contemporaneamente."
                    )
                )
                continue

            squares_to_process = []
            squares_to_process.append((first_square_str, piece_name))

            valid = True
            for part in parts[1:]:
                part = part.lower()
                if len(part) != 2:
                    print(_("Formato casa '{part}' non valido.").format(part=part))
                    valid = False
                    break
                squares_to_process.append((part, piece_name))

            if not valid:
                continue

            for sq_str, p_name in squares_to_process:
                square = chess.parse_square(sq_str)
                existing_piece = tmp_board.piece_at(square)

                if p_name is None:
                    if existing_piece and existing_piece.piece_type == chess.KING:
                        print(_("Non puoi rimuovere il Re. Spostalo usando Ke4 o ke4."))
                    else:
                        tmp_board.remove_piece_at(square)
                elif p_name.upper() == "K":
                    color = chess.WHITE if p_name.isupper() else chess.BLACK
                    old_sq = tmp_board.king(color)
                    if old_sq is not None:
                        tmp_board.remove_piece_at(old_sq)
                    tmp_board.set_piece_at(square, chess.Piece(chess.KING, color))
                elif existing_piece and existing_piece.piece_type == chess.KING:
                    print(
                        _("Casa occupata dal Re. Sposta prima il Re in {sq}.").format(
                            sq=sq_str
                        )
                    )
                else:
                    color = chess.WHITE if p_name.isupper() else chess.BLACK
                    p_type = chess.PIECE_SYMBOLS.index(p_name.lower())
                    tmp_board.set_piece_at(square, chess.Piece(p_type, color))

        except (ValueError, IndexError):
            print(_("Input non riconosciuto."))

    print(_("Editing completato.") + "\n" + str(tmp_board))
    return tmp_board.fen()


def ExplorerMode(game, engine, analysis_time_default=2, sharing_window=None, nodo=None):
    """Modalità esplorazione per navigare nella partita, dalla mossa nodo,
    o dall'inizio. Nella finestra l'area e' il cruscotto, e la scacchiera
    interattiva manda i comandi con Alt davanti."""
    node = game if nodo is None else nodo
    stato = posizione.Stato("esploratore")
    # Il commento si dice quando si arriva sulla mossa, non a ogni tasto.
    commentato = None
    # Fondamentale: usiamo la scacchiera del PGN come base per la sincronizzazione
    initial_board = game.board()
    analysis_time = analysis_time_default
    local_multipv = orologic_engine.multipv
    var_index = 0

    def SyncBoardToNode(node):
        board = initial_board.copy()
        # La posizione si ricostruisce risalendo i nodi fino alla radice.
        move_stack = []
        temp = node
        while temp.parent:
            move_stack.append(temp.move)
            temp = temp.parent
        move_stack.reverse()
        for move in move_stack:
            if move:
                board.push(move)
        return board

    current_board = SyncBoardToNode(node)
    is_modified = False

    while True:
        if sharing_window and sharing_window.is_active():
            sharing_window.update_board(current_board, node)
        variant_count = len(node.variations)
        if var_index >= variant_count:
            var_index = 0

        if node.comment and node is not commentato:
            print(node.comment)
        commentato = node

        p_node = node.parent
        if p_node and p_node.move:
            b_parent = p_node.parent.board()
            if b_parent.turn == chess.WHITE:
                parent_str = f"{b_parent.fullmove_number}. {p_node.san()}"
            else:
                parent_str = f"{b_parent.fullmove_number}...{p_node.san()}"
        else:
            parent_str = ""

        if node.move:
            b_curr = node.parent.board()
            if b_curr.turn == chess.WHITE:
                current_str = f"{b_curr.fullmove_number}. {node.san()}"
            elif p_node and p_node.move and p_node.parent.board().turn == chess.WHITE:
                current_str = f"{node.san()}"
            else:
                current_str = f"{b_curr.fullmove_number}...{node.san()}"
        else:
            current_str = _("inizio")

        if variant_count > 0:
            v_node = node.variations[var_index]
            b_next = current_board
            if b_next.turn == chess.WHITE:
                next_str = f"{b_next.fullmove_number}. {v_node.san()}"
            elif node.move and node.parent.board().turn == chess.WHITE:
                next_str = f"{v_node.san()}"
            else:
                next_str = f"{b_next.fullmove_number}...{v_node.san()}"
        else:
            next_str = game.headers.get("Result", _("fine"))

        level = 0
        temp_node = node
        while temp_node.parent:
            if temp_node.parent.variations[0] != temp_node:
                level += 1
            temp_node = temp_node.parent

        prompt = f"\nLvl{level}"
        if parent_str:
            prompt += f" {parent_str}"
        prompt += f" ({current_str}) {next_str}"
        if variant_count > 1:
            prompt += f" [V{var_index + 1}/{variant_count}]"

        stato.aggiorna(game, current_board, node, var_index)
        strato.fornisci(lambda: cruscotto.dati_di(stato), MNEXPLORER)
        with strato.prompt_di_gioco():
            command = key(prompt=prompt)

        from ..lichess_board import handle_exploration_command

        if handle_exploration_command(command, current_board):
            continue

        if command == "a":
            if node.parent:
                node = node.parent
                current_board = SyncBoardToNode(node)
                var_index = 0
            else:
                print(_("Nessuna mossa precedente"))
        elif command == "?":
            with strato.da_leggere(_("Comandi dell'esploratore")):
                menu(d=MNEXPLORER, show_only=True, pager=0 if strato.con_la_plancia() else 20)
        elif command == "d":
            if variant_count > 0:
                node = node.variations[var_index]
                # Ottimizzazione: invece di ricalcolare tutto, pushiamo solo se sincronizzati
                # Ma per sicurezza usiamo sync
                current_board = SyncBoardToNode(node)
                var_index = 0
            else:
                print(_("fine della partita"))
        elif command == "x":  # Next Variant
            if variant_count > 1:
                var_index = (var_index + 1) % variant_count
                print(_("Variante {n}: {mossa}").format(n=var_index + 1, mossa=node.variations[var_index].san()))
            else:
                print(_("Nessuna variante alternativa."))
        elif command == "w":  # Prev Variant
            if variant_count > 1:
                var_index = (var_index - 1 + variant_count) % variant_count
                print(_("Variante {n}: {mossa}").format(n=var_index + 1, mossa=node.variations[var_index].san()))
            else:
                print(_("Nessuna variante alternativa."))
        elif command == "q":
            node = game
            current_board = SyncBoardToNode(node)
            var_index = 0
        elif command == "e":
            while node.variations:
                node = node.variations[0]
                current_board.push(node.move)
            var_index = 0
        elif command == "z":
            temp_node = node
            while temp_node.parent and temp_node.parent.variations[0] == temp_node:
                temp_node = temp_node.parent
            if temp_node.parent:
                parent_node = temp_node.parent
                var_index = parent_node.variations.index(temp_node)
                node = parent_node
                current_board = SyncBoardToNode(node)
        elif command == "b":
            current_board = SyncBoardToNode(node)
            cb = CustomBoard()
            cb.set_fen(current_board.fen())
            with strato.da_leggere(_("Scacchiera")):
                print(cb)
        elif command == "u":
            # Taglia la mossa col suo seguito: con un seguito si chiede, come
            # .u del menu, perche' si perde di piu'; prima tagliava e basta.
            seguito = posizione.semimosse_dopo(node)
            if node.parent and seguito and not enter_escape(posizione.domanda_del_taglio(seguito)):
                continue
            if node.parent:
                parent = node.parent
                if node in parent.variations:
                    parent.variations.remove(node)
                    node = parent
                    current_board = SyncBoardToNode(node)
                    is_modified = True
                    suona_annulla()
                    print(_("Mossa/Variante eliminata. Tornati indietro."))
                    var_index = 0
                else:
                    print(
                        _(
                            "Errore: Impossibile trovare la mossa nella lista varianti del padre."
                        )
                    )
            else:
                print(_("Impossibile eliminare l'inizio della partita."))
        elif command == "c":
            if node.comment:
                print(node.comment)
        elif command == "s":
            current_board = SyncBoardToNode(node)
            print(_("Analisi in corso..."))
            if engine:
                with strato.da_leggere(_("Analisi")):
                    for riga in analysis_utils.analizza(current_board, engine, analysis_time, local_multipv)[1]:
                        print(riga)
            else:
                print(_("Motore non disponibile."))
        elif command == "r":
            # Nel prompt di gioco: la scacchiera manda r e i secondi insieme.
            with strato.prompt_di_gioco():
                analysis_time = dgt(
                    prompt=_("Secondi analisi: "),
                    kind="i",
                    imin=1,
                    imax=1800,
                    default=analysis_time,
                )
        elif command == "t":
            with strato.prompt_di_gioco():
                local_multipv = dgt(
                    prompt=_("Linee analisi: "),
                    kind="i",
                    imin=1,
                    imax=20,
                    default=local_multipv,
                )
            print(_("Linee impostate a {n}").format(n=local_multipv))
        elif command == "i":
            # Una mossa nella partita o nella variante: dalla scacchiera, con
            # Invio; nel terminale si scrive. Se c'e' gia', ci si va.
            with strato.prompt_di_gioco():
                testo = dgt(prompt=_("Mossa da aggiungere: "), kind="s", smin=0, smax=20, default="").strip()
            if not testo:
                continue
            mossa = posizione.leggi_la_mossa(current_board, testo)
            if mossa is None:
                colore = _("Bianco") if current_board.turn == chess.WHITE else _("Nero")
                print(_("{k}: mossa illegale per il {c}.").format(k=testo, c=colore))
                continue
            print(DescribeMove(mossa, current_board))
            esistente = next((variante for variante in node.variations if variante.move == mossa), None)
            if esistente is not None:
                node = esistente
            else:
                nuova_variante = bool(node.variations)
                node = node.add_variation(mossa)
                is_modified = True
                if nuova_variante:
                    print(_("Nuova variante creata."))
            current_board = SyncBoardToNode(node)
            var_index = 0
        elif command == "_":
            with strato.prompt_di_gioco():
                testo = dgt(prompt=_("Commento: "), kind="s", smin=0, smax=2000, default="")
            posizione.metti_il_testo(node, testo)
            is_modified = True
            print(_("Commento registrato."))
        elif command == ".":
            print()
            return is_modified, node
