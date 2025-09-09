from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import sys
import os

block_cipher = None

a = Analysis(
    ['src/main.py'],  # Main Python script
    pathex=[],  # Additional paths to search for imports
    binaries=[],  # Additional binary files
    datas=[  # Data files to include
        ('resources', 'resources'),
    ],
    hiddenimports=['pygame'],  # Hidden imports not detected automatically
    hookspath=[],  # Custom hooks for PyInstaller
    excludes=[],  # Modules to exclude
    cipher=None,  # Encryption for bytecode (optional)
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Exclude binaries if using COLLECT
    name='Workout_Timer',  # Name of the executable
    debug=False,
    console=False,  # Set to True if you want a console window
    icon='resources/icon.ico',  # Optional: Path to the icon file
    splash='resources/splash.png', # Optional: Path to splash screen image
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='Workout_Timer'
)