# Orologic, prove delle sfide e delle varianti di Lichess (rilievi R20 e
# R125 della revisione 2).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Orologic su Lichess gioca solo gli scacchi standard e Chess960, per
scelta di Gabriele del 26 novembre 2026 (R20): le altre varianti escono dal
menu, e la scacchiera, che e' quella standard, non le riceve mai. Una sfida
ricevuta in una di quelle varianti, o con una cadenza che la Board API non
gioca, si rifiuta con un messaggio prima di accettarla (R125). La rete non
si tocca: le risposte di Lichess sono finte."""

import pytest

from orologic_modules import lichess_app, lichess_board


def _sfida(variante="standard", limite=600, incremento=0, nome=None):
    return {
        "id": "abcd1234",
        "variant": {"key": variante, "name": nome or variante},
        "speed": "rapid",
        "timeControl": {"type": "clock", "limit": limite, "increment": incremento, "show": f"{limite // 60}+{incremento}"},
        "challenger": {"name": "Rossi"},
        "rated": False,
    }


def test_le_sfide_che_orologic_non_gioca():
    perche = lichess_app.perche_non_si_gioca
    assert perche(_sfida()) is None
    assert perche(_sfida("chess960", 300, 3)) is None
    frase, motivo = perche(_sfida("crazyhouse", nome="Crazyhouse"))
    assert motivo == "variant" and "Crazyhouse" in frase
    frase, motivo = perche(_sfida(limite=60))
    assert motivo == "tooFast" and "bullet" in frase
    corrispondenza = {"id": "x", "variant": {"key": "standard"}, "timeControl": {"type": "correspondence", "daysPerTurn": 2}}
    assert perche(corrispondenza) is None


@pytest.mark.parametrize(("sfida", "motivo"), [(_sfida("atomic", nome="Atomic"), "variant"), (_sfida(limite=30), "tooFast")])
def test_la_sfida_che_non_si_gioca_si_rifiuta_prima_di_accettarla(monkeypatch, sfida, motivo):
    monkeypatch.setattr(lichess_app, "get_challenges", lambda *_argomenti, **_opzioni: ([sfida], []))
    scelte = iter(["1", "."])
    monkeypatch.setattr(lichess_app, "menu", lambda *_argomenti, **_opzioni: next(scelte))
    monkeypatch.setattr(lichess_app, "key", lambda *_argomenti, **_opzioni: "\r")
    monkeypatch.setattr(lichess_app, "accept_challenge", lambda *_argomenti: pytest.fail("la sfida non si accetta"))
    monkeypatch.setattr(lichess_board, "play_game", lambda *_argomenti: pytest.fail("la partita non parte"))
    rifiutate = []
    monkeypatch.setattr(lichess_app, "decline_challenge", lambda token, sfida_id, motivo=None: rifiutate.append((token, sfida_id, motivo)) or True)
    lichess_app.rispondi_alle_sfide("token", "prova")
    assert rifiutate == [("token", "abcd1234", motivo)]


def test_il_rifiuto_dice_il_motivo_a_lichess(monkeypatch):
    mandate = []
    monkeypatch.setattr(lichess_app.rete, "invia", lambda url, token=None, dati=None, **_opzioni: mandate.append((url, dati)) or (True, None))
    assert lichess_app.decline_challenge("token", "abcd1234", "variant")
    assert mandate == [("https://lichess.org/api/challenge/abcd1234/decline", {"reason": "variant"})]


def test_fuori_dallo_standard_c_e_solo_chess960(monkeypatch):
    monkeypatch.setattr(lichess_app, "dgt", lambda *_argomenti, **_opzioni: "10+0")
    risposte = iter([False, False])
    monkeypatch.setattr(lichess_app, "enter_escape", lambda *_argomenti, **_opzioni: next(risposte))
    menu_mostrati = []

    def menu(voci, **_opzioni):
        menu_mostrati.append(dict(voci))
        return "1"

    monkeypatch.setattr(lichess_app, "menu", menu)
    parametri = lichess_app.get_game_params()
    assert parametri["variant"] == "chess960"
    # L'unico menu e' quello del colore: nessun elenco di varianti.
    assert len(menu_mostrati) == 1 and "chess960" not in menu_mostrati[0]


def test_una_partita_in_una_variante_non_si_gioca_sulla_scacchiera_standard():
    """R20: una partita aperta da Lichess in una variante, per esempio
    cominciata dal sito, faceva cadere Orologic alla prima mossa: la
    scacchiera e' sempre quella standard."""
    assert lichess_board.variante_giocabile("standard")
    assert lichess_board.variante_giocabile("chess960")
    assert not lichess_board.variante_giocabile("crazyhouse")
    # Da una posizione data le regole sono quelle standard.
    assert lichess_board.variante_giocabile("fromPosition")
    assert lichess_app.perche_non_si_gioca(_sfida("fromPosition")) is None
