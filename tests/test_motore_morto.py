# Orologic, prove del motore che muore durante l'analisi (rilievo R41 della
# revisione 2, 26 novembre 2026).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Motori finti: uno morto, che solleva EngineTerminatedError, e uno buono,
che risponde. interroga riavvia il motore una volta e lo dice."""

import chess
import chess.engine
import pytest

from orologic_modules import engine


class Morto:
    def analyse(self, *a, **k):
        raise chess.engine.EngineTerminatedError("engine process died unexpectedly")

    def quit(self):
        pass


class Buono:
    def __init__(self):
        self.id = {"name": "Buono"}

    def analyse(self, board, limit, **k):
        return [{"score": chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE), "pv": [chess.Move.from_uci("e2e4")]}]

    def quit(self):
        pass


@pytest.fixture
def motore(monkeypatch):
    monkeypatch.setattr(engine, "ENGINE", Morto())
    engine.cache_analysis.clear()
    yield
    engine.cache_analysis.clear()


def test_il_motore_morto_riparte_una_volta(motore, monkeypatch, capsys):
    def riavvia():
        engine.ENGINE = Buono()
        return True

    monkeypatch.setattr(engine, "InitEngine", riavvia)
    risultato = engine.interroga(chess.Board(), chess.engine.Limit(time=0.1), multipv=1)
    assert risultato[0]["pv"] == [chess.Move.from_uci("e2e4")]
    assert "Il motore si e' fermato: lo riavvio." in capsys.readouterr().out
    # Easyfish, col motore vivo, vede il motore nuovo.
    assert engine.MOTORE and engine.MOTORE.id == {"name": "Buono"}


def test_il_motore_che_non_riparte_si_dice_e_non_fa_cadere(motore, monkeypatch, capsys):
    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    assert engine._analizza_con_cache(chess.Board(), 1) is None
    assert engine.ENGINE is None and not engine.MOTORE
    assert "Il motore non riparte: niente analisi." in capsys.readouterr().out
    assert engine.CalculateBest(chess.Board()) is None


# R49: la configurazione del motore.


class Finto:
    def __init__(self):
        self.id = {"name": "Finto"}
        self.chiuso = False

    def quit(self):
        self.chiuso = True


@pytest.fixture
def motore_finto(impostazioni_rimesse, monkeypatch, tmp_path):
    import os

    from orologic_modules import config

    cartella = config.percorso_salvataggio("motore_di_prova")
    os.makedirs(cartella, exist_ok=True)
    open(os.path.join(cartella, "finto.exe"), "wb").close()
    aperti = []
    monkeypatch.setattr(engine.chess.engine.SimpleEngine, "popen_uci", lambda percorso, **k: aperti.append((percorso, Finto())) or aperti[-1][1])
    monkeypatch.setattr(engine, "SearchForEngine", lambda: (cartella, "finto.exe", False))
    monkeypatch.setattr(engine, "ENGINE", None)
    yield aperti
    engine.CloseEngine()


def test_il_motore_spostato_si_dice_e_si_cerca(motore_finto, monkeypatch, capsys):
    from orologic_modules import storage

    monkeypatch.setattr(engine, "_configura_opzioni", lambda cfg: None)
    storage.SetValue("engine_config", {"engine_path": "Z:/non/esiste/stockfish.exe", "engine_is_relative": False})
    assert engine.InitEngine()
    assert "Il motore configurato non si trova piu'" in capsys.readouterr().out
    cfg = storage.LoadDB()["engine_config"]
    # Sta nella cartella di Orologic: si salva relativo.
    assert cfg["engine_is_relative"] is True and cfg["engine_path"].endswith("finto.exe")


def test_la_configurazione_fallita_chiude_il_motore(motore_finto, monkeypatch):
    from orologic_modules import storage

    def guasta(_cfg):
        raise chess.engine.EngineError("opzione rifiutata")

    monkeypatch.setattr(engine, "_configura_opzioni", guasta)
    storage.SetValue("engine_config", {})
    assert not engine.InitEngine()
    assert engine.ENGINE is None
    assert motore_finto[-1][1].chiuso


# R55: il segno del matto.


def test_il_matto_subito_ha_il_segno(monkeypatch):
    from orologic_modules import board_utils
    from orologic_modules.easyfish import posizione

    scacchiera = chess.Board()
    linea = [{"score": chess.engine.PovScore(chess.engine.Mate(-3), chess.WHITE), "pv": [chess.Move.from_uci("e2e4")]}]
    assert "-M3" in posizione.righe_dell_analisi(scacchiera, linea)[0]
    linea[0]["score"] = chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)
    riga = posizione.righe_dell_analisi(scacchiera, linea)[0]
    assert "M2" in riga and "-M2" not in riga
    assert board_utils.testo_del_matto(-1) == "-M1"
    # La linea migliore del motore dice chi subisce il matto.
    monkeypatch.setattr(engine, "Acusticator", lambda *a, **k: None)
    monkeypatch.setattr(engine, "_analizza_con_cache", lambda board, linee: [{"score": chess.engine.PovScore(chess.engine.Mate(-3), chess.WHITE), "pv": [chess.Move.from_uci("e2e4")]}])
    assert engine.CalculateBest(scacchiera, as_san=True)[0].startswith("Matto subito in 3")


class MortoInPartita:
    """Un motore morto durante una partita: ping, play e id cadono."""

    def __init__(self):
        self.options = {"UCI_Elo": None}

    def ping(self):
        raise chess.engine.EngineTerminatedError("engine process died unexpectedly")

    def play(self, *a, **k):
        raise chess.engine.EngineTerminatedError("engine process died unexpectedly")

    @property
    def id(self):
        raise chess.engine.EngineTerminatedError("engine process died unexpectedly")

    def quit(self):
        pass


class BuonoInPartita:
    def __init__(self):
        self.id = {"name": "Buono"}
        self.options = {"UCI_Elo": None, "UCI_LimitStrength": None}
        self.configurazioni = []

    def ping(self):
        pass

    def configure(self, opzioni):
        self.configurazioni.append(dict(opzioni))

    def play(self, board, limit, **k):
        return chess.engine.PlayResult(next(iter(board.legal_moves)), None)

    def quit(self):
        pass


def test_la_partita_dopo_una_morte_del_motore_lo_riavvia(monkeypatch):
    """R111: se il motore moriva in partita usciva Errore motore, ma ENGINE
    restava non nullo, e alla partita dopo la proprieta' id faceva cadere il
    nucleo, finche' non si riavviava Orologic."""
    from orologic_modules import gioca

    buono = BuonoInPartita()
    monkeypatch.setattr(engine, "ENGINE", MortoInPartita())
    monkeypatch.setattr(engine, "CloseEngine", lambda: None)

    def avvia():
        engine.ENGINE = buono
        return True

    monkeypatch.setattr(engine, "InitEngine", avvia)
    assert not engine.motore_vivo()
    motore = gioca._motore_pronto()
    assert motore and engine.ENGINE is buono
    assert motore.id == {"name": "Buono"}


