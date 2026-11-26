# Orologic: le tipologie del controllo del tempo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le tipologie del controllo del tempo, chieste da Gabriele il 21 novembre
2026 con la finestra degli orologi, dopo una ricerca sui manuali dei DGT
3000, 2010 e 2500, sulle regole FIDE e US Chess e sulle regole del go.

Ogni fase ha la sua tipologia (scelta di Gabriele nel modulo), nella chiave
tipo, e i suoi valori per ogni colore, con white_ e black_ davanti alla
chiave del valore. Una fase senza tipo e' della tipologia di sempre,
l'incremento dopo la mossa, col suo incremento in white_inc e black_inc.
Le fasi cambiano a mosse, giocatore per giocatore, come prima: il tempo
della fase nuova si aggiunge a quello che resta.

Le tipologie, con le regole dei DGT:
  dopo       l'incremento a mossa fatta; la prima mossa non ne ha. E'
             quello che Orologic ha sempre fatto, e resta il predefinito.
  prima      l'incremento prima della mossa, il Fischer dei DGT e della
             FIDE: c'e' gia' alla partenza, e a mossa fatta arriva quello
             per la mossa dopo, della fase in cui sara' giocata.
  bronstein  il ritardo Bronstein dei DGT: c'e' gia' alla partenza, e a
             mossa fatta torna il tempo usato fino al ritardo, senza
             superare quello d'inizio turno.
  ritardo    il ritardo semplice, US delay: a ogni turno il tempo resta
             fermo per i secondi del ritardo, poi scende; il ritardo non
             usato si perde. Ha lo stesso effetto del Bronstein; cambia
             quello che si vede.
  clessidra  il tempo che chi muove consuma passa all'avversario.
  byoyomi    il byo-yomi giapponese: finito il tempo, i periodi, tutti
             insieme; una mossa dentro un periodo lo fa ripartire intero,
             e superarlo lo consuma. Finiti i periodi, la bandierina.
  canadese   il byo-yomi canadese: finito il tempo, le mosse del periodo
             nel tempo del periodo, e la mossa in corso e' la prima; fatte
             tutte, il periodo riparte.
  contasu    finito il tempo, l'orologio non cade e conta in su il tempo
             in piu', come nello Scrabble.
Le ultime tre sono tempi supplementari: stanno solo nell'ultima fase, come
sui DGT. Il gong dei DGT 2010 e 2500 non c'e': alterna i giocatori da solo,
senza mosse, e Orologic le mosse le conta.

