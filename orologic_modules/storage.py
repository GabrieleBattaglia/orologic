# Orologic, modulo storage: accesso al database delle impostazioni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import contextlib
import copy
import datetime
import json
import os
import tempfile
import threading
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
    "analysis_thresholds": {
        "inesattezza": 50,
        "errore": 100,
        "svarione": 250,
        "mossa_buona": 20,
        "mossa_geniale_gap": 180,
        # Il giudizio dell'OAA dal calo della probabilita' di vittoria, in
        # punti percentuali, come Lichess (Gabriele, 23 novembre 2026):
        # inesattezza, errore e svarione al 5, 10 e 15. Le tre soglie in
        # centesimi di prima restano solo per chi ha un database vecchio.
        "calo_inesattezza": 5,
        "calo_errore": 10,
        "calo_svarione": 15,
    },
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
    """Completa una fase di orologio con i valori mancanti.

    Dalla finestra degli orologi una fase ha anche la tipologia del
    controllo, un testo, e i valori della tipologia per ogni colore,
    numeri con white_ o black_ davanti: si conservano. Quale tipologia e
    quali valori siano validi lo dice controlli.py, quando la fase si usa.
    """
    if not isinstance(fase, dict):
        return dict(DEFAULT_PHASE)
    pulita = {}
    for chiave, ripiego in DEFAULT_PHASE.items():
        pulita[chiave] = _numero(fase.get(chiave), ripiego)
    if isinstance(fase.get("tipo"), str):
        pulita["tipo"] = fase["tipo"]
    for chiave, valore in fase.items():
        if chiave not in pulita and chiave.startswith(("white_", "black_")):
            numero = _numero(valore, None)
            if numero is not None:
                pulita[chiave] = numero
    return pulita


def data_di_adesso():
    """Il momento attuale come lo salva il database: data e ora ai minuti."""
    return datetime.datetime.now().isoformat(timespec="minutes")


def _data_di_creazione(valore):
    """Restituisce la data di creazione se leggibile, altrimenti quella di adesso.

    Gli orologi nati prima del tachimetro non la conoscono: prendono il
    momento in cui il database viene letto la prima volta, che LoadDB
    salva subito, cosi' da quel giorno in poi resta quella.
    """
    if isinstance(valore, str):
        try:
            if datetime.datetime.fromisoformat(valore).tzinfo is None:
                return valore
        except ValueError:
            pass
    return data_di_adesso()


def _normalizza_orologio(orologio):
    """Completa un orologio salvato. Restituisce None se non e' recuperabile.

    Data di creazione e secondi di corsa li scrive il programma, senza
    chiederli all'utente: qui si garantisce solo che ci siano e che siano
    leggibili.
    """
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
        "created": _data_di_creazione(orologio.get("created")),
        "run_seconds": max(0, int(_numero(orologio.get("run_seconds"), 0))),
    }


def _normalizza(db):
    """Garantisce chiavi e tipi attesi, conservando tutto il resto.

    Restituisce la terna (db normalizzato, numero di orologi scartati,
    numero di orologi a cui sono stati completati data di creazione o
    secondi di corsa).
    """
    if not isinstance(db, dict):
        # Una copia profonda, come _predefiniti (R97).
        return copy.deepcopy(DEFAULT_DB), 0, 0
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
    db["volume"] = min(1.0, max(0.0, _numero(db.get("volume"), 1.0)))
    db["launch_count"] = int(_numero(db.get("launch_count"), 0))
    db["default_analysis_time"] = _numero(db.get("default_analysis_time"), 1.0)
    db["default_multipv"] = int(_numero(db.get("default_multipv"), 3))
    orologi = db.get("clocks")
    if not isinstance(orologi, list):
        orologi = []
    validi = []
    scartati = 0
    completati = 0
    for orologio in orologi:
        normalizzato = _normalizza_orologio(orologio)
        if normalizzato is None:
            scartati += 1
            continue
        completato = normalizzato["created"] != orologio.get("created") or (
            normalizzato["run_seconds"] != orologio.get("run_seconds")
        )
        if completato:
            completati += 1
        validi.append(normalizzato)
    db["clocks"] = validi
    return db, scartati, completati


