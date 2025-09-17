# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files

# รวม data ที่ทำให้ไม่พังเรื่อง Lorem ipsum.txt
datas  = collect_data_files('setuptools')
datas += collect_data_files('jaraco.text', includes=['*.txt'])

# (ตัวเลือก) รวมไฟล์แอปของคุณไปด้วย
datas += [
    ('windows/config/db.json', 'windows/config'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5.QtWebEngineWidgets','PyQt5.QtWebEngineCore','PyQt5.QtWebEngine'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Simbox-V3-TestProgram',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Simbox-V3-TestProgram',
)
