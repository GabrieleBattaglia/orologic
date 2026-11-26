# Orologic: menu principale e avvio dell'applicazione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import atexit
import datetime
import json
import multiprocessing
import os
import sys
import warnings

# I processi della lettura dei PGN in parallelo, lettura_pgn.py, nel
# pacchetto compilato ripartono da questo file: qui fanno il loro lavoro ed
# escono, senza caricare il resto di Orologic ne' aprire finestre.
if __name__ == "__main__":
    multiprocessing.freeze_support()

from GBUtils import (
    Acusticator,
    Donazione,
    enter_escape,
    gestisci_aggiornamento,
    key,
    menu,
)

# Prima di config, che sceglie la lingua all'importazione: nella finestra la
# lingua del primo avvio si sceglie in una finestra, non in console (T5a).
if __name__ == "__main__":
    from orologic_modules import avvio

    avvio.prepara(sys.argv)

from orologic_modules import (
    aperture,
    board_utils,
    cleaner,
    clock,
    config,
    engine,
    game_flow,
    gioca,
    lichess_app,
    memoboard_app,
    modello_prompt,
    pgn_search,
    storage,
    strato,
    tempo,
    tempo_app,
    ui,
    version,
)
from orologic_modules.config import _, lingua_rilevata
from orologic_modules.easyfish import easyfish_app
from orologic_modules.temi import TEMI_MENU

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


# I temi dei menu stanno in orologic_modules/temi.py, perche' anche la
# finestra delle impostazioni li suoni uguali.


def menu_orologi():
    """Sottomenu degli orologi: crea, vedi, elimina.

    Le tre voci stavano nel menu principale in ordine sparso, fra le
    modalita' di gioco: qui stanno insieme e ci si puo' fare piu' di una
    cosa senza tornare indietro ogni volta.
    """
    while True:
        db = storage.LoadDB()
        scelta = menu(
            config.MENU_OROLOGI,
            show=True,
            keyslist=True,
            p=_("\nOrologi, scegli un'azione: "),
            numbered=db.get("menu_numerati", False),
        )
        if scelta is None or scelta == ".":
            return
        if scelta == "crea":
            _suona("crea")
            clock.CreateClock()
        elif scelta == "vedi":
            _suona("vedi")
            clock.ViewClocks()
        elif scelta == "elimina":
            _suona("elimina")
            clock.DeleteClock()


def _voci_impostazioni(db):
    """Le voci del sottomenu impostazioni, con lo stato attuale nell'etichetta.

    Chi ascolta il menu sa gia' com'e' messa ogni cosa senza doverci
    entrare: gli interruttori si girano scegliendo la voce, e al giro dopo
    il menu dice il valore nuovo.
    """
    salvataggio = _("attivo") if db.get("autosave_enabled") else _("non attivo")
    stile = _("numeri") if db.get("menu_numerati") else _("parole")
    return {
        "analisi": _("Analisi: tempo, linee e soglie di giudizio"),
        "motore": _("Motore scacchistico: {nome}").format(nome=engine.ENGINE_NAME),
        "nomi": _("Nomi dei pezzi, delle colonne e delle mosse"),
        "giocatore": _("Il mio nome: {nome}").format(
            nome=db.get("nome_utente") or _("non ancora scritto")
        ),
        "prompt": _("Prompt di gioco: {modello}").format(
            modello=modello_prompt.modello()
        ),
        "salvataggio": _("Salvataggio automatico: {stato}").format(stato=salvataggio),
        "stile": _("Stile dei menu: {stato}").format(stato=stile),
        "volume": _("Volume dei suoni: {vol}%").format(
            vol=round(config.VOLUME * 100)
        ),
        ".": _("Torna al menu principale"),
    }


