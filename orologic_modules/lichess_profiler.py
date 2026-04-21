import json
import urllib.request
import urllib.parse
import sys
import os
import datetime
from GBUtils import menu, key, dgt, enter_escape, Acusticator
from . import config, storage


def _(testo):
    from .config import L10N

    return L10N.get(testo, testo)


def get_token(secrets):
    return secrets.get("lichess_token")


def search_player():
    print(_("\n=== RICERCA GIOCATORE ==="))
    print(
        _(
            "Digita il nome utente. Usa il tasto Backspace per correggere, INVIO per confermare, ESC per annullare."
        )
    )
    print(
        _(
            "Seleziona uno dei suggerimenti scrivendolo per intero. Se non compare, premetti '=' al nome (es: =MioNome)."
        )
    )

    term = ""
    results = []

    while True:
        if len(term) >= 3 and not term.startswith("="):
            try:
                url = f"https://lichess.org/api/player/autocomplete?term={urllib.parse.quote(term)}&object=true"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                results = data.get("result", [])
            except Exception:
                results = []
        else:
            results = []

        if term.startswith("="):
            print(_("\n[Ricerca ESATTA forzata per: {t}]").format(t=term[1:]))
        elif len(term) >= 3:
            if results:
                nomi = [res.get("name") for res in results]
                print("\n({n}) {lista}".format(n=len(nomi), lista=", ".join(nomi)))
            else:
                print(_("\nNessun giocatore trovato per '{t}'.").format(t=term))
        else:
            print()

        prompt_text = f"> {term}"
        c = key(prompt=prompt_text)

        if c == "\x1b":  # ESC
            return None
        elif c in ("\r", "\n"):  # Invio
            if term.startswith("="):
                exact = term[1:].strip()
                if exact:
                    return exact
                continue

            if not term:
                return None

            exact_match = next(
                (
                    res.get("name")
                    for res in results
                    if res.get("name").lower() == term.lower()
                ),
                None,
            )
            if exact_match:
                return exact_match

            if len(results) == 1:
                return results[0].get("name")

            print(
                _(
                    "\nIl termine inserito '{t}' non corrisponde esattamente a un suggerimento. Affina la ricerca o usa '=' per forzare."
                ).format(t=term)
            )
        elif c in ("\b", "\x08"):  # Backspace
            term = term[:-1]
        elif c and c.isprintable():  # Caratteri normali
            term += c


def format_profile(profile):
    p = []
    p.append(_("--- PROFILO DI {u} ---").format(u=profile.get("username")))
    if "title" in profile:
        p.append(_("Titolo: {t}").format(t=profile["title"]))

    p.append(
        _("Bio: {b}").format(
            b=profile.get("profile", {}).get("bio", _("Non specificata"))
        )
    )

    createdAt = profile.get("createdAt")
    if createdAt:
        dt = datetime.datetime.fromtimestamp(createdAt / 1000.0)
        p.append(_("Iscritto il: {d}").format(d=dt.strftime("%d/%m/%Y")))

    seenAt = profile.get("seenAt")
    if seenAt:
        dt = datetime.datetime.fromtimestamp(seenAt / 1000.0)
        p.append(_("Ultimo accesso: {d}").format(d=dt.strftime("%d/%m/%Y %H:%M")))

    count = profile.get("count", {})
    t = count.get("all", 0)
    w = count.get("win", 0)
    d = count.get("draw", 0)
    l = count.get("loss", 0)
    if t > 0:
        pw = (w / t) * 100
        pd = (d / t) * 100
        pl = (l / t) * 100
        p.append(
            _(
                "Partite totali: {t} (Vinte: {w} [{pw:.1f}%], Patte: {d} [{pd:.1f}%], Perse: {l} [{pl:.1f}%])"
            ).format(t=t, w=w, pw=pw, d=d, pd=pd, l=l, pl=pl)
        )
    else:
        p.append(
            _("Partite totali: {t} (Vinte: {w}, Patte: {d}, Perse: {l})").format(
                t=t, w=w, d=d, l=l
            )
        )

    playTime = profile.get("playTime", {})
    total_seconds = playTime.get("total", 0)
    if total_seconds > 0:
        y = total_seconds // 31536000
        rem = total_seconds % 31536000
        mo = rem // 2592000
        rem = rem % 2592000
        wk = rem // 604800
        rem = rem % 604800
        dy = rem // 86400
        rem = rem % 86400
        hr = rem // 3600
        rem = rem % 3600
        mi = rem // 60

        time_parts = []
        if y > 0:
            time_parts.append(_("{y} anni").format(y=y) if y != 1 else _("1 anno"))
        if mo > 0:
            time_parts.append(_("{mo} mesi").format(mo=mo) if mo != 1 else _("1 mese"))
        if wk > 0:
            time_parts.append(
                _("{wk} settimane").format(wk=wk) if wk != 1 else _("1 settimana")
            )
        if dy > 0:
            time_parts.append(
                _("{dy} giorni").format(dy=dy) if dy != 1 else _("1 giorno")
            )
        if hr > 0:
            time_parts.append(_("{hr} ore").format(hr=hr) if hr != 1 else _("1 ora"))
        if mi > 0:
            time_parts.append(
                _("{mi} minuti").format(mi=mi) if mi != 1 else _("1 minuto")
            )

        p.append(
            _("Tempo di gioco totale: {t_str}").format(t_str=", ".join(time_parts))
        )
    else:
        p.append(_("Tempo di gioco totale: 0 minuti"))

    p.append(_("\n-- Punteggi Elo --"))
    perfs = profile.get("perfs", {})
    for perf_name, perf_data in perfs.items():
        if perf_name in [
            "blitz",
            "rapid",
            "classical",
            "bullet",
            "puzzle",
            "correspondence",
        ]:
            games = perf_data.get("games", 0)
            if games > 0:
                p.append(
                    f"{perf_name.capitalize()}: {perf_data.get('rating', '?')} ({games} partite)"
                )

    return "\n".join(p)


