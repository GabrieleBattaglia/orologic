# Orologic, prove di pgn-extract dentro Orologic.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""pgn_extract.py, issue 74: l'elenco di pe -h unito alla tabella, la
validazione dei valori, il comando nell'ordine di Orologic, il riassunto
dell'uscita, la guida divisa in sezioni, lo scaricamento con la cartella
che si sostituisce solo a lavoro riuscito, e la proposta di aggiornamento.
Le prove con pe vero partono soltanto se l'eseguibile c'e' nella cartella
pgn-extract del progetto, che non e' in git; la rete non si tocca mai."""

import io
import json
import os
import shutil

import pytest
from conftest import RADICE

from orologic_modules import config, pgn_extract

PE_VERO = os.path.join(RADICE, "pgn-extract", "pgn-extract.exe")
con_pe = pytest.mark.skipif(not os.path.isfile(PE_VERO), reason="pgn-extract.exe non c'e' nella cartella del progetto")

# Un elenco nella forma di pe -h, scritto per la prova.
AIUTO = """pgn-extract v99-01 (prova): un elenco per le prove.
Usage: pgn-extract [arguments] [file.pgn ...]
-7 -- output only the seven tag roster.
-bnum -- bounds on the number of moves.
       lnum lower bound,
       unum upper bound.
-C -- don't include comments in the output.
-h -- print the arguments.
-ooutputfile -- write games to outputfile.
-S -- simple soundex.
-Tcriterion -- tag criteria.
--minmoves N - only output games with at least N moves.
--nocomments - see -C
--nuovissimo X - an option the table does not know.
--sola - a flag the table does not know.
"""

# Le righe di pe su un archivio con una mossa illegale, un risultato in
# conflitto col matto e un doppione, come le scrive la v26-04. pe chiude
# con uno spazio la riga di ogni partita: qui e' il segno |, che si toglie.
USCITA = """Processing prova.pgn
Bianco, Uno - Nero, Uno Prova Qui 2026.11.25 |
No king move possible to e3.
File prova.pgn: Line number: 19 character 22
Failed to make move 2. Ke3 in the game:
rnbqkbnr
pppp.ppp
........
....p...
....P...
........
PPPP.PPP
RNBQKBNR

Bianco, Due - Nero, Due Prova Qui 2026.11.25 |
File prova.pgn: Line number: 19 character 22
Warning: Result of 1-0 is inconsistent with checkmate by black in
Bianco, Tre - Nero, Tre Prova Qui 2026.11.25 |
2 games matched out of 4.
""".replace(" |\n", " \n")

