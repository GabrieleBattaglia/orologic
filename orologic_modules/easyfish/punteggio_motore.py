# Orologic: il punteggio dell'utente nella carriera contro il motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il punteggio Elo dell'utente nella carriera contro il motore.

Contano soltanto le partite di carriera, dal menu gioca, dove il motore ha
un Elo che decide il modello scelto dall'utente. Il calcolo e'
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
# L'Elo del motore per la prossima partita di carriera. La chiave porta
# ancora il nome della partita a punteggio, il .ea della 8.38.0, perche' i
# dati gia' salvati restino validi.
CHIAVE_EA = "partita_a_punteggio"
ELO_MOTORE_PREDEFINITO = 1500
# La forza dell'ultima partita libera, che torna alla seguente anche dopo
# aver chiuso il programma: prima il motore ripartiva al massimo.
CHIAVE_FORZA = "forza_del_motore"
# Il modello con cui il motore della carriera sceglie il proprio Elo.
CHIAVE_MODELLO = "modello_del_motore"
MODELLO_PREDEFINITO = {"tipo": "casuale", "da": -50, "a": 50}
# La curva dell'inseguimento: il salto e' d * |d| / (|d| + CURVA).
CURVA = 100


def leggi():
    """I dati del punteggio, o None se non si e' ancora giocata una partita."""
    return storage.LoadDB().get(CHIAVE)


def stato_ea():
    """L'Elo del motore per la prossima partita di carriera. La chiave
    attiva, della partita a punteggio .ea fino alla 8.41.5, non serve piu'."""
    dati = storage.LoadDB().get(CHIAVE_EA) or {}
    try:
        elo = int(dati.get("elo_motore") or ELO_MOTORE_PREDEFINITO)
    except (TypeError, ValueError):
        elo = ELO_MOTORE_PREDEFINITO
    return {"attiva": bool(dati.get("attiva")), "elo_motore": elo}


def salva_ea(**campi):
    """Aggiorna l'Elo del motore per la prossima partita, elo_motore."""

    def modifica(db):
        dati = dict(db.get(CHIAVE_EA) or {})
        dati.update(campi)
        db[CHIAVE_EA] = dati

    storage.UpdateDB(modifica)


def forza_ricordata():
    """La forza dell'ultima partita a punteggio spento, o None."""
    forza = storage.LoadDB().get(CHIAVE_FORZA)
    if isinstance(forza, dict) and forza.get("tipo") in ("livello", "elo", "lichess"):
        return forza
    return None


def ricorda_forza(forza):
    def modifica(db):
        db[CHIAVE_FORZA] = {
            "tipo": forza.get("tipo"),
            "valore": forza.get("valore"),
            "profondita": forza.get("profondita"),
        }

    storage.UpdateDB(modifica)


def modello():
    """Il modello del motore della carriera, con i suoi valori."""
    salvato = storage.LoadDB().get(CHIAVE_MODELLO)
    if isinstance(salvato, dict) and salvato.get("tipo") in (
        "uguale",
        "delta",
        "casuale",
        "inseguimento",
    ):
        return salvato
    return dict(MODELLO_PREDEFINITO)


def salva_modello(nuovo):
    def modifica(db):
        db[CHIAVE_MODELLO] = dict(nuovo)

    storage.UpdateDB(modifica)


def descrivi_modello(scelto):
    """Il modello in una frase breve, per il menu della carriera."""
    tipo = scelto.get("tipo")
    if tipo == "uguale":
        return _("uguale, il motore ha il tuo Elo")
    if tipo == "delta":
        return _("delta assoluto, il tuo Elo {d:+d}").format(d=scelto.get("delta", 0))
    if tipo == "casuale":
        return _("delta casuale, il tuo Elo da {a:+d} a {b:+d}").format(
            a=scelto.get("da", 0), b=scelto.get("a", 0)
        )
    return _("inseguimento, il motore ti insegue")


def passo_di_inseguimento(elo_utente, elo_motore, punti):
    """Di quanto si sposta il motore che insegue, dopo una partita.

    La distanza d e' il tuo Elo, gia' aggiornato, meno quello del motore. Se
    il risultato spinge il motore verso di te, cioe' vinci quando lui e'
    sotto o perdi quando e' sopra, il salto segue una curva: d * |d| /
    (|d| + 100), 17 punti a 50 di distanza, 50 a 100, 225 a 300. La patta
    da' meta' del salto, verso di te. Il risultato contrario lascia il motore
    fermo, e la distanza la chiude il tuo Elo, cosi' il sorpasso e'
    possibile: tu 1600 e il motore 1800, vincendo sempre lo superi alla
    sedicesima, e poi lui ti insegue a circa 25 punti; in discesa lo stesso.
    Regola decisa con Gabriele il 12 novembre 2026, issue 70: prima il passo
    contrario di 5 punti, e il passo di 10 sotto i 10 punti di distanza,
    tenevano il motore sempre davanti.
    """
    d = elo_utente - elo_motore
    salto = d * abs(d) / (abs(d) + CURVA)
    if punti == 0.5:
        return round(salto / 2)
    favorevole = (punti == 1 and d > 0) or (punti == 0 and d < 0)
    return round(salto) if favorevole else 0


def prossimo_elo(scelto, elo_utente, elo_motore, punti, minimo, massimo, caso):
    """L'Elo del motore per la partita seguente, secondo il modello, entro i
    limiti del motore. caso e' una funzione come random.randint, passata
    da fuori perche' le prove la possano fissare. punti e' None quando il
    modello cambia fra una partita e l'altra."""
    tipo = scelto.get("tipo")
    if tipo == "uguale":
        voluto = elo_utente
    elif tipo == "delta":
        voluto = elo_utente + int(scelto.get("delta", 0))
    elif tipo == "casuale":
        da, a = int(scelto.get("da", 0)), int(scelto.get("a", 0))
        voluto = elo_utente + caso(min(da, a), max(da, a))
    elif punti is None:
        voluto = elo_motore
    else:
        passo = passo_di_inseguimento(elo_utente, elo_motore, punti)
        # Fuori dalla portata del motore il passo contrario non vale: sotto il
        # suo minimo non sale, sopra il suo massimo non scende, perche' ti
        # allontanerebbe senza che tu possa mai raggiungerlo. Issue 70: tu a
        # 1135 vinci, il motore a 1320, il suo minimo, saliva a 1325.
        if elo_utente < minimo:
            passo = min(passo, 0)
        elif elo_utente > massimo:
            passo = max(passo, 0)
        voluto = elo_motore + passo
        # Fermo al limite perche' sei fuori portata: il messaggio lo dice.
        if elo_utente < minimo and voluto <= minimo:
            voluto = min(voluto, elo_utente)
        elif elo_utente > massimo and voluto >= massimo:
            voluto = max(voluto, elo_utente)
    return max(minimo, min(massimo, voluto)), voluto


def azzera_carriera():
    """Cancella la carriera: punteggio, registro delle partite ed Elo del
    motore. Il modello resta quello scelto."""
    from . import statistiche_motore

    def modifica(db):
        for chiave in (CHIAVE, CHIAVE_EA, statistiche_motore.CHIAVE):
            db.pop(chiave, None)

    storage.UpdateDB(modifica)


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
