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

## Dettagli Implementativi
### Login
Il login utilizza un **Personal API Token** generato dall'utente sul sito di Lichess (OAuth token page). Il token viene validato chiamando l'endpoint `/api/account`. Una volta convalidato, token e username vengono salvati in `orologic_db.json`. L'interfaccia mostra automaticamente il punteggio Elo aggiornato per le modalità principali (Rapid, Blitz, Classical).

