# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the frozen sidecar (openspec/changes/fix-linux-live-capture-alsa).

build_sidecar.py used to pass --onefile/--name/--add-data/--icon on the command
line. A spec-based build IGNORES those flags, so everything they did lives here
now; only --distpath and --workpath stay on the command line.

The reason for the move: PyInstaller has no flag to exclude a bundled shared
library, and the sidecar must NOT ship the build host's libasound.so.2. A
bundled libasound carries the ALSA plugin directory it was compiled with, so an
Ubuntu-built binary looks for plugins in /usr/lib/x86_64-linux-gnu/alsa-lib and
finds nothing on Fedora/openSUSE: no pipewire/default PCM is defined, PortAudio
reports zero input devices, and live capture dies with "Could not auto-detect
microphone". Leaving libasound to the host fixes it, because the host's copy is
the one whose compiled-in plugin directory matches the host's plugin files.
"""
import importlib.util
import platform
from pathlib import Path

SYSTEM = platform.system().lower()


def _faster_whisper_assets_dir() -> str:
    # silero_vad_v6.onnx and friends are data files PyInstaller's static
    # analysis cannot see (build_sidecar.py's original --add-data).
    spec = importlib.util.find_spec("faster_whisper")
    return str(Path(spec.origin).parent / "assets")


# ELF binaries carry no icon, so Linux passes none.
_ICON_NAME = {"windows": "icon.ico", "darwin": "icon.icns"}.get(SYSTEM)
_ICON = str(Path(SPECPATH) / "src-tauri" / "icons" / _ICON_NAME) if _ICON_NAME else None


a = Analysis(
    [str(Path(SPECPATH) / "transcriber.py")],
    pathex=[],
    binaries=[],
    datas=[(_faster_whisper_assets_dir(), "faster_whisper/assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)


def _is_host_owned_alsa(entry) -> bool:
    """True for the top-level libasound the sounddevice/PortAudio hook pulls in.

    PyAV ships its own copy at av.libs/libasound-<hash>.so.2.0.0, loaded under
    that path for its own decoding; both are loaded at runtime and only the
    top-level one is what PortAudio resolves against. Dropping PyAV's copy
    would risk file transcription, which is not broken -- so match only a
    bare libasound.so* at the bundle root.
    """
    dest = entry[0].replace("\\", "/")
    return "/" not in dest and dest.startswith("libasound.so")


if SYSTEM == "linux":
    # Plain list, not TOC(...): PyInstaller 6 keeps TOC only for backward
    # compatibility and marks the class deprecated.
    a.binaries = [e for e in a.binaries if not _is_host_owned_alsa(e)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="transcriber-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_ICON,
)
