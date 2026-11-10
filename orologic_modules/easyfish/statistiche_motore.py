# Orologic, Easyfish: le statistiche delle partite contro il motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, UltraCode).

"""Le statistiche delle partite contro il motore, issue 66.

Ogni partita .g conclusa con un risultato si registra con data, colore,
risultato e forza del motore, a qualunque forza: servono ai conti per
colore, all'attivita' nel tempo e alla proposta del colore della partita
seguente. Il punteggio Elo resta in punteggio_motore, che conta soltanto le
partite leali contro un motore impostato con .e; qui ogni partita ricorda se
e' entrata anche li'.

Le partite giocate prima della 8.33.0 non hanno questo registro: restano nei
totali del punteggio Elo, ma non nei conti per colore.
"""

import datetime

import chess

from .. import storage
from ..config import _
from . import punteggio_motore

CHIAVE = "partite_contro_il_motore"
GIORNI_PER_MESE = 365.25 / 12
GIORNI_RECENTI = 30
BIANCO, NERO = "w", "b"


def leggi():
    """L'elenco delle partite registrate, dalla piu' vecchia."""
    return list(storage.LoadDB().get(CHIAVE) or [])


def punti_del_risultato(risultato, colore_umano):
    """1, 0.5 o 0 per l'umano; None se la partita non ha un risultato."""
    if risultato == "1/2-1/2":
        return 0.5
    if risultato not in ("1-0", "0-1"):
        return None
    vince_il_bianco = risultato == "1-0"
    return 1 if vince_il_bianco == (colore_umano == chess.WHITE) else 0


def registra(
    risultato,
    colore_umano,
    forza,
    conta_per_elo,
    quando=None,
    elo_utente=None,
    variazione=None,
    elo_motore=None,
):
    """Aggiunge una partita conclusa al registro. Restituisce la voce scritta,
    o None se la partita non ha un risultato e quindi non si registra. Le
    partite a punteggio ricordano anche il tuo Elo dopo la partita, la sua
    variazione e l'Elo del motore per la seguente: sono la serie del mese."""
    punti = punti_del_risultato(risultato, colore_umano)
    if punti is None:
        return None
    voce = {
        "data": quando or storage.data_di_adesso(),
        "colore": BIANCO if colore_umano == chess.WHITE else NERO,
        "risultato": risultato,
        "punti": punti,
        "forza": {"tipo": forza.get("tipo"), "valore": forza.get("valore")},
        "profondita": forza.get("profondita"),
        "elo": bool(conta_per_elo),
        "carriera": True,
    }
    if conta_per_elo and elo_utente is not None:
        voce.update(
            elo_utente=elo_utente, variazione=variazione, elo_motore=elo_motore
        )

    def modifica(db):
        db.setdefault(CHIAVE, []).append(voce)

    storage.UpdateDB(modifica)
    return voce


def di_carriera(partite):
    """Le partite della carriera. Quelle registrate da Easyfish fino alla
    8.41.5 restano se erano entrate nel punteggio; le altre erano partite
    libere, e le statistiche della carriera non le contano."""
    return [voce for voce in partite if voce.get("carriera") or voce.get("elo")]


def righe_record(partite, dati_elo):
    """I record della carriera: la vittoria contro il motore piu' forte, la
    serie piu' lunga di vittorie e il tuo Elo massimo, con le date."""
    righe = [_("Record della carriera.")]
    vittorie = [
        voce
        for voce in partite
        if voce.get("punti") == 1 and (voce.get("forza") or {}).get("tipo") == "elo"
    ]
    if vittorie:
        migliore = max(vittorie, key=lambda voce: voce["forza"].get("valore") or 0)
        data = _data(migliore)
        righe.append(
            _("Vittoria contro il motore piu' forte: Elo {e}, il {data}.").format(
                e=migliore["forza"].get("valore"),
                data=data.strftime("%d/%m/%Y") if data else "?",
            )
        )
    else:
        righe.append(_("Nessuna vittoria contro il motore, per ora."))
    serie = serie_piu_lunga_di_vittorie(partite)
    if serie:
        righe.append(_("Serie piu' lunga di vittorie: {n}.").format(n=serie))
    con_elo = [voce for voce in partite if voce.get("elo_utente") is not None]
    if con_elo:
        cima = max(con_elo, key=lambda voce: voce["elo_utente"])
        data = _data(cima)
        righe.append(
            _("Il tuo Elo massimo: {e}, il {data}.").format(
                e=cima["elo_utente"], data=data.strftime("%d/%m/%Y") if data else "?"
            )
        )
    elif dati_elo:
        righe.append(_("Il tuo Elo massimo: {e}.").format(e=dati_elo["massimo"]))
    return righe


