# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['time_tracker.py'],
    pathex=['F:/time_tracker'],
    binaries=[],
    datas=[('config.py', '.')],
    hiddenimports=[
        'win32api', 'win32con', 'win32ts', 'win32gui',
        'win32security', 'win32process', 'win32event', 'pywintypes',
        'pystray', 'pystray._win32',
        'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'ctypes', 'ctypes.wintypes',
        'tkinter', 'tkinter.ttk',
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
    name='TimeTracker',
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
