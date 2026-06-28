# Piano di Sviluppo — Ricerca PGN (Issue #25)

## Panoramica

Nuovo modulo `pgn_search.py` in `orologic_modules/` che implementa la ricerca e l'esplorazione interattiva di archivi PGN multi-partita. L'utente accede alla funzione dal menu principale tramite la nuova voce **"Ricerca PGN"**.

---

## Architettura

### File coinvolti

| File | Azione |
|------|--------|
| `orologic_modules/pgn_search.py` | **NUOVO** — Modulo principale con tutta la logica |
| `orologic_modules/config.py` | Aggiunta voce `"ricerca": _("Ricerca PGN")` a `MENU_CHOICES` |
| `orologic.py` | Import del modulo + gestione `elif scelta == "ricerca"` nel loop principale |

### Dipendenze riutilizzate dal progetto

- `board_utils.CopyPgnGame(game)` — copia sicura per l'analisi
- `engine.AnalyzeGame()` / `engine.AnalisiAutomatica()` — analisi partita esistente
- `menu()`, `dgt()`, `enter_escape()`, `key()` da `GBUtils`
- `Acusticator` per feedback sonoro
- `pyperclip` per la lettura degli appunti
- `chess` / `chess.pgn` per la navigazione dei nodi

---

## Flusso Utente Dettagliato

### 1. Ingresso e Caricamento

1. L'utente seleziona **"Ricerca PGN"** dal menu principale
2. Il modulo legge gli appunti tramite `pyperclip.paste()`
3. Determina se il contenuto è:
   - Un **percorso file** (es. `E:\archivi\fischer.pgn`) → legge il file
   - Un **URL** (es. `https://...`) → scarica il contenuto
   - **Testo PGN** diretto → lo usa così com'è
4. Parsa tutte le partite con `chess.pgn.read_game()` in loop (parsing leggero, per velocità su archivi grandi)
5. **Validazione**: se il numero di partite è < 20, avvisa l'utente e chiede se proseguire ugualmente (`enter_escape`)
6. Per archivi molto grandi, mostra un messaggio di caricamento con contatore partite

### 2. Statistiche Iniziali

Dopo il caricamento, mostra un riepilogo:

```
=== Archivio PGN Caricato ===
Partite totali: 6.794

--- Statistiche per il Bianco ---
  Vittorie:  2.341 (34.5%)
  Patte:     1.826 (26.9%)
  Sconfitte: 2.237 (32.9%)
  Altre/ND:    390 (5.7%)

--- Statistiche per il Nero ---
  Vittorie:  2.237 (32.9%)
  Patte:     1.826 (26.9%)
  Sconfitte: 2.341 (34.5%)
  Altre/ND:    390 (5.7%)

Giocatori univoci:    284
Eventi univoci:       47
Anni univoci:         23 (1972 - 1994)
Aperture ECO univoche: 89
```

### 3. Filtri Interattivi

L'utente accede a un sottomenu filtri. **Ad ogni filtro applicato viene aggiornato il conteggio dei risultati rimanenti.**

Menu filtri (loop con `menu()`):

```
Partite corrispondenti: 6.794 di 6.794

1. Giocatore Bianco: [qualsiasi]
2. Giocatore Nero: [qualsiasi]
3. Giocatore (bianco o nero): [qualsiasi]
4. Risultato: [qualsiasi]
5. ELO minimo: [nessun limite]
6. ELO massimo: [nessun limite]
7. Evento: [qualsiasi]
8. Anno dal: [nessun limite]
9. Anno al: [nessun limite]
10. Codice ECO: [qualsiasi]
11. Azzera filtri
12. >>> Procedi all'albero delle aperture
```

**Dettaglio filtri:**

| Filtro | Input | Logica |
|--------|-------|--------|
| Giocatore Bianco | stringa via `dgt(kind="s")` | `filtro.lower() in header["White"].lower()` (operatore `in`) |
| Giocatore Nero | stringa via `dgt(kind="s")` | `filtro.lower() in header["Black"].lower()` (operatore `in`) |
| Giocatore (B o N) | stringa via `dgt(kind="s")` | cerca in **entrambi** i campi White e Black con `in` |
| Risultato | sottomenu: 1-0, 0-1, 1/2-1/2 | match esatto su `Result` |
| ELO minimo | intero via `dgt(kind="i")` | `max(WhiteElo, BlackElo) >= valore` |
| ELO massimo | intero via `dgt(kind="i")` | `min(WhiteElo, BlackElo) <= valore` |
| Evento | stringa via `dgt(kind="s")` | `filtro.lower() in header["Event"].lower()` |
| Anno dal/al | intero via `dgt(kind="i")` | range su anno estratto dal campo `Date` |
| Codice ECO | stringa via `dgt(kind="s")` | match prefisso su `ECO` header (es. "B" matcha "B01", "B15" ecc.) |

- **Stringa vuota** (Invio senza digitare) = filtro rimosso / qualsiasi
- Partite senza ELO header vengono escluse **solo** se è impostato un filtro ELO

