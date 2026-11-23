# Orologic, prove di Easyfish nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Easyfish nella finestra, come l'ha voluto Gabriele il 22 novembre 2026:
le righe sulla posizione del cruscotto, il commento che tiene analisi e
disegni, le voci del navigatore; la scacchiera interattiva nel menu
principale e nell'esploratore, coi comandi Alt; l'editor della scacchiera;
il navigatore della partita; e un giro vero del nucleo, col cruscotto, il
prompt di gioco, le righe da leggere, l'esploratore e il navigatore."""

import io

import chess
import chess.engine
import chess.pgn
import pytest
import wx
from conftest import pompa

from orologic_modules import (
    dialoghi,
    finestra_editor,
    finestra_navigatore,
    finestra_scacchiera,
)
from orologic_modules import engine as orologic_engine
from orologic_modules.easyfish import constants, easyfish_app, posizione
from orologic_modules.finestra import Attesa

PARTITA = """[Event "Prova"]
[White "Uno"]
[Black "Due"]
[Result "*"]

1. e4 e5 2. Nf3 (2. Bc4 Nf6) Nc6 {Buona [%cal Gb8c6] [Val: +0.30]} 3. Bb5 *
"""


def partita():
    return chess.pgn.read_game(io.StringIO(PARTITA))


def _tasto(dialogo, codice, *modificatori, oggetto=None):
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(codice)
    for modificatore in modificatori:
        getattr(evento, f"Set{modificatore}Down")(True)
    evento.SetEventObject(oggetto or dialogo.area)
    dialogo._tasto(evento)


def _scrivi(dialogo, testo):
    for carattere in testo:
        evento = wx.KeyEvent(wx.wxEVT_CHAR)
        evento.SetKeyCode(ord(carattere))
        evento.SetUnicodeKey(ord(carattere))
        dialogo._carattere(evento)


def _detti(finestra):
    return [testo for testo, _chiave, dove, _interrompi in finestra.sintesi.chiamate if dove == "sintesi"]


# Le funzioni della posizione.


def test_il_commento_da_leggere_e_quello_scritto_a_mano():
    nodo = partita().variations[0].variations[0].variations[0].variations[0]
    assert nodo.move == chess.Move.from_uci("b8c6")
    assert posizione.testo_del_commento(nodo.comment) == "Buona [Val: +0.30]"
    assert posizione.testo_del_commento("[%eval 0.35] [%clk 0:01:00]") == "valutazione 0.35"
    assert posizione.testo_libero(nodo.comment) == "Buona"
    posizione.metti_il_testo(nodo, "Molto buona")
    assert nodo.comment == "Molto buona [%cal Gb8c6] [Val: +0.30]"
    posizione.metti_il_testo(nodo, "")
    assert nodo.comment == "[%cal Gb8c6] [Val: +0.30]"


def test_le_righe_della_posizione_e_le_mosse():
    game = partita()
    e5 = game.variations[0].variations[0]
    board = posizione.scacchiera_del_nodo(game, e5)
    assert isinstance(board, easyfish_app.CustomBoard) and len(board.move_stack) == 2
    righe = posizione.righe_della_posizione(e5, board, scelta=1)
    assert righe[0] == "Linea principale."
    assert righe[1].startswith("Seguito: 2. ") and righe[1].endswith("; varianti: Bc4.")
    assert righe[2] == "Scelta: 2 di 2, Bc4."
    bc4 = e5.variations[1]
    assert posizione.righe_della_posizione(bc4, posizione.scacchiera_del_nodo(game, bc4))[0] == "Variante, livello 1."
    assert posizione.inizio_della_variante(bc4.variations[0]) is bc4
    assert posizione.inizio_della_variante(e5) is None
    assert posizione.leggi_la_mossa(chess.Board("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1"), "ed5") == chess.Move.from_uci("e4d5")
    assert posizione.leggi_la_mossa(board, "bc4") == chess.Move.from_uci("f1c4")
    assert posizione.leggi_la_mossa(board, "Qh8") is None
    # Una partita da una posizione data: la scacchiera parte da li'.
    studio = chess.pgn.read_game(io.StringIO('[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"]\n\n1. e4 *\n'))
    assert posizione.scacchiera_del_nodo(studio, studio.end()).fen().startswith("4k3/8/8/8/4P3/8/8/4K3 b")
    # Dopo un taglio si torna al piu' vicino che c'e'.
    e5.variations.remove(e5.variations[0])
    assert posizione.ancora_nella_partita(game.end()) is game.end()
    nodo_tagliato = game.variations[0].variations[0]
    assert posizione.ancora_nella_partita(nodo_tagliato) is nodo_tagliato


