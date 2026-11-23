# Orologic, prove dell'Analisi Automatica (OAA).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le correzioni dell'OAA del 23 novembre 2026, dopo la revisione chiesta da
Gabriele: la mossa giocata si valuta dalla stessa posizione delle
alternative, con root_moves se non e' fra le linee; il matto si conta dopo
la mossa e dice chi lo da'; una linea di matto a fine partita va nel
commento e non allunga la partita; la Mossa Geniale vuole un sacrificio; la
teoria non entra nella precisione; il marcatore [OAA] si riconosce anche
alla francese. Il motore e' finto, con un copione."""

import io

import chess
import chess.engine
import chess.pgn
import pytest

from orologic_modules import engine

# Lo spazio indivisibile del francese.
NB = chr(0xA0)

PARTITA = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 1-0"


def _cp(valore, colore):
    return chess.engine.PovScore(chess.engine.Cp(valore), colore)


def _matto(mosse, colore):
    return chess.engine.PovScore(chess.engine.Mate(mosse), colore)


class MotoreFinto:
    """La mossa della partita e' la migliore, a zero, o col punteggio del
    copione; le altre perdono dieci centesimi. Nelle posizioni assenti la
    mossa giocata non e' fra le linee, e la si chiede con root_moves."""

    def __init__(self, partita, copione=None, assenti=()):
        self.giocate = {nodo.parent.board().fen(): nodo.move for nodo in partita.mainline()}
        self.copione = copione or {}
        self.assenti = set(assenti)
        self.chiamate = []
        self.id = {"name": "Finto", "author": "Prove"}

    @staticmethod
    def _linea(board, mossa, punteggio):
        seguito = [mossa]
        prova = board.copy()
        prova.push(mossa)
        for _giro in range(3):
            legali = sorted(prova.legal_moves, key=lambda m: m.uci())
            if not legali:
                break
            seguito.append(legali[0])
            prova.push(legali[0])
        return {"score": punteggio, "pv": seguito}

    def analyse(self, board, limit, multipv=None, root_moves=None):
        fen = board.fen()
        giocata = self.giocate.get(fen)
        punteggio = self.copione.get(fen, _cp(0, board.turn))
        if root_moves:
            self.chiamate.append(root_moves[0])
            return self._linea(board, root_moves[0], punteggio)
        altre = [mossa for mossa in sorted(board.legal_moves, key=lambda m: m.uci()) if mossa != giocata]
        linee = []
        if fen in self.assenti:
            linee.append(self._linea(board, altre.pop(0), _cp(0, board.turn)))
        elif giocata is not None:
            linee.append(self._linea(board, giocata, punteggio))
        for mossa in altre[: multipv - len(linee)]:
            linee.append(self._linea(board, mossa, _cp(-10, board.turn)))
        return linee


def _analizza(monkeypatch, tmp_path, partita, motore, saltate=2):
    catturati = {}
    # Il PGN analizzato in una cartella sua: in quella comune delle prove
    # lo troverebbe la prova della pulizia.
    monkeypatch.setattr(engine, "percorso_salvataggio", lambda relativo: str(tmp_path / relativo))
    monkeypatch.setattr(engine, "ENGINE", motore)
    monkeypatch.setattr(engine, "key", lambda *_a, **_k: "")
    monkeypatch.setattr(engine, "Acusticator", lambda *_a, **_k: None)
    monkeypatch.setattr(engine, "_parametri_analisi_automatica", lambda *_a: (1, chess.engine.Limit(depth=1), 0, saltate, None))
    monkeypatch.setattr(engine, "genera_sommario_analitico_txt", lambda *argomenti: catturati.update(accuracies=argomenti[10], risultati=argomenti[2]))
    engine.AnalisiAutomatica(partita)
    return catturati


def _posizione_prima_dell_ultima(partita):
    return partita.end().parent.board().fen()


