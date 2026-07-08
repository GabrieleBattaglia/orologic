import time
import threading
import os
import datetime
from GBUtils import dgt, Acusticator, key, polipo, menu
from . import config
from . import board_utils
from . import clock
from . import ui
from . import version
from .game_flow import clock_thread, async_arbitration_input

# Inizializzazione localizzazione
lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

TEMPO_COMMANDS = {
    ".1": _("Mostra il tempo rimanente del bianco"),
    ".2": _("Mostra il tempo rimanente del nero"),
    ".3": _("Mostra entrambi gli orologi"),
    ".4": _("Confronta i tempi rimanenti e indica il vantaggio"),
    ".5": _("Stato orologi/pausa"),
    ".6": _("Modifica timing aggiornamento orologio"),
    ".p": _("Pausa/Ripresa"),
    ".b+": _("Aggiunge tempo al bianco (in pausa)"),
    ".b-": _("Sottrae tempo al bianco (in pausa)"),
    ".n+": _("Aggiunge tempo al nero (in pausa)"),
    ".n-": _("Sottrae tempo al nero (in pausa)"),
    ".q": _("Elimina l'ultimo input"),
    ".": _("Termina sessione e mostra il riepilogo"),
    ".?": _("Aiuto (mostra questa lista)"),
}


def StartTempo(clock_config):
    """Inizia la sessione Tempo con l'orologio selezionato."""
    print(_("\nAvvio modalita' Tempo\n"))
    print(_(
        "Questa modalita' permette di tenere traccia del tempo senza scacchiera.\n"
        "Al prompt puoi inserire qualsiasi annotazione (o premere INVIO per inserire 'x' e passare il turno).\n"
        "Premi '.' per terminare e salvare il report, o '.?' per la lista dei comandi.\n"
    ))

    # Inizializzazione dello stato di gioco (senza logiche scacchistiche)
    game_state = board_utils.GameState(clock_config)
    game_state.white_player = _("Bianco")
    game_state.black_player = _("Nero")

    nota_sessione = ""
    while True:
        nota_sessione = dgt(
            _("Inserisci una nota per questa sessione (massimo 250 caratteri): "),
            kind="s"
        )
        if len(nota_sessione) <= 250:
            break
        print(_("Errore: la nota non deve superare i 250 caratteri. Attualmente e' di {len_note} caratteri.").format(len_note=len(nota_sessione)))
    game_state.session_note = nota_sessione

    key(
        _("Premi un tasto qualsiasi per iniziare quando sei pronto..."),
        attesa=7200,
    )

    # Countdown acustico iniziale
    Acusticator(
        [
            "c6",
            0.07,
            0,
            config.VOLUME,
            "p",
            0.93,
            0,
            0.5,
            "c6",
            0.07,
            0,
            config.VOLUME,
            "p",
            0.93,
            0,
            0.5,
            "c6",
            0.07,
            0,
            config.VOLUME,
            "p",
            0.93,
            0,
            0.5,
            "c7",
            0.5,
            0,
            config.VOLUME,
        ],
        kind=1,
        sync=True,
    )

    # Avvio del thread dell'orologio
    threading.Thread(target=clock_thread, args=(game_state,), daemon=True).start()

    # Esecuzione del loop principale per Tempo
    _loop_tempo(game_state, clock_config)


