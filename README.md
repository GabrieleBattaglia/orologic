# Orologic: Orologio Scacchistico con PGN

## Indice

1.  [Introduzione](#introduzione)
2.  [Requisiti](#requisiti)
3.  [Installazione](#installazione)
4.  [Utilizzo](#utilizzo)
    *   [Schermata Iniziale](#schermata-iniziale)
    *   [Menù Principale](#menù-principale)
    *   [Creazione di un Orologio](#creazione-di-un-orologio)
    *   [Visualizzazione degli Orologi Salvati](#visualizzazione-degli-orologi-salvati)
    *   [Eliminazione di un Orologio](#eliminazione-di-un-orologio)
    *   [Modifica delle Informazioni PGN Predefinite](#modifica-delle-informazioni-pgn-predefinite)
    *   [Avvio di una Partita](#avvio-di-una-partita)
    *   [Comandi Durante la Partita](#comandi-durante-la-partita)
    *   [Salvataggio della Partita (PGN)](#salvataggio-della-partita-pgn)
5. [Descrizione Dettagliata delle Funzioni](#descrizione-dettagliata-delle-funzioni)
6.  [Formato Orario](#formato-orario)
7.  [Note sulla Nomenclatura Scacchistica](#note-sulla-nomenclatura-scacchistica)
8.  [Crediti](#crediti)
9.  [Licenza](#licenza)

## 1. Introduzione <a name="introduzione"></a>

**Orologic** è un'applicazione Python per la gestione del tempo in partite di scacchi.  Fornisce un orologio scacchistico virtuale, permettendo di impostare tempi diversi per i giocatori (Bianco e Nero), gestire incrementi, fasi multiple e allarmi sonori.  Orologic registra le mosse in formato PGN (Portable Game Notation), lo standard per la memorizzazione di partite di scacchi, e permette di salvare e caricare configurazioni di orologio personalizzate.

## 2. Requisiti <a name="requisiti"></a>

*   Python 3.6 o superiore.
*   Librerie Python:
    *   `python-chess` (per la gestione della scacchiera e delle mosse)
    *   `GBUtils` (per le funzioni interne del programma)
    *   `dateutil` (per calcoli con date e tempi)
    *   `webbrowser` (per aprire il manuale)

## 3. Installazione <a name="installazione"></a>

1.  **Clonare il repository:**
    ```bash
    git clone https://github.com/GabrieleBattaglia/orologic.git
    cd tuo_repository
    ```

2.  **Installare le librerie richieste:**
    ```bash
    pip install python-chess python-dateutil
    ```
    per GBUtils, la puoi scaricare clonando:
    git clone https://github.com/GabrieleBattaglia/GBUtils.git
    Se `pip` non è disponibile, potresti dover usare `pip3`.

## 4. Utilizzo <a name="utilizzo"></a>

Per eseguire l'applicazione, aprire un terminale nella cartella del progetto ed eseguire:

```bash
python orologic.py
```
oppure se necessario:
```bash
python3 orologic.py
```

### 4.1 Schermata Iniziale <a name="schermata-iniziale"></a>

All'avvio, l'applicazione mostra informazioni sulla versione, data di creazione e autore.  Viene anche mostrato un messaggio che invita a digitare `?` per visualizzare il menù principale.

### 4.2 Menù Principale <a name="menù-principale"></a>

Il menù principale è accessibile digitando `?` e premendo Invio.  Le opzioni disponibili sono:

*   **`?` - Visualizza il menù:** Mostra questo elenco di opzioni.
*   **`c` - Crea un orologio:** Permette di definire una nuova configurazione di orologio.
*   **`v` - Vedi gli orologi salvati:** Elenca le configurazioni di orologio salvate.
*   **`d` - Elimina un orologio salvato:** Rimuove una configurazione di orologio.
*   **`e` - Modifica info default per PGN:** Permette di impostare i valori predefiniti per i tag PGN (Evento, Sito, Round).
*   **`m` - Visualizza il manuale:** Apre questo file `README.md` nel browser predefinito.
*   **`g` - Inizia a giocare:** Avvia una nuova partita utilizzando una configurazione di orologio selezionata.
*   **`.` - Esci dall'applicazione:** Termina l'esecuzione del programma.

### 4.3 Creazione di un Orologio (`c`) <a name="creazione-di-un-orologio"></a>

Quando si seleziona "Crea un orologio", l'applicazione guida l'utente attraverso una serie di domande per definire la configurazione:

1.  **Nome dell'orologio:** Un nome univoco per identificare la configurazione (es. "Blitz 5+3").
2.  **Bianco e Nero partono con lo stesso tempo?:**
    *   Rispondere premendo Invio (per *sì*) o `n` (per *no*). Se sì, le impostazioni di tempo saranno uguali per entrambi i giocatori.
3.  **Fasi:** Un orologio può avere fino a 4 fasi.  Per ogni fase:
    *   **Tempo (hh:mm:ss):** Il tempo totale a disposizione per la fase (vedi [Formato Orario](#formato-orario)).
    *   **Incremento in secondi:**  L'incremento di tempo aggiunto *dopo* ogni mossa del giocatore.
    *   **Numero di mosse:** Il numero di mosse da completare *entro* la fase corrente.  Se impostato a 0, la fase dura fino alla fine della partita (utile per l'ultima fase).
    * Se si imposta *Numero di mosse* a *0* non sarà più necessario rispondere alle successive domande di configurazione delle fasi.
4.  **Allarmi:** È possibile impostare fino a 5 allarmi sonori:
    *   **Tempo (in secondi):** Il tempo rimanente in cui l'allarme suonerà.  Ad esempio, un allarme a 30 secondi suonerà quando il tempo rimanente del giocatore attivo raggiungerà i 30 secondi.
5.  **Nota:** Una nota opzionale per descrivere la configurazione (es. "Regolamento torneo").

### 4.4 Visualizzazione degli Orologi Salvati (`v`) <a name="visualizzazione-degli-orologi-salvati"></a>

Questa opzione mostra un elenco numerato degli orologi salvati, con le seguenti informazioni:

*   Nome dell'orologio.
*   Indicatore `B=N` (se i tempi di Bianco e Nero sono uguali) o `B/N` (se diversi).
*   Dettagli delle fasi (tempo e incremento per ogni fase).
*   Eventuali note associate.

### 4.5 Eliminazione di un Orologio (`d`) <a name="eliminazione-di-un-orologio"></a>

Permette di eliminare un orologio salvato.  Viene visualizzato l'elenco degli orologi (come in "Visualizzazione"), e l'utente può selezionare il numero corrispondente all'orologio da eliminare.

### 4.6 Modifica delle Informazioni PGN Predefinite (`e`) <a name="modifica-delle-informazioni-pgn-predefinite"></a>

Questa opzione permette di modificare i valori predefiniti per i tag PGN che verranno utilizzati nelle nuove partite:

*   **Event:** Nome dell'evento (es. "Campionato Sociale").  Il valore predefinito è "Orologic Game".
*   **Site:** Luogo dell'evento (es. "Circolo Scacchistico XYZ").  Il valore predefinito è "Sede sconosciuta".
*   **Round:**  Turno di gioco (es. "1").  Il valore predefinito è "Round 1".

Questi valori predefiniti vengono utilizzati quando si inizia una nuova partita, ma possono essere modificati anche all'inizio di ogni partita.

### 4.7 Avvio di una Partita (`g`) <a name="avvio-di-una-partita"></a>

1.  **Selezione dell'orologio:** Viene visualizzato l'elenco degli orologi salvati.  Selezionare l'orologio da utilizzare inserendo il numero corrispondente.
2.  **Inserimento dati PGN:**
    *   **Nome del bianco:** Nome del giocatore che conduce i pezzi bianchi. Se lasciato vuoto il valore di default è "Bianco".
    *   **Nome del nero:** Nome del giocatore che conduce i pezzi neri. Se lasciato vuoto il valore di default è "Nero".
    *   **Elo del bianco:** Punteggio Elo del giocatore bianco. Se lasciato vuoto il valore di default è "?".
    *   **Elo del nero:** Punteggio Elo del giocatore nero. Se lasciato vuoto il valore di default è "?".
    *   **Event, Site, Round:**  Vengono richiesti questi valori, utilizzando i valori predefiniti (vedi [Modifica delle Informazioni PGN Predefinite](#modifica-delle-informazioni-pgn-predefinite)).  È possibile modificarli o accettare i valori predefiniti premendo Invio.
3.  **Inizio partita:**  Premere Invio per iniziare la partita.

### 4.8 Comandi Durante la Partita <a name="comandi-durante-la-partita"></a>

Durante la partita, l'orologio del giocatore attivo (inizialmente il Bianco) è in esecuzione.  Il prompt mostra:

*   Il numero della mossa (es. `1.`).
*   L'ultima mossa registrata (se presente) (es. `e4`).
*   Un prompt per inserire la mossa successiva (es. `1. e4 `).
* se il gioco è in pausa le sezioni sopra indicate saranno mostrate tra parentesi quadre (es. `[1. e4] `).

Sono disponibili i seguenti comandi, che iniziano con un punto (`.`):

*   **`.1`:** Mostra il tempo rimanente del Bianco.
*   **`.2`:** Mostra il tempo rimanente del Nero.
*   **`.3`:** Confronta i tempi rimanenti e indica quale giocatore è in vantaggio (e di quanto).
*   **`.p`:** Mette in pausa/riavvia il countdown degli orologi.  Quando in pausa, viene visualizzato il tempo trascorso in pausa.
*   **`.q`:** *Solo in pausa:* Annulla l'ultima mossa (sia nella scacchiera che nel PGN).
*   **`.b+X`:** *Solo in pausa:* Aggiunge `X` secondi al tempo del Bianco.  `X` deve essere un numero (es. `.b+5`, `.b+0.5`).
*   **`.b-X`:** *Solo in pausa:* Sottrae `X` secondi al tempo del Bianco.
*   **`.n+X`:** *Solo in pausa:* Aggiunge `X` secondi al tempo del Nero.
*   **`.n-X`:** *Solo in pausa:* Sottrae `X` secondi al tempo del Nero.
*   **`.s`:** Visualizza la scacchiera corrente, inclusi il materiale dei giocatori, ultima mossa giocata ed il FEN della posizione.
*   **`.bianco`:** Assegna la vittoria al Bianco (risultato `1-0`).
*   **`.nero`:** Assegna la vittoria al Nero (risultato `0-1`).
*   **`.patta`:** Assegna la patta (risultato `1/2-1/2`).
*   **`.*`:** Assegna un risultato non definito (`*`) e conclude la partita.
*   **`.c commento`:** Aggiunge un commento alla mossa *precedente*.  Ad esempio, dopo aver inserito la mossa `e4`, digitando `.c Ottima apertura!` si aggiungerà il commento "Ottima apertura!" alla mossa `e4` nel PGN.
* **`.?`:** Mostra elenco dei comandi disponibili.

**Inserimento delle mosse:** Le mosse devono essere inserite in notazione algebrica SAN (Standard Algebraic Notation).  Esempi:

*   `e4` (muove il pedone in e4)
*   `Nf3` (muove il cavallo in f3)
*   `O-O` (arrocco corto)
*   `O-O-O` (arrocco lungo)
*   `exd5` (il pedone in e cattura il pezzo in d5)
*   `Bxf7+` (l'alfiere cattura il pezzo in f7, dando scacco)
*   `Qe8#` (la donna si muove in e8, dando scaccomatto)
*   `a8=Q` (il pedone in a7 si muove in a8 e promuove a donna.)
* `a8=Q+` (il pedone in a7 si muove in a8 e promuove a donna, dando scacco.)

Dopo ogni mossa inserita correttamente, l'applicazione:

1.  Visualizza una descrizione verbale della mossa (es. "il pedone si muove in e4").
2.  Aggiunge l'eventuale incremento al tempo del giocatore.
3.  Passa il turno all'altro giocatore.

### 4.9 Salvataggio della Partita (PGN) <a name="salvataggio-della-partita-pgn"></a>

Al termine della partita (sia per abbandono, scaccomatto, patta, o assegnazione manuale del risultato), il PGN completo della partita viene salvato in un file. Il nome del file è composto da:

`NomeBianco-NomeNero-DataOra.pgn`

Esempio: `Carlsen-Anand-20240315143000.pgn`

## 5. Descrizione Dettagliata delle Funzioni <a name="descrizione-dettagliata-delle-funzioni"></a>
*   **`describe_move(move, board)`:** Questa funzione prende una mossa (oggetto `chess.Move`) e una scacchiera (`chess.Board`) e restituisce una descrizione testuale della mossa in italiano.  Gestisce arrocchi, promozioni, catture (inclusa l'en passant) e scacchi/scaccomatti. Analizza la notazione SAN (Standard Algebraic Notation) della mossa per fornire una descrizione più dettagliata.

*   **`CalculateMaterial(board)`:** Calcola il valore materiale totale del Bianco e del Nero sulla scacchiera, basandosi sui valori standard dei pezzi (Pedone=1, Cavallo=3, Alfiere=3, Torre=5, Donna=9, Re=0).

*   **`normalize_move(m)`:**  "Normalizza" una stringa di mossa inserita dall'utente.  Gestisce le varianti di notazione per gli arrocchi (minuscolo, maiuscolo, "0-0" invece di "O-O") e converte la prima lettera dei pezzi da minuscolo a maiuscolo (es. `nf3` diventa `Nf3`).

*   **`load_db()` / `save_db(db)`:** Carica e salva i dati dell'applicazione (configurazioni degli orologi e impostazioni PGN predefinite) in un file JSON (`orologic_db.json`).

*   **`seconds_to_hms(seconds)`:** Converte un numero di secondi in formato ore:minuti:secondi (`hh:mm:ss`).

*   **`format_time(seconds)`:** Converte un numero di secondi in un formato testuale più leggibile (es. "1 ora, 2 minuti, 30 secondi").

*   **`parse_time_input(prompt)`:** Chiede all'utente di inserire un tempo nel formato `hh:mm:ss` e lo converte in secondi.

*   **`ClockConfig` (classe):** Rappresenta la configurazione di un orologio, inclusi nome, fasi, allarmi e note.  Include metodi per convertire la configurazione in un dizionario (per il salvataggio) e viceversa.

*   **`create_clock()` / `view_clocks()` / `delete_clock()` / `edit_default_pgn()`:** Funzioni per la gestione delle configurazioni degli orologi e delle impostazioni PGN (vedi sezioni dedicate sopra).

*   **`select_clock()`:** Funzione di supporto utilizzata da `delete_clock()` e `start_game()` per permettere all'utente di selezionare un orologio da un elenco.

*   **`CustomBoard` (classe):** Estende la classe `chess.Board` per fornire un metodo `__str__` personalizzato, che visualizza la scacchiera in modo più leggibile, con informazioni aggiuntive (ultima mossa, materiale, ecc.).

*   **`GameState` (classe):**  Rappresenta lo stato di una partita in corso.  Gestisce la scacchiera, la configurazione dell'orologio, i tempi rimanenti, le fasi, il turno corrente, la storia delle mosse e il PGN.  Il metodo `switch_turn()` gestisce il cambio di turno e l'aggiornamento delle fasi.

*   **`clock_thread(game_state)`:**  Funzione eseguita in un thread separato.  Gestisce il countdown del tempo dei giocatori e gli allarmi.

*   **`start_game(clock_config)`:**  Funzione principale per l'avvio e la gestione di una partita.  Gestisce l'input dell'utente (mosse e comandi), aggiorna lo stato di gioco, visualizza la scacchiera e salva il PGN alla fine.

*   **`open_manual()`:** Apre il file `README.md` nel browser web predefinito.

*   **`show_initial_screen()`:** Mostra la schermata iniziale all'avvio dell'applicazione.

*   **`main()`:**  Funzione principale del programma.  Mostra la schermata iniziale e gestisce il ciclo principale dell'applicazione (visualizzazione del menù e gestione delle scelte dell'utente).

## 6. Formato Orario <a name="formato-orario"></a>

Il tempo, sia per le fasi dell'orologio che per gli allarmi, deve essere inserito nel formato `hh:mm:ss`:

*   **`hh`:** Ore (due cifre, es. `01`, `12`).
*   **`mm`:** Minuti (due cifre, es. `05`, `59`).
*   **`ss`:** Secondi (due cifre, es. `00`, `30`).

Esempi:

*   `01:30:00` (1 ora, 30 minuti)
*   `00:05:00` (5 minuti)
*   `00:00:10` (10 secondi)

## 7. Note sulla Nomenclatura Scacchistica <a name="note-sulla-nomenclatura-scacchistica"></a>
* **LETTER_FILE_MAP**: Questo dizionario associa a ogni lettera che identifica una colonna della scacchiera (da *a* ad *h*) il nome corrispondente in italiano, usato per comporre la descrizione verbale delle mosse.
* **PIECE_NAMES**: Contiene la traduzione in italiano dei nomi dei pezzi.

## 8. Crediti <a name="crediti"></a>

*   Sviluppato da: Gabriele Battaglia
*   Data di creazione: 14 Febbraio 2025
*   Versione: 2.1.3
*   Creato con l'ausilio di ChatGPT.

## 9. Licenza <a name="licenza"></a>

Questo progetto è rilasciato sotto licenza [GPL].  Vedi il file `LICENSE` per i dettagli.
```