def test_la_linea_di_matto_a_fine_partita_va_nel_commento(monkeypatch, tmp_path):
    partita = chess.pgn.read_game(io.StringIO(PARTITA))
    copione = {_posizione_prima_dell_ultima(partita): _matto(2, chess.WHITE)}
    catturati = _analizza(monkeypatch, tmp_path, partita, MotoreFinto(partita, copione))
    assert list((tmp_path / "pgn").glob("*_auto_*.pgn"))
    # La partita resta di sette semimosse: prima la linea diventava principale.
    assert len(list(partita.mainline_moves())) == 7
    commento = partita.end().comment
    assert "Il Bianco dà matto in 1" in commento
    assert "[OAA: Linea: " in commento
    # La teoria fuori dalla precisione: tre mosse del Bianco, due del Nero,
    # tutte le migliori, al 100%.
    # La formula di Lichess da' 99,9999 a una mossa perfetta.
    assert {lato: len(valori) for lato, valori in catturati["accuracies"].items()} == {"w": 3, "b": 2}
    assert all(valore == pytest.approx(100, abs=0.001) for valori in catturati["accuracies"].values() for valore in valori)


def test_la_mossa_giocata_fuori_dalle_linee_si_chiede_con_root_moves(monkeypatch, tmp_path):
    partita = chess.pgn.read_game(io.StringIO(PARTITA))
    prima_di_bc4 = partita.variations[0].variations[0].variations[0].variations[0].board().fen()
    motore = MotoreFinto(partita, {prima_di_bc4: _cp(-300, chess.WHITE)}, assenti=[prima_di_bc4])
    _analizza(monkeypatch, tmp_path, partita, motore)
    alfiere = partita.variations[0].variations[0].variations[0].variations[0].variations[0]
    assert alfiere.san() == "Bc4"
    assert motore.chiamate == [alfiere.move]
    assert "Perdita: +3.00" in alfiere.comment
    # Le alternative accanto alla mossa sbagliata.
    assert len(alfiere.parent.variations) == 2


def test_il_matto_si_conta_dopo_la_mossa_e_dice_chi_lo_da():
    assert engine._matto_dopo(_matto(3, chess.WHITE), chess.WHITE) == "il Bianco dà matto in 2"
    assert engine._matto_dopo(_matto(1, chess.WHITE), chess.WHITE) == "scacco matto"
    # Chi muove subisce il matto: il conto dell'avversario non cambia.
    assert engine._matto_dopo(_matto(-2, chess.WHITE), chess.WHITE) == "il Nero dà matto in 2"
    assert engine._matto_dopo(_matto(2, chess.BLACK), chess.BLACK) == "il Nero dà matto in 1"
    assert engine._matto_dopo(_cp(150, chess.WHITE), chess.WHITE) is None


def _nodo(fen, san):
    partita = chess.pgn.Game()
    partita.setup(chess.Board(fen))
    return partita.add_variation(partita.board().parse_san(san))


GRECO = "r1bq1rk1/pppn1ppp/4p3/3pP3/1b1P4/2NB1N2/PPP2PPP/R1BQK2R w KQ - 0 8"
RIPRESA = "rnbqkb1r/pppp1ppp/5B2/4p3/4P3/8/PPPP1PPP/RN1QKBNR b KQkq - 0 3"


def test_il_sacrificio_e_la_ripresa():
    assert engine._e_un_sacrificio(chess.Board(GRECO), chess.Board(GRECO).parse_san("Bxh7+"))
    assert not engine._e_un_sacrificio(chess.Board(RIPRESA), chess.Board(RIPRESA).parse_san("gxf6"))
    # Sotto scacco si risponde per forza.
    scacco = chess.Board("4k3/8/8/8/8/8/4q3/4K3 w - - 0 1")
    assert not engine._e_un_sacrificio(scacco, scacco.parse_san("Kxe2"))


def _giudica(nodo, migliore, seconda, giocata=None):
    turno = nodo.parent.board().turn
    linee = [{"move": nodo.move if giocata is None else seconda[1], "score": migliore}, {"move": seconda[1], "score": seconda[0]}]
    if giocata is not None:
        linee[0]["move"] = chess.Move.null()
    return engine._classifica_mossa(nodo, linee, linee[0], giocata or migliore, turno, engine.storage.DEFAULT_DB["analysis_thresholds"])[0]


def test_la_mossa_geniale_vuole_un_sacrificio():
    greco = _nodo(GRECO, "Bxh7+")
    altra = chess.Board(GRECO).parse_san("a3")
    assert _giudica(greco, _cp(300, chess.WHITE), (_cp(0, chess.WHITE), altra)) == "Mossa Geniale"
    ripresa = _nodo(RIPRESA, "gxf6")
    altra = chess.Board(RIPRESA).parse_san("Qxf6")
    assert _giudica(ripresa, _cp(0, chess.BLACK), (_cp(-300, chess.BLACK), altra)) == "Mossa Buona"


