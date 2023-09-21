# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ["caribou/cli.py"],
    pathex=["/Users/ouabde_r/signals/caribou"],
    binaries=[],
    datas=[],
    hiddenimports=["packaging"],
    hookspath=[],
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
    name="Caribou",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="icon.icns",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Caribou",
)
app = BUNDLE(
    coll,
    name="Caribou.app",
    icon="icon.icns",
    bundle_identifier=None,
    windowed=True,
    info_plist={
        "NSRequiresAquaSystemAppearance": "No",
        "NSHighResolutionCapable": "True",
    },
)
