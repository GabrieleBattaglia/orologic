# Orologic, prove della scacchiera interattiva, la finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra della scacchiera interattiva sul desktop nascosto: lo spazio
che la apre solo al prompt delle mosse vuoto, i tasti, gli annunci alla
sintesi, la mossa scritta nel prompt, i comandi, la pausa col menu, la
posizione che arriva dal nucleo, la chiusura per una domanda e la
riapertura, e una partita con il ciclo d'attesa vero."""

import threading

import chess
import pytest
import wx
from conftest import pompa

from orologic_modules import board_utils, config, finestra_scacchiera, game_flow, strato
from orologic_modules.finestra import Attesa
from orologic_modules.scacchiera import nome_casa


def _tasto(dialogo, codice, *modificatori):
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(codice)
    for modificatore in modificatori:
        getattr(evento, f"Set{modificatore}Down")(True)
    dialogo._tasto(evento)


def _scrivi(dialogo, testo):
    for carattere in testo:
        evento = wx.KeyEvent(wx.wxEVT_CHAR)
        evento.SetKeyCode(ord(carattere))
        evento.SetUnicodeKey(ord(carattere))
        dialogo._carattere(evento)


def _detti(finestra):
    """Gli annunci della scacchiera: solo alla sintesi."""
    return [(testo, interrompi) for testo, _chiave, dove, interrompi in finestra.sintesi.chiamate if dove == "sintesi"]


def _ultimo_detto(finestra, testo):
    return pompa(lambda: _detti(finestra) and _detti(finestra)[-1] == (testo, True), 2)


@pytest.fixture
def aperta(finestra, monkeypatch):
    """La scacchiera aperta senza ShowModal, con un cruscotto finto: i tasti
    mandati al nucleo e i suoni si segnano."""
    dati = {"board": chess.Board(), "mio": None, "pausa": False, "senza_orologio": False, "vista_ferma": False, "da_guardare": False}
    finestra.fornitore = lambda: {**dati, "board": dati["board"].copy()}
    finestra.comandi = config.DOT_COMMANDS
    premuti = []
    monkeypatch.setattr(finestra.faccia, "premi", premuti.append)
    suonati = []
    monkeypatch.setattr(finestra_scacchiera, "suona", suonati.append)
    stato = {"dati": dati, "premuti": premuti, "suonati": suonati, "dialogo": None}

    def apri():
        if stato["dialogo"] is not None:
            stato["dialogo"].Destroy()
        stato["dialogo"] = finestra_scacchiera.FinestraScacchiera(finestra)
        finestra.dialogo_scacchiera = stato["dialogo"]
        return stato["dialogo"]

    stato["apri"] = apri
    try:
        yield stato
    finally:
        finestra.dialogo_scacchiera = None
        finestra.fornitore = None
        if stato["dialogo"]:
            stato["dialogo"].Destroy()
        pompa(lambda: False, 0.05)


def _mandati(stato):
    return "".join(stato["premuti"])


def test_le_chiavi_dei_comandi():
    chiavi = finestra_scacchiera.chiavi_dei_comandi(config.DOT_COMMANDS)
    assert {".1", ".5", ".p", ".c", ".s", ".b"} <= chiavi
    assert finestra_scacchiera.chiavi_dei_comandi([("draw", "draw : Proponi patta"), ("oo / ooo", "arrocchi")]) == {"draw", "oo", "ooo"}
    assert finestra_scacchiera.chiavi_dei_comandi(None) == set()


