# Orologic, Easyfish: menu principale della modalita'.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import builtins
import contextlib
import re
import weakref

import chess
import chess.engine
from GBUtils import Acusticator, dgt, enter_escape, menu

from .. import board_utils, config, cruscotto, strato, ui
from .. import engine as orologic_engine

# DRY: Uso le utility di Orologic
from ..board_utils import (
    CustomBoard,
    DescribeMove,
    accoda_commento,
    format_pv_descriptively,
    mosse_fino_al_nodo,
    testo_valutazione,
)
from ..config import _
from . import analysis_utils, posizione
from .constants import MNMAIN
from .drawing import drawing_menu, verbalize_drawings
from .image_exporter import export_board_pdf, image_settings_menu
from .interaction import BoardEditor, ExplorerMode, posizione_dal_fen
from .pgn_handler import (
    AddingPGNTAGS,
    CopyPGNToClipboard,
    InitNewPGN,
    PastePGNFromClipboard,
    SaveGameToFile,
    ScegliPartitaDallaCartella,
)
from .utils import suona_annulla

_orig_print = builtins.print
show_output_on_board = False
sharing_window = None


def custom_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    sep = kwargs.get("sep", " ")
    text = sep.join(str(arg) for arg in args)
    if not text.strip():
        return
    if show_output_on_board and sharing_window and sharing_window.is_active():
        sharing_window.update_text(text)


def GetDynamicPrompt(board, node):
    """Genera il prompt basandosi sul turno, numero di mossa e livello variante."""
    n = board.fullmove_number

    # Calcolo livello variante
    variant_level = 0
    temp_node = node
    while temp_node.parent:
        if temp_node.parent.variations[0] != temp_node:
            variant_level += 1
        temp_node = temp_node.parent

    prefix = f"var{variant_level} " if variant_level else ""

    if not board.move_stack:
        return _("{p}INIZIO {n}. ").format(p=prefix, n=n)

    # La notazione si ricava su una copia: prima la mossa veniva tolta e
    # rimessa sulla scacchiera vera, e un errore fra le due operazioni
    # avrebbe lasciato la posizione senza una mossa.
    copia = board.copy()
    last_move = copia.pop()
    last_san = copia.san(last_move)

    if board.turn == chess.WHITE:
        return f"{prefix}{n - 1}... {last_san}: "
    else:
        return f"{prefix}{n}. {last_san}: "


# Le partite di cui Result l'ha scritto Orologic, dalla fine della linea
# principale, col risultato: se quella fine non e' piu' conclusa, per
# esempio dopo .u dal matto, l'asterisco torna (R112).
_RISULTATI_SCRITTI = weakref.WeakKeyDictionary()


def _segna_il_risultato(game):
    """Result della partita dalla fine della linea principale: l'esito, se
    e' una posizione conclusa; l'asterisco, se non lo e' piu' e l'esito
    l'aveva scritto Orologic. Dentro una variante il PGN salvato e il nome
    del file prendevano un risultato che la partita non ha (R14); dopo .vm o
    .u restava quello di prima (R112)."""
    fine = board_utils.fine_della_partita(game.end().board())
    if fine is not None:
        game.headers["Result"] = fine.risultato
        _RISULTATI_SCRITTI[game] = fine.risultato
    elif _RISULTATI_SCRITTI.get(game) == game.headers.get("Result"):
        game.headers["Result"] = "*"
        _RISULTATI_SCRITTI.pop(game, None)


def CheckGameOver(board, node=None):
    """Controlla se la posizione chiude la partita e dice l'esito, con la
    regola di board_utils.fine_della_partita: la triplice ripetizione e le
    cinquanta mosse solo a fatto avvenuto (R9, R94). Con node, Result della
    partita segue la fine della sua linea principale (R14, R112)."""
    if node is not None:
        _segna_il_risultato(node.root())
    fine = board_utils.fine_della_partita(board)
    if fine is None:
        return
    print(fine.frase())
    board_utils.suona_la_fine()


