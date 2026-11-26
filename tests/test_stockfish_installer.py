# Orologic, prove dell'installazione di Stockfish (rilievo R109 della
# verifica della revisione 2).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'aggiornamento di Stockfish sostituisce solo il programma: i file
dell'utente nella cartella del motore restano, anche nelle sottocartelle e
anche quando il nome comincia per stockfish. Il programma si riconosce
dall'elenco dei file del suo archivio, che l'installazione scrive accanto.
Lo scaricamento e' finto: l'archivio e' uno zip fatto qui, e la rete non si
tocca. La cartella del motore e' quella delle prove."""

import os
import shutil
import zipfile

import pytest

from orologic_modules import config, stockfish_installer

ESEGUIBILE = "stockfish-windows-x86-64-avx2.exe"


def _scrivi(percorso, testo):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "w", encoding="utf-8") as file:
        file.write(testo)


def _leggi(percorso):
    with open(percorso, encoding="utf-8") as file:
        return file.read()


def _archivio(percorso, file):
    with zipfile.ZipFile(percorso, "w") as zip_scritto:
        for nome, testo in file.items():
            zip_scritto.writestr(nome, testo)
    return percorso


@pytest.fixture
def motore(tmp_path, monkeypatch):
    cartella = config.percorso_salvataggio("engine")
    shutil.rmtree(cartella, ignore_errors=True)
    monkeypatch.setattr(stockfish_installer, "GetLatestStockfishURL", lambda: "https://example.invalid/stockfish.zip")
    scaricati = []

    def scarica(_indirizzo, percorso):
        shutil.copyfile(scaricati.pop(0), percorso)

    monkeypatch.setattr(stockfish_installer, "_scarica_file", scarica)
    yield cartella, scaricati, tmp_path
    for resto in (cartella, cartella + ".vecchio", cartella + ".nuovo"):
        shutil.rmtree(resto, ignore_errors=True)


def test_l_aggiornamento_tiene_i_file_dell_utente(motore):
    """R109: i file del programma si riconoscevano dal nome che comincia per
    stockfish, e solo nella radice della cartella: le note dell'utente, una
    versione tenuta apposta e un libro nella sottocartella del programma
    restavano nella cartella vecchia, che subito dopo si cancellava."""
    cartella, scaricati, tmp_path = motore
    # Stockfish installato da una versione di Orologic di prima, senza
    # l'elenco dell'archivio, e i file messi li' dall'utente.
    _scrivi(os.path.join(cartella, "stockfish", ESEGUIBILE), "vecchio")
    _scrivi(os.path.join(cartella, "stockfish", "AUTHORS"), "autori vecchi")
    _scrivi(os.path.join(cartella, "Stockfish_note.txt"), "le mie note")
    _scrivi(os.path.join(cartella, "stockfish-17", "stockfish-17.exe"), "tenuta apposta")
    _scrivi(os.path.join(cartella, "stockfish", "libri", "apertura.bin"), "il mio libro")
    scaricati.append(_archivio(tmp_path / "nuovo.zip", {f"stockfish/{ESEGUIBILE}": "nuovo", "stockfish/AUTHORS": "autori nuovi", "stockfish/README.md": "leggimi"}))
    radice, eseguibile = stockfish_installer.DownloadAndInstallEngine()
    assert (os.path.normcase(radice), eseguibile) == (os.path.normcase(os.path.join(cartella, "stockfish")), ESEGUIBILE)
    assert _leggi(os.path.join(cartella, "stockfish", ESEGUIBILE)) == "nuovo"
    assert _leggi(os.path.join(cartella, "stockfish", "AUTHORS")) == "autori nuovi"
    assert _leggi(os.path.join(cartella, "Stockfish_note.txt")) == "le mie note"
    assert _leggi(os.path.join(cartella, "stockfish-17", "stockfish-17.exe")) == "tenuta apposta"
    assert _leggi(os.path.join(cartella, "stockfish", "libri", "apertura.bin")) == "il mio libro"
    assert not os.path.exists(cartella + ".vecchio") and not os.path.exists(cartella + ".nuovo")
    # L'elenco dell'archivio sta accanto: all'aggiornamento dopo, un file
    # del programma che l'archivio nuovo non ha piu' se ne va, quelli
    # dell'utente restano.
    elenco = stockfish_installer.leggi_l_elenco(cartella)
    assert os.path.join("stockfish", "README.md") in elenco and "Stockfish_note.txt" not in elenco
    scaricati.append(_archivio(tmp_path / "dopo.zip", {f"stockfish/{ESEGUIBILE}": "dopo"}))
    stockfish_installer.DownloadAndInstallEngine()
    assert _leggi(os.path.join(cartella, "stockfish", ESEGUIBILE)) == "dopo"
    assert not os.path.exists(os.path.join(cartella, "stockfish", "README.md"))
    assert not os.path.exists(os.path.join(cartella, "stockfish", "AUTHORS"))
    assert _leggi(os.path.join(cartella, "Stockfish_note.txt")) == "le mie note"
    assert _leggi(os.path.join(cartella, "stockfish", "libri", "apertura.bin")) == "il mio libro"
