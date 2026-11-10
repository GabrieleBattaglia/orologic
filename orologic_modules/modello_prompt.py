# Orologic: il prompt di gioco componibile, issue 61.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il prompt delle partite, composto da un modello che l'utente scrive.

Un solo modello vale in tutte le modalita' di gioco: arbitraggio, Tempo, la
partita contro il motore, la partita su Lichess e quella osservata. Il
modello e' testo libero in cui il segno di percento seguito da una lettera
chiama un indicatore del catalogo, per esempio %b %n %m; %% scrive un
percento vero. Le lettere valgono maiuscole o minuscole.

Dalla 8.45.0 il modello sta nel file settings/prompt.txt: le righe che
cominciano con il dollaro sono spiegazioni, e il modello e' l'ultima riga
senza dollaro. La voce Prompt di gioco lo riscrive con le spiegazioni
aggiornate, lo apre nel Blocco note, aspetta che si chiuda e lo rilegge. La
cartella settings, e non resources, perche' sopravviva agli aggiornamenti.

Ogni modalita' raccoglie i suoi dati in un dizionario. componi restituisce
il corpo del prompt; prompt_per_input lo da' alle modalita' con la loro
cornice e, se dopo %m c'e' altro, diviso in due, perche' il cursore stia
dopo la mossa e il resto gli scorra a destra. Un indicatore che in una
modalita' non ha senso resta vuoto, e con lui sparisce uno spazio accanto.

Un numero dopo il percento, da 1 a 120, rende il prompt dinamico: %4 lo
riscrive ogni 4 secondi, come .6 4. Un modello senza numero e' statico, e
con il prompt statico i tempi non compaiono.

Gli indicatori con una forma estesa, a parole, la danno con una v dopo la
lettera; %bp e %np danno la percentuale di tempo consumato, come .1 e .2.
%c e' la scacchiera in caratteri, su piu' righe: si stampa quando la
posizione cambia, e ogni secondo si riscrive solo l'ultima riga.

Gli stati, pausa, senza orologio, premossa e RECLAMA, hanno il codice %s per
decidere dove compaiono; se il modello non lo contiene compaiono da soli,
dove comparivano prima che il prompt fosse componibile.
"""

import os
import re
import shutil
import subprocess
import time

import chess
from GBUtils import Acusticator, enter_escape, key

from . import config, storage, tempo
from .config import _

CHIAVE = "modello_prompt"
# Riproduce il prompt di prima della 8.34.0, in tutte le modalita'.
PREDEFINITO = "%b %n %m"
LUNGHEZZA_MASSIMA = 200
# I secondi dell'aggiornamento automatico, gli stessi di .6.
INTERVALLO_MASSIMO = 120
COMMENTO = "$"
NOME_FILE = "prompt.txt"
# Se il Blocco note torna prima di cosi', non ha aspettato la chiusura: su
# Windows 11 il notepad.exe di sistema puo' passare la mano all'app e uscire.
ATTESA_MINIMA_EDITOR = 2.0

_cache = {"modello": None}


def catalogo():
    """Le lettere del catalogo con la loro descrizione, nell'ordine in cui si
    leggono: prima i tempi, poi la partita, poi il contorno e gli stati."""
    return [
        ("b", _("tempo del Bianco")),
        ("n", _("tempo del Nero")),
        ("i", _("il tuo tempo, dove hai un colore: Easyfish e Lichess")),
        ("a", _("il tempo dell'avversario, dove hai un colore")),
        ("d", _("differenza fra gli orologi, positiva se il Bianco ha piu' tempo")),
        ("h", _("chi ha piu' tempo: < il Bianco, > il Nero, = pari")),
        ("m", _("numero di mossa con l'ultima mossa, come il prompt classico")),
        ("k", _("numero della mossa da giocare")),
        ("u", _("ultima mossa giocata")),
        ("v", _("bilancio del materiale, positivo se il Bianco ne ha di piu'")),
        ("t", _("a chi tocca, B o N")),
        ("r", _("mosse senza catture ne' mosse di pedone, verso le 50")),
        ("p", _("mosse che mancano al prossimo controllo del tempo")),
        ("f", _("la posizione in FEN")),
        ("c", _("la scacchiera in caratteri, su piu' righe, come quella di .s")),
        ("g", _("durata della partita")),
        ("o", _("nome dell'avversario")),
        ("s", _("stati: pausa, senza orologio, premossa, RECLAMA")),
    ]


def lettere():
    return {lettera for lettera, _descrizione in catalogo()}


# Gli indicatori con la forma estesa, che si chiede con una v dopo la lettera.
ESTESE = ("b", "n", "i", "a", "d", "g", "t", "u", "v")
# Gli orologi con la percentuale di tempo consumato, con una p dopo la lettera.
PERCENTUALI = ("b", "n")


def percorso_file():
    """Il file del modello, ricalcolato a ogni chiamata come tutti i percorsi."""
    return config.percorso_salvataggio(os.path.join("settings", NOME_FILE))


def leggi_file(percorso=None):
    """Il modello scritto nel file: l'ultima riga che non comincia con il
    dollaro e non e' vuota. None se il file non c'e' o non ha un modello."""
    percorso = percorso or percorso_file()
    try:
        with open(percorso, encoding="utf-8-sig") as f:
            righe = f.read().splitlines()
    except OSError:
        return None
    trovato = None
    for riga in righe:
        if riga.lstrip().startswith(COMMENTO) or not riga.strip():
            continue
        trovato = riga.strip()
    return trovato


