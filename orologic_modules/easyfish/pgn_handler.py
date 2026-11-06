# Orologic, Easyfish: lettura e scrittura dei PGN.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import datetime
import os
import re
from collections import Counter

import chess
import chess.pgn
import pyperclip
from GBUtils import Acusticator, dgt, key, menu

from .. import ui
from ..board_utils import format_pgn_comments, validate_and_clean_pgn
from ..config import _, maiuscole_nomi, percorso_salvataggio, sanitize_filename
from .constants import (
    DEFAULT_BLACK_SURENAME,
    DEFAULT_EVENT,
    DEFAULT_ROUND,
    DEFAULT_SITE,
    DEFAULT_WHITE_SURENAME,
)


def CopyPGNToClipboard(game):
    """Copia la partita corrente negli appunti in formato PGN."""
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    game.accept(exporter)
    ui.copia_negli_appunti(str(exporter), _("PGN copiato negli appunti."))


def PastePGNFromClipboard():
    """Incolla una partita dagli appunti in formato PGN."""
    pgn_string = pyperclip.paste()
    if not pgn_string.strip():
        return None
    try:
        games, is_corrupted, is_corrected, err_msg, cleaned_text = (
            validate_and_clean_pgn(pgn_string)
        )

        if is_corrupted:
            from ..config import VOLUME

            Acusticator(["d3", 0.5, 0, VOLUME], kind=3)
            print(_("\n[Errore] PGN non valido:"))
            print(err_msg)
            return None

        if is_corrected:
            pyperclip.copy(cleaned_text)
            print(
                _(
                    "\n[Info] Il PGN presentava lievi imperfezioni di layout ed e' stato corretto e aggiornato negli appunti."
                )
            )
            from ..config import VOLUME

            Acusticator(["c5", 0.1, 0, VOLUME, "e5", 0.1, 0, VOLUME], kind=1)

        if not games:
            return None
        return games[0], is_corrected
    # Rete di sicurezza: un errore qui non deve fermare il programma.
    except Exception:  # noqa: BLE001
        return None


def _leggi_intestazioni(percorso):
    """Le intestazioni di ogni partita del file, con la posizione da cui
    rileggerla per intero. Le mosse non si leggono: un database scaricato da
    Lichess ne ha centinaia, e per elencarle bastano i tag."""
    voci = []
    with open(percorso, encoding="utf-8-sig", errors="replace") as f:
        while True:
            posizione = f.tell()
            intestazioni = chess.pgn.read_headers(f)
            if intestazioni is None:
                break
            voci.append((posizione, intestazioni))
    return voci


def _istante_del_file(nome, intestazioni):
    """La chiave per ordinare i file dal piu' recente: la data, e l'ora se
    c'e', che Orologic scrive nel nome di ogni file che salva; per gli altri
    file la data della prima partita."""
    trovati = re.findall(r"(\d{8})(?:_?(\d{6}))?", nome)
    if trovati:
        data, ora = trovati[-1]
        return data + (ora or "000000")
    data = re.sub(r"[^0-9?]", "", intestazioni.get("Date", "")).replace("?", "0")
    return data[:8].ljust(8, "0") + "000000"


def _descrivi_partita(intestazioni):
    """Una riga per l'elenco: giocatori, risultato e data."""
    return _("{w} contro {b}, {res}, {data}").format(
        w=intestazioni.get("White", "?"),
        b=intestazioni.get("Black", "?"),
        res=intestazioni.get("Result", "*"),
        data=intestazioni.get("Date", "?"),
    )


def _data_filtro(testo):
    """La data scritta dall'utente nella forma delle date PGN, 2026.10.01.

    Vanno bene l'anno da solo, anno e mese o la data intera, con l'anno in
    testa come nel PGN o in coda come si scrive di solito, 1/10/2026, e con
    punti, trattini, barre o spazi in mezzo. Restituisce la stringa vuota per
    un campo vuoto e None per una data che non si capisce.
    """
    testo = testo.strip()
    if not testo:
        return ""
    parti = re.split(r"[./\-\s]+", testo)
    if len(parti) > 3 or not all(p.isdigit() for p in parti):
        return None
    if len(parti[0]) != 4:
        parti.reverse()
    anno, *resto = parti
    if len(anno) != 4:
        return None
    for valore, limite in zip(resto, (12, 31), strict=False):
        if not 1 <= int(valore) <= limite:
            return None
    return ".".join([anno] + [v.zfill(2) for v in resto])


def _chiedi_data(prompt):
    """Chiede una data finche' non se ne scrive una che si capisce."""
    while True:
        data = _data_filtro(dgt(prompt, kind="s", smin=0, smax=20))
        if data is not None:
            return data
        print(_("Data non capita. Esempi: 2026.10.01, 2026.10, 2026, 1/10/2026."))


