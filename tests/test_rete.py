# Orologic, prove degli strumenti di rete (rilievi R34 e R35 della revisione
# 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Niente rete vera: gli indirizzi si controllano nella richiesta preparata,
e gli errori si fingono sostituendo urlopen."""

import email.message
import http.client
import io
import urllib.error

import pytest

from orologic_modules import rete


@pytest.fixture(autouse=True)
def senza_freno():
    rete.azzera_limite()
    yield
    rete.azzera_limite()


def test_i_nomi_con_spazi_e_accenti_si_codificano():
    richiesta = rete.prepara("https://lichess.org/api/user/Mario Rossè?x=1&y=a%20b")
    assert richiesta.full_url == "https://lichess.org/api/user/Mario%20Ross%C3%A8?x=1&y=a%20b"


def test_il_429_con_un_corpo_mette_il_freno():
    corpo = io.BytesIO(b'{"error": "Too many requests"}')
    errore = urllib.error.HTTPError("https://lichess.org/api/x", 429, "Too Many Requests", email.message.Message(), corpo)
    messaggio = rete._messaggio_http(errore)
    assert "limitando le richieste" in messaggio
    assert rete.attesa_residua() > 0


@pytest.mark.parametrize("errore", [http.client.IncompleteRead(b""), http.client.InvalidURL("x"), UnicodeEncodeError("ascii", "è", 0, 1, "no")])
def test_gli_errori_del_protocollo_non_fanno_cadere(monkeypatch, errore):
    def guasto(*a, **k):
        raise errore

    monkeypatch.setattr(rete.urllib.request, "urlopen", guasto)
    risposta, messaggio = rete.apri("https://lichess.org/api/x")
    assert risposta is None and messaggio.startswith("Connessione non riuscita")


def test_una_lettura_interrotta_a_meta(monkeypatch):
    class Risposta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            raise http.client.IncompleteRead(b"mezzo")

    monkeypatch.setattr(rete.urllib.request, "urlopen", lambda *a, **k: Risposta())
    testo, messaggio = rete.leggi("https://lichess.org/api/x")
    assert testo is None and messaggio.startswith("Lettura interrotta")


def test_gli_errori_degli_altri_server_non_parlano_di_lichess():
    errore = urllib.error.HTTPError("https://api.github.com/repos/x", 403, "Forbidden", email.message.Message(), io.BytesIO(b""))
    assert rete._messaggio_http(errore) == "Il server ha risposto con l'errore 403."
    errore = urllib.error.HTTPError("https://api.github.com/repos/x", 429, "Too Many", email.message.Message(), io.BytesIO(b""))
    rete._messaggio_http(errore)
    assert rete.attesa_residua() == 0


@pytest.mark.parametrize(
    ("indirizzo", "atteso"),
    [
        ("https://lichess.org/api/games/user/x", True),
        ("https://www.lichess.org/abc", True),
        ("https://lichess.org.altro.example/x", False),
        ("http://lichess.org/x", False),
        ("https://altro.example/?lichess.org", False),
    ],
)
def test_il_token_solo_a_lichess(indirizzo, atteso):
    assert rete.e_di_lichess(indirizzo) is atteso


def test_la_ricerca_manda_il_token_solo_a_lichess(monkeypatch):
    """R39: la ricerca PGN aggiungeva il token a ogni indirizzo con la
    scritta lichess.org."""
    from orologic_modules import lichess_app, pgn_search

    richieste = []
    monkeypatch.setattr(lichess_app, "load_secrets", lambda: {"lichess_token": "segreto"})
    monkeypatch.setattr(pgn_search.urllib.request, "urlopen", lambda richiesta, **k: richieste.append(richiesta))
    pgn_search._apri_indirizzo("https://lichess.org.altro.example/partite.pgn")
    pgn_search._apri_indirizzo("https://lichess.org/api/games/user/x")
    assert [r.get_header("Authorization") for r in richieste] == [None, "Bearer segreto"]


# R38: le credenziali di Lichess.


def test_le_credenziali_si_scrivono_solo_se_cambiano(tmp_path, monkeypatch):
    from orologic_modules import lichess_app, storage

    monkeypatch.setattr(lichess_app, "SECRETS_FILE", str(tmp_path / "secrets.json"))
    scritture = []
    vera = storage.scrivi_json
    monkeypatch.setattr(storage, "scrivi_json", lambda percorso, dati, **k: (scritture.append(dati), vera(percorso, dati, **k)))
    lichess_app.save_secrets({"lichess_token": "t", "lichess_username": "u"})
    lichess_app.save_secrets({"lichess_token": "t", "lichess_username": "u"})
    assert len(scritture) == 1
    assert lichess_app.load_secrets() == {"lichess_token": "t", "lichess_username": "u"}


def test_le_credenziali_guaste_vanno_da_parte(tmp_path, monkeypatch, capsys):
    from orologic_modules import lichess_app

    file = tmp_path / "secrets.json"
    file.write_text("{ guasto", encoding="utf-8")
    monkeypatch.setattr(lichess_app, "SECRETS_FILE", str(file))
    assert lichess_app.load_secrets() == {}
    assert "messe da parte" in capsys.readouterr().out
    assert any(p.name.startswith("secrets.json.danneggiato-") for p in tmp_path.iterdir())
    assert lichess_app.load_secrets() == {}


# R58: i punteggi di Memoboard.


def test_un_record_guasto_non_fa_perdere_le_classifiche(tmp_path, monkeypatch):
    import json

    from orologic_modules import memoboard_app

    file = tmp_path / "memoboard_scores.json"
    dati = {"colors": [{"username": "gabry", "net_per_minute": 12.5}, {"username": "rotto", "net_per_minute": "tanti"}], "knights": [], "bishops": [], "mixed": []}
    file.write_text(json.dumps(dati), encoding="utf-8")
    monkeypatch.setattr(memoboard_app, "SCORES_FILE", str(file))
    punteggi = memoboard_app.load_scores()
    assert [r["username"] for r in punteggi["colors"]] == ["Gabry"]
    assert [p.name for p in tmp_path.iterdir()] == ["memoboard_scores.json"]


def test_senza_copia_il_file_dei_punteggi_non_si_copre(tmp_path, monkeypatch):
    from orologic_modules import memoboard_app, storage

    file = tmp_path / "memoboard_scores.json"
    file.write_text("{ guasto", encoding="utf-8")
    monkeypatch.setattr(memoboard_app, "SCORES_FILE", str(file))
    monkeypatch.setattr(storage, "metti_da_parte", lambda percorso: None)
    monkeypatch.setitem(memoboard_app._PUNTEGGI, "non_letti", False)
    memoboard_app.save_scores(memoboard_app.load_scores())
    assert file.read_text(encoding="utf-8") == "{ guasto"


def test_l_alfiere_sorteggia_prima_la_casa():
    """R59: le diagonali da due case uscivano nel 15% delle domande."""
    import random

    from orologic_modules import memoboard_app

    random.seed(59)
    corte = {"A7", "B8", "G1", "H2", "A2", "B1", "G8", "H7"}
    domande = [memoboard_app.case_dell_alfiere() for _volta in range(4000)]
    for sq1, sq2, sono in domande:
        stessa = any(sq1 in linea and sq2 in linea for linea in memoboard_app.diagonals.values())
        assert sq1 != sq2 and stessa == sono
    gia_corte = sum(1 for sq1, sq2, sono in domande if sono and {sq1, sq2} <= corte)
    assert gia_corte / 4000 < 0.03


# R80: il flusso degli eventi di Lichess.


def test_il_token_revocato_ferma_l_ascolto_e_si_dice(monkeypatch, capsys):
    import threading

    from orologic_modules import lichess_eventi
    from orologic_modules.config import _

    chiamate = []
    revocato = lichess_eventi.rete.ErroreDiRete(_("Il token di accesso non e' piu' valido: rifai il login a Lichess."), 401)
    monkeypatch.setattr(lichess_eventi.rete, "apri", lambda *a, **k: chiamate.append(1) or (None, revocato))
    monkeypatch.setattr(lichess_eventi, "ATTESA_DOPO_ERRORE", 0)
    filo = threading.Thread(target=lichess_eventi._ascolta, args=("token", "io", threading.Event()))
    filo.start()
    filo.join(3)
    assert not filo.is_alive() and chiamate == [1]
    assert "non arrivano piu'" in capsys.readouterr().out


def test_dopo_una_chiusura_pulita_si_riparte_subito(monkeypatch):
    """R80, con R122: dopo un flusso rimasto aperto, qui finto con una durata
    minima di zero secondi."""
    import contextlib
    import threading
    import time

    from orologic_modules import lichess_eventi

    monkeypatch.setattr(lichess_eventi, "FLUSSO_DURATO", 0)
    aperture = []
    ferma = threading.Event()

    def apri(*a, **k):
        aperture.append(time.monotonic())
        if len(aperture) == 2:
            ferma.set()
        return contextlib.nullcontext(iter([])), None

    monkeypatch.setattr(lichess_eventi.rete, "apri", apri)
    monkeypatch.setattr(lichess_eventi, "ATTESA_DOPO_LA_CHIUSURA", 0.05)
    filo = threading.Thread(target=lichess_eventi._ascolta, args=("token", "io", ferma))
    filo.start()
    filo.join(5)
    assert len(aperture) == 2 and aperture[1] - aperture[0] < 2


def test_gli_amici_hanno_lo_stato_online(monkeypatch):
    """R82: l'elenco dei seguiti non porta il campo online, e tutti
    risultavano sempre Offline."""
    from orologic_modules import lichess_app

    monkeypatch.setattr(lichess_app.rete, "leggi_righe_json", lambda *a, **k: ([{"id": "gabry", "username": "Gabry"}, {"id": "anna", "username": "Anna"}], None))
    chiesti = []

    def stato(indirizzo, **k):
        chiesti.append(indirizzo)
        return [{"id": "gabry", "online": True, "playingId": "AbCd1234"}, {"id": "anna"}], None

    monkeypatch.setattr(lichess_app.rete, "leggi_json", stato)
    amici = lichess_app.fetch_following("token")
    assert chiesti[0].endswith("ids=gabry,anna")
    assert amici[0]["online"] and amici[0]["playing"] == "https://lichess.org/AbCd1234"
    assert not amici[1]["online"] and "playing" not in amici[1]
    assert lichess_app.id_della_partita(amici[0]["playing"]) == "AbCd1234"


# R81: le squadre di una battaglia a squadre.


def test_le_squadre_nelle_varie_forme():
    from orologic_modules import lichess_tornei

    trova = lichess_tornei.squadre_del_torneo
    assert trova({"teamBattle": {"teams": {"a": "Alfa"}}}) == {"a": "Alfa"}
    assert trova({"teamBattle": {"teams": [["a", "Alfa"], ["b", "Beta"]]}}) == {"a": "Alfa", "b": "Beta"}
    assert trova({"teamBattle": {"teams": ["a", "b"]}}) == {"a": "a", "b": "b"}
    assert trova({"teamBattle": {"teams": [{"id": "a", "name": "Alfa"}]}}) == {"a": "Alfa"}
    assert trova({}) == {}


def test_le_cadenze_della_board_api():
    """R75: le sfide non controllavano la cadenza, mentre la Board API
    gioca solo rapid, classica e corrispondenza, e il blitz nelle sfide
    dirette."""
    from orologic_modules import lichess_app

    motivo = lichess_app.motivo_della_cadenza
    assert motivo(600, 0, True) is None
    assert motivo(300, 3, True) is not None
    assert motivo(300, 3, False) is None
    assert motivo(60, 0, False) is not None and "bullet" in motivo(60, 0, False)
    assert motivo(120, 2, False) is None


# R94: il ciclo comune degli esercizi di Memoboard.


@pytest.mark.parametrize("esercizio", ["ExKnights", "ExBishops", "ExColors"])
def test_gli_esercizi_a_due_risposte_col_ciclo_comune(monkeypatch, esercizio):
    from orologic_modules import memoboard_app

    monkeypatch.setattr(memoboard_app.strato, "svuota_tastiera", lambda: None)
    monkeypatch.setattr(memoboard_app, "key", lambda: "\r")
    monkeypatch.setattr(memoboard_app.time, "sleep", lambda _secondi: None)
    monkeypatch.setattr(memoboard_app, "Acusticator", lambda *_a, **_k: None)
    _punti, _elenco, _durata, tempi, giuste, errori, esiti = getattr(memoboard_app, esercizio)(20)
    assert len(tempi) == len(esiti) == 20
    assert giuste == esiti.count(True) and len(errori) == esiti.count(False)
    # Invio dice si': gli errori sono le domande dove la risposta era no.
    for errore in errori:
        assert errore["user_answer"] in ("y", "Bianco") and errore["correct_answer"] in ("n", "Nero")


def test_i_punteggi_dopo_un_file_che_non_si_leggeva(tmp_path, monkeypatch):
    """R114: la bandiera dei punteggi non letti non tornava mai falsa: da li'
    ogni salvataggio usciva in silenzio, e Memoboard diceva comunque che il
    risultato era salvato. save_scores ora dice se ha scritto."""
    from orologic_modules import memoboard_app, storage

    file = tmp_path / "memoboard_scores.json"
    file.write_text("{ guasto", encoding="utf-8")
    monkeypatch.setattr(memoboard_app, "SCORES_FILE", str(file))
    monkeypatch.setattr(storage, "metti_da_parte", lambda percorso: None)
    monkeypatch.setitem(memoboard_app._PUNTEGGI, "non_letti", False)
    assert memoboard_app.save_scores(memoboard_app.load_scores()) is False
    # Il file torna buono: la lettura dopo azzera la bandiera.
    file.write_text('{"colors": [], "knights": [], "bishops": [], "mixed": []}', encoding="utf-8")
    punteggi = memoboard_app.load_scores()
    punteggi["colors"].append({"username": "gabry", "net_per_minute": 3.0})
    assert memoboard_app.save_scores(punteggi) is True
    assert "Gabry" in file.read_text(encoding="utf-8")


def test_una_misura_scritta_come_testo_non_fa_mettere_da_parte_il_file(tmp_path, monkeypatch):
    """R114: una misura come "12.5" passava il controllo, poi l'ordinamento
    falliva fra testo e numero, e l'intero file andava da parte come guasto."""
    import json

    from orologic_modules import memoboard_app

    file = tmp_path / "memoboard_scores.json"
    dati = {"colors": [{"username": "gabry", "net_per_minute": "12.5"}, {"username": "cris", "net_per_minute": 7.0}], "knights": [], "bishops": [], "mixed": []}
    file.write_text(json.dumps(dati), encoding="utf-8")
    monkeypatch.setattr(memoboard_app, "SCORES_FILE", str(file))
    punteggi = memoboard_app.load_scores()
    assert [r["username"] for r in punteggi["colors"]] == ["Gabry", "Cris"]
    assert [p.name for p in tmp_path.iterdir()] == ["memoboard_scores.json"]


