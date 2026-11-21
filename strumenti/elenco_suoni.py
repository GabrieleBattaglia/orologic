# Orologic, strumenti: l'elenco dei suoni della scacchiera interattiva per Acu_Maker.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
# 21/11/2026: nasce con i suoni della scacchiera, sul modello di Ciechino
# strumenti/elenco_suoni.py.

"""Scrive nella cartella del progetto suoni_della_scacchiera.txt, che elenca
ogni azione della scacchiera interattiva con il nome del suo preset nella
collezione di GBUtils: con l'elenco in mano Gabriele ritocca i suoni con
Acu_Maker, senza leggere il codice. Si genera dalle tabelle SUONI e AZIONI di
orologic_modules/finestra_scacchiera.py, e una prova controlla che sia
aggiornato.

Uso, dalla cartella del progetto:
  python strumenti\\elenco_suoni.py
"""

import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOME_DEL_FILE = "suoni_della_scacchiera.txt"


def testo():
    """Il contenuto dell'elenco, riga per riga, senza separatori grafici."""
    if RADICE not in sys.path:
        sys.path.insert(0, RADICE)
    from orologic_modules.finestra_scacchiera import AZIONI, SUONI

    righe = [
        f"I suoni della scacchiera interattiva di Orologic e i loro preset nella collezione di GBUtils, da ritoccare con Acu_Maker: {len(SUONI)} suoni.",
        "Ogni riga dice l'azione che fa suonare il preset e, dopo i due punti, il suo nome. Il file lo scrive strumenti/elenco_suoni.py dalle tabelle di orologic_modules/finestra_scacchiera.py: non va modificato a mano.",
    ]
    righe.extend(f"{AZIONI[evento]}: {preset}." for evento, preset in SUONI.items())
    return "\r\n".join(righe) + "\r\n"


def scrivi():
    percorso = os.path.join(RADICE, NOME_DEL_FILE)
    with open(percorso, "wb") as file:
        file.write(testo().encode("utf-8"))
    return percorso


if __name__ == "__main__":
    print(scrivi())
    sys.exit(0)
