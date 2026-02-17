# OROLOGIC - Modular Version
# Data di concepimento: 14/02/2025 by Gabriele Battaglia & AIs

import sys
import os
import datetime
import webbrowser
from dateutil.relativedelta import relativedelta
from GBUtils import polipo, menu, Acusticator, key, dgt, Donazione
from orologic_modules import config, storage, ui, clock, engine, game_flow, version, board_utils

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

# Variabili globali per il glue code
volume = 1.0
STILE_MENU_NUMERICO = False

def OpenManual():
    print(_("\nApertura manuale\n"))
    readme_path = config.resource_path(os.path.join("resources", "readme.htm"))
    if os.path.exists(readme_path):
        webbrowser.open("file://" + os.path.realpath(readme_path))
    else:
        print(_("Il file {path} non esiste.").format(path=readme_path))

def SchermataIniziale():
    now = datetime.datetime.now()
    diff1 = relativedelta(now, version.BIRTH_DATE)
    diff2 = relativedelta(now, version.RELEASE_DATE)
    parts1 = []
    if diff1.years:
        parts1.append(_("{num} anni").format(num=diff1.years))
    if diff1.months:
        parts1.append(_("{num} mesi").format(num=diff1.months))
    if diff1.days:
        parts1.append(_("{num} giorni").format(num=diff1.days))
    if diff1.hours:
        parts1.append(_("{num} ore").format(num=diff1.hours))
    if diff1.minutes:
        parts1.append(_("e {num} minuti").format(num=diff1.minutes))
    age_string = ", ".join(parts1)
    parts2 = []
    if diff2.years:
        parts2.append(_("{num} anni").format(num=diff2.years))
    if diff2.months:
        parts2.append(_("{num} mesi").format(num=diff2.months))
    if diff2.days:
        parts2.append(_("{num} giorni").format(num=diff2.days))
    if diff2.hours:
        parts2.append(_("{num} ore").format(num=diff2.hours))
    if diff2.minutes:
        parts2.append(_("{num} minuti").format(num=diff2.minutes))
    release_string = ", ".join(parts2)
    print(_("\nCiao! Benvenuto, sono Orologic e ho {age}.").format(age=age_string))
    print(_("L'ultima versione è la {version} ed è stata rilasciata il {release_date}.").format(version=version.VERSION, release_date=version.RELEASE_DATE.strftime('%d/%m/%Y %H:%M')))
    print(_("\tcioè: {release_ago} fa.").format(release_ago=release_string))
    print("\t\t" + _("Autore: ") + version.PROGRAMMER)
    print("\t\t\t" + _("Digita '?' per visualizzare il menù."))
    Acusticator(['c4', 0.125, 0, volume, 'd4', 0.125, 0, volume, 'e4', 0.125, 0, volume, 'g4', 0.125, 0, volume, 'a4', 0.125, 0, volume, 'e5', 0.125, 0, volume, 'p', 0.125, 0, 0.5, 'a5', 0.125, 0, volume], kind=1, adsr=[0.01, 0, 100, 99])

