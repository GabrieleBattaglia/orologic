# Orologic: le parole delle due voci del PUB, il gruppo di supporto: la mail che iscrive e quella che chiede aiuto.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Entra al PUB e Chiedi aiuto al PUB, le ultime voci delle impostazioni
della finestra, accanto a Offrimi un caffè (T5a, S2; issue 57 di GBUtils,
richiesta di Gabriele del 21 ottobre 2026, per tutti i programmi del parco
che hanno una finestra). Sul modello di pub.py di MeTeOra e di Ciechino,
senza la casella dei registri degli errori, che Orologic non ha.

Gli indirizzi, le informazioni sul computer e la composizione della mail
vengono da GBUtils, la finestra che la prepara da GBwx, finestra_mail: qui
ci sono soltanto le parole di Orologic, perche' GBUtils non ne ha di sue. La
finestra si apre sempre, anche quando il programma di posta c'e', perche' il
nuovo Outlook di Windows 11 e' spesso associato a mailto anche per chi non lo
usa; senza posta accompagna l'utente un passo alla volta, copiando negli
appunti un campo per volta. Orologic non spedisce mai niente: spedisce
l'utente, se vuole, dopo aver letto e corretto.
"""

from .config import _

PULSANTI = {"apri": _("&Apri nel programma di posta"), "passi": _("&Passo per passo"), "ok": _("&OK"), "chiudi": _("&Chiudi"), "annulla": _("&Annulla")}
SENZA_POSTA = _(
    "Non trovo un programma di posta, oppure non si è aperto: prepariamo la mail un pezzo alla volta, da incollare nella tua "
    "posta, per esempio nella webmail del browser."
)
# Le informazioni del computer nella mail d'aiuto, nell'ordine in cui
# compaiono; quelle che non si leggono restano fuori. Se il programma e'
# compilato lo dice gia' la riga del programma.
ETICHETTE = {
    # Traduttori: le etichette delle informazioni sul computer, nella mail di Chiedi aiuto al PUB.
    "windows": _("Sistema operativo"),
    "windows_versione": _("Versione di Windows"),
    # Traduttori: il numero di build di Windows, come 26100.
    "windows_build": _("Build di Windows"),
    # Traduttori: l'architettura del processore, come AMD64.
    "architettura": _("Architettura"),
    "processore": _("Processore"),
    # Traduttori: quanti processori logici ha il computer.
    "nuclei": _("Nuclei logici"),
    # Traduttori: la memoria RAM del computer.
    "memoria_totale": _("Memoria"),
    "memoria_libera": _("Memoria libera"),
    "lingua": _("Lingua di sistema"),
    "screen_reader": _("Screen reader"),
    # Traduttori: lo schermo del computer, con la sua risoluzione.
    "schermo": _("Schermo"),
    # Traduttori: il ridimensionamento di Windows, come 150%.
    "scala": _("Scala dello schermo"),
    "python": "Python",
}
# Traduttori: le risposte sì e no nelle informazioni sul computer della mail di Chiedi aiuto al PUB.
PAROLE = {True: _("sì"), False: _("no")}
_ALTRA_STRADA = _(
    "Se la mail non compare, torna qui e scegli Passo per passo: ti guido a scriverla nella tua posta, per esempio nella webmail "
    "del browser."
)
_ISCRIVITI = _("Se non sei ancora iscritto al PUB, puoi farlo con Entra al PUB, nelle impostazioni.")


def mail_d_iscrizione():
    """Entra al PUB: le parole della mail che iscrive al gruppo. All'indirizzo
    dell'iscrizione Google non legge oggetto e testo, e risponde con una mail
    di conferma: nei passi basta l'indirizzo."""
    from GBUtils import PUB_ISCRIZIONE

    return {
        "titolo": _("Entra al PUB, il gruppo di supporto"),
        "destinatario": PUB_ISCRIZIONE,
        # Traduttori: l'oggetto della mail che iscrive al PUB; Google non lo legge.
        "oggetto": _("Iscrizione al PUB"),
        "corpo": _("Invia questo messaggio così com'è per iscriverti al PUB. Google ti scriverà per chiederti di confermare."),
        "spiegazione": "\n".join(
            (
                _(
                    "Il PUB è il gruppo di supporto dei programmi di Gabriele Battaglia, una lista di posta su Google Groups, dove si chiede aiuto, si "
                    "segnalano i problemi e si propongono idee."
                ),
                # {programma} lo riempie finestra_mail di GBwx con il nome del
                # programma di posta: qui il segnaposto resta com'e'.
                # Traduttori: {programma} è il programma di posta, come Outlook o Thunderbird.
                _(
                    "Il pulsante Apri nel programma di posta prepara in {programma} la mail che ti iscrive: spediscila così com'è, perché Orologic non "
                    "spedisce niente da solo. Poi Google ti scriverà per chiederti di confermare l'iscrizione: segui le sue istruzioni."
                ).format(programma="{programma}"),
                _ALTRA_STRADA,
            )
        ),
        "passi": (
            # Traduttori: il campo A è quello del destinatario della mail.
            (
                _(
                    "Passo 1 di 2. Scrivi una mail nuova nella tua posta, per esempio nella webmail del browser, e incolla nel campo A l'indirizzo "
                    "dell'iscrizione, che ho copiato negli appunti; poi torna qui e premi OK. L'indirizzo è questo:"
                ),
                PUB_ISCRIZIONE,
            ),
            (
                _(
                    "Passo 2 di 2. Oggetto e testo possono restare vuoti, perché Google non li legge: spedisci la mail così com'è. Google ti scriverà "
                    "per chiederti di confermare l'iscrizione: segui le sue istruzioni. OK chiude questa finestra."
                ),
                None,
            ),
        ),
    }