def menu_impostazioni():
    """Sottomenu delle impostazioni: analisi, motore, nomi, prompt di gioco,
    interruttori, volume.

    Prima motore, nomi e volume stavano nel menu principale, e il resto era
    un'unica sequenza di domande da attraversare tutta per cambiare una
    cosa sola. Qui ogni voce fa una cosa, e si resta nel sottomenu finche'
    non si digita il punto, come per gli orologi.
    """
    while True:
        db = storage.LoadDB()
        scelta = menu(
            _voci_impostazioni(db),
            show=True,
            keyslist=True,
            p=_("\nImpostazioni, scegli una voce: "),
            numbered=db.get("menu_numerati", False),
        )
        if scelta is None or scelta == ".":
            return
        if scelta == "analisi":
            ui.ImpostazioniAnalisi()
        elif scelta == "motore":
            _suona("motore")
            engine.MenuMotore()
        elif scelta == "nomi":
            _suona("nomi")
            ui.EditLocalization()
        elif scelta == "prompt":
            modello_prompt.imposta()
        elif scelta == "giocatore":
            gioca.imposta_nome()
        elif scelta == "salvataggio":
            if ui.alterna_impostazione("autosave_enabled"):
                print(_("Salvataggio automatico attivo."))
            else:
                print(_("Salvataggio automatico non attivo."))
        elif scelta == "stile":
            if ui.alterna_impostazione("menu_numerati"):
                print(_("I menu sono a numeri."))
            else:
                print(_("I menu sono a parole."))
        elif scelta == "volume":
            ui.RegolaVolume()


def riprendi_dal_salvataggio(percorso):
    """La partita in sospeso del salvataggio automatico, letta da percorso,
    ricostruita e giocata."""
    # Nel try solo la lettura e la ricostruzione: un errore della
    # partita ripresa non e' un file illeggibile, e non deve
    # cancellarlo (rilievo R5 della revisione 2).
    try:
        with open(percorso, encoding="utf-8") as f:
            dati_partita = json.load(f)
        ripresa = game_flow.prepara_la_ripresa(dati_partita)
    # Il file di ripresa puo' essere di una versione precedente o
    # essere stato scritto a meta': si dice perche' e lo si mette da
    # parte, invece di non far partire il programma o di perderlo.
    except Exception as e:  # noqa: BLE001
        print(_("Impossibile ripristinare la partita: {e}").format(e=e))
        copia = storage.metti_da_parte(percorso)
        if copia:
            print(_("Il file di ripresa e' stato messo da parte: {copia}").format(copia=copia))
    else:
        game_flow.gioca_la_ripresa(*ripresa)


def _voci_del_menu_principale():
    """Le voci del menu principale; nella finestra anche archivi, PGN
    gestione archivi con pgn-extract (issue 74), e aperture, l'albero delle
    aperture di eco.pgn. L'ordine lo fa menu di GBUtils, alfabetico per
    chiave: aperture viene dopo analizza, archivi dopo arbitra."""
    if not strato.con_la_plancia():
        return config.MENU_CHOICES
    voci = {}
    for chiave, testo in config.MENU_CHOICES.items():
        voci[chiave] = testo
        if chiave == "ricerca":
            voci["archivi"] = config.VOCE_ARCHIVI
            voci["aperture"] = config.VOCE_APERTURE
    return voci


def _suona(voce):
    """Esegue il tema sonoro della voce di menu, se ne ha uno."""
    tema = TEMI_MENU.get(voce)
    if tema:
        tema()


def _incrementa_lanci(db):
    db["launch_count"] = db.get("launch_count", 0) + 1


# Le frasi che gestisci_aggiornamento di GBUtils dice durante l'aggiornamento.
# Stanno qui soltanto perche' pybabel le estragga nei cataloghi: il file
# babel.cfg guarda i sorgenti di Orologic e non la libreria. Devono restare
# identiche, carattere per carattere, a quelle scritte in GBUtils, altrimenti
# la traduzione non viene trovata e l'utente sente l'italiano.
FRASI_AGGIORNAMENTO_GBUTILS = (
    _("Controllo aggiornamenti."),
    _("Hai gia' l'ultima versione,"),
    _("Controllo non riuscito, si prosegue."),
    _("Disponibile la versione"),
    _("ma il pacchetto non e' ancora pronto."),
    _("Tu hai la"),
    _("Novita' di questa versione:"),
    _("Novita'"),
    _("Vuoi aggiornare adesso?"),
    _("Aggiornamento rimandato."),
    _("Scarico l'aggiornamento."),
    # Dalla V294 di GBUtils, gestisci_aggiornamento 1.3.2: prima restava in
    # italiano.
    _("{percento}%, {fatti} MB su {tutti}."),
    _("Aggiornamento pronto, il programma si chiude per applicarlo."),
    _("Aggiornamento non riuscito, si prosegue con questa versione."),
    _("Nessuna risposta."),
)


