import atexit
import datetime
import json
import os
import sys
import time
import warnings

from dateutil.relativedelta import relativedelta
from orologic_modules import (
    board_utils,
    cleaner,
    clock,
    config,
    engine,
    game_flow,
    lichess_app,
    memoboard_app,
    pgn_search,
    storage,
    tempo_app,
    ui,
    version,
)
from orologic_modules.easyfish import easyfish_app

from GBUtils import (
    Acusticator,
    Donazione,
    dgt,
    enter_escape,
    key,
    menu,
    perform_update,
    polipo,
    update_checker,
)

warnings.filterwarnings(
    "ignore", message="urllib3 .* doesn't match a supported version!"
)

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(
    source_language="it",
    localedir=config.CARTELLA_LOCALES,
    config_path=config.CARTELLA_SETTINGS,
)


def OpenManual():
    manual_path = config.resource_path(os.path.join("resources", "readme.htm"))
    if os.path.exists(manual_path):
        try:
            if sys.platform == "win32":
                os.startfile(manual_path)
            else:
                import subprocess

                subprocess.run(
                    ["open" if sys.platform == "darwin" else "xdg-open", manual_path]
                )
        except Exception as e:
            print(_("Errore nell'apertura del manuale:"), e)
    else:
        print(_("Manuale non trovato in:"), manual_path)


def OpenChangelog():
    changelog_path = config.resource_path(os.path.join("resources", "changelog.htm"))
    if os.path.exists(changelog_path):
        try:
            if sys.platform == "win32":
                os.startfile(changelog_path)
            else:
                import subprocess

                subprocess.run(
                    ["open" if sys.platform == "darwin" else "xdg-open", changelog_path]
                )
        except Exception as e:
            print(_("Errore nell'apertura del changelog:"), e)
    else:
        print(_("Changelog non trovato in:"), changelog_path)


def _format_time_delta_parts(diff):
    parts = []
    if diff.years:
        parts.append(
            _("1 anno") if diff.years == 1 else _("{num} anni").format(num=diff.years)
        )
    if diff.months:
        parts.append(
            _("1 mese") if diff.months == 1 else _("{num} mesi").format(num=diff.months)
        )
    if diff.days:
        parts.append(
            _("1 giorno") if diff.days == 1 else _("{num} giorni").format(num=diff.days)
        )
    if diff.hours:
        parts.append(
            _("1 ora") if diff.hours == 1 else _("{num} ore").format(num=diff.hours)
        )
    if diff.minutes:
        parts.append(
            _("1 minuto")
            if diff.minutes == 1
            else _("{num} minuti").format(num=diff.minutes)
        )

    if not parts:
        return _("meno di un minuto")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + _(" e ") + parts[-1]


def SchermataIniziale():
    now = datetime.datetime.now()
    diff1 = relativedelta(now, version.BIRTH_DATE)
    diff2 = relativedelta(now, version.RELEASE_DATE)
    age_string = _format_time_delta_parts(diff1)
    release_string = _format_time_delta_parts(diff2)
    print(_("\nCiao! Benvenuto, sono Orologic e ho {age}.").format(age=age_string))
    print(
        _(
            "L'ultima versione e' la {version} ed e' stata rilasciata {release_date}."
        ).format(
            version=version.VERSION,
            release_date=config.format_date_italian(version.RELEASE_DATE),
        )
    )
    print(_("\tcioe': {release_ago} fa.").format(release_ago=release_string))
    print("\t\t" + _("Autore: ") + version.PROGRAMMER)
    print("\t\t\t" + _("Digita '?' per visualizzare il menu'."))
    Acusticator(
        [
            "c4",
            0.125,
            0,
            config.VOLUME,
            "d4",
            0.125,
            0,
            config.VOLUME,
            "e4",
            0.125,
            0,
            config.VOLUME,
            "g4",
            0.125,
            0,
            config.VOLUME,
            "a4",
            0.125,
            0,
            config.VOLUME,
            "e5",
            0.125,
            0,
            config.VOLUME,
            "p",
            0.125,
            0,
            0.5,
            "a5",
            0.125,
            0,
            config.VOLUME,
        ],
        kind=1,
        adsr=[0.01, 0, 100, 99],
    )


