# Orologic, utilita': prepara l'archivio per la distribuzione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
# 02/09/2026: il lavoro e' passato a crea_archivio_release di GBUtils V93.

"""Comprime la cartella prodotta da PyInstaller in un solo archivio.

Tutto il mestiere sta in GBUtils, cosi' la regola sulle esclusioni e' una
sola per tutti i progetti. Qui restano soltanto i nomi di Orologic.

Le cartelle dei dati dell'utente, log, settings, pgn, txt e images, sono
gia' saltate d'ufficio dalla funzione: nascono accanto all'eseguibile
appena lo si avvia per la prova e senza questa rete di sicurezza
finirebbero nell'archivio pubblico insieme ai dati di chi ha compilato.
"""

import sys

from GBUtils import crea_archivio_release


def main():
    try:
        crea_archivio_release("Orologic", cartella_dist="dist/orologic")
    except (FileNotFoundError, OSError) as e:
        print(f"Archivio non creato: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
