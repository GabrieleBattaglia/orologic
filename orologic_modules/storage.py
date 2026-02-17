import json
import os
from . import config

def LoadDB():
    """Carica il database (impostazioni e orologi)."""
    if not os.path.exists(config.DB_FILE):
        return {"clocks": [], "menu_numerati": False}
    try:
        with open(config.DB_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"clocks": [], "menu_numerati": False}

def SaveDB(db):
    """Salva il database su file JSON."""
    try:
        os.makedirs(os.path.dirname(config.DB_FILE), exist_ok=True)
        with open(config.DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
        # print(f"[DEBUG] DB salvato in: {config.DB_FILE}") # Scommentare se serve debug
    except IOError as e:
        print(f"Errore nel salvataggio del DB: {e}")
