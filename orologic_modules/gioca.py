# Orologic: il gioco contro il motore, dal menu principale.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La voce gioca del menu principale, issue 69.

Fino alla 8.41.5 il gioco contro il motore stava in Easyfish, con .g, .ea e
.gs. Qui ha un menu suo, con due strade. Libero: la partita con la forza che
scegli tu, anche da Fischer Random, che non entra nelle statistiche.
Carriera: dalla posizione iniziale, contro un motore che ha l'Elo deciso dal
modello, con il tuo Elo calcolato come fa la FIDE, statistiche, record e
sonificazione della serie.

La partita la gioca easyfish/game_mode, come prima; qui si preparano le
intestazioni del PGN e, a partita finita, si fa quello che fa l'arbitraggio:
tempi, PGN salvato e negli appunti, analisi automatica o in Easyfish.
"""

import datetime
import random

import chess
import chess.pgn
import pyperclip
from GBUtils import Acusticator, dgt, enter_escape, menu, sonify

from . import board_utils, chess960_utils, config, engine, storage, ui, version
from .config import _
from .easyfish import game_mode, punteggio_motore, statistiche_motore

CHIAVE_NOME = "nome_utente"
LUNGHEZZA_NOME = 60
# Le partite piu' corte non si analizzano, come in arbitraggio.
MOSSE_PER_I_TEMPI = 8
MOSSE_PER_L_ANALISI = 4
DELTA_MASSIMO = 1000


def nome_utente(chiedi=True):
    """Il nome dell'utente per il PGN. Se manca e chiedi e' vero, lo si
    chiede una volta e lo si salva; si cambia dalle impostazioni."""
    nome = (storage.LoadDB().get(CHIAVE_NOME) or "").strip()
    if not nome and chiedi:
        nome = dgt(
            _("Come ti chiami? Il nome va nelle partite salvate: "),
            kind="s",
            smax=LUNGHEZZA_NOME,
            default="",
        ).strip()
        if nome:
            salva_nome(nome)
    return nome or _("Giocatore")


def salva_nome(nome):
    def modifica(db):
        db[CHIAVE_NOME] = nome

    storage.UpdateDB(modifica)


def imposta_nome():
    """La voce Il mio nome delle impostazioni."""
    attuale = (storage.LoadDB().get(CHIAVE_NOME) or "").strip()
    nuovo = dgt(
        _("Il tuo nome, INVIO per lasciarlo com'e': "),
        kind="s",
        smax=LUNGHEZZA_NOME,
        default=attuale,
    ).strip()
    if nuovo and nuovo != attuale:
        salva_nome(nuovo)
        print(_("Nome salvato: {n}.").format(n=nuovo))
    else:
        print(_("Nome invariato."))


def _motore_pronto():
    """Il motore, avviato se serve; None se non c'e' verso."""
    if engine.ENGINE is None and not engine.InitEngine():
        if enter_escape(
            _(
                "Il motore scacchistico non e' configurato. Vuoi configurarlo "
                "ora? (INVIO per si', ESC per no): "
            )
        ):
            engine.MenuMotore()
        if engine.ENGINE is None and not engine.InitEngine():
            print(_("Senza motore non si gioca. Ritorno al menu."))
            return None
    return engine.ENGINE


def _classifica_apertura(partita):
    """L'apertura nel PGN, come a fine arbitraggio: ECO, Opening e
    Variation dell'ultima posizione della linea principale che il database
    riconosce. Nel Fischer Random non c'e' apertura da classificare."""
    if partita.headers.get("Variant", "") == "Chess960":
        return
    database = board_utils.LoadEcoDatabaseWithFEN("eco.db")
    if not database:
        return
    scacchiera = partita.board()
    trovata = None
    for mossa in partita.mainline_moves():
        scacchiera.push(mossa)
        voce = board_utils.DetectOpeningByFEN(scacchiera, database)
        if voce:
            trovata = voce
    if not trovata:
        return
    partita.headers["ECO"] = trovata["eco"]
    partita.headers["Opening"] = trovata["opening"]
    if trovata.get("variation"):
        partita.headers["Variation"] = trovata["variation"]


def _intestazioni(partita, nome, carriera):
    """Le intestazioni che non dipendono dal colore: il colore si sceglie
    dentro la partita, e White e Black si scrivono dopo. Intanto portano
    tutti e due il tuo nome, che la partita usa per gli annunci."""
    partita.headers["Event"] = (
        _("Orologic, carriera contro il motore") if carriera else _("Orologic, partita libera")
    )
    partita.headers["Site"] = "Orologic"
    partita.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
    # Una partita singola, libera o di carriera, non e' un turno di torneo.
    partita.headers["Round"] = "-"
    partita.headers["White"] = nome
    partita.headers["Black"] = nome
    partita.headers["Annotator"] = f"Orologic V{version.VERSION} by {version.PROGRAMMER}"


def _colori(partita, stato, nome, elo_utente=None, elo_motore=None):
    """Dopo la partita: tu da una parte, il motore con nome e versione
    dall'altra, e in carriera gli Elo con cui avete cominciato."""
    motore = engine.ENGINE_NAME
    umano_bianco = stato.human_color == chess.WHITE
    partita.headers["White"] = nome if umano_bianco else motore
    partita.headers["Black"] = motore if umano_bianco else nome
    if elo_utente is not None and elo_motore is not None:
        partita.headers["WhiteElo"] = str(elo_utente if umano_bianco else elo_motore)
        partita.headers["BlackElo"] = str(elo_motore if umano_bianco else elo_utente)


