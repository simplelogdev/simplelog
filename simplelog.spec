# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for SimpleLog.
  Linux : produces dist/simplelog/ (directory) + wrapped into AppImage / .deb
  macOS : produces dist/SimpleLog.app  (bundle)  + wrapped into .dmg
"""
import os
import sys

block_cipher = None
APP_VERSION = os.environ.get("VERSION", "0.0.0").lstrip("v")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        "boto3",
        "botocore",
        "botocore.handlers",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtSvg",
        "PyQt6.sip",
        "paramiko",
        "paramiko.transport",
        "paramiko.auth_handler",
        "paramiko.sftp_client",
        "cryptography",
        "cryptography.hazmat.primitives",
        "ssh_utils",
        "docker_utils",
        "vercel_utils",
        "creds_store",
        "profiles_store",
        "gcp_utils",
        "azure_utils",
        "google.cloud.logging",
        "google.cloud.resourcemanager_v3",
        "google.oauth2.service_account",
        "azure.monitor.query",
        "azure.identity",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "test"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="simplelog",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window; stdin pipe still works
    disable_windowed_traceback=False,
    argv_emulation=False,   # set True only if needed on macOS CLI
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
    upx=True,
    upx_exclude=[],
    name="simplelog",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="SimpleLog.app",
        icon=None,
        bundle_identifier="com.sindus.simplelog",
        info_plist={
            "CFBundleName": "SimpleLog",
            "CFBundleDisplayName": "SimpleLog",
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSMinimumSystemVersion": "12.0",
        },
    )
