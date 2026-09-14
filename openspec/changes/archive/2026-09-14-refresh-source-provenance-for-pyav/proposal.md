## Why

`SOURCE-PROVENANCE.txt` is how the project meets GPLv3 §6(d) for the GPL-licensed FFmpeg, x264 and x265 that PyAV bundles into every sidecar. It describes a build that is no longer shipped:

- **Recorded:** `av == 16.0.1`, which pins `PyAV-Org/pyav-ffmpeg` tag `8.0-2` (FFmpeg 8.0, x264 commit `32c3b80`, x265 4.1). Last verified 2026-09-08.
- **Shipped:** PyAV **18.1.0**, reporting FFmpeg **8.1.2**. That is what the project venv, a fresh venv from `requirements-linux.txt`, and the CI builds all install. PyAV 18.1.0's `scripts/ffmpeg-8.1.json` pins `pyav-ffmpeg` tag **`8.1.2-1`**.
- **The components changed, not just the versions.** The `8.1.2-1` recipe (`scripts/pkg.py` and `build-ffmpeg.py`, which replaced the monolithic recipe the file cites):
  - builds FFmpeg 8.1.2, x264 commit `b35605a`, x265 4.2, Opus 1.6.1, dav1d 1.5.3, SVT-AV1 4.1.0, libvpx 1.16.0, libwebp 1.6.0, opencore-amr 0.1.6, libpng 1.6.58, and GnuTLS/nettle/libunistring on some platforms;
  - no longer lists TwoLAME, Speex, libvorbis/libogg, libaom or OpenH264;
  - adds AMF and libvpl headers on Windows and VideoToolbox on macOS;
  - enables different options per platform.
- **`THIRD-PARTY-LICENSES.txt` is stale the same way:** "PyAV 16.0.1", "FFmpeg 8.0", "x265 4.1", TwoLAME.

`licensing` requires that "when a dependency update changes the version of a bundled GPL component, the directions published with the new release identify the new versions". Today every build breaks that, and the draft `v0.1.0` (2026-09-14) can't be published until it's fixed.

**Root cause:** PyAV is not pinned. It arrives transitively through `faster-whisper>=1.0.0`, so each build takes the newest PyAV. `preflight` only checks that the file's URLs resolve, not that it describes what's bundled. The next PyAV release would make the file stale again without any signal. The maintainer chose to fix the cause as well: pin PyAV, and guard the pin in CI.

## What Changes

- **Re-derive `SOURCE-PROVENANCE.txt` for PyAV 18.1.0 / `pyav-ffmpeg` `8.1.2-1`:**
  - the chain from PyAV to the recipe tag, citing the new `pkg.py` and `build-ffmpeg.py`;
  - library versions and a configure string read from the shipped binary;
  - the per-platform differences in the recipe;
  - the per-component source URLs, with components that are no longer built removed and new ones added;
  - a new "last verified" date.
- **Update `THIRD-PARTY-LICENSES.txt`'s** PyAV, FFmpeg and codec entries to match.
- **Pin `av==18.1.0`** in `requirements.txt`, `requirements-linux.txt` and `requirements-macos.txt`.
- **A preflight guard in `release.yml`** fails a run, before any platform build, unless all three requirements files pin `av` to one exact version **and** `SOURCE-PROVENANCE.txt` records that same version. It runs on manual and tagged runs alike, so drift shows up in a test build before a release.
- **README's maintenance note** says PyAV is pinned and a bump must re-derive the file, which the guard now enforces.
- **Not in scope:**
  - Publishing or re-tagging `v0.1.0`.
  - Pinning faster-whisper, CTranslate2 or other non-GPL dependencies.
  - Rehosting sources. The existing link check stays and must pass on the new URLs.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `release-build`: adds a requirement that a build refuses to run when PyAV isn't pinned to the one exact version the source-provenance file records, checked before any platform build. `licensing` is unchanged: this change brings the files back in line with it.

## Impact

- **Changed:** `SOURCE-PROVENANCE.txt`, `THIRD-PARTY-LICENSES.txt`, the three app `requirements*.txt` files, `.github/workflows/release.yml` (one preflight step), and `README.md`.
- **Unchanged:** application code, packaging scripts, and which PyAV actually ships (18.1.0 is already what installs; the pin only freezes it).
- **Dependency:** pinning `av==18.1.0` must stay compatible with faster-whisper 1.2.1's `av` requirement; a task checks this.
- **Verification:**
  - Local: the guard's script passes on the tree and fails on each kind of mismatch.
  - CI: a manual run shows the guard passing, every link resolving, and the frozen sidecars reporting PyAV 18.1.0 and FFmpeg 8.1.2.
