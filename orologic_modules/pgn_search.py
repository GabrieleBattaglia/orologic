# orologic_modules/pgn_search.py

"""Modulo per la ricerca e l'esplorazione di archivi PGN.

Permette di caricare un archivio PGN multi-partita (da file, URL o appunti),
visualizzare statistiche, applicare filtri interattivi e navigare
un albero delle aperture con statistiche W/D/L per ogni ramo.
"""

import os
import io
import sys
import time
import urllib.request
import urllib.error
import pyperclip
import chess
import chess.pgn
from collections import defaultdict

from GBUtils import dgt, menu, enter_escape, key, polipo
from orologic_modules import board_utils, engine

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    """Entry point principale, chiamato dal menu principale di Orologic."""
    print(_("\n=== Ricerca PGN ==="))
    print(_("Caricamento archivio dagli appunti..."))

    games = _carica_archivio()
    if games is None:
        return

    totale = len(games)

    # Validazione minima
    if totale < 20:
        print(
            _("\nAttenzione: l'archivio contiene solo {n} partite (minimo consigliato: 20).").format(
                n=totale
            )
        )
        if not enter_escape(_("Desideri proseguire ugualmente? (INVIO per si', ESC per annullare): ")):
            return

    # Estrai info headers da ogni partita
    info_list = _estrai_info(games)

    # Mostra statistiche generali
    _mostra_statistiche(totale, info_list)
    giocatore_comune = _trova_giocatore_comune(info_list)
    if giocatore_comune:
        print(
            _("\nRilevato giocatore principale: {player} (presente in >=90{pct} delle partite).").format(
                player=giocatore_comune, pct="%"
            )
        )
        print(_("Le statistiche dell'albero saranno relative al suo punteggio (+ = -)."))

    # Loop filtri → albero
    while True:
        indici_filtrati, filtri_attivi = _menu_filtri(games, info_list, totale)
        if indici_filtrati is None:
            # L'utente ha premuto '.' per uscire dai filtri
            break
        _albero_aperture(games, info_list, indici_filtrati, filtri_attivi, totale, giocatore_comune)


# ---------------------------------------------------------------------------
# Caricamento archivio
# ---------------------------------------------------------------------------