def _comandi_informativi(cmd, board, node, game, sharing_window):
    """Comandi del menu che si limitano a riferire qualcosa.

    Scacchiera, elenco comandi, mossa migliore, intestazioni del PGN e
    stato della finestra di condivisione. Restituisce vero se il
    comando e' stato riconosciuto.
    """
    if cmd == ".v":
        print(
            _(
                "Pronto per nuova variante. Inserisci una mossa diversa per creare un nuovo ramo."
            )
        )
    elif cmd == ".?":
        # Nella finestra l'elenco e' tutto da leggere: a pagine aspetterebbe
        # un tasto fra l'una e l'altra, e quel tasto la' non si vede.
        with strato.da_leggere(_("Comandi di Easyfish")):
            menu(d=MNMAIN, show_only=True, pager=0 if strato.con_la_plancia() else 20)
    elif cmd in ui.COMANDI_SCACCHIERA or cmd in (".m", ".bm"):
        # Scacchiera e materiale sono quelli di tutte le altre modalita':
        # qui il menu stampava una scacchiera grezza, senza le colonne.
        with strato.da_leggere(_("Scacchiera")):
            ui.comandi_lettura(".m" if cmd in (".m", ".bm") else ".s", game, board=board)
    elif cmd == ".gp":
        CopyPGNToClipboard(game)
    elif cmd == ".i":
        export_board_pdf(board, node)
    elif cmd == ".ii":
        image_settings_menu()
        if sharing_window and sharing_window.is_active():
            sharing_window.nuove_impostazioni()
    elif cmd == ".gf":
        ui.copia_negli_appunti(board.fen(), _("Partita in FEN. Copiata negli appunti"))
    elif cmd == ".gb":
        # La stessa griglia di .s, girata dal lato di chi ha il tratto, poi il
        # tratto a parole e il FEN, per chi la vuole portare in un programma.
        if board.turn == chess.WHITE:
            tratto = _("Tocca al Bianco muovere.")
        else:
            tratto = _("Tocca al Nero muovere.")
        ui.copia_negli_appunti(
            f"{CustomBoard(board.fen())}\n{tratto}\n{board.fen()}\n",
            _("Scacchiera copiata negli appunti, con il tratto e il FEN."),
        )
    elif cmd in [".csb", ".csn", ".cst"]:
        if sharing_window is None or not sharing_window.is_active():
            print(_("Errore: devi prima avviare la condivisione con il comando .cs"))
        elif cmd == ".csb":
            sharing_window.set_orientation("white")
            print(_("Orientamento scacchiera condivisa impostato: Bianco (fisso)."))
        elif cmd == ".csn":
            sharing_window.set_orientation("black")
            print(_("Orientamento scacchiera condivisa impostato: Nero (fisso)."))
        elif cmd == ".cst":
            sharing_window.set_orientation("turn")
            print(
                _(
                    "Orientamento scacchiera condivisa impostato: in base al turno (dinamico)."
                )
            )
    else:
        return False
    return True


def _comandi_analisi(cmd_clean, board, engine, number_command, info, info_fen):
    """Analizza la posizione: .a per i secondi chiesti, .al per le linee
    chieste.

    Restituisce il risultato dell'analisi e il FEN della posizione
    analizzata, che servono a .ac per sapere se quel risultato vale ancora.
    Le linee stavano su punto elle, che pero' in tutte le altre modalita' e'
    la lista delle mosse: era l'ultimo comando rimasto con due significati
    diversi.
    """
    if cmd_clean not in (".a", ".al"):
        return info, info_fen
    if not engine:
        print(_("Motore non caricato in Orologic."))
        return info, info_fen
    # .a# analizza per # secondi, .al# con # linee; il valore che manca e'
    # quello delle impostazioni, con l'intestazione del motore. Prima .al#
    # rileggeva la linea # dell'ultima analisi, e con una linea sola nelle
    # impostazioni rispondeva che ce n'era una sola (Gabriele, collaudo del
    # 23 novembre 2026: il numero di .al ha la precedenza).
    sec = number_command if cmd_clean == ".a" and number_command > 0 else orologic_engine.analysis_time
    linee = number_command if cmd_clean == ".al" and number_command > 0 else orologic_engine.multipv
    print(_("Analisi posizione corrente per {s} secondi.").format(s=sec))
    analisi, righe = analysis_utils.analizza(board, engine, sec, linee)
    for riga in righe:
        print(riga)
    if analisi:
        info = analisi
        info_fen = board.fen()
    return info, info_fen


