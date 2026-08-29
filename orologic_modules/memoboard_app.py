# MEMOBOARD - Il tuo assistente per giocare a scacchi senza scacchiera.
# Born on monday, may 6th, 2024 by Gabriele Battaglia IZ4APU.
# June 28th, 2024: moved on Github
# Fuso in Orologic il 29 Maggio 2026.

import datetime
import json
import os
import random
import time

from GBUtils import Acusticator, dgt, key, menu

from . import config
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

mnu = {
    "cavalli": _("Esercizio con i salti di cavallo"),
    "alfieri": _("Esercizio con le diagonali"),
    "colori": _("Questa casa è bianca o nera?"),
    "mista": _("Affronta la sfida mista da 100 domande!"),
    "classifiche": _("Mostra la classifica"),
    ".": _("per tornare ad Orologic"),
}


board_set = set()
for y in "12345678":
    for x in "ABCDEFGH":
        board_set.add(f"{x}{y}")
board = list(board_set)

diagonals = {
    "A1H8": ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8"],
    "B1H7": ["B1", "C2", "D3", "E4", "F5", "G6", "H7"],
    "C1H6": ["C1", "D2", "E3", "F4", "G5", "H6"],
    "D1H5": ["D1", "E2", "F3", "G4", "H5"],
    "E1H4": ["E1", "F2", "G3", "H4"],
    "F1H3": ["F1", "G2", "H3"],
    "G1H2": ["G1", "H2"],
    "B1A2": ["B1", "A2"],
    "C1A3": ["C1", "B2", "A3"],
    "D1A4": ["D1", "C2", "B3", "A4"],
    "E1A5": ["E1", "D2", "C3", "B4", "A5"],
    "F1A6": ["F1", "E2", "D3", "C4", "B5", "A6"],
    "G1A7": ["G1", "F2", "E3", "D4", "C5", "B6", "A7"],
    "H1A8": ["H1", "G2", "F3", "E4", "D5", "C6", "B7", "A8"],
}


def get_column_spelling(col_letter):
    """Ottiene la pronuncia fonetica delle colonne da Orologic (config.L10N)."""
    col_lower = col_letter.lower()
    return config.L10N.get("columns", {}).get(col_lower, col_letter).title()


# --- FUNZIONI GESTIONE PUNTEGGI (JSON) ---


def _deduplicate_scores(data):
    """
    Assicura che in ciascun esercizio ogni utente abbia un unico record (il migliore).
    """
    cleaned = {"colors": [], "knights": [], "bishops": [], "mixed": []}
    for ex_name in cleaned:
        ex_list = data.get(ex_name, [])
        metric_key = "score" if ex_name == "mixed" else "score_per_minute"
        best_by_user = {}

        for rec in ex_list:
            if not isinstance(rec, dict):
                continue
            user = rec.get("username", _("Anonimo")).strip().title()
            rec["username"] = user
            val = rec.get(metric_key, 0)

            if user not in best_by_user or val > best_by_user[user].get(metric_key, 0):
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
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
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
    except Exception:
        return default_structure


def save_scores(scores_data):
    """
    Salva il dizionario dei punteggi nel file JSON dopo la deduplicazione.
    """
    try:
        cleaned_data = _deduplicate_scores(scores_data)
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
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


