# Orologic, sviluppo: compila i cataloghi dopo averli controllati.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

"""Compila i cataloghi in forma binaria, ma solo se sono in ordine.

I file .po sono testo e si leggono; quelli .mo sono la forma che il
programma usa davvero. Fra i due passaggi ci si mette il controllo dei
segnaposto: compilare una traduzione rotta significa consegnarla, e il
guaio si vedrebbe solo quando quel messaggio esce a schermo.

Uso: python compila_cataloghi.py [--forza]
"""

import os
import subprocess
import sys


def main():
    # La console di Windows non sa scrivere tutti gli accenti delle quattro
    # lingue: si sostituiscono invece di far cadere lo strumento.
    for flusso in (sys.stdout, sys.stderr):
        if hasattr(flusso, "reconfigure"):
            flusso.reconfigure(errors="replace")
    forza = "--forza" in sys.argv
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(radice)

    print("Controllo dei segnaposto e della forma:")
    esito = subprocess.run(
        [sys.executable, os.path.join("strumenti", "verifica_cataloghi.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print(esito.stdout.rstrip())
    if esito.returncode != 0 and not forza:
        print("Compilazione non eseguita: sistema prima le traduzioni rotte.")
        print("Se sai quello che fai, ripeti con --forza.")
        return 1

    print()
    print("Compilazione dei cataloghi:")
    esito = subprocess.run(
        [sys.executable, "-m", "babel.messages.frontend", "compile", "-d", "locales"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print((esito.stdout + esito.stderr).rstrip())
    if esito.returncode != 0:
        print("La compilazione non e' riuscita.")
        return 1

    for lingua in sorted(os.listdir("locales")):
        percorso = os.path.join("locales", lingua, "LC_MESSAGES", "messages.mo")
        if os.path.exists(percorso):
            print(f"   {lingua}: {os.path.getsize(percorso)} byte")
    print("Fatto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
