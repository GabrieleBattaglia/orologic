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

def menu_profilo(db):
    print(_("\n[WIP] Qui verra' mostrato il profilo utente e il rating (se il login e' effettuato)."))

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
        elif scelta == "puzzle":
            menu_puzzle(db)
        elif scelta == "guarda":
            menu_guarda(db)
        elif scelta == "gioca":
            menu_gioca(db)

if __name__ == "__main__":
    run()
