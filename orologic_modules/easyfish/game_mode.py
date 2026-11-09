# Orologic, Easyfish: la partita contro il motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import random

import chess
import chess.engine
import chess.pgn
from GBUtils import Acusticator, dgt, enter_escape, menu

from .. import config, modello_prompt, orologio, tempo, ui
from .. import engine as orologic_engine
from ..board_utils import (
    CustomBoard,
    DescribeMove,
    NormalizeMove,
    mosse_fino_al_nodo,
)
from ..config import _
from . import analysis_utils, punteggio_motore, statistiche_motore
from .constants import MNGAME
from .utils import suona_annulla


class EasyfishGameState:
    def __init__(self):
        self.white_remaining = 0.0
        self.black_remaining = 0.0
        self.white_inc = 0.0
        self.black_inc = 0.0
        self.active_color = chess.WHITE
        self.game_over = False
        self.flag_fallen = False
        self.paused = False
        self.human_color = None
        self.engine_has_clock = True
        self.ignore_clock = False
        # I nomi servono agli annunci degli orologi, che sono quelli di
        # tutte le altre modalita' e li danno per esistenti.
        self.white_player = _("Bianco")
        self.black_player = _("Nero")
        self.refresh_interval = 0
        # Per il punteggio contro il motore: una partita conta solo con la
        # partita a punteggio accesa, se comincia dalla posizione iniziale e
        # senza ritiri di mosse.
        self.mosse_iniziali = 0
        self.dalla_posizione_iniziale = False
        self.ritiri = 0
        self.a_punteggio = False
        # I limiti dell'Elo del motore, letti dalle sue opzioni: il motore che
        # segue l'utente non deve uscirne.
        self.elo_minimo = 1320
        self.elo_massimo = 3190


# Gli otto livelli di Lichess, dalla tabella di fishnet, il programma che fa
# giocare Stockfish sul sito: abilita', profondita' e secondi per mossa.
# Lichess usa Fairy-Stockfish, che accetta abilita' negative, -9, -5 e -1 per
# i primi tre livelli; Stockfish ufficiale parte da zero, quindi qui quei tre
# sono un'approssimazione, con abilita' zero e la profondita' abbassata da 5
# a 1, 2 e 3.
LIVELLI_LICHESS = {
    1: (0, 1, 0.05),
    2: (0, 2, 0.1),
    3: (0, 3, 0.15),
    4: (3, 5, 0.2),
    5: (7, 5, 0.3),
    6: (11, 8, 0.4),
    7: (16, 13, 0.5),
    8: (20, 22, 1.0),
}
LIVELLI_APPROSSIMATI = (1, 2, 3)


def livello_da_elo(elo):
    """Il livello di abilita' che Stockfish ricava da UCI_Elo, con la sua
    stessa formula, in search.h: fra 0 e 19, da 1320 a 3190 punti."""
    e = (elo - 1320) / (3190 - 1320)
    return min(19.0, max(0.0, ((37.2473 * e - 40.8525) * e + 22.2943) * e - 0.311438))


def profondita_della_forza(forza):
    """La profondita' a cui Stockfish sceglie la mossa per quella forza, o
    None per la forza piena.

    Con un livello sotto il 20, o con un Elo, Stockfish sceglie la mossa,
    peggiorata di proposito, quando la ricerca arriva a 1 piu' il livello, e
    il tempo in piu' non la cambia: serve solo a consumare processore.
    Fermarlo li' da' la forza dichiarata nel tempo minimo, misurato il 9
    novembre 2026 sul Gigante con un solo thread: un centesimo di secondo
    fino a 2500 punti, meno di un secondo a 3190.
    """
    if forza["tipo"] == "elo":
        return 1 + int(livello_da_elo(forza["valore"]))
    if forza["tipo"] == "livello" and forza["valore"] < 20:
        return 1 + int(forza["valore"])
    return None


def _limiti_della_forza():
    """Profondita' e secondi per mossa che la forza scelta impone al motore.

    La profondita' di .p vale sempre; un livello di Lichess porta anche la
    sua, se .p non ne ha messa una, e il suo tempo per mossa. Con un livello
    o un Elo il motore si ferma alla profondita' in cui sceglie la mossa,
    se .p non lo ferma prima: il tempo scelto dall'utente resta un tetto.
    """
    forza = orologic_engine.forza
    profondita = forza["profondita"]
    tempo = None
    if forza["tipo"] == "lichess":
        _abilita, profondita_livello, tempo = LIVELLI_LICHESS[forza["valore"]]
        if profondita is None:
            profondita = profondita_livello
    scelta = profondita_della_forza(forza)
    if scelta is not None:
        profondita = scelta if profondita is None else min(profondita, scelta)
    return profondita, tempo


def descrivi_forza():
    """La forza con cui il motore gioca, in una riga."""
    forza = orologic_engine.forza
    if forza["tipo"] == "elo":
        riga = _("Forza del motore: Elo {n}.").format(n=forza["valore"])
    elif forza["tipo"] == "lichess":
        riga = _("Forza del motore: livello {n} di Lichess.").format(n=forza["valore"])
    else:
        riga = _("Forza del motore: livello {n} di 20.").format(n=forza["valore"])
    if forza["profondita"]:
        riga += " " + _("Profondita' massima: {d} semimosse.").format(
            d=forza["profondita"]
        )
    return riga