Il motore lavora sullo stato della partita: inizio_partita all'avvio,
inizio_turno quando un giocatore prende il tratto, scorri mentre il tempo
corre, a_mossa_fatta e a_turno_passato attorno al cambio di tratto, annulla
quando l'arbitro toglie una mossa, scaduto per la bandierina. Lo stato di
ogni colore sta in stato.controllo, e il registro di ogni mossa, per
annullarla, in stato.rettifiche: tutti e due viaggiano nel salvataggio
automatico. Annullare toglie quello che la mossa aveva aggiunto e lascia il
tempo speso, come Orologic ha sempre fatto con l'incremento.
"""

import copy
import math
from collections import namedtuple

from GBUtils import Acusticator

from . import config, tempo
from .config import _

PREDEFINITO = "dopo"
SUPPLEMENTARI = ("byoyomi", "canadese", "contasu")

# Un valore di una tipologia: chiave nella fase, con white_ o black_
# davanti; etichetta della combo; minimo, massimo e predefinito.
Parametro = namedtuple("Parametro", "chiave etichetta minimo massimo predefinito")
Tipo = namedtuple("Tipo", "codice nome descrizione parametri")


def _parametri():
    return {
        "inc": Parametro("inc", _("Incremento"), 0, 300, 0),
        "ritardo": Parametro("ritardo", _("Ritardo"), 0, 300, 5),
        "periodo": Parametro("periodo", _("Secondi del periodo"), 1, 300, 30),
        "periodi": Parametro("periodi", _("Periodi"), 1, 99, 5),
        "minuti_periodo": Parametro("minuti_periodo", _("Minuti del periodo"), 1, 60, 5),
        "mosse_periodo": Parametro("mosse_periodo", _("Mosse del periodo"), 1, 50, 25),
    }


def tipi():
    """Le tipologie, nell'ordine dell'elenco della finestra; la prima e'
    quella di sempre."""
    p = _parametri()
    return [
        Tipo("dopo", _("Incremento dopo la mossa"),
             _("a ogni mossa fatta si aggiungono i secondi dell'incremento; la prima mossa non ne ha. E' il modo di sempre di Orologic"),
             (p["inc"],)),
        Tipo("prima", _("Incremento prima della mossa, Fischer"),
             _("l'incremento c'e' gia' alla partenza, e a ogni mossa fatta arriva quello per la mossa dopo, come nei DGT e nelle regole FIDE"),
             (p["inc"],)),
        Tipo("bronstein", _("Ritardo Bronstein"),
             _("a ogni mossa fatta torna il tempo usato, fino ai secondi del ritardo, senza superare quello d'inizio turno; il ritardo c'e' gia' alla partenza"),
             (p["ritardo"],)),
        Tipo("ritardo", _("Ritardo semplice, US delay"),
             _("a ogni turno il tempo resta fermo per i secondi del ritardo, poi scende; il ritardo non usato si perde"),
             (p["ritardo"],)),
        Tipo("clessidra", _("Clessidra"),
             _("il tempo che usi passa all'avversario: la somma dei due orologi resta la stessa"),
             ()),
        Tipo("byoyomi", _("Byo-yomi giapponese"),
             _("finito il tempo, ci sono i periodi: una mossa dentro un periodo lo fa ripartire intero, superarlo lo consuma; finiti i periodi cade la bandierina. Solo nell'ultima fase"),
             (p["periodo"], p["periodi"])),
        Tipo("canadese", _("Byo-yomi canadese"),
             _("finito il tempo, le mosse del periodo vanno fatte nei minuti del periodo, contando quella in corso; fatte tutte, il periodo riparte. Solo nell'ultima fase"),
             (p["minuti_periodo"], p["mosse_periodo"])),
        Tipo("contasu", _("Conta in su"),
             _("finito il tempo, la bandierina non cade: l'orologio conta in su il tempo in piu', come nello Scrabble. Solo nell'ultima fase"),
             ()),
    ]


def tipo(codice):
    """La tipologia col codice; la predefinita se il codice non c'e'."""
    for candidato in tipi():
        if candidato.codice == codice:
            return candidato
    return tipi()[0]


def indice(codice):
    codici = [candidato.codice for candidato in tipi()]
    return codici.index(codice) if codice in codici else 0


def voce(candidato):
    """La voce dell'elenco delle tipologie: il nome e la spiegazione."""
    return _("{nome}: {descrizione}").format(nome=candidato.nome, descrizione=candidato.descrizione)


def tutti_i_parametri():
    """I valori di tutte le tipologie, una volta sola ciascuno: la finestra
    crea una combo per ognuno e mostra quelle della tipologia scelta."""
    return list(_parametri().values())


def completa(fase):
    """La fase con una tipologia valida e tutti i valori, per i due colori."""
    fase["tipo"] = tipo(fase.get("tipo")).codice
    for parametro in tutti_i_parametri():
        for colore in ("white", "black"):
            fase.setdefault(f"{colore}_{parametro.chiave}", parametro.predefinito)
    return fase


def valore(fase, chiave, colore):
    predefinito = _parametri()[chiave].predefinito if chiave in _parametri() else 0
    if isinstance(colore, bool):
        colore = "white" if colore else "black"
    return fase.get(f"{colore}_{chiave}", predefinito)


def codice_di(fase):
    return tipo((fase or {}).get("tipo")).codice


# Le parole, per l'elenco e la scheda.


def sommario_fase(fase, colore):
    """Il tempo della fase per il colore, a parole, con la sua tipologia: per
    quella di sempre il testo di prima, 5 minuti piu' 3 secondi di
    incremento."""
    t = tempo.parlato(fase.get(f"{colore}_time", 0))
    codice = codice_di(fase)

    def durata(chiave):
        return tempo.parlato(valore(fase, chiave, colore))

    if codice in ("dopo", "prima"):
        if not valore(fase, "inc", colore):
            return t
        if codice == "dopo":
            return _("{t} piu' {i} di incremento").format(t=t, i=durata("inc"))
        return _("{t} piu' {i} di incremento prima della mossa").format(t=t, i=durata("inc"))
    if codice == "bronstein":
        return _("{t} con ritardo Bronstein di {d}").format(t=t, d=durata("ritardo"))
    if codice == "ritardo":
        return _("{t} con ritardo semplice di {d}").format(t=t, d=durata("ritardo"))
    if codice == "clessidra":
        return _("{t} a clessidra").format(t=t)
    if codice == "byoyomi":
        return _("{t} piu' byo-yomi di {n} periodi da {p}").format(t=t, n=valore(fase, "periodi", colore), p=durata("periodo"))
    if codice == "canadese":
        return _("{t} piu' byo-yomi canadese di {m} mosse in {p}").format(
            t=t, m=valore(fase, "mosse_periodo", colore), p=tempo.parlato(60 * valore(fase, "minuti_periodo", colore)))
    return _("{t}, poi conta in su").format(t=t)