def _filtra_partite(voci):
    """Il filtro a piu' passi per i file da molte partite: bianco, nero,
    risultato e intervallo di date, dove un campo vuoto vale per tutte.
    Restituisce le voci che passano."""
    from ..pgn_search import applica_filtri, estrai_info

    filtri = {}
    bianco = dgt(_("Nome giocatore Bianco (vuoto=qualsiasi): "), kind="s", smin=0)
    if bianco.strip():
        filtri["white"] = bianco.strip()
    nero = dgt(_("Nome giocatore Nero (vuoto=qualsiasi): "), kind="s", smin=0)
    if nero.strip():
        filtri["black"] = nero.strip()
    risultati = {
        "1-0": _("Vittoria Bianco (1-0)"),
        "0-1": _("Vittoria Nero (0-1)"),
        "1/2-1/2": _("Patta (1/2-1/2)"),
        "qualsiasi": _("Qualsiasi risultato"),
    }
    risultato = menu(
        risultati, show=True, p=_("Scegli risultato: "), empty_enter="qualsiasi"
    )
    if risultato and risultato != "qualsiasi":
        filtri["result"] = risultato
    dal = _chiedi_data(_("Dalla data, per esempio 2026.10.01 (vuoto=qualsiasi): "))
    if dal:
        filtri["date_from"] = dal
    al = _chiedi_data(_("Alla data, per esempio 2026.10.31 (vuoto=qualsiasi): "))
    if al:
        filtri["date_to"] = al
    indici = applica_filtri(estrai_info([h for _p, h in voci]), filtri)
    totale = len(voci)
    print(
        _("Partite corrispondenti: {n} di {tot} ({pct:.2f}%)").format(
            n=len(indici), tot=totale, pct=len(indici) / totale * 100
        )
    )
    return [voci[i] for i in indici]


def _scegli(voci, prompt):
    """Sceglie una voce da un elenco numerato, nell'ordine dato. Con una
    voce sola menu la restituirebbe in silenzio: qui la si dice."""
    if len(voci) == 1:
        print(next(iter(voci.values())))
    return menu(voci, show=True, p=prompt, numbered=True, ordered=False)


def ScegliPartitaDallaCartella():
    """Comando .pa: sceglie una partita fra i file della cartella pgn.

    I file si filtrano per nome e si elencano dal piu' recente. Un file da
    una partita sola la consegna subito; per quelli da molte, come i database
    scaricati da Lichess, c'e' prima il filtro a piu' passi. Restituisce la
    partita letta, o None se non se ne sceglie nessuna.
    """
    cartella = percorso_salvataggio("pgn")
    filtro = dgt(_("Parte del nome del file (vuoto=tutti): "), kind="s", smin=0)
    filtro = filtro.strip().lower()
    try:
        nomi = [
            n
            for n in os.listdir(cartella)
            if n.lower().endswith(".pgn") and filtro in n.lower()
        ]
    except OSError:
        nomi = []
    file_trovati = []
    for nome in nomi:
        percorso = os.path.join(cartella, nome)
        try:
            voci = _leggi_intestazioni(percorso)
        except OSError:
            continue
        if voci:
            file_trovati.append((_istante_del_file(nome, voci[0][1]), percorso, voci))
    if not file_trovati:
        print(_("Nessun file trovato nella cartella pgn."))
        return None
    file_trovati.sort(key=lambda t: (t[0], t[1]), reverse=True)
    elenco = {}
    per_percorso = {}
    for _istante, percorso, voci in file_trovati:
        nome = os.path.splitext(os.path.basename(percorso))[0]
        if len(voci) == 1:
            elenco[percorso] = _descrivi_partita(voci[0][1])
        else:
            elenco[percorso] = _("{nome}, {n} partite").format(nome=nome, n=len(voci))
        per_percorso[percorso] = voci
    # Una partita e la sua analisi automatica hanno gli stessi tag: solo
    # allora il nome del file, che le distingue, entra nella riga.
    ripetute = Counter(elenco.values())
    for percorso, riga in elenco.items():
        if ripetute[riga] > 1:
            nome = os.path.splitext(os.path.basename(percorso))[0]
            elenco[percorso] = f"{riga}, {nome}"
    percorso = _scegli(elenco, _("Scegli un file (ESC per annullare): "))
    if percorso is None:
        return None
    voci = per_percorso[percorso]
    if len(voci) > 1:
        voci = _filtra_partite(voci)
        if not voci:
            print(_("Nessuna partita corrisponde ai criteri di ricerca."))
            return None
        partite = {str(i): _descrivi_partita(h) for i, (_p, h) in enumerate(voci)}
        scelta = _scegli(partite, _("Scegli una partita (ESC per annullare): "))
        if scelta is None:
            return None
        voci = [voci[int(scelta)]]
    posizione = voci[0][0]
    with open(percorso, encoding="utf-8-sig", errors="replace") as f:
        f.seek(posizione)
        return chess.pgn.read_game(f)