ARCHIVIO = """[Event "Prova"]
[Site "Qui"]
[Date "2026.11.25"]
[Round "1"]
[White "Bianco, Uno"]
[Black "Nero, Uno"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0

[Event "Prova"]
[Site "Qui"]
[Date "2026.11.25"]
[Round "2"]
[White "Bianco, Due"]
[Black "Nero, Due"]
[Result "1-0"]

1. e4 e5 2. Ke3 Nc6 1-0

[Event "Prova"]
[Site "Qui"]
[Date "2026.11.25"]
[Round "1"]
[White "Bianco, Uno"]
[Black "Nero, Uno"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""


# Un catalogo nella forma di arguments.json di David, scritto per la prova.
CATALOGO = {
    "format": "pgn-extract-arguments",
    "format_version": 1,
    "program_version": "v99-01",
    "options": [
        {
            "name": "-7",
            "aliases": ["--seven"],
            "value": None,
            "repetition": "idempotent",
            "description": "Seven tags.",
            "help_id": "sette",
            "conflicts_with": [
                {"option": "-C", "severity": "error"},
                {"option": "--minmoves", "severity": "warning", "when": "Only when the moon is full."},
            ],
        },
        {
            "name": "-C",
            "aliases": ["--nocomments"],
            "value": None,
            "repetition": "idempotent",
            "description": "No comments.",
            "help_id": "dup",
            "conflicts_with": [{"option": "-7", "severity": "error"}],
        },
        {
            "name": "--minmoves",
            "aliases": [],
            "value": {"arity": "required", "kind": "unsigned-integer", "forms": {"--minmoves": ["separate"]}, "minimum": 1},
            "repetition": "replace",
            "description": "Minimum moves.",
            "help_id": "output",
            "conflicts_with": [{"option": "-7", "severity": "warning", "when": "Only when the moon is full."}],
        },
        {
            "name": "--nuovissimo",
            "aliases": [],
            "value": {"arity": "required", "kind": "unsigned-integer", "forms": {"--nuovissimo": ["separate"]}, "minimum": 2, "maximum": 9, "syntax": "N"},
            "repetition": "accumulate",
            "description": "A new number.",
            "help_id": "interna",
        },
        {"name": "--sola", "aliases": [], "value": None, "repetition": "idempotent", "description": "A flag."},
    ],
}


def _per_voce(elenco):
    return {parametro.voce: parametro for parametro in elenco}


def test_l_elenco_di_pe_si_legge_con_le_righe_rientrate():
    voci = pgn_extract.voci_dell_aiuto(AIUTO)
    opzioni = [opzione for opzione, _sintassi, _riga in voci]
    assert opzioni == ["-7", "-b", "-C", "-h", "-o", "-S", "-T", "--minmoves", "--nocomments", "--nuovissimo", "--sola"]
    sintassi = {opzione: (sintassi, riga) for opzione, sintassi, riga in voci}
    assert sintassi["-b"] == ("num", "bounds on the number of moves. lnum lower bound, unum upper bound.")
    assert sintassi["--minmoves"][0] == "N"
    assert sintassi["--nocomments"][1] == "see -C"


def test_i_parametri_uniscono_l_elenco_e_la_tabella():
    elenco = pgn_extract.parametri(AIUTO)
    per_voce = _per_voce(elenco)
    # Prima Altro file sorgente, che si ripete e non e' un'opzione di pe.
    assert elenco[0].opzione == pgn_extract.ALTRO_SORGENTE and elenco[0].ripetibile
    # -C ha l'altro nome di pe, e --nocomments non e' una voce a parte.
    assert per_voce["-C"].alias == ("--nocomments",)
    assert "--nocomments" not in per_voce
    assert per_voce["-C"].etichetta == "-C, --nocomments: don't include comments in the output."
    # Orologic gestisce da se' -h e -o.
    assert "-h" not in per_voce and "-o" not in per_voce
    # Le varianti separate, coi loro prefissi.
    assert per_voce["-bl"].prefisso == "-bl" and per_voce["-bl"].valore == "intero"
    assert "-Tw" in per_voce and per_voce["-Tw"].ripetibile
    # Gli sconosciuti: un valore se pe -h gli scrive la sintassi, separato
    # per le lunghe; un interruttore altrimenti.
    assert per_voce["--nuovissimo"].valore == "testo" and per_voce["--nuovissimo"].separato
    assert not per_voce["--nuovissimo"].conosciuto
    assert per_voce["--sola"].valore is None


def test_il_catalogo_si_legge_solo_se_e_lui(tmp_path):
    percorso = tmp_path / "arguments.json"
    percorso.write_text(json.dumps(CATALOGO), encoding="utf-8")
    catalogo = pgn_extract.leggi_il_catalogo(str(percorso))
    assert catalogo.versione == "v99-01"
    # I nomi lunghi senza badare alle maiuscole, i brevi si'.
    assert catalogo.canonico("--NOCOMMENTS") == "-C"
    assert catalogo.canonico("-c") is None
    assert catalogo.trova("--seven")["name"] == "-7"
    # Un file d'altro genere, rotto o assente non e' un catalogo.
    percorso.write_text(json.dumps({**CATALOGO, "format": "altro"}), encoding="utf-8")
    assert pgn_extract.leggi_il_catalogo(str(percorso)) is None
    percorso.write_text("{ rotto", encoding="utf-8")
    assert pgn_extract.leggi_il_catalogo(str(percorso)) is None
    assert pgn_extract.leggi_il_catalogo(str(tmp_path / "manca.json")) is None
    assert pgn_extract.leggi_il_catalogo(None) is None


def test_il_catalogo_arricchisce_i_parametri():
    catalogo = pgn_extract.catalogo_dai_dati(CATALOGO)
    per_voce = _per_voce(pgn_extract.parametri(AIUTO, catalogo))
    # I conflitti e il nome di David.
    assert per_voce["-C"].canonico == "-C"
    assert per_voce["-C"].conflitti == (pgn_extract.Conflitto("-7", True),)
    # L'ancora del catalogo per prima, quella della tabella dopo.
    assert per_voce["-7"].ancora == "sette" and per_voce["-7"].altre_ancore == ("-7",)
    # Lo sconosciuto alla tabella col valore giusto, dal catalogo.
    nuovo = per_voce["--nuovissimo"]
    assert (nuovo.valore, nuovo.minimo, nuovo.massimo, nuovo.separato, nuovo.ripetibile, nuovo.esempio) == ("intero", 2, 9, True, True, "N")
    assert nuovo.conosciuto and nuovo.canonico == "--nuovissimo"
    assert pgn_extract.valida(nuovo, "1")[0] is None
    assert per_voce["--sola"].valore is None
    # Senza catalogo, tutto come prima.
    senza = _per_voce(pgn_extract.parametri(AIUTO))
    assert senza["-C"].conflitti == () and senza["-C"].canonico is None
    assert senza["--nuovissimo"].valore == "testo"


def test_i_conflitti_fra_gli_scelti():
    per_voce = _per_voce(pgn_extract.parametri(AIUTO, pgn_extract.catalogo_dai_dati(CATALOGO)))
    scelti = [pgn_extract.Scelto(per_voce[voce]) for voce in ("-7", "-C", "--minmoves", "--sola")]
    trovati = pgn_extract.conflitti(scelti)
    assert [(primo.voce, secondo.voce) for primo, secondo, _conflitto in trovati] == [("-7", "-C"), ("-7", "--minmoves")]
    grave, lieve = (conflitto for _primo, _secondo, conflitto in trovati)
    assert pgn_extract.blocca(grave) and not pgn_extract.blocca(lieve)
    assert pgn_extract.spiega_il_conflitto(*trovati[0]) == "-7 e -C non vanno insieme: pgn-extract si fermerebbe."
    assert pgn_extract.spiega_il_conflitto(*trovati[1]) == (
        "-7 e --minmoves insieme: pgn-extract ne ignorerebbe uno, o spegnerebbe qualcosa. Only when the moon is full."
    )
    grave_con_condizione = pgn_extract.Conflitto("-C", True, "When it rains.")
    assert not pgn_extract.blocca(grave_con_condizione)
    assert pgn_extract.spiega_il_conflitto(per_voce["-7"], per_voce["-C"], grave_con_condizione) == "-7 e -C non vanno insieme quando: When it rains."


def test_la_validazione_dice_perche():
    per_voce = _per_voce(pgn_extract.parametri(AIUTO))
    minmoves = per_voce["--minmoves"]
    assert pgn_extract.valida(minmoves, " 20 ") == ("20", None)
    valore, motivo = pgn_extract.valida(minmoves, "venti")
    assert valore is None and "--minmoves" in motivo
    valore, motivo = pgn_extract.valida(minmoves, "")
    assert valore is None and "vuole un valore" in motivo
    regolato = pgn_extract.Parametro(voce="-x", opzione="-x", prefisso="-x", valore="testo", regola=r"[elu]?\d+", esempio="like l20")
    assert pgn_extract.valida(regolato, "l20") == ("l20", None)
    valore, motivo = pgn_extract.valida(regolato, "molte")
    assert valore is None and motivo.endswith("like l20")
    scelta = pgn_extract.Parametro(voce="-W", opzione="-W", prefisso="-W", valore="scelta", scelte=(("san", "SAN"), ("lalg", "long")))
    assert pgn_extract.valida(scelta, "lalg") == ("lalg", None)
    assert pgn_extract.valida(scelta, "uci")[0] is None
    file = pgn_extract.Parametro(voce="-c", opzione="-c", prefisso="-c", valore="file")
    assert pgn_extract.valida(file, os.path.join(RADICE, "nessun_file.pgn"))[0] is None


def test_il_comando_nell_ordine_di_orologic(tmp_path):
    per_voce = _per_voce(pgn_extract.parametri(AIUTO))
    altro = pgn_extract.altro_sorgente()
    scelti = [
        pgn_extract.Scelto(per_voce["-Tw"], "Carlsen"),
        pgn_extract.Scelto(altro, "secondo.pgn"),
        pgn_extract.Scelto(per_voce["--minmoves"], "20"),
        pgn_extract.Scelto(per_voce["-S"]),
        pgn_extract.Scelto(per_voce["-C"]),
    ]
    comando = pgn_extract.argomenti("pe.exe", scelti, "primo.pgn", "uscita.pgn")
    # -S davanti, i valori attaccati alle brevi e separati per le lunghe,
    # -o, e i sorgenti in fondo.
    assert comando == ["pe.exe", "-S", "-TwCarlsen", "--minmoves", "20", "-C", "-ouscita.pgn", "primo.pgn", "secondo.pgn"]
    assert pgn_extract.comando_leggibile(comando).startswith("pgn-extract -S -TwCarlsen")
    # Con -r non si scrive: niente -o.
    solo = [pgn_extract.Scelto(pgn_extract.Parametro(voce="-r", opzione="-r", prefisso="-r"))]
    assert pgn_extract.argomenti("pe.exe", solo, "primo.pgn", "uscita.pgn") == ["pe.exe", "-r", "primo.pgn"]
    assert not pgn_extract.serve_la_destinazione(solo)


def test_e_senza_file_usa_l_eco_di_orologic(monkeypatch):
    monkeypatch.setattr(pgn_extract, "percorso_eco", lambda: r"C:\orologic\eco.pgn")
    eco = pgn_extract.Parametro(voce="-e", opzione="-e", prefisso="-e", valore="file", facoltativo=True)
    comando = pgn_extract.argomenti("pe.exe", [pgn_extract.Scelto(eco, "")], "primo.pgn", "uscita.pgn")
    assert comando[1] == r"-eC:\orologic\eco.pgn"


def test_il_riassunto_raggruppa_i_messaggi():
    riassunto = pgn_extract.Riassunto()
    for riga in USCITA.splitlines():
        riassunto.osserva(riga)
    assert riassunto.letti == ["prova.pgn"]
    assert (riassunto.abbinate, riassunto.totale) == (2, 4)
    # Tre tipi: la mossa del re, la mossa fallita e il risultato col matto.
    assert riassunto.messaggi == 3
    righe = riassunto.righe()
    assert righe[0] == "Partite lette: 4; accettate dai criteri: 2."
    testo = "\n".join(righe)
    assert "No king move possible to <move>." in testo
    # L'esempio dice la partita e dove sta nel file.
    assert "Bianco, Due - Nero, Due Prova Qui 2026.11.25; File prova.pgn: Line number: 19 character 22" in testo
    # Lo schema della scacchiera non e' un messaggio.
    assert "rnbqkbnr" not in testo


def test_lo_stesso_tipo_si_conta_insieme():
    riassunto = pgn_extract.Riassunto()
    for mossa in ("e3", "d4", "f5", "g6"):
        riassunto.osserva(f"No king move possible to {mossa}.")
    assert list(riassunto.tipi) == ["No king move possible to <move>."]
    voce = riassunto.tipi["No king move possible to <move>."]
    assert voce["volte"] == 4 and len(voce["esempi"]) == pgn_extract.ESEMPI_PER_TIPO


GUIDA = """<html><body><h1>pgn-extract<br>Version 26-04 by D</h1>
<h2 id="output">Output files (-o, --output, -a, --append)</h2>
<p>The -o flag writes games
to a file.</p><pre>pgn-extract -ofile.pgn
games.pgn</pre>
<h2 id="dup">Duplicate games</h2><p>Use --noduplicates to drop &amp; keep.</p>
</body></html>"""


def test_la_guida_in_sezioni():
    sezioni = pgn_extract.sezioni_della_guida(GUIDA)
    assert [sezione.ancora for sezione in sezioni] == ["output", "dup"]
    assert sezioni[0].titolo == "Output files (-o, --output, -a, --append)"
    # Il testo va a capo coi blocchi, il <pre> tiene le sue righe.
    assert sezioni[0].righe == ["The -o flag writes games to a file.", "pgn-extract -ofile.pgn", "games.pgn"]
    assert sezioni[1].righe == ["Use --noduplicates to drop & keep."]
    assert pgn_extract.versione_della_guida(GUIDA) == "26-04"
    # La sezione del parametro: l'ancora, poi il titolo, poi il testo.
    a = pgn_extract.Parametro(voce="-a", opzione="-a", prefisso="-a")
    assert pgn_extract.sezione_del_parametro(sezioni, a).ancora == "output"
    nodup = pgn_extract.Parametro(voce="-D", opzione="-D", prefisso="-D", alias=("--noduplicates",))
    assert pgn_extract.sezione_del_parametro(sezioni, nodup).ancora == "dup"
    nessuno = pgn_extract.Parametro(voce="-Z", opzione="-Z", prefisso="-Z")
    assert pgn_extract.sezione_del_parametro(sezioni, nessuno) is None
    assert pgn_extract.guida_intera(sezioni)[0] == "Output files (-o, --output, -a, --append)"
    # L'ancora del catalogo dentro una sezione, su un paragrafo: si legge la
    # sezione che la contiene; un'ancora che la guida non ha lascia il posto
    # alla seconda.
    con_interne = pgn_extract.sezioni_della_guida(GUIDA.replace("<p>The -o flag", '<p id="interna">The -o flag'))
    assert con_interne[0].interne == ("interna",)
    interna = pgn_extract.Parametro(voce="-Y", opzione="-Y", prefisso="-Y", ancora="interna")
    assert pgn_extract.sezione_del_parametro(con_interne, interna).ancora == "output"
    seconda = pgn_extract.Parametro(voce="-Y", opzione="-Y", prefisso="-Y", ancora="nuova", altre_ancore=("dup",))
    assert pgn_extract.sezione_del_parametro(sezioni, seconda).ancora == "dup"


def test_la_tabella_copre_ogni_parametro_di_pe():
    """Ogni voce di pe -h vero e' nella tabella, come voce o altro nome."""
    from orologic_modules import parametri_pe

    if not os.path.isfile(PE_VERO):
        pytest.skip("pgn-extract.exe non c'e'")
    noti = set()
    for voce in parametri_pe.PARAMETRI:
        noti.update((voce["opzione"], voce["voce"], *(voce.get("alias") or ())))
    voci = pgn_extract.voci_dell_aiuto(pgn_extract.testo_dell_aiuto(PE_VERO))
    mancanti = [opzione for opzione, _sintassi, _riga in voci if opzione not in noti]
    assert not mancanti
    assert all(parametro.conosciuto for parametro in pgn_extract.parametri(pgn_extract.testo_dell_aiuto(PE_VERO)))


