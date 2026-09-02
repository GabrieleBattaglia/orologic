# Orologic, orologi: creazione e modifica dei controlli di tempo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

from GBUtils import Acusticator, dgt, enter_escape, key, menu

from . import board_utils, config, storage, tempo
from .config import _

# Sotto i due secondi una fase non e' giocabile: la bandierina cadrebbe
# prima che l'orologio parta.
TEMPO_MINIMO_FASE = 2
TEMPO_MINIMO_ALLARME = 1
# Tre orologi per schermata: di piu' scorrerebbero via prima che lo
# screen reader finisca di leggerli.
OROLOGI_PER_SCHERMATA = 3

# Volume gestito via config.VOLUME


def generate_time_control_string(clock_config):
    phases = clock_config["phases"]
    tc_list = []
    for phase in phases:
        moves = phase["moves"]
        base_time = int(phase["white_time"])
        inc = int(phase["white_inc"])
        if moves == 0:
            tc = f"{base_time}+{inc}" if inc > 0 else f"{base_time}"
        else:
            tc = f"{moves}/{base_time}+{inc}" if inc > 0 else f"{moves}/{base_time}"
        tc_list.append(tc)
    return ", ".join(tc_list)


class ClockConfig:
    def __init__(self, name, same_time, phases, alarms, note):
        self.name = name
        self.same_time = same_time
        self.phases = phases
        self.alarms = alarms
        self.note = note

    def to_dict(self):
        return {
            "name": self.name,
            "same_time": self.same_time,
            "phases": self.phases,
            "alarms": self.alarms,
            "note": self.note,
        }


def _chiedi_durata(prompt, minimo=TEMPO_MINIMO_FASE):
    """Chiede una durata e insiste finche' non e' utilizzabile.

    Restituisce i secondi, oppure nulla se l'utente scrive un punto per
    rinunciare. Prima bastava un errore di battitura per creare un
    orologio con una fase da nessun secondo: il controllo cercava il
    valore meno uno, che il modulo tempo non produce piu' da quando le
    durate sono state unificate, e quindi non scattava mai.
    """
    while True:
        risposta = dgt(prompt, kind="s").strip()
        if risposta == ".":
            return None
        secondi = tempo.da_testo(risposta)
        if secondi is None:
            print(
                _(
                    "Tempo non riconosciuto: scrivilo come ore:minuti:secondi, minuti:secondi o secondi."
                )
            )
            continue
        if secondi < minimo:
            print(
                _("Tempo troppo breve: il minimo e' {quanto}.").format(
                    quanto=tempo.parlato(minimo)
                )
            )
            continue
        return secondi