def comando_di_forza(cmd):
    """Vero per .s, .e, .f e .p seguiti da un numero: i comandi che cambiano
    la forza del motore in partita."""
    return cmd[:2] in (".s", ".e", ".f", ".p") and cmd[2:].strip().isdigit()


def _forza_bloccata(cmd, game_state):
    """Con la partita a punteggio la forza non si cambia: lo si dice e si
    restituisce vero."""
    if not (game_state.a_punteggio and comando_di_forza(cmd)):
        return False
    Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
    print(
        _(
            "La partita e' a punteggio: la forza del motore resta quella scelta. "
            "Per cambiarla, spegni .ea dal prompt di Easyfish."
        )
    )
    return True


def applica_forza(engine_instance, forza):
    """Porta il motore alla forza indicata, livello, Elo o livello di
    Lichess, con la sua profondita'. Restituisce vero se ci e' riuscito."""
    tipo, valore = forza.get("tipo"), forza.get("valore")
    try:
        if tipo == "elo":
            if "UCI_Elo" not in engine_instance.options:
                return False
            engine_instance.configure({"UCI_LimitStrength": True})
            engine_instance.configure({"UCI_Elo": int(valore)})
        else:
            if tipo == "lichess":
                abilita = LIVELLI_LICHESS[int(valore)][0]
            else:
                abilita = int(valore)
            if "UCI_LimitStrength" in engine_instance.options:
                engine_instance.configure({"UCI_LimitStrength": False})
            engine_instance.configure({"Skill Level": abilita})
    # Un motore che rifiuta un valore lascia la forza com'era.
    except Exception:  # noqa: BLE001
        return False
    orologic_engine.forza.update(
        tipo=tipo, valore=int(valore), profondita=forza.get("profondita")
    )
    return True


def _chiedi_elo_del_motore(engine_instance, proposto):
    """L'Elo del motore per la partita a punteggio, entro i limiti che il
    motore dichiara: INVIO tiene quello dell'ultima volta."""
    opzione = engine_instance.options["UCI_Elo"]
    minimo = getattr(opzione, "min", None) or 1320
    massimo = getattr(opzione, "max", None) or 3190
    proposto = max(minimo, min(massimo, proposto))
    return dgt(
        _("Elo del motore per questa partita, da {a} a {b} (INVIO per {p}): ").format(
            a=minimo, b=massimo, p=proposto
        ),
        kind="i",
        imin=minimo,
        imax=massimo,
        default=proposto,
    )


def _prepara_la_forza(engine_instance, game_state):
    """Prima della partita: con .ea acceso si sceglie l'Elo del motore, con
    .ea spento torna la forza dell'ultima volta. Poi la riga che dice che
    cosa succedera' a fine partita."""
    ea = punteggio_motore.stato_ea()
    game_state.a_punteggio = ea["attiva"]
    if ea["attiva"] and "UCI_Elo" not in engine_instance.options:
        print(
            _(
                "Il motore non accetta un Elo: la partita a punteggio non e' "
                "possibile, e questa partita non conta."
            )
        )
        game_state.a_punteggio = False
    if game_state.a_punteggio:
        opzione = engine_instance.options["UCI_Elo"]
        game_state.elo_minimo = getattr(opzione, "min", None) or 1320
        game_state.elo_massimo = getattr(opzione, "max", None) or 3190
        # L'Elo del motore si chiede solo alla prima partita a punteggio:
        # dopo il motore si adatta all'utente, partita dopo partita.
        if punteggio_motore.leggi() is None:
            elo = _chiedi_elo_del_motore(engine_instance, ea["elo_motore"])
        else:
            elo = max(
                game_state.elo_minimo, min(game_state.elo_massimo, ea["elo_motore"])
            )
        applica_forza(engine_instance, {"tipo": "elo", "valore": elo, "profondita": None})
        punteggio_motore.salva_ea(elo_motore=elo)
    else:
        ricordata = punteggio_motore.forza_ricordata()
        if ricordata:
            applica_forza(engine_instance, ricordata)
    print(descrivi_forza())
    if not game_state.a_punteggio:
        print(
            _(
                "Partita a punteggio spenta: questa partita non entra nel tuo "
                "Elo contro il motore. La accendi con .ea dal prompt di Easyfish."
            )
        )
        return
    if not game_state.dalla_posizione_iniziale:
        print(
            _(
                "Partita a punteggio accesa, ma la partita non parte dalla "
                "posizione iniziale: non entrera' nel tuo Elo."
            )
        )
        return
    dati = punteggio_motore.leggi()
    if dati:
        print(
            _(
                "Partita a punteggio: il tuo Elo, ora {p}, contro il motore a "
                "{e}. A fine partita il motore si adatta al tuo Elo, con un "
                "margine di caso; la forza resta ferma, e ritirare una mossa "
                "toglie la partita dal conteggio."
            ).format(p=dati["punteggio"], e=orologic_engine.forza["valore"])
        )
    else:
        print(
            _(
                "Partita a punteggio, la prima: a fine partita ti chiedo il "
                "punteggio da cui partire, poi si aggiorna contro il motore a "
                "{e}, che da li' in avanti si adatta al tuo Elo. La forza resta "
                "ferma, e ritirare una mossa toglie la partita dal conteggio."
            ).format(e=orologic_engine.forza["valore"])
        )