def serie_dell_elo(partite):
    """I valori del tuo Elo dopo ogni partita di carriera, per la
    sonificazione: dal primo all'ultimo."""
    return [voce["elo_utente"] for voce in partite if voce.get("elo_utente") is not None]


def _data(voce):
    try:
        return datetime.datetime.fromisoformat(voce.get("data", ""))
    except ValueError:
        return None


def conteggi_per_colore(partite):
    """Partite, vinte, patte e perse per ciascun colore."""
    conti = {
        colore: {"partite": 0, "vinte": 0, "patte": 0, "perse": 0}
        for colore in (BIANCO, NERO)
    }
    for voce in partite:
        conto = conti.get(voce.get("colore"))
        if conto is None:
            continue
        conto["partite"] += 1
        punti = voce.get("punti")
        if punti == 1:
            conto["vinte"] += 1
        elif punti == 0.5:
            conto["patte"] += 1
        else:
            conto["perse"] += 1
    return conti


def colore_proposto(partite):
    """Il colore da proporre per la partita seguente, con il motivo.

    La regola, decisa con Gabriele: il colore con meno partite; a parita',
    quello con piu' sconfitte; a parita' ancora, il Bianco. Restituisce il
    colore di python-chess e una frase che spiega la scelta.
    """
    conti = conteggi_per_colore(partite)
    bianco, nero = conti[BIANCO], conti[NERO]
    if bianco["partite"] != nero["partite"]:
        if bianco["partite"] < nero["partite"]:
            colore = chess.WHITE
        else:
            colore = chess.BLACK
        motivo = _("partite col Bianco {b}, col Nero {n}.").format(
            b=bianco["partite"], n=nero["partite"]
        )
    elif bianco["perse"] != nero["perse"]:
        colore = chess.WHITE if bianco["perse"] > nero["perse"] else chess.BLACK
        motivo = _(
            "a parita' di partite, sconfitte col Bianco {b}, col Nero {n}."
        ).format(b=bianco["perse"], n=nero["perse"])
    else:
        colore = chess.WHITE
        if bianco["partite"]:
            motivo = _("stesse partite e stesse sconfitte coi due colori.")
        else:
            motivo = _("e' la tua prima partita registrata.")
    return colore, motivo


def mesi_trascorsi(dal, adesso):
    """I mesi dalla prima partita, mai meno di uno: una partita giocata oggi
    vale una partita al mese, non trenta."""
    giorni = (adesso - dal).total_seconds() / 86400
    return max(1.0, giorni / GIORNI_PER_MESE)


def attivita(partite, adesso=None):
    """Data della prima partita, partite al mese da allora e partite degli
    ultimi trenta giorni. None se non c'e' nessuna partita datata."""
    adesso = adesso or datetime.datetime.now()
    date = [d for d in (_data(voce) for voce in partite) if d is not None]
    if not date:
        return None
    prima = min(date)
    soglia = adesso - datetime.timedelta(days=GIORNI_RECENTI)
    return {
        "prima": prima,
        "al_mese": len(date) / mesi_trascorsi(prima, adesso),
        "recenti": sum(1 for d in date if d >= soglia),
    }


def serie_in_corso(partite):
    """L'esito delle ultime partite di fila: (punti, quante). (None, 0) se
    non ci sono partite."""
    if not partite:
        return None, 0
    ultimo = partite[-1].get("punti")
    quante = 0
    for voce in reversed(partite):
        if voce.get("punti") != ultimo:
            break
        quante += 1
    return ultimo, quante


def serie_piu_lunga_di_vittorie(partite):
    migliore = attuale = 0
    for voce in partite:
        attuale = attuale + 1 if voce.get("punti") == 1 else 0
        migliore = max(migliore, attuale)
    return migliore


def serie_del_mese(partite, adesso=None):
    """La serie dell'Elo nel mese corrente, dalle partite a punteggio: Elo
    di inizio mese, attuale, massimo, minimo e medio, e quante partite. None
    se nel mese non ce n'e'."""
    adesso = adesso or datetime.datetime.now()
    valori = []
    for voce in partite:
        data = _data(voce)
        if voce.get("elo_utente") is None or data is None:
            continue
        if (data.year, data.month) == (adesso.year, adesso.month):
            valori.append(voce)
    if not valori:
        return None
    elo = [voce["elo_utente"] for voce in valori]
    inizio = valori[0]["elo_utente"] - (valori[0].get("variazione") or 0)
    return {
        "partite": len(valori),
        "inizio": inizio,
        "attuale": elo[-1],
        "variazione": elo[-1] - inizio,
        "massimo": max([inizio, *elo]),
        "minimo": min([inizio, *elo]),
        "media": sum(elo) / len(elo),
        "motore": valori[-1].get("elo_motore"),
    }


