Ecco le specifiche tecniche, le formule matematiche e l'architettura logica estratte dal documento, ripulite dalle parti discorsive e pronte per essere fornite come prompt a una IA per l'implementazione in Python.

### Requisiti di Sistema e Librerie
*   **Linguaggio:** Python 3.6+.
*   **Librerie:** `python-chess`, `numpy`, `math`.
*   **Dipendenze Esterne:** Eseguibile binario locale di Stockfish (versione 15 o superiore).

### 1. Inizializzazione e Connessione al Motore
Il motore deve essere inizializzato tramite interfaccia UCI e interrogato per ottenere l'aspettativa di vittoria (WDL - *Win-Draw-Loss*).

```python
import chess
import chess.engine
import math
import numpy as np

# Inizializzazione di Stockfish
engine_path = "/path/to/stockfish"
engine = chess.engine.SimpleEngine.popen_uci(engine_path) #
```

### 2. Estrazione dell'Aspettativa Probabilistica (Win Expectancy - $W$)
Invece di usare i centipedoni lineari, l'algoritmo calcola le probabilità di vittoria. Tramite l'API di `python-chess`, è possibile estrarre direttamente l'aspettativa normalizzata [0.0, 1.0] usando il modello calibrato di Lichess, che incorpora le probabilità di patta.

```python
# Analisi della posizione (es. profondità 16)
limit = chess.engine.Limit(depth=16)
info = engine.analyse(board, limit)

# Estrazione del punteggio dal punto di vista del Bianco
score = info["score"].white() 

# Ottenimento dell'aspettativa probabilistica W (modello Lichess)
win_expectation = score.wdl(model="lichess").expectation() #
```
*Nota per l'IA:* Qualora non fosse possibile usare `wdl(model="lichess")` tramite API, l'aspettativa $Win\%$ va derivata dai centipedoni grezzi ($cp$) tramite questa funzione logistica sigmoide: 
$Win\% = 50 + 50 \cdot (\frac{2}{1 + \exp(-0.00368208 \cdot cp)} - 1)$.

### 3. Calcolo della Precisione della Singola Mossa ($Accuracy_{mossa}$)
Per ogni mossa giocata, il calcolo della precisione richiede di valutare la perdita di probabilità ($\Delta W$) e applicare una funzione di decadimento esponenziale.

1.  **Calcolo del Delta Probabilistico:** $\Delta W = W_{prima} - W_{dopo}$.
2.  **Conversione in Precisione % (Funzione di decadimento):**
    $Accuracy\% = 103.1668 \cdot \exp(-0.04354 \cdot \Delta W) - 3.1669$.
    *(Il risultato è asintotico: se $\Delta W = 0$, la precisione è 100%; se $\Delta W$ cresce, il punteggio crolla in modo non lineare)*.

### 4. Flusso Logico (Ciclo sulla Partita)
Iterare il file PGN mossa dopo mossa registrando i punteggi in due array numpy separati per Bianco e Nero.

1.  Valutare lo stato iniziale $\rightarrow$ ottenere $W_{prima}$.
2.  Applicare la mossa umana: `board.push(move)`.
3.  Valutare il nuovo stato $\rightarrow$ ottenere $W_{dopo}$. **Attenzione:** La prospettiva deve essere *rigorosamente invertita* o calcolata sempre per lo stesso colore per quantificare il delta correttamente per chi ha mosso.
4.  Calcolare $\Delta W$ e applicare la formula del decadimento esponenziale per ottenere l' $Accuracy_{mossa}$.
5.  Salvare l' $Accuracy_{mossa}$ e il $W_{prima}$ nell'array del giocatore di turno.

### 5. Aggregazione: Calcolo della Game Accuracy Finale
La media aritmetica semplice produce falsi positivi; è richiesta una doppia aggregazione pesata.

1.  **Finestre Scorrevoli e Volatilità ($\sigma$):** Dividere l'array delle probabilità in "finestre scorrevoli" di larghezza proporzionale alla lunghezza della partita. Calcolare la deviazione standard ($\sigma$) del $Win\%$ all'interno di ogni finestra per ottenere la *Volatilità* locale (peso della tensione tattica).
2.  **Media Ponderata sulla Volatilità:** Aggregare le $Accuracy_{mossa}$ usando le volatilità ($\sigma$) calcolate come array di pesi moltiplicatori.
3.  **Media Armonica:** Calcolare la media armonica di tutte le $Accuracy_{mossa}$ dell'array: $\frac{n}{\sum_{i=1}^n \frac{1}{x_i}}$ (penalizza fortemente i "blunder").
4.  **Formula Finale:** $Game\_Accuracy = \frac{Media\_Ponderata + Media\_Armonica}{2}$.

### *Opzionale*: Stima del Rating ELO (Modello Polinomiale)
Se l'implementazione richiede di stimare il punteggio ELO in base alla precisione percentuale calcolata ($Acc$), la funzione polinomiale derivata dai dataset è:
$Rating_{Stimato} \approx 2.05 + 12.9 \cdot Acc - 0.256 \cdot Acc^2 + 0.00401 \cdot Acc^3$.

Per una sintesi estrema avevo tralasciato alcuni dettagli tecnici, ma per un'implementazione **completamente esaustiva** ci sono altre tre specifiche matematiche e di libreria presenti nel documento che dovresti aggiungere al prompt per l'IA:

### 6. Classificazione Tassonomica delle Mosse (Etichettatura)
Se l'implementazione richiede di assegnare un'etichetta testuale alla qualità della mossa (come fa Chess.com), l'algoritmo deve mappare il Delta Probabilistico ($\Delta W$) appena calcolato secondo queste soglie asintotiche:
*   **Migliore (Best):** $\Delta W = 0.00$
*   **Eccellente (Excellent):** $0.00 < \Delta W \le 0.02$
*   **Buona (Good):** $0.02 < \Delta W \le 0.05$
*   **Imprecisione (Inaccuracy):** $0.05 < \Delta W \le 0.10$
*   **Errore (Mistake):** $0.10 < \Delta W \le 0.20$
*   **Grave Errore (Blunder):** $0.20 < \Delta W \le 1.00$

### 7. Gestione Automatica degli Scacchi Matti
Un'informazione fondamentale per il codice Python: **l'IA non deve scrivere eccezioni o blocchi `try/except` per gestire i punteggi di scacco matto** (es. `Mate(5)` restituiti dal motore). La funzione `score.wdl().expectation()` della libreria `python-chess` gestisce già questi casi in modo nativo ed elegante, convertendo un matto inevitabile direttamente nei float estremi `1.0` (vittoria) o `0.0` (sconfitta), prevenendo qualsiasi crash matematico.

### 8. Varianti per il Parametro WDL
Nella chiamata `score.wdl(model="lichess")`, il modello "lichess" è raccomandato perché condensa nativamente le probabilità di patta e ignora la profondità dei nodi (*ply*). Tuttavia, l'IA deve sapere che l'API supporta alternative se si vogliono usare calibrazioni pure di Stockfish:
*   `model="sf"` o `model="sf16"` (utilizza la calibrazione interna dell'ultima versione di Stockfish).
*   `model="sf15"` o `model="sf14"` (per retrocompatibilità storica e riproducibilità numerica su vecchie partite).
