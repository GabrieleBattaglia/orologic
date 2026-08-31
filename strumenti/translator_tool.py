# Orologic, sviluppo: aiuto alla traduzione dei cataloghi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

"""Traduce le stringhe mancanti di un catalogo gettext.

La traduzione automatica serve a partire, non ad arrivare: quello che
produce va sempre riletto. Questo strumento si preoccupa soprattutto di
non consegnare stringhe che facciano cadere il programma, e quindi
controlla che ogni segnaposto torni indietro identico a come e' partito.
Le stringhe su cui il controllo fallisce restano da tradurre e finiscono
in un rapporto, invece di entrare rotte nel catalogo.

Uso: python translator_tool.py <file.po> <lingua> [--pausa 0.4] [--prova 5]
"""

import argparse
import os
import re
import shutil
import sys
import time

try:
    import polib
    from deep_translator import GoogleTranslator
except ImportError:
    print("Librerie mancanti. Installale con: pip install -r requirements-dev.txt")
    sys.exit(1)

# I segnaposto vengono sostituiti da marcatori che il traduttore lascia
# stare. Le parentesi matematiche non compaiono nel testo del programma e
# non vengono tradotte.
SEGNAPOSTO = re.compile(r"\{[^{}]*\}")
MARCATORE = "⟦{}⟧"
RITROVA_MARCATORE = re.compile(r"⟦\s*(\d+)\s*⟧")


def _scomponi(testo):
    """Divide una stringa in spazi iniziali, corpo e spazi finali.

    Gli a capo e gli spazi ai bordi contano quanto le parole: servono a
    come il messaggio viene letto ad alta voce, e il traduttore li perde.
    """
    corpo = testo.strip(" \t\r\n")
    if not corpo:
        return testo, "", ""
    inizio = testo[: testo.index(corpo)]
    fine = testo[testo.index(corpo) + len(corpo) :]
    return inizio, corpo, fine


def _proteggi(corpo):
    """Sostituisce i segnaposto con marcatori, restituendo anche l'elenco."""
    trovati = SEGNAPOSTO.findall(corpo)
    protetto = corpo
    for numero, segnaposto in enumerate(trovati):
        protetto = protetto.replace(segnaposto, MARCATORE.format(numero), 1)
    return protetto, trovati


def _ripristina(tradotto, trovati):
    """Rimette i segnaposto al posto dei marcatori."""

    def sostituisci(trovato):
        indice = int(trovato.group(1))
        return trovati[indice] if indice < len(trovati) else trovato.group(0)

    return RITROVA_MARCATORE.sub(sostituisci, tradotto)


def _ripara_spazi(originale, tradotto):
    """Rimette gli spazi attorno ai segnaposto dove il traduttore li mangia.

    Google attacca volentieri il segnaposto alla parola che lo precede,
    e "salvato in:{percorso}" letto ad alta voce diventa incomprensibile.
    Se nell'originale c'era uno spazio, ci deve essere anche qui.
    """
    for segnaposto in dict.fromkeys(SEGNAPOSTO.findall(originale)):
        quotato = re.escape(segnaposto)
        prima_originale = re.search(r"(.?)" + quotato, originale)
        dopo_originale = re.search(quotato + r"(.?)", originale)
        if prima_originale and prima_originale.group(1) == " ":
            tradotto = re.sub(
                r"(?<=[^\s])" + quotato, " " + segnaposto, tradotto
            )
        if dopo_originale and dopo_originale.group(1) == " ":
            tradotto = re.sub(
                quotato + r"(?=[^\s])", segnaposto + " ", tradotto
            )
    return tradotto


def _segnaposto_intatti(originale, tradotto):
    """Vero se la traduzione ha gli stessi segnaposto dell'originale.

    L'ordine puo' cambiare, perche' ogni lingua mette le parole dove
    vuole, ma non possono mancarne ne' comparirne di nuovi, e la forma di
    ciascuno deve essere identica: un {media:.0f} diventato {media:.Of}
    farebbe cadere il programma nel momento in cui quel messaggio esce.
    """
    return sorted(SEGNAPOSTO.findall(originale)) == sorted(
        SEGNAPOSTO.findall(tradotto)
    )


def traduci_stringa(traduttore, originale):
    """Traduce una stringa conservandone forma e segnaposto.

    Restituisce la traduzione, oppure nulla se il risultato non e'
    affidabile: meglio una stringa non tradotta, che gettext mostrera'
    in italiano, di una tradotta male che fa cadere il programma.
    """
    inizio, corpo, fine = _scomponi(originale)
    if not corpo:
        return None
    protetto, trovati = _proteggi(corpo)
    grezzo = traduttore.translate(protetto)
    if not grezzo:
        return None
    tradotto = inizio + _ripara_spazi(corpo, _ripristina(grezzo, trovati)) + fine
    if not _segnaposto_intatti(originale, tradotto):
        return None
    return tradotto


def traduci_catalogo(percorso, lingua, pausa=0.4, limite=None, ogni=20):
    if not os.path.exists(percorso):
        print(f"File non trovato: {percorso}")
        return 1

    po = polib.pofile(percorso)
    traduttore = GoogleTranslator(source="it", target=lingua)
    da_fare = [e for e in po.untranslated_entries() if e.msgid and not e.obsolete]
    if limite:
        da_fare = da_fare[:limite]
    if not da_fare:
        print(f"[{lingua}] Non c'e' niente da tradurre.")
        return 0

    print(f"[{lingua}] Stringhe da tradurre: {len(da_fare)}")
    shutil.copy2(percorso, percorso + ".bak")

    fatte = 0
    scartate = []
    for numero, voce in enumerate(da_fare, start=1):
        try:
            tradotta = traduci_stringa(traduttore, voce.msgid)
        except Exception as e:  # noqa: BLE001
            # Rete di rete e servizio altrui: si annota e si prosegue.
            scartate.append((voce.msgid, f"errore: {e}"))
            time.sleep(pausa * 3)
            continue
        if tradotta is None:
            scartate.append((voce.msgid, "segnaposto non conservati"))
        else:
            voce.msgstr = tradotta
            fatte += 1
        if numero % ogni == 0:
            po.save()
            print(f"[{lingua}] {numero}/{len(da_fare)}, tradotte {fatte}")
        time.sleep(pausa)

    po.save()
    print(f"[{lingua}] Finito: tradotte {fatte}, lasciate stare {len(scartate)}")
    if scartate:
        rapporto = f"{percorso}.da_rivedere.txt"
        with open(rapporto, "w", encoding="utf-8") as f:
            f.write(f"Stringhe non tradotte automaticamente per {lingua}.\n")
            f.write("Restano in italiano: vanno tradotte a mano.\n\n")
            for testo, motivo in scartate:
                f.write(f"{motivo}\n{testo!r}\n\n")
        print(f"[{lingua}] Elenco di quelle da fare a mano: {rapporto}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Traduce un catalogo gettext.")
    parser.add_argument("catalogo", help="percorso del file .po")
    parser.add_argument("lingua", help="codice della lingua, per esempio pt")
    parser.add_argument(
        "--pausa",
        type=float,
        default=0.4,
        help="secondi fra una stringa e l'altra, per non farsi rifiutare",
    )
    parser.add_argument(
        "--prova",
        type=int,
        default=None,
        metavar="N",
        help="traduce solo le prime N stringhe, per vedere come va",
    )
    argomenti = parser.parse_args()
    return traduci_catalogo(
        argomenti.catalogo, argomenti.lingua, argomenti.pausa, argomenti.prova
    )


if __name__ == "__main__":
    sys.exit(main())
