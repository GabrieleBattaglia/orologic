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

# La traduzione della lingua scelta, per predefinito, che ha un _ suo.
_della_lingua = _


def predefinito(traduci=None):
    """Dizionario di partenza, con i termini italiani di casa.

    Le colonne usano l'alfabeto telefonico italiano: alla sintesi vocale una
    parola intera arriva senza ambiguita', mentre le singole lettere si
    confondono facilmente fra loro. traduci, se c'e', e' la funzione di
    traduzione di un'altra lingua: serve allo sfoltimento dei nomi salvati
    interi (R110).
    """
    # Un _ locale, e pybabel estrae ancora i nomi.
    _ = traduci or _della_lingua
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


def differenze(dizionario, base=None):
    """Le sole voci di dizionario diverse da quelle di partenza nella lingua
    del momento. Prima si salvavano tutti i termini, e passando a un'altra
    lingua pezzi, colonne e giudizi restavano nella vecchia per sempre
    (R33)."""
    if base is None:
        base = predefinito()
    diverse = {}
    for chiave, valore in dizionario.items():
        if isinstance(valore, dict) and isinstance(base.get(chiave), dict):
            sotto = differenze(valore, base[chiave])
            if sotto:
                diverse[chiave] = sotto
        elif base.get(chiave) != valore:
            diverse[chiave] = valore
    return diverse


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


def _foglie(dizionario, prima=()):
    """I percorsi delle voci finali del dizionario."""
    foglie = set()
    for chiave, valore in dizionario.items():
        if isinstance(valore, dict):
            foglie |= _foglie(valore, (*prima, chiave))
        else:
            foglie.add((*prima, chiave))
    return foglie


def _predefiniti_di_ogni_lingua():
    """I nomi di partenza in italiano e in ogni lingua dei cataloghi."""
    import gettext
    import os

    from . import config

    basi = [predefinito(lambda testo: testo)]
    try:
        lingue = sorted(os.listdir(config.CARTELLA_LOCALES))
    except OSError:
        return basi
    for lingua in lingue:
        if os.path.isdir(os.path.join(config.CARTELLA_LOCALES, lingua, "LC_MESSAGES")):
            traduzione = gettext.translation("messages", localedir=config.CARTELLA_LOCALES, languages=[lingua], fallback=True)
            basi.append(predefinito(traduzione.gettext))
    return basi


def _sfoltite(scelte, basi):
    """Le scelte senza le voci uguali ai nomi di partenza di una delle basi."""
    restano = {}
    for chiave, valore in scelte.items():
        sotto = [base.get(chiave) for base in basi]
        if isinstance(valore, dict):
            diverse = _sfoltite(valore, [base for base in sotto if isinstance(base, dict)])
            if diverse:
                restano[chiave] = diverse
        elif valore not in sotto:
            restano[chiave] = valore
    return restano


def sfoltisci(scelte):
    """Le scelte salvate, sfoltite se sono il dizionario intero di prima
    della 9.5.26: le voci uguali ai nomi di partenza di una lingua qualunque
    se ne vanno, e restano le scelte vere. Prima nessuno sfoltiva quei
    database, e cambiando lingua pezzi, colonne e giudizi restavano nella
    vecchia (R110). Le sole differenze, salvate dopo, restano come sono."""
    if not scelte or not _foglie(predefinito()) <= _foglie(scelte):
        return scelte
    return _sfoltite(scelte, _predefiniti_di_ogni_lingua())


def carica(silenziosa=False):
    """Dizionario completo: termini di partenza piu' personalizzazioni salvate.
    silenziosa all'importazione: gli avvisi della lettura del database li
    dice Main dopo il benvenuto, perche' nella finestra andrebbero nel
    vuoto (R31). Il dizionario intero di prima della 9.5.26 si sfoltisce, e
    lo sfoltito si salva, una volta (R110)."""
    dizionario = predefinito()
    scelte_utente = storage.LoadDB(silenziosa=silenziosa).get("localization", {})
    sfoltite = sfoltisci(scelte_utente)
    if sfoltite != scelte_utente:
        storage.SetValue("localization", sfoltite)
        scelte_utente = sfoltite
    if scelte_utente:
        unisci(dizionario, scelte_utente)
    return dizionario


# Dizionario vivo, condiviso da tutti i moduli. Viene aggiornato sul posto e
# mai sostituito, cosi' chi lo ha gia' in mano continua a vedere i valori
# aggiornati: prima la personalizzazione dei nomi ricaricava una copia sola e
# le descrizioni delle mosse restavano indietro fino al riavvio.
L10N = carica(silenziosa=True)


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