@con_pe
def test_pe_vero_risponde_e_lavora(tmp_path):
    assert pgn_extract.come_numeri(pgn_extract.versione(PE_VERO)) >= (26, 4)
    sorgente = tmp_path / "prova.pgn"
    sorgente.write_text(ARCHIVIO, encoding="utf-8")
    elenco = _per_voce(pgn_extract.parametri(pgn_extract.testo_dell_aiuto(PE_VERO)))
    scelti = [pgn_extract.Scelto(elenco["-D"])]
    uscita = pgn_extract.uscita_provvisoria(str(tmp_path / "pulito.pgn"))
    comando = pgn_extract.argomenti(PE_VERO, scelti, str(sorgente), uscita)
    avanzamenti = []
    esito = pgn_extract.lavora(comando, str(tmp_path), str(tmp_path / "resoconto.txt"), avanzamenti.append, lambda: False)
    assert esito.errore is None and esito.codice == 0 and not esito.fermato
    # Tre partite, una illegale e un doppione: ne resta una.
    assert (esito.riassunto.abbinate, esito.riassunto.totale) == (1, 3)
    # La mossa del re e la mossa fallita: le righe delle partite non sono messaggi.
    assert esito.riassunto.messaggi == 2 and esito.riassunto.partite >= 2
    assert os.path.isfile(uscita)
    resoconto = (tmp_path / "resoconto.txt").read_text(encoding="utf-8")
    assert "No king move possible" in resoconto and "Finito: codice 0" in resoconto