def test_un_matto_piu_lento_di_una_mossa_e_un_inesattezza():
    nodo = _nodo(GRECO, "a3")
    altra = chess.Board(GRECO).parse_san("h3")
    assert _giudica(nodo, _matto(3, chess.WHITE), (_cp(0, chess.WHITE), altra), giocata=_matto(4, chess.WHITE)) == "Inesattezza"
    assert _giudica(nodo, _matto(3, chess.WHITE), (_cp(0, chess.WHITE), altra), giocata=_matto(3, chess.WHITE)) == "Mossa Buona"


def test_il_marcatore_oaa_alla_francese_nel_riepilogo():
    partita = chess.pgn.read_game(io.StringIO("1. e4 e5 *"))
    alternativa = partita.variations[0].parent.add_variation(chess.Move.from_uci("d2d4"))
    alternativa.comment = f"[OAA{NB}: Alt{NB}: +0.30]"
    partita.variations[0].comment = f"Bella [OAA{NB}: Mossa buona. Perte{NB}: +0.00]"
    righe = []
    engine._stampa_albero_pgn(partita, {}, righe, "Bianco", "Nero", 1, {})
    testo = "\n".join(righe)
    assert f"[Alt{NB}: +0.30]" in testo
    assert "Note: Bella" in testo
    assert "Perte" not in testo


# Le scelte di Gabriele del 23 novembre 2026: la precisione come Lichess,
# l'Elo come intervallo, il giudizio dal calo della probabilita', le
# alternative dal lato del Bianco, la confutazione, le statistiche nuove.


def test_le_formule_di_lichess():
    assert engine.calculate_move_accuracy(0.5, 0.5) == 100.0
    assert engine.calculate_move_accuracy(0.4, 0.5) == 100.0
    assert engine.calculate_move_accuracy(0.5, 0.4) == pytest.approx(64.58, abs=0.01)
    assert engine.percentuale_di_vittoria(_cp(0, chess.WHITE)) == 50
    # Il matto vale mille centesimi, e oltre mille non si va.
    assert engine.percentuale_di_vittoria(_matto(3, chess.WHITE)) == pytest.approx(97.54, abs=0.01)
    assert engine.percentuale_di_vittoria(_cp(2500, chess.WHITE)) == engine.percentuale_di_vittoria(_cp(1000, chess.WHITE))
    assert engine.percentuale_di_vittoria(_cp(300, chess.BLACK)) == pytest.approx(100 - engine.percentuale_di_vittoria(_cp(300, chess.WHITE)))


def test_la_precisione_della_partita_come_lichess():
    perfette = [{"colore": colore, "vittoria_prima": 50.0, "vittoria_dopo": 50.0, "precisione": 100.0} for colore in [chess.WHITE, chess.BLACK] * 10]
    assert engine.precisione_della_partita(perfette) == {chess.WHITE: 100.0, chess.BLACK: 100.0}
    # Una mossa a zero azzera la media armonica, come in Lichess: resta la pesata a meta'.
    con_zero = [dict(mossa) for mossa in perfette]
    con_zero[0]["precisione"] = 0.0
    risultato = engine.precisione_della_partita(con_zero)
    assert risultato[chess.BLACK] == 100.0
    assert risultato[chess.WHITE] == pytest.approx(45.0)
    assert engine.precisione_della_partita([]) == {chess.WHITE: None, chess.BLACK: None}


def test_l_elo_stimato_e_un_intervallo():
    assert engine.intervallo_elo(85) == (1450, 2010)
    basso, alto = engine.intervallo_elo(99)
    assert basso < alto == round(engine.estimate_elo_poly(100), -1)


def test_il_giudizio_guarda_il_calo_della_probabilita():
    nodo = _nodo(GRECO, "a3")
    altra = chess.Board(GRECO).parse_san("h3")

    def giudizio(migliore, giocata):
        return _giudica(nodo, migliore, (_cp(-2000, chess.WHITE), altra), giocata=giocata)

    # Da +12 a +8 la partita resta vinta: prima erano 400 centesimi, uno svarione.
    assert giudizio(_cp(1200, chess.WHITE), _cp(800, chess.WHITE)) == "Mossa Normale"
    assert giudizio(_cp(0, chess.WHITE), _cp(-60, chess.WHITE)) == "Inesattezza"
    assert giudizio(_cp(0, chess.WHITE), _cp(-300, chess.WHITE)) == "Svarione"
    # Il matto lasciato andare, come Lichess, secondo quanto si resta sopra.
    assert giudizio(_matto(3, chess.WHITE), _cp(1200, chess.WHITE)) == "Inesattezza"
    assert giudizio(_matto(3, chess.WHITE), _cp(800, chess.WHITE)) == "Errore"
    assert giudizio(_matto(3, chess.WHITE), _cp(300, chess.WHITE)) == "Svarione"
    # Il matto che si subisce, secondo quanto si era gia' sotto.
    assert giudizio(_cp(-800, chess.WHITE), _matto(-3, chess.WHITE)) == "Errore"
    assert giudizio(_cp(0, chess.WHITE), _matto(-3, chess.WHITE)) == "Svarione"