def test_il_file_dei_punteggi_che_non_si_lascia_leggere_non_e_guasto(tmp_path, monkeypatch):
    """R114: un file buono che in quel momento non si lasciava leggere, per
    un antivirus o una sincronizzazione, andava da parte come guasto, come il
    database di R7. Ora resta com'e', e la sessione non lo copre."""
    import builtins

    from orologic_modules import memoboard_app

    file = tmp_path / "memoboard_scores.json"
    file.write_text('{"colors": [{"username": "Gabry", "net_per_minute": 3.0}], "knights": [], "bishops": [], "mixed": []}', encoding="utf-8")
    monkeypatch.setattr(memoboard_app, "SCORES_FILE", str(file))
    vera = builtins.open

    def bloccata(percorso, *argomenti, **opzioni):
        if str(percorso) == str(file):
            raise PermissionError("tenuto da un altro programma")
        return vera(percorso, *argomenti, **opzioni)

    monkeypatch.setattr(builtins, "open", bloccata)
    punteggi = memoboard_app.load_scores()
    monkeypatch.setattr(builtins, "open", vera)
    assert [p.name for p in tmp_path.iterdir()] == ["memoboard_scores.json"]
    assert memoboard_app.save_scores(punteggi) is False
    assert "Gabry" in file.read_text(encoding="utf-8")


