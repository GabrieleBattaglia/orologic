# Orologic, Orolichess: i tornei arena di Lichess, da consultare.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, UltraCode).

"""I tornei arena di Lichess: elenco, scheda e classifica.

E' il primo pezzo della issue 57, e si consulta soltanto. Iscrizione, ritiro
e gioco vengono dopo, insieme ai tornei svizzeri, che Lichess non elenca da
soli ma solo attraverso le squadre.
"""

import datetime

from GBUtils import menu

from . import config, rete, tempo, ui
from .config import _

URL_ELENCO = "https://lichess.org/api/tournament"
URL_TORNEO = "https://lichess.org/api/tournament/{id}"
URL_CLASSIFICA = "https://lichess.org/api/tournament/{id}/results?nb={nb}"
URL_PAGINA = "https://lichess.org/tournament/{id}"
POSTI_IN_CLASSIFICA = 50
# Gli stati di un torneo arena nelle risposte di Lichess.
IN_ARRIVO, IN_CORSO, FINITO = 10, 20, 30


def cadenza(torneo):
    """La cadenza come la calcola Lichess: la durata stimata di una partita e'
    il tempo base piu' quaranta volte l'incremento. L'ultrabullet sta con il
    bullet, perche' nell'elenco ne compaiono pochi."""
    orologio = torneo.get("clock") or {}
    stima = orologio.get("limit", 0) + 40 * orologio.get("increment", 0)
    if stima < 180:
        return "bullet"
    if stima < 480:
        return "blitz"
    if stima < 1500:
        return "rapid"
    return "classical"


def _nomi_delle_cadenze():
    return {
        "bullet": _("Bullet"),
        "blitz": _("Blitz"),
        "rapid": _("Rapido"),
        "classical": _("Classico"),
    }


def _orologio(torneo):
    """Il tempo come lo scrive Lichess, minuti piu' secondi: 3+2, 0.5+0."""
    orologio = torneo.get("clock") or {}
    return f"{orologio.get('limit', 0) / 60:g}+{orologio.get('increment', 0)}"


def _quando(millisecondi, oggi, altro_giorno):
    """L'ora, e il giorno quando non e' oggi, dentro la frase giusta."""
    # Lichess da' i millisecondi dall'epoca, in UTC: si passa all'ora locale.
    utc = datetime.UTC
    momento = datetime.datetime.fromtimestamp(millisecondi / 1000, tz=utc).astimezone()
    ora = momento.strftime("%H:%M")
    if momento.date() == datetime.datetime.now(tz=utc).astimezone().date():
        return oggi.format(ora=ora)
    giorno = config.format_date_italian(momento, include_time=False)
    return altro_giorno.format(giorno=giorno, ora=ora)


def _giocatori(n):
    return _("1 giocatore") if n == 1 else _("{n} giocatori").format(n=n)


def riga_elenco(torneo):
    """Una riga dell'elenco: nome, tempo, variante, giocatori e orario."""
    parti = [torneo.get("fullName", "?"), _orologio(torneo)]
    chiave, nome = _variante(torneo)
    if chiave != "standard":
        parti.append(nome)
    if not torneo.get("rated", True):
        parti.append(_("amichevole"))
    parti.append(_giocatori(torneo.get("nbPlayers", 0)))
    if torneo.get("status") == IN_CORSO:
        parti.append(
            _quando(
                torneo.get("finishesAt", 0),
                _("in corso fino alle {ora}"),
                _("in corso fino a {giorno} alle {ora}"),
            )
        )
    else:
        parti.append(
            _quando(
                torneo.get("startsAt", 0),
                _("inizia alle {ora}"),
                _("inizia {giorno} alle {ora}"),
            )
        )
    return ", ".join(parti)


def tornei_da_elencare(dati, scelta):
    """I tornei della cadenza scelta, o di tutte con scelta None: prima
    quelli in corso, per ora di fine, poi quelli in arrivo, per ora
    d'inizio. Quelli finiti restano fuori."""
    in_corso = [t for t in dati.get("started", []) if scelta in (None, cadenza(t))]
    in_arrivo = [t for t in dati.get("created", []) if scelta in (None, cadenza(t))]
    in_corso.sort(key=lambda t: t.get("finishesAt", 0))
    in_arrivo.sort(key=lambda t: t.get("startsAt", 0))
    return in_corso + in_arrivo


def _variante(torneo, dall_elenco=None):
    """Chiave e nome della variante. Nell'elenco Lichess la da' come oggetto,
    con il nome; nella scheda solo come chiave, e il nome si prende
    dall'elenco da cui il torneo e' stato scelto."""
    variante = torneo.get("variant") or "standard"
    if isinstance(variante, dict):
        return variante.get("key", "standard"), variante.get("name", "?")
    if dall_elenco:
        return _variante(dall_elenco)
    return variante, variante.capitalize()