def compute_time_stats(timeslist):
    """
    Calcola le statistiche sui tempi di risposta:
    - Minimo, massimo e medio
    - Suddivisione in quartili cronologici con medie e variazioni percentuali (indice di stanchezza)
    """
    if not timeslist:
        return None

    min_t = min(timeslist)
    max_t = max(timeslist)
    avg_t = sum(timeslist) / len(timeslist)

    n = len(timeslist)
    quartiles_info = []

    if n >= 4:
        chunk_size = n / 4.0
        chunks = []
        for i in range(4):
            start_idx = int(round(i * chunk_size))
            end_idx = int(round((i + 1) * chunk_size))
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
    lines.append(_("Media {avg:.1f} secondi.").format(avg=time_stats["avg"]))

    quartiles = time_stats.get("quartiles", [])
    if quartiles:
        lines.append(_("Andamento nel corso della sessione."))
        for q in quartiles:
            idx = q["quartile"]
            pct_var = q["pct_var"]
            if idx == 1:
                confronto = _("e' il riferimento")
            elif pct_var > 0:
                confronto = _("cioe' {p:.0f} per cento piu' lento del primo").format(
                    p=pct_var
                )
            elif pct_var < 0:
                confronto = _("cioe' {p:.0f} per cento piu' rapido del primo").format(
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
):
    """
    Mostra il report della sessione e aggiorna la classifica.
    """
    score_per_minute = (score / duration) * 60 if duration > 0 else 0
    average_time = duration / rpt if rpt > 0 else 0
    ex_label = EX_NAME_MAP.get(exercise_name, exercise_name)

    time_stats = compute_time_stats(timeslist)
    time_stats_str = format_time_stats_string(time_stats)

    print(_("Risultati Esercizio"))
    print(
        _("Hai ottenuto {wins} risposte corrette su {rpt}.").format(wins=wins, rpt=rpt)
    )
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

    if exercises_played is not None:
        if ex_label not in exercises_played:
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
            if time_stats_str:
                log_entry += "\n" + time_stats_str
            session_logs.append(log_entry)
            if save_session_callback:
                save_session_callback()
        key(prompt=_("\nPremi un tasto per procedere..."))
        return

    # 2. Verifica qualificazione Top 10
    ranking_metric = "score" if exercise_name == "mixed" else "score_per_minute"
    new_performance = score if exercise_name == "mixed" else score_per_minute

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
        username = (
            input(_("Per favore, inserisci il tuo nome per la classifica: "))
            .strip()
            .title()
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
                        "\n🎉 Nuovo record personale per {username}! Precedente: {old_perf:.0f}, Attuale: {new_perf:.0f}."
                    ).format(
                        username=username, old_perf=old_perf, new_perf=new_performance
                    )
                )
                ex_list[existing_index] = new_entry
            else:
                print(
                    _(
                        "\nHai ottenuto un punteggio inferiore al tuo precedente record ({old_perf:.0f} vs {new_perf:.0f})."
                    ).format(old_perf=old_perf, new_perf=new_performance)
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
    """Durata di una sessione detta in minuti e secondi."""
    secondi = int(secondi or 0)
    minuti, resto = divmod(secondi, 60)
    if minuti and resto:
        return _("{m} minuti e {s} secondi").format(m=minuti, s=resto)
    if minuti:
        return _("{m} minuti").format(m=minuti)
    return _("{s} secondi").format(s=resto)


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
                    "{pmin:.0f} al minuto, {acc:.0f} per cento di risposte esatte."
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
            key=lambda item: item.get("score_per_minute", 0),
            reverse=True,
        )[:MAX_LEADERBOARD_ENTRIES]

        print(
            _(
                "Classifica {exercise}, ordinata per punti al minuto, almeno venti domande."
            ).format(exercise=_nome_esercizio(selected_exercise))
        )

        for i, item in enumerate(sorted_leaderboard, 1):
            user = item.get("username", _("Anonimo"))
            reps = item.get("repetitions", 0)
            wins = item.get("wins", 0)
            precisione = (wins / reps) * 100 if reps else 0.0
            print(
                _("{pos}. {user}, {pmin:.0f} punti al minuto.").format(
                    pos=i, user=user, pmin=item.get("score_per_minute", 0)
                )
            )
            print(
                _(
                    "{reps} domande, {acc:.0f} per cento esatte, media {avg:.1f} secondi."
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
    timeex = time.time()
    timeslist = []
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

        now = time.time()

        user_says_yes = None
        while True:
            s = key()
            if s == "" or s in ("\r", "\n", "enter"):
                user_says_yes = True
                break
            elif s in ("\x1b", "esc"):
                user_says_yes = False
                break

        singlescore = (scoretime * 1000) - (time.time() - now) * 1000
        singlescore = max(singlescore, 0)

        elapsed_q = time.time() - now
        timeslist.append(elapsed_q)
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

    duration = time.time() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list


def ExBishops(ripetitions):
    """Esercizio sugli alfieri"""
    initial_rpt = ripetitions
    score = 0
    wins = 0
    scoretime = 15
    timeex = time.time()
    timeslist = []
    scoreslist = []
    errors_list = []

    while ripetitions > 0:
        kd = random.choice(list(diagonals.keys()))
        sq1 = random.choice(diagonals[kd])
        yes = random.choice([True, False])
        if not yes:
            sq2 = Prox(sq1, "B", range_limit=7)
        else:
            while True:
                sq2 = random.choice(diagonals[kd])
                if sq1 != sq2:
                    break

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

        now = time.time()

        user_says_yes = None
        while True:
            s = key()
            if s == "" or s in ("\r", "\n", "enter"):
                user_says_yes = True
                break
            elif s in ("\x1b", "esc"):
                user_says_yes = False
                break

        singlescore = (scoretime * 1000) - (time.time() - now) * 1000
        singlescore = max(singlescore, 0)

        elapsed_q = time.time() - now
        timeslist.append(elapsed_q)
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

    duration = time.time() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list


def ExMixed(ripetitions):
    """
    Esegue una serie di domande di tipo misto.
    """
    initial_rpt = ripetitions
    score = 0
    wins = 0
    scoretime = 15
    timeex = time.time()
    timeslist = []
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

            now = time.time()
            user_says_white = None
            while True:
                s = key()
                if s == "" or s in ("\r", "\n", "enter"):
                    user_says_white = True
                    break
                elif s in ("\x1b", "esc"):
                    user_says_white = False
                    break
            elapsed_q = time.time() - now
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

            now = time.time()
            user_says_yes = None
            while True:
                s = key()
                if s == "" or s in ("\r", "\n", "enter"):
                    user_says_yes = True
                    break
                elif s in ("\x1b", "esc"):
                    user_says_yes = False
                    break
            elapsed_q = time.time() - now
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
            kd = random.choice(list(diagonals.keys()))
            sq1 = random.choice(diagonals[kd])
            yes = random.choice([True, False])
            if not yes:
                sq2 = Prox(sq1, "B", range_limit=7)
            else:
                while True:
                    sq2 = random.choice(diagonals[kd])
                    if sq1 != sq2:
                        break

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

            now = time.time()
            user_says_yes = None
            while True:
                s = key()
                if s == "" or s in ("\r", "\n", "enter"):
                    user_says_yes = True
                    break
                elif s in ("\x1b", "esc"):
                    user_says_yes = False
                    break
            elapsed_q = time.time() - now
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

    duration = time.time() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list


def ExColors(ripetitions):
    """Esercizio sui colori delle case"""
    initial_rpt = ripetitions
    score = 0
    wins = 0
    scoretime = 15
    timeex = time.time()
    timeslist = []
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

        now = time.time()

        user_says_white = None
        while True:
            s = key()
            if s == "" or s in ("\r", "\n", "enter"):
                user_says_white = True
                break
            elif s in ("\x1b", "esc"):
                user_says_white = False
                break

        singlescore = (scoretime * 1000) - (time.time() - now) * 1000
        singlescore = max(singlescore, 0)

        elapsed_q = time.time() - now
        timeslist.append(elapsed_q)
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

    duration = time.time() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list


def main():
    start_memoboard_time = time.time()
    session_start_dt = datetime.datetime.now()
    all_scores = load_scores()
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
            except Exception:
                pass
        current_session_filepath = target_path

        endtime = time.time() - start_memoboard_time
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
        except Exception as e:
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
            score, scoreslist, duration, timeslist, wins, errors_list = ExColors(rpt)
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
            score, scoreslist, duration, timeslist, wins, errors_list = ExKnights(rpt)
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
            score, scoreslist, duration, timeslist, wins, errors_list = ExBishops(rpt)
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
            score, scoreslist, duration, timeslist, wins, errors_list = ExMixed(100)
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
            )

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
    endtime = time.time() - start_memoboard_time

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
