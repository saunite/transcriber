## Context

See proposal.md - Why. Facts established while planning, 2026-09-14:

- **What installs:** PyAV 18.1.0 (`.venv` and a fresh venv from `requirements-linux.txt` agree), with `av.ffmpeg_version_info` = `8.1.2`.
  - `av.library_versions`: libavutil 60.26.102, libavcodec 62.28.102, libavformat 62.12.102, libavdevice 62.3.102, libavfilter 11.14.102, libswscale 9.5.102, libswresample 6.3.102.
  - PyAV 18 has no `library_meta`, so the configure string isn't available through Python.
- **Where it comes from:** faster-whisper 1.2.1 requires `av>=11`, and nothing in this repo pins `av`.
- **PyAV 18.1.0 `scripts/`:** `ffmpeg-8.0.json` → `pyav-ffmpeg` `8.0.1-5`; `ffmpeg-8.1.json` and `ffmpeg-latest.json` → `8.1.2-1`. The installed FFmpeg 8.1.2 confirms `8.1.2-1` is the build in use.
- **`pyav-ffmpeg` at `8.1.2-1`:** components and URLs now live in `scripts/pkg.py`, and configure flags in `scripts/build-ffmpeg.py`, which also has `cibuildpkg.py` and `sbom.py`. The release (published 2026-06-29) has 14 platform tarballs, including `manylinux-x86_64`, `windows-x86_64` and `macos-arm64`, the three we ship.
  - x264 and x265 are built on every platform except 32-bit ARM, so they are in all three of our targets.
  - Per-platform flags: `--enable-alsa`, GnuTLS and `--enable-libxcb` depend on platform; Windows adds `--enable-mediafoundation`, AMF and libvpl; macOS adds VideoToolbox and AudioToolbox.
- **The current preflight** only resolves URLs grepped from `SOURCE-PROVENANCE.txt`.

## Goals / Non-Goals

**Goals:**
- `SOURCE-PROVENANCE.txt` and `THIRD-PARTY-LICENSES.txt` describe exactly what PyAV 18.1.0 ships on Linux x86-64, Windows x86-64 and macOS arm64.
- A future PyAV change can't reach a build without the provenance being refreshed.

**Non-Goals:**
- Legal review of the licence analysis itself. The existing reasoning (x264/x265 GPL-2.0-or-later, `--enable-version3`) is kept and re-checked against the new build.
- Pinning anything other than `av`.

## Decisions

### 1. Derive from the recipe, confirm against the shipped binaries

The recipe at the tag is the authoritative source list: it is literally "the scripts used to control compilation". Each component's version and source URL is copied from `scripts/pkg.py` at `8.1.2-1`, and its licence is taken from the component's upstream licence.

- **Two cross-checks against what actually ships:**
  - `av.library_versions` from the installed wheel;
  - the configure string, read with `strings` out of the bundled `libavutil` in the Linux wheel and matched against the recipe's flags.
- **If a tarball contains an SBOM** (the recipe has `sbom.py`), it's read as a third cross-check. Any disagreement is recorded rather than smoothed over, the way the current file records the missing `--enable-gpl` oddity.

**Rejected: deriving only from the binaries.** Libraries report their own versions, but not the URLs or exact commits their source came from, and that's what the GPL directions need.

**Per-platform differences get their own subsection.** The component list is shared, and each platform's extra flags and optional libraries are listed. The Windows and macOS configure strings aren't read from binaries here: there's no Windows or Mac environment locally, and CI extraction would add machinery for a document. Their flags come from `build-ffmpeg.py`, and the file says so.

### 2. Pin `av==18.1.0` in all three app requirements files

That's an exact pin, not `~=`: the provenance names one build, so the dependency must resolve to that build. `requirements-dev.txt` is untouched, since it doesn't ship. faster-whisper's `av>=11` accepts it.

### 3. The guard is a static preflight check, on every run

A new step in `preflight`, before the link check, needing no install:
1. From each of `requirements.txt`, `requirements-linux.txt` and `requirements-macos.txt`, extract the line matching `^av==<version>$`. Fail naming the file if there's none, or if it uses any other operator.
2. Fail if the three versions differ, naming each file and version.
3. Extract `av == <version>` from `SOURCE-PROVENANCE.txt`, and fail naming both versions if it differs.

It runs on manual and tagged runs alike (no `if:`), so drift fails a test build before it can reach a release.

**Rejected: checking the installed `av.__version__` in each platform job.** With an exact pin, pip installs exactly that version, so a runtime check would repeat the static one about 15 minutes later and only after installing dependencies. The static check fails in seconds, before any runner starts building.

**Rejected: generating `SOURCE-PROVENANCE.txt` automatically from the recipe.** The file carries licence analysis and caveats a script can't write, and a regenerate-on-bump workflow is machinery for an event that happens a few times a year.

### 4. Notices and README follow the provenance

`THIRD-PARTY-LICENSES.txt`'s "Bundled media libraries" section and its PyAV table line are updated to match the new component set: TwoLAME removed, new copyleft or weak-copyleft libraries added, versions refreshed. README's maintenance bullet stops hedging with "if the pinned PyAV version changed" (it now is pinned) and names the guard.

## Risks / Trade-offs

- **[Risk]** A component moved hosts, so a new URL doesn't resolve. x265 4.2 is still on Bitbucket, the known risk. → The existing link check runs in the verification CI run, and a dead link blocks the change.
- **[Risk]** The Windows or macOS binaries differ from what `build-ffmpeg.py` suggests. → The file states those configure strings come from the recipe, not the binaries. The link to the exact tag lets anyone verify.
- **[Trade-off]** An exact pin means PyAV security fixes don't arrive automatically. Each bump is now a deliberate change, which the GPL obligation requires anyway, since every new PyAV version needs new directions.
- **[Risk]** A later faster-whisper requires a newer `av` than the pin. → pip fails to resolve at install, loudly, and the fix is the same deliberate bump.
