# Orologic: cio' che si fa all'avvio, prima di importare il resto del programma.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'avvio, tappe T5a e T5b della GUI (Piano della GUI.txt, S3 e S4).

config sceglie la lingua all'importazione, con polipo di GBUtils, e in
console la chiede al primo avvio. Nella finestra non c'e' una console da cui
chiederla: orologic.py chiama prepara prima di importare il resto, e qui, al
primo avvio, la lingua si sceglie in una finestra. Per questo il modulo non
importa config, ne' altro di Orologic che lo importi: solo percorsi e
GBUtils, e wx soltanto quando serve.

La finestra della lingua parla prima che una lingua ci sia: il titolo e'
quello che polipo scrive in console, Select your language:, e le lingue
hanno il nome che Windows da' loro nella loro lingua, italiano, English.
"""

import ctypes
import json
import os
import sys

import percorsi

SORGENTE = "it"
DOMINIO = "messages"
# Il nome della lingua nella lingua stessa, per GetLocaleInfoEx.
LOCALE_SNATIVELANGUAGENAME = 0x04
TITOLO = "Select your language:"


def cartella_dei_cataloghi():
    return percorsi.resource_path("locales")


def cartella_delle_impostazioni():
    return percorsi.percorso_salvataggio("settings")


def lingue():
    """I codici delle lingue che Orologic sa parlare: l'italiano e quelle che
    hanno il catalogo compilato, in ordine."""
    cartella = cartella_dei_cataloghi()
    try:
        nomi = os.listdir(cartella)
    except OSError:
        nomi = []
    return sorted({SORGENTE} | {n for n in nomi if os.path.isfile(os.path.join(cartella, n, "LC_MESSAGES", f"{DOMINIO}.mo"))})


def nome(codice):
    """Il nome della lingua nella lingua stessa, come lo dice Windows. Senza
    risposta, il codice."""
    testo = ctypes.create_unicode_buffer(85)
    try:
        if ctypes.WinDLL("kernel32").GetLocaleInfoEx(codice, LOCALE_SNATIVELANGUAGENAME, testo, len(testo)):
            return testo.value
    except (OSError, AttributeError):
        pass
    return codice


def lingua_salvata():
    """La lingua scelta e salvata da polipo, o None se non c'e' ancora."""
    try:
        with open(os.path.join(cartella_delle_impostazioni(), "selected_language.json"), encoding="utf-8") as file:
            dati = json.load(file)
    except (OSError, ValueError):
        return None
    codice = dati.get("language_code") if isinstance(dati, dict) else None
    return codice if codice in lingue() else None


def lingua_di_windows():
    """Il codice della lingua di Windows, come it o en, se Orologic la parla."""
    testo = ctypes.create_unicode_buffer(85)
    try:
        if ctypes.WinDLL("kernel32").GetUserDefaultLocaleName(testo, len(testo)):
            codice = testo.value.split("-")[0].lower()
            return codice if codice in lingue() else None
    except (OSError, AttributeError):
        pass
    return None


def salva(codice):
    """Fa salvare a polipo la lingua scelta, che config ritrovera'. Con None
    polipo sceglie da se', la lingua di Windows o l'italiano."""
    from GBUtils import polipo

    polipo(
        source_language=SORGENTE,
        localedir=cartella_dei_cataloghi(),
        config_path=cartella_delle_impostazioni(),
        interattivo=False,
        lingua=codice,
    )


def scegli_nella_finestra(codici, scelta):
    """La finestra della lingua: un elenco, Invio sceglie, Esc lascia la
    scelta a polipo. Restituisce il codice, o None."""
    import wx
    from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

    wx.GetApp() or wx.App()
    with wx.Dialog(None, title="Orologic", style=STILE_ADATTABILE) as dialogo:
        pannello = pannello_scorrevole(dialogo)
        sizer = wx.BoxSizer(wx.VERTICAL)
        etichetta = wx.StaticText(pannello, label=TITOLO)
        lista = wx.ListBox(pannello, choices=[nome(codice) for codice in codici], style=wx.LB_SINGLE)
        lista.SetName(TITOLO)
        # I pulsanti di serie, figli del pannello: le loro parole le da' wx,
        # perche' una lingua di Orologic ancora non c'e'.
        pulsanti = wx.StdDialogButtonSizer()
        conferma = wx.Button(pannello, wx.ID_OK)
        conferma.SetDefault()
        pulsanti.AddButton(conferma)
        pulsanti.AddButton(wx.Button(pannello, wx.ID_CANCEL))
        pulsanti.Realize()
        sizer.Add(etichetta, 0, wx.ALL, 5)
        sizer.Add(lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(pulsanti, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        adatta_finestra(dialogo, pannello, (420, 320))
        dialogo.Maximize()
        lista.SetSelection(scelta)
        lista.Bind(wx.EVT_LISTBOX_DCLICK, lambda _evento: dialogo.EndModal(wx.ID_OK))
        lista.SetFocus()
        if dialogo.ShowModal() != wx.ID_OK or lista.GetSelection() == wx.NOT_FOUND:
            return None
        return codici[lista.GetSelection()]


def scegli_la_lingua_se_serve(chiedi=scegli_nella_finestra):
    """Al primo avvio nella finestra, la lingua. Restituisce il codice scelto,
    o None se non c'era niente da scegliere."""
    codici = lingue()
    if len(codici) < 2 or lingua_salvata() is not None:
        return None
    proposta = lingua_di_windows() or SORGENTE
    codice = chiedi(codici, codici.index(proposta))
    salva(codice)
    return codice


def apri_la_console():
    """Il pacchetto non ha console (S3): con --cli se ne apre una sua, e
    tastiera e schermo vanno li', come nel terminale di sempre. Da sorgente,
    o se una console c'e' gia', non fa niente."""
    if not getattr(sys, "frozen", False):
        return False
    kernel32 = ctypes.WinDLL("kernel32")
    if kernel32.GetConsoleWindow() or not kernel32.AllocConsole():
        return False
    kernel32.SetConsoleTitleW("Orologic")
    sys.stdin = open("CONIN$", encoding="utf-8")  # noqa: SIM115 - resta aperto per tutta la vita del programma
    sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)  # noqa: SIM115
    return True


def uscite_mute():
    """Nel pacchetto senza console, prima che la finestra prenda lo schermo,
    stdout e stderr non ci sono: una scrittura diretta cadrebbe in errore.
    Vanno nel vuoto finche' la finestra non li prende."""
    for nome in ("stdout", "stderr"):
        if getattr(sys, nome) is None:
            setattr(sys, nome, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


def installazione_a_posto():
    """Il mutex che l'installatore cerca, e dal programma compilato la
    versione giusta in App installate (T5c)."""
    from . import installazione, version

    installazione.tieni_il_mutex()
    if getattr(sys, "frozen", False):
        installazione.aggiorna_la_versione(version.VERSION, os.path.dirname(sys.executable))


def prepara(argomenti):
    """Prima di importare il resto di Orologic: il mutex e App installate;
    col --cli la console del pacchetto; nella finestra la lingua del primo
    avvio."""
    installazione_a_posto()
    if "--cli" in argomenti:
        apri_la_console()
    else:
        uscite_mute()
        scegli_la_lingua_se_serve()
