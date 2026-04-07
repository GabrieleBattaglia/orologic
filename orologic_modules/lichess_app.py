import os
import json
import urllib.request
import urllib.error
import webbrowser
from GBUtils import menu, enter_escape
from . import storage
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
    except Exception as e:
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
            valid_modes[mode] = _("{m} (Partite: {g})").format(m=mode.capitalize(), g=data["games"])
            
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

def menu_amici(db):
    print(_("\n[WIP] Interfaccia per la gestione amici e messaggistica."))

def menu_puzzle(db):
    print(_("\n[WIP] Qui si interfaccerà con l'API dei puzzle di Lichess."))

def menu_guarda(db):
    print(_("\n[WIP] Qui si potra' seguire una partita in corso o caricare il PGN di una passata."))

def menu_gioca(db):
    print(_("\n[WIP] Interfaccia per avviare una nuova partita su Lichess o accettare sfide."))

def run():
    """Entry point principale di Orolichess integrato in orologic."""
    db = storage.LoadDB()
    secrets = load_secrets()
    
    # Fetch iniziale del profilo per ottenere Elo aggiornato se già loggati
    rating_info = ""
    token = secrets.get("lichess_token")
    if token:
        print(_("Connessione a Lichess in corso..."))
        profile = fetch_profile_info(token)
        if profile:
            username = profile.get("username", secrets.get("lichess_username", "Utente"))
            secrets["lichess_username"] = username
            rating_info = format_ratings(profile.get("perfs", {}))
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
            
        MENU_CHOICES.update({
            "profilo": _("Profilo Lichess"),
            "statistiche": _("Statistiche utente"),
            "amici": _("Gestione Amici"),
            "puzzle": _("Risolvi puzzle"),
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
