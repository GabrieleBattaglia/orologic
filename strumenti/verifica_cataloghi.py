# Orologic, sviluppo: controlla i cataloghi tradotti prima di compilarli.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

"""Controlla che le traduzioni siano usabili, prima di metterle in produzione.

Fa tre cose, in ordine di gravita'.

La prima e' la sola che possa far cadere il programma: verifica che i
segnaposto delle traduzioni siano gli stessi dell'originale. Un {tempo}
diventato {tiempo} in spagnolo non si vede finche' quel messaggio non
esce a schermo, e a quel punto il programma si ferma.

La seconda guarda la forma: spazi e a capo iniziali e finali, che
servono a come il messaggio viene letto ad alta voce, e i separatori
grafici, che nel programma non vogliamo.

La terza segnala le traduzioni sospette: identiche all'italiano, molto
piu' lunghe dell'originale, o che contengono i marcatori di lavorazione
rimasti in mezzo.

Uso: python verifica_cataloghi.py [cartella_locales]
"""

import os
import re
import sys

try:
    import polib
except ImportError:
    print("Libreria mancante. Installala con: pip install -r requirements-dev.txt")
    sys.exit(1)

SEGNAPOSTO = re.compile(r"\{[^{}]*\}")
MARCATORE_RIMASTO = re.compile(r"⟦|⟧|VAR\d+QQ")
SEPARATORI = re.compile(r"[-=_]{4,}")


def _bordi(testo):
    """Gli spazi e gli a capo ai due estremi, che vanno conservati."""
    return (
        testo[: len(testo) - len(testo.lstrip(" \t\r\n"))],
        testo[len(testo.rstrip(" \t\r\n")) :],
    )


def controlla(percorso):
    """Restituisce gli elenchi dei problemi trovati in un catalogo."""
    po = polib.pofile(percorso)
    rotte, forma, sospette = [], [], []
    for voce in po:
        if voce.obsolete or not voce.msgstr or not voce.msgid:
            continue
        originale, tradotta = voce.msgid, voce.msgstr

        attesi = sorted(SEGNAPOSTO.findall(originale))
        trovati = sorted(SEGNAPOSTO.findall(tradotta))
        if attesi != trovati:
            mancanti = [s for s in attesi if s not in trovati]
            estranei = [s for s in trovati if s not in attesi]
            rotte.append((voce, mancanti, estranei))
            continue

        if MARCATORE_RIMASTO.search(tradotta):
            rotte.append((voce, ["marcatore di lavorazione rimasto"], []))
            continue

        if _bordi(originale) != _bordi(tradotta):
            forma.append((voce, "spazi o a capo ai bordi diversi"))
        elif SEPARATORI.search(tradotta) and not SEPARATORI.search(originale):
            forma.append((voce, "contiene una riga di separatori"))

        if tradotta == originale and len(originale) > 12:
            sospette.append((voce, "identica all'italiano"))
        elif len(tradotta) > max(30, len(originale) * 2.5):
            sospette.append((voce, "molto piu' lunga dell'originale"))
    return po, rotte, forma, sospette


def main():
    radice = sys.argv[1] if len(sys.argv) > 1 else "locales"
    if not os.path.isdir(radice):
        print(f"Cartella non trovata: {radice}")
        return 1

    totale_rotte = 0
    for lingua in sorted(os.listdir(radice)):
        percorso = os.path.join(radice, lingua, "LC_MESSAGES", "messages.po")
        if not os.path.exists(percorso):
            continue
        po, rotte, forma, sospette = controlla(percorso)
        tradotte = len(po.translated_entries())
        print(f"{lingua}: {tradotte} tradotte, da tradurre {len(po.untranslated_entries())}")
        print(
            f"   segnaposto rotti {len(rotte)}, forma da guardare {len(forma)}, "
            f"traduzioni sospette {len(sospette)}"
        )
        totale_rotte += len(rotte)
        for voce, mancanti, estranei in rotte[:5]:
            print(f"   ROTTA: {voce.msgid[:56]!r}")
            print(f"      tradotta: {voce.msgstr[:56]!r}")
            if mancanti:
                print(f"      mancano: {mancanti}")
            if estranei:
                print(f"      in piu': {estranei}")
        for voce, motivo in forma[:3]:
            print(f"   forma, {motivo}: {voce.msgid[:44]!r} -> {voce.msgstr[:44]!r}")
        for voce, motivo in sospette[:3]:
            print(f"   sospetta, {motivo}: {voce.msgid[:44]!r}")
    print()
    if totale_rotte:
        print(f"Attenzione: {totale_rotte} traduzioni farebbero cadere il programma.")
        print("Vanno sistemate prima di compilare i cataloghi.")
        return 1
    print("Nessuna traduzione con segnaposto rotti: si puo' compilare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
