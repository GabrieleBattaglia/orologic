# Orologic, diagnostica: verifica che il motore sia presente e risponda.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

"""Controlla che il motore configurato ci sia e sappia rispondere.

Da lanciare a mano quando il motore non parte e non si capisce perche'.
La ricerca dell'eseguibile e' quella del programma, non una seconda
versione: cosi' questo controllo dice la verita' su cosa fara' Orologic.
"""

import sys

import chess.engine

from orologic_modules import engine as motore_orologic


def main():
    cartella, eseguibile, _relativo = motore_orologic.SearchForEngine()
    if not cartella or not eseguibile:
        print("Motore non trovato dove il programma lo cerca.")
        return 1
    percorso = (
        f"{cartella}\\{eseguibile}"
        if not cartella.endswith("\\")
        else cartella + eseguibile
    )
    print(f"Trovato: {percorso}")
    try:
        uci = chess.engine.SimpleEngine.popen_uci(percorso)
    # Diagnostica: interessa proprio sapere che il motore non parte,
    # qualunque sia il motivo.
    except Exception as e:  # noqa: BLE001
        print(f"Il motore non si avvia: {e}")
        return 1
    try:
        nome = uci.id.get("name", "sconosciuto")
        autore = uci.id.get("author", "sconosciuto")
        print(f"Risponde: {nome}, di {autore}")
        opzioni = sorted(uci.options)
        print(f"Opzioni dichiarate: {len(opzioni)}")
        for attesa in ("Hash", "Threads", "Skill Level"):
            print(f"   {attesa}: {'si' if attesa in uci.options else 'no'}")
    finally:
        uci.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
