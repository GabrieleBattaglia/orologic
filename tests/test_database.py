# Orologic, prove del database delle impostazioni (rilievi R7, R29 e R30
# della revisione 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il database in una cartella temporanea della prova: un errore di lettura
non e' corruzione e non fa scrivere i predefiniti; un file guasto va da
parte e si riparte dall'ultima copia buona; i salvataggi di piu' fili
insieme non si pestano i piedi."""

import builtins
import json
import os
import threading

import pytest

from orologic_modules import config, storage


@pytest.fixture
def database(tmp_path, monkeypatch):
    percorso = tmp_path / "orologic_db.json"
    monkeypatch.setattr(config, "DB_FILE", str(percorso))
    monkeypatch.setattr(storage, "PAUSA_FRA_I_TENTATIVI", 0)
    return percorso


def _scrivi(percorso, dati):
    percorso.write_text(json.dumps(dati), encoding="utf-8")


def test_un_errore_di_lettura_non_tocca_il_database(database, monkeypatch):
    _scrivi(database, {"launch_count": 77})
    vera = builtins.open
    tentativi = []

    def bloccata(file, *a, **k):
        if str(file) == str(database) and not a:
            tentativi.append(file)
            raise PermissionError("tenuto da un altro programma")
        return vera(file, *a, **k)

    monkeypatch.setattr(builtins, "open", bloccata)
    db = storage.UpdateDB(lambda d: d.update(launch_count=d["launch_count"] + 1))
    monkeypatch.setattr(builtins, "open", vera)
    assert isinstance(db, storage.DatabaseNonLetto)
    assert len(tentativi) == storage.TENTATIVI_DI_LETTURA
    # Il database vero e' rimasto com'era, e nessuna copia "danneggiata".
    assert json.loads(database.read_text(encoding="utf-8")) == {"launch_count": 77}
    assert [p.name for p in database.parent.iterdir()] == [database.name]
    assert not storage.SaveDB(db)


def test_un_errore_di_lettura_passeggero_si_riprova(database, monkeypatch):
    _scrivi(database, {"launch_count": 77})
    vera = builtins.open
    errori = [PermissionError("un attimo")]

    def una_volta(file, *a, **k):
        if str(file) == str(database) and not a and errori:
            raise errori.pop()
        return vera(file, *a, **k)

    monkeypatch.setattr(builtins, "open", una_volta)
    assert storage.LoadDB()["launch_count"] == 77


def test_il_file_guasto_riparte_dall_ultima_copia_buona(database, capsys):
    _scrivi(database, {"launch_count": 5})
    db = storage.LoadDB()
    assert storage.SaveDB(db)
    assert os.path.isfile(storage.copia_di_riserva())
    database.write_text("{ guasto", encoding="utf-8")
    ripreso = storage.LoadDB()
    assert ripreso["launch_count"] == 5
    assert "ultima copia buona" in capsys.readouterr().out
    assert any(p.name.startswith("orologic_db.json.danneggiato-") for p in database.parent.iterdir())
    # Il file vero e' tornato buono.
    assert json.loads(database.read_text(encoding="utf-8"))["launch_count"] == 5


def test_un_json_che_non_e_un_oggetto_e_un_guasto(database, capsys):
    _scrivi(database, [1, 2, 3])
    db = storage.LoadDB()
    assert db["clocks"] == []
    assert "non e' leggibile" in capsys.readouterr().out
    assert any(p.name.startswith("orologic_db.json.danneggiato-") for p in database.parent.iterdir())


def test_senza_copia_messa_da_parte_i_predefiniti_non_coprono_il_guasto(database, monkeypatch):
    database.write_text("{ guasto", encoding="utf-8")
    monkeypatch.setattr(storage, "metti_da_parte", lambda percorso: None)
    db = storage.UpdateDB(lambda d: d.update(launch_count=1))
    assert isinstance(db, storage.DatabaseNonLetto)
    assert database.read_text(encoding="utf-8") == "{ guasto"


def test_i_predefiniti_non_si_modificano_da_fuori(database):
    db = storage.LoadDB()
    db["clocks"].append({"name": "prova"})
    assert storage.DEFAULT_DB["clocks"] == []


def test_i_salvataggi_di_piu_fili_non_si_perdono(database):
    _scrivi(database, {"launch_count": 0})

    def conta():
        for _volta in range(20):
            storage.UpdateDB(lambda d: d.update(launch_count=d["launch_count"] + 1))

    fili = [threading.Thread(target=conta) for _filo in range(4)]
    for filo in fili:
        filo.start()
    for filo in fili:
        filo.join()
    assert storage.LoadDB()["launch_count"] == 80
    assert not [p.name for p in database.parent.iterdir() if p.name.endswith(".tmp")]
