# Orologic, prove dei suoni: la finestra suona come il terminale (T5).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Per ogni impostazione, i suoni della funzione del terminale e quelli della
finestra per la stessa azione, registrati nota per nota e confrontati: lo
stesso evento deve avere lo stesso suono (Gabriele, collaudo della T5).
Acusticator e' sostituito da un registro in ogni modulo che suona: niente
esce dalle casse."""

import os
import shutil
import time

import pytest
import wx

from orologic_modules import (
    config,
    dialoghi,
    engine,
    gioca,
    impostazioni,
    modello_prompt,
    storage,
    temi,
    ui,
)


class Registro:
    """Acusticator finto: si segna ogni suono, come chiamata e argomenti."""

    def __init__(self):
        self.suoni = []

    def __call__(self, *argomenti, **opzioni):
        self.suoni.append(("suono", argomenti, tuple(sorted(opzioni.items()))))

    def play(self, nome, **opzioni):
        self.suoni.append(("preset", (nome,), tuple(sorted(opzioni.items()))))

    def prendi(self):
        suoni, self.suoni = self.suoni, []
        return suoni


@pytest.fixture
def registro(monkeypatch):
    finto = Registro()
    for modulo in (ui, engine, impostazioni, temi, modello_prompt):
        monkeypatch.setattr(modulo, "Acusticator", finto)
    monkeypatch.setattr(time, "sleep", lambda _secondi: None)
    monkeypatch.setattr(engine, "InitEngine", lambda: True)
    monkeypatch.setattr(engine, "CloseEngine", lambda: None)
    volume = config.VOLUME
    config.VOLUME = 0.3
    cartella = os.path.dirname(config.DB_FILE)
    copia = cartella + ".suoni"
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(cartella, copia)
    try:
        yield finto
    finally:
        config.VOLUME = volume
        shutil.rmtree(cartella, ignore_errors=True)
        shutil.copytree(copia, cartella)
        shutil.rmtree(copia, ignore_errors=True)


def _risposte(*valori):
    fila = list(valori)

    def risposta(*_argomenti, **_opzioni):
        return fila.pop(0)

    return risposta


@pytest.fixture
def gestore(finestra, monkeypatch, impostazioni_rimesse):
    def risposte(*valori):
        # Una fila sola per le due domande, nell'ordine in cui arrivano.
        risposta = _risposte(*valori)
        monkeypatch.setattr(finestra, "chiedi_valore", risposta)
        monkeypatch.setattr(finestra, "scegli", risposta)

    # Un avviso sarebbe un dialogo modale, fermo per sempre sul desktop nascosto.
    monkeypatch.setattr(finestra, "avvisa", lambda _genitore, testo: pytest.fail(testo))
    # Il nucleo fermo in un menu: il motore si puo' cambiare.
    monkeypatch.setattr(finestra, "motore_in_uso", lambda: False)
    finestra.gestore.risposte = risposte
    yield finestra.gestore
    if finestra.gestore.lavoro is not None:
        finestra.gestore.lavoro.join(5)


def test_il_volume(registro, gestore, monkeypatch):
    monkeypatch.setattr(ui, "dgt", _risposte(40))
    ui.RegolaVolume()
    terminale = registro.prendi()
    config.VOLUME = 0.3
    gestore.risposte(40)
    gestore.cambia("volume", None)
    assert registro.prendi() == terminale
    assert len(terminale) == 2


def test_tempo_e_linee_dell_analisi(registro, gestore, monkeypatch):
    monkeypatch.setattr(ui, "dgt", _risposte(2.5, 4))
    monkeypatch.setattr(ui, "enter_escape", lambda *_a, **_o: False)
    ui.ImpostazioniAnalisi()
    terminale = registro.prendi()
    storage.SetValue("default_analysis_time", 1.0)
    storage.SetValue("default_multipv", 3)
    gestore.risposte(2.5, 4)
    gestore.cambia("analisi_tempo", None)
    gestore.cambia("analisi_linee", None)
    assert registro.prendi() == terminale
    assert len(terminale) == 2


def test_le_soglie(registro, gestore, monkeypatch):
    monkeypatch.setattr(ui, "dgt", _risposte(1.0, 3, 4, 9, 14))
    monkeypatch.setattr(ui, "enter_escape", lambda *_a, **_o: True)
    ui.ImpostazioniAnalisi()
    # Nel terminale le tre soglie hanno un bip solo, in fondo: e' il terzo.
    bip = registro.prendi()[-1]
    gestore.risposte(6)
    gestore.cambia("soglia_inesattezza", None)
    assert registro.prendi() == [bip]


def test_gli_interruttori(registro, gestore):
    ui.alterna_impostazione("autosave_enabled")
    terminale = registro.prendi()
    gestore.risposte(1 if storage.LoadDB().get("autosave_enabled") else 0)
    gestore.cambia("salvataggio", None)
    assert registro.prendi() == terminale
    assert len(terminale) == 1


def test_il_nome_del_giocatore_non_suona(registro, gestore, monkeypatch):
    monkeypatch.setattr(gioca, "dgt", _risposte("Gabry"))
    gioca.imposta_nome()
    assert registro.prendi() == []
    gestore.risposte("Gabriele")
    gestore.cambia("giocatore", None)
    assert registro.prendi() == []


def test_i_nomi(registro, gestore, monkeypatch):
    """Il terminale: il nome del pedone, il genere, il plurale, il genere, e il
    punto, che chiude e salva. La finestra: il nome, il plurale, il genere e
    la chiusura dell'elenco. Le sue note sono quelle del terminale, nello
    stesso ordine."""
    monkeypatch.setattr(ui, "dgt", _risposte("pedone", "m", "pedoni", "m", "."))
    ui.EditLocalization()
    terminale = registro.prendi()
    temi.suona("nomi")
    tema = registro.prendi()
    assert tema and len(terminale) == 5

    class Elenco:
        def __init__(self, *_argomenti):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_eccezione):
            return False

        def ShowModal(self):
            gestore.risposte("pedina", "pedine", 0)
            gestore.cambia_un_nome(("pieces", "pawn", "name"), "Nome per 'Pedone'", None)
            gestore.cambia_un_nome(("pieces", "pawn", "pname"), "Nome PLURALE per 'Pedone'", None)
            gestore.cambia_un_nome(("pieces", "pawn", "gender"), None, None)

    monkeypatch.setattr(dialoghi, "FinestraImpostazioni", Elenco)
    gestore.cambia("nomi", None)
    finestra = registro.prendi()
    assert finestra[0] == tema[0]
    # Nome, plurale, genere dopo il plurale, arpeggio.
    assert finestra[1:] == [terminale[0], terminale[2], terminale[3], terminale[4]]


def test_il_motore(registro, gestore, monkeypatch, tmp_path):
    vero = tmp_path / "stockfish.exe"
    vero.write_bytes(b"")
    monkeypatch.setattr(engine, "dgt", _risposte(str(tmp_path), "stockfish.exe", 64, 1, 10, 30))
    engine.EditEngineConfig()
    terminale = registro.prendi()
    temi.suona("motore")
    tema = registro.prendi()
    assert tema
    # I bip delle cinque domande, poi la nota del motore salvato.
    bip, salvato = terminale[:5], terminale[5]
    assert len(terminale) == 6

    class Elenco:
        def __init__(self, *_argomenti):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_eccezione):
            return False

        def ShowModal(self):
            pass

    monkeypatch.setattr(dialoghi, "FinestraImpostazioni", Elenco)
    gestore.cambia("motore", None)
    assert registro.prendi() == tema
    altra = tmp_path / "altra"
    altra.mkdir()
    (altra / "stockfish.exe").write_bytes(b"")
    risposte = {"percorso": str(altra), "hash": 128, "core": 2, "skill": 12, "overhead": 40}
    for numero, voce in enumerate(("percorso", "hash", "core", "skill", "overhead")):
        gestore.risposte(risposte[voce])
        gestore.cambia_il_motore(voce, None)
        if gestore.lavoro is not None:
            gestore.lavoro.join(5)
        suoni = registro.prendi()
        assert suoni[0] == bip[numero], voce
    # La nota del motore salvato, dopo il riavvio, come nel terminale.
    gestore.risposte(256)
    gestore.cambia_il_motore("hash", None)
    gestore.lavoro.join(5)
    assert registro.prendi() == [bip[1], salvato]


def test_il_prompt_sbagliato(registro, app):
    modello_prompt._errore()
    terminale = registro.prendi()
    # Un testo libero troppo lungo: il modello supera i 200 caratteri.
    finestra_del_prompt = dialoghi.FinestraPrompt(None, "%b", lambda *_argomenti: "x" * 250, suono_d_errore=modello_prompt._errore)
    try:
        finestra_del_prompt.disponibili.SetSelection(finestra_del_prompt.disponibili.GetCount() - 1)
        finestra_del_prompt.aggiungi()
        finestra_del_prompt.conferma()
    finally:
        finestra_del_prompt.Destroy()
    assert registro.prendi() == terminale
    assert len(terminale) == 1
    impostazioni.Impostazioni.salva_il_prompt("%b %n %m", "%b %4 %m")
    impostazioni.Impostazioni.salva_il_prompt("%b %4 %m", modello_prompt.PREDEFINITO)
    assert [s[1][0] for s in registro.prendi()] == ["orologic_prompt_salvato", "orologic_prompt_predefinito"]


def test_ctrl_virgola_suona_il_tema_delle_impostazioni(registro, finestra):
    temi.suona("impostazioni")
    tema = registro.prendi()
    assert tema

    def chiudi():
        if finestra.dialogo_impostazioni:
            finestra.dialogo_impostazioni.EndModal(wx.ID_CANCEL)
            return
        wx.CallLater(50, chiudi)

    wx.CallLater(50, chiudi)
    evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    evento.SetKeyCode(ord(","))
    evento.SetControlDown(True)
    finestra._tasto_della_finestra(evento)
    assert registro.prendi() == tema