def spiegazione(fase):
    """Le righe della scheda che spiegano la tipologia della fase: per
    quella di sempre nessuna, la scheda era gia' chiara."""
    candidato = tipo((fase or {}).get("tipo"))
    if candidato.codice == PREDEFINITO:
        return []
    return [voce(candidato)]


def errori_della_fase(fase, colore, numero):
    """Che cosa non va nei tempi della fase per il colore, come frasi. Con
    i tempi supplementari il tempo di base puo' essere zero; coi ritardi e
    con l'incremento prima basta che base e ritardo, o incremento, facciano
    il minimo: e' il contamosse dei DGT, il tempo per mossa."""
    from .clock import TEMPO_MINIMO_FASE

    codice = codice_di(fase)
    base = fase.get(f"{colore}_time", 0)
    if codice in SUPPLEMENTARI:
        return []
    if codice == "prima":
        base += valore(fase, "inc", colore)
    elif codice in ("bronstein", "ritardo"):
        base += valore(fase, "ritardo", colore)
    if base < TEMPO_MINIMO_FASE:
        chi = _("bianco") if colore == "white" else _("nero")
        return [_("Fase {n}, {chi}: tempo troppo breve, il minimo e' {quanto}.").format(n=numero, chi=chi, quanto=tempo.parlato(TEMPO_MINIMO_FASE))]
    return []


def tempo_totale(fasi, colore):
    """Il tempo totale dell'orologio per il colore: le fasi sommate, con i
    tempi supplementari, periodi del byo-yomi e periodo canadese. Gli
    allarmi devono stare sotto, almeno per un colore (scelta di Gabriele)."""
    totale = 0
    for fase in fasi:
        totale += fase.get(f"{colore}_time", 0)
        codice = codice_di(fase)
        if codice == "byoyomi":
            totale += valore(fase, "periodo", colore) * valore(fase, "periodi", colore)
        elif codice == "canadese":
            totale += 60 * valore(fase, "minuti_periodo", colore)
    return totale


def errori_delle_fasi(fasi):
    """I tempi supplementari stanno solo nell'ultima fase."""
    errori = []
    for numero, fase in enumerate(fasi[:-1], 1):
        if codice_di(fase) in SUPPLEMENTARI:
            errori.append(_("Fase {n}: {nome} sta solo nell'ultima fase.").format(n=numero, nome=tipo(fase.get("tipo")).nome))
    return errori


# Il motore, in partita.


def _blocco():
    from .orologio import blocco

    return blocco()


def _fase(stato, bianco, indice_della_fase=None):
    fasi = (getattr(stato, "clock_config", None) or {}).get("phases") or []
    if not fasi:
        return {}
    if indice_della_fase is None:
        indice_della_fase = getattr(stato, "white_phase" if bianco else "black_phase", 0)
    return fasi[max(0, min(indice_della_fase, len(fasi) - 1))]


def _di(stato, bianco):
    """Lo stato del colore: inizio_turno, il residuo all'inizio del turno;
    ritardo, quello che resta del ritardo semplice; oltre, il tempo
    supplementare in corso, o None; periodi del byo-yomi e mosse del periodo
    canadese che restano; speso, i secondi corsi davvero nel turno, pause
    escluse, per il tempo speso della mossa."""
    controllo = getattr(stato, "controllo", None)
    if not isinstance(controllo, dict):
        controllo = {}
        stato.controllo = controllo
    colore = "white" if bianco else "black"
    if colore not in controllo:
        controllo[colore] = {"inizio_turno": 0.0, "ritardo": 0.0, "oltre": None, "periodi": 0, "mosse_periodo": 0, "speso": 0.0}
    return controllo[colore]


