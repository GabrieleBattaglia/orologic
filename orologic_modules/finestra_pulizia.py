# Orologic: la finestra della pulizia dei file accumulati.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La pulizia, chiesta da Gabriele il 21 novembre 2026: la voce Pulizia delle
impostazioni apre questa finestra, che si apre anche da sola all'avvio se ci
sono file piu' vecchi di t (sua scelta nel modulo), come faceva l'avviso del
terminale.

In cima la situazione: per le cartelle pgn, txt e images quanti file e
quanto pesano, in tutto, e quanti sono piu' vecchi di t, con il loro peso.
Poi l'elenco dei file, dal piu' vecchio: Canc lo manda nel cestino. Poi i
pulsanti Elimina tutto ed Elimina piu' vecchi di, con l'elenco di t, a passi
di due mesi da due mesi a tre anni, che resta scelto anche alle prossime
aperture, Ripristina date ai file vecchi, che li riporta a oggi come
l'avviso ignorato del terminale, e Chiudi, che non cancella niente.

Tutto va nel cestino di Windows, con nel_cestino di GBUtils (V306): dove il
cestino non c'e' il file resta dov'e'. Le due cancellazioni di molti file
chiedono conferma; Canc su un file no, perche' dal cestino si torna indietro.
"""

import time

import wx
from GBUtils import Acusticator, formatta_dimensione, nel_cestino
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto, cleaner, config
from .config import _

SUONI = {
    # Come il terminale quando cancella i file vecchi.
    "eliminati": lambda: Acusticator(["c5", 0.1, -1, config.VOLUME, "c5", 0.1, 1, config.VOLUME], kind=1),
    # Come un orologio eliminato.
    "eliminato": lambda: Acusticator(["c4", 0.025, 0, config.VOLUME]),
    # Nuovo: le date riportate a oggi, due note che salgono.
    "ripristinate": lambda: Acusticator(["g5", 0.06, 0, config.VOLUME, "c6", 0.1, 0, config.VOLUME], kind=1),
    "no": lambda: Acusticator(["e3", 0.2, 0, config.VOLUME], kind=2),
}


def suona(evento):
    """I suoni della finestra; le prove li sostituiscono."""
    SUONI[evento]()


def peso(byte):
    """Il peso di un file o di un gruppo, con la virgola nelle lingue che la usano."""
    separatore = "," if config.lingua_rilevata in ("it", "es", "fr", "pt") else "."
    return formatta_dimensione(byte, decimali=1, separatore=separatore, byte_interi=True)


def eta(file, adesso=None):
    giorni = int(((time.time() if adesso is None else adesso) - file["data"]) // 86400)
    return _("1 giorno") if giorni == 1 else _("{n} giorni").format(n=max(0, giorni))


def voce(file, adesso=None):
    """La voce dell'elenco: il nome, la cartella, l'eta' e il peso."""
    return _("{nome}, {cartella}, {eta}, {peso}").format(nome=file["nome"], cartella=file["cartella"], eta=eta(file, adesso), peso=peso(file["peso"]))


def situazione(files, giorni, adesso=None):
    """Le righe dell'area della situazione."""
    righe = []
    for nome in cleaner.CARTELLE:
        della_cartella = [file for file in files if file["cartella"] == nome]
        if della_cartella:
            righe.append(_("{cartella}: {n} file, {peso}").format(cartella=nome, n=len(della_cartella), peso=peso(sum(f["peso"] for f in della_cartella))))
        else:
            righe.append(_("{cartella}: nessun file").format(cartella=nome))
    righe.append(_("In tutto: {n} file, {peso}").format(n=len(files), peso=peso(sum(f["peso"] for f in files))))
    vecchi = cleaner.vecchi(files, giorni, adesso)
    righe.append(_("Piu' vecchi di {durata}: {n} file, {peso}").format(
        durata=cleaner.durata_dei_giorni(giorni), n=len(vecchi), peso=peso(sum(f["peso"] for f in vecchi))))
    return righe


