# PyInstaller build for the portable PC program. Run build.ps1 (it uses a clean venv).
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

APP_MODULES = ["ai_comment", "browser_automation", "config", "database", "youtube_api"]

datas = [
    # app.py is run by Streamlit as a script, so it ships as a file (its imports are hiddenimports).
    ("app.py", "."),
    ("styles.css", "."),
    ("settings.example.yaml", "."),
    ("vendor/im_not_ai", "vendor/im_not_ai"),
]
datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")
datas += collect_data_files("playwright")  # includes driver/node.exe and driver/package
# googleapiclient's discovery documents come from its PyInstaller hook (trimmed below).
datas += collect_data_files("youtube_transcript_api")
datas += collect_data_files("anthropic")

hiddenimports = APP_MODULES + [
    "streamlit.components.v1",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "playwright.async_api",
    "googleapiclient.discovery",
    "youtube_transcript_api",
    "anthropic",
    "yaml",
    "dotenv",
]
hiddenimports += collect_submodules("streamlit")

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "dev_fixtures",  # --ui-dev only; never enabled in the program
        "tkinter", "matplotlib", "scipy", "IPython", "jupyter", "notebook", "pytest",
        "setuptools", "pip", "PyQt5", "PyQt6", "PySide2", "PySide6", "torch",
    ],
    noarchive=False,
)
# The app only calls build("youtube", "v3"): drop the other ~500 Google API documents (~75 MB).
_DOCS = "googleapiclient/discovery_cache/documents/"
a.datas = [d for d in a.datas
           if not d[0].replace("\\", "/").startswith(_DOCS) or d[0].endswith("/youtube.v3.json")
           or d[0].endswith("\\youtube.v3.json")]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarketingAI",
    console=True,  # the console shows status; closing the app window or this console quits
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MarketingAI", upx=False)
