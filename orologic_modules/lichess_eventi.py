# Orologic, Orolichess: gli avvisi di Lichess in tempo reale.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, UltraCode).

"""L'ascolto del flusso degli eventi di Lichess, in sottofondo.

Finche' si e' in Orolichess con il token, un thread tiene aperto
/api/stream/event: Lichess vi manda in tempo reale le sfide che arrivano e
quelle ritirate, e appena ci si collega anche quelle gia' in attesa, con una
riga vuota ogni sette secondi per tenere viva la connessione. Ogni sfida in
arrivo si annuncia con un suono e una riga, ovunque si sia in Orolichess;
durante una partita propria solo con il suono, per non coprire le mosse.
Lichess tiene un solo flusso degli eventi per token: aprirne un secondo
chiude il primo, quindi ne esiste sempre uno solo.

Dallo stesso flusso arrivano le partite che cominciano. Quelle di un torneo
arena vanno all'attesa del torneo, se l'utente vi si trova, che le apre da
sola; altrimenti si annunciano, perche' l'utente le riprenda dal menu.
"""

import contextlib
import json
import queue
import sys
import threading

from GBUtils import Acusticator

from . import config, rete
from .config import _

URL = "https://lichess.org/api/stream/event"
# Dopo una caduta della rete si riprova, ma senza martellare Lichess.
ATTESA_DOPO_ERRORE = 15

_stato = {"thread": None, "ferma": None, "risposta": None, "token": None}
_solo_suono = threading.Event()
_annunciate = {}
_lucchetto = threading.Lock()
# L'attesa del torneo in cui si trova l'utente, e le partite che Lichess vi
# ha abbinato, pronte da aprire.
_attesa = {"torneo": None}
_partite_di_torneo = queue.Queue()
# Le partite di torneo gia' viste: Lichess rimanda gameStart per tutte le
# partite in corso a ogni riapertura del flusso.
_partite_viste = set()


def _scrivi(testo):
    sys.stdout.write("\n" + testo + "\n")
    sys.stdout.flush()


def _arrivata(sfida, mio_nome):
    """Una sfida nuova: si annuncia una volta sola, e mai quelle lanciate da
    chi usa Orologic, che il flusso manda anche loro."""
    sfidante = sfida.get("challenger") or {}
    if (sfidante.get("id") or "").lower() == (mio_nome or "").lower():
        return
    id_sfida = sfida.get("id")
    nome = sfidante.get("name", _("Anonimo"))
    with _lucchetto:
        if not id_sfida or id_sfida in _annunciate:
            return
        _annunciate[id_sfida] = nome
    Acusticator.play("orologic_sfida_in_arrivo", volume=config.VOLUME)
    if _solo_suono.is_set():
        return
    _scrivi(
        _("\nSfida da {u} ({v}, {s}, {r})")
        .format(
            u=nome,
            v=(sfida.get("variant") or {}).get("name", ""),
            s=sfida.get("speed", ""),
            r=_("Classificata") if sfida.get("rated") else _("Amichevole"),
        )
        .strip()
        + ". "
        + _("La trovi in Sfide in attesa, nel menu di Orolichess.")
    )


def _ritirata(sfida):
    """Una sfida annunciata e poi ritirata o rifiutata: lo si dice, perche'
    non la si cerchi invano nel menu."""
    with _lucchetto:
        nome = _annunciate.pop(sfida.get("id"), None)
    if nome and not _solo_suono.is_set():
        _scrivi(_("La sfida di {u} non c'e' piu'.").format(u=nome))