def _dopo_la_partita(partita, stato):
    """Quello che fa l'arbitraggio a fine partita: i tempi, il PGN salvato e
    negli appunti, l'analisi automatica o quella in Easyfish."""
    from . import game_flow

    mosse = len(stato.move_history)
    # Un tasto rimasto dalla partita faceva ripetere la domanda dei tempi.
    ui.svuota_tastiera()
    if stato.modalita in ("1", "2") and mosse >= MOSSE_PER_I_TEMPI:
        if enter_escape(
            _(
                "Vuoi vedere come hai usato il tempo a tua disposizione? (INVIO "
                "per si', ESC per no): "
            )
        ):
            board_utils.AnalizzaEStampaStatisticheTempo(stato, color_filter=None)
            if stato.modalita == "1" and enter_escape(
                _(
                    "Desideri salvare i tempi mossa nel PGN? (INVIO per si', ESC "
                    "per no): "
                )
            ):
                board_utils.AggiungiTempiPgn(
                    partita, stato.clocks_history, stato.move_times
                )
    _classifica_apertura(partita)
    pgn = board_utils.format_pgn_comments(str(partita))
    nome_file = config.sanitize_filename(
        "{w}-{b}-{r}-{t}.pgn".format(
            w=partita.headers.get("White"),
            b=partita.headers.get("Black"),
            r=partita.headers.get("Result", "*"),
            t=datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        )
    )
    game_flow.salva_pgn_partita(pgn, nome_file)
    try:
        pyperclip.copy(pgn)
        print(_("PGN copiato negli appunti."))
    except (pyperclip.PyperclipException, OSError) as e:
        print(_("Errore durante la copia del PGN negli appunti: {error}").format(error=e))
    if mosse < MOSSE_PER_L_ANALISI:
        return
    # Due domande distinte, come chiede la issue 69: prima l'analisi
    # automatica, poi Easyfish. Al collaudo della 8.43.2 l'OAA stava dietro
    # alla domanda sull'analisi, e chi rispondeva no non la vedeva.
    chess960_utils.verifica_motore_chess960(
        engine.ENGINE, partita.headers.get("Variant", "") == "Chess960"
    )
    if enter_escape(
        _("Vuoi l'analisi automatica OAA della partita? (INVIO per si', ESC per no): ")
    ):
        engine.cache_analysis.clear()
        engine.AnalisiAutomatica(board_utils.CopyPgnGame(partita))
    if enter_escape(
        _(
            "Vuoi aprire la partita in Easyfish, per analizzarla tu? (INVIO per "
            "si', ESC per no): "
        )
    ):
        from .easyfish import easyfish_app

        easyfish_app.run(partita)


