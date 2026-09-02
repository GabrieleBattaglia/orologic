# Orologic, Orolichess: menu, profilo e sfide.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import json
import os
import time
import webbrowser

import chess
import chess.pgn
from GBUtils import Acusticator, dgt, enter_escape, key, menu

from . import board_utils, config, lichess_board, lichess_profiler, rete, storage, ui
from .config import _, percorso_salvataggio

SECRETS_FILE = percorso_salvataggio(os.path.join("settings", "secrets.json"))


def load_secrets():
    try:
        with open(SECRETS_FILE, encoding="utf-8") as f:
            return json.load(f)
    # Le risposte di Lichess possono cambiare forma: si rinuncia a
    # questo dato e si prosegue.
    except Exception:  # noqa: BLE001
        return {}


def save_secrets(secrets):
    try:
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump(secrets, f, indent=4)
    # Le risposte di Lichess possono cambiare forma: si rinuncia a
    # questo dato e si prosegue.
    except Exception as e:  # noqa: BLE001
        print(_("Errore salvataggio segreti: {e}").format(e=e))


def fetch_profile_info(token, silenzioso=True):
    """Recupera le info del profilo dal server Lichess.

    Con silenzioso a falso, il motivo del mancato recupero viene detto
    all'utente invece di restituire soltanto nulla.
    """
    dati, errore = rete.leggi_json("https://lichess.org/api/account", token=token)
    if errore:
        if not silenzioso:
            print(_("Profilo non recuperato. {motivo}").format(motivo=errore))
        return None
    return dati


def format_ratings(perfs):
    """Formatta i punteggi Elo dai dati perfs dell'API."""
    if not perfs:
        return ""
    ratings = []
    # Mostriamo Rapid, Blitz, Classical e Correspondence se l'utente ha giocato almeno una partita
    for mode in ["rapid", "blitz", "classical", "correspondence"]:
        if mode in perfs and "rating" in perfs[mode]:
            games = perfs[mode].get("games", 0)
            if games > 0:
                ratings.append(
                    _("{mode}: {rating}").format(
                        mode=_(mode.capitalize()), rating=perfs[mode]["rating"]
                    )
                )
    if ratings:
        return _(" - Elo [{ratings}]").format(ratings=", ".join(ratings))
    return ""


def menu_login(db):
    """Gestisce il login e il salvataggio del token di Lichess."""
    print(_("Login a Lichess"))
    print(_("Per collegare Orologic a Lichess e' necessario un 'Personal API Token'."))
    print(
        _(
            "Assicurati di concedere i permessi necessari (leggere il profilo, giocare, puzzle, ecc.)."
        )
    )

    key(_("Premi un tasto per aprire il browser e generare il token su Lichess..."))
    try:
        webbrowser.open("https://lichess.org/account/oauth/token")
    # Le risposte di Lichess possono cambiare forma: si rinuncia a
    # questo dato e si prosegue.
    except Exception:  # noqa: BLE001
        print(
            _(
                "Impossibile aprire il browser automaticamente. Vai manualmente su: https://lichess.org/account/oauth/token"
            )
        )

    # Il token si digita mascherato: e' una credenziale e non deve restare
    # leggibile a schermo ne' nella cronologia del terminale.
    token = dgt(
        _("Incolla qui il tuo token personale, INVIO per annullare: "),
        kind="s",
        pwd=True,
    ).strip()

    if token:
        print(_("Verifica del token in corso..."))
        profile = fetch_profile_info(token)
        if profile:
            username = profile.get("username", _("Sconosciuto"))
            secrets = load_secrets()
            secrets["lichess_token"] = token
            secrets["lichess_username"] = username
            save_secrets(secrets)
            print(_("Token valido! Benvenuto, {username}!").format(username=username))
            # Ritorniamo il profile per aggiornare l'interfaccia subito
            return profile
        else:
            print(
                _(
                    "Errore: Il token inserito non e' valido, e' scaduto, oppure c'e' un problema di connessione."
                )
            )
    else:
        print(_("Login annullato."))
    return None


def menu_logout(db):
    """Gestisce il logout rimuovendo il token."""
    print(_("Logout da Lichess"))
    secrets = load_secrets()
    if "lichess_token" in secrets:
        if enter_escape(
            _(
                "Sei sicuro di voler effettuare il logout e cancellare il token salvato? (Invio = Si, Esc = No): "
            )
        ):
            del secrets["lichess_token"]
            if "lichess_username" in secrets:
                del secrets["lichess_username"]
            save_secrets(secrets)
            print(_("Logout effettuato con successo. Token rimosso."))
            return True
        else:
            print(_("Logout annullato."))
    else:
        print(_("Non sei attualmente loggato (nessun token presente)."))
    return False


def format_timestamp(ts):
    import datetime

    if not ts:
        return _("Sconosciuto")
    return config.format_date_italian(datetime.datetime.fromtimestamp(ts / 1000))


def format_playtime(seconds):
    if not seconds:
        return _("0 secondi")
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(_("{n} giorni").format(n=days) if days != 1 else _("1 giorno"))
    if hours > 0:
        parts.append(_("{n} ore").format(n=hours) if hours != 1 else _("1 ora"))
    if minutes > 0:
        parts.append(
            _("{n} minuti").format(n=minutes) if minutes != 1 else _("1 minuto")
        )
    return ", ".join(parts) if parts else _("< 1 minuto")


