import chess
import chess.engine
import chess.pgn
import time
import threading
from GBUtils import dgt, key, menu, Acusticator
from ..config import _
from .. import engine as orologic_engine
from .. import storage
from ..board_utils import DescribeMove, FormatTime, NormalizeMove, CustomBoard
from .constants import MNGAME
from . import analysis_utils

class EasyfishGameState:
    def __init__(self):
        self.white_time = 0.0
        self.black_time = 0.0
        self.white_inc = 0.0
        self.black_inc = 0.0
        self.active_color = chess.WHITE 
        self.game_over = False
        self.flag_fallen = False
        self.paused = False
        self.human_color = None
        self.engine_has_clock = True
        self.ignore_clock = False

def clock_thread(game_state):
    """Thread che gestisce il decremento del tempo e la bandierina."""
    last_time = time.time()
    
    while not game_state.game_over:
        current_time = time.time()
        elapsed = current_time - last_time
        last_time = current_time
        
        if not game_state.paused and not game_state.ignore_clock:
            if game_state.active_color == chess.WHITE:
                # Decrementa solo se white ha un clock (sempre vero per l'umano se bianco, o per motore se game mode)
                # Ma qui semplifichiamo: i tempi ci sono sempre, al massimo sono infiniti o ignorati per il motore
                if game_state.active_color == game_state.human_color or game_state.engine_has_clock:
                     game_state.white_time -= elapsed

                if game_state.white_time <= 0 and (game_state.active_color == game_state.human_color or game_state.engine_has_clock):
                    game_state.white_time = 0
                    game_state.flag_fallen = True
                    if not game_state.game_over:
                         Acusticator(["e4", 0.2, -0.5, 0.5, "d4", 0.2, 0, 0.5, "c4", 0.2, 0.5, 0.5], kind=1, adsr=[10, 0, 90, 10])
                         print(_("\nTempo Bianco scaduto!"))
                         game_state.paused = True 
            else:
                if game_state.active_color == game_state.human_color or game_state.engine_has_clock:
                    game_state.black_time -= elapsed

                if game_state.black_time <= 0 and (game_state.active_color == game_state.human_color or game_state.engine_has_clock):
                    game_state.black_time = 0
                    game_state.flag_fallen = True
                    if not game_state.game_over:
                        Acusticator(["e4", 0.2, -0.5, 0.5, "d4", 0.2, 0, 0.5, "c4", 0.2, 0.5, 0.5], kind=1, adsr=[10, 0, 90, 10])
                        print(_("\nTempo Nero scaduto!"))
                        game_state.paused = True

        time.sleep(0.1)

def ParseTimeInput(prompt_text):
    """Richiede input tempo in formato HH:MM:SS o sss."""
    while True:
        s = dgt(prompt=prompt_text + " (HH:MM:SS o sec): ", kind="s").strip()
        if not s: return None
        try:
            if ":" in s:
                parts = s.split(':')
                if len(parts) == 3:
                    return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0])*60 + int(parts[1])
            else:
                return int(s)
        except ValueError:
            print(_("Formato non valido."))