def libero():
    """La partita libera: forza a scelta, anche da Fischer Random, e niente
    statistiche."""
    motore = _motore_pronto()
    if motore is None:
        return
    nome = nome_utente()
    if enter_escape(
        _(
            "Vuoi giocare alla variante standard (scacchi standard)? (INVIO per "
            "si', ESC per no): "
        )
    ):
        partita = chess.pgn.Game()
        chess960_utils.verifica_motore_chess960(motore, False)
    else:
        scacchiera, fen, _numero = chess960_utils.setup_fischer_random_board_interactive()
        if scacchiera is None:
            print(_("Configurazione Fischer Random annullata."))
            return
        partita = chess.pgn.Game()
        partita.setup(scacchiera)
        chess960_utils.setup_pgn_headers_chess960(partita, scacchiera, fen)
        chess960_utils.verifica_motore_chess960(motore, True)
    _intestazioni(partita, nome, carriera=False)
    _nodo, stato = game_mode.StartEngineGame(partita, motore, carriera=False)
    if stato is None:
        return
    _colori(partita, stato, nome)
    _dopo_la_partita(partita, stato)


def _gioca_in_carriera():
    motore = _motore_pronto()
    if motore is None:
        return
    nome = nome_utente()
    chess960_utils.verifica_motore_chess960(motore, False)
    dati = punteggio_motore.leggi()
    # L'Elo con cui cominci, letto prima: a fine partita il punteggio cambia.
    elo_prima = dati["punteggio"] if dati else None
    partita = chess.pgn.Game()
    _intestazioni(partita, nome, carriera=True)
    _nodo, stato = game_mode.StartEngineGame(partita, motore, carriera=True)
    if stato is None:
        return
    elo_utente = elo_prima if elo_prima is not None else stato.elo_di_partenza
    elo_motore = engine.forza["valore"] if stato.a_punteggio else None
    _colori(partita, stato, nome, elo_utente, elo_motore)
    _dopo_la_partita(partita, stato)


def _limiti_del_motore():
    opzione = (getattr(engine.ENGINE, "options", None) or {}).get("UCI_Elo")
    return (getattr(opzione, "min", None) or 1320, getattr(opzione, "max", None) or 3190)


def _scegli_il_modello(db):
    attuale = punteggio_motore.modello()
    voci = {
        "uguale": _("Uguale: il motore ha il tuo stesso Elo"),
        "delta": _("Delta assoluto: il tuo Elo piu' o meno un valore fisso"),
        "casuale": _("Delta casuale: il tuo Elo piu' un valore a caso fra due limiti"),
        "inseguimento": _("Inseguimento: il motore ti insegue, a passi che dipendono da distanza e risultato"),
        ".": _("Lascia il modello com'e'"),
    }
    print(_("Modello attuale: {m}.").format(m=punteggio_motore.descrivi_modello(attuale)))
    scelta = menu(
        voci,
        show=True,
        keyslist=True,
        p=_("\nModello del motore: "),
        numbered=db.get("menu_numerati", False),
    )
    if scelta in (".", None):
        return
    nuovo = {"tipo": scelta}
    if scelta == "delta":
        nuovo["delta"] = dgt(
            _("Di quanti punti il motore sta sopra o sotto il tuo Elo, da -1000 a 1000 (INVIO per {d}): ").format(
                d=attuale.get("delta", 100)
            ),
            kind="i",
            imin=-DELTA_MASSIMO,
            imax=DELTA_MASSIMO,
            default=attuale.get("delta", 100),
        )
    elif scelta == "casuale":
        nuovo["da"] = dgt(
            _("Limite in basso, da -1000 a 0 (INVIO per {d}): ").format(d=attuale.get("da", -50)),
            kind="i",
            imin=-DELTA_MASSIMO,
            imax=0,
            default=attuale.get("da", -50),
        )
        nuovo["a"] = dgt(
            _("Limite in alto, da 0 a 1000 (INVIO per {d}): ").format(d=attuale.get("a", 50)),
            kind="i",
            imin=0,
            imax=DELTA_MASSIMO,
            default=attuale.get("a", 50),
        )
    punteggio_motore.salva_modello(nuovo)
    Acusticator.play("orologic_modello_scelto", volume=config.VOLUME)
    print(_("Modello del motore: {m}.").format(m=punteggio_motore.descrivi_modello(nuovo)))
    dati = punteggio_motore.leggi()
    if dati is None:
        return
    # Il modello nuovo vale gia' per la prossima partita.
    minimo, massimo = _limiti_del_motore()
    elo_motore = punteggio_motore.stato_ea()["elo_motore"]
    elo, _voluto = punteggio_motore.prossimo_elo(
        nuovo, dati["punteggio"], elo_motore, None, minimo, massimo, random.randint
    )
    punteggio_motore.salva_ea(elo_motore=elo)
    print(_("Alla prossima partita il motore gioca a Elo {e}.").format(e=elo))