def metti_da_parte(percorso):
    """Sposta un file illeggibile invece di lasciarlo sovrascrivere.

    Il nome porta la data, cosi' i tentativi successivi non si pestano i
    piedi. Restituisce il percorso della copia, oppure nulla se non c'e'
    stato modo di spostarla.
    """
    marca = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    destinazione = f"{percorso}.danneggiato-{marca}"
    try:
        os.replace(percorso, destinazione)
        return destinazione
    except OSError:
        return None


def riporta_i_file_dell_utente(vecchia, nuova, del_programma=None):
    """Dopo che la cartella nuova di un programma scaricato ha preso il posto
    della vecchia, riporta nella nuova i file che stavano nella vecchia e
    nella nuova non ci sono, tranne quelli che del_programma(relativo)
    riconosce come parte del programma di prima. Prima l'installazione
    cancellava la cartella intera, e un altro motore, i suoi pesi o i libri
    messi li' dall'utente sparivano senza cestino (R36). Si guarda anche
    dentro le sottocartelle, file per file: un libro messo nella sottocartella
    del programma spariva con la cartella vecchia (R109). Restituisce
    (riportati, rimasti): i percorsi relativi spostati e quelli che non si
    sono potuti spostare."""
    riportati, rimasti = [], []
    for radice, _cartelle, nomi in os.walk(vecchia):
        for nome in nomi:
            sorgente = os.path.join(radice, nome)
            relativo = os.path.relpath(sorgente, vecchia)
            arrivo = os.path.join(nuova, relativo)
            if os.path.exists(arrivo) or (del_programma is not None and del_programma(relativo)):
                continue
            try:
                os.makedirs(os.path.dirname(arrivo), exist_ok=True)
                os.replace(sorgente, arrivo)
                riportati.append(relativo)
            except OSError:
                rimasti.append(relativo)
    return riportati, rimasti


def _salva_copia_danneggiata():
    """Mette da parte un database illeggibile invece di sovrascriverlo."""
    return metti_da_parte(config.DB_FILE)


# Il lucchetto del database: scrivono il nucleo, la finestra, con le
# impostazioni aperte in ogni momento, e il filo del motore (R29 della
# revisione 2, 26 novembre 2026).
_LUCCHETTO = threading.RLock()
# Un database che non si lascia leggere, tenuto un momento da un antivirus
# o da un programma di sincronizzazione, si riprova prima di arrendersi (R7).
TENTATIVI_DI_LETTURA = 10
PAUSA_FRA_I_TENTATIVI = 0.1
# Gli avvisi della lettura silenziosa, quella dell'importazione, che nella
# finestra andrebbero nel vuoto: Main li dice dopo il benvenuto (R31).
_SILENZIOSA = {"attiva": False}
_AVVISI_IN_SOSPESO = []


def _di(testo):
    """Un avviso della lettura: a schermo, o da parte se la lettura e'
    silenziosa."""
    if _SILENZIOSA["attiva"]:
        _AVVISI_IN_SOSPESO.append(testo)
    else:
        print(testo)


def avvisi_in_sospeso():
    """Gli avvisi messi da parte dalle letture silenziose, una volta sola.
    Se intanto il database e' tornato leggibile, l'avviso che le modifiche
    non si salvano non vale piu', e si dice che ora si salvano: prima si
    diceva il falso, a salvataggio gia' riuscito (R135)."""
    with _LUCCHETTO:
        avvisi = list(_AVVISI_IN_SOSPESO)
        _AVVISI_IN_SOSPESO.clear()
        riuscita = _ULTIMA_LETTURA["riuscita"]
    non_si_salvano = _("Le modifiche non si salvano finche' il database non torna leggibile.")
    if riuscita and non_si_salvano in avvisi:
        avvisi = [avviso for avviso in avvisi if avviso != non_si_salvano]
        avvisi.append(_("Ora il database si legge di nuovo, e le modifiche si salvano."))
    return avvisi


# Com'e' andata l'ultima lettura del database (R135).
_ULTIMA_LETTURA = {"riuscita": True}


class DatabaseNonLetto(dict):
    """I predefiniti al posto di un database che c'e' ma non si e' potuto
    leggere, o che non si e' potuto mettere da parte: SaveDB non li scrive,
    per non coprire il database vero. Prima un solo errore di lettura
    metteva da parte il database buono come danneggiato, e i predefiniti
    lo sostituivano (R7)."""


