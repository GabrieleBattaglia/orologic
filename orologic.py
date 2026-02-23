import sys
import os
import time
import datetime
import chess
import copy
from dateutil.relativedelta import relativedelta
from GBUtils import dgt, menu, Acusticator, key, Donazione, polipo
from orologic_modules import config, storage, ui, clock, engine, game_flow, version, board_utils, stockfish_installer
from orologic_modules.easyfish import easyfish_app

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

def OpenManual():
    manual_path = config.resource_path(os.path.join("resources", "manuale_it.txt" if lingua_rilevata == "it" else "manual_en.txt"))
    if os.path.exists(manual_path):
        try:
            if sys.platform == "win32": os.startfile(manual_path)
            else:
                import subprocess
                subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", manual_path])
        except Exception as e: print(_("Errore nell'apertura del manuale:"), e)
    else: print(_("Manuale non trovato in:"), manual_path)

def SchermataIniziale():
	now = datetime.datetime.now()
	diff1 = relativedelta(now, version.BIRTH_DATE)
	diff2 = relativedelta(now, version.RELEASE_DATE)
	parts1 = []
	if diff1.years: parts1.append(_("{num} anni").format(num=diff1.years))
	if diff1.months: parts1.append(_("{num} mesi").format(num=diff1.months))
	if diff1.days: parts1.append(_("{num} giorni").format(num=diff1.days))
	if diff1.hours: parts1.append(_("{num} ore").format(num=diff1.hours))
	if diff1.minutes: parts1.append(_("e {num} minuti").format(num=diff1.minutes))
	age_string = ", ".join(parts1)
	parts2 = []
	if diff2.years: parts2.append(_("{num} anni").format(num=diff2.years))
	if diff2.months: parts2.append(_("{num} mesi").format(num=diff2.months))
	if diff2.days: parts2.append(_("{num} giorni").format(num=diff2.days))
	if diff2.hours: parts2.append(_("{num} ore").format(num=diff2.hours))
	if diff2.minutes: parts2.append(_("{num} minuti").format(num=diff2.minutes))
	release_string = ", ".join(parts2)
	print(_("\nCiao! Benvenuto, sono Orologic e ho {age}.").format(age=age_string))
	print(_("L'ultima versione e' la {version} ed e' stata rilasciata il {release_date}.").format(version=version.VERSION, release_date=version.RELEASE_DATE.strftime('%d/%m/%Y %H:%M')))
	print(_("\tcioe': {release_ago} fa.").format(release_ago=release_string))
	print("\t\t" + _("Autore: ") + version.PROGRAMMER)
	print("\t\t\t" + _("Digita '?' per visualizzare il menu'."))
	Acusticator(['c4', 0.125, 0, config.VOLUME, 'd4', 0.125, 0, config.VOLUME, 'e4', 0.125, 0, config.VOLUME, 'g4', 0.125, 0, config.VOLUME, 'a4', 0.125, 0, config.VOLUME, 'e5', 0.125, 0, config.VOLUME, 'p', 0.125, 0, 0.5, 'a5', 0.125, 0, config.VOLUME], kind=1, adsr=[0.01, 0, 100, 99])

