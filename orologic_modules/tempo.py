# Orologic, modulo tempo: un solo posto per dire e leggere le durate.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
#
# Prima le funzioni di formattazione erano dodici, sparse in sei file, con due
# coppie identiche fra loro e differenze di dettaglio nelle altre: la stessa
# durata poteva uscire come 1 ora, 5 minuti, 3 secondi oppure 1 ore, 5 minuti e
# 3 secondi a seconda di chi la stampava.

from .config import _


def parlato(secondi):
    """Durata detta a parole, per esempio 1 ora, 5 minuti e 3 secondi.

    E' la forma da usare quando il testo viene letto dalla sintesi vocale.
    """
    totale = round(secondi or 0)
    if totale <= 0:
        return _("0 secondi")
    ore, resto = divmod(totale, 3600)
    minuti, sec = divmod(resto, 60)
    parti = []
    if ore:
        parti.append(_("1 ora") if ore == 1 else _("{n} ore").format(n=ore))
    if minuti:
        parti.append(_("1 minuto") if minuti == 1 else _("{n} minuti").format(n=minuti))
    if sec:
        parti.append(_("1 secondo") if sec == 1 else _("{n} secondi").format(n=sec))
    if len(parti) == 1:
        return parti[0]
    return ", ".join(parti[:-1]) + _(" e ") + parti[-1]


def mmss_parlato(secondi):
    """Minuti e secondi detti a parole, usato dagli allarmi."""
    if secondi is None or secondi < 0:
        secondi = 0
    minuti, sec = divmod(int(secondi), 60)
    return _("{m:02d} minuti e {s:02d} secondi").format(m=minuti, s=sec)


def orologio(secondi):
    """Durata in ore, minuti e secondi con due cifre, per esempio 01:30:00."""
    totale = max(0, int(secondi or 0))
    ore, resto = divmod(totale, 3600)
    minuti, sec = divmod(resto, 60)
    return f"{ore:02d}:{minuti:02d}:{sec:02d}"


def compatto(secondi):
    """Forma breve per il prompt: mm:ss, oppure h:mm:ss, oppure con i giorni.

    Serve dove il tempo va letto di continuo e ogni carattere in meno aiuta
    la lettura su display braille.
    """
    totale = max(0, int(secondi or 0))
    minuti, sec = divmod(totale, 60)
    ore, minuti = divmod(minuti, 60)
    giorni, ore = divmod(ore, 24)
    if giorni:
        return _("{g}g").format(g=giorni) + f" {ore:02d}:{minuti:02d}:{sec:02d}"
    if ore:
        return f"{ore}:{minuti:02d}:{sec:02d}"
    return f"{minuti:02d}:{sec:02d}"


def pgn(secondi):
    """Durata nel formato dei tag PGN clk ed emt."""
    totale = max(0, int(secondi or 0))
    ore, resto = divmod(totale, 3600)
    minuti, sec = divmod(resto, 60)
    if ore:
        return f"{ore}:{minuti:02d}:{sec:02d}"
    if minuti:
        return f"{minuti}:{sec:02d}"
    return f"{sec}"


def da_hms(testo):
    """Legge una durata scritta come ore:minuti:secondi.

    Restituisce i secondi, oppure None se il testo non e' utilizzabile: il
    vecchio meno uno come segnale d'errore si confondeva con un valore.
    """
    if not testo:
        return None
    parti = str(testo).strip().split(":")
    if len(parti) != 3:
        return None
    try:
        ore, minuti, sec = (int(p) for p in parti)
    except ValueError:
        return None
    if ore < 0 or not 0 <= minuti <= 59 or not 0 <= sec <= 59:
        return None
    return ore * 3600 + minuti * 60 + sec


def da_mmss(testo):
    """Legge una durata scritta come minuti:secondi. None se non e' valida."""
    if not testo:
        return None
    parti = str(testo).strip().split(":")
    if len(parti) != 2:
        return None
    try:
        minuti, sec = (int(p) for p in parti)
    except ValueError:
        return None
    if minuti < 0 or not 0 <= sec <= 59:
        return None
    return minuti * 60 + sec


def da_testo(testo):
    """Legge una durata in una qualsiasi delle forme accettate.

    Riconosce ore:minuti:secondi, minuti:secondi e i soli secondi, cosi' chi
    inserisce un tempo puo' scriverlo come gli viene comodo.
    """
    if testo is None:
        return None
    grezzo = str(testo).strip()
    if not grezzo:
        return None
    if grezzo.count(":") == 2:
        return da_hms(grezzo)
    if grezzo.count(":") == 1:
        return da_mmss(grezzo)
    try:
        secondi = int(grezzo)
    except ValueError:
        return None
    return secondi if secondi >= 0 else None


def fra_date(inizio, fine):
    """Distanza fra due momenti detta a parole, dagli anni ai minuti."""
    from dateutil.relativedelta import relativedelta

    differenza = relativedelta(fine, inizio)
    parti = []
    if differenza.years:
        parti.append(
            _("1 anno")
            if differenza.years == 1
            else _("{n} anni").format(n=differenza.years)
        )
    if differenza.months:
        parti.append(
            _("1 mese")
            if differenza.months == 1
            else _("{n} mesi").format(n=differenza.months)
        )
    if differenza.days:
        parti.append(
            _("1 giorno")
            if differenza.days == 1
            else _("{n} giorni").format(n=differenza.days)
        )
    if differenza.hours:
        parti.append(
            _("1 ora")
            if differenza.hours == 1
            else _("{n} ore").format(n=differenza.hours)
        )
    if differenza.minutes:
        parti.append(
            _("1 minuto")
            if differenza.minutes == 1
            else _("{n} minuti").format(n=differenza.minutes)
        )
    if not parti:
        return _("meno di un minuto")
    if len(parti) == 1:
        return parti[0]
    return ", ".join(parti[:-1]) + _(" e ") + parti[-1]