class DatabasePredefinito(dict):
    """I predefiniti al posto di un database che manca, o che e' guasto,
    senza una copia buona da cui ripartire: SaveDB li scrive nel database ma
    non nella copia di riserva, che puo' tenere ancora i dati veri (R108)."""


def _predefiniti():
    # Una copia profonda: con dict(DEFAULT_DB) gli orologi aggiunti finivano
    # nella lista dei predefiniti stessi.
    return copy.deepcopy(DEFAULT_DB)


def copia_di_riserva():
    """L'ultimo database scritto per intero, che LoadDB riprende se il file
    vero si guasta (R30)."""
    return config.DB_FILE + ".bak"


# Le letture fallite di recente, per file: la lettura dopo non dorme, perche'
# i tentativi dormivano col lucchetto preso a ogni lettura, finche' il file
# restava illeggibile (R136).
_LETTURE_FALLITE = {}
FALLITA_DI_RECENTE = 10


def _leggi(percorso):
    """Il contenuto JSON del file. Un errore di lettura si riprova, ma una
    volta sola se la lettura e' fallita da poco; un JSON non valido solleva
    ValueError subito, e un file che manca subito FileNotFoundError."""
    di_recente = time.monotonic() - _LETTURE_FALLITE.get(percorso, float("-inf")) < FALLITA_DI_RECENTE
    tentativi = 1 if di_recente else TENTATIVI_DI_LETTURA
    for tentativo in range(tentativi):
        try:
            with open(percorso, encoding="utf-8") as f:
                dati = json.load(f)
            _LETTURE_FALLITE.pop(percorso, None)
            return dati
        except FileNotFoundError:
            raise
        except OSError:
            if tentativo == tentativi - 1:
                _LETTURE_FALLITE[percorso] = time.monotonic()
                raise
            time.sleep(PAUSA_FRA_I_TENTATIVI)
    return None


def _dalla_riserva():
    """Il database dell'ultima copia buona; None se non c'e' o e' guasta.
    Un errore di lettura risale: la copia c'e', e i predefiniti scritti al
    suo posto la coprivano (R108)."""
    try:
        dati = _leggi(copia_di_riserva())
    except (FileNotFoundError, ValueError):
        return None
    return dati if isinstance(dati, dict) else None


def _riserva_illeggibile(errore):
    """La copia di riserva c'e' ma non si lascia leggere: niente si scrive,
    per non coprirla."""
    _di(_("Nemmeno l'ultima copia buona si lascia leggere: {errore}").format(errore=errore))
    _di(_("Le modifiche non si salvano finche' il database non torna leggibile."))
    return DatabaseNonLetto(_predefiniti())


def _dalla_riserva_se_manca():
    """Il database che manca: dall'ultima copia buona, se c'e', dicendolo, e
    rimesso al suo posto; altrimenti i predefiniti. Prima i predefiniti, e
    il primo salvataggio copriva anche la riserva (R108)."""
    try:
        riserva = _dalla_riserva()
    except OSError as e:
        return _riserva_illeggibile(e)
    if riserva is None:
        return DatabasePredefinito(_predefiniti())
    _di(_("Il database delle impostazioni manca."))
    _di(_("Riparto dall'ultima copia buona: {percorso}").format(percorso=copia_di_riserva()))
    db, _scartati, _completati = _normalizza(riserva)
    SaveDB(db)
    return db


def _da_danneggiato(errore):
    """Il database da usare al posto di uno danneggiato, che va da parte."""
    copia = _salva_copia_danneggiata()
    _di(_("Il database delle impostazioni non e' leggibile: {errore}").format(errore=errore))
    if not copia:
        _di(_("Attenzione: non sono riuscita a metterne da parte una copia."))
        _di(_("Le modifiche non si salvano finche' il database non torna leggibile."))
        return DatabaseNonLetto(_predefiniti())
    _di(_("Ne ho messo da parte una copia in {percorso}").format(percorso=copia))
    try:
        riserva = _dalla_riserva()
    except OSError as e:
        return _riserva_illeggibile(e)
    if riserva is not None:
        _di(_("Riparto dall'ultima copia buona: {percorso}").format(percorso=copia_di_riserva()))
        db, _scartati, _completati = _normalizza(riserva)
        SaveDB(db)
        return db
    _di(_("Riparto dalle impostazioni predefinite, gli orologi salvati non sono andati perduti nella copia."))
    return DatabasePredefinito(_predefiniti())


