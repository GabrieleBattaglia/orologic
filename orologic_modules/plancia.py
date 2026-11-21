# Orologic: l'albero dei menu e delle voci della plancia.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La plancia, tappa T4 della GUI (Piano della GUI.txt, P1-P4 e A1-A4).

Nella finestra menu di GBUtils non scrive le sue voci nell'area: le
consegna, con sorgente_delle_scelte, alla plancia, l'albero accanto
all'area, che aspetta la scelta. La plancia e' un albero vero: in cima le
voci del menu principale, e le voci che aprono un altro menu sono rami, che
si aprono con freccia destra e si chiudono con freccia sinistra, con
Orologic che entra nel menu del ramo o ne esce. Le voci hanno il testo
dell'elenco di menu, chiave e descrizione, nello stesso ordine.

Qui c'e' solo la parte senza wx, che si prova da sola.

I livelli. Ogni menu e' riconosciuto dal punto del programma che lo chiama,
il suo sito: le voci possono cambiare, per esempio la lista degli orologi
dopo un'eliminazione, ma il sito resta. Albero tiene la pila dei menu
aperti, dalla radice, ognuno con le sue voci e con la voce scelta che porta
al livello sotto. Un menu con un sito gia' nella pila vi torna, e i livelli
sotto si chiudono; uno nuovo diventa il livello sotto la voce scelta; il
menu principale di orologic.py riparte sempre dalla radice.

I rami. Quali voci aprono un altro menu lo dice RAMI, per sito, cioe' per
file e funzione che chiamano menu: e' l'unico punto di Orologic che sa
della plancia.

La strada. Per entrare in un ramo, uscirne o scegliere una voce di un altro
livello, la finestra chiede a strada la prossima risposta da dare al menu di
adesso: tornare su con la voce punto, o con Esc dove il punto non c'e',
scendere con la voce del ramo, o scegliere la voce finale.