def menu_profilo(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    if not token:
        print(_("\nDevi prima effettuare il login per vedere il tuo profilo."))
        return

    print(_("\nRecupero dati del profilo in corso..."))
    profile = fetch_profile_info(token)
    if not profile:
        print(
            _(
                "Impossibile recuperare il profilo. Controlla la tua connessione o il token."
            )
        )
        return

    print(lichess_profiler.format_profile(profile))

    enter_escape(_("\nPremi Invio per tornare al menu Lichess..."))


def fetch_perf_info(username, perf):
    """Recupera le statistiche dettagliate di una variante."""
    dati, errore = rete.leggi_json(
        f"https://lichess.org/api/user/{username}/perf/{perf}"
    )
    if errore:
        print(_("Statistiche non recuperate. {motivo}").format(motivo=errore))
        return None
    return dati


def format_iso_date(iso_str):
    """Formatta una stringa ISO 8601 di Lichess."""
    if not iso_str:
        return _("Sconosciuto")
    import datetime

    try:
        # Rimuove millisecondi e Z per la compatibilità con le vecchie versioni di Python
        iso_str = iso_str.split(".")[0].replace("Z", "")
        dt = datetime.datetime.fromisoformat(iso_str)
        return config.format_date_italian(dt)
    # Le risposte di Lichess possono cambiare forma: si rinuncia a
    # questo dato e si prosegue.
    except Exception:  # noqa: BLE001
        return iso_str


def menu_statistiche(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    username = secrets.get("lichess_username")

    if not token or not username:
        print(_("\nDevi prima effettuare il login per vedere le statistiche."))
        return

    print(_("\nRecupero dati utente in corso..."))
    profile = fetch_profile_info(token)
    if not profile:
        print(_("Impossibile recuperare il profilo. Controlla la tua connessione."))
        return

    perfs = profile.get("perfs", {})
    if not perfs:
        print(_("Nessuna statistica disponibile."))
        return

    valid_modes = {}
    for mode, data in perfs.items():
        if isinstance(data, dict) and data.get("games", 0) > 0:
            valid_modes[mode] = _("Partite: {g}").format(g=data["games"])

    if not valid_modes:
        print(_("\nNon hai ancora giocato nessuna partita."))
        return

    while True:
        # Ricostruiamo il menu iterativamente per permettere di tornare indietro
        scelte_mod = dict(valid_modes)
        scelte_mod["."] = _("Torna al menu Lichess")

        scelta = menu(
            scelte_mod,
            show=True,
            keyslist=True,
            p=_("\nScegli una modalita' per le statistiche: "),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            break

        if scelta == "puzzle":
            print(_("     STATISTICHE: PUZZLE"))
            puzzle_perf = perfs.get("puzzle", {})
            print(_("Elo Attuale: {r}").format(r=puzzle_perf.get("rating", "N/A")))
            print(_("Puzzle giocati: {g}").format(g=puzzle_perf.get("games", 0)))
            if puzzle_perf.get("prov"):
                print(_("Stato: Provvisorio"))
            print(_("Progressione (recente): {p}").format(p=puzzle_perf.get("prog", 0)))
            print(
                _(
                    "\nNota: Le statistiche avanzate (es. Win/Loss/Streak) per i puzzle non sono esposte dall'API di base di Lichess."
                )
            )
            enter_escape(_("\nPremi Invio per continuare..."))
            continue

        print(
            _("\nRecupero statistiche dettagliate per {m}...").format(
                m=scelta.capitalize()
            )
        )
        perf_data = fetch_perf_info(username, scelta)
        if not perf_data or "stat" not in perf_data:
            print(_("Impossibile recuperare le statistiche per questa modalita'."))
            continue

        stat = perf_data["stat"]
        perf = perf_data.get("perf", {})

        print(_("     STATISTICHE: {m}").format(m=scelta.upper()))

        glicko = perf.get("glicko", {})
        print(
            _("Elo Attuale: {r} (Deviazione: {d})").format(
                r=glicko.get("rating", "N/A"), d=glicko.get("deviation", "N/A")
            )
        )
        print(
            _("Progressione (ultime 12 partite): {p}").format(p=perf.get("progress", 0))
        )
        percentile = perf_data.get("percentile")
        if percentile is not None:
            print(
                _("Percentile: {p}% (Sei migliore del {p}% dei giocatori)").format(
                    p=percentile
                )
            )

        count = stat.get("count", {})
        total = count.get("all", 0)
        rated = count.get("rated", 0)
        wins = count.get("win", 0)
        losses = count.get("loss", 0)
        draws = count.get("draw", 0)

        print(
            _("\n[Risultati su {t} partite ({r} classificate)]").format(
                t=total, r=rated
            )
        )
        if total > 0:
            p_win = (wins / total) * 100
            p_loss = (losses / total) * 100
            p_draw = (draws / total) * 100
            print(_("Vittorie: {w} ({p:.2f}%)").format(w=wins, p=p_win))
            print(_("Sconfitte: {l} ({p:.2f}%)").format(l=losses, p=p_loss))
            print(_("Patte: {d} ({p:.2f}%)").format(d=draws, p=p_draw))
        else:
            print(
                _("Vittorie: {w}\nSconfitte: {l}\nPatte: {d}").format(
                    w=wins, l=losses, d=draws
                )
            )

        berserk = count.get("berserk", 0)
        if berserk > 0 and total > 0:
            p_berserk = (berserk / total) * 100
            print(
                _("Volte in cui sei andato Berserk: {b} ({p:.2f}%)").format(
                    b=berserk, p=p_berserk
                )
            )

        opAvg = count.get("opAvg")
        if opAvg is not None:
            print(_("Elo medio avversari: {avg}").format(avg=opAvg))

        disconnects = count.get("disconnects", 0)
        if disconnects > 0:
            print(_("Disconnessioni: {d}").format(d=disconnects))

        highest = stat.get("highest", {})
        lowest = stat.get("lowest", {})
        if highest.get("int") or lowest.get("int"):
            print(_("\n[Record Elo]"))
            if highest.get("int"):
                print(
                    _("Piu' alto: {r} (il {d})").format(
                        r=highest["int"], d=format_iso_date(highest.get("at"))
                    )
                )
            if lowest.get("int"):
                print(
                    _("Piu' basso: {r} (il {d})").format(
                        r=lowest["int"], d=format_iso_date(lowest.get("at"))
                    )
                )

        streaks = stat.get("resultStreak", {})
        win_streak = streaks.get("win", {}).get("max", {}).get("v", 0)
        loss_streak = streaks.get("loss", {}).get("max", {}).get("v", 0)
        if win_streak > 0 or loss_streak > 0:
            print(_("\n[Serie]"))
            print(_("Vittorie consecutive piu' lunga: {w}").format(w=win_streak))
            print(_("Sconfitte consecutive piu' lunga: {l}").format(l=loss_streak))

        time_seconds = count.get("seconds", 0)
        if time_seconds > 0:
            print(
                _("\nTempo speso in questa modalita': {t}").format(
                    t=format_playtime(time_seconds)
                )
            )

        enter_escape(_("\nPremi Invio per continuare..."))


def fetch_following(token):
    utenti, errore = rete.leggi_righe_json(
        "https://lichess.org/api/rel/following", token=token
    )
    if errore:
        print(_("Elenco dei seguiti non recuperato. {motivo}").format(motivo=errore))
        return []
    return utenti


def follow_user(token, username):
    riuscito, errore = rete.invia(
        f"https://lichess.org/api/rel/follow/{username}", token=token
    )
    if riuscito:
        print(_("Ora segui {u}!").format(u=username))
        return True
    print(
        _("Non e' stato possibile seguire {u}. {motivo}").format(
            u=username, motivo=errore
        )
    )
    return False


def unfollow_user(token, username):
    riuscito, errore = rete.invia(
        f"https://lichess.org/api/rel/unfollow/{username}", token=token
    )
    if riuscito:
        print(_("Non segui piu' {u}.").format(u=username))
        return True
    print(_("Operazione non riuscita. {motivo}").format(motivo=errore))
    return False


def send_message(token, username, text):
    riuscito, errore = rete.invia(
        f"https://lichess.org/inbox/{username}", token=token, dati={"text": text}
    )
    if riuscito:
        print(_("Messaggio inviato a {u} con successo!").format(u=username))
        return True
    print(_("Messaggio non inviato a {u}. {motivo}").format(u=username, motivo=errore))
    return False


def menu_amici(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    if not token:
        print(_("\nDevi prima effettuare il login per gestire gli amici."))
        return

    while True:
        print(_("          GESTIONE AMICI"))

        scelte_amici = {
            "vedi": _("Vedi persone che segui"),
            "cerca": _("Cerca e segui nuovo giocatore"),
            ".": _("Torna al menu Lichess"),
        }

        scelta = menu(
            scelte_amici,
            show=True,
            keyslist=True,
            p=_("\nScegli un'azione: "),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            break
        elif scelta == "vedi":
            print(_("\nRecupero lista dei giocatori seguiti..."))
            following = fetch_following(token)
            if not following:
                print(
                    _("Non stai seguendo nessuno o e' impossibile recuperare la lista.")
                )
                enter_escape(_("\nPremi Invio per continuare..."))
            else:
                sorted_following = sorted(
                    following,
                    key=lambda x: (
                        1 if x.get("online") else 0,
                        x.get("username", "").lower(),
                    ),
                    reverse=True,
                )
                amici_menu = {}
                for u in sorted_following:
                    username = u.get("username", _("Sconosciuto"))
                    title = u.get("title", "")
                    title_str = f"[{title}] " if title else ""
                    online = _("ONLINE") if u.get("online") else _("Offline")
                    amici_menu[username] = f"{title_str}{online}"
                amici_menu["."] = _("Indietro")

                scelta_amico = menu(
                    amici_menu,
                    show=True,
                    keyslist=True,
                    p=_("\nScegli un amico per visualizzare le azioni: "),
                    numbered=db.get("menu_numerati", False),
                )
                if scelta_amico != ".":
                    lichess_profiler.show_player_menu(scelta_amico, secrets)

        elif scelta == "cerca":
            lichess_profiler.run_profiler(secrets)


def describe_board(board, last_move_san=None):
    turn = (
        _("Tocca al Bianco muovere.")
        if board.turn == chess.WHITE
        else _("Tocca al Nero muovere.")
    )

    castling = []
    if board.has_kingside_castling_rights(chess.WHITE):
        castling.append(_("Corto Bianco"))
    if board.has_queenside_castling_rights(chess.WHITE):
        castling.append(_("Lungo Bianco"))
    if board.has_kingside_castling_rights(chess.BLACK):
        castling.append(_("Corto Nero"))
    if board.has_queenside_castling_rights(chess.BLACK):
        castling.append(_("Lungo Nero"))
    castling_str = (
        _("Diritti di arrocco: {c}").format(c=", ".join(castling))
        if castling
        else _("Nessun diritto di arrocco.")
    )

    ep_str = ""
    if board.ep_square:
        ep_sq = chess.square_name(board.ep_square)
        ep_str = _("Presa en passant possibile in {sq}.").format(sq=ep_sq)

    last_str = (
        _("Ultima mossa giocata: {m}").format(m=last_move_san) if last_move_san else ""
    )

    return "\n".join(filter(None, [turn, castling_str, ep_str, last_str]))


def handle_exploration_command(user_input, game_state):
    """Comandi di esplorazione, piu' i due che valgono solo qui."""
    if ui.esplora_scacchiera(user_input, game_state):
        return True

    if user_input.lower() == ".b":
        Acusticator(
            [
                "c4",
                0.2,
                -1,
                config.VOLUME,
                "g4",
                0.2,
                -0.3,
                config.VOLUME,
                "c5",
                0.2,
                0.3,
                config.VOLUME,
                "e5",
                0.2,
                1,
                config.VOLUME,
            ],
            kind=1,
            adsr=[5, 5, 80, 10],
        )
        print(game_state.board)
        return True

    if user_input == ".?":
        Acusticator(
            [440.0, 0.3, 0, config.VOLUME, 880.0, 0.3, 0, config.VOLUME],
            kind=1,
            adsr=[10, 0, 100, 20],
        )
        menu(
            {
                "-": _("Riepilogo dei pezzi Bianchi"),
                "+": _("Riepilogo dei pezzi Neri"),
                "-[a-h]": _("Esplora colonna"),
                "-[1-8]": _("Esplora traversa"),
                "-[casa]": _("Dettagli su una casa (es. -e4)"),
                "/[a-h]": _("Diagonale ascendente destra"),
                "\\[a-h]": _("Diagonale ascendente sinistra"),
                ",[P,N,B,R,Q,K]": _("Posizioni di un pezzo specifico"),
                ".b": _("Mostra la scacchiera grafica"),
                ".": _("Arrenditi o esci dal puzzle"),
            },
            show_only=True,
            p=_("Comandi di esplorazione disponibili:"),
            ordered=False,
        )
        return True

    return False


def fetch_puzzle(token=None, daily=False, difficulty=None, angle=None):
    url = (
        "https://lichess.org/api/puzzle/daily"
        if daily
        else "https://lichess.org/api/puzzle/next"
    )
    if difficulty or angle:
        params = []
        if difficulty:
            params.append(f"difficulty={difficulty}")
        if angle:
            params.append(f"angle={angle}")
        if params:
            url += "?" + "&".join(params)

    dati, errore = rete.leggi_json(url, token=None if daily else token)
    if errore:
        print(_("Puzzle non recuperato. {motivo}").format(motivo=errore))
        return None
    return dati


def send_puzzle_result(token, puzzle_id, win):
    if not token or not puzzle_id:
        return
    # L'esito del puzzle e' un dato accessorio: se non arriva a destinazione
    # non vale la pena interrompere il gioco, ma un avviso breve ci sta.
    riuscito, errore = rete.invia(
        "https://lichess.org/api/puzzle/batch/mix",
        token=token,
        dati_json={"solutions": [{"id": puzzle_id, "win": win, "rated": True}]},
    )
    if not riuscito:
        print(
            _("Esito del puzzle non inviato a Lichess. {motivo}").format(motivo=errore)
        )


def calcola_difficolta(user_elo, puzzle_elo_richiesto):
    diff = puzzle_elo_richiesto - user_elo
    if diff <= -400:
        return "easiest"
    if diff <= -150:
        return "easier"
    if diff <= 150:
        return "normal"
    if diff <= 400:
        return "harder"
    return "hardest"


def get_puzzle_themes():
    return {
        "advancedPawn": _("Pedone avanzato"),
        "advantage": _("Vantaggio"),
        "attraction": _("Attrazione"),
        "backRankMate": _("Matto del corridoio"),
        "bishopEndgame": _("Finale di Alfieri"),
        "castling": _("Arrocco"),
        "capturingDefender": _("Cattura del difensore"),
        "clearance": _("Sgombero"),
        "crushing": _("Schiacciante"),
        "deflection": _("Deviazione"),
        "discoveredAttack": _("Attacco di scoperta"),
        "doubleCheck": _("Scacco doppio"),
        "endgame": _("Finale"),
        "enPassant": _("Presa in Passant"),
        "equality": _("Parita'"),
        "exposedKing": _("Re esposto"),
        "fork": _("Forchetta/Attacco doppio"),
        "hangingPiece": _("Pezzo in presa"),
        "interference": _("Interferenza"),
        "intermezzo": _("Mossa intermedia (Zwischenzug)"),
        "kingsideAttack": _("Attacco sull'ala di Re"),
        "knightEndgame": _("Finale di Cavalli"),
        "long": _("Lungo (3 mosse)"),
        "master": _("Partite di Maestri"),
        "mate": _("Scacco matto"),
        "mateIn1": _("Matto in 1"),
        "mateIn2": _("Matto in 2"),
        "mateIn3": _("Matto in 3"),
        "mateIn4": _("Matto in 4"),
        "mateIn5": _("Matto in 5+"),
        "middlegame": _("Medio gioco"),
        "oneMove": _("Una mossa"),
        "opening": _("Apertura"),
        "pawnEndgame": _("Finale di Pedoni"),
        "pin": _("Inchiodatura"),
        "promotion": _("Promozione"),
        "queenEndgame": _("Finale di Donne"),
        "queenRookEndgame": _("Finale Donna e Torre"),
        "queensideAttack": _("Attacco sull'ala di Donna"),
        "quietMove": _("Mossa silenziosa"),
        "rookEndgame": _("Finale di Torri"),
        "sacrifice": _("Sacrificio"),
        "short": _("Corto (2 mosse)"),
        "skewer": _("Infilata"),
        "smotheredMate": _("Matto affogato"),
        "trappedPiece": _("Pezzo intrappolato"),
        "underPromotion": _("Sottopromozione"),
        "veryLong": _("Molto lungo (4+ mosse)"),
        "zugzwang": _("Zugzwang"),
        "vuoto": _("Casuale (Nessun filtro)"),
    }


def get_last_moves_san(board, num=5):
    if not board.move_stack:
        return ""
    moves = board.move_stack[-num:]
    temp_board = board.copy()
    for _mossa in range(len(moves)):
        temp_board.pop()
    parts = []
    for m in moves:
        san = temp_board.san(m)
        if temp_board.turn == chess.WHITE:
            parts.append(f"{temp_board.fullmove_number}. {san}")
        elif not parts:
            parts.append(f"{temp_board.fullmove_number}... {san}")
        else:
            parts.append(san)
        temp_board.push(m)
    return " ".join(parts)


def menu_puzzle(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")

    while True:
        print(_("             PUZZLE LICHESS"))

        scelte_puzzle = {
            "giorno": _("Puzzle del Giorno"),
            "nuovo": _("Risolvi un nuovo puzzle"),
            ".": _("Torna al menu Lichess"),
        }

        scelta = menu(
            scelte_puzzle,
            show=True,
            keyslist=True,
            p=_("\nScegli un'opzione: "),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            break

        difficulty = None
        angle = None
        if scelta == "nuovo":
            # Calcolo Elo Puzzle dell'utente
            user_puzzle_elo = 1500
            if token:
                profile = fetch_profile_info(token)
                if profile and "perfs" in profile and "puzzle" in profile["perfs"]:
                    user_puzzle_elo = profile["perfs"]["puzzle"].get("rating", 1500)

            print(
                _("\nIl tuo punteggio puzzle stimato e': {elo}").format(
                    elo=user_puzzle_elo
                )
            )
            scelta_elo = dgt(
                _(
                    "A quale Elo vuoi esercitarti? (es. 1800, oppure invio per mantenere il tuo): "
                )
            ).strip()

            if scelta_elo.isdigit():
                target_elo = int(scelta_elo)
                difficulty = calcola_difficolta(user_puzzle_elo, target_elo)
                print(
                    _("Lichess adattera' la ricerca alla difficolta': {d}").format(
                        d=difficulty
                    )
                )

            themes = get_puzzle_themes()
            print(_("\nScegli la categoria di puzzle:"))
            angle_scelto = menu(
                themes,
                show=False,
                keyslist=True,
                p=_("Seleziona il tema: "),
                numbered=db.get("menu_numerati", False),
            )
            if angle_scelto != "vuoto":
                angle = angle_scelto

        print(_("\nRecupero puzzle in corso..."))
        puzzle_data = fetch_puzzle(
            token, daily=(scelta == "giorno"), difficulty=difficulty, angle=angle
        )

        if not puzzle_data or "puzzle" not in puzzle_data:
            print(_("Impossibile caricare il puzzle."))
            continue

        puz = puzzle_data["puzzle"]
        game_info = puzzle_data.get("game", {})

        print(_("Puzzle {id}").format(id=puz.get("id")))
        print(_("Difficolta' (Rating Lichess): {r}").format(r=puz.get("rating")))
        print(_("Tema: {t}").format(t=", ".join(puz.get("themes", []))))

        import io

        last_move_san = None
        board = board_utils.CustomBoard()

        if "pgn" in game_info and "initialPly" in puz:
            try:
                pgn_game = chess.pgn.read_game(io.StringIO(game_info["pgn"]))
                node = pgn_game
                ply = 0
                initial_ply = puz["initialPly"]

                board = board_utils.CustomBoard()
                moves_to_push = []
                while node.variations and ply <= initial_ply:
                    node = node.variations[0]
                    moves_to_push.append(node.move)
                    ply += 1

                for m in moves_to_push:
                    board.push(m)

                if node.move and node.parent:
                    last_move_san = board_utils.DescribeMove(
                        node.move, node.parent.board()
                    )
            # Le risposte di Lichess possono cambiare forma: si rinuncia a
            # questo dato e si prosegue.
            except Exception as e:  # noqa: BLE001
                print(_("Errore nel parsing del PGN: {e}").format(e=e))
                # Fallback
                if puz.get("fen"):
                    board = board_utils.CustomBoard(puz["fen"])
                    last_move_san = puz.get("lastMove")
        elif puz.get("fen"):
            board = board_utils.CustomBoard(puz["fen"])
            last_move_san = puz.get("lastMove")

        print("\n" + describe_board(board, last_move_san))
        ui.report_all_pieces(board, not board.turn)
        ui.report_all_pieces(board, board.turn)
        Acusticator(
            [
                "c5",
                0.05,
                0,
                config.VOLUME,
                "e5",
                0.05,
                0,
                config.VOLUME,
                "g5",
                0.05,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[0, 0, 100, 5],
        )

        print(
            _("\nSuggerimento: digita . per uscire, .? per l'aiuto sulle esplorazioni")
        )

        soluzione = puz.get("solution", [])
        mossa_idx = 0
        risolto = False
        result_sent = False
        start_time = time.time()

        while mossa_idx < len(soluzione):
            mossa_corretta_uci = soluzione[mossa_idx]
            mossa_corretta_move = chess.Move.from_uci(mossa_corretta_uci)

            last_5 = get_last_moves_san(board, 5)
            prompt_text = f"\n{last_5} > " if last_5 else "\n> "
            user_input = dgt(prompt_text).strip()
            if not user_input:
                continue

            if handle_exploration_command(user_input, board):
                if user_input.lower() != ".b" and user_input != ".?":
                    continue

            if user_input == "." or user_input.lower() == "s":
                if user_input == ".":
                    if enter_escape(
                        _(
                            "Vuoi vedere la soluzione del puzzle? (Invio = Si', Esc = No): "
                        )
                    ):
                        user_input = "s"
                    else:
                        print(_("Puzzle interrotto."))
                        if not result_sent:
                            send_puzzle_result(token, puz.get("id"), win=False)
                            result_sent = True
                        end_time = time.time()
                        elapsed = int(end_time - start_time)
                        mins = elapsed // 60
                        secs = elapsed % 60
                        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                        print(_("Tempo impiegato: {t}").format(t=time_str))
                        break

                if user_input == "s":
                    if not result_sent:
                        send_puzzle_result(token, puz.get("id"), win=False)
                        result_sent = True
                    print(_("Soluzione del Puzzle"))
                    temp_board = board.copy()
                    for i in range(mossa_idx, len(soluzione)):
                        sol_move = chess.Move.from_uci(soluzione[i])
                        desc = board_utils.DescribeMove(sol_move, temp_board)
                        if i % 2 == mossa_idx % 2:
                            print(_("Il tuo tratto: {m}").format(m=desc))
                        else:
                            print(_("L'avversario risponde con: {m}").format(m=desc))
                        temp_board.push(sol_move)
                    end_time = time.time()
                    elapsed = int(end_time - start_time)
                    mins = elapsed // 60
                    secs = elapsed % 60
                    time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                    print(_("Tempo impiegato: {t}").format(t=time_str))
                break

            if user_input.startswith((".", "/", "\\", "-", ",")) or user_input == "+":
                continue

            try:
                raw_input = board_utils.NormalizeMove(user_input)
                move = board.parse_san(raw_input)
            except ValueError:
                try:
                    move = board.parse_uci(raw_input)
                except ValueError:
                    Acusticator([600.0, 0.6, 0, config.VOLUME], adsr=[5, 0, 35, 90])
                    print(
                        _(
                            "Mossa non valida. Digita . per uscire, .? per l'aiuto sulle esplorazioni"
                        )
                    )
                    continue

            if move == mossa_corretta_move:
                Acusticator(
                    [1000.0, 0.01, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0]
                )
                desc_move = board_utils.DescribeMove(move, board)
                print(_("Corretto! Hai giocato: {m}").format(m=desc_move))
                board.push(move)
                mossa_idx += 1

                if mossa_idx < len(soluzione):
                    avv_uci = soluzione[mossa_idx]
                    avv_move = chess.Move.from_uci(avv_uci)
                    desc_avv = board_utils.DescribeMove(avv_move, board)
                    print(_("L'avversario risponde con: {m}").format(m=desc_avv))
                    board.push(avv_move)
                    mossa_idx += 1
                    Acusticator(
                        [
                            "c5",
                            0.05,
                            0,
                            config.VOLUME,
                            "e5",
                            0.05,
                            0,
                            config.VOLUME,
                            "g5",
                            0.05,
                            0,
                            config.VOLUME,
                        ],
                        kind=1,
                        adsr=[0, 0, 100, 5],
                    )
                else:
                    risolto = True
            else:
                if not result_sent:
                    send_puzzle_result(token, puz.get("id"), win=False)
                    result_sent = True
                Acusticator(["a3", 0.15, 0, config.VOLUME], kind=2, adsr=[5, 20, 0, 75])
                print(_("Mossa errata, riprova."))

        if risolto:
            if not result_sent:
                send_puzzle_result(token, puz.get("id"), win=True)
                result_sent = True
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
            print(_("\nCongratulazioni! Hai risolto il puzzle!"))
            end_time = time.time()
            elapsed = int(end_time - start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            print(_("Tempo impiegato: {t}").format(t=time_str))
            enter_escape(_("Premi Invio per continuare..."))


def fetch_user_profile(username, token=None):
    dati, errore = rete.leggi_json(
        f"https://lichess.org/api/user/{username}", token=token
    )
    if errore:
        print(
            _("Profilo di {u} non recuperato. {motivo}").format(
                u=username, motivo=errore
            )
        )
        return None
    return dati


def watch_player(username, token):
    import msvcrt
    import sys

    print(_("Controllo se l'utente e' in gioco..."))
    profile = fetch_user_profile(username, token)
    if profile:
        if "playing" in profile:
            game_url = profile["playing"]
            game_id = game_url.split("/")[-1][:8]
            lichess_board.spectate_game(game_id, token)
            return True
        else:
            print(_("L'utente non ha partite in corso in questo momento."))
            if enter_escape(
                _(
                    "Desideri attendere l'inizio di una partita? (Invio = Si', Esc = No): "
                )
            ):
                start_time = time.time()
                timeout = 30 * 60  # 30 minuti
                polling_interval = 10  # 10 secondi

                print(
                    _(
                        "\nIn attesa che {u} inizi a giocare... (Premi ESC o digita . per annullare)"
                    ).format(u=username)
                )

                while time.time() - start_time < timeout:
                    elapsed = time.time() - start_time
                    remaining = int(timeout - elapsed)
                    rem_min = remaining // 60
                    rem_sec = remaining % 60

                    sys.stdout.write(
                        _("\rAttesa in corso... Tempo residuo: {m:02d}:{s:02d}").format(
                            m=rem_min, s=rem_sec
                        )
                    )
                    sys.stdout.flush()

                    interrupted = False
                    for _idx in range(polling_interval * 10):
                        if msvcrt.kbhit():
                            c = msvcrt.getwch()
                            if c in ("\x1b", "."):
                                interrupted = True
                                break
                        time.sleep(0.1)

                    if interrupted:
                        print(_("\nAttesa annullata."))
                        return False

                    profile = fetch_user_profile(username, token)
                    if profile and "playing" in profile:
                        game_url = profile["playing"]
                        game_id = game_url.split("/")[-1][:8]
                        sys.stdout.write("\n")
                        print(_("Partita iniziata! Connessione in corso..."))
                        lichess_board.spectate_game(game_id, token)
                        return True

                print(
                    _(
                        "\nTempo massimo di attesa (30 minuti) superato. Ritorno al menu."
                    )
                )
    else:
        print(_("Utente non trovato o errore di connessione."))
    return False


def menu_guarda(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")

    while True:
        print(_("          GUARDA PARTITA"))
        scelte = {
            "id": _("Inserisci ID o URL Partita"),
            "giocatore": _("Inserisci Nome Utente Lichess"),
            "amico": _("Scegli un Amico"),
            "tv": _("Lichess TV (Migliori in corso)"),
            ".": _("Torna al menu Lichess"),
        }

        scelta = menu(
            scelte,
            show=True,
            keyslist=True,
            p=_("\nScegli un'opzione: "),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            break

        elif scelta == "id":
            val = dgt(_("\nID o URL della partita: ")).strip()
            if not val:
                continue
            if "lichess.org/@/" in val:
                username = val.split("lichess.org/@/")[-1].split("/")[0]
                watch_player(username, token)
            elif "lichess.org/" in val:
                val = val.split("lichess.org/")[-1].split("/")[0][:8]
                lichess_board.spectate_game(val, token)
            else:
                lichess_board.spectate_game(val, token)

        elif scelta == "giocatore":
            val = dgt(_("\nNome Utente: ")).strip()
            if not val:
                continue
            watch_player(val, token)

        elif scelta == "amico":
            if not token:
                print(_("Devi aver fatto il login per vedere gli amici."))
                continue
            print(_("Recupero lista degli amici in corso..."))
            following = fetch_following(token)
            if not following:
                print(
                    _("Non stai seguendo nessuno o e' impossibile recuperare la lista.")
                )
                enter_escape(_("\nPremi Invio per continuare..."))
                continue

            sorted_friends = sorted(
                following,
                key=lambda x: (1 if "playing" in x else 0, 1 if x.get("online") else 0),
                reverse=True,
            )

            scelte_amici = {}
            for f in sorted_friends:
                username = f.get("username", f.get("id"))
                title = f.get("title", "")
                title_str = f"[{title}] " if title else ""
                status = ""
                if "playing" in f:
                    status = _("IN GIOCO")
                elif f.get("online"):
                    status = _("ONLINE")
                else:
                    status = _("Offline")
                scelte_amici[username] = f"{title_str}{status}"
            scelte_amici["."] = _("Indietro")

            amico_scelto = menu(
                scelte_amici,
                show=True,
                keyslist=True,
                p=_("\nScegli un amico da guardare: "),
                numbered=db.get("menu_numerati", False),
            )
            if amico_scelto != ".":
                f_obj = next(
                    f
                    for f in following
                    if f.get("username", f.get("id")) == amico_scelto
                )
                if "playing" in f_obj:
                    game_url = f_obj["playing"]
                    game_id = game_url.split("/")[-1][:8]
                    lichess_board.spectate_game(game_id, token)
                else:
                    watch_player(amico_scelto, token)

        elif scelta == "tv":
            print(_("Recupero canali TV in corso..."))
            data, errore = rete.leggi_json("https://lichess.org/api/tv/channels")
            if errore:
                print(_("Canali TV non recuperati. {motivo}").format(motivo=errore))
                continue

            scelte_tv = {}
            for k, v in data.items():
                user_name = v.get("user", {}).get("name", _("Anonimo"))
                rating = v.get("rating", "?")
                scelte_tv[k] = _("{channel} ({user} - Elo: {rating})").format(
                    channel=_(k.capitalize()), user=user_name, rating=rating
                )
            scelte_tv["."] = _("Indietro")

            canale_scelto = menu(
                scelte_tv,
                show=True,
                keyslist=True,
                p=_("\nScegli canale: "),
                numbered=db.get("menu_numerati", False),
            )
            if canale_scelto != ".":
                game_id = data[canale_scelto].get("gameId")
                if not game_id:
                    print(_("Lichess non ha indicato quale partita: riprova."))
                    continue
                lichess_board.spectate_game(game_id, token)


# Le due domande che il menu fa a Lichess a ogni giro. La risposta resta
# buona per qualche secondo: senza questo, tornando al menu dopo ogni voce
# si aspettava la rete ogni volta.
_DURATA_CACHE = 5.0
_cache_rete = {}


def _da_cache(chiave):
    """Risposta ancora fresca per quella domanda, oppure nulla."""
    voce = _cache_rete.get(chiave)
    if voce and time.time() - voce[0] < _DURATA_CACHE:
        return voce[1]
    return None


def _in_cache(chiave, valore):
    _cache_rete[chiave] = (time.time(), valore)
    return valore


def scorda_cache_rete():
    """Da usare quando la situazione e' cambiata di sicuro: login, logout,
    partita appena accettata o abbandonata."""
    _cache_rete.clear()


def get_active_games(token, silenzioso=True, usa_cache=True):
    """Partite in corso. Interrogata a ogni giro di menu, quindi per scelta
    tace sugli errori se non le si chiede il contrario."""
    if not token:
        return []
    if usa_cache:
        pronte = _da_cache(("partite", token))
        if pronte is not None:
            return pronte
    dati, errore = rete.leggi_json(
        "https://lichess.org/api/account/playing", token=token
    )
    if errore:
        if not silenzioso:
            print(_("Partite in corso non recuperate. {motivo}").format(motivo=errore))
        return []
    return _in_cache(("partite", token), dati.get("nowPlaying", []))


def get_incoming_challenges(token, silenzioso=True, usa_cache=True):
    """Sfide in arrivo, con la stessa regola di silenzio delle partite attive."""
    if not token:
        return []
    if usa_cache:
        pronte = _da_cache(("sfide", token))
        if pronte is not None:
            return pronte
    dati, errore = rete.leggi_json("https://lichess.org/api/challenge", token=token)
    if errore:
        if not silenzioso:
            print(_("Sfide in arrivo non recuperate. {motivo}").format(motivo=errore))
        return []
    return _in_cache(("sfide", token), dati.get("in", []))


def accept_challenge(token, challenge_id):
    riuscito, errore = rete.invia(
        f"https://lichess.org/api/challenge/{challenge_id}/accept", token=token
    )
    if not riuscito:
        print(_("Sfida non accettata. {motivo}").format(motivo=errore))
    return riuscito


def decline_challenge(token, challenge_id):
    riuscito, errore = rete.invia(
        f"https://lichess.org/api/challenge/{challenge_id}/decline", token=token
    )
    if not riuscito:
        print(_("Sfida non rifiutata. {motivo}").format(motivo=errore))
    return riuscito


def get_game_params(for_seek=False, for_bot=False):
    limit = None
    inc = None
    days = None
    while True:
        tempo = dgt(
            _(
                "Tempo di gioco (minuti+incremento, es. 5+3, oppure invio per Corrispondenza): "
            )
        ).strip()
        if not tempo:
            days_str = dgt(
                _("Giorni per mossa (es. 1, 2, 3... o invio per 1): ")
            ).strip()
            days = int(days_str) if days_str.isdigit() else 1
            break
        if "+" in tempo:
            parts = tempo.split("+")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                limit = int(parts[0]) * 60
                inc = int(parts[1])
                break
        print(_("Formato non valido. Usa minuti+secondi, ad esempio 10+0 o 5+3."))

    if enter_escape(
        _("\nVuoi giocare una partita Standard? (Invio = Si', Esc = No): ")
    ):
        variant = "standard"
    else:
        variant_scelte = {
            "chess960": _("Chess960"),
            "crazyhouse": _("Crazyhouse"),
            "antichess": _("Antichess"),
            "atomic": _("Atomic"),
            "horde": _("Horde"),
            "kingOfTheHill": _("King of the Hill"),
            "racingKings": _("Racing Kings"),
            "threeCheck": _("Three-check"),
        }
        db = storage.LoadDB()
        variant = menu(
            variant_scelte,
            show=True,
            keyslist=True,
            p=_("Scegli la variante: "),
            numbered=db.get("menu_numerati", False),
        )

    rated = False
    if not for_bot:
        rated = enter_escape(
            _("\nPartita classificata (Rated)? (Invio = Si', Esc = No): ")
        )

    color_scelte = {"1": _("Bianco"), "2": _("Nero"), "3": _("Casuale")}
    color_key = menu(color_scelte, show=True, keyslist=True, p=_("Scegli il colore: "))

    color_map = {"1": "white", "2": "black", "3": "random"}
    color = color_map.get(color_key, "random")

    rating_range = ""
    if for_seek and rated:
        print(
            _(
                "\nRange Elo avversario (es. 1500-1800). Lascia vuoto per qualsiasi avversario."
            )
        )
        rating_range = dgt(_("Range Elo: ")).strip()

    return {
        "clock_limit": limit,
        "clock_increment": inc,
        "days": days,
        "variant": variant,
        "rated": rated,
        "color": color,
        "rating_range": rating_range,
    }


def challenge_ai(token, level, params_dict):
    payload = {
        "level": level,
        "color": params_dict["color"],
        "variant": params_dict["variant"],
    }
    if params_dict["clock_limit"] is not None:
        payload["clock.limit"] = params_dict["clock_limit"]
        payload["clock.increment"] = params_dict["clock_increment"]
    else:
        payload["days"] = params_dict.get("days", 1)

    dati, errore = rete.leggi_json(
        "https://lichess.org/api/challenge/ai", token=token, metodo="POST", dati=payload
    )
    if errore:
        print(
            _("Partita contro il computer non creata. {motivo}").format(motivo=errore)
        )
        return None
    return dati


def challenge_user(token, username, params_dict):
    payload = {
        "color": params_dict["color"],
        "variant": params_dict["variant"],
        "rated": "true" if params_dict["rated"] else "false",
    }
    if params_dict["clock_limit"] is not None:
        payload["clock.limit"] = params_dict["clock_limit"]
        payload["clock.increment"] = params_dict["clock_increment"]
    else:
        payload["days"] = params_dict.get("days", 1)

    dati, errore = rete.leggi_json(
        f"https://lichess.org/api/challenge/{username}",
        token=token,
        metodo="POST",
        dati=payload,
    )
    if errore:
        print(_("Sfida non inviata. {motivo}").format(motivo=errore))
        return None
    return dati


def seek_game(token, params_dict):
    import msvcrt
    import sys
    import threading

    payload = {
        "color": params_dict["color"],
        "variant": params_dict["variant"],
        "rated": "true" if params_dict["rated"] else "false",
    }
    if params_dict["clock_limit"] is not None:
        # Lichess accetta i minuti anche con la mezza unita': la divisione
        # intera faceva diventare un minuto e mezzo un minuto secco.
        payload["time"] = params_dict["clock_limit"] / 60
        payload["increment"] = params_dict["clock_increment"]
    else:
        payload["days"] = params_dict.get("days", 1)

    if params_dict.get("rating_range"):
        payload["ratingRange"] = params_dict["rating_range"]

    stop_seek = threading.Event()
    problemi = []

    def do_seek():
        """Tiene aperta la richiesta di avversario finche' non arriva una
        partita. Se il server rifiuta piu' volte di seguito, si arrende e
        lascia detto perche': prima girava all'infinito in silenzio."""
        errori_di_fila = 0
        while not stop_seek.is_set():
            risposta, errore = rete.apri(
                "https://lichess.org/api/board/seek",
                token=token,
                metodo="POST",
                dati=payload,
                timeout=rete.TIMEOUT_STREAM,
            )
            if errore:
                errori_di_fila += 1
                if errori_di_fila >= 3:
                    problemi.append(errore)
                    stop_seek.set()
                    return
                time.sleep(2)
                continue
            errori_di_fila = 0
            try:
                with risposta:
                    for _riga in risposta:
                        if stop_seek.is_set():
                            break
            except OSError:
                pass
            if not stop_seek.is_set():
                time.sleep(1)

    t = threading.Thread(target=do_seek, daemon=True)
    t.start()

    print(_("\nRicerca avversario in corso... (Premi ESC per annullare)"))

    game_found = False
    game_id = None

    start_time = time.time()
    last_poll = start_time
    last_print = start_time

    initial_games = {g["gameId"] for g in get_active_games(token, usa_cache=False)}

    while t.is_alive() or not stop_seek.is_set():
        if problemi:
            ui.pulisci_riga()
            print(_("Ricerca interrotta. {motivo}").format(motivo=problemi[0]))
            return None
        if msvcrt.kbhit() and msvcrt.getwch() == "\x1b":
            stop_seek.set()
            ui.pulisci_riga()
            print(_("Ricerca annullata."))
            return None

        now = time.time()

        # 30 seconds feedback
        if now - last_print >= 30:
            elapsed = int(now - start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            ui.pulisci_riga()
            sys.stdout.write(
                _(
                    "Ricerca avversario in corso da {m:02d}:{s:02d}... (Premi ESC per annullare)"
                ).format(m=mins, s=secs)
            )
            sys.stdout.flush()
            last_print = now

        # 5 seconds poll
        if now - last_poll > 5:
            current_games = get_active_games(token, usa_cache=False)
            for g in current_games:
                if g["gameId"] not in initial_games:
                    game_found = True
                    game_id = g["gameId"]
                    stop_seek.set()
                    break
            last_poll = now

        if game_found:
            break
        time.sleep(0.1)

    if game_found:
        sys.stdout.write("\n")
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
                "e6",
                0.4,
                0,
                config.VOLUME,
            ],
            kind=1,
            adsr=[10, 10, 80, 20],
        )
        print(_("Avversario trovato!"))
        return game_id
    else:
        ui.pulisci_riga()
        print(_("Ricerca terminata o interrotta."))
        return None


def menu_gioca(db):
    secrets = load_secrets()
    token = secrets.get("lichess_token")
    if not token:
        print(_("\nDevi prima effettuare il login per giocare."))
        return

    while True:
        print(_("          GIOCA PARTITA"))

        scelte = {
            "cerca": _("Cerca avversario casuale (Seek)"),
            "bot": _("Gioca contro il computer"),
            "amico": _("Sfida un amico"),
            "accetta": _("Accetta sfide in attesa"),
            "riprendi": _("Riprendi partita in corso"),
            ".": _("Torna al menu Lichess"),
        }

        scelta = menu(
            scelte,
            show=True,
            keyslist=True,
            p=_("\nScegli un'opzione: "),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            break

        elif scelta == "cerca":
            print(_("\nImpostazioni per la ricerca dell'avversario:"))
            params = get_game_params(for_seek=True, for_bot=False)
            game_id = seek_game(token, params)
            if game_id:
                lichess_board.play_game(game_id, token, secrets.get("lichess_username"))

        elif scelta == "bot":
            level_str = dgt(
                _("Livello di Stockfish (da 1 a 8, predefinito 3): ")
            ).strip()
            level = (
                int(level_str)
                if level_str.isdigit() and 1 <= int(level_str) <= 8
                else 3
            )
            print(_("\nImpostazioni della partita:"))
            params = get_game_params(for_seek=False, for_bot=True)

            print(_("\nAvvio partita in corso..."))
            game_info = challenge_ai(token, level, params)
            if game_info:
                print(
                    _("Partita avviata! ID: {id}").format(
                        id=game_info.get("id", _("sconosciuto"))
                    )
                )
                lichess_board.play_game(
                    game_info["id"], token, secrets.get("lichess_username")
                )

        elif scelta == "amico":
            print(_("Recupero lista degli amici..."))
            following = fetch_following(token)
            if not following:
                print(
                    _(
                        "Non stai seguendo nessun amico. Usa il Profilatore per cercare e seguire altri giocatori."
                    )
                )
                continue

            scelte_amici = {}
            for f in following:
                online = _("ONLINE") if f.get("online") else _("Offline")
                scelte_amici[f["id"]] = _("{u} ({o})").format(u=f["username"], o=online)
            scelte_amici["."] = _("Annulla")

            amico_scelto = menu(
                scelte_amici,
                show=True,
                keyslist=True,
                p=_("\nScegli un amico da sfidare: "),
                numbered=db.get("menu_numerati", False),
            )
            if amico_scelto == ".":
                continue

            print(_("\nImpostazioni della sfida:"))
            params = get_game_params(for_seek=False, for_bot=False)

            print(_("\nInvio sfida in corso..."))
            resp = challenge_user(token, amico_scelto, params)
            if resp and "challenge" in resp:
                challenge_id = resp["challenge"]["id"]
                print(_("Sfida inviata! In attesa che l'avversario accetti..."))

                timeout = 60
                start_time = time.time()
                game_started = False
                while time.time() - start_time < timeout:
                    print(
                        _(
                            "In attesa... ({t}s rimanenti) - Premi CTRL+C o ESC per annullare"
                        ).format(t=int(timeout - (time.time() - start_time))),
                        end="\r",
                    )

                    import msvcrt

                    if msvcrt.kbhit():
                        c = msvcrt.getwch()
                        if c == "\x1b" or c == "\x03":  # ESC or CTRL+C
                            print()
                            break

                    active = get_active_games(token, usa_cache=False)
                    for game in active:
                        if game.get("gameId") == challenge_id:
                            print(_("\nSfida accettata!"))

                            lichess_board.play_game(
                                challenge_id, token, secrets.get("lichess_username")
                            )
                            game_started = True
                            break
                    if game_started:
                        break
                    time.sleep(2)

                if not game_started:
                    print(
                        _(
                            "\nL'avversario non ha accettato la sfida in tempo (oppure e' offline)."
                        )
                    )
                    print(
                        _(
                            "Nota: La sfida potrebbe rimanere valida su Lichess se era per corrispondenza."
                        )
                    )
                    rete.invia(
                        f"https://lichess.org/api/challenge/{challenge_id}/cancel",
                        token=token,
                    )

        elif scelta == "accetta":
            print(_("Controllo sfide in entrata..."))
            challenges = get_incoming_challenges(token, usa_cache=False)
            if not challenges:
                print(_("Non hai sfide in attesa."))
                continue

            for c in challenges:
                c_id = c["id"]
                challenger = c.get("challenger", {}).get("name", _("Anonimo"))
                variant = c["variant"]["name"]
                speed = c["speed"]
                rated = _("Classificata") if c["rated"] else _("Amichevole")
                print(
                    _("\nSfida da {u} ({v}, {s}, {r})").format(
                        u=challenger, v=variant, s=speed, r=rated
                    )
                )

                if enter_escape(
                    _("Vuoi accettare questa sfida? (Invio = Si', Esc = No): ")
                ):
                    print(_("Accetto la sfida..."))
                    if accept_challenge(token, c_id):
                        print(_("Sfida accettata!"))
                        lichess_board.play_game(
                            c_id, token, secrets.get("lichess_username")
                        )
                        break
                    else:
                        print(
                            _(
                                "Impossibile accettare la sfida (potrebbe essere stata annullata)."
                            )
                        )
                else:
                    print(_("Rifiuto la sfida..."))
                    decline_challenge(token, c_id)

        elif scelta == "riprendi":
            print(_("Cerco partite in corso..."))
            games = get_active_games(token, usa_cache=False)
            if not games:
                print(_("Non hai partite attive."))
                continue

            scelte_games = {}
            for g in games:
                opp = g.get("opponent", {}).get("username", _("Anonimo"))
                color = _("Bianco") if g.get("color") == "white" else _("Nero")
                scelte_games[g["gameId"]] = _("Contro {o} (Sei il {c})").format(
                    o=opp, c=color
                )
            scelte_games["."] = _("Annulla")

            game_scelto = menu(
                scelte_games,
                show=True,
                keyslist=True,
                p=_("\nScegli la partita da riprendere: "),
                numbered=db.get("menu_numerati", False),
            )
            if game_scelto != ".":
                lichess_board.play_game(
                    game_scelto, token, secrets.get("lichess_username")
                )


def run():
    """Entry point principale di Orolichess integrato in orologic."""
    db = storage.LoadDB()
    secrets = load_secrets()

    # Fetch iniziale del profilo per ottenere Elo aggiornato se già loggati
    rating_info = ""
    puzzle_games = None
    token = secrets.get("lichess_token")
    if token:
        print(_("Connessione a Lichess in corso..."))
        profile = fetch_profile_info(token)
        if profile:
            username = profile.get(
                "username", secrets.get("lichess_username", _("Utente"))
            )
            secrets["lichess_username"] = username
            rating_info = format_ratings(profile.get("perfs", {}))
            if "perfs" in profile and "puzzle" in profile["perfs"]:
                puzzle_games = profile["perfs"]["puzzle"].get("games")
            save_secrets(secrets)

    while True:
        # Costruiamo il menu dinamicamente in base allo stato del login
        MENU_CHOICES = {}

        secrets = load_secrets()
        # Il token va riletto a ogni giro insieme ai segreti: dopo un login
        # o un logout fatti in questa stessa sessione, quello tenuto in
        # memoria non e' piu' quello buono.
        token = secrets.get("lichess_token")
        is_logged = "lichess_token" in secrets

        active_games = []
        num_challenges = 0
        if is_logged:
            MENU_CHOICES["logout"] = _("Logout (Rimuovi token)")
            active_games = get_active_games(token)
            if active_games:
                if len(active_games) == 1:
                    MENU_CHOICES["riprendi"] = _(
                        "Riprendi partita in sospeso (1 attiva)"
                    )
                else:
                    MENU_CHOICES["riprendi"] = _(
                        "Riprendi partita in sospeso ({n} attive)"
                    ).format(n=len(active_games))

            # Controllo sfide in sospeso
            try:
                challenges = get_incoming_challenges(token)
                num_challenges = len(challenges) if challenges else 0
            # Le risposte di Lichess possono cambiare forma: si rinuncia a
            # questo dato e si prosegue.
            except Exception:  # noqa: BLE001
                num_challenges = 0
        else:
            MENU_CHOICES["login"] = _("Login (Imposta API Token)")

        testo_puzzle = _("Risolvi puzzle")
        if puzzle_games is not None:
            testo_puzzle += _(" (Partite: {p})").format(p=puzzle_games)

        MENU_CHOICES.update(
            {
                "profilo": _("Profilo Lichess"),
                "statistiche": _("Statistiche utente"),
                "storia": _("Storia Elo e Sonificazione"),
                "amici": _("Gestione Amici"),
                "puzzle": testo_puzzle,
                "cerca": _("Cerca e Profila Giocatore"),
                "guarda": _("Guarda una partita"),
                "gioca": _("Gioca una partita"),
            }
        )

        if is_logged:
            MENU_CHOICES["messaggi"] = _("Casella Postale (Apri Lichess Inbox)")
            if num_challenges > 0:
                MENU_CHOICES["sfide"] = _("Sfide in attesa ({n})").format(
                    n=num_challenges
                )

        MENU_CHOICES["."] = _("Ritorna a Orologic (Esci)")

        if is_logged:
            username = secrets.get("lichess_username", _("Utente"))
            print(
                # I tre trattini erano l'ultimo separatore grafico rimasto
                # nel programma: lo screen reader li legge uno per uno.
                _("Orolichess, connesso come: {username}{rating}").format(
                    username=username, rating=rating_info
                )
            )
        else:
            print(_("Orolichess, non connesso: scegli Login per iniziare"))

        scelta = menu(
            MENU_CHOICES,
            show=True,
            keyslist=True,
            p=_("\nScegli un'azione: "),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            print(_("Uscita da Orolichess in corso. Ritorno a orologic..."))
            break
        elif scelta == "riprendi":
            scelte_games = {}
            for g in active_games:
                opp = g.get("opponent", {}).get("username", _("Anonimo"))
                color = _("Bianco") if g.get("color") == "white" else _("Nero")
                my_turn = g.get("isMyTurn", False)
                # Notare che `isMyTurn` viene fornito dall'API playing
                turn_str = (
                    _("Tocca a TE!") if my_turn else _("In attesa dell'avversario")
                )
                scelte_games[g["gameId"]] = _("Contro {o} (Sei il {c}) - {t}").format(
                    o=opp, c=color, t=turn_str
                )
            scelte_games["."] = _("Annulla")

            game_scelto = menu(
                scelte_games,
                show=True,
                keyslist=True,
                p=_("\nScegli la partita da riprendere: "),
                numbered=db.get("menu_numerati", False),
            )
            if game_scelto != ".":
                lichess_board.play_game(
                    game_scelto, token, secrets.get("lichess_username")
                )
        elif scelta == "login":
            scorda_cache_rete()
            new_profile = menu_login(db)
            if new_profile:
                rating_info = format_ratings(new_profile.get("perfs", {}))
        elif scelta == "logout":
            if menu_logout(db):
                scorda_cache_rete()
                rating_info = ""
        elif scelta == "profilo":
            menu_profilo(db)
        elif scelta == "statistiche":
            menu_statistiche(db)
        elif scelta == "storia":
            if is_logged:
                from . import lichess_stats

                lichess_stats.run_stats(secrets.get("lichess_username"), secrets)
            else:
                print(_("\nDevi prima effettuare il login per vedere la storia Elo."))
                enter_escape(_("\nPremi Invio per continuare..."))
        elif scelta == "amici":
            menu_amici(db)
        elif scelta == "puzzle":
            menu_puzzle(db)
        elif scelta == "cerca":
            lichess_profiler.run_profiler(secrets)
        elif scelta == "guarda":
            menu_guarda(db)
        elif scelta == "gioca":
            menu_gioca(db)
        elif scelta == "messaggi":
            print(_("Apertura della casella postale nel browser..."))
            try:
                webbrowser.open("https://lichess.org/inbox")
            # Le risposte di Lichess possono cambiare forma: si rinuncia a
            # questo dato e si prosegue.
            except Exception as e:  # noqa: BLE001
                print(_("Impossibile aprire il browser: {e}").format(e=e))
        elif scelta == "sfide":
            print(_("Controllo sfide in entrata..."))
            try:
                challenges = get_incoming_challenges(token, usa_cache=False)
            # Le risposte di Lichess possono cambiare forma: si rinuncia a
            # questo dato e si prosegue.
            except Exception:  # noqa: BLE001
                challenges = []

            if not challenges:
                print(_("Non hai sfide in attesa."))
                continue

            for c in challenges:
                c_id = c["id"]
                challenger = c.get("challenger", {}).get("name", _("Anonimo"))
                variant = c["variant"]["name"]
                speed = c["speed"]
                rated = _("Classificata") if c["rated"] else _("Amichevole")
                print(
                    _("\nSfida da {u} ({v}, {s}, {r})").format(
                        u=challenger, v=variant, s=speed, r=rated
                    )
                )

                if enter_escape(
                    _("Vuoi accettare questa sfida? (Invio = Si', Esc = No): ")
                ):
                    print(_("Accetto la sfida..."))
                    if accept_challenge(token, c_id):
                        print(_("Sfida accettata!"))
                        lichess_board.play_game(
                            c_id, token, secrets.get("lichess_username")
                        )
                        break
                    else:
                        print(
                            _(
                                "Impossibile accettare la sfida (potrebbe essere stata annullata)."
                            )
                        )
                else:
                    print(_("Rifiuto la sfida..."))
                    decline_challenge(token, c_id)


if __name__ == "__main__":
    run()