def _residuo(stato, bianco):
    return stato.white_remaining if bianco else stato.black_remaining


def _imposta(stato, bianco, secondi):
    if bianco:
        stato.white_remaining = secondi
    else:
        stato.black_remaining = secondi


def _nome(stato, bianco):
    predefinito = _("Bianco") if bianco else _("Nero")
    return getattr(stato, "white_player" if bianco else "black_player", "") or predefinito


def inizio_partita(stato):
    """All'avvio: l'incremento prima della mossa e il ritardo Bronstein ci
    sono gia', per i due colori, e il turno del Bianco comincia."""
    with _blocco():
        for bianco in (True, False):
            fase = _fase(stato, bianco)
            codice = codice_di(fase)
            if codice == "prima":
                _imposta(stato, bianco, _residuo(stato, bianco) + valore(fase, "inc", bianco))
            elif codice == "bronstein":
                _imposta(stato, bianco, _residuo(stato, bianco) + valore(fase, "ritardo", bianco))
        inizio_turno(stato, _tocca_al_bianco(stato))


def _tocca_al_bianco(stato):
    colore = getattr(stato, "active_color", "white")
    return colore == "white" if isinstance(colore, str) else bool(colore)


def inizio_turno(stato, bianco):
    """Il colore prende il tratto: il residuo d'inizio turno per il
    Bronstein, il ritardo semplice intero."""
    with _blocco():
        fase = _fase(stato, bianco)
        stato_del_colore = _di(stato, bianco)
        stato_del_colore["inizio_turno"] = _residuo(stato, bianco)
        stato_del_colore["ritardo"] = float(valore(fase, "ritardo", bianco)) if codice_di(fase) == "ritardo" else 0.0
        stato_del_colore["speso"] = 0.0


def scorri(stato, bianco, trascorso):
    """Il tempo che corre per il colore di turno, secondo la tipologia della
    sua fase. Si chiama col lucchetto dei tempi preso, dal filo
    dell'orologio. Restituisce gli avvisi da dare fuori dal lucchetto, come
    coppie (testo, suono)."""
    fase = _fase(stato, bianco)
    codice = codice_di(fase)
    stato_del_colore = _di(stato, bianco)
    avvisi = []
    residuo = _residuo(stato, bianco)
    # Il tempo vero del turno, qualunque cosa faccia l'orologio.
    stato_del_colore["speso"] = stato_del_colore.get("speso", 0.0) + trascorso
    if stato_del_colore["oltre"] == "contasu":
        _imposta(stato, bianco, residuo + trascorso)
        return avvisi
    if codice == "ritardo" and stato_del_colore["ritardo"] > 0:
        usato = min(stato_del_colore["ritardo"], trascorso)
        stato_del_colore["ritardo"] -= usato
        trascorso -= usato
        if trascorso <= 0:
            return avvisi
    residuo -= trascorso
    if codice == "clessidra":
        _imposta(stato, not bianco, _residuo(stato, not bianco) + trascorso)
    if residuo <= 0 and stato_del_colore["oltre"] is None:
        chi = _nome(stato, bianco)
        if codice == "byoyomi":
            periodo = valore(fase, "periodo", bianco)
            periodi = valore(fase, "periodi", bianco)
            stato_del_colore["oltre"] = "byoyomi"
            stato_del_colore["periodi"] = periodi
            residuo += periodo * periodi
            avvisi.append((_("{chi} entra nel byo-yomi: {n} periodi da {p}.").format(chi=chi, n=periodi, p=tempo.parlato(periodo)), "byoyomi"))
        elif codice == "canadese":
            secondi = 60 * valore(fase, "minuti_periodo", bianco)
            mosse = valore(fase, "mosse_periodo", bianco)
            stato_del_colore["oltre"] = "canadese"
            stato_del_colore["mosse_periodo"] = mosse
            residuo += secondi
            avvisi.append((_("{chi} entra nel byo-yomi canadese: {m} mosse in {p}.").format(chi=chi, m=mosse, p=tempo.parlato(secondi)), "canadese"))
        elif codice == "contasu":
            stato_del_colore["oltre"] = "contasu"
            residuo = -residuo
            avvisi.append((_("{chi}: tempo finito, l'orologio ora conta in su.").format(chi=chi), "contasu"))
    elif stato_del_colore["oltre"] == "byoyomi" and residuo > 0:
        periodo = valore(fase, "periodo", bianco)
        restano = math.ceil(residuo / periodo - 1e-9)
        if restano < stato_del_colore["periodi"]:
            stato_del_colore["periodi"] = restano
            avvisi.append((_("{chi}: periodo consumato, ne restano {n}.").format(chi=_nome(stato, bianco), n=restano), "periodo"))
    _imposta(stato, bianco, residuo)
    return avvisi


