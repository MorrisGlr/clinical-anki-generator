# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the CAST desktop app (macOS .app bundle).
#
# Build with:
#   pyinstaller cast.spec --clean
#
# The output is dist/CAST.app (macOS).
# build/build_macos.sh wraps it in a .dmg for distribution.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all Flask/Jinja2 data files (templates bundled with those packages)
datas = [
    # CAST server templates and static assets
    ("cast/server/templates", "cast/server/templates"),
    ("cast/server/static", "cast/server/static"),
]

hidden_imports = [
    # Flask internals
    "flask",
    "flask.templating",
    "jinja2",
    "jinja2.ext",
    "werkzeug",
    "werkzeug.serving",
    "werkzeug.debug",
    # CAST packages
    "cast",
    "cast.core",
    "cast.cli",
    "cast.launcher",
    "cast.server",
    "cast.server.app",
    "cast.parsers",
    "cast.parsers.uworld",
    "cast.parsers.amboss",
    "cast.parsers.apgo",
    "cast.parsers.nbme",
    # Third-party
    "bs4",
    "openai",
    "pydantic",
    "pydantic.v1",
    "markdown",
    "dotenv",
    "python_dotenv",
]

a = Analysis(
    ["cast/launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["imgkit", "tkinter", "matplotlib", "numpy", "pandas", "PIL"],
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
    name="CAST",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # suppress terminal window on macOS/Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CAST",
)

# macOS .app bundle
app = BUNDLE(
    coll,
    name="CAST.app",
    icon=None,          # set to "media/cast.icns" once an icon is created
    bundle_identifier="com.morrisaguilar.cast",
    info_plist={
        "CFBundleName": "CAST",
        "CFBundleDisplayName": "CAST — Clinical Anki Study Tool",
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable": True,
        "LSUIElement": False,
    },
)