def test_un_flusso_degli_eventi_chiuso_subito_aspetta(monkeypatch):
    """R122: dopo una chiusura pulita il flusso degli eventi si riapriva ogni
    secondo: due Orologic sullo stesso token si chiudevano a vicenda una
    volta al secondo, e il 429 che ne veniva fermava anche le mosse. Ora il
    respiro breve vale solo per un flusso rimasto aperto."""
    import contextlib
    import threading
    import time

    from orologic_modules import lichess_eventi

    aperture = []
    ferma = threading.Event()

    def apri(*a, **k):
        aperture.append(time.monotonic())
        if len(aperture) == 2:
            ferma.set()
        return contextlib.nullcontext(iter([])), None

    monkeypatch.setattr(lichess_eventi.rete, "apri", apri)
    monkeypatch.setattr(lichess_eventi, "ATTESA_DOPO_LA_CHIUSURA", 0.05)
    monkeypatch.setattr(lichess_eventi, "ATTESA_DOPO_ERRORE", 0.6)
    filo = threading.Thread(target=lichess_eventi._ascolta, args=("token", "io", ferma))
    filo.start()
    filo.join(5)
    assert len(aperture) == 2 and aperture[1] - aperture[0] >= 0.5


@pytest.mark.parametrize("codice", [401, 403])
def test_il_token_respinto_si_dice_una_volta(monkeypatch, capsys, codice):
    """R122: il 403 di un token senza il permesso si ritentava per sempre
    senza dirlo, e l'avviso del token revocato tornava a ogni giro del menu,
    perche' ogni giro faceva ripartire l'ascolto."""
    from orologic_modules import lichess_eventi

    chiamate = []
    errore = lichess_eventi.rete.ErroreDiRete("respinto", codice)
    monkeypatch.setattr(lichess_eventi.rete, "apri", lambda *a, **k: chiamate.append(1) or (None, errore))
    monkeypatch.setattr(lichess_eventi, "ATTESA_DOPO_ERRORE", 0)
    monkeypatch.setitem(lichess_eventi._stato, "respinto", None)
    for _giro in range(3):
        lichess_eventi.avvia("token", "io")
        lichess_eventi._stato["thread"].join(3) if lichess_eventi._stato["thread"] else None
    lichess_eventi.ferma()
    assert chiamate == [1]
    assert capsys.readouterr().out.count("non arrivano piu'") == 1


