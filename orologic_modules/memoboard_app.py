# Orologic, Memoboard: esercizi di memoria sulla scacchiera.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

# MEMOBOARD - Il tuo assistente per giocare a scacchi senza scacchiera.
# Born on monday, may 6th, 2024 by Gabriele Battaglia IZ4APU.
# June 28th, 2024: moved on Github
# Fuso in Orologic il 29 Maggio 2026.

import datetime
import json
import os
import random
import statistics
import time

from GBUtils import Acusticator, dgt, key, menu

from . import config, localizzazione, storage, strato, tempo
from .config import _

# COSTANTI
READING_TIME = (
    0.8  # Tempo di lettura delle domande in secondi, da parte della sintesi vocale
)
SCORES_FILE = config.percorso_salvataggio(
    os.path.join("settings", "memoboard_scores.json")
)
FREQ_START, FREQ_END = 130.81, 4186.01  # C3 (130.81 Hz) a C8 (4186.01 Hz)
PAN_START, PAN_END = -1.0, 1.0
AUDIO_BAR_DUR = 0.025
MIN_REPETITIONS_FOR_LEADERBOARD = (
    20  # Domande minime per qualificare la sessione nei giochi singoli
)
MAX_LEADERBOARD_ENTRIES = 10  # Numero massimo di posizioni in classifica
# L'andamento per quarti si mostra da qui in su: con meno domande un quarto
# ne ha una o due, e il confronto e' rumore.
MINIMO_PER_I_QUARTI = 20

mnu = {
    "cavalli": _("Esercizio con i salti di cavallo"),
    "alfieri": _("Esercizio con le diagonali"),
    "colori": _("Questa casa è bianca o nera?"),
    "mista": _("Affronta la sfida mista da 100 domande!"),
    "classifiche": _("Mostra la classifica"),
    ".": _("per tornare ad Orologic"),
}


# Le case si elencano in ordine: prima nascevano da un insieme, quindi
# in ordine diverso a ogni avvio. Non cambiava nulla all'uso, perche' si
# pescano a sorte, ma rendeva gli esercizi non ripetibili.
board = [f"{colonna}{traversa}" for traversa in "12345678" for colonna in "ABCDEFGH"]


def _diagonali():
    """Tutte le diagonali di almeno due case, col nome della prima e
    dell'ultima, dalla traversa piu' bassa. Prima erano scritte a mano,
    ed erano 14 su 26: mancavano quelle che partono dalle colonne A e H
    sopra la prima traversa, come A2-G8, e Prox poteva dare per no due
    case che sono sulla stessa diagonale, come B3 e D5 (23 novembre
    2026)."""
    gruppi = {}
    for casa in board:
        colonna, traversa = ord(casa[0]) - ord("A"), int(casa[1])
        gruppi.setdefault(("sale", colonna - traversa), []).append(casa)
        gruppi.setdefault(("scende", colonna + traversa), []).append(casa)
    return {linea[0] + linea[-1]: linea for linea in gruppi.values() if len(linea) > 1}


diagonals = _diagonali()


def case_dell_alfiere():
    """(prima casa, seconda casa, vero se sono sulla stessa diagonale), per
    l'esercizio degli alfieri e la sfida mista. Prima la casa, a caso fra
    tutte, poi la compagna: sorteggiando prima la diagonale, le quattro da
    due case uscivano nel 15% delle domande e gonfiavano i punteggi (R59)."""
    sq1 = random.choice(board)
    yes = random.choice([True, False])
    if yes:
        compagne = [casa for linea in diagonals.values() if sq1 in linea for casa in linea if casa != sq1]
        sq2 = random.choice(compagne)
    else:
        sq2 = Prox(sq1, "B", range_limit=7)
    return sq1, sq2, yes


def get_column_spelling(col_letter):
    """Ottiene la pronuncia fonetica delle colonne da Orologic (config.L10N)."""
    col_lower = col_letter.lower()
    return localizzazione.L10N.get("columns", {}).get(col_lower, col_letter).title()


# --- FUNZIONI GESTIONE PUNTEGGI (JSON) ---


def nette_al_minuto(wins, repetitions, duration):
    """Le giuste nette al minuto: le giuste meno le sbagliate, divise per i
    minuti. E' la misura delle classifiche degli esercizi singoli dal 23
    novembre 2026, al posto dei punti al minuto, che contavano la velocita'
    due volte, nei punti e nella durata, e pesavano poco gli errori: in una
    simulazione Invio a raffica, senza ascoltare, batteva chi rispondeva
    sempre giusto in un secondo. Chi tira a indovinare fa zero (Gabriele)."""
    if not duration or duration <= 0:
        return 0.0
    return (wins - (repetitions - wins)) / duration * 60


def _metrica(ex_name):
    """Il campo che ordina la classifica: i punti nella sfida mista, che ha
    sempre cento domande, le giuste nette al minuto negli altri."""
    return "score" if ex_name == "mixed" else "net_per_minute"


def _misura(ex_name, valore):
    """Il valore della misura come si legge: i punti interi, le nette con un
    decimale."""
    return f"{valore:.0f}" if ex_name == "mixed" else f"{valore:.1f}"


def _deduplicate_scores(data):
    """
    Assicura che in ciascun esercizio ogni utente abbia un unico record (il migliore).
    """
    cleaned = {"colors": [], "knights": [], "bishops": [], "mixed": []}
    for ex_name in cleaned:
        ex_list = data.get(ex_name, [])
        metric_key = _metrica(ex_name)
        best_by_user = {}

        for rec in ex_list:
            if not isinstance(rec, dict):
                continue
            # Un record malformato si scarta da solo: prima faceva mettere
            # da parte tutto il file (R58).
            try:
                user = config.maiuscole_nomi(str(rec.get("username", _("Anonimo"))))
                rec["username"] = user
                if metric_key == "net_per_minute" and "net_per_minute" not in rec:
                    # Le classifiche di prima si ricalcolano: ogni voce ha gia'
                    # giuste, domande e durata.
                    rec["net_per_minute"] = nette_al_minuto(rec.get("wins", 0), rec.get("repetitions", 0), rec.get("duration", 0))
                val = float(rec.get(metric_key, 0))
            except (TypeError, ValueError, AttributeError, ZeroDivisionError):
                continue

            if user not in best_by_user or val > float(best_by_user[user].get(metric_key, 0)):
                best_by_user[user] = rec

        sorted_users = sorted(
            best_by_user.values(), key=lambda x: x.get(metric_key, 0), reverse=True
        )[:MAX_LEADERBOARD_ENTRIES]
        cleaned[ex_name] = sorted_users

    return cleaned