def LoadDB(silenziosa=False):
    """Carica il database, completando le chiavi mancanti.

    Un database illeggibile non viene mai perso in silenzio: viene messo da
    parte con la data nel nome e l'utente ne viene avvisato a schermo; se
    c'e', si riparte dall'ultima copia buona. Un file che c'e' ma non si
    lascia leggere non e' danneggiato: si riprova, e se non si legge si
    usano i predefiniti senza scriverli. silenziosa, per la lettura
    dell'importazione, mette gli avvisi da parte per avvisi_in_sospeso.
    """
    with _LUCCHETTO:
        prima = _SILENZIOSA["attiva"]
        _SILENZIOSA["attiva"] = silenziosa or prima
        try:
            db = _carica()
            riuscita = not isinstance(db, DatabaseNonLetto)
            tornato = riuscita and (not _ULTIMA_LETTURA["riuscita"] or not getattr(config, "VOLUME_LETTO", True))
            _ULTIMA_LETTURA["riuscita"] = riuscita
            if tornato:
                _quando_torna_leggibile(db)
            return db
        finally:
            _SILENZIOSA["attiva"] = prima


def _quando_torna_leggibile(db):
    """Il database prima illeggibile ora si legge: il volume e i nomi, presi
    coi predefiniti all'avvio, prendono i valori veri. Prima restavano
    quelli predefiniti per tutta la sessione (R136)."""
    import sys

    config.VOLUME_LETTO = True
    with contextlib.suppress(TypeError, ValueError):
        config.VOLUME = min(1.0, max(0.0, float(db.get("volume", config.VOLUME))))
    localizzazione = sys.modules.get(__package__ + ".localizzazione")
    if localizzazione is not None and isinstance(db.get("localization"), dict):
        nuovo = localizzazione.unisci(localizzazione.predefinito(), localizzazione.sfoltisci(db["localization"]))
        localizzazione.L10N.clear()
        localizzazione.L10N.update(nuovo)


def _carica():
    if not os.path.exists(config.DB_FILE):
        return _dalla_riserva_se_manca()
    try:
        dati = _leggi(config.DB_FILE)
    except FileNotFoundError:
        return _dalla_riserva_se_manca()
    except OSError as e:
        _di(_("Il database delle impostazioni non si lascia leggere: {errore}").format(errore=e))
        _di(_("Le modifiche non si salvano finche' il database non torna leggibile."))
        return DatabaseNonLetto(_predefiniti())
    except ValueError as e:
        return _da_danneggiato(e)
    # Un JSON valido che non e' un oggetto e' un database guasto come gli
    # altri: prima i predefiniti lo sostituivano senza un avviso (R30).
    if not isinstance(dati, dict):
        return _da_danneggiato(_("non contiene le impostazioni"))
    db, scartati, completati = _normalizza(dati)
    if scartati:
        _di(_("Ho ignorato {numero} orologi salvati perche' incompleti.").format(numero=scartati))
    if completati:
        # Gli orologi nati prima del tachimetro hanno appena ricevuto data
        # di creazione e secondi di corsa: si salvano subito, una volta
        # sola, altrimenti la data cambierebbe a ogni lettura.
        SaveDB(db)
    return db


def scrivi_json(percorso, dati, indent=4):
    """Scrive un file JSON in modo atomico.

    Il contenuto va prima su un file temporaneo, che prende il posto di
    quello buono solo a scrittura conclusa: un'interruzione non lascia
    mai un file troncato. In caso di guai il temporaneo viene rimosso e
    l'errore risale al chiamante, che sa cosa dire all'utente.
    """
    cartella = os.path.dirname(percorso)
    if cartella:
        os.makedirs(cartella, exist_ok=True)
    _togli_i_provvisori_vecchi(percorso)
    # Un temporaneo col suo nome a ogni scrittura: con un nome fisso due
    # fili che salvavano insieme si scambiavano il file (R29).
    descrittore, temporaneo = tempfile.mkstemp(prefix=os.path.basename(percorso) + ".", suffix=".tmp", dir=cartella or None)
    try:
        with os.fdopen(descrittore, "w", encoding="utf-8") as f:
            json.dump(dati, f, indent=indent, ensure_ascii=False)
            # Su disco prima della sostituzione: dopo uno spegnimento brusco
            # il file non resta vuoto (R30).
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporaneo, percorso)
    except (OSError, TypeError, ValueError):
        with contextlib.suppress(OSError):
            os.remove(temporaneo)
        raise


