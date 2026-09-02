# Orologic, utilita': prepara l'archivio per la distribuzione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).

"""Comprime la cartella prodotta da PyInstaller in un solo archivio.

I file estratti devono stare alla radice dell'archivio, senza cartelle
intermedie: e' quello che l'auto updater di GBUtils sa gestire, e gli
strumenti di compressione di Windows non lo fanno.

Quello che non deve entrare nel pacchetto pubblico viene lasciato fuori
anche qui, oltre che ripulito a mano prima di comprimere: partite, log e
impostazioni nascono accanto all'eseguibile appena lo si avvia per la
prova, e senza questa rete di sicurezza finirebbero nell'archivio
insieme ai dati di chi ha compilato.
"""

import os
import sys
import zipfile

CARTELLA = os.path.join("dist", "orologic")
ARCHIVIO = "Orologic.zip"
CARTELLE_ESCLUSE = {"__pycache__", ".git", "log", "settings", "pgn", "txt", "images"}
CODE_ESCLUSE = (".dat", ".bak", ".tmp", ".pdb", ".log", ".pyc", ".zip")


def main():
    print(f"Creo {ARCHIVIO} a partire da {CARTELLA}.")
    if not os.path.isdir(CARTELLA):
        print(f"La cartella {CARTELLA} non esiste: PyInstaller ha finito?")
        return 1
    quanti = 0
    lasciati = []
    with zipfile.ZipFile(ARCHIVIO, "w", zipfile.ZIP_DEFLATED) as archivio:
        for radice, cartelle, file in os.walk(CARTELLA):
            cartelle[:] = [c for c in cartelle if c not in CARTELLE_ESCLUSE]
            # Le estensioni si guardano solo accanto all'eseguibile, dove
            # nascono i file di chi lo prova: dentro _internal c'e' quello
            # che ha messo PyInstaller, compresi un base_library.zip e dei
            # .dat di libreria che servono davvero.
            alla_radice = os.path.abspath(radice) == os.path.abspath(CARTELLA)
            for nome in file:
                if alla_radice and nome.lower().endswith(CODE_ESCLUSE):
                    lasciati.append(nome)
                    continue
                percorso = os.path.join(radice, nome)
                archivio.write(percorso, os.path.relpath(percorso, CARTELLA))
                quanti += 1
    print(f"Fatto: {ARCHIVIO} contiene {quanti} file.")
    if lasciati:
        print(f"Lasciati fuori {len(lasciati)} file di lavoro: {lasciati[:5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