def load_scores():
    """
    Carica i punteggi dal file JSON ed elimina eventuali duplicati per utente.
    """
    default_structure = {"colors": [], "knights": [], "bishops": [], "mixed": []}
    if not os.path.exists(SCORES_FILE):
        return default_structure
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return default_structure

        # Se già nel nuovo formato (chiavi di esercizi come liste)
        if any(k in data and isinstance(data[k], list) for k in default_structure):
            for k in default_structure:
                if k in data and isinstance(data[k], list):
                    default_structure[k] = data[k]
            return _deduplicate_scores(default_structure)

        # Altrimenti converti dal vecchio formato { username: { exercise: data } }
        for user, user_exs in data.items():
            if isinstance(user_exs, dict):
                for ex_name, ex_data in user_exs.items():
                    if ex_name in default_structure and isinstance(ex_data, dict):
                        rec = dict(ex_data)
                        rec["username"] = user
                        default_structure[ex_name].append(rec)

        return _deduplicate_scores(default_structure)
    # Un esercizio che va storto non deve far perdere i punteggi.
    except Exception as e:  # noqa: BLE001
        # Senza questo avviso le classifiche sparivano in silenzio: il
        # primo salvataggio successivo le avrebbe cancellate per sempre.
        copia = storage.metti_da_parte(SCORES_FILE)
        print(_("Il file dei punteggi non e' leggibile: {errore}").format(errore=e))
        if copia:
            print(_("L'ho messo da parte come {copia}.").format(copia=copia))
            print(_("Le classifiche ripartono da zero."))
        else:
            # Senza la copia il file resta com'e': prima l'uscita da
            # Memoboard lo copriva con le classifiche vuote (R58).
            _PUNTEGGI["non_letti"] = True
            print(_("Non sono riuscita a metterlo da parte: i punteggi di questa sessione non si salvano."))
        return default_structure


# Il file dei punteggi che non si e' letto e non si e' potuto mettere da
# parte non si sovrascrive (R58).
_PUNTEGGI = {"non_letti": False}


def save_scores(scores_data):
    """
    Salva il dizionario dei punteggi nel file JSON dopo la deduplicazione.
    """
    if _PUNTEGGI["non_letti"]:
        return
    try:
        cleaned_data = _deduplicate_scores(scores_data)
        storage.scrivi_json(SCORES_FILE, cleaned_data, indent=2)
    # Un esercizio che va storto non deve far perdere i punteggi.
    except Exception as e:  # noqa: BLE001
        print(_("Errore nel salvataggio dei punteggi: {e}").format(e=e))


# --- FUNZIONI HELPER ---


def is_knight_move(sq1, sq2):
    """Controlla se due case sono a un salto di cavallo di distanza. Ritorna True o False."""
    if sq1 == sq2:
        return False
    dx = abs(ord(sq1[0]) - ord(sq2[0]))
    dy = abs(ord(sq1[1]) - ord(sq2[1]))
    return {dx, dy} == {1, 2}


def get_square_color(sq):
    """Determina il colore di una casa. Ritorna 'b' per nero o 'w' per bianco."""
    col = ord(sq[0]) - ord("A")
    row = ord(sq[1]) - ord("1")
    return "b" if (col + row) % 2 == 0 else "w"


def Prox(sq, kind, range_limit):
    """Genera una casa vicina a 'sq' che NON sia sulla stessa diagonale (kind='B')
    o a un salto di cavallo (kind='N')."""
    x, y = ord(sq[0]) - 64, ord(sq[1]) - 48
    x1, x2 = max(1, x - range_limit), min(8, x + range_limit)
    y1, y2 = max(1, y - range_limit), min(8, y + range_limit)

    while True:
        psq = chr(random.randint(x1, x2) + 64) + chr(random.randint(y1, y2) + 48)
        if psq == sq:
            continue

        check = False
        if kind == "B":
            found = [k for k, v in diagonals.items() if sq in v]
            for j in found:
                if psq in diagonals[j]:
                    check = True
        else:  # kind == 'N'
            check = is_knight_move(sq, psq)

        if not check:
            break

    return psq


EX_NAME_MAP = {
    "colors": "colori",
    "knights": "cavalli",
    "bishops": "alfieri",
    "mixed": "mista",
}


def compute_time_stats(timeslist, esiti=None):
    """
    Calcola le statistiche sui tempi di risposta:
    - Minimo, massimo, media e mediana: la mediana non risente di una
      distrazione lunga, la media si'
    - Le giuste e le sbagliate, ognuna col suo numero e la sua mediana, se
      esiti dice domanda per domanda se la risposta era giusta
    - Da MINIMO_PER_I_QUARTI domande in su, la suddivisione in quartili
      cronologici con medie e variazioni percentuali (indice di stanchezza)
    """
    if not timeslist:
        return None

    min_t = min(timeslist)
    max_t = max(timeslist)
    avg_t = sum(timeslist) / len(timeslist)
    median_t = statistics.median(timeslist)
    giuste = sbagliate = None
    if esiti is not None and len(esiti) == len(timeslist):
        giuste = [t for t, esatta in zip(timeslist, esiti, strict=True) if esatta]
        sbagliate = [t for t, esatta in zip(timeslist, esiti, strict=True) if not esatta]

    n = len(timeslist)
    quartiles_info = []

    if n >= MINIMO_PER_I_QUARTI:
        chunk_size = n / 4.0
        chunks = []
        for i in range(4):
            start_idx = round(i * chunk_size)
            end_idx = round((i + 1) * chunk_size)
            if start_idx == end_idx:
                end_idx = min(start_idx + 1, n)
            chunk = timeslist[start_idx:end_idx]
            chunks.append((start_idx + 1, end_idx, chunk))

        first_chunk = chunks[0][2]
        q1_avg = sum(first_chunk) / len(first_chunk) if first_chunk else avg_t

        for i, (q_start, q_end, chunk) in enumerate(chunks, 1):
            if chunk:
                q_avg = sum(chunk) / len(chunk)
                pct_var = ((q_avg - q1_avg) / q1_avg) * 100 if q1_avg > 0 else 0
                quartiles_info.append(
                    {
                        "quartile": i,
                        "start_q": q_start,
                        "end_q": q_end,
                        "count": len(chunk),
                        "avg": q_avg,
                        "pct_var": pct_var,
                    }
                )

    return {
        "min": min_t,
        "max": max_t,
        "avg": avg_t,
        "median": median_t,
        "giuste": giuste,
        "sbagliate": sbagliate,
        "quartiles": quartiles_info,
    }


