# Orologic, sviluppo: controlla i termini scacchistici nelle traduzioni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

"""Controlla che i pezzi e i termini di gioco siano tradotti come si deve.

E' il punto in cui un traduttore automatico sbaglia piu' spesso, perche'
traduce la parola e non il termine: la torre diventa una costruzione, il
cavallo un animale, la donna una signora. Qui si confronta la traduzione
con i termini che ogni lingua usa davvero negli scacchi.

Uso: python verifica_scacchi.py [cartella_locales]
"""

import os
import re
import sys

try:
    import polib
except ImportError:
    print("Libreria mancante. Installala con: pip install -r requirements-dev.txt")
    sys.exit(1)

# Per ogni termine italiano, le forme accettabili in ciascuna lingua.
# La prima e' quella preferita, le altre sono varianti in uso.
GLOSSARIO = {
    "pedone": {
        "en": ["pawn"],
        "es": ["peón", "peon"],
        "fr": ["pion"],
        "pt": ["peão", "peao"],
    },
    "pedoni": {
        "en": ["pawns"],
        "es": ["peones"],
        "fr": ["pions"],
        "pt": ["peões", "peoes"],
    },
    "cavallo": {
        "en": ["knight"],
        "es": ["caballo"],
        "fr": ["cavalier"],
        "pt": ["cavalo"],
    },
    "cavalli": {
        "en": ["knights"],
        "es": ["caballos"],
        "fr": ["cavaliers"],
        "pt": ["cavalos"],
    },
    "alfiere": {"en": ["bishop"], "es": ["alfil"], "fr": ["fou"], "pt": ["bispo"]},
    "alfieri": {"en": ["bishops"], "es": ["alfiles"], "fr": ["fous"], "pt": ["bispos"]},
    "torre": {"en": ["rook"], "es": ["torre"], "fr": ["tour"], "pt": ["torre"]},
    "torri": {"en": ["rooks"], "es": ["torres"], "fr": ["tours"], "pt": ["torres"]},
    "donna": {
        "en": ["queen"],
        "es": ["dama", "reina"],
        "fr": ["dame", "reine"],
        "pt": ["dama", "rainha"],
    },
    "donne": {
        "en": ["queens"],
        "es": ["damas", "reinas"],
        "fr": ["dames", "reines"],
        "pt": ["damas", "rainhas"],
    },
    "re": {"en": ["king"], "es": ["rey"], "fr": ["roi"], "pt": ["rei"]},
    "scacco": {
        "en": ["check"],
        "es": ["jaque"],
        "fr": ["échec", "echec"],
        "pt": ["xeque"],
    },
    "matto": {
        "en": ["mate", "checkmate"],
        "es": ["mate"],
        "fr": ["mat"],
        "pt": ["mate"],
    },
    "arrocco corto": {
        "en": ["short castling", "kingside castling", "castles short"],
        "es": ["enroque corto"],
        "fr": ["petit roque"],
        "pt": ["roque curto", "roque pequeno"],
    },
    "arrocco lungo": {
        "en": ["long castling", "queenside castling", "castles long"],
        "es": ["enroque largo"],
        "fr": ["grand roque"],
        "pt": ["roque longo", "roque grande"],
    },
    "presa al varco": {
        "en": ["en passant"],
        "es": ["al paso", "en passant"],
        "fr": ["en passant", "prise en passant"],
        "pt": ["en passant", "captura en passant"],
    },
    "patta": {
        "en": ["draw"],
        "es": ["tablas", "empate"],
        "fr": ["nulle", "partie nulle"],
        "pt": ["empate"],
    },
    "stallo": {
        "en": ["stalemate"],
        "es": ["ahogado", "rey ahogado"],
        "fr": ["pat"],
        "pt": ["afogamento", "rei afogado"],
    },
}

# A quale termine di gioco si riferisce ogni trappola: la parola sospetta
# vale solo se la frase italiana parla davvero di quel pezzo o di quella
# situazione. "Andare berserk" tradotto "volverse loco" e' corretto, e non
# c'entra niente con il matto.
RIGUARDA = {
    "tower": "torre",
    "horse": "cavall",
    "woman": "donna",
    "lady": "donna",
    "ensign": "alfier",
    "standard bearer": "alfier",
    "crazy": "matto",
    "mad": "matto",
    "chess set": "scacc",
    "tie": "patta",
    "stall": "stallo",
    "loco": "matto",
    "mujer": "donna",
    "senora": "donna",
    "señora": "donna",
    "abanderado": "alfier",
    "establo": "stallo",
    "folle": "matto",
    "fou furieux": "matto",
    "femme": "donna",
    "cheval": "cavall",
    "stalle": "stallo",
    "louco": "matto",
    "mulher": "donna",
    "senhora": "donna",
    "cavalheiro": "cavall",
    "estabulo": "stallo",
    "estábulo": "stallo",
}