### 4. Albero delle Aperture

Dopo aver confermato i filtri, si entra nella navigazione ad albero.

#### Visualizzazione

```
Partite filtrate: 2.341
Ramo: 1. e4 e5 2. Nf3 | 876 partite | B:52% P:30% N:18%

Mosse disponibili:
1. Nc6 (654 partite) = 74.7% | B:53% P:29% N:18%
2. d6 (132 partite) = 15.1% | B:58% P:24% N:18%
3. Nf6 (68 partite) = 7.8%  | B:49% P:32% N:19%
4. f5 (22 partite) = 2.5%   | B:64% P:18% N:18%

0 = Sfoglia le partite del ramo attuale
```

Ogni ramo mostra:
- Numero di partite e percentuale sul totale
- **Statistiche W/D/L** (Bianco% / Patta% / Nero%) per valutare la forza di ogni continuazione

Il **breadcrumb** del ramo corrente include un mini-riepilogo statistico.

#### Mappa Tasti per la Navigazione (ispirata all'editor Easyfish)

La navigazione dell'albero usa tasti lettera compatibili con NVDA, seguendo lo schema **WASD-like** già familiare nell'app:

| Tasto | Azione |
|-------|--------|
| `d` | **Scendi nel ramo** — equivale a selezionare il ramo evidenziato (avanti nell'albero) |
| `a` | **Risali di un livello** — torna al ramo padre |
| `w` | **Ramo precedente** — sposta la selezione al ramo sopra nella lista corrente |
| `x` | **Ramo successivo** — sposta la selezione al ramo sotto nella lista corrente |
| `1`..`9` | **Selezione diretta** — salta direttamente al ramo N e ci entra |
| `0` | **Sfoglia partite** — apre il pager con le partite del ramo corrente |
| `s` | **Salva PGN filtrato** — salva su file le partite che passano i filtri correnti (avvisa se non ci sono filtri attivi) |
| `t` | **Ripeti informazioni** — rilegge ramo corrente, statistiche e lista rami |
| `?` | **Aiuto** — mostra la mappa dei tasti |
| `.` | **Esci** — esce dall'albero (torna ai filtri) |

**Comportamento navigazione:**

- Vengono mostrati solo rami con >= 1 partita
- Ordinamento: per quantità di partite decrescente
- Se un ramo ha una sola partita, questa viene automaticamente passata all'analisi
- La selezione ciclica `w`/`x` permette di scorrere i rami senza numeri, utile quando ce ne sono più di 9
- Il tasto `s` salva su file (con `dgt` per il nome) le partite filtrate in formato PGN; se non ci sono filtri attivi avvisa che sarebbe una copia dell'originale e chiede conferma

### 5. Pager Partite (Tasto 0)

Quando l'utente preme 0, le partite del ramo corrente vengono formattate e passate a `menu()`:

Esempio (ramo corrente: `1. e4 e5 2. Nf3`):

```
1. Fischer vs Spassky, 1-0, 2... Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O
2. Kasparov vs Karpov, 1/2, 2... Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O
3. Tal vs Botvinnik, 1-0, 2... d6 3. d4 exd4 4. Nxd4 Nf6
```

- Le mosse di continuazione mostrano le mosse **successive al ramo radice attivo**, limitate a ~5 mosse per leggibilità
- L'utente seleziona una partita dal pager → viene passata all'analisi

### 6. Passaggio all'Analisi

Quando una partita viene selezionata (dal pager o da ramo con una sola partita):

1. Si chiede `enter_escape("Analisi automatica? INVIO=si, ESC=manuale")`
2. Si controlla che il motore sia inizializzato (stessa logica del caso "analizza" nel main)
3. Si passa a `engine.AnalisiAutomatica(CopyPgnGame(game))` o `engine.AnalyzeGame(game)`

---

## Struttura del Modulo `pgn_search.py`

```python
# orologic_modules/pgn_search.py

"""Modulo per la ricerca e l'esplorazione di archivi PGN."""

import os
import io
import urllib.request
import pyperclip
import chess
import chess.pgn
from collections import Counter

from GBUtils import dgt, menu, enter_escape, key, Acusticator
from orologic_modules import board_utils, config, engine


def run():
    """Entry point principale, chiamato dal menu principale."""
    ...

def _carica_archivio():
    """Legge appunti, determina sorgente (file/url/testo), parsa partite.
    Returns: list[chess.pgn.Game] o None
    """
    ...

def _estrai_info(games):
    """Estrae gli headers da ogni partita.
    Returns: list[dict]
    """
    ...

def _mostra_statistiche(games, info_list):
    """Calcola e stampa le statistiche dell'archivio (incluse W/D/L)."""
    ...

def _calcola_wdl(info_list, indici):
    """Calcola percentuali vittoria bianco/patta/nero per un sottoinsieme.
    Returns: (pct_white, pct_draw, pct_black)
    """
    ...

def _menu_filtri(games, info_list):
    """Loop interattivo filtri con conteggio aggiornato.
    Returns: list[int]  # indici partite filtrate
    """
    ...

def _applica_filtri(info_list, filtri):
    """Applica i filtri e restituisce gli indici validi.
    Returns: list[int]
    """
    ...

def _albero_aperture(games, info_list, indici_filtrati):
    """Navigazione interattiva dell'albero con tasti WASD-like."""
    ...

def _mostra_rami(games, indici, ramo_mosse, info_list):
    """Calcola mosse disponibili con statistiche W/D/L per ramo.
    Returns: list[(str, list[int], pct_w, pct_d, pct_b)]
    """
    ...

def _sfoglia_partite(games, indici, ramo_mosse, info_list):
    """Pager per sfogliare le partite del ramo, con mosse di continuazione."""
    ...

def _avvia_analisi(game):
    """Gestisce il passaggio all'analisi (automatica o manuale)."""
    ...
```

---

## Modifiche ai File Esistenti

### `config.py` — Aggiunta voce menu (riga ~221)

```diff
 MENU_CHOICES = {
     "analizza": _("Modalita' analisi partita"),
     "crea": _("Nuovo orologio"),
     "easyfish": _("Easyfish (Interfaccia Accessibile)"),
     "lichess": _("Orolichess (Integrazione Lichess)"),
     "memoboard": _("Memoboard (Allenamento alla cieca)"),
     "elimina": _("Elimina orologio"),
     "arbitra": _("Inizia partita (Arbitraggio)"),
     "tempo": _("Tempo (Orologio nudo e crudo)"),
     "manuale": _("Guida app"),
     "motore": _("Configurazione motore"),
     "nomi": _("Personalizzazione nomi"),
+    "ricerca": _("Ricerca PGN"),
     "impostazioni": _("Impostazioni varie"),
     "vedi": _("Vedi orologi"),
     "volume": _("Regolazione volume"),
     ".": _("Esci"),
 }
```

### `orologic.py` — Import (riga ~33)

```diff
 from orologic_modules import (
     board_utils,
     config,
     storage,
     ui,
     clock,
     engine,
     game_flow,
     version,
     lichess_app,
     cleaner,
     memoboard_app,
     tempo_app,
+    pgn_search,
 )
```

### `orologic.py` — Gestione nel loop (dopo il blocco `elif scelta == "motore"`)

```diff
+        elif scelta == "ricerca":
+            Acusticator(
+                [
+                    "d5", 0.08, -0.5, config.VOLUME,
+                    "a5", 0.08, 0, config.VOLUME,
+                    "f#5", 0.08, 0.5, config.VOLUME,
+                    "d6", 0.12, 0, config.VOLUME,
+                ],
+                kind=1,
+                adsr=[2, 5, 90, 3],
+            )
+            pgn_search.run()
```

---

## Note Tecniche

- Tutte le stringhe utente wrappate in `_()` per la localizzazione
- Il modulo è autosufficiente: nessuna modifica a `board_utils.py`, `engine.py` o `ui.py`
- Per il parsing si usa `chess.pgn.read_game()` in loop (leggero, senza validazione errori stretta)
- Il rientro dall'albero (tasto `a`) usa uno stack di mosse per risalire i livelli
- L'ELO nelle partite PGN è spesso assente: i filtri ELO escludono solo le partite senza ELO
- I tasti di navigazione seguono il pattern WAXD dell'editor Easyfish, già familiare e compatibile con NVDA

## Test Manuali (Superati)

Tutti i test manuali sono stati completati con successo da Gabriele Battaglia (T1, T2, T3, T13, T17, T21).

---

## Post-Test e Rilascio

Dopo aver ricevuto l'OK su questi test:

### 1. Aggiornamento versione e changelog
- Aggiornare `version.py`: versione → `8.7.0`, data di rilascio → data corrente
- Aggiornare `Todo_and_Changelog.txt` in testa al changelog con il formato standard:
  ```
  8.7.0 (data - ora)
  	+ [Core] Nuova funzionalità "Ricerca PGN": caricamento archivi PGN multi-partita da appunti (file, URL o testo), statistiche dettagliate, filtri interattivi (giocatore, ELO, risultato, evento, anno, ECO), navigazione ad albero delle aperture con statistiche W/D/L, pager partite con mosse di continuazione, passaggio diretto all'analisi.
  ```

### 2. Aggiornamento manuale
- Modificare `resources/readme.htm` con una sezione dedicata alla nuova funzionalità

### 3. Procedura di rilascio
Seguire i passi descritti in `mine\docs\Compilazione e invio release.txt`:
1. Verifica aggiornamento dipendenze pip
2. Compilazione con `pyinstaller orologic.spec`
3. Verifica eseguibile `.\dist\orologic.exe`
4. Git: add, commit, tag, push
5. GitHub Release: `gh release create`

**Attendo il tuo OK prima di procedere a ciascuna di queste fasi.**

---

**Questo piano richiede la tua approvazione prima di procedere alla scrittura del codice.**
Se hai domande o modifiche, fammi sapere!
