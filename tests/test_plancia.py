# Orologic, prove della plancia (tappa T4 della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La plancia: il percorso dei menu senza finestra, poi la finestra vera sul
desktop nascosto di conftest.py, con un nucleo finto che usa menu,
enter_escape e dgt di GBUtils, e la voce e i suoni sostituiti da registri."""

import wx
from conftest import attiva, pompa, rami_della_plancia, righe_dell_area
from GBUtils import dgt, enter_escape, menu

from orologic_modules import plancia

# Il percorso, senza finestra.


def test_il_percorso_si_apre_e_si_chiude_coi_siti():
    percorso = plancia.Percorso()
    percorso.menu("principale")
    assert percorso.etichette() == ["Menu principale"]
    percorso.scelto("Orologi")
    assert percorso.etichette() == ["Menu principale", "Orologi"]
    percorso.menu("orologi")
    assert percorso.etichette() == ["Menu principale", "Orologi"]
    percorso.scelto("Elimina orologio")
    percorso.menu("quale orologio")
    assert percorso.etichette() == ["Menu principale", "Orologi", "Elimina orologio"]
    # Lo stesso menu di nuovo, con voci diverse: resta dov'e'.
    percorso.scelto("Lampo")
    percorso.menu("quale orologio")
    assert percorso.etichette() == ["Menu principale", "Orologi", "Elimina orologio"]
    # Tornare a un menu del percorso chiude quelli sotto.
    percorso.menu("principale")
    assert percorso.etichette() == ["Menu principale"]


def test_il_menu_principale_riparte_dalla_radice():
    percorso = plancia.Percorso()
    percorso.menu("domanda all'avvio", "Lingua: ")
    percorso.scelto("Italiano")
    percorso.menu("principale", alla_radice=True)
    assert percorso.etichette() == ["Menu principale"]


def test_senza_scelta_il_livello_prende_il_prompt():
    percorso = plancia.Percorso()
    percorso.menu("primo")
    percorso.menu("secondo", "\nScegli il filtro: ")
    assert percorso.etichette() == ["Menu principale", "Scegli il filtro"]


def test_le_voci_del_menu():
    voci = [(".", "Esci"), ("crea", "Nuovo orologio"), ("7", "")]
    assert plancia.voci_del_menu(voci) == [("Nuovo orologio", "crea"), ("7", "7"), ("Esci", ".")]
    con_invio = plancia.voci_del_menu(voci, "\nScegli o premi INVIO: ", "procedi")
    assert con_invio[-1] == ("Invio senza scegliere: Scegli o premi INVIO:", "procedi")
    assert plancia.voci_del_menu(voci, "", ".") == plancia.voci_del_menu(voci)


# La finestra.


def test_menu_domande_e_fuoco_nella_plancia(finestra):
    esiti = []

    def nucleo():
        print("Benvenuto.")
        while True:
            scelta = menu({"orologi": "Orologi", ".": "Esci"}, p="Scegli: ")
            if scelta == ".":
                break
            esiti.append(scelta)
            if scelta == "orologi":
                esiti.append(menu({"crea": "Nuovo orologio", ".": "Indietro"}))
                esiti.append(enter_escape("Confermi? "))
                esiti.append(dgt("Nome: "))
        print("Fine.")

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.attesa.tipo == "menu")
    # Le voci stanno nella plancia, non nell'area, e il fuoco va da loro.
    assert rami_della_plancia(finestra) == [(0, "Menu principale"), (1, "Orologi"), (1, "Esci")]
    assert "Orologi" not in finestra.area.GetValue()
    assert pompa(lambda: wx.Window.FindFocus() is finestra.plancia)
    assert finestra.suonati == ["spostamento_f5"]
    assert finestra.plancia.GetItemText(finestra.plancia.GetSelection()) == "Orologi"
    # Cio' che si scrive nell'area mentre la plancia aspetta non va al nucleo.
    finestra.vai_all_area()
    pompa(lambda: False, 0.1)
    finestra._manda("x")
    assert wx.Window.FindFocus() is finestra.plancia
    attiva(finestra, "Orologi")
    assert pompa(lambda: finestra.attesa.tipo == "menu" and len(rami_della_plancia(finestra)) == 4)
    assert rami_della_plancia(finestra) == [(0, "Menu principale"), (1, "Orologi"), (2, "Nuovo orologio"), (2, "Indietro")]
    attiva(finestra, "Nuovo orologio")
    # La domanda: Si' e No nella plancia, il fuoco all'area per Invio ed Esc.
    assert pompa(lambda: finestra.attesa.tipo == "sino")
    assert rami_della_plancia(finestra)[-3:] == [(3, "Confermi?"), (4, "Sì, come Invio"), (4, "No, come Esc")]
    assert pompa(lambda: wx.Window.FindFocus() is finestra.area)
    attiva(finestra, "Sì, come Invio")
    assert pompa(lambda: finestra.attesa.tipo == "area" and "Nome:" in finestra.area.GetValue())
    for tasto in "Lampo\r":
        finestra.faccia.premi(tasto)
    # Di nuovo il menu principale: il percorso si richiude.
    assert pompa(lambda: finestra.attesa.tipo == "menu" and rami_della_plancia(finestra)[0] == (0, "Menu principale") and len(rami_della_plancia(finestra)) == 3)
    # Tornando al menu e' selezionata la voce scelta l'ultima volta.
    assert finestra.plancia.GetItemText(finestra.plancia.GetSelection()) == "Orologi"
    # Esc nella plancia vale come Esc nel menu: il ciclo lo ripropone.
    finestra._tasto_della_plancia(_tasto(wx.WXK_ESCAPE))
    assert pompa(lambda: finestra.attesa.tipo == "menu")
    attiva(finestra, "Esci")
    assert pompa(lambda: not finestra.nucleo.is_alive())
    assert esiti == ["orologi", "crea", True, "Lampo", None]
    assert righe_dell_area(finestra)[0] == "Benvenuto."
    assert "Fine." in finestra.area.GetValue()
    assert finestra.suonati[:3] == ["spostamento_f5", "spostamento_f6", "spostamento_f5"]


def _tasto(codice):
    evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    evento.SetKeyCode(codice)
    return evento