def StartEngineGame(game_node, engine_instance):
    """
    Avvia una partita contro il motore a partire dalla posizione corrente di game_node.
    Utilizza un thread separato per la gestione dell'orologio.
    """
    if not engine_instance:
        print(_("Motore non disponibile. Configuralo nelle impostazioni."))
        return game_node

    print(_("\n--- Nuova Partita contro il Motore ---"))
    
    engine_mode = menu({
        "1": _("Partita a tempo"),
        "2": _("Tempo per mossa motore"),
        "3": _("Senza tempo (Amichevole)")
    }, p=_("Modalita' di gioco: "), numbered=True)
    
    user_time = 0
    user_inc = 0
    engine_time = 0
    engine_inc = 0
    engine_limit_type = "game"
    engine_has_clock = True
    ignore_clock = False
    
    if engine_mode == "1":
        user_time = ParseTimeInput(_("Tuo tempo partita"))
        if user_time is None: return game_node
        user_inc = dgt(_("Tuo incremento (sec): "), kind="i", default=0)
        
        c = dgt(_("Usare stesso tempo per il motore? (s/n): "), kind="s", default="s").lower()
        if c == "s":
            engine_time = user_time
            engine_inc = user_inc
        else:
            engine_time = ParseTimeInput(_("Tempo partita motore"))
            if engine_time is None: return game_node
            engine_inc = dgt(_("Incremento motore (sec): "), kind="i", default=0)
            
    elif engine_mode == "2":
        engine_limit_type = "move"
        engine_has_clock = False
        user_time = ParseTimeInput(_("Tuo tempo partita"))
        if user_time is None: return game_node
        user_inc = dgt(_("Tuo incremento (sec): "), kind="i", default=0)
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
    game_state.human_color = board.turn # L'utente gioca chi ha il turno
    game_state.engine_has_clock = engine_has_clock
    
    if game_state.human_color == chess.WHITE:
        game_state.white_time = float(user_time)
        game_state.white_inc = float(user_inc)
        game_state.black_time = float(engine_time) if engine_has_clock else 0
        game_state.black_inc = float(engine_inc) if engine_has_clock else 0
        print(_("Giochi col BIANCO."))
    else:
        game_state.black_time = float(user_time)
        game_state.black_inc = float(user_inc)
        game_state.white_time = float(engine_time) if engine_has_clock else 0
        game_state.white_inc = float(engine_inc) if engine_has_clock else 0
        print(_("Giochi col NERO."))

    try:
        db = storage.LoadDB()
        current_skill = db.get("engine_config", {}).get("skill_level", 20)
        print(_("Livello forza motore (Skill Level): {s}").format(s=current_skill))
        
        # Forza attivazione WDL dal motore per l'analisi e gioco
        try:
            engine_instance.configure({"UCI_ShowWDL": True})
        except: pass
    except Exception as e:
        print(_("Errore lettura skill level: {e}").format(e=e))

    # Avvio Thread Orologio
    t = threading.Thread(target=clock_thread, args=(game_state,), daemon=True)
    t.start()
    
    current_node = game_node
    
    try:
        while not game_state.game_over and not board.is_game_over():
            if game_state.flag_fallen:
                print(_("Tempo scaduto! Partita terminata."))
                game_state.game_over = True
                res = "0-1" if game_state.active_color == chess.WHITE else "1-0"
                if current_node.root(): current_node.root().headers["Result"] = res
                break

            move_num = board.fullmove_number
            last_move_san = current_node.san() if current_node.move else ""
            
            if not current_node.move:
                prompt = f"{move_num}. "
            elif board.turn == chess.WHITE:
                prompt = f"{move_num-1}... {last_move_san} {move_num}. "
            else:
                prompt = f"{move_num}. {last_move_san} "

            # --- TURNO UMANO ---
            if board.turn == game_state.human_color:
                # Input
                move_input = dgt(prompt=prompt, kind="s")
                
                if game_state.flag_fallen: continue 
                if not move_input: continue

                # Comandi
                if move_input.startswith("."):
                    cmd = move_input.lower()
                    if cmd == ".":
                        print(_("Hai abbandonato."))
                        game_state.game_over = True
                        # Assegna risultato (Umano perde)
                        res = "0-1" if game_state.human_color == chess.WHITE else "1-0"
                        if current_node.root(): current_node.root().headers["Result"] = res
                        break
                    elif cmd == ".1":
                        if getattr(game_state, 'ignore_clock', False): print(_("Orologi disattivati."))
                        else: print(_("Tempo Bianco: {t}").format(t=FormatTime(game_state.white_time)))
                    elif cmd == ".2":
                        if getattr(game_state, 'ignore_clock', False): print(_("Orologi disattivati."))
                        else: print(_("Tempo Nero: {t}").format(t=FormatTime(game_state.black_time)))
                    elif cmd == ".a":
                         lines = analysis_utils.RunAnalysis(board, engine_instance, orologic_engine.analysis_time, 1)
                         for l in lines: print(l)
                    elif cmd == ".b":
                         print(CustomBoard(board.fen()))
                    elif cmd == ".?":
                         menu(MNGAME, show_only=True)
                    elif cmd.startswith(".s") and len(cmd) > 2 and cmd[2:].isdigit():
                         try:
                             new_skill = int(cmd[2:])
                             if 1 <= new_skill <= 20:
                                 engine_instance.configure({"Skill Level": new_skill})
                                 Acusticator(["g5", 0.05, 0, 0.5], kind=1)
                                 print(_("Livello di forza del motore impostato a {n}.").format(n=new_skill))
                             else:
                                 Acusticator([400.0, 0.2, 0, 0.5], kind=1)
                                 print(_("Il livello deve essere compreso tra 1 e 20."))
                         except Exception as e:
                             print(_("Errore durante l'impostazione del livello: {e}").format(e=e))
                    elif cmd == ".v":
                        try:
                            res = orologic_engine.CalculateBest(board, bestmove=False, as_san=False)
                            if res and len(res) > 0:
                                var_node = current_node.add_variation(res[0])
                                var_node.add_line(res[1:])
                                print(_("Variante suggerita aggiunta all'albero."))
                            else: print(_("Nessuna linea trovata."))
                        except Exception as e: print(f"Err: {e}")
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
                            Acusticator(["c4", 0.1, -1, 0.5, "e4", 0.1, 0, 0.5], kind=1)
                            print(_("Annullate {n} semimosse. Tocca a te.").format(n=steps))
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
                        
                        if game_state.human_color == chess.WHITE:
                            game_state.white_time += game_state.white_inc
                        else:
                            game_state.black_time += game_state.black_inc
                            
                        game_state.active_color = board.turn
                        Acusticator([1000.0, 0.05, 0, 0.5], kind=1)
                        print(DescribeMove(move, current_node.parent.board()))
                    else:
                        Acusticator([400.0, 0.2, 0, 0.5], kind=1)
                        print(_("Mossa illegale."))
                except ValueError:
                    Acusticator([400.0, 0.2, 0, 0.5], kind=1)
                    print(_("Input non valido."))

            # --- TURNO MOTORE ---
            else:
                
                limit = None
                if engine_limit_type == "game":
                    limit = chess.engine.Limit(
                        white_clock=game_state.white_time,
                        black_clock=game_state.black_time,
                        white_inc=game_state.white_inc,
                        black_inc=game_state.black_inc
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
                                game_state.white_time += game_state.white_inc
                            else:
                                game_state.black_time += game_state.black_inc

                        new_node = current_node.add_main_variation(result.move)
                        current_node = new_node
                        board.push(result.move)
                        
                        game_state.active_color = board.turn
                        Acusticator([1000.0, 0.05, 0, 0.5], kind=1)
                        print(DescribeMove(result.move, current_node.parent.board()))
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
    
    if res == "*" or res == "?": # Se non ancora deciso dall'abbandono/tempo
        if board.is_checkmate():
            res = "0-1" if board.turn == chess.WHITE else "1-0"
        elif board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
            res = "1/2-1/2"
        
        if current_node.root(): current_node.root().headers["Result"] = res

    print(_("Risultato: {r}").format(r=res))
    # Stampa Scacchiera Formattata
    cb = CustomBoard()
    cb.set_fen(board.fen())
    print(cb)
    
    return current_node
