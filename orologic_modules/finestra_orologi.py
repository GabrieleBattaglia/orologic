# Orologic: la finestra degli orologi della collezione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""La finestra degli orologi, chiesta da Gabriele il 21 novembre 2026: una
finestra sola per creare, eliminare, modificare e vedere gli orologi della
collezione, che nella finestra prende il posto del sottomenu orologi.

In cima l'elenco degli orologi salvati, ognuno col nome e un sommario di
tempi, tipologie, fasi e allarmi, e in fondo Crea nuovo; Canc chiede se
eliminare l'orologio, Invio su un orologio lo fa vedere, su Crea nuovo apre
i campi. Poi i pulsanti Modifica e Vedi. I campi dell'orologio compaiono
sotto con Crea nuovo o Modifica e spariscono con Salva o Annulla (scelte di
Gabriele nel modulo): il nome, la nota, il tempo uguale per i due colori,
l'elenco delle fasi con Nuova fase, le combo di ore, minuti e secondi e
quelle della tipologia, per il Bianco e, senza la spunta, per il Nero, le
mosse della fase, l'elenco delle tipologie, l'elenco degli allarmi con
Nuovo allarme e le combo del tempo dell'allarme, Salva e Annulla. In fondo
la scheda dell'orologio scelto, senza a capo, col tachimetro, che non si
modifica; Invio su un orologio ci porta. Il pulsante Vedi c'era, e il
collaudo l'ha tolto: la scheda c'e' sempre.