def _partita_iniziata(partita):
    """Una partita cominciata: conta solo se e' di un torneo. All'attesa di
    quel torneo arriva in coda; fuori dall'attesa si annuncia una volta."""
    torneo = partita.get("tournamentId")
    if not torneo:
        return
    with _lucchetto:
        if partita.get("gameId") in _partite_viste:
            return
        _partite_viste.add(partita.get("gameId"))
    # Il richiamo suona subito, anche nell'attesa: l'utente puo' essere
    # dentro la classifica, e la partita aspetta che ne esca.
    Acusticator.play("orologic_torneo_abbinamento", volume=config.VOLUME)
    if _attesa["torneo"] == torneo:
        _partite_di_torneo.put(dict(partita, suonata=True))
        return
    if _solo_suono.is_set():
        return
    avversario = (partita.get("opponent") or {}).get("username", _("Anonimo"))
    _scrivi(
        _(
            "Una tua partita di torneo e' cominciata, contro {u}: la trovi in "
            "Riprendi partita in corso, nel menu Gioca una partita."
        ).format(u=avversario)
    )


def entra_in_attesa(id_torneo):
    """L'utente e' nell'attesa di quel torneo: le sue partite vanno li'."""
    while not _partite_di_torneo.empty():
        _partite_di_torneo.get_nowait()
    _attesa["torneo"] = id_torneo


def esci_dall_attesa():
    _attesa["torneo"] = None


def partita_di_torneo():
    """La prossima partita abbinata nell'attesa, o None."""
    try:
        return _partite_di_torneo.get_nowait()
    except queue.Empty:
        return None


def _ascolta(token, mio_nome, ferma):
    while not ferma.is_set():
        risposta, errore = rete.apri(
            URL, token=token, timeout=rete.TIMEOUT_STREAM, accetta="application/x-ndjson"
        )
        if errore:
            ferma.wait(ATTESA_DOPO_ERRORE)
            continue
        _stato["risposta"] = risposta
        try:
            with risposta as flusso:
                for riga in flusso:
                    if ferma.is_set():
                        break
                    if not riga.strip():
                        continue
                    try:
                        evento = json.loads(riga.decode("utf-8"))
                    except ValueError:
                        continue
                    tipo = evento.get("type")
                    if tipo == "challenge":
                        _arrivata(evento.get("challenge") or {}, mio_nome)
                    elif tipo in ("challengeCanceled", "challengeDeclined"):
                        _ritirata(evento.get("challenge") or {})
                    elif tipo == "gameStart":
                        _partita_iniziata(evento.get("game") or {})
        # Una connessione caduta, o chiusa da ferma, non deve far cadere
        # Orologic: l'ascolto riparte dopo una pausa, se non e' finito.
        except Exception:  # noqa: BLE001, S110
            pass
        _stato["risposta"] = None
        ferma.wait(ATTESA_DOPO_ERRORE)


def avvia(token, mio_nome):
    """Comincia ad ascoltare, se non lo si sta gia' facendo con quel token."""
    thread = _stato["thread"]
    if thread and thread.is_alive() and _stato["token"] == token:
        return
    ferma()
    evento_ferma = threading.Event()
    thread = threading.Thread(
        target=_ascolta, args=(token, mio_nome, evento_ferma), daemon=True
    )
    _stato.update(thread=thread, ferma=evento_ferma, token=token)
    thread.start()


def ferma():
    """Smette di ascoltare: all'uscita da Orolichess e al logout."""
    if _stato["ferma"]:
        _stato["ferma"].set()
    risposta = _stato["risposta"]
    if risposta is not None:
        with contextlib.suppress(Exception):
            risposta.close()
    _stato.update(thread=None, ferma=None, risposta=None, token=None)
    with _lucchetto:
        _annunciate.clear()
        _partite_viste.clear()


def dimentica(id_sfida):
    """Una sfida accettata o rifiutata da qui: Lichess ne mandera' il ritiro,
    e non c'e' bisogno di annunciarlo a chi l'ha appena chiusa."""
    with _lucchetto:
        _annunciate.pop(id_sfida, None)


@contextlib.contextmanager
def solo_suono():
    """Durante una partita propria le sfide si annunciano solo col suono."""
    _solo_suono.set()
    try:
        yield
    finally:
        _solo_suono.clear()
