# Orologic, modulo storage: accesso al database delle impostazioni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import json
import os
import time

from . import config
from .config import _

# Struttura minima garantita del database. Le chiavi non elencate qui vengono
# comunque conservate: la normalizzazione aggiunge, non cancella.
DEFAULT_DB = {
    "db_version": 1,
    "clocks": [],
    "menu_numerati": False,
    "volume": 1.0,
    "launch_count": 0,
    "autosave_enabled": False,
    "default_analysis_time": 1.0,
    "default_multipv": 3,
    "analysis_thresholds": {"inesattezza": 50, "errore": 100, "svarione": 250},
    "engine_config": {},
    "localization": {},
    "image_settings": {},
    "default_pgn": {},
}

# Chiavi non piu' usate, rimosse a ogni caricamento. lichess_token e
# lichess_username vivono solo in settings/secrets.json, che resta locale e
# fuori dal repository: il database invece viene condiviso fra le macchine,
# quindi qui dentro un token non deve mai comparire. engine_path alla radice
# e' l'antenato di engine_config e nessuno la legge piu'.
CHIAVI_OBSOLETE = ("engine_path", "lichess_token", "lichess_username")

# Valori minimi garantiti per ogni fase di un orologio.
DEFAULT_PHASE = {
    "white_time": 0,
    "black_time": 0,
    "white_inc": 0,
    "black_inc": 0,
    "moves": 0,
}


def _numero(valore, ripiego):
    """Restituisce valore se e' un numero utilizzabile, altrimenti ripiego."""
    if isinstance(valore, bool):
        return ripiego
    if isinstance(valore, (int, float)):
        return valore
    return ripiego


def _normalizza_fase(fase):
    """Completa una fase di orologio con i valori mancanti."""
    if not isinstance(fase, dict):
        return dict(DEFAULT_PHASE)
    pulita = {}
    for chiave, ripiego in DEFAULT_PHASE.items():
        pulita[chiave] = _numero(fase.get(chiave), ripiego)
    return pulita


def _normalizza_orologio(orologio):
    """Completa un orologio salvato. Restituisce None se non e' recuperabile."""
    if not isinstance(orologio, dict):
        return None
    nome = orologio.get("name")
    if not isinstance(nome, str) or not nome.strip():
        return None
    fasi = orologio.get("phases")
    if not isinstance(fasi, list) or not fasi:
        return None
    allarmi = orologio.get("alarms")
    if not isinstance(allarmi, list):
        allarmi = []
    nota = orologio.get("note")
    if not isinstance(nota, str):
        nota = ""
    return {
        "name": nome,
        "same_time": bool(orologio.get("same_time", True)),
        "phases": [_normalizza_fase(f) for f in fasi],
        "alarms": [a for a in allarmi if isinstance(a, (int, float))],
        "note": nota,
    }


def _normalizza(db):
    """Garantisce chiavi e tipi attesi, conservando tutto il resto.

    Restituisce la coppia (db normalizzato, numero di orologi scartati).
    """
    if not isinstance(db, dict):
        return dict(DEFAULT_DB), 0
    for chiave in CHIAVI_OBSOLETE:
        db.pop(chiave, None)
    for chiave, ripiego in DEFAULT_DB.items():
        if chiave not in db:
            db[chiave] = (
                ripiego.copy() if isinstance(ripiego, (dict, list)) else ripiego
            )
    for chiave in ("engine_config", "localization", "image_settings", "default_pgn"):
        if not isinstance(db[chiave], dict):
            db[chiave] = {}
    soglie = db.get("analysis_thresholds")
    if not isinstance(soglie, dict):
        soglie = {}
    for nome, ripiego in DEFAULT_DB["analysis_thresholds"].items():
        soglie[nome] = _numero(soglie.get(nome), ripiego)
    db["analysis_thresholds"] = soglie
    db["menu_numerati"] = bool(db.get("menu_numerati", False))
    db["autosave_enabled"] = bool(db.get("autosave_enabled", False))
    db["volume"] = _numero(db.get("volume"), 1.0)
    db["launch_count"] = int(_numero(db.get("launch_count"), 0))
    db["default_analysis_time"] = _numero(db.get("default_analysis_time"), 1.0)
    db["default_multipv"] = int(_numero(db.get("default_multipv"), 3))
    orologi = db.get("clocks")
    if not isinstance(orologi, list):
        orologi = []
    validi = []
    scartati = 0
    for orologio in orologi:
        normalizzato = _normalizza_orologio(orologio)
        if normalizzato is None:
            scartati += 1
        else:
            validi.append(normalizzato)
    db["clocks"] = validi
    return db, scartati


