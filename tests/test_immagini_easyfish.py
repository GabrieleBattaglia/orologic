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
