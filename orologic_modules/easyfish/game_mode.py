# Orologic, Easyfish: la partita contro il motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import chess
import chess.engine
import chess.pgn

from GBUtils import Acusticator, dgt, enter_escape, menu

from .. import engine as orologic_engine
from .. import config, orologio, storage, tempo, ui
from ..board_utils import CustomBoard, DescribeMove, NormalizeMove
from ..config import _
from . import analysis_utils
from .constants import MNGAME


class EasyfishGameState:
    def __init__(self):
        self.white_remaining = 0.0
        self.black_remaining = 0.0
        self.white_inc = 0.0
        self.black_inc = 0.0
        self.active_color = chess.WHITE
        self.game_over = False
        self.flag_fallen = False
        self.paused = False
        self.human_color = None
        self.engine_has_clock = True
        self.ignore_clock = False


def ParseTimeInput(prompt_text):
    """Chiede tempo ed eventuale incremento, per esempio 20:00+15.

    La lettura della durata e' quella del modulo tempo: qui si aggiunge solo
    la parte dopo il piu', cioe' l'incremento in secondi.
    """
    while True:
        risposta = dgt(
            prompt=prompt_text + _(" (es. 01:15:00+10, 20:00+15 o 400+5): "), kind="s"
        ).strip()
        if not risposta:
            return None, None

        parte_tempo, _sep, parte_incremento = risposta.partition("+")
        incremento = 0
        if parte_incremento:
            try:
                incremento = int(parte_incremento.strip())
            except ValueError:
                print(_("L'incremento deve essere un numero di secondi."))
                continue

        secondi = tempo.da_testo(parte_tempo)
        if secondi is None:
            print(_("Tempo non riconosciuto: usa ore:minuti:secondi oppure i secondi."))
            continue
        return secondi, incremento


def _comandi_informativi(cmd, board, game_state, engine_instance):
    """Comandi che si limitano a riferire qualcosa.

    I comandi da punto uno a punto sei stanno in ui, uguali per tutte le
    modalita': qui restano materiale, scacchiera, elenco comandi e forza
    del motore. Restituisce vero se il comando e' stato riconosciuto.
    """
    if ui.comandi_orologio(cmd, game_state):
        return True
    if ui.comandi_lettura(cmd, game_state, board=board):
        return True
    elif cmd == ".a":
        lines = analysis_utils.get_lines_from_engine(
            board, engine_instance, orologic_engine.analysis_time, 1
        )
        for line in lines:
            print(line)
    elif cmd == ".?":
        menu(MNGAME, show_only=True)
    elif cmd.startswith(".s") and len(cmd) > 2 and cmd[2:].isdigit():
        try:
            new_skill = int(cmd[2:])
            if 0 <= new_skill <= 20:
                # Disattiva limitazione Elo per usare Skill Level
                try:
                    engine_instance.configure({"UCI_LimitStrength": False})
                except Exception:
                    pass
                engine_instance.configure({"Skill Level": new_skill})
                Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1)
                print(
                    _(
                        "Livello di forza del motore impostato a {n} (Skill Level)."
                    ).format(n=new_skill)
                )
            else:
                Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
                print(_("Il livello deve essere compreso tra 0 e 20."))
        except Exception as e:
            print(_("Errore durante l'impostazione del livello: {e}").format(e=e))
    else:
        return False
    return True


