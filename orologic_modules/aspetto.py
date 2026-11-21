# Orologic: colori e dimensioni dei caratteri delle finestre.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Colori e dimensioni dei caratteri, dalla richiesta di Gabriele del 21
novembre 2026, durante il collaudo della T6 (Piano della GUI.txt).

Due gruppi di impostazioni, la plancia e l'area centrale, ognuno col colore
dei caratteri, quello dello sfondo e la dimensione, salvati nel database
sotto la chiave aspetto. Un valore None e' quello di Windows: chi non tocca
niente ha le finestre di sempre. I colori sono percentuali di rosso, verde
e blu, da 0 a 100, col conto di Tornello e di MESS; la dimensione va da 8 a
72 punti, come in MESS.

Valgono per tutte le finestre di Orologic, con la scelta di Gabriele: gli
elenchi e gli alberi prendono caratteri e sfondo della plancia; campi di
testo, etichette e sfondo della finestra quelli dell'area; i pulsanti e le
linguette delle schede solo la dimensione, perche' Windows li disegna coi
suoi colori. Restano coi colori di Windows gli avvisi, che sono finestre di
Windows, e la mail del PUB, che e' di GBwx (decisione di Gabriele: niente
aggancio in GBwx).

Nelle aree di testo ricche, come l'area centrale, lo stile va anche nel
testo: il RichEdit di Windows non lo prende dai colori del controllo. Lo
stile predefinito dell'area lo mette wx in ogni testo che arriva dopo, con
ChangeValue, Replace e WriteText; quello che c'e' gia' si ricolora qui.

I colori personali, quelli di Salva colore, stanno a parte, sotto la
chiave colori_personali, e si salvano subito, anche se poi si annulla.
"""

import copy

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from . import storage
from .config import _

CHIAVE = "aspetto"
CHIAVE_DEI_PERSONALI = "colori_personali"
RUOLI = ("plancia", "area")
PARTI = ("testo", "sfondo", "dimensione")
DIMENSIONE_MINIMA = 8
DIMENSIONE_MASSIMA = 72
LUNGHEZZA_DEL_NOME = 40
# Gli elenchi e gli alberi hanno l'aspetto della plancia, il resto quello
# dell'area; i pulsanti e le schede prendono solo la dimensione.
LISTE = (wx.TreeCtrl, wx.ListBox, wx.ListCtrl)
SOLO_DIMENSIONE = (wx.Button, wx.ToggleButton, wx.Notebook)


def predefiniti():
    """I colori predefiniti della combo, come (nome, percentuali): neri e
    bianchi, i forti contrasti per chi vede poco, e qualche tinta. Una
    funzione, perche' i nomi si traducano nella lingua di adesso. Nero puro
    e Bianco puro, perche' Nero e Bianco nei cataloghi sono i giocatori, e
    in francese e in portoghese hanno il plurale."""
    return [
        (_("Nero puro"), (0, 0, 0)),
        (_("Bianco puro"), (100, 100, 100)),
        (_("Grigio chiaro"), (83, 83, 83)),
        (_("Grigio scuro"), (25, 25, 25)),
        (_("Giallo"), (100, 100, 0)),
        (_("Verde terminale"), (0, 100, 0)),
        (_("Ambra"), (100, 75, 0)),
        (_("Ciano"), (0, 100, 100)),
        (_("Azzurro"), (0, 75, 100)),
        (_("Blu notte"), (5, 5, 25)),
        (_("Blu marino"), (0, 0, 50)),
        (_("Rosso"), (100, 0, 0)),
        (_("Arancione"), (100, 50, 0)),
        (_("Magenta"), (100, 0, 100)),
        (_("Avorio"), (100, 100, 94)),
        (_("Crema"), (100, 99, 82)),
    ]


def vuote():
    """Le impostazioni di Windows: niente toccato."""
    return {ruolo: dict.fromkeys(PARTI) for ruolo in RUOLI}


def _colore_valido(valore):
    return (
        isinstance(valore, (list, tuple))
        and len(valore) == 3
        and all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 100 for c in valore)
    )


def _dimensione_valida(valore):
    return isinstance(valore, int) and not isinstance(valore, bool) and DIMENSIONE_MINIMA <= valore <= DIMENSIONE_MASSIMA


def valide(dati):
    """Le impostazioni lette, con i valori sbagliati o mancanti tornati a
    quelli di Windows: un database rovinato non ferma niente."""
    risultato = vuote()
    if not isinstance(dati, dict):
        return risultato
    for ruolo in RUOLI:
        gruppo = dati.get(ruolo)
        if not isinstance(gruppo, dict):
            continue
        for parte in ("testo", "sfondo"):
            if _colore_valido(gruppo.get(parte)):
                risultato[ruolo][parte] = list(gruppo[parte])
        if _dimensione_valida(gruppo.get("dimensione")):
            risultato[ruolo]["dimensione"] = gruppo["dimensione"]
    return risultato


def carica():
    return valide(storage.LoadDB().get(CHIAVE))


def salva(impostazioni):
    storage.SetValue(CHIAVE, valide(impostazioni))


def di_windows(impostazioni):
    """Vero se niente e' stato cambiato."""
    return all(valore is None for gruppo in impostazioni.values() for valore in gruppo.values())


