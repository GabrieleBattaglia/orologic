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


def test_la_lettura_silenziosa_mette_da_parte_gli_avvisi(database, capsys):
    """R31: la prima lettura, all'importazione, avvisava nel vuoto della
    finestra; ora gli avvisi aspettano Main, che li dice dopo il benvenuto."""
    storage.avvisi_in_sospeso()
    database.write_text("{ guasto", encoding="utf-8")
    storage.LoadDB(silenziosa=True)
    assert capsys.readouterr().out == ""
    avvisi = storage.avvisi_in_sospeso()
    assert avvisi[0].startswith("Il database delle impostazioni non e' leggibile")
    assert storage.avvisi_in_sospeso() == []
    # Le letture di dopo parlano di nuovo.
    database.write_text("{ guasto", encoding="utf-8")
    storage.LoadDB()
    assert "non e' leggibile" in capsys.readouterr().out


def test_i_nomi_salvati_sono_solo_le_differenze():
    """R33: cambiando un nome si salvavano tutti i termini nella lingua del
    momento, che restavano anche passando a un'altra lingua."""
    from orologic_modules import localizzazione

    nomi = localizzazione.predefinito()
    nomi["pieces"]["rook"]["name"] = "rocca"
    nomi["columns"]["a"] = "Alfa"
    assert localizzazione.differenze(nomi) == {"pieces": {"rook": {"name": "rocca"}}, "columns": {"a": "Alfa"}}
    assert localizzazione.differenze(localizzazione.predefinito()) == {}


# R96, R97 e R98: i rilievi bassi.


def test_il_prompt_salvato_in_ansi_si_legge(tmp_path):
    from orologic_modules import modello_prompt

    file = tmp_path / "prompt.txt"
    file.write_bytes("$ commento\n{mossa} è qui\n".encode("cp1252"))
    assert modello_prompt.leggi_file(str(file)) == "{mossa} è qui"


def test_il_volume_e_i_predefiniti(database):
    _scrivi(database, {"volume": 7})
    assert storage.LoadDB()["volume"] == 1.0
    db, _scartati, _completati = storage._normalizza([1, 2])
    db["clocks"].append({"name": "x"})
    assert storage.DEFAULT_DB["clocks"] == []


def test_una_data_nel_futuro_non_e_negativa():
    import datetime

    from orologic_modules import tempo

    adesso = datetime.datetime.now()
    assert "-" not in tempo.fra_date(adesso + datetime.timedelta(hours=3), adesso)


def test_la_correzione_dell_arbitro_sposta_l_inizio_del_turno():
    from orologic_modules import board_utils, controlli

    stato = board_utils.GameState({"phases": [{"white_time": 60, "black_time": 60, "white_inc": 0, "black_inc": 0, "moves": 0, "tipo": "bronstein", "white_ritardo": 5, "black_ritardo": 5}]})
    controlli.inizio_partita(stato)
    prima = stato.controllo["white"]["inizio_turno"]
    controlli.corretto(stato, True, 30)
    assert stato.controllo["white"]["inizio_turno"] == prima + 30


def test_select_clock_dice_gli_orologi_a_parole(monkeypatch):
    """R99: SelectClock mostrava ancora la forma B=N F1:00:05:00+0."""
    from orologic_modules import clock

    mostrate = []
    monkeypatch.setattr(clock, "menu", lambda scelte, **k: mostrate.append(dict(scelte)) or None)
    db = {"clocks": [{"name": "Lampo", "same_time": True, "phases": [{"white_time": 300, "black_time": 300, "white_inc": 3, "black_inc": 3, "moves": 0}]}]}
    clock.SelectClock(db)
    voce = mostrate[0]["Lampo"]
    assert "B=N" not in voce and "F1:" not in voce and "5 minuti" in voce


def _con_la_riserva(database, dati):
    """Il database scritto e salvato una volta, cosi' c'e' anche la copia di
    riserva."""
    _scrivi(database, dati)
    assert storage.SaveDB(storage.LoadDB())
    assert os.path.isfile(storage.copia_di_riserva())


