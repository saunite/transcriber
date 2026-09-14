## 1. Pin and guard

- [x] 1.1 Add `av==18.1.0` to `requirements.txt`, `requirements-linux.txt` and `requirements-macos.txt` (design.md Decision 2). Verify that in a fresh venv `pip install -r requirements-linux.txt` resolves without conflict, and that `python -c "import av; print(av.__version__, av.ffmpeg_version_info)"` prints `18.1.0 8.1.2`.

  **Done 2026-09-14.** `av==18.1.0` is added right after `faster-whisper` in all three files, with a comment on why it's exact. A fresh venv from `requirements-linux.txt` installed without conflict: `pip check` reports "No broken requirements found", and `import av` gives `18.1.0 8.1.2`.
- [x] 1.2 Add the preflight guard step to `.github/workflows/release.yml`, before "Source-provenance links resolve" and with no `if:` (Decision 3). Verify:
  - PyYAML parses the workflow;
  - the step's script, run locally from the parsed YAML, **fails** at this point, naming `SOURCE-PROVENANCE.txt`'s recorded `16.0.1` against `18.1.0` (the real drift);
  - it also fails, on scratch copies, for a requirements file with no `av` line, one with `av>=18.1.0`, and two files with different pinned versions.

  **Done 2026-09-14.** Step "PyAV pin matches source provenance" sits right before "Source-provenance links resolve", with no `if:`, and PyYAML parses the workflow. Running its script from the parsed YAML:
  - **real tree:** exit 1, `requirements pin av==18.1.0 but SOURCE-PROVENANCE.txt records av == 16.0.1`;
  - **scratch copy with the provenance set to 18.1.0:** exit 0;
  - **no `av` line in `requirements-macos.txt`:** exit 1, naming it;
  - **`av>=18.1.0` in `requirements-linux.txt`:** exit 1, naming it and quoting the line;
  - **`requirements.txt` pinning 18.0.0:** exit 1, naming each file and version, plus the provenance mismatch.

## 2. Re-derive the provenance