def _carica_archivio():
    """Legge appunti, determina sorgente (file/url/testo), parsa partite.

    Returns:
        list[chess.pgn.Game] o None se il caricamento fallisce.
    """
    try:
        clipboard = pyperclip.paste()
    except Exception:
        print(_("Impossibile accedere agli appunti."))
        return None

    if not clipboard or not clipboard.strip():
        print(_("Gli appunti sono vuoti."))
        return None

    clipboard = clipboard.strip().strip('"')
    pgn_text = None

    # Percorso file?
    if os.path.isfile(clipboard):
        print(_("Rilevato percorso file: {path}").format(path=clipboard))
        try:
            with open(clipboard, "r", encoding="utf-8", errors="replace") as f:
                pgn_text = f.read()
        except Exception as e:
            print(_("Errore nella lettura del file: {e}").format(e=e))
            return None

    # URL?
    elif clipboard.lower().startswith("http"):
        print(_("Rilevato URL: {url}").format(url=clipboard))
        try:
            req = urllib.request.Request(
                clipboard,
                headers={"User-Agent": "Orologic PGN Search"},
            )
            # Aggiungi token Lichess se presente
            token = None
            try:
                from orologic_modules.config import percorso_salvataggio
                import json
                secrets_path = percorso_salvataggio(os.path.join("settings", "secrets.json"))
                if os.path.exists(secrets_path):
                    with open(secrets_path, "r", encoding="utf-8") as f:
                        secrets = json.load(f)
                        token = secrets.get("lichess_token")
            except Exception:
                pass
            if token and "lichess.org" in clipboard.lower():
                req.add_header("Authorization", f"Bearer {token}")

            with urllib.request.urlopen(req, timeout=30) as resp:
                # Scarica a blocchi di 64KB per mostrare il progresso ed evitare freeze
                chunk_size = 65536
                data = []
                downloaded = 0
                last_download_print = 0.0
                start_time = time.time()
                while True:
                    # Controllo tasto ESC per interruzione manuale
                    if os.name == 'nt':
                        import msvcrt
                        if msvcrt.kbhit():
                            ch = msvcrt.getwch()
                            if ch == "\x1b":
                                sys.stdout.write("\n")
                                print(_("Scaricamento interrotto dall'utente. Elaborazione delle partite caricate finora..."))
                                break

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    data.append(chunk)
                    downloaded += len(chunk)
                    
                    now = time.time()
                    elapsed = now - start_time
                    if elapsed > 3600.0:  # Timeout di 60 minuti (3600 secondi)
                        sys.stdout.write("\n")
                        print(_("Tempo massimo di scaricamento (60 minuti) raggiunto. Elaborazione delle partite caricate finora..."))
                        break
                    
                    if now - last_download_print >= 0.5:
                        mb = downloaded / (1024 * 1024)
                        sys.stdout.write(_("\rScaricamento in corso: {mb:.2f} MB ({elapsed:.0f}s)...\r").format(mb=mb, elapsed=elapsed))
                        sys.stdout.flush()
                        last_download_print = now
                if downloaded > 0:
                    sys.stdout.write("\n")
                pgn_text = b"".join(data).decode("utf-8", errors="replace")
        except Exception as e:
            sys.stdout.write("\n")
            if isinstance(e, urllib.error.HTTPError):
                print(_("Errore HTTP durante il download: {code} {reason}").format(code=e.code, reason=e.reason))
            else:
                print(_("Errore nel download: {e}").format(e=e))
            return None

    # Testo PGN diretto
    else:
        pgn_text = clipboard

    if not pgn_text or not pgn_text.strip():
        print(_("Nessun contenuto PGN trovato."))
        return None

    # Pre-check per evitare di interpretare testo casuale non PGN
    clean_text = pgn_text.strip()
    if "[" not in clean_text and "1." not in clean_text:
        print(_("Il testo negli appunti non sembra contenere dati PGN validi."))
        return None

    # Parsing partite
    print(_("Analisi del PGN in corso..."))
    games = []
    pgn_io = io.StringIO(pgn_text)
    count = 0
    excluded_count = 0
    last_print = 0.0

    while True:
        try:
            game = chess.pgn.read_game(pgn_io)
        except Exception:
            continue
        if game is None:
            break

        count += 1

        # Filtra record spazzatura che non hanno né mosse né header significativi
        has_real_headers = False
        for val in game.headers.values():
            if val not in ("?", "*", "????.??.??"):
                has_real_headers = True
                break
        has_moves = len(list(game.mainline_moves())) > 0
        if not has_real_headers and not has_moves:
            continue

        # Escludi varianti non standard (Setup/FEN personalizzato e Chess960)
        is_setup = game.headers.get("SetUp") == "1"
        is_chess960 = game.headers.get("Variant", "").lower() in ("chess960", "fischerandom", "fischer random")

        is_non_standard = False
        if is_setup:
            fen = game.headers.get("FEN", "").strip()
            if fen:
                normalized_fen = " ".join(fen.split()[:4]).lower()
                standard_normalized = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -".lower()
                if normalized_fen != standard_normalized:
                    is_non_standard = True

        if is_chess960 or is_non_standard:
            excluded_count += 1
            continue

        games.append(game)

        now = time.time()
        if now - last_print >= 3.0:
            sys.stdout.write(_("\rPartite caricate: {n}...").format(n=count))
            sys.stdout.flush()
            last_print = now

    if last_print > 0.0:
        sys.stdout.write("\n")

    if not games:
        print(_("Nessuna partita valida trovata nel PGN."))
        if excluded_count > 0:
            print(
                _("{ex} partite sono state escluse perche' non iniziano dalla posizione standard.").format(ex=excluded_count)
            )
        return None

    if excluded_count > 0:
        total_valid_and_excluded = len(games) + excluded_count
        pct = (excluded_count / total_valid_and_excluded) * 100
        print(
            _(
                "Nota: {ex} partite su {tot} ({pct:.2f}%) sono state escluse perche' non iniziano dalla posizione standard (Setup o Chess960)."
            ).format(ex=excluded_count, tot=total_valid_and_excluded, pct=pct)
        )

    print(_("Caricate {n} partite valide.").format(n=len(games)))
    return games


# ---------------------------------------------------------------------------
# Estrazione info headers
# ---------------------------------------------------------------------------

def _estrai_info(games):
    """Estrae gli headers rilevanti da ogni partita.

    Returns:
        list[dict] con chiavi: White, Black, Result, WhiteElo, BlackElo,
                               Event, Date, Year, ECO
    """
    info_list = []
    for g in games:
        h = g.headers
        year = None
        date_str = h.get("Date", "????.??.??")
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except (ValueError, TypeError):
                pass

        w_elo = None
        b_elo = None
        try:
            w_elo = int(h.get("WhiteElo", ""))
        except (ValueError, TypeError):
            pass
        try:
            b_elo = int(h.get("BlackElo", ""))
        except (ValueError, TypeError):
            pass

        info_list.append({
            "White": h.get("White", "?"),
            "Black": h.get("Black", "?"),
            "Result": h.get("Result", "*"),
            "WhiteElo": w_elo,
            "BlackElo": b_elo,
            "Event": h.get("Event", "?"),
            "Date": date_str,
            "Year": year,
            "ECO": h.get("ECO", ""),
        })
    return info_list


# ---------------------------------------------------------------------------
# Statistiche
# ---------------------------------------------------------------------------