def _dal_database():
    """Il modello salvato prima della 8.45.0, nel database. Il vecchio %c,
    numero della mossa, diventa %k: %c ora e' la scacchiera."""
    valore = storage.LoadDB().get(CHIAVE)
    if not isinstance(valore, str):
        return None
    return re.sub(r"(?<!%)%([cC])(?![vVpP])", "%k", valore)


def modello():
    """Il modello in uso. Si legge una volta sola: il prompt si riscrive ogni
    secondo, e rileggere il file a ogni giro sarebbe uno spreco."""
    if _cache["modello"] is None:
        _cache["modello"] = leggi_file() or _dal_database() or PREDEFINITO
    return _cache["modello"]


def testo_del_file(attuale):
    """Il contenuto di prompt.txt: le spiegazioni, ogni riga con il dollaro
    davanti, e in fondo il modello in uso."""
    d = COMMENTO + " "
    righe = [
        d + _("Prompt di gioco di Orologic. Le righe che cominciano con il dollaro sono spiegazioni, e Orologic le ignora."),
        d + _("Scrivi il modello nell'ultima riga, quella senza dollaro, poi salva e chiudi il Blocco note."),
        d + _("Ogni codice e' il percento seguito da una lettera, maiuscola o minuscola; il resto e' testo libero."),
    ]
    righe += [f"{d}%{lettera} {descrizione}" for lettera, descrizione in catalogo()]
    righe += [
        d + _("Con una v dopo la lettera, la forma estesa, a parole: %bv %nv %iv %av %dv %gv %tv %uv %vv."),
        d + _("%bp e %np: la percentuale di tempo consumato dal Bianco e dal Nero, come .1 e .2, dove ci sono le fasi."),
        d + _("Un numero dopo il percento, da 1 a 120, rende il prompt dinamico: %4 lo riscrive ogni 4 secondi. Senza numero il prompt e' statico, e i tempi non compaiono."),
        d + _("Se dopo %m c'e' altro, il cursore resta dopo la mossa, e il resto del prompt ti scorre a destra mentre scrivi."),
        d + _("%c va messo prima di %m: la scacchiera si stampa sopra la riga dove scrivi."),
        d + _("%% scrive un percento vero."),
        d + _("Il modello predefinito e': {m}").format(m=PREDEFINITO),
        attuale,
    ]
    return "\r\n".join(righe) + "\r\n"


