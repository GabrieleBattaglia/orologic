# Orologic, i percorsi: dove stanno i file, da sorgente e da eseguibile.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, UltraCode).
# 12/09/2026: nasce con l'adozione di cartella_applicazione e percorso_risorsa
# di GBUtils, issue 20 e 31 della libreria. Prima le stesse tre righe stavano
# in orologic_modules/config.py, che risaliva di una cartella per arrivare
# qui: ogni progetto del parco software aveva la sua copia, e adesso la
# logica e' scritta una volta sola nella libreria condivisa.

"""I percorsi di Orologic.

Questo modulo sta nella radice del progetto, accanto a orologic.py, e non
dentro orologic_modules: e' quella la cartella a cui i percorsi si
riferiscono, cioe' dove stanno i salvataggi dell'utente e le risorse del
programma, e una funzione di GBUtils risponde la cartella del modulo che la
chiama. Tenerlo qui rende Orologic uguale agli altri progetti del parco
software, che sono piatti e non hanno questo problema.

Due regole, prese dal memorandum sui percorsi in docs. Cio' che il programma
scrive, cioe' pgn, txt, impostazioni e database, sta accanto al programma:
accanto all'eseguibile quando e' compilato, accanto ai sorgenti altrimenti.
Cio' che il programma legge soltanto, cioe' i cataloghi delle traduzioni, il
manuale, il changelog e il database delle aperture, da compilato viaggia
dentro il pacchetto, nella cartella temporanea che PyInstaller apre
all'avvio, e li' va cercato per primo.
"""

import os

from GBUtils import cartella_applicazione
from GBUtils import percorso_risorsa as _percorso_risorsa


def radice_app():
    """La cartella di questo file, cioe' la radice del progetto: da compilato
    quella dell'eseguibile. Mai la directory di lavoro, che dipende da dove il
    programma e' stato lanciato e non da dove sta.
    E' una funzione e non una costante apposta: una costante si calcolerebbe
    all'importazione del modulo e resterebbe quella, mentre cosi' la risposta
    guarda ogni volta se il programma e' compilato, com'e' sempre stato."""
    return cartella_applicazione()


def resource_path(relative_path):
    """Percorso di una risorsa inclusa nel pacchetto (manuale, changelog, eco.db)."""
    return _percorso_risorsa(relative_path)


def percorso_salvataggio(relative_path):
    """Percorso di lettura e scrittura dei dati dell'utente (pgn, txt, settings)."""
    return os.path.join(cartella_applicazione(), relative_path)