def test_lo_spazio_la_apre_solo_al_prompt_vuoto(finestra, monkeypatch):
    monkeypatch.setattr(finestra.faccia, "premi", lambda tasto: None)
    finestra.attesa = Attesa("area", gioco=True)
    assert not finestra.si_apre_la_scacchiera()
    finestra.fornitore = lambda: {"board": chess.Board()}
    try:
        assert finestra.si_apre_la_scacchiera()
        finestra.premi_nel_prompt("e")
        assert not finestra.si_apre_la_scacchiera()
        finestra.premi_nel_prompt("\x08")
        assert finestra.si_apre_la_scacchiera()
        finestra.premi_nel_prompt("x")
        finestra.premi_nel_prompt("\r")
        assert finestra.si_apre_la_scacchiera()
        # Una domanda che non e' il prompt delle mosse, e Tempo senza scacchiera.
        finestra.attesa = Attesa("area")
        assert not finestra.si_apre_la_scacchiera()
        finestra.attesa = Attesa("area", gioco=True)
        finestra.fornitore = lambda: {"board": None}
        assert not finestra.si_apre_la_scacchiera()
    finally:
        finestra.fornitore = None


def test_frecce_lettere_e_annunci(finestra, aperta):
    dialogo = aperta["apri"]()
    assert aperta["suonati"] == ["apri"]
    assert dialogo.area.GetValue().split("\n") == dialogo.scacchiera.righe()
    assert _ultimo_detto(finestra, f"{nome_casa(chess.E1)}, Re bianco")
    # Il cursore dell'area sul segno della casa.
    _trovata, colonna, riga = dialogo.area.PositionToXY(dialogo.area.GetInsertionPoint())
    assert dialogo.area.GetLineText(riga)[colonna] == "K"
    _tasto(dialogo, wx.WXK_LEFT)
    assert _ultimo_detto(finestra, f"{nome_casa(chess.D1)}, Donna bianca")
    _tasto(dialogo, wx.WXK_DOWN)
    assert aperta["suonati"][-1] == "bordo"
    assert dialogo.scacchiera.cursore == chess.D1
    _tasto(dialogo, wx.WXK_DOWN, "Alt")
    assert dialogo.scacchiera.cursore == chess.D8
    assert aperta["suonati"][-1] == "giro_giu"
    # Con Alt lontano dal bordo e' un passo, senza suono.
    _tasto(dialogo, wx.WXK_LEFT, "Alt")
    assert dialogo.scacchiera.cursore == chess.C8
    assert aperta["suonati"][-1] == "giro_giu"
    for _volta in range(3):
        _tasto(dialogo, wx.WXK_LEFT, "Alt")
    assert dialogo.scacchiera.cursore == chess.H8
    assert aperta["suonati"][-1] == "giro_sinistra"
    _tasto(dialogo, wx.WXK_RIGHT, "Alt")
    _tasto(dialogo, wx.WXK_UP, "Alt")
    assert dialogo.scacchiera.cursore == chess.A1
    assert aperta["suonati"][-2:] == ["giro_destra", "giro_su"]
    _scrivi(dialogo, "d8")
    _tasto(dialogo, wx.WXK_RIGHT, "Control")
    assert dialogo.scacchiera.cursore == chess.E7
    _tasto(dialogo, wx.WXK_LEFT, "Shift")
    assert dialogo.scacchiera.cursore == chess.D8
    _scrivi(dialogo, "e4")
    assert _ultimo_detto(finestra, f"{nome_casa(chess.E4)}, vuota")
    _scrivi(dialogo, "7")
    assert dialogo.scacchiera.cursore == chess.E7
    _scrivi(dialogo, "9")
    assert dialogo.scacchiera.dal_nero
    assert _ultimo_detto(finestra, "Dal Nero")
    assert aperta["premuti"] == []


def test_la_mossa_va_al_nucleo(finestra, aperta):
    dialogo = aperta["apri"]()
    _scrivi(dialogo, "e2")
    _tasto(dialogo, wx.WXK_SPACE)
    assert aperta["suonati"][-1] == "solleva"
    assert "[P]" in dialogo.area.GetValue()
    assert _ultimo_detto(finestra, "Sollevato: Pedone bianco")
    _tasto(dialogo, wx.WXK_SPACE, "Control")
    assert _ultimo_detto(finestra, f"In mano: Pedone bianco, da {nome_casa(chess.E2)}.")
    _scrivi(dialogo, "e4")
    _tasto(dialogo, wx.WXK_RETURN)
    assert _mandati(aperta) == "e4\r"
    assert aperta["suonati"][-1] == "posa"
    assert dialogo.scacchiera.sollevato is None