def salva(nuovo):
    """Scrive il modello nel file, con le spiegazioni, e lo mette in uso. Il
    modello vecchio del database non serve piu'."""
    percorso = percorso_file()
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "w", encoding="utf-8", newline="") as f:
        f.write(testo_del_file(nuovo))

    def modifica(db):
        db.pop(CHIAVE, None)

    storage.UpdateDB(modifica)
    _cache["modello"] = nuovo


def analizza(testo):
    """Divide il modello in pezzi: ("testo", stringa), ("codice", codice) o
    ("intervallo", secondi). Il codice e' la lettera, con v o p dopo per le
    forme estese e le percentuali.

    Restituisce i pezzi e l'elenco dei codici sconosciuti, ciascuno con il
    suo percento davanti, nell'ordine in cui compaiono. Un percento in fondo,
    senza lettera, e' sconosciuto anche lui.
    """
    validi = lettere()
    pezzi = []
    sconosciuti = []
    letterale = []
    indice = 0
    while indice < len(testo):
        carattere = testo[indice]
        if carattere != "%":
            letterale.append(carattere)
            indice += 1
            continue
        seguente = testo[indice + 1] if indice + 1 < len(testo) else ""
        if seguente.isdigit():
            fine = indice + 1
            while fine < len(testo) and testo[fine].isdigit():
                fine += 1
            secondi = int(testo[indice + 1 : fine])
            if 1 <= secondi <= INTERVALLO_MASSIMO:
                if letterale:
                    pezzi.append(("testo", "".join(letterale)))
                    letterale = []
                pezzi.append(("intervallo", secondi))
            else:
                sconosciuti.append(testo[indice:fine])
                letterale.append(testo[indice:fine])
            indice = fine
            continue
        if seguente == "%":
            letterale.append("%")
        elif seguente.lower() in validi and seguente:
            if letterale:
                pezzi.append(("testo", "".join(letterale)))
                letterale = []
            codice = seguente.lower()
            dopo = (testo[indice + 2] if indice + 2 < len(testo) else "").lower()
            if codice in PERCENTUALI and dopo == "p":
                codice += "p"
                indice += 1
            elif codice in ESTESE and dopo == "v":
                codice += "v"
                indice += 1
            pezzi.append(("codice", codice))
        else:
            sconosciuti.append("%" + seguente)
            letterale.append("%" + seguente)
        indice += 2
    if letterale:
        pezzi.append(("testo", "".join(letterale)))
    return pezzi, sconosciuti


def _finali(valori):
    """I pezzi gia' calcolati, uno per uno. Un indicatore vuoto si porta via
    lo spazio che lo segue o, se dopo non ce n'e', quello che lo precede."""
    parti = [list(pezzo) for pezzo in valori]
    for posizione, (tipo, valore) in enumerate(parti):
        if tipo != "codice" or valore:
            continue
        dopo = parti[posizione + 1] if posizione + 1 < len(parti) else None
        prima = parti[posizione - 1] if posizione > 0 else None
        if dopo and dopo[0] == "testo" and dopo[1].startswith(" "):
            dopo[1] = dopo[1][1:]
        elif prima and prima[0] == "testo" and prima[1].endswith(" "):
            prima[1] = prima[1][:-1]
    return [valore for _tipo, valore in parti]


def _unisci(valori):
    return "".join(_finali(valori))


def _pulisci(testo):
    """Niente spazi ai bordi delle righe della scacchiera, ne' ai bordi."""
    return re.sub(r"[ ]*\n[ ]*", "\n", testo).strip()


def _differenza_estesa(bianco, nero):
    scarto = bianco - nero
    secondi = int(abs(scarto))
    if not secondi:
        return _("orologi pari")
    if scarto > 0:
        return _("vantaggio del Bianco: {t}").format(t=tempo.parlato(secondi))
    return _("vantaggio del Nero: {t}").format(t=tempo.parlato(secondi))