@con_pe
def test_la_destinazione_si_sostituisce_dopo_la_copia(tmp_path):
    destinazione = tmp_path / "archivio.pgn"
    destinazione.write_text("vecchio", encoding="utf-8")
    provvisoria = tmp_path / "archivio.pgn.pgn-extract.tmp"
    provvisoria.write_text("nuovo", encoding="utf-8")
    copia = pgn_extract.sostituisci(str(provvisoria), str(destinazione))
    assert destinazione.read_text(encoding="utf-8") == "nuovo"
    assert os.path.dirname(copia) == config.percorso_salvataggio("pgn")
    with open(copia, encoding="utf-8") as file:
        assert file.read() == "vecchio"
    os.remove(copia)
    assert pgn_extract.stesso_file(str(destinazione), str(tmp_path / "." / "archivio.pgn"))


def test_la_destinazione_proposta_col_numero(tmp_path):
    sorgente = tmp_path / "GBChessDB.pgn"
    sorgente.write_text("x", encoding="utf-8")
    assert pgn_extract.destinazione_proposta(str(sorgente)) == str(tmp_path / "GBChessDB (1).pgn")
    (tmp_path / "GBChessDB (1).pgn").write_text("x", encoding="utf-8")
    # Il file provvisorio di un lavoro in corso conta come occupato.
    (tmp_path / "GBChessDB (2).pgn.pgn-extract.tmp").write_text("x", encoding="utf-8")
    assert pgn_extract.destinazione_proposta(str(sorgente)) == str(tmp_path / "GBChessDB (3).pgn")
    # Da un risultato il numero sale, non si somma.
    assert pgn_extract.destinazione_proposta(str(tmp_path / "GBChessDB (1).pgn")) == str(tmp_path / "GBChessDB (3).pgn")
    # Gli appunti nella cartella pgn di Orologic.
    assert pgn_extract.destinazione_proposta(None) == os.path.join(config.percorso_salvataggio("pgn"), "appunti (1).pgn")


