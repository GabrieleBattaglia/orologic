import os
import time
from .config import percorso_salvataggio, L10N

def _(testo):
    return L10N.get(testo, testo)

def check_and_clean_old_files(days=365):
    """
    Controlla le cartelle specificate per file più vecchi di `days` giorni.
    Permette all'utente di vederli, cancellarli o ignorare l'avviso aggiornando
    la data di modifica.
    """
    dirs_to_check = ["pgn", "txt", "images"]
    cutoff_time = time.time() - (days * 86400)
    
    for d in dirs_to_check:
        folder_path = percorso_salvataggio(d)
        if not os.path.exists(folder_path):
            continue
            
        old_files = []
        try:
            for f in os.listdir(folder_path):
                filepath = os.path.join(folder_path, f)
                if os.path.isfile(filepath):
                    try:
                        mtime = os.path.getmtime(filepath)
                        if mtime < cutoff_time:
                            old_files.append(filepath)
                    except OSError:
                        pass
        except OSError:
            continue
                    
        if old_files:
            while True:
                print(_("\nAttenzione: la cartella '{d}' contiene {n} file piu' vecchi di {days} giorni.").format(d=d, n=len(old_files), days=days))
                print(_("Vuoi (v)edere la lista, (c)ancellarli, o (i)gnorare questo avviso?"))
                choice = input("> ").strip().lower()
                
                if choice == 'v':
                    print(_("\nLista file:"))
                    for f in old_files:
                        print(f" - {os.path.basename(f)}")
                    print() # Riga vuota
                elif choice == 'c':
                    from GBUtils import Acusticator
                    from . import config
                    Acusticator(["c5", 0.1, -1, config.VOLUME, "c5", 0.1, 1, config.VOLUME], kind=1)
                    deleted = 0
                    for f in old_files:
                        try:
                            os.remove(f)
                            deleted += 1
                        except OSError as e:
                            print(_("Errore durante l'eliminazione di {f}: {e}").format(f=os.path.basename(f), e=e))
                    print(_("Cancellati {d} file su {t}.").format(d=deleted, t=len(old_files)))
                    break
                elif choice == 'i':
                    current_time = time.time()
                    for f in old_files:
                        try:
                            os.utime(f, (current_time, current_time))
                        except OSError:
                            pass
                    print(_("Avviso ignorato. La data di modifica dei file e' stata aggiornata."))
                    break
                else:
                    print(_("Scelta non valida. Premi v, c, oppure i."))
