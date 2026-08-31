# Orologic: menu principale e avvio dell'applicazione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import atexit
import datetime
import json
import os
import sys
import time
import warnings

from GBUtils import (
    Acusticator,
    Donazione,
    dgt,
    enter_escape,
    key,
    menu,
    perform_update,
    update_checker,
)

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
    tempo,
    tempo_app,
    ui,
    version,
)
from orologic_modules.config import _, lingua_rilevata
from orologic_modules.easyfish import easyfish_app

warnings.filterwarnings(
    "ignore", message="urllib3 .* doesn't match a supported version!"
)


def _apri_documento(nome_file, descrizione):
    """Apre un documento della cartella resources con il programma di sistema."""
    percorso = config.resource_path(os.path.join("resources", nome_file))
    if not os.path.exists(percorso):
        print(_("{cosa} non trovato in {dove}").format(cosa=descrizione, dove=percorso))
        return
    try:
        if sys.platform == "win32":
            os.startfile(percorso)
        else:
            import subprocess

            apri = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.run([apri, percorso], check=False)
    except OSError as e:
        print(
            _("Non riesco ad aprire {cosa}: {motivo}").format(
                cosa=descrizione, motivo=e
            )
        )


def OpenManual():
    _apri_documento("readme.htm", _("il manuale"))


def OpenChangelog():
    _apri_documento("changelog.htm", _("il changelog"))


def SchermataIniziale():
    now = datetime.datetime.now()
    age_string = tempo.fra_date(version.BIRTH_DATE, now)
    release_string = tempo.fra_date(version.RELEASE_DATE, now)
    print(_("Ciao! Benvenuto, sono Orologic e ho {age}.").format(age=age_string))
    print(
        _(
            "L'ultima versione e' la {version} ed e' stata rilasciata {release_date}."
        ).format(
            version=version.VERSION,
            release_date=config.format_date_italian(version.RELEASE_DATE),
        )
    )
    print(_("Cioe' {release_ago} fa.").format(release_ago=release_string))
    print(_("Autore: {autore}").format(autore=version.PROGRAMMER))
    print(_("Digita punto interrogativo per il menu."))
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


# Il suono che accompagna ogni voce del menu. Le sequenze erano scritte
# per esteso dentro i rami, nota per nota, per centinaia di righe.
TEMI_MENU = {
    ".": lambda: Acusticator(
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
    ),
    "analizza": lambda: Acusticator(
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
            0.12,
            0,
            config.VOLUME,
        ],
        kind=1,
        adsr=[2, 8, 90, 0],
    ),
    "crea": lambda: Acusticator(
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
    ),
    "easyfish": lambda: Acusticator(
        ["c5", 0.1, -0.5, config.VOLUME, "e5", 0.1, 0.5, config.VOLUME], kind=1
    ),
    "lichess": lambda: Acusticator(
        ["g4", 0.1, 0, config.VOLUME, "c5", 0.2, 0, config.VOLUME], kind=1
    ),
    "memoboard": lambda: Acusticator(
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
    ),
    "motore": lambda: Acusticator(
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
    ),
    "ricerca": lambda: Acusticator(
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
    ),
    "nomi": lambda: Acusticator(
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
    ),
    "impostazioni": lambda: Acusticator(
        ["a4", 0.2, 0, config.VOLUME, "c5", 0.2, 0, config.VOLUME],
        kind=1,
        adsr=[5, 5, 80, 10],
    ),
    "arbitra": lambda: Acusticator(
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
    ),
    "tempo": lambda: Acusticator(
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
    ),
    "manuale": lambda: Acusticator(
        [400.0, 0.2, 0, config.VOLUME, 600.0, 0.2, 0, config.VOLUME],
        kind=1,
        adsr=[10, 10, 80, 10],
    ),
    "novita": lambda: Acusticator(
        [400.0, 0.2, 0, config.VOLUME, 600.0, 0.2, 0, config.VOLUME],
        kind=1,
        adsr=[10, 10, 80, 10],
    ),
    "vedi": lambda: Acusticator(
        [1000.0, 0.1, 0, config.VOLUME, "p", 0.1, 0, 0, 1000.0, 0.1, 0, config.VOLUME],
        kind=1,
        adsr=[0, 0, 100, 0],
    ),
    "elimina": lambda: Acusticator(
        [200.0, 0.5, 0, config.VOLUME], kind=2, adsr=[10, 10, 80, 10]
    ),
}