def test_la_copia_del_sorgente_una_per_versione(tmp_path):
    sorgente = tmp_path / "Torneo.pgn"
    sorgente.write_text("prima", encoding="utf-8")
    copia, nuova = pgn_extract.copia_del_sorgente(str(sorgente))
    assert nuova and os.path.dirname(copia) == config.percorso_salvataggio("pgn")
    assert pgn_extract.copia_del_sorgente(str(sorgente)) == (copia, False)
    # Cambiato il sorgente, la copia e' nuova; quella di prima resta.
    sorgente.write_text("dopo!", encoding="utf-8")
    seconda, nuova = pgn_extract.copia_del_sorgente(str(sorgente))
    assert nuova and seconda != copia and os.path.isfile(copia)
    os.remove(copia)
    os.remove(seconda)


class _Risposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_dettagli):
        self.close()


def _sito_finto(monkeypatch, contenuti, guasto=None):
    """Il sito di pe sostituito: i file dai contenuti, o l'errore guasto."""
    chiesti = []

    def apri(indirizzo, _attesa):
        chiesti.append(indirizzo)
        nome = indirizzo.rsplit("/", 1)[-1]
        if guasto and nome == guasto:
            return None, "il sito non risponde"
        return _Risposta(contenuti[nome]), None

    monkeypatch.setattr(pgn_extract, "_apri", apri)
    return chiesti