def CreateClock():
    print(_("Creazione orologi"))
    name = dgt(_("Nome dell'orologio: "), kind="s", smin=1)
    Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME], sync=True)
    db = storage.LoadDB()
    if any(c["name"] == name for c in db.get("clocks", [])):
        print(_("Un orologio con questo nome esiste gia'."))
        Acusticator(["a3", 1, 0, config.VOLUME], kind=2)
        return
    same = dgt(
        _("Bianco e Nero partono con lo stesso tempo? (Invio per si', 'n' per no): "),
        kind="s",
    )
    Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])
    # Vale si' anche chi lo scrive invece di premere Invio: prima solo la
    # riga vuota contava, e rispondere s dava due tempi diversi.
    same_time = same.strip().lower() not in ("n", "no")
    phases = []
    phase_count = 0
    while phase_count < 4:
        phase = {}
        if same_time:
            total_seconds = _chiedi_durata(
                _("Tempo (hh:mm:ss) per fase {num}, punto per annullare: ").format(
                    num=phase_count + 1
                )
            )
            if total_seconds is None:
                print(_("Creazione dell'orologio annullata."))
                return
            inc = dgt(
                _("Incremento in secondi per fase {num}: ").format(num=phase_count + 1),
                kind="i",
                imin=0,
            )
            phase["white_time"] = phase["black_time"] = total_seconds
            phase["white_inc"] = phase["black_inc"] = inc
        else:
            total_seconds_w = _chiedi_durata(
                _(
                    "Tempo per il bianco (hh:mm:ss) fase {num}, punto per annullare: "
                ).format(num=phase_count + 1)
            )
            if total_seconds_w is None:
                print(_("Creazione dell'orologio annullata."))
                return
            inc_w = dgt(
                _("Incremento per il bianco fase {num}: ").format(num=phase_count + 1),
                kind="i",
                imin=0,
            )
            total_seconds_b = _chiedi_durata(
                _(
                    "Tempo per il nero (hh:mm:ss) fase {num}, punto per annullare: "
                ).format(num=phase_count + 1)
            )
            if total_seconds_b is None:
                print(_("Creazione dell'orologio annullata."))
                return
            inc_b = dgt(
                _("Incremento per il nero fase {num}: ").format(num=phase_count + 1),
                kind="i",
                imin=0,
            )
            phase["white_time"] = total_seconds_w
            phase["black_time"] = total_seconds_b
            phase["white_inc"] = inc_w
            phase["black_inc"] = inc_b
        Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])
        moves = dgt(
            _("Numero di mosse per fase {num} (0 per terminare): ").format(
                num=phase_count + 1
            ),
            kind="i",
            imin=0,
        )
        phase["moves"] = moves
        phases.append(phase)
        if moves == 0:
            break
        phase_count += 1
    alarms = []
    num_alarms = dgt(
        _("Numero di allarmi da inserire (max 5, 0 per nessuno): "),
        kind="i",
        imax=5,
        imin=0,
        default=0,
    )
    for i in range(num_alarms):
        sec = _chiedi_durata(
            _(
                "Inserisci il tempo (mm:ss) per l'allarme {num}, punto per annullare: "
            ).format(num=i + 1),
            minimo=TEMPO_MINIMO_ALLARME,
        )
        if sec is None:
            print(_("Creazione dell'orologio annullata."))
            return
        alarms.append(sec)
        Acusticator(["f7", 0.09, 0, config.VOLUME, "d4", 0.07, 0, config.VOLUME])
    note = dgt(
        _("Inserisci una nota per l'orologio (opzionale): "), kind="s", default=""
    )
    # Il controllo finale sui dati non serve piu': ogni durata viene
    # verificata quando la si inserisce, e chi sbaglia se la vede
    # richiedere subito invece di perdere tutto alla fine.
    Acusticator(
        [
            "f7",
            0.09,
            0,
            config.VOLUME,
            "d5",
            0.07,
            0,
            config.VOLUME,
            "p",
            0.1,
            0,
            0,
            "d5",
            0.07,
            0,
            config.VOLUME,
            "f7",
            0.09,
            0,
            config.VOLUME,
        ]
    )
    new_clock = ClockConfig(name, same_time, phases, alarms, note)

    def aggiungi(db_aggiornato):
        db_aggiornato.setdefault("clocks", []).append(new_clock.to_dict())

    storage.UpdateDB(aggiungi)
    print(_("Orologio creato e salvato."))


def _durata_con_incremento(secondi, incremento):
    """Durata detta a parole, con l'incremento se c'e'."""
    if incremento:
        return _("{t} piu' {i} di incremento").format(
            t=tempo.parlato(secondi), i=tempo.parlato(incremento)
        )
    return tempo.parlato(secondi)


def _descrivi_orologio(numero, orologio):
    """Righe che descrivono un orologio, pensate per essere ascoltate.

    Prima era una tabella con sigle e abbreviazioni, B=N F1:01:30:00+30,
    che alla sintesi vocale non diceva quasi nulla e taceva del tutto il
    numero di mosse per fase.
    """
    righe = [f"{numero}. {orologio['name']}"]
    nota = (orologio.get("note") or "").strip()
    if nota:
        righe.append(f"  {nota}")
    stesso_tempo = orologio.get("same_time", True)
    righe.append(
        _("  Tempo uguale per i due colori")
        if stesso_tempo
        else _("  Tempi distinti per bianco e nero")
    )
    for indice, fase in enumerate(orologio.get("phases", []), 1):
        if stesso_tempo:
            righe.append(
                _("  fase {n}: {t}").format(
                    n=indice,
                    t=_durata_con_incremento(fase["white_time"], fase["white_inc"]),
                )
            )
        else:
            righe.append(
                _("  fase {n}, bianco: {t}").format(
                    n=indice,
                    t=_durata_con_incremento(fase["white_time"], fase["white_inc"]),
                )
            )
            righe.append(
                _("  fase {n}, nero: {t}").format(
                    n=indice,
                    t=_durata_con_incremento(fase["black_time"], fase["black_inc"]),
                )
            )
        mosse = fase.get("moves", 0)
        righe.append(
            _("  per: {n} mosse").format(n=mosse)
            if mosse
            else _("  per: tutte le mosse restanti")
        )
    allarmi = orologio.get("alarms") or []
    if allarmi:
        righe.append(
            _("  allarmi a: {elenco}").format(
                elenco=", ".join(tempo.parlato(a) for a in allarmi)
            )
        )
    else:
        righe.append(_("  nessun allarme"))
    return righe


