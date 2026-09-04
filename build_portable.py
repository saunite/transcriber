#!/usr/bin/env python3
"""
Assemble the single no-install artifact for the current platform from the
raw `cargo tauri build` output (openspec/changes/remove-installer-packaging).
Replaces build_portable.ps1, which was Windows-only and so could not
produce the Linux or macOS artifact.

Per-platform, per design.md Decision 3:
  - Linux:   locate the AppImage from bundle/appimage/ -- no assembly needed.
  - macOS:   zip Transcriber.app from bundle/macos/ (uses `ditto` when
             available, to preserve resource forks/signing metadata).
  - Windows: copy transcriber-gui.exe, transcriber-sidecar.exe and
             WebView2Loader.dll from target/<triple>/release/, plus the
             bundled model, into resources/model/ -- exactly the relative
             layout resolve_model_dir() in sidecar.rs depends on -- then
             zip the folder.

Pass --target when the build used `cargo tauri build --target <triple>`
(explicit on all three CI legs, and on the local Windows cross-build) so
the release dir is found at target/<triple>/release/ instead of
target/release/.

Usage: python build_portable.py [--target x86_64-pc-windows-gnu]
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def _cargo_target_dir() -> Path | None:
    # Ask cargo itself where it writes (openspec/changes/02-add-wsl-linux-build)
    # -- e.g. to relocate build output off a Windows-mounted (/mnt/c) path
    # under WSL. cargo resolves this from $CARGO_TARGET_DIR, then
    # ~/.cargo/config.toml's build.target-dir, then the in-tree default;
    # asking cargo directly (rather than re-checking only the env var)
    # matches whichever of those actually applied for the real build.
    try:
        result = subprocess.run(
            ["cargo", "metadata", "--format-version", "1", "--no-deps"],
            cwd=REPO_ROOT / "src-tauri",
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(json.loads(result.stdout)["target_directory"])
    except (OSError, subprocess.CalledProcessError, KeyError, json.JSONDecodeError):
        return None


def _release_dir(target: str | None) -> Path:
    base = _cargo_target_dir() or (REPO_ROOT / "src-tauri" / "target")
    return (base / target / "release") if target else (base / "release")


def _zip_dir(src_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src_dir.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(src_dir.parent))


def build_windows(target: str | None) -> Path:
    release_dir = _release_dir(target)
    required = ["transcriber-gui.exe", "transcriber-sidecar.exe"]
    for name in required:
        if not (release_dir / name).exists():
            raise SystemExit(
                f"Missing {name} in {release_dir} -- run the build first "
                f"(see README.md's WSL build section or 'cargo tauri build')."
            )
    # WebView2Loader.dll is a sibling file on the mingw target (statically
    # linked on MSVC instead, so it won't exist there) -- see design.md
    # Decision 2, point 2. Copy it when present, don't require it.
    optional = ["WebView2Loader.dll"]

    model_dir = REPO_ROOT / "src-tauri" / "resources" / "model"
    if not (model_dir / "model.bin").exists():
        raise SystemExit(f"Missing model.bin under {model_dir} -- run fetch_sidecar_resources.py first.")

    out_dir = REPO_ROOT / "dist" / "portable" / "Transcriber"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    for name in required:
        shutil.copy2(release_dir / name, out_dir / name)
    for name in optional:
        if (release_dir / name).exists():
            shutil.copy2(release_dir / name, out_dir / name)

    out_model_dir = out_dir / "resources" / "model"
    shutil.copytree(model_dir, out_model_dir)

    zip_path = out_dir.with_suffix(".zip")
    _zip_dir(out_dir, zip_path)
    return zip_path


def build_linux(target: str | None) -> Path:
    appimage_dir = _release_dir(target) / "bundle" / "appimage"
    matches = sorted(appimage_dir.glob("*.AppImage"))
    if not matches:
        raise SystemExit(f"No .AppImage found in {appimage_dir} -- run 'cargo tauri build' first.")

    out_dir = REPO_ROOT / "dist" / "portable"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / matches[0].name
    shutil.copy2(matches[0], dest)
    dest.chmod(dest.stat().st_mode | 0o111)
    return dest


def build_macos(target: str | None) -> Path:
    app_dir = _release_dir(target) / "bundle" / "macos"
    matches = sorted(app_dir.glob("*.app"))
    if not matches:
        raise SystemExit(f"No .app found in {app_dir} -- run 'cargo tauri build' first.")
    app_path = matches[0]

    out_dir = REPO_ROOT / "dist" / "portable"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{app_path.stem}.zip"
    if zip_path.exists():
        zip_path.unlink()

    ditto = shutil.which("ditto")
    if ditto:
        import subprocess

        subprocess.run([ditto, "-c", "-k", "--sequesterRsrc", str(app_path), str(zip_path)], check=True)
    else:
        _zip_dir(app_path, zip_path)
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default=None,
        help="Rust target triple, if 'cargo tauri build' was given one (e.g. x86_64-pc-windows-gnu)",
    )
    args = parser.parse_args()

    # Dispatch on the --target triple when given (openspec/changes/03-add-wsl-windows-build)
    # -- e.g. `--target x86_64-pc-windows-gnu` run under WSL's own (Linux-reporting)
    # Python must still take the Windows branch. platform.system() reflects the
    # running interpreter, not the target, so it's only a correct fallback when
    # no --target was given (every existing caller already passes one explicitly).
    target = args.target or ""
    if "windows" in target:
        artifact = build_windows(args.target)
    elif "linux" in target:
        artifact = build_linux(args.target)
    elif "darwin" in target:
        artifact = build_macos(args.target)
    else:
        system = platform.system()
        if system == "Windows":
            artifact = build_windows(args.target)
        elif system == "Linux":
            artifact = build_linux(args.target)
        elif system == "Darwin":
            artifact = build_macos(args.target)
        else:
            raise SystemExit(f"Unsupported platform: {system}")

    print(f"Portable artifact assembled at: {artifact}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