def _salva_copia_danneggiata():
    """Mette da parte un database illeggibile invece di sovrascriverlo.

    Restituisce il percorso della copia, oppure None se non e' stato possibile.
    """
    marca = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    destinazione = f"{config.DB_FILE}.danneggiato-{marca}"
    try:
        os.replace(config.DB_FILE, destinazione)
        return destinazione
    except OSError:
        return None


def LoadDB():
    """Carica il database, completando le chiavi mancanti.

    Un database illeggibile non viene mai perso in silenzio: viene messo da
    parte con la data nel nome e l'utente ne viene avvisato a schermo.
    """
    if not os.path.exists(config.DB_FILE):
        return dict(DEFAULT_DB)
    try:
        with open(config.DB_FILE, "r", encoding="utf-8") as f:
            dati = json.load(f)
    except (OSError, ValueError) as e:
        copia = _salva_copia_danneggiata()
        print(
            _("Il database delle impostazioni non e' leggibile: {errore}").format(
                errore=e
            )
        )
        if copia:
            print(
                _("Ne ho messo da parte una copia in {percorso}").format(percorso=copia)
            )
            print(
                _(
                    "Riparto dalle impostazioni predefinite, gli orologi salvati non sono andati perduti nella copia."
                )
            )
        else:
            print(_("Attenzione: non sono riuscita a metterne da parte una copia."))
        return dict(DEFAULT_DB)
    db, scartati = _normalizza(dati)
    if scartati:
        print(
            _("Ho ignorato {numero} orologi salvati perche' incompleti.").format(
                numero=scartati
            )
        )
    return db


def SaveDB(db):
    """Salva il database in modo atomico.

    Scrive prima su un file temporaneo e lo sostituisce solo a scrittura
    riuscita, cosi' un'interruzione non lascia mai il database a meta'.
    Restituisce vero se il salvataggio e' andato a buon fine.
    """
    temporaneo = config.DB_FILE + ".tmp"
    try:
        os.makedirs(os.path.dirname(config.DB_FILE), exist_ok=True)
        with open(temporaneo, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        os.replace(temporaneo, config.DB_FILE)
        return True
    except (OSError, TypeError, ValueError) as e:
        print(_("Errore nel salvataggio del database: {errore}").format(errore=e))
        try:
            if os.path.exists(temporaneo):
                os.remove(temporaneo)
        except OSError:
            pass
        return False


def UpdateDB(modifica):
    """Ricarica il database dal disco, applica la modifica e salva.

    E' il modo corretto di scrivere nel database: ricaricando subito prima
    della scrittura, le modifiche fatte nel frattempo da altre parti del
    programma non vengono sovrascritte.
    La funzione ricevuta modifica il dizionario sul posto; se restituisce un
    dizionario, viene usato quello. Restituisce il database aggiornato.
    """
    db = LoadDB()
    risultato = modifica(db)
    if isinstance(risultato, dict):
        db = risultato
    SaveDB(db)
    return db


def SetValue(chiave, valore):
    """Scorciatoia per aggiornare una sola voce del database senza perdere il resto."""

    def modifica(db):
        db[chiave] = valore

    return UpdateDB(modifica)
