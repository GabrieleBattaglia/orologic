# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['orologic.py'],
    # GBUtils non sta nei pacchetti installati ma accanto al progetto: senza
    # questo percorso PyInstaller non lo troverebbe.
    pathex=[r'E:\git\mine\GBUtils'],
    binaries=[],
    datas=[
        ('locales', 'locales'),
        ('resources', 'resources'),
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
    console=True,
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