def show_profile(username, token):
    try:
        url = f"https://lichess.org/api/user/{username}"
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            profile = json.loads(resp.read().decode("utf-8"))
            print("\n" + format_profile(profile))
            return profile
    except Exception as e:
        print(_("Errore durante il caricamento del profilo: {e}").format(e=e))
        return None


def send_message(username, token):
    if not token:
        print(_("Devi essere loggato per inviare messaggi."))
        return

    msg = input(
        _("\nScrivi il messaggio per {u} (lascia vuoto per annullare): ").format(
            u=username
        )
    ).strip()
    if not msg:
        return

    try:
        url = f"https://lichess.org/inbox/{username}"
        data = urllib.parse.urlencode({"text": msg}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                Acusticator(["c5", 0.1, 0, config.VOLUME], kind=1)
                print(_("Messaggio inviato con successo."))
    except urllib.error.HTTPError as e:
        print(_("Impossibile inviare il messaggio. Errore API: {c}").format(c=e.code))
    except Exception as e:
        print(_("Errore: {e}").format(e=e))


def follow_player(username, token, follow=True):
    if not token:
        print(_("Devi essere loggato per seguire i giocatori."))
        return

    action = "follow" if follow else "unfollow"
    try:
        url = f"https://lichess.org/api/rel/{action}/{username}"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                Acusticator(["e5", 0.1, 0, config.VOLUME], kind=1)
                if follow:
                    print(_("Ora segui {u}.").format(u=username))
                else:
                    print(_("Non segui piu' {u}.").format(u=username))
    except Exception as e:
        print(_("Errore: {e}").format(e=e))


def download_games(username, token):
    print(_("\n--- Scarica e Filtra Partite di {u} ---").format(u=username))

    if enter_escape(
        _(
            "Premi INVIO per scaricare l'intero database, oppure ESC per impostare filtri di ricerca: "
        )
    ):
        # Nessun filtro
        filters = {}
        is_partial = False
    else:
        is_partial = True
        filters = {}

        # Colore
        col = key(
            _("Vuoi partite giocate col (b)ianco, (n)ero o (e)ntrambi? (b/n/e): ")
        ).lower()
        if col == "b":
            filters["color"] = "white"
        elif col == "n":
            filters["color"] = "black"

        # Risultato
        res = key(
            _("Risultato: (v)ittoria, (p)areggio, (s)confitta o (t)utte? (v/p/s/t): ")
        ).lower()
        if res in ["v", "p", "s"]:
            filters["result"] = res

        # Range Elo
        if enter_escape(
            _(
                "Vuoi specificare un range di Elo per l'avversario? (INVIO per si', ESC per no): "
            )
        ):
            min_elo = dgt(_("Elo minimo: "), kind="i", imin=0, imax=4000)
            max_elo = dgt(_("Elo massimo: "), kind="i", imin=0, imax=4000)
            filters["elo"] = (min_elo, max_elo)

        # ECO
        if enter_escape(
            _("Vuoi specificare un codice ECO? (INVIO per si', ESC per no): ")
        ):
            eco = input(_("Codice ECO (es. B10): ")).strip().upper()
            if eco:
                filters["eco"] = eco

    # Download
    print(_("\nInizio download e filtraggio in corso... (potrebbe volerci del tempo)"))

    url = f"https://lichess.org/api/games/user/{username}?pgnInJson=true&opening=true"
    if "color" in filters:
        url += f"&color={filters['color']}"

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/x-ndjson")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    downloaded_games = []
    analyzed = 0
    matched = 0

    try:
        with urllib.request.urlopen(req) as resp:
            for line in resp:
                if not line.strip():
                    continue
                analyzed += 1
                try:
                    game = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                # Applica filtri locali
                keep = True

                if is_partial:
                    # Result filter
                    if "result" in filters:
                        res_filter = filters["result"]
                        winner = game.get("winner")
                        player_color = (
                            "white"
                            if game.get("players", {})
                            .get("white", {})
                            .get("user", {})
                            .get("id")
                            == username.lower()
                            else "black"
                        )

                        if res_filter == "v":
                            if winner != player_color:
                                keep = False
                        elif res_filter == "s":
                            if winner is None or winner == player_color:
                                keep = False
                        elif res_filter == "p":
                            if winner is not None:
                                keep = False

                    # Elo filter
                    if keep and "elo" in filters:
                        min_e, max_e = filters["elo"]
                        opp_color = (
                            "black"
                            if game.get("players", {})
                            .get("white", {})
                            .get("user", {})
                            .get("id")
                            == username.lower()
                            else "white"
                        )
                        opp_elo = (
                            game.get("players", {}).get(opp_color, {}).get("rating", 0)
                        )
                        if not (min_e <= opp_elo <= max_e):
                            keep = False

                    # ECO filter
                    if keep and "eco" in filters:
                        eco_code = game.get("opening", {}).get("eco", "")
                        if not eco_code.startswith(filters["eco"]):
                            keep = False

                if keep and "pgn" in game:
                    downloaded_games.append(game)
                    matched += 1

                if analyzed % 50 == 0:
                    sys.stdout.write(f"\rAnalizzate: {analyzed}, {matched} trovate.")
                    sys.stdout.flush()

    except Exception as e:
        print(_("\nErrore durante il download: {e}").format(e=e))

    sys.stdout.write(f"\rAnalizzate: {analyzed}, {matched} trovate.\n")

    if matched == 0:
        print(_("Nessuna partita corrisponde ai criteri di ricerca."))
        return

    # Salvataggio PGN
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    kind_str = "partial" if is_partial else "complete"
    filename = f"{username}_{kind_str}_games_{now_str}.pgn"
    filepath = config.percorso_salvataggio(os.path.join("pgn", filename))

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            for g in downloaded_games:
                f.write(g["pgn"])
                f.write("\n\n")
        print(_("\nFile salvato in: {f}").format(f=filepath))
    except Exception as e:
        print(_("Errore nel salvataggio del file: {e}").format(e=e))
        return

    # Selezione partita per analisi
    if enter_escape(
        _("\nVuoi scegliere una partita da analizzare? (INVIO per si', ESC per no): ")
    ):
        choose_game_for_analysis(downloaded_games)


def choose_game_for_analysis(games_list):
    page_size = 25
    total = len(games_list)
    current_page = 0

    while True:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, total)
        page_games = games_list[start_idx:end_idx]

        choices = {}
        for i, g in enumerate(page_games):
            idx = start_idx + i
            w = (
                g.get("players", {})
                .get("white", {})
                .get("user", {})
                .get("name", "Anonimo")
            )
            b = (
                g.get("players", {})
                .get("black", {})
                .get("user", {})
                .get("name", "Anonimo")
            )
            res = ""
            if g.get("winner") == "white":
                res = "1-0"
            elif g.get("winner") == "black":
                res = "0-1"
            else:
                res = "1/2-1/2"

            eco = g.get("opening", {}).get("eco", "")
            date = datetime.datetime.fromtimestamp(
                g.get("createdAt", 0) / 1000
            ).strftime("%Y-%m-%d")

            desc = f"{w} vs {b} ({res}) - ECO: {eco} - {date}"
            choices[str(i + 1)] = desc

        if start_idx > 0:
            choices["p"] = _("Pagina Precedente")
        if end_idx < total:
            choices["n"] = _("Pagina Successiva")

        choices["."] = _("Annulla")

        print(
            _("\n--- Partite Trovate (Pagina {c}/{t}) ---").format(
                c=current_page + 1, t=(total + page_size - 1) // page_size
            )
        )

        scelta = menu(
            choices,
            show=True,
            keyslist=True,
            p=_("\nScegli una partita (numero) o naviga: "),
        )

        if scelta == ".":
            break
        elif scelta == "n" and end_idx < total:
            current_page += 1
        elif scelta == "p" and start_idx > 0:
            current_page -= 1
        elif scelta.isdigit() and 1 <= int(scelta) <= len(page_games):
            idx = int(scelta) - 1
            selected_game = page_games[idx]
            pgn_str = selected_game["pgn"]
            import pyperclip

            pyperclip.copy(pgn_str)
            print(_("\nIl PGN della partita e' stato copiato negli appunti!"))
            print(_("Ora verrai reindirizzato a Easyfish."))
            print(
                _(
                    "Premi Invio per continuare e, quando sarai nel menu principale di Easyfish, digita '.pg' per incollare e analizzare la partita."
                )
            )
            input()
            from .easyfish import easyfish_app

            easyfish_app.run()
            break


