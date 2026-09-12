#!/usr/bin/env python3
"""
Assemble the no-install artifacts for one platform from the raw
`cargo tauri build` output (openspec/changes/remove-installer-packaging),
plus that platform's standalone CLI archive
(openspec/changes/01-add-release-pipeline). Replaces build_portable.ps1,
which was Windows-only and so could not produce the Linux or macOS
artifact.

GUI artifact, per platform (remove-installer-packaging design.md Decision 3):
  - Linux:   locate the AppImage from bundle/appimage/ and repack it without
             the host-owned libwayland libraries linuxdeploy bundles, which
             otherwise abort with EGL_BAD_PARAMETER
             (openspec/changes/fix-appimage-egl-crash).
  - macOS:   zip Transcriber.app from bundle/macos/ (uses `ditto` when
             available, to preserve resource forks/signing metadata).
  - Windows: copy transcriber-gui.exe, transcriber-sidecar.exe and
             WebView2Loader.dll from target/<triple>/release/, plus the
             bundled model, into resources/model/ -- exactly the relative
             layout resolve_model_dir() in sidecar.rs depends on -- then
             zip the folder.

CLI archive, every platform: the frozen sidecar from dist/<system>/ renamed
to `transcriber`, the bundled model in model/ (where the frozen CLI looks
for it), the platform's launcher scripts, and the notice files. Zip on
Windows, tar.gz elsewhere (tarfile keeps the executable bit).

Pass --target when the build used `cargo tauri build --target <triple>`
(explicit in CI, and on the local Windows cross-build) so the release dir
is found at target/<triple>/release/ instead of target/release/.

Usage: python build_portable.py [--target x86_64-pc-windows-gnu]
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
MODEL_DIR = REPO_ROOT / "src-tauri" / "resources" / "model"

# Licence notices must reach whoever receives the artifact, not just whoever
# clones the repo -- the artifacts bundle GPL binaries (FFmpeg/x264/x265 via
# PyAV), and that obligation attaches to what is distributed. The AppImage is
# a sealed single file, so its copies ride along as Tauri bundle resources
# (tauri.conf.json) instead of being placed here.
NOTICE_FILES = ("LICENSE", "THIRD-PARTY-LICENSES.txt", "SOURCE-PROVENANCE.txt")

# ponytail: one architecture per OS, matching what the release pipeline builds
# (macOS is arm64-only by decision). Add entries if another arch ever ships.
PLATFORM_LABEL = {"windows": "windows-x64", "linux": "linux-x64", "darwin": "macos-arm64"}

LAUNCHERS = {
    "windows": ("win-start-transcription.bat", "transcribe_file.bat"),
    "linux": ("linux-start-transcription.sh",),
    "darwin": ("mac-start-transcription.sh",),
}


def _version() -> str:
    # tauri.conf.json's version is what Tauri stamps into the installers, so
    # every artifact name derives from the same value.
    return json.loads((REPO_ROOT / "src-tauri" / "tauri.conf.json").read_text())["version"]


def _copy_notices(dest_dir: Path) -> None:
    for name in NOTICE_FILES:
        src = REPO_ROOT / name
        if not src.exists():
            raise SystemExit(f"Missing {name} at {REPO_ROOT} -- it must ship inside the artifact.")
        shutil.copy2(src, dest_dir / name)


def _copy_model(dest_dir: Path) -> None:
    # The model's LICENSE.txt is tracked in git next to the weights and comes
    # along; .cache/ is only huggingface download bookkeeping.
    if not (MODEL_DIR / "model.bin").exists():
        raise SystemExit(f"Missing model.bin under {MODEL_DIR} -- run fetch_sidecar_resources.py first.")
    shutil.copytree(MODEL_DIR, dest_dir, ignore=shutil.ignore_patterns(".cache"))


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


def _fresh_dir(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


# Host-owned graphics libraries that must NOT ship inside the AppImage.
# linuxdeploy-plugin-gtk deploys GTK with `copy_tree "$gtk3_libdir" "$APPDIR/"`
# -- a wholesale directory copy -- so the build machine's libwayland lands in
# the bundle and AppRun puts it ahead of the host's on LD_LIBRARY_PATH. The
# host's much newer EGL is then forced onto a years-old libwayland-client and
# aborts with "Could not create default EGL display: EGL_BAD_PARAMETER".
# Upstream's AppImage excludelist does list libwayland-client, but it only
# governs ldd-resolved deployment and never applies to a blind copy_tree.
# See openspec/changes/fix-appimage-egl-crash/.
STRIP_FROM_APPIMAGE = ("usr/lib/libwayland-client.so.0", "usr/lib/libwayland-egl.so.1")

# Used only when the input's own settings can't be read (see _squashfs_settings).
DEFAULT_SQUASHFS = ("zstd", 131072)


def _squashfs_settings(image: Path, offset: int) -> tuple[str, int]:
    # Mirror the input's compressor and block size rather than hardcoding them:
    # repacking a zstd/128K payload with mksquashfs's default gzip made the
    # image 9.7 MB larger, so a future bundler switching compressor would
    # silently inflate every download (design.md Decision 3).
    try:
        out = subprocess.run(
            ["unsquashfs", "-o", str(offset), "-s", str(image)],
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return DEFAULT_SQUASHFS

    comp, block = DEFAULT_SQUASHFS
    for line in out.splitlines():
        if line.startswith("Compression "):
            comp = line.split()[1]
        elif line.startswith("Block size "):
            block = int(line.split()[2])
    return comp, block


def _verify_stripped(image: Path, offset: int, expected_size: int, source_size: int) -> None:
    # Checks run on the OUTPUT, because that is what gets published
    # (design.md Decision 4). A truncated payload is not hypothetical: a full
    # disk once produced a plausible-looking short image that only failed when
    # it was run.
    actual = image.stat().st_size
    if actual != expected_size:
        raise SystemExit(
            f"{image.name} is {actual} bytes, expected {expected_size} "
            "(runtime header + payload) -- short write, refusing to publish it."
        )
    if actual > source_size * 1.05:
        raise SystemExit(
            f"{image.name} grew from {source_size} to {actual} bytes "
            "-- likely a squashfs compressor mismatch, refusing to publish it."
        )
    listing = subprocess.run(
        ["unsquashfs", "-o", str(offset), "-l", str(image)],
        capture_output=True, text=True, check=True,
    ).stdout
    still_there = [lib for lib in STRIP_FROM_APPIMAGE if f"squashfs-root/{lib}" in listing]
    if still_there:
        raise SystemExit(f"{image.name} still bundles {', '.join(still_there)} -- the strip did not apply.")


def _strip_appimage_libs(src: Path, dest: Path, offset: int | None = None) -> Path:
    """Rebuild `src` as `dest` without the host-owned graphics libraries.

    A squashfs is read-only, so the payload has to be rebuilt: split off the
    ELF runtime header, extract, delete, re-make, concatenate. `offset` is
    read from the image itself unless given (the tests pass it, so they can
    use a fake header instead of a real AppImage runtime).
    """
    if offset is None:
        offset = int(subprocess.run(
            [str(src), "--appimage-offset"], capture_output=True, text=True, check=True,
        ).stdout.strip())
    comp, block = _squashfs_settings(src, offset)

    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp_name:
        tmp = Path(tmp_name)
        root, payload = tmp / "root", tmp / "payload.squashfs"
        with src.open("rb") as fh:
            runtime = fh.read(offset)
        if len(runtime) != offset:
            raise SystemExit(f"{src} is shorter than its own {offset}-byte runtime header.")

        subprocess.run(
            ["unsquashfs", "-o", str(offset), "-d", str(root), str(src)],
            capture_output=True, text=True, check=True,
        )
        # Absence is fine, and is the outcome we want if a future linuxdeploy
        # stops bundling these at all (design.md Decision 4).
        for lib in STRIP_FROM_APPIMAGE:
            (root / lib).unlink(missing_ok=True)
        subprocess.run(
            ["mksquashfs", str(root), str(payload),
             "-root-owned", "-noappend", "-no-xattrs", "-comp", comp, "-b", str(block)],
            capture_output=True, text=True, check=True,
        )

        if dest.exists():
            dest.unlink()
        with dest.open("wb") as out:
            out.write(runtime)
            with payload.open("rb") as fh:
                shutil.copyfileobj(fh, out)
        expected = len(runtime) + payload.stat().st_size

    dest.chmod(dest.stat().st_mode | 0o111)
    _verify_stripped(dest, offset, expected, src.stat().st_size)
    return dest


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

    out_dir = _fresh_dir(REPO_ROOT / "dist" / "portable" / "Transcriber")
    for name in required:
        shutil.copy2(release_dir / name, out_dir / name)
    for name in optional:
        if (release_dir / name).exists():
            shutil.copy2(release_dir / name, out_dir / name)

    _copy_model(out_dir / "resources" / "model")
    _copy_notices(out_dir)

    zip_path = out_dir.parent / f"Transcriber_{_version()}_{PLATFORM_LABEL['windows']}.zip"
    _zip_dir(out_dir, zip_path)
    return zip_path


def build_linux(target: str | None) -> Path:
    appimage_dir = _release_dir(target) / "bundle" / "appimage"
    matches = sorted(appimage_dir.glob("*.AppImage"))
    if not matches:
        raise SystemExit(f"No .AppImage found in {appimage_dir} -- run 'cargo tauri build' first.")

    out_dir = REPO_ROOT / "dist" / "portable"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Repack on the way out instead of a plain copy: the bundler's AppImage
    # ships host-owned libwayland and aborts on a current desktop. The
    # bundler's own output is left untouched, so re-running is idempotent
    # (fix-appimage-egl-crash design.md Decision 5).
    return _strip_appimage_libs(matches[0], out_dir / matches[0].name)


def build_macos(target: str | None) -> Path:
    app_dir = _release_dir(target) / "bundle" / "macos"
    matches = sorted(app_dir.glob("*.app"))
    if not matches:
        raise SystemExit(f"No .app found in {app_dir} -- run 'cargo tauri build' first.")
    app_path = matches[0]

    # Inside the bundle, so the notices survive the user moving the .app around.
    _copy_notices(app_path / "Contents" / "Resources")

    out_dir = REPO_ROOT / "dist" / "portable"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{app_path.stem}_{_version()}_{PLATFORM_LABEL['darwin']}.zip"
    if zip_path.exists():
        zip_path.unlink()

    ditto = shutil.which("ditto")
    if ditto:
        subprocess.run([ditto, "-c", "-k", "--sequesterRsrc", str(app_path), str(zip_path)], check=True)
    else:
        _zip_dir(app_path, zip_path)
    return zip_path


def build_cli(system: str) -> Path:
    exe = ".exe" if system == "windows" else ""
    sidecar = REPO_ROOT / "dist" / system / f"transcriber-sidecar{exe}"
    if not sidecar.exists():
        raise SystemExit(f"Missing {sidecar} -- run build_sidecar.py first.")

    name = f"transcriber-cli_{_version()}_{PLATFORM_LABEL[system]}"
    out_dir = _fresh_dir(REPO_ROOT / "dist" / "portable" / name)
    shutil.copy2(sidecar, out_dir / f"transcriber{exe}")
    _copy_model(out_dir / "model")
    for launcher in LAUNCHERS[system]:
        shutil.copy2(REPO_ROOT / launcher, out_dir / launcher)
    _copy_notices(out_dir)

    if system == "windows":
        archive = out_dir.with_suffix(".zip")
        _zip_dir(out_dir, archive)
        return archive

    # Don't trust the checkout's modes (a synced or Windows-side checkout can
    # drop them): the binary and launchers must extract executable.
    for path in [out_dir / "transcriber", *(out_dir / launcher for launcher in LAUNCHERS[system])]:
        path.chmod(path.stat().st_mode | 0o111)
    archive = out_dir.parent / f"{name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(out_dir, arcname=name)
    return archive


BUILDERS = {"windows": build_windows, "linux": build_linux, "darwin": build_macos}


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
    # no --target was given.
    target = args.target or ""
    system = next((s for s in BUILDERS if s in target), None) or platform.system().lower()
    if system not in BUILDERS:
        raise SystemExit(f"Unsupported platform: {system}")

    print(f"Portable artifact assembled at: {BUILDERS[system](args.target)}")
    print(f"CLI archive assembled at: {build_cli(system)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