def _loop_tempo(game_state, clock_config):
    """Loop principale della modalita' Tempo."""
    paused_time_start = None
    total_paused_time = 0.0
    start_time = time.time()

    while not game_state.game_over:
        # --- GESTIONE BANDIERINA CADUTA ---
        if game_state.flag_fallen and not game_state.ignore_clock:
            print(_("\nTempo scaduto!"))
            print(
                _(
                    "Premere INVIO per continuare senza orologio, oppure ESC per terminare."
                )
            )
            choice = key(">>> ")
            if choice in ("\x1b", "esc"):
                game_state.game_over = True
                break
            else:
                game_state.ignore_clock = True
                game_state.paused = False
                print(
                    _(
                        "Partita continuata senza limiti di tempo. Usa '.' per terminare."
                    )
                )
                game_state.flag_fallen = False
                continue

        # Generatore di prompt dinamicizzato
        def get_prompt():
            if not game_state.move_history:
                prompt_text = _("Inizio, mossa 0. ")
            elif len(game_state.move_history) % 2 == 1:
                full_move = (len(game_state.move_history) + 1) // 2
                prompt_text = "{num}. {last_move} ".format(
                    num=full_move, last_move=game_state.move_history[-1]
                )
            else:
                full_move = (len(game_state.move_history)) // 2
                prompt_text = "{num}... {last_move} ".format(
                    num=full_move, last_move=game_state.move_history[-1]
                )

            if game_state.paused:
                prompt_text = "[" + prompt_text.strip() + "] "
            elif game_state.ignore_clock:
                prompt_text = "(NoClock) " + prompt_text.strip() + " "

            # Visualizzazione dinamica del tempo al tick dell'orologio (se refresh_interval > 0)
            clock_str = ""
            refresh_interval = getattr(game_state, "refresh_interval", 0)
            if refresh_interval > 0 and not game_state.ignore_clock:
                wt = max(0.0, game_state.white_remaining)
                bt = max(0.0, game_state.black_remaining)

                def fmt(sec):
                    sec = max(0, int(sec))
                    m, s = divmod(sec, 60)
                    h, m = divmod(m, 60)
                    d, h = divmod(h, 24)
                    if d > 0:
                        d_str = _("{d}g").format(d=d)
                        return f"{d_str} {h:02d}:{m:02d}:{s:02d}"
                    if h > 0:
                        return f"{h}:{m:02d}:{s:02d}"
                    return f"{m:02d}:{s:02d}"

                clock_str = f"{fmt(wt)} {fmt(bt)} "

            prefix = "\n" if not game_state.move_history else ""
            return prefix + clock_str + prompt_text

        # Lettura asincrona dell'input
        user_input = async_arbitration_input(game_state, get_prompt)
        if user_input is None:
            continue

        if game_state.flag_fallen and not game_state.ignore_clock:
            continue

        u_input = user_input.strip()

        # Gestione Dot-Comandi
        if u_input.startswith("."):
            cmd = u_input.rstrip(".").lower()

            clock_commands = [
                ".1",
                ".2",
                ".3",
                ".4",
                ".5",
                ".6",
                ".p",
                ".b+",
                ".b-",
                ".n+",
                ".n-",
            ]
            if game_state.ignore_clock and any(
                cmd.startswith(c) for c in clock_commands
            ):
                print(_("Comando non disponibile: orologio disabilitato."))
                continue

            # Punto singolo: termine sessione e riepilogo
            if u_input == ".":
                game_state.game_over = True
                break

            elif cmd == ".?":
                Acusticator(
                    [440.0, 0.3, 0, config.VOLUME, 880.0, 0.3, 0, config.VOLUME],
                    kind=1,
                    adsr=[10, 0, 100, 20],
                )
                menu(
                    TEMPO_COMMANDS,
                    show_only=True,
                    p=_("Comandi disponibili nella modalita' Tempo:"),
                    ordered=False,
                )

            elif cmd == ".1":
                Acusticator(
                    ["a6", 0.14, -1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100]
                )
                ui.report_white_time(game_state)
            elif cmd == ".2":
                Acusticator(
                    ["b6", 0.14, 1, config.VOLUME], kind=1, adsr=[0, 0, 100, 100]
                )
                ui.report_black_time(game_state)
            elif cmd == ".3":
                Acusticator(
                    ["e7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100]
                )
                ui.report_white_time(game_state)
                ui.report_black_time(game_state)
            elif cmd == ".4":
                Acusticator(
                    ["f7", 0.14, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100]
                )
                diff = abs(game_state.white_remaining - game_state.black_remaining)
                adv = (
                    _("bianco")
                    if game_state.white_remaining > game_state.black_remaining
                    else _("nero")
                )
                print(
                    _("{player} in vantaggio di ").format(player=adv)
                    + board_utils.FormatTime(diff)
                )
            elif cmd == ".5":
                if game_state.paused:
                    Acusticator(
                        ["d4", 0.54, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100]
                    )
                    pause_duration = (
                        time.time() - paused_time_start if paused_time_start else 0
                    )
                    hours = int(pause_duration // 3600)
                    minutes = int((pause_duration % 3600) // 60)
                    seconds = int(pause_duration % 60)
                    ms = int((pause_duration - int(pause_duration)) * 1000)
                    print(
                        _("Tempo in pausa da: {duration}").format(
                            duration="{h_str}{m_str}{s_str}{ms_str}".format(
                                h_str=_("{h} ore, ").format(h=hours) if hours else "",
                                m_str=_("{m} minuti, ").format(m=minutes)
                                if minutes or hours
                                else "",
                                s_str=_("{s} secondi e ").format(s=seconds)
                                if seconds or minutes or hours
                                else "",
                                ms_str=_("{ms} ms").format(ms=ms) if ms else "",
                            )
                        )
                    )
                else:
                    Acusticator(
                        ["f4", 0.54, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 100]
                    )
                    player = (
                        game_state.white_player
                        if game_state.active_color == "white"
                        else game_state.black_player
                    )
                    print(_("Orologio di {player} in moto").format(player=player))
            elif cmd == ".6":
                sec = dgt(
                    _("\nInserisci i secondi per l'aggiornamento automatico (0-120, 0 = disattiva): "),
                    kind="i",
                    imin=0,
                    imax=120,
                    default=game_state.refresh_interval,
                )
                game_state.refresh_interval = sec
                print(_("Intervallo di aggiornamento impostato a {s} secondi.").format(s=sec))
                continue
            elif cmd == ".p":
                game_state.paused = not game_state.paused
                if game_state.paused:
                    paused_time_start = time.time()
                    print(_("Orologi in pausa"))
                    Acusticator(
                        [
                            "c5",
                            0.1,
                            1,
                            config.VOLUME,
                            "g4",
                            0.1,
                            0.3,
                            config.VOLUME,
                            "e4",
                            0.1,
                            -0.3,
                            config.VOLUME,
                            "c4",
                            0.1,
                            -1,
                            config.VOLUME,
                        ],
                        kind=1,
                        adsr=[2, 8, 80, 10],
                    )
                else:
                    pause_duration = (
                        time.time() - paused_time_start if paused_time_start else 0
                    )
                    total_paused_time += pause_duration
                    paused_time_start = None
                    Acusticator(
                        [
                            "c4",
                            0.1,
                            -1,
                            config.VOLUME,
                            "e4",
                            0.1,
                            -0.3,
                            config.VOLUME,
                            "g4",
                            0.1,
                            0.3,
                            config.VOLUME,
                            "c5",
                            0.1,
                            1,
                            config.VOLUME,
                        ],
                        kind=1,
                        adsr=[2, 8, 80, 10],
                    )
                    print(_("Pausa durata ") + board_utils.FormatTime(pause_duration))
            elif cmd == ".q":
                if not game_state.move_history:
                    print(_("Nulla da eliminare."))
                    Acusticator(["e3", 0.2, 0, config.VOLUME], kind=2)
                else:
                    # Rimuoviamo l'ultima mossa
                    last_move = game_state.move_history.pop()
                    # Revertiamo il turno e il tempo
                    if game_state.active_color == "white":
                        game_state.active_color = "black"
                        game_state.black_moves = max(0, game_state.black_moves - 1)
                        game_state.black_remaining -= game_state.clock_config["phases"][
                            game_state.black_phase
                        ]["black_inc"]
                    else:
                        game_state.active_color = "white"
                        game_state.white_moves = max(0, game_state.white_moves - 1)
                        game_state.white_remaining -= game_state.clock_config["phases"][
                            game_state.white_phase
                        ]["white_inc"]
                    
                    Acusticator(
                        [
                            "g4",
                            0.1,
                            0,
                            config.VOLUME,
                            "e4",
                            0.1,
                            0,
                            config.VOLUME,
                        ],
                        kind=1,
                    )
                    print(_("Ultimo input '{move}' eliminato.").format(move=last_move))
            elif (
                cmd.startswith(".b+")
                or cmd.startswith(".b-")
                or cmd.startswith(".n+")
                or cmd.startswith(".n-")
            ):
                if game_state.paused:
                    try:
                        adjust = float(cmd[3:])
                        if cmd.startswith(".b+"):
                            Acusticator(
                                [
                                    "d4",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                    "f4",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                    "a4",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                    "c5",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                ],
                                kind=1,
                                adsr=[15, 0, 90, 5],
                            )
                            game_state.white_remaining += adjust
                        elif cmd.startswith(".b-"):
                            Acusticator(
                                [
                                    "c5",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                    "a4",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                    "f4",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                    "d4",
                                    0.15,
                                    -0.5,
                                    config.VOLUME,
                                ],
                                kind=1,
                                adsr=[15, 0, 90, 5],
                            )
                            game_state.white_remaining -= adjust
                        elif cmd.startswith(".n+"):
                            Acusticator(
                                [
                                    "d4",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                    "f4",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                    "a4",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                    "c5",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                ],
                                kind=1,
                                adsr=[15, 0, 90, 5],
                            )
                            game_state.black_remaining += adjust
                        elif cmd.startswith(".n-"):
                            Acusticator(
                                [
                                    "c5",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                    "a4",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                    "f4",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                    "d4",
                                    0.15,
                                    0.5,
                                    config.VOLUME,
                                ],
                                kind=1,
                                adsr=[15, 0, 90, 5],
                            )
                            game_state.black_remaining -= adjust
                        print(
                            _(
                                "Nuovo tempo bianco: {white_time}, nero: {black_time}"
                            ).format(
                                white_time=board_utils.FormatTime(
                                    game_state.white_remaining
                                ),
                                black_time=board_utils.FormatTime(
                                    game_state.black_remaining
                                ),
                            )
                        )
                    except Exception:
                        print(_("Comando non valido."))
            else:
                Acusticator(
                    ["e3", 1, 0, config.VOLUME, "a2", 1, 0, config.VOLUME],
                    kind=3,
                    adsr=[1, 7, 100, 92],
                )
                print(_("Comando non riconosciuto."))

        else:
            # Rilevamento stringa o invio vuoto
            if game_state.paused:
                print(
                    _(
                        "Non e' possibile inserire note mentre il tempo e' in pausa. Riavvia il tempo con .p"
                    )
                )
                Acusticator(["b3", 0.2, 0, config.VOLUME], kind=2)
                continue

            # Se l'utente preme invio a vuoto, viene salvato "x"
            mossa_str = user_input if user_input != "" else "x"

            Acusticator(
                [1000.0, 0.01, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0]
            )

            # Aggiungiamo alla cronologia temporanea
            game_state.move_history.append(mossa_str)

            # Applica incrementi o cambi fase
            if game_state.active_color == "white":
                game_state.white_remaining += game_state.clock_config["phases"][
                    game_state.white_phase
                ]["white_inc"]
            else:
                game_state.black_remaining += game_state.clock_config["phases"][
                    game_state.black_phase
                ]["black_inc"]

            game_state.switch_turn()

    # --- RIEPILOGO FINALE ---
    end_time = time.time()
    elapsed_real = end_time - start_time

    if paused_time_start is not None:
        total_paused_time += (end_time - paused_time_start)

    tempo_gioco = elapsed_real - total_paused_time
    tempo_pausa = total_paused_time
    tempo_totale = elapsed_real

    n_mosse = (len(game_state.move_history) + 1) // 2

    # Visualizzazione a schermo
    print("\n" + "--- " + _("Riepilogo Sessione Tempo") + " ---")
    print(
        _("Tempo rimasto al Bianco: {time}").format(
            time=board_utils.FormatTime(game_state.white_remaining)
        )
    )
    print(
        _("Tempo rimasto al Nero: {time}").format(
            time=board_utils.FormatTime(game_state.black_remaining)
        )
    )
    print(_("Numero di mosse giocate: {n}").format(n=n_mosse))
    print(
        _("Tempo totale di gioco: {time}").format(
            time=board_utils.FormatTime(tempo_gioco)
        )
    )
    print(
        _("Tempo totale in pausa: {time}").format(
            time=board_utils.FormatTime(tempo_pausa)
        )
    )
    print(
        _("Tempo totale + tempo in pausa: {time}").format(
            time=board_utils.FormatTime(tempo_totale)
        )
    )
    print("--------------------------------\n")

    # Salva il file di report
    _salva_report_tempo(
        clock_config,
        game_state,
        n_mosse,
        tempo_gioco,
        tempo_pausa,
        tempo_totale,
    )

    key(_("Premi un tasto qualsiasi per tornare al menu'..."), attesa=7200)


def _salva_report_tempo(
    clock_config,
    game_state,
    n_mosse,
    tempo_gioco,
    tempo_pausa,
    tempo_totale,
):
    """Salva il report testuale della sessione in formato Tempo+data+ora.txt."""
    now = datetime.datetime.now()
    data_ora_str = now.strftime("%d/%m/%Y %H:%M:%S")

    file_content = _("Sessione Orologio - Tempo\n")
    file_content += "================================\n"
    file_content += _("Data e ora: {datetime}\n").format(datetime=data_ora_str)
    file_content += _("Orologio utilizzato: {clock_name}\n").format(
        clock_name=clock_config.get("name", "N/D")
    )
    file_content += _("Controllo del tempo: {tc}\n").format(
        tc=clock.generate_time_control_string(clock_config)
    )
    file_content += "--------------------------------\n\n"

    session_note = getattr(game_state, "session_note", "")
    if session_note:
        file_content += _("Nota: {note}\n").format(note=session_note)
        file_content += "--------------------------------\n\n"

    file_content += _("Lista Mosse:\n")
    for i in range(0, len(game_state.move_history), 2):
        num_mossa = (i // 2) + 1
        w_move = game_state.move_history[i]
        b_move = (
            game_state.move_history[i + 1]
            if i + 1 < len(game_state.move_history)
            else ""
        )
        file_content += f"{num_mossa}. {w_move}" + (
            f" {b_move}\n" if b_move else "\n"
        )

    file_content += "\n--------------------------------\n"
    file_content += _("STATISTICHE FINALI:\n")
    file_content += _("Tempo rimasto al Bianco: {time}\n").format(
        time=board_utils.FormatTime(game_state.white_remaining)
    )
    file_content += _("Tempo rimasto al Nero: {time}\n").format(
        time=board_utils.FormatTime(game_state.black_remaining)
    )
    file_content += _("Numero di mosse giocate: {n}\n").format(n=n_mosse)
    file_content += _("Tempo totale di gioco: {time}\n").format(
        time=board_utils.FormatTime(tempo_gioco)
    )
    file_content += _("Tempo totale in pausa: {time}\n").format(
        time=board_utils.FormatTime(tempo_pausa)
    )
    file_content += _("Tempo totale + tempo in pausa: {time}\n").format(
        time=board_utils.FormatTime(tempo_totale)
    )
    file_content += "================================\n"
    file_content += _("Generato da Orologic V{version}\n").format(
        version=version.VERSION
    )

    data_str = now.strftime("%Y-%m-%d")
    ora_str = now.strftime("%H-%M-%S")
    filename = f"Tempo+{data_str}+{ora_str}.txt"

    txt_path = config.percorso_salvataggio(os.path.join("txt", filename))
    os.makedirs(os.path.dirname(txt_path), exist_ok=True)
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        print(_("Report salvato in: {path}").format(path=txt_path))
    except Exception as e:
        print(_("Errore nel salvataggio del report: {error}").format(error=e))
