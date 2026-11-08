# Orologic, Orolichess: i tornei arena di Lichess, da consultare.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, UltraCode).

"""I tornei arena di Lichess: elenco, scheda, classifica, iscrizione e gioco.

Dalla 8.31.0 si consultano; dalla 8.35.0, issue 57, ci si iscrive, ci si
ritira e si gioca. I tornei svizzeri restano per dopo: Lichess non li elenca
da soli, ma solo attraverso le squadre.

Due vincoli di Lichess decidono come si gioca. Le API di Orologic sono quelle
delle scacchiere elettroniche, che nei tornei ammettono soltanto le cadenze
rapid e classica: ai bullet e ai blitz non ci si iscrive. E Lichess abbina
solo chi sta sulla pagina del torneo, o chi ogni minuto rinnova la richiesta
con pairMeAsap: per questo si gioca dall'attesa del torneo, che rinnova la
richiesta, apre da sola le partite abbinate e, quando la si lascia a torneo
iniziato, mette l'utente in pausa, perche' non venga abbinato mentre e'
altrove.
"""

import datetime
import msvcrt
import sys
import time

from GBUtils import Acusticator, dgt, menu

from . import config, lichess_eventi, rete, tempo, ui
from .config import _

URL_ELENCO = "https://lichess.org/api/tournament"
URL_TORNEO = "https://lichess.org/api/tournament/{id}"
URL_CLASSIFICA = "https://lichess.org/api/tournament/{id}/results?nb={nb}"
URL_PAGINA = "https://lichess.org/tournament/{id}"
URL_ISCRIZIONE = "https://lichess.org/api/tournament/{id}/join"
URL_RITIRO = "https://lichess.org/api/tournament/{id}/withdraw"
# Le sole cadenze che le API delle scacchiere ammettono nei tornei.
CADENZE_GIOCABILI = ("rapid", "classical")
# Lichess lascia valida la richiesta pairMeAsap per un minuto: la si rinnova
# un po' prima.
RINNOVO_RICHIESTA = 50
AGGIORNA_TORNEO = 30
# A ridosso dell'inizio il torneo si rilegge piu' spesso, ma non piu' di
# una volta ogni tre secondi.
RILETTURA_ALL_INIZIO = 3
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
    if io and io.get("withdraw"):
        righe.append(_("Sei in pausa nel torneo, al posto {r}.").format(r=io.get("rank", "?")))
    elif io:
        righe.append(_("Sei iscritto, al posto {r}.").format(r=io.get("rank", "?")))
    podio = torneo.get("podium") or []
    if podio:
        righe.append(
            _("Podio: {nomi}.").format(nomi=", ".join(p.get("name", "?") for p in podio))
        )
    return righe


def giocabile(torneo):
    """Vero se il torneo ha una cadenza che Orologic puo' giocare."""
    return cadenza(torneo) in CADENZE_GIOCABILI


def spiega_errore(errore):
    """Il rifiuto di Lichess in parole. Senza il permesso tournament:write il
    token non basta per iscriversi: lo si dice, e si dice come rimediare."""
    if errore == _("Il tuo token non ha i permessi necessari per questa operazione."):
        return _(
            "Il tuo token non ha il permesso di iscriverti ai tornei. Creane uno "
            "nuovo su lichess.org/account/oauth/token, spuntando anche "
            "Create, update, and join tournaments (tournament:write), e rifai "
            "il login di Orolichess con il token nuovo."
        )
    return errore


def iscriviti(torneo, token):
    """Iscrive al torneo, o lo riprende dopo una pausa, chiedendo a Lichess
    di abbinare subito. Chiede la password ai tornei privati e la squadra
    alle battaglie a squadre. Restituisce vero se Lichess ha accettato."""
    dati = {"pairMeAsap": "true"}
    if torneo.get("private"):
        password = dgt(
            _("Il torneo e' privato: scrivi la password, INVIO per rinunciare: "),
            kind="s",
            default="",
        ).strip()
        if not password:
            return False
        dati["password"] = password
    squadre = (torneo.get("teamBattle") or {}).get("teams") or {}
    if squadre:
        voci = dict(squadre)
        squadra = menu(
            voci,
            show=True,
            numbered=True,
            ordered=False,
            p=_("Torneo a squadre: scegli la tua squadra (ESC per rinunciare): "),
        )
        if squadra is None:
            return False
        dati["team"] = squadra
    riuscito, errore = rete.invia(
        URL_ISCRIZIONE.format(id=torneo["id"]), token=token, dati=dati
    )
    if not riuscito:
        Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
        print(_("Iscrizione non riuscita. {motivo}").format(motivo=spiega_errore(errore)))
        return False
    return True