def test_la_mossa_illegale_si_spiega(finestra, aperta):
    dialogo = aperta["apri"]()
    _scrivi(dialogo, "e2")
    _tasto(dialogo, wx.WXK_SPACE)
    _scrivi(dialogo, "e5")
    _tasto(dialogo, wx.WXK_RETURN)
    assert aperta["premuti"] == []
    assert aperta["suonati"][-1] == "mossa_non_vale"
    assert _ultimo_detto(finestra, f"Pedone bianco non puo' andare in {nome_casa(chess.E5)}.")
    # Posato di nuovo sulla sua casa.
    _scrivi(dialogo, "e2")
    _tasto(dialogo, wx.WXK_SPACE)
    assert aperta["suonati"][-1] == "rimetti"
    assert dialogo.scacchiera.sollevato is None
    # Invio senza niente in mano, spazio su una casa vuota, u senza mosse.
    _tasto(dialogo, wx.WXK_RETURN)
    assert aperta["suonati"][-1] == "niente_in_mano"
    assert _ultimo_detto(finestra, "Nessun pezzo in mano.")
    _scrivi(dialogo, "e4")
    _tasto(dialogo, wx.WXK_SPACE)
    assert aperta["suonati"][-1] == "casa_vuota"
    _scrivi(dialogo, "u")
    assert aperta["suonati"][-1] == "nessuna_mossa"


def test_la_promozione_chiede_il_pezzo(finestra, aperta, monkeypatch):
    aperta["dati"]["board"] = chess.Board("8/4P2k/8/8/8/8/8/4K3 w - - 0 1")
    domande = []

    def scegli(genitore, titolo, voci, scelta):
        domande.append((titolo, voci))
        return 3

    monkeypatch.setattr(finestra, "scegli", scegli)
    dialogo = aperta["apri"]()
    _scrivi(dialogo, "e7")
    _tasto(dialogo, wx.WXK_SPACE)
    _scrivi(dialogo, "e8")
    _tasto(dialogo, wx.WXK_RETURN)
    assert domande == [("Promozione", ["Donna", "Torre", "Alfiere", "Cavallo"])]
    assert _mandati(aperta) == "e8=N\r"


def test_i_comandi(finestra, aperta, monkeypatch):
    monkeypatch.setattr(finestra, "chiedi_valore", lambda *argomenti: "bella")
    dialogo = aperta["apri"]()
    _tasto(dialogo, wx.WXK_TAB)
    _tasto(dialogo, wx.WXK_F1)
    _scrivi(dialogo, "RWwC")
    assert _mandati(aperta) == "-e1\r.1\r,R\r-\r+\r.c bella\r"
    # La b senza numero, passato il tempo, dice gli alfieri neri.
    del aperta["premuti"][:]
    _scrivi(dialogo, "b")
    assert aperta["premuti"] == []
    assert pompa(lambda: _mandati(aperta) == ",b\r", 2)
    _scrivi(dialogo, "l")
    assert _ultimo_detto(finestra, "Nessuna mossa ancora giocata.")
    _scrivi(dialogo, "g1m")
    assert _ultimo_detto(finestra, f"Cavallo bianco in {nome_casa(chess.G1)}: {nome_casa(chess.F3)}, {nome_casa(chess.H3)}.")
    # Dove la modalita' non ha gli orologi, F1 suona il no.
    finestra.comandi = [("draw", "draw : Proponi patta")]
    del aperta["premuti"][:]
    _tasto(dialogo, wx.WXK_F1)
    _scrivi(dialogo, "C")
    assert aperta["premuti"] == []
    assert aperta["suonati"][-2:] == ["comando_assente", "comando_assente"]


RISPOSTA_DEL_MENU = {}


