# Orologic, prove del contatore dei lanci con la chiusura da Alt+F4.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il contatore dei lanci si aggiorna all'avvio, prima del menu principale,
e si scrive subito nel database: chiudere con Alt+F4 invece che dal menu non
lo perde, e non lo conta due volte (Gabriele, 23 novembre 2026)."""

from conftest import pompa


def test_orologic_parte_e_conta_il_lancio_anche_chiuso_con_alt_f4(finestra, monkeypatch):
    import os

    import orologic
    from orologic_modules import engine, storage

    monkeypatch.setattr(engine, "InitEngine", lambda: False)
    # Se il nucleo non si chiudesse in tempo, la finestra uscirebbe dal
    # processo: qui si segna e basta, per non chiudere le prove.
    uscite = []
    monkeypatch.setattr(os, "_exit", uscite.append)
    prima = storage.LoadDB().get("launch_count", 0)
    finestra.avvia_il_nucleo(lambda: orologic.esegui(con_la_finestra=True))
    assert pompa(lambda: finestra.attesa.tipo == "menu", 30)
    assert storage.LoadDB()["launch_count"] == prima + 1
    # Alt+F4 arriva alla finestra come richiesta di chiusura.
    finestra.Close()
    assert pompa(lambda: not finestra.nucleo.is_alive(), 10)
    assert uscite == []
    assert storage.LoadDB()["launch_count"] == prima + 1