def ritirati(torneo, token):
    """Lascia un torneo che non e' cominciato, o si mette in pausa in uno in
    corso: punti e serie restano. Restituisce vero se Lichess ha accettato."""
    riuscito, errore = rete.invia(URL_RITIRO.format(id=torneo["id"]), token=token)
    if not riuscito:
        print(_("Ritiro non riuscito. {motivo}").format(motivo=spiega_errore(errore)))
        return False
    Acusticator.play("orologic_torneo_ritiro", volume=config.VOLUME)
    if torneo.get("isStarted"):
        print(
            _(
                "Sei in pausa nel torneo: punti e serie restano. Per rientrare, "
                "scegli Rientra nell'attesa nella scheda del torneo."
            )
        )
    else:
        print(_("Non sei piu' iscritto al torneo."))
    return True


def in_pausa(torneo):
    """Vero se l'utente e' iscritto ma in pausa: Lichess lo dice in me."""
    return bool((torneo.get("me") or {}).get("withdraw"))


def riga_attesa(torneo):
    """La riga che si riscrive nell'attesa: stato, posto e tempo."""
    io = torneo.get("me") or {}
    if torneo.get("isFinished"):
        return _("Torneo finito.")
    if not torneo.get("isStarted"):
        return _("Inizia fra {t}").format(
            t=tempo.compatto(max(0, torneo.get("secondsToStart", 0)))
        )
    fine = tempo.compatto(max(0, torneo.get("secondsToFinish", 0)))
    if io.get("rank"):
        return _("Posto {r}, fine fra {t}").format(r=io["rank"], t=fine)
    return _("In attesa, fine fra {t}").format(t=fine)


def _aiuto_attesa():
    print(_("Attesa del torneo. Lichess ti abbina da solo, e la partita si apre qui."))
    print(_("c: classifica dei primi cinquanta"))
    print(_("s: scheda del torneo"))
    print(_("g: riprendi la tua partita in corso nel torneo"))
    print(_("?: questo aiuto"))
    print(_("ESC: esci dall'attesa; a torneo iniziato ti mette in pausa"))


def _scrivi_riga(testo):
    ui.pulisci_riga()
    sys.stdout.write("\r" + testo + "\r")
    sys.stdout.flush()


def _aggiorna(id_torneo, token):
    """Rilegge il torneo: i dati nuovi, o None se la lettura non riesce, e
    allora il chiamante tiene quelli che ha, con il loro orologio."""
    nuovo, errore = rete.leggi_json(URL_TORNEO.format(id=id_torneo), token=token)
    if errore or not isinstance(nuovo, dict):
        return None
    nuovo.setdefault("id", id_torneo)
    return nuovo


def _rinnova(id_torneo, token):
    """Chiede a Lichess di abbinare subito; vale un minuto. A chi e' gia'
    iscritto non servono password ne' squadra. Restituisce (riuscito,
    errore)."""
    return rete.invia(
        URL_ISCRIZIONE.format(id=id_torneo), token=token, dati={"pairMeAsap": "true"}
    )


def _gioca(partita_id, token, username):
    from . import lichess_board

    print()
    lichess_board.play_game(partita_id, token, username)


def _in_vista(torneo, partenza):
    """Il torneo con i secondi che corrono dall'ultima lettura riuscita."""
    trascorsi = int(time.monotonic() - partenza)
    vista = dict(torneo)
    for chiave in ("secondsToStart", "secondsToFinish"):
        if chiave in vista:
            vista[chiave] = max(0, vista[chiave] - trascorsi)
    return vista


