# Orologic, strumenti: l'ascolto alla cieca dei suoni della scacchiera interattiva.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
# 21/11/2026: nasce per la tappa 1 della scacchiera, sul modello di
# MeTeOra prototipi\ascolto_effetti.py.

"""L'ascolto alla cieca dei suoni della scacchiera interattiva.

Uso, dalla cartella E:\\git\\tmp\\Orologic-gui, con il via di Gabriele:
  python strumenti\\ascolto_scacchiera.py 1
  python strumenti\\ascolto_scacchiera.py 2
La parte 1 ha tre gruppi: sollevare e posare, dove ogni candidato e' una
coppia, il suono del pezzo sollevato e, mezzo secondo dopo, quello del pezzo
posato; la scacchiera che si apre; il cursore che si ferma al bordo. La
parte 2 ha i sei suoni del no, uno per gruppo. I candidati sono preset della
collezione di GBUtils che nessuno firmava.

In ogni gruppo i candidati, piu' uno di loro ripetuto, estratto a caso, si
danno alle lettere a caso: chi ascolta non sa quale sia quale, ne' quale sia
ripetuto. Prima la rassegna, tutti di fila, una volta ciascuno, dopo la loro
lettera; poi un candidato alla volta, la lettera e due ascolti, e il voto da
1 a 5: r lo riascolta, Escape lo lascia senza voto. Il gruppo si chiude con
il menu comune dei collaudi: r riascolta la rassegna, c commenta, Invio lo
da' per superato. Gli esiti, con le lettere sciolte, vanno in
strumenti\\ascolto_scacchiera_esiti.txt, con in fondo il riepilogo dei voti;
a schermo, durante l'ascolto, niente nomi.
"""

import json
import os
import random
import sys
import time

from collaudo_comune import Esiti, gruppo
from GBUtils import Acusticator, key

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
ESITI = os.path.join(QUI, "ascolto_scacchiera_esiti.txt")
INTESTAZIONE = "Orologic 9: ascolto alla cieca dei suoni della scacchiera interattiva, tappa 1."
GRUPPI = (
    (
        "sollevare e posare",
        (
            ("filtro_polisportiva", "filtro_comune"),
            ("casella_usciti_spuntata", "casella_usciti_tolta"),
            ("casella_ritirati_spuntata", "casella_ritirati_tolta"),
            ("casella_ritirati_che_allenano_spuntata", "casella_ritirati_che_allenano_tolta"),
            ("casella_disponibili_oggi_spuntata", "casella_disponibili_oggi_tolta"),
            ("soffio_che_riparte", "soffio_che_rallenta"),
        ),
    ),
    ("la scacchiera che si apre", ("banda_che_si_allarga", "due_ante_che_si_aprono", "casella_liberi_spuntata", "soffio_che_prende_velocita")),
    ("il cursore al bordo", ("filtro_posto_attuale", "filtro_classe_peggiore", "filtro_provincia", "filtro_tratto_indifferente", "filtro_visus")),
)
# La seconda parte, i suoni del no, un gruppo per evento, ognuno coi suoi
# candidati, diversi da quelli degli altri gruppi e da quelli gia' scelti.
GRUPPI_DEL_NO = (
    ("la mossa che non vale", ("filtro_tratto_no", "due_cadute_di_quinta", "casella_senza_acciacchi_tolta", "casella_in_vendita_tolta")),
    ("lo spazio su una casa vuota", ("banda_precedente", "casella_usciti_tolta", "casella_ritirati_che_allenano_tolta", "casella_del_computer_tolta")),
    ("Invio senza un pezzo in mano", ("casella_liberi_tolta", "casella_tuoi_tolta", "casella_senza_prelazione_tolta", "casella_disponibili_oggi_tolta")),
    ("un comando che qui non c'e'", ("filtro_mesi_contratto", "filtro_stipendio_massimo", "filtro_costo_massimo", "filtro_valore_minimo")),
    ("la scacchiera solo da guardare", ("orecchio_che_cerca", "spia_che_si_affievolisce", "soffio_che_rallenta", "notifica_tramite_interfaccia_utente_8")),
    ("u quando non ci sono mosse", ("filtro_eta_minima", "filtro_regione", "filtro_indole", "filtro_stipendio_capo")),
)
PARTI = {"1": GRUPPI, "2": GRUPPI_DEL_NO}
LETTERE = "ABCDEFGH"
ASCOLTI = 2
VOTI = "12345"
SILENZIO_INIZIALE = 4.0
# Dopo la lettera, perche' la sintesi finisca di dirla prima del suono.
SILENZIO_LETTERA = 1.5
SILENZIO_RASSEGNA = 2.0
SILENZIO_CANDIDATO = 2.0
SILENZIO_FRA_ASCOLTI = 2.5
# Nella coppia, fra il pezzo sollevato e il pezzo posato.
SILENZIO_DELLA_MOSSA = 0.5


def volume():
    """Il volume di Orologic, dal database del worktree; mezzo, se non c'e'."""
    try:
        with open(os.path.join(RADICE, "settings", "orologic_db.json"), encoding="utf-8") as file:
            return float(json.load(file).get("volume", 0.5))
    except (OSError, ValueError, TypeError):
        return 0.5


VOLUME = volume()