def _calcola_wdl(info_list, indici):
    """Calcola percentuali vittoria bianco / patta / nero.

    Returns:
        (pct_white, pct_draw, pct_black, n_other) — percentuali su totale indici
    """
    w = d = b = other = 0
    for i in indici:
        r = info_list[i]["Result"]
        if r == "1-0":
            w += 1
        elif r == "1/2-1/2":
            d += 1
        elif r == "0-1":
            b += 1
        else:
            other += 1
    tot = len(indici)
    if tot == 0:
        return 0.0, 0.0, 0.0, 0
    return (
        w / tot * 100,
        d / tot * 100,
        b / tot * 100,
        other,
    )


def _formato_statistiche(info_list, indici, filtri_attivi, giocatore_comune=None):
    """Calcola le statistiche (assolute o relative al giocatore) e restituisce la stringa formattata."""
    ref_player = None
    if isinstance(filtri_attivi, dict):
        ref_player = filtri_attivi.get("player") or filtri_attivi.get("white") or filtri_attivi.get("black")

    if not ref_player:
        ref_player = giocatore_comune

    if ref_player:
        # Statistiche relative al giocatore cercato: + (vittorie), = (patte), - (sconfitte)
        win = draw = loss = other = 0
        ref = ref_player.lower()
        for i in indici:
            info = info_list[i]
            r = info["Result"]

            # Determina se il giocatore cercato era il bianco o il nero
            is_white = ref in info.get("White", "").lower()
            is_black = ref in info.get("Black", "").lower()

            if r == "1/2-1/2":
                draw += 1
            elif r == "1-0":
                if is_white:
                    win += 1
                elif is_black:
                    loss += 1
                else:
                    other += 1
            elif r == "0-1":
                if is_black:
                    win += 1
                elif is_white:
                    loss += 1
                else:
                    other += 1
            else:
                other += 1

        tot = len(indici)
        if tot == 0:
            return "+0% =0% -0%"
        pw = win / tot * 100
        pd = draw / tot * 100
        pl = loss / tot * 100
        return f"+{pw:.0f}% ={pd:.0f}% -{pl:.0f}%"
    else:
        # Statistiche assolute del bianco e del nero
        w = d = b = other = 0
        for i in indici:
            r = info_list[i]["Result"]
            if r == "1-0":
                w += 1
            elif r == "1/2-1/2":
                d += 1
            elif r == "0-1":
                b += 1
            else:
                other += 1
        tot = len(indici)
        if tot == 0:
            return "B:0% P:0% N:0%"
        pw = w / tot * 100
        pd = d / tot * 100
        pb = b / tot * 100
        return f"B:{pw:.0f}% P:{pd:.0f}% N:{pb:.0f}%"


def _mostra_statistiche(totale, info_list):
    """Stampa le statistiche generali dell'archivio caricato."""
    tutti = list(range(totale))
    pw, pd, pb, other = _calcola_wdl(info_list, tutti)

    w_count = sum(1 for i in tutti if info_list[i]["Result"] == "1-0")
    d_count = sum(1 for i in tutti if info_list[i]["Result"] == "1/2-1/2")
    b_count = sum(1 for i in tutti if info_list[i]["Result"] == "0-1")

    print(_("\n=== Archivio PGN Caricato ==="))
    print(_("Partite totali: {n}").format(n=totale))

    print(_("\n--- Statistiche Risultati ---"))
    print(_("  Vittorie Bianco: {n} ({p:.1f}%)").format(n=w_count, p=pw))
    print(_("  Patte:           {n} ({p:.1f}%)").format(n=d_count, p=pd))
    print(_("  Vittorie Nero:   {n} ({p:.1f}%)").format(n=b_count, p=pb))
    if other > 0:
        print(_("  Altre/ND:        {n} ({p:.1f}%)").format(
            n=other, p=other / totale * 100
        ))

    # Conteggi univoci
    giocatori = set()
    eventi = set()
    anni = set()
    eco = set()
    for info in info_list:
        giocatori.add(info["White"])
        giocatori.add(info["Black"])
        if info["Event"] and info["Event"] != "?":
            eventi.add(info["Event"])
        if info["Year"]:
            anni.add(info["Year"])
        if info["ECO"]:
            eco.add(info["ECO"])

    print(_("\nGiocatori univoci:     {n}").format(n=len(giocatori)))
    print(_("Eventi univoci:        {n}").format(n=len(eventi)))
    if anni:
        print(_("Anni univoci:          {n} ({min} - {max})").format(
            n=len(anni), min=min(anni), max=max(anni)
        ))
    else:
        print(_("Anni univoci:          N/D"))
    print(_("Aperture ECO univoche: {n}").format(n=len(eco)))


def _trova_giocatore_comune(info_list):
    """Trova un giocatore presente in almeno il 90% delle partite (case-insensitive)."""
    if not info_list:
        return None
    counts = defaultdict(int)
    orig_names = {}
    for info in info_list:
        w = info.get("White")
        b = info.get("Black")
        if w:
            wl = w.lower()
            counts[wl] += 1
            orig_names[wl] = w
        if b:
            bl = b.lower()
            counts[bl] += 1
            orig_names[bl] = b

    n_total = len(info_list)
    threshold = int(n_total * 0.9)  # Almeno il 90% delle partite
    for p_lower, count in counts.items():
        if count >= threshold:
            return orig_names[p_lower]
    return None


