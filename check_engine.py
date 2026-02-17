import chess.engine
import os
import sys

path = r"C:\Users\Utente\AppData\Local\Orologic\Engine\stockfish\stockfish-windows-x86-64-avx2.exe"

print(f"Path: {path}")
print(f"Exists: {os.path.exists(path)}")

try:
    engine = chess.engine.SimpleEngine.popen_uci(path)
    print(f"Engine launched: {engine.id}")
    engine.quit()
    print("Engine quit successfully")
except Exception as e:
    print(f"Error launching engine: {e}")