def test_le_voci_del_navigatore():
    game = partita()
    voci = posizione.albero(game)
    assert [nodo.san() for nodo, _testo, _varianti in voci] == ["e4", "e5", "Nf3", "Nc6", "Bb5"]
    assert voci[0][1].startswith("1. e4, ")
    assert voci[1][1].startswith("1... e5, ")
    variante, testo, seguito = voci[2][2][0]
    assert variante.san() == "Bc4" and testo.startswith("Variante: 2. Bc4, ")
    assert [nodo.san() for nodo, _testo, _varianti in seguito] == ["Nf6"]
    assert voci[3][1].endswith(". Commento: Buona [Val: +0.30]")
    assert posizione.voce_della_partita(game) == "Uno vs Due, *"


def test_le_righe_dell_analisi():
    board = chess.Board()
    analisi = [{"pv": [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")], "score": chess.engine.PovScore(chess.engine.Cp(30), chess.WHITE)},
               {"pv": [chess.Move.from_uci("d2d4")], "score": chess.engine.PovScore(chess.engine.Mate(3), chess.WHITE)}]
    assert posizione.righe_dell_analisi(board, analisi) == ["1. +0.30 e4 e5", "2. M3 d4"]


def test_i_comandi_nuovi_nell_aiuto():
    assert ".na" in constants.MNMAIN
    assert {"i", "_"} <= set(constants.MNEXPLORER)


# La scacchiera interattiva nei contesti di Easyfish.


@pytest.fixture
def aperta(finestra, monkeypatch):
    dati = {"board": chess.Board(), "mio": None, "pausa": False, "senza_orologio": False, "vista_ferma": False, "da_guardare": False, "contesto": "esploratore"}
    finestra.fornitore = lambda: {**dati, "board": dati["board"].copy()}
    finestra.comandi = constants.MNEXPLORER
    premuti = []
    monkeypatch.setattr(finestra.faccia, "premi", premuti.append)
    suonati = []
    monkeypatch.setattr(finestra_scacchiera, "suona", suonati.append)
    monkeypatch.setattr(finestra_editor, "suona", suonati.append)
    stato = {"dati": dati, "premuti": premuti, "suonati": suonati, "dialogo": None}

    def apri():
        stato["dialogo"] = finestra_scacchiera.FinestraScacchiera(finestra)
        finestra.dialogo_scacchiera = stato["dialogo"]
        return stato["dialogo"]

    stato["apri"] = apri
    try:
        yield stato
    finally:
        finestra.dialogo_scacchiera = None
        finestra.fornitore = None
        finestra.comandi = None
        if stato["dialogo"]:
            stato["dialogo"].Destroy()
        pompa(lambda: False, 0.05)


def test_la_scacchiera_nell_esploratore(aperta, finestra, monkeypatch):
    finestra.attesa = Attesa("area", gioco=True, tasto=True)
    d = aperta["apri"]()
    # Alt con le lettere: i comandi dell'esploratore, senza Invio.
    _tasto(d, ord("D"), "Alt")
    _tasto(d, ord("S"), "Alt")
    assert "".join(aperta["premuti"]) == "ds"
    monkeypatch.setattr(finestra, "chiedi_valore", lambda *_dati, **_opzioni: 5)
    _tasto(d, ord("R"), "Alt")
    assert "".join(aperta["premuti"]) == "dsr5\r"
    del aperta["premuti"][:]
    # Invio: la mossa col comando i.
    d.scacchiera.cursore = chess.E2
    d.spazio()
    d.scacchiera.cursore = chess.E4
    d.invio()
    assert "".join(aperta["premuti"]) == "ie4\r"
    del aperta["premuti"][:]
    # C: il commento col trattino basso.
    monkeypatch.setattr(finestra, "chiedi_valore", lambda *_dati, **_opzioni: "Bella")
    _scrivi(d, "C")
    assert "".join(aperta["premuti"]) == "_Bella\r"
    del aperta["premuti"][:]
    # I pezzi e la casa li dice la scacchiera, perche' il nucleo legge un tasto solo.
    _scrivi(d, "N")
    assert pompa(lambda: any("cavall" in testo.lower() for testo in _detti(finestra)), 2)
    _tasto(d, wx.WXK_TAB)
    assert pompa(lambda: any(testo.startswith("La casa E4") for testo in _detti(finestra)), 2)
    assert aperta["premuti"] == []
    assert "Alt con a e d" in "\n".join(d.righe_d_aiuto())


def test_la_scacchiera_nel_menu_di_easyfish(aperta, finestra, monkeypatch):
    aperta["dati"]["contesto"] = "easyfish"
    finestra.comandi = constants.MNMAIN
    d = aperta["apri"]()
    d.scacchiera.cursore = chess.G1
    d.spazio()
    d.scacchiera.cursore = chess.F3
    d.invio()
    assert "".join(aperta["premuti"]) == "Nf3\r"
    del aperta["premuti"][:]
    monkeypatch.setattr(finestra, "chiedi_valore", lambda *_dati, **_opzioni: "Idea")
    _scrivi(d, "C")
    _scrivi(d, "N")
    assert "".join(aperta["premuti"]) == "_Idea\r,N\r"
    # Alt con le lettere qui non fa niente.
    del aperta["premuti"][:]
    _tasto(d, ord("D"), "Alt")
    assert aperta["premuti"] == []


# L'editor della scacchiera.


def test_l_editor_della_scacchiera(finestra, monkeypatch):
    suonati = []
    monkeypatch.setattr(finestra_scacchiera, "suona", suonati.append)
    monkeypatch.setattr(finestra_editor, "suona", suonati.append)
    editor = finestra_editor.EditorDellaScacchiera(finestra, finestra, chess.STARTING_FEN)
    editor.Show()
    try:
        board = editor.scacchiera.board
        assert editor.GetTitle() == "Editor della scacchiera"
        assert editor.tratto.GetSelection() == 0 and all(casella.GetValue() for casella in editor.arrocchi.values())
        # Una lettera mette il pezzo; il Re si sposta.
        editor.scacchiera.vai("e", 4)
        _scrivi(editor, "Q")
        assert board.piece_at(chess.E4) == chess.Piece.from_symbol("Q")
        editor.scacchiera.vai("d", 4)
        _scrivi(editor, "K")
        assert board.piece_at(chess.D4) == chess.Piece.from_symbol("K") and board.piece_at(chess.E1) is None
        # Sul Re non si mette niente, e Canc non lo toglie.
        _scrivi(editor, "R")
        _tasto(editor, wx.WXK_DELETE)
        assert board.piece_at(chess.D4) == chess.Piece.from_symbol("K")
        assert suonati[-3:] == ["metti", "re_da_spostare", "re_da_spostare"]
        # Spazio e Invio spostano senza regole.
        editor.scacchiera.vai("a", 2)
        editor.spazio()
        editor.scacchiera.vai("a", 6)
        editor.invio()
        assert board.piece_at(chess.A6) == chess.Piece.from_symbol("P") and board.piece_at(chess.A2) is None
        # Canc svuota.
        _tasto(editor, wx.WXK_DELETE)
        assert board.piece_at(chess.A6) is None and suonati[-1] == "togli"
        # Alt con una lettera dice dove sono i pezzi, senza toccarli.
        prima = board.fen()
        _tasto(editor, ord("Q"), "Alt")
        assert board.fen() == prima
        # La posizione non e' legale: il Bianco ha arrocchi ma il Re e' in d4.
        editor.conferma()
        assert editor.fen is None and suonati[-1] == "posizione_illegale"
        assert pompa(lambda: any("Diritti di arrocco non validi" in testo for testo in _detti(finestra)), 2)
        # Senza gli arrocchi del Bianco si puo'.
        for simbolo in "KQ":
            editor.arrocchi[simbolo].SetValue(False)
        editor.numero.SetValue(12)
        editor.conferma()
        assert editor.fen is not None
        risultato = chess.Board(editor.fen)
        assert risultato.turn == chess.WHITE and risultato.fullmove_number == 12 and risultato.castling_xfen() == "kq"
        # Col Nero al tratto la casa dell'en passant passa alla terza
        # traversa; in a3, senza un pedone che vi sia appena passato, no.
        editor.fen = None
        editor.tratto.SetSelection(1)
        editor._case_dell_en_passant()
        assert editor.en_passant.GetCount() == 9 and editor._case[1] == chess.A3
        editor.en_passant.SetSelection(1)
        editor.conferma()
        assert editor.fen is None
        assert pompa(lambda: any("Casa en passant non valida" in testo for testo in _detti(finestra)), 2)
        # Svuota lascia i due Re.
        editor.svuota()
        assert sorted(chess.square_name(casa) for casa in editor.scacchiera.board.piece_map()) == ["e1", "e8"]
        assert suonati[-1] == "da_capo"
    finally:
        editor.Destroy()
        pompa(lambda: False, 0.05)


# Il navigatore della partita.


def test_il_navigatore_della_partita(finestra, monkeypatch):
    game = partita()
    monkeypatch.setattr(finestra_navigatore, "analizza", lambda _board: (["1. +0.30 e5"], None, None))
    letture = []
    monkeypatch.setattr(finestra_navigatore.dialoghi, "da_leggere", lambda _genitore, titolo, righe, *_resto: letture.append((titolo, righe)))
    detti = []
    conferme = []
    nav = finestra_navigatore.Navigatore(finestra, game, game.end(), lambda _g, testo: conferme.append(testo) or True,
                                         lambda *_dati, **_opzioni: "Nuovo", detti.extend)
    nav.Show()
    try:
        albero = nav.albero
        radice = albero.GetRootItem()
        assert albero.GetItemText(radice) == "Uno vs Due, *"
        assert albero.GetItemData(albero.GetSelection()) is game.end()
        voci = [albero.GetItemText(voce) for voce in _figli(albero, radice)]
        assert len(voci) == 5 and voci[2].startswith("2. Nf3, ")
        nf3 = list(_figli(albero, radice))[2]
        ramo = next(_figli(albero, nf3))
        assert albero.GetItemText(ramo).startswith("Variante: 2. Bc4, ")
        # Promuovi la variante dalla sua seconda mossa.
        nf6 = next(_figli(albero, ramo))
        albero.SelectItem(nf6)
        nav.promuovi()
        assert game.variations[0].variations[0].variations[0].san() == "Bc4" and nav.modificata
        assert albero.GetItemData(albero.GetSelection()).san() == "Nf6"
        # Il commento tiene i disegni.
        nc6 = game.variations[0].variations[0].variations[1].variations[0]
        albero.SelectItem(nav.voci[id(nc6)])
        nav.commento()
        assert nc6.comment == "Nuovo [%cal Gb8c6] [Val: +0.30]"
        # Taglia, con la conferma del seguito.
        nav.taglia()
        assert nc6 not in nc6.parent.variations and conferme
        # L'analisi, nel filo, in una finestra da leggere.
        nav.analizza()
        assert pompa(lambda: letture == [("Analisi", ["1. +0.30 e5"])])
        # Invio: si va alla voce.
        albero.SelectItem(albero.GetRootItem())
        nav.vai()
        assert nav.scelto is game
    finally:
        nav.Destroy()
        pompa(lambda: False, 0.05)


def _figli(albero, voce):
    figlio, biscotto = albero.GetFirstChild(voce)
    while figlio.IsOk():
        yield figlio
        figlio, biscotto = albero.GetNextChild(voce, biscotto)


# Un giro vero del nucleo.


def _premi(finestra, testo):
    for carattere in testo:
        finestra.faccia.premi(carattere)


def test_easyfish_nella_finestra(finestra, monkeypatch):
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    salvate = []
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", salvate.append)
    letture = []
    monkeypatch.setattr(dialoghi, "da_leggere", lambda _genitore, titolo, righe, *_resto: letture.append((titolo, righe)))
    navigate = []

    def naviga(_genitore, partita_navigata, nodo, *_altro):
        navigate.append(nodo)
        return partita_navigata.variations[0], False

    monkeypatch.setattr(finestra_navigatore, "naviga", naviga)
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))

    def contesto():
        dati = finestra.fornitore() if finestra.fornitore is not None else None
        return dati and dati["contesto"]

    # Il menu principale: il cruscotto, e il prompt di gioco.
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco and contesto() == "easyfish")
    dati = finestra.fornitore()
    assert dati["in_piu"][:2] == ["Linea principale.", "Fine della linea."]
    assert len(dati["board"].move_stack) == 5
    assert finestra.si_apre_la_scacchiera()
    # L'aiuto in una finestra da leggere.
    _premi(finestra, ".?\r")
    assert pompa(lambda: letture and letture[-1][0] == "Comandi di Easyfish")
    # Il commento scritto a mano.
    _premi(finestra, "_Bella\r")
    assert pompa(lambda: game.end().comment == "Bella")
    # L'esploratore parte dalla mossa dove si e', e legge un tasto solo.
    _premi(finestra, ".e\r")
    assert pompa(lambda: finestra.attesa.tasto and contesto() == "esploratore")
    assert finestra.si_apre_la_scacchiera()
    _premi(finestra, "a")
    assert pompa(lambda: len(finestra.fornitore()["board"].move_stack) == 4)
    # i aggiunge una mossa: qui diventa una variante.
    _premi(finestra, "iBc4\r")
    assert pompa(lambda: finestra.fornitore()["board"].peek() == chess.Move.from_uci("f1c4"))
    nc6 = game.variations[0].variations[0].variations[0].variations[0]
    assert [variante.san() for variante in nc6.variations] == ["Bb5", "Bc4"]
    _premi(finestra, ".")
    assert pompa(lambda: contesto() == "easyfish" and not finestra.attesa.tasto)
    assert len(finestra.fornitore()["board"].move_stack) == 5
    # Il navigatore: si va alla prima mossa.
    _premi(finestra, ".na\r")
    assert pompa(lambda: navigate and len(finestra.fornitore()["board"].move_stack) == 1)
    assert navigate[0].move == chess.Move.from_uci("f1c4")
    # Si esce: la partita cambiata si salva.
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert salvate == [game]
    assert finestra.fornitore is None


