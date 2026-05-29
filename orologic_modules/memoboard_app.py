# MEMOBOARD - Il tuo assistente per giocare a scacchi senza scacchiera.
# Born on monday, may 6th, 2024 by Gabriele Battaglia IZ4APU.
# June 28th, 2024: moved on Github
# Fuso in Orologic il 29 Maggio 2026.

from GBUtils import key, dgt, menu, Acusticator
import time
import datetime
import random
import json
import os

from . import config
from .config import _

# COSTANTI
READING_TIME = 0.8  # Tempo di lettura delle domande in secondi, da parte della sintesi vocale
STARTTIME = time.time()
SCORES_FILE = config.percorso_salvataggio(os.path.join("settings", "memoboard_scores.json"))
FREQ_START, FREQ_END = 130.81, 2093.0
PAN_START, PAN_END = -1.0, 1.0
AUDIO_YES_NO_DUR = 0.06
AUDIO_YES_NO_VOL = 0.2
AUDIO_BAR_DUR = 0.025
AUDIO_BAR_VOL = 0.15

mnu = {
    "cavalli": _("Esercizio con i salti di cavallo"),
    "alfieri": _("Esercizio con le diagonali"),
    "colori": _("Questa casa è bianca o nera?"),
    "mista": _("Affronta la sfida mista da 100 domande!"),
    "classifiche": _("Mostra la classifica"),
    ".": _("per tornare ad Orologic")
}
log = None

board_set = set()
for y in "12345678":
    for x in "ABCDEFGH":
        board_set.add(f"{x}{y}")
board = list(board_set)

diagonals = {
    'A1H8': ['A1', 'B2', 'C3', 'D4', 'E5', 'F6', 'G7', 'H8'],
    'B1H7': ['B1', 'C2', 'D3', 'E4', 'F5', 'G6', 'H7'],
    'C1H6': ['C1', 'D2', 'E3', 'F4', 'G5', 'H6'],
    'D1H5': ['D1', 'E2', 'F3', 'G4', 'H5'],
    'E1H4': ['E1', 'F2', 'G3', 'H4'],
    'F1H3': ['F1', 'G2', 'H3'], 'G1H2': ['G1', 'H2'],
    'B1A2': ['B1', 'A2'], 'C1A3': ['C1', 'B2', 'A3'],
    'D1A4': ['D1', 'C2', 'B3', 'A4'],
    'E1A5': ['E1', 'D2', 'C3', 'B4', 'A5'],
    'F1A6': ['F1', 'E2', 'D3', 'C4', 'B5', 'A6'],
    'G1A7': ['G1', 'F2', 'E3', 'D4', 'C5', 'B6', 'A7'],
    'H1A8': ['H1', 'G2', 'F3', 'E4', 'D5', 'C6', 'B7', 'A8']
}


def get_column_spelling(col_letter):
    """Ottiene la pronuncia fonetica delle colonne da Orologic (config.L10N)."""
    col_lower = col_letter.lower()
    return config.L10N.get("columns", {}).get(col_lower, col_letter).title()


# --- FUNZIONI GESTIONE PUNTEGGI (JSON) ---

def load_scores():
    """
    Carica i punteggi dal file JSON.
    Se il file non esiste o è vuoto, ritorna un dizionario vuoto.
    """
    if not os.path.exists(SCORES_FILE):
        return {}
    try:
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_scores(scores_data):
    """
    Salva il dizionario dei punteggi nel file JSON.
    """
    try:
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, 'w', encoding='utf-8') as f:
            json.dump(scores_data, f, indent=2, ensure_ascii=False)
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
    col = ord(sq[0]) - ord('A')
    row = ord(sq[1]) - ord('1')
    return 'b' if (col + row) % 2 == 0 else 'w'


def Prox(sq, kind, range_limit):
    '''Genera una casa vicina a 'sq' che NON sia sulla stessa diagonale (kind='B') 
       o a un salto di cavallo (kind='N').'''
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