def test_il_database_che_manca_riparte_dalla_riserva(database, capsys):
    """R108: se orologic_db.json mancava e il .bak c'era, si partiva dai
    predefiniti, e il primo salvataggio copriva anche la riserva."""
    _con_la_riserva(database, {"launch_count": 77})
    database.unlink()
    db = storage.LoadDB()
    assert db["launch_count"] == 77
    assert "ultima copia buona" in capsys.readouterr().out
    assert json.loads(database.read_text(encoding="utf-8"))["launch_count"] == 77


def test_la_riserva_che_non_si_lascia_leggere_non_si_copre(database, monkeypatch):
    """R108: col database guasto e la riserva che in quel momento non si
    lasciava leggere, si ripartiva dai predefiniti e li si scriveva sopra la
    riserva buona."""
    _con_la_riserva(database, {"launch_count": 77})
    database.write_text("{ guasto", encoding="utf-8")
    vera = builtins.open
    riserva = storage.copia_di_riserva()

    def bloccata(file, *a, **k):
        if str(file) == riserva and not a:
            raise PermissionError("tenuta da un altro programma")
        return vera(file, *a, **k)

    monkeypatch.setattr(builtins, "open", bloccata)
    db = storage.UpdateDB(lambda d: d.update(launch_count=1))
    monkeypatch.setattr(builtins, "open", vera)
    assert isinstance(db, storage.DatabaseNonLetto)
    with open(riserva, encoding="utf-8") as file:
        assert json.load(file)["launch_count"] == 77


def test_il_database_dei_predefiniti_non_scrive_la_riserva(database):
    """R108: un database nato dai predefiniti, perche' il vero e la riserva
    erano guasti, non si scrive sopra la riserva."""
    _con_la_riserva(database, {"launch_count": 77})
    with open(storage.copia_di_riserva(), "w", encoding="utf-8") as file:
        file.write("{ guasta anche lei")
    database.write_text("{ guasto", encoding="utf-8")
    db = storage.LoadDB()
    assert isinstance(db, storage.DatabasePredefinito)
    assert storage.SaveDB(db)
    with open(storage.copia_di_riserva(), encoding="utf-8") as file:
        assert file.read() == "{ guasta anche lei"


def test_i_nomi_salvati_interi_di_prima_si_sfoltiscono(database):
    """R110: dalla 9.5.26 dei nomi si salvano solo le differenze, ma un
    database di prima teneva il dizionario intero, nella lingua di allora,
    e cambiando lingua pezzi, colonne e giudizi restavano nella vecchia. Al
    caricamento le voci uguali ai nomi di partenza di una lingua qualunque
    dei cataloghi si tolgono, una volta, e restano le scelte vere."""
    import gettext

    from orologic_modules import localizzazione

    inglese = gettext.translation("messages", localedir=config.CARTELLA_LOCALES, languages=["en"]).gettext
    intero = localizzazione.predefinito(inglese)
    assert intero["pieces"]["rook"]["name"] != localizzazione.predefinito()["pieces"]["rook"]["name"]
    intero["columns"]["a"] = "Arezzo"
    _scrivi(database, {"localization": intero})
    dizionario = localizzazione.carica()
    assert dizionario["pieces"]["rook"]["name"] == localizzazione.predefinito()["pieces"]["rook"]["name"]
    assert dizionario["columns"]["a"] == "Arezzo"
    assert storage.LoadDB()["localization"] == {"columns": {"a": "Arezzo"}}
    # Le sole differenze, salvate dopo la 9.5.26, restano come sono, anche
    # quando somigliano ai nomi di un'altra lingua.
    _scrivi(database, {"localization": {"pieces": {"rook": {"name": intero["pieces"]["rook"]["name"]}}}})
    assert localizzazione.carica()["pieces"]["rook"]["name"] == intero["pieces"]["rook"]["name"]
