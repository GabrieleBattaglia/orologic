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
    revocato = _("Il token di accesso non e' piu' valido: rifai il login a Lichess.")
    monkeypatch.setattr(lichess_eventi.rete, "apri", lambda *a, **k: chiamate.append(1) or (None, revocato))
    monkeypatch.setattr(lichess_eventi, "ATTESA_DOPO_ERRORE", 0)
    filo = threading.Thread(target=lichess_eventi._ascolta, args=("token", "io", threading.Event()))
    filo.start()
    filo.join(3)
    assert not filo.is_alive() and chiamate == [1]
    assert "non arrivano piu'" in capsys.readouterr().out


def test_dopo_una_chiusura_pulita_si_riparte_subito(monkeypatch):
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
