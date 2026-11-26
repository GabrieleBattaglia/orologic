# Orologic, prove delle immagini e dei PDF di Easyfish.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le impostazioni grafiche e l'esportazione della scacchiera di Easyfish
(revisione 2 del 26 novembre 2026). Su un'installazione nuova il database ha
la chiave image_settings vuota: le predefinite riempiono quello che manca
(R2)."""

import chess

from orologic_modules import storage
from orologic_modules.easyfish import image_exporter


def test_le_impostazioni_grafiche_di_un_database_nuovo(impostazioni_rimesse):
    storage.SetValue("image_settings", {})
    impostazioni = image_exporter.get_image_settings()
    assert impostazioni["square_light"] == [94, 85, 71] and impostazioni["size"] == 600
    assert "<svg" in image_exporter.generate_custom_svg(chess.Board())
    # Quelle salvate vincono, e il resto viene dalle predefinite.
    storage.SetValue("image_settings", {"size": 400})
    impostazioni = image_exporter.get_image_settings()
    assert impostazioni["size"] == 400 and impostazioni["square_dark"] == [41, 30, 25]
    # Chi cambia la copia non cambia le predefinite.
    impostazioni["square_light"][0] = 0
    assert image_exporter.IMPOSTAZIONI_PREDEFINITE["square_light"][0] == 94


def test_il_pdf_dopo_qualche_mossa(tmp_path, monkeypatch, capsys):
    """R13: export_board_pdf passava a variation_san i nodi invece delle
    mosse, e il PDF nasceva solo dalla posizione iniziale."""
    import io

    import chess.pgn

    from orologic_modules import config

    game = chess.pgn.read_game(io.StringIO("1. e4 e5 2. Nf3 Nc6 *"))
    nodo = game.end()
    monkeypatch.setattr(image_exporter, "Acusticator", lambda *a, **k: None)
    risposte = iter(["prova", "un commento"])
    monkeypatch.setattr(image_exporter, "dgt", lambda *a, **k: next(risposte))
    monkeypatch.setattr(config, "percorso_salvataggio", lambda nome: str(tmp_path / nome))
    image_exporter.export_board_pdf(nodo.board(), nodo)
    uscita = capsys.readouterr().out
    assert "Errore" not in uscita
    pdf = list((tmp_path / "images").glob("prova_*.pdf"))
    assert len(pdf) == 1 and pdf[0].stat().st_size > 1000


def test_la_scacchiera_mostra_ultima_mossa_e_scacco(impostazioni_rimesse):
    """R56: .ii chiedeva i colori dell'ultima mossa e dello scacco, ma alla
    scacchiera non si passavano."""
    board = chess.Board()
    for mossa in ("f2f3", "e7e5", "g2g4", "d8h4"):
        board.push_uci(mossa)
    svg = image_exporter.generate_custom_svg(board)
    assert svg.count("lastmove") == 2
    assert "check_gradient" in svg
    impostazioni = image_exporter.get_image_settings()
    chiara = image_exporter.rgb_from_percent(*impostazioni["square_light"])
    assert chiara in svg