def _statistiche():
    Acusticator.play("orologic_statistiche_motore", volume=config.VOLUME)
    partite = statistiche_motore.di_carriera(statistiche_motore.leggi())
    for riga in statistiche_motore.righe_pagina(partite, punteggio_motore.leggi()):
        print(riga)


def _record():
    Acusticator.play("orologic_record", volume=config.VOLUME)
    partite = statistiche_motore.di_carriera(statistiche_motore.leggi())
    for riga in statistiche_motore.righe_record(partite, punteggio_motore.leggi()):
        print(riga)


def _sonifica():
    """La serie del tuo Elo in suono, come la storia Elo di Orolichess."""
    partite = statistiche_motore.di_carriera(statistiche_motore.leggi())
    serie = statistiche_motore.serie_dell_elo(partite)
    if len(serie) < 5:
        print(
            _("Per la sonificazione servono almeno 5 partite di carriera: ne hai {n}.").format(
                n=len(serie)
            )
        )
        return
    portamento = enter_escape(_("Abilitare il portamento? (Invio = Si', Esc = No): "))
    durata = dgt(
        _("Durata in secondi, da 1 a 30: "), kind="f", fmin=1.0, fmax=30.0, default=5.0
    )
    volume = config.VOLUME or 0.2
    print(
        _("La serie del tuo Elo, {n} valori da {a} a {b}.").format(
            n=len(serie), a=serie[0], b=serie[-1]
        )
    )
    sonify(serie, durata, ptm=portamento, vol=volume)


def _inizializza():
    if not punteggio_motore.leggi() and not statistiche_motore.di_carriera(
        statistiche_motore.leggi()
    ):
        print(_("La carriera e' gia' vuota."))
        return
    if not enter_escape(
        _(
            "Cancellare la carriera, cioe' il tuo Elo, le statistiche e i "
            "record? Non si torna indietro. (INVIO per cancellare, ESC per "
            "lasciarla): "
        )
    ):
        print(_("Carriera lasciata com'era."))
        return
    punteggio_motore.azzera_carriera()
    Acusticator.play("orologic_carriera_azzerata", volume=config.VOLUME)
    print(
        _(
            "Carriera cancellata. Alla prossima partita ti chiedo il tuo Elo e "
            "quello del motore."
        )
    )


def menu_carriera(db):
    while True:
        voci = {
            "gioca": _("Gioca una partita di carriera"),
            "statistiche": _("Statistiche"),
            "modello": _("Modello del motore: {m}").format(
                m=punteggio_motore.descrivi_modello(punteggio_motore.modello())
            ),
            "record": _("Record"),
            "sonifica": _("Sonifica la serie del tuo Elo"),
            "inizializza": _("Inizializza la carriera"),
            ".": _("Torna al menu gioca"),
        }
        scelta = menu(
            voci,
            show=True,
            keyslist=True,
            p=_("\nCarriera, scegli: "),
            numbered=db.get("menu_numerati", False),
        )
        if scelta in (".", None):
            return
        if scelta == "gioca":
            _gioca_in_carriera()
        elif scelta == "statistiche":
            _statistiche()
        elif scelta == "modello":
            _scegli_il_modello(db)
        elif scelta == "record":
            _record()
        elif scelta == "sonifica":
            _sonifica()
        elif scelta == "inizializza":
            _inizializza()


def menu_gioca():
    """La voce gioca del menu principale: carriera o libero."""
    while True:
        db = storage.LoadDB()
        scelta = menu(
            {
                "carriera": _("Carriera: il tuo Elo contro il motore"),
                "libero": _("Libero: la partita con la forza che scegli tu"),
                ".": _("Torna al menu principale"),
            },
            show=True,
            keyslist=True,
            p=_("\nGioca contro il motore: "),
            numbered=db.get("menu_numerati", False),
        )
        if scelta in (".", None):
            return
        if scelta == "carriera":
            Acusticator.play("orologic_carriera", volume=config.VOLUME)
            menu_carriera(db)
        elif scelta == "libero":
            Acusticator.play("orologic_libero", volume=config.VOLUME)
            libero()