@con_pe
def test_lo_scaricamento_mette_la_cartella_nuova_solo_se_pe_risponde(monkeypatch):
    with open(PE_VERO, "rb") as file:
        eseguibile = file.read()
    contenuti = {
        "pgn-extract.exe": eseguibile,
        "eco.pgn": b"[ECO \"A00\"]\n\n1. a3 *\n",
        "COPYING": b"GPL",
        "help.html": GUIDA.encode(),
        "arguments.json": json.dumps(CATALOGO).encode(),
    }
    cartella = pgn_extract.cartella()
    shutil.rmtree(cartella, ignore_errors=True)
    os.makedirs(cartella)
    with open(os.path.join(cartella, "vecchio.txt"), "w", encoding="utf-8") as file:
        file.write("prima")
    try:
        # Un file che non arriva: la cartella di prima resta com'era.
        _sito_finto(monkeypatch, contenuti, guasto="COPYING")
        versione, errore = pgn_extract.scarica(lambda _riga: None, lambda: False)
        assert versione is None and errore == "il sito non risponde"
        assert os.listdir(cartella) == ["vecchio.txt"]
        assert not os.path.exists(cartella + ".nuovo")
        # Tutto arrivato e pe risponde: la cartella nuova prende il posto.
        chiesti = _sito_finto(monkeypatch, contenuti)
        righe = []
        versione, errore = pgn_extract.scarica(righe.append, lambda: False)
        assert errore is None and pgn_extract.come_numeri(versione) >= (26, 4)
        assert chiesti == [pgn_extract.SITO + nome for nome in pgn_extract.FILE_DEL_SITO] + [pgn_extract.INDIRIZZO_DEL_CATALOGO]
        # Il file messo dall'utente resta nella cartella nuova (R36).
        assert sorted(os.listdir(cartella)) == sorted((*pgn_extract.FILE_DEL_SITO, pgn_extract.CATALOGO, "vecchio.txt"))
        assert not os.path.exists(cartella + ".vecchio")
        assert pgn_extract.eseguibile() == os.path.join(cartella, "pgn-extract.exe")
        assert pgn_extract.mancano_dei_file() == []
        assert len(righe) == len(pgn_extract.FILE_DEL_SITO) + 1
        assert pgn_extract.leggi_il_catalogo(pgn_extract.percorso_del_catalogo()).versione == "v99-01"
        # Il catalogo che non arriva non ferma niente: resta quello di prima.
        _sito_finto(monkeypatch, contenuti, guasto="arguments.json")
        versione, errore = pgn_extract.scarica(lambda _riga: None, lambda: False)
        assert errore is None and versione
        assert pgn_extract.leggi_il_catalogo(pgn_extract.percorso_del_catalogo()).versione == "v99-01"
        # Un pe che non risponde non prende il posto di quello buono.
        contenuti["pgn-extract.exe"] = b"non sono un programma"
        _sito_finto(monkeypatch, contenuti)
        versione, errore = pgn_extract.scarica(lambda _riga: None, lambda: False)
        assert versione is None and "non risponde" in errore
        assert pgn_extract.versione(os.path.join(cartella, "pgn-extract.exe"))
    finally:
        shutil.rmtree(cartella, ignore_errors=True)