def _scorri_a_blocchi(blocchi, quanti=OROLOGI_PER_SCHERMATA):
    """Mostra i blocchi qualche pezzo per volta, aspettando un tasto.

    Il pager di menu conta le voci a una riga e separa le pagine con una
    fila di trattini: qui ogni orologio occupa piu' righe e i separatori
    grafici non si leggono, quindi si contano i blocchi e lo si dice a
    parole. Restituisce vero se si e' arrivati in fondo, falso se si e'
    usciti con ESC.
    """
    totale = len(blocchi)
    mostrati = 0
    while mostrati < totale:
        gruppo = blocchi[mostrati : mostrati + quanti]
        for righe in gruppo:
            for riga in righe:
                print(riga)
        primo = mostrati + 1
        mostrati += len(gruppo)
        if mostrati >= totale:
            return True
        # Il ritorno carrello in apertura e in chiusura porta il cursore
        # di sistema su questa riga, cosi' lo screen reader e il display
        # braille ci restano sopra mentre si decide se continuare.
        avviso = _(
            "Orologi {a} a {b} di {n}, ESC per uscire, un altro tasto continua"
        ).format(a=primo, b=mostrati, n=totale)
        if key("\r" + avviso + "\r") == "\x1b":
            return False
    return True


def ViewClocks():
    print(_("Orologi salvati"))
    db = storage.LoadDB()
    if not db.get("clocks"):
        print(_("Nessun orologio salvato."))
        return
    blocchi = [
        _descrivi_orologio(numero, orologio)
        for numero, orologio in enumerate(db["clocks"], 1)
    ]
    # Chi esce con ESC ha gia' detto di voler tornare al menu: chiedergli
    # un altro tasto sarebbe una domanda in piu' per niente.
    if _scorri_a_blocchi(blocchi):
        key(_("\nPremi un tasto per tornare al menu..."))
    Acusticator(["f7", 0.013, 0, config.VOLUME])


def SelectClock(db=None):
    if not db:
        db = storage.LoadDB()
    if not db.get("clocks"):
        Acusticator(["c3", 0.72, 0, config.VOLUME], kind=2)
        print(_("Nessun orologio salvato."))
        return None
    choices = {}
    STILE_MENU_NUMERICO = db.get("menu_numerati", False)
    for c in db["clocks"]:
        fasi = "".join(
            [
                " F{n}:{t}+{i}".format(
                    n=j + 1,
                    t=board_utils.SecondsToHMS(p["white_time"]),
                    i=p["white_inc"],
                )
                for j, p in enumerate(c["phases"])
            ]
        )
        choices[c["name"]] = "{ind}{fasi}".format(
            ind="B=N" if c["same_time"] else "B/N", fasi=fasi
        )
    choice = menu(choices, show=True, keyslist=True, numbered=STILE_MENU_NUMERICO)
    if choice:
        Acusticator(["f7", 0.013, 0, config.VOLUME])
        return next((c for c in db["clocks"] if c["name"] == choice), None)
    return None


def DeleteClock(db=None):
    print(_("Eliminazione di un orologio salvato"))
    Acusticator(["b4", 0.02, 0, config.VOLUME, "d4", 0.2, 0, config.VOLUME])
    orologio = SelectClock(db)
    if orologio and enter_escape(
        _("Sei sicuro di voler eliminare {name}? (INVIO per si', ESC per no): ").format(
            name=orologio["name"]
        )
    ):
        nome = orologio["name"]

        def elimina(db_aggiornato):
            db_aggiornato["clocks"] = [
                c for c in db_aggiornato.get("clocks", []) if c.get("name") != nome
            ]

        storage.UpdateDB(elimina)
        Acusticator(["c4", 0.025, 0, config.VOLUME])
        print(_("Orologio eliminato."))