def test_le_squadre_nella_forma_vera_di_lichess():
    """R124: la scheda vera di una battaglia a squadre manda le squadre come
    oggetto da id a coppia di nome e simbolo, e la voce del menu diventava
    "['21Community', 'objects.coin']". Qui la forma del JSON vero di un
    torneo del 26 novembre 2026."""
    from orologic_modules import lichess_tornei

    torneo = {"teamBattle": {"teams": {"21community": ["21Community", "objects.coin"], "lichess-swiss": ["Lichess Swiss", None]}, "nbLeaders": 5}}
    assert lichess_tornei.squadre_del_torneo(torneo) == {"21community": "21Community", "lichess-swiss": "Lichess Swiss"}


def test_le_credenziali_col_bom_si_leggono(tmp_path, monkeypatch):
    """R106: un secrets.json salvato dal Blocco note con la marca BOM si
    prendeva per guasto, e andava da parte col token dentro, in chiaro."""
    import codecs
    import json

    from orologic_modules import lichess_app

    file = tmp_path / "secrets.json"
    file.write_bytes(codecs.BOM_UTF8 + json.dumps({"lichess_token": "finto"}).encode("utf-8"))
    monkeypatch.setattr(lichess_app, "SECRETS_FILE", str(file))
    assert lichess_app.load_secrets() == {"lichess_token": "finto"}
    assert [p.name for p in tmp_path.iterdir()] == ["secrets.json"]


@pytest.mark.parametrize("col_token", [True, False])
def test_il_logout_toglie_anche_le_copie_messe_da_parte(tmp_path, monkeypatch, col_token):
    """R106: al logout restavano le copie di secrets.json messe da parte,
    col token di Lichess in chiaro."""
    import json

    from orologic_modules import lichess_app

    file = tmp_path / "secrets.json"
    file.write_text(json.dumps({"lichess_token": "finto", "lichess_username": "io"} if col_token else {}), encoding="utf-8")
    (tmp_path / "secrets.json.danneggiato-20261126-120000").write_text('{"lichess_token": "vecchio"}', encoding="utf-8")
    monkeypatch.setattr(lichess_app, "SECRETS_FILE", str(file))
    monkeypatch.setattr(lichess_app, "enter_escape", lambda *_argomenti: True)
    lichess_app.menu_logout({})
    assert [p.name for p in tmp_path.iterdir()] == ["secrets.json"]
    assert "lichess_token" not in json.loads(file.read_text(encoding="utf-8"))
