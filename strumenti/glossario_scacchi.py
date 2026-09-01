# Orologic, sviluppo: mette a posto i termini di gioco nelle traduzioni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

"""Corregge nei cataloghi i termini che un traduttore automatico sbaglia.

Sono le parole che si sentono a ogni mossa, e proprio per questo sono le
piu' importanti: una torre tradotta come costruzione o un pedone tradotto
come chi attraversa la strada rendono il programma inutilizzabile in
quella lingua. Qui si scrivono a mano, una volta per tutte, i termini che
gli scacchi usano davvero in ciascuna lingua.

Uso: python glossario_scacchi.py [--prova]
"""

import os
import sys

try:
    import polib
except ImportError:
    print("Libreria mancante. Installala con: pip install -r requirements-dev.txt")
    sys.exit(1)

# italiano: (inglese, spagnolo, francese, portoghese)
GLOSSARIO = {
    # I pezzi, al singolare e al plurale.
    "pedone": ("pawn", "peón", "pion", "peão"),
    "pedoni": ("pawns", "peones", "pions", "peões"),
    "cavallo": ("knight", "caballo", "cavalier", "cavalo"),
    "cavalli": ("knights", "caballos", "cavaliers", "cavalos"),
    "alfiere": ("bishop", "alfil", "fou", "bispo"),
    "alfieri": ("bishops", "alfiles", "fous", "bispos"),
    "torre": ("rook", "torre", "tour", "torre"),
    "torri": ("rooks", "torres", "tours", "torres"),
    "donna": ("queen", "dama", "dame", "dama"),
    "donne": ("queens", "damas", "dames", "damas"),
    "re": ("king", "rey", "roi", "rei"),
    # Cosa fa una mossa.
    "prende": ("takes", "toma", "prend", "toma"),
    "va in": ("to", "a", "en", "para"),
    "en passant": ("en passant", "al paso", "en passant", "en passant"),
    "arrocco corto": (
        "short castling",
        "enroque corto",
        "petit roque",
        "roque curto",
    ),
    "arrocco lungo": (
        "long castling",
        "enroque largo",
        "grand roque",
        "roque longo",
    ),
    "promuove a": ("promotes to", "promociona a", "promeut en", "promove a"),
    "e promuove a": (
        "and promotes to",
        "y promociona a",
        "et promeut en",
        "e promove a",
    ),
    "scacco": ("check", "jaque", "échec", "xeque"),
    "scacco matto": ("checkmate", "jaque mate", "échec et mat", "xeque-mate"),
    "scacco matto!": ("checkmate!", "¡jaque mate!", "échec et mat !", "xeque-mate!"),
    # I colori, nelle forme che servono agli accordi.
    "bianco": ("white", "blanco", "blanc", "branco"),
    "bianca": ("white", "blanca", "blanche", "branca"),
    "bianchi": ("white", "blancos", "blancs", "brancos"),
    "bianche": ("white", "blancas", "blanches", "brancas"),
    "nero": ("black", "negro", "noir", "preto"),
    "nera": ("black", "negra", "noire", "preta"),
    "neri": ("black", "negros", "noirs", "pretos"),
    "nere": ("black", "negras", "noires", "pretas"),
    # Come finisce una partita.
    "patta": ("draw", "tablas", "nulle", "empate"),
    "stallo": ("stalemate", "ahogado", "pat", "afogamento"),
    "abbandono": ("resignation", "abandono", "abandon", "desistência"),
}

LINGUE = ("en", "es", "fr", "pt")


def sistema(radice="locales", prova=False):
    totale = 0
    for posizione, lingua in enumerate(LINGUE):
        percorso = os.path.join(radice, lingua, "LC_MESSAGES", "messages.po")
        if not os.path.exists(percorso):
            continue
        po = polib.pofile(percorso)
        cambiate = []
        for voce in po:
            if voce.obsolete:
                continue
            giusta = GLOSSARIO.get(voce.msgid)
            if giusta is None:
                continue
            attesa = giusta[posizione]
            if voce.msgstr != attesa:
                cambiate.append((voce.msgid, voce.msgstr, attesa))
                if not prova:
                    voce.msgstr = attesa
        if cambiate and not prova:
            po.save()
        print(f"{lingua}: termini sistemati {len(cambiate)}")
        for italiano, vecchia, nuova in cambiate:
            print(f"   {italiano!r}: {vecchia!r} diventa {nuova!r}")
        totale += len(cambiate)
    print()
    if prova:
        print(
            f"Prova: sarebbero {totale} correzioni. Rilancia senza --prova per farle."
        )
    else:
        print(f"Termini di gioco sistemati: {totale}")
    return 0


if __name__ == "__main__":
    sys.exit(sistema(prova="--prova" in sys.argv))
