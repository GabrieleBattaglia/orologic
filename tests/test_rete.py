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
