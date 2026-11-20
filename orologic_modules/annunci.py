# Orologic: le impostazioni degli annunci della finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le impostazioni degli annunci, tappa T3 della GUI (Piano della GUI.txt, R3
e R8).

Nella finestra il testo nuovo della console si annuncia con GBsintesi, come
lo legge NVDA nel terminale. Si decide qui se annunciarlo, con quale uscita,
se alla sintesi, al braille o a tutti e due, e se un annuncio nuovo
interrompe quello in corso o si accoda: per la risposta a un tasto, cioe' il
testo che segue Invio, Esc o un tasto letto da key, e per il testo che
arriva da se', come la mossa dell'avversario, l'orologio o un avviso di
Lichess. Di partenza la risposta a un tasto interrompe e il resto si accoda
(R8).

I valori stanno nel database di Orologic, sotto la chiave annunci, e si
leggono sempre con normalizza: un valore mancante o sbagliato prende il
predefinito. Qui non c'e' wx: le prove lo usano senza finestra.
"""

from GBsintesi import AUTOMATICA, DESTINAZIONI, USCITE

from . import storage
from .config import _

CHIAVE = "annunci"
# Le voci, nell'ordine della finestra delle impostazioni.
VOCI = ("attivi", "uscita", "destinazione", "tasti_interrompono", "testo_interrompe")
PREDEFINITE = {
    "attivi": True,
    "uscita": AUTOMATICA,
    # La sintesi sola, come la T2 che Gabriele ha collaudato: il braille
    # segue gia' da se' la riga del cursore.
    "destinazione": "sintesi",
    "tasti_interrompono": True,
    "testo_interrompe": False,
}
USCITE_POSSIBILI = (AUTOMATICA, *USCITE)
SCELTE = {
    "attivi": (True, False),
    "uscita": USCITE_POSSIBILI,
    "destinazione": DESTINAZIONI,
    "tasti_interrompono": (True, False),
    "testo_interrompe": (False, True),
}


def normalizza(valori):
    """Le impostazioni complete: ogni voce mancante, o con un valore che non
    e' fra le sue scelte, prende il predefinito."""
    if not isinstance(valori, dict):
        valori = {}
    pulite = {}
    for voce in VOCI:
        valore = valori.get(voce, PREDEFINITE[voce])
        # True == 1 in Python: un numero non vale come si' o no.
        valida = any(valore == scelta and type(valore) is type(scelta) for scelta in SCELTE[voce])
        pulite[voce] = valore if valida else PREDEFINITE[voce]
    return pulite


def carica():
    return normalizza(storage.LoadDB().get(CHIAVE))


def salva(valori):
    storage.SetValue(CHIAVE, normalizza(valori))


def interrompe(valori, dal_tasto):
    """Se l'annuncio interrompe quello in corso: dal_tasto e' vero per la
    risposta a un tasto."""
    return valori["tasti_interrompono"] if dal_tasto else valori["testo_interrompe"]


# Le parole, per la finestra delle impostazioni.


def etichetta(voce):
    return {
        "attivi": _("Annunci"),
        "uscita": _("Uscita degli annunci"),
        "destinazione": _("Destinazione degli annunci"),
        "tasti_interrompono": _("La risposta a un tasto"),
        "testo_interrompe": _("Il testo che arriva da sé"),
    }[voce]


def nome_della_scelta(voce, scelta):
    """Come si legge una scelta della voce."""
    if voce == "attivi":
        return _("sì") if scelta else _("no")
    if voce == "uscita":
        return {
            AUTOMATICA: _("automatica, il primo screen reader attivo, se no la voce di Windows"),
            "nvda": "NVDA",
            "jaws": "JAWS",
            "sapi5": _("la voce di Windows"),
        }.get(scelta, scelta)
    if voce == "destinazione":
        return {
            "entrambi": _("sintesi e braille"),
            "sintesi": _("solo la sintesi"),
            "braille": _("solo il braille"),
        }.get(scelta, scelta)
    return _("interrompe l'annuncio in corso") if scelta else _("si accoda all'annuncio in corso")


def riga(voce, valori):
    """La riga della finestra delle impostazioni: Etichetta: valore."""
    # Traduttori: una riga delle impostazioni, come Annunci: sì.
    return _("{etichetta}: {valore}").format(etichetta=etichetta(voce), valore=nome_della_scelta(voce, valori[voce]))