def _imposta_livello_lichess(cmd, board, game_state, engine_instance):
    """Comando .f: uno degli otto livelli di Lichess."""
    if not cmd[2:].isdigit() or int(cmd[2:]) not in LIVELLI_LICHESS:
        Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
        print(_("Il livello di Lichess va da 1 a 8, per esempio .f3."))
        return
    livello = int(cmd[2:])
    abilita, profondita, tempo = LIVELLI_LICHESS[livello]
    try:
        if "UCI_LimitStrength" in engine_instance.options:
            engine_instance.configure({"UCI_LimitStrength": False})
        engine_instance.configure({"Skill Level": abilita})
    # Rete di sicurezza della partita contro il motore: un errore
    # non deve far perdere la partita in corso.
    except Exception as e:  # noqa: BLE001
        print(_("Errore durante l'impostazione del livello: {e}").format(e=e))
        return
    orologic_engine.forza.update(tipo="lichess", valore=livello)
    Acusticator.play("orologic_forza_lichess", volume=config.VOLUME)
    print(
        _(
            "Forza del motore impostata al livello {n} di Lichess: abilita' {s}, "
            "profondita' {d}, {ms} millisecondi per mossa."
        ).format(n=livello, s=abilita, d=profondita, ms=round(tempo * 1000))
    )
    if livello in LIVELLI_APPROSSIMATI:
        print(
            _(
                "E' un'approssimazione: su Lichess questo livello usa un'abilita' "
                "sotto lo zero, che Stockfish ufficiale non ha."
            )
        )


def _imposta_profondita(cmd, board, game_state):
    """Comando .p: la profondita' massima della ricerca, 0 per toglierla."""
    if not cmd[2:].isdigit() or int(cmd[2:]) > 99:
        Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
        print(_("La profondita' va da 1 a 99, per esempio .p5, oppure .p0 per toglierla."))
        return
    profondita = int(cmd[2:]) or None
    orologic_engine.forza["profondita"] = profondita
    Acusticator.play("orologic_profondita", volume=config.VOLUME)
    if profondita:
        print(_("Profondita' massima del motore: {d} semimosse.").format(d=profondita))
    else:
        print(_("Profondita' del motore senza limite."))


def _aggiorna_punteggio(risultato, game_state):
    """Alla fine della partita, il punteggio dell'utente contro il motore.

    Conta solo con la partita a punteggio accesa, il comando .ea, dove il
    motore ha l'Elo scelto prima della partita e la forza non si cambia; e
    solo se la partita e' leale: dalla posizione iniziale, con un risultato
    e senza ritiri. Quando non conta lo dice, e dice perche'. Con .ea spento
    non conta mai, e la riga prima della partita lo ha gia' detto.
    Restituisce i dati del punteggio e la variazione se la partita e'
    entrata nel punteggio, altrimenti None.
    """
    forza = orologic_engine.forza
    if not game_state.a_punteggio or risultato not in ("1-0", "0-1", "1/2-1/2"):
        return None
    motivo = None
    if not game_state.dalla_posizione_iniziale:
        motivo = _("la partita non partiva dalla posizione iniziale.")
    elif game_state.ritiri:
        motivo = _("hai ritirato delle mosse.")
    if motivo:
        print(_("Partita non conteggiata nel tuo punteggio: {motivo}").format(motivo=motivo))
        return None
    if risultato == "1/2-1/2":
        punti = 0.5
    else:
        vince_il_bianco = risultato == "1-0"
        punti = 1 if vince_il_bianco == (game_state.human_color == chess.WHITE) else 0
    partenza = punteggio_motore.PUNTEGGIO_DI_PARTENZA
    if punteggio_motore.leggi() is None:
        partenza = dgt(
            _(
                "Prima partita per il tuo punteggio contro il motore: da quale "
                "punteggio parti? (INVIO per 1500): "
            ),
            kind="i",
            imin=100,
            imax=3500,
            default=punteggio_motore.PUNTEGGIO_DI_PARTENZA,
        )
    dati, variazione = punteggio_motore.registra(punti, forza["valore"], partenza)
    if variazione > 0:
        Acusticator.play("orologic_punteggio_sale", volume=config.VOLUME)
    elif variazione < 0:
        Acusticator.play("orologic_punteggio_scende", volume=config.VOLUME)
    for riga in punteggio_motore.righe_dopo_la_partita(dati, variazione):
        print(riga)
    return dati, variazione


# Il margine di caso del motore che si adatta, deciso con Gabriele il 9
# novembre 2026: fino a 50 punti in piu' o in meno del tuo Elo.
MARGINE_DI_CASO = 50