def test_il_catalogo_che_manca_arriva_da_solo(monkeypatch, tmp_path):
    cartella = pgn_extract.cartella()
    shutil.rmtree(cartella, ignore_errors=True)
    os.makedirs(cartella)
    nostro = pgn_extract.nella_cartella(pgn_extract.ESEGUIBILE)
    with open(nostro, "wb") as file:
        file.write(b"")
    try:
        # Non un catalogo: non si tiene.
        _sito_finto(monkeypatch, {"arguments.json": b"<html>non trovato</html>"})
        assert not pgn_extract.aggiorna_il_catalogo(nostro)
        assert sorted(os.listdir(cartella)) == [pgn_extract.ESEGUIBILE]
        chiesti = _sito_finto(monkeypatch, {"arguments.json": json.dumps(CATALOGO).encode()})
        assert pgn_extract.aggiorna_il_catalogo(nostro)
        assert chiesti == [pgn_extract.INDIRIZZO_DEL_CATALOGO]
        assert pgn_extract.leggi_il_catalogo(pgn_extract.percorso_del_catalogo(nostro)).versione == "v99-01"
        # C'e' gia': non si chiede piu'; e accanto a un pe scelto a mano no.
        assert not pgn_extract.aggiorna_il_catalogo(nostro)
        assert not pgn_extract.aggiorna_il_catalogo(str(tmp_path / "pe.exe"))
        assert chiesti == [pgn_extract.INDIRIZZO_DEL_CATALOGO]
    finally:
        shutil.rmtree(cartella, ignore_errors=True)


def test_la_proposta_di_aggiornamento(monkeypatch, tmp_path):
    monkeypatch.setattr(pgn_extract, "versione_sul_sito", lambda: ("26-07", None))
    monkeypatch.setattr(pgn_extract, "versione", lambda _percorso: "26-04")
    domanda, motivo = pgn_extract.aggiornamento(str(tmp_path / "pgn-extract.exe"))
    assert motivo is None and "26-07" in domanda and "26-04" in domanda
    monkeypatch.setattr(pgn_extract, "versione_sul_sito", lambda: ("26-04", None))
    assert pgn_extract.aggiornamento(str(tmp_path / "pgn-extract.exe")) == (None, None)
    # Nella cartella di Orologic, coi file del sito che mancano.
    monkeypatch.setattr(pgn_extract, "mancano_dei_file", lambda: ["COPYING"])
    domanda, motivo = pgn_extract.aggiornamento(pgn_extract.nella_cartella(pgn_extract.ESEGUIBILE))
    assert "COPYING" in domanda
    monkeypatch.setattr(pgn_extract, "versione_sul_sito", lambda: (None, "nessuna rete"))
    assert pgn_extract.aggiornamento(None) == (None, "nessuna rete")


