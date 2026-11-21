# Orologic, prove della plancia (tappa T4 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La plancia: l'albero dei menu senza finestra, poi la finestra vera sul
desktop nascosto di conftest.py, con un nucleo finto che usa menu,
enter_escape e dgt di GBUtils, e la voce e i suoni sostituiti da registri."""

import wx
from conftest import attiva, pompa, rami_della_plancia, voce_della_plancia
from GBUtils import dgt, enter_escape, menu

from orologic_modules import (
    config,
    game_flow,
    lichess_app,
    lichess_eventi,
    plancia,
    strato,
)

# L'albero, senza finestra.


def test_i_livelli_si_aprono_e_si_chiudono_coi_siti():
    albero = plancia.Albero()
    albero.menu("principale", [("orologi", "Orologi"), (".", "Esci")])
    albero.scelto("orologi")
    albero.menu("orologi", [("elimina", "Elimina"), (".", "Indietro")])
    assert albero.percorso() == ("orologi",)
    albero.scelto("elimina")
    albero.menu("quale", [("lampo", ""), (".", "Indietro")])
    assert albero.percorso() == ("orologi", "elimina")
    # Lo stesso menu con voci diverse resta dov'e'.
    albero.menu("quale", [(".", "Indietro")])
    assert albero.percorso() == ("orologi", "elimina")
    assert albero.adesso().voci == [(".", "Indietro")]
    # Tornare a un menu della pila chiude quelli sotto.
    albero.menu("principale", [("orologi", "Orologi"), (".", "Esci")])
    assert albero.percorso() == ()
    # Il menu principale riparte dalla radice.
    albero.scelto("orologi")
    albero.menu("altro", [("x", "X")])
    albero.menu("principale", [("orologi", "Orologi")], alla_radice=True)
    assert len(albero.livelli) == 1


def test_la_strada_verso_una_voce():
    albero = plancia.Albero()
    albero.menu("principale", [("orologi", "Orologi"), ("analizza", "Analisi"), (".", "Esci")])
    assert albero.strada(("orologi",)) == ("avanti", "orologi")
    albero.scelto("orologi")
    albero.menu("orologi", [("crea", "Nuovo"), (".", "Indietro")])
    assert albero.strada(("orologi",)) == ("arrivato", None)
    assert albero.strada(("orologi",), "crea") == ("finale", "crea")
    assert albero.strada((), "analizza") == ("indietro", ".")
    albero.scelto("crea")
    albero.menu("senza punto", [("a", "A"), ("b", "B")])
    assert albero.strada(()) == ("indietro", None)


def test_le_voci_del_menu_hanno_il_testo_di_menu(monkeypatch):
    monkeypatch.setitem(plancia.RAMI, ("orologic.py", "Main"), {"orologi"})
    livello = plancia.Livello(("C:\\x\\orologic.py", "Main", 610), [(".", "Esci"), ("orologi", "Orologi"), ("7", "")])
    assert plancia.voci_del_menu(livello) == [(".: Esci", ".", False), ("orologi: Orologi", "orologi", True), ("7", "7", False)]
    livello = plancia.Livello(None, [("eco", "Codice ECO"), (".", "Torna")], "Scegli: ", "procedi")
    assert plancia.voci_del_menu(livello)[-1] == ("INVIO", "procedi", False)


def test_i_comandi_della_partita_dalle_righe_dell_aiuto():
    nodi = {nodo.etichetta: nodo for nodo in plancia.comandi_della_partita(config.DOT_COMMANDS)}
    assert nodi[".3: Mostra entrambi gli orologi"] == plancia.Nodo(".3: Mostra entrambi gli orologi", ".3")
    diagonale = nodi["/[col]: Esplora diagonale alto-destra"]
    assert [figlio.testo for figlio in diagonale.figli] == [f"/{c}" for c in "abcdefgh"]
    esplora = nodi["-[col|trv|casa]: Esplora colonna, traversa o casa"]
    assert [figlio.etichetta for figlio in esplora.figli] == ["col", "trv", "casa"]
    assert esplora.figli[2].figli[0].figli[7].testo == "-a8"
    pezzi = nodi[",[P,N,B,R,Q,K]: Posizioni di un pezzo specifico"]
    assert [figlio.testo for figlio in pezzi.figli] == [",P", ",N", ",B", ",R", ",Q", ",K"]
    risultati = next(nodo for etichetta, nodo in nodi.items() if etichetta.startswith(".1-0 .0-1"))
    assert [figlio.testo for figlio in risultati.figli] == [".1-0", ".0-1", ".1/2", ".*"]
    assert [figlio.testo for figlio in nodi[".s oppure .b: Scacchiera testuale"].figli] == [".s", ".b"]
    motore = plancia.comandi_della_partita({".s#": "Livello", ".e#": "Elo", "_[testo]": "Chat"})
    assert [figlio.testo for figlio in motore[0].figli] == [f".s{n}" for n in range(21)]
    assert (motore[1].testo, motore[1].invio, motore[2].testo, motore[2].invio) == (".e", False, "_", False)
    lichess = plancia.comandi_della_partita([(".1", ".1 : Tempo Bianco")])
    assert lichess == [plancia.Nodo(".1 : Tempo Bianco", ".1")]


# La finestra.

PRINCIPALE = {"orologi": "Orologi", "analizza": "Analisi", ".": "Esci"}
OROLOGI = {"crea": "Nuovo orologio", "elimina": "Elimina orologio", ".": "Indietro"}


def _apri(finestra, etichetta):
    finestra.plancia.Expand(voce_della_plancia(finestra, etichetta))


def _chiudi(finestra, etichetta):
    finestra.plancia.Collapse(voce_della_plancia(finestra, etichetta))


def _selezionata(finestra):
    return finestra.plancia.GetItemText(finestra.plancia.GetSelection())


def test_l_albero_dei_menu(finestra, monkeypatch):
    monkeypatch.setitem(plancia.RAMI, ("test_plancia.py", "nucleo"), {"orologi"})
    esiti = []

    def orologi():
        while True:
            scelta = menu(OROLOGI)
            if scelta in (".", None):
                return
            esiti.append(scelta)
            if scelta == "crea":
                esiti.append(enter_escape("Confermi? "))
                esiti.append(dgt("Nome: "))

    def nucleo():
        print("Benvenuto.")
        while True:
            scelta = menu(PRINCIPALE, p="Scegli: ")
            if scelta == ".":
                break
            esiti.append(scelta)
            if scelta == "orologi":
                orologi()
        print("Fine.")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.attesa.tipo == "menu")
    # Il testo e l'ordine dell'elenco di menu; nell'area niente voci.
    assert rami_della_plancia(finestra) == [(0, ".: Esci"), (0, "analizza: Analisi"), (0, "orologi: Orologi")]
    assert "Orologi" not in finestra.area.GetValue()
    assert finestra.plancia.ItemHasChildren(voce_della_plancia(finestra, "orologi: Orologi"))
    assert pompa(lambda: wx.Window.FindFocus() is finestra.plancia)
    assert finestra.suonati == ["spostamento_f5"]
    # Freccia destra sul ramo: Orologic entra, e il ramo si apre.
    _apri(finestra, "orologi: Orologi")
    assert pompa(lambda: len(rami_della_plancia(finestra)) == 6)
    assert rami_della_plancia(finestra)[3:] == [(1, ".: Indietro"), (1, "crea: Nuovo orologio"), (1, "elimina: Elimina orologio")]
    assert finestra.plancia.IsExpanded(voce_della_plancia(finestra, "orologi: Orologi"))
    assert _selezionata(finestra) == "orologi: Orologi"
    # Freccia sinistra sul ramo aperto: Orologic torna su col punto.
    _chiudi(finestra, "orologi: Orologi")
    assert pompa(lambda: len(rami_della_plancia(finestra)) == 3 and finestra.attesa.tipo == "menu")
    assert _selezionata(finestra) == "orologi: Orologi"
    # Una voce dentro il ramo: Orologic entra e la sceglie.
    _apri(finestra, "orologi: Orologi")
    assert pompa(lambda: len(rami_della_plancia(finestra)) == 6)
    attiva(finestra, "crea: Nuovo orologio")
    # La domanda sotto la voce, con INVIO ed ESC; il fuoco all'area.
    assert pompa(lambda: finestra.attesa.tipo == "sino")
    assert rami_della_plancia(finestra)[4:8] == [(1, "crea: Nuovo orologio"), (2, "Confermi?"), (3, "INVIO"), (3, "ESC")]
    assert pompa(lambda: wx.Window.FindFocus() is finestra.area)
    attiva(finestra, "INVIO")
    assert pompa(lambda: finestra.attesa.tipo == "area" and "Nome:" in finestra.area.GetValue())
    for tasto in "Lampo\r":
        finestra.faccia.premi(tasto)
    # Di nuovo il menu degli orologi, con la voce scelta selezionata.
    assert pompa(lambda: finestra.attesa.tipo == "menu" and len(rami_della_plancia(finestra)) == 6)
    assert _selezionata(finestra) == "crea: Nuovo orologio"
    # Una voce del menu sopra: Orologic torna su e la sceglie.
    attiva(finestra, "analizza: Analisi")
    assert pompa(lambda: finestra.attesa.tipo == "menu" and len(rami_della_plancia(finestra)) == 3 and "analizza" in esiti)
    attiva(finestra, ".: Esci")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert esiti == ["orologi", "orologi", "crea", True, "Lampo", "analizza"]
    assert "Fine." in finestra.area.GetValue()


def test_cio_che_si_scrive_mentre_la_plancia_aspetta(finestra):
    def nucleo():
        menu({"a": "Prima", "b": "Seconda"})

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.attesa.tipo == "menu")
    finestra.vai_all_area()
    pompa(lambda: False, 0.1)
    finestra._manda("x")
    assert wx.Window.FindFocus() is finestra.plancia
    # Esc nella plancia vale come Esc nel menu.
    evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    evento.SetKeyCode(wx.WXK_ESCAPE)
    finestra._tasto_della_plancia(evento)
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_i_comandi_della_partita_nella_plancia(finestra):
    esiti = []
    comandi = {".": "Esci", ".3": "Entrambi gli orologi", "/[col]": "Diagonale"}

    def nucleo():
        stato = type("Stato", (), {"flag_fallen": False, "ignore_clock": False, "refresh_interval": 0, "vista_ferma": False})()
        with strato.partita():
            esiti.append(game_flow.async_arbitration_input(stato, lambda: "1. e4 ", comandi))
            esiti.append(game_flow.async_arbitration_input(stato, lambda: "1. e4 ", comandi))
        esiti.append("fine")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.comandi == comandi and finestra.attesa.tipo == "area")
    assert [r for r in rami_della_plancia(finestra) if r[0] == 0] == [(0, ".: Esci"), (0, ".3: Entrambi gli orologi"), (0, "/[col]: Diagonale")]
    attiva(finestra, ".3: Entrambi gli orologi")
    assert pompa(lambda: len(esiti) == 1)
    assert esiti == [".3"]
    # Il ramo della diagonale, con le otto colonne.
    _apri(finestra, "/[col]: Diagonale")
    attiva(finestra, "/e")
    assert pompa(lambda: esiti[-1] == "fine")
    assert esiti == [".3", "/e", "fine"]
    assert pompa(lambda: finestra.comandi is None and ".3: Entrambi gli orologi" not in [r for _p, r in rami_della_plancia(finestra)])


def test_la_sfida_che_arriva_interrompe_il_menu_di_orolichess(finestra, monkeypatch):
    monkeypatch.setattr(lichess_app, "scorda_cache_rete", lambda: None)
    esiti = []
    voci = {"gioca": "Gioca", ".": "Esci"}

    def nucleo():
        esiti.append(lichess_app.scegli_ascoltando_le_sfide(voci, {}, "\nScegli: "))
        esiti.append(lichess_app.scegli_ascoltando_le_sfide(voci, {}, "\nScegli: "))

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.attesa.tipo == "menu")
    assert "Gioca" not in finestra.area.GetValue()
    lichess_eventi.sfida_arrivata.set()
    assert pompa(lambda: finestra.attesa.tipo == "sino")
    finestra.faccia.premi("\x1b")
    assert pompa(lambda: len(esiti) == 1 and finestra.attesa.tipo == "menu")
    attiva(finestra, "gioca: Gioca")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert esiti == [None, "gioca"]
    assert not lichess_eventi.sfida_arrivata.is_set()


def test_il_ramo_che_non_si_apre_ferma_la_strada(finestra, monkeypatch):
    """Come arbitra senza orologi salvati: la voce e' un ramo, ma Orologic
    stampa e torna allo stesso menu. La plancia non riprova."""
    monkeypatch.setitem(plancia.RAMI, ("test_plancia.py", "nucleo"), {"arbitra"})
    scelte = []

    def nucleo():
        while True:
            scelta = menu({"arbitra": "Arbitraggio", ".": "Esci"})
            scelte.append(scelta)
            if scelta == ".":
                return
            print("Nessun orologio salvato.")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.attesa.tipo == "menu")
    _apri(finestra, "arbitra: Arbitraggio")
    assert pompa(lambda: scelte == ["arbitra"] and finestra.attesa.tipo == "menu" and finestra.meta is None)
    pompa(lambda: False, 0.3)
    assert scelte == ["arbitra"]
    attiva(finestra, ".: Esci")
    assert pompa(lambda: not finestra.nucleo.is_alive())


def test_i_rami_del_censimento():
    principale = ("C:\\o\\orologic.py", "Main", 1)
    assert plancia.e_un_ramo(principale, "orologi") and not plancia.e_un_ramo(principale, "analizza")
    amici = ("C:\\o\\lichess_app.py", "menu_amici", 1)
    assert plancia.e_un_ramo(amici, "vedi", ["vedi", "cerca", "."]) and not plancia.e_un_ramo(amici, "cerca", ["vedi", "cerca", "."])
    assert plancia.e_un_ramo(amici, "gabry", ["gabry", "."]) and not plancia.e_un_ramo(amici, ".", ["gabry", "."])
    statistiche = ("C:\\o\\lichess_stats.py", "run_stats", 1)
    assert plancia.e_un_ramo(statistiche, "blitz", ["blitz", "."]) and not plancia.e_un_ramo(statistiche, "1", ["1", "2", "3", "."])