I comandi delle partite. comandi_della_partita fa l'albero dei comandi di
una modalita' di gioco dalle righe dell'aiuto: i comandi con piu' forme e
quelli con un seguito dai valori finiti diventano rami, con le colonne, le
traverse, le case, i pezzi e i livelli del motore.
"""

import os

# Le voci che aprono un altro menu, per sito: (file, funzione) del punto che
# chiama menu, e le chiavi di quel menu che sono rami, o una funzione che lo
# dice dalla chiave e da tutte le chiavi del menu, per le funzioni che
# chiamano piu' menu. Censimento del 21 novembre 2026. Sono rami solo le
# voci che aprono il loro menu senza fare prima un'azione: restano foglie
# analizza e ricerca, che con poche partite negli appunti analizzano
# subito, e gioca della carriera, dove Esc nel menu del tempo, che servirebbe
# a richiudere il ramo, farebbe partire la partita. Una voce che apre un menu
# solo dopo una domanda e' una foglia: la domanda e' gia' un'azione.
RAMI = {
    ("orologic.py", "Main"): {"orologi", "gioca", "lichess", "memoboard", "impostazioni", "arbitra", "tempo"},
    ("orologic.py", "menu_orologi"): {"elimina"},
    ("gioca.py", "menu_gioca"): {"carriera"},
    ("gioca.py", "menu_carriera"): {"modello"},
    ("lichess_app.py", "scegli_ascoltando_le_sfide"): {
        "riprendi",
        "statistiche",
        "storia",
        "amici",
        "puzzle",
        "guarda",
        "gioca",
        "tornei",
        "sfide",
    },
    # Il menu degli amici, poi l'elenco degli amici: ognuno apre il suo menu.
    ("lichess_app.py", "menu_amici"): lambda chiave, chiavi: chiave == "vedi" if "cerca" in chiavi else chiave != ".",
    ("lichess_app.py", "menu_guarda"): lambda chiave, chiavi: "giocatore" in chiavi and chiave in ("amico", "tv"),
    ("lichess_app.py", "menu_gioca"): lambda chiave, chiavi: "bot" in chiavi and chiave in ("amico", "accetta", "riprendi"),
    ("lichess_profiler.py", "show_player_menu"): {"storia"},
    # Le varianti, poi le scelte su una variante, che sono foglie.
    ("lichess_stats.py", "run_stats"): lambda chiave, chiavi: chiave != "." and not {"1", "2"} <= set(chiavi),
    # Le cadenze, poi i tornei: ognuno apre il suo menu.
    ("lichess_tornei.py", "menu_tornei"): lambda chiave, chiavi: chiave != ".",
    ("memoboard_app.py", "main"): {"classifiche"},
    ("pgn_search.py", "_menu_filtri"): {"risultato"},
}

COLONNE = "abcdefgh"
TRAVERSE = "12345678"
# I seguiti con i numeri, in Easyfish: il livello del motore e quelli di Lichess.
NUMERI = {".s": range(21), ".f": range(1, 9)}


def etichetta(chiave, descrizione):
    """La riga di una voce come la stampa menu: chiave: descrizione, o la
    chiave sola."""
    descrizione = str(descrizione)
    return f"{chiave}: {descrizione}" if descrizione else str(chiave)


def e_un_ramo(sito, chiave, chiavi=()):
    if sito is None:
        return False
    rami = RAMI.get((os.path.basename(sito[0]), sito[1]), ())
    if callable(rami):
        return bool(rami(chiave, list(chiavi)))
    return chiave in rami


class Livello:
    def __init__(self, sito, voci, prompt="", vuoto=None):
        self.sito = sito
        self.voci = list(voci)
        self.prompt = prompt
        self.vuoto = vuoto
        # La chiave scelta in questo menu, finche' non arriva il menu dopo.
        self.scelta = None

    def chiavi(self):
        return [chiave for chiave, _descrizione in self.voci]

    def indietro(self):
        """La risposta che torna al menu sopra: la voce punto, o Esc."""
        return "." if "." in self.chiavi() else None


class Albero:
    def __init__(self):
        self.livelli = []

    def menu(self, sito, voci, prompt="", vuoto=None, alla_radice=False):
        """Arriva il menu del sito: la pila si apre o si chiude fino a lui."""
        nuovo = Livello(sito, voci, prompt, vuoto)
        siti = [livello.sito for livello in self.livelli]
        if alla_radice or not self.livelli:
            self.livelli = [nuovo]
        elif sito in siti:
            del self.livelli[siti.index(sito) :]
            self.livelli.append(nuovo)
        elif self.livelli[-1].scelta is None:
            # Un menu dopo l'altro senza una scelta che li leghi: prende il
            # posto di quello di prima.
            self.livelli[-1] = nuovo
        else:
            self.livelli.append(nuovo)

    def scelto(self, chiave):
        if self.livelli:
            self.livelli[-1].scelta = chiave

    def adesso(self):
        return self.livelli[-1] if self.livelli else None

    def percorso(self):
        """Le chiavi che portano dalla radice al menu di adesso."""
        return tuple(livello.scelta for livello in self.livelli[:-1])

    def strada(self, verso, finale=None):
        """La prossima risposta al menu di adesso per arrivare al menu del
        percorso verso, e li' scegliere finale se c'e'. Restituisce una
        coppia: ("indietro", la voce punto o None), ("avanti", la voce del
        ramo), ("finale", finale), o ("arrivato", None)."""
        attuale = self.percorso()
        comune = 0
        while comune < min(len(attuale), len(verso)) and attuale[comune] == verso[comune]:
            comune += 1
        if len(attuale) > comune:
            return "indietro", self.adesso().indietro()
        if len(verso) > comune:
            return "avanti", verso[comune]
        if finale is not None:
            return "finale", finale
        return "arrivato", None


def voci_del_menu(livello):
    """Le voci di un menu come le mostra la plancia: terne (etichetta,
    valore, ramo), nell'ordine di menu. Se Invio a vuoto ha un suo valore
    fuori dalle chiavi, ha anche lui la sua voce, INVIO."""
    chiavi = livello.chiavi()
    righe = [(etichetta(chiave, descrizione), chiave, e_un_ramo(livello.sito, chiave, chiavi)) for chiave, descrizione in livello.voci]
    if livello.vuoto is not None and livello.vuoto not in livello.chiavi():
        righe.append(("INVIO", livello.vuoto, False))
    return righe


def voci_della_domanda():
    """Le voci di una domanda di enter_escape: il tasto che ciascuna manda,
    con le parole che le domande di Orologic usano."""
    return [("INVIO", "\r"), ("ESC", "\x1b")]


# I comandi delle partite.


class Nodo:
    """Una voce dei comandi: testo e' cio' che si scrive nel prompt, invio
    se lo si manda subito; un ramo ha i figli e niente testo."""

    def __init__(self, etichetta, testo=None, invio=True, figli=()):
        self.etichetta = etichetta
        self.testo = testo
        self.invio = invio
        self.figli = list(figli)

    def __eq__(self, altro):
        return isinstance(altro, Nodo) and (self.etichetta, self.testo, self.invio, self.figli) == (
            altro.etichetta,
            altro.testo,
            altro.invio,
            altro.figli,
        )

    # Si confronta per contenuto, nelle prove: non va nei dizionari.
    __hash__ = None

    def __repr__(self):
        return f"Nodo({self.etichetta!r}, {self.testo!r}, {self.invio!r}, {self.figli!r})"


def _foglie(prefisso, valori):
    return [Nodo(f"{prefisso}{valore}", f"{prefisso}{valore}") for valore in valori]


def _seguito(forma, riga):
    """Il nodo di una forma con un seguito, come /[col], ,[P,N,B,R,Q,K] e
    .s#: un ramo coi valori, o una voce che scrive l'inizio e lascia il resto
    all'area se i valori sono liberi."""
    if forma.endswith("#"):
        prefisso = forma[:-1]
        if prefisso in NUMERI:
            return Nodo(riga, figli=_foglie(prefisso, NUMERI[prefisso]))
        return Nodo(riga, prefisso, invio=False)
    prefisso, _parentesi, resto = forma.partition("[")
    specie = resto.rstrip("]")
    if specie in ("col", "a-h"):
        return Nodo(riga, figli=_foglie(prefisso, COLONNE))
    if specie == "col|trv|casa":
        case = [Nodo(colonna, figli=_foglie(prefisso + colonna, TRAVERSE)) for colonna in COLONNE]
        return Nodo(
            riga,
            figli=[Nodo("col", figli=_foglie(prefisso, COLONNE)), Nodo("trv", figli=_foglie(prefisso, TRAVERSE)), Nodo("casa", figli=case)],
        )
    if "," in specie:
        return Nodo(riga, figli=_foglie(prefisso, specie.split(",")))
    return Nodo(riga, prefisso, invio=False)


def _forma(forma, riga):
    if "[" in forma or forma.endswith("#"):
        return _seguito(forma, riga)
    return Nodo(riga, forma)


def comandi_della_partita(comandi):
    """L'albero dei comandi di una modalita' di gioco. comandi e' una lista
    di coppie (chiave, riga dell'aiuto), o un dizionario chiave: descrizione,
    le cui righe diventano chiave: descrizione come le stampa menu. Le chiavi
    con piu' forme, .s oppure .b, oo / ooo, .1-0 .0-1 .1/2 .*, sono rami con
    una forma ciascuno."""
    if isinstance(comandi, dict):
        comandi = [(chiave, etichetta(chiave, descrizione)) for chiave, descrizione in comandi.items()]
    nodi = []
    for chiave, riga in comandi:
        chiave = str(chiave).strip()
        if " oppure " in chiave:
            forme = [forma.strip() for forma in chiave.split(" oppure ")]
        elif " / " in chiave:
            forme = [forma.strip() for forma in chiave.split(" / ")]
        else:
            forme = chiave.split() or [chiave]
        if len(forme) == 1:
            nodi.append(_forma(forme[0], riga))
        else:
            nodi.append(Nodo(riga, figli=[_forma(forma, forma) for forma in forme]))
    return nodi