# Quante semimosse della linea principale entrano nel commento di .ac: la
# linea intera di un'analisi lunga sarebbe troppo da rileggere.
LINEA_SEMIMOSSE = 10


def _analisi_nel_commento(board, node, engine, secondi, info, info_fen):
    """Comando .ac: scrive nel commento della mossa valutazione, mossa
    migliore e linea principale, nella forma di x e v della modalita' Analisi.

    Senza numero riusa l'ultima analisi, se e' di questa posizione; se non lo
    e', o con un numero, ne fa una nuova, di un secondo o dei secondi scritti.
    Restituisce l'analisi, il suo FEN e vero se il commento e' cambiato.
    """
    if not engine:
        print(_("Motore non caricato in Orologic."))
        return info, info_fen, False
    if secondi > 0 or not info or info_fen != board.fen():
        sec = secondi if secondi > 0 else 1
        print(_("Analisi posizione corrente per {s} secondi.").format(s=sec))
        try:
            info = engine.analyse(
                board,
                chess.engine.Limit(time=sec),
                multipv=orologic_engine.multipv,
            )
            info_fen = board.fen()
        # Contorno di Easyfish: si prosegue.
        except Exception as e:  # noqa: BLE001
            print(_("Errore analisi: {e}").format(e=e))
            return info, info_fen, False
    migliore = info[0] if isinstance(info, list) else info
    pv = migliore.get("pv", [])
    score = migliore.get("score")
    if not pv or score is None:
        print(_("Nessuna linea trovata."))
        return info, info_fen, False
    annotazione = " ".join(
        (
            _("[Val: {ev}]").format(ev=testo_valutazione(score)),
            _("[BM: {bm}]").format(bm=format_pv_descriptively(board, pv[:1])),
            _("[Linea: {linea}]").format(
                linea=board.variation_san(pv[:LINEA_SEMIMOSSE])
            ),
        )
    )
    accoda_commento(node, annotazione)
    print(annotazione)
    print(_("Commento registrato."))
    return info, info_fen, True


