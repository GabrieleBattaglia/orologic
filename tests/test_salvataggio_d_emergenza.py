# Orologic, prove del salvataggio d'emergenza delle partite (rilievo R107
# della verifica della revisione 2).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le partite aperte si salvano chiudendo Orologic, su un errore del nucleo,
e quando la finestra esce col nucleo fermo: qui la partita contro il motore
e il registro dello strato. Le altre partite hanno le loro prove in
test_arbitraggio, test_easyfish_salvataggio e test_lichess_mosse. I PGN si
scrivono davvero, nella cartella pgn delle prove, e si tolgono."""

import os

import chess
import pytest

from orologic_modules import config, gioca, strato
from orologic_modules.easyfish import game_mode


def _pgn_di_adesso():
    cartella = config.percorso_salvataggio("pgn")
    return set(os.listdir(cartella)) if os.path.isdir(cartella) else set()


def _pgn_nuovi(prima):
    cartella = config.percorso_salvataggio("pgn")
    return [os.path.join(cartella, nome) for nome in sorted(_pgn_di_adesso() - prima)]


@pytest.mark.parametrize("guasto", [KeyboardInterrupt, RuntimeError])
def test_la_partita_contro_il_motore_interrotta_si_salva(monkeypatch, guasto):
    """La partita contro il motore, chiusa a meta' o caduta per un errore,
    si perdeva."""
    monkeypatch.setattr(gioca, "_motore_pronto", object)
    monkeypatch.setattr(gioca, "nome_utente", lambda chiedi=True: "Prova")
    monkeypatch.setattr(gioca, "enter_escape", lambda _domanda: True)
    monkeypatch.setattr(gioca.chess960_utils, "verifica_motore_chess960", lambda *_argomenti: None)

    def interrotta(partita, _motore, carriera=False):
        partita.add_line([chess.Move.from_uci(mossa) for mossa in ("e2e4", "e7e5")])
        raise guasto

    monkeypatch.setattr(game_mode, "StartEngineGame", interrotta)
    prima = _pgn_di_adesso()
    try:
        with pytest.raises(guasto):
            gioca.libero()
        nuovi = _pgn_nuovi(prima)
        assert len(nuovi) == 1 and "interrotta" in os.path.basename(nuovi[0])
        with open(nuovi[0], encoding="utf-8") as file:
            assert "1. e4 e5" in file.read()
    finally:
        for percorso in _pgn_nuovi(prima):
            os.remove(percorso)


def test_il_registro_chiama_le_partite_aperte_una_volta():
    """Il registro dello strato: la finestra chiama i salvataggi delle
    partite aperte, dall'ultima; uscite dalla zona non ci sono piu', e un
    salvataggio che cade non ferma gli altri."""
    chiamati = []

    def guasto():
        chiamati.append("guasto")
        raise OSError("disco pieno")

    with strato.salvataggio_d_emergenza(lambda: chiamati.append("prima")), strato.salvataggio_d_emergenza(guasto):
        strato.salva_le_partite_aperte()
    assert chiamati == ["guasto", "prima"]
    strato.salva_le_partite_aperte()
    assert chiamati == ["guasto", "prima"]