# Parole che, se compaiono, tradiscono la traduzione letterale.
TRAPPOLE = {
    "en": {
        "tower": "torre tradotta come costruzione invece che rook",
        "horse": "cavallo tradotto come animale invece che knight",
        "woman": "donna tradotta come persona invece che queen",
        "lady": "donna tradotta come signora invece che queen",
        "ensign": "alfiere tradotto come grado militare invece che bishop",
        "standard bearer": "alfiere tradotto alla lettera invece che bishop",
        "crazy": "matto tradotto come folle invece che mate",
        "mad": "matto tradotto come folle invece che mate",
        "chess set": "scacco tradotto come gioco invece che check",
        "tie": "patta tradotta come pareggio sportivo invece che draw",
        "stall": "stallo tradotto come pausa invece che stalemate",
    },
    "es": {
        "loco": "matto tradotto come folle invece che mate",
        "mujer": "donna tradotta come persona invece che dama",
        "senora": "donna tradotta come signora invece che dama",
        "señora": "donna tradotta come signora invece che dama",
        "abanderado": "alfiere tradotto come portabandiera invece che alfil",
        "establo": "stallo tradotto come stalla invece che ahogado",
    },
    "fr": {
        "folle": "matto tradotto come folle invece che mat",
        "fou furieux": "matto tradotto come folle invece che mat",
        "femme": "donna tradotta come persona invece che dame",
        "cheval": "cavallo tradotto come animale invece che cavalier",
        "stalle": "stallo tradotto come stalla invece che pat",
    },
    "pt": {
        "louco": "matto tradotto come folle invece che mate",
        "mulher": "donna tradotta come persona invece che dama",
        "senhora": "donna tradotta come signora invece che dama",
        "cavalheiro": "cavallo tradotto come gentiluomo invece che cavalo",
        "estabulo": "stallo tradotto come stalla invece che afogamento",
        "estábulo": "stallo tradotto come stalla invece che afogamento",
    },
}


def controlla(percorso, lingua):
    po = polib.pofile(percorso)
    per_termine = {}
    for voce in po:
        if voce.obsolete or not voce.msgstr:
            continue
        per_termine[voce.msgid.strip().lower()] = voce.msgstr

    sbagliati, trappole = [], []
    for italiano, lingue in GLOSSARIO.items():
        tradotta = per_termine.get(italiano)
        if tradotta is None:
            continue
        attese = lingue.get(lingua, [])
        if attese and not any(a in tradotta.lower() for a in attese):
            sbagliati.append((italiano, tradotta, attese[0]))

    for voce in po:
        if voce.obsolete or not voce.msgstr:
            continue
        minuscolo = voce.msgstr.lower()
        for parola, motivo in TRAPPOLE.get(lingua, {}).items():
            # Parole intere: "install" contiene "stall" ma non c'entra nulla.
            if not re.search(rf"(?<!\w){re.escape(parola)}(?!\w)", minuscolo):
                continue
            # E la frase italiana deve parlare davvero di quel termine.
            riferimento = RIGUARDA.get(parola)
            if riferimento and riferimento not in voce.msgid.lower():
                continue
            if True:
                trappole.append((voce.msgid, voce.msgstr, motivo))
                break
    return sbagliati, trappole


def main():
    radice = sys.argv[1] if len(sys.argv) > 1 else "locales"
    problemi = 0
    for lingua in sorted(os.listdir(radice)):
        percorso = os.path.join(radice, lingua, "LC_MESSAGES", "messages.po")
        if not os.path.exists(percorso):
            continue
        sbagliati, trappole = controlla(percorso, lingua)
        print(
            f"{lingua}: termini fuori posto {len(sbagliati)}, parole sospette {len(trappole)}"
        )
        for italiano, tradotta, attesa in sbagliati:
            print(
                f"   {italiano!r} tradotto {tradotta!r}, ci si aspetta qualcosa come {attesa!r}"
            )
        for originale, tradotta, motivo in trappole[:8]:
            print(f"   {motivo}")
            print(f"      {originale[:50]!r} -> {tradotta[:50]!r}")
        problemi += len(sbagliati) + len(trappole)
    print()
    print(
        "Nessun termine di gioco fuori posto."
        if not problemi
        else f"Da guardare a mano: {problemi} punti."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
