# Orologic, prove della ricerca PGN nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La ricerca PGN come l'ha descritta Gabriele il 21 novembre 2026: il file
scelto con la finestra di Windows o gli appunti, il caricamento nel filo, le
statistiche, i filtri, l'albero delle mosse un ramo alla volta, la foglia che
mostra la partita, i pulsanti, e il ritorno allo stesso punto dopo Easyfish o
l'analisi. Le finestre di Windows, la vista della partita e l'elenco delle
partite sono sostituite, i suoni e gli annunci si segnano."""

import io
import sys

import chess
import pytest
import wx
from conftest import pompa

from orologic_modules import board_utils, finestra_ricerca, pgn_search

ARCHIVIO = """[Event "Prova"]
[White "Rossi"]
[Black "Bianchi"]
[Result "1-0"]
[Date "2020.01.01"]

1. e4 e5 2. Nf3 Nc6 1-0

[Event "Prova"]
[White "Verdi"]
[Black "Rossi"]
[Result "0-1"]
[Date "2021.01.01"]

1. e4 c5 2. Nf3 0-1

[Event "Torneo"]
[White "Rossi"]
[Black "Neri"]
[Result "1/2-1/2"]

1. d4 d5 1/2-1/2

[Event "Prova"]
[White "Gialli"]
[Black "Rossi"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nf6 {Una variante} (2... d6) 1-0
"""


def archivio():
    caricato, righe = pgn_search.carica_archivio("testo", ARCHIVIO)
    assert caricato is not None, righe
    return caricato


def test_il_caricamento_dal_testo_e_le_righe():
    caricato, righe = pgn_search.carica_archivio("testo", ARCHIVIO)
    assert len(caricato.games) == 4
    assert righe[-1] == "Caricate 4 partite valide."
    assert caricato.giocatore_comune == "Rossi"
    riepilogo = pgn_search.righe_dell_archivio(caricato)
    assert riepilogo[:3] == ["Archivio PGN Caricato", "Partite totali: 4", "Statistiche Risultati"]
    assert "Vittorie Bianco: 2 (50.0%)" in riepilogo
    assert "Patte: 1 (25.0%)" in riepilogo
    assert "Rilevato giocatore principale: Rossi (presente in >=90% delle partite)." in riepilogo
    assert riepilogo[-1] == "Attenzione: l'archivio contiene solo 4 partite (minimo consigliato: 20)."
    # Niente righe vuote, e uno spazio solo fra le parole.
    assert all(riga and "  " not in riga for riga in riepilogo)


def test_i_caricamenti_che_non_vanno(tmp_path):
    assert pgn_search.carica_archivio("testo", "  ")[1] == ["Gli appunti sono vuoti."]
    assert pgn_search.carica_archivio("testo", "la spesa di domani")[1] == ["Il testo negli appunti non sembra contenere dati PGN validi."]
    caricato, righe = pgn_search.carica_archivio("file", str(tmp_path / "manca.pgn"))
    assert caricato is None
    assert righe[0].startswith("Rilevato percorso file: ") and righe[1].startswith("Errore nella lettura del file: ")
    # Fermato subito: nessuna partita.
    caricato, righe = pgn_search.carica_archivio("testo", ARCHIVIO, fermato=lambda: True)
    assert caricato is None and righe == ["Nessuna partita valida trovata nel PGN."]


def test_fermato_a_meta_tiene_le_partite_lette():
    lette = []

    def fermato():
        return len(lette) >= 1

    caricato, righe = pgn_search.carica_archivio("testo", ARCHIVIO, avanzamento=lette.append, fermato=fermato)
    assert lette == ["Partite caricate: 1..."]
    assert len(caricato.games) == 1
    assert righe[-2:] == ["Lettura fermata: tengo le partite lette finora.", "Caricate 1 partite valide."]


def test_lo_scaricamento_fermato(monkeypatch):
    class Risposta(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_dati):
            return False

    monkeypatch.setattr(pgn_search, "_apri_indirizzo", lambda _indirizzo: Risposta(ARCHIVIO.encode("utf-8")))
    caricato, righe = pgn_search.carica_archivio("url", "https://lichess.org/api/games/user/prova")
    assert len(caricato.games) == 4
    assert righe[0] == "Rilevato URL: https://lichess.org/api/games/user/prova"
    caricato, righe = pgn_search.carica_archivio("url", "https://lichess.org/api/games/user/prova", fermato=lambda: True)
    assert caricato is None
    assert righe[1] == "Scaricamento interrotto dall'utente. Elaborazione delle partite caricate finora..."


def test_l_albero_un_ramo_alla_volta():
    a = archivio()
    rami, finite = a.figli(list(range(4)), 0)
    assert [(mossa.uci(), indici) for mossa, indici in rami] == [("e2e4", [0, 1, 3]), ("d2d4", [2])]
    assert finite == []
    # Le varianti dei commenti non entrano: la quarta partita sta solo in Nf6.
    rami, _finite = a.figli([0, 3], 3)
    assert [(mossa.uci(), indici) for mossa, indici in rami] == [("b8c6", [0]), ("g8f6", [3])]
    # Le partite che finiscono li'.
    rami, finite = a.figli([0, 1], 3)
    assert finite == [1]
    radice = pgn_search.voce_della_radice(a, [0, 1, 2, 3], {})
    assert radice == "(radice) (4 partite) | +50% =25% -25%"
    board = chess.Board()
    e4 = pgn_search.voce_del_ramo(a, board, chess.Move.from_uci("e2e4"), [0, 1, 3], 4, {})
    assert e4.endswith(" (e4) (3 partite) = 75.0% | +67% =0% -33%")
    assert e4.startswith(board_utils.DescribeMove(chess.Move.from_uci("e2e4"), board))
    d4 = pgn_search.voce_del_ramo(a, board, chess.Move.from_uci("d2d4"), [2], 4, {})
    assert d4.endswith(" (d4): Rossi vs Neri, 1/2-1/2")
    # Col filtro del giocatore le statistiche sono le sue.
    assert pgn_search.voce_della_radice(a, [0, 1, 3], {"player": "verdi"}) == "(radice) (3 partite) | +0% =0% -33%"
    mosse = a.mosse[0]
    assert pgn_search.sequenza_del_percorso(tuple(mosse)) == "1. e4 e5 2. Nf3 Nc6"
    assert pgn_search.sequenza_del_percorso(()) == "(radice)"
    assert a.voce_della_lista(board, 0, 0, 1) == "Rossi vs Bianchi (1): 1-0, 1. e4 e5 2. Nf3 Nc6"
    dopo = pgn_search.scacchiera_del_percorso(tuple(mosse[:1]))
    assert a.voce_della_lista(dopo, 1, 1, 2) == "Verdi vs Rossi (2): 0-1, 1... c5 2. Nf3"


def test_il_terminale_resta_com_era(monkeypatch):
    uscita = io.StringIO()
    monkeypatch.setattr(pgn_search.pyperclip, "paste", lambda: ARCHIVIO)
    monkeypatch.setattr(sys, "stdout", uscita)
    games = pgn_search._carica_archivio()
    assert len(games) == 4
    testo = uscita.getvalue()
    assert "Analisi del PGN in corso...\n" in testo
    assert "\rPartite caricate: 1...\n" in testo
    assert testo.endswith("Caricate 4 partite valide.\n")


def test_la_finestra_passa_a_easyfish_e_all_analisi(monkeypatch):
    """Ogni uscita va a Easyfish o all'analisi, con la partita giusta, e la
    ricerca si riapre con lo stesso stato; Chiudi la finisce."""
    uscite = [("easyfish", 0), ("automatica", 2), ("manuale", 1), None]
    stati = []

    def apri(ricerca):
        stati.append(ricerca)
        ricerca.archivio = ricerca.archivio or archivio()
        return uscite.pop(0)

    passate = []
    monkeypatch.setattr(pgn_search.strato, "ricerca_pgn", apri)
    from orologic_modules.easyfish import easyfish_app

    monkeypatch.setattr(easyfish_app, "run", lambda partita=None: passate.append(("easyfish", partita.headers["White"])))
    monkeypatch.setattr(pgn_search, "_avvia_analisi", lambda game, automatica=None: passate.append((automatica, game.headers["White"])))
    pgn_search._nella_finestra("https://lichess.org/api/games/user/prova")
    assert passate == [("easyfish", "Rossi"), (True, "Rossi"), (False, "Verdi")]
    assert len(set(map(id, stati))) == 1 and stati[0].indirizzo == "https://lichess.org/api/games/user/prova"


class Prova:
    def __init__(self, monkeypatch, ricerca, file=None):
        self.suoni = []
        self.domande = []
        self.avvisi = []
        self.detti = []
        self.partite = []
        self.scelte = []
        self.azione = None
        self.risposta = True
        self.salva_in = None
        monkeypatch.setattr(finestra_ricerca, "suona", self.suoni.append)
        monkeypatch.setattr(finestra_ricerca, "scegli_il_file", lambda _genitore: file)
        monkeypatch.setattr(finestra_ricerca, "scegli_dove_salvare", lambda _genitore: self.salva_in)
        monkeypatch.setattr(finestra_ricerca, "mostra_la_partita", self._partita)
        monkeypatch.setattr(finestra_ricerca, "scegli", self._scegli)
        self.dialogo = finestra_ricerca.FinestraRicerca(None, ricerca, self._conferma, lambda _g, testo: self.avvisi.append(testo), self.detti.extend)
        self.dialogo.Show()

    def _conferma(self, _genitore, testo):
        self.domande.append(testo)
        return self.risposta

    def _partita(self, _genitore, testo):
        self.partite.append(testo)
        return self.azione

    def _scegli(self, _genitore, titolo, voci, scelta=0):
        self.scelte.append((titolo, list(voci), scelta))
        return self.risposte_della_lista.pop(0)

    def voce(self, *etichette):
        """La voce dell'albero col principio di ogni etichetta, ramo dopo ramo."""
        albero = self.dialogo.albero
        voce = albero.GetRootItem()
        for etichetta in etichette:
            self.dialogo._popola(voce)
            voce = next(figlio for figlio in self.dialogo.figli(voce) if etichetta in albero.GetItemText(figlio))
        return voce

    def testi(self, voce):
        return [self.dialogo.albero.GetItemText(figlio) for figlio in self.dialogo.figli(voce)]

    def invio(self, oggetto):
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.SetKeyCode(wx.WXK_RETURN)
        evento.SetEventObject(oggetto)
        self.dialogo._tasto(evento)


@pytest.fixture
def prova(app, monkeypatch):
    aperte = []

    def apri(ricerca, file=None):
        aperta = Prova(monkeypatch, ricerca, file)
        aperte.append(aperta)
        return aperta

    yield apri
    # Dall'ultima aperta, come nella vita vera, dove la seconda e' modale:
    # GBwx alla distruzione rimette il fuoco nella finestra di prima, e se
    # quella e' gia' distrutta Windows cade con una violazione d'accesso.
    for aperta in reversed(aperte):
        if aperta.dialogo.filo is not None:
            aperta.dialogo.filo.join(timeout=5)
        aperta.dialogo.Destroy()
        pompa(lambda: False, 0.05)


@pytest.fixture
def file_pgn(tmp_path):
    percorso = tmp_path / "prova.pgn"
    percorso.write_text(ARCHIVIO, encoding="utf-8")
    return str(percorso)


def test_si_apre_sul_file_e_lo_carica_nel_filo(prova, file_pgn):
    p = prova(pgn_search.Ricerca(), file_pgn)
    d = p.dialogo
    assert pompa(lambda: d.ricerca.archivio is not None and not d.carica_in_corso())
    assert d.ricerca.righe[0] == "Rilevato percorso file: " + file_pgn
    assert d.riepilogo.GetValue().split("\n")[-2:] == [
        "Le statistiche dell'albero saranno relative al suo punteggio (+ = -).",
        "Attenzione: l'archivio contiene solo 4 partite (minimo consigliato: 20).",
    ]
    assert d.etichetta_dell_albero.GetLabel() == "Partite corrispondenti: 4 di 4 (100.00%)"
    assert p.detti[0] == "Analisi del PGN in corso..."
    assert p.detti[-1] == "Caricate 4 partite valide."
    radice = d.albero.GetRootItem()
    assert d.albero.GetItemText(radice) == "(radice) (4 partite) | +50% =25% -25%"
    assert d.albero.IsExpanded(radice) and d.albero.GetSelection() == radice
    testi = p.testi(radice)
    assert len(testi) == 2 and "(e4) (3 partite)" in testi[0] and testi[1].endswith("(d4): Rossi vs Neri, 1/2-1/2")
    assert pompa(lambda: wx.Window.FindFocus() is d.albero)


def test_annullato_il_file_resta_aperta_vuota(prova):
    p = prova(pgn_search.Ricerca())
    d = p.dialogo
    pompa(lambda: False, 0.2)
    assert d.ricerca.archivio is None
    assert d.riepilogo.GetValue() == "Nessun archivio caricato."
    d.inizio()
    d.percorso()
    d.applica()
    assert p.suoni == ["no", "no", "no"]


def test_dagli_appunti(prova, monkeypatch):
    p = prova(pgn_search.Ricerca())
    d = p.dialogo
    monkeypatch.setattr(finestra_ricerca.pyperclip, "paste", lambda: "")
    d.dagli_appunti()
    assert p.avvisi == ["Gli appunti sono vuoti."]
    monkeypatch.setattr(finestra_ricerca.pyperclip, "paste", lambda: ARCHIVIO)
    d.dagli_appunti()
    assert pompa(lambda: d.ricerca.archivio is not None and not d.carica_in_corso())
    assert len(d.ricerca.archivio.games) == 4


def test_un_caricamento_che_non_va_avvisa(prova, tmp_path):
    p = prova(pgn_search.Ricerca(), str(tmp_path / "manca.pgn"))
    d = p.dialogo
    assert pompa(lambda: p.avvisi)
    assert p.avvisi[0].split("\n")[1].startswith("Errore nella lettura del file: ")
    assert p.suoni == ["no"] and d.ricerca.archivio is None


def test_invio_apre_i_rami_e_mostra_la_partita(prova):
    ricerca = pgn_search.Ricerca()
    ricerca.archivio = archivio()
    p = prova(ricerca)
    d = p.dialogo
    e4 = p.voce("(e4)")
    d.albero.SelectItem(e4)
    assert not d.albero.IsExpanded(e4)
    p.invio(d.albero)
    assert d.albero.IsExpanded(e4)
    assert [testo.split(" (")[1] for testo in p.testi(e4)] == ["e5)", "c5): Verdi vs Rossi, 0-1"]
    p.invio(d.albero)
    assert not d.albero.IsExpanded(e4)
    # La foglia: la vista della partita, e Chiudi non esce.
    nc6 = p.voce("(e4)", "(e5)", "(Nf3)", "(Nc6)")
    d.albero.SelectItem(nc6)
    p.invio(d.albero)
    assert p.partite[0].split("\n") == ["Event: Prova", "Date: 2020.01.01", "White: Rossi", "Black: Bianchi", "Result: 1-0", "1. e4 e5 2. Nf3 Nc6 1-0"]
    assert d.uscita is None and d.IsShown()
    # Passa a Easyfish: l'uscita, e la posizione per il ritorno.
    p.azione = "easyfish"
    p.invio(d.albero)
    assert d.uscita == ("easyfish", 0)
    assert not d.IsShown() and d.GetReturnCode() == wx.ID_OK
    # Riaperta, torna sulla stessa foglia.
    di_nuovo = prova(ricerca).dialogo
    selezionata = di_nuovo.albero.GetSelection()
    assert di_nuovo.albero.GetItemData(selezionata).partita == 0
    assert "(Nc6): Rossi vs Bianchi, 1-0" in di_nuovo.albero.GetItemText(selezionata)


def test_i_filtri(prova):
    ricerca = pgn_search.Ricerca()
    ricerca.archivio = archivio()
    p = prova(ricerca)
    d = p.dialogo
    nomi = [d.campi[chiave].GetName() for chiave, _domanda, _tipo in finestra_ricerca.domande_dei_filtri()]
    assert nomi[:2] == ["Nome giocatore Bianco (vuoto=qualsiasi)", "Nome giocatore Nero (vuoto=qualsiasi)"]
    assert nomi[3] == "Scegli risultato"
    d.campi["event"].ChangeValue("prova")
    d.campi["result"].SetSelection(1)
    p.invio(d.campi["event"])
    assert ricerca.filtri == {"event": "prova", "result": "1-0"}
    assert d.etichetta_dell_albero.GetLabel() == "Partite corrispondenti: 2 di 4 (50.00%)"
    assert p.detti[-1] == "Partite corrispondenti: 2 di 4 (50.00%)"
    d.campi["eco"].ChangeValue("b90")
    d.campi["elo_min"].SetValue(2000)
    assert d.filtri_dei_campi() == {"event": "prova", "result": "1-0", "eco": "B90", "elo_min": 2000}
    d.azzera()
    assert ricerca.filtri == {} and d.campi["event"].GetValue() == "" and d.campi["result"].GetSelection() == 0
    assert p.detti[-1] == "Tutti i filtri sono stati rimossi (azzerati). Partite corrispondenti: 4 di 4 (100.00%)"
    # Riaperta, i campi tengono i filtri dello stato.
    ricerca.filtri = {"white": "Rossi"}
    di_nuovo = prova(ricerca).dialogo
    assert di_nuovo.campi["white"].GetValue() == "Rossi"
    assert di_nuovo.etichetta_dell_albero.GetLabel() == "Partite corrispondenti: 2 di 4 (50.00%)"


def test_i_pulsanti(prova, tmp_path):
    ricerca = pgn_search.Ricerca()
    ricerca.archivio = archivio()
    p = prova(ricerca)
    d = p.dialogo
    e5 = p.voce("(e4)", "(e5)")
    d.albero.SelectItem(e5)
    d.percorso()
    assert p.detti[-1] == "1. e4 e5"
    # Partite del ramo: l'elenco, la partita, e chiusa la partita l'elenco di nuovo.
    p.risposte_della_lista = [1, None]
    d.partite_del_ramo()
    assert p.scelte[0][0] == "Partite del ramo"
    assert p.scelte[0][1] == ["Rossi vs Bianchi (1): 1-0, 2. Nf3 Nc6", "Gialli vs Rossi (2): 1-0, 2. Nf3 Nf6"]
    assert p.scelte[1][2] == 1
    assert "White: Gialli" in p.partite[0]
    # Salva il PGN: le partite della voce.
    p.salva_in = str(tmp_path / "ramo")
    d.salva()
    with open(p.salva_in + ".pgn", encoding="utf-8") as file:
        salvato = file.read()
    assert salvato.count("[Event ") == 2 and "2... d6" in salvato
    assert p.detti[-1] == "Salvate 2 partite in: " + p.salva_in + ".pgn"
    assert p.domande == []
    # Dalla radice senza filtri si chiede prima.
    d.inizio()
    assert d.albero.GetSelection() == d.albero.GetRootItem()
    p.risposta = False
    d.salva()
    assert p.domande == ["Attenzione: non ci sono filtri attivi. Il file salvato sarebbe una copia dell'archivio originale. Salvo lo stesso?"]


def test_esc_ferma_il_caricamento(prova):
    """Esc durante il caricamento lo ferma, e la finestra resta aperta;
    fuori dal caricamento Chiudi chiude senza uscita."""
    p = prova(pgn_search.Ricerca())
    d = p.dialogo
    pompa(lambda: False, 0.1)
    fermato = d._fermato = finestra_ricerca.threading.Event()
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(wx.WXK_ESCAPE)
    evento.SetEventObject(d.riepilogo)
    d._tasto(evento)
    assert fermato.is_set() and d.IsShown()
    d._fermato = None
    d._chiudi()
    assert not d.IsShown() and d.GetReturnCode() == wx.ID_CANCEL and d.uscita is None


def test_la_vista_della_partita(app):
    game = archivio().games[0]
    vista = finestra_ricerca.VistaDellaPartita(None, finestra_ricerca.testo_della_partita(game))
    try:
        vista.Show()
        assert vista.testo.GetValue().split("\n")[0] == "Event: Prova"
        assert [p.GetLabel() for p in vista.pulsanti.values()] == ["Passa a &Easyfish", "Analisi &automatica", "Analisi &manuale"]
        vista.scegli("manuale")
        assert vista.azione == "manuale"
    finally:
        vista.Destroy()


def test_dal_nucleo_alla_finestra_e_ritorno(finestra, monkeypatch):
    """Il nucleo chiede la ricerca, la finestra la apre col suo stato, e la
    partita scelta torna al nucleo come uscita."""
    from orologic_modules import strato

    ricerca = pgn_search.Ricerca()
    ricerca.archivio = archivio()
    monkeypatch.setattr(finestra_ricerca, "mostra_la_partita", lambda _genitore, _testo: "automatica")
    uscite = []

    def nucleo():
        uscite.append(strato.ricerca_pgn(ricerca))

    def scegli_la_foglia():
        dialogo = finestra.dialogo_ricerca
        if dialogo is not None and dialogo.IsModal():
            radice = dialogo.albero.GetRootItem()
            d4 = next(figlio for figlio in dialogo.figli(radice) if "(d4)" in dialogo.albero.GetItemText(figlio))
            dialogo.attiva(d4)
            return
        wx.CallLater(30, scegli_la_foglia)

    wx.CallLater(30, scegli_la_foglia)
    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: uscite == [("automatica", 2)])
    assert finestra.dialogo_ricerca is None
    assert ricerca.posizione[1] is None
