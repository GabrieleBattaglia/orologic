import os
import sys
import requests
import zipfile
from GBUtils import polipo
from . import config

# Inizializzazione localizzazione per questo modulo
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

def GetLatestStockfishURL():
    """
    Ottiene l'URL di download dell'ultima versione di Stockfish per Windows AVX2 tramite API GitHub.
    """
    try:
        api_url = "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest"
        print(_("Controllo ultima versione su GitHub..."))
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        
        tag_name = data.get("tag_name", "Sconosciuta")
        print(_("Ultima versione trovata: {v}").format(v=tag_name))
        
        for asset in data.get("assets", []):
            name = asset.get("name", "").lower()
            # Criteri di ricerca per l'asset corretto: windows, avx2 e zip
            # Nota: Stockfish a volte usa 'win' o 'windows' nel nome
            if "windows" in name and "avx2" in name and name.endswith(".zip"):
                download_url = asset.get("browser_download_url")
                print(_("Trovato asset: {n}").format(n=name))
                return download_url
                
        print(_("Nessun asset compatibile trovato nell'ultima release."))
        return None

    except Exception as e:
        print(_("Errore durante il controllo della versione: {e}").format(e=e))
        return None

def DownloadAndInstallEngine():
    """
    Scarica Stockfish, lo estrae in una cartella locale e restituisce il percorso all'eseguibile.
    """
    try:
        # Recupera URL dinamico
        download_url = GetLatestStockfishURL()
        
        # Fallback al config se l'API fallisce (o se l'utente preferisce un override statico)
        if not download_url:
            print(_("Tentativo con URL di fallback..."))
            download_url = config.STOCKFISH_DOWNLOAD_URL

        # Definisce il percorso di installazione locale nella cartella del progetto
        install_path = config.percorso_salvataggio("engine")
        
        # PULIZIA: Rimuove versioni precedenti per evitare conflitti
        if os.path.exists(install_path):
            try:
                print(_("Rimozione versioni precedenti..."))
                for filename in os.listdir(install_path):
                    file_path = os.path.join(install_path, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            import shutil
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(_("Impossibile rimuovere {file}: {e}").format(file=file_path, e=e))
            except Exception as e:
                 print(_("Errore durante la pulizia della cartella: {e}").format(e=e))
        else:
            os.makedirs(install_path)
            
        zip_filename = os.path.join(install_path, "stockfish.zip")
        
        # 1. Download
        print(_("\nSto scaricando Stockfish da {url}...").format(url=download_url))
        response = requests.get(download_url, stream=True)
        response.raise_for_status() # Verifica errori HTTP
        
        with open(zip_filename, "wb") as f:
            total_length = int(response.headers.get('content-length', 0))
            downloaded = 0
            for chunk in response.iter_content(chunk_size=4096):
                downloaded += len(chunk)
                f.write(chunk)
                if total_length > 0:
                    done = int(50 * downloaded / total_length)
                    sys.stdout.write("\r[{}{}] {:.1f}%".format('=' * done, ' ' * (50-done), (downloaded/total_length)*100))
                    sys.stdout.flush()
        
        print("\n" + _("Download completato."))
        
        # 2. Estrazione
        print(_("...sto estraendo i file..."))
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(install_path)
        print(_("Estrazione completata."))
        
        # Pulizia file zip
        try:
            os.remove(zip_filename)
        except OSError:
            pass

        # 3. Trova l'eseguibile dentro la cartella appena estratta
        for root, dirs, files in os.walk(install_path):
            for file in files:
                if file.lower().startswith("stockfish") and file.lower().endswith(".exe"):
                    print(_("Installazione di Stockfish completata con successo!"))
                    return root, file # Restituisce cartella ed eseguibile

    except requests.exceptions.RequestException as e:
        print(_("\nErrore di rete durante il download: {error}").format(error=e))
    except zipfile.BadZipFile:
        print(_("\nErrore: Il file scaricato non e' uno zip valido."))
    except Exception as e:
        print(_("\nSi e' verificato un errore imprevisto durante l'installazione: {error}").format(error=e))
        
    return None, None