def righe_scheda(torneo, dall_elenco=None, connesso=False):
    """La scheda di un torneo, una riga per informazione. L'esito delle
    condizioni si dice solo a chi e' connesso: senza token Lichess le da'
    per soddisfatte, e la frase sarebbe falsa."""
    nomi = _nomi_delle_cadenze()
    righe = [torneo.get("fullName", "?")]
    righe.append(
        _("{cadenza} {orologio}, durata {m} minuti.").format(
            cadenza=nomi[cadenza(torneo)],
            orologio=_orologio(torneo),
            m=torneo.get("minutes", 0),
        )
    )
    chiave, nome = _variante(torneo, dall_elenco)
    if chiave != "standard":
        righe.append(_("Variante: {v}.").format(v=nome))
    righe.append(
        _("Valido per il punteggio.") if torneo.get("rated", True) else _("Amichevole.")
    )
    righe.append(_giocatori(torneo.get("nbPlayers", 0)) + ".")
    if torneo.get("isFinished"):
        righe.append(_("Finito."))
    elif torneo.get("isStarted"):
        righe.append(
            _("In corso, finisce fra {t}.").format(
                t=tempo.parlato(torneo.get("secondsToFinish", 0))
            )
        )
    else:
        righe.append(
            _("Inizia fra {t}.").format(t=tempo.parlato(torneo.get("secondsToStart", 0)))
        )
    posizione = torneo.get("position") or {}
    if posizione.get("name"):
        righe.append(_("Apertura obbligata: {nome}.").format(nome=posizione["name"]))
    for verdetto in (torneo.get("verdicts") or {}).get("list", []):
        if not connesso:
            righe.append(_("Condizione: {c}.").format(c=verdetto.get("condition")))
            continue
        esito = (
            _("soddisfatta") if verdetto.get("verdict") == "ok" else _("non soddisfatta")
        )
        righe.append(
            _("Condizione: {c}, {esito}.").format(c=verdetto.get("condition"), esito=esito)
        )
    io = torneo.get("me")
    if io:
        righe.append(_("Sei iscritto, al posto {r}.").format(r=io.get("rank", "?")))
    podio = torneo.get("podium") or []
    if podio:
        righe.append(
            _("Podio: {nomi}.").format(nomi=", ".join(p.get("name", "?") for p in podio))
        )
    return righe


def riga_classifica(giocatore):
    """Un giocatore in classifica: nome con il titolo, punti ed Elo."""
    nome = giocatore.get("username", "?")
    if giocatore.get("title"):
        nome = f"{giocatore['title']} {nome}"
    punti = giocatore.get("score", 0)
    testo_punti = _("1 punto") if punti == 1 else _("{n} punti").format(n=punti)
    return _("{nome}, {punti}, Elo {elo}").format(
        nome=nome, punti=testo_punti, elo=giocatore.get("rating", "?")
    )


def _classifica(id_torneo, token):
    giocatori, errore = rete.leggi_righe_json(
        URL_CLASSIFICA.format(id=id_torneo, nb=POSTI_IN_CLASSIFICA), token=token
    )
    if errore:
        print(_("Classifica non scaricata. {motivo}").format(motivo=errore))
        return
    if not giocatori:
        print(_("La classifica e' ancora vuota."))
        return
    # Le chiavi sono i posti, nell'ordine di Lichess: menu le mostra a
    # pagine, e ordinate come stringhe metterebbe il 10 prima del 2.
    righe = {str(g.get("rank", i)): riga_classifica(g) for i, g in enumerate(giocatori, 1)}
    menu(righe, show_only=True, ordered=False)


def _scheda(dall_elenco, token, db):
    id_torneo = dall_elenco["id"]
    torneo, errore = rete.leggi_json(URL_TORNEO.format(id=id_torneo), token=token)
    if errore:
        print(_("Torneo non scaricato. {motivo}").format(motivo=errore))
        return
    for riga in righe_scheda(torneo, dall_elenco, connesso=bool(token)):
        print(riga)
    while True:
        scelta = menu(
            {
                "classifica": _("Classifica"),
                "link": _("Copia il link del torneo negli appunti"),
                ".": _("Torna all'elenco"),
            },
            show=True,
            keyslist=True,
            p=_("\nScegli: "),
            numbered=db.get("menu_numerati", False),
        )
        if scelta in (".", None):
            return
        if scelta == "classifica":
            _classifica(id_torneo, token)
        elif scelta == "link":
            ui.copia_negli_appunti(
                URL_PAGINA.format(id=id_torneo),
                _("Link del torneo copiato negli appunti."),
            )


def menu_tornei(db, token=None):
    """Voce Tornei di Orolichess: cadenza, elenco, scheda e classifica."""
    dati, errore = rete.leggi_json(URL_ELENCO, token=token)
    if errore:
        print(_("Elenco dei tornei non scaricato. {motivo}").format(motivo=errore))
        return
    voci = dict(_nomi_delle_cadenze())
    voci["tutte"] = _("Tutte le cadenze")
    voci["."] = _("Torna al menu di Orolichess")
    while True:
        scelta = menu(
            voci,
            show=True,
            keyslist=True,
            p=_("\nTornei arena, scegli la cadenza: "),
            numbered=db.get("menu_numerati", False),
        )
        if scelta in (".", None):
            return
        tornei = tornei_da_elencare(dati, None if scelta == "tutte" else scelta)
        if not tornei:
            print(_("Nessun torneo di questa cadenza in corso o in arrivo."))
            continue
        print(
            _("{n} tornei, prima quelli in corso.").format(n=len(tornei))
            if len(tornei) > 1
            else _("1 torneo.")
        )
        elenco = {t["id"]: riga_elenco(t) for t in tornei}
        # Dalla scheda si torna all'elenco, e da qui con ESC alle cadenze.
        while True:
            scelto = menu(
                elenco,
                show=True,
                numbered=True,
                ordered=False,
                p=_("Scegli un torneo (ESC per tornare alle cadenze): "),
            )
            if scelto is None:
                break
            _scheda(next(t for t in tornei if t["id"] == scelto), token, db)