def _chi_ha_piu_tempo(bianco, nero):
    """%h: < se il Bianco ha piu' tempo, > se il Nero, = se pari, sui secondi
    interi come la differenza."""
    scarto = int(bianco) - int(nero)
    return "<" if scarto > 0 else ">" if scarto < 0 else "="


def _materiale_esteso(board):
    from .board_utils import CalculateMaterial

    bianco, nero = CalculateMaterial(board)
    scarto = bianco - nero
    if not scarto:
        return _("materiale pari")
    if scarto > 0:
        return _("vantaggio del Bianco: {n}").format(n=scarto)
    return _("vantaggio del Nero: {n}").format(n=-scarto)


def _mossa_descritta(board, mosse):
    """L'ultima mossa a parole, come la dice Orologic; dove la scacchiera non
    la conosce, come in Tempo, resta quella scritta."""
    if board is not None and board.move_stack:
        from .board_utils import DescribeMove

        prima = board.copy()
        mossa = prima.pop()
        try:
            return DescribeMove(mossa, prima)
        # Una descrizione mancata non deve togliere il prompt.
        except Exception:  # noqa: BLE001, S110
            pass
    return mosse[-1] if mosse else ""


def _differenza(bianco, nero):
    """Lo scarto fra gli orologi. Il segno si decide sui secondi interi, gli
    stessi che compatto scrive: sotto il secondo non c'e' vantaggio da dire."""
    scarto = bianco - nero
    secondi = int(abs(scarto))
    segno = "" if not secondi else "+" if scarto > 0 else "-"
    return segno + tempo.compatto(secondi)


def _materiale(board):
    from .board_utils import CalculateMaterial

    bianco, nero = CalculateMaterial(board)
    scarto = bianco - nero
    return f"{scarto:+d}" if scarto else "0"


def _scacchiera(board):
    """La scacchiera in caratteri, la stessa di .s, fra due a capo."""
    from .board_utils import CustomBoard

    return "\n" + str(CustomBoard(board.fen())) + "\n"


def _percentuale(residuo, iniziale):
    """La quota di tempo consumata nella fase, come la dice .1."""
    if not iniziale:
        return ""
    return f"{(iniziale - max(0.0, residuo)) / iniziale * 100:.0f}%"


def _stati(dati):
    stati = []
    if dati.get("pausa"):
        stati.append(_("[pausa]"))
    if dati.get("senza_orologio"):
        stati.append(_("senza orologio"))
    stati.extend(dati.get("altri_stati") or [])
    return " ".join(stati)