def tempo_speso(stato, bianco, inizio, adesso):
    """I secondi spesi per la mossa, interi, per il tempo della mossa nel
    post partita e il tag emt del PGN. Se l'orologio e' sceso del tempo vero
    del turno, la differenza dei residui arrotondati, come sempre: residuo
    di prima meno tempo speso piu' quello che la mossa da' torna il residuo
    scritto nel tag clk. Se non lo segue, come col ritardo semplice, che lo
    tiene fermo, o coi tempi supplementari, che lo ricaricano, il tempo vero
    del turno (Gabriele, collaudo della finestra degli orologi). Si chiama
    col lucchetto dei tempi preso, prima di a_mossa_fatta."""
    misurato = _di(stato, bianco).get("speso", 0.0)
    if abs((inizio - adesso) - misurato) < 0.5:
        return max(0, tempo.intero(inizio) - tempo.intero(adesso))
    return tempo.intero(misurato)


def tempo_in_piu(stato, bianco):
    """Col conta in su, i secondi oltre il tempo; None se il tempo non e' finito."""
    controllo = (getattr(stato, "controllo", None) or {}).get("white" if bianco else "black") or {}
    if controllo.get("oltre") != "contasu":
        return None
    return _residuo(stato, bianco)


def scaduto(stato, bianco):
    """Vero se la bandierina del colore e' caduta: il tempo e' finito, e
    non conta in su."""
    if _residuo(stato, bianco) > 0:
        return False
    controllo = getattr(stato, "controllo", None) or {}
    oltre = (controllo.get("white" if bianco else "black") or {}).get("oltre")
    if oltre == "contasu":
        return False
    # Chi ha il tempo di base finito ma non e' ancora entrato nei tempi
    # supplementari, come chi parte da zero, non e' scaduto: ci entra al
    # primo giro del suo orologio. Prima, col tempo di base a zero e il
    # byo-yomi, il Nero cadeva al primo giro del Bianco (R43).
    return not (oltre is None and codice_di(_fase(stato, bianco)) in SUPPLEMENTARI)


def a_mossa_fatta(stato, bianco):
    """Il colore ha fatto la mossa, prima che il tratto passi: quello che la
    tipologia della fase della mossa da' a mossa fatta. Restituisce il
    registro della mossa, da passare ad a_turno_passato."""
    with _blocco():
        fase_della_mossa = getattr(stato, "white_phase" if bianco else "black_phase", 0)
        fase = _fase(stato, bianco, fase_della_mossa)
        codice = codice_di(fase)
        stato_del_colore = _di(stato, bianco)
        registro = {"bianco": bianco, "fase": fase_della_mossa, "prima": copy.deepcopy(stato_del_colore), "aggiunto": 0.0}
        residuo = _residuo(stato, bianco)
        nuovo = residuo
        if codice == "dopo":
            nuovo = residuo + valore(fase, "inc", bianco)
        elif codice == "bronstein":
            nuovo = max(residuo, min(stato_del_colore["inizio_turno"], residuo + valore(fase, "ritardo", bianco)))
        elif stato_del_colore["oltre"] == "byoyomi":
            periodo = valore(fase, "periodo", bianco)
            nuovo = math.ceil(residuo / periodo - 1e-9) * periodo
        elif stato_del_colore["oltre"] == "canadese":
            stato_del_colore["mosse_periodo"] -= 1
            if stato_del_colore["mosse_periodo"] <= 0:
                nuovo = 60 * valore(fase, "minuti_periodo", bianco)
                stato_del_colore["mosse_periodo"] = valore(fase, "mosse_periodo", bianco)
                registro["avviso"] = (
                    _("{chi}: periodo canadese nuovo, {m} mosse in {p}.").format(
                        chi=_nome(stato, bianco), m=stato_del_colore["mosse_periodo"], p=tempo.parlato(nuovo)),
                    "canadese",
                )
        _imposta(stato, bianco, nuovo)
        registro["aggiunto"] = nuovo - residuo
        return registro