# ---------------------------------------------------------------------------
# Filtri
# ---------------------------------------------------------------------------

def _menu_filtri(games, info_list, totale):
    """Loop interattivo per impostare filtri.

    Returns:
        (list[int], bool) — (indici partite filtrate, True se ci sono filtri attivi)
        oppure (None, False) se l'utente esce.
    """
    filtri = {}
    from orologic_modules import storage
    db = storage.LoadDB()
    stile_numerato = db.get("menu_numerati", False)

    while True:
        indici = _applica_filtri(info_list, filtri)
        n_filtrate = len(indici)
        pct = (n_filtrate / totale) * 100 if totale > 0 else 0.0

        print(_("\n--- Filtri ---"))
        print(
            _("Partite corrispondenti: {n} di {tot} ({pct:.2f}%)").format(n=n_filtrate, tot=totale, pct=pct)
        )

        # Costruisci menu filtri
        voci = {
            "bianco": _("Giocatore Bianco: [{v}]").format(
                v=filtri.get("white", _("qualsiasi"))
            ),
            "nero": _("Giocatore Nero: [{v}]").format(
                v=filtri.get("black", _("qualsiasi"))
            ),
            "giocatore": _("Giocatore (bianco o nero): [{v}]").format(
                v=filtri.get("player", _("qualsiasi"))
            ),
            "risultato": _("Risultato: [{v}]").format(
                v=filtri.get("result", _("qualsiasi"))
            ),
            "elo_min": _("ELO minimo: [{v}]").format(
                v=filtri.get("elo_min", _("nessun limite"))
            ),
            "elo_max": _("ELO massimo: [{v}]").format(
                v=filtri.get("elo_max", _("nessun limite"))
            ),
            "evento": _("Evento: [{v}]").format(
                v=filtri.get("event", _("qualsiasi"))
            ),
            "anno_dal": _("Anno dal: [{v}]").format(
                v=filtri.get("year_from", _("nessun limite"))
            ),
            "anno_al": _("Anno al: [{v}]").format(
                v=filtri.get("year_to", _("nessun limite"))
            ),
            "eco": _("Codice ECO: [{v}]").format(
                v=filtri.get("eco", _("qualsiasi"))
            ),
            ".": _("Torna al menu' principale (Esci)"),
        }

        scelta = menu(
            voci,
            show=True,
            p=_("\nScegli un filtro o premi INVIO per procedere all'albero: "),
            numbered=stile_numerato,
            empty_enter="procedi",
        )

        if scelta == ".":
            return None, False

        elif scelta is None:
            # Tasto ESC -> Azzera filtri
            filtri.clear()
            print(_("Tutti i filtri sono stati rimossi (azzerati)."))
            continue

        elif scelta == "procedi":
            # Tasto INVIO su input vuoto -> Procedi
            return indici, filtri

        elif scelta == "bianco":
            v = dgt(_("Nome giocatore Bianco (vuoto=qualsiasi): "), kind="s", smin=0)
            filtri["white"] = v if v else None
            if not v and "white" in filtri:
                del filtri["white"]

        elif scelta == "nero":
            v = dgt(_("Nome giocatore Nero (vuoto=qualsiasi): "), kind="s", smin=0)
            filtri["black"] = v if v else None
            if not v and "black" in filtri:
                del filtri["black"]

        elif scelta == "giocatore":
            v = dgt(_("Nome giocatore (cerca in bianco E nero, vuoto=qualsiasi): "), kind="s", smin=0)
            filtri["player"] = v if v else None
            if not v and "player" in filtri:
                del filtri["player"]

        elif scelta == "risultato":
            r_voci = {
                "1-0": _("Vittoria Bianco (1-0)"),
                "0-1": _("Vittoria Nero (0-1)"),
                "1/2-1/2": _("Patta (1/2-1/2)"),
                "qualsiasi": _("Qualsiasi risultato"),
            }
            r = menu(r_voci, show=True, p=_("Scegli risultato: "), numbered=stile_numerato)
            if r and r != "." and r != "qualsiasi":
                filtri["result"] = r
            else:
                if "result" in filtri:
                    del filtri["result"]

        elif scelta == "elo_min":
            v = dgt(_("ELO minimo (0=nessun limite): "), kind="i", imin=0, imax=4000, default=0)
            if v and v > 0:
                filtri["elo_min"] = v
            elif "elo_min" in filtri:
                del filtri["elo_min"]

        elif scelta == "elo_max":
            v = dgt(_("ELO massimo (0=nessun limite): "), kind="i", imin=0, imax=4000, default=0)
            if v and v > 0:
                filtri["elo_max"] = v
            elif "elo_max" in filtri:
                del filtri["elo_max"]

        elif scelta == "evento":
            v = dgt(_("Nome evento (vuoto=qualsiasi): "), kind="s", smin=0)
            filtri["event"] = v if v else None
            if not v and "event" in filtri:
                del filtri["event"]

        elif scelta == "anno_dal":
            v = dgt(_("Anno dal (0=nessun limite): "), kind="i", imin=0, imax=2100, default=0)
            if v and v > 0:
                filtri["year_from"] = v
            elif "year_from" in filtri:
                del filtri["year_from"]

        elif scelta == "anno_al":
            v = dgt(_("Anno al (0=nessun limite): "), kind="i", imin=0, imax=2100, default=0)
            if v and v > 0:
                filtri["year_to"] = v
            elif "year_to" in filtri:
                del filtri["year_to"]

        elif scelta == "eco":
            v = dgt(_("Codice ECO (es. 'B', 'B90', vuoto=qualsiasi): "), kind="s", smin=0)
            filtri["eco"] = v.upper() if v else None
            if not v and "eco" in filtri:
                del filtri["eco"]