def _suona(voce):
    """Esegue il tema sonoro della voce di menu, se ne ha uno."""
    tema = TEMI_MENU.get(voce)
    if tema:
        tema()


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
                print(_("\nAggiornamento disponibile."))
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
                print(_("\nAggiornamento disponibile."))
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
        print(_("\nRipristino della partita."))
        if enter_escape(
            _(
                "E' stata rilevata una partita di arbitraggio in sospeso. Desideri riprenderla? (INVIO per si', ESC per no): "
            )
        ):
            try:
                with open(autosave_file_path, encoding="utf-8") as f:
                    dati_partita = json.load(f)
                game_flow.RiprendiPartita(dati_partita)
            # Il file di ripresa puo' essere di una versione precedente o
            # essere stato scritto a meta': in ogni caso si dice perche' e
            # si riparte puliti, invece di non far partire il programma.
            except Exception as e:  # noqa: BLE001
                print(_("Impossibile ripristinare la partita: {e}").format(e=e))
                try:
                    os.remove(autosave_file_path)
                except OSError:
                    pass
        else:
            try:
                os.remove(autosave_file_path)
            except OSError:
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
            _suona(".")
            engine.CloseEngine()
            break

        elif scelta == "analizza":
            _suona("analizza")
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
            _suona("crea")
            clock.CreateClock()

        elif scelta == "easyfish":
            _suona("easyfish")
            easyfish_app.run()

        elif scelta == "lichess":
            _suona("lichess")
            lichess_app.run()

        elif scelta == "memoboard":
            _suona("memoboard")
            memoboard_app.main()

        elif scelta == "motore":
            _suona("motore")
            engine.MenuMotore()

        elif scelta == "ricerca":
            _suona("ricerca")
            pgn_search.run()

        elif scelta == "nomi":
            _suona("nomi")
            ui.EditLocalization()

        elif scelta == "impostazioni":
            _suona("impostazioni")
            ui.Impostazioni()

        elif scelta == "arbitra":
            _suona("arbitra")
            db = storage.LoadDB()
            clock_config = clock.SelectClock(db)
            if clock_config:
                game_flow.StartGame(clock_config)

        elif scelta == "tempo":
            _suona("tempo")
            db = storage.LoadDB()
            clock_config = clock.SelectClock(db)
            if clock_config:
                tempo_app.StartTempo(clock_config)

        elif scelta == "manuale":
            _suona("manuale")
            OpenManual()

        elif scelta == "novita":
            _suona("novita")
            OpenChangelog()

        elif scelta == "vedi":
            _suona("vedi")
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
            _suona("elimina")
            clock.DeleteClock()


def saluta(inizio, fine=None):
    """Saluta dicendo quante volte ci siamo visti e per quanto tempo.

    La durata la scrive tempo.fra_date, come tutte le altre del
    programma: prima questo blocco se la ricalcolava da solo.
    """
    fine = fine or datetime.datetime.now()
    durata = tempo.fra_date(inizio, fine, con_secondi=True)
    db_f = storage.LoadDB()
    l_count = db_f.get("launch_count", _("sconosciuto"))
    print(
        _(
            "\nArrivederci da Orologic {v}.\nQuesta era la nostra {lc}a volta e ci siamo divertiti assieme per: {d}"
        ).format(v=version.VERSION, lc=l_count, d=durata)
    )


if __name__ == "__main__":
    t_start = datetime.datetime.now()
    try:
        Main()
    except KeyboardInterrupt:
        print(_("\nInterruzione richiesta, chiudo Orologic."))
    saluta(t_start)
    Donazione(lang=lingua_rilevata)
    key(prompt=_("\nPremi un tasto per uscire..."), attesa=300)
    sys.exit(0)
