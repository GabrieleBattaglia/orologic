# Orologic: il prompt di gioco componibile, issue 61.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, UltraCode).

"""Il prompt delle partite, composto da un modello che l'utente scrive.

Un solo modello vale in tutte le modalita' di gioco: arbitraggio, Tempo,
Easyfish contro il motore, partita su Lichess e partita osservata. Il
modello e' testo libero in cui il segno di percento seguito da una lettera
chiama un indicatore del catalogo, per esempio %b %n %m; %% scrive un
percento vero. Le lettere valgono maiuscole o minuscole.

Ogni modalita' raccoglie i suoi dati in un dizionario e chiama componi, che
restituisce il corpo del prompt; la cornice resta della modalita', per
esempio il segno di maggiore della partita osservata. Un indicatore che in
una modalita' non ha senso, come il tuo tempo nell'arbitraggio, resta vuoto,
e con lui sparisce uno spazio accanto, cosi' il prompt non si riempie di
buchi. I tempi compaiono solo con l'aggiornamento automatico acceso da .6.

Gli indicatori che hanno una forma estesa, a parole, la danno con una v dopo
la lettera: %b scrive 01:14:43, %bv scrive 1 ora, 14 minuti e 43 secondi.
La vogliono gli utenti che ascoltano senza display braille.

Gli stati, pausa, senza orologio, premossa e RECLAMA, hanno il codice %s per
decidere dove compaiono; se il modello non lo contiene compaiono da soli,
dove comparivano prima che il prompt fosse componibile.
"""

import time

import chess
from GBUtils import Acusticator, dgt, enter_escape

from . import config, storage, tempo
from .config import _

CHIAVE = "modello_prompt"
# Riproduce il prompt di prima della 8.34.0, in tutte le modalita'.
PREDEFINITO = "%b %n %m"
LUNGHEZZA_MASSIMA = 200
# dgt tronca in silenzio a smax: si legge di piu' e si controlla a parte.
LETTURA_MASSIMA = 1000

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
        ("m", _("numero di mossa con l'ultima mossa, come il prompt classico")),
        ("c", _("numero della mossa da giocare")),
        ("u", _("ultima mossa giocata")),
        ("v", _("bilancio del materiale, positivo se il Bianco ne ha di piu'")),
        ("t", _("a chi tocca, B o N")),
        ("r", _("mosse senza catture ne' mosse di pedone, verso le 50")),
        ("p", _("mosse che mancano al prossimo controllo del tempo")),
        ("g", _("durata della partita")),
        ("o", _("nome dell'avversario")),
        ("s", _("stati: pausa, senza orologio, premossa, RECLAMA")),
    ]


def lettere():
    return {lettera for lettera, _descrizione in catalogo()}


# Gli indicatori con la forma estesa, che si chiede con una v dopo la lettera.
ESTESE = ("b", "n", "i", "a", "d", "g", "t", "u", "v")


def modello():
    """Il modello in uso. Si legge dal database una volta sola: il prompt si
    riscrive ogni secondo, e rileggere il file a ogni giro sarebbe uno
    spreco."""
    if _cache["modello"] is None:
        valore = storage.LoadDB().get(CHIAVE)
        _cache["modello"] = valore if isinstance(valore, str) else PREDEFINITO
    return _cache["modello"]


def salva(nuovo):
    """Salva il modello; il predefinito toglie la chiave dal database."""

    def modifica(db):
        if nuovo == PREDEFINITO:
            db.pop(CHIAVE, None)
        else:
            db[CHIAVE] = nuovo

    storage.UpdateDB(modifica)
    _cache["modello"] = nuovo


def analizza(testo):
    """Divide il modello in pezzi: ("testo", stringa) o ("codice", lettera).

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
        if seguente == "%":
            letterale.append("%")
        elif seguente.lower() in validi and seguente:
            if letterale:
                pezzi.append(("testo", "".join(letterale)))
                letterale = []
            codice = seguente.lower()
            dopo = testo[indice + 2] if indice + 2 < len(testo) else ""
            if codice in ESTESE and dopo.lower() == "v":
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


def _unisci(valori):
    """Unisce i pezzi gia' calcolati. Un indicatore vuoto si porta via lo
    spazio che lo segue o, se dopo non ce n'e', quello che lo precede."""
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
    return "".join(valore for _tipo, valore in parti)


def _differenza_estesa(bianco, nero):
    scarto = bianco - nero
    secondi = int(abs(scarto))
    if not secondi:
        return _("orologi pari")
    if scarto > 0:
        return _("vantaggio del Bianco: {t}").format(t=tempo.parlato(secondi))
    return _("vantaggio del Nero: {t}").format(t=tempo.parlato(secondi))


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
    di due lettere, con la v in fondo, chiede la forma estesa."""
    lettera, esteso = codice[0], len(codice) == 2
    durata = tempo.parlato if esteso else tempo.compatto
    board = dati.get("board")
    bianco, nero = dati.get("bianco"), dati.get("nero")
    mio = dati.get("mio")
    tempi = bianco is not None and nero is not None
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
    if lettera == "m":
        return dati.get("mossa", "")
    if lettera == "c":
        return str(board.fullmove_number) if board is not None else ""
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


