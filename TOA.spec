# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['bootstrap.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('update_config.json', '.'),
        ('launcher.py', '.'),
        ('auto_updater.py', '.')
    ],
    hiddenimports=[
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.models',
        'requests.sessions',
        'requests.structures',
        'urllib3',
        'pygame',
        'pygame.gfxdraw',
        'wave',
        'unzip',
        'osu_to_level',
        'songpack_loader',
        'songpack_ui'
    ],
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
    name='TOA',
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
