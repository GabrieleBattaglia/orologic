import datetime


from GBUtils import enter_escape, menu, sonify

from . import rete, storage, tempo
from .config import _


def fetch_rating_history(username):
    dati, errore = rete.leggi_json(
        f"https://lichess.org/api/user/{username}/rating-history"
    )
    if errore:
        print(_("Storia Elo non recuperata. {motivo}").format(motivo=errore))
        return None
    return dati


def calcola_durata_str(dt1, dt2):
    return tempo.fra_date(dt1, dt2)


def calcola_statistiche(sub_history):
    if not sub_history:
        return None

    ratings = [item["rating"] for item in sub_history]
    n = len(ratings)

    min_val = min(ratings)
    max_val = max(ratings)
    mean_val = sum(ratings) / n

    # Varianza, Deviazione Standard e Coefficiente di Variazione
    var_val = sum((x - mean_val) ** 2 for x in ratings) / n
    std_dev = var_val**0.5
    cv_val = (std_dev / mean_val) * 100 if mean_val != 0 else 0.0

    # Tendenza (trend slope di regressione lineare)
    if n > 1:
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(ratings)
        sum_xy = sum(x[i] * ratings[i] for i in range(n))
        sum_x2 = sum(i**2 for i in range(n))
        num = n * sum_xy - sum_x * sum_y
        den = n * sum_x2 - sum_x**2
        trend_val = num / den if den != 0 else 0.0
    else:
        trend_val = 0.0

    # Moda
    from collections import Counter

    c = Counter(ratings)
    mode_val = c.most_common(1)[0][0]

    return {
        "min": min_val,
        "max": max_val,
        "mean": mean_val,
        "cv": cv_val,
        "trend": trend_val,
        "mode": mode_val,
        "n": n,
        "start_dt": sub_history[0]["dt"],
        "end_dt": sub_history[-1]["dt"],
        "start_date": sub_history[0]["date"],
        "end_date": sub_history[-1]["date"],
    }


def dividi_in_quartili(sub_history):
    n = len(sub_history)
    if n < 4:
        return sub_history, [], [], []

    n1 = n // 4
    n2 = (2 * n) // 4
    n3 = (3 * n) // 4

    q1 = sub_history[0:n1]
    q2 = sub_history[n1:n2]
    q3 = sub_history[n2:n3]
    q4 = sub_history[n3:]
    return q1, q2, q3, q4


def formatta_stats_globale(title, stats):
    if not stats:
        return _("{title}: N/A").format(title=title)
    line1 = _(
        "{title}: {n} valori, minimo {min}, massimo {max}, media {mean:.0f}"
    ).format(
        title=title,
        n=stats["n"],
        min=stats["min"],
        max=stats["max"],
        mean=stats["mean"],
    )
    line2 = _(
        "Variabilita' {cv:.0f} per cento, tendenza {trend:.2f} punti a partita, valore piu' frequente {mode}"
    ).format(cv=stats["cv"], trend=stats["trend"], mode=stats["mode"])
    return f"{line1}\n{line2}"


def formatta_stats_quartile(title, stats):
    if not stats:
        return _("{title}: N/A").format(title=title)
    durata_str = calcola_durata_str(stats["start_dt"], stats["end_dt"])
    line1 = _("{title} (N={n}) {start} - {end} (Durata: {durata})").format(
        title=title,
        n=stats["n"],
        start=stats["start_date"],
        end=stats["end_date"],
        durata=durata_str,
    )
    line2 = _(
        "Minimo {min}, massimo {max}, media {mean:.0f}, variabilita' {cv:.0f} per cento, tendenza {trend:.2f}, piu' frequente {mode}"
    ).format(
        min=stats["min"],
        max=stats["max"],
        mean=stats["mean"],
        cv=stats["cv"],
        trend=stats["trend"],
        mode=stats["mode"],
    )
    return f"{line1}\n{line2}"


def calcola_dea(ratings, emin, emax):
    pri = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    pridiv = len(pri)
    eran = emax - emin
    dea = ""
    for j in ratings:
        w = (j - emin) * (pridiv - 1) / eran if eran > 0 else 0.0
        dea += pri[round(w)]
    return dea


def print_wrapped_dea(label, dea_str):
    if len(dea_str) < 73:
        print(f"{label}: {dea_str}")
    else:
        indent = " " * (len(label) + 2)
        for i in range(0, len(dea_str), 72):
            part = dea_str[i : i + 72]
            if i == 0:
                print(f"{label}: {part}")
            else:
                print(f"{indent}{part}")