def _valore(codice, dati):
    """Il testo di un indicatore; stringa vuota dove non ha senso. Un codice
    con la v in fondo chiede la forma estesa, con la p la percentuale."""
    lettera = codice[0]
    esteso = codice.endswith("v") and len(codice) == 2
    durata = tempo.parlato if esteso else tempo.compatto
    board = dati.get("board")
    bianco, nero = dati.get("bianco"), dati.get("nero")
    mio = dati.get("mio")
    tempi = bianco is not None and nero is not None
    if codice == "bp":
        return _percentuale(bianco, dati.get("iniziale_bianco")) if tempi else ""
    if codice == "np":
        return _percentuale(nero, dati.get("iniziale_nero")) if tempi else ""
    if lettera == "b":
        return durata(max(0.0, bianco)) if tempi else ""
    if lettera == "n":
        return durata(max(0.0, nero)) if tempi else ""
    if lettera in ("i", "a"):
        if not tempi or mio is None:
            return ""
        io_bianco = mio == chess.WHITE
        if lettera == "a":
            io_bianco = not io_bianco
        return durata(max(0.0, bianco if io_bianco else nero))
    if lettera == "d":
        if not tempi:
            return ""
        return _differenza_estesa(bianco, nero) if esteso else _differenza(bianco, nero)
    if lettera == "h":
        return _chi_ha_piu_tempo(bianco, nero) if tempi else ""
    if lettera == "m":
        return dati.get("mossa", "")
    if lettera == "k":
        return str(board.fullmove_number) if board is not None else ""
    if lettera == "f":
        return board.fen() if board is not None else ""
    if lettera == "c":
        return _scacchiera(board) if board is not None else ""
    if lettera == "u":
        mosse = dati.get("mosse") or []
        if esteso:
            return _mossa_descritta(board, mosse)
        return mosse[-1] if mosse else ""
    if lettera == "v":
        if board is None:
            return ""
        return _materiale_esteso(board) if esteso else _materiale(board)
    if lettera == "t":
        # In Tempo la scacchiera non segue la partita: il tratto lo dice la
        # modalita', con la chiave tratto.
        tratto = board.turn if board is not None else dati.get("tratto")
        if tratto is None:
            return ""
        if esteso:
            return _("Bianco") if tratto == chess.WHITE else _("Nero")
        return _("B") if tratto == chess.WHITE else _("N")
    if lettera == "r":
        return str(board.halfmove_clock // 2) if board is not None else ""
    if lettera == "p":
        mancano = dati.get("mosse_al_controllo")
        return str(mancano) if mancano is not None else ""
    if lettera == "g":
        inizio = dati.get("inizio")
        if not inizio:
            return ""
        return durata(max(0.0, dati.get("adesso", time.time()) - inizio))
    if lettera == "o":
        return dati.get("avversario") or ""
    if lettera == "s":
        return _stati(dati)
    return ""


def _calcola(dati, testo):
    """I pezzi del modello con i loro valori, e dove sta %m."""
    pezzi, _sconosciuti = analizza(modello() if testo is None else testo)
    usa_stati = ("codice", "s") in pezzi
    calcolati = []
    indice_mossa = None
    for tipo, valore in pezzi:
        if tipo == "testo":
            calcolati.append((tipo, valore))
            continue
        if tipo == "intervallo":
            # Non scrive niente: dice solo ogni quanto riscrivere il prompt.
            calcolati.append(("codice", ""))
            continue
        uscita = _valore(valore, dati)
        if valore == "m":
            if indice_mossa is None:
                indice_mossa = len(calcolati)
            if not usa_stati and uscita:
                # Gli stati al loro posto di sempre: la pausa chiude la mossa
                # fra quadre, senza orologio le sta davanti.
                if dati.get("pausa"):
                    uscita = "[" + uscita + "]"
                elif dati.get("senza_orologio"):
                    uscita = _("senza orologio") + " " + uscita
        calcolati.append((tipo, uscita))
    return calcolati, usa_stati, indice_mossa


def _in_fondo(dati, usa_stati, usa_mossa):
    """Senza %s gli stati non si perdono: con %m premossa e RECLAMA vanno in
    fondo, come prima; senza nemmeno %m ci vanno tutti."""
    if usa_stati:
        return []
    if usa_mossa:
        return [stato for stato in dati.get("altri_stati") or [] if stato]
    stati = _stati(dati)
    return [stati] if stati else []


def componi(dati, testo=None):
    """Il corpo del prompt per i dati di una modalita'.

    I dati sono un dizionario: bianco e nero, i secondi dei due orologi o
    None se i tempi non vanno mostrati; iniziale_bianco e iniziale_nero, il
    tempo della fase, per le percentuali; mio, il colore dell'utente o None;
    board, la posizione; mosse, le mosse in SAN; mossa, il testo di %m come
    lo scrive la modalita'; pausa e senza_orologio, veri o falsi; altri_stati,
    l'elenco di premossa e RECLAMA; mosse_al_controllo; inizio, l'istante di
    inizio della partita; avversario; tratto, il colore al tratto, che serve
    solo dove board e' None.
    """
    calcolati, usa_stati, indice_mossa = _calcola(dati, testo)
    corpo = _pulisci(_unisci(calcolati))
    coda = _in_fondo(dati, usa_stati, indice_mossa is not None)
    return " ".join(parte for parte in [corpo, *coda] if parte)


def componi_diviso(dati, testo=None):
    """Il prompt diviso dove va il cursore: (prima, dopo). dopo e' vuoto se
    dopo %m non c'e' niente, o se %m manca, o se il resto va a capo, come
    una scacchiera messa dopo la mossa: li' il cursore resta in fondo."""
    calcolati, usa_stati, indice_mossa = _calcola(dati, testo)
    if indice_mossa is None:
        return componi(dati, testo), ""
    finali = _finali(calcolati)
    prima = _pulisci("".join(finali[: indice_mossa + 1]))
    resto = "".join(finali[indice_mossa + 1 :])
    coda = _in_fondo(dati, usa_stati, True)
    dopo = " ".join(parte for parte in [resto.strip(), *coda] if parte)
    if not dopo.strip() or "\n" in resto:
        return componi(dati, testo), ""
    return prima, dopo.strip()


def prompt_per_input(dati, inizio="", fine=" "):
    """Il prompt per i cicli d'attesa delle modalita', con la loro cornice:
    una stringa, o la coppia (prima, dopo) quando il cursore va dopo %m."""
    prima, dopo = componi_diviso(dati)
    if not dopo:
        return inizio + prima + fine
    return inizio + prima + " ", " " + dopo + fine.rstrip()


def intervallo(testo=None):
    """I secondi dell'aggiornamento automatico che il modello chiede, o 0 se
    il modello e' statico. Se ci sono piu' numeri vale il primo."""
    pezzi, _sconosciuti = analizza(modello() if testo is None else testo)
    for tipo, valore in pezzi:
        if tipo == "intervallo":
            return valore
    return 0


def mossa_classica(mosse):
    """Il %m dell'arbitraggio, di Tempo e di Lichess: 12. Cf3, 12... e5."""
    if not mosse:
        # Lo stesso msgid di prima della 8.34.0, gia' tradotto in tutte le
        # lingue, spazio compreso.
        return _("Inizio, mossa 0. ").strip()
    if len(mosse) % 2 == 1:
        return f"{(len(mosse) + 1) // 2}. {mosse[-1]}"
    return f"{len(mosse) // 2}... {mosse[-1]}"


def tempi_visibili(intervallo, bianco, nero, nascosti=False):
    """I due tempi da passare a componi, o None se il prompt e' statico."""
    if intervallo <= 0 or nascosti:
        return None, None
    return bianco, nero


def esempio():
    """Dati di esempio per l'anteprima: dopo 1. e4 e5 2. Cf3, il Nero al
    tratto, l'utente col Bianco contro Stockfish, in una fase di 5 minuti."""
    board = chess.Board()
    mosse = []
    for san in ("e4", "e5", "Nf3"):
        mosse.append(san)
        board.push_san(san)
    adesso = time.time()
    return {
        "bianco": 295.0,
        "nero": 287.0,
        "iniziale_bianco": 300.0,
        "iniziale_nero": 300.0,
        "mio": chess.WHITE,
        "board": board,
        "mosse": mosse,
        "mossa": mossa_classica(mosse),
        "pausa": False,
        "senza_orologio": False,
        "altri_stati": [],
        "mosse_al_controllo": 38,
        "inizio": adesso - 95,
        "adesso": adesso,
        "avversario": "Stockfish",
    }


def errori_del_modello(nuovo):
    """Le frasi che dicono che cosa non va nel modello, vuote se va bene."""
    errori = []
    if len(nuovo) > LUNGHEZZA_MASSIMA:
        errori.append(
            _("Il modello e' lungo {n} caratteri: il massimo e' {m}.").format(
                n=len(nuovo), m=LUNGHEZZA_MASSIMA
            )
        )
    _pezzi, sconosciuti = analizza(nuovo)
    lettere_ignote = [c for c in sconosciuti if c.strip() != "%"]
    numeri_fuori = [c for c in lettere_ignote if c[1:].isdigit()]
    codici = [c for c in lettere_ignote if not c[1:].isdigit()]
    if numeri_fuori:
        errori.append(
            _("Il numero dopo il percento va da 1 a 120 secondi: {c} non va.").format(
                c=", ".join(numeri_fuori)
            )
        )
    if codici:
        errori.append(_("Codici sconosciuti: {c}.").format(c=", ".join(codici)))
    if len(lettere_ignote) < len(sconosciuti):
        errori.append(
            _(
                "C'e' un percento senza lettera dopo: per scrivere un percento "
                "vero usa due percento di seguito."
            )
        )
    return errori


def _errore():
    Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)