# I file provvisori della scrittura piu' vecchi di tanto sono di una
# scrittura interrotta, e se ne vanno (R136).
PROVVISORIO_VECCHIO = 600
# I tentativi di scrittura, come quelli di lettura: un file tenuto un
# momento da un antivirus non fa perdere il salvataggio (R136).
TENTATIVI_DI_SCRITTURA = 3
# Com'e' andato l'ultimo SaveDB di ogni filo: chi dice salvato lo chiede
# (R136).
_ULTIMO_SALVATAGGIO = threading.local()


def _togli_i_provvisori_vecchi(percorso):
    """I provvisori di una scrittura interrotta dello stesso file, rimasti
    nella cartella: un'interruzione li lasciava, e nessuno li toglieva."""
    cartella = os.path.dirname(percorso) or "."
    prefisso = os.path.basename(percorso) + "."
    try:
        nomi = os.listdir(cartella)
    except OSError:
        return
    adesso = time.time()
    for nome in nomi:
        if not (nome.startswith(prefisso) and nome.endswith(".tmp")):
            continue
        provvisorio = os.path.join(cartella, nome)
        with contextlib.suppress(OSError):
            if adesso - os.path.getmtime(provvisorio) > PROVVISORIO_VECCHIO:
                os.remove(provvisorio)


def salvataggio_riuscito():
    """Vero se l'ultimo salvataggio del database, in questo filo, e'
    riuscito: prima UpdateDB e SetValue ne buttavano l'esito, e chi li
    chiamava diceva salvato quando non lo era (R136)."""
    return getattr(_ULTIMO_SALVATAGGIO, "riuscito", False)


def SaveDB(db):
    """Salva il database in modo atomico.

    Restituisce vero se il salvataggio e' andato a buon fine, e lo ricorda
    per salvataggio_riuscito. Il database salvato va anche nella copia di
    riserva (R30). I predefiniti dati al posto di un database che non si e'
    letto non si scrivono (R7). Un errore di scrittura si riprova (R136).
    """
    _ULTIMO_SALVATAGGIO.riuscito = False
    if isinstance(db, DatabaseNonLetto):
        print(_("Modifica non salvata: il database delle impostazioni non si e' potuto leggere."))
        return False
    with _LUCCHETTO:
        for tentativo in range(TENTATIVI_DI_SCRITTURA):
            try:
                scrivi_json(config.DB_FILE, db)
                break
            except OSError as e:
                if tentativo == TENTATIVI_DI_SCRITTURA - 1:
                    print(_("Errore nel salvataggio del database: {errore}").format(errore=e))
                    return False
                time.sleep(PAUSA_FRA_I_TENTATIVI)
            except (TypeError, ValueError) as e:
                print(_("Errore nel salvataggio del database: {errore}").format(errore=e))
                return False
        # Un database nato dai predefiniti non copre la riserva (R108).
        if not isinstance(db, DatabasePredefinito):
            with contextlib.suppress(OSError, TypeError, ValueError):
                scrivi_json(copia_di_riserva(), db)
        _ULTIMO_SALVATAGGIO.riuscito = True
        return True


def UpdateDB(modifica):
    """Ricarica il database dal disco, applica la modifica e salva.

    E' il modo corretto di scrivere nel database: ricaricando subito prima
    della scrittura, le modifiche fatte nel frattempo da altre parti del
    programma non vengono sovrascritte.
    La funzione ricevuta modifica il dizionario sul posto; se restituisce un
    dizionario, viene usato quello. Restituisce il database aggiornato.
    """
    with _LUCCHETTO:
        db = LoadDB()
        # LoadDB ha gia' detto che il database non si e' letto.
        non_letto = isinstance(db, DatabaseNonLetto)
        risultato = modifica(db)
        if isinstance(risultato, dict):
            db = risultato
        if non_letto:
            _ULTIMO_SALVATAGGIO.riuscito = False
        else:
            SaveDB(db)
        return db


def SetValue(chiave, valore):
    """Scorciatoia per aggiornare una sola voce del database senza perdere il resto."""

    def modifica(db):
        db[chiave] = valore

    return UpdateDB(modifica)