- [x] 2.1 Collect the build facts for `pyav-ffmpeg` `8.1.2-1` (Decision 1):
  - every component's name, version, source URL and upstream licence from `scripts/pkg.py`;
  - the per-platform flags from `scripts/build-ffmpeg.py` for Linux x86-64, Windows x86-64 and macOS arm64;
  - `av.library_versions` and `av.ffmpeg_version_info` from the installed wheel;
  - the configure string, read with `strings` from the Linux wheel's bundled `libavutil`;
  - an SBOM from the `ffmpeg-manylinux-x86_64.tar.gz` release tarball, if it has one.
  Record every disagreement between these sources, and confirm that TwoLAME, Speex, libvorbis/libogg, libaom and OpenH264 are really absent from `pkg.py`, not just defined differently.

  **Done 2026-09-14.** Sources: `pyav-ffmpeg` `8.1.2-1`'s `scripts/pkg.py` and `scripts/build-ffmpeg.py`, and the **real PyAV 18.1.0 wheels for all three platforms**: `manylinux_2_28_x86_64`, `win_amd64` and `macosx_14_0_arm64`, fetched with `pip download --no-deps` and unzipped.
  **Deviation from design.md Decision 1, for the better:** `pip download` provides the Windows and macOS binaries without those machines, so their bundled library lists and configure strings are read from the binaries, not inferred from the recipe.
  - **Recipe:** FFmpeg 8.1.2; codecs LAME 3.100, Opus 1.6.1, dav1d 1.5.3, SVT-AV1 4.1.0, libvpx 1.16.0, libpng 1.6.58, libwebp 1.6.0, opencore-amr 0.1.6, x264 `b35605ace3dd…`, x265 4.2.
    - GnuTLS group, **Linux only**: GMP 6.3.0, libunistring 1.4.2, nettle 3.10.2, GnuTLS 3.8.13.
    - ALSA 1.2.14, **Linux only**.
    - nv-codec-headers n13.0.19.0, AMF headers 1.5.0 and libvpl 2.16.0, **Linux and Windows only**.
    - NASM 2.16.03 is a build tool and isn't shipped.
    - **TwoLAME, Speex, libvorbis/libogg, libaom and OpenH264 are absent from `pkg.py`**; confirmed by reading the whole file.
  - **Shipped libraries:**
    - **Linux:** the codecs plus GMP, GnuTLS, nettle/hogweed, libunistring, ALSA, libvpl, and `libdrm`, `libXau` and `libxcb`/`-shape`/`-shm`/`-xfixes`, which are copied from the manylinux build image and aren't in the recipe.
    - **Windows:** the codecs plus libvpl, `zlib1` (1.3.2), `libiconv-2` (**1.19**, read from its exported `_libiconv_version` = 0x0113), and the MSYS2 GCC **16.1.0** runtime: `libgcc_s_seh`, `libstdc++`, `libwinpthread` (mingw-w64).
    - **macOS:** only FFmpeg and the codecs.
    - **libpng isn't shipped on any platform:** no "libpng version" string appears in any bundled library.
  - **Library versions** (`av.library_versions`, identical to the version suffixes on the macOS dylibs): avutil 60.26.102, avcodec 62.28.102, avformat 62.12.102, avdevice 62.3.102, avfilter 11.14.102, swscale 9.5.102, swresample 6.3.102.
  - **Configure strings**, read with `strings` from each platform's avutil: all share `--enable-version3 --enable-libx264 --enable-libx265` and the codec flags. Linux adds `--enable-alsa --enable-gnutls --enable-libxcb --enable-nvenc --enable-nvdec --enable-amf --enable-libvpl`; Windows adds `--enable-mediafoundation --enable-nvenc --enable-nvdec --enable-amf --enable-libvpl`; macOS adds `--enable-videotoolbox --enable-audiotoolbox`. They match `build-ffmpeg.py`'s per-platform switches. **`--enable-gpl` is still absent on every platform**, the same unexplained oddity the old file recorded. **`--enable-gmp` is gone**: 8.0-2's Windows build had it.
  - **No SBOM:** the `ffmpeg-manylinux-x86_64.tar.gz` release tarball contains headers and libraries only. `sbom.py` just prints from the recipe, so it adds nothing beyond `pkg.py`.
- [x] 2.2 Rewrite `SOURCE-PROVENANCE.txt`, keeping its section structure (how the binaries got here, what ships, per-component source, maintenance):
  - `av == 18.1.0`, pinning `8.1.2-1`, with links to the recipe files at that tag;
  - the library versions and Linux configure string from 2.1;
  - a per-platform subsection whose Windows and macOS flags are stated as recipe-derived;
  - copyleft and permissive components with the new versions and URLs, removed components dropped;
  - the x265 hosting-risk note kept;
  - the maintenance section saying PyAV is pinned and the preflight guard enforces the match;
  - "Last verified" set to the date of 2.3.
  Verify with the guard script from 1.2, which must now pass, and `git diff` shows no leftover `16.0.1`, `8.0-2` or `FFmpeg 8.0` text.

  **Done 2026-09-14.** `SOURCE-PROVENANCE.txt` is rewritten in its four sections, with `av == 18.1.0` → `8.1.2-1` and links to PyAV's `ffmpeg-8.1.json` and to the recipe's tree, `pkg.py` and `build-ffmpeg.py` at the tag. It records the library versions, and the configure strings read from **all three** platforms' avutil (a common block plus per-platform additions), keeping the missing `--enable-gpl` note. A per-platform bundled-library list adds the Linux libraries copied in from the build image, the Windows MSYS2 libiconv 1.19 and GCC 16.1.0 runtime, and says libpng is built but not shipped. Copyleft sources are split into all-platform, Linux-only and Windows-only (toolchain) groups; permissive ones are listed; the removed codecs are gone; the x265 hosting-risk note is kept. The maintenance section now describes the pin and the guard. "Last verified: 2026-09-14". The guard script from 1.2 now **passes** (exit 0), and no `16.0.1`, `8.0-2` or `FFmpeg 8.0` text remains.