def report_and_update_scores(all_scores, username, exercise_name, rpt, score, duration, wins):
    """
    Mostra un report dettagliato, confronta con i risultati precedenti e aggiorna i dati dell'utente.
    Chiede conferma prima di sovrascrivere un record con un punteggio peggiore.
    """
    new_results = {
        "score": score,
        "wins": wins,
        "repetitions": rpt,
        "duration": duration,
        "average_time_per_guess": duration / rpt if rpt > 0 else 0,
        "score_per_win": score / wins if wins > 0 else 0,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    new_results["score_per_minute"] = (score / duration) * 60 if duration > 0 else 0

    print(_("\n--- Risultati Esercizio ---"))
    print(_("Hai ottenuto {wins} risposte corrette su {rpt}.").format(wins=wins, rpt=rpt))
    print(_("Punteggio totale: {score:.0f} in {duration:.1f} secondi.").format(score=score, duration=duration))
    print(_("Performance: {score_per_minute:.0f} punti al minuto.").format(score_per_minute=new_results['score_per_minute']))

    previous_results = all_scores.get(username, {}).get(exercise_name)

    should_save = True

    if previous_results:
        print(_("\n--- Confronto Dettagliato vs. Precedente ---"))
        
        header = _("{metrica:<20} {precedente:>12} {attuale:>12} {differenza:<25}").format(
            metrica=_("Metrica"),
            precedente=_("Precedente"),
            attuale=_("Attuale"),
            differenza=_("Differenza")
        )
        print(header)
        print("-" * len(header))
        
        metrics_to_compare = {
            _("Punti al Minuto"): ("score_per_minute", ".0f"),
            _("Punteggio Totale"): ("score", ".0f"),
            _("Risposte Corrette"): ("wins", ".0f")
        }

        for label, (metric_key, fmt) in metrics_to_compare.items():
            old_val = previous_results.get(metric_key, 0)
            new_val = new_results.get(metric_key, 0)
            diff = new_val - old_val
            
            perc_str = f"({(diff / old_val) * 100:+.2f}%)" if old_val != 0 else _("(N/D)")
            
            old_val_str = f"{old_val:{fmt}}"
            new_val_str = f"{new_val:{fmt}}"
            diff_str = f"{diff:+{fmt}} {perc_str}"

            row = _("{label:<20} {old_val_str:>12} {new_val_str:>12} {diff_str:<25}").format(
                label=label, old_val_str=old_val_str, new_val_str=new_val_str, diff_str=diff_str
            )
            print(row)
        
        print("-" * len(header))

        ranking_metric = "score" if exercise_name == 'mixed' else "score_per_minute"
        
        old_performance = previous_results.get(ranking_metric, 0)
        new_performance = new_results.get(ranking_metric, 0)

        if new_performance < old_performance:
            print(_("\nHai ottenuto un punteggio inferiore al precedente."))
            si_key = _("s")
            answer = key(_("Vuoi sovrascrivere il tuo record con questo punteggio? (s/n): ")).lower()
            if answer != si_key:
                should_save = False
                print(_("Il vecchio punteggio è stato mantenuto."))
        
        new_record_jingle = ['c5', 0.08, -0.7, config.VOLUME, 'e5', 0.08, -0.2, config.VOLUME, 'g5', 0.08, 0.2, config.VOLUME, 'c6', 0.15, 0.7, config.VOLUME]
        no_record_jingle = ['a4', 0.12, 0, config.VOLUME, 'e4', 0.20, 0, config.VOLUME]
        if new_performance > old_performance:
            Acusticator(new_record_jingle, kind=1)
        else:
            Acusticator(no_record_jingle, kind=1)
        
        key(prompt=_("\nPremi un tasto per procedere..."))

    else:
        print(_("\nQuesto è il tuo primo risultato per questo esercizio. Ottimo! Hai stabilito un nuovo record!"))
        first_record_jingle = ['g4', 0.07, -0.5, config.VOLUME, 'c5', 0.07, 0.5, config.VOLUME, 'e5', 0.1, 0, config.VOLUME]
        Acusticator(first_record_jingle, kind=1)
        key(prompt=_("\nPremi un tasto per continuare..."))

    if should_save:
        if username not in all_scores:
            all_scores[username] = {}
        all_scores[username][exercise_name] = new_results
        
        if log:
            log.write(_("\n## Esercizio '{exercise_name}' per {username}:").format(exercise_name=exercise_name, username=username))
            log.write(_("\nRisposte corrette: {wins}/{rpt} in {duration:.1f}s. Punti: {score:.0f}. Performance: {score_per_minute:.0f} p/min. [SALVATO]").format(
                wins=wins, rpt=rpt, duration=duration, score=score, score_per_minute=new_results['score_per_minute']
            ))
        print(_("\nRisultato salvato!"))
    else:
        if log:
            log.write(_("\n## Esercizio '{exercise_name}' per {username}: Nuovo punteggio di {score:.0f} scartato dall'utente. [SCARTATO]").format(
                exercise_name=exercise_name, username=username, score=score
            ))


def show_leaderboard(all_scores):
    """
    Mostra una classifica dettagliata.
    """
    if not all_scores:
        print(_("\nNon ci sono ancora punteggi registrati per mostrare una classifica."))
        key(prompt=_("\nPremi un tasto per tornare al menu..."))
        return

    print(_("\nQuale classifica vorresti vedere?"))
    map_menu_to_db = {
        "cavalli": "knights",
        "alfieri": "bishops",
        "colori": "colors",
        "mista": "mixed"
    }
    menu_options = {
        "cavalli": _("Classifica Esercizio Cavalli"),
        "alfieri": _("Classifica Esercizio Alfieri"),
        "colori": _("Classifica Esercizio Colori"),
        "mista": _("Classifica Sfida Mista")
    }

    selected_menu = menu(d=menu_options, show=True, keyslist=True, ntf=_("Scelta non valida"))

    if not selected_menu:
        return

    selected_exercise = map_menu_to_db[selected_menu]

    leaderboard_data = []
    for user, data in all_scores.items():
        if selected_exercise in data:
            ex_data = data[selected_exercise]
            score = ex_data.get("score", 0)
            performance = ex_data.get("score_per_minute", 0)
            reps = ex_data.get("repetitions", 0)
            wins = ex_data.get("wins", 0)
            duration = ex_data.get("duration", 0)
            timestamp = ex_data.get("timestamp", None)
            avg_time = ex_data.get("average_time_per_guess", 0)
            leaderboard_data.append((user, score, performance, reps, wins, duration, timestamp, avg_time))

    if not leaderboard_data:
        print(_("\nNessun punteggio trovato per l'esercizio '{selected_exercise}'.").format(selected_exercise=selected_exercise))
    else:
        if selected_exercise == 'mixed':
            sorted_leaderboard = sorted(leaderboard_data, key=lambda item: item[1], reverse=True)
            
            print(_("\n--- 🏆 CLASSIFICA: {exercise} (Ordinata per Punteggio Totale) 🏆 ---").format(exercise=selected_exercise.upper()))
            header = _("{pos:<4} {utente:<12} {punti:>10} {pmin:>8} {win:>5} {avg:>7} {tempo:>6} {data:>17}").format(
                pos=_("Pos"), utente=_("Utente"), punti=_("Punti"), pmin=_("P/Min"), win=_("Win%"), avg=_("Avg(s)"), tempo=_("Tempo"), data=_("Data")
            )
            print(header)
            print("-" * len(header))

            for i, item in enumerate(sorted_leaderboard, 1):
                user, score, performance, reps, wins, duration, timestamp, avg_time = item
                accuracy_str = f"{(wins / reps) * 100:3.0f}%" if reps > 0 else _("N/D")
                time_str = f"{int(duration // 60):02d}:{int(duration % 60):02d}"
                date_str = datetime.datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M') if timestamp else _("N/D")
                
                row = _("{pos:<4} {user:<12} {score:>10.0f} {performance:>8.0f} {accuracy:>5} {avg_time:>7.2f} {time_str:>6} {date_str:>17}").format(
                    pos=i, user=user[:12], score=score, performance=performance, accuracy=accuracy_str, avg_time=avg_time, time_str=time_str, date_str=date_str
                )
                print(row)
            print("-" * len(header))

        else: 
            sorted_leaderboard = sorted(leaderboard_data, key=lambda item: item[2], reverse=True)
            
            print(_("\n--- 🏆 CLASSIFICA: {exercise} (Ordinata per Punti/Min) 🏆 ---").format(exercise=selected_exercise.upper()))
            header = _("{pos:<4} {utente:<12} {tent:>4} {win:>5} {avg:>7} {pmin:>8} {data:>17}").format(
                pos=_("Pos"), utente=_("Utente"), tent=_("Tent"), win=_("Win%"), avg=_("Avg(s)"), pmin=_("P/Min"), data=_("Data")
            )
            print(header)
            print("-" * len(header))

            for i, item in enumerate(sorted_leaderboard, 1):
                user, unused_score, performance, reps, wins, unused_duration, timestamp, avg_time = item
                accuracy_str = f"{(wins / reps) * 100:3.0f}%" if reps > 0 else _("N/D")
                date_str = datetime.datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M') if timestamp else _("N/D")
                
                row = _("{pos:<4} {user:<12} {reps:>4} {accuracy:>5} {avg_time:>7.2f} {performance:>8.0f} {date_str:>17}").format(
                    pos=i, user=user[:12], reps=reps, accuracy=accuracy_str, avg_time=avg_time, performance=performance, date_str=date_str
                )
                print(row)
            print("-" * len(header))

    key(prompt=_("\nPremi un tasto per tornare al menu..."))


# --- FUNZIONI DEGLI ESERCIZI ---

def ExKnights(ripetitions):
    '''Esercizio sui cavalli'''
    initial_rpt = ripetitions
    score = 0; wins = 0; scoretime = 15
    timeex = time.time()
    timeslist = []; scoreslist = []
    errors_list = []
    knight_moves = [(1, 2), (1, -2), (-1, 2), (-1, -2), (2, 1), (2, -1), (-2, 1), (-2, -1)]

    while ripetitions > 0:
        sq1 = random.choice(board)
        yes = random.choice([True, False])
        if not yes: 
            sq2 = Prox(sq1, 'N', range_limit=2)
        else:
            x, y = ord(sq1[0]), ord(sq1[1])
            possible_sq2 = []
            for dx, dy in knight_moves:
                new_x, new_y = x + dx, y + dy
                if ord('A') <= new_x <= ord('H') and ord('1') <= new_y <= ord('8'):
                    possible_sq2.append(f"{chr(new_x)}{chr(new_y)}")
            if not possible_sq2:
                continue
            sq2 = random.choice(possible_sq2)

        question_str = _("Mossa di cavallo: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
        print(_("\nCavallo: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?").format(
            sq1_spelling=get_column_spelling(sq1[0]), sq1_rank=sq1[1],
            sq2_spelling=get_column_spelling(sq2[0]), sq2_rank=sq2[1]
        ), end="", flush=True)
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
        if singlescore < 0:
            singlescore = 0
        
        correct = (user_says_yes == yes)
        if correct:
            timeslist.append(time.time() - now)
            wins += 1
            score += singlescore
            scoreslist.append(singlescore)
        else:
            errors_list.append({
                "question": question_str,
                "user_answer": "y" if user_says_yes else "n",
                "correct_answer": "y" if yes else "n"
            })
        current_rep_index = initial_rpt - ripetitions 
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress
        note_feedback = 'c6' if correct else 'c4'
        sound_score = [note_feedback, AUDIO_YES_NO_DUR, 0, config.VOLUME, current_freq, AUDIO_BAR_DUR, current_pan, AUDIO_BAR_VOL]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1
        
    duration = time.time() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list


def ExBishops(ripetitions):
    '''Esercizio sugli alfieri'''
    initial_rpt = ripetitions
    score = 0; wins = 0; scoretime = 15
    timeex = time.time()
    timeslist = []; scoreslist = []
    errors_list = []

    while ripetitions > 0:
        kd = random.choice(list(diagonals.keys()))
        sq1 = random.choice(diagonals[kd])
        yes = random.choice([True, False])
        if not yes:
            sq2 = Prox(sq1, 'B', range_limit=7)
        else:
            while True:
                sq2 = random.choice(diagonals[kd])
                if sq1 != sq2:
                    break
        
        question_str = _("Stessa diagonale: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
        print(_("\nAlfiere: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?").format(
            sq1_spelling=get_column_spelling(sq1[0]), sq1_rank=sq1[1],
            sq2_spelling=get_column_spelling(sq2[0]), sq2_rank=sq2[1]
        ), end="", flush=True)
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
        if singlescore < 0:
            singlescore = 0
        
        correct = (user_says_yes == yes)
        if correct:
            timeslist.append(time.time() - now)
            wins += 1
            score += singlescore
            scoreslist.append(singlescore)
        else:
            errors_list.append({
                "question": question_str,
                "user_answer": "y" if user_says_yes else "n",
                "correct_answer": "y" if yes else "n"
            })
        current_rep_index = initial_rpt - ripetitions 
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress
        note_feedback = 'c6' if correct else 'c4'
        sound_score = [note_feedback, AUDIO_YES_NO_DUR, 0, config.VOLUME, current_freq, AUDIO_BAR_DUR, current_pan, AUDIO_BAR_VOL]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1
    duration = time.time() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list


def ExMixed(ripetitions):
    """
    Esegue una serie di domande di tipo misto.
    """
    initial_rpt = ripetitions
    score = 0; wins = 0; scoretime = 15
    timeex = time.time()
    errors_list = []
    knight_moves = [(1, 2), (1, -2), (-1, 2), (-1, -2), (2, 1), (2, -1), (-2, 1), (-2, -1)]

    while ripetitions > 0:
        exercise_type = random.choice(['colors', 'knights', 'bishops'])
        correct = False

        if exercise_type == 'colors':
            sq = random.choice(board)
            print(_("\nColore per {sq_spelling} {sq_rank}?").format(
                sq_spelling=get_column_spelling(sq[0]), sq_rank=sq[1]
            ), end="", flush=True)
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
            if singlescore < 0:
                singlescore = 0
            
            correct_is_white = (get_square_color(sq) == 'w')
            correct = (user_says_white == correct_is_white)
            if correct:
                wins += 1
                score += singlescore
            else:
                errors_list.append({
                    "question": _("Colore di {sq}").format(sq=sq),
                    "user_answer": _("Bianco") if user_says_white else _("Nero"),
                    "correct_answer": _("Bianco") if correct_is_white else _("Nero")
                })

        elif exercise_type == 'knights':
            sq1 = random.choice(board)
            yes = random.choice([True, False])
            if not yes:
                sq2 = Prox(sq1, 'N', range_limit=2)
            else:
                x, y = ord(sq1[0]), ord(sq1[1])
                possible_sq2 = []
                for dx, dy in knight_moves:
                    new_x, new_y = x + dx, y + dy
                    if ord('A') <= new_x <= ord('H') and ord('1') <= new_y <= ord('8'):
                        possible_sq2.append(f"{chr(new_x)}{chr(new_y)}")
                if not possible_sq2:
                    continue
                sq2 = random.choice(possible_sq2)

            question_str = _("Mossa di cavallo: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
            print(_("\nCavallo: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?").format(
                sq1_spelling=get_column_spelling(sq1[0]), sq1_rank=sq1[1],
                sq2_spelling=get_column_spelling(sq2[0]), sq2_rank=sq2[1]
            ), end="", flush=True)
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
            if singlescore < 0:
                singlescore = 0
            
            correct = (user_says_yes == yes)
            if correct:
                wins += 1
                score += singlescore
            else:
                errors_list.append({
                    "question": question_str,
                    "user_answer": "y" if user_says_yes else "n",
                    "correct_answer": "y" if yes else "n"
                })

        elif exercise_type == 'bishops':
            kd = random.choice(list(diagonals.keys()))
            sq1 = random.choice(diagonals[kd])
            yes = random.choice([True, False])
            if not yes:
                sq2 = Prox(sq1, 'B', range_limit=7)
            else:
                while True:
                    sq2 = random.choice(diagonals[kd])
                    if sq1 != sq2:
                        break
            
            question_str = _("Stessa diagonale: {sq1}-{sq2}").format(sq1=sq1, sq2=sq2)
            print(_("\nAlfiere: {sq1_spelling} {sq1_rank} e {sq2_spelling} {sq2_rank}?").format(
                sq1_spelling=get_column_spelling(sq1[0]), sq1_rank=sq1[1],
                sq2_spelling=get_column_spelling(sq2[0]), sq2_rank=sq2[1]
            ), end="", flush=True)
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
            if singlescore < 0:
                singlescore = 0
            
            correct = (user_says_yes == yes)
            if correct:
                wins += 1
                score += singlescore
            else:
                errors_list.append({
                    "question": question_str,
                    "user_answer": "y" if user_says_yes else "n",
                    "correct_answer": "y" if yes else "n"
                })

        current_rep_index = initial_rpt - ripetitions
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress
        note_feedback = 'c6' if correct else 'c4'
        sound_score = [note_feedback, AUDIO_YES_NO_DUR, 0, config.VOLUME, current_freq, AUDIO_BAR_DUR, current_pan, AUDIO_BAR_VOL]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1
        
    duration = time.time() - timeex
    return score, duration, wins, errors_list


def ExColors(ripetitions):
    '''Esercizio sui colori delle case'''
    initial_rpt = ripetitions
    score = 0; wins = 0; scoretime = 15
    timeex = time.time()
    timeslist = []; scoreslist = []
    errors_list = []
    
    while ripetitions > 0:
        sq = random.choice(board)
        print(_("\nColore per {sq_spelling} {sq_rank}?").format(
            sq_spelling=get_column_spelling(sq[0]), sq_rank=sq[1]
        ), end="", flush=True)
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
        if singlescore < 0:
            singlescore = 0
        
        correct_is_white = (get_square_color(sq) == 'w')
        correct = (user_says_white == correct_is_white)
        if correct:
            timeslist.append(time.time() - now)
            wins += 1
            score += singlescore
            scoreslist.append(singlescore)
        else:
            errors_list.append({
                "question": _("Colore di {sq}").format(sq=sq),
                "user_answer": _("Bianco") if user_says_white else _("Nero"),
                "correct_answer": _("Bianco") if correct_is_white else _("Nero")
            })
        
        current_rep_index = initial_rpt - ripetitions 
        progress = current_rep_index / (initial_rpt - 1) if initial_rpt > 1 else 1
        current_freq = FREQ_START + (FREQ_END - FREQ_START) * progress
        current_pan = PAN_START + (PAN_END - PAN_START) * progress
        note_feedback = 'c6' if correct else 'c4'
        sound_score = [note_feedback, AUDIO_YES_NO_DUR, 0, config.VOLUME, current_freq, AUDIO_BAR_DUR, current_pan, AUDIO_BAR_VOL]
        Acusticator(sound_score, kind=1)
        ripetitions -= 1
        
    duration = time.time() - timeex
    return score, scoreslist, duration, timeslist, wins, errors_list


def main():
    global log
    all_scores = load_scores()
    print(_("Benvenuto in MemoBoard.\nIl tuo assistente per giocare a scacchi senza scacchiera.\nQuesta utility ti aiuta a visualizzare la scacchiera e a diventare un giocatore migliore.\n\t(Integrato in Orologic {version})").format(version=config.VERSION))
    Acusticator(['c4', 0.08, 0, config.VOLUME, 'e4', 0.08, 0, config.VOLUME, 'g4', 0.1, 0, config.VOLUME], kind=1)
    
    # Inizializziamo il log all'interno di main()
    log_dir = config.percorso_salvataggio("txt")
    os.makedirs(log_dir, exist_ok=True)
    log = open(os.path.join(log_dir, "memoboard.txt"), "a+", encoding="utf-8")
    log.write(f"\n# {time.asctime()} Ciao, Memoboard (Orologic {config.VERSION}) si avvia.")

    username = input(_("\nPer favore, inserisci il tuo nome: ")).strip().title()
    if not username:
        username = _("UtentePredefinito")
    print(_("\nBentornato, {username}! Pronto ad allenarti? Digita '?'.\nSe hai attivato i menu numerati in Orologic, puoi usarli anche qui.").format(username=username))
    
    while True:
        s = menu(d=mnu, ntf=_("Comando non trovato"), show=True, keyslist=True)
        if s == ".":
            break
        
        elif s == "colori":
            print(_("Indovina il colore della casa.\nRispondi premendo ESC per il nero e INVIO per il bianco."))
            rpt = dgt(prompt=_("\nBello! E buona fortuna con i colori, quante domande vuoi fare? "), kind="i", imin=5, imax=150)
            key(prompt=_("Pronto?"))
            print(_(" Inizio"))
            score, scoreslist, duration, timeslist, wins, errors_list = ExColors(rpt)
            if errors_list:
                print(_("\n--- I tuoi errori ---"))
                for err in errors_list:
                    q = err['question']
                    ua = err['user_answer']
                    ca = err['correct_answer']
                    print(_("> Domanda: {q} | La tua risposta: '{ua}', corretta: '{ca}'").format(q=q, ua=ua, ca=ca))
                key(_("\nPremi un tasto per procedere alla classifica..."))
            report_and_update_scores(all_scores, username, "colors", rpt, score, duration, wins)

        elif s == "cavalli":
            print(_("Indovina se due case sono a un salto di cavallo.\nRispondi premendo INVIO per sì e ESC per no."))
            rpt = dgt(prompt=_("\nBene, divertiti con il salto del cavallo, quante domande vuoi fare? "), kind="i", imin=5, imax=150)
            key(prompt=_("Pronto?"))
            print(_(" Inizio"))
            score, scoreslist, duration, timeslist, wins, errors_list = ExKnights(rpt)
            if errors_list:
                print(_("\n--- I tuoi errori ---"))
                for err in errors_list:
                    q = err['question']
                    ua = _("Sì") if err['user_answer'] == 'y' else _("No")
                    ca = _("Sì") if err['correct_answer'] == 'y' else _("No")
                    print(_("> Domanda: {q} | La tua risposta: '{ua}', Corretta: '{ca}'").format(q=q, ua=ua, ca=ca))
                key(_("\nPremi un tasto per procedere alla classifica..."))
            report_and_update_scores(all_scores, username, "knights", rpt, score, duration, wins)
            
        elif s == "alfieri":
            print(_("Indovina se due case sono sulla stessa diagonale.\nRispondi premendo INVIO per sì e ESC per no."))
            rpt = dgt(prompt=_("\nBene, divertiti con l'esercizio dell'alfiere, quante domande vuoi fare? "), kind="i", imin=5, imax=150)
            key(prompt=_("Pronto?"))
            print(_(" Inizio"))
            score, scoreslist, duration, timeslist, wins, errors_list = ExBishops(rpt)
            if errors_list:
                print(_("\n--- I tuoi errori ---"))
                for err in errors_list:
                    q = err['question']
                    ua = _("Sì") if err['user_answer'] == 'y' else _("No")
                    ca = _("Sì") if err['correct_answer'] == 'y' else _("No")
                    print(_("> Domanda: {q} | La tua risposta: '{ua}', Corretta: '{ca}'").format(q=q, ua=ua, ca=ca))
                key(_("\nPremi un tasto per procedere alla classifica..."))
            report_and_update_scores(all_scores, username, "bishops", rpt, score, duration, wins)

        elif s == "classifiche":
            Acusticator(['g4', 0.07, -0.5, config.VOLUME, 'c5', 0.07, 0.5, config.VOLUME, 'e5', 0.1, 0, config.VOLUME], kind=1)
            show_leaderboard(all_scores)
            
        elif s == "mista":
            print(_("\nBenvenuto alla Sfida Mista!"))
            print(_("Saranno presentate 100 domande di tipo casuale (colori, cavalli, alfieri)."))
            print(_("Questa è la prova definitiva delle tue abilità e della tua resistenza. Buona fortuna!\nRicorda di rispondere con INVIO per sì/bianco e ESC per no/nero."))
            
            key(prompt=_("Sei pronto per iniziare? Via!"))
            score, duration, wins, errors_list = ExMixed(100)
            rpt = 100
            
            print(_("\n--- SFIDA MISTA COMPLETATA! ---"))
            if errors_list:
                print(_("\n--- I tuoi errori nella Sfida Mista ---"))
                for err in errors_list:
                    q = err['question']
                    ua = err['user_answer']
                    ca = err['correct_answer']

                    if ua in ('y', 'n'):
                        ua_fmt = _("Sì") if ua == 'y' else _("No")
                        ca_fmt = _("Sì") if ca == 'y' else _("No")
                        print(_("> {q} | La tua risposta: '{ua}', Corretta: '{ca}'").format(q=q, ua=ua_fmt, ca=ca_fmt))
                    else:
                        print(_("> {q} | La tua risposta: '{ua}', Corretta: '{ca}'").format(q=q, ua=ua, ca=ca))

                key(_("\nPremi un tasto per procedere alla classifica..."))             
            report_and_update_scores(all_scores, username, "mixed", rpt, score, duration, wins)

    save_scores(all_scores)
    Acusticator(['g4', 0.1, 0, config.VOLUME, 'e4', 0.08, 0, config.VOLUME, 'c4', 0.15, 0, config.VOLUME], kind=1, sync=True)
    endtime = time.time() - STARTTIME
    print(_("\nMemoBoard terminato. Tempo di esecuzione: {minuti} minuti e {secondi} secondi.\n\tControlla txt/memoboard.txt. Arrivederci!").format(
        minuti=int(endtime/60), secondi=int(endtime%60)
    ))
    log.write(f"\n### Arrivederci da Memoboard, eseguito per {int(endtime/60)} minuti e {int(endtime%60)} secondi.\n")
    log.close()


if __name__ == "__main__":
    # Fallback per test o sviluppo se lanciato come main
    main()
