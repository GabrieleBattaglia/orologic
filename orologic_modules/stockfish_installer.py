# Orologic, modulo stockfish_installer: scarica e aggiorna il motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import os
import re
import shutil
import zipfile

from . import config, rete
from .config import _

API_RELEASE = (
    "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest"
)
# Il download del motore e' un file di parecchi megabyte: serve piu' respiro
# della normale interrogazione di un'API.
TIMEOUT_DOWNLOAD = 120.0
# I pacchetti per Windows a 64 bit, in ordine di preferenza. Dalla 19
# Stockfish pubblica un solo eseguibile universale, che riconosce da se' le
# istruzioni del processore; fino alla 18 le varianti erano separate e si
# sceglieva AVX2. Cercare soltanto avx2 ha reso la 19 invisibile.
PACCHETTI_WINDOWS = ("windows-x86-64-universal", "windows-x86-64-avx2")


def _asset_windows(dati):
    """Cerca fra gli allegati della release il pacchetto per Windows a 64 bit."""
    allegati = [
        (asset.get("name", "").lower(), asset.get("browser_download_url"))
        for asset in dati.get("assets", [])
    ]
    for cercato in PACCHETTI_WINDOWS:
        for nome, url in allegati:
            if cercato in nome and nome.endswith(".zip") and url:
                return url, nome
    return None, None


def _nome_release(dati):
    """Il nome leggibile della release, Stockfish 19, invece del tag sf_19."""
    return dati.get("name") or dati.get("tag_name") or "?"


def GetLatestStockfishURL():
    """Indirizzo dell'ultima versione di Stockfish per Windows a 64 bit."""
    print(_("Controllo ultima versione su GitHub..."))
    dati, errore = rete.leggi_json(API_RELEASE)
    if errore:
        print(
            _("Controllo della versione non riuscito. {motivo}").format(motivo=errore)
        )
        return None
    print(_("Ultima versione trovata: {v}").format(v=_nome_release(dati)))
    url, nome = _asset_windows(dati)
    if not url:
        print(_("Nessun pacchetto compatibile nell'ultima release."))
        return None
    print(_("Trovato pacchetto: {n}").format(n=nome))
    return url


def _estrai_in_sicurezza(archivio, destinazione):
    """Estrae lo zip rifiutando i percorsi che uscirebbero dalla cartella.

    Un archivio confezionato male, o malevolo, puo' contenere nomi con
    percorsi risalenti e scrivere altrove nel disco.
    """
    radice = os.path.abspath(destinazione)
    for elemento in archivio.namelist():
        completo = os.path.abspath(os.path.join(radice, elemento))
        if not completo.startswith(radice + os.sep) and completo != radice:
            raise ValueError(
                _("L'archivio contiene un percorso non valido: {p}").format(p=elemento)
            )
    archivio.extractall(radice)


def _scarica_file(url, destinazione):
    """Scarica a blocchi mostrando l'avanzamento a scatti radi.

    Niente barre disegnate con caratteri ripetuti: solo qualche riga di
    avanzamento, leggibile dalla sintesi vocale senza diventare invadente.
    """
    risposta, errore = rete.apri(url, timeout=TIMEOUT_DOWNLOAD)
    if errore:
        return errore
    try:
        with risposta as sorgente, open(destinazione, "wb") as f:
            totale = int(sorgente.headers.get("content-length", 0) or 0)
            scaricato = 0
            prossimo_avviso = 25
            while True:
                blocco = sorgente.read(65536)
                if not blocco:
                    break
                f.write(blocco)
                scaricato += len(blocco)
                if totale > 0:
                    percentuale = scaricato * 100 // totale
                    if percentuale >= prossimo_avviso:
                        print(
                            _("Scaricato il {p} per cento.").format(p=prossimo_avviso)
                        )
                        prossimo_avviso += 25
    except OSError as e:
        return _("Scaricamento interrotto: {motivo}").format(motivo=e)
    return None


