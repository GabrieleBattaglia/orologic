# Orologic, Tempo: l'orologio nudo e crudo.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

import datetime
import os
import time

from GBUtils import Acusticator, dgt, key, menu

from . import board_utils, clock, config, orologio, ui, version
from .config import _
from .game_flow import async_arbitration_input

# I comandi che Tempo ha in comune con la partita si prendono dall'elenco
# di config, cosi' le due descrizioni non possono divergere. Qui restano
# solo le voci proprie della modalita'.
_COMUNI = (".1", ".2", ".3", ".4", ".5", ".6", ".p", ".b+", ".b-", ".n+", ".n-")
TEMPO_COMMANDS = {chiave: config.DOT_COMMANDS[chiave] for chiave in _COMUNI}
TEMPO_COMMANDS.update(
    {
        ".q": _("Elimina l'ultimo input"),
        ".": _("Termina sessione e mostra il riepilogo"),
        ".?": _("Aiuto (mostra questa lista)"),
    }
)


def StartTempo(clock_config):
    """Inizia la sessione Tempo con l'orologio selezionato."""
    print(_("\nAvvio modalita' Tempo\n"))
    print(
        _(
            "Questa modalita' permette di tenere traccia del tempo senza scacchiera.\n"
            "Al prompt puoi inserire qualsiasi annotazione (o premere INVIO per inserire 'x' e passare il turno).\n"
            "Premi '.' per terminare e salvare il report, o '.?' per la lista dei comandi.\n"
        )
    )

    # Inizializzazione dello stato di gioco (senza logiche scacchistiche)
    game_state = board_utils.GameState(clock_config)
    game_state.white_player = _("Bianco")
    game_state.black_player = _("Nero")
    # Orologio nudo: chi lo usa fa da arbitro, quindi pausa e correzioni.
    game_state.arbitro_presente = True

    nota_sessione = dgt(
        _("Nota per questa sessione, al massimo 250 caratteri: "),
        kind="s",
        smax=250,
    )
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
    orologio.avvia(game_state)

    # Esecuzione del loop principale per Tempo
    _loop_tempo(game_state, clock_config)


def _loop_tempo(game_state, clock_config):
    """Loop principale della modalita' Tempo."""
    game_state.paused_time_start = None
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
            return board_utils.prompt_partita(game_state)

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

            elif ui.comandi_orologio(cmd, game_state) or ui.comandi_pausa(
                cmd, game_state
            ):
                pass
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
                        orologio.aggiungi(
                            game_state,
                            False,
                            -game_state.clock_config["phases"][game_state.black_phase][
                                "black_inc"
                            ],
                        )
                    else:
                        game_state.active_color = "white"
                        game_state.white_moves = max(0, game_state.white_moves - 1)
                        orologio.aggiungi(
                            game_state,
                            True,
                            -game_state.clock_config["phases"][game_state.white_phase][
                                "white_inc"
                            ],
                        )

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

            Acusticator([1000.0, 0.01, 0, config.VOLUME], kind=1, adsr=[0, 0, 100, 0])

            # Aggiungiamo alla cronologia temporanea
            game_state.move_history.append(mossa_str)

            # Applica incrementi o cambi fase
            if game_state.active_color == "white":
                orologio.aggiungi(
                    game_state,
                    True,
                    game_state.clock_config["phases"][game_state.white_phase][
                        "white_inc"
                    ],
                )
            else:
                orologio.aggiungi(
                    game_state,
                    False,
                    game_state.clock_config["phases"][game_state.black_phase][
                        "black_inc"
                    ],
                )

            game_state.switch_turn()

    # --- RIEPILOGO FINALE ---
    end_time = time.time()
    elapsed_real = end_time - start_time

    # Il tempo passato fermi lo accumula ui.comandi_pausa dentro lo stato:
    # qui si aggiunge solo l'ultima pausa, se la sessione finisce con gli
    # orologi ancora fermi.
    total_paused_time = getattr(game_state, "tempo_in_pausa", 0.0)
    if game_state.paused_time_start is not None:
        total_paused_time += end_time - game_state.paused_time_start

    tempo_gioco = elapsed_real - total_paused_time
    tempo_pausa = total_paused_time
    tempo_totale = elapsed_real

    n_mosse = (len(game_state.move_history) + 1) // 2

    # Visualizzazione a schermo
    print("\n" + "" + _("Riepilogo Sessione Tempo") + "")
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
    data_ora_str = config.format_date_italian(now)

    file_content = _("Sessione Orologio - Tempo\n")
    file_content += _("Data e ora: {datetime}\n").format(datetime=data_ora_str)
    file_content += _("Orologio utilizzato: {clock_name}\n").format(
        clock_name=clock_config.get("name", "N/D")
    )
    file_content += _("Controllo del tempo: {tc}\n").format(
        tc=clock.generate_time_control_string(clock_config)
    )

    session_note = getattr(game_state, "session_note", "")
    if session_note:
        file_content += _("Nota: {note}\n").format(note=session_note)

    file_content += _("Lista Mosse:\n")
    for i in range(0, len(game_state.move_history), 2):
        num_mossa = (i // 2) + 1
        w_move = game_state.move_history[i]
        b_move = (
            game_state.move_history[i + 1]
            if i + 1 < len(game_state.move_history)
            else ""
        )
        file_content += f"{num_mossa}. {w_move}" + (f" {b_move}\n" if b_move else "\n")

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
