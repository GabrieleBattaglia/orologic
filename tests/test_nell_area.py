# Orologic, prove del testo da studiare nell'area della finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""strato.nell_area: un testo lungo, come il riepilogo dell'analisi
automatica, entra nell'area intero e senza voce; il cursore va sulla sua
prima riga, l'unica che si annuncia, e il fuoco resta sull'area anche al
menu dopo (Gabriele, 23 novembre 2026)."""

import wx
from conftest import pompa
from GBUtils import menu

from orologic_modules import annunci, strato


def test_il_testo_da_studiare_va_nell_area_intero_e_in_silenzio(finestra):
    finestra.annunci = annunci.normalizza({"attivi": True})
    # Come nell'uso vero, l'analisi arriva dopo il menu principale: al primo
    # menu dell'avvio il cursore torna sul benvenuto, apposta.
    finestra.primo_menu = False
    # Piu' righe di quelle che l'area conserva: le tiene tutte.
    testo = "\n".join(f"Riga {numero} del riepilogo" for numero in range(finestra.righe_tenute + 100))
    scelte = []

    def nucleo():
        print("Prima dell'analisi")
        strato.nell_area(testo)
        print("Ritorno al menu principale.")
        scelte.append(menu(d={"a": "Alfa", "b": "Beta"}, show=True, keyslist=True))

    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: finestra.attesa.tipo == "menu")
    valore = finestra.area.GetValue()
    assert "Riga 0 del riepilogo\n" in valore
    assert f"Riga {finestra.righe_tenute + 99} del riepilogo" in valore
    riga, _colonna = finestra._riga_e_colonna()
    assert finestra.area.GetLineText(riga) == "Riga 0 del riepilogo"
    assert wx.Window.FindFocus() is finestra.area
    detti = finestra.sintesi.testi()
    assert "Riga 0 del riepilogo" in detti
    assert not any("Riga 1 " in detto or "Riga 150" in detto for detto in detti)
    finestra.faccia.scegli("a")
    assert pompa(lambda: scelte == ["a"])