def _applica_filtri(info_list, filtri):
    """Applica i filtri correnti e restituisce gli indici delle partite valide.

    Returns:
        list[int]
    """
    indici = []
    for i, info in enumerate(info_list):
        # Filtro giocatore bianco
        fw = filtri.get("white")
        if fw and fw.lower() not in info["White"].lower():
            continue

        # Filtro giocatore nero
        fb = filtri.get("black")
        if fb and fb.lower() not in info["Black"].lower():
            continue

        # Filtro giocatore bidirezionale
        fp = filtri.get("player")
        if fp:
            fp_lower = fp.lower()
            if fp_lower not in info["White"].lower() and fp_lower not in info["Black"].lower():
                continue

        # Filtro risultato
        fr = filtri.get("result")
        if fr and info["Result"] != fr:
            continue

        # Filtro ELO minimo
        elo_min = filtri.get("elo_min")
        if elo_min:
            w_elo = info["WhiteElo"]
            b_elo = info["BlackElo"]
            if w_elo is None and b_elo is None:
                continue
            max_elo = max(e for e in (w_elo, b_elo) if e is not None)
            if max_elo < elo_min:
                continue

        # Filtro ELO massimo
        elo_max = filtri.get("elo_max")
        if elo_max:
            w_elo = info["WhiteElo"]
            b_elo = info["BlackElo"]
            if w_elo is None and b_elo is None:
                continue
            min_elo = min(e for e in (w_elo, b_elo) if e is not None)
            if min_elo > elo_max:
                continue

        # Filtro evento
        fe = filtri.get("event")
        if fe and fe.lower() not in info["Event"].lower():
            continue

        # Filtro anno dal
        yf = filtri.get("year_from")
        if yf:
            if info["Year"] is None or info["Year"] < yf:
                continue

        # Filtro anno al
        yt = filtri.get("year_to")
        if yt:
            if info["Year"] is None or info["Year"] > yt:
                continue

        # Filtro ECO
        feco = filtri.get("eco")
        if feco:
            game_eco = info["ECO"].upper() if info["ECO"] else ""
            if not game_eco.startswith(feco):
                continue

        indici.append(i)

    return indici


# ---------------------------------------------------------------------------
# Albero delle aperture
# ---------------------------------------------------------------------------