I suoni sono quelli del terminale per gli stessi eventi: il tema di crea
quando si apre un orologio nuovo, quello di vedi, la conferma e la nota
dell'eliminazione, il bip dopo ogni fase e ogni allarme, l'arpeggio del
salvataggio, la nota grave del nome gia' usato. Nuovi, dove il terminale
non aveva l'evento: l'apertura di un orologio da modificare, una fase o un
allarme tolti, i campi chiusi senza salvare.
"""

import copy
import time

import wx
from GBUtils import Acusticator
from GBwx import STILE_ADATTABILE, adatta_finestra, pannello_scorrevole

from . import aspetto, clock, config, controlli, storage, temi, tempo
from .config import _

# Come nel terminale: al piu' quattro fasi e cinque allarmi.
FASI_MASSIME = 4
ALLARMI_MASSIMI = 5
ORE_MASSIME = 23
MOSSE_MASSIME = 200
LUNGHEZZA_DEL_NOME = 60
LUNGHEZZA_DELLA_NOTA = 200
# Un Invio entro tanti secondi dall'apertura, o dall'Invio di prima, e' un
# tasto tenuto giu', o rimandato da NVDA: non fa niente.
GRAZIA_INVIO = 0.65
COLORI = ("white", "black")


def _bip():
    """Il bip delle risposte del terminale, dopo una fase o un allarme."""
    Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])


SUONI = {
    "salvato": lambda: Acusticator(
        ["f7", 0.09, 0, config.VOLUME, "d5", 0.07, 0, config.VOLUME, "p", 0.1, 0, 0, "d5", 0.07, 0, config.VOLUME, "f7", 0.09, 0, config.VOLUME]
    ),
    "nome_usato": lambda: Acusticator(["a3", 1, 0, config.VOLUME], kind=2),
    "elimina": lambda: Acusticator(["b4", 0.02, 0, config.VOLUME, "d4", 0.2, 0, config.VOLUME]),
    "eliminato": lambda: Acusticator(["c4", 0.025, 0, config.VOLUME]),
    # Nuovi: l'orologio da modificare, il tema di crea rovesciato, da
    # destra a sinistra; una fase o un allarme tolti, due note che
    # scendono; i campi chiusi senza salvare; il no, quello del terminale.
    "modifica": lambda: Acusticator(
        [900.0, 0.05, 1, config.VOLUME, "p", 0.05, 0, 0, 1000.0, 0.05, -1, config.VOLUME], kind=1, adsr=[0, 0, 100, 0]
    ),
    "tolto": lambda: Acusticator(["g4", 0.04, 0, config.VOLUME, "c4", 0.06, 0, config.VOLUME], kind=1),
    "annullato": lambda: Acusticator(["e5", 0.04, 0, config.VOLUME, "c5", 0.04, 0, config.VOLUME, "a4", 0.06, 0, config.VOLUME], kind=1),
    "no": lambda: Acusticator(["e3", 0.2, 0, config.VOLUME], kind=2),
}


def suona(evento):
    """I suoni della finestra; le prove li sostituiscono."""
    if evento in ("crea", "vedi"):
        temi.suona(evento)
    elif evento == "bip":
        _bip()
    else:
        SUONI[evento]()


def _premuto_invio(evento):
    return evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not evento.HasAnyModifiers()


def _premuto_canc(evento):
    return evento.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and not evento.HasAnyModifiers()


def _senza_due_punti(testo):
    return testo.rstrip().rstrip(":").rstrip()


def fase_nuova(precedente=None):
    """Una fase nuova: quella di prima ripetuta, o cinque minuti senza
    incremento, della tipologia predefinita."""
    if precedente is not None:
        fase = copy.deepcopy(precedente)
        fase["moves"] = 0
        return fase
    fase = {"white_time": 300, "black_time": 300, "moves": 0, "tipo": controlli.PREDEFINITO}
    controlli.completa(fase)
    return fase


def orologio_nuovo():
    return {"name": "", "note": "", "same_time": True, "phases": [fase_nuova()], "alarms": []}


def sommario(orologio):
    """La voce dell'elenco: il nome e un sommario di tempi, tipologie, fasi
    e allarmi, con i testi della scheda del terminale."""
    stesso = orologio.get("same_time", True)
    fasi = orologio.get("phases", [])
    parti = []
    for numero, fase in enumerate(fasi, 1):
        if stesso:
            tempi = controlli.sommario_fase(fase, "white")
        else:
            tempi = _("bianco {b}, nero {n}").format(b=controlli.sommario_fase(fase, "white"), n=controlli.sommario_fase(fase, "black"))
        testo = _("  fase {n}: {t}").format(n=numero, t=tempi).strip() if len(fasi) > 1 else tempi
        if fase.get("moves") and numero < len(fasi):
            testo += ", " + _("  per: {n} mosse").format(n=fase["moves"]).strip()
        parti.append(testo)
    allarmi = orologio.get("alarms") or []
    if allarmi:
        parti.append(_("  allarmi a: {elenco}").format(elenco=", ".join(tempo.parlato(a) for a in allarmi)).strip())
    else:
        parti.append(_("  nessun allarme").strip())
    return _("{nome}: {sommario}").format(nome=orologio["name"], sommario="; ".join(parti))


class _Campo:
    """Un'etichetta e una combo di numeri, da minimo a massimo."""

    def __init__(self, genitore, sizer, minimo, massimo):
        self.minimo = minimo
        self.etichetta = wx.StaticText(genitore)
        self.scelta = wx.Choice(genitore, choices=[str(n) for n in range(minimo, massimo + 1)])
        self.scelta.SetSelection(0)
        riga = wx.BoxSizer(wx.HORIZONTAL)
        riga.Add(self.etichetta, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        riga.Add(self.scelta, 0)
        self.riga = riga
        sizer.Add(riga, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)

    def nome(self, testo):
        self.etichetta.SetLabel(testo)
        self.scelta.SetName(_senza_due_punti(testo))

    @property
    def valore(self):
        return self.minimo + max(self.scelta.GetSelection(), 0)

    @valore.setter
    def valore(self, numero):
        indice = int(numero) - self.minimo
        self.scelta.SetSelection(max(0, min(indice, self.scelta.GetCount() - 1)))

    def mostra(self, si):
        self.etichetta.Show(si)
        self.scelta.Show(si)


class FinestraOrologi(wx.Dialog):
    """La finestra degli orologi; chiedi_conferma(genitore, testo) chiede si'
    o no, avvisa(genitore, testo) dice che cosa non va."""

    def __init__(self, genitore, chiedi_conferma, avvisa):
        super().__init__(genitore, title=_("Orologi"), style=STILE_ADATTABILE)
        self._chiedi_conferma = chiedi_conferma
        self._avvisa = avvisa
        self.orologi = storage.LoadDB().get("clocks", [])
        # L'orologio nei campi: None se i campi sono chiusi; in_modifica e'
        # l'indice dell'orologio salvato, o None per uno nuovo.
        self.bozza = None
        self.in_modifica = None
        self._caricando = False
        self.pannello = pannello = pannello_scorrevole(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # L'ordine di creazione e' quello del Tab, e ogni controllo prende
        # il nome del testo creato subito prima.
        sizer.Add(wx.StaticText(pannello, label=_("Orologi salvati")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.elenco = wx.ListBox(pannello, style=wx.LB_SINGLE)
        self.elenco.SetName(_("Orologi salvati"))
        sizer.Add(self.elenco, 1, wx.EXPAND | wx.ALL, 5)
        pulsanti = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_modifica = wx.Button(pannello, label=_("&Modifica"))
        pulsanti.Add(self.pulsante_modifica, 0)
        sizer.Add(pulsanti, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.editor = wx.Panel(pannello)
        self._crea_i_campi(self.editor)
        sizer.Add(self.editor, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(pannello, label=_("Scheda dell'orologio")), 0, wx.LEFT | wx.RIGHT, 5)
        # Senza a capo: ogni riga della scheda resta una riga, intera, per
        # NVDA e per il display braille (collaudo della finestra).
        self.scheda = wx.TextCtrl(pannello, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP)
        self.scheda.SetName(_("Scheda dell'orologio"))
        sizer.Add(self.scheda, 1, wx.EXPAND | wx.ALL, 5)
        chiudi = wx.Button(pannello, wx.ID_CANCEL, _("Chiudi"))
        sizer.Add(chiudi, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        pannello.SetSizer(sizer)
        self.editor.Hide()
        aspetto.applica_alla_finestra(self)
        adatta_finestra(self, pannello, (640, 480))
        self.Maximize()
        self.Bind(wx.EVT_CHAR_HOOK, self._tasto)
        self.elenco.Bind(wx.EVT_LISTBOX, lambda _evento: self._mostra_la_scheda())
        self.pulsante_modifica.Bind(wx.EVT_BUTTON, lambda _evento: self.modifica())
        self._riempi_l_elenco(0)
        self.ultimo_invio = time.monotonic()
        self.elenco.SetFocus()

    # I campi dell'orologio.

    def _crea_i_campi(self, editor):
        sizer = wx.BoxSizer(wx.VERTICAL)
        domanda = _("Nome dell'orologio: ")
        sizer.Add(wx.StaticText(editor, label=domanda.strip()), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.nome = wx.TextCtrl(editor)
        self.nome.SetMaxLength(LUNGHEZZA_DEL_NOME)
        self.nome.SetName(_senza_due_punti(domanda))
        sizer.Add(self.nome, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        domanda = _("Inserisci una nota per l'orologio (opzionale): ")
        sizer.Add(wx.StaticText(editor, label=domanda.strip()), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.nota = wx.TextCtrl(editor)
        self.nota.SetMaxLength(LUNGHEZZA_DELLA_NOTA)
        self.nota.SetName(_senza_due_punti(domanda))
        sizer.Add(self.nota, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        self.stesso_tempo = wx.CheckBox(editor, label=_("  Tempo uguale per i due colori").strip())
        sizer.Add(self.stesso_tempo, 0, wx.ALL, 5)
        sizer.Add(wx.StaticText(editor, label=_("Fasi")), 0, wx.LEFT | wx.RIGHT, 5)
        self.fasi = wx.ListBox(editor, style=wx.LB_SINGLE)
        self.fasi.SetName(_("Fasi"))
        sizer.Add(self.fasi, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        # Per ogni colore ore, minuti e secondi, poi i valori di tutte le
        # tipologie: si mostrano quelli della tipologia della fase.
        self.gruppi = {}
        for colore in COLORI:
            campi = {
                "ore": _Campo(editor, sizer, 0, ORE_MASSIME),
                "minuti": _Campo(editor, sizer, 0, 59),
                "secondi": _Campo(editor, sizer, 0, 59),
            }
            for parametro in controlli.tutti_i_parametri():
                campi[parametro.chiave] = _Campo(editor, sizer, parametro.minimo, parametro.massimo)
            self.gruppi[colore] = campi
        self.mosse = _Campo(editor, sizer, 0, MOSSE_MASSIME)
        self.mosse.nome(_("Mosse della fase, 0 per tutte le restanti:"))
        sizer.Add(wx.StaticText(editor, label=_("Tipologia")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.tipologie = wx.ListBox(editor, style=wx.LB_SINGLE, choices=[controlli.voce(tipo) for tipo in controlli.tipi()])
        self.tipologie.SetName(_("Tipologia"))
        sizer.Add(self.tipologie, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer.Add(wx.StaticText(editor, label=_("Allarmi")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.allarmi = wx.ListBox(editor, style=wx.LB_SINGLE)
        self.allarmi.SetName(_("Allarmi"))
        sizer.Add(self.allarmi, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        # Il tempo dell'allarme scelto, con combo di soli numeri come i
        # tempi delle fasi (collaudo della finestra).
        self.allarme = {
            "ore": _Campo(editor, sizer, 0, ORE_MASSIME),
            "minuti": _Campo(editor, sizer, 0, 59),
            "secondi": _Campo(editor, sizer, 0, 59),
        }
        self.allarme["ore"].nome(_("Ore dell'allarme"))
        self.allarme["minuti"].nome(_("Minuti dell'allarme"))
        self.allarme["secondi"].nome(_("Secondi dell'allarme"))
        riga = wx.BoxSizer(wx.HORIZONTAL)
        self.pulsante_salva = wx.Button(editor, label=_("&Salva"))
        self.pulsante_annulla = wx.Button(editor, label=_("&Annulla"))
        riga.Add(self.pulsante_salva, 0, wx.RIGHT, 5)
        riga.Add(self.pulsante_annulla, 0)
        sizer.Add(riga, 0, wx.ALL, 5)
        editor.SetSizer(sizer)
        self.stesso_tempo.Bind(wx.EVT_CHECKBOX, lambda _evento: self._stesso_tempo_cambiato())
        self.fasi.Bind(wx.EVT_LISTBOX, lambda _evento: self._carica_la_fase())
        self.tipologie.Bind(wx.EVT_LISTBOX, lambda _evento: self._tipologia_cambiata())
        self.allarmi.Bind(wx.EVT_LISTBOX, lambda _evento: self._carica_l_allarme())
        for campi in self.gruppi.values():
            for campo in campi.values():
                campo.scelta.Bind(wx.EVT_CHOICE, lambda _evento: self._salva_la_fase())
        self.mosse.scelta.Bind(wx.EVT_CHOICE, lambda _evento: self._salva_la_fase())
        for campo in self.allarme.values():
            campo.scelta.Bind(wx.EVT_CHOICE, lambda _evento: self._salva_l_allarme())
        self.pulsante_salva.Bind(wx.EVT_BUTTON, lambda _evento: self.salva())
        self.pulsante_annulla.Bind(wx.EVT_BUTTON, lambda _evento: self.annulla())

    # L'elenco e la scheda.

    def _riempi_l_elenco(self, indice):
        self.orologi = storage.LoadDB().get("clocks", [])
        self.elenco.Set([sommario(orologio) for orologio in self.orologi] + [_("Crea nuovo")])
        self.elenco.SetSelection(max(0, min(indice, self.elenco.GetCount() - 1)))
        self._mostra_la_scheda()

    def scelto(self):
        """L'indice dell'orologio scelto nell'elenco, o None su Crea nuovo."""
        indice = self.elenco.GetSelection()
        return indice if 0 <= indice < len(self.orologi) else None

    def _mostra_la_scheda(self):
        indice = self.scelto()
        righe = [] if indice is None else clock.descrivi_orologio(indice + 1, self.orologi[indice])
        self.scheda.ChangeValue("\n".join(riga.strip() for riga in righe))

    def vedi(self):
        if self.scelto() is None:
            suona("no")
            return
        suona("vedi")
        self._mostra_la_scheda()
        self.scheda.SetInsertionPoint(0)
        self.scheda.SetFocus()

    def elimina(self):
        indice = self.scelto()
        if indice is None:
            suona("no")
            return
        nome = self.orologi[indice]["name"]
        suona("elimina")
        if not self._chiedi_conferma(self, _("Sei sicuro di voler eliminare {name}?").format(name=nome)):
            return

        def togli(db):
            db["clocks"] = [c for c in db.get("clocks", []) if c.get("name") != nome]

        storage.UpdateDB(togli)
        suona("eliminato")
        self._riempi_l_elenco(indice)
        self.elenco.SetFocus()

    # I campi: aperti, riempiti, chiusi.

    def crea(self):
        suona("crea")
        self._apri(orologio_nuovo(), None)

    def modifica(self):
        indice = self.scelto()
        if indice is None:
            self.crea()
            return
        suona("modifica")
        orologio = copy.deepcopy(self.orologi[indice])
        for fase in orologio["phases"]:
            controlli.completa(fase)
        self._apri(orologio, indice)

    def _apri(self, orologio, indice):
        self.bozza = orologio
        self.in_modifica = indice
        self._caricando = True
        self.nome.ChangeValue(orologio["name"])
        self.nota.ChangeValue(orologio.get("note", ""))
        self.stesso_tempo.SetValue(orologio.get("same_time", True))
        self._caricando = False
        self._riempi_le_fasi(0)
        self._riempi_gli_allarmi(0)
        self.editor.Show()
        self._rifai()
        self.nome.SetFocus()

    def _chiudi_i_campi(self):
        self.bozza = None
        self.in_modifica = None
        self.editor.Hide()
        self._rifai()
        self.elenco.SetFocus()

    def _rifai(self):
        self.editor.Layout()
        self.pannello.Layout()
        self.pannello.FitInside()

    def annulla(self):
        suona("annullato")
        self._chiudi_i_campi()

    # Le fasi.

    def _riempi_le_fasi(self, indice):
        voci = [_("Fase {n}").format(n=numero) for numero in range(1, len(self.bozza["phases"]) + 1)]
        if len(self.bozza["phases"]) < FASI_MASSIME:
            voci.append(_("Nuova fase"))
        self.fasi.Set(voci)
        self.fasi.SetSelection(max(0, min(indice, len(self.bozza["phases"]) - 1)))
        self._carica_la_fase()

    def fase_scelta(self):
        indice = self.fasi.GetSelection()
        fasi = self.bozza["phases"]
        return indice if 0 <= indice < len(fasi) else len(fasi) - 1

    def _carica_la_fase(self):
        """I valori della fase scelta nelle combo, con quelli della sua
        tipologia, e la tipologia selezionata nel suo elenco."""
        if self.bozza is None:
            return
        fase = self.bozza["phases"][self.fase_scelta()]
        controlli.completa(fase)
        self._caricando = True
        for colore in COLORI:
            campi = self.gruppi[colore]
            ore, resto = divmod(int(fase[f"{colore}_time"]), 3600)
            minuti, secondi = divmod(resto, 60)
            campi["ore"].valore = ore
            campi["minuti"].valore = minuti
            campi["secondi"].valore = secondi
            for parametro in controlli.tutti_i_parametri():
                campi[parametro.chiave].valore = controlli.valore(fase, parametro.chiave, colore)
        self.mosse.valore = fase.get("moves", 0)
        self.tipologie.SetSelection(controlli.indice(fase["tipo"]))
        self._caricando = False
        self._aggiorna_i_campi()

    def _aggiorna_i_campi(self):
        """Nomi e presenza delle combo: quelle del Nero solo senza la spunta,
        e di ogni tipologia solo i suoi valori."""
        if self.bozza is None:
            return
        stesso = self.stesso_tempo.GetValue()
        fase = self.bozza["phases"][self.fase_scelta()]
        tipo = controlli.tipo(fase["tipo"])
        for colore in COLORI:
            campi = self.gruppi[colore]
            visibile = colore == "white" or not stesso

            def nome(testo, colore=colore):
                if stesso:
                    return testo
                if colore == "white":
                    return _("{campo} del Bianco").format(campo=testo)
                return _("{campo} del Nero").format(campo=testo)

            campi["ore"].nome(nome(_("Ore")))
            campi["minuti"].nome(nome(_("Minuti")))
            campi["secondi"].nome(nome(_("Secondi")))
            campi["ore"].mostra(visibile)
            campi["minuti"].mostra(visibile)
            campi["secondi"].mostra(visibile)
            usati = {parametro.chiave for parametro in tipo.parametri}
            for parametro in controlli.tutti_i_parametri():
                campi[parametro.chiave].nome(nome(parametro.etichetta))
                campi[parametro.chiave].mostra(visibile and parametro.chiave in usati)
        self._rifai()

    def _salva_la_fase(self):
        """Le combo nella fase scelta; con la spunta il Nero ha i tempi del Bianco."""
        if self.bozza is None or self._caricando:
            return
        fase = self.bozza["phases"][self.fase_scelta()]
        stesso = self.stesso_tempo.GetValue()
        for colore in COLORI:
            campi = self.gruppi["white" if stesso else colore]
            fase[f"{colore}_time"] = campi["ore"].valore * 3600 + campi["minuti"].valore * 60 + campi["secondi"].valore
            for parametro in controlli.tutti_i_parametri():
                fase[f"{colore}_{parametro.chiave}"] = campi[parametro.chiave].valore
        fase["moves"] = self.mosse.valore

    def _tipologia_cambiata(self):
        if self.bozza is None or self._caricando:
            return
        fase = self.bozza["phases"][self.fase_scelta()]
        fase["tipo"] = controlli.tipi()[self.tipologie.GetSelection()].codice
        controlli.completa(fase)
        self._aggiorna_i_campi()

    def _stesso_tempo_cambiato(self):
        if self.bozza is None:
            return
        self.bozza["same_time"] = self.stesso_tempo.GetValue()
        if self.bozza["same_time"]:
            # Il Nero prende i tempi del Bianco in tutte le fasi.
            for fase in self.bozza["phases"]:
                for chiave in list(fase):
                    if chiave.startswith("white_"):
                        fase["black_" + chiave[len("white_"):]] = fase[chiave]
        self._carica_la_fase()

    def aggiungi_una_fase(self):
        if len(self.bozza["phases"]) >= FASI_MASSIME:
            suona("no")
            return
        self.bozza["phases"].append(fase_nuova(self.bozza["phases"][-1]))
        _bip()
        self._riempi_le_fasi(len(self.bozza["phases"]) - 1)

    def togli_la_fase(self):
        indice = self.fasi.GetSelection()
        if not 0 < indice < len(self.bozza["phases"]):
            suona("no")
            return
        del self.bozza["phases"][indice]
        suona("tolto")
        self._riempi_le_fasi(indice)

    # Gli allarmi.

    def _riempi_gli_allarmi(self, indice):
        allarmi = self.bozza["alarms"]
        voci = [_("Allarme {n}: {t}").format(n=numero, t=tempo.parlato(secondi)) for numero, secondi in enumerate(allarmi, 1)]
        if len(allarmi) < ALLARMI_MASSIMI:
            voci.append(_("Nuovo allarme"))
        self.allarmi.Set(voci)
        self.allarmi.SetSelection(max(0, min(indice, self.allarmi.GetCount() - 1)))
        self._carica_l_allarme()

    def _carica_l_allarme(self):
        """Il tempo dell'allarme scelto nelle sue combo; su Nuovo allarme le
        combo non ci sono."""
        indice = self.allarmi.GetSelection()
        allarmi = self.bozza["alarms"] if self.bozza else []
        scelto = 0 <= indice < len(allarmi)
        if scelto:
            ore, resto = divmod(int(allarmi[indice]), 3600)
            minuti, secondi = divmod(resto, 60)
            self._caricando = True
            self.allarme["ore"].valore = ore
            self.allarme["minuti"].valore = minuti
            self.allarme["secondi"].valore = secondi
            self._caricando = False
        for campo in self.allarme.values():
            campo.mostra(scelto)
        self._rifai()

    def _salva_l_allarme(self):
        """Le combo nell'allarme scelto, e la sua voce nell'elenco."""
        indice = self.allarmi.GetSelection()
        if self.bozza is None or self._caricando or not 0 <= indice < len(self.bozza["alarms"]):
            return
        self.bozza["alarms"][indice] = self.allarme["ore"].valore * 3600 + self.allarme["minuti"].valore * 60 + self.allarme["secondi"].valore
        self.allarmi.SetString(indice, self._voce_dell_allarme(indice))

    def _voce_dell_allarme(self, indice):
        return _("Allarme {n}: {t}").format(n=indice + 1, t=tempo.parlato(self.bozza["alarms"][indice]))

    def aggiungi_un_allarme(self):
        """Invio su Nuovo allarme: l'allarme nasce a un minuto, e il fuoco va
        ai minuti del suo tempo."""
        allarmi = self.bozza["alarms"]
        if len(allarmi) >= ALLARMI_MASSIMI:
            suona("no")
            return
        allarmi.append(60)
        self._riempi_gli_allarmi(len(allarmi) - 1)
        self.allarme["minuti"].scelta.SetFocus()

    def errori_degli_allarmi(self, solo=None):
        """Che cosa non va negli allarmi, o nel solo allarme con quell'indice:
        il minimo di un secondo, due allarmi allo stesso tempo, un allarme
        che non sta sotto il tempo totale di nessuno dei due colori."""
        self._salva_la_fase()
        allarmi = self.bozza["alarms"]
        fasi = self.bozza["phases"]
        colori = ("white",) if self.stesso_tempo.GetValue() else COLORI
        totale = max(controlli.tempo_totale(fasi, colore) for colore in colori)
        errori = []
        for indice, secondi in enumerate(allarmi):
            if solo is not None and indice != solo:
                continue
            numero = indice + 1
            if secondi < clock.TEMPO_MINIMO_ALLARME:
                errori.append(_("Allarme {n}: il minimo e' {quanto}.").format(n=numero, quanto=tempo.parlato(clock.TEMPO_MINIMO_ALLARME)))
            elif secondi in allarmi[:indice] or (solo is not None and allarmi.count(secondi) > 1):
                errori.append(_("Allarme {n}: c'e' gia' un allarme a {t}.").format(n=numero, t=tempo.parlato(secondi)))
            elif secondi >= totale:
                errori.append(_("Allarme {n}: {t} non e' sotto il tempo totale dell'orologio, {totale}.").format(
                    n=numero, t=tempo.parlato(secondi), totale=tempo.parlato(totale)))
        return errori

    def conferma_l_allarme(self):
        """Invio nelle combo dell'allarme: se il tempo va bene, il bip del
        terminale e il fuoco torna all'elenco; se no, che cosa non va."""
        indice = self.allarmi.GetSelection()
        if not 0 <= indice < len(self.bozza["alarms"]):
            suona("no")
            return
        errori = self.errori_degli_allarmi(indice)
        if errori:
            suona("nome_usato")
            self._avvisa(self, "\n".join(errori))
            return
        _bip()
        self.allarmi.SetFocus()

    def togli_l_allarme(self):
        indice = self.allarmi.GetSelection()
        if not 0 <= indice < len(self.bozza["alarms"]):
            suona("no")
            return
        del self.bozza["alarms"][indice]
        suona("tolto")
        self._riempi_gli_allarmi(indice)

    # Il salvataggio.

    def errori(self):
        """Che cosa impedisce di salvare la bozza, come frasi, vuote se
        niente: il nome, i tempi delle fasi, le mosse delle fasi prima
        dell'ultima, i valori delle tipologie."""
        errori = []
        nome = " ".join(self.nome.GetValue().split())
        if not nome:
            errori.append(_("Scrivi il nome dell'orologio."))
        altri = [orologio["name"] for indice, orologio in enumerate(self.orologi) if indice != self.in_modifica]
        if nome in altri:
            errori.append(_("Un orologio con questo nome esiste gia'."))
        fasi = self.bozza["phases"]
        colori = ("white",) if self.stesso_tempo.GetValue() else COLORI
        for numero, fase in enumerate(fasi, 1):
            for colore in colori:
                errori += controlli.errori_della_fase(fase, colore, numero)
            if numero < len(fasi) and not fase.get("moves"):
                errori.append(_("La fase {n} ha 0 mosse: la fase dopo non comincerebbe mai.").format(n=numero))
        errori += controlli.errori_delle_fasi(fasi)
        errori += self.errori_degli_allarmi()
        return errori

    def salva(self):
        self._salva_la_fase()
        errori = self.errori()
        if errori:
            suona("nome_usato")
            self._avvisa(self, "\n".join(errori))
            return
        orologio = self.bozza
        orologio["name"] = " ".join(self.nome.GetValue().split())
        orologio["note"] = self.nota.GetValue().strip()
        orologio["same_time"] = self.stesso_tempo.GetValue()
        indice = self.in_modifica
        if indice is None:
            nuovo = clock.ClockConfig(orologio["name"], orologio["same_time"], orologio["phases"], orologio["alarms"], orologio["note"]).to_dict()

            def scrivi(db):
                db.setdefault("clocks", []).append(nuovo)

            posizione = len(self.orologi)
        else:
            # Data di creazione e tachimetro restano quelli dell'orologio.
            vecchio_nome = self.orologi[indice]["name"]

            def scrivi(db):
                for salvato in db.get("clocks", []):
                    if salvato.get("name") == vecchio_nome:
                        for chiave in ("name", "note", "same_time", "phases", "alarms"):
                            salvato[chiave] = copy.deepcopy(orologio[chiave])
                        return

            posizione = indice
        storage.UpdateDB(scrivi)
        suona("salvato")
        self.bozza = None
        self.in_modifica = None
        self.editor.Hide()
        self._riempi_l_elenco(posizione)
        self._rifai()
        self.elenco.SetFocus()

    # I tasti.

    def _tasto(self, evento):
        oggetto = evento.GetEventObject()
        if evento.GetKeyCode() == wx.WXK_ESCAPE and not evento.HasAnyModifiers() and self.bozza is not None:
            # Esc nei campi li chiude senza salvare; fuori chiude la finestra.
            self.annulla()
            return
        if _premuto_canc(evento):
            azioni = {self.elenco: self.elimina, self.fasi: self.togli_la_fase, self.allarmi: self.togli_l_allarme}
            if oggetto in azioni:
                azioni[oggetto]()
                return
        if _premuto_invio(evento):
            adesso = time.monotonic()
            precedente, self.ultimo_invio = self.ultimo_invio, adesso
            if evento.IsAutoRepeat() or adesso - precedente < GRAZIA_INVIO:
                return
            if oggetto is self.elenco:
                if self.scelto() is None:
                    self.crea()
                else:
                    self.vedi()
                return
            if oggetto is self.fasi:
                if self.fasi.GetSelection() >= len(self.bozza["phases"]):
                    self.aggiungi_una_fase()
                return
            if oggetto is self.allarmi:
                if self.allarmi.GetSelection() >= len(self.bozza["alarms"]):
                    self.aggiungi_un_allarme()
                else:
                    self.allarme["minuti"].scelta.SetFocus()
                return
            if any(oggetto is campo.scelta for campo in self.allarme.values()):
                self.conferma_l_allarme()
                return
            if not isinstance(oggetto, wx.Button):
                # Nei campi Invio non salva per sbaglio: si salva con Salva.
                return
        evento.Skip()