# I difetti corretti, che valevano anche nel terminale.


def test_sovrascrivi_tiene_le_varianti_e_u_chiede(finestra, monkeypatch):
    game = partita()
    monkeypatch.setattr(orologic_engine, "ENGINE", object())
    monkeypatch.setattr(easyfish_app, "SaveGameToFile", lambda _game: None)
    finestra.avvia_il_nucleo(lambda: easyfish_app.run(partita=game))
    assert pompa(lambda: finestra.attesa.tipo == "area" and finestra.attesa.gioco)
    e5 = game.variations[0].variations[0]
    # Alla seconda mossa del Bianco, una mossa diversa: Sovrascrivi, con Invio.
    _premi(finestra, ".k2\r")
    assert pompa(lambda: finestra.fornitore is not None and len(finestra.fornitore()["board"].move_stack) == 2)
    _premi(finestra, "d4\r")
    assert pompa(lambda: finestra.attesa.tipo == "sino")
    _premi(finestra, "\r")
    assert pompa(lambda: [variante.san() for variante in e5.variations] == ["d4", "Bc4"])
    # Nell'esploratore u, con un seguito, chiede: Esc non taglia.
    _premi(finestra, ".e\r")
    assert pompa(lambda: finestra.attesa.tasto)
    _premi(finestra, "a")
    assert pompa(lambda: len(finestra.fornitore()["board"].move_stack) == 2)
    _premi(finestra, "u")
    assert pompa(lambda: finestra.attesa.tipo == "sino")
    _premi(finestra, "\x1b")
    assert pompa(lambda: finestra.attesa.tasto)
    assert e5 in e5.parent.variations
    _premi(finestra, ".")
    assert pompa(lambda: not finestra.attesa.tasto and finestra.attesa.gioco)
    _premi(finestra, ".\r")
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_l_analisi_della_partita_col_motore_non_cade():
    import contextlib
    import types

    from orologic_modules.easyfish import game_mode

    class Motore:
        def analyse(self, _board, _limite, multipv=1):
            return [{"pv": [chess.Move.from_uci("e2e4")], "score": chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE), "time": 1.0, "depth": 10, "seldepth": 12}]

    uscita = io.StringIO()
    with contextlib.redirect_stdout(uscita):
        assert game_mode._comandi_informativi(".a", chess.Board(), types.SimpleNamespace(a_punteggio=False), Motore())
    assert "e4" in uscita.getvalue()


