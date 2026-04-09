import os
import json
import urllib.request
import urllib.error
import webbrowser
import chess
import time
from GBUtils import menu, enter_escape, Acusticator, dgt
from . import storage, board_utils, config, ui, lichess_spectator
from .config import percorso_salvataggio

SECRETS_FILE = percorso_salvataggio(os.path.join("settings", "secrets.json"))

def load_secrets():
    try:
        with open(SECRETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_secrets(secrets):
    try:
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump(secrets, f, indent=4)
    except Exception as e:
        print(f"Errore salvataggio segreti: {e}")

def _(testo):
    """
    Quando L10N è configurato, importalo dal modulo apposito.
    Per ora usa una pass-through per compatibilità.
    """
    from .config import L10N
    return L10N.get(testo, testo)

def fetch_profile_info(token):
    """Recupera le info del profilo dal server Lichess."""
    req = urllib.request.Request("https://lichess.org/api/account")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception:
        pass
    return None

def format_ratings(perfs):
    """Formatta i punteggi Elo dai dati perfs dell'API."""
    if not perfs:
        return ""
    ratings = []
    # Mostriamo Rapid, Blitz e Classical se l'utente ha giocato almeno una partita
    for mode in ["rapid", "blitz", "classical"]:
        if mode in perfs and "rating" in perfs[mode]:
            games = perfs[mode].get("games", 0)
            if games > 0:
                ratings.append(f"{mode.capitalize()}: {perfs[mode]['rating']}")
    if ratings:
        return " - Elo [" + ", ".join(ratings) + "]"
    return ""

def menu_login(db):
    """Gestisce il login e il salvataggio del token di Lichess."""
    print(_("\n--- Login a Lichess ---"))
    print(_("Per collegare Orologic a Lichess e' necessario un 'Personal API Token'."))
    print(_("Assicurati di concedere i permessi necessari (leggere il profilo, giocare, puzzle, ecc.)."))
    
    input(_("Premi Invio per aprire il browser e generare il tuo token su Lichess..."))
    try:
        webbrowser.open("https://lichess.org/account/oauth/token")
    except Exception:
        print(_("Impossibile aprire il browser automaticamente. Vai manualmente su: https://lichess.org/account/oauth/token"))
    
    token = input(_("\nIncolla qui il tuo Personal API Token (oppure premi Invio per annullare): ")).strip()
    
    if token:
        print(_("Verifica del token in corso..."))
        profile = fetch_profile_info(token)
        if profile:
            username = profile.get("username", "Sconosciuto")
            secrets = load_secrets()
            secrets["lichess_token"] = token
            secrets["lichess_username"] = username
            save_secrets(secrets)
            print(_("Token valido! Benvenuto, {username}!").format(username=username))
            # Ritorniamo il profile per aggiornare l'interfaccia subito
            return profile
        else:
            print(_("Errore: Il token inserito non e' valido, e' scaduto, oppure c'e' un problema di connessione."))
    else:
        print(_("Login annullato."))
    return None

def menu_logout(db):
    """Gestisce il logout rimuovendo il token."""
    print(_("\n--- Logout da Lichess ---"))
    secrets = load_secrets()
    if "lichess_token" in secrets:
        if enter_escape(_("Sei sicuro di voler effettuare il logout e cancellare il token salvato? (Invio = Si, Esc = No): ")):
            del secrets["lichess_token"]
            if "lichess_username" in secrets:
                del secrets["lichess_username"]
            save_secrets(secrets)
            print(_("Logout effettuato con successo. Token rimosso."))
            return True
        else:
            print(_("Logout annullato."))
    else:
        print(_("Non sei attualmente loggato (nessun token presente)."))
    return False

def format_timestamp(ts):
    import datetime
    if not ts: return _("Sconosciuto")
    return datetime.datetime.fromtimestamp(ts/1000).strftime('%d/%m/%Y %H:%M')

def format_playtime(seconds):
    if not seconds: return _("0 secondi")
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(_("{n} giorni").format(n=days) if days != 1 else _("1 giorno"))
    if hours > 0:
        parts.append(_("{n} ore").format(n=hours) if hours != 1 else _("1 ora"))
    if minutes > 0:
        parts.append(_("{n} minuti").format(n=minutes) if minutes != 1 else _("1 minuto"))
    return ", ".join(parts) if parts else _("< 1 minuto")

def menu_profilo(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    if not token:
        print(_("\nDevi prima effettuare il login per vedere il tuo profilo."))
        return

    print(_("\nRecupero dati del profilo in corso..."))
    profile = fetch_profile_info(token)
    if not profile:
        print(_("Impossibile recuperare il profilo. Controlla la tua connessione o il token."))
        return
    
    print(_("\n=================================="))
    print(_("         PROFILO LICHESS"))
    print(_("=================================="))
    print(_("Username: {u}").format(u=profile.get("username", "Sconosciuto")))
    
    prof_data = profile.get("profile", {})
    bio = prof_data.get("bio")
    if bio:
        print(_("Biografia: {b}").format(b=bio))
    fide = prof_data.get("fideRating")
    if fide:
        print(_("Elo FIDE: {f}").format(f=fide))
    
    print(_("\n[Statistiche Generali]"))
    print(_("Data iscrizione: {d}").format(d=format_timestamp(profile.get("createdAt"))))
    print(_("Ultimo accesso: {d}").format(d=format_timestamp(profile.get("seenAt"))))
    if "playTime" in profile:
        total_seconds = profile["playTime"].get("total", 0)
        print(_("Tempo totale di gioco: {t}").format(t=format_playtime(total_seconds)))
    
    print(_("\n[Punteggi Elo]"))
    perfs = profile.get("perfs", {})
    if not perfs:
        print(_("Nessun punteggio disponibile."))
    else:
        for mode, data in perfs.items():
            if isinstance(data, dict) and "rating" in data:
                games = data.get("games", 0)
                if games > 0:
                    print(_(" - {m}: {r} (Partite: {g})").format(m=mode.capitalize(), r=data["rating"], g=games))
    print(_("=================================="))
    
    enter_escape(_("\nPremi Invio per tornare al menu Lichess..."))

def fetch_perf_info(username, perf):
    """Recupera le statistiche dettagliate di una variante."""
    req = urllib.request.Request(f"https://lichess.org/api/user/{username}/perf/{perf}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception:
        pass
    return None

def format_iso_date(iso_str):
    """Formatta una stringa ISO 8601 di Lichess."""
    if not iso_str: return _("Sconosciuto")
    import datetime
    try:
        # Rimuove millisecondi e Z per la compatibilità con le vecchie versioni di Python
        iso_str = iso_str.split('.')[0].replace('Z', '')
        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return iso_str

def menu_statistiche(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    username = secrets.get("lichess_username")
    
    if not token or not username:
        print(_("\nDevi prima effettuare il login per vedere le statistiche."))
        return

    print(_("\nRecupero dati utente in corso..."))
    profile = fetch_profile_info(token)
    if not profile:
        print(_("Impossibile recuperare il profilo. Controlla la tua connessione."))
        return
        
    perfs = profile.get("perfs", {})
    if not perfs:
        print(_("Nessuna statistica disponibile."))
        return
        
    valid_modes = {}
    for mode, data in perfs.items():
        if isinstance(data, dict) and data.get("games", 0) > 0:
            valid_modes[mode] = _("Partite: {g}").format(g=data["games"])
            
    if not valid_modes:
        print(_("\nNon hai ancora giocato nessuna partita."))
        return
        
    while True:
        # Ricostruiamo il menu iterativamente per permettere di tornare indietro
        scelte_mod = dict(valid_modes)
        scelte_mod["."] = _("Torna al menu Lichess")
        
        scelta = menu(scelte_mod, show=True, keyslist=True, p=_("\nScegli una modalita' per le statistiche: "), numbered=db.get("menu_numerati", False))
        
        if scelta == ".":
            break
            
        if scelta == "puzzle":
            print(_("\n=================================="))
            print(_("     STATISTICHE: PUZZLE"))
            print(_("=================================="))
            puzzle_perf = perfs.get("puzzle", {})
            print(_("Elo Attuale: {r}").format(r=puzzle_perf.get("rating", "N/A")))
            print(_("Puzzle giocati: {g}").format(g=puzzle_perf.get("games", 0)))
            if "prov" in puzzle_perf and puzzle_perf["prov"]:
                print(_("Stato: Provvisorio"))
            print(_("Progressione (recente): {p}").format(p=puzzle_perf.get("prog", 0)))
            print(_("\nNota: Le statistiche avanzate (es. Win/Loss/Streak) per i puzzle non sono esposte dall'API di base di Lichess."))
            print(_("=================================="))
            enter_escape(_("\nPremi Invio per continuare..."))
            continue
            
        print(_("\nRecupero statistiche dettagliate per {m}...").format(m=scelta.capitalize()))
        perf_data = fetch_perf_info(username, scelta)
        if not perf_data or "stat" not in perf_data:
            print(_("Impossibile recuperare le statistiche per questa modalita'."))
            continue
            
        stat = perf_data["stat"]
        perf = perf_data.get("perf", {})
        
        print(_("\n=================================="))
        print(_("     STATISTICHE: {m}").format(m=scelta.upper()))
        print(_("=================================="))
        
        glicko = perf.get("glicko", {})
        print(_("Elo Attuale: {r} (Deviazione: {d})").format(r=glicko.get("rating", "N/A"), d=glicko.get("deviation", "N/A")))
        print(_("Progressione (ultime 12 partite): {p}").format(p=perf.get("progress", 0)))
        percentile = perf_data.get("percentile")
        if percentile is not None:
            print(_("Percentile: {p}% (Sei migliore del {p}% dei giocatori)").format(p=percentile))
            
        count = stat.get("count", {})
        total = count.get("all", 0)
        rated = count.get("rated", 0)
        wins = count.get("win", 0)
        losses = count.get("loss", 0)
        draws = count.get("draw", 0)
        
        print(_("\n[Risultati su {t} partite ({r} classificate)]").format(t=total, r=rated))
        if total > 0:
            p_win = (wins / total) * 100
            p_loss = (losses / total) * 100
            p_draw = (draws / total) * 100
            print(_("Vittorie: {w} ({p:.2f}%)").format(w=wins, p=p_win))
            print(_("Sconfitte: {l} ({p:.2f}%)").format(l=losses, p=p_loss))
            print(_("Patte: {d} ({p:.2f}%)").format(d=draws, p=p_draw))
        else:
            print(_("Vittorie: {w}\nSconfitte: {l}\nPatte: {d}").format(w=wins, l=losses, d=draws))
            
        berserk = count.get("berserk", 0)
        if berserk > 0 and total > 0:
            p_berserk = (berserk / total) * 100
            print(_("Volte in cui sei andato Berserk: {b} ({p:.2f}%)").format(b=berserk, p=p_berserk))
            
        opAvg = count.get("opAvg")
        if opAvg is not None:
            print(_("Elo medio avversari: {avg}").format(avg=opAvg))
        
        disconnects = count.get("disconnects", 0)
        if disconnects > 0:
            print(_("Disconnessioni: {d}").format(d=disconnects))
            
        highest = stat.get("highest", {})
        lowest = stat.get("lowest", {})
        if highest.get("int") or lowest.get("int"):
            print(_("\n[Record Elo]"))
            if highest.get("int"):
                print(_("Piu' alto: {r} (il {d})").format(r=highest["int"], d=format_iso_date(highest.get("at"))))
            if lowest.get("int"):
                print(_("Piu' basso: {r} (il {d})").format(r=lowest["int"], d=format_iso_date(lowest.get("at"))))
                
        streaks = stat.get("resultStreak", {})
        win_streak = streaks.get("win", {}).get("max", {}).get("v", 0)
        loss_streak = streaks.get("loss", {}).get("max", {}).get("v", 0)
        if win_streak > 0 or loss_streak > 0:
            print(_("\n[Serie]"))
            print(_("Vittorie consecutive piu' lunga: {w}").format(w=win_streak))
            print(_("Sconfitte consecutive piu' lunga: {l}").format(l=loss_streak))
            
        time_seconds = count.get("seconds", 0)
        if time_seconds > 0:
            print(_("\nTempo speso in questa modalita': {t}").format(t=format_playtime(time_seconds)))
            
        print(_("=================================="))
        enter_escape(_("\nPremi Invio per continuare..."))

def fetch_following(token):
    req = urllib.request.Request("https://lichess.org/api/rel/following")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                lines = response.read().decode('utf-8').strip().split('\n')
                users = []
                for line in lines:
                    if line.strip():
                        try:
                            users.append(json.loads(line))
                        except Exception:
                            pass
                return users
    except Exception as e:
        print(_("Errore durante il recupero dei seguiti: {e}").format(e=e))
    return []

def follow_user(token, username):
    req = urllib.request.Request(f"https://lichess.org/api/rel/follow/{username}", method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(_("Ora segui {u}!").format(u=username))
                return True
    except urllib.error.HTTPError as e:
        print(_("Errore HTTP: {c} (Assicurati di avere il permesso follow:write)").format(c=e.code))
    except Exception as e:
        print(_("Errore di connessione: {e}").format(e=e))
    return False

def unfollow_user(token, username):
    req = urllib.request.Request(f"https://lichess.org/api/rel/unfollow/{username}", method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(_("Non segui piu' {u}.").format(u=username))
                return True
    except urllib.error.HTTPError as e:
        print(_("Errore HTTP: {c}").format(c=e.code))
    except Exception as e:
        print(_("Errore di connessione: {e}").format(e=e))
    return False

def send_message(token, username, text):
    import urllib.parse
    req = urllib.request.Request(f"https://lichess.org/inbox/{username}", method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    data = urllib.parse.urlencode({'text': text}).encode('utf-8')
    try:
        with urllib.request.urlopen(req, data=data) as response:
            if response.status == 200:
                print(_("Messaggio inviato a {u} con successo!").format(u=username))
                return True
    except urllib.error.HTTPError as e:
        print(_("Errore HTTP: {c} (L'utente potrebbe non accettare messaggi o ti manca il permesso msg:write)").format(c=e.code))
    except Exception as e:
        print(_("Errore di connessione: {e}").format(e=e))
    return False

def menu_amici(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    if not token:
        print(_("\nDevi prima effettuare il login per gestire gli amici."))
        return

    while True:
        print(_("\n=================================="))
        print(_("          GESTIONE AMICI"))
        print(_("=================================="))
        
        scelte_amici = {
            "vedi": _("Vedi persone che segui"),
            "segui": _("Segui un nuovo giocatore"),
            "smetti": _("Smetti di seguire un giocatore"),
            "messaggio": _("Invia un messaggio privato"),
            ".": _("Torna al menu Lichess")
        }
        
        scelta = menu(scelte_amici, show=True, keyslist=True, p=_("\nScegli un'azione: "), numbered=db.get("menu_numerati", False))
        
        if scelta == ".":
            break
        elif scelta == "vedi":
            print(_("\nRecupero lista dei giocatori seguiti..."))
            following = fetch_following(token)
            if not following:
                print(_("Non stai seguendo nessuno o e' impossibile recuperare la lista."))
            else:
                print(_("\nStai seguendo {n} giocatori:").format(n=len(following)))
                for u in following:
                    username = u.get('username', 'Sconosciuto')
                    title = u.get('title', '')
                    title_str = f"[{title}] " if title else ""
                    online = _("ONLINE") if u.get('online') else _("Offline")
                    print(_(" - {t}{u} ({o})").format(t=title_str, u=username, o=online))
            enter_escape(_("\nPremi Invio per continuare..."))
            
        elif scelta == "segui":
            username = input(_("\nInserisci l'username del giocatore da seguire: ")).strip()
            if username:
                follow_user(token, username)
            enter_escape(_("\nPremi Invio per continuare..."))
            
        elif scelta == "smetti":
            username = input(_("\nInserisci l'username del giocatore da smettere di seguire: ")).strip()
            if username:
                unfollow_user(token, username)
            enter_escape(_("\nPremi Invio per continuare..."))
            
        elif scelta == "messaggio":
            username = input(_("\nInserisci l'username del destinatario: ")).strip()
            if not username:
                continue
            testo = input(_("Inserisci il messaggio: ")).strip()
            if not testo:
                print(_("Messaggio annullato."))
            else:
                send_message(token, username, testo)
            enter_escape(_("\nPremi Invio per continuare..."))

class DummyGameState:
    def __init__(self, board):
        self.board = board
        self.white_player = _("Bianco")
        self.black_player = _("Nero")

def describe_board(board, last_move_san=None):
    turn = _("Tocca al Bianco muovere.") if board.turn == chess.WHITE else _("Tocca al Nero muovere.")
    
    castling = []
    if board.has_kingside_castling_rights(chess.WHITE): castling.append(_("Corto Bianco"))
    if board.has_queenside_castling_rights(chess.WHITE): castling.append(_("Lungo Bianco"))
    if board.has_kingside_castling_rights(chess.BLACK): castling.append(_("Corto Nero"))
    if board.has_queenside_castling_rights(chess.BLACK): castling.append(_("Lungo Nero"))
    castling_str = _("Diritti di arrocco: {c}").format(c=", ".join(castling)) if castling else _("Nessun diritto di arrocco.")
    
    ep_str = ""
    if board.ep_square:
        ep_sq = chess.square_name(board.ep_square)
        ep_str = _("Presa en passant possibile in {sq}.").format(sq=ep_sq)
        
    last_str = _("Ultima mossa giocata: {m}").format(m=last_move_san) if last_move_san else ""
    
    return "\n".join(filter(None, [turn, castling_str, ep_str, last_str]))

def handle_exploration_command(user_input, game_state):
    if user_input.startswith("/"):
        Acusticator(["c5", 0.07, -1, config.VOLUME,"d5", 0.07, -.75, config.VOLUME,"e5", 0.07, -.5, config.VOLUME,"f5", 0.07, -.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"a5", 0.07, .25, config.VOLUME,"b5", 0.07, .5, config.VOLUME,"c6", 0.07, .75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
        base_column = user_input[1:2].strip()
        ui.read_diagonal(game_state, base_column, True)
        return True
    elif user_input.startswith("\\"):
        Acusticator(["c5", 0.07, 1, config.VOLUME,"d5", 0.07, 0.75, config.VOLUME,"e5", 0.07, 0.5, config.VOLUME,"f5", 0.07, 0.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"a5", 0.07, -0.25, config.VOLUME,"b5", 0.07, -0.5, config.VOLUME,"c6", 0.07, -0.75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
        base_column = user_input[1:2].strip()
        ui.read_diagonal(game_state, base_column, False)
        return True
    elif user_input.startswith("-"):
        param = user_input[1:].strip()
        if not param:
            Acusticator(["c5", 0.07, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            ui.report_all_pieces(game_state, chess.WHITE)
            return True
        elif len(param) == 1 and param.isalpha():
            Acusticator(["c5", 0.07, 0, config.VOLUME, "d5", 0.07, 0, config.VOLUME, "e5", 0.07, 0, config.VOLUME, "f5", 0.07, 0, config.VOLUME, "g5", 0.07, 0, config.VOLUME, "a5", 0.07, 0, config.VOLUME, "b5", 0.07, 0, config.VOLUME, "c6", 0.07, 0, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
            ui.read_file(game_state, param)
        elif len(param) == 1 and param.isdigit():
            rank_number = int(param)
            if 1 <= rank_number <= 8:
                Acusticator(["g5", 0.07, -1, config.VOLUME,"g5", 0.07, -.75, config.VOLUME,"g5", 0.07, -.5, config.VOLUME,"g5", 0.07, -.25, config.VOLUME,"g5", 0.07, 0, config.VOLUME,"g5", 0.07, .25, config.VOLUME,"g5", 0.07, .5, config.VOLUME,"g5", 0.07, .75, config.VOLUME], kind=3, adsr=[0, 0, 100, 100])
                ui.read_rank(game_state, rank_number)
            else:
                print(_("Traversa non valida."))
        elif len(param) == 2 and param[0].isalpha() and param[1].isdigit():
            Acusticator(["d#4", .7, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
            ui.read_square(game_state, param)
        else:
            print(_("Comando dash non riconosciuto."))
        return True
    elif user_input == "+":
        Acusticator(["c4", 0.07, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100])
        ui.report_all_pieces(game_state, chess.BLACK)
        return True
    elif user_input.startswith(","):
        Acusticator(["a3", .06, -1, config.VOLUME, "c4", .06, -0.5, config.VOLUME, "d#4", .06, 0.5, config.VOLUME, "f4", .06, 1, config.VOLUME], kind=3, adsr=[20, 5, 70, 25])
        ui.report_piece_positions(game_state, user_input[1:2])
        return True
    elif user_input.lower() == ".b":
        Acusticator(["c4", 0.2, -1, config.VOLUME, "g4", 0.2, -0.3, config.VOLUME, "c5", 0.2, 0.3, config.VOLUME, "e5", 0.2, 1, config.VOLUME, "g5", 0.4, 0, config.VOLUME], kind=1, adsr=[10, 5, 80, 5])
        print(game_state.board)
        return True
    elif user_input == ".?":
        Acusticator([440.0, 0.3, 0, config.VOLUME, 880.0, 0.3, 0, config.VOLUME], kind=1, adsr=[10, 0, 100, 20])
        commands = {
            "-": _("Riepilogo dei pezzi Bianchi"),
            "+": _("Riepilogo dei pezzi Neri"),
            "-[a-h]": _("Esplora colonna"),
            "-[1-8]": _("Esplora traversa"),
            "-[casa]": _("Dettagli su una casa (es. -e4)"),
            "/[a-h]": _("Diagonale ascendente destra"),
            "\\[a-h]": _("Diagonale ascendente sinistra"),
            ",[P,N,B,R,Q,K]": _("Posizioni di un pezzo specifico"),
            ".b": _("Mostra la scacchiera grafica"),
            ".": _("Arrenditi o esci dal puzzle")
        }
        menu(commands, show_only=True, p=_("Comandi di esplorazione disponibili:"), ordered=False)
        return True
    return False

def fetch_puzzle(token=None, daily=False, difficulty=None, angle=None):
    url = "https://lichess.org/api/puzzle/daily" if daily else "https://lichess.org/api/puzzle/next"
    if difficulty or angle:
        params = []
        if difficulty: params.append(f"difficulty={difficulty}")
        if angle: params.append(f"angle={angle}")
        if params: url += "?" + "&".join(params)
        
    req = urllib.request.Request(url)
    if token and not daily:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(_("Errore HTTP durante il recupero del puzzle: {c}").format(c=e.code))
    except Exception as e:
        print(_("Errore di connessione: {e}").format(e=e))
    return None

def send_puzzle_result(token, puzzle_id, win):
    if not token or not puzzle_id:
        return
    url = "https://lichess.org/api/puzzle/batch/mix"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    data = json.dumps({
        "solutions": [
            {
                "id": puzzle_id,
                "win": win,
                "rated": True
            }
        ]
    }).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data):
            pass
    except Exception:
        pass

def calcola_difficolta(user_elo, puzzle_elo_richiesto):
    diff = puzzle_elo_richiesto - user_elo
    if diff <= -400: return "easiest"
    if diff <= -150: return "easier"
    if diff <= 150: return "normal"
    if diff <= 400: return "harder"
    return "hardest"

def get_puzzle_themes():
    return {
        "advancedPawn": _("Pedone avanzato"),
        "advantage": _("Vantaggio"),
        "attraction": _("Attrazione"),
        "backRankMate": _("Matto del corridoio"),
        "bishopEndgame": _("Finale di Alfieri"),
        "castling": _("Arrocco"),
        "capturingDefender": _("Cattura del difensore"),
        "clearance": _("Sgombero"),
        "crushing": _("Schiacciante"),
        "deflection": _("Deviazione"),
        "discoveredAttack": _("Attacco di scoperta"),
        "doubleCheck": _("Scacco doppio"),
        "endgame": _("Finale"),
        "enPassant": _("Presa in Passant"),
        "equality": _("Parita'"),
        "exposedKing": _("Re esposto"),
        "fork": _("Forchetta/Attacco doppio"),
        "hangingPiece": _("Pezzo in presa"),
        "interference": _("Interferenza"),
        "intermezzo": _("Mossa intermedia (Zwischenzug)"),
        "kingsideAttack": _("Attacco sull'ala di Re"),
        "knightEndgame": _("Finale di Cavalli"),
        "long": _("Lungo (3 mosse)"),
        "master": _("Partite di Maestri"),
        "mate": _("Scacco matto"),
        "mateIn1": _("Matto in 1"),
        "mateIn2": _("Matto in 2"),
        "mateIn3": _("Matto in 3"),
        "mateIn4": _("Matto in 4"),
        "mateIn5": _("Matto in 5+"),
        "middlegame": _("Medio gioco"),
        "oneMove": _("Una mossa"),
        "opening": _("Apertura"),
        "pawnEndgame": _("Finale di Pedoni"),
        "pin": _("Inchiodatura"),
        "promotion": _("Promozione"),
        "queenEndgame": _("Finale di Donne"),
        "queenRookEndgame": _("Finale Donna e Torre"),
        "queensideAttack": _("Attacco sull'ala di Donna"),
        "quietMove": _("Mossa silenziosa"),
        "rookEndgame": _("Finale di Torri"),
        "sacrifice": _("Sacrificio"),
        "short": _("Corto (2 mosse)"),
        "skewer": _("Infilata"),
        "smotheredMate": _("Matto affogato"),
        "trappedPiece": _("Pezzo intrappolato"),
        "underPromotion": _("Sottopromozione"),
        "veryLong": _("Molto lungo (4+ mosse)"),
        "zugzwang": _("Zugzwang"),
        "vuoto": _("Casuale (Nessun filtro)")
    }

def get_last_moves_san(board, num=5):
    if not board.move_stack:
        return ""
    moves = board.move_stack[-num:]
    temp_board = board.copy()
    for _ in range(len(moves)):
        temp_board.pop()
    parts = []
    for m in moves:
        san = temp_board.san(m)
        if temp_board.turn == chess.WHITE:
            parts.append(f"{temp_board.fullmove_number}. {san}")
        else:
            if not parts:
                parts.append(f"{temp_board.fullmove_number}... {san}")
            else:
                parts.append(san)
        temp_board.push(m)
    return " ".join(parts)

def menu_puzzle(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    
    while True:
        print(_("\n=================================="))
        print(_("             PUZZLE LICHESS"))
        print(_("=================================="))
        
        scelte_puzzle = {
            "giorno": _("Puzzle del Giorno"),
            "nuovo": _("Risolvi un nuovo puzzle"),
            ".": _("Torna al menu Lichess")
        }
        
        scelta = menu(scelte_puzzle, show=True, keyslist=True, p=_("\nScegli un'opzione: "), numbered=db.get("menu_numerati", False))
        
        if scelta == ".":
            break
            
        difficulty = None
        angle = None
        if scelta == "nuovo":
            # Calcolo Elo Puzzle dell'utente
            user_puzzle_elo = 1500
            if token:
                profile = fetch_profile_info(token)
                if profile and "perfs" in profile and "puzzle" in profile["perfs"]:
                    user_puzzle_elo = profile["perfs"]["puzzle"].get("rating", 1500)
            
            print(_("\nIl tuo punteggio puzzle stimato e': {elo}").format(elo=user_puzzle_elo))
            scelta_elo = dgt(_("A quale Elo vuoi esercitarti? (es. 1800, oppure invio per mantenere il tuo): ")).strip()
            
            if scelta_elo.isdigit():
                target_elo = int(scelta_elo)
                difficulty = calcola_difficolta(user_puzzle_elo, target_elo)
                print(_("Lichess adattera' la ricerca alla difficolta': {d}").format(d=difficulty))
            
            themes = get_puzzle_themes()
            print(_("\nScegli la categoria di puzzle:"))
            angle_scelto = menu(themes, show=False, keyslist=True, p=_("Seleziona il tema: "))
            if angle_scelto != "vuoto":
                angle = angle_scelto
            
        print(_("\nRecupero puzzle in corso..."))
        puzzle_data = fetch_puzzle(token, daily=(scelta == "giorno"), difficulty=difficulty, angle=angle)
        
        if not puzzle_data or "puzzle" not in puzzle_data:
            print(_("Impossibile caricare il puzzle."))
            continue
            
        puz = puzzle_data["puzzle"]
        game_info = puzzle_data.get("game", {})
        
        print(_("\n--- Puzzle {id} ---").format(id=puz.get("id")))
        print(_("Difficolta' (Rating Lichess): {r}").format(r=puz.get("rating")))
        print(_("Tema: {t}").format(t=", ".join(puz.get("themes", []))))
        
        import io
        import chess.pgn
        
        last_move_san = None
        board = board_utils.CustomBoard()
        
        if "pgn" in game_info and "initialPly" in puz:
            try:
                pgn_game = chess.pgn.read_game(io.StringIO(game_info["pgn"]))
                node = pgn_game
                ply = 0
                initial_ply = puz["initialPly"]
                
                board = board_utils.CustomBoard()
                moves_to_push = []
                while node.variations and ply <= initial_ply:
                    node = node.variations[0]
                    moves_to_push.append(node.move)
                    ply += 1
                
                for m in moves_to_push:
                    board.push(m)
                
                if node.move and node.parent:
                    last_move_san = board_utils.DescribeMove(node.move, node.parent.board())
            except Exception as e:
                print(_("Errore nel parsing del PGN: {e}").format(e=e))
                # Fallback
                if puz.get("fen"):
                    board = board_utils.CustomBoard(puz["fen"])
                    last_move_san = puz.get("lastMove")
        elif puz.get("fen"):
            board = board_utils.CustomBoard(puz["fen"])
            last_move_san = puz.get("lastMove")
            
        game_state = DummyGameState(board)
        
        print("\n" + describe_board(board, last_move_san))
        ui.report_all_pieces(game_state, not board.turn)
        ui.report_all_pieces(game_state, board.turn)
        Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
        
        print(_("\nSuggerimento: digita . per uscire, .? per l'aiuto sulle esplorazioni"))
        
        soluzione = puz.get("solution", [])
        mossa_idx = 0
        risolto = False
        result_sent = False
        start_time = time.time()
        
        while mossa_idx < len(soluzione):
            mossa_corretta_uci = soluzione[mossa_idx]
            mossa_corretta_move = chess.Move.from_uci(mossa_corretta_uci)
            
            last_5 = get_last_moves_san(board, 5)
            prompt_text = f"\n{last_5} > " if last_5 else "\n> "
            user_input = dgt(prompt_text).strip()
            if not user_input: continue
            
            if handle_exploration_command(user_input, game_state):
                if user_input.lower() != ".b" and user_input != ".?":
                    continue
            
            if user_input == "." or user_input.lower() == "s":
                if user_input == ".":
                    if enter_escape(_("Vuoi vedere la soluzione del puzzle? (Invio = Si', Esc = No): ")):
                        user_input = "s"
                    else:
                        print(_("Puzzle interrotto."))
                        if not result_sent:
                            send_puzzle_result(token, puz.get("id"), win=False)
                            result_sent = True
                        end_time = time.time()
                        elapsed = int(end_time - start_time)
                        mins = elapsed // 60
                        secs = elapsed % 60
                        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                        print(_("Tempo impiegato: {t}").format(t=time_str))
                        break
                        
                if user_input == "s":
                    if not result_sent:
                        send_puzzle_result(token, puz.get("id"), win=False)
                        result_sent = True
                    print(_("\n--- Soluzione del Puzzle ---"))
                    temp_board = board.copy()
                    for i in range(mossa_idx, len(soluzione)):
                        sol_move = chess.Move.from_uci(soluzione[i])
                        desc = board_utils.DescribeMove(sol_move, temp_board)
                        if i % 2 == mossa_idx % 2:
                            print(_("Il tuo tratto: {m}").format(m=desc))
                        else:
                            print(_("L'avversario risponde con: {m}").format(m=desc))
                        temp_board.push(sol_move)
                    end_time = time.time()
                    elapsed = int(end_time - start_time)
                    mins = elapsed // 60
                    secs = elapsed % 60
                    time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                    print(_("Tempo impiegato: {t}").format(t=time_str))
                break
                
            if user_input.startswith(".") or user_input.startswith("/") or user_input.startswith("\\") or user_input.startswith("-") or user_input.startswith(",") or user_input == "+":
                continue
                
            try:
                raw_input = board_utils.NormalizeMove(user_input)
                move = board.parse_san(raw_input)
            except ValueError:
                try:
                    move = board.parse_uci(raw_input)
                except ValueError:
                    Acusticator([600.0, 0.6, 0, config.VOLUME], adsr=[5, 0, 35, 90])
                    print(_("Mossa non valida. Digita . per uscire, .? per l'aiuto sulle esplorazioni"))
                    continue
                    
            if move == mossa_corretta_move:
                Acusticator([1000.0, 0.01, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0])
                desc_move = board_utils.DescribeMove(move, board)
                print(_("Corretto! Hai giocato: {m}").format(m=desc_move))
                board.push(move)
                mossa_idx += 1
                
                if mossa_idx < len(soluzione):
                    avv_uci = soluzione[mossa_idx]
                    avv_move = chess.Move.from_uci(avv_uci)
                    desc_avv = board_utils.DescribeMove(avv_move, board)
                    print(_("L'avversario risponde con: {m}").format(m=desc_avv))
                    board.push(avv_move)
                    mossa_idx += 1
                    Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME, "g5", 0.05, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 5])
                else:
                    risolto = True
            else:
                if not result_sent:
                    send_puzzle_result(token, puz.get("id"), win=False)
                    result_sent = True
                Acusticator(["a3", 0.15, 0, config.VOLUME], kind=2, adsr=[5, 20, 0, 75])
                print(_("Mossa errata, riprova."))
                
        if risolto:
            if not result_sent:
                send_puzzle_result(token, puz.get("id"), win=True)
                result_sent = True
            Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.1, 0.5, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
            print(_("\nCongratulazioni! Hai risolto il puzzle!"))
            end_time = time.time()
            elapsed = int(end_time - start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            print(_("Tempo impiegato: {t}").format(t=time_str))
            enter_escape(_("Premi Invio per continuare..."))

def fetch_user_profile(username, token=None):
    req = urllib.request.Request(f"https://lichess.org/api/user/{username}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception:
        pass
    return None

def menu_guarda(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    
    while True:
        print(_("\n=================================="))
        print(_("          GUARDA PARTITA"))
        print(_("=================================="))
        scelte = {
            "id": _("Inserisci ID o URL Partita"),
            "giocatore": _("Inserisci Nome Utente Lichess"),
            "amico": _("Scegli un Amico"),
            "tv": _("Lichess TV (Migliori in corso)"),
            ".": _("Torna al menu Lichess")
        }
        
        scelta = menu(scelte, show=True, keyslist=True, p=_("\nScegli un'opzione: "), numbered=db.get("menu_numerati", False))
        
        if scelta == ".":
            break
            
        elif scelta == "id":
            val = dgt(_("\nID o URL della partita: ")).strip()
            if not val: continue
            if "lichess.org/" in val:
                val = val.split("lichess.org/")[-1].split("/")[0][:8]
            lichess_spectator.spectate_game(val, token)
            
        elif scelta == "giocatore":
            val = dgt(_("\nNome Utente: ")).strip()
            if not val: continue
            print(_("Controllo se l'utente e' in gioco..."))
            profile = fetch_user_profile(val, token)
            if profile and "playing" in profile:
                game_url = profile["playing"]
                game_id = game_url.split("/")[-1][:8]
                lichess_spectator.spectate_game(game_id, token)
            elif profile:
                print(_("L'utente non ha partite in corso in questo momento."))
            else:
                print(_("Utente non trovato o errore di connessione."))
                
        elif scelta == "amico":
            if not token:
                print(_("Devi aver fatto il login per vedere gli amici."))
                continue
            print(_("Recupero lista degli amici in corso..."))
            following = fetch_following(token)
            playing_friends = [f for f in following if "playing" in f]
            if not playing_friends:
                print(_("Nessun amico sta giocando in questo momento."))
                continue
                
            scelte_amici = {f["id"]: f["username"] for f in playing_friends}
            scelte_amici["."] = _("Indietro")
            amico_scelto = menu(scelte_amici, show=True, keyslist=True, p=_("\nScegli un amico da guardare: "))
            if amico_scelto != ".":
                f_obj = next(f for f in playing_friends if f["id"] == amico_scelto)
                game_url = f_obj["playing"]
                game_id = game_url.split("/")[-1][:8]
                lichess_spectator.spectate_game(game_id, token)
                
        elif scelta == "tv":
            print(_("Recupero canali TV in corso..."))
            req = urllib.request.Request("https://lichess.org/api/tv/channels")
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                print(_("Errore recupero TV: {e}").format(e=e))
                continue
            
            scelte_tv = {}
            for k, v in data.items():
                user_name = v.get("user", {}).get("name", "Anonimo")
                rating = v.get("rating", "?")
                scelte_tv[k] = f"{k.capitalize()} ({user_name} - Elo: {rating})"
            scelte_tv["."] = _("Indietro")
            
            canale_scelto = menu(scelte_tv, show=True, keyslist=True, p=_("\nScegli canale: "), numbered=db.get("menu_numerati", False))
            if canale_scelto != ".":
                game_id = data[canale_scelto]["gameId"]
                lichess_spectator.spectate_game(game_id, token)

def menu_gioca(db):
    print(_("\n[WIP] Interfaccia per avviare una nuova partita su Lichess o accettare sfide."))

def run():
    """Entry point principale di Orolichess integrato in orologic."""
    db = storage.LoadDB()
    secrets = load_secrets()
    
    # Fetch iniziale del profilo per ottenere Elo aggiornato se già loggati
    rating_info = ""
    puzzle_games = None
    token = secrets.get("lichess_token")
    if token:
        print(_("Connessione a Lichess in corso..."))
        profile = fetch_profile_info(token)
        if profile:
            username = profile.get("username", secrets.get("lichess_username", "Utente"))
            secrets["lichess_username"] = username
            rating_info = format_ratings(profile.get("perfs", {}))
            if "perfs" in profile and "puzzle" in profile["perfs"]:
                puzzle_games = profile["perfs"]["puzzle"].get("games")
            save_secrets(secrets)
    
    while True:
        # Costruiamo il menu dinamicamente in base allo stato del login
        MENU_CHOICES = {}
        
        secrets = load_secrets()
        is_logged = "lichess_token" in secrets
        
        if is_logged:
            MENU_CHOICES["logout"] = _("Logout (Rimuovi token)")
        else:
            MENU_CHOICES["login"] = _("Login (Imposta API Token)")
            
        testo_puzzle = _("Risolvi puzzle")
        if puzzle_games is not None:
            testo_puzzle += _(" (Partite: {p})").format(p=puzzle_games)
            
        MENU_CHOICES.update({
            "profilo": _("Profilo Lichess"),
            "statistiche": _("Statistiche utente"),
            "amici": _("Gestione Amici"),
            "puzzle": testo_puzzle,
            "guarda": _("Guarda una partita"),
            "gioca": _("Gioca una partita"),
            ".": _("Ritorna a Orologic (Esci)")
        })
        
        if is_logged:
            username = secrets.get("lichess_username", "Utente")
            print(_("\n--- OROLICHESS --- CONNESSO COME: {username}{rating} ---").format(username=username, rating=rating_info))
        else:
            print(_("\n--- OROLICHESS --- DISCONNESSO (Seleziona Login per iniziare) ---"))
            
        scelta = menu(MENU_CHOICES, show=True, keyslist=True, p=_("\nScegli un'azione: "), numbered=db.get("menu_numerati", False))
        
        if scelta == ".":
            print(_("Uscita da Orolichess in corso. Ritorno a orologic..."))
            break
        elif scelta == "login":
            new_profile = menu_login(db)
            if new_profile:
                rating_info = format_ratings(new_profile.get("perfs", {}))
        elif scelta == "logout":
            if menu_logout(db):
                rating_info = ""
        elif scelta == "profilo":
            menu_profilo(db)
        elif scelta == "statistiche":
            menu_statistiche(db)
        elif scelta == "amici":
            menu_amici(db)
        elif scelta == "puzzle":
            menu_puzzle(db)
        elif scelta == "guarda":
            menu_guarda(db)
        elif scelta == "gioca":
            menu_gioca(db)

if __name__ == "__main__":
    run()
