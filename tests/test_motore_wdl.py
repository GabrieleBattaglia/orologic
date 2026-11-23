# Orologic, prove delle percentuali di vittoria, patta e sconfitta.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il motore riceve UCI_ShowWDL all'avvio, cosi' ogni analisi ha vittoria,
patta e sconfitta, anche Rendi verbosa senza una partita giocata prima
(Gabriele, collaudo del 23 novembre 2026). Un motore che non conosce
l'opzione non la riceve, e non compare fra quelle ignorate."""

from orologic_modules import engine


class MotoreFinto:
    def __init__(self, opzioni):
        self.options = dict.fromkeys(opzioni)
        self.configurate = {}

    def configure(self, opzioni):
        self.configurate.update(opzioni)


def test_le_percentuali_si_chiedono_al_motore_che_le_conosce(monkeypatch):
    finto = MotoreFinto(["Hash", "Threads", "Skill Level", "Move Overhead", "UCI_ShowWDL"])
    monkeypatch.setattr(engine, "ENGINE", finto)
    engine._configura_opzioni({})
    assert finto.configurate["UCI_ShowWDL"] is True


def test_un_motore_senza_percentuali_non_le_riceve_e_non_avvisa(monkeypatch, capsys):
    finto = MotoreFinto(["Hash", "Threads", "Skill Level", "Move Overhead"])
    monkeypatch.setattr(engine, "ENGINE", finto)
    engine._configura_opzioni({})
    assert "UCI_ShowWDL" not in finto.configurate
    assert "UCI_ShowWDL" not in capsys.readouterr().out
