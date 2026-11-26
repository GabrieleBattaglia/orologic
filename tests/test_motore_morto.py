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
