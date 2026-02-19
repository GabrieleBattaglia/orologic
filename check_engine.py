from orologic_modules import config
import chess.engine
import os
import sys

# Utilizza il percorso dinamico configurato nel progetto
engine_dir = config.percorso_salvataggio("engine")
path = None

# Cerca l'eseguibile di Stockfish nella cartella engine
if os.path.exists(engine_dir):
    for root, dirs, files in os.walk(engine_dir):
        for file in files:
            if file.lower().startswith("stockfish") and file.lower().endswith(".exe"):
                path = os.path.join(root, file)
                break
        if path: break

if not path:
    print(f"Errore: Motore non trovato in {engine_dir}")
    sys.exit(1)

print(f"Path: {path}")
print(f"Exists: {os.path.exists(path)}")

try:
    engine = chess.engine.SimpleEngine.popen_uci(path)
    print(f"Engine launched: {engine.id}")
    engine.quit()
    print("Engine quit successfully")
except Exception as e:
    print(f"Error launching engine: {e}")