def Main():
    global volume, STILE_MENU_NUMERICO
    os.makedirs(config.percorso_salvataggio("pgn"), exist_ok=True)
    os.makedirs(config.percorso_salvataggio("txt"), exist_ok=True)
    os.makedirs(config.percorso_salvataggio("settings"), exist_ok=True)
    db = storage.LoadDB()
    volume = db.get("volume", 0.5)
    STILE_MENU_NUMERICO = db.get("menu_numerati", False)
    launch_count = db.get("launch_count", 0) + 1
    db["launch_count"] = launch_count
    storage.SaveDB(db)
    
    SchermataIniziale()
    engine.InitEngine()
    if engine.ENGINE is not None:
        print(_("✅ Motore attivo: {engine_name}").format(engine_name=config.ENGINE_NAME))
        
    ui.LoadLocalization()
    
    # --- Inizio Blocco Autosave ---
    AUTOSAVE_FILE = "autosave.json"
    autosave_path = config.percorso_salvataggio(os.path.join("settings", AUTOSAVE_FILE))
    if os.path.exists(autosave_path):
        print("\n" + "="*40)
        print("⚠️ " + _("Trovata una partita non conclusa!"))
        print("="*40)
        scelta_ripresa = key(_("Vuoi riprenderla? (Invio per Sì / 'n' per No): ")).lower().strip()
        if scelta_ripresa != 'n':
            try:
                with open(autosave_path, 'r', encoding='utf-8') as f:
                    dati_caricati = json.load(f)
                print(_("Partita caricata. Avvio in corso..."))
                Acusticator(["c5", 0.1, -0.8, volume, "e5", 0.1, 0, volume, "g5", 0.2, 0.8, volume], kind=1, adsr=[2, 8, 90, 0])
                game_flow.RiprendiPartita(dati_caricati)
            except Exception as e:
                print(_("Errore critico durante il caricamento della partita: {error}").format(error=e))
                print(_("Il file di salvataggio potrebbe essere corrotto. Verrà ignorato per questa sessione."))
                Acusticator(["a3", .3, 0, volume], kind=2, adsr=[5, 15, 0, 80])
        else:
            print(_("Ok, la partita salvata verrà ignorata."))
            
    while True:
        # Rilegge lo stile menu dal DB in caso sia cambiato in Impostazioni
        STILE_MENU_NUMERICO = storage.LoadDB().get("menu_numerati", False)
        
        scelta = menu(config.MENU_CHOICES, show=True, keyslist=True, numbered=STILE_MENU_NUMERICO)
        
        if scelta == "analizza":
            Acusticator(["a5", .04, 0, volume, "e5", .04, 0, volume, "p",.08,0,0, "g5", .04, 0, volume, "e6", .120, 0, volume], kind=1, adsr=[2, 8, 90, 0])
            print(_("\nCaricamento partita dagli appunti..."))
            pgn_da_analizzare = engine.LoadPGNFromClipboard()
            if pgn_da_analizzare:
                if engine.ENGINE is None and not engine.InitEngine():
                    print(_("Impossibile inizializzare il motore. Analisi annullata."))
                else:
                    engine.cache_analysis.clear()
                    if ui.enter_escape(_("Desideri l'analisi automatica? (INVIO per sì, ESC per manuale): ")):
                        # Importante: usiamo una copia deep per non modificare l'oggetto originale se serve altrove
                        import copy
                        engine.AnalisiAutomatica(copy.deepcopy(pgn_da_analizzare))
                    else:
                        engine.AnalyzeGame(pgn_da_analizzare)
            else:
                pass # Messaggio già stampato da LoadPGNFromClipboard
                
        elif scelta == "crea":
            Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
            clock.CreateClock()
            
        elif scelta == "comandi":
            Acusticator([500.0, 0.4, -1, volume, 800.0, 0.4, 1, volume], kind=3, adsr=[20, 10, 50, 20])
            menu(config.DOT_COMMANDS, show_only=True)
            
        elif scelta == "motore":
            Acusticator(["e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume,"e7",.02,0,volume,"a6",.02,0,volume])
            print(_("\nAzioni per il motore scacchistico:"))
            scelta_azione = key(_("Vuoi [c] cercare un motore nel tuo pc, [s] scaricare Stockfish, o [m] per modificare manualmente la configurazione? (c/s/m): ")).lower().strip()
            if scelta_azione == 'c':
                res = engine.SearchForEngine()
                # SearchForEngine ritorna (path, exe, wants_download) o (None, None, flag)
                if res:
                    path, exe, wants_download = res
                    if wants_download:
                        path, exe = engine.DownloadAndInstallEngine()
                        if path and exe:
                            engine.EditEngineConfig(initial_path=path, initial_executable=exe)
                    elif path and exe:
                        print(_("Motore trovato: ") + os.path.join(path, exe))
                        engine.EditEngineConfig(initial_path=path, initial_executable=exe)
                    else:
                        print(_("Nessun motore selezionato."))
            elif scelta_azione == 's':
                path, exe = engine.DownloadAndInstallEngine()
                if path and exe:
                    engine.EditEngineConfig(initial_path=path, initial_executable=exe)
            elif scelta_azione == 'm':
                engine.EditEngineConfig()
                
        elif scelta == "volume":
            Acusticator(["f6",.02,0,volume,"p",.04,0,volume,"a6",.02,0,volume])
            old_volume = volume
            volume_input = dgt(_("\nVolume attuale: {vol}, nuovo? (0-100): ").format(vol=int(volume*100)), kind="i", imin=0, imax=100, default=50)
            volume = volume_input / 100
            db = storage.LoadDB()
            db["volume"] = volume
            storage.SaveDB(db)
            Acusticator(["c5",.5,0,old_volume],adsr=[0,0,100,100],sync=True)
            Acusticator(["c5",.5,0,volume],adsr=[0,0,100,100])
            
        elif scelta == "vedi":
            Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
            clock.ViewClocks()
            
        elif scelta == "elimina":
            clock.DeleteClock(db)
            Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
            
        elif scelta == "impostazioni":
            ui.Impostazioni(db)
            Acusticator([1000.0, 0.05, -1, volume, "p", 0.05, 0, 0, 900.0, 0.05, 1, volume], kind=1, adsr=[0, 0, 100, 0])
            
        elif scelta == "nomi":
            ui.EditLocalization()
            Acusticator([1200.0, 0.05, 0, volume, "p", 0.05, 0, 0, 1100.0, 0.05, 0, volume], kind=1, adsr=[0, 0, 100, 0])
            
        elif scelta == "manuale":
            OpenManual()
            
        elif scelta == "gioca":
            Acusticator(["c5", 0.1, 0, volume, "e5", 0.1, 0, volume, "g5", 0.1, 0, volume, "c6", 0.3, 0, volume, "g5", 0.1, 0, volume, "e5", 0.1, 0, volume, "c5", 0.1, 0, volume], kind=1, adsr=[5, 5, 90, 10])
            print(_("\nAvvio partita\n"))
            db = storage.LoadDB()
            if not db.get("clocks"):
                Acusticator(["c5", 0.3, 0, volume, "g4", 0.3, 0, volume], kind=1, adsr=[30, 20, 80, 20])
                print(_("Nessun orologio disponibile. Creane uno prima."))
            else:
                clock_config = clock.SelectClock(db)
                if clock_config is not None:
                    game_flow.StartGame(clock_config)
                else:
                    print(_("Scelta non valida."))
                    
        elif scelta == ".":
            Acusticator(["g4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "a4", 0.15, -0.5, volume, "g4", 0.15, 0.5, volume, "p", 0.15, 0, 0, "b4", 0.15, -0.5, volume, "c5", 0.3, 0.5, volume], kind=1, adsr=[5, 0, 100, 5])
            if engine.ENGINE is not None:
                engine.ENGINE.quit()
                print(_("\nConnessione col motore UCI chiusa"))
            break

if __name__ == "__main__":
    time_start = datetime.datetime.now()
    # board = CustomBoard() # Non serve instanziare qui
    Main()
    time_end = datetime.datetime.now()
    delta = relativedelta(time_end, time_start)
    components = []
    if delta.days:
        components.append(_("{num} giorni").format(num=delta.days))
    if delta.hours:
        components.append(_("{num} ore").format(num=delta.hours))
    if delta.minutes:
        components.append(_("{num} minuti").format(num=delta.minutes))
    if delta.seconds:
        components.append(_("{num} secondi").format(num=delta.seconds))
    ms = delta.microseconds // 1000
    if ms:
        components.append(_("{num} millisecondi").format(num=ms))
    result = ", ".join(components) if components else _("0 millisecondi")
    final_db = storage.LoadDB()
    final_launch_count = final_db.get("launch_count", _("sconosciuto"))
    print(_("Arrivederci da Orologic {version}.\nQuesta era la nostra {launch_count}a volta e ci siamo divertiti assieme per: {duration}").format(version=version.VERSION, launch_count=final_launch_count, duration=result))
    Donazione()
    key(prompt=_("\nPremi un tasto per uscire..."), attesa=300)
    sys.exit(0)