def DownloadAndInstallEngine():
    """Scarica Stockfish e lo installa, restituendo (cartella, eseguibile).

    Il motore gia' presente viene sostituito soltanto quando il nuovo e'
    scaricato ed estratto: se qualcosa va storto per strada, quello vecchio
    resta al suo posto e continua a funzionare.
    """
    url = GetLatestStockfishURL() or config.STOCKFISH_DOWNLOAD_URL
    destinazione = config.percorso_salvataggio("engine")
    lavorazione = destinazione + ".nuovo"
    archivio = os.path.join(lavorazione, "stockfish.zip")

    try:
        shutil.rmtree(lavorazione, ignore_errors=True)
        os.makedirs(lavorazione, exist_ok=True)
    except OSError as e:
        print(
            _("Impossibile preparare la cartella di lavoro: {motivo}").format(motivo=e)
        )
        return None, None

    print(_("Scaricamento di Stockfish in corso, attendere."))
    errore = _scarica_file(url, archivio)
    if errore:
        print(_("Motore non aggiornato. {motivo}").format(motivo=errore))
        print(_("Il motore gia' installato resta invariato."))
        shutil.rmtree(lavorazione, ignore_errors=True)
        return None, None

    print(_("Scaricamento completato, estrazione in corso."))
    try:
        with zipfile.ZipFile(archivio, "r") as zip_ref:
            _estrai_in_sicurezza(zip_ref, lavorazione)
    except (zipfile.BadZipFile, ValueError, OSError) as e:
        print(_("Archivio non utilizzabile: {motivo}").format(motivo=e))
        print(_("Il motore gia' installato resta invariato."))
        shutil.rmtree(lavorazione, ignore_errors=True)
        return None, None

    try:
        os.remove(archivio)
    except OSError:
        pass

    eseguibile = None
    for radice, _cartelle, file_presenti in os.walk(lavorazione):
        for nome in file_presenti:
            if nome.lower().startswith("stockfish") and nome.lower().endswith(".exe"):
                eseguibile = (radice, nome)
                break
        if eseguibile:
            break

    if not eseguibile:
        print(_("Nell'archivio non c'e' l'eseguibile di Stockfish."))
        print(_("Il motore gia' installato resta invariato."))
        shutil.rmtree(lavorazione, ignore_errors=True)
        return None, None

    # Solo adesso, a nuovo motore pronto, si sostituisce il vecchio.
    cartella_relativa = os.path.relpath(eseguibile[0], lavorazione)
    vecchio = destinazione + ".vecchio"
    try:
        shutil.rmtree(vecchio, ignore_errors=True)
        if os.path.exists(destinazione):
            os.replace(destinazione, vecchio)
        os.replace(lavorazione, destinazione)
    except OSError as e:
        print(_("Sostituzione non riuscita: {motivo}").format(motivo=e))
        if os.path.exists(vecchio) and not os.path.exists(destinazione):
            os.replace(vecchio, destinazione)
            print(_("Ripristinato il motore precedente."))
        shutil.rmtree(lavorazione, ignore_errors=True)
        return None, None

    shutil.rmtree(vecchio, ignore_errors=True)
    cartella_finale = os.path.normpath(os.path.join(destinazione, cartella_relativa))
    print(_("Installazione di Stockfish completata."))
    return cartella_finale, eseguibile[1]


def _versione(testo):
    """Estrae la versione dal nome del motore, per esempio 17.1 da Stockfish 17.1.

    Prende il primo gruppo numerico: sommando tutte le cifre del nome, come si
    faceva prima, Stockfish 16 AVX2 64bit diventava 1664 e nessun
    aggiornamento risultava mai disponibile.
    """
    trovato = re.search(r"(\d+(?:\.\d+)*)", testo or "")
    if not trovato:
        return ()
    return tuple(int(x) for x in trovato.group(1).split("."))


def CheckForStockfishUpdatesSilent():
    """Se esiste una versione piu' recente di Stockfish, propone di installarla."""
    from GBUtils import enter_escape

    from . import engine, storage

    if not engine.ENGINE or "stockfish" not in engine.ENGINE_NAME.lower():
        return

    locale = _versione(engine.ENGINE_NAME)
    if not locale:
        return

    dati, errore = rete.leggi_json(API_RELEASE, timeout=5)
    if errore:
        # Controllo di cortesia all'avvio: non vale un allarme, ma nemmeno il
        # silenzio totale di prima, che nascondeva anche gli errori veri.
        print(
            _("Aggiornamenti del motore non verificati. {motivo}").format(motivo=errore)
        )
        return

    tag = dati.get("tag_name", "")
    remota = _versione(tag)
    if not remota or remota <= locale:
        return

    nuova = _nome_release(dati)
    url, _nome = _asset_windows(dati)
    if not url:
        # Senza un pacchetto riconosciuto l'aggiornamento non si puo'
        # proporre, ma va detto: e' questo silenzio che ha nascosto la 19,
        # pubblicata con un nome di pacchetto nuovo.
        print(
            _("E' uscito {nuova}, ma non riconosco il suo pacchetto per Windows.").format(
                nuova=nuova
            )
        )
        return

    print(_("Aggiornamento del motore disponibile."))
    print(
        _("Versione nuova: {new}. Installata: {curr}.").format(
            new=nuova, curr=engine.ENGINE_NAME
        )
    )
    if not enter_escape(
        _("Desideri aggiornare il motore ora? (INVIO per si', ESC per ignorare): ")
    ):
        return

    engine.CloseEngine()
    cartella, eseguibile = DownloadAndInstallEngine()
    if not (cartella and eseguibile):
        print(_("Aggiornamento non riuscito, riavvio il motore precedente."))
        engine.InitEngine()
        return

    percorso = os.path.join(cartella, eseguibile)
    base = config.percorso_salvataggio("")

    def aggiorna_motore(db):
        cfg = db.get("engine_config", {})
        try:
            cfg["engine_path"] = os.path.relpath(percorso, base)
            cfg["engine_is_relative"] = True
        except ValueError:
            cfg["engine_path"] = percorso
            cfg["engine_is_relative"] = False
        db["engine_config"] = cfg

    storage.UpdateDB(aggiorna_motore)
    print(_("Aggiornamento completato."))
    engine.InitEngine()