def test_il_pe_indicato_a_mano_si_ricorda(tmp_path, impostazioni_rimesse):
    finto = tmp_path / "pe.exe"
    finto.write_bytes(b"")
    assert pgn_extract.eseguibile() is None
    pgn_extract.ricorda_il_percorso(str(finto))
    assert pgn_extract.eseguibile() == str(finto)


def test_un_catalogo_di_forma_diversa_non_blocca_niente(tmp_path):
    """R68: un arguments.json di un formato diverso sollevava un errore
    che nessuno prendeva, e la finestra non si apriva piu'."""
    import json as json_

    percorso = tmp_path / "arguments.json"
    for dati in (
        {"format": "pgn-extract-arguments", "format_version": 2, "options": []},
        {"format": "pgn-extract-arguments", "format_version": 1, "options": ["-7", {"name": "-s", "value": ["strano"]}]},
        {"format": "pgn-extract-arguments", "format_version": 1, "options": [{"name": "-s", "aliases": 5}]},
    ):
        percorso.write_text(json_.dumps(dati), encoding="utf-8")
        assert pgn_extract.leggi_il_catalogo(str(percorso)) is None
    # Il catalogo vero si legge ancora.
    vero = os.path.join(RADICE, "pgn-extract", "arguments.json")
    if os.path.isfile(vero):
        assert pgn_extract.leggi_il_catalogo(vero) is not None


def test_i_file_che_dividere_in_piu_file_sovrascriverebbe(tmp_path):
    """R60: con -# pgn-extract sovrascrive 1.pgn e seguenti, con -E accoda
    ad A.pgn, B00.pgn e simili."""
    for nome in ("1.pgn", "12.pgn", "A.pgn", "B00.pgn", "partite.pgn", "C123.pgn"):
        (tmp_path / nome).write_text("x", encoding="utf-8")

    class Scelto:
        def __init__(self, opzione):
            self.parametro = type("P", (), {"opzione": opzione})()

    assert pgn_extract.file_che_sovrascriverebbe([Scelto("-#")], str(tmp_path)) == ["1.pgn", "12.pgn"]
    assert pgn_extract.file_che_sovrascriverebbe([Scelto("-E")], str(tmp_path)) == ["A.pgn", "B00.pgn"]
    assert pgn_extract.file_che_sovrascriverebbe([Scelto("-C")], str(tmp_path)) == []


def test_i_nomi_fuori_dalla_codepage_arrivano_a_pe_col_nome_corto(tmp_path):
    """R62: pgn-extract riceve gli argomenti nella codepage di Windows, e un
    sorgente come Kasparov in cirillico non si apriva."""
    import subprocess

    cartella = tmp_path / "Čech Łódź"
    cartella.mkdir()
    sorgente = cartella / "Каспаров.pgn"
    sorgente.write_text('[Event "E"]\n[White "A"]\n[Black "B"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n', encoding="utf-8")
    assert pgn_extract.per_pe("C:/semplice/città.pgn") == "C:/semplice/città.pgn"
    corto = pgn_extract.per_pe(str(sorgente))
    if corto is None:
        pytest.skip("il disco delle prove non ha i nomi corti 8.3")
    assert corto.isascii()
    uscita = cartella / "uscita è.pgn"
    comando = pgn_extract.argomenti(PE_VERO, [], str(sorgente), str(uscita) + ".pgn-extract.tmp", per_pgn_extract=True)
    assert all(parte.encode("mbcs") for parte in comando)
    subprocess.run(comando, cwd=str(tmp_path), capture_output=True, timeout=60, check=False)
    assert "1. e4 e5" in (cartella / "uscita è.pgn.pgn-extract.tmp").read_text(encoding="utf-8", errors="replace")
