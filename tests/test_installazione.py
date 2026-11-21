# Orologic, prove dell'installazione: App installate e il mutex (tappa T5c della GUI).
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La versione in App installate si corregge solo per la cartella installata,
con un registro finto; il mutex si apre e si tiene. Il registro vero non si
tocca, e il mutex delle prove ha un nome suo."""

import os
import re

from orologic_modules import installazione


class Registro:
    """winreg finto: una chiave sola, coi suoi valori."""

    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_WRITE = 2
    REG_SZ = 1

    def __init__(self, valori=None):
        self.valori = valori
        self.scritti = {}

    def OpenKey(self, radice, chiave, _riservato, _accesso):
        if self.valori is None or chiave != installazione.CHIAVE or radice != "HKCU":
            raise OSError("chiave assente")
        registro = self

        class Chiave:
            def __enter__(self):
                return registro

            def __exit__(self, *_eccezione):
                return False

        return Chiave()

    def QueryValueEx(self, _chiave, nome):
        if nome not in self.valori:
            raise OSError(nome)
        return self.valori[nome], self.REG_SZ

    def SetValueEx(self, _chiave, nome, _riservato, _tipo, valore):
        self.scritti[nome] = valore
        self.valori[nome] = valore


def test_la_versione_si_corregge_solo_nella_sua_cartella():
    registro = Registro({"InstallLocation": "C:\\Programmi\\Orologic", "DisplayVersion": "9.0.0"})
    assert installazione.aggiorna_la_versione("9.0.1", "c:\\programmi\\orologic\\", registro)
    assert registro.scritti == {"DisplayVersion": "9.0.1"}
    # Gia' giusta, non si riscrive.
    assert not installazione.aggiorna_la_versione("9.0.1", "C:\\Programmi\\Orologic", registro)
    # Una copia portatile altrove non tocca la voce.
    assert not installazione.aggiorna_la_versione("9.0.2", "D:\\Orologic", registro)
    assert registro.valori["DisplayVersion"] == "9.0.1"
    # Senza installazione non succede niente.
    assert not installazione.aggiorna_la_versione("9.0.2", "C:\\Programmi\\Orologic", Registro())


def test_l_appid_e_lo_stesso_dell_installatore():
    radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(radice, "Orologic.iss"), encoding="utf-8-sig") as file:
        testo = file.read()
    appid = re.search(r"^AppId=\{\{([0-9A-F-]+)\}", testo, re.MULTILINE).group(1)
    assert "{" + appid + "}_is1" in installazione.CHIAVE
    assert "AppMutex=" + installazione.NOME_DEL_MUTEX in testo


def test_il_mutex_si_tiene(monkeypatch):
    monkeypatch.setattr(installazione, "_MUTEX", None)
    maniglia = installazione.tieni_il_mutex(f"Orologic-prove-{os.getpid()}")
    assert maniglia
    assert installazione.tieni_il_mutex() == maniglia
