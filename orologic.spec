# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Il percorso di GBUtils lo dice GBUtils stesso, che sta nel percorso di
# Python: cosi' la compilazione riesce da qualunque cartella, anche dal
# worktree del ramo gui, e su una macchina dove i repository stanno altrove.
import GBUtils

GBUTILS_DIR = os.path.dirname(GBUtils.__file__)

# Delle traduzioni al programma servono soltanto i cataloghi compilati: i
# .po sono il testo su cui si lavora, e accanto a loro restano le copie di
# sicurezza e i rapporti degli strumenti di verifica, che nel pacchetto
# pubblico non c'entrano niente.
cataloghi = [
    (str(percorso), str(percorso.parent))
    for percorso in Path("locales").rglob("*.mo")
]

# Dalla 9.0.0 la finestra annuncia con accessible_output2, attraverso
# GBsintesi di GBUtils: nel pacchetto entrano le DLL dei lettori di schermo,
# che la libreria cerca nella sua cartella lib, e le uscite, che GBsintesi
# apre per nome. Restano fuori, come in MeTeOra, MESS e Ciechino, le DLL
# proprietarie di PC-Talker, ZDSR, Dolphin e System Access, che non danno il
# permesso di ridistribuirle, quella a 32 bit di NVDA, e le varianti di
# PortAudio che sounddevice non carica mai su Windows a 64 bit.
lettori = collect_data_files('accessible_output2', include_py_files=False)
FUORI = {
    'pctkusr.dll', 'pctkusr64.dll', 'zdsrapi.dll', 'zdsrapi_x64.dll', 'dolapi.dll', 'saapi32.dll', 'nvdacontrollerclient32.dll',
    'libportaudio.dylib', 'libportaudio32bit.dll', 'libportaudio32bit-asio.dll', 'libportaudio64bit-asio.dll', 'libportaudioarm64.dll',
    'libportaudioarm64-asio.dll',
}


def dentro(voce):
    return os.path.basename(voce[0]).lower() not in FUORI


a = Analysis(
    ['orologic.py'],
    # GBUtils non sta nei pacchetti installati ma accanto al progetto: senza
    # questo percorso PyInstaller non lo troverebbe.
    pathex=[GBUTILS_DIR],
    binaries=[],
    datas=[voce for voce in lettori if dentro(voce)] + cataloghi + [
        ('resources/readme.htm', 'resources'),
        ('resources/changelog.htm', 'resources'),
        ('resources/eco.pgn', 'resources'),
        # La collezione dei suoni, da cui gli allarmi dell'orologio prendono
        # le loro voci per nome: da compilato Acusticator la cerca nella
        # radice del pacchetto, e senza gli allarmi resterebbero muti.
        (str(Path(GBUTILS_DIR, 'Acu_Collection.json')), '.'),
    ],
    # Qui vanno le librerie che PyInstaller non trova da solo, cioe' quelle
    # importate dentro le funzioni invece che in testa al file, e quelle che
    # caricano pezzi di se stesse a runtime.
    hiddenimports=[
        'scipy.signal',
        'sounddevice',
        'numpy',
        'dateutil',
        'dateutil.relativedelta',
        'chess',
        'chess.engine',
        'chess.pgn',
        'GBUtils',
        'pygame',
        'pyperclip',
        'reportlab',
        'reportlab.graphics',
        'reportlab.lib.pagesizes',
        'reportlab.platypus',
        'svglib',
        'svglib.svglib',
        *collect_submodules('accessible_output2.outputs'),
        # Il documento del RichEdit dell'area, che cambia il testo senza
        # toccare il cursore per il braille, in finestra.py.
        'pythoncom',
        'pywintypes',
        'win32com',
        'win32com.client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Entrano nel pacchetto perche' installate nell'ambiente, non perche'
    # servano: sono cinquanta megabyte che ogni utente scaricherebbe per
    # niente. Verificato che reportlab e svglib, cioe' l'esportazione in
    # PDF, funzionino senza.
    excludes=[
        'jedi',
        'matplotlib',
        'pandas',
        'IPython',
        'notebook',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries = [voce for voce in a.binaries if dentro(voce)]
a.datas = [voce for voce in a.datas if dentro(voce)]
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='orologic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # Dalla 9.0.0 Orologic parte nella finestra: senza console. Con --cli la
    # console se la apre da se', avvio.apri_la_console.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='orologic',
)
