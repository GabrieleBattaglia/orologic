# Orologic, manutenzione: cancellazione dei file datati.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import os
import time

from GBUtils import enter_escape, key

from . import storage
from .config import _, percorso_salvataggio

# Le cartelle dove i file si accumulano: le partite, i resoconti e le
# immagini e i PDF di Easyfish. In settings ci sono le impostazioni, e li'
# non si pulisce.
CARTELLE = ("pgn", "txt", "images")
CHIAVE_GIORNI = "pulizia_giorni"
GIORNI_PREDEFINITI = 365
# I valori di t, a passi di due mesi da due mesi a tre anni (scelta di
# Gabriele): un mese e' un dodicesimo di 365 giorni, cosi' un anno e' 365
# giorni e tre anni 1095.
MESI = tuple(range(2, 37, 2))


def giorni_di(mesi):
    return round(mesi * 365 / 12)


VALORI_DEI_GIORNI = tuple(giorni_di(mesi) for mesi in MESI)


def durata_in_mesi(mesi):
    """Due mesi, un anno, un anno e due mesi, tre anni."""
    anni, resto = divmod(mesi, 12)
    parti = []
    if anni:
        parti.append(_("1 anno") if anni == 1 else _("{n} anni").format(n=anni))
    if resto:
        parti.append(_("1 mese") if resto == 1 else _("{n} mesi").format(n=resto))
    return _(" e ").join(parti)


def durata_dei_giorni(giorni):
    """La durata di un valore di t, come durata_in_mesi."""
    for mesi in MESI:
        if giorni_di(mesi) == giorni:
            return durata_in_mesi(mesi)
    return _("{n} giorni").format(n=giorni)


def giorni_salvati():
    """Il t scelto, salvato nel database; 365 se non c'e'."""
    valore = storage.LoadDB().get(CHIAVE_GIORNI)
    return valore if valore in VALORI_DEI_GIORNI else GIORNI_PREDEFINITI


def salva_giorni(giorni):
    storage.SetValue(CHIAVE_GIORNI, giorni)


def cartella(nome):
    return percorso_salvataggio(nome)


def file_accumulati():
    """I file delle cartelle, dal piu' vecchio: dizionari con percorso,
    nome, cartella, peso in byte e data, quella dell'ultima modifica."""
    trovati = []
    for nome_della_cartella in CARTELLE:
        percorso = cartella(nome_della_cartella)
        try:
            nomi = os.listdir(percorso)
        except OSError:
            continue
        for nome in nomi:
            completo = os.path.join(percorso, nome)
            try:
                if not os.path.isfile(completo):
                    continue
                informazioni = os.stat(completo)
            except OSError:
                continue
            trovati.append({"percorso": completo, "nome": nome, "cartella": nome_della_cartella,
                            "peso": informazioni.st_size, "data": informazioni.st_mtime})
    return sorted(trovati, key=lambda file: (file["data"], file["nome"]))


def vecchi(files, giorni, adesso=None):
    """I file piu' vecchi di giorni."""
    limite = (time.time() if adesso is None else adesso) - giorni * 86400
    return [file for file in files if file["data"] < limite]


def ci_sono_vecchi(giorni):
    return bool(vecchi(file_accumulati(), giorni))


def ripristina_date(files):
    """La data dei file torna a oggi, cosi' non sono piu' vecchi: l'avviso
    ignorato del terminale. Restituisce quanti."""
    adesso = time.time()
    fatti = 0
    for file in files:
        try:
            os.utime(file["percorso"], (adesso, adesso))
            fatti += 1
        except OSError:
            pass
    return fatti


def check_and_clean_old_files(days=365):
    """
    Controlla le cartelle specificate per file più vecchi di `days` giorni.
    Permette all'utente di vederli, cancellarli o ignorare l'avviso aggiornando
    la data di modifica.
    """
    dirs_to_check = CARTELLE
    cutoff_time = time.time() - (days * 86400)

    for d in dirs_to_check:
        folder_path = cartella(d)
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
                print(
                    _(
                        "Attenzione: la cartella '{d}' contiene {n} file piu' vecchi di {days} giorni."
                    ).format(d=d, n=len(old_files), days=days)
                )
                print(
                    _(
                        "Vuoi (v)edere la lista, (c)ancellarli, o (i)gnorare questo avviso?"
                    )
                )
                choice = key(_("Scegli v, c oppure i: ")).strip().lower()

                if choice == "v":
                    print(_("Lista file:"))
                    for f in old_files:
                        print(f" - {os.path.basename(f)}")
                elif choice == "c":
                    if not enter_escape(
                        _(
                            "Confermi la cancellazione di {n} file? Non si torna indietro. INVIO per si', ESC per no: "
                        ).format(n=len(old_files))
                    ):
                        print(_("Cancellazione annullata."))
                        continue
                    from GBUtils import Acusticator

                    from . import config

                    Acusticator(
                        ["c5", 0.1, -1, config.VOLUME, "c5", 0.1, 1, config.VOLUME],
                        kind=1,
                    )
                    deleted = 0
                    for f in old_files:
                        try:
                            os.remove(f)
                            deleted += 1
                        except OSError as e:
                            print(
                                _("Errore durante l'eliminazione di {f}: {e}").format(
                                    f=os.path.basename(f), e=e
                                )
                            )
                    print(
                        _("Cancellati {d} file su {t}.").format(
                            d=deleted, t=len(old_files)
                        )
                    )
                    break
                elif choice == "i":
                    current_time = time.time()
                    for f in old_files:
                        try:
                            os.utime(f, (current_time, current_time))
                        except OSError:
                            pass
                    print(
                        _(
                            "Avviso ignorato. La data di modifica dei file e' stata aggiornata."
                        )
                    )
                    break
                else:
                    print(_("Scelta non valida. Premi v, c, oppure i."))