def show_player_menu(username, secrets):
    db = storage.LoadDB()
    token = secrets.get("lichess_token")

    # Mostra sùbito il profilo e ottieni i dati (incluso se lo seguiamo)
    profile = show_profile(username, token)

    while True:
        # Se profile non è disponibile, assumiamo False per following
        is_following = profile.get("following", False) if profile else False

        choices = {
            "profilo": _("Leggi profilo dettagliato"),
            "messaggio": _("Invia un messaggio"),
            "sfida": _("Sfida a una partita"),
            "scarica": _("Cerca e scarica partite"),
        }

        if is_following:
            choices["smetti"] = _("Smetti di seguire")
        else:
            choices["segui"] = _("Segui giocatore")

        choices["."] = _("Torna indietro")

        scelta = menu(
            choices,
            show=True,
            keyslist=True,
            p=_("\nAzioni per {u}: ").format(u=username),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            break
        elif scelta == "profilo":
            profile = show_profile(username, token)
        elif scelta == "messaggio":
            send_message(username, token)
        elif scelta == "sfida":
            from . import lichess_app

            print(_("\nImpostazioni della sfida:"))
            params = lichess_app.get_game_params(for_seek=False, for_bot=False)
            print(_("\nInvio sfida in corso..."))
            resp = lichess_app.challenge_user(token, username, params)
            if resp and "challenge" in resp:
                challenge_id = resp["challenge"]["id"]
                print(_("Sfida inviata! In attesa che l'avversario accetti..."))
                import time

                timeout = 60
                start_time = time.time()
                game_started = False
                while time.time() - start_time < timeout:
                    print(
                        _("In attesa... ({t}s rimanenti)").format(
                            t=int(timeout - (time.time() - start_time))
                        ),
                        end="\r",
                    )
                    active = lichess_app.get_active_games(token)
                    for game in active:
                        if game.get("gameId") == challenge_id:
                            print(_("\nSfida accettata!"))
                            from . import lichess_board

                            lichess_board.play_game(
                                challenge_id, token, secrets.get("lichess_username")
                            )
                            game_started = True
                            break
                    if game_started:
                        break
                    time.sleep(5)

                if not game_started:
                    print(
                        _(
                            "\nL'avversario non ha accettato la sfida in tempo (oppure e' offline)."
                        )
                    )
                    try:
                        import urllib.request

                        req = urllib.request.Request(
                            f"https://lichess.org/api/challenge/{challenge_id}/cancel",
                            method="POST",
                        )
                        req.add_header("Authorization", f"Bearer {token}")
                        urllib.request.urlopen(req)
                    except Exception:
                        pass
        elif scelta == "segui":
            follow_player(username, token, follow=True)
            if profile:
                profile["following"] = True
        elif scelta == "smetti":
            follow_player(username, token, follow=False)
            if profile:
                profile["following"] = False
        elif scelta == "scarica":
            download_games(username, token)


def run_profiler(secrets):
    while True:
        print(_("\n=== RICERCA GIOCATORE (PROFILATORE) ==="))
        username = search_player()
        if not username:
            break

        show_player_menu(username, secrets)