def _righe_del_mese(serie):
    if serie["partite"] == 1:
        partite = _("1 partita a punteggio")
    else:
        partite = _("{n} partite a punteggio").format(n=serie["partite"])
    return [
        _("Questo mese, {partite}: Elo da {a} a {b}, {v:+d}.").format(
            partite=partite, a=serie["inizio"], b=serie["attuale"], v=serie["variazione"]
        ),
        _("Nel mese massimo {max}, minimo {min}, media {m:.0f}.").format(
            max=serie["massimo"], min=serie["minimo"], m=serie["media"]
        ),
    ]


def _riga_colore(nome, conto):
    if not conto["partite"]:
        return _("{colore}: nessuna partita.").format(colore=nome)
    fatti = (conto["vinte"] + conto["patte"] / 2) / conto["partite"] * 100
    return _(
        "{colore}: partite {n}, vinte {w}, patte {d}, perse {l}, punti {pct:.0f}%."
    ).format(
        colore=nome,
        n=conto["partite"],
        w=conto["vinte"],
        d=conto["patte"],
        l=conto["perse"],
        pct=fatti,
    )


def _riga_serie(punti, quante):
    if quante < 2:
        return None
    if punti == 1:
        return _("Serie in corso: {n} vittorie di fila.").format(n=quante)
    if punti == 0.5:
        return _("Serie in corso: {n} patte di fila.").format(n=quante)
    return _("Serie in corso: {n} sconfitte di fila.").format(n=quante)


def righe_pagina(partite, dati_elo, adesso=None):
    """Le righe della pagina delle statistiche della carriera, nell'ordine
    in cui si leggono. partite sono gia' quelle di carriera."""
    righe = [_("Statistiche della carriera contro il motore.")]
    if not partite:
        righe.append(_("Nessuna partita di carriera registrata."))
    else:
        conti = conteggi_per_colore(partite)
        tot = {
            chiave: conti[BIANCO][chiave] + conti[NERO][chiave]
            for chiave in conti[BIANCO]
        }
        righe.append(_riga_colore(_("In totale"), tot))
        righe.append(_riga_colore(_("Col Bianco"), conti[BIANCO]))
        righe.append(_riga_colore(_("Col Nero"), conti[NERO]))
        dati = attivita(partite, adesso)
        if dati:
            righe.append(
                _("Dal {data}: {m:.2f} partite al mese.").format(
                    data=dati["prima"].strftime("%d/%m/%Y"), m=dati["al_mese"]
                )
            )
            righe.append(
                _("Partite negli ultimi {g} giorni: {n}.").format(
                    g=GIORNI_RECENTI, n=dati["recenti"]
                )
            )
        serie = _riga_serie(*serie_in_corso(partite))
        if serie:
            righe.append(serie)
        migliore = serie_piu_lunga_di_vittorie(partite)
        if migliore >= 2:
            righe.append(
                _("Serie piu' lunga di vittorie: {n}.").format(n=migliore)
            )
        ultima = _data(partite[-1])
        if ultima:
            righe.append(
                _("Ultima partita: {data}.").format(
                    data=ultima.strftime("%d/%m/%Y %H:%M")
                )
            )
        colore, motivo = colore_proposto(partite)
        nome = _("il Bianco") if colore == chess.WHITE else _("il Nero")
        righe.append(
            _("Alla prossima partita ti propongo {colore}: {motivo}").format(
                colore=nome, motivo=motivo
            )
        )
    if dati_elo:
        righe.append(punteggio_motore.riga_attuale(dati_elo))
        righe.extend(punteggio_motore.righe_riepilogo(dati_elo))
        elo = [voce for voce in partite if voce.get("elo")]
        if elo:
            conti = conteggi_per_colore(elo)
            righe.append(_riga_colore(_("Con l'Elo, col Bianco"), conti[BIANCO]))
            righe.append(_riga_colore(_("Con l'Elo, col Nero"), conti[NERO]))
        serie = serie_del_mese(partite, adesso)
        if serie:
            righe.extend(_righe_del_mese(serie))
        righe.append(
            _("Alla prossima partita il motore gioca a Elo {e}.").format(
                e=punteggio_motore.stato_ea()["elo_motore"]
            )
        )
    else:
        righe.append(
            _(
                "Punteggio Elo contro il motore: alla prima partita di carriera "
                "ti chiedo da dove parti."
            )
        )
    righe.append(
        _("Modello del motore: {m}.").format(
            m=punteggio_motore.descrivi_modello(punteggio_motore.modello())
        )
    )
    return righe
