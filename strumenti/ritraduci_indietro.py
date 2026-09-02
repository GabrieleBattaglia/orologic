# Orologic, sviluppo: controlla le traduzioni ritraducendole in italiano.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).

"""Riporta ogni traduzione in italiano e la confronta con l'originale.

E' il modo per accorgersi che una traduzione dice un'altra cosa senza
conoscere la lingua: se la frase tornata indietro non somiglia a quella
di partenza, qualcosa si e' perso per strada. Non e' una prova, e' un
sospetto: la lista che produce va letta a mano, perche' anche una buona
traduzione torna indietro con parole diverse.

Uso: python ritraduci_indietro.py <lingua> [--pausa 1.0] [--da 0] [--quante 0]
"""

import argparse
import os
import re
import sys
import time
from difflib import SequenceMatcher

try:
    import polib
    from deep_translator import GoogleTranslator
except ImportError:
    print("Librerie mancanti. Installale con: pip install -r requirements-dev.txt")
    sys.exit(1)

SEGNAPOSTO = re.compile(r"\{[^{}]*\}")


def nocciolo(testo):
    """Il testo ridotto a parole, per confrontare il senso e non la forma."""
    senza = SEGNAPOSTO.sub(" ", testo)
    return re.sub(r"[\s\W_]+", " ", senza.lower()).strip()


def main():
    for flusso in (sys.stdout, sys.stderr):
        if hasattr(flusso, "reconfigure"):
            flusso.reconfigure(errors="replace")
    lettore = argparse.ArgumentParser()
    lettore.add_argument("lingua")
    lettore.add_argument("--pausa", type=float, default=1.0)
    lettore.add_argument("--da", type=int, default=0)
    lettore.add_argument("--quante", type=int, default=0)
    lettore.add_argument("--soglia", type=float, default=0.55)
    argomenti = lettore.parse_args()

    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    percorso = os.path.join(
        radice, "locales", argomenti.lingua, "LC_MESSAGES", "messages.po"
    )
    catalogo = polib.pofile(percorso)
    voci = [
        v
        for v in catalogo
        if not v.obsolete and v.msgstr.strip() and len(nocciolo(v.msgid)) > 8
    ]
    if argomenti.quante:
        voci = voci[argomenti.da : argomenti.da + argomenti.quante]
    else:
        voci = voci[argomenti.da :]

    traduttore = GoogleTranslator(source=argomenti.lingua, target="it")
    rapporto = percorso + ".ritorno.txt"
    sospette = 0
    with open(rapporto, "w", encoding="utf-8") as f:
        f.write(f"Ritorno in italiano delle traduzioni {argomenti.lingua}.\n")
        f.write("Ogni voce riporta la frase originale e quella tornata indietro.\n")
        for numero, voce in enumerate(voci, 1):
            ritorno = None
            for tentativo in range(3):
                try:
                    ritorno = traduttore.translate(voce.msgstr) or ""
                    break
                # Il servizio di traduzione risponde in tanti modi diversi
                # quando non ce la fa, e spesso e' solo troppa fretta: si
                # aspetta un po' di piu' e si riprova, invece di perdere
                # la stringa.
                except Exception as errore:  # noqa: BLE001
                    if tentativo == 2:
                        f.write(f"\nERRORE {errore}\n  IT {voce.msgid}\n")
                    else:
                        time.sleep(argomenti.pausa * 6 * (tentativo + 1))
            if ritorno is None:
                continue
            somiglianza = SequenceMatcher(
                None, nocciolo(voce.msgid), nocciolo(ritorno)
            ).ratio()
            if somiglianza < argomenti.soglia:
                sospette += 1
                f.write(f"\n[{somiglianza:.2f}]\n")
                f.write(f"  IT      {voce.msgid}\n")
                f.write(f"  {argomenti.lingua.upper()}      {voce.msgstr}\n")
                f.write(f"  RITORNO {ritorno}\n")
            if numero % 50 == 0:
                print(f"[{argomenti.lingua}] {numero}/{len(voci)}, sospette {sospette}")
                f.flush()
            time.sleep(argomenti.pausa)
    print(f"[{argomenti.lingua}] Finito: {len(voci)} controllate, {sospette} sospette")
    print(f"[{argomenti.lingua}] Rapporto: {rapporto}")


if __name__ == "__main__":
    main()