def Main():
    # Incremento contatore lanci
    db = storage.LoadDB()
    db["launch_count"] = db.get("launch_count", 0) + 1
    storage.SaveDB(db)
    
    SchermataIniziale()
    
    # Inizializzazione Motore (se configurato)
    engine.InitEngine()
    
    # Loop Principale
    while True:
        scelta = menu(config.MENU_CHOICES, show=True, keyslist=True, p=_("\nScegli un'azione: "), numbered=db.get("menu_numerati", False))
        
        if scelta == ".":
            Acusticator(["g4", 0.15, -0.5, config.VOLUME, "g4", 0.15, 0.5, config.VOLUME, "a4", 0.15, -0.5, config.VOLUME, "g4", 0.15, 0.5, config.VOLUME, "p", 0.15, 0, 0, "b4", 0.15, -0.5, config.VOLUME, "c5", 0.3, 0.5, config.VOLUME], kind=1, adsr=[5, 0, 100, 5])
            engine.CloseEngine()
            break
            
        elif scelta == "analizza":
            Acusticator(["a5", .04, 0, config.VOLUME, "e5", .04, 0, config.VOLUME, "p",.08,0,0, "g5", .04, 0, config.VOLUME, "e6", .120, 0, config.VOLUME], kind=1, adsr=[2, 8, 90, 0])
            print(_("\nCaricamento partita dagli appunti..."))
            pgn_da_analizzare = engine.LoadPGNFromClipboard()
            if pgn_da_analizzare:
                if engine.ENGINE is None and not engine.InitEngine():
                    print(_("Impossibile inizializzare il motore. Analisi annullata."))
                else:
                    engine.cache_analysis.clear()
                    if ui.enter_escape(_("Desideri l'analisi automatica? (INVIO per si', ESC per manuale): ")):
                        engine.AnalisiAutomatica(copy.deepcopy(pgn_da_analizzare))
                    else: engine.AnalyzeGame(pgn_da_analizzare)
            
        elif scelta == "crea":
            Acusticator([1000.0, 0.05, -1, config.VOLUME, "p", 0.05, 0, 0, 900.0, 0.05, 1, config.VOLUME], kind=1, adsr=[0, 0, 100, 0])
            clock.CreateClock()
            
        elif scelta == "easyfish":
            Acusticator(["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0.5, config.VOLUME], kind=1)
            easyfish_app.run()
            
        elif scelta == "motore":
            Acusticator(["e7",.02,0,config.VOLUME,"a6",.02,0,config.VOLUME,"e7",.02,0,config.VOLUME,"a6",.02,0,config.VOLUME,"e7",.02,0,config.VOLUME,"a6",.02,0,config.VOLUME])
            print(_("\nAzioni per il motore scacchistico:"))
            scelta_azione = key(_("Vuoi [c] cercare un motore nel tuo pc, [s] scaricare Stockfish, o [m] per modificare manualmente la configurazione? (c/s/m): ")).lower().strip()
            if scelta_azione == 'c':
                p, e, _u = engine.SearchForEngine()
                if p and e: engine.EditEngineConfig(initial_path=p, initial_executable=e)
            elif scelta_azione == 's':
                p, e = stockfish_installer.DownloadAndInstallEngine()
                if p and e: engine.EditEngineConfig(initial_path=p, initial_executable=e)
            elif scelta_azione == 'm': engine.EditEngineConfig()
            
        elif scelta == "nomi":
            Acusticator(["c5", 0.1, -1, config.VOLUME, "e5", 0.1, -0.3, config.VOLUME, "g5", 0.1, 0.3, config.VOLUME, "c6", 0.1, 1, config.VOLUME], kind=1, adsr=[2, 8, 80, 10])
            ui.EditLocalization()
            
        elif scelta == "impostazioni":
            Acusticator(["a4", 0.2, 0, config.VOLUME, "c5", 0.2, 0, config.VOLUME], kind=1, adsr=[5, 5, 80, 10])
            ui.Impostazioni(db)
            
        elif scelta == "arbitra":
            Acusticator(["c4", 0.2, -1, config.VOLUME, "e4", 0.2, -0.3, config.VOLUME, "g4", 0.2, 0.3, config.VOLUME, "c5", 0.4, 1, config.VOLUME], kind=1, adsr=[10, 5, 80, 5])
            db = storage.LoadDB()
            clock_config = clock.SelectClock(db)
            if clock_config: game_flow.StartGame(clock_config)
            
        elif scelta == "manuale":
            Acusticator([400.0, 0.2, 0, config.VOLUME, 600.0, 0.2, 0, config.VOLUME], kind=1, adsr=[10, 10, 80, 10])
            OpenManual()
            
        elif scelta == "vedi":
            Acusticator([1000.0, 0.1, 0, config.VOLUME, "p", 0.1, 0, 0, 1000.0, 0.1, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0])
            clock.ViewClocks()
            
        elif scelta == "volume":
            print(_("\nRegolazione Volume"))
            print(_("Volume attuale: {vol:.0f}%").format(vol=config.VOLUME * 100))
            new_vol = dgt(_("Inserisci nuovo volume (0-100): "), kind="i", imin=0, imax=100)
            old_v = config.VOLUME; config.VOLUME = new_vol / 100.0
            db["volume"] = config.VOLUME; storage.SaveDB(db)
            Acusticator(["c5", 0.2, 0, old_v], sync=True); time.sleep(0.3)
            Acusticator(["c6", 0.2, 0, config.VOLUME]); print(_("Volume impostato a {vol:.0f}%").format(vol=config.VOLUME * 100))
            
        elif scelta == "elimina":
            Acusticator([200.0, 0.5, 0, config.VOLUME], kind=2, adsr=[10, 10, 80, 10])
            clock.DeleteClock(db)

if __name__ == "__main__":
    t_start = datetime.datetime.now()
    Main()
    t_end = datetime.datetime.now()
    delta = relativedelta(t_end, t_start)
    comp = []
    if delta.days: comp.append(_("{n} giorni").format(n=delta.days))
    if delta.hours: comp.append(_("{n} ore").format(n=delta.hours))
    if delta.minutes: comp.append(_("{n} minuti").format(n=delta.minutes))
    if delta.seconds: comp.append(_("{n} secondi").format(n=delta.seconds))
    ms = delta.microseconds // 1000
    if ms: comp.append(_("{n} millisecondi").format(n=ms))
    durata = ", ".join(comp) if comp else _("0 millisecondi")
    
    db_f = storage.LoadDB()
    l_count = db_f.get("launch_count", _("sconosciuto"))
    print(_("\nArrivederci da Orologic {v}.\nQuesta era la nostra {lc}a volta e ci siamo divertiti assieme per: {d}").format(v=version.VERSION, lc=l_count, d=durata))
    Donazione()
    key(prompt=_("\nPremi un tasto per uscire..."), attesa=300)
    sys.exit(0)
