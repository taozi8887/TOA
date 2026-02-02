# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('levels', 'levels'), ('beatmaps', 'beatmaps'), ('update_config.json', '.'), ('main.py', '.'), ('osu_to_level.py', '.'), ('unzip.py', '.'), ('auto_updater.py', '.')],
    hiddenimports=['requests', 'main', 'osu_to_level', 'unzip', 'auto_updater'],
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
    name='TOA-v0.4.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.png'],
    version='file_version_info.txt',
)
