# Orologic: il registro degli errori, in un file della cartella delle impostazioni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il registro degli errori (rilievo R15 della revisione 2, 26 novembre
2026). Prima un'eccezione del nucleo scriveva il traceback nell'area e nello
stesso giro la finestra si chiudeva: nessuno lo leggeva, e nel pacchetto
stderr andava nel vuoto, con gli errori dei gestori di wx e degli altri fili.

Ora ogni errore non gestito finisce in settings/errori.log, con l'ora e la
versione: quelli del nucleo, che la finestra mostra anche in una finestra da
leggere prima di chiudere, quelli di sys.excepthook, dove arrivano anche i
gestori di wx, e quelli dei fili, con threading.excepthook. Nel pacchetto
senza console anche stderr scrive qui. Oltre un megabyte il registro
riparte, e il vecchio resta accanto, errori.log.1.

Come avvio.py, il modulo non importa config: si installa prima del resto.
"""

import datetime
import os
import sys
import threading
import traceback

import percorsi

NOME = "errori.log"
MASSIMO = 1_000_000


def percorso():
    return percorsi.percorso_salvataggio(os.path.join("settings", NOME))


# Un filo per volta scrive nel registro (R136).
_LUCCHETTO = threading.Lock()


def _apri_in_fondo():
    file = percorso()
    os.makedirs(os.path.dirname(file), exist_ok=True)
    if os.path.isfile(file) and os.path.getsize(file) > MASSIMO:
        # Se il registro non si gira, per esempio perche' e' aperto in un
        # altro programma, la voce va in fondo lo stesso: prima si perdeva
        # (R136).
        try:
            os.replace(file, file + ".1")
        except OSError:
            pass
    return open(file, "a", encoding="utf-8")


def scrivi(testo):
    """Il testo in fondo al registro, con l'ora e la versione: il percorso
    del registro, o None se non si e' potuto scrivere. Non solleva mai."""
    try:
        from . import version

        with _LUCCHETTO, _apri_in_fondo() as registro:
            registro.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} Orologic {version.VERSION}\n{testo.rstrip()}\n\n")
        return percorso()
    # Il registro non deve mai fermare il programma che registra.
    except Exception:  # noqa: BLE001
        return None


class SulRegistro:
    """stderr nel pacchetto senza console: il testo va nel registro com'e'."""

    def write(self, testo):
        try:
            with _LUCCHETTO, _apri_in_fondo() as registro:
                registro.write(testo)
        # Come scrivi: mai un errore per scrivere un errore.
        except Exception:  # noqa: BLE001, S110
            pass
        return len(testo)

    def flush(self):
        pass


def installa():
    """I ganci sys.excepthook e threading.excepthook. stderr, nel pacchetto
    senza console, lo mette qui avvio.uscite_mute."""
    precedente = sys.excepthook

    def gancio(tipo, valore, tb):
        scrivi("".join(traceback.format_exception(tipo, valore, tb)))
        # Dove stderr e' gia' il registro, il gancio di serie lo scriverebbe due volte.
        if not isinstance(sys.stderr, SulRegistro):
            precedente(tipo, valore, tb)

    sys.excepthook = gancio
    precedente_dei_fili = threading.excepthook

    def gancio_dei_fili(argomenti):
        if argomenti.exc_type is not SystemExit:
            nome = argomenti.thread.name if argomenti.thread is not None else "?"
            scrivi(f"Filo {nome}:\n" + "".join(traceback.format_exception(argomenti.exc_type, argomenti.exc_value, argomenti.exc_traceback)))
        if not isinstance(sys.stderr, SulRegistro):
            precedente_dei_fili(argomenti)

    threading.excepthook = gancio_dei_fili
