# Orologic, modulo orologio: il tempo che scorre, in un posto solo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
#
# Prima esistevano tre thread orologio quasi uguali, uno per l'arbitraggio, uno
# per la modalita' Tempo che lo importava, e uno riscritto dentro Easyfish.
# Nessuno dei tre proteggeva i tempi mentre il resto del programma li
# modificava: aggiunte, sottrazioni e annullamenti potevano incrociarsi con il
# decremento in corso.

import threading
import time

from GBUtils import Acusticator

from . import config, tempo
from .config import _

# Un solo lucchetto per tutti i tempi di gioco. E' rientrante perche' le
# sezioni protette a volte si chiamano fra loro.
LUCCHETTO = threading.RLock()

# Ogni quanto il thread si sveglia per aggiornare i tempi.
PASSO = 0.1


def blocco():
    """Sezione in cui i tempi non devono cambiare sotto i piedi.

    Da usare con with attorno a ogni modifica dei tempi fatta dal programma
    principale, cosi' non si accavalla con il decremento del thread.
    """
    return LUCCHETTO


def _e_bianco(stato):
    """Vero se tocca al bianco, comunque sia scritto il colore di turno."""
    colore = stato.active_color
    if isinstance(colore, str):
        return colore == "white"
    return bool(colore)


def _residuo(stato, bianco):
    return stato.white_remaining if bianco else stato.black_remaining


def _imposta_residuo(stato, bianco, valore):
    if bianco:
        stato.white_remaining = valore
    else:
        stato.black_remaining = valore


def _deve_scorrere(stato, bianco):
    """Il tempo del colore di turno va consumato?

    In Easyfish il motore puo' giocare senza orologio: in quel caso il tempo
    scorre solo quando tocca all'essere umano.
    """
    if getattr(stato, "engine_has_clock", True):
        return True
    umano = getattr(stato, "human_color", None)
    if umano is None:
        return True
    umano_e_bianco = umano == "white" if isinstance(umano, str) else bool(umano)
    return bianco == umano_e_bianco


def _nome(stato, bianco):
    predefinito = _("Bianco") if bianco else _("Nero")
    return getattr(stato, "white_player" if bianco else "black_player", predefinito)


def _suona_allarme(bianco):
    Acusticator(["c4", 0.2, -0.75 if bianco else 0.75, config.VOLUME])


def _suona_bandierina():
    Acusticator(
        [
            "e4",
            0.2,
            -0.5,
            config.VOLUME,
            "d4",
            0.2,
            0,
            config.VOLUME,
            "c4",
            0.2,
            0.5,
            config.VOLUME,
        ],
        kind=1,
        adsr=[10, 0, 90, 10],
    )


def _ciclo(stato):
    """Consuma il tempo di chi ha il tratto e avvisa quando serve."""
    ultimo = time.time()
    allarmi = []
    if getattr(stato, "clock_config", None):
        allarmi = stato.clock_config.get("alarms", []) or []
    # Gli allarmi gia' superati alla partenza non hanno senso di suonare.
    with LUCCHETTO:
        suonati = {("white", a) for a in allarmi if stato.white_remaining <= a} | {
            ("black", a) for a in allarmi if stato.black_remaining <= a
        }

    while not stato.game_over:
        adesso = time.time()
        trascorso = adesso - ultimo
        ultimo = adesso

        with LUCCHETTO:
            in_corso = not stato.paused and not stato.ignore_clock
            if in_corso:
                bianco = _e_bianco(stato)
                if _deve_scorrere(stato, bianco):
                    _imposta_residuo(stato, bianco, _residuo(stato, bianco) - trascorso)
                    chiave_colore = "white" if bianco else "black"
                    for soglia in allarmi:
                        if (chiave_colore, soglia) in suonati:
                            continue
                        if _residuo(stato, bianco) <= soglia:
                            suonati.add((chiave_colore, soglia))
                            print(
                                _("Allarme, {chi} e' sceso a {quanto}").format(
                                    chi=_nome(stato, bianco),
                                    quanto=tempo.mmss_parlato(soglia),
                                )
                            )
                            _suona_allarme(bianco)

            scaduto = not stato.ignore_clock and (
                stato.white_remaining <= 0 or stato.black_remaining <= 0
            )
            primo_avviso = scaduto and not stato.flag_fallen
            if primo_avviso:
                bianco_scaduto = stato.white_remaining <= 0
                if bianco_scaduto:
                    stato.white_remaining = 0
                else:
                    stato.black_remaining = 0
                stato.flag_fallen = True
                stato.paused = True

        if primo_avviso:
            # Fuori dal lucchetto: suoni e messaggi non devono trattenere il
            # tempo di gioco.
            _suona_bandierina()
            print(
                _("Bandierina caduta: tempo scaduto per {chi}.").format(
                    chi=_nome(stato, bianco_scaduto)
                )
            )

        time.sleep(PASSO)


def avvia(stato):
    """Fa partire l'orologio per la partita indicata e restituisce il thread."""
    filo = threading.Thread(target=_ciclo, args=(stato,), daemon=True)
    filo.start()
    return filo


def aggiungi(stato, bianco, secondi):
    """Aggiunge o toglie tempo a un colore, senza interferire col decremento."""
    with LUCCHETTO:
        _imposta_residuo(stato, bianco, _residuo(stato, bianco) + secondi)
        return _residuo(stato, bianco)