def attesa(torneo, token, username, db):
    """L'attesa del torneo: rinnova la richiesta di abbinamento, apre le
    partite che Lichess abbina e si riscrive su una riga con il tempo che
    corre. All'uscita, a torneo iniziato, mette in pausa."""
    id_torneo = torneo["id"]
    if username:
        lichess_eventi.avvia(token, username)
    lichess_eventi.entra_in_attesa(id_torneo)
    _aiuto_attesa()
    letto = time.time()
    partenza = time.monotonic()
    rinnovato = time.time()
    rifiuto_detto = False
    iniziato = bool(torneo.get("isStarted"))
    # Le partite gia' aperte o lasciate non si riaprono da sole: Lichess le
    # rimanda a ogni riapertura del flusso. Le riprende il tasto g.
    giocate = set()
    try:
        while True:
            partita = lichess_eventi.partita_di_torneo()
            if partita and partita.get("gameId") in giocate:
                partita = None
            if partita is None:
                in_corso = (torneo.get("me") or {}).get("gameId")
                if in_corso and in_corso not in giocate:
                    partita = {"gameId": in_corso}
            if partita:
                if not partita.get("suonata"):
                    Acusticator.play("orologic_torneo_abbinamento", volume=config.VOLUME)
                avversario = (partita.get("opponent") or {}).get("username")
                print()
                if avversario:
                    print(_("Abbinamento: giochi contro {u}.").format(u=avversario))
                else:
                    print(_("Hai una partita in corso nel torneo: la riapro."))
                giocate.add(partita["gameId"])
                _gioca(partita["gameId"], token, username)
                print(_("Sei di nuovo nell'attesa del torneo."))
                _rinnova(id_torneo, token)
                rinnovato = time.time()
                letto = time.time()
                nuovo = _aggiorna(id_torneo, token)
                if nuovo:
                    torneo, partenza = nuovo, time.monotonic()
            adesso = time.time()
            vista = _in_vista(torneo, partenza)
            # A ridosso dell'inizio si rilegge spesso, ma non a ogni giro:
            # un limite di frequenza di Lichess fermerebbe anche le partite.
            sta_per_iniziare = not vista.get("isStarted") and not vista.get(
                "secondsToStart", 1
            )
            intervallo = RILETTURA_ALL_INIZIO if sta_per_iniziare else AGGIORNA_TORNEO
            if adesso - letto >= intervallo:
                letto = adesso
                nuovo = _aggiorna(id_torneo, token)
                if nuovo:
                    torneo, partenza = nuovo, time.monotonic()
                    vista = _in_vista(torneo, partenza)
            if torneo.get("isStarted") and not iniziato:
                # Appena comincia si chiede subito l'abbinamento: prima
                # dell'inizio pairMeAsap non vale.
                iniziato = True
                rinnovato = 0.0
            if torneo.get("isFinished"):
                Acusticator.play("orologic_torneo_finito", volume=config.VOLUME)
                print()
                posto = (torneo.get("me") or {}).get("rank")
                if posto:
                    print(_("Il torneo e' finito: sei arrivato al posto {r}.").format(r=posto))
                else:
                    print(_("Il torneo e' finito."))
                return
            if adesso - rinnovato >= RINNOVO_RICHIESTA and not torneo.get(
                "pairingsClosed"
            ):
                riuscito, errore = _rinnova(id_torneo, token)
                rinnovato = adesso
                if riuscito:
                    rifiuto_detto = False
                elif not rifiuto_detto:
                    rifiuto_detto = True
                    print()
                    print(
                        _("Lichess non ha accettato la richiesta di abbinamento. {motivo}").format(
                            motivo=spiega_errore(errore)
                        )
                    )
            _scrivi_riga(riga_attesa(vista))
            fine = time.monotonic() + 1
            while time.monotonic() < fine:
                if msvcrt.kbhit():
                    break
                time.sleep(0.05)
            if not msvcrt.kbhit():
                continue
            tasto = msvcrt.getwch()
            if tasto in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue
            tasto = tasto.lower()
            print()
            if tasto in ("\x1b", "."):
                if torneo.get("isStarted") and not torneo.get("isFinished"):
                    ritirati(torneo, token)
                else:
                    print(
                        _(
                            "Resti iscritto. Quando il torneo comincia, torna "
                            "nell'attesa: Lichess abbina solo chi e' presente."
                        )
                    )
                return
            if tasto == "c":
                _classifica(id_torneo, token)
            elif tasto == "s":
                for riga in righe_scheda(vista, connesso=True):
                    print(riga)
            elif tasto == "g":
                in_corso = (torneo.get("me") or {}).get("gameId")
                if in_corso:
                    giocate.discard(in_corso)
                else:
                    print(_("Non hai partite in corso nel torneo."))
            elif tasto == "?":
                _aiuto_attesa()
            else:
                print(_("Tasto non previsto: ? per l'aiuto."))
    finally:
        lichess_eventi.esci_dall_attesa()


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


