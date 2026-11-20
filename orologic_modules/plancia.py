# Orologic: il percorso dei menu e le voci della plancia.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La plancia, tappa T4 della GUI (Piano della GUI.txt, P1 e P2).

Nella finestra menu di GBUtils non scrive le sue voci nell'area: le
consegna, con sorgente_delle_scelte, alla plancia, l'albero accanto
all'area, che aspetta la scelta. La plancia mostra in cima il percorso dei
menu, come rami aperti, per esempio Menu principale e poi Orologi, e dentro
l'ultimo le voci del menu di adesso.

Qui c'e' solo la parte senza wx, che si prova da sola: il percorso, che si
costruisce dai punti del programma da cui menu e' chiamata, e le voci di un
menu come la plancia le mostra.

Il percorso. Ogni menu e' riconosciuto dal punto del programma che lo
chiama, il suo sito: le voci di un menu possono cambiare, per esempio la
lista degli orologi dopo un'eliminazione, ma il sito resta. Un menu con un
sito gia' nel percorso vi torna, e i livelli sotto si chiudono: e' cosi' che
si torna al menu principale. Un sito nuovo diventa un livello sotto
l'ultimo, col nome della voce scelta prima. Il menu principale riparte
sempre dalla radice.
"""

from .config import _


def radice():
    return _("Menu principale")


class Percorso:
    def __init__(self):
        # I livelli aperti, come coppie [sito, etichetta], dalla radice.
        self.livelli = []
        # L'etichetta della voce scelta nel menu dell'ultimo livello, finche'
        # non arriva il menu dopo: e' cio' che Orologic sta facendo.
        self.scelta = None

    def menu(self, sito, prompt="", alla_radice=False):
        """Arriva il menu del sito: il percorso si apre o si chiude fino a
        lui."""
        siti = [s for s, _etichetta in self.livelli]
        if alla_radice or not self.livelli:
            self.livelli = [[sito, radice()]]
        elif sito in siti:
            del self.livelli[siti.index(sito) + 1 :]
        else:
            etichetta = self.scelta or " ".join(prompt.split()).rstrip(":>").strip() or _("Scelta")
            self.livelli.append([sito, etichetta])
        self.scelta = None

    def scelto(self, etichetta):
        self.scelta = etichetta

    def etichette(self):
        """I rami del percorso, dalla radice, con la voce scelta in fondo."""
        rami = [etichetta for _sito, etichetta in self.livelli]
        if self.scelta:
            rami.append(self.scelta)
        return rami


def voci_del_menu(voci, prompt="", vuoto=None):
    """Le voci di un menu come le mostra la plancia: coppie (etichetta,
    valore), dove il valore e' cio' che menu deve restituire. L'etichetta e'
    la descrizione, o la chiave se manca. La voce col punto, che in Orologic
    esce o torna indietro, va in fondo: nell'elenco di menu sta in cima, e
    nella plancia un Invio di troppo sulla prima voce chiuderebbe il menu.
    Se Invio a vuoto ha un suo valore fuori dalle chiavi, ha anche lui la
    sua voce, col prompt che lo spiega."""
    ordinate = [voce for voce in voci if voce[0] != "."] + [voce for voce in voci if voce[0] == "."]
    righe = [(str(descrizione) if str(descrizione).strip() else str(chiave), chiave) for chiave, descrizione in ordinate]
    if vuoto is not None and vuoto not in [chiave for chiave, _descrizione in voci]:
        spiegazione = " ".join(prompt.split())
        if spiegazione:
            # Traduttori: la voce della plancia che vale come Invio a vuoto nel menu; {prompt} e' la domanda del menu.
            righe.append((_("Invio senza scegliere: {prompt}").format(prompt=spiegazione), vuoto))
        else:
            righe.append((_("Invio senza scegliere"), vuoto))
    return righe


def voci_del_si_e_no():
    """Le voci di una domanda di enter_escape: il tasto che ciascuna manda."""
    return [(_("Sì, come Invio"), "\r"), (_("No, come Esc"), "\x1b")]