def apri_nell_editor(percorso):
    """Apre il file nel Blocco note e aspetta che si chiuda. Se il Blocco
    note manca, o torna subito senza aspettare, come puo' fare quello di
    Windows 11, si apre l'editor predefinito e si aspetta un tasto."""
    blocco_note = shutil.which("notepad.exe") or os.path.join(
        os.environ.get("SYSTEMROOT", r"C:\Windows"), "notepad.exe"
    )
    if os.path.exists(blocco_note):
        print(_("Apro il modello nel Blocco note: salvalo e chiudilo per tornare."))
        inizio = time.monotonic()
        try:
            subprocess.run([blocco_note, percorso], check=False)
        except OSError:
            pass
        else:
            if time.monotonic() - inizio >= ATTESA_MINIMA_EDITOR:
                return
    else:
        try:
            os.startfile(percorso)
        except OSError as e:
            print(_("Non riesco ad aprire il file: {e}").format(e=e))
            return
    key(_("\rQuando hai salvato e chiuso il file, premi un tasto per tornare.\r"))
    print()


def imposta():
    """La voce Prompt di gioco delle impostazioni: il modello va nel file
    prompt.txt, con le spiegazioni, si apre nel Blocco note, e alla chiusura
    Orologic lo rilegge e lo applica."""
    attuale = modello()
    percorso = percorso_file()
    while True:
        os.makedirs(os.path.dirname(percorso), exist_ok=True)
        with open(percorso, "w", encoding="utf-8", newline="") as f:
            f.write(testo_del_file(attuale))
        apri_nell_editor(percorso)
        nuovo = leggi_file(percorso)
        if not nuovo:
            _errore()
            if enter_escape(
                _(
                    "Nel file non c'e' un modello. Riaprirlo per scriverlo? "
                    "(INVIO per riaprire, ESC per tenere quello di prima): "
                )
            ):
                continue
            print(_("Modello invariato."))
            salva(attuale)
            return
        errori = errori_del_modello(nuovo)
        if errori:
            _errore()
            for riga in errori:
                print(riga)
            if enter_escape(
                _(
                    "Riaprire il file per correggerlo? (INVIO per riaprire, ESC "
                    "per tenere il modello di prima): "
                )
            ):
                attuale = nuovo
                continue
            print(_("Modello invariato."))
            salva(modello())
            return
        break
    if nuovo == modello():
        salva(nuovo)
        print(_("Modello invariato."))
        return
    salva(nuovo)
    print(_("Anteprima: {p}").format(p=componi(esempio(), nuovo)))
    secondi = intervallo(nuovo)
    if secondi:
        print(_("Prompt dinamico, riscritto ogni {n} secondi.").format(n=secondi))
    else:
        print(_("Prompt statico."))
    if nuovo == PREDEFINITO:
        Acusticator.play("orologic_prompt_predefinito", volume=config.VOLUME)
        print(_("Torna il prompt predefinito."))
    else:
        Acusticator.play("orologic_prompt_salvato", volume=config.VOLUME)
        print(_("Modello del prompt salvato."))