def voci_scheda(torneo, dall_elenco=None, connesso=False):
    """Le voci della scheda: iscrizione, attesa e ritiro solo a chi e'
    connesso, in un torneo non finito e di una cadenza giocabile. Chi e' in
    pausa puo' solo rientrare."""
    voci = {}
    if connesso and not torneo.get("isFinished") and giocabile(dall_elenco or torneo):
        io = torneo.get("me")
        if not io:
            voci["iscriviti"] = _("Iscriviti ed entra nell'attesa")
        elif in_pausa(torneo):
            voci["attesa"] = _("Rientra nell'attesa del torneo")
        else:
            voci["attesa"] = _("Entra nell'attesa del torneo")
            voci["ritirati"] = (
                _("Mettiti in pausa nel torneo")
                if torneo.get("isStarted")
                else _("Ritira l'iscrizione")
            )
    voci["classifica"] = _("Classifica")
    voci["link"] = _("Copia il link del torneo negli appunti")
    voci["."] = _("Torna all'elenco")
    return voci


def _scheda(dall_elenco, token, db, username=None):
    """La scheda di un torneo e il suo menu. Si rilegge e si ridice solo dopo
    un'iscrizione, un'attesa o un ritiro, che la cambiano."""
    id_torneo = dall_elenco["id"]
    da_leggere = True
    while True:
        if da_leggere:
            torneo, errore = rete.leggi_json(URL_TORNEO.format(id=id_torneo), token=token)
            if errore:
                print(_("Torneo non scaricato. {motivo}").format(motivo=errore))
                return
            torneo.setdefault("id", id_torneo)
            for riga in righe_scheda(torneo, dall_elenco, connesso=bool(token)):
                print(riga)
            if token and not torneo.get("isFinished") and not giocabile(dall_elenco):
                print(
                    _(
                        "Su Orologic si giocano solo i tornei rapid e classici: Lichess "
                        "vieta il bullet e il blitz ai programmi come questo."
                    )
                )
            da_leggere = False
        scelta = menu(
            voci_scheda(torneo, dall_elenco, connesso=bool(token)),
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
        elif scelta == "iscriviti":
            if iscriviti(torneo, token):
                Acusticator.play("orologic_torneo_iscrizione", volume=config.VOLUME)
                print(_("Sei iscritto al torneo."))
                attesa(torneo, token, username, db)
            da_leggere = True
        elif scelta == "attesa":
            # Chi e' gia' iscritto rientra con la sola richiesta di
            # abbinamento, che toglie anche la pausa: password e squadra
            # Lichess le ha gia'.
            riuscito, errore = _rinnova(id_torneo, token)
            if riuscito:
                attesa(torneo, token, username, db)
            else:
                Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
                print(_("Rientro non riuscito. {motivo}").format(motivo=spiega_errore(errore)))
            da_leggere = True
        elif scelta == "ritirati":
            ritirati(torneo, token)
            da_leggere = True


def menu_tornei(db, token=None, username=None):
    """Voce Tornei di Orolichess: cadenza, elenco, scheda e classifica; con il
    token anche iscrizione, ritiro e gioco."""
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
            if len(tornei) == 1:
                # Con una voce sola menu la restituisce subito, senza
                # chiedere: nel ciclo la scheda si riapriva all'infinito, e
                # dalla 8.32.1 non si usciva piu' dai tornei. Qui la scheda si
                # apre una volta, e all'uscita si torna alle cadenze.
                _scheda(tornei[0], token, db, username)
                break
            scelto = menu(
                elenco,
                show=True,
                numbered=True,
                ordered=False,
                p=_("Scegli un torneo (ESC per tornare alle cadenze): "),
            )
            if scelto is None:
                break
            _scheda(next(t for t in tornei if t["id"] == scelto), token, db, username)
