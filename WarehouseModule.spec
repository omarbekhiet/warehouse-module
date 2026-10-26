# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_exe.py'],
    pathex=[],
    binaries=[],
    datas=[('J:/warehouse-module/app/static', 'app/static'), ('J:/warehouse-module/database', 'database'), ('J:/warehouse-module/requirements.txt', '.'), ('J:/warehouse-module/README.md', '.')],
    hiddenimports=['flask', 'flask_cors', 'openpyxl', 'sqlite3', 'app', 'app.routes', 'app.services', 'app.ai', 'app.database', 'app.config', 'app.utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WarehouseModule',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