def _apri_condivisione(board, node, sharing_window):
    """Apre o chiude la finestra grafica per la didattica.

    Restituisce la finestra da usare d'ora in poi, che puo' essere
    quella appena aperta, quella gia' attiva o nessuna.
    """
    if sharing_window is None or not sharing_window.is_active():
        print(
            _(
                "\nAttivazione condivisione scacchiera (finestra grafica per didattica)..."
            )
        )
        print(_("ISTRUZIONI:"))
        print(_("- Puoi condividere la nuova finestra su Meet, Zoom o Teams."))
        print(
            _(
                "- Per continuare ad inserire comandi, ricordati di riportare il focus (cliccare) su questa finestra di testo della console."
            )
        )
        Acusticator(
            [
                "c5",
                0.1,
                0,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0,
                config.VOLUME,
                "c6",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
        )
        # pygame si carica solo per la scacchiera condivisa, non a ogni
        # avvio di Orologic (R93).
        from .sharing_window import PygameBoardWindow

        sharing_window = PygameBoardWindow(config.VERSION)
        sharing_window.start(board, node)
    else:
        Acusticator(
            [
                "c6",
                0.1,
                0,
                config.VOLUME,
                "g5",
                0.1,
                0,
                config.VOLUME,
                "e5",
                0.1,
                0,
                config.VOLUME,
                "c5",
                0.2,
                0,
                config.VOLUME,
            ],
            kind=1,
        )
        sharing_window.stop()
        sharing_window = None
        print(_("\nCondivisione scacchiera disattivata."))
    return sharing_window


@contextlib.contextmanager
def _stampa_deviata():
    """Manda le stampe alla finestra grafica, e le rimette a posto comunque.

    Il ripristino stava sull'ultima riga della funzione: un'uscita
    anticipata o un errore lasciavano tutte le stampe del programma,
    motore e scacchiera compresi, dirottate sulla finestra di Easyfish
    anche dopo esserne usciti.
    """
    originale = builtins.print
    builtins.print = custom_print
    try:
        yield
    finally:
        builtins.print = originale


def _apri_partita(game):
    """La scacchiera e il nodo finale di una partita da aprire in Easyfish.

    Serve a .pg e alle partite che arrivano da altri moduli: in tutti e due i
    casi ci si ritrova sull'ultima mossa della linea principale. La
    posizione di partenza e' quella della partita, anche negli scacchi 960.
    """
    nodo = game.end()
    return posizione.scacchiera_del_nodo(game, nodo), nodo


def _nel_terminale(board):
    """La scacchiera stampata, nel terminale: nella finestra c'e' il
    cruscotto, che la mostra gia'."""
    if not strato.con_la_plancia():
        print(board)


def run(partita=None):
    """Avvia Easyfish, riportando la stampa alla normalita' all'uscita.

    partita, se c'e', e' un chess.pgn.Game che Easyfish apre subito, come
    dopo .pg: cosi' arrivano le partite scelte nel profilatore di Lichess.
    Nella finestra Easyfish e' la zona di una partita: l'area diventa il
    cruscotto, e i prompt valgono come quello delle mosse.
    """
    # Easyfish analizza con la forza della configurazione, anche dopo una
    # partita contro il motore indebolito.
    orologic_engine.forza_della_configurazione()
    # Chiudendo Orologic a meta', per esempio con Alt+F4, o su un errore del
    # nucleo, la partita modificata si salva comunque: prima si salvava solo
    # col punto, e mosse, varianti e commenti si perdevano (R11, R107).
    with _stampa_deviata(), strato.partita():
        try:
            with strato.salvataggio_d_emergenza(_salva_la_partita_aperta):
                _esegui(partita)
        finally:
            _APERTA.update(game=None, modificata=False, testo=None)


# La partita aperta in Easyfish, se e' modificata secondo la bandiera, e il
# suo PGN di quando era appena aperta o salvata, rinfrescati in testa al
# ciclo, per il salvataggio d'emergenza (R11). Conta il confronto col PGN:
# la bandiera si rinfresca solo in testa al ciclo, e una modifica fatta
# dentro un comando, come un commento scritto nell'esploratore, sfuggiva
# chiudendo Orologic da li' (R107).
_APERTA = {"game": None, "modificata": False, "testo": None}


def _salva_la_partita_aperta():
    """Il salvataggio d'emergenza: la partita aperta, se e' cambiata, una
    volta sola."""
    game = _APERTA["game"]
    if game is None or (not _APERTA["modificata"] and str(game) == _APERTA["testo"]):
        return
    _APERTA["game"] = None
    print(_("Orologic si chiude con la partita modificata: la salvo."))
    SaveGameToFile(game)


def _ricorda_la_partita_aperta(game, modificata):
    """In testa al ciclo: la partita aperta e la bandiera, e il PGN di
    confronto quando la partita e' nuova o appena salvata."""
    if not modificata and (_APERTA["game"] is not game or _APERTA["modificata"]):
        _APERTA["testo"] = str(game)
    _APERTA.update(game=game, modificata=modificata)


def _esegui(partita=None):
    global sharing_window, show_output_on_board
    print(
        _(
            "\nBenvenuto in Easyfish, la tua interfaccia testuale con il motore scacchistico.\n\tBuon divertimento!"
        )
    )

    # Init Engine
    if not orologic_engine.ENGINE:
        from ..storage import LoadDB

        db = LoadDB()
        cfg = db.get("engine_config", {})
        if not cfg or not cfg.get("engine_path"):
            if enter_escape(
                _(
                    "Il motore scacchistico non e' configurato, ma e' necessario per Easyfish. Vuoi configurarlo ora? (INVIO per si', ESC per no): "
                )
            ):
                orologic_engine.MenuMotore()

        print(_("Inizializzazione Motore Orologic per Easyfish..."))
        orologic_engine.InitEngine()

    # Il motore vivo, non quello di quando Easyfish e' partito: se muore,
    # riparte (R41).
    engine = orologic_engine.MOTORE

    # New Game
    board = CustomBoard()
    game, node = InitNewPGN(board)
    if partita is not None:
        game = partita
        board, node = _apri_partita(game)
        print(_("Nuova partita caricata."))
        _nel_terminale(board)


    # State
    info = {}
    info_fen = None
    fen_from_clip = ""
    is_modified = False
    last_checked_state = None
    sharing_window = None
    stato = posizione.Stato("easyfish")

    while True:
        _ricorda_la_partita_aperta(game, is_modified)
        if sharing_window and not sharing_window.is_active():
            Acusticator(
                [
                    "c6",
                    0.05,
                    0,
                    config.VOLUME,
                    "g5",
                    0.05,
                    0,
                    config.VOLUME,
                    "e5",
                    0.05,
                    0,
                    config.VOLUME,
                    "c5",
                    0.1,
                    0,
                    config.VOLUME,
                ],
                kind=1,
            )
            print(_("\nFinestra di condivisione scacchiera chiusa."))
            sharing_window = None

        current_state = (board.fen(), len(board.move_stack))
        if current_state != last_checked_state:
            CheckGameOver(board, node)
            drawings_text = verbalize_drawings(node)
            if drawings_text:
                print(drawings_text)
            last_checked_state = current_state
            if sharing_window and sharing_window.is_active():
                sharing_window.update_board(board, node)

        prompt = GetDynamicPrompt(board, node)
        stato.aggiorna(game, board, node)
        strato.fornisci(lambda: cruscotto.dati_di(stato), MNMAIN)
        with strato.prompt_di_gioco():
            key_command = dgt(prompt=prompt, kind="s", smin=1, smax=8192).strip()

        if not key_command:
            continue

        number_command_str = "".join([char for char in key_command if char.isdigit()])
        number_command = int(number_command_str) if number_command_str else 0

        if key_command.startswith("."):
            cmd = key_command.lower()
            # Il comando e' la prima parola senza le cifre: ".cso on", ".a 5"
            # e ".k 12" tenevano lo spazio e la parola, e non arrivavano al
            # loro ramo (R95).
            cmd_clean = "".join([char for char in cmd.split()[0] if not char.isdigit()])

            if cmd == ".":  # ESCI o RISALI
                # Logica di risalita variante
                is_variant = False
                temp = node
                while temp.parent:
                    if temp.parent.variations[0] != temp:
                        is_variant = True
                        break
                    temp = temp.parent

                if is_variant and node.parent:
                    temp_node = node
                    while (
                        temp_node.parent and temp_node.parent.variations[0] == temp_node
                    ):
                        board.pop()
                        temp_node = temp_node.parent
                    if temp_node.parent:
                        board.pop()
                        temp_node = temp_node.parent
                    node = temp_node
                    print(_("Chiusa variante. Ritorno al nodo padre."))
                    continue

                # Si guarda la partita, non la scacchiera del momento: chi
                # tornava all'inizio e poi usciva perdeva la partita (R12).
                if is_modified and (game.variations or game.comment or game.board().fen() != chess.STARTING_FEN):
                    print(_("Salvataggio partita in corso..."))
                    # Se non si salva, si esce solo se lo si vuole (R52).
                    if not SaveGameToFile(game) and not enter_escape(
                        _("La partita non si e' salvata, ma il PGN e' negli appunti. Esco lo stesso? (INVIO si', ESC no): ")
                    ):
                        continue
                if sharing_window:
                    sharing_window.stop()
                break

            elif _comandi_informativi(cmd, board, node, game, sharing_window):
                pass

            elif cmd == ".vm":
                # Promuovi Variante a Mainline
                if node.parent and len(node.parent.variations) > 1:
                    parent = node.parent
                    vars_list = parent.variations

                    # Trova l'indice del nodo corrente
                    try:
                        current_idx = vars_list.index(node)
                        if current_idx > 0:
                            # Scambia con l'indice 0 (Mainline)
                            vars_list[0], vars_list[current_idx] = (
                                vars_list[current_idx],
                                vars_list[0],
                            )
                            is_modified = True
                            # La posizione non cambia, ma la fine della
                            # linea principale si': il controllo rigira
                            # (R112).
                            last_checked_state = None
                            print(_("Variante promossa a linea principale!"))
                        else:
                            print(_("Questa linea è già la principale."))
                    except ValueError:
                        print(_("Errore: nodo non trovato nelle varianti."))
                else:
                    print(
                        _(
                            "Non sei in una variante o non ci sono alternative da promuovere."
                        )
                    )

            elif cmd_clean in [".k", ".k+", ".k-"]:
                target_move = 0
                is_black = False

                # Parsing regex
                # Anche con lo spazio, .k 12 (R95).
                match = re.search(r"^\.k\s*(\d+)\s*([+-]?)$", key_command.lower())
                if match:
                    target_move = int(match.group(1))
                    is_black = match.group(2) == "-"

                # Se non parsato o 0, chiedi interattivamente
                if target_move <= 0:
                    try:
                        target_move = dgt(
                            prompt=_("Numero mossa: "),
                            kind="i",
                            imin=1,
                            imax=600,
                            default=1,
                        )
                        turn_choice = (
                            dgt(
                                prompt=_("B per Bianco, N per Nero: "),
                                kind="s",
                                default="B",
                            )
                            .strip()
                            .upper()
                        )
                        is_black = turn_choice == "N"
                    # Contorno di Easyfish: si prosegue.
                    except Exception:  # noqa: BLE001
                        target_move = 1
                        is_black = False

                color_str = _("Nero") if is_black else _("Bianco")
                print(
                    _("Salto alla mossa {n} ({c})...").format(
                        n=target_move, c=color_str
                    )
                )

                board.reset()
                if "FEN" in game.headers:
                    board.set_fen(game.headers["FEN"])
                node = game

                found = False
                # Gestione caso speciale: Inizio Partita (se corrisponde alla richiesta)
                if target_move == board.fullmove_number and board.turn == (
                    chess.BLACK if is_black else chess.WHITE
                ):
                    found = True
                else:
                    for move in game.mainline_moves():
                        current_turn_is_black = board.turn == chess.BLACK

                        if board.fullmove_number == target_move:
                            if is_black == current_turn_is_black:
                                found = True
                                break

                        board.push(move)
                        if node.variations:
                            node = node.variations[0]
                        else:
                            # Fine partita raggiunta
                            break

                    # Check finale se la richiesta corrisponde all'ultima posizione raggiunta (es. ultima mossa nera giocata -> siamo al bianco successivo, ma loop finito)
                    if (
                        not found
                        and board.fullmove_number == target_move
                        and (board.turn == chess.BLACK) == is_black
                    ):
                        found = True

                if not found:
                    print(
                        _("Mossa {n} {c} non raggiunta (fine partita).").format(
                            n=target_move, c=color_str
                        )
                    )

                _nel_terminale(board)

            elif cmd == ".e":
                # L'esploratore parte dalla mossa dove si e', non dall'inizio.
                print(_("Accesso alla modalità esplorazione..."))
                mod_in_exp, final_node = ExplorerMode(
                    game, engine, sharing_window=sharing_window, nodo=node
                )
                node = final_node
                board = posizione.scacchiera_del_nodo(game, node)
                if mod_in_exp:
                    is_modified = True

            elif cmd == ".na":
                if not strato.con_la_plancia():
                    print(_("Il navigatore della partita c'e' nella finestra: nel terminale usa .e"))
                    continue
                scelto, cambiata = strato.navigatore(game, node)
                if cambiata:
                    is_modified = True
                if scelto is not None:
                    node = scelto
                # Dopo un taglio la mossa di prima puo' non esserci piu'.
                node = posizione.ancora_nella_partita(node)
                board = posizione.scacchiera_del_nodo(game, node)

            elif cmd == ".d":
                # Nella finestra, la finestra dei disegni; nel terminale il menu.
                modificata = strato.disegni(game, node)
                if modificata is None:
                    modificata = drawing_menu(game, node)
                if modificata:
                    is_modified = True
                    if sharing_window and sharing_window.is_active():
                        sharing_window.trigger_update()

            elif cmd == ".pt":
                AddingPGNTAGS(game)
                is_modified = True

            elif cmd == ".cs":
                sharing_window = _apri_condivisione(board, node, sharing_window)

            elif cmd_clean == ".cso":
                parts = key_command.strip().split()
                if len(parts) > 1:
                    val = parts[1].lower()
                    if val == "on":
                        show_output_on_board = True
                    elif val == "off":
                        show_output_on_board = False
                    else:
                        print(_("Opzione non valida. Usa: .cso on | .cso off"))
                        continue
                else:
                    show_output_on_board = not show_output_on_board
                status_str = _("attivata") if show_output_on_board else _("disattivata")
                print(
                    _(
                        "Visualizzazione dell'output di testo sotto la scacchiera {status}."
                    ).format(status=status_str)
                )
                Acusticator(
                    ["c5", 0.08, 0, config.VOLUME, "g5", 0.08, 0, config.VOLUME]
                )
                if sharing_window and sharing_window.is_active():
                    sharing_window.set_show_text_mode(show_output_on_board)

            elif cmd == ".pg":
                print(_("Incolla una nuova posizione PGN dagli appunti..."))
                res = PastePGNFromClipboard()
                if res:
                    loaded_game, is_corrected = res
                    print(
                        _(
                            "ATTENZIONE: La partita corrente verrà salvata e ne inizierà una nuova."
                        )
                    )
                    if is_modified and not SaveGameToFile(game):
                        print(_("La partita corrente non si e' salvata: resta aperta. Il PGN e' negli appunti."))
                        continue
                    game = loaded_game
                    board, node = _apri_partita(game)
                    is_modified = is_corrected
                    print(_("Nuova partita caricata."))
                    _nel_terminale(board)
                else:
                    print(_("PGN non valido o appunti vuoti."))

            elif cmd == ".u":
                # Si ritira la mossa in cui ci si trova, con il suo seguito.
                # Senza seguito, il caso dell'errore di battitura, sparisce
                # subito; con un seguito si chiede, perche' si perde di piu'.
                seguito = posizione.semimosse_dopo(node)
                domanda = posizione.domanda_del_taglio(seguito)
                if not node.parent:
                    print(_("Impossibile eliminare l'inizio della partita."))
                elif seguito == 0 or enter_escape(domanda):
                    node.parent.variations.remove(node)
                    node = node.parent
                    board.pop()
                    is_modified = True
                    suona_annulla()
                    print(_("Mossa/Variante eliminata. Tornati indietro."))

            elif cmd == ".pa":
                scelta = ScegliPartitaDallaCartella()
                if scelta is not None:
                    # Come .pg: la partita modificata si salva in un file
                    # nuovo, quindi aprirne un'altra non fa perdere niente.
                    if is_modified:
                        print(_("Salvataggio partita in corso..."))
                        if not SaveGameToFile(game):
                            print(_("La partita corrente non si e' salvata: resta aperta. Il PGN e' negli appunti."))
                            continue
                    game = scelta
                    board, node = _apri_partita(game)
                    is_modified = False
                    print(_("Nuova partita caricata."))
                    _nel_terminale(board)

            elif cmd == ".fg":
                fen_from_clip = ui.leggi_dagli_appunti()
                if fen_from_clip is None:
                    pass
                elif not fen_from_clip.strip():
                    print(_("Spiacente, appunti vuoti. Copia prima un FEN valido."))
                else:
                    fen_from_clip = fen_from_clip.strip()
                    print(_("Incolla una nuova posizione FEN dagli appunti..."))
                    try:
                        # La posizione deve essere legale, come nell'editor:
                        # prima passava anche senza un Re (R54). I soli
                        # campi accessori sbagliati si correggono (R113).
                        tmp_board, correzioni, errori = posizione_dal_fen(fen_from_clip)
                        if errori:
                            print(_("La posizione del FEN non e' legale:"))
                            for riga in errori:
                                print(riga)
                            continue
                        for riga in correzioni:
                            print(riga)
                        print(
                            _(
                                "FEN valido. ATTENZIONE: La partita corrente verrà salvata e ne inizierà una nuova da questa posizione."
                            )
                        )
                        if is_modified and not SaveGameToFile(game):
                            print(_("La partita corrente non si e' salvata: resta aperta. Il PGN e' negli appunti."))
                            continue
                        board = tmp_board
                        game, node = InitNewPGN(board)
                        is_modified = False
                        _nel_terminale(board)
                    except ValueError:
                        print(_("Stringa FEN non valida."))

            elif cmd == ".n":
                print(_("Nuova partita. La corrente verrà salvata."))
                if is_modified and not SaveGameToFile(game):
                    print(_("La partita corrente non si e' salvata: resta aperta. Il PGN e' negli appunti."))
                    continue
                print(_("Nuova scacchiera pronta. Si parte!"))
                board = CustomBoard()
                game, node = InitNewPGN(board)
                is_modified = False

            elif cmd == ".be":
                print(
                    _(
                        "Accesso all'editor. ATTENZIONE: Al termine dell'editing, la partita corrente verrà salvata e ne inizierà una nuova dalla posizione impostata."
                    )
                )
                if strato.con_la_plancia():
                    # Nella finestra l'editor ha la scacchiera interattiva, e
                    # Annulla lascia la partita com'e'.
                    new_fen = strato.editor_della_scacchiera(board.fen())
                else:
                    new_fen = BoardEditor(
                        starting_fen=board.fen(), sharing_window=sharing_window
                    )
                if new_fen:
                    if is_modified and not SaveGameToFile(game):
                        print(_("La partita corrente non si e' salvata: resta aperta. Il PGN e' negli appunti."))
                        continue
                    board = CustomBoard()
                    board.set_fen(new_fen)
                    game, node = InitNewPGN(board)
                    is_modified = False
                    print(_("Nuova partita avviata dalla posizione editata."))
                    _nel_terminale(board)

            elif cmd_clean in (".a", ".al"):
                with strato.da_leggere(_("Analisi")):
                    info, info_fen = _comandi_analisi(
                        cmd_clean, board, engine, number_command, info, info_fen
                    )

            elif cmd_clean == ".ac":
                info, info_fen, scritto = _analisi_nel_commento(
                    board, node, engine, number_command, info, info_fen
                )
                if scritto:
                    is_modified = True

            elif cmd_clean == ".l":
                # La lista delle mosse e' quella di tutte le altre
                # modalita': qui le mosse si ricostruiscono dal PGN.
                with strato.da_leggere(_("Lista delle mosse")):
                    ui.comandi_lettura(
                        ".l", game, board=board, mosse=mosse_fino_al_nodo(node)
                    )

            else:
                print(
                    _(
                        "Spiacente, {cmd} non è un comando valido.\nDigita '.?' per il menu."
                    ).format(cmd=cmd)
                )

        elif key_command.startswith("_"):
            # Il testo nuovo prende il posto di quello scritto prima, e le
            # analisi di .ac e i disegni restano.
            posizione.metti_il_testo(node, key_command[1:])
            is_modified = True
            print(_("Commento registrato."))

        else:
            from ..lichess_board import handle_exploration_command

            if handle_exploration_command(key_command, board):
                continue
            move = posizione.leggi_la_mossa(board, key_command)

            if move:
                print(DescribeMove(move, board))
                board.push(move)

                existing_variation = None
                for variant in node.variations:
                    if variant.move == move:
                        existing_variation = variant
                        break

                if existing_variation:
                    node = existing_variation
                else:
                    if node.variations:
                        # Divergenza: chiediamo cosa fare
                        print(_("Mossa diversa trovata."))
                        scelta = enter_escape(
                            _("Sovrascrivi linea (Invio) o Aggiungi Variante (Esc)? ")
                        )
                        if scelta:
                            # Invio -> Sovrascrivi: la mossa nuova prende il
                            # posto della linea principale; le varianti
                            # restano, prima sparivano anche loro.
                            node.variations.pop(0)
                            node = node.add_main_variation(move)
                            print(_("Linea sovrascritta."))
                        else:
                            # Esc -> Aggiungi variante
                            node = node.add_variation(move)
                            print(_("Nuova variante creata."))
                    else:
                        node = node.add_variation(move)
                    is_modified = True
            else:
                color = _("Bianco") if board.turn == chess.WHITE else _("Nero")
                print(
                    _("{k}: mossa illegale per il {c}.").format(k=key_command, c=color)
                )