# Le porte verso il mondo, che la prova sostituisce: suono, attesa e tastiera.
def suona(nome):
    Acusticator.play(nome, sync=True, volume=VOLUME)


def pausa(secondi):
    time.sleep(secondi)


def tasto(prompt):
    return key(prompt)


def nome_del_candidato(candidato):
    return " poi ".join(candidato) if isinstance(candidato, tuple) else candidato


def riproduci(candidato):
    """Un candidato: un suono solo, o la coppia della mossa."""
    if isinstance(candidato, tuple):
        suona(candidato[0])
        pausa(SILENZIO_DELLA_MOSSA)
        suona(candidato[1])
    else:
        suona(candidato)


def lettere_a_caso(candidati, caso):
    """Le coppie (lettera, candidato), con i candidati e uno di loro ripetuto,
    tutti in ordine a caso."""
    voci = [*candidati, caso.choice(candidati)]
    caso.shuffle(voci)
    return list(zip(LETTERE, voci, strict=False))


def rassegna(scelte):
    """Tutti i candidati di fila, una volta ciascuno, dopo la loro lettera."""
    print("Rassegna.")
    pausa(SILENZIO_LETTERA)
    for numero, (lettera, candidato) in enumerate(scelte, 1):
        print(f"{lettera}.")
        pausa(SILENZIO_LETTERA)
        riproduci(candidato)
        if numero < len(scelte):
            pausa(SILENZIO_RASSEGNA)
    print("Fine della rassegna.")


def ascolti(candidato):
    for volta in range(ASCOLTI):
        riproduci(candidato)
        if volta < ASCOLTI - 1:
            pausa(SILENZIO_FRA_ASCOLTI)


def voto(lettera, ripeti):
    """Il voto di un candidato, da 1 a 5, o None con Escape; r riascolta."""
    while True:
        scelta = tasto(f"\rVoto per {lettera} da 1 a 5, r ripete, Esc salta\r")
        print()
        if len(scelta) == 1 and scelta in VOTI:
            return int(scelta)
        if scelta in ("r", "R"):
            ripeti()
        elif scelta == "\x1b":
            return None
        else:
            print("Da 1 a 5, r o Escape.")


def ascolta_il_gruppo(numero, quanti, titolo, candidati, esiti, caso):
    """Un gruppo: annuncio, rassegna, ogni lettera con il suo voto, e il menu.
    Restituisce le terne (lettera, candidato, voto), o None se si salta."""
    scelte = lettere_a_caso(candidati, caso)
    if not gruppo(f"{numero} di {quanti}, {titolo}", len(scelte), "lettere"):
        return None
    pausa(SILENZIO_INIZIALE)
    rassegna(scelte)
    voti = []
    for lettera, candidato in scelte:
        print(f"Lettera {lettera}, {ASCOLTI} volte.")
        pausa(SILENZIO_CANDIDATO)
        ascolti(candidato)
        voti.append((lettera, candidato, voto(lettera, lambda candidato=candidato: ascolti(candidato))))
    misura = "; ".join(f"{lettera} {nome_del_candidato(c)}, {'senza voto' if v is None else f'voto {v}'}" for lettera, c, v in voti)
    esiti.esito(f"{numero} di {quanti}, {titolo}", riproduci=lambda: rassegna(scelte), misura=misura)
    return voti


def riepilogo(tutti):
    """Le righe del riepilogo: per gruppo i candidati dal voto migliore,
    contando il ripetuto con il primo voto, e i due voti del ripetuto, che
    dicono quanto i voti tengono."""
    righe = []
    for titolo, voti in tutti.items():
        primi, ripetuti = {}, []
        for lettera, candidato, v in voti:
            nome = nome_del_candidato(candidato)
            if nome in primi:
                ripetuti.append(f"{nome}: {primi[nome][0]} {primi[nome][1]} e {lettera} {v}")
                continue
            primi[nome] = (lettera, v)
        ordinati = sorted(primi.items(), key=lambda voce: -(voce[1][1] or 0))
        righe.append(f"{titolo}: " + ", ".join(f"{nome} ({lettera}) {'senza voto' if v is None else v}" for nome, (lettera, v) in ordinati) + ".")
        righe.extend(f"  ripetuto, {riga}." for riga in ripetuti)
    return righe


def principale(caso=None, parte="1"):
    caso = caso or random.Random()
    esiti = Esiti(ESITI, INTESTAZIONE)
    gruppi = PARTI[parte]
    tutti = {}
    for numero, (titolo, candidati) in enumerate(gruppi, 1):
        voti = ascolta_il_gruppo(numero, len(gruppi), titolo, candidati, esiti, caso)
        if voti is not None:
            tutti[titolo] = voti
    if tutti:
        with open(ESITI, "a", encoding="utf-8") as file:
            file.write(f"\nRiepilogo della parte {parte}, del " + time.strftime("%Y-%m-%d %H:%M") + "\n")
            file.write("\n".join(riepilogo(tutti)) + "\n")
    print("Ascolto finito, grazie.")
    return tutti


if __name__ == "__main__":
    scelta = sys.argv[1] if len(sys.argv) > 1 else "1"
    if scelta not in PARTI:
        print("Uso: python strumenti\\ascolto_scacchiera.py 1 oppure 2")
        sys.exit(1)
    principale(parte=scelta)
    sys.exit(0)
