# Orologic, prove dell'albero delle aperture.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""L'albero delle aperture di eco.pgn (Gabriele, 25 novembre 2026): le
linee in un albero di mosse, la percentuale sul totale, il nome esatto o il
piu' vicino, anche per trasposizione, la linea come partita, la finestra coi
suoi pulsanti e la voce del menu principale; e eco.pgn in una copia sola."""

import os
import time

import chess
import pytest
from conftest import pompa

from orologic_modules import aperture, board_utils, finestra_aperture, pgn_extract


def _voce(eco, apertura, *mosse, variante=""):
    board = chess.Board()
    for san in mosse:
        board.push_san(san)
    return board.epd(), {"eco": eco, "opening": apertura, "variation": variante, "moves": list(mosse), "ply": len(mosse)}


def _eco_db(*voci):
    database = {}
    for epd, voce in voci:
        database.setdefault(epd, []).append(voce)
    return database


# Cinque linee: 1.Nf3 c5 2.e4 arriva per trasposizione dove arriva 1.e4 c5
# 2.Nf3, che di suo non ha una linea.
ECO_DB = _eco_db(
    _voce("B00", "King's pawn opening", "e4"),
    _voce("B20", "Sicilian defence", "e4", "c5"),
    _voce("B50", "Sicilian", "e4", "c5", "Nf3", "d6", variante="Prova"),
    _voce("A40", "Queen's pawn", "d4"),
    _voce("A04", "Reti", "Nf3", "c5", "e4", variante="transposing to Sicilian"),
)


@pytest.fixture
def albero():
    return aperture.costruisci(ECO_DB)


def _nodo(albero, *mosse):
    board = chess.Board()
    giocate = []
    for san in mosse:
        giocate.append(board.push_san(san))
    return aperture.trova(albero, giocate)


def test_l_albero_conta_le_linee_e_da_i_nomi(albero):
    assert albero.totale == 5
    # Prima le mosse con piu' linee.
    assert [nodo.mossa.uci() for nodo in albero.radice.figli_in_ordine()] == ["e2e4", "d2d4", "g1f3"]
    e4 = _nodo(albero, "e4")
    assert e4.linee == 3 and e4.semimosse == 1
    assert aperture.nome_della_voce(e4.voce) == "B00 King's pawn opening"
    # La posizione di 1.e4 c5 2.Nf3 ha il nome della linea che ci arriva da
    # 1.Nf3 c5 2.e4, come classifica pgn-extract.
    assert aperture.nome_della_voce(_nodo(albero, "e4", "c5", "Nf3").voce) == "A04 Reti, transposing to Sicilian"
    # Senza nome suo, quello della mossa sopra piu' vicina, o nessuno.
    assert _nodo(albero, "Nf3", "c5").voce is None
    assert _nodo(albero, "Nf3", "c5").voce_piu_vicina() is None
    assert aperture.nome_della_voce(_nodo(albero, "e4", "c5", "Nf3", "d6").voce_piu_vicina()) == "B50 Sicilian, Prova"


def test_la_voce_la_linea_e_la_partita(albero):
    e4 = _nodo(albero, "e4")
    assert aperture.voce_del_nodo(e4, albero.totale).endswith("(1. e4) = 60.0%, B00 King's pawn opening")
    d6 = _nodo(albero, "e4", "c5", "Nf3", "d6")
    assert aperture.voce_del_nodo(d6, albero.totale).endswith("(2... d6) = 20.0%, B50 Sicilian, Prova")
    assert aperture.linea(d6) == "1. e4 c5 2. Nf3 d6"
    partita = aperture.partita(d6)
    assert partita.headers["ECO"] == "B50" and partita.headers["Opening"] == "Sicilian" and partita.headers["Variation"] == "Prova"
    assert partita.board().variation_san(list(partita.mainline_moves())) == "1. e4 c5 2. Nf3 d6"
    # trova si ferma dove l'albero finisce.
    assert aperture.trova(albero, [*d6.percorso(), chess.Move.from_uci("a2a3")]) is d6


def test_l_albero_vero_di_eco_pgn():
    inizio = time.monotonic()
    albero = aperture.carica()
    assert albero.totale > 1900
    assert time.monotonic() - inizio < 20
    prime = {nodo.mossa.uci(): nodo for nodo in albero.radice.figli_in_ordine()}
    assert {"e2e4", "d2d4", "c2c4", "g1f3"} <= set(prime)
    assert prime["e2e4"].voce is not None


def test_eco_pgn_in_una_copia_sola():
    assert os.path.normpath(board_utils.percorso_eco()).endswith(os.path.join("resources", "eco.pgn"))
    assert "eco.pgn" not in pgn_extract.FILE_DEL_SITO
    # Una lettura sola: la seconda viene dalla memoria.
    assert board_utils.LoadEcoDatabaseWithFEN("eco.pgn") is board_utils.LoadEcoDatabaseWithFEN("eco.pgn")


class Prova:
    def __init__(self, monkeypatch, albero, mosse=()):
        self.suoni = []
        self.detti = []
        monkeypatch.setattr(finestra_aperture, "suona", self.suoni.append)
        self.stato = aperture.Stato(albero=albero, mosse=list(mosse))
        self.dialogo = finestra_aperture.FinestraAperture(None, self.stato, self.detti.extend)
        self.dialogo.Show()
        pompa(lambda: False, 0.05)

    def chiudi(self):
        self.dialogo.Destroy()
        pompa(lambda: False, 0.05)


@pytest.fixture
def aperta(app, monkeypatch, albero):
    aperte = []

    def apri(mosse=()):
        prova = Prova(monkeypatch, albero, mosse)
        aperte.append(prova)
        return prova

    yield apri
    for prova in reversed(aperte):
        prova.chiudi()


def _testo(dialogo):
    voce, _nodo = dialogo.selezionata()
    return dialogo.albero.GetItemText(voce)


def test_la_finestra_l_albero_e_la_linea(aperta):
    prova = aperta()
    dialogo = prova.dialogo
    # La prima mossa scelta, con la sua linea.
    assert _testo(dialogo).endswith("(1. e4) = 60.0%, B00 King's pawn opening")
    assert dialogo.linea.GetValue() == "1. e4, B00 King's pawn opening"
    # Invio apre il ramo, e lo richiude.
    voce, _nodo = dialogo.selezionata()
    dialogo.attiva()
    assert dialogo.albero.IsExpanded(voce)
    figlio, _cookie = dialogo.albero.GetFirstChild(voce)
    assert dialogo.albero.GetItemText(figlio).endswith("(1... c5) = 40.0%, B20 Sicilian defence")
    dialogo.attiva()
    assert not dialogo.albero.IsExpanded(voce)
    # Con una semimossa sola i pulsanti dicono di no.
    dialogo.vai("manuale")
    assert prova.suoni == ["no"] and prova.detti == ["Serve una linea di almeno 2 semimosse."]
    assert dialogo.uscita is None


def test_la_linea_va_all_analisi_e_la_finestra_si_riapre_li(aperta, albero):
    prova = aperta()
    dialogo = prova.dialogo
    dialogo._vai_alla_linea(_nodo(albero, "e4", "c5", "Nf3").percorso())
    assert dialogo.linea.GetValue() == "1. e4 c5 2. Nf3, A04 Reti, transposing to Sicilian"
    dialogo.vai("easyfish")
    azione, partita = dialogo.uscita
    assert azione == "easyfish" and partita.headers["ECO"] == "A04"
    assert len(list(partita.mainline_moves())) == 3
    # Riaperta con lo stato, allo stesso punto.
    di_nuovo = aperta(prova.stato.mosse)
    assert _testo(di_nuovo.dialogo).endswith("(2. Nf3) = 20.0%, A04 Reti, transposing to Sicilian")
    # Una foglia: Invio dice la linea.
    di_nuovo.dialogo._vai_alla_linea(_nodo(albero, "d4").percorso())
    di_nuovo.dialogo.attiva()
    assert di_nuovo.detti[-1] == "1. d4, A40 Queen's pawn"


def test_run_passa_la_linea_all_analisi_e_a_easyfish(monkeypatch, albero):
    from orologic_modules import pgn_search, strato
    from orologic_modules.easyfish import easyfish_app

    partita = aperture.partita(_nodo(albero, "e4", "c5"))
    uscite = iter([("manuale", partita), ("easyfish", partita), None])
    stati = []
    monkeypatch.setattr(strato, "albero_aperture", lambda stato: stati.append(stato) or next(uscite))
    fatti = []
    monkeypatch.setattr(pgn_search, "_avvia_analisi", lambda game, automatica=None: fatti.append(("analisi", automatica, game)))
    monkeypatch.setattr(easyfish_app, "run", lambda partita=None: fatti.append(("easyfish", partita)))
    aperture.run()
    assert [fatto[0] for fatto in fatti] == ["analisi", "easyfish"]
    assert fatti[0][1] is False and fatti[0][2] is partita
    # Lo stato e' uno solo, per riaprire allo stesso punto.
    assert len(stati) == 3 and stati[0] is stati[1] is stati[2]
