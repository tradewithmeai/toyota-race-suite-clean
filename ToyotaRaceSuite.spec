# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Toyota Race Suite
# Cross-platform configuration for Windows and macOS builds

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all scipy submodules (required for scientific computing)
scipy_hidden = collect_submodules('scipy')
pandas_hidden = collect_submodules('pandas')

# Additional hidden imports that PyInstaller might miss
hidden_imports = [
    'scipy.special._ufuncs_cxx',
    'scipy.linalg.cython_blas',
    'scipy.linalg.cython_lapack',
    'scipy.spatial.transform._rotation_groups',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.skiplist',
    'numpy.core._dtype_ctypes',
    'dearpygui.dearpygui',
    'PIL._tkinter_finder',
] + scipy_hidden + pandas_hidden

# Platform-specific conditional imports
if sys.platform == 'win32':
    hidden_imports.extend([
        'win32gui',
        'win32con',
        'win32api',
    ])

# Data files to include
# Format: (source, destination_in_bundle)
datas = [
    ('assets', 'assets'),
    ('data/sample', 'data/sample'),
]

# Binaries (empty for now, PyInstaller auto-detects most)
binaries = []

a = Analysis(
    ['src/app/main.py'],
    pathex=['src'],  # Add src to path so 'from app.xxx' imports work
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tests',
        'docs',
        'tkinter',
        '_tkinter',
        'matplotlib.tests',
        'numpy.tests',
        'scipy.tests',
        'pandas.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    [],
    name='ToyotaRaceSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for clean presentation
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.png' if sys.platform != 'win32' else None,  # Windows needs .ico
)

# macOS specific: Create .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='ToyotaRaceSuite.app',
        icon='assets/logo.png',
        bundle_identifier='com.toyota.racesuite',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '10.13.0',
        },
    )