class _MenuFinto:
    """Il menu della partita, senza finestra: risponde come dice
    RISPOSTA_DEL_MENU."""

    def __init__(self, genitore, nodi):
        self.nodi = nodi
        self.scelto = RISPOSTA_DEL_MENU.get("scelto")
        self.ripresa = RISPOSTA_DEL_MENU.get("ripresa", False)

    def __enter__(self):
        return self

    def __exit__(self, *errore):
        return False

    def ShowModal(self):
        return wx.ID_OK


def test_backspace_ferma_il_tempo_e_apre_il_menu(finestra, aperta, monkeypatch):
    monkeypatch.setattr(finestra_scacchiera, "MenuDellaPartita", _MenuFinto)
    dialogo = aperta["apri"]()
    RISPOSTA_DEL_MENU.clear()
    RISPOSTA_DEL_MENU.update({"ripresa": True})
    _tasto(dialogo, wx.WXK_BACK)
    assert _mandati(aperta) == ".p\r.p\r"
    del aperta["premuti"][:]
    # Gia' in pausa: il menu si apre e basta; il comando scelto va al nucleo.
    aperta["dati"]["pausa"] = True
    RISPOSTA_DEL_MENU.clear()
    RISPOSTA_DEL_MENU.update({"scelto": finestra_scacchiera.plancia.Nodo(".l", ".l")})
    _tasto(dialogo, wx.WXK_BACK)
    assert _mandati(aperta) == ".l\r"
    # Senza orologi niente pausa.
    del aperta["premuti"][:]
    aperta["dati"].update(pausa=False, senza_orologio=True)
    RISPOSTA_DEL_MENU.clear()
    RISPOSTA_DEL_MENU.update({"ripresa": True})
    _tasto(dialogo, wx.WXK_BACK)
    assert aperta["premuti"] == []


def test_la_vista_ferma_e_la_partita_da_guardare(finestra, aperta):
    aperta["dati"]["vista_ferma"] = True
    dialogo = aperta["apri"]()
    _tasto(dialogo, wx.WXK_TAB)
    assert _mandati(aperta) == " -e1\r"
    del aperta["premuti"][:]
    aperta["dati"].update(vista_ferma=False, da_guardare=True)
    _tasto(dialogo, wx.WXK_SPACE)
    _tasto(dialogo, wx.WXK_RETURN)
    assert aperta["premuti"] == []
    assert aperta["suonati"][-2:] == ["da_guardare", "da_guardare"]
    assert _ultimo_detto(finestra, "Qui la scacchiera e' solo da guardare.")


def test_un_suono_per_evento_firmato_da_orologic():
    """Ogni evento della scacchiera ha un preset suo, che c'e' nella
    collezione, diverso da tutti gli altri anche nel contenuto, e firmato da
    Orologic; ogni evento che il codice suona ha il suo preset e la sua
    azione nell'elenco per Acu_Maker."""
    import pathlib
    import re

    from GBUtils import Acusticator

    suoni = finestra_scacchiera.SUONI
    nomi = list(suoni.values())
    assert len(set(nomi)) == len(nomi)
    impronte = {repr(Acusticator.preset(nome)) for nome in nomi}
    assert len(impronte) == len(nomi)
    for nome in nomi:
        assert "orologic" in Acusticator.usato_da(nome), nome
    assert set(finestra_scacchiera.GIRI.values()) <= set(suoni)
    sorgente = pathlib.Path(finestra_scacchiera.__file__).read_text(encoding="utf-8")
    usati = set(re.findall(r'suona\("([a-z_]+)"\)', sorgente)) | set(finestra_scacchiera.GIRI.values())
    assert usati == set(suoni)
    assert set(finestra_scacchiera.AZIONI) == set(suoni)


def test_l_elenco_dei_suoni_e_aggiornato():
    """suoni_della_scacchiera.txt e' quello che scrive strumenti/elenco_suoni.py
    dalle tabelle di adesso: se una cambia, si rigenera."""
    import importlib.util
    import pathlib

    radice = pathlib.Path(__file__).resolve().parent.parent
    specifica = importlib.util.spec_from_file_location("elenco_suoni", radice / "strumenti" / "elenco_suoni.py")
    elenco = importlib.util.module_from_spec(specifica)
    specifica.loader.exec_module(elenco)
    assert (radice / elenco.NOME_DEL_FILE).read_bytes().decode("utf-8") == elenco.testo()