def InitNewPGN(board=None, tags=None):
    """Inizializza una nuova partita PGN con header di default e posizione iniziale."""
    game = chess.pgn.Game()

    # Se board è specificata e non è la posizione standard, impostiamo FEN e SetUp
    if board and board.fen() != chess.STARTING_FEN:
        game.headers["SetUp"] = "1"
        game.headers["FEN"] = board.fen()
        # Se stiamo iniziando una partita da una posizione personalizzata, la board deve essere passata a setup
        game.setup(board)

    game.headers["Event"] = DEFAULT_EVENT
    game.headers["Site"] = DEFAULT_SITE
    game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = DEFAULT_ROUND

    # Se tags personalizzati sono passati (es. nomi giocatori), usali
    if tags:
        for k, v in tags.items():
            game.headers[k] = v
    else:
        game.headers["White"] = DEFAULT_WHITE_SURENAME
        game.headers["Black"] = DEFAULT_BLACK_SURENAME

    game.headers["Result"] = "*"

    # Il nodo corrente per le variazioni è l'inizio del gioco
    node = game
    return game, node


def AddingPGNTAGS(game):
    """Permette all'utente di modificare i tag PGN."""
    print(
        _(
            "Modifica i tag della partita corrente. Premi Invio per accettare i valori attuali."
        )
    )

    current_event = game.headers.get("Event", DEFAULT_EVENT)
    event = dgt(
        prompt=_("Evento [{d}]: ").format(d=current_event),
        kind="s",
        smax=128,
        default=current_event,
    )

    current_site = game.headers.get("Site", DEFAULT_SITE)
    site = dgt(
        prompt=_("Luogo [{d}]: ").format(d=current_site),
        kind="s",
        smax=128,
        default=current_site,
    )

    current_round = game.headers.get("Round", DEFAULT_ROUND)
    round_number = dgt(
        prompt=_("Round [{d}]: ").format(d=current_round),
        kind="s",
        smin=1,
        smax=5,
        default=current_round,
    )

    current_white = game.headers.get("White", DEFAULT_WHITE_SURENAME)
    white_player = dgt(
        prompt=_("Giocatore Bianco [{d}]: ").format(d=current_white),
        kind="s",
        smin=2,
        smax=64,
        default=current_white,
    )
    white_player = maiuscole_nomi(white_player)

    current_black = game.headers.get("Black", DEFAULT_BLACK_SURENAME)
    black_player = dgt(
        prompt=_("Giocatore Nero [{d}]: ").format(d=current_black),
        kind="s",
        smin=2,
        smax=64,
        default=current_black,
    )
    black_player = maiuscole_nomi(black_player)

    result_prompt = _("Risultato: [W]Bianco, [B]Nero, [D]Patta, [U]Sconosciuto.")
    print(result_prompt)
    while True:
        select_result = key().lower()
        if select_result in "wbdu":
            break
        else:
            print(result_prompt)

    if select_result == "w":
        result = "1-0"
    elif select_result == "b":
        result = "0-1"
    elif select_result == "d":
        result = "1/2-1/2"
    elif select_result == "u":
        result = "*"

    game.headers["Event"] = event
    game.headers["Site"] = site
    if "Date" not in game.headers or game.headers["Date"] == "????.??.??":
        game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = round_number
    game.headers["White"] = white_player
    game.headers["Black"] = black_player
    game.headers["Result"] = result

    print(_("Tag aggiornati."))


def SaveGameToFile(game):
    """Salva la partita corrente su un file PGN singolo nella cartella pgn/."""
    # Aggiorna data salvataggio solo se assente
    if "Date" not in game.headers or game.headers["Date"] == "????.??.??":
        game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    game.accept(exporter)
    pgn_str = str(exporter)
    pgn_str = format_pgn_comments(pgn_str)

    # Generazione Nome File
    white = game.headers.get("White", "White")
    black = game.headers.get("Black", "Black")
    result = game.headers.get("Result", "*")
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    base_filename = f"{white}-{black}-{result}-{timestamp}.pgn"
    sanitized_name = sanitize_filename(base_filename)

    # Percorso: usa config.percorso_salvataggio per garantire la cartella corretta
    full_path = percorso_salvataggio(os.path.join("pgn", sanitized_name))

    # Assicuriamoci che la cartella pgn esista (dovrebbe, ma per sicurezza)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(pgn_str)
        print(_("Partita salvata in: {path}").format(path=full_path))

        # Copia negli appunti (filosofia Orologic)
        try:
            pyperclip.copy(pgn_str)
            print(_("PGN copiato automaticamente negli appunti."))
        # Rete di sicurezza: un errore qui non deve fermare il programma.
        except Exception:  # noqa: BLE001, S110
            pass

    # Rete di sicurezza: un errore qui non deve fermare il programma.
    except Exception as e:  # noqa: BLE001
        print(_("Errore durante il salvataggio del file PGN: {e}").format(e=e))
