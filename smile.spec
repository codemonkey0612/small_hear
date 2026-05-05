# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['smile.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32api', 'pywintypes',
        'pystray', 'pystray._win32',
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['telegram', 'requests', 'matplotlib', 'numpy'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='smile',
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    windowed=True,
    onefile=True,
    icon=None,
)
