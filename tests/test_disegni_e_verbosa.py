# Orologic, prove della finestra dei disegni, di Rendi verbosa e della voce
# Spazio della plancia.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Dal collaudo di Gabriele del 23 novembre 2026: la finestra dei disegni
di Easyfish, coi disegni di tutta la partita, Canc, Aggiungi e Pulisci
tutto; Rendi verbosa nelle finestre delle analisi, col cursore sulla prima
linea; la voce della plancia che apre la scacchiera interattiva."""

import io

import chess
import chess.engine
import chess.pgn
import pytest
import wx
from conftest import pompa
from GBUtils import Acusticator

from orologic_modules import dialoghi, finestra_disegni, finestra_navigatore, strato
from orologic_modules.easyfish import analysis_utils, drawing
from orologic_modules.finestra import APRI_LA_SCACCHIERA, Attesa

PARTITA = "1. e4 { [%cal Ge2e4] } e5 2. Nf3 (2. f4 { [%csl Rf4] } exf4) 2... Nc6 { bella [%cal Rf8b4][%csl Gc6] } *"


def partita():
    return chess.pgn.read_game(io.StringIO(PARTITA))


def test_l_ordine_e_i_disegni_della_partita():
    game = partita()
    nomi = [finestra_disegni.nome_della_mossa(game, nodo) for nodo in finestra_disegni.nodi_in_ordine(game)]
    assert nomi == ["Posizione iniziale", "1. e4", "1... e5", "2. Nf3", "2. f4", "2... exf4", "2... Nc6"]
    disegni = [(finestra_disegni.nome_della_mossa(game, nodo), forma, codice) for nodo, forma, codice in finestra_disegni.disegni_della_partita(game)]
    assert disegni == [("1. e4", "freccia", "Ge2e4"), ("2. f4", "cerchio", "Rf4"), ("2... Nc6", "freccia", "Rf8b4"), ("2... Nc6", "cerchio", "Gc6")]


def test_aggiungere_cambiare_e_togliere():
    nodo = partita().end()
    assert finestra_disegni.aggiungi(nodo, "freccia", "B", "d2", "d4") == "aggiunto"
    assert finestra_disegni.aggiungi(nodo, "freccia", "B", "d2", "d4") == "presente"
    # Le stesse case con un altro colore: il colore cambia.
    assert finestra_disegni.aggiungi(nodo, "freccia", "Y", "d2", "d4") == "cambiato"
    assert drawing.get_drawings_from_node(nodo) == (["Rf8b4", "Yd2d4"], ["Gc6"])
    finestra_disegni.togli(nodo, "cerchio", "Gc6")
    assert drawing.get_drawings_from_node(nodo) == (["Rf8b4", "Yd2d4"], [])
    # Il testo del commento resta.
    assert nodo.comment.startswith("bella")


@pytest.fixture
def disegni(app, monkeypatch):
    suonati, domande, detti = [], [], []
    risposte = []
    monkeypatch.setattr(finestra_disegni, "suona", suonati.append)

    def apri(game, nodo):
        dialogo = finestra_disegni.FinestraDisegni(None, game, nodo, lambda _g, testo: (domande.append(testo), risposte.pop(0))[1], detti.extend)
        dialogo.Show()
        aperti.append(dialogo)
        return dialogo

    aperti = []
    stato = {"apri": apri, "suonati": suonati, "domande": domande, "detti": detti, "risposte": risposte}
    yield stato
    for dialogo in reversed(aperti):
        dialogo.Destroy()
    pompa(lambda: False, 0.05)


def _canc(dialogo):
    evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    evento.SetKeyCode(wx.WXK_DELETE)
    dialogo._tasto_dell_elenco(evento)


def test_la_finestra_dei_disegni(disegni):
    game = partita()
    attuale = game.end()
    d = disegni["apri"](game, attuale)
    voci = [d.elenco.GetString(n) for n in range(d.elenco.GetCount())]
    assert voci == [
        "1. e4: Freccia da Empoli 2 a Empoli 4 (verde)",
        "2. f4: Cerchio su Firenze 4 (rosso)",
        "2... Nc6: Freccia da Firenze 8 a Bologna 4 (rosso) [mossa attuale]",
        "2... Nc6: Cerchio su Como 6 (verde) [mossa attuale]",
    ]
    assert disegni["suonati"] == ["apri"]
    # Le case partono dalla mossa attuale, c6 da b8.
    assert (d.colonna_da.GetSelection(), d.traversa_da.GetSelection()) == (1, 7)
    assert d.colonna_da.GetName() == "Colonna di partenza" and d.colonna_da.GetString(4) == "e Empoli"
    # Canc toglie il disegno scelto, anche di un'altra mossa.
    d.elenco.SetSelection(1)
    _canc(d)
    assert disegni["suonati"][-1] == "cancellato" and d.modificata
    assert d.elenco.GetCount() == 3 and d.elenco.GetSelection() == 1
    assert drawing.get_drawings_from_node(game.variations[0].variations[0].variations[1]) == ([], [])
    # Un cerchio: l'arrivo si spegne; il disegno va sulla mossa attuale.
    d.forma.SetSelection(1)
    d._forma_scelta()
    assert not d.colonna_a.IsEnabled() and not d.traversa_a.IsEnabled()
    d.colore.SetSelection(2)
    d.colonna_da.SetSelection(3)
    d.traversa_da.SetSelection(4)
    d.aggiungi()
    assert disegni["suonati"][-1] == "aggiunto"
    assert disegni["detti"][-1] == "Aggiunto: Cerchio su Domodossola 5 (blu)"
    assert drawing.get_drawings_from_node(attuale)[1] == ["Gc6", "Bd5"]
    assert d.elenco.GetStringSelection() == "2... Nc6: Cerchio su Domodossola 5 (blu) [mossa attuale]"
    d.aggiungi()
    assert disegni["suonati"][-1] == "no" and disegni["detti"][-1] == "Questo disegno c'e' gia'."
    # Una freccia da una casa a se stessa no.
    d.forma.SetSelection(0)
    d._forma_scelta()
    d.colonna_a.SetSelection(3)
    d.traversa_a.SetSelection(4)
    d.aggiungi()
    assert disegni["detti"][-1] == "La freccia deve andare da una casa a un'altra."
    # Pulisci tutto, dopo la conferma: prima no, poi si'.
    disegni["risposte"].extend([False, True])
    d.pulisci_tutto()
    assert d.elenco.GetCount() == 4
    d.pulisci_tutto()
    assert disegni["domande"] == ["Cancello tutti i disegni della partita?"] * 2
    assert d.elenco.GetCount() == 0 and disegni["suonati"][-1] == "pulito"
    assert disegni["detti"][-1] == "Pulizia completata. Cancellati disegni in 2 mosse."
    assert attuale.comment == "bella"
    d.pulisci_tutto()
    assert disegni["detti"][-1] == "Nessun disegno nella partita."


def test_i_suoni_della_finestra_e_di_rendi_verbosa_sono_firmati():
    for nome in (finestra_disegni.SUONO_DELLA_CANCELLAZIONE, dialoghi.SUONO_DELLA_FORMA_VERBOSA):
        assert "orologic" in Acusticator.usato_da(nome), nome


def test_dal_nucleo_e_dal_navigatore(finestra, monkeypatch):
    aperte = []
    monkeypatch.setattr(finestra_disegni, "disegna", lambda _genitore, game, nodo, _chiedi, _annuncia: (aperte.append(nodo), True)[1])
    game = partita()
    esiti = []
    finestra.avvia_il_nucleo(lambda: esiti.append(strato.disegni(game, game.end())))
    assert pompa(lambda: esiti == [True])
    assert aperte == [game.end()]
    navigatore = finestra_navigatore.Navigatore(None, game, game.end(), lambda *_a: True, lambda *_a: None, lambda _righe: None)
    try:
        assert navigatore.pulsanti["disegni"].GetLabel() == "&Disegni"
        navigatore.disegni()
        assert navigatore.modificata and aperte[-1] is game.end()
    finally:
        navigatore.Destroy()


class _Punteggio:
    def __init__(self, centesimi):
        self.centesimi = centesimi

    def pov(self, _colore):
        return chess.engine.Cp(self.centesimi)


def test_la_forma_verbosa_dell_analisi():
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
    board.push_san("f5")
    analisi = [
        {"pv": [chess.Move.from_uci("e5f6"), chess.Move.from_uci("g8f6")], "score": _Punteggio(35), "wdl": chess.engine.PovWdl(chess.engine.Wdl(520, 400, 80), chess.WHITE)},
        {"pv": [chess.Move.from_uci("d2d4")], "score": _Punteggio(-12)},
    ]
    righe = analysis_utils.forma_verbosa(board, analisi)
    assert righe[0] == "Linea 1: +0.35, vittoria 52%, patta 40%, sconfitta 8%"
    assert righe[1].startswith("3. ") and "en passant" in righe[1] and ", " in righe[1]
    assert righe[2:] == ["Linea 2: -0.12", righe[3]] and righe[3].startswith("3. ")


def test_rendi_verbosa_e_il_cursore_sulla_prima_linea(app, monkeypatch):
    suonati = []
    righe = ["Motore: Prova.", "Le linee:", "1. +0.35 e4 e5", "2. +0.20 d4"]
    dialogo = dialoghi.FinestraDaLeggere(None, "Analisi", righe, ["Linea 1: +0.35", "1. pedone in Empoli 4"], "1. +0.35 e4 e5", suona=suonati.append)
    try:
        dialogo.Show()
        assert dialogo.testo.GetInsertionPoint() == len("Motore: Prova.\nLe linee:\n")
        assert dialogo.pulsante_verboso.GetLabel() == "Rendi verbosa"
        dialogo.rendi_verbosa()
        assert suonati == ["banda_che_si_allarga"]
        assert dialogo.testo.GetValue() == "Linea 1: +0.35\n1. pedone in Empoli 4"
        assert dialogo.testo.GetInsertionPoint() == 0 and not dialogo.pulsante_verboso.IsShown()
    finally:
        dialogo.Destroy()
    # Senza la forma verbosa il pulsante non c'e'.
    dialogo = dialoghi.FinestraDaLeggere(None, "Aiuto", ["una riga"])
    try:
        assert dialogo.pulsante_verboso is None
    finally:
        dialogo.Destroy()


def test_la_lettura_porta_la_forma_verbosa_alla_finestra(finestra, monkeypatch):
    lette = []
    monkeypatch.setattr(dialoghi, "da_leggere", lambda _g, titolo, righe, verbosa=None, inizio=None: lette.append((titolo, righe, verbosa, inizio)))

    def nucleo():
        with strato.da_leggere("Analisi"):
            print("Le linee:")
            print("1. +0.35 e4")
            strato.lettura_verbosa(["Linea 1: +0.35"])
            strato.lettura_dalla_riga("1. +0.35 e4")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: lette)
    assert lette == [("Analisi", ["Le linee:", "1. +0.35 e4"], ["Linea 1: +0.35"], "1. +0.35 e4")]
    # Fuori da una lettura non fanno niente.
    strato.lettura_verbosa(["niente"])
    strato.lettura_dalla_riga("niente")


def test_la_voce_spazio_della_plancia(finestra, monkeypatch):
    aperte = []
    monkeypatch.setattr(finestra, "apri_la_scacchiera", lambda: aperte.append(True))
    finestra.comandi = {".b": "Mostra scacchiera mini"}
    finestra.attesa = Attesa("area", gioco=True)
    finestra.fornitore = lambda: {"board": chess.Board()}
    try:
        finestra._riscrivi_la_plancia()
        albero = finestra.plancia
        prima, _cookie = albero.GetFirstChild(albero.GetRootItem())
        assert albero.GetItemText(prima) == "Spazio: per accedere alla scacchiera interattiva"
        assert finestra.voci_della_plancia[prima][1].testo == APRI_LA_SCACCHIERA
        evento = wx.TreeEvent(wx.wxEVT_TREE_ITEM_ACTIVATED, albero, prima)
        finestra._voce_attivata(evento)
        assert aperte == [True]
        # Senza una posizione da mostrare la voce non c'e'.
        finestra.fornitore = lambda: {"board": None}
        finestra._riscrivi_la_plancia()
        prima, _cookie = albero.GetFirstChild(albero.GetRootItem())
        assert albero.GetItemText(prima) != "Spazio: per accedere alla scacchiera interattiva"
    finally:
        finestra.fornitore = None
        finestra.comandi = None
        finestra.attesa = Attesa(None)