def Main():
    # Il motore va chiuso comunque vada: uscita dal menu, eccezione o
    # interruzione da tastiera. Senza questo, Stockfish resterebbe in
    # esecuzione come processo orfano. CloseEngine e' ripetibile senza danni.
    atexit.register(engine.CloseEngine)

    # Incremento contatore lanci
    db = storage.UpdateDB(_incrementa_lanci)

    SchermataIniziale()

    # Pulizia dei file vecchi, piu' vecchi del t scelto, 365 giorni se non
    # c'e': nella finestra si apre da sola la finestra della pulizia, nel
    # terminale l'avviso di sempre.
    giorni = cleaner.giorni_salvati()
    if strato.con_la_plancia():
        if cleaner.ci_sono_vecchi(giorni):
            strato.pulizia()
    else:
        cleaner.check_and_clean_old_files(days=giorni)

    # Aggiornamento automatico: la conversazione la conduce GBUtils, che
    # da sorgente tace e dal pacchetto compilato controlla, mostra le
    # novita' una pagina alla volta, chiede e scarica. Le sue frasi sono in
    # italiano e passano dal catalogo tramite traduci; restituisce vero
    # solo quando il programma deve chiudersi per farsi sostituire.
    api_url = "https://api.github.com/repos/GabrieleBattaglia/orologic/releases/latest"
    if gestisci_aggiornamento("orologic", version.VERSION, api_url, traduci=_):
        sys.exit(0)

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
            riprendi_dal_salvataggio(autosave_file_path)
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
            _voci_del_menu_principale(),
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

        elif scelta == "orologi":
            _suona("orologi")
            # Nella finestra gli orologi stanno tutti in una finestra sola.
            if strato.con_la_plancia():
                strato.orologi()
            else:
                menu_orologi()

        elif scelta == "easyfish":
            _suona("easyfish")
            easyfish_app.run()

        elif scelta == "gioca":
            _suona("gioca")
            gioca.menu_gioca()

        elif scelta == "lichess":
            _suona("lichess")
            lichess_app.run()

        elif scelta == "memoboard":
            _suona("memoboard")
            memoboard_app.main()

        elif scelta == "ricerca":
            _suona("ricerca")
            pgn_search.run()

        elif scelta == "archivi":
            _suona("archivi")
            strato.archivi_pgn()

        elif scelta == "aperture":
            _suona("aperture")
            aperture.run()

        elif scelta == "impostazioni":
            _suona("impostazioni")
            # Nella finestra le impostazioni stanno tutte in un luogo solo.
            if strato.con_la_plancia():
                strato.impostazioni()
            else:
                menu_impostazioni()

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


def esegui(con_la_finestra=False):
    """Orologic dall'inizio alla fine, uguale nel terminale e nella finestra.
    Nella finestra l'invito al caffe' non compare alla chiusura: nei
    programmi con finestra sta in un menu."""
    t_start = datetime.datetime.now()
    try:
        Main()
    except KeyboardInterrupt:
        print(_("\nInterruzione richiesta, chiudo Orologic."))
    saluta(t_start)
    if not con_la_finestra:
        Donazione(lang=lingua_rilevata)
    key(prompt=_("\nPremi un tasto per uscire..."), attesa=300)


if __name__ == "__main__":
    # Dalla 9.0.0 Orologic parte nella finestra; con --cli nel terminale,
    # come prima. Il programma e' lo stesso: cambia solo chi gli fa da
    # tastiera e da schermo, attraverso lo strato.
    if "--cli" in sys.argv:
        esegui()
    else:
        from orologic_modules import finestra

        finestra.avvia(lambda: esegui(con_la_finestra=True))
    sys.exit(0)
