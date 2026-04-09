# Orolichess - Integrazione Lichess per Orologic

## Obiettivo
Orolichess è un modulo nativo per `orologic` che permette agli utenti di interfacciarsi con Lichess.org direttamente dall'applicazione principale.

## Architettura e Integrazione
- **Attuale:** Modulo integrato `Mine\orologic\orologic_modules\lichess_app.py`, richiamato dal menu principale di `orologic`.
- **Librerie di base:** Utilizza `GBUtils` per menu e input, e `urllib.request` per le API di Lichess. Salva i dati sensibili (come il token API) all'interno del database principale di Orologic (`orologic_db.json`).

## Struttura del Menu
1. Login / Logout (Dinamico a seconda dello stato)
2. Profilo Lichess
3. Statistiche
4. Amici
5. Risolvi puzzle
6. Guarda una partita
7. Gioca una partita
8. Esci (ritorna a orologic)

## Roadmap di Sviluppo
- [x] FASE 1: Setup dell'infrastruttura di base (menu principale, entry point integrato in orologic).
- [x] FASE 2: Implementazione Login/Logout (gestione del token API personale di Lichess).
- [x] FASE 2.5: Miglioramenti UX (Menu dinamico, visualizzazione Elo al lancio).
- [x] FASE 3: Lettura e visualizzazione dettagliata del Profilo utente (Dati generali ed Elo). Nota: modifica disabilitata per limiti API.
- [x] FASE 4: Visualizzazione super ricca delle Statistiche (separata dal Profilo).
- [x] FASE 5: Gestione Amici (Aggiunta/Rimozione seguiti, messaggistica).
- [x] FASE 6: Visualizzazione e interazione con i Puzzle.
- [x] FASE 7: Guarda una partita (streaming o caricamento PGN).
- [ ] FASE 8: Gioca una partita (interfaccia di gioco da terminale/audio).

## Dettagli Implementativi
### Login
Il login utilizza un **Personal API Token** generato dall'utente sul sito di Lichess (OAuth token page). Il token viene validato chiamando l'endpoint `/api/account`. Una volta convalidato, token e username vengono salvati in `orologic_db.json`. L'interfaccia mostra automaticamente il punteggio Elo aggiornato per le modalità principali (Rapid, Blitz, Classical).

