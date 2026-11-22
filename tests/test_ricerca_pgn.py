# Orologic, prove della ricerca PGN nella finestra.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La ricerca PGN come l'ha descritta Gabriele il 21 novembre 2026 e come
l'ha voluta dopo il collaudo del 22: il file scelto con la finestra di
Windows o gli appunti, il caricamento nel filo, le statistiche, le due
schede, i filtri, l'albero delle mosse un ramo alla volta con le varianti
contate a parte, le non classificate con Classifica, i problemi con Ripara e
la copia di sicurezza, la foglia che mostra la partita, i pulsanti, Alt+1-4,
e il ritorno allo stesso punto dopo Easyfish o l'analisi. Le finestre di
Windows, la vista della partita e l'elenco delle partite sono sostituite, i
suoni e gli annunci si segnano."""

import io
import os
import pathlib
import sys

import chess
import pytest
import wx
from conftest import pompa

from orologic_modules import archivio_pgn, board_utils, finestra_ricerca, pgn_search

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

# Tre partite: la prima gioca 2. Nf3, e 2. Bc4 solo in una variante.
VARIANTI = """[Event "V"]
[White "Uno"]
[Black "Due"]
[Result "1-0"]

1. e4 e5 2. Nf3 (2. Bc4) 1-0

[Event "V"]
[White "Tre"]
[Black "Quattro"]
[Result "0-1"]

1. e4 e5 2. Bc4 0-1

[Event "V"]
[White "Cinque"]
[Black "Sei"]
[Result "1/2-1/2"]

1. e4 e5 2. Bc4 1/2-1/2
"""

# Un problema per tipo: data, Elo e risultato col matto; una mossa
# illegale; intestazioni mancanti, e la stessa partita due volte.
PROBLEMI = """[Event "A"]
[Site "?"]
[Date "2024-05-03"]
[Round "1"]
[White "Primo"]
[Black "Secondo"]
[Result "1-0"]
[WhiteElo "2400a"]

1. f3 e5 2. g4 Qh4# 1-0

