# Orologic, modulo localizzazione: i nomi con cui il programma parla di scacchi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
#
# Qui sta l'unico dizionario dei termini scacchistici. Prima ne esistevano due,
# uno in config e uno in ui, con contenuti divergenti: la stessa figura era
# donna o regina, la stessa colonna Ancona oppure a, e la stessa annotazione
# mossa dubbia oppure mossa interessante, a seconda di quale parte del
# programma stesse parlando. Un terzo elenco, in alfabeto NATO, viveva dentro
# Easyfish.

from . import storage
from .config import _


def predefinito():
    """Dizionario di partenza, con i termini italiani di casa.

    Le colonne usano l'alfabeto telefonico italiano: alla sintesi vocale una
    parola intera arriva senza ambiguita', mentre le singole lettere si
    confondono facilmente fra loro.
    """
    return {
        "pieces": {
            "pawn": {"name": _("pedone"), "pname": _("pedoni"), "gender": "m"},
            "knight": {"name": _("cavallo"), "pname": _("cavalli"), "gender": "m"},
            "bishop": {"name": _("alfiere"), "pname": _("alfieri"), "gender": "m"},
            "rook": {"name": _("torre"), "pname": _("torri"), "gender": "f"},
            "queen": {"name": _("donna"), "pname": _("donne"), "gender": "f"},
            "king": {"name": _("re"), "pname": _("re"), "gender": "m"},
        },
        "columns": {
            "a": _("Ancona"),
            "b": _("Bologna"),
            "c": _("Como"),
            "d": _("Domodossola"),
            "e": _("Empoli"),
            "f": _("Firenze"),
            "g": _("Genova"),
            "h": _("Hotel"),
        },
        "adjectives": {
            "white": {
                "m": _("bianco"),
                "f": _("bianca"),
                "mp": _("bianchi"),
                "fp": _("bianche"),
            },
            "black": {
                "m": _("nero"),
                "f": _("nera"),
                "mp": _("neri"),
                "fp": _("nere"),
            },
        },
        "moves": {
            "capture": _("prende"),
            "capture_on": _("in"),
            "move": _("va in"),
            "move_to": _("in"),
            "en_passant": _("en passant"),
            "short_castle": _("arrocco corto"),
            "long_castle": _("arrocco lungo"),
            "promotion": _("promuove a"),
            "promotes_to": _("e promuove a"),
            "check": _("scacco"),
            "mate": _("scacco matto"),
            "checkmate": _("scacco matto!"),
        },
        "annotations": {
            "!": _("mossa forte"),
            "?": _("mossa debole"),
            "!!": _("mossa molto forte"),
            "??": _("mossa molto debole"),
            "!?": _("mossa interessante"),
            "?!": _("mossa dubbia"),
            "=": _("proposta di patta"),
        },
        "analysis": {
            "blunder": _("Svarione"),
            "mistake": _("Errore"),
            "inaccuracy": _("Inesattezza"),
            "good": _("Buona"),
            "brilliant": _("Geniale"),
            "normal": _("Ok"),
            "book": _("Teoria"),
        },
    }


def unisci(base, personalizzazioni):
    """Sovrappone al dizionario di partenza le scelte dell'utente."""
    for chiave, valore in personalizzazioni.items():
        if (
            chiave in base
            and isinstance(base[chiave], dict)
            and isinstance(valore, dict)
        ):
            unisci(base[chiave], valore)
        else:
            base[chiave] = valore
    return base


def carica():
    """Dizionario completo: termini di partenza piu' personalizzazioni salvate."""
    dizionario = predefinito()
    scelte_utente = storage.LoadDB().get("localization", {})
    if scelte_utente:
        unisci(dizionario, scelte_utente)
    return dizionario


# Dizionario vivo, condiviso da tutti i moduli. Viene aggiornato sul posto e
# mai sostituito, cosi' chi lo ha gia' in mano continua a vedere i valori
# aggiornati: prima la personalizzazione dei nomi ricaricava una copia sola e
# le descrizioni delle mosse restavano indietro fino al riavvio.
L10N = carica()


def ricarica():
    """Rilegge le personalizzazioni e aggiorna il dizionario per tutti."""
    nuovo = carica()
    L10N.clear()
    L10N.update(nuovo)
    return L10N


def colonna(lettera):
    """Nome parlato di una colonna, per esempio Ancona per la a."""
    return L10N.get("columns", {}).get(str(lettera).lower(), lettera)


def nome_pezzo(tipo_o_chiave, plurale=False):
    """Nome del pezzo a partire dal tipo di python-chess o dalla sua chiave."""
    chiave = tipo_o_chiave
    if isinstance(tipo_o_chiave, int):
        import chess

        chiave = chess.PIECE_NAMES[tipo_o_chiave]
    voce = L10N.get("pieces", {}).get(str(chiave).lower(), {})
    return voce.get("pname" if plurale else "name", str(chiave))


def genere_pezzo(tipo_o_chiave):
    """Genere grammaticale del pezzo, per accordare gli aggettivi."""
    chiave = tipo_o_chiave
    if isinstance(tipo_o_chiave, int):
        import chess

        chiave = chess.PIECE_NAMES[tipo_o_chiave]
    return L10N.get("pieces", {}).get(str(chiave).lower(), {}).get("gender", "m")


def aggettivo_colore(e_bianco, genere="m", plurale=False):
    """Aggettivo di colore accordato: bianca, neri, bianche e cosi' via."""
    voce = L10N.get("adjectives", {}).get("white" if e_bianco else "black", {})
    chiave = ("f" if genere == "f" else "m") + ("p" if plurale else "")
    ripiego = {
        "m": _("bianco") if e_bianco else _("nero"),
        "f": _("bianca") if e_bianco else _("nera"),
        "mp": _("bianchi") if e_bianco else _("neri"),
        "fp": _("bianche") if e_bianco else _("nere"),
    }[chiave]
    return voce.get(chiave, ripiego)