def _adatta_il_motore(game_state, elo_utente):
    """Il motore della partita a punteggio si adatta all'utente: per la
    partita seguente prende il suo Elo, piu' o meno un valore a caso fino a
    MARGINE_DI_CASO, entro i limiti del motore. Si dice solo l'Elo nuovo,
    non quanto c'e' di caso. Restituisce l'Elo nuovo."""
    voluto = elo_utente + random.randint(-MARGINE_DI_CASO, MARGINE_DI_CASO)
    nuovo = max(game_state.elo_minimo, min(game_state.elo_massimo, voluto))
    punteggio_motore.salva_ea(elo_motore=nuovo)
    if nuovo == game_state.elo_minimo and voluto < nuovo:
        print(
            _(
                "Il motore si adatta: alla prossima partita gioca a Elo {n}, il "
                "suo minimo."
            ).format(n=nuovo)
        )
    elif nuovo == game_state.elo_massimo and voluto > nuovo:
        print(
            _(
                "Il motore si adatta: alla prossima partita gioca a Elo {n}, il "
                "suo massimo."
            ).format(n=nuovo)
        )
    else:
        print(
            _("Il motore si adatta: alla prossima partita gioca a Elo {n}.").format(
                n=nuovo
            )
        )
    return nuovo


def _scegli_colore():
    """La scelta del colore, con la proposta delle statistiche, issue 66.

    Il colore proposto e' quello di INVIO, ESC da' l'altro: senza partite
    registrate la proposta e' il Bianco, come era INVIO prima.
    """
    proposto, motivo = statistiche_motore.colore_proposto(statistiche_motore.leggi())
    if proposto == chess.WHITE:
        print(_("Ti propongo il Bianco: {motivo}").format(motivo=motivo))
        domanda = _("Giochi col bianco (INVIO) o col nero (ESCAPE)?: ")
    else:
        print(_("Ti propongo il Nero: {motivo}").format(motivo=motivo))
        domanda = _("Giochi col nero (INVIO) o col bianco (ESCAPE)?: ")
    accetta = enter_escape(domanda)
    if accetta:
        return proposto
    return chess.BLACK if proposto == chess.WHITE else chess.WHITE


def ParseTimeInput(prompt_text):
    """Chiede tempo ed eventuale incremento, per esempio 20:00+15.

    La lettura della durata e' quella del modulo tempo: qui si aggiunge solo
    la parte dopo il piu', cioe' l'incremento in secondi.
    """
    while True:
        risposta = dgt(
            prompt=prompt_text + _(" (es. 01:15:00+10, 20:00+15 o 400+5): "), kind="s"
        ).strip()
        if not risposta:
            return None, None

        parte_tempo, _sep, parte_incremento = risposta.partition("+")
        incremento = 0
        if parte_incremento:
            try:
                incremento = int(parte_incremento.strip())
            except ValueError:
                print(_("L'incremento deve essere un numero di secondi."))
                continue

        secondi = tempo.da_testo(parte_tempo)
        if secondi is None:
            print(_("Tempo non riconosciuto: usa ore:minuti:secondi oppure i secondi."))
            continue
        return secondi, incremento


def _attendi_mossa(game_state, prompt, board, ultima_mossa):
    """Aspetta la mossa dell'umano tenendo d'occhio la bandierina.

    E' lo stesso ciclo dell'arbitraggio e di Tempo: restituisce nulla se
    il tempo e' scaduto mentre si scriveva, cosi' la partita si chiude da
    sola invece di aspettare che l'utente prema un tasto. Il prompt viene
    dal modello dell'utente, come in tutte le modalita': prompt e' il testo
    di %m, e i tempi compaiono quando punto sei ha acceso l'aggiornamento.
    """
    from ..game_flow import async_arbitration_input

    umano_bianco = game_state.human_color == chess.WHITE
    avversario = game_state.black_player if umano_bianco else game_state.white_player

    def get_prompt():
        bianco, nero = modello_prompt.tempi_visibili(
            getattr(game_state, "refresh_interval", 0),
            game_state.white_remaining,
            game_state.black_remaining,
            game_state.ignore_clock,
        )
        dati = {
            "bianco": bianco,
            "nero": nero,
            "mio": game_state.human_color,
            "board": board,
            "mosse": [ultima_mossa] if ultima_mossa else [],
            "mossa": prompt.strip(),
            "pausa": False,
            "senza_orologio": False,
            "altri_stati": [],
            "mosse_al_controllo": None,
            "inizio": getattr(game_state, "inizio_partita", None),
            "avversario": avversario,
        }
        return modello_prompt.componi(dati) + " "

    return async_arbitration_input(game_state, get_prompt)


def _nomi_dei_contendenti(game_state, game_node, engine_instance):
    """Da' un nome ai due lati, per gli annunci degli orologi.

    Il motore si presenta da solo con il proprio nome, l'umano prende
    quello del PGN. Senza questi due nomi il comando punto cinque non
    saprebbe di chi annunciare il tratto.
    """
    nome_motore = _("il motore")
    identita = getattr(engine_instance, "id", None)
    if isinstance(identita, dict):
        nome_motore = identita.get("name") or nome_motore
    umano_e_bianco = game_state.human_color == chess.WHITE
    intestazioni = game_node.root().headers
    nome_umano = intestazioni.get("White" if umano_e_bianco else "Black", "")
    if not nome_umano or nome_umano == "?":
        nome_umano = _("Bianco") if umano_e_bianco else _("Nero")
    if umano_e_bianco:
        game_state.white_player = nome_umano
        game_state.black_player = nome_motore
    else:
        game_state.white_player = nome_motore
        game_state.black_player = nome_umano