def _valuta_fine_partita(board, current_node, game_state):
    """Riconosce le posizioni che chiudono la partita.

    Matto, stallo e le patte riconosciute dalla libreria. Restituisce
    vero quando la partita e' finita, cosi' il ciclo si ferma.
    """
    if board.is_game_over(claim_draw=True):
        game_state.game_over = True
        if board.is_checkmate():
            res = "1-0" if board.turn == chess.BLACK else "0-1"
            if current_node.root():
                current_node.root().headers["Result"] = res
            print(_("Scacco matto!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_stalemate():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per stallo!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_insufficient_material():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per materiale insufficiente!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_seventyfive_moves() or board.can_claim_fifty_moves():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per la regola delle 50/75 mosse!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_fivefold_repetition() or board.can_claim_threefold_repetition():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per ripetizione della posizione!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        return True
    return False


def _partita_finita_dopo_la_mossa(board, current_node, game_state):
    """Controlla se la mossa appena giocata ha chiuso la partita.

    Matto, stallo, materiale insufficiente, settantacinque mosse e
    quintuplice ripetizione. Restituisce vero quando la partita e'
    finita: prima queste duecento righe stavano in due copie identiche,
    una dopo la mossa dell'umano e una dopo quella del motore.
    """
    if board.is_checkmate():
        game_state.game_over = True
        res = "1-0" if game_state.active_color == chess.BLACK else "0-1"
        if current_node.root():
            current_node.root().headers["Result"] = res
        print(_("Scacco matto!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_stalemate():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per stallo!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_insufficient_material():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per materiale insufficiente!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_seventyfive_moves():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per la regola delle 75 mosse!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_fivefold_repetition():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per ripetizione della posizione (5 volte)!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.can_claim_fifty_moves():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per la regola delle 50 mosse!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.can_claim_threefold_repetition():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per triplice ripetizione della posizione!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    return False


def StartEngineGame(game_node, engine_instance, sharing_window=None):
    """
    Avvia una partita contro il motore a partire dalla posizione corrente di game_node.
    Utilizza un thread separato per la gestione dell'orologio.
    """
    if sharing_window and sharing_window.is_active():
        sharing_window.update_board(game_node.board(), game_node)
    if not engine_instance:
        print(_("Motore non disponibile. Configuralo nelle impostazioni."))
        return game_node

    print(_("Nuova Partita contro il Motore"))

    engine_mode = menu(
        {
            "1": _("Partita a tempo"),
            "2": _("Tempo per mossa motore"),
            "3": _("Senza tempo (Amichevole)"),
        },
        p=_("Modalita' di gioco: "),
        numbered=True,
    )

    user_time = 0
    user_inc = 0
    engine_time = 0
    engine_inc = 0
    engine_limit_type = "game"
    engine_has_clock = True
    ignore_clock = False

    if engine_mode == "1":
        user_time, user_inc = ParseTimeInput(_("Tuo tempo partita"))
        if user_time is None:
            return game_node

        same_time = not enter_escape(
            _("Usare stesso tempo per il motore? (INVIO per no, ESC per si'): ")
        )
        if same_time:
            engine_time = user_time
            engine_inc = user_inc
        else:
            engine_time, engine_inc = ParseTimeInput(_("Tempo partita motore"))
            if engine_time is None:
                return game_node

    elif engine_mode == "2":
        ignore_clock = True
        engine_limit_type = "move"
        engine_has_clock = False
        engine_time = dgt(_("Secondi per mossa motore: "), kind="f", default=2.0)

    elif engine_mode == "3":
        ignore_clock = True
        engine_limit_type = "move"
        engine_has_clock = False
        engine_time = dgt(_("Secondi riflessione motore: "), kind="f", default=2.0)

    # Setup GameState
    game_state = EasyfishGameState()
    game_state.ignore_clock = ignore_clock
    board = game_node.board()
    game_state.active_color = board.turn
    game_state.engine_has_clock = engine_has_clock

    # Scelta del colore
    is_white = enter_escape(_("Vuoi giocare col bianco (INVIO) o col nero (ESCAPE)?: "))
    game_state.human_color = chess.WHITE if is_white else chess.BLACK

    if game_state.human_color == chess.WHITE:
        game_state.white_remaining = float(user_time)
        game_state.white_inc = float(user_inc)
        game_state.black_remaining = float(engine_time) if engine_has_clock else 0
        game_state.black_inc = float(engine_inc) if engine_has_clock else 0
        print(_("Giochi col BIANCO."))
    else:
        game_state.black_remaining = float(user_time)
        game_state.black_inc = float(user_inc)
        game_state.white_remaining = float(engine_time) if engine_has_clock else 0
        game_state.white_inc = float(engine_inc) if engine_has_clock else 0
        print(_("Giochi col NERO."))

    try:
        db = storage.LoadDB()
        current_skill = db.get("engine_config", {}).get("skill_level", 20)
        print(_("Livello forza motore (Skill Level): {s}").format(s=current_skill))

        # Forza attivazione WDL dal motore per l'analisi e gioco
        try:
            engine_instance.configure({"UCI_ShowWDL": True})
        except Exception:
            pass
    except Exception as e:
        print(_("Errore lettura skill level: {e}").format(e=e))

    # Avvio dell'orologio, lo stesso usato dall'arbitraggio.
    orologio.avvia(game_state)

    current_node = game_node

    try:
        while not game_state.game_over:
            # --- CONTROLLI FINE PARTITA ---
            if _valuta_fine_partita(board, current_node, game_state):
                break

            if game_state.flag_fallen:
                print(_("Tempo scaduto! Partita terminata."))
                game_state.game_over = True
                res = "0-1" if game_state.active_color == chess.WHITE else "1-0"
                if current_node.root():
                    current_node.root().headers["Result"] = res
                break

            move_num = board.fullmove_number
            last_move_san = current_node.san() if current_node.move else ""

            if not current_node.move:
                prompt = f"{move_num}. "
            elif board.turn == chess.WHITE:
                prompt = f"{move_num - 1}... {last_move_san} {move_num}. "
            else:
                prompt = f"{move_num}. {last_move_san} "

            # --- TURNO UMANO ---
            if board.turn == game_state.human_color:
                # Input
                move_input = dgt(prompt=prompt, kind="s")

                if game_state.flag_fallen:
                    continue
                if not move_input:
                    continue

                from ..lichess_board import handle_exploration_command

                if handle_exploration_command(move_input, board):
                    continue

                # Comandi
                if move_input.startswith("."):
                    cmd = move_input.lower()
                    if cmd == ".":
                        print(_("Hai abbandonato."))
                        game_state.game_over = True
                        # Assegna risultato (Umano perde)
                        res = "0-1" if game_state.human_color == chess.WHITE else "1-0"
                        if current_node.root():
                            current_node.root().headers["Result"] = res
                        break
                    elif _comandi_informativi(cmd, board, game_state, engine_instance):
                        pass
                    elif cmd == ".l":
                        # L'elenco si ricostruisce dal PGN, poi il riepilogo e' quello
                        # di tutte le altre modalita'.
                        mosse = []
                        node = current_node.root()
                        while node != current_node and node.variations:
                            mossa = node.variations[0].move
                            mosse.append(node.board().san(mossa))
                            node = node.variations[0]
                        ui.comandi_lettura(cmd, game_state, board=board, mosse=mosse)
                    elif cmd.startswith(".e"):
                        try:
                            elo_part = cmd[2:].strip()
                            if not elo_part.isdigit():
                                print(_("Formato non valido. Usa .e1200 o .e 1200."))
                                continue

                            new_elo = int(elo_part)
                            if "UCI_Elo" not in engine_instance.options:
                                print(
                                    _(
                                        "Il motore non supporta la configurazione diretta dell'Elo."
                                    )
                                )
                                continue

                            opt = engine_instance.options["UCI_Elo"]
                            try:
                                # Attiva limitazione Elo
                                engine_instance.configure({"UCI_LimitStrength": True})
                                engine_instance.configure({"UCI_Elo": new_elo})
                                Acusticator(["b5", 0.05, 0, config.VOLUME], kind=1)
                                print(
                                    _(
                                        "Forza del motore impostata a Rating Elo: {n}."
                                    ).format(n=new_elo)
                                )
                            except Exception:
                                msg = _("Valore Elo non accettato dal motore.")
                                if hasattr(opt, "min") and hasattr(opt, "max"):
                                    msg += _(
                                        " Range consentito per questo motore: {min}-{max}."
                                    ).format(min=opt.min, max=opt.max)
                                print(msg)
                        except Exception as e:
                            print(
                                _("Errore durante l'impostazione dell'Elo: {e}").format(
                                    e=e
                                )
                            )
                    elif cmd == ".v":
                        try:
                            res = orologic_engine.CalculateBest(
                                board, bestmove=False, as_san=False
                            )
                            if res and len(res) > 0:
                                var_node = current_node.add_variation(res[0])
                                var_node.add_line(res[1:])
                                print(_("Variante suggerita aggiunta all'albero."))
                            else:
                                print(_("Nessuna linea trovata."))
                        except Exception as e:
                            print(f"Err: {e}")
                    elif cmd == ".u":
                        steps = 0
                        temp_node = current_node
                        if temp_node.parent:
                            temp_node = temp_node.parent
                            steps += 1
                            if temp_node.parent:
                                temp_node = temp_node.parent
                                steps += 1

                        if steps > 0:
                            current_node = temp_node
                            board = current_node.board()
                            game_state.active_color = board.turn
                            if sharing_window and sharing_window.is_active():
                                sharing_window.update_board(board, current_node)
                            Acusticator(
                                [
                                    "c4",
                                    0.1,
                                    -1,
                                    config.VOLUME,
                                    "e4",
                                    0.1,
                                    0,
                                    config.VOLUME,
                                ],
                                kind=1,
                            )
                            print(
                                _("Annullate {n} semimosse. Tocca a te.").format(
                                    n=steps
                                )
                            )
                            print(CustomBoard(board.fen()))
                        else:
                            print(_("Impossibile annullare."))
                    continue

                # Mossa
                try:
                    move_san_norm = NormalizeMove(move_input)
                    move = board.parse_san(move_san_norm)
                    if move in board.legal_moves:
                        new_node = current_node.add_main_variation(move)
                        current_node = new_node
                        board.push(move)
                        if sharing_window and sharing_window.is_active():
                            sharing_window.update_board(board, current_node)

                        if game_state.human_color == chess.WHITE:
                            orologio.aggiungi(game_state, True, game_state.white_inc)
                        else:
                            orologio.aggiungi(game_state, False, game_state.black_inc)

                        game_state.active_color = board.turn
                        Acusticator([1000.0, 0.05, 0, config.VOLUME], kind=1)
                        print(DescribeMove(move, current_node.parent.board()))

                        # Controlli fine partita
                        if _partita_finita_dopo_la_mossa(
                            board, current_node, game_state
                        ):
                            break
                    else:
                        Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
                        print(_("Mossa illegale."))
                except ValueError:
                    Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
                    print(_("Input non valido."))

            # --- TURNO MOTORE ---
            else:
                limit = None
                if engine_limit_type == "game":
                    limit = chess.engine.Limit(
                        white_clock=game_state.white_remaining,
                        black_clock=game_state.black_remaining,
                        white_inc=game_state.white_inc,
                        black_inc=game_state.black_inc,
                    )
                elif engine_limit_type == "move":
                    limit = chess.engine.Limit(time=engine_time)
                else:
                    limit = chess.engine.Limit(time=engine_time)

                try:
                    result = engine_instance.play(board, limit)

                    if result.move:
                        if engine_has_clock:
                            if game_state.active_color == chess.WHITE:
                                orologio.aggiungi(
                                    game_state, True, game_state.white_inc
                                )
                            else:
                                orologio.aggiungi(
                                    game_state, False, game_state.black_inc
                                )

                        new_node = current_node.add_main_variation(result.move)
                        current_node = new_node
                        board.push(result.move)
                        if sharing_window and sharing_window.is_active():
                            sharing_window.update_board(board, current_node)

                        game_state.active_color = board.turn
                        Acusticator([1000.0, 0.05, 0, config.VOLUME], kind=1)
                        print(DescribeMove(result.move, current_node.parent.board()))

                        # Controlli fine partita
                        if _partita_finita_dopo_la_mossa(
                            board, current_node, game_state
                        ):
                            break
                    else:
                        print(_("Il motore abbandona o stallo."))
                        game_state.game_over = True
                        break

                except Exception as e:
                    print(_("Errore motore: {e}").format(e=e))
                    break

    except KeyboardInterrupt:
        print(_("\nPartita interrotta."))
    finally:
        game_state.game_over = True

    print(_("Partita terminata."))

    # Risultato finale (se non già settato)
    # Nota: board.result() di python-chess ritorna "*" se non terminata, o il risultato se terminata per regole scacchi
    # Ma noi vogliamo salvare nell'header
    res = current_node.root().headers.get("Result", "*")

    if res == "*" or res == "?":  # Se non ancora deciso dall'abbandono/tempo
        if board.is_checkmate():
            res = "0-1" if board.turn == chess.WHITE else "1-0"
        elif (
            board.is_stalemate()
            or board.is_insufficient_material()
            or board.is_seventyfive_moves()
            or board.is_fivefold_repetition()
        ):
            res = "1/2-1/2"

        if current_node.root():
            current_node.root().headers["Result"] = res

    print(_("Risultato: {r}").format(r=res))
    # Stampa Scacchiera Formattata
    cb = CustomBoard()
    cb.set_fen(board.fen())
    print(cb)

    return current_node