def a_turno_passato(stato, registro):
    """Dopo il cambio di tratto, e di fase: l'incremento prima della mossa,
    quello della fase in cui il colore giochera' la prossima; per una fase
    nuova la differenza del ritardo Bronstein, o il ritardo intero; poi il
    turno dell'avversario comincia. Il registro va in stato.rettifiche, per
    annullare la mossa. Restituisce il residuo del colore che ha mosso, per
    il tag clk: zero se conta in su."""
    with _blocco():
        bianco = registro["bianco"]
        vecchia = _fase(stato, bianco, registro["fase"])
        nuova = _fase(stato, bianco)
        aggiunta = 0
        if codice_di(nuova) == "prima":
            aggiunta = valore(nuova, "inc", bianco)
        elif codice_di(nuova) == "bronstein" and nuova is not vecchia:
            aggiunta = valore(nuova, "ritardo", bianco)
            if codice_di(vecchia) == "bronstein":
                aggiunta -= valore(vecchia, "ritardo", bianco)
        _imposta(stato, bianco, _residuo(stato, bianco) + aggiunta)
        registro["aggiunto"] += aggiunta
        rettifiche = getattr(stato, "rettifiche", None)
        if not isinstance(rettifiche, list):
            rettifiche = []
            stato.rettifiche = rettifiche
        rettifiche.append({chiave: valore_ for chiave, valore_ in registro.items() if chiave != "avviso"})
        inizio_turno(stato, _tocca_al_bianco(stato))
        # Col conta in su il tempo e' finito: nel tag clk resta zero, non il
        # tempo in piu' che l'orologio conta.
        residuo = 0.0 if _di(stato, bianco)["oltre"] == "contasu" else _residuo(stato, bianco)
    if registro.get("avviso"):
        testo, suono = registro["avviso"]
        print(testo)
        suona(suono)
    return residuo


def corretto(stato, bianco, secondi):
    """L'arbitro ha corretto di secondi il tempo del colore: l'inizio del
    suo turno si sposta dello stesso, cosi' il Bronstein e il tempo speso
    della mossa non contano la correzione come tempo giocato (R98)."""
    with _blocco():
        controllo = _di(stato, bianco)
        controllo["inizio_turno"] = controllo.get("inizio_turno", 0.0) + secondi


def annulla(stato, bianco, riparti=True):
    """L'arbitro toglie l'ultima mossa del colore: via quello che la mossa
    gli aveva dato, lo stato del colore com'era, e, con riparti, il suo turno
    riparte; chi deve prima riportare indietro la fase chiama inizio_turno
    dopo. Il tempo speso resta speso. Restituisce i secondi tolti."""
    with _blocco():
        rettifiche = getattr(stato, "rettifiche", None) or []
        tolti = 0.0
        if rettifiche and rettifiche[-1].get("bianco") == bianco:
            registro = rettifiche.pop()
            tolti = registro.get("aggiunto", 0.0)
            _imposta(stato, bianco, _residuo(stato, bianco) - tolti)
            controllo = _di(stato, bianco)
            controllo.update(registro.get("prima") or {})
        if riparti:
            inizio_turno(stato, bianco)
        return tolti


# I suoni nuovi della partita, dove il terminale non aveva l'evento: il
# byo-yomi e il canadese che cominciano, un periodo consumato, il conta in su.
SUONI = {
    "byoyomi": lambda: Acusticator(["c5", 0.08, 0, config.VOLUME, "e5", 0.08, 0, config.VOLUME, "g5", 0.12, 0, config.VOLUME], kind=2),
    "periodo": lambda: Acusticator(["g4", 0.1, 0, config.VOLUME, "g4", 0.1, 0, config.VOLUME], kind=2),
    "canadese": lambda: Acusticator(["c5", 0.08, 0, config.VOLUME, "g5", 0.08, 0, config.VOLUME, "c6", 0.12, 0, config.VOLUME], kind=2),
    "contasu": lambda: Acusticator(["c4", 0.1, 0, config.VOLUME, "c5", 0.1, 0, config.VOLUME, "c6", 0.2, 0, config.VOLUME], kind=1),
}


def suona(evento):
    """I suoni del motore; le prove li sostituiscono."""
    SUONI[evento]()