def test_la_posizione_nuova_e_la_fine_della_partita(finestra, aperta):
    dialogo = aperta["apri"]()
    aperta["dati"]["board"] = chess.Board()
    aperta["dati"]["board"].push_san("e4")
    assert pompa(lambda: dialogo.scacchiera.board.piece_at(chess.E4) is not None, 2)
    assert dialogo.area.GetValue().split("\n")[4] == "4| - | + | - | + | P | + | - | + |4"
    finestra.fornitore = None
    assert pompa(lambda: dialogo.chiusa, 2)
    # Chiusa, non scrive piu' nel prompt.
    dialogo.scrivi("e5")
    assert aperta["premuti"] == []


def test_una_domanda_la_chiude_e_il_prompt_la_riapre(finestra, aperta, monkeypatch):
    dialogo = aperta["apri"]()
    finestra._cambia_attesa(Attesa("area", gioco=True))
    assert not dialogo.chiusa
    finestra._cambia_attesa(Attesa(None))
    assert not dialogo.chiusa
    finestra._cambia_attesa(Attesa("sino", prompt="Salvi?"))
    assert dialogo.chiusa
    assert finestra.scacchiera_da_riaprire
    assert finestra.fuoco_voluto == "console"
    # Come alla fine di apri_la_scacchiera.
    finestra.dialogo_scacchiera = None
    riaperte = []
    monkeypatch.setattr(finestra, "apri_la_scacchiera", lambda: riaperte.append(True))
    finestra._cambia_attesa(Attesa("area", gioco=True))
    assert pompa(lambda: riaperte == [True], 2)
    assert not finestra.scacchiera_da_riaprire


def test_una_partita_col_ciclo_d_attesa_vero(finestra, monkeypatch):
    suonati = []
    monkeypatch.setattr(finestra_scacchiera, "suona", suonati.append)
    stato = board_utils.GameState({"phases": [{"white_time": 300, "black_time": 300, "white_inc": 0, "black_inc": 0, "moves": 40}]})
    stato.flag_fallen = False
    stato.ignore_clock = False
    stato.refresh_interval = 0
    ricevute = []
    fine = threading.Event()

    def nucleo():
        with strato.partita():
            while True:
                mossa = game_flow.async_arbitration_input(stato, lambda: "Mossa: ")
                ricevute.append(mossa)
                if mossa == ".":
                    break
                stato.board.push_san(mossa)
                stato.move_history.append(mossa)
        fine.wait(10)

    finestra.avvia_il_nucleo(nucleo)
    try:
        assert pompa(finestra.si_apre_la_scacchiera)
        passi = {}

        def guida():
            dialogo = finestra.dialogo_scacchiera
            if dialogo is None:
                wx.CallLater(20, guida)
                return
            if not passi:
                passi["mossa"] = True
                _scrivi(dialogo, "g1")
                _tasto(dialogo, wx.WXK_SPACE)
                _scrivi(dialogo, "f3")
                _tasto(dialogo, wx.WXK_RETURN)
            if dialogo.scacchiera.board.piece_at(chess.F3) is None:
                wx.CallLater(20, guida)
                return
            _tasto(dialogo, wx.WXK_ESCAPE)

        wx.CallLater(20, guida)
        evento = wx.KeyEvent(wx.wxEVT_CHAR)
        evento.SetKeyCode(wx.WXK_SPACE)
        evento.SetUnicodeKey(wx.WXK_SPACE)
        finestra._carattere(evento)
        assert finestra.dialogo_scacchiera is None
        assert ricevute == ["Nf3"]
        assert suonati[:2] == ["apri", "solleva"]
        for tasto in ".\r":
            finestra.faccia.premi(tasto)
        assert pompa(lambda: ricevute == ["Nf3", "."] and finestra.fornitore is None)
    finally:
        fine.set()
        for tasto in ".\r":
            finestra.faccia.premi(tasto)
