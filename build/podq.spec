# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
a = Analysis(
    ['../podq/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('../podq/templates', 'podq/templates')],
    hiddenimports=[
        'faster_whisper',
        'ctranslate2',
        'llama_cpp',
        'fastembed',
        'onnxruntime',
    ],
    hookspath=['hooks'],
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
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='podq',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)
