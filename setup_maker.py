"""Orologic, utilita': compila l'installatore con Inno Setup.

Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
Nasce il 21 novembre 2026 per la 9.0.0, sul modello di setup_maker.py di
Ciechino (issue 73, Piano della GUI.txt, T5c). Compila Orologic.iss col
compilatore di Inno Setup 6, passandogli la versione di
orologic_modules/version.py, e scrive Orologic-Setup-<versione>.exe nella
cartella del progetto, accanto a Orologic.zip. Si lancia dopo PyInstaller e
zip_maker.py, con dist ripulita (prontuario, fase 7.0 e 7.5). Il compilatore
si cerca nella variabile OROLOGIC_ISCC, poi sulla path, poi nelle cartelle
dove Inno Setup si installa.
La versione si prende da version.py, che importa soltanto datetime: config
no, perche' sveglierebbe polipo e chiederebbe la lingua.
Si lancia a mano: importarlo non fa niente.
"""

import os
import shutil
import subprocess
import sys

from orologic_modules.version import VERSION

# La cartella del progetto, dove stanno Orologic.iss e dist e dove nasce
# l'installatore, da qualunque cartella si lanci lo script.
RADICE = os.path.dirname(os.path.abspath(__file__))
VARIABILE_DEL_COMPILATORE = "OROLOGIC_ISCC"
RICETTA = "Orologic.iss"


def compilatore():
    """Il percorso di ISCC.exe, o None."""
    candidati = [os.environ.get(VARIABILE_DEL_COMPILATORE), shutil.which("iscc")]
    if os.environ.get("LOCALAPPDATA"):
        candidati.append(os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Inno Setup 6", "ISCC.exe"))
    for radice in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if radice:
            candidati.append(os.path.join(radice, "Inno Setup 6", "ISCC.exe"))
    return next((c for c in candidati if c and os.path.isfile(c)), None)


def main():
    iscc = compilatore()
    if iscc is None:
        print(f"Installatore non creato: non trovo ISCC.exe di Inno Setup 6. Indica il percorso con la variabile {VARIABILE_DEL_COMPILATORE}.")
        return 1
    if not os.path.isfile(os.path.join(RADICE, "dist", "orologic", "orologic.exe")):
        print("Installatore non creato: manca dist\\orologic\\orologic.exe. Compila prima con PyInstaller.")
        return 1
    esito = subprocess.run([iscc, "/Q", f"/DVersione={VERSION}", RICETTA], cwd=RADICE, check=False)
    if esito.returncode:
        print(f"Installatore non creato: ISCC ha finito con il codice {esito.returncode}.")
        return esito.returncode
    print(f"Installatore creato: Orologic-Setup-{VERSION}.exe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
