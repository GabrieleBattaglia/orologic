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


def test_la_condivisione_non_legge_il_database_dal_suo_filo(monkeypatch):
    """R57: il filo di pygame leggeva il database a ogni ridisegno. Ora le
    impostazioni arrivano dal filo di chi apre la finestra, e dopo .ii."""
    from orologic_modules.easyfish import sharing_window

    letture = []
    monkeypatch.setattr(sharing_window, "get_image_settings", lambda: letture.append(1) or {"size": 321})
    finestra = sharing_window.PygameBoardWindow("prova")
    finestra.nuove_impostazioni()
    assert finestra.impostazioni == {"size": 321} and finestra.update_event.is_set()
    disegnate = []

    def svg(board, node, orientation=None, override_size=None, settings=None):
        disegnate.append(settings)
        raise RuntimeError("basta cosi'")

    monkeypatch.setattr(sharing_window, "generate_custom_svg", svg)
    finestra.board = chess.Board()
    finestra._render(None)
    assert disegnate == [{"size": 321}] and letture == [1]


def test_l_avvio_non_carica_reportlab_svglib_e_pygame():
    """R93: reportlab, svglib e pygame si caricavano a ogni avvio, e un loro
    guasto nel pacchetto avrebbe impedito l'avvio di tutto Orologic."""
    import subprocess
    import sys

    from conftest import RADICE

    codice = (
        "import sys; sys.path.insert(0, r'" + RADICE + "'); "
        "import percorsi, tempfile; percorsi.cartella_applicazione = lambda: tempfile.mkdtemp(); "
        "from orologic_modules.easyfish import easyfish_app; "
        "print(sorted(m for m in ('reportlab', 'svglib', 'pygame') if m in sys.modules))"
    )
    uscita = subprocess.run([sys.executable, "-B", "-c", codice], capture_output=True, text=True, timeout=120, cwd=RADICE, check=False)
    assert uscita.stdout.strip().splitlines()[-1] == "[]", uscita.stderr[-2000:]


def test_ii_non_chiede_piu_ombreggiatura_e_colore_dello_scacco(impostazioni_rimesse, monkeypatch, capsys):
    """R56 e R134, scelta di Gabriele del 26 novembre 2026: .ii chiedeva
    l'ombreggiatura dei pezzi, che nessuno disegnava, e il colore dello
    scacco, che python-chess non riceve. Le due domande escono, con le loro
    chiavi; lo scacco resta rosso."""
    domande = []

    def dgt(prompt="", default=None, **_opzioni):
        domande.append(prompt)
        return default

    monkeypatch.setattr(image_exporter, "dgt", dgt)
    monkeypatch.setattr(image_exporter, "Acusticator", lambda *_a, **_k: None)
    storage.SetValue("image_settings", {"shadow": False, "check_color": [1, 2, 3]})
    image_exporter.image_settings_menu()
    assert not any("ombreggiatura" in domanda.lower() for domanda in domande)
    assert "Colore Scacco Re" not in capsys.readouterr().out
    salvate = storage.LoadDB()["image_settings"]
    assert "shadow" not in salvate and "check_color" not in salvate
    assert "shadow" not in image_exporter.IMPOSTAZIONI_PREDEFINITE and "check_color" not in image_exporter.IMPOSTAZIONI_PREDEFINITE


def test_un_colore_guasto_nel_database_non_fa_cadere_le_immagini(impostazioni_rimesse):
    """R134: i valori delle impostazioni grafiche non si controllavano, e un
    colore guasto nel database faceva cadere .i e .ii. Un valore salvato vale
    solo se ha la forma del predefinito."""
    storage.SetValue("image_settings", {"square_light": "rosso", "square_dark": [1, 2], "size": "grande", "coord": [10, 20, 30]})
    impostazioni = image_exporter.get_image_settings()
    assert impostazioni["square_light"] == [94, 85, 71] and impostazioni["square_dark"] == [41, 30, 25]
    assert impostazioni["size"] == 600 and impostazioni["coord"] == [10, 20, 30]
    assert "<svg" in image_exporter.generate_custom_svg(chess.Board())


def test_la_scacchiera_condivisa_senza_pygame_non_fa_cadere(monkeypatch, capsys):
    """R134: l'import della finestra di condivisione stava fuori da ogni try,
    e .cs senza pygame faceva cadere il nucleo."""
    import sys

    from orologic_modules.easyfish import easyfish_app

    monkeypatch.setitem(sys.modules, "orologic_modules.easyfish.sharing_window", None)
    monkeypatch.setattr(easyfish_app, "Acusticator", lambda *_a, **_k: None)
    assert easyfish_app._apri_condivisione(chess.Board(), None, None) is None
    assert "pygame" in capsys.readouterr().out