def _comandi_informativi(cmd, board, game_state, engine_instance):
    """Comandi che si limitano a riferire qualcosa.

    I comandi da punto uno a punto sei stanno in ui, uguali per tutte le
    modalita': qui restano materiale, scacchiera, elenco comandi e forza
    del motore. Restituisce vero se il comando e' stato riconosciuto.
    """
    if ui.comandi_orologio(cmd, game_state):
        return True
    if _forza_bloccata(cmd, game_state):
        return True
    if ui.comandi_lettura(cmd, game_state, board=board):
        return True
    elif cmd == ".a":
        lines = analysis_utils.get_lines_from_engine(
            board, engine_instance, orologic_engine.analysis_time, 1
        )
        for line in lines:
            print(line)
    elif cmd == ".?":
        menu(MNGAME, show_only=True)
    elif cmd.startswith(".s") and len(cmd) > 2 and cmd[2:].isdigit():
        try:
            new_skill = int(cmd[2:])
            if 0 <= new_skill <= 20:
                # Disattiva limitazione Elo per usare Skill Level
                try:
                    engine_instance.configure({"UCI_LimitStrength": False})
                # Rete di sicurezza della partita contro il motore: un errore
                # non deve far perdere la partita in corso.
                except Exception:  # noqa: BLE001, S110
                    pass
                engine_instance.configure({"Skill Level": new_skill})
                orologic_engine.forza.update(tipo="livello", valore=new_skill)
                Acusticator(["g5", 0.05, 0, config.VOLUME], kind=1)
                print(
                    _(
                        "Livello di forza del motore impostato a {n} (Skill Level)."
                    ).format(n=new_skill)
                )
            else:
                Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
                print(_("Il livello deve essere compreso tra 0 e 20."))
        # Rete di sicurezza della partita contro il motore: un errore
        # non deve far perdere la partita in corso.
        except Exception as e:  # noqa: BLE001
            print(_("Errore durante l'impostazione del livello: {e}").format(e=e))
    elif cmd.startswith(".f") and len(cmd) > 2:
        _imposta_livello_lichess(cmd, board, game_state, engine_instance)
    elif cmd.startswith(".p") and len(cmd) > 2:
        _imposta_profondita(cmd, board, game_state)
    else:
        return False
    return True


