# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py', 'unzip.py', 'osu_to_level.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('levels', 'levels'), ('beatmaps', 'beatmaps')],
    hiddenimports=[],
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
    name='TOA-v0.3.5',
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
    icon=['assets\\box.jpg'],
    version='file_version_info.txt',
)