def run_stats(username, secrets):
    print(_("\nRecupero storia Elo per {u} in corso...").format(u=username))
    history_data = fetch_rating_history(username)
    if not history_data:
        print(_("Impossibile caricare la storia Elo del giocatore."))
        enter_escape(_("\nPremi Invio per continuare..."))
        return

    while True:
        available_variants = {}
        for item in history_data:
            name = item.get("name", "")
            points = item.get("points", [])
            if len(points) >= 1:
                available_variants[name.lower()] = _("{name} ({count} valori)").format(
                    name=name, count=len(points)
                )

        if not available_variants:
            print(_("Nessun dato storico Elo disponibile per questo giocatore."))
            enter_escape(_("\nPremi Invio per continuare..."))
            return

        available_variants["."] = _("Torna indietro")

        db = storage.LoadDB()
        variant_choice = menu(
            available_variants,
            show=True,
            keyslist=True,
            p=_("\nScegli una variante Elo da esaminare: "),
            numbered=db.get("menu_numerati", False),
        )

        if variant_choice == ".":
            break

        selected_item = next(
            (
                item
                for item in history_data
                if item.get("name", "").lower() == variant_choice
            ),
            None,
        )
        if not selected_item:
            continue

        points = selected_item["points"]
        pt_list = [
            {
                "date": f"{pt[2]:02d}/{pt[1] + 1:02d}/{pt[0]}",
                "dt": datetime.datetime(pt[0], pt[1] + 1, pt[2]),
                "rating": pt[3],
            }
            for pt in points
        ]

        start_idx = 0
        end_idx = len(pt_list) - 1

        while True:
            selected_pts = pt_list[start_idx : end_idx + 1]
            stats = calcola_statistiche(selected_pts)
            q1, q2, q3, q4 = dividi_in_quartili(selected_pts)
            stats_q1 = calcola_statistiche(q1)
            stats_q2 = calcola_statistiche(q2)
            stats_q3 = calcola_statistiche(q3)
            stats_q4 = calcola_statistiche(q4)

            print(_("STATISTICHE ELO: {v}").format(v=selected_item.get("name")))
            print(
                _("Periodo: {d1} - {d2} (valori {i1}-{i2} su {tot})").format(
                    d1=pt_list[start_idx]["date"],
                    d2=pt_list[end_idx]["date"],
                    i1=start_idx + 1,
                    i2=end_idx + 1,
                    tot=len(pt_list),
                )
            )

            # Stampa durata totale del periodo selezionato
            durata_totale = calcola_durata_str(
                pt_list[start_idx]["dt"], pt_list[end_idx]["dt"]
            )
            print(_("Durata totale: {d}").format(d=durata_totale))

            print(formatta_stats_globale(_("Globale"), stats))
            if stats_q1:
                print(formatta_stats_quartile("Q1", stats_q1))
            if stats_q2:
                print(formatta_stats_quartile("Q2", stats_q2))
            if stats_q3:
                print(formatta_stats_quartile("Q3", stats_q3))
            if stats_q4:
                print(formatta_stats_quartile("Q4", stats_q4))

            options = {
                "1": _("Scegli valore temporale iniziale"),
                "2": _("Scegli valore temporale finale"),
                "3": _("Tutto il periodo"),
                "4": _("Ascolta sonificazione"),
                "5": _("Leggi stringa DEA tradotta"),
                ".": _("Torna indietro"),
            }

            scelta = menu(
                options,
                show=True,
                keyslist=True,
                p=_("\nScegli un'opzione: "),
                numbered=db.get("menu_numerati", False),
            )

            if choix_menu_abort := (scelta == "."):
                break
            elif scelta == "1":
                print(
                    _("Primo valore: 1 - {d} (Elo: {r})").format(
                        d=pt_list[0]["date"], r=pt_list[0]["rating"]
                    )
                )
                print(
                    _("Ultimo valore: {tot} - {d} (Elo: {r})").format(
                        tot=len(pt_list),
                        d=pt_list[-1]["date"],
                        r=pt_list[-1]["rating"],
                    )
                )
                try:
                    val = input(
                        _(
                            "Inserisci l'indice iniziale (1-{tot}, o invio per annullare): "
                        ).format(tot=len(pt_list))
                    ).strip()
                    if val:
                        val_idx = int(val) - 1
                        if 0 <= val_idx <= end_idx:
                            start_idx = val_idx
                        else:
                            print(_("Indice non valido o superiore all'indice finale."))
                except ValueError:
                    print(_("Valore non valido."))
            elif scelta == "2":
                print(
                    _("Primo valore: 1 - {d} (Elo: {r})").format(
                        d=pt_list[0]["date"], r=pt_list[0]["rating"]
                    )
                )
                print(
                    _("Ultimo valore: {tot} - {d} (Elo: {r})").format(
                        tot=len(pt_list),
                        d=pt_list[-1]["date"],
                        r=pt_list[-1]["rating"],
                    )
                )
                try:
                    val = input(
                        _(
                            "Inserisci l'indice finale (1-{tot}, o invio per annullare): "
                        ).format(tot=len(pt_list))
                    ).strip()
                    if val:
                        val_idx = int(val) - 1
                        if start_idx <= val_idx < len(pt_list):
                            end_idx = val_idx
                        else:
                            print(
                                _("Indice non valido o inferiore all'indice iniziale.")
                            )
                except ValueError:
                    print(_("Valore non valido."))
            elif scelta == "3":
                start_idx = 0
                end_idx = len(pt_list) - 1
            elif scelta == "4":
                ratings_subset = [item["rating"] for item in selected_pts]
                if len(ratings_subset) < 5:
                    print(_("Per la sonificazione sono necessari almeno 5 valori Elo."))
                    continue

                ptm = enter_escape(
                    _("Abilitare il portamento? (Invio = Si', Esc = No): ")
                )

                try:
                    sec_str = input(
                        _(
                            "Inserisci la durata in secondi (es. 5, max 30, o invio per 5): "
                        )
                    ).strip()
                    duration = float(sec_str) if sec_str else 5.0
                    if duration < 1.0 or duration > 30.0:
                        duration = 5.0
                except ValueError:
                    duration = 5.0

                db_data = storage.LoadDB()
                volume = db_data.get("volume", 1.0)
                sonify_vol = 0.2 if volume == 0 else volume

                print(_("Riproduzione sonificazione in corso..."))
                sonify(ratings_subset, duration, ptm=ptm, vol=sonify_vol)
            elif scelta == "5":
                ratings_subset = [item["rating"] for item in selected_pts]
                if not ratings_subset:
                    print(_("Nessun dato Elo disponibile per il periodo selezionato."))
                    continue

                emin_global = min(ratings_subset)
                emax_global = max(ratings_subset)

                span_days = (selected_pts[-1]["dt"] - selected_pts[0]["dt"]).days
                usa_quartili = False
                if (
                    len(ratings_subset) >= 20
                    or len(ratings_subset) >= 8
                    and span_days >= 60
                ):
                    usa_quartili = True

                # La stringa DEA e' un grafico disegnato con caratteri: utile
                # a chi guarda, illeggibile con la sintesi vocale. Resta
                # disponibile su richiesta, mentre l'andamento si ascolta con
                # la sonificazione, che porta la stessa informazione.
                if not enter_escape(
                    _(
                        "Vuoi anche la stringa DEA, il grafico in caratteri? (INVIO per si', ESC per no): "
                    )
                ):
                    continue

                if usa_quartili:
                    q1, q2, q3, q4 = dividi_in_quartili(selected_pts)
                    r1 = [item["rating"] for item in q1]
                    r2 = [item["rating"] for item in q2]
                    r3 = [item["rating"] for item in q3]
                    r4 = [item["rating"] for item in q4]

                    dea_q1 = calcola_dea(r1, emin_global, emax_global) if r1 else ""
                    dea_q2 = calcola_dea(r2, emin_global, emax_global) if r2 else ""
                    dea_q3 = calcola_dea(r3, emin_global, emax_global) if r3 else ""
                    dea_q4 = calcola_dea(r4, emin_global, emax_global) if r4 else ""

                    if dea_q1:
                        print_wrapped_dea("DEA-Q1", dea_q1)
                    if dea_q2:
                        print_wrapped_dea("DEA-Q2", dea_q2)
                    if dea_q3:
                        print_wrapped_dea("DEA-Q3", dea_q3)
                    if dea_q4:
                        print_wrapped_dea("DEA-Q4", dea_q4)
                else:
                    dea_unica = calcola_dea(ratings_subset, emin_global, emax_global)
                    print_wrapped_dea("DEA", dea_unica)

                enter_escape(_("\nPremi Invio per continuare..."))

        if choix_menu_abort:
            break
