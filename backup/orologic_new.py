import sys
import os
import datetime
from GBUtils import polipo, menu, Acusticator, key, dgt
from orologic_modules import config, storage, ui, clock, engine, game_flow, version, board_utils

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

def SchermataIniziale():
    now = datetime.datetime.now()
    print(f"
Orologic Modular v{version.VERSION}")
    print(f"Rilasciato il: {version.RELEASE_DATE}")
    print(f"Autore: {version.PROGRAMMER}")
    Acusticator(['c4', 0.1, 0, 1.0, 'e4', 0.1, 0, 1.0, 'g4', 0.1, 0, 1.0])

def Main():
    # Setup directories
    os.makedirs(config.percorso_salvataggio("pgn"), exist_ok=True)
    os.makedirs(config.percorso_salvataggio("txt"), exist_ok=True)
    os.makedirs(config.percorso_salvataggio("settings"), exist_ok=True)
    
    db = storage.LoadDB()
    # Aggiorna config globali se necessario
    
    SchermataIniziale()
    engine.InitEngine()
    
    if engine.ENGINE:
        print(f"Motore attivo: {engine.ENGINE.id.get('name', 'Stockfish')}")
        
    ui.LoadLocalization()
    
    # Check Autosave (semplificato)
    autosave_path = config.percorso_salvataggio(os.path.join("settings", "autosave.json"))
    if os.path.exists(autosave_path):
        print("
Trovata partita salvata.")
        # game_flow.RiprendiPartita(...)
    
    while True:
        scelta = menu(config.MENU_CHOICES, show=True, keyslist=True, numbered=storage.LoadDB().get("menu_numerati", False))
        
        if scelta == "analizza":
            print(_("Analisi partita..."))
            pgn = engine.LoadPGNFromClipboard()
            if pgn:
                if ui.enter_escape(_("Analisi automatica? (INVIO=Sì, ESC=No)")):
                    engine.AnalisiAutomatica(pgn)
                else:
                    engine.AnalyzeGame(pgn)
            else:
                print(_("Nessun PGN valido negli appunti."))
                
        elif scelta == "crea":
            clock.CreateClock()
            
        elif scelta == "vedi":
            clock.ViewClocks()
            
        elif scelta == "elimina":
            clock.DeleteClock()
            
        elif scelta == "gioca":
            db = storage.LoadDB()
            clk = clock.SelectClock(db)
            if clk:
                game_flow.StartGame(clk)
                
        elif scelta == "motore":
            engine.DownloadAndInstallEngine() # O menu completo
            
        elif scelta == "nomi":
            ui.EditLocalization()
            
        elif scelta == ".":
            break
            
if __name__ == "__main__":
    Main()