def _valuta_fine_partita(board, current_node, game_state):
    """Riconosce le posizioni che chiudono la partita.

    Matto, stallo e le patte riconosciute dalla libreria. Restituisce
    vero quando la partita e' finita, cosi' il ciclo si ferma.
    """
    if board.is_game_over(claim_draw=True):
        game_state.game_over = True
        if board.is_checkmate():
            res = "1-0" if board.turn == chess.BLACK else "0-1"
            if current_node.root():
                current_node.root().headers["Result"] = res
            print(_("Scacco matto!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_stalemate():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per stallo!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_insufficient_material():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per materiale insufficiente!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_seventyfive_moves() or board.can_claim_fifty_moves():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per la regola delle 50/75 mosse!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        elif board.is_fivefold_repetition() or board.can_claim_threefold_repetition():
            if current_node.root():
                current_node.root().headers["Result"] = "1/2-1/2"
            print(_("Patta per ripetizione della posizione!"))
            Acusticator(
                [
                    "c5",
                    0.1,
                    -0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.5,
                    config.VOLUME,
                    "c6",
                    0.2,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
        return True
    return False


def _partita_finita_dopo_la_mossa(board, current_node, game_state):
    """Controlla se la mossa appena giocata ha chiuso la partita.

    Matto, stallo, materiale insufficiente, settantacinque mosse e
    quintuplice ripetizione. Restituisce vero quando la partita e'
    finita: prima queste duecento righe stavano in due copie identiche,
    una dopo la mossa dell'umano e una dopo quella del motore.
    """
    if board.is_checkmate():
        game_state.game_over = True
        res = "1-0" if game_state.active_color == chess.BLACK else "0-1"
        if current_node.root():
            current_node.root().headers["Result"] = res
        print(_("Scacco matto!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_stalemate():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per stallo!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_insufficient_material():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per materiale insufficiente!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_seventyfive_moves():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per la regola delle 75 mosse!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.is_fivefold_repetition():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per ripetizione della posizione (5 volte)!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.can_claim_fifty_moves():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per la regola delle 50 mosse!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    elif board.can_claim_threefold_repetition():
        game_state.game_over = True
        if current_node.root():
            current_node.root().headers["Result"] = "1/2-1/2"
        print(_("Patta per triplice ripetizione della posizione!"))
        Acusticator(
            [
                "c5",
                0.1,
                -0.5,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0.5,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[2, 8, 90, 0],
        )
        return True
    return False


def StartEngineGame(game_node, engine_instance, sharing_window=None):
    """
    Avvia una partita contro il motore a partire dalla posizione corrente di game_node.
    Utilizza un thread separato per la gestione dell'orologio.
    """
    if sharing_window and sharing_window.is_active():
        sharing_window.update_board(game_node.board(), game_node)
    if not engine_instance:
        print(_("Motore non disponibile. Configuralo nelle impostazioni."))
        return game_node
    # Da una posizione gia' conclusa non si gioca: la partita finirebbe senza
    # una mossa, e le statistiche conterebbero un risultato mai giocato.
    if game_node.board().is_game_over(claim_draw=True):
        print(
            _(
                "La posizione e' gia' conclusa: torna a una mossa precedente "
                "per giocare contro il motore."
            )
        )
        return game_node

    print(_("Nuova Partita contro il Motore"))

    engine_mode = menu(
        {
            "1": _("Partita a tempo"),
            "2": _("Tempo per mossa motore"),
            "3": _("Senza tempo (Amichevole)"),
        },
        p=_("Modalita' di gioco: "),
        numbered=True,
    )

    user_time = 0
    user_inc = 0
    engine_time = 0
    engine_inc = 0
    engine_limit_type = "game"
    engine_has_clock = True
    ignore_clock = False

    if engine_mode == "1":
        user_time, user_inc = ParseTimeInput(_("Tuo tempo partita"))
        if user_time is None:
            return game_node

        same_time = not enter_escape(
            _("Usare stesso tempo per il motore? (INVIO per no, ESC per si'): ")
        )
        if same_time:
            engine_time = user_time
            engine_inc = user_inc
        else:
            engine_time, engine_inc = ParseTimeInput(_("Tempo partita motore"))
            if engine_time is None:
                return game_node

    elif engine_mode == "2":
        ignore_clock = True
        engine_limit_type = "move"
        engine_has_clock = False
        engine_time = dgt(_("Secondi per mossa motore: "), kind="f", default=2.0)

    elif engine_mode == "3":
        ignore_clock = True
        engine_limit_type = "move"
        engine_has_clock = False
        engine_time = dgt(_("Secondi riflessione motore: "), kind="f", default=2.0)

    # Setup GameState
    game_state = EasyfishGameState()
    game_state.ignore_clock = ignore_clock
    board = game_node.board()
    game_state.active_color = board.turn
    game_state.engine_has_clock = engine_has_clock
    game_state.mosse_iniziali = len(board.move_stack)
    game_state.dalla_posizione_iniziale = board.fen() == chess.STARTING_FEN
    # Il risultato si legge alla fine dall'intestazione: quello di una
    # partita caricata o di una .g precedente non deve passare per questo.
    radice = game_node.root()
    risultato_precedente = radice.headers.get("Result", "*")
    radice.headers["Result"] = "*"

    # Scelta del colore
    game_state.human_color = _scegli_colore()

    if game_state.human_color == chess.WHITE:
        game_state.white_remaining = float(user_time)
        game_state.white_inc = float(user_inc)
        game_state.black_remaining = float(engine_time) if engine_has_clock else 0
        game_state.black_inc = float(engine_inc) if engine_has_clock else 0
        print(_("Giochi col BIANCO."))
    else:
        game_state.black_remaining = float(user_time)
        game_state.black_inc = float(user_inc)
        game_state.white_remaining = float(engine_time) if engine_has_clock else 0
        game_state.white_inc = float(engine_inc) if engine_has_clock else 0
        print(_("Giochi col NERO."))

    _nomi_dei_contendenti(game_state, game_node, engine_instance)

    # La forza che il motore ha davvero adesso, e che cosa succedera' a fine
    # partita: la partita a punteggio, o la forza dell'ultima volta.
    _prepara_la_forza(engine_instance, game_state)
    # Forza attivazione WDL dal motore per l'analisi e gioco
    try:
        engine_instance.configure({"UCI_ShowWDL": True})
    # Rete di sicurezza della partita contro il motore: un errore
    # non deve far perdere la partita in corso.
    except Exception:  # noqa: BLE001, S110
        pass

    # Avvio dell'orologio, lo stesso usato dall'arbitraggio.
    orologio.avvia(game_state)

    current_node = game_node

    try:
        while not game_state.game_over:
            # --- CONTROLLI FINE PARTITA ---
            if _valuta_fine_partita(board, current_node, game_state):
                break

            if game_state.flag_fallen:
                print(_("Tempo scaduto! Partita terminata."))
                game_state.game_over = True
                # Perde chi ha esaurito il tempo, come lo ha visto l'orologio:
                # il tratto puo' essere passato nel frattempo.
                bianco_scaduto = getattr(
                    game_state,
                    "bianco_scaduto",
                    game_state.active_color == chess.WHITE,
                )
                res = "0-1" if bianco_scaduto else "1-0"
                if current_node.root():
                    current_node.root().headers["Result"] = res
                break

            move_num = board.fullmove_number
            last_move_san = current_node.san() if current_node.move else ""

            if not current_node.move:
                prompt = f"{move_num}. "
            elif board.turn == chess.WHITE:
                prompt = f"{move_num - 1}... {last_move_san} {move_num}. "
            else:
                prompt = f"{move_num}. {last_move_san} "

            # --- TURNO UMANO ---
            if board.turn == game_state.human_color:
                # Input. Si aspetta con il ciclo dell'arbitraggio e non con
                # dgt: dgt sta ferma sull'input finche' non arriva Invio,
                # quindi la bandierina cadeva senza che nessuno se ne
                # accorgesse e l'aggiornamento automatico di punto sei non
                # aveva modo di farsi sentire.
                move_input = _attendi_mossa(
                    game_state, prompt, board, last_move_san
                )

                if move_input is None:
                    continue
                if game_state.flag_fallen:
                    continue
                if not move_input:
                    continue

                from ..lichess_board import handle_exploration_command

                if handle_exploration_command(move_input, board):
                    continue

                # Comandi
                if move_input.startswith("."):
                    cmd = move_input.lower()
                    if cmd == ".":
                        # La conferma serve da quando l'attesa e' quella
                        # dell'arbitraggio: li' ESC vale punto, e senza
                        # domanda un tasto sbagliato farebbe perdere la
                        # partita.
                        if not enter_escape(
                            _("Vuoi davvero abbandonare? (INVIO per si', ESC per no): ")
                        ):
                            continue
                        print(_("Hai abbandonato."))
                        game_state.game_over = True
                        # Assegna risultato (Umano perde)
                        res = "0-1" if game_state.human_color == chess.WHITE else "1-0"
                        if current_node.root():
                            current_node.root().headers["Result"] = res
                        break
                    elif _comandi_informativi(cmd, board, game_state, engine_instance):
                        pass
                    elif cmd == ".l":
                        # L'elenco si ricostruisce dal PGN, poi il riepilogo e' quello
                        # di tutte le altre modalita'.
                        ui.comandi_lettura(
                            cmd,
                            game_state,
                            board=board,
                            mosse=mosse_fino_al_nodo(current_node),
                        )
                    elif _forza_bloccata(cmd, game_state):
                        pass
                    elif cmd.startswith(".e"):
                        try:
                            elo_part = cmd[2:].strip()
                            if not elo_part.isdigit():
                                print(_("Formato non valido. Usa .e1200 o .e 1200."))
                                continue

                            new_elo = int(elo_part)
                            if "UCI_Elo" not in engine_instance.options:
                                print(
                                    _(
                                        "Il motore non supporta la configurazione diretta dell'Elo."
                                    )
                                )
                                continue

                            opt = engine_instance.options["UCI_Elo"]
                            try:
                                # Attiva limitazione Elo
                                engine_instance.configure({"UCI_LimitStrength": True})
                                engine_instance.configure({"UCI_Elo": new_elo})
                                orologic_engine.forza.update(tipo="elo", valore=new_elo)
                                Acusticator(["b5", 0.05, 0, config.VOLUME], kind=1)
                                print(
                                    _(
                                        "Forza del motore impostata a Rating Elo: {n}."
                                    ).format(n=new_elo)
                                )
                            # Rete di sicurezza della partita contro il motore: un errore
                            # non deve far perdere la partita in corso.
                            except Exception:  # noqa: BLE001
                                msg = _("Valore Elo non accettato dal motore.")
                                if hasattr(opt, "min") and hasattr(opt, "max"):
                                    msg += _(
                                        " Range consentito per questo motore: {min}-{max}."
                                    ).format(min=opt.min, max=opt.max)
                                print(msg)
                        # Rete di sicurezza della partita contro il motore: un errore
                        # non deve far perdere la partita in corso.
                        except Exception as e:  # noqa: BLE001
                            print(
                                _("Errore durante l'impostazione dell'Elo: {e}").format(
                                    e=e
                                )
                            )
                    elif cmd == ".v":
                        try:
                            res = orologic_engine.CalculateBest(
                                board, bestmove=False, as_san=False
                            )
                            if res and len(res) > 0:
                                var_node = current_node.add_variation(res[0])
                                var_node.add_line(res[1:])
                                print(_("Variante suggerita aggiunta all'albero."))
                            else:
                                print(_("Nessuna linea trovata."))
                        # Rete di sicurezza della partita contro il motore: un errore
                        # non deve far perdere la partita in corso.
                        except Exception as e:  # noqa: BLE001
                            print(f"Err: {e}")
                    elif cmd == ".u":
                        steps = 0
                        temp_node = current_node
                        if temp_node.parent:
                            temp_node = temp_node.parent
                            steps += 1
                            if temp_node.parent:
                                temp_node = temp_node.parent
                                steps += 1

                        if steps > 0:
                            game_state.ritiri += 1
                            current_node = temp_node
                            board = current_node.board()
                            game_state.active_color = board.turn
                            if sharing_window and sharing_window.is_active():
                                sharing_window.update_board(board, current_node)
                            suona_annulla()
                            print(
                                _("Annullate {n} semimosse. Tocca a te.").format(
                                    n=steps
                                )
                            )
                            print(CustomBoard(board.fen()))
                        else:
                            print(_("Impossibile annullare."))
                    continue

                # Mossa
                try:
                    move_san_norm = NormalizeMove(move_input)
                    move = board.parse_san(move_san_norm)
                    if move in board.legal_moves:
                        new_node = current_node.add_main_variation(move)
                        current_node = new_node
                        board.push(move)
                        if sharing_window and sharing_window.is_active():
                            sharing_window.update_board(board, current_node)

                        if game_state.human_color == chess.WHITE:
                            orologio.aggiungi(game_state, True, game_state.white_inc)
                        else:
                            orologio.aggiungi(game_state, False, game_state.black_inc)

                        game_state.active_color = board.turn
                        Acusticator([1000.0, 0.05, 0, config.VOLUME], kind=1)
                        print(DescribeMove(move, current_node.parent.board()))

                        # Controlli fine partita
                        if _partita_finita_dopo_la_mossa(
                            board, current_node, game_state
                        ):
                            break
                    else:
                        Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
                        print(_("Mossa illegale."))
                except ValueError:
                    Acusticator([400.0, 0.2, 0, config.VOLUME], kind=1)
                    print(_("Input non valido."))

            # --- TURNO MOTORE ---
            else:
                # La profondita' di .p, o quella di un livello di Lichess,
                # vale in ogni modalita'; il tempo per mossa di un livello di
                # Lichess fa parte del livello e prende il posto di quello
                # scelto all'inizio, mentre a orologio il motore pensa al
                # massimo quel tanto, e l'orologio scorre comunque.
                profondita, tempo_livello = _limiti_della_forza()
                if engine_limit_type == "game":
                    limit = chess.engine.Limit(
                        white_clock=game_state.white_remaining,
                        black_clock=game_state.black_remaining,
                        white_inc=game_state.white_inc,
                        black_inc=game_state.black_inc,
                        depth=profondita,
                        time=tempo_livello,
                    )
                else:
                    limit = chess.engine.Limit(
                        time=tempo_livello or engine_time, depth=profondita
                    )

                try:
                    result = engine_instance.play(board, limit)
                    # La bandierina del motore e' caduta mentre pensava: la
                    # mossa arriva fuori tempo, e non si gioca.
                    if game_state.flag_fallen:
                        continue

                    if result.move:
                        if engine_has_clock:
                            if game_state.active_color == chess.WHITE:
                                orologio.aggiungi(
                                    game_state, True, game_state.white_inc
                                )
                            else:
                                orologio.aggiungi(
                                    game_state, False, game_state.black_inc
                                )

                        new_node = current_node.add_main_variation(result.move)
                        current_node = new_node
                        board.push(result.move)
                        if sharing_window and sharing_window.is_active():
                            sharing_window.update_board(board, current_node)

                        game_state.active_color = board.turn
                        Acusticator([1000.0, 0.05, 0, config.VOLUME], kind=1)
                        print(DescribeMove(result.move, current_node.parent.board()))

                        # Controlli fine partita
                        if _partita_finita_dopo_la_mossa(
                            board, current_node, game_state
                        ):
                            break
                    else:
                        print(_("Il motore abbandona o stallo."))
                        game_state.game_over = True
                        break

                # Rete di sicurezza della partita contro il motore: un errore
                # non deve far perdere la partita in corso.
                except Exception as e:  # noqa: BLE001
                    print(_("Errore motore: {e}").format(e=e))
                    break

    except KeyboardInterrupt:
        print(_("\nPartita interrotta."))
    finally:
        game_state.game_over = True

    print(_("Partita terminata."))

    # Risultato finale (se non già settato)
    # Nota: board.result() di python-chess ritorna "*" se non terminata, o il risultato se terminata per regole scacchi
    # Ma noi vogliamo salvare nell'header
    res = current_node.root().headers.get("Result", "*")

    if res == "*" or res == "?":  # Se non ancora deciso dall'abbandono/tempo
        if board.is_checkmate():
            res = "0-1" if board.turn == chess.WHITE else "1-0"
        elif (
            board.is_stalemate()
            or board.is_insufficient_material()
            or board.is_seventyfive_moves()
            or board.is_fivefold_repetition()
        ):
            res = "1/2-1/2"

        if current_node.root():
            current_node.root().headers["Result"] = res
    if res in ("*", "?") and len(board.move_stack) == game_state.mosse_iniziali:
        # Interrotta prima di qualunque mossa: l'albero torna com'era.
        current_node.root().headers["Result"] = risultato_precedente

    print(_("Risultato: {r}").format(r=res))
    forza_finale = dict(orologic_engine.forza)
    if not game_state.a_punteggio:
        # La prossima partita, anche dopo aver chiuso Easyfish, riparte da qui.
        punteggio_motore.ricorda_forza(forza_finale)
    esito_elo = _aggiorna_punteggio(res, game_state)
    elo_utente = variazione = elo_motore = None
    if esito_elo:
        dati_elo, variazione = esito_elo
        elo_utente = dati_elo["punteggio"]
        elo_motore = _adatta_il_motore(game_state, elo_utente)
    statistiche_motore.registra(
        res,
        game_state.human_color,
        forza_finale,
        bool(esito_elo),
        elo_utente=elo_utente,
        variazione=variazione,
        elo_motore=elo_motore,
    )
    # La scacchiera finale non si stampa piu' da sola: chi la vuole la
    # chiede con punto s, come in tutte le altre modalita'.
    return current_node