def test_la_mossa_del_motore_morto_si_riprova_con_la_forza(monkeypatch):
    """R111: la mossa del motore passa da gioca_la_mossa, che riavvia il
    motore morto una volta e gli rimette la forza della partita."""
    from orologic_modules.easyfish import game_mode

    buono = BuonoInPartita()
    monkeypatch.setattr(engine, "ENGINE", MortoInPartita())
    monkeypatch.setattr(engine, "CloseEngine", lambda: None)

    def avvia():
        engine.ENGINE = buono
        return True

    monkeypatch.setattr(engine, "InitEngine", avvia)
    monkeypatch.setattr(engine, "forza", {"tipo": "elo", "valore": 1500, "profondita": None})
    risultato = engine.gioca_la_mossa(chess.Board(), chess.engine.Limit(time=0.1), rimetti_la_forza=lambda motore: game_mode.applica_forza(motore, dict(engine.forza)))
    assert risultato.move in chess.Board().legal_moves
    assert {"UCI_Elo": 1500} in buono.configurazioni


class SordoAlQuit:
    """Un motore che non risponde a quit: close lo chiude comunque."""

    def __init__(self):
        self.chiuso = False

    def quit(self):
        raise TimeoutError("il motore non risponde")

    def close(self):
        self.chiuso = True


def test_dopo_un_quit_fallito_il_motore_si_chiude_comunque(monkeypatch):
    """R131: CloseEngine non chiamava close dopo un quit fallito, e un motore
    che non rispondeva teneva il processo e poteva restare orfano."""
    sordo = SordoAlQuit()
    monkeypatch.setattr(engine, "ENGINE", sordo)
    engine.CloseEngine()
    assert sordo.chiuso and engine.ENGINE is None


class Lento(Morto):
    """Un motore vivo che non risponde."""

    def analyse(self, *a, **k):
        raise TimeoutError("nessuna risposta")


def test_il_motore_che_non_risponde_si_riavvia_e_tiene_tempo_e_linee(motore, monkeypatch):
    """R131: il TimeoutError del motore vivo che non risponde non lo
    prendeva nessuno, e il riavvio dentro interroga rimetteva tempo
    d'analisi e linee ai predefiniti."""
    monkeypatch.setattr(engine, "ENGINE", Lento())
    monkeypatch.setattr(engine, "analysis_time", 7)
    monkeypatch.setattr(engine, "multipv", 4)

    def avvia():
        engine.ENGINE = Buono()
        engine.analysis_time, engine.multipv = 2, 1
        return True

    monkeypatch.setattr(engine, "InitEngine", avvia)
    assert engine.interroga(chess.Board(), chess.engine.Limit(time=0.1))
    assert (engine.analysis_time, engine.multipv) == (7, 4)
    # Se non riparte, l'analisi in cache non cade.
    monkeypatch.setattr(engine, "ENGINE", Lento())
    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    engine.cache_analysis.clear()
    assert engine._analizza_con_cache(chess.Board(), 1) is None


def test_il_motore_mancante_si_dice_una_volta(monkeypatch, capsys):
    """R131: se il motore configurato era sparito, le due righe tornavano a
    ogni avvio del motore."""
    from orologic_modules import storage

    db = storage.LoadDB()
    db["engine_config"] = {"engine_path": "C:/non/c/e/stockfish.exe", "engine_is_relative": False}
    monkeypatch.setattr(storage, "LoadDB", lambda *a, **k: db)
    monkeypatch.setattr(engine, "SearchForEngine", lambda: (None, None, None))
    monkeypatch.setattr(engine, "_MOTORI_MANCANTI_DETTI", set())
    monkeypatch.setattr(engine, "ENGINE", None)
    assert not engine.InitEngine()
    assert not engine.InitEngine()
    uscita = capsys.readouterr().out
    assert uscita.count("non si trova piu'") == 1 and uscita.count("Nessun motore trovato") == 1