def componi(dati, testo=None):
    """Il corpo del prompt per i dati di una modalita'.

    I dati sono un dizionario: bianco e nero, i secondi dei due orologi o
    None se i tempi non vanno mostrati; mio, il colore dell'utente o None;
    board, la posizione; mosse, le mosse in SAN; mossa, il testo di %m come
    lo scrive la modalita'; pausa e senza_orologio, veri o falsi; altri_stati,
    l'elenco di premossa e RECLAMA; mosse_al_controllo; inizio, l'istante di
    inizio della partita; avversario; tratto, il colore al tratto, che serve
    solo dove board e' None.
    """
    pezzi, _sconosciuti = analizza(modello() if testo is None else testo)
    usa_stati = ("codice", "s") in pezzi
    usa_mossa = ("codice", "m") in pezzi
    calcolati = []
    for tipo, valore in pezzi:
        if tipo == "testo":
            calcolati.append((tipo, valore))
            continue
        uscita = _valore(valore, dati)
        if valore == "m" and not usa_stati and uscita:
            # Gli stati al loro posto di sempre: la pausa chiude la mossa fra
            # quadre, senza orologio le sta davanti.
            if dati.get("pausa"):
                uscita = "[" + uscita + "]"
            elif dati.get("senza_orologio"):
                uscita = _("senza orologio") + " " + uscita
        calcolati.append((tipo, uscita))
    corpo = _unisci(calcolati).strip()
    if usa_stati:
        return corpo
    # Senza %s gli stati non si perdono: con %m premossa e RECLAMA vanno in
    # fondo, come prima; senza nemmeno %m ci vanno tutti.
    if usa_mossa:
        in_fondo = list(dati.get("altri_stati") or [])
    else:
        in_fondo = [_stati(dati)]
    return " ".join(parte for parte in [corpo, *in_fondo] if parte)


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
    """I due tempi da passare a componi, o None se .6 e' spento."""
    if intervallo <= 0 or nascosti:
        return None, None
    return bianco, nero


def esempio():
    """Dati di esempio per l'anteprima: dopo 1. e4 e5 2. Cf3, il Nero al
    tratto, l'utente col Bianco contro Stockfish."""
    board = chess.Board()
    mosse = []
    for san in ("e4", "e5", "Nf3"):
        mosse.append(san)
        board.push_san(san)
    adesso = time.time()
    return {
        "bianco": 295.0,
        "nero": 287.0,
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


def _errore():
    Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)


def imposta():
    """La voce Prompt di gioco delle impostazioni: catalogo, modello attuale,
    scrittura del nuovo, anteprima e conferma."""
    print(_("Prompt di gioco. Ogni codice e' il percento seguito da una lettera:"))
    for lettera, descrizione in catalogo():
        print(f"%{lettera} {descrizione}")
    print(
        _(
            "Con una v dopo la lettera, la forma estesa, a parole: %bv %nv %iv "
            "%av %dv %gv %tv %uv %vv."
        )
    )
    print(_("%% scrive un percento; il resto del modello e' testo libero."))
    attuale = modello()
    print(_("Modello attuale: {m}").format(m=attuale))
    print(_("Anteprima: {p}").format(p=componi(esempio(), attuale)))
    while True:
        nuovo = dgt(
            _(
                "Nuovo modello, INVIO per lasciarlo com'e', un asterisco per il "
                "predefinito: "
            ),
            kind="s",
            smax=LETTURA_MASSIMA,
            default="",
        ).strip()
        if not nuovo:
            print(_("Modello invariato."))
            return
        if nuovo == "*":
            nuovo = PREDEFINITO
        if len(nuovo) > LUNGHEZZA_MASSIMA:
            _errore()
            print(
                _("Il modello e' lungo {n} caratteri: il massimo e' {m}.").format(
                    n=len(nuovo), m=LUNGHEZZA_MASSIMA
                )
            )
            continue
        _pezzi, sconosciuti = analizza(nuovo)
        lettere_ignote = [c for c in sconosciuti if c.strip() != "%"]
        if lettere_ignote:
            _errore()
            print(
                _("Codici sconosciuti: {c}. Riscrivi il modello.").format(
                    c=", ".join(lettere_ignote)
                )
            )
            continue
        if sconosciuti:
            _errore()
            print(
                _(
                    "C'e' un percento senza lettera dopo: per scrivere un "
                    "percento vero usa due percento di seguito. Riscrivi il "
                    "modello."
                )
            )
            continue
        print(_("Anteprima: {p}").format(p=componi(esempio(), nuovo)))
        if enter_escape(_("Salvare questo modello? (INVIO per si', ESC per no): ")):
            salva(nuovo)
            if nuovo == PREDEFINITO:
                Acusticator.play("orologic_prompt_predefinito", volume=config.VOLUME)
                print(_("Torna il prompt predefinito."))
            else:
                Acusticator.play("orologic_prompt_salvato", volume=config.VOLUME)
                print(_("Modello del prompt salvato."))
        else:
            print(_("Modello invariato."))
        return
