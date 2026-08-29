# Orologic, modulo rete: chiamate HTTP con timeout e messaggi parlanti.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from .config import _

# Attesa massima per una richiesta normale. Oltre questa soglia si rinuncia e
# si avvisa l'utente, invece di lasciare il programma muto a tempo indefinito.
TIMEOUT = 15.0
# Gli stream restano aperti a lungo e Lichess invia righe di presenza ogni
# pochi secondi: il timeout qui vale per la singola lettura, non per la durata
# complessiva, e serve ad accorgersi che la connessione e' caduta in silenzio.
TIMEOUT_STREAM = 30.0

INTESTAZIONE_AGENTE = "Orologic"


def prepara(url, token=None, metodo="GET", accetta=None):
    """Costruisce la richiesta con le intestazioni d'uso."""
    richiesta = urllib.request.Request(url, method=metodo)
    richiesta.add_header("User-Agent", INTESTAZIONE_AGENTE)
    if token:
        richiesta.add_header("Authorization", f"Bearer {token}")
    if accetta:
        richiesta.add_header("Accept", accetta)
    return richiesta


def _dettaglio_lichess(errore):
    """Estrae la spiegazione che Lichess mette nel corpo della risposta."""
    try:
        corpo = errore.read().decode("utf-8", errors="replace")
    except (OSError, AttributeError):
        return ""
    if not corpo:
        return ""
    try:
        dati = json.loads(corpo)
    except ValueError:
        return ""
    testo = dati.get("error") if isinstance(dati, dict) else None
    if isinstance(testo, dict):
        testo = ", ".join(f"{k}: {v}" for k, v in testo.items())
    return str(testo) if testo else ""


def _messaggio_http(errore):
    """Traduce un errore HTTP in una frase comprensibile."""
    codice = errore.code
    dettaglio = _dettaglio_lichess(errore)
    # Per i problemi di credenziali il consiglio pratico vale piu' della frase
    # del server, che dice soltanto che il token non esiste.
    if codice == 401:
        return _("Il token di accesso non e' piu' valido: rifai il login a Lichess.")
    if codice == 403:
        return _("Il tuo token non ha i permessi necessari per questa operazione.")
    if dettaglio:
        return _("Lichess ha rifiutato la richiesta: {motivo}").format(motivo=dettaglio)
    if codice == 404:
        return _("Non trovato: l'indirizzo richiesto non esiste su Lichess.")
    if codice == 429:
        attesa = errore.headers.get("Retry-After") if errore.headers else None
        if attesa:
            return _(
                "Lichess sta limitando le richieste. Riprova fra {n} secondi."
            ).format(n=attesa)
        return _("Lichess sta limitando le richieste. Attendi qualche istante.")
    if 500 <= codice < 600:
        return _(
            "Lichess ha un problema momentaneo (errore {c}). Riprova piu' tardi."
        ).format(c=codice)
    return _("Lichess ha risposto con l'errore {c}.").format(c=codice)


def _messaggio_urlerror(errore, secondi):
    """Traduce un errore di connessione in una frase comprensibile."""
    motivo = getattr(errore, "reason", errore)
    if isinstance(motivo, TimeoutError):
        return _("Nessuna risposta entro {n} secondi.").format(n=int(secondi))
    if isinstance(motivo, socket.gaierror):
        return _("Server non raggiungibile: controlla la connessione a internet.")
    return _("Connessione non riuscita: {motivo}").format(motivo=motivo)


def apri(
    url,
    token=None,
    metodo="GET",
    dati=None,
    timeout=TIMEOUT,
    accetta=None,
    dati_json=None,
):
    """Apre una connessione e restituisce la coppia (risposta, errore).

    La risposta va usata come contesto e chiusa dal chiamante; serve per gli
    stream e per le letture a blocchi. Se errore non e' None, la risposta e'
    None e il messaggio e' gia' pronto da mostrare all'utente.
    I dati si passano come dizionario da codificare in forma classica, oppure
    con dati_json quando il servizio pretende un corpo JSON.
    """
    richiesta = prepara(url, token=token, metodo=metodo, accetta=accetta)
    if dati_json is not None:
        corpo = json.dumps(dati_json).encode("utf-8")
        richiesta.add_header("Content-Type", "application/json")
    else:
        corpo = urllib.parse.urlencode(dati).encode("utf-8") if dati else None
    try:
        return urllib.request.urlopen(richiesta, data=corpo, timeout=timeout), None
    except urllib.error.HTTPError as e:
        return None, _messaggio_http(e)
    except urllib.error.URLError as e:
        return None, _messaggio_urlerror(e, timeout)
    except TimeoutError:
        return None, _("Nessuna risposta entro {n} secondi.").format(n=int(timeout))
    except OSError as e:
        return None, _("Connessione non riuscita: {motivo}").format(motivo=e)


def leggi(url, token=None, metodo="GET", dati=None, timeout=TIMEOUT, accetta=None):
    """Scarica una risorsa e ne restituisce il testo, con (testo, errore)."""
    risposta, errore = apri(
        url, token=token, metodo=metodo, dati=dati, timeout=timeout, accetta=accetta
    )
    if errore:
        return None, errore
    try:
        with risposta:
            return risposta.read().decode("utf-8", errors="replace"), None
    except TimeoutError:
        return None, _("Nessuna risposta entro {n} secondi.").format(n=int(timeout))
    except OSError as e:
        return None, _("Lettura interrotta: {motivo}").format(motivo=e)


def leggi_json(url, token=None, metodo="GET", dati=None, timeout=TIMEOUT):
    """Scarica e interpreta una risposta JSON, con (dati, errore)."""
    testo, errore = leggi(
        url,
        token=token,
        metodo=metodo,
        dati=dati,
        timeout=timeout,
        accetta="application/json",
    )
    if errore:
        return None, errore
    if not testo or not testo.strip():
        return None, _("Il server ha risposto senza dati.")
    try:
        return json.loads(testo), None
    except ValueError:
        return None, _("La risposta del server non e' comprensibile.")


def leggi_righe_json(url, token=None, timeout=TIMEOUT):
    """Scarica un elenco in formato ndjson e restituisce (lista, errore).

    Le righe illeggibili vengono saltate: il formato prevede un oggetto per
    riga e una riga corrotta non deve far perdere tutte le altre.
    """
    testo, errore = leggi(
        url, token=token, timeout=timeout, accetta="application/x-ndjson"
    )
    if errore:
        return None, errore
    elementi = []
    for riga in testo.splitlines():
        riga = riga.strip()
        if not riga:
            continue
        try:
            elementi.append(json.loads(riga))
        except ValueError:
            continue
    return elementi, None


def invia(url, token=None, dati=None, timeout=TIMEOUT, dati_json=None):
    """Esegue una richiesta POST e restituisce (riuscita, errore).

    Diversamente dal semplice vero o falso, in caso di rifiuto il messaggio
    dice perche': token scaduto, mossa non accettata, limite di frequenza.
    """
    risposta, errore = apri(
        url,
        token=token,
        metodo="POST",
        dati=dati,
        timeout=timeout,
        dati_json=dati_json,
    )
    if errore:
        return False, errore
    with risposta:
        if 200 <= risposta.status < 300:
            return True, None
        return False, _("Lichess ha risposto con l'errore {c}.").format(
            c=risposta.status
        )
