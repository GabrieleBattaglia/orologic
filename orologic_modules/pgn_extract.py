# Orologic: pgn-extract, lo strumento di David J. Barnes per gli archivi PGN.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""pgn-extract dentro Orologic, la voce PGN gestione archivi della finestra
(issue 74, piano di Gabriele in PE-Piano.txt, 23 e 24 novembre 2026).

pgn-extract, pe per brevita', e' di David J. Barnes, GPL 3 come Orologic, e
David ha dato il suo consenso il 23 novembre 2026. Non sta nel repository:
lo scaricano le copie degli utenti dal suo sito, con eco.pgn, la licenza
COPYING e la guida help.html, nella cartella pgn-extract accanto al
programma. In alternativa l'utente indica dov'e' il suo, e il percorso si
salva nel database.

Qui c'e' tutto quello che non e' finestra:
  i parametri, dall'elenco che pe stampa con -h, uniti alla tabella di
    parametri_pe.py, che dice che valore vuole ciascuno; un parametro che la
    tabella non conosce compare lo stesso, col valore senza controllo;
  la guida, help.html divisa nelle sue sezioni, per leggere solo quella del
    parametro;
  la validazione dei valori, con la motivazione;
  il comando, nell'ordine giusto, che decide Orologic;
  il lavoro di pe in un filo, con l'uscita completa in un file della
    cartella txt e il riassunto, perche' pe scrive una riga per partita;
  lo scaricamento e l'aggiornamento dal sito.
"""

import dataclasses
import filecmp
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

from . import config, rete, storage
from .config import _

SITO = "https://www.cs.kent.ac.uk/people/staff/djb/pgn-extract/"
ESEGUIBILE = "pgn-extract.exe"
CARTELLA = "pgn-extract"
GUIDA = "help.html"
# I file che si scaricano insieme, e che un aggiornamento riscrive tutti:
# eco.pgn puo' essere piu' ricco del nostro (Gabriele, 24 novembre 2026).
FILE_DEL_SITO = (ESEGUIBILE, "eco.pgn", "COPYING", GUIDA)
# La chiave del database col percorso indicato a mano.
CHIAVE_DEL_PERCORSO = "pgn_extract_path"
# Quanto si aspetta pe per --version e -h, e il sito.
ATTESA_BREVE = 10
ATTESA_DEL_SITO = 20
ATTESA_DELLO_SCARICAMENTO = 120
# Ogni quanto il filo dice a che punto e', in secondi.
INTERVALLO_DELL_AVANZAMENTO = 0.5
# Quanti esempi per tipo di messaggio entrano nel riassunto.
ESEMPI_PER_TIPO = 3
# Il segnaposto della voce Altro file sorgente fra i parametri.
ALTRO_SORGENTE = "altro sorgente"


def _senza_finestra():
    """pe e' un programma da console: senza questa bandiera aprirebbe una
    finestra nera a ogni chiamata."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def cartella():
    """La cartella di pe accanto al programma."""
    return config.percorso_salvataggio(CARTELLA)


def nella_cartella(nome):
    return os.path.join(cartella(), nome)


def eseguibile():
    """Il percorso di pe: quello della cartella di Orologic, se c'e', poi
    quello indicato a mano; None se non c'e' nessuno dei due."""
    nostro = nella_cartella(ESEGUIBILE)
    if os.path.isfile(nostro):
        return nostro
    indicato = storage.LoadDB().get(CHIAVE_DEL_PERCORSO)
    if indicato and os.path.isfile(indicato):
        return indicato
    return None


def ricorda_il_percorso(percorso):
    """Il pe indicato a mano, nel database."""

    def aggiorna(db):
        db[CHIAVE_DEL_PERCORSO] = percorso

    storage.UpdateDB(aggiorna)


