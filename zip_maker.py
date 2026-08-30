# Orologic, utilita': prepara l'archivio per la distribuzione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

"""Comprime la cartella prodotta da PyInstaller in un solo archivio."""

import os
import sys
import zipfile

CARTELLA = os.path.join("dist", "orologic")
ARCHIVIO = "Orologic.zip"


def main():
    print(f"Creo {ARCHIVIO} a partire da {CARTELLA}.")
    if not os.path.isdir(CARTELLA):
        print(f"La cartella {CARTELLA} non esiste: PyInstaller ha finito?")
        return 1
    quanti = 0
    with zipfile.ZipFile(ARCHIVIO, "w", zipfile.ZIP_DEFLATED) as archivio:
        for radice, _cartelle, file in os.walk(CARTELLA):
            for nome in file:
                percorso = os.path.join(radice, nome)
                archivio.write(percorso, os.path.relpath(percorso, CARTELLA))
                quanti += 1
    print(f"Fatto: {ARCHIVIO} contiene {quanti} file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
