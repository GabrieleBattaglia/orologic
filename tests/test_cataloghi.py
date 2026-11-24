# Orologic, prove dei cataloghi delle traduzioni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Ogni traduzione delle quattro lingue tiene la forma della frase italiana:
gli stessi segnaposto fra graffe, che format riempie e che una traduzione
rotta farebbe cadere; gli stessi codici del prompt di gioco; la stessa e
commerciale degli acceleratori; gli stessi spazi ai bordi e gli stessi a
capo, che reggono la console e il display braille. Sono i guasti che il
traduttore automatico faceva un tempo, e che qui non devono tornare. I .mo
compilati devono esserci e dire quello che dicono i .po."""

import gettext
import os
import re

import polib
import pytest
from babel.messages.pofile import read_po

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINGUE = ("en", "es", "fr", "pt")
GRAFFE = re.compile(r"\{[^{}]*\}")
CODICI = re.compile(r"%(?:%|\d+|[a-zA-Z][vVpP]?)")


def _catalogo(lingua):
    return polib.pofile(os.path.join(RADICE, "locales", lingua, "LC_MESSAGES", "messages.po"))


def _bordi(testo):
    return testo[: len(testo) - len(testo.lstrip())], testo[len(testo.rstrip()) :]


def _guasti(originale, tradotta):
    guai = []
    if sorted(GRAFFE.findall(originale)) != sorted(GRAFFE.findall(tradotta)):
        guai.append("segnaposto")
    if "%" in originale and sorted(CODICI.findall(originale)) != sorted(CODICI.findall(tradotta)):
        guai.append("codici del prompt")
    if originale.replace("&&", "").count("&") != tradotta.replace("&&", "").count("&"):
        guai.append("e commerciale")
    if _bordi(originale) != _bordi(tradotta):
        guai.append("spazi ai bordi")
    if originale.count("\n") != tradotta.count("\n"):
        guai.append("a capo")
    return guai


@pytest.mark.parametrize("lingua", LINGUE)
def test_le_traduzioni_tengono_la_forma(lingua):
    rotte = []
    controllate = 0
    for voce in _catalogo(lingua):
        if voce.obsolete or not voce.msgstr:
            continue
        controllate += 1
        guai = _guasti(voce.msgid, voce.msgstr)
        if guai:
            rotte.append(f"{', '.join(guai)}: {voce.msgid!r} -> {voce.msgstr!r}")
    assert not rotte, "\n".join(rotte)
    # Tutto il catalogo, non un pezzo: alla 9.0.0 sono piu' di duemila voci.
    assert controllate > 2000


@pytest.mark.parametrize("lingua", LINGUE)
def test_babel_non_trova_errori(lingua):
    """Il controllo che pybabel compile fa prima di scrivere il .mo. Una frase
    con le graffe e un percento seguito da una lettera, come "% del", Babel la
    prendeva anche per una frase col formato vecchio, %d, e confrontava
    segnaposto che non esistono: il .mo usciva lo stesso, ma il resoconto
    diceva errore (issue 75)."""
    with open(os.path.join(RADICE, "locales", lingua, "LC_MESSAGES", "messages.po"), "rb") as file:
        catalogo = read_po(file, locale=lingua)
    errori = [f"{messaggio.id!r}: {'; '.join(str(errore) for errore in guai)}" for messaggio, guai in catalogo.check()]
    assert not errori, "\n".join(errori)


@pytest.mark.parametrize("lingua", LINGUE)
def test_il_catalogo_e_completo_e_compilato(lingua):
    catalogo = _catalogo(lingua)
    assert catalogo.untranslated_entries() == []
    assert catalogo.fuzzy_entries() == []
    traduzione = gettext.translation("messages", os.path.join(RADICE, "locales"), languages=[lingua])
    for voce in catalogo.translated_entries()[:: max(1, len(catalogo.translated_entries()) // 200)]:
        assert traduzione.gettext(voce.msgid) == voce.msgstr, voce.msgid