def _formatta_sequenza_mosse(mosse):
    """Formatta una lista di mosse SAN in notazione scacchistica standard.
    Es: ['e4', 'e5', 'Nf3'] -> '1. e4 e5 2. Nf3'
    """
    if not mosse:
        return _("(radice)")
    parti = []
    for i, m in enumerate(mosse):
        move_num = (i // 2) + 1
        if i % 2 == 0:
            parti.append(f"{move_num}. {m}")
        else:
            parti.append(m)
    return " ".join(parti)


def _formatta_breadcrumb_compatto(ramo_mosse, mossa_selezionata):
    """Formatta la sequenza di mosse tenendo solo nonno, padre e mossa corrente.
    Esempio: [4... Qa4]<5. Bd7> ...Qb3:
    """
    seq = ramo_mosse + [mossa_selezionata]
    L = len(seq)

    grand_str = ""
    if L >= 3:
        idx = L - 3
        num = (idx // 2) + 1
        m = seq[idx]
        grand_str = f"[{num}. {m}]" if idx % 2 == 0 else f"[{num}... {m}]"

    parent_str = ""
    if L >= 2:
        idx = L - 2
        num = (idx // 2) + 1
        m = seq[idx]
        parent_str = f"<{num}. {m}>" if idx % 2 == 0 else f"<{num}... {m}>"

    idx = L - 1
    num = (idx // 2) + 1
    m = seq[idx]
    current_str = f"{num}. {m}:" if idx % 2 == 0 else f"...{m}:"

    parts = []
    if grand_str:
        parts.append(grand_str)
    if parent_str:
        parts.append(parent_str)

    prefix = "".join(parts)
    if prefix:
        return f"{prefix} {current_str}"
    else:
        return current_str


def _ottieni_scacchiera_ramo(ramo_mosse):
    """Restituisce un CustomBoard (o chess.Board) dopo aver eseguito le mosse del ramo."""
    board = chess.Board()
    for m in ramo_mosse:
        try:
            board.push_san(m)
        except Exception:
            break
    return board


def _albero_aperture(games, info_list, indici_filtrati, filtri_attivi, totale_archivio, giocatore_comune=None):
    """Navigazione interattiva dell'albero delle aperture con tasti WASD-like."""

    indici_originali = indici_filtrati  # set filtrato immutabile
    ramo_mosse = []  # stack di mosse SAN che formano il ramo corrente
    selezione = 0  # indice del ramo attualmente selezionato
    must_print_list = True

    while True:
        # Ricalcola la scacchiera del ramo ad ogni iterazione
        board_ramo = _ottieni_scacchiera_ramo(ramo_mosse)

        # Ricalcola sempre gli indici correnti dal set originale + ramo
        indici_correnti = _indici_partite_ramo(games, indici_originali, ramo_mosse)

        # Calcola i rami disponibili a questo livello
        rami = _calcola_rami(games, indici_originali, ramo_mosse, info_list)

        if not rami:
            print(_("\nNessuna mossa disponibile a questo livello."))
            if ramo_mosse:
                ramo_mosse.pop()
                must_print_list = True
                continue
            else:
                break

        # Se c'è un solo ramo con una sola partita, vai direttamente all'analisi
        if len(rami) == 1 and len(rami[0][1]) == 1:
            print(
                _("\nUna sola partita rimasta nel ramo. Passaggio all'analisi...")
            )
            _avvia_analisi(games[rami[0][1][0]])
            break

        # Assicura selezione valida
        if selezione >= len(rami):
            selezione = 0

        # Mostra la lista solo se richiesto (es: cambio livello, aiuto, repeat)
        if must_print_list:
            # Mostra ramo corrente e statistiche
            _stampa_ramo_corrente(ramo_mosse, indici_correnti, info_list, filtri_attivi, giocatore_comune)
            # Mostra rami disponibili
            _stampa_lista_rami(rami, board_ramo, info_list, filtri_attivi, giocatore_comune)
            must_print_list = False

        # Costruisci il breadcrumb compatto
        prompt_str = _formatta_breadcrumb_compatto(ramo_mosse, rami[selezione][0])

        # Calcola statistiche per il ramo potenziale selezionato
        n_part = len(rami[selezione][1])
        stats_str = _formato_statistiche(info_list, rami[selezione][1], filtri_attivi, giocatore_comune)

        # Prompt con \r all'inizio e alla fine, con padding per pulire residui
        raw_prompt = f"{prompt_str} | {n_part} part. | {stats_str} | Azione: "
        prompt = f"\r{raw_prompt.ljust(75)}\r"

        tasto = key(prompt)

        # Se non è una navigazione semplice (w/x), stampa a capo per evitare sovrapposizioni
        if tasto not in ("w", "x"):
            print()

        if tasto == ".":
            # Torna al menu filtri
            break

        elif tasto == "?":
            _mostra_aiuto()
            must_print_list = True

        elif tasto == "t":
            must_print_list = True
            continue

        elif tasto == "w":
            # Ramo precedente
            selezione = (selezione - 1) % len(rami)

        elif tasto == "x":
            # Ramo successivo
            selezione = (selezione + 1) % len(rami)

        elif tasto == "d":
            # Scendi nel ramo selezionato
            mossa_san = rami[selezione][0]
            ramo_mosse.append(mossa_san)
            selezione = 0
            must_print_list = True

        elif tasto == "a":
            # Risali di un livello
            if ramo_mosse:
                ramo_mosse.pop()
                selezione = 0
                must_print_list = True
            else:
                # Alla radice, torna ai filtri
                break

        elif tasto == "0":
            # Sfoglia partite del ramo corrente
            _sfoglia_partite(games, indici_correnti, ramo_mosse, info_list)
            must_print_list = True

        elif tasto == "s":
            # Salva PGN filtrato
            _salva_pgn_filtrato(games, indici_correnti, filtri_attivi)
            must_print_list = True

        elif tasto in "123456789":
            n = int(tasto)
            if 1 <= n <= len(rami):
                mossa_san = rami[n - 1][0]
                ramo_mosse.append(mossa_san)
                selezione = 0
                must_print_list = True
            else:
                print(_("Numero non valido."))
                must_print_list = True

        # Se dopo la discesa c'è una sola partita, analisi diretta
        if ramo_mosse:
            partite_correnti = _indici_partite_ramo(games, indici_originali, ramo_mosse)
            if len(partite_correnti) == 1:
                print(
                    _("\nUna sola partita rimasta nel ramo. Passaggio all'analisi...")
                )
                _avvia_analisi(games[partite_correnti[0]])
                ramo_mosse.pop()
                must_print_list = True


def _calcola_rami(games, indici, ramo_mosse, info_list):
    """Calcola le mosse disponibili al livello corrente dell'albero.

    Returns:
        list di tuple (mossa_san, list_indici, pct_w, pct_d, pct_b)
        ordinata per numero di partite decrescente.
    """
    rami_dict = defaultdict(list)  # mossa_san -> [indici]

    for idx in indici:
        game = games[idx]
        node = game
        # Naviga fino alla profondità richiesta
        match = True
        for depth, target_move in enumerate(ramo_mosse):
            found = False
            for variation in node.variations:
                san = node.board().san(variation.move)
                if san == target_move:
                    node = variation
                    found = True
                    break
            if not found:
                match = False
                break

        if not match:
            continue

        # Ora siamo al livello giusto: raccogliamo le mosse disponibili
        for variation in node.variations:
            san = node.board().san(variation.move)
            rami_dict[san].append(idx)

    # Ordina per frequenza e aggiungi statistiche W/D/L
    rami = []
    for mossa, idx_list in rami_dict.items():
        pw, pd, pb, _other = _calcola_wdl(info_list, idx_list)
        rami.append((mossa, idx_list, pw, pd, pb))

    rami.sort(key=lambda x: len(x[1]), reverse=True)
    return rami


def _indici_partite_ramo(games, indici, ramo_mosse):
    """Restituisce gli indici delle partite che contengono il ramo specificato."""
    if not ramo_mosse:
        return indici

    risultato = []
    for idx in indici:
        game = games[idx]
        node = game
        match = True
        for target_move in ramo_mosse:
            found = False
            for variation in node.variations:
                san = node.board().san(variation.move)
                if san == target_move:
                    node = variation
                    found = True
                    break
            if not found:
                match = False
                break
        if match:
            risultato.append(idx)
    return risultato


def _ricalcola_indici_ramo(games, indici_base, ramo_mosse):
    """Ricalcola gli indici partendo da indici_base e filtrando per il ramo."""
    return _indici_partite_ramo(games, indici_base, ramo_mosse)


def _stampa_ramo_corrente(ramo_mosse, indici, info_list, filtri_attivi, giocatore_comune=None):
    """Stampa il breadcrumb del ramo corrente con statistiche."""
    if not ramo_mosse:
        breadcrumb = _("(radice)")
    else:
        # Costruisci breadcrumb con numerazione mosse
        parti = []
        for i, mossa in enumerate(ramo_mosse):
            move_num = (i // 2) + 1
            if i % 2 == 0:
                parti.append("{n}. {m}".format(n=move_num, m=mossa))
            else:
                parti.append("{n}... {m}".format(n=move_num, m=mossa))
        breadcrumb = " > ".join(parti)

    stats_str = _formato_statistiche(info_list, indici, filtri_attivi, giocatore_comune)
    print(
        _("\nRamo: {ramo} | {n} partite | {stats}").format(
            ramo=breadcrumb, n=len(indici), stats=stats_str
        )
    )


def _stampa_lista_rami(rami, board, info_list, filtri_attivi, giocatore_comune=None):
    """Stampa la lista dei rami disponibili con statistiche."""
    print(_("\nMosse disponibili:"))
    totale = sum(len(r[1]) for r in rami)
    for i, (mossa, idx_list, pw, pd, pb) in enumerate(rami):
        n = len(idx_list)
        pct = n / totale * 100 if totale > 0 else 0

        # Genera la descrizione verbosa della mossa usando DescribeMove
        try:
            move_obj = board.parse_san(mossa)
            desc_mossa = board_utils.DescribeMove(move_obj, board)
        except Exception:
            desc_mossa = mossa

        stats_str = _formato_statistiche(info_list, idx_list, filtri_attivi, giocatore_comune)
        print(
            "  {num}. {mossa_verbose} ({mossa_san}) ({n} partite) = {pct:.1f}% | {stats}".format(
                num=i + 1, mossa_verbose=desc_mossa, mossa_san=mossa, n=n, pct=pct, stats=stats_str
            )
        )


def _mostra_aiuto():
    """Mostra la mappa dei tasti per la navigazione dell'albero."""
    print(_("\n--- Aiuto Navigazione Albero ---"))
    print(_("  w = Ramo precedente (su)"))
    print(_("  x = Ramo successivo (giu')"))
    print(_("  d = Scendi nel ramo selezionato"))
    print(_("  a = Risali di un livello"))
    print(_("  1-9 = Seleziona direttamente un ramo"))
    print(_("  0 = Sfoglia le partite del ramo corrente"))
    print(_("  s = Salva PGN con le partite filtrate"))
    print(_("  t = Ripeti informazioni ramo corrente"))
    print(_("  ? = Questo aiuto"))
    print(_("  . = Esci dall'albero"))


# ---------------------------------------------------------------------------
# Pager partite
# ---------------------------------------------------------------------------

def _sfoglia_partite(games, indici, ramo_mosse, info_list):
    """Mostra le partite del ramo corrente nel pager menu().

    Le partite vengono formattate con bianco, nero, risultato e
    mosse di continuazione dopo il ramo corrente.
    """
    print()  # Ritorno a capo per pulire la riga del prompt precedente

    partite_ramo = _indici_partite_ramo(games, indici, ramo_mosse)

    if not partite_ramo:
        print(_("Nessuna partita nel ramo corrente."))
        return

    # Costruisci le voci del menu
    voci = {}
    voci_mapping = {}
    for i, idx in enumerate(partite_ramo):
        info = info_list[idx]
        game = games[idx]

        # Ottieni mosse di continuazione dopo il ramo
        continuazione = _mosse_continuazione(game, ramo_mosse, max_mosse=5)

        # Chiave univoca basata sui giocatori per ordinamento e selezione
        chiave = "{w} vs {b} ({num})".format(
            w=info["White"], b=info["Black"], num=i + 1
        )

        valore = info["Result"]
        if continuazione:
            valore += ", " + continuazione

        voci[chiave] = valore
        voci_mapping[chiave] = game

    scelta = menu(
        voci,
        show=True,
        p=_("\nScegli una partita (. per tornare): "),
        numbered=False,
    )

    if scelta and scelta != ".":
        game_scelto = voci_mapping.get(scelta)
        if game_scelto:
            _avvia_analisi(game_scelto)


def _mosse_continuazione(game, ramo_mosse, max_mosse=5):
    """Restituisce le mosse di continuazione dopo il ramo come stringa SAN.

    Es: '2... Nc6 3. Bb5 a6 4. Ba4'
    """
    node = game
    # Naviga fino al punto del ramo
    for target_move in ramo_mosse:
        found = False
        for variation in node.variations:
            san = node.board().san(variation.move)
            if san == target_move:
                node = variation
                found = True
                break
        if not found:
            return ""

    # Raccogli le mosse successive
    parti = []
    count = 0
    while node.variations and count < max_mosse:
        board = node.board()
        next_node = node.variations[0]
        san = board.san(next_node.move)
        fullmove = board.fullmove_number
        if board.turn == chess.WHITE:
            parti.append("{n}. {m}".format(n=fullmove, m=san))
        else:
            if not parti:
                parti.append("{n}... {m}".format(n=fullmove, m=san))
            else:
                parti.append(san)
        node = next_node
        count += 1

    return " ".join(parti)


# ---------------------------------------------------------------------------
# Salvataggio PGN filtrato
# ---------------------------------------------------------------------------

def _salva_pgn_filtrato(games, indici, filtri_attivi):
    """Salva su file le partite che passano i filtri correnti.

    Se non ci sono filtri attivi avvisa l'utente che sarebbe una copia
    dell'archivio originale.
    """
    if not filtri_attivi:
        print(
            _("\nAttenzione: non ci sono filtri attivi. "
              "Il file salvato sarebbe una copia dell'archivio originale.")
        )
        if not enter_escape(
            _("Desideri procedere ugualmente? (INVIO per si', ESC per annullare): ")
        ):
            return

    if not indici:
        print(_("Nessuna partita da salvare."))
        return

    nome = dgt(
        _("Nome del file da salvare (senza estensione): "),
        kind="s",
        smin=1,
        smax=200,
    )
    if not nome:
        return

    # Aggiungi estensione .pgn se non presente
    if not nome.lower().endswith(".pgn"):
        nome += ".pgn"

    # Salva nella cartella pgn del progetto o nella cwd
    percorso = os.path.join(os.getcwd(), nome)

    try:
        with open(percorso, "w", encoding="utf-8") as f:
            for i, idx in enumerate(indici):
                game = games[idx]
                exporter = chess.pgn.StringExporter(
                    headers=True, variations=True, comments=True
                )
                pgn_str = game.accept(exporter)
                f.write(str(pgn_str))
                f.write("\n\n")

        print(
            _("Salvate {n} partite in: {path}").format(n=len(indici), path=percorso)
        )
    except Exception as e:
        print(_("Errore nel salvataggio: {e}").format(e=e))


# ---------------------------------------------------------------------------
# Analisi
# ---------------------------------------------------------------------------

def _avvia_analisi(game):
    """Gestisce il passaggio di una partita all'analisi (automatica o manuale)."""
    print(_("\n--- Partita selezionata ---"))
    for k, v in game.headers.items():
        if v and v != "?" and v != "????.??.??":
            print("  {k}: {v}".format(k=k, v=v))

    # Controlla che il motore sia disponibile
    if engine.ENGINE is None and not engine.InitEngine():
        if enter_escape(
            _(
                "Il motore scacchistico non e' configurato. Vuoi configurarlo ora? "
                "(INVIO per si', ESC per no): "
            )
        ):
            engine.MenuMotore()
        if engine.ENGINE is None and not engine.InitEngine():
            print(_("Impossibile inizializzare il motore. Analisi annullata."))
            return

    engine.cache_analysis.clear()

    if enter_escape(
        _("Desideri l'analisi automatica? (INVIO per si', ESC per manuale): ")
    ):
        engine.AnalisiAutomatica(board_utils.CopyPgnGame(game))
    else:
        engine.AnalyzeGame(game, is_corrected=False)