class FinestraPulizia(wx.Dialog):
    """chiedi_conferma(genitore, testo) chiede si' o no; avvisa(genitore,
    testo) dice che cosa non e' andato."""

    def __init__(self, genitore, chiedi_conferma, avvisa):
        super().__init__(genitore, title=_("Pulizia"), style=STILE_ADATTABILE)
        self._chiedi_conferma = chiedi_conferma
        self._avvisa = avvisa
        self.giorni = cleaner.giorni_salvati()
        self.files = []
        pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        sizer.Add(wx.StaticText(pannello, label=_("Situazione dei file")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.riepilogo = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP)
        self.riepilogo.SetName(_("Situazione dei file"))
        sizer.Add(self.riepilogo, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticText(pannello, label=_("File, dal piu' vecchio")), 0, wx.LEFT | wx.RIGHT, 5)
        self.elenco = wx.ListBox(pannello, style=wx.LB_SINGLE)
        self.elenco.SetName(_("File, dal piu' vecchio"))
        sizer.Add(self.elenco, 1, wx.EXPAND | wx.ALL, 5)
        self.pulsante_tutto = wx.Button(pannello, label=_("Elimina &tutto"))
        self.pulsante_vecchi = wx.Button(pannello, label=_("Elimina &piu' vecchi di"))
        domanda = _("Piu' vecchi di:")
        etichetta_dei_giorni = wx.StaticText(pannello, label=domanda)
        self.scelta_dei_giorni = wx.Choice(pannello, choices=[
            _("{durata}, {n} giorni").format(durata=cleaner.durata_in_mesi(mesi), n=cleaner.giorni_di(mesi)) for mesi in cleaner.MESI])
        self.scelta_dei_giorni.SetName(domanda.rstrip(":").rstrip())
        self.scelta_dei_giorni.SetSelection(cleaner.VALORI_DEI_GIORNI.index(self.giorni))
        self.pulsante_date = wx.Button(pannello, label=_("&Ripristina date ai file vecchi"))
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        riga = wx.BoxSizer(wx.HORIZONTAL)
        riga.Add(self.pulsante_tutto, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_vecchi, 0, wx.RIGHT, 5)
        riga.Add(etichetta_dei_giorni, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        riga.Add(self.scelta_dei_giorni, 0, wx.RIGHT, 5)
        sizer.Add(riga, 0, wx.ALL, 5)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        riga.Add(self.pulsante_date, 0, wx.RIGHT, 5)
        riga.Add(chiudi, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        pannello.SetSizer(sizer)
        aspetto.applica_alla_finestra(self)
        self.riepilogo.SetMinSize(wx.Size(-1, self.riepilogo.GetCharHeight() * 7))
        self.elenco.SetMinSize(self.elenco.GetEffectiveMinSize())
        adatta_finestra(self, pannello, (640, 480))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.pulsante_tutto.Bind(wx.EVT_BUTTON, lambda _evento: self.elimina_tutto())
        self.pulsante_vecchi.Bind(wx.EVT_BUTTON, lambda _evento: self.elimina_i_vecchi())
        self.pulsante_date.Bind(wx.EVT_BUTTON, lambda _evento: self.ripristina_le_date())
        self.scelta_dei_giorni.Bind(wx.EVT_CHOICE, lambda _evento: self._giorni_cambiati())
        self.aggiorna(0)
        self.riepilogo.SetInsertionPoint(0)
        self.riepilogo.SetFocus()

    def aggiorna(self, indice=None):
        """Rilegge le cartelle e riscrive situazione ed elenco, con la voce
        scelta a quell'indice, o dove era."""
        if indice is None:
            indice = max(self.elenco.GetSelection(), 0)
        self.files = cleaner.file_accumulati()
        adesso = time.time()
        self.riepilogo.ChangeValue("\n".join(situazione(self.files, self.giorni, adesso)))
        self.elenco.Set([voce(file, adesso) for file in self.files] or [_("Nessun file.")])
        self.elenco.SetSelection(max(0, min(indice, self.elenco.GetCount() - 1)))

    def _giorni_cambiati(self):
        """Il t scelto resta, anche per l'apertura all'avvio."""
        self.giorni = cleaner.VALORI_DEI_GIORNI[self.scelta_dei_giorni.GetSelection()]
        cleaner.salva_giorni(self.giorni)
        self.aggiorna()

    def _nel_cestino(self, files):
        """I file nel cestino; restituisce quelli che non ci sono andati."""
        maniglia = self.GetHandle()
        return [file for file in files if not nel_cestino(file["percorso"], maniglia)]

    def _dopo(self, files, rimasti, indice):
        self.aggiorna(indice)
        if len(rimasti) < len(files):
            suona("eliminati" if len(files) > 1 else "eliminato")
        if rimasti:
            suona("no")
            self._avvisa(self, _("Non sono andati nel cestino: {elenco}.").format(elenco=", ".join(file["nome"] for file in rimasti)))

    def elimina_il_file(self):
        """Canc: il file scelto nel cestino, senza domande."""
        indice = self.elenco.GetSelection()
        if not 0 <= indice < len(self.files):
            suona("no")
            return
        file = self.files[indice]
        self._dopo([file], self._nel_cestino([file]), indice)

    def elimina_tutto(self):
        if not self.files:
            suona("no")
            return
        if len(self.files) == 1:
            domanda = _("Mando nel cestino l'unico file, {peso}?").format(peso=peso(self.files[0]["peso"]))
        else:
            domanda = _("Mando nel cestino tutti i {n} file, {peso}?").format(n=len(self.files), peso=peso(sum(f["peso"] for f in self.files)))
        if not self._chiedi_conferma(self, domanda):
            return
        files = list(self.files)
        self._dopo(files, self._nel_cestino(files), 0)

    def elimina_i_vecchi(self):
        files = cleaner.vecchi(self.files, self.giorni)
        if not files:
            suona("no")
            return
        durata = cleaner.durata_dei_giorni(self.giorni)
        if len(files) == 1:
            domanda = _("Mando nel cestino il file piu' vecchio di {durata}, {peso}?").format(durata=durata, peso=peso(files[0]["peso"]))
        else:
            domanda = _("Mando nel cestino i {n} file piu' vecchi di {durata}, {peso}?").format(
                n=len(files), durata=durata, peso=peso(sum(f["peso"] for f in files)))
        if not self._chiedi_conferma(self, domanda):
            return
        self._dopo(files, self._nel_cestino(files), 0)

    def ripristina_le_date(self):
        """I file vecchi tornano alla data di oggi, e non sono piu' vecchi."""
        files = cleaner.vecchi(self.files, self.giorni)
        if not files:
            suona("no")
            return
        cleaner.ripristina_date(files)
        suona("ripristinate")
        self.aggiorna()

    def _tasto(self, evento):
        if evento.GetEventObject() is self.elenco and evento.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and not evento.HasAnyModifiers():
            self.elimina_il_file()
            return
        evento.Skip()
