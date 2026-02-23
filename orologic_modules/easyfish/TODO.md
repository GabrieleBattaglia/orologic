# EasyFish Roadmap & Todo (Updated Feb 23, 2026)

## 1. Core Gameplay & Variants (High Priority)
- [ ] **T. Variants Support**:
    - [ ] Implement `.v` command: Start a new variation branch from current position.
    - [ ] Implement `.vok` command: Close current variant and return to the main line/parent branch.
    - [ ] Update Prompt Logic: Display current variance level (e.g., `15. Qc6 Lvl1 c4 >`) to indicate depth.
    - [ ] Handle "No Variant" error: Handle `.vok` when not in a variant.
- [ ] **AI. Takeback/Undo**: Implement `.u` (or `.q` like Orologic) command to delete/undo the last move made.

## 2. File Management & Navigation
- [ ] **Y. Load Game from File**: Replace the old "Collection" logic with a file browser to load individual `.pgn` files from the `pgn/` folder.
- [ ] **AA. Board to Clipboard**: Copy the ASCII board representation to clipboard (command `.ba`?).

## 3. Analysis Enhancements
- [ ] **U. Auto-Analysis Comment**: Implement command (e.g., `.ac`) to insert current engine analysis directly into the move's comment.
- [ ] **Persistent Settings**: Save analysis settings (multipv, time) to `easyfish.json` so they persist between sessions.

## 4. Accessibility & Board Info
- [ ] **AC. Group Listing**: Add command to list *all* White pieces or *all* Black pieces at once (e.g., `.pw`, `.pb`).
- [ ] **AD. Pinned Pieces**: Logic to identify pinned pieces.
- [ ] **AE. Show Pinned**: Include "pinned" status in piece info output (command `-square`).

## Completed Tasks
- [x] **Refactoring & Architecture**: Modularization, State Management, Orologic Integration (v6.0.0+).
- [x] **Localization**: Native Italian strings, `_()` wrapping.
- [x] **Board Editor**: Full rewrite with intelligent piece handling, smart King management, and native Orologic `CustomBoard` usage.
- [x] **PGN Handling**: Native single-file save with timestamp, clipboard integration, removal of legacy "Collection".
- [x] **Smart Move Parsing**: Robust handling of pawn captures without 'x' and smart fallback for 'b' (Pawn vs Bishop).
- [x] **Analysis Output**: Compact WDL + Score format.
- [x] **Explorer Mode**: Fixed crash on `GetDynamicPrompt`, correct board synchronization.