def format_time_stats_string(time_stats):
    if not time_stats:
        return ""

    # Frasi brevi e complete: niente incolonnamenti, niente barre verticali,
    # unita' scritte per esteso perche' la sintesi non legga esse per secondi.
    lines = []
    lines.append(_("Tempi di risposta."))
    lines.append(
        _("Piu' rapida {min:.1f} secondi, piu' lenta {max:.1f} secondi.").format(
            min=time_stats["min"], max=time_stats["max"]
        )
    )
    lines.append(
        _("Media {avg:.1f} secondi, mediana {med:.1f}.").format(
            avg=time_stats["avg"], med=time_stats["median"]
        )
    )
    giuste, sbagliate = time_stats.get("giuste"), time_stats.get("sbagliate")
    if giuste and sbagliate:
        lines.append(
            _(
                "Giuste {g}, mediana {mg:.1f} secondi; sbagliate {s}, mediana {ms:.1f} secondi."
            ).format(
                g=len(giuste),
                mg=statistics.median(giuste),
                s=len(sbagliate),
                ms=statistics.median(sbagliate),
            )
        )

    quartiles = time_stats.get("quartiles", [])
    if quartiles:
        lines.append(_("Andamento nel corso della sessione."))
        for q in quartiles:
            idx = q["quartile"]
            pct_var = q["pct_var"]
            # Una differenza che si legge 0% e' come il primo, non 0% piu' rapido.
            if idx == 1:
                confronto = _("e' il riferimento")
            elif round(pct_var) > 0:
                confronto = _("cioe' {p:.0f}% piu' lento del primo").format(
                    p=pct_var
                )
            elif round(pct_var) < 0:
                confronto = _("cioe' {p:.0f}% piu' rapido del primo").format(
                    p=abs(pct_var)
                )
            else:
                confronto = _("come il primo")
            lines.append(
                _(
                    "Quarto {idx}, domande da {start_q} a {end_q}: media {q_avg:.1f} secondi, {confronto}."
                ).format(
                    idx=idx,
                    start_q=q["start_q"],
                    end_q=q["end_q"],
                    q_avg=q["avg"],
                    confronto=confronto,
                )
            )
    return "\n".join(lines)


