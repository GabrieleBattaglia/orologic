# Orologic, Easyfish: il punteggio dell'utente contro il motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, UltraCode).

"""Il punteggio Elo dell'utente nelle partite contro il motore.

Contano soltanto le partite contro un motore impostato con .e, perche' solo
li' l'avversario ha un numero: l'Elo che Stockfish dichiara. Il calcolo e'
quello del regolamento FIDE B.02: punteggio atteso dalla differenza di Elo,
con una differenza oltre i 400 punti contata come 400, e coefficiente K di
40 per le prime 30 partite, poi 20, e 10 da 2400 in su.

L'Elo di Stockfish e' tarato su partite fra motori, la scala CCRL Blitz, e
non su giocatori in carne e ossa: il punteggio dice come si va contro il
motore, e va letto cosi'.
"""

from .. import storage
from ..config import _

CHIAVE = "punteggio_contro_il_motore"
PUNTEGGIO_DI_PARTENZA = 1500


def leggi():
    """I dati del punteggio, o None se non si e' ancora giocata una partita."""
    return storage.LoadDB().get(CHIAVE)


def atteso(mio, avversario):
    """Il punteggio atteso in una partita, fra 0 e 1."""
    differenza = max(-400, min(400, avversario - mio))
    return 1 / (1 + 10 ** (differenza / 400))


def coefficiente(dati):
    """Il K della FIDE: 40 per le prime 30 partite, poi 20, 10 da 2400."""
    if dati["partite"] < 30:
        return 40
    if dati["punteggio"] >= 2400:
        return 10
    return 20


def registra(punti, avversario, partenza=PUNTEGGIO_DI_PARTENZA):
    """Aggiunge una partita: punti vale 1, 0.5 o 0, avversario e' l'Elo del
    motore. partenza serve solo alla prima partita. Restituisce i dati
    aggiornati e la variazione del punteggio."""
    esito = {}

    def modifica(db):
        dati = db.get(CHIAVE) or {
            "punteggio": partenza,
            "partite": 0,
            "vinte": 0,
            "patte": 0,
            "perse": 0,
            "massimo": partenza,
            "minimo": partenza,
        }
        variazione = round(
            coefficiente(dati) * (punti - atteso(dati["punteggio"], avversario))
        )
        dati["punteggio"] += variazione
        dati["partite"] += 1
        dati["vinte" if punti == 1 else "patte" if punti == 0.5 else "perse"] += 1
        dati["massimo"] = max(dati["massimo"], dati["punteggio"])
        dati["minimo"] = min(dati["minimo"], dati["punteggio"])
        dati["ultimo_avversario"] = avversario
        dati["ultima_partita"] = storage.data_di_adesso()
        db[CHIAVE] = dati
        esito.update(dati=dati, variazione=variazione)

    storage.UpdateDB(modifica)
    return esito["dati"], esito["variazione"]


def riga_attuale(dati):
    """Una riga da dire prima della partita."""
    if dati["partite"] == 1:
        return _("Il tuo punteggio contro il motore: {p}, dopo 1 partita.").format(
            p=dati["punteggio"]
        )
    return _("Il tuo punteggio contro il motore: {p}, dopo {n} partite.").format(
        p=dati["punteggio"], n=dati["partite"]
    )


def righe_dopo_la_partita(dati, variazione):
    """Le righe da dire dopo una partita conteggiata."""
    return [
        _("Punteggio contro il motore: {p}, {v:+d}.").format(
            p=dati["punteggio"], v=variazione
        ),
        *righe_riepilogo(dati),
    ]


def righe_riepilogo(dati):
    """Partite, esiti, massimo e minimo: dopo la partita e nella pagina di .gs."""
    fatti = (dati["vinte"] + dati["patte"] / 2) / dati["partite"] * 100
    return [
        _("Partite {n}: vinte {w}, patte {d}, perse {l}, punti {pct:.0f}%.").format(
            n=dati["partite"],
            w=dati["vinte"],
            d=dati["patte"],
            l=dati["perse"],
            pct=fatti,
        ),
        _("Massimo {max}, minimo {min}.").format(
            max=dati["massimo"], min=dati["minimo"]
        ),
    ]
