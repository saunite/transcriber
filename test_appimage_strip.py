#!/usr/bin/env python3
"""Checks for build_portable.py's AppImage repack (fix-appimage-egl-crash).

Builds a fake AppImage -- an arbitrary byte header standing in for the ELF
runtime, plus a real mksquashfs payload -- so the repack can be exercised
without a genuine AppImage runtime. That is what `_strip_appimage_libs`'s
`offset` argument is for.

Run: python test_appimage_strip.py   (needs mksquashfs/unsquashfs on PATH)
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from build_portable import (
    STRIP_FROM_APPIMAGE,
    _squashfs_settings,
    _strip_appimage_libs,
    _verify_stripped,
)

HEADER = b"FAKE-APPIMAGE-RUNTIME\n" * 64  # stands in for the ELF runtime


def _fake_appimage(path: Path, tmp: Path, *, with_libs: bool) -> int:
    """Write a fake AppImage to `path`; return its runtime-header length."""
    root = tmp / "root"
    (root / "usr" / "lib").mkdir(parents=True, exist_ok=True)
    (root / "AppRun").write_text("#!/bin/sh\n")
    (root / "usr" / "lib" / "libgtk-3.so.0").write_bytes(b"keep me" * 100)
    if with_libs:
        for lib in STRIP_FROM_APPIMAGE:
            (root / lib).write_bytes(b"host-owned" * 100)

    payload = tmp / "payload.squashfs"
    if payload.exists():
        payload.unlink()
    subprocess.run(
        ["mksquashfs", str(root), str(payload),
         "-root-owned", "-noappend", "-no-xattrs", "-comp", "zstd", "-b", "131072"],
        capture_output=True, check=True,
    )
    with path.open("wb") as out:
        out.write(HEADER)
        out.write(payload.read_bytes())
    shutil.rmtree(root)
    return len(HEADER)


def _listing(image: Path, offset: int) -> str:
    return subprocess.run(
        ["unsquashfs", "-o", str(offset), "-l", str(image)],
        capture_output=True, text=True, check=True,
    ).stdout


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)

        # 1. The libraries are removed, and everything else survives.
        src = tmp / "in.AppImage"
        offset = _fake_appimage(src, tmp, with_libs=True)
        before = _listing(src, offset)
        assert all(f"squashfs-root/{lib}" in before for lib in STRIP_FROM_APPIMAGE), before

        out = _strip_appimage_libs(src, tmp / "out" / "fixed.AppImage", offset=offset)
        after = _listing(out, offset)
        for lib in STRIP_FROM_APPIMAGE:
            assert f"squashfs-root/{lib}" not in after, f"{lib} survived the strip"
        assert "squashfs-root/usr/lib/libgtk-3.so.0" in after, after
        assert "squashfs-root/AppRun" in after, after
        assert out.read_bytes()[: len(HEADER)] == HEADER, "runtime header not preserved"
        assert out.stat().st_mode & 0o111, "result is not executable"

        # 2. Already-stripped input succeeds -- absence must not fail the build.
        clean = tmp / "clean.AppImage"
        clean_offset = _fake_appimage(clean, tmp, with_libs=False)
        again = _strip_appimage_libs(clean, tmp / "out" / "clean-out.AppImage", offset=clean_offset)
        assert "squashfs-root/usr/lib/libgtk-3.so.0" in _listing(again, clean_offset)

        # 3. The size guard rejects a short write (the full-disk failure).
        truncated = tmp / "truncated.AppImage"
        data = out.read_bytes()
        truncated.write_bytes(data[: len(data) // 2])
        try:
            _verify_stripped(truncated, offset, len(data), src.stat().st_size)
        except SystemExit as exc:
            assert "short write" in str(exc), exc
        else:
            raise AssertionError("a truncated image passed verification")

        # 4. The growth guard rejects a compressor mismatch.
        try:
            _verify_stripped(out, offset, out.stat().st_size, source_size=1000)
        except SystemExit as exc:
            assert "compressor mismatch" in str(exc), exc
        else:
            raise AssertionError("an oversized image passed verification")

        # 5. Settings are read from the input, not hardcoded.
        comp, block = _squashfs_settings(src, offset)
        assert (comp, block) == ("zstd", 131072), (comp, block)
        # An unreadable image falls back rather than crashing the build.
        assert _squashfs_settings(tmp / "nope.AppImage", 0) == ("zstd", 131072)

    print("test_appimage_strip: all checks passed")


if __name__ == "__main__":
    main()
