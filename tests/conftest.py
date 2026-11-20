# Orologic, preparazione delle prove automatiche.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Le prove non toccano mai i dati veri: prima di importare qualunque modulo
di Orologic, la cartella dei salvataggi, quella che percorsi.py chiede a
cartella_applicazione di GBUtils, diventa una cartella temporanea, con la
sola lingua scelta copiata dalla cartella vera, cosi' polipo non la chiede.
Le risorse in sola lettura, come i cataloghi delle traduzioni, restano
quelle vere. Nate con la tappa T1 della GUI, il 20 novembre 2026.
"""

import os
import shutil
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

import percorsi  # noqa: E402

CARTELLA_DELLE_PROVE = tempfile.mkdtemp(prefix="orologic_prove_")
os.makedirs(os.path.join(CARTELLA_DELLE_PROVE, "settings"))
_LINGUA = os.path.join(RADICE, "settings", "selected_language.json")
if os.path.exists(_LINGUA):
    shutil.copy2(_LINGUA, os.path.join(CARTELLA_DELLE_PROVE, "settings"))
percorsi.cartella_applicazione = lambda: CARTELLA_DELLE_PROVE


def pytest_unconfigure(config):
    shutil.rmtree(CARTELLA_DELLE_PROVE, ignore_errors=True)