def _incrementa_lanci(db):
    db["launch_count"] = db.get("launch_count", 0) + 1


def Main():
    # Il motore va chiuso comunque vada: uscita dal menu, eccezione o
    # interruzione da tastiera. Senza questo, Stockfish resterebbe in
    # esecuzione come processo orfano. CloseEngine e' ripetibile senza danni.
    atexit.register(engine.CloseEngine)

    # Incremento contatore lanci
    db = storage.UpdateDB(_incrementa_lanci)

    SchermataIniziale()

    # Pulizia vecchi file
    cleaner.check_and_clean_old_files(days=365)

    # Auto-Updater
    if getattr(sys, "frozen", False):
        api_url = (
            "https://api.github.com/repos/GabrieleBattaglia/orologic/releases/latest"
        )
        has_update, new_ver, dl_url, _changelog = update_checker(
            version.VERSION, api_url
        )
        if has_update:
            if dl_url:
                print(_("\n*** AGGIORNAMENTO DISPONIBILE ***"))
                print(
                    _(
                        "E' disponibile la nuova versione {new_ver}! (Attuale: {curr_ver})"
                    ).format(new_ver=new_ver, curr_ver=version.VERSION)
                )
                if enter_escape(
                    _(
                        "Desideri scaricare e installare l'aggiornamento ora? (INVIO per si', ESC per ignorare): "
                    )
                ):
                    print(_("Download dell'aggiornamento in corso. Attendere prego..."))
                    if perform_update(dl_url, "orologic"):
                        print(
                            _(
                                "Aggiornamento pronto. Orologic si chiudera' per l'installazione..."
                            )
                        )
                        sys.exit(0)
                    else:
                        print(
                            _(
                                "Si e' verificato un errore durante la preparazione dell'aggiornamento."
                            )
                        )
            else:
                print(_("\n*** AGGIORNAMENTO DISPONIBILE ***"))
                print(
                    _(
                        "E' disponibile la nuova versione {new_ver}, ma i file di installazione non sono ancora pronti per il download."
                    ).format(new_ver=new_ver)
                )
                print(_("Riprova piu' tardi."))
        elif new_ver is None:
            print(_("\nImpossibile verificare gli aggiornamenti."))

    # Inizializzazione Motore (se configurato)
    if engine.InitEngine():
        from orologic_modules import stockfish_installer

        stockfish_installer.CheckForStockfishUpdatesSilent()

    # Controllo salvataggio automatico (Ripristino)
    autosave_file_path = config.percorso_salvataggio(
        os.path.join("settings", "autosave.json")
    )
    if db.get("autosave_enabled", False) and os.path.exists(autosave_file_path):
        print(_("\n*** RIPRISTINO PARTITA ***"))
        if enter_escape(
            _(
                "E' stata rilevata una partita di arbitraggio in sospeso. Desideri riprenderla? (INVIO per si', ESC per no): "
            )
        ):
            try:
                with open(autosave_file_path, "r", encoding="utf-8") as f:
                    dati_partita = json.load(f)
                game_flow.RiprendiPartita(dati_partita)
            except Exception as e:
                print(_("Impossibile ripristinare la partita: {e}").format(e=e))
                try:
                    os.remove(autosave_file_path)
                except Exception:
                    pass
        else:
            try:
                os.remove(autosave_file_path)
            except Exception:
                pass

    # Loop Principale
    while True:
        # Ricarico a ogni giro: le voci di menu possono aver salvato modifiche
        # e la copia in memoria sarebbe vecchia.
        db = storage.LoadDB()
        scelta = menu(
            config.MENU_CHOICES,
            show=True,
            keyslist=True,
            p=_("\nScegli un'azione: "),
            numbered=db.get("menu_numerati", False),
        )

        if scelta == ".":
            Acusticator(
                [
                    "g4",
                    0.15,
                    -0.5,
                    config.VOLUME,
                    "g4",
                    0.15,
                    0.5,
                    config.VOLUME,
                    "a4",
                    0.15,
                    -0.5,
                    config.VOLUME,
                    "g4",
                    0.15,
                    0.5,
                    config.VOLUME,
                    "p",
                    0.15,
                    0,
                    0,
                    "b4",
                    0.15,
                    -0.5,
                    config.VOLUME,
                    "c5",
                    0.3,
                    0.5,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[5, 0, 100, 5],
            )
            engine.CloseEngine()
            break

        elif scelta == "analizza":
            Acusticator(
                [
                    "a5",
                    0.04,
                    0,
                    config.VOLUME,
                    "e5",
                    0.04,
                    0,
                    config.VOLUME,
                    "p",
                    0.08,
                    0,
                    0,
                    "g5",
                    0.04,
                    0,
                    config.VOLUME,
                    "e6",
                    0.120,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 90, 0],
            )
            print(_("\nCaricamento partita dagli appunti..."))
            res = engine.LoadPGNFromClipboard()
            if res:
                pgn_da_analizzare, is_corrected = res
                if engine.ENGINE is None and not engine.InitEngine():
                    if enter_escape(
                        _(
                            "Il motore scacchistico non e' configurato. Vuoi configurarlo ora? (INVIO per si', ESC per no): "
                        )
                    ):
                        engine.MenuMotore()
                    if engine.ENGINE is None and not engine.InitEngine():
                        print(
                            _("Impossibile inizializzare il motore. Analisi annullata.")
                        )
                        continue
                engine.cache_analysis.clear()
                if ui.enter_escape(
                    _(
                        "Desideri l'analisi automatica? (INVIO per si', ESC per manuale): "
                    )
                ):
                    engine.AnalisiAutomatica(board_utils.CopyPgnGame(pgn_da_analizzare))
                else:
                    engine.AnalyzeGame(pgn_da_analizzare, is_corrected=is_corrected)

        elif scelta == "crea":
            Acusticator(
                [
                    1000.0,
                    0.05,
                    -1,
                    config.VOLUME,
                    "p",
                    0.05,
                    0,
                    0,
                    900.0,
                    0.05,
                    1,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[0, 0, 100, 0],
            )
            clock.CreateClock()

        elif scelta == "easyfish":
            Acusticator(
                ["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0.5, config.VOLUME], kind=1
            )
            easyfish_app.run()

        elif scelta == "lichess":
            Acusticator(
                ["g4", 0.1, 0, config.VOLUME, "c5", 0.2, 0, config.VOLUME], kind=1
            )
            lichess_app.run()

        elif scelta == "memoboard":
            Acusticator(
                [
                    "g4",
                    0.08,
                    0,
                    config.VOLUME,
                    "b4",
                    0.08,
                    0,
                    config.VOLUME,
                    "d5",
                    0.1,
                    0,
                    config.VOLUME,
                ],
                kind=1,
            )
            memoboard_app.main()

        elif scelta == "motore":
            Acusticator(
                [
                    "e7",
                    0.02,
                    0,
                    config.VOLUME,
                    "a6",
                    0.02,
                    0,
                    config.VOLUME,
                    "e7",
                    0.02,
                    0,
                    config.VOLUME,
                    "a6",
                    0.02,
                    0,
                    config.VOLUME,
                    "e7",
                    0.02,
                    0,
                    config.VOLUME,
                    "a6",
                    0.02,
                    0,
                    config.VOLUME,
                ]
            )
            engine.MenuMotore()

        elif scelta == "ricerca":
            Acusticator(
                [
                    "d5",
                    0.08,
                    -0.5,
                    config.VOLUME,
                    "a5",
                    0.08,
                    0,
                    config.VOLUME,
                    "f#5",
                    0.08,
                    0.5,
                    config.VOLUME,
                    "d6",
                    0.12,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 5, 90, 3],
            )
            pgn_search.run()

        elif scelta == "nomi":
            Acusticator(
                [
                    "c5",
                    0.1,
                    -1,
                    config.VOLUME,
                    "e5",
                    0.1,
                    -0.3,
                    config.VOLUME,
                    "g5",
                    0.1,
                    0.3,
                    config.VOLUME,
                    "c6",
                    0.1,
                    1,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[2, 8, 80, 10],
            )
            ui.EditLocalization()

        elif scelta == "impostazioni":
            Acusticator(
                ["a4", 0.2, 0, config.VOLUME, "c5", 0.2, 0, config.VOLUME],
                kind=1,
                adsr=[5, 5, 80, 10],
            )
            ui.Impostazioni()

        elif scelta == "arbitra":
            Acusticator(
                [
                    "c4",
                    0.2,
                    -1,
                    config.VOLUME,
                    "e4",
                    0.2,
                    -0.3,
                    config.VOLUME,
                    "g4",
                    0.2,
                    0.3,
                    config.VOLUME,
                    "c5",
                    0.4,
                    1,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[10, 5, 80, 5],
            )
            db = storage.LoadDB()
            clock_config = clock.SelectClock(db)
            if clock_config:
                game_flow.StartGame(clock_config)

        elif scelta == "tempo":
            Acusticator(
                [
                    "c4",
                    0.2,
                    -1,
                    config.VOLUME,
                    "e4",
                    0.2,
                    -0.3,
                    config.VOLUME,
                    "g4",
                    0.2,
                    0.3,
                    config.VOLUME,
                    "c5",
                    0.4,
                    1,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[10, 5, 80, 5],
            )
            db = storage.LoadDB()
            clock_config = clock.SelectClock(db)
            if clock_config:
                tempo_app.StartTempo(clock_config)

        elif scelta == "manuale":
            Acusticator(
                [400.0, 0.2, 0, config.VOLUME, 600.0, 0.2, 0, config.VOLUME],
                kind=1,
                adsr=[10, 10, 80, 10],
            )
            OpenManual()

        elif scelta == "novita":
            Acusticator(
                [400.0, 0.2, 0, config.VOLUME, 600.0, 0.2, 0, config.VOLUME],
                kind=1,
                adsr=[10, 10, 80, 10],
            )
            OpenChangelog()

        elif scelta == "vedi":
            Acusticator(
                [
                    1000.0,
                    0.1,
                    0,
                    config.VOLUME,
                    "p",
                    0.1,
                    0,
                    0,
                    1000.0,
                    0.1,
                    0,
                    config.VOLUME,
                ],
                kind=1,
                adsr=[0, 0, 100, 0],
            )
            clock.ViewClocks()

        elif scelta == "volume":
            print(_("\nRegolazione Volume"))
            print(_("Volume attuale: {vol:.0f}%").format(vol=config.VOLUME * 100))
            new_vol = dgt(
                _("Inserisci nuovo volume (0-100): "), kind="i", imin=0, imax=100
            )
            old_v = config.VOLUME
            config.VOLUME = new_vol / 100.0
            db = storage.SetValue("volume", config.VOLUME)
            Acusticator(["c5", 0.2, 0, old_v], sync=True)
            time.sleep(0.3)
            Acusticator(["c6", 0.2, 0, config.VOLUME])
            print(_("Volume impostato a {vol:.0f}%").format(vol=config.VOLUME * 100))

        elif scelta == "elimina":
            Acusticator([200.0, 0.5, 0, config.VOLUME], kind=2, adsr=[10, 10, 80, 10])
            clock.DeleteClock()


if __name__ == "__main__":
    t_start = datetime.datetime.now()
    try:
        Main()
    except KeyboardInterrupt:
        print(_("\nInterruzione richiesta, chiudo Orologic."))
    t_end = datetime.datetime.now()
    delta = relativedelta(t_end, t_start)
    comp = []
    if delta.days:
        comp.append(_("{n} giorni").format(n=delta.days))
    if delta.hours:
        comp.append(_("{n} ore").format(n=delta.hours))
    if delta.minutes:
        comp.append(_("{n} minuti").format(n=delta.minutes))
    if delta.seconds:
        comp.append(_("{n} secondi").format(n=delta.seconds))
    ms = delta.microseconds // 1000
    if ms:
        comp.append(_("{n} millisecondi").format(n=ms))
    durata = ", ".join(comp) if comp else _("0 millisecondi")

    db_f = storage.LoadDB()
    l_count = db_f.get("launch_count", _("sconosciuto"))
    print(
        _(
            "\nArrivederci da Orologic {v}.\nQuesta era la nostra {lc}a volta e ci siamo divertiti assieme per: {d}"
        ).format(v=version.VERSION, lc=l_count, d=durata)
    )
    Donazione(lang=lingua_rilevata)
    key(prompt=_("\nPremi un tasto per uscire..."), attesa=300)
    sys.exit(0)