def test_l_intestazione_dell_analisi_dice_tutto_il_motore():
    """Gabriele, 22 novembre 2026: il motore, la ricerca e tutte le opzioni
    in uso, poi le linee, tante quante chieste."""
    import types

    from orologic_modules.easyfish import analysis_utils

    opzioni = {
        "Threads": chess.engine.Option("Threads", "spin", 1, 1, 1024, None),
        "Hash": chess.engine.Option("Hash", "spin", 16, 1, 33554432, None),
        "Clear Hash": chess.engine.Option("Clear Hash", "button", None, None, None, None),
        "Ponder": chess.engine.Option("Ponder", "check", False, None, None, None),
        "SyzygyPath": chess.engine.Option("SyzygyPath", "string", "", None, None, None),
    }
    chieste = []

    class Motore:
        def __init__(self):
            self.id = {"name": "Stockfish 17", "author": "the Stockfish developers"}
            self.options = opzioni
            self.protocol = types.SimpleNamespace(config={"Threads": 4, "Hash": 256})

        def analyse(self, _board, limite, multipv=1):
            chieste.append((limite.time, multipv))
            comune = {"time": 2.0, "depth": 22, "seldepth": 31, "nodes": 3456789, "nps": 1728394, "hashfull": 123, "tbhits": 0}
            return [
                {**comune, "pv": [chess.Move.from_uci("e2e4")], "score": chess.engine.PovScore(chess.engine.Cp(30), chess.WHITE)},
                {**comune, "pv": [chess.Move.from_uci("d2d4")], "score": chess.engine.PovScore(chess.engine.Cp(25), chess.WHITE)},
            ]

    analisi, righe = analysis_utils.analizza(chess.Board(), Motore(), 2.0, 3)
    assert chieste == [(2.0, 3)] and len(analisi) == 2
    assert righe == [
        "Motore: Stockfish 17, di the Stockfish developers.",
        "Tempo: 2.00 secondi.",
        "Profondita': 22, selettiva 31.",
        "Nodi: 3456789.",
        "Nodi al secondo: 1728394.",
        "Hash occupata: 12.3%.",
        "Posizioni trovate nelle tablebase: 0.",
        "Linee: 3 chieste, 2 avute.",
        "Opzioni del motore:",
        "Threads: 4",
        "Hash: 256",
        "Ponder: no",
        "SyzygyPath: vuota",
        "Le linee:",
        "1. +0.30 e4",
        "2. +0.25 d4",
    ]
    assert analysis_utils.analizza(chess.Board(), None, 1, 3) == (None, ["Motore non disponibile."])