def test_le_fasi_della_partita():
    assert engine.fase_della_posizione(chess.Board()) == "apertura"
    assert engine.fase_della_posizione(chess.Board("4k3/8/8/8/8/8/4P3/R3K2R w - - 0 40")) == "finale"
    sedicesima = chess.Board()
    sedicesima.fullmove_number = 16
    assert engine.fase_della_posizione(sedicesima) == "mediogioco"


OROLOGI = (
    '[White "Gabry"]\n[Black "Nero"]\n[TimeControl "60+0"]\n[Result "1-0"]\n\n'
    "1. e4 { [%clk 0:00:58] } e5 { [%clk 0:00:55] } 2. Nf3 { [%clk 0:00:50] } Nc6 { [%clk 0:00:40] } "
    "3. Bc4 { [%clk 0:00:45] } Nf6 { [%clk 0:00:30] } 4. Ng5 { [%clk 0:00:44] } 1-0\n"
)


def test_i_tempi_dagli_orologi():
    partita = chess.pgn.read_game(io.StringIO(OROLOGI))
    tempi = {_mossa.san(): secondi for _mossa, secondi in engine._tempi_delle_mosse(partita).items()}
    assert tempi == {"e4": 2, "e5": 5, "Nf3": 8, "Nc6": 15, "Bc4": 5, "Nf6": 10, "Ng5": 1}


def test_il_riepilogo_ha_le_statistiche_nuove_e_la_confutazione(monkeypatch, tmp_path):
    partita = chess.pgn.read_game(io.StringIO(OROLOGI))
    prima_di_bc4 = partita.variations[0].variations[0].variations[0].variations[0].board().fen()
    motore = MotoreFinto(partita, {prima_di_bc4: _cp(-300, chess.WHITE)}, assenti=[prima_di_bc4])
    monkeypatch.setattr(engine, "percorso_salvataggio", lambda relativo: str(tmp_path / relativo))
    monkeypatch.setattr(engine, "ENGINE", motore)
    monkeypatch.setattr(engine, "key", lambda *_a, **_k: "")
    monkeypatch.setattr(engine, "Acusticator", lambda *_a, **_k: None)
    monkeypatch.setattr(engine.pyperclip, "copy", lambda *_a: None)
    monkeypatch.setattr(engine, "_parametri_analisi_automatica", lambda *_a: (1, chess.engine.Limit(depth=1), 0, 2, None))
    engine.AnalisiAutomatica(partita)
    riepilogo = next((tmp_path / "txt").glob("*.txt")).read_text(encoding="utf-8")
    assert "  Gabry: " in riepilogo and "Elo stimato fra" in riepilogo
    assert "Mosse come il motore:" in riepilogo
    assert "  Nero: prima scelta 100%, fra le prime tre 100%, su 2 mosse." in riepilogo
    assert "Precisione per fase:" in riepilogo
    assert "Momenti decisivi:" in riepilogo
    assert "3. Bc4, Gabry: la probabilità di vittoria del Bianco passa dal 50% al 25%." in riepilogo
    assert "Uso del tempo:" in riepilogo
    assert "  Gabry, le mosse più lunghe: 2. Nf3 in 8 secondi" in riepilogo
    assert "sulle mosse giudicate inesattezza, errore o svarione" in riepilogo
    # La confutazione dopo la mossa sbagliata, e le alternative dal lato del Bianco.
    alfiere = partita.variations[0].variations[0].variations[0].variations[0].variations[0]
    assert any(variante.comment == "[OAA: Confutazione]" for variante in alfiere.variations[1:])
    assert all(variante.comment == "[OAA: Alt: +0.00]" for variante in alfiere.parent.variations[1:])