def _esegui_breve(percorso, argomento):
    """L'uscita di pe con un solo argomento, stdout e stderr insieme, o None
    se non parte."""
    try:
        finito = subprocess.run(
            [percorso, argomento],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=ATTESA_BREVE,
            check=False,
            **_senza_finestra(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _decodifica(finito.stdout) + _decodifica(finito.stderr)


def _decodifica(dati):
    """I byte di pe: UTF-8, o Latin-1 per i nomi degli archivi vecchi."""
    try:
        return dati.decode("utf-8")
    except UnicodeDecodeError:
        return dati.decode("latin-1")


def versione(percorso):
    """La versione di pe, come 26-04, o None se non risponde."""
    uscita = _esegui_breve(percorso, "--version")
    if not uscita:
        return None
    trovata = re.search(r"v?(\d+-\d+)", uscita)
    return trovata.group(1) if trovata else None


def come_numeri(versione_scritta):
    """26-04 come (26, 4), per confrontare le versioni."""
    return tuple(int(numero) for numero in re.findall(r"\d+", versione_scritta or ""))


def testo_dell_aiuto(percorso):
    """L'elenco dei parametri che pe stampa con -h, o None."""
    return _esegui_breve(percorso, "-h")


# I parametri.


@dataclasses.dataclass
class Parametro:
    """Un parametro di pe, come lo vede la finestra. riga e' la spiegazione
    di pe -h, in inglese; conosciuto e' vero se la tabella lo descrive."""

    voce: str
    opzione: str
    prefisso: str
    valore: object = None
    separato: bool = False
    facoltativo: bool = False
    ripetibile: bool = False
    ancora: object = None
    alias: tuple = ()
    riga: str = ""
    esempio: object = None
    regola: object = None
    minimo: object = None
    massimo: object = None
    scelte: tuple = ()
    conosciuto: bool = True

    @property
    def etichetta(self):
        """La voce fra i disponibili: il parametro, gli altri nomi e la
        spiegazione."""
        nomi = ", ".join((self.voce, *self.alias))
        return f"{nomi}: {self.riga}" if self.riga else nomi

    @property
    def vuole_un_valore(self):
        return self.valore is not None


def voci_dell_aiuto(testo):
    """L'elenco di pe -h come [(opzione, sintassi, spiegazione)], nell'ordine,
    con le righe rientrate unite alla voce prima. Le brevi sono -X seguito
    dalla sintassi e da --, le lunghe --nome, la sintassi e un trattino."""
    voci = []
    for riga in (testo or "").splitlines():
        if not riga.strip():
            continue
        if riga.startswith("--"):
            sinistra, trovato, spiegazione = riga.partition(" - ")
            if not trovato:
                continue
            pezzi = sinistra.split(None, 1)
            voci.append([pezzi[0], pezzi[1].strip() if len(pezzi) > 1 else "", spiegazione.strip()])
        elif riga.startswith("-") and len(riga) > 1:
            sinistra, trovato, spiegazione = riga.partition(" -- ")
            if not trovato:
                continue
            voci.append([sinistra[:2], sinistra[2:].strip(), spiegazione.strip()])
        elif riga[0].isspace() and voci:
            voci[-1][2] = f"{voci[-1][2]} {riga.strip()}".strip()
    return [tuple(voce) for voce in voci]


def _rimando(spiegazione):
    """L'opzione a cui rimanda una riga come see -C, o None."""
    trovato = re.fullmatch(r"see (-{1,2}[^\s;,.]+)\.?", spiegazione.strip())
    return trovato.group(1) if trovato else None


def _tabella():
    """La tabella di parametri_pe.py, o vuota se manca."""
    try:
        from . import parametri_pe
    except ImportError:
        return ()
    return parametri_pe.PARAMETRI


def _dalla_tabella(voce, riga):
    return Parametro(
        voce=voce["voce"],
        opzione=voce["opzione"],
        prefisso=voce.get("prefisso", voce["voce"]),
        valore=voce.get("valore"),
        separato=bool(voce.get("separato")),
        facoltativo=bool(voce.get("facoltativo")),
        ripetibile=bool(voce.get("ripetibile")),
        ancora=voce.get("ancora"),
        alias=tuple(voce.get("alias") or ()),
        riga=voce.get("descrizione") or riga,
        esempio=voce.get("esempio"),
        regola=voce.get("regola"),
        minimo=voce.get("minimo"),
        massimo=voce.get("massimo"),
        scelte=tuple(voce.get("scelte") or ()),
    )


def _sconosciuto(opzione, sintassi, spiegazione):
    """Un parametro che la tabella non conosce: vuole un valore se pe -h gli
    scrive una sintassi, attaccato per le brevi e separato per le lunghe, e
    facoltativo se la sintassi e' fra parentesi quadre."""
    return Parametro(
        voce=opzione,
        opzione=opzione,
        prefisso=opzione,
        valore="testo" if sintassi else None,
        separato=opzione.startswith("--"),
        facoltativo=sintassi.startswith("["),
        riga=spiegazione,
        conosciuto=False,
    )


def altro_sorgente():
    """La voce Altro file sorgente: un archivio in piu' da leggere insieme al
    primo, per unirli; si ripete, e il file va in fondo al comando."""
    return Parametro(
        voce=_("Altro file sorgente"),
        opzione=ALTRO_SORGENTE,
        prefisso="",
        valore="file",
        ripetibile=True,
        riga=_("un archivio in piu' da leggere insieme al primo, per unirli."),
    )


def parametri(testo):
    """I parametri da mostrare, dall'elenco di pe -h: prima Altro file
    sorgente, poi quelli della tabella nell'ordine di pe, con le varianti
    separate, come -Tw e -Tb, e senza quelli che Orologic gestisce da se';
    i rimandi, come --nocomments - see -C, sono gli altri nomi della voce;
    per ultimi gli sconosciuti, con la loro riga."""
    voci = voci_dell_aiuto(testo)
    righe = {opzione: spiegazione for opzione, _sintassi, spiegazione in voci}
    tabella = _tabella()
    per_opzione = {}
    nomi_della_tabella = set()
    for voce in tabella:
        per_opzione.setdefault(voce["opzione"], []).append(voce)
        nomi_della_tabella.update((voce["opzione"], voce["voce"], *(voce.get("alias") or ())))
    elenco = [altro_sorgente()]
    for opzione, sintassi, spiegazione in voci:
        if opzione in per_opzione:
            for voce in per_opzione[opzione]:
                if not voce.get("nascosto"):
                    elenco.append(_dalla_tabella(voce, spiegazione))
            continue
        if opzione in nomi_della_tabella:
            continue
        rimando = _rimando(spiegazione)
        if rimando is not None and rimando in righe:
            continue
        elenco.append(_sconosciuto(opzione, sintassi, spiegazione))
    # Gli alias della tabella che questo pe non conosce non si mostrano.
    for parametro in elenco:
        parametro.alias = tuple(alias for alias in parametro.alias if alias in righe)
    return elenco


# I valori.


def valida(parametro, testo):
    """(valore, motivo): il valore da usare, o None e il perche', in
    italiano, con l'esempio di pe se c'e'."""
    testo = (testo or "").strip()
    esempio = f" {parametro.esempio}" if parametro.esempio else ""
    if not testo:
        if parametro.facoltativo:
            return "", None
        return None, _("{voce} vuole un valore.").format(voce=parametro.voce) + esempio
    if parametro.valore == "intero":
        try:
            numero = int(testo)
        except ValueError:
            return None, _("{voce} vuole un numero intero.").format(voce=parametro.voce) + esempio
        if parametro.minimo is not None and numero < parametro.minimo:
            return None, _("{voce} vuole un numero da {minimo} in su.").format(voce=parametro.voce, minimo=parametro.minimo)
        if parametro.massimo is not None and numero > parametro.massimo:
            return None, _("{voce} vuole un numero fino a {massimo}.").format(voce=parametro.voce, massimo=parametro.massimo)
        return str(numero), None
    if parametro.valore == "scelta":
        valori = [valore for valore, _spiegazione in parametro.scelte]
        if testo not in valori:
            return None, _("{voce} vuole uno di questi valori: {valori}.").format(voce=parametro.voce, valori=", ".join(v for v in valori if v))
        return testo, None
    if parametro.valore == "file":
        if not os.path.isfile(testo):
            return None, _("Il file {percorso} non c'e'.").format(percorso=testo)
        return testo, None
    if parametro.valore == "file_nuovo":
        cartella_del_file = os.path.dirname(os.path.abspath(testo))
        if not os.path.isdir(cartella_del_file):
            return None, _("La cartella {cartella} non c'e'.").format(cartella=cartella_del_file)
        return testo, None
    if parametro.regola:
        try:
            buono = re.fullmatch(parametro.regola, testo) is not None
        except re.error:
            buono = True
        if not buono:
            return None, _("Il valore {valore} non va bene per {voce}.").format(valore=testo, voce=parametro.voce) + esempio
    return testo, None


@dataclasses.dataclass
class Scelto:
    """Un parametro della catena, col suo valore; None finche' non c'e'."""

    parametro: Parametro
    valore: object = None

    @property
    def manca_il_valore(self):
        return self.parametro.vuole_un_valore and self.valore is None and not self.parametro.facoltativo

    @property
    def etichetta(self):
        voce = self.parametro.voce
        if self.parametro.opzione == ALTRO_SORGENTE:
            if self.valore:
                return f"{voce}: {self.valore}"
            return f"{voce} ({_('manca il file')})"
        if self.manca_il_valore:
            return f"{voce} ({_('manca il valore')})"
        if self.valore:
            return f"{voce} {self.valore}"
        return voce


# Il comando.

# I parametri che pe vuole prima di altri: -S deve precedere -t e -T.
PRIMA = ("-S",)
# Quelli che scrivono da se' piu' file nella cartella di lavoro, al posto
# di -o, e quello che controlla soltanto.
IN_PIU_FILE = ("-#", "-E")
SOLO_CONTROLLO = ("-r",)


def _opzioni(scelti):
    return {scelto.parametro.opzione for scelto in scelti}


def scrive_la_destinazione(scelti):
    """Vero se pe scrive le partite nel file di destinazione: non con -r, che
    controlla soltanto, ne' con -# ed -E, che scrivono nella cartella."""
    opzioni = _opzioni(scelti)
    return not (opzioni & set(SOLO_CONTROLLO)) and not (opzioni & set(IN_PIU_FILE))


def serve_la_destinazione(scelti):
    """Con -r la destinazione non serve; con -# ed -E serve la sua cartella."""
    return not (_opzioni(scelti) & set(SOLO_CONTROLLO))


def percorso_eco():
    """eco.pgn per -e senza file: pe lo cercherebbe nella cartella di
    lavoro, che e' quella della destinazione."""
    from . import board_utils

    return board_utils.percorso_eco()


def argomenti(percorso_di_pe, scelti, sorgente, uscita):
    """La riga di comando: pe, i parametri nell'ordine di scelta con -S
    davanti, -o con il file d'uscita se scrive la destinazione, e i file
    sorgente in fondo, il primo e gli altri file sorgente."""
    ordinati = sorted(scelti, key=lambda scelto: 0 if scelto.parametro.opzione in PRIMA else 1)
    comando = [percorso_di_pe]
    sorgenti = [sorgente]
    for scelto in ordinati:
        parametro = scelto.parametro
        if parametro.opzione == ALTRO_SORGENTE:
            if scelto.valore:
                sorgenti.append(scelto.valore)
            continue
        valore = scelto.valore or ""
        if parametro.opzione == "-e" and not valore:
            valore = percorso_eco()
        if not parametro.vuole_un_valore or not valore:
            comando.append(parametro.prefisso)
        elif parametro.separato:
            comando.extend((parametro.prefisso, valore))
        else:
            comando.append(parametro.prefisso + valore)
    if uscita and scrive_la_destinazione(scelti):
        comando.append("-o" + uscita)
    comando.extend(sorgenti)
    return comando


def comando_leggibile(comando):
    """Il comando come si scriverebbe nel terminale, con pgn-extract al posto
    del percorso intero."""
    return subprocess.list2cmdline(["pgn-extract", *comando[1:]])


def spiegazione(scelti, sorgente_descritta, destinazione, comando):
    """Le righe dell'area del comando: il comando, cosa legge, cosa scrive e
    cosa fa ogni parametro, con la riga di pe."""
    righe = [_("Comando: {comando}").format(comando=comando_leggibile(comando))]
    righe.append(_("Legge: {sorgente}.").format(sorgente=sorgente_descritta))
    for scelto in scelti:
        if scelto.parametro.opzione == ALTRO_SORGENTE and scelto.valore:
            righe.append(_("Legge anche: {sorgente}.").format(sorgente=scelto.valore))
    if not serve_la_destinazione(scelti):
        righe.append(_("Controlla soltanto, senza scrivere partite."))
    elif not scrive_la_destinazione(scelti):
        righe.append(_("Scrive piu' file nella cartella {cartella}.").format(cartella=os.path.dirname(destinazione) or destinazione))
    elif destinazione and os.path.exists(destinazione):
        righe.append(_("Scrive: {destinazione}, che c'e' gia': prima la copia di sicurezza nella cartella pgn, poi lo sostituisce.").format(destinazione=destinazione))
    elif destinazione:
        righe.append(_("Scrive: {destinazione}, un file nuovo.").format(destinazione=destinazione))
    for scelto in scelti:
        parametro = scelto.parametro
        if parametro.opzione == ALTRO_SORGENTE:
            continue
        nome = f"{parametro.voce} {scelto.valore}" if scelto.valore else parametro.voce
        righe.append(f"{nome}: {parametro.riga}" if parametro.riga else nome)
    return righe


# La guida.


def percorso_della_guida(percorso_di_pe=None):
    """help.html nella cartella di pe, o accanto al pe indicato a mano."""
    nostra = nella_cartella(GUIDA)
    if os.path.isfile(nostra):
        return nostra
    if percorso_di_pe:
        accanto = os.path.join(os.path.dirname(percorso_di_pe), GUIDA)
        if os.path.isfile(accanto):
            return accanto
    return None


_BLOCCHI = re.compile(r"</?(?:p|br|li|ul|ol|tr|table|div|h[1-6]|dt|dd|dl|blockquote)\b[^>]*>", re.I)
_PRE = re.compile(r"(<pre\b[^>]*>.*?</pre>)", re.I | re.S)
_ETICHETTE = re.compile(r"<[^>]+>")


def _in_testo(frammento):
    """Un pezzo di HTML in righe di testo: i blocchi vanno a capo, i <pre>
    tengono le loro righe, le righe vuote si tolgono."""
    pezzi = []
    for pezzo in _PRE.split(frammento):
        if _PRE.fullmatch(pezzo):
            pezzi.append("\n" + html.unescape(_ETICHETTE.sub("", pezzo)) + "\n")
        else:
            pezzo = re.sub(r"\s+", " ", pezzo)
            pezzo = _BLOCCHI.sub("\n", pezzo)
            pezzi.append(html.unescape(_ETICHETTE.sub("", pezzo)))
    return [riga.strip() for riga in "".join(pezzi).split("\n") if riga.strip()]


@dataclasses.dataclass
class Sezione:
    ancora: str
    titolo: str
    righe: list


def sezioni_della_guida(testo):
    """help.html nelle sue sezioni <h2>, con l'id, il titolo e le righe."""
    sezioni = []
    pezzi = re.split(r"(<h2\b[^>]*>.*?</h2>)", testo or "", flags=re.I | re.S)
    for indice in range(1, len(pezzi), 2):
        intestazione = pezzi[indice]
        corpo = pezzi[indice + 1] if indice + 1 < len(pezzi) else ""
        ancora = re.search(r'\bid="([^"]+)"', intestazione)
        titolo = " ".join(_in_testo(intestazione))
        sezioni.append(Sezione(ancora.group(1) if ancora else "", titolo, _in_testo(corpo)))
    return sezioni


def leggi_la_guida(percorso):
    """Le sezioni della guida, o [] se non si legge."""
    if not percorso:
        return []
    try:
        with open(percorso, encoding="utf-8", errors="replace") as file:
            return sezioni_della_guida(file.read())
    except OSError:
        return []


def _nomina(testo, nome):
    return re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", testo) is not None


def sezione_del_parametro(sezioni, parametro):
    """La sezione che spiega il parametro: quella della sua ancora, poi la
    prima col suo nome nel titolo, poi la prima che lo nomina; o None."""
    nomi = (parametro.opzione, *parametro.alias)
    if parametro.ancora:
        for sezione in sezioni:
            if sezione.ancora == parametro.ancora:
                return sezione
    for sezione in sezioni:
        if any(_nomina(sezione.titolo, nome) for nome in nomi):
            return sezione
    for sezione in sezioni:
        if any(_nomina(riga, nome) for riga in sezione.righe for nome in nomi):
            return sezione
    return None


def guida_intera(sezioni):
    """Tutte le sezioni, ognuna col suo titolo."""
    righe = []
    for sezione in sezioni:
        righe.append(sezione.titolo)
        righe.extend(sezione.righe)
    return righe


# Il lavoro e il riassunto.

_FINALE = re.compile(r"^(\d+) games? matched out of (\d+)\.?$")
_SCACCHIERA = re.compile(r"^[.pnbrqkPNBRQK]{8}$")
_POSIZIONE = re.compile(r"^File .*Line number")


def _tipo(riga):
    """Il tipo di un messaggio di pe: la riga coi numeri, le case e le mosse
    al posto dei loro valori, cosi' gli stessi messaggi su partite diverse
    si contano insieme."""
    tipo = re.sub(r'"[^"]*"', '"..."', riga)
    tipo = re.sub(r"\b(?:[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|O-O(?:-O)?)[+#]?(?=[\s.,:;]|$)", "<move>", tipo)
    tipo = re.sub(r"\d+", "N", tipo)
    return tipo


class Riassunto:
    """Le righe di pe una alla volta: le partite riportate, i file letti, la
    riga finale coi conteggi, e i messaggi raggruppati per tipo, ognuno coi
    primi esempi, la partita e la posizione nel file. pe riporta ogni
    partita con una riga che finisce con uno spazio; dopo un messaggio
    riporta quella che lo riguarda."""

    def __init__(self):
        self.partite = 0
        self.letti = []
        self.abbinate = None
        self.totale = None
        self.tipi = {}
        self._esempio = None

    def osserva(self, riga):
        riga = riga.rstrip("\r\n")
        pulita = riga.strip()
        if not pulita or _SCACCHIERA.fullmatch(pulita):
            return
        finale = _FINALE.fullmatch(pulita)
        if finale:
            self.abbinate, self.totale = int(finale.group(1)), int(finale.group(2))
            self._esempio = None
            return
        if pulita.startswith("Processing "):
            self.letti.append(pulita[len("Processing "):])
            return
        if _POSIZIONE.match(pulita):
            if self._esempio is not None and "posizione" not in self._esempio:
                self._esempio["posizione"] = pulita
            return
        if riga.endswith(" "):
            self.partite += 1
            if self._esempio is not None and "partita" not in self._esempio:
                self._esempio["partita"] = pulita
            return
        tipo = _tipo(pulita)
        voce = self.tipi.setdefault(tipo, {"volte": 0, "esempi": []})
        voce["volte"] += 1
        if len(voce["esempi"]) < ESEMPI_PER_TIPO:
            self._esempio = {"riga": pulita}
            voce["esempi"].append(self._esempio)
        else:
            self._esempio = None

    @property
    def messaggi(self):
        return sum(voce["volte"] for voce in self.tipi.values())

    def righe(self):
        """Il riassunto, in italiano, coi messaggi di pe come li scrive."""
        righe = []
        if self.totale is not None:
            righe.append(_("Partite lette: {totale}; accettate dai criteri: {abbinate}.").format(totale=self.totale, abbinate=self.abbinate))
        else:
            righe.append(_("Partite riportate da pgn-extract: {n}.").format(n=self.partite))
        if not self.tipi:
            righe.append(_("Nessun messaggio di errore o di avviso."))
            return righe
        righe.append(_("Messaggi di pgn-extract: {n}, di {tipi} tipi.").format(n=self.messaggi, tipi=len(self.tipi)))
        for tipo, voce in sorted(self.tipi.items(), key=lambda coppia: -coppia[1]["volte"]):
            righe.append(_("{volte} volte: {tipo}").format(volte=voce["volte"], tipo=tipo))
            for esempio in voce["esempi"]:
                dettagli = [esempio["riga"], esempio.get("partita"), esempio.get("posizione")]
                righe.append(_("Esempio: {dettagli}").format(dettagli="; ".join(d for d in dettagli if d)))
        return righe


def percorso_del_resoconto(sorgente_descritta):
    """Il file dell'uscita completa, nella cartella txt, col nome
    dell'archivio e l'ora."""
    cartella_txt = config.percorso_salvataggio("txt")
    os.makedirs(cartella_txt, exist_ok=True)
    nome = os.path.splitext(os.path.basename(sorgente_descritta))[0] or "pgn-extract"
    nome = re.sub(r'[\\/:*?"<>|]', "_", nome)
    return os.path.join(cartella_txt, f"pgn-extract {nome} {time.strftime('%Y%m%d-%H%M%S')}.txt")


@dataclasses.dataclass
class Esito:
    """Come e' andato il lavoro: codice di pe, o None se non e' partito;
    fermato se l'ha fermato l'utente; il riassunto; il resoconto completo;
    errore, il motivo se non e' partito; secondi."""

    codice: object
    fermato: bool
    riassunto: Riassunto
    resoconto: str
    errore: object = None
    secondi: float = 0.0


def lavora(comando, cartella_di_lavoro, resoconto, avanzamento, fermato):
    """pe col comando, nella cartella di lavoro: ogni riga va nel resoconto
    e al riassunto; avanzamento(partite) ogni mezzo secondo; fermato() vero
    ferma pe. Restituisce l'Esito. Gira nel filo della finestra."""
    riassunto = Riassunto()
    try:
        with open(resoconto, "w", encoding="utf-8") as file_del_resoconto:
            return _lavora_nel_file(comando, cartella_di_lavoro, file_del_resoconto, riassunto, avanzamento, fermato, resoconto)
    except OSError as errore:
        return Esito(None, False, riassunto, resoconto, str(errore))


def _lavora_nel_file(comando, cartella_di_lavoro, file_del_resoconto, riassunto, avanzamento, fermato, resoconto):
    inizio = time.monotonic()
    file_del_resoconto.write(_("Comando: {comando}").format(comando=comando_leggibile(comando)) + "\n")
    file_del_resoconto.write(_("Iniziato: {quando}").format(quando=time.strftime("%Y-%m-%d %H:%M:%S")) + "\n")
    try:
        processo = subprocess.Popen(
            comando,
            cwd=cartella_di_lavoro,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            **_senza_finestra(),
        )
    except OSError as errore:
        file_del_resoconto.write(str(errore) + "\n")
        return Esito(None, False, riassunto, resoconto, str(errore))
    fermo = threading.Event()

    def sorveglia():
        # pe non si ferma da se' quando l'utente vuole: lo si chiude.
        while processo.poll() is None and not fermo.wait(0.1):
            if fermato():
                processo.terminate()
                return

    threading.Thread(target=sorveglia, name="pgn-extract, fermata", daemon=True).start()
    try:
        ultimo = 0.0
        for dati in processo.stderr:
            riga = _decodifica(dati).rstrip("\r\n")
            file_del_resoconto.write(riga + "\n")
            riassunto.osserva(riga)
            adesso = time.monotonic()
            if adesso - ultimo >= INTERVALLO_DELL_AVANZAMENTO:
                ultimo = adesso
                avanzamento(riassunto.partite)
        codice = processo.wait()
    finally:
        fermo.set()
        # Se il resoconto non si scrive piu', pe non resta acceso da solo.
        if processo.poll() is None:
            processo.kill()
            processo.wait()
    secondi = time.monotonic() - inizio
    file_del_resoconto.write(_("Finito: codice {codice}, {secondi:.1f} secondi.").format(codice=codice, secondi=secondi) + "\n")
    return Esito(codice, fermato(), riassunto, resoconto, None, secondi)


def file_degli_appunti(testo):
    """Il PGN degli appunti in un file temporaneo, per pe: il percorso."""
    descrittore, percorso = tempfile.mkstemp(prefix="orologic-appunti-", suffix=".pgn")
    with os.fdopen(descrittore, "w", encoding="utf-8") as file:
        file.write(testo)
    return percorso


# Il numero che Orologic mette dopo il nome dei risultati, come Windows.
_NUMERO_IN_FONDO = re.compile(r"^(.*) \((\d+)\)$")


def destinazione_proposta(sorgente):
    """Il risultato accanto al sorgente, col primo numero libero dopo il
    nome, come Windows: a1.pgn porta a a1 (1).pgn, e lavorando su a1 (1).pgn
    il numero sale, a1 (2).pgn (Gabriele, 24 novembre 2026). Per il testo
    degli appunti, sorgente None, la cartella pgn di Orologic."""
    if sorgente:
        cartella_del_risultato = os.path.dirname(os.path.abspath(sorgente))
        base, estensione = os.path.splitext(os.path.basename(sorgente))
    else:
        cartella_del_risultato = config.percorso_salvataggio("pgn")
        os.makedirs(cartella_del_risultato, exist_ok=True)
        base, estensione = _("appunti"), ".pgn"
    numerato = _NUMERO_IN_FONDO.match(base)
    if numerato:
        base = numerato.group(1)
    estensione = estensione or ".pgn"
    numero = 1
    while True:
        candidato = os.path.join(cartella_del_risultato, f"{base} ({numero}){estensione}")
        if not os.path.exists(candidato) and not os.path.exists(uscita_provvisoria(candidato)):
            return candidato
        numero += 1


def copia_del_sorgente(sorgente):
    """Dopo un lavoro riuscito, la copia di sicurezza del sorgente nella
    cartella pgn, perche' l'utente possa cancellare l'originale quando il
    risultato gli piace: una per versione, cioe' niente copia nuova se ce
    n'e' gia' una uguale byte per byte (Gabriele, 24 novembre 2026).
    Restituisce (percorso della copia, vero se e' nuova)."""
    from . import archivio_pgn

    cartella_pgn = config.percorso_salvataggio("pgn")
    nome, estensione = os.path.splitext(os.path.basename(sorgente))
    prefisso = f"{nome} {_('copia')} "
    try:
        dimensione = os.path.getsize(sorgente)
        presenti = sorted(os.listdir(cartella_pgn)) if os.path.isdir(cartella_pgn) else []
        for voce in presenti:
            if not voce.startswith(prefisso) or not voce.lower().endswith((estensione or ".pgn").lower()):
                continue
            percorso = os.path.join(cartella_pgn, voce)
            if os.path.getsize(percorso) == dimensione and filecmp.cmp(sorgente, percorso, shallow=False):
                return percorso, False
    except OSError:
        pass
    return archivio_pgn.copia_di_sicurezza(sorgente), True


def uscita_provvisoria(destinazione):
    """Il file dove pe scrive, accanto alla destinazione: prende il suo
    posto solo se pe finisce bene, cosi' un lavoro fermato o fallito non
    tocca la destinazione."""
    return destinazione + ".pgn-extract.tmp"


def sostituisci(provvisoria, destinazione):
    """La destinazione dal file provvisorio, dopo la copia di sicurezza se
    c'era gia': il percorso della copia, o None."""
    from . import archivio_pgn

    copia = None
    if os.path.exists(destinazione):
        copia = archivio_pgn.copia_di_sicurezza(destinazione)
    os.replace(provvisoria, destinazione)
    return copia


def stesso_file(primo, secondo):
    """Vero se i due percorsi sono lo stesso file."""
    if not primo or not secondo:
        return False
    try:
        if os.path.exists(primo) and os.path.exists(secondo):
            return os.path.samefile(primo, secondo)
    except OSError:
        pass
    return os.path.normcase(os.path.abspath(primo)) == os.path.normcase(os.path.abspath(secondo))


# Il sito: versione, scaricamento e aggiornamento.


def _apri(indirizzo, attesa):
    """(risposta, errore) dal sito di pe. I messaggi di rete.apri parlano di
    Lichess, e il suo freno per le troppe richieste e' di Lichess: qui si
    apre da se', col contesto dei certificati di GBUtils."""
    from GBUtils import contesto_ssl

    try:
        return urllib.request.urlopen(rete.prepara(indirizzo), timeout=attesa, context=contesto_ssl()), None
    except urllib.error.HTTPError as errore:
        return None, _("Il sito di pgn-extract ha risposto con l'errore {codice}.").format(codice=errore.code)
    except urllib.error.URLError as errore:
        return None, rete._messaggio_urlerror(errore, attesa)
    except TimeoutError:
        return None, _("Nessuna risposta entro {n} secondi.").format(n=int(attesa))
    except OSError as errore:
        return None, _("Connessione non riuscita: {motivo}").format(motivo=errore)


def versione_della_guida(testo):
    """La versione scritta nella guida, Version 26-04, o None."""
    trovata = re.search(r"Version\s+(\d+-\d+)", testo or "")
    return trovata.group(1) if trovata else None


def versione_sul_sito():
    """(versione, errore): la versione che il sito offre, dalla sua guida."""
    risposta, errore = _apri(SITO + GUIDA, ATTESA_DEL_SITO)
    if errore:
        return None, errore
    try:
        with risposta:
            testo = _decodifica(risposta.read())
    except OSError as errore:
        return None, _("Lettura interrotta: {motivo}").format(motivo=errore)
    trovata = versione_della_guida(testo)
    if trovata is None:
        return None, _("Sul sito di pgn-extract non trovo la versione.")
    return trovata, None


def mancano_dei_file():
    """I file del sito che mancano nella cartella di pe."""
    return [nome for nome in FILE_DEL_SITO if not os.path.isfile(nella_cartella(nome))]


def _scarica_un_file(indirizzo, destinazione, fermato):
    risposta, errore = _apri(indirizzo, ATTESA_DELLO_SCARICAMENTO)
    if errore:
        return errore
    try:
        with risposta as sorgente, open(destinazione, "wb") as file:
            while True:
                if fermato():
                    return _("Scaricamento fermato.")
                blocco = sorgente.read(65536)
                if not blocco:
                    break
                file.write(blocco)
    except OSError as errore:
        return _("Scaricamento interrotto: {motivo}").format(motivo=errore)
    return None


def scarica(avanzamento, fermato):
    """Scarica dal sito i file di pe in una cartella di lavoro, prova che
    l'eseguibile risponda, e solo allora la mette al posto di quella di
    prima, come per Stockfish. avanzamento(riga) dice a che punto e';
    restituisce (versione, errore)."""
    destinazione = cartella()
    lavorazione = destinazione + ".nuovo"
    vecchia = destinazione + ".vecchio"
    shutil.rmtree(lavorazione, ignore_errors=True)
    try:
        os.makedirs(lavorazione)
    except OSError as errore:
        return None, _("Impossibile preparare la cartella di lavoro: {motivo}").format(motivo=errore)
    for numero, nome in enumerate(FILE_DEL_SITO, start=1):
        avanzamento(_("Scarico {nome}, {numero} di {tutti}.").format(nome=nome, numero=numero, tutti=len(FILE_DEL_SITO)))
        errore = _scarica_un_file(SITO + nome, os.path.join(lavorazione, nome), fermato)
        if errore:
            shutil.rmtree(lavorazione, ignore_errors=True)
            return None, errore
    nuova = versione(os.path.join(lavorazione, ESEGUIBILE))
    if nuova is None:
        shutil.rmtree(lavorazione, ignore_errors=True)
        return None, _("Il pgn-extract scaricato non risponde: resta quello di prima.")
    try:
        shutil.rmtree(vecchia, ignore_errors=True)
        if os.path.exists(destinazione):
            os.replace(destinazione, vecchia)
        os.replace(lavorazione, destinazione)
    except OSError as errore:
        if os.path.exists(vecchia) and not os.path.exists(destinazione):
            os.replace(vecchia, destinazione)
        shutil.rmtree(lavorazione, ignore_errors=True)
        return None, _("Sostituzione non riuscita: {motivo}").format(motivo=errore)
    shutil.rmtree(vecchia, ignore_errors=True)
    return nuova, None


def aggiornamento(percorso_di_pe):
    """Cosa proporre all'apertura, dal filo: (domanda, None) se c'e' da
    scaricare, una versione nuova o i file che mancano accanto a pe;
    (None, motivo) se il sito non risponde; (None, None) se e' tutto a
    posto."""
    locale = versione(percorso_di_pe) if percorso_di_pe else None
    remota, errore = versione_sul_sito()
    if errore:
        return None, errore
    if locale and come_numeri(remota) > come_numeri(locale):
        return _("E' uscita la versione {nuova} di pgn-extract, tu hai la {vecchia}. La scarico dal sito di David J. Barnes, con la guida, eco.pgn e la licenza?").format(nuova=remota, vecchia=locale), None
    if percorso_di_pe == nella_cartella(ESEGUIBILE) and mancano_dei_file():
        return _("Accanto a pgn-extract mancano dei file: {file}. Riscarico pgn-extract {versione} dal sito, con la guida, eco.pgn e la licenza?").format(file=", ".join(mancano_dei_file()), versione=remota), None
    return None, None