def report_and_update_scores(
    all_scores,
    exercise_name,
    rpt,
    score,
    duration,
    wins,
    session_logs=None,
    exercises_played=None,
    save_session_callback=None,
    timeslist=None,
    esiti=None,
):
    """
    Mostra il report della sessione e aggiorna la classifica.
    """
    score_per_minute = (score / duration) * 60 if duration > 0 else 0
    net_per_minute = nette_al_minuto(wins, rpt, duration)
    esattezza = wins / rpt * 100 if rpt > 0 else 0.0
    riga_delle_nette = _("Risposte esatte {p:.0f}%, giuste nette al minuto {n:.1f}.").format(p=esattezza, n=net_per_minute)
    average_time = duration / rpt if rpt > 0 else 0
    ex_label = EX_NAME_MAP.get(exercise_name, exercise_name)

    time_stats = compute_time_stats(timeslist, esiti)
    time_stats_str = format_time_stats_string(time_stats)

    print(_("Risultati Esercizio"))
    print(
        _("Hai ottenuto {wins} risposte corrette su {rpt}.").format(wins=wins, rpt=rpt)
    )
    print(riga_delle_nette)
    print(
        _("Punteggio totale: {score:.0f} in {duration:.1f} secondi.").format(
            score=score, duration=duration
        )
    )
    print(
        _("Performance: {score_per_minute:.0f} punti al minuto.").format(
            score_per_minute=score_per_minute
        )
    )
    if time_stats_str:
        print(time_stats_str)

    if exercises_played is not None and ex_label not in exercises_played:
        exercises_played.append(ex_label)

    # 1. Se le ripetizioni sono inferiori a MIN_REPETITIONS_FOR_LEADERBOARD
    if exercise_name != "mixed" and rpt < MIN_REPETITIONS_FOR_LEADERBOARD:
        print(
            _(
                "\nNota: Per qualificare un punteggio in classifica occorre eseguire almeno {min_rpt} domande (ne hai svolte {rpt})."
            ).format(min_rpt=MIN_REPETITIONS_FOR_LEADERBOARD, rpt=rpt)
        )
        if session_logs is not None:
            date_str = config.format_date_italian()
            log_entry = _(
                "Esercizio '{exercise_name}' ({date_str}):\n"
                "  Risposte corrette: {wins}/{rpt} in {duration:.1f}s. Punti: {score:.0f} (Perf: {score_per_minute:.0f} p/min) - Non qualificato per la classifica (meno di {min_rpt} domande)."
            ).format(
                exercise_name=ex_label,
                date_str=date_str,
                wins=wins,
                rpt=rpt,
                duration=duration,
                score=score,
                score_per_minute=score_per_minute,
                min_rpt=MIN_REPETITIONS_FOR_LEADERBOARD,
            )
            log_entry += "\n  " + riga_delle_nette
            if time_stats_str:
                log_entry += "\n" + time_stats_str
            session_logs.append(log_entry)
            if save_session_callback:
                save_session_callback()
        key(prompt=_("\nPremi un tasto per procedere..."))
        return

    # 2. Verifica qualificazione Top 10
    ranking_metric = _metrica(exercise_name)
    new_performance = score if exercise_name == "mixed" else net_per_minute

    ex_list = all_scores.get(exercise_name, [])
    sorted_ex_list = sorted(
        ex_list, key=lambda x: x.get(ranking_metric, 0), reverse=True
    )

    qualifies = False
    if len(sorted_ex_list) < MAX_LEADERBOARD_ENTRIES:
        qualifies = True
    else:
        worst_score = sorted_ex_list[MAX_LEADERBOARD_ENTRIES - 1].get(ranking_metric, 0)
        if new_performance > worst_score:
            qualifies = True

    new_record_jingle = [
        "c5",
        0.08,
        -0.7,
        config.VOLUME,
        "e5",
        0.08,
        -0.2,
        config.VOLUME,
        "g5",
        0.08,
        0.2,
        config.VOLUME,
        "c6",
        0.15,
        0.7,
        config.VOLUME,
    ]
    no_record_jingle = ["a4", 0.12, 0, config.VOLUME, "e4", 0.20, 0, config.VOLUME]

    username = _("Anonimo")
    if qualifies:
        Acusticator(new_record_jingle, kind=1)
        print(
            _(
                "\n🏆 COMPLIMENTI! Ti sei guadagnato un posto nella Top 10 della classifica! 🏆"
            )
        )
        username = config.maiuscole_nomi(
            dgt(_("Il tuo nome per la classifica: "), kind="s", smax=40)
        )
        if not username:
            username = _("Anonimo")

        new_entry = {
            "username": username,
            "score": score,
            "wins": wins,
            "repetitions": rpt,
            "duration": duration,
            "average_time_per_guess": average_time,
            "score_per_minute": score_per_minute,
            "net_per_minute": net_per_minute,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Cerca se l'utente esiste già in questo esercizio
        existing_index = None
        for i, rec in enumerate(ex_list):
            if rec.get("username", "").strip().lower() == username.lower():
                existing_index = i
                break

        should_save = True
        if existing_index is not None:
            old_record = ex_list[existing_index]
            old_perf = old_record.get(ranking_metric, 0)

            if new_performance > old_perf:
                print(
                    _(
                        "\n🎉 Nuovo record personale per {username}! Precedente: {old_perf}, Attuale: {new_perf}."
                    ).format(
                        username=username,
                        old_perf=_misura(exercise_name, old_perf),
                        new_perf=_misura(exercise_name, new_performance),
                    )
                )
                ex_list[existing_index] = new_entry
            else:
                print(
                    _(
                        "\nHai ottenuto un punteggio inferiore al tuo precedente record ({old_perf} vs {new_perf})."
                    ).format(old_perf=_misura(exercise_name, old_perf), new_perf=_misura(exercise_name, new_performance))
                )
                si_key = _("s")
                answer = key(
                    _(
                        "Vuoi sovrascrivere il tuo record personale con questo punteggio? (s/n): "
                    )
                ).lower()
                if answer == si_key:
                    ex_list[existing_index] = new_entry
                    print(_("Record personale aggiornato con il nuovo punteggio."))
                else:
                    should_save = False
                    print(_("Il vecchio record personale è stato mantenuto."))
        else:
            ex_list.append(new_entry)

        if should_save:
            sorted_updated = sorted(
                ex_list, key=lambda x: x.get(ranking_metric, 0), reverse=True
            )[:MAX_LEADERBOARD_ENTRIES]
            all_scores[exercise_name] = sorted_updated
            save_scores(all_scores)
            print(_("\nRisultato salvato in classifica con successo!"))

        if session_logs is not None:
            date_str = config.format_date_italian()
            log_entry = _(
                "Esercizio '{exercise_name}' per {username} ({date_str}):\n"
                "  Risposte corrette: {wins}/{rpt} in {duration:.1f}s. Punti: {score:.0f}. Performance: {score_per_minute:.0f} p/min. [QUALIFICATO]"
            ).format(
                exercise_name=ex_label,
                username=username,
                date_str=date_str,
                wins=wins,
                rpt=rpt,
                duration=duration,
                score=score,
                score_per_minute=score_per_minute,
            )
            log_entry += "\n  " + riga_delle_nette
            if time_stats_str:
                log_entry += "\n" + time_stats_str
            session_logs.append(log_entry)
    else:
        Acusticator(no_record_jingle, kind=1)
        print(
            _(
                "\nOttima prova! Purtroppo questo punteggio non è sufficiente per entrare nella Top 10."
            )
        )
        if session_logs is not None:
            date_str = config.format_date_italian()
            log_entry = _(
                "Esercizio '{exercise_name}' ({date_str}):\n"
                "  Risposte corrette: {wins}/{rpt} in {duration:.1f}s. Punti: {score:.0f} (Perf: {score_per_minute:.0f} p/min) - Non qualificato."
            ).format(
                exercise_name=ex_label,
                date_str=date_str,
                wins=wins,
                rpt=rpt,
                duration=duration,
                score=score,
                score_per_minute=score_per_minute,
            )
            log_entry += "\n  " + riga_delle_nette
            if time_stats_str:
                log_entry += "\n" + time_stats_str
            session_logs.append(log_entry)

    if save_session_callback:
        save_session_callback()

    key(prompt=_("\nPremi un tasto per procedere..."))


NOMI_ESERCIZI = {
    "knights": _("salti di cavallo"),
    "bishops": _("diagonali"),
    "colors": _("colore delle case"),
    "mixed": _("sfida mista"),
}


def _nome_esercizio(chiave):
    return NOMI_ESERCIZI.get(chiave, chiave)


def _data_parlata(timestamp):
    """Data e ora di un punteggio, in forma leggibile e senza sigle."""
    if not timestamp:
        return _("data sconosciuta")
    try:
        quando = datetime.datetime.fromisoformat(timestamp)
    except (TypeError, ValueError):
        return _("data sconosciuta")
    return config.format_date_italian(quando)


def _durata_parlata(secondi):
    return tempo.parlato(secondi)


def show_leaderboard(all_scores):
    """
    Mostra una classifica dettagliata Top 10.
    """
    if not all_scores or not any(all_scores.values()):
        print(
            _("\nNon ci sono ancora punteggi registrati per mostrare una classifica.")
        )
        key(prompt=_("\nPremi un tasto per tornare al menu..."))
        return

    print(_("\nQuale classifica vorresti vedere?"))
    map_menu_to_db = {
        "cavalli": "knights",
        "alfieri": "bishops",
        "colori": "colors",
        "mista": "mixed",
    }
    menu_options = {
        "cavalli": _("Classifica Esercizio Cavalli"),
        "alfieri": _("Classifica Esercizio Alfieri"),
        "colori": _("Classifica Esercizio Colori"),
        "mista": _("Classifica Sfida Mista"),
    }

    selected_menu = menu(
        d=menu_options, show=True, keyslist=True, ntf=_("Scelta non valida")
    )

    if not selected_menu:
        return

    selected_exercise = map_menu_to_db[selected_menu]
    leaderboard_data = all_scores.get(selected_exercise, [])

    if not leaderboard_data:
        print(
            _(
                "\nNessun punteggio trovato in classifica per l'esercizio '{selected_exercise}'."
            ).format(selected_exercise=selected_exercise)
        )
        key(prompt=_("\nPremi un tasto per tornare al menu..."))
        return

    if selected_exercise == "mixed":
        sorted_leaderboard = sorted(
            leaderboard_data, key=lambda item: item.get("score", 0), reverse=True
        )[:MAX_LEADERBOARD_ENTRIES]

        print(
            _("Classifica {exercise}, ordinata per punteggio totale.").format(
                exercise=_nome_esercizio(selected_exercise)
            )
        )

        for i, item in enumerate(sorted_leaderboard, 1):
            user = item.get("username", _("Anonimo"))
            reps = item.get("repetitions", 0)
            wins = item.get("wins", 0)
            duration = item.get("duration", 0)
            precisione = (wins / reps) * 100 if reps else 0.0
            print(
                _("{pos}. {user}, {score:.0f} punti.").format(
                    pos=i, user=user, score=item.get("score", 0)
                )
            )
            print(
                _(
                    "{pmin:.0f} al minuto, risposte esatte {acc:.0f}%."
                ).format(pmin=item.get("score_per_minute", 0), acc=precisione)
            )
            print(
                _("Media {avg:.1f} secondi, durata {dur}.").format(
                    avg=item.get("average_time_per_guess", 0),
                    dur=_durata_parlata(duration),
                )
            )
            print(
                _("Ottenuto il {data}.").format(
                    data=_data_parlata(item.get("timestamp"))
                )
            )

    else:
        sorted_leaderboard = sorted(
            leaderboard_data,
            key=lambda item: item.get("net_per_minute", 0),
            reverse=True,
        )[:MAX_LEADERBOARD_ENTRIES]

        print(
            _(
                "Classifica {exercise}, ordinata per giuste nette al minuto, almeno venti domande."
            ).format(exercise=_nome_esercizio(selected_exercise))
        )

        for i, item in enumerate(sorted_leaderboard, 1):
            user = item.get("username", _("Anonimo"))
            reps = item.get("repetitions", 0)
            wins = item.get("wins", 0)
            precisione = (wins / reps) * 100 if reps else 0.0
            print(
                _("{pos}. {user}, {nette:.1f} giuste nette al minuto.").format(
                    pos=i, user=user, nette=item.get("net_per_minute", 0)
                )
            )
            print(
                _(
                    "{reps} domande, esatte {acc:.0f}%, media {avg:.1f} secondi."
                ).format(
                    reps=reps, acc=precisione, avg=item.get("average_time_per_guess", 0)
                )
            )
            print(
                _("Ottenuto il {data}.").format(
                    data=_data_parlata(item.get("timestamp"))
                )
            )

    key(prompt=_("\nPremi un tasto per tornare al menu..."))


# --- FUNZIONI DEGLI ESERCIZI ---


def ExKnights(ripetitions):
    """Esercizio sui cavalli"""
    initial_rpt = ripetitions
    score = 0
    wins = 0
    scoretime = 15
    timeex = time.perf_counter()
    timeslist = []
    esiti = []
    scoreslist = []
    errors_list = []
    knight_moves = [
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
    ]

    while ripetitions > 0:
        sq1 = random.choice(board)
        yes = random.choice([True, False])
        if not yes:
            sq2 = Prox(sq1, "N", range_limit=2)
        else:
            x, y = ord(sq1[0]), ord(sq1[1])
            possible_sq2 = []
            for dx, dy in knight_moves:
                new_x, new_y = x + dx, y + dy
                if ord("A") <= new_x <= ord("H") and ord("1") <= new_y <= ord("8"):
                    possible_sq2.append(f"{chr(new_x)}{chr(new_y)}")
            if not possible_sq2:
                continue
            sq2 = random.choice(possible_sq2)

        question_str = _("Mossa di cavallo: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
        print(
            _(
                "\nCavallo: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?"
            ).format(
                sq1_spelling=get_column_spelling(sq1[0]),
                sq1_rank=sq1[1],
                sq2_spelling=get_column_spelling(sq2[0]),
                sq2_rank=sq2[1],
            ),
            end="",
            flush=True,
        )
        time.sleep(READING_TIME)
        # I tasti premuti prima che parta il cronometro, anche durante la
        # pausa di lettura, non rispondono: il secondo Invio di una doppia
        # pressione rispondeva alla domanda dopo, con tempo zero.
        strato.svuota_tastiera()

        now = time.perf_counter()

        user_says_yes = None
        while True:
            s = key()
            if s == "" or s in ("\r", "\n", "enter"):
                user_says_yes = True
                break
            elif s in ("\x1b", "esc"):
                user_says_yes = False
                break

        elapsed_q = time.perf_counter() - now
        timeslist.append(elapsed_q)
        singlescore = max((scoretime - elapsed_q) * 1000, 0)
        correct = user_says_yes == yes
        if correct:
            wins += 1
            score += singlescore
            scoreslist.append(singlescore)
        else:
            errors_list.append(
                {
                    "question": question_str,
                    "user_answer": "y" if user_says_yes else "n",
                    "correct_answer": "y" if yes else "n",
                }
            )

        esiti.append(correct)
        current_rep_index = initial_rpt - ripetitions
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1.0
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress

        # Portamento a 6 semitoni (+6 se corretto, -6 se errato)
        semitone_ratio = (2.0 ** (6.0 / 12.0)) if correct else (2.0 ** (-6.0 / 12.0))
        target_freq = max(20.0, current_freq * semitone_ratio)

        portamento_str = f"{int(current_freq)}.{int(target_freq)}"
        sound_score = [
            portamento_str,
            AUDIO_BAR_DUR * 3.0,
            current_pan,
            config.VOLUME,
        ]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1

    duration = time.perf_counter() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list, esiti


def ExBishops(ripetitions):
    """Esercizio sugli alfieri"""
    initial_rpt = ripetitions
    score = 0
    wins = 0
    scoretime = 15
    timeex = time.perf_counter()
    timeslist = []
    esiti = []
    scoreslist = []
    errors_list = []

    while ripetitions > 0:
        sq1, sq2, yes = case_dell_alfiere()

        question_str = _("Stessa diagonale: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
        print(
            _(
                "\nAlfiere: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?"
            ).format(
                sq1_spelling=get_column_spelling(sq1[0]),
                sq1_rank=sq1[1],
                sq2_spelling=get_column_spelling(sq2[0]),
                sq2_rank=sq2[1],
            ),
            end="",
            flush=True,
        )
        time.sleep(READING_TIME)
        # I tasti premuti prima che parta il cronometro, anche durante la
        # pausa di lettura, non rispondono: il secondo Invio di una doppia
        # pressione rispondeva alla domanda dopo, con tempo zero.
        strato.svuota_tastiera()

        now = time.perf_counter()

        user_says_yes = None
        while True:
            s = key()
            if s == "" or s in ("\r", "\n", "enter"):
                user_says_yes = True
                break
            elif s in ("\x1b", "esc"):
                user_says_yes = False
                break

        elapsed_q = time.perf_counter() - now
        timeslist.append(elapsed_q)
        singlescore = max((scoretime - elapsed_q) * 1000, 0)
        correct = user_says_yes == yes
        if correct:
            wins += 1
            score += singlescore
            scoreslist.append(singlescore)
        else:
            errors_list.append(
                {
                    "question": question_str,
                    "user_answer": "y" if user_says_yes else "n",
                    "correct_answer": "y" if yes else "n",
                }
            )

        esiti.append(correct)
        current_rep_index = initial_rpt - ripetitions
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1.0
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress

        # Portamento a 6 semitoni (+6 se corretto, -6 se errato)
        semitone_ratio = (2.0 ** (6.0 / 12.0)) if correct else (2.0 ** (-6.0 / 12.0))
        target_freq = max(20.0, current_freq * semitone_ratio)

        portamento_str = f"{int(current_freq)}.{int(target_freq)}"
        sound_score = [
            portamento_str,
            AUDIO_BAR_DUR * 3.0,
            current_pan,
            config.VOLUME,
        ]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1

    duration = time.perf_counter() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list, esiti


def ExMixed(ripetitions):
    """
    Esegue una serie di domande di tipo misto.
    """
    initial_rpt = ripetitions
    score = 0
    wins = 0
    scoretime = 15
    timeex = time.perf_counter()
    timeslist = []
    esiti = []
    scoreslist = []
    errors_list = []
    knight_moves = [
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
    ]

    while ripetitions > 0:
        exercise_type = random.choice(["colors", "knights", "bishops"])
        correct = False

        if exercise_type == "colors":
            sq = random.choice(board)
            print(
                _("\nColore per {sq_spelling} {sq_rank}?").format(
                    sq_spelling=get_column_spelling(sq[0]), sq_rank=sq[1]
                ),
                end="",
                flush=True,
            )
            time.sleep(READING_TIME)
            # I tasti premuti prima che parta il cronometro, anche durante la
            # pausa di lettura, non rispondono: il secondo Invio di una doppia
            # pressione rispondeva alla domanda dopo, con tempo zero.
            strato.svuota_tastiera()

            now = time.perf_counter()
            user_says_white = None
            while True:
                s = key()
                if s == "" or s in ("\r", "\n", "enter"):
                    user_says_white = True
                    break
                elif s in ("\x1b", "esc"):
                    user_says_white = False
                    break
            elapsed_q = time.perf_counter() - now
            timeslist.append(elapsed_q)
            singlescore = (scoretime * 1000) - (elapsed_q * 1000)
            singlescore = max(singlescore, 0)

            correct_is_white = get_square_color(sq) == "w"
            correct = user_says_white == correct_is_white
            if correct:
                wins += 1
                score += singlescore
                scoreslist.append(singlescore)
            else:
                errors_list.append(
                    {
                        "question": _("Colore di {sq}").format(sq=sq),
                        "user_answer": _("Bianco") if user_says_white else _("Nero"),
                        "correct_answer": _("Bianco")
                        if correct_is_white
                        else _("Nero"),
                    }
                )

        elif exercise_type == "knights":
            sq1 = random.choice(board)
            yes = random.choice([True, False])
            if not yes:
                sq2 = Prox(sq1, "N", range_limit=2)
            else:
                x, y = ord(sq1[0]), ord(sq1[1])
                possible_sq2 = []
                for dx, dy in knight_moves:
                    new_x, new_y = x + dx, y + dy
                    if ord("A") <= new_x <= ord("H") and ord("1") <= new_y <= ord("8"):
                        possible_sq2.append(f"{chr(new_x)}{chr(new_y)}")
                if not possible_sq2:
                    continue
                sq2 = random.choice(possible_sq2)

            question_str = _("Mossa di cavallo: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
            print(
                _(
                    "\nCavallo: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?"
                ).format(
                    sq1_spelling=get_column_spelling(sq1[0]),
                    sq1_rank=sq1[1],
                    sq2_spelling=get_column_spelling(sq2[0]),
                    sq2_rank=sq2[1],
                ),
                end="",
                flush=True,
            )
            time.sleep(READING_TIME)
            # I tasti premuti prima che parta il cronometro, anche durante la
            # pausa di lettura, non rispondono: il secondo Invio di una doppia
            # pressione rispondeva alla domanda dopo, con tempo zero.
            strato.svuota_tastiera()

            now = time.perf_counter()
            user_says_yes = None
            while True:
                s = key()
                if s == "" or s in ("\r", "\n", "enter"):
                    user_says_yes = True
                    break
                elif s in ("\x1b", "esc"):
                    user_says_yes = False
                    break
            elapsed_q = time.perf_counter() - now
            timeslist.append(elapsed_q)
            singlescore = (scoretime * 1000) - (elapsed_q * 1000)
            singlescore = max(singlescore, 0)

            correct = user_says_yes == yes
            if correct:
                wins += 1
                score += singlescore
                scoreslist.append(singlescore)
            else:
                errors_list.append(
                    {
                        "question": question_str,
                        "user_answer": "y" if user_says_yes else "n",
                        "correct_answer": "y" if yes else "n",
                    }
                )

        elif exercise_type == "bishops":
            sq1, sq2, yes = case_dell_alfiere()

            question_str = _("Stessa diagonale: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
            print(
                _(
                    "\nAlfiere: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?"
                ).format(
                    sq1_spelling=get_column_spelling(sq1[0]),
                    sq1_rank=sq1[1],
                    sq2_spelling=get_column_spelling(sq2[0]),
                    sq2_rank=sq2[1],
                ),
                end="",
                flush=True,
            )
            time.sleep(READING_TIME)
            # I tasti premuti prima che parta il cronometro, anche durante la
            # pausa di lettura, non rispondono: il secondo Invio di una doppia
            # pressione rispondeva alla domanda dopo, con tempo zero.
            strato.svuota_tastiera()

            now = time.perf_counter()
            user_says_yes = None
            while True:
                s = key()
                if s == "" or s in ("\r", "\n", "enter"):
                    user_says_yes = True
                    break
                elif s in ("\x1b", "esc"):
                    user_says_yes = False
                    break
            elapsed_q = time.perf_counter() - now
            timeslist.append(elapsed_q)
            singlescore = (scoretime * 1000) - (elapsed_q * 1000)
            singlescore = max(singlescore, 0)

            correct = user_says_yes == yes
            if correct:
                wins += 1
                score += singlescore
                scoreslist.append(singlescore)
            else:
                errors_list.append(
                    {
                        "question": question_str,
                        "user_answer": "y" if user_says_yes else "n",
                        "correct_answer": "y" if yes else "n",
                    }
                )

        esiti.append(correct)
        current_rep_index = initial_rpt - ripetitions
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1.0
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress

        # Portamento a 6 semitoni (+6 se corretto, -6 se errato)
        semitone_ratio = (2.0 ** (6.0 / 12.0)) if correct else (2.0 ** (-6.0 / 12.0))
        target_freq = max(20.0, current_freq * semitone_ratio)

        portamento_str = f"{int(current_freq)}.{int(target_freq)}"
        sound_score = [
            portamento_str,
            AUDIO_BAR_DUR * 3.0,
            current_pan,
            config.VOLUME,
        ]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1

    duration = time.perf_counter() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list, esiti


def ExColors(ripetitions):
    """Esercizio sui colori delle case"""
    initial_rpt = ripetitions
    score = 0
    wins = 0
    scoretime = 15
    timeex = time.perf_counter()
    timeslist = []
    esiti = []
    scoreslist = []
    errors_list = []

    while ripetitions > 0:
        sq = random.choice(board)
        print(
            _("\nColore per {sq_spelling} {sq_rank}?").format(
                sq_spelling=get_column_spelling(sq[0]), sq_rank=sq[1]
            ),
            end="",
            flush=True,
        )
        time.sleep(READING_TIME)
        # I tasti premuti prima che parta il cronometro, anche durante la
        # pausa di lettura, non rispondono: il secondo Invio di una doppia
        # pressione rispondeva alla domanda dopo, con tempo zero.
        strato.svuota_tastiera()

        now = time.perf_counter()

        user_says_white = None
        while True:
            s = key()
            if s == "" or s in ("\r", "\n", "enter"):
                user_says_white = True
                break
            elif s in ("\x1b", "esc"):
                user_says_white = False
                break

        elapsed_q = time.perf_counter() - now
        timeslist.append(elapsed_q)
        singlescore = max((scoretime - elapsed_q) * 1000, 0)
        correct_is_white = get_square_color(sq) == "w"
        correct = user_says_white == correct_is_white
        if correct:
            wins += 1
            score += singlescore
            scoreslist.append(singlescore)
        else:
            errors_list.append(
                {
                    "question": _("Colore di {sq}").format(sq=sq),
                    "user_answer": _("Bianco") if user_says_white else _("Nero"),
                    "correct_answer": _("Bianco") if correct_is_white else _("Nero"),
                }
            )

        esiti.append(correct)
        current_rep_index = initial_rpt - ripetitions
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1.0
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress

        # Portamento a 6 semitoni (+6 se corretto, -6 se errato)
        semitone_ratio = (2.0 ** (6.0 / 12.0)) if correct else (2.0 ** (-6.0 / 12.0))
        target_freq = max(20.0, current_freq * semitone_ratio)

        portamento_str = f"{int(current_freq)}.{int(target_freq)}"
        sound_score = [
            portamento_str,
            AUDIO_BAR_DUR * 3.0,
            current_pan,
            config.VOLUME,
        ]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1

    duration = time.perf_counter() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list, esiti


def main():
    start_memoboard_time = time.perf_counter()
    session_start_dt = datetime.datetime.now()
    all_scores = load_scores()
    # All'uscita si salva solo se qualcosa e' cambiato (R58).
    punteggi_letti = json.dumps(all_scores, sort_keys=True, default=str)
    session_logs = []
    exercises_played = []
    current_session_filepath = None

    def save_current_session_report():
        nonlocal current_session_filepath
        if not session_logs:
            return
        types_str = "_".join(exercises_played) if exercises_played else "sessione"
        save_dir = config.percorso_salvataggio("txt")
        os.makedirs(save_dir, exist_ok=True)

        timestamp_str = session_start_dt.strftime("%Y%m%d%H%M%S")
        filename = config.sanitize_filename(
            f"Memoboard_{types_str}_{timestamp_str}.txt"
        )
        target_path = os.path.join(save_dir, filename)

        if (
            current_session_filepath
            and current_session_filepath != target_path
            and os.path.exists(current_session_filepath)
        ):
            try:
                os.remove(current_session_filepath)
            # Un esercizio che va storto non deve far perdere i punteggi.
            except Exception:  # noqa: BLE001, S110
                pass
        current_session_filepath = target_path

        endtime = time.perf_counter() - start_memoboard_time
        header = (
            ""
            f"Report Sessione MemoBoard (Orologic V{config.VERSION})\n"
            f"Data e ora: {config.format_date_italian(session_start_dt)}\n"
            "======================================================================\n\n"
        )
        footer = (
            "\n\n======================================================================\n"
            f"Fine sessione MemoBoard. Tempo di esecuzione: {int(endtime / 60)} minuti e {int(endtime % 60)} secondi.\n"
            ""
        )
        report_content = header + "\n\n".join(session_logs) + footer

        try:
            with open(current_session_filepath, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(
                _("\n[Report salvato in: txt/{filename}]").format(
                    filename=os.path.basename(current_session_filepath)
                )
            )
        # Un esercizio che va storto non deve far perdere i punteggi.
        except Exception as e:  # noqa: BLE001
            print(_("Errore durante il salvataggio del report: {e}").format(e=e))

    print(
        _(
            "Benvenuto in MemoBoard.\nIl tuo assistente per giocare a scacchi senza scacchiera.\nQuesta utility ti aiuta a visualizzare la scacchiera e a diventare un giocatore migliore."
        )
    )
    Acusticator(
        [
            "c4",
            0.08,
            0,
            config.VOLUME,
            "e4",
            0.08,
            0,
            config.VOLUME,
            "g4",
            0.1,
            0,
            config.VOLUME,
        ],
        kind=1,
    )

    print(_("\nPronto ad allenarti? Scegli un esercizio dal menu."))

    while True:
        s = menu(d=mnu, ntf=_("Comando non trovato"), show=True, keyslist=True)
        if s == ".":
            break

        elif s == "colori":
            print(
                _(
                    "Indovina il colore della casa.\nRispondi premendo ESC per il nero e INVIO per il bianco."
                )
            )
            rpt = dgt(
                prompt=_(
                    "\nBello! E buona fortuna con i colori, quante domande vuoi fare? "
                ),
                kind="i",
                imin=5,
                imax=300,
            )
            rpt = min(rpt, 300)
            key(prompt=_("Pronto?"))
            print(_(" Inizio"))
            score, _elenco, duration, timeslist, wins, errors_list, esiti = ExColors(rpt)
            if errors_list:
                print(_("I tuoi errori"))
                for err in errors_list:
                    q = err["question"]
                    ua = err["user_answer"]
                    ca = err["correct_answer"]
                    print(
                        _(
                            "> Domanda: {q} | La tua risposta: '{ua}', corretta: '{ca}'"
                        ).format(q=q, ua=ua, ca=ca)
                    )
                key(_("\nPremi un tasto per procedere alla classifica..."))
            report_and_update_scores(
                all_scores,
                "colors",
                rpt,
                score,
                duration,
                wins,
                session_logs,
                exercises_played,
                save_current_session_report,
                timeslist,
                esiti,
            )

        elif s == "cavalli":
            print(
                _(
                    "Indovina se due case sono a un salto di cavallo.\nRispondi premendo INVIO per sì e ESC per no."
                )
            )
            rpt = dgt(
                prompt=_(
                    "\nBene, divertiti con il salto del cavallo, quante domande vuoi fare? "
                ),
                kind="i",
                imin=5,
                imax=300,
            )
            rpt = min(rpt, 300)
            key(prompt=_("Pronto?"))
            print(_(" Inizio"))
            score, _elenco, duration, timeslist, wins, errors_list, esiti = ExKnights(rpt)
            if errors_list:
                print(_("I tuoi errori"))
                for err in errors_list:
                    q = err["question"]
                    ua = _("Sì") if err["user_answer"] == "y" else _("No")
                    ca = _("Sì") if err["correct_answer"] == "y" else _("No")
                    print(
                        _(
                            "> Domanda: {q} | La tua risposta: '{ua}', Corretta: '{ca}'"
                        ).format(q=q, ua=ua, ca=ca)
                    )
                key(_("\nPremi un tasto per procedere alla classifica..."))
            report_and_update_scores(
                all_scores,
                "knights",
                rpt,
                score,
                duration,
                wins,
                session_logs,
                exercises_played,
                save_current_session_report,
                timeslist,
                esiti,
            )

        elif s == "alfieri":
            print(
                _(
                    "Indovina se due case sono sulla stessa diagonale.\nRispondi premendo INVIO per sì e ESC per no."
                )
            )
            rpt = dgt(
                prompt=_(
                    "\nBene, divertiti con l'esercizio dell'alfiere, quante domande vuoi fare? "
                ),
                kind="i",
                imin=5,
                imax=300,
            )
            rpt = min(rpt, 300)
            key(prompt=_("Pronto?"))
            print(_(" Inizio"))
            score, _elenco, duration, timeslist, wins, errors_list, esiti = ExBishops(rpt)
            if errors_list:
                print(_("I tuoi errori"))
                for err in errors_list:
                    q = err["question"]
                    ua = _("Sì") if err["user_answer"] == "y" else _("No")
                    ca = _("Sì") if err["correct_answer"] == "y" else _("No")
                    print(
                        _(
                            "> Domanda: {q} | La tua risposta: '{ua}', Corretta: '{ca}'"
                        ).format(q=q, ua=ua, ca=ca)
                    )
                key(_("\nPremi un tasto per procedere alla classifica..."))
            report_and_update_scores(
                all_scores,
                "bishops",
                rpt,
                score,
                duration,
                wins,
                session_logs,
                exercises_played,
                save_current_session_report,
                timeslist,
                esiti,
            )

        elif s == "classifiche":
            Acusticator(
                [
                    "g4",
                    0.07,
                    -0.5,
                    config.VOLUME,
                    "c5",
                    0.07,
                    0.5,
                    config.VOLUME,
                    "e5",
                    0.1,
                    0,
                    config.VOLUME,
                ],
                kind=1,
            )
            show_leaderboard(all_scores)

        elif s == "mista":
            print(_("\nBenvenuto alla Sfida Mista!"))
            print(
                _(
                    "Saranno presentate 100 domande di tipo casuale (colori, cavalli, alfieri)."
                )
            )
            print(
                _(
                    "Questa è la prova definitiva delle tue abilità e della tua resistenza. Buona fortuna!\nRicorda di rispondere con INVIO per sì/bianco e ESC per no/nero."
                )
            )

            key(prompt=_("Sei pronto per iniziare? Via!"))
            score, _scoreslist, duration, timeslist, wins, errors_list, esiti = ExMixed(100)
            rpt = 100

            print(_("SFIDA MISTA COMPLETATA!"))
            if errors_list:
                print(_("I tuoi errori nella Sfida Mista"))
                for err in errors_list:
                    q = err["question"]
                    ua = err["user_answer"]
                    ca = err["correct_answer"]

                    if ua in ("y", "n"):
                        ua_fmt = _("Sì") if ua == "y" else _("No")
                        ca_fmt = _("Sì") if ca == "y" else _("No")
                        print(
                            _(
                                "> {q} | La tua risposta: '{ua}', Corretta: '{ca}'"
                            ).format(q=q, ua=ua_fmt, ca=ca_fmt)
                        )
                    else:
                        print(
                            _(
                                "> {q} | La tua risposta: '{ua}', Corretta: '{ca}'"
                            ).format(q=q, ua=ua, ca=ca)
                        )

                key(_("\nPremi un tasto per procedere alla classifica..."))
            report_and_update_scores(
                all_scores,
                "mixed",
                rpt,
                score,
                duration,
                wins,
                session_logs,
                exercises_played,
                save_current_session_report,
                timeslist,
                esiti,
            )

    if json.dumps(all_scores, sort_keys=True, default=str) != punteggi_letti:
        save_scores(all_scores)
    Acusticator(
        [
            "g4",
            0.1,
            0,
            config.VOLUME,
            "e4",
            0.08,
            0,
            config.VOLUME,
            "c4",
            0.15,
            0,
            config.VOLUME,
        ],
        kind=1,
        sync=True,
    )
    endtime = time.perf_counter() - start_memoboard_time

    if session_logs:
        save_current_session_report()
        print(
            _(
                "\nMemoBoard terminato. Tempo di esecuzione: {minuti} minuti e {secondi} secondi.\n\tReport salvato in: txt/{filename}. Arrivederci!"
            ).format(
                minuti=int(endtime / 60),
                secondi=int(endtime % 60),
                filename=os.path.basename(current_session_filepath),
            )
        )
    else:
        print(
            _(
                "\nMemoBoard terminato. Tempo di esecuzione: {minuti} minuti e {secondi} secondi. Arrivederci!"
            ).format(minuti=int(endtime / 60), secondi=int(endtime % 60))
        )


if __name__ == "__main__":
    main()