def mail_d_aiuto(versione, compilato, informazioni):
    """Chiedi aiuto al PUB: le parole della mail al gruppo. L'oggetto dice la
    versione; il testo ha una prima riga da sostituire con la domanda e sotto
    le informazioni: il programma, con la versione e se gira compilato o dai
    sorgenti, e il computer, da informazioni_di_sistema di GBUtils con le
    etichette di qui."""
    from GBUtils import PUB_GRUPPO, righe_informazioni

    # Traduttori: l'oggetto della mail che chiede aiuto al PUB; {versione} è come 9.0.0.
    oggetto = _("Chiedo per Orologic {versione}").format(versione=versione)
    if compilato:
        programma = _("Programma: Orologic {versione}, pacchetto compilato").format(versione=versione)
    else:
        programma = _("Programma: Orologic {versione}, dai sorgenti").format(versione=versione)
    corpo = "\n".join(
        (
            _("Scrivi qui la tua domanda, al posto di questa riga."),
            _("Informazioni su Orologic e sul computer di chi scrive:"),
            programma,
            *righe_informazioni(ETICHETTE, informazioni, PAROLE),
        )
    )
    totale = 4
    passi = (
        # Traduttori: {totale} è il numero dei passi; il campo A è quello del destinatario della mail.
        (
            _(
                "Passo 1 di {totale}. Scrivi una mail nuova nella tua posta, per esempio nella webmail del browser, e incolla nel campo A "
                "l'indirizzo del PUB, che ho copiato negli appunti; poi torna qui e premi OK. L'indirizzo è questo:"
            ).format(totale=totale),
            PUB_GRUPPO,
        ),
        (
            _("Passo 2 di {totale}. Incolla nel campo Oggetto quello che ho copiato negli appunti, poi torna qui e premi OK. L'oggetto è questo:").format(
                totale=totale
            ),
            oggetto,
        ),
        (
            _(
                "Passo 3 di {totale}. Incolla nel testo della mail quello che ho copiato negli appunti, e scrivi la tua domanda al posto della prima "
                "riga; le informazioni su Orologic e sul computer, sotto, puoi cancellarle se preferisci. Poi torna qui e premi OK. Il testo è questo:"
            ).format(totale=totale),
            corpo,
        ),
        # Traduttori: {passo} e {totale} sono lo stesso numero, l'ultimo passo; {iscriviti} è la frase che invita a iscriversi al PUB.
        (
            _("Passo {passo} di {totale}. Spedisci la mail. {iscriviti} OK chiude questa finestra.").format(
                passo=totale, totale=totale, iscriviti=_ISCRIVITI
            ),
            None,
        ),
    )
    return {
        "titolo": _("Chiedi aiuto al PUB"),
        "destinatario": PUB_GRUPPO,
        "oggetto": oggetto,
        "corpo": corpo,
        "spiegazione": "\n".join(
            (
                # Traduttori: {programma} è il programma di posta, come Outlook o Thunderbird; {oggetto} l'oggetto della mail.
                _(
                    "Il pulsante Apri nel programma di posta prepara in {programma} una mail al PUB, il gruppo di supporto dei programmi di "
                    "Gabriele Battaglia, con l'oggetto {oggetto}."
                ).format(programma="{programma}", oggetto=oggetto),
                _(
                    "Scrivi la tua domanda al posto della prima riga del testo; sotto ci sono le informazioni su Orologic e sul tuo computer, utili a "
                    "chi ti risponde, che puoi cancellare se preferisci."
                ),
                # Traduttori: {iscriviti} è la frase che invita a iscriversi al PUB.
                _("Poi spediscila tu: Orologic non spedisce niente da solo. {iscriviti}").format(iscriviti=_ISCRIVITI),
                _ALTRA_STRADA,
            )
        ),
        "passi": passi,
    }