def personali():
    """I colori salvati da chi usa Orologic, come (nome, percentuali), nell'ordine in cui sono nati."""
    elenco = storage.LoadDB().get(CHIAVE_DEI_PERSONALI)
    if not isinstance(elenco, list):
        return []
    return [
        (voce["nome"], tuple(voce["colore"]))
        for voce in elenco
        if isinstance(voce, dict) and isinstance(voce.get("nome"), str) and voce["nome"].strip() and _colore_valido(voce.get("colore"))
    ]


def salva_personale(nome, colore):
    """Salva un colore col suo nome; un nome che c'e' gia' prende il colore
    nuovo. Restituisce l'elenco aggiornato."""
    nome = " ".join(nome.split())[:LUNGHEZZA_DEL_NOME]
    elenco = [{"nome": n, "colore": list(c)} for n, c in personali() if n != nome]
    elenco.append({"nome": nome, "colore": list(colore)})
    storage.SetValue(CHIAVE_DEI_PERSONALI, elenco)
    return personali()


def da_percentuale(percentuale):
    """Una componente da percentuale, da 0 a 100, a byte, da 0 a 255, col conto di Tornello."""
    return max(0, min(255, int(percentuale / 100 * 255)))


def a_percentuale(byte):
    """Il contrario, per mettere nei cursori un colore di Windows."""
    return max(0, min(100, round(byte * 100 / 255)))


def colore(percentuali):
    return wx.Colour(*(da_percentuale(c) for c in percentuali))


def carattere_di_windows():
    return wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)


def carattere(impostazioni, ruolo):
    font = wx.Font(carattere_di_windows())
    if impostazioni[ruolo]["dimensione"]:
        font.SetPointSize(impostazioni[ruolo]["dimensione"])
    return font


def dimensione_in_uso(impostazioni, ruolo):
    return impostazioni[ruolo]["dimensione"] or carattere_di_windows().GetPointSize()


def colore_in_uso(impostazioni, ruolo, parte):
    """Il colore del ruolo, in percentuali: quello scelto, o quello di
    Windows per l'albero della plancia o per un campo di testo."""
    if impostazioni[ruolo][parte]:
        return tuple(impostazioni[ruolo][parte])
    attributi = (wx.TreeCtrl if ruolo == "plancia" else wx.TextCtrl).GetClassDefaultAttributes()
    scelto = attributi.colFg if parte == "testo" else attributi.colBg
    return a_percentuale(scelto.Red()), a_percentuale(scelto.Green()), a_percentuale(scelto.Blue())


def ruolo_di(controllo):
    return "plancia" if isinstance(controllo, LISTE) else "area"


def applica_al_controllo(controllo, impostazioni, ruolo=None):
    """Carattere e colori a un controllo solo; ruolo, se c'e', vale al posto
    di quello del tipo, per l'anteprima."""
    ruolo = ruolo or ruolo_di(controllo)
    font = carattere(impostazioni, ruolo)
    controllo.SetFont(font)
    if isinstance(controllo, SOLO_DIMENSIONE):
        return
    di_classe = controllo.GetClassDefaultAttributes()
    testo = colore(impostazioni[ruolo]["testo"]) if impostazioni[ruolo]["testo"] else di_classe.colFg
    sfondo = colore(impostazioni[ruolo]["sfondo"]) if impostazioni[ruolo]["sfondo"] else di_classe.colBg
    controllo.SetForegroundColour(testo)
    controllo.SetBackgroundColour(sfondo)
    if isinstance(controllo, wx.TextCtrl) and controllo.GetWindowStyleFlag() & (wx.TE_RICH | wx.TE_RICH2):
        stile = wx.TextAttr(testo, sfondo, font)
        controllo.SetDefaultStyle(stile)
        if controllo.GetLastPosition():
            controllo.SetStyle(0, controllo.GetLastPosition(), stile)
    controllo.Refresh()


def _discendenti(finestra):
    for figlio in finestra.GetChildren():
        if figlio.IsTopLevel():
            continue
        yield figlio
        yield from _discendenti(figlio)


def applica_alla_finestra(finestra, impostazioni=None, forza=False):
    """Carattere e colori a una finestra e a tutti i suoi controlli. Senza
    forza, una finestra con le impostazioni di Windows non si tocca."""
    impostazioni = carica() if impostazioni is None else impostazioni
    if not finestra or (not forza and di_windows(impostazioni)):
        return
    for controllo in (finestra, *_discendenti(finestra)):
        applica_al_controllo(controllo, impostazioni)


def rifai_l_impaginazione(finestra):
    """Dopo un cambio di dimensione: i sizer si rifanno, e i pannelli che
    scorrono ricalcolano le barre."""
    for controllo in (*_discendenti(finestra), finestra):
        if controllo.GetSizer():
            controllo.Layout()
        if isinstance(controllo, ScrolledPanel):
            controllo.FitInside()


def applica_a_tutte(impostazioni):
    """Le impostazioni in uso subito, in tutte le finestre aperte."""
    impostazioni = copy.deepcopy(impostazioni)
    for finestra in wx.GetTopLevelWindows():
        if finestra and not finestra.IsBeingDeleted():
            applica_alla_finestra(finestra, impostazioni, forza=True)
            rifai_l_impaginazione(finestra)