- [x] 2.3 Run the preflight link check's command locally against the new file. Verify every non-template URL resolves (`curl -fsSL -r 0-0`), and record any that don't, fixing or noting them before continuing.

  **Done 2026-09-14.** Running the preflight "Source-provenance links resolve" script, taken from the parsed workflow, against the new file: **all 29 non-template URLs resolve**, exit 0. They include the x265 4.2 Bitbucket download, libiconv-1.19, gcc-16.1.0 and every `pkg.py` source. None needed fixing.
- [x] 2.4 Update `THIRD-PARTY-LICENSES.txt` (Decision 4): the "Bundled media libraries" entries (FFmpeg 8.1.2, x264, x265 4.2, the component list per 2.1) and the `PyAV 18.1.0` table line, with the `--enable-version3` statement re-checked against the new configure string. Verify that `grep -n "16.0.1\|FFmpeg 8.0\|x265 4.1\|TwoLAME"` finds nothing, unless 2.1 showed that component is still built.

  **Done 2026-09-14.** In `THIRD-PARTY-LICENSES.txt`:
  - the effective-licence bullet now says `--enable-version3` is on every platform, pulls in opencore-amr under version-3 terms, and pulls in GnuTLS with GMP, nettle and libunistring on Linux;
  - the Bundled media libraries section is rebuilt with FFmpeg 8.1.2 and all-platform, Linux-only and Windows-only copyleft groups, with the permissive list updated;
  - the removed codecs are dropped, and libvpl, the AMF and NVIDIA headers, and libdrm/libXau/libxcb are added;
  - the PyAV table line reads `PyAV 18.1.0`;
  - the MIT/BSD blanket notice now also covers BSD-3-Clause-Clear, for SVT-AV1.
  The leftover grep finds nothing.
- [x] 2.5 Update README's licensing maintenance bullet to say PyAV is pinned (`av==18.1.0`), and that a bump must re-derive `SOURCE-PROVENANCE.txt`, which the preflight check enforces. Verify the bullet no longer says "If the pinned PyAV version changed".

  **Done 2026-09-14.** The README bullet now reads "PyAV is pinned (`av==18.1.0` in the three `requirements*.txt` files), and bumping it means re-deriving everything in `SOURCE-PROVENANCE.txt`…", listing `pkg.py`, `build-ffmpeg.py` and the wheels, and saying the preflight fails a build whose pin differs. "If the pinned PyAV version changed" no longer appears.

## 3. Verification

- [x] 3.1 Run `.venv/bin/python run_tests.py` with the recording set, in a venv matching the pinned requirements. Verify it exits 0.

  **Done 2026-09-14.** In the project `.venv`, which has `av 18.1.0` (the pinned version), with the recording set: 12/12 suites passed in 24.8s.
- [x] 3.2 Manual `workflow_dispatch` run on `dev` (only when the user asks for it). Verify:
  - the new guard step passes;
  - "Source-provenance links resolve" passes with the new URLs;
  - all platform jobs pass;
  - a job log's pip output shows `av-18.1.0` being installed.

  **Done 2026-09-14,** `workflow_dispatch` run 34893981518 on `dev` at `8e6f296`, requested by the user. **"PyAV pin matches source provenance" passed**, printing `requirements.txt: av==18.1.0`, `requirements-linux.txt: av==18.1.0` and so on, with no error annotation. **"Source-provenance links resolve" passed** with the new URLs. All four jobs succeeded. Each platform job's pip installed exactly the pinned wheel: `av-18.1.0-cp311-abi3-manylinux_2_28_x86_64.whl`, `…-win_amd64.whl` and `…-macosx_14_0_arm64.whl` — the three wheels the provenance was derived from.