[Event "B"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Terzo"]
[Black "Quarto"]
[Result "*"]

1. e4 e5 2. Ke3 Nf6 *

[Event "C"]
[White "Quinto"]
[Black "Sesto"]
[Result "1/2-1/2"]

1. d4 d5 1/2-1/2

[Event "C"]
[White "Quinto"]
[Black "Sesto"]
[Result "1/2-1/2"]

1. d4 d5 1/2-1/2
"""

# Una partita senza ECO, una con, una da una posizione di studio, una
# senza mosse.
NON_CLASSIFICATE = """[Event "N"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Senza"]
[Black "Eco"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0

[Event "N"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Con"]
[Black "Eco"]
[Result "0-1"]
[ECO "B20"]

1. e4 c5 0-1

[Event "N"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Studio"]
[Black "Finale"]
[Result "1-0"]
[SetUp "1"]
[FEN "8/8/8/8/8/5k2/6p1/4K3 b - - 0 1"]

1... g1=Q+ 1-0

[Event "N"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Senza"]
[Black "Mosse"]
[Result "*"]

*
"""


def archivio(testo=ARCHIVIO):
    caricato, righe = archivio_pgn.carica("testo", testo)
    assert caricato is not None, righe
    return caricato


def codice(uci):
    return archivio_pgn.codice(chess.Move.from_uci(uci))


def test_il_caricamento_dal_testo_e_le_righe():
    caricato, righe = archivio_pgn.carica("testo", ARCHIVIO)
    assert len(caricato) == 4
    assert righe[-1] == "Caricate 4 partite valide."
    assert caricato.giocatore_comune == "Rossi"
    riepilogo = archivio_pgn.righe_dell_archivio(caricato)
    assert riepilogo[:3] == ["Archivio PGN Caricato", "Partite totali: 4", "Statistiche Risultati"]
    assert "Vittorie Bianco: 2 (50.0%)" in riepilogo
    assert "Patte: 1 (25.0%)" in riepilogo
    assert "Rilevato giocatore principale: Rossi (presente in >=90% delle partite)." in riepilogo
    assert riepilogo[-1] == "Attenzione: l'archivio contiene solo 4 partite (minimo consigliato: 20)."
    # Niente righe vuote, e uno spazio solo fra le parole.
    assert all(riga and "  " not in riga for riga in riepilogo)
    # La partita intera si rilegge dal suo pezzo di testo.
    assert caricato.partita_intera(3).headers["White"] == "Gialli"


def test_i_caricamenti_che_non_vanno(tmp_path):
    assert archivio_pgn.carica("testo", "  ")[1] == ["Gli appunti sono vuoti."]
    assert archivio_pgn.carica("testo", "la spesa di domani")[1] == ["Il testo negli appunti non sembra contenere dati PGN validi."]
    caricato, righe = archivio_pgn.carica("file", str(tmp_path / "manca.pgn"))
    assert caricato is None
    assert righe[0].startswith("Rilevato percorso file: ") and righe[1].startswith("Errore nella lettura del file: ")
    # Fermato subito: nessuna partita.
    caricato, righe = archivio_pgn.carica("testo", ARCHIVIO, fermato=lambda: True)
    assert caricato is None and righe == ["Nessuna partita valida trovata nel PGN."]


def test_fermato_a_meta_tiene_le_partite_lette_e_il_resto_del_testo():
    lette = []

    def fermato():
        return len(lette) >= 1

    caricato, righe = archivio_pgn.carica("testo", ARCHIVIO, avanzamento=lette.append, fermato=fermato)
    assert lette == ["Partite caricate: 1..."]
    assert len(caricato) == 1
    assert righe[-2:] == ["Lettura fermata: tengo le partite lette finora.", "Caricate 1 partite valide."]
    # Il testo non letto resta nei pezzi: riscrivendo non si perde.
    assert "".join(caricato.testo[inizio:fine] for inizio, fine, _indice in caricato.pezzi) == caricato.testo


def test_lo_scaricamento_fermato(monkeypatch):
    class Risposta(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_dati):
            return False

    monkeypatch.setattr(pgn_search, "_apri_indirizzo", lambda _indirizzo: Risposta(ARCHIVIO.encode("utf-8")))
    caricato, righe = archivio_pgn.carica("url", "https://lichess.org/api/games/user/prova")
    assert len(caricato) == 4 and caricato.percorso is None
    assert righe[0] == "Rilevato URL: https://lichess.org/api/games/user/prova"
    caricato, righe = archivio_pgn.carica("url", "https://lichess.org/api/games/user/prova", fermato=lambda: True)
    assert caricato is None
    assert righe[1] == "Scaricamento interrotto dall'utente. Elaborazione delle partite caricate finora..."


def test_l_albero_un_ramo_alla_volta():
    a = archivio()
    tutte = list(range(4))
    rami, finite, finite_varianti = a.figli(tutte, a.linee_di(tutte), 0)
    assert [(mossa.uci(), partite, varianti) for mossa, partite, _coppie, varianti in rami] == [("e2e4", [0, 1, 3], []), ("d2d4", [2], [])]
    assert finite == [] and finite_varianti == []
    # La variante della quarta partita, 2... d6, ha il suo ramo, contata a parte.
    percorso = [chess.Move.from_uci(uci) for uci in ("e2e4", "e7e5", "g1f3")]
    linee = [(3, 0)]
    rami, _finite, _fv = a.figli([0, 3], linee, 3)
    assert [(mossa.uci(), partite, varianti) for mossa, partite, _coppie, varianti in rami] == [("b8c6", [0], []), ("g8f6", [3], []), ("d7d6", [], [(3, 0)])]
    board = archivio_pgn.scacchiera_del_percorso(percorso)
    d6 = archivio_pgn.voce_del_ramo(a, board, chess.Move.from_uci("d7d6"), [], [(3, 0)], 2, {})
    assert d6.endswith(" (d6): Gialli vs Rossi, 1-0, in una variante")
    # Le partite che finiscono li'.
    rami, finite, _fv = a.figli([0, 1], [], 3)
    assert finite == [1]
    radice = archivio_pgn.voce_della_radice(a, tutte, {})
    assert radice == "(radice) (4 partite) | +50% =25% -25%"
    board = chess.Board()
    e4 = archivio_pgn.voce_del_ramo(a, board, chess.Move.from_uci("e2e4"), [0, 1, 3], [], 4, {})
    assert e4.endswith(" (e4) (3 partite) = 75.0% | +67% =0% -33%")
    assert e4.startswith(board_utils.DescribeMove(chess.Move.from_uci("e2e4"), board))
    d4 = archivio_pgn.voce_del_ramo(a, board, chess.Move.from_uci("d2d4"), [2], [], 4, {})
    assert d4.endswith(" (d4): Rossi vs Neri, 1/2-1/2")
    # Col filtro del giocatore le statistiche sono le sue.
    assert archivio_pgn.voce_della_radice(a, [0, 1, 3], {"player": "verdi"}) == "(radice) (3 partite) | +0% =0% -33%"
    mosse = tuple(archivio_pgn.mossa(numero) for numero in a.schede[0].mosse)
    assert archivio_pgn.sequenza_del_percorso(mosse) == "1. e4 e5 2. Nf3 Nc6"
    assert archivio_pgn.sequenza_del_percorso(()) == "(radice)"
    assert a.voce_della_lista(board, 0, 0, 1) == "Rossi vs Bianchi (1): 1-0, 1. e4 e5 2. Nf3 Nc6"
    dopo = archivio_pgn.scacchiera_del_percorso(mosse[:1])
    assert a.voce_della_lista(dopo, 1, 1, 2) == "Verdi vs Rossi (2): 0-1, 1... c5 2. Nf3"


def test_le_varianti_contate_a_parte():
    a = archivio(VARIANTI)
    tutte = list(range(3))
    percorso = (chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5"))
    rami, _finite, _fv = a.figli(tutte, a.linee_di(tutte), 2)
    assert [(mossa.uci(), partite, varianti) for mossa, partite, _coppie, varianti in rami] == [("f1c4", [1, 2], [(0, 0)]), ("g1f3", [0], [])]
    board = archivio_pgn.scacchiera_del_percorso(percorso)
    bc4 = archivio_pgn.voce_del_ramo(a, board, chess.Move.from_uci("f1c4"), [1, 2], [(0, 0)], 3, {})
    # Statistiche e percentuale delle sole due partite giocate.
    assert bc4.endswith(" (Bc4) (2 partite, piu' 1 dalle varianti) = 66.7% | B:0% P:50% N:50%")
    assert a.voce_della_lista(board, 0, 2, 3, 0) == "Uno vs Due (3): 1-0, variante, 2. Bc4"


def test_la_lettura_tiene_tutto_il_testo_e_la_codifica(tmp_path):
    dati = ("[Event \"C\"]\r\n[White \"Müller\"]\r\n[Black \"Rossi\"]\r\n[Result \"1-0\"]\r\n\r\n1. e4 1-0\r\n\r\n"
            "[Event \"C\"]\r\n[White \"Bianchi\"]\r\n[Black \"Rossi\"]\r\n[Result \"0-1\"]\r\n\r\n1. d4 0-1\r\n").encode("cp1252")
    testo, cattive, a_capo, bom = archivio_pgn.decodifica(dati)
    assert "Müller" in testo and "\r" not in testo and a_capo == "\r\n" and not bom
    assert cattive == [testo.index('[White "M')]
    file = tmp_path / "cp1252.pgn"
    file.write_bytes(dati)
    caricato, _righe = archivio_pgn.carica("file", str(file))
    assert caricato.info[0]["White"] == "Müller"
    assert caricato.schede[0].problemi == {"intestazioni": ("Site", "Date", "Round"), "codifica": True}
    assert caricato.schede[1].problemi == {"intestazioni": ("Site", "Date", "Round")}
    # Senza cambi il testo riscritto e' quello di prima.
    assert archivio_pgn.riscritto(caricato, {}).testo == caricato.testo


def test_le_modifiche_al_testo_delle_partite():
    partita = '[Event "A"]\n[White "B"]\n\n1. e4 e5 1-0\n\n'
    assert archivio_pgn.metti_le_intestazioni(partita, {"White": 'Lo "zio"', "Site": "?"}) == '[Event "A"]\n[White "Lo \\"zio\\""]\n[Site "?"]\n\n1. e4 e5 1-0\n\n'
    assert archivio_pgn.metti_le_intestazioni("\n1. e4 *\n\n", {"Event": "?"}) == '\n[Event "?"]\n\n1. e4 *\n\n'
    assert archivio_pgn.metti_il_segno(partita, "0-1") == '[Event "A"]\n[White "B"]\n\n1. e4 e5 0-1\n\n'
    assert archivio_pgn.metti_il_segno('[Event "A"]\n\n1. e4 {fine}\n', "*") == '[Event "A"]\n\n1. e4 {fine} *\n'
    assert archivio_pgn.data_riscritta("2024-05-03") == "2024.05.03"
    assert archivio_pgn.data_riscritta("2024/5/3") == "2024.05.03"
    assert archivio_pgn.data_riscritta("2024") == "2024.??.??"
    assert archivio_pgn.data_riscritta("03.05.2024") is None


def test_i_problemi_e_la_riparazione(tmp_path, monkeypatch):
    monkeypatch.setattr(archivio_pgn.config, "percorso_salvataggio", lambda nome: str(tmp_path / nome))
    file = tmp_path / "problemi.pgn"
    file.write_bytes(PROBLEMI.encode("utf-8"))
    a, _righe = archivio_pgn.carica("file", str(file))
    assert a.schede[0].problemi == {"risultato": ("posizione", "0-1"), "data": "2024-05-03", "elo": "WhiteElo 2400a"}
    assert a.schede[1].problemi == {"mosse": "2. Ke3"}
    assert a.schede[2].problemi == {"intestazioni": ("Site", "Date", "Round")}
    assert not a.doppioni_cercati
    archivio_pgn.segna_i_doppioni(a, archivio_pgn.cerca_i_doppioni(a))
    assert a.schede[3].problemi["doppioni"] == 2 and a.doppioni_cercati
    trovati = a.problemi(range(4))
    assert {tipo: indici for tipo, indici in trovati.items()} == {
        "risultato": [0], "data": [0], "elo": [0], "mosse": [1], "intestazioni": [2, 3], "doppioni": [3]}
    assert archivio_pgn.voce_del_problema(a, 1, "mosse") == "Terzo vs Quarto, *: 2. Ke3"
    assert archivio_pgn.voce_del_problema(a, 0, "risultato") == "Primo vs Secondo, 1-0: la posizione dice 0-1"
    assert archivio_pgn.voce_del_problema(a, 3, "doppioni") == "Quinto vs Sesto, 1/2-1/2: uguale alla partita 3"
    tipi = {tipo for tipo, _nome in archivio_pgn.tipi_dei_problemi()}
    cambi, tolte, conti = archivio_pgn.ripara(a, a.con_problemi(range(4)), tipi)
    assert tolte == {3} and set(cambi) == {0, 2}
    assert archivio_pgn.righe_della_riparazione(conti) == [
        "Intestazioni aggiunte: 1 partite.", "Risultati corretti: 1.", "Date riscritte: 1.", "Doppioni tolti: 1.",
        "Mosse illegali, da sistemare a mano: 1 partite.", "Elo non numerici, da sistemare a mano: 1 partite."]
    nuovo, righe = archivio_pgn.applica_le_modifiche(a, cambi, tolte)
    copia = righe[0].removeprefix("Copia di sicurezza: ")
    assert os.path.dirname(copia) == str(tmp_path / "pgn") and pathlib.Path(copia).read_bytes() == PROBLEMI.encode("utf-8")
    assert righe[1] == "File riscritto: " + str(file)
    scritto = file.read_text(encoding="utf-8")
    assert scritto.count('[Event "C"]') == 1
    assert '[Date "2024.05.03"]' in scritto and '[Result "0-1"]' in scritto and "Qh4# 0-1" in scritto
    assert '[Result "1/2-1/2"]\n[Site "?"]\n[Date "????.??.??"]\n[Round "?"]\n\n1. d4 d5' in scritto
    # La partita con la mossa illegale resta com'era, con le mosse dopo l'errore.
    assert "1. e4 e5 2. Ke3 Nf6 *" in scritto
    assert len(nuovo) == 3
    assert [scheda.problemi for scheda in nuovo.schede] == [{"elo": "WhiteElo 2400a"}, {"mosse": "2. Ke3"}, None]


def test_le_non_classificate_e_classifica(tmp_path, monkeypatch):
    monkeypatch.setattr(archivio_pgn.config, "percorso_salvataggio", lambda nome: str(tmp_path / nome))
    file = tmp_path / "aperture.pgn"
    file.write_bytes(NON_CLASSIFICATE.encode("utf-8"))
    a, _righe = archivio_pgn.carica("file", str(file))
    assert len(a) == 4
    assert a.non_classificate(range(4)) == ([3], [2], [0])
    assert [a.nell_albero(indice) for indice in range(4)] == [True, True, False, False]
    cambi = archivio_pgn.classifica(a, [0], archivio_pgn.carica_le_aperture())
    assert set(cambi) == {0} and '[ECO "C' in cambi[0] and '[Opening "' in cambi[0]
    nuovo, _righe = archivio_pgn.applica_le_modifiche(a, cambi)
    assert nuovo.info[0]["ECO"].startswith("C")
    assert nuovo.non_classificate(range(4)) == ([3], [2], [])
    assert '[ECO "C' in file.read_text(encoding="utf-8")


def test_i_filtri_nuovi():
    a = archivio(PROBLEMI + "\n" + VARIANTI)
    # La seconda si ferma alla mossa illegale: una mossa sola.
    assert [info["Mosse"] for info in a.info] == [2, 1, 1, 1, 2, 2, 2]
    assert pgn_search.applica_filtri(a.info, {"matto": True}) == [0]
    assert pgn_search.applica_filtri(a.info, {"result": "*"}) == [1]
    assert pgn_search.applica_filtri(a.info, {"mosse_min": 2}) == [0, 4, 5, 6]
    assert pgn_search.applica_filtri(a.info, {"mosse_max": 2}) == [1, 2, 3]
    promozione = archivio(NON_CLASSIFICATE)
    assert pgn_search.applica_filtri(promozione.info, {"promozione": True}) == [2]


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
        self.dialogo._popola(voce)
        return [self.dialogo.albero.GetItemText(figlio) for figlio in self.dialogo.figli(voce)]

    def invio(self, oggetto):
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.SetKeyCode(wx.WXK_RETURN)
        evento.SetEventObject(oggetto)
        self.dialogo._tasto(evento)

    def alt(self, cifra):
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.SetKeyCode(ord(str(cifra)))
        evento.SetAltDown(True)
        evento.SetEventObject(self.dialogo.albero)
        self.dialogo._tasto(evento)

    def finiti_i_doppioni(self):
        return pompa(lambda: self.dialogo.ricerca.archivio is not None and self.dialogo.ricerca.archivio.doppioni_cercati)


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
        aperta.dialogo._chiudi()
        for filo in (aperta.dialogo.filo, aperta.dialogo.filo_doppioni):
            if filo is not None:
                filo.join(timeout=5)
        pompa(lambda: False, 0.05)
        aperta.dialogo.Destroy()
        pompa(lambda: False, 0.05)


@pytest.fixture
def file_pgn(tmp_path):
    percorso = tmp_path / "prova.pgn"
    percorso.write_text(ARCHIVIO, encoding="utf-8")
    return str(percorso)


def test_si_apre_sul_file_e_lo_carica_nel_filo(prova, file_pgn):
    p = prova(archivio_pgn.Ricerca(), file_pgn)
    d = p.dialogo
    assert pompa(lambda: d.ricerca.archivio is not None and not d.in_corso())
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
    assert p.finiti_i_doppioni()
    testi = p.testi(radice)
    assert len(testi) == 4 and "(e4) (3 partite)" in testi[0] and testi[1].endswith("(d4): Rossi vs Neri, 1/2-1/2")
    # Nessuna ha il codice ECO, e a tutte mancano delle intestazioni.
    assert testi[2:] == ["Non classificate (4 partite)", "Problemi (4 partite)"]
    assert pompa(lambda: wx.Window.FindFocus() is d.albero)
    assert d.schede.GetPageText(0) == "Partite" and d.schede.GetPageText(1) == "Filtri"


def test_annullato_il_file_resta_aperta_vuota(prova):
    p = prova(archivio_pgn.Ricerca())
    d = p.dialogo
    pompa(lambda: False, 0.2)
    assert d.ricerca.archivio is None
    assert d.riepilogo.GetValue() == "Nessun archivio caricato."
    d.inizio()
    d.percorso()
    d.applica()
    d.classifica()
    d.ripara()
    assert p.suoni == ["no"] * 5


def test_dagli_appunti(prova, monkeypatch):
    p = prova(archivio_pgn.Ricerca())
    d = p.dialogo
    monkeypatch.setattr(finestra_ricerca.pyperclip, "paste", lambda: "")
    d.dagli_appunti()
    assert p.avvisi == ["Gli appunti sono vuoti."]
    monkeypatch.setattr(finestra_ricerca.pyperclip, "paste", lambda: ARCHIVIO)
    d.dagli_appunti()
    assert pompa(lambda: d.ricerca.archivio is not None and not d.in_corso())
    assert len(d.ricerca.archivio) == 4


def test_un_caricamento_che_non_va_avvisa(prova, tmp_path):
    p = prova(archivio_pgn.Ricerca(), str(tmp_path / "manca.pgn"))
    d = p.dialogo
    assert pompa(lambda: p.avvisi)
    assert p.avvisi[0].split("\n")[1].startswith("Errore nella lettura del file: ")
    assert p.suoni == ["no"] and d.ricerca.archivio is None


def test_invio_apre_i_rami_e_mostra_la_partita(prova):
    ricerca = archivio_pgn.Ricerca()
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
    # La variante 2... d6 ha la sua foglia.
    assert p.testi(p.voce("(e4)", "(e5)", "(Nf3)"))[2].endswith("(d6): Gialli vs Rossi, 1-0, in una variante")
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
    assert ricerca.posizione == (codice("e2e4"), codice("e7e5"), codice("g1f3"), codice("b8c6"))
    assert not d.IsShown() and d.GetReturnCode() == wx.ID_OK
    # Riaperta, torna sulla stessa foglia.
    di_nuovo = prova(ricerca).dialogo
    selezionata = di_nuovo.albero.GetSelection()
    assert di_nuovo.albero.GetItemData(selezionata).partita == 0
    assert "(Nc6): Rossi vs Bianchi, 1-0" in di_nuovo.albero.GetItemText(selezionata)


def test_i_filtri(prova):
    ricerca = archivio_pgn.Ricerca()
    ricerca.archivio = archivio()
    p = prova(ricerca)
    d = p.dialogo
    nomi = [d.campi[chiave].GetName() for chiave, _domanda, _tipo in finestra_ricerca.domande_dei_filtri()]
    assert nomi[:2] == ["Nome giocatore Bianco (vuoto=qualsiasi)", "Nome giocatore Nero (vuoto=qualsiasi)"]
    assert nomi[3] == "Scegli risultato"
    assert nomi[10:] == ["Con almeno queste mosse (0=nessun limite)", "Con meno di queste mosse (0=nessun limite)", "Terminata con il matto", "Con promozione"]
    assert d.campi["result"].GetString(4) == "Non specificato (*)"
    assert all(campo.GetParent() is d.pagina_filtri for campo in d.campi.values())
    d.campi["event"].ChangeValue("prova")
    d.campi["result"].SetSelection(1)
    p.invio(d.campi["event"])
    assert ricerca.filtri == {"event": "prova", "result": "1-0"}
    assert d.etichetta_dell_albero.GetLabel() == "Partite corrispondenti: 2 di 4 (50.00%)"
    assert p.detti[-1] == "Partite corrispondenti: 2 di 4 (50.00%)"
    d.campi["eco"].ChangeValue("b90")
    d.campi["elo_min"].SetValue(2000)
    d.campi["matto"].SetValue(True)
    assert d.filtri_dei_campi() == {"event": "prova", "result": "1-0", "eco": "B90", "elo_min": 2000, "matto": True}
    d.azzera()
    assert ricerca.filtri == {} and d.campi["event"].GetValue() == "" and d.campi["result"].GetSelection() == 0
    assert not d.campi["matto"].GetValue()
    assert p.detti[-1] == "Tutti i filtri sono stati rimossi (azzerati). Partite corrispondenti: 4 di 4 (100.00%)"
    # Riaperta, i campi tengono i filtri dello stato.
    ricerca.filtri = {"white": "Rossi", "promozione": True}
    di_nuovo = prova(ricerca).dialogo
    assert di_nuovo.campi["white"].GetValue() == "Rossi" and di_nuovo.campi["promozione"].GetValue()
    assert di_nuovo.etichetta_dell_albero.GetLabel() == "Partite corrispondenti: 0 di 4 (0.00%)"


def test_alt_e_una_cifra_portano_alle_sezioni(prova):
    ricerca = archivio_pgn.Ricerca()
    ricerca.archivio = archivio()
    p = prova(ricerca)
    d = p.dialogo
    p.alt(4)
    assert d.schede.GetSelection() == 1
    assert pompa(lambda: wx.Window.FindFocus() is d.campi["white"])
    p.alt(1)
    assert d.schede.GetSelection() == 0
    assert pompa(lambda: wx.Window.FindFocus() is d.riepilogo)
    p.alt(3)
    assert pompa(lambda: wx.Window.FindFocus() is d.pulsante_inizio)
    p.alt(2)
    assert pompa(lambda: wx.Window.FindFocus() is d.albero)


def test_i_pulsanti(prova, tmp_path):
    ricerca = archivio_pgn.Ricerca()
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
    # Salva il PGN: le partite della voce, com'erano.
    p.salva_in = str(tmp_path / "ramo")
    d.salva()
    with open(p.salva_in + ".pgn", encoding="utf-8") as file:
        salvato = file.read()
    assert salvato.count("[Event ") == 2 and "{Una variante} (2... d6)" in salvato
    assert p.detti[-1] == "Salvate 2 partite in: " + p.salva_in + ".pgn"
    assert p.domande == []
    # Dalla radice senza filtri si chiede prima.
    d.inizio()
    assert d.albero.GetSelection() == d.albero.GetRootItem()
    p.risposta = False
    d.salva()
    assert p.domande == ["Attenzione: non ci sono filtri attivi. Il file salvato sarebbe una copia dell'archivio originale. Salvo lo stesso?"]
    # Classifica e Ripara fuori dai loro rami suonano il no.
    d.classifica()
    d.ripara()
    assert p.suoni == ["no", "no"]


def test_le_varianti_nella_finestra(prova):
    ricerca = archivio_pgn.Ricerca()
    ricerca.archivio = archivio(VARIANTI)
    p = prova(ricerca)
    d = p.dialogo
    bc4 = p.voce("(e4)", "(e5)", "(Bc4)")
    assert "(2 partite, piu' 1 dalle varianti)" in d.albero.GetItemText(bc4)
    d.albero.SelectItem(bc4)
    p.risposte_della_lista = [None]
    d.partite_del_ramo()
    assert p.scelte[0][1] == ["Tre vs Quattro (1): 0-1", "Cinque vs Sei (2): 1/2-1/2", "Uno vs Due (3): 1-0, variante"]


def test_problemi_e_ripara_nella_finestra(prova, tmp_path, monkeypatch):
    monkeypatch.setattr(archivio_pgn.config, "percorso_salvataggio", lambda nome: str(tmp_path / nome))
    file = tmp_path / "problemi.pgn"
    file.write_bytes(PROBLEMI.encode("utf-8"))
    p = prova(archivio_pgn.Ricerca(), str(file))
    d = p.dialogo
    assert pompa(lambda: d.ricerca.archivio is not None and not d.in_corso())
    assert p.finiti_i_doppioni()
    problemi = p.voce("Problemi")
    assert d.albero.GetItemText(problemi) == "Problemi (4 partite)"
    assert p.testi(problemi) == [
        "Mosse illegali o illeggibili (1 partite)", "Intestazioni obbligatorie mancanti (2 partite)", "Risultato che non torna (1 partite)",
        "Date malformate (1 partite)", "Elo non numerici (1 partite)", "Partite doppie (1 partite)"]
    data = p.voce("Problemi", "Date malformate", "Primo")
    assert d.albero.GetItemText(data) == "Primo vs Secondo, 1-0: 2024-05-03"
    # Da un tipo, solo quel tipo.
    d.albero.SelectItem(data)
    d.ripara()
    assert pompa(lambda: not d.in_corso() and p.avvisi)
    assert p.avvisi[-1].split("\n")[0] == "Date riscritte: 1."
    assert '[Date "2024.05.03"]' in file.read_text(encoding="utf-8")
    assert p.finiti_i_doppioni()
    # Dal ramo Problemi, tutti: restano Elo e la mossa illegale.
    d.albero.SelectItem(p.voce("Problemi"))
    d.ripara()
    assert pompa(lambda: not d.in_corso() and len(p.avvisi) == 2)
    assert p.avvisi[-1].split("\n")[:3] == ["Intestazioni aggiunte: 1 partite.", "Risultati corretti: 1.", "Doppioni tolti: 1."]
    assert p.finiti_i_doppioni()
    assert p.testi(p.voce("Problemi")) == ["Mosse illegali o illeggibili (1 partite)", "Elo non numerici (1 partite)"]
    assert len(os.listdir(tmp_path / "pgn")) == 2


def test_classifica_nella_finestra(prova, tmp_path, monkeypatch):
    monkeypatch.setattr(archivio_pgn.config, "percorso_salvataggio", lambda nome: str(tmp_path / nome))
    file = tmp_path / "aperture.pgn"
    file.write_bytes(NON_CLASSIFICATE.encode("utf-8"))
    p = prova(archivio_pgn.Ricerca(), str(file))
    d = p.dialogo
    assert pompa(lambda: d.ricerca.archivio is not None and not d.in_corso())
    radice = d.albero.GetRootItem()
    assert [testo.split(" (")[0] for testo in p.testi(radice)][-2:] == ["Non classificate", "Problemi"]
    fuori = p.voce("Non classificate")
    assert p.testi(fuori) == ["Senza mosse (1 partite)", "Da una posizione di studio (1 partite)", "Senza codice ECO (1 partite)"]
    assert p.testi(p.voce("Non classificate", "Da una posizione")) == ["Studio vs Finale, 1-0"]
    assert "(e4)" in p.testi(p.voce("Non classificate", "Senza codice ECO"))[0]
    d.albero.SelectItem(fuori)
    d.classifica()
    assert pompa(lambda: not d.in_corso() and p.avvisi)
    assert p.avvisi[-1].split("\n")[:2] == ["Classificate 1 partite su 1.", "Le partite senza mosse o da una posizione di studio non si classificano."]
    assert p.testi(p.voce("Non classificate")) == ["Senza mosse (1 partite)", "Da una posizione di studio (1 partite)"]
    # Di nuovo: nessuna da classificare.
    d.albero.SelectItem(p.voce("Non classificate"))
    d.classifica()
    assert p.detti[-1] == "Nessuna partita da classificare." and p.suoni == ["no"]


def test_esc_ferma_il_caricamento(prova):
    """Esc durante il caricamento lo ferma, e la finestra resta aperta;
    fuori dal caricamento Chiudi chiude senza uscita."""
    p = prova(archivio_pgn.Ricerca())
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
    game = archivio().partita_intera(0)
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

    ricerca = archivio_pgn.Ricerca()
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
            dialogo.albero.SelectItem(d4)
            dialogo.attiva(d4)
            return
        wx.CallLater(30, scegli_la_foglia)

    wx.CallLater(30, scegli_la_foglia)
    finestra.avvia_il_nucleo(nucleo)
    assert pompa(lambda: uscite == [("automatica", 2)])
    assert finestra.dialogo_ricerca is None
    assert ricerca.posizione == (codice("d2d4"),)
