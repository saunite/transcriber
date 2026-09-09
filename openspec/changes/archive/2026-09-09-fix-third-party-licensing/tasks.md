## 1. Author the notices

- [x] 1.1 Create `THIRD-PARTY-LICENSES.txt` at the repo root covering every bundled component, each with license name, copyright holder, and upstream URL

  Components verified as actually bundled in the current artifact:
  - **FFmpeg libraries** via PyAV `av==16.0.1` (`av.libs/`): `avcodec-62`, `avformat-62`, `avutil-60`, `avdevice-62`, `avfilter-11`, `swresample-6`, `swscale-9` — GPL (see 1.2)
  - **GPL-only codecs** pulled in by that build: `libx264-165`, `libx265`
  - **`--enable-version3` components**: `libopencore-amrnb`, `libopencore-amrwb`, `libgmp`
  - **Other codec libraries**: `libaom`, `libdav1d`, `libSvtAv1Enc`, `libvpx`, `libwebp`/`libwebpmux`/`libsharpyuv`, `libopenh264`, `libmp3lame`, `libtwolame`, `libvorbis`/`libvorbisenc`, `libogg`, `libopus`, `libspeex`, `zlib`
  - **Toolchain runtime**: `libgcc_s_seh-1`, `libstdc++-6`, `libwinpthread-1`, `libiconv-2`
  - **PyAV** (BSD-3-Clause), **faster-whisper** (MIT, SYSTRAN), **CTranslate2** (MIT), **ONNX Runtime** (MIT), **tokenizers**, **huggingface-hub**, **numpy**/**scipy** (BSD), **sounddevice** + **PortAudio** (MIT), **pyaudiowpatch** (MIT), **tqdm** (MIT)
  - **Whisper model weights** — MIT, OpenAI, redistributed via `Systran/faster-whisper-base` (verified: MIT, not gated, no acceptable-use policy)
  - **Tauri / Rust crates** (MIT or Apache-2.0), **`WebView2Loader.dll`** (Microsoft, proprietary — see design.md decision 2)
  - **PyInstaller** bootloader — GPL with its bootloader exception, which permits frozen applications under any license

- [x] 1.2 In the same file, state that the bundled FFmpeg is a `--enable-gpl --enable-version3` build, so the FFmpeg binaries are GPLv3, and that the distributed artifact is therefore offered as GPLv3 (design.md decision 1)

- [x] 1.3 Determine the exact upstream versions PyAV 16.0.1 built, and record them in a `SOURCE-PROVENANCE.txt` with a resolving source URL for each

  This is the real work behind the source obligation — the binaries were built by PyAV, not here, so "corresponding source" means the versions *it* pinned. Read PyAV's build scripts at the `16.0.1` tag for the pinned FFmpeg, x264, and x265 versions, and cross-check against what the shipped binary reports: `libavcodec 62.11.100`, `libavformat 62.3.100`, `libavutil 60.8.100`, `libswresample 6.1.100` (FFmpeg 8.0.x), `libx264` build 165, `libx265`.

  Record: `av==16.0.1`, those library versions, the full configure string (already extracted — see design.md decision 1), and a **verified-resolving** source URL for each GPL component. Under GPLv3 §6(d) these URLs *are* the compliance mechanism, so each one must be checked to actually resolve before publishing, not assumed.

- [x] 1.4 Document the release step and the standing duty to keep the source links alive

  Per design.md decision 3, compliance rests on directions to upstream source, so the release procedure must state that `SOURCE-PROVENANCE.txt` ships with every release and its links are re-checked at release time. Note the standing obligation: under §6(d) the project remains responsible for source availability even though a third party hosts it, so a link that stops resolving must be fixed or the source rehosted — x265's original Bitbucket hosting disappearing in 2020 is the precedent. Note also that a dependency bump changing any bundled version requires refreshing this file.

## 2. Correct the existing licensing documents

- [x] 2.1 Rewrite `LICENSE`'s "Third-Party Components" section

  Delete the FFmpeg entry's "**Note: FFmpeg must be installed separately on the system**" — false since `drop-ffmpeg-dependency`; FFmpeg is now bundled. Replace the vague "All Python dependencies ... use licenses compatible with GPLv2" with a pointer to `THIRD-PARTY-LICENSES.txt`, and state the GPLv3 position from 1.2.

- [x] 2.2 Correct `README.md`'s License section (currently `## License` → "GPLv2" plus a single line about faster-whisper)

  It should state that the source is GPL-2.0-or-later, that the distributed binary is GPLv3 because of bundled components, and point at `LICENSE` and `THIRD-PARTY-LICENSES.txt` instead of naming one dependency.

- [x] 2.3 Add the MIT notice and attribution for the model into `src-tauri/resources/model/`

  `tauri.conf.json` already bundles that directory, so the notice travels with the app automatically. Credit both OpenAI (original weights) and SYSTRAN (CTranslate2 conversion).

## 3. Ship the notices inside the artifact

- [x] 3.1 Change `build_portable.py` to copy `THIRD-PARTY-LICENSES.txt` and `LICENSE` into the assembled artifact for every platform it targets (Windows folder/zip, Linux AppImage, macOS)

  This is the task that actually discharges the obligation — notices that exist only in the repo do not reach anyone who receives the zip.

  Three files ship, not two: `SOURCE-PROVENANCE.txt` was added alongside `LICENSE` and `THIRD-PARTY-LICENSES.txt`, since under GPLv3 §6(d) the source directions are themselves part of what must reach the recipient. `build_portable.py` gained a `NOTICE_FILES` constant and a `_copy_notices()` helper that fails loudly if any of the three is missing, rather than shipping an artifact silently short a notice.

  Per platform:
  - **Windows** — `_copy_notices()` writes all three into the assembled folder. Verified: the extracted folder and `Transcriber.zip` both contain `LICENSE`, `THIRD-PARTY-LICENSES.txt`, `SOURCE-PROVENANCE.txt`, and `resources/model/LICENSE.txt`.
  - **Linux** — **verified on real hardware** (Fedora, `cargo tauri build` + `build_portable.py`, then `--appimage-extract`). The AppImage is a sealed single file that `build_portable.py` only copies, so the notices are bundled at `cargo tauri build` time via `tauri.conf.json`'s `bundle.resources`. Inside the extracted AppImage they land at `usr/lib/Transcriber/{LICENSE,THIRD-PARTY-LICENSES.txt,SOURCE-PROVENANCE.txt}`, with the model notice at `usr/lib/Transcriber/resources/model/LICENSE.txt`.

    **The `../` array form worked but placed them badly, so the config changed.** Tauri rewrites `..` path components to a literal `_up_` directory (`resource_relpath()` in `tauri-utils`), so `"../LICENSE"` in the array form shipped as `usr/lib/Transcriber/_up_/LICENSE` — present, and technically compliant, but filed under a directory name that tells a recipient nothing. `bundle.resources` was switched to Tauri's map form, which takes an explicit destination per entry, putting each notice at the root of the resource dir under its own name.

    The model entry became `"resources/model": "resources/model"` — a **directory** key, not the previous `resources/model/**/*` glob. That distinction matters: in map form Tauri flattens glob matches (`dest.join(file_name)`), which would have collapsed the `.cache/huggingface/` subtree into `resources/model/`, whereas a directory key walks and preserves structure (`dest.join(strip_prefix(pattern))`). Verified the resulting tree is identical to the source `src-tauri/resources/model/` file-for-file, so `resolve_model_dir()` in `sidecar.rs` is unaffected.

    *Build-environment note, not a code issue:* on Fedora 44 `cargo tauri build` fails at `failed to run linuxdeploy`. The cause is stripping, not FUSE — linuxdeploy strips every bundled library using the `strip` from its own AppImage, and that binutils is too old to parse `.relr.dyn` (`unknown type [0x13] section`), a compact relocation format Fedora's toolchain now emits by default, so every modern system library it copied in fails. `NO_STRIP=1 cargo tauri build` skips the strip pass and the bundle completes. (Tauri already exports `APPIMAGE_EXTRACT_AND_RUN=1` when it invokes linuxdeploy, so FUSE is never on the path.)
  - **macOS** — `_copy_notices()` writes into `Transcriber.app/Contents/Resources/` before the bundle is zipped, so the notices survive the user moving the `.app`. **Not run on macOS hardware in this change**, but the exposure is now small: that path is plain `shutil.copy2` from the same verified helper as Windows, and since the map-form change Tauri independently bundles the same three files to the same `Contents/Resources/` directory, so the script's copies overwrite identical content rather than being the only mechanism.

## 4. Verify

- [x] 4.1 Rebuild the Windows portable artifact and confirm the extracted folder contains both `LICENSE` and `THIRD-PARTY-LICENSES.txt`, and that `resources/model/` contains the model notice

- [x] 4.2 Confirm no remaining text anywhere in the repo claims ffmpeg must be installed separately

  `grep -rn -i "install.*ffmpeg\|ffmpeg.*install" README.md LICENSE *.bat *.sh` should return nothing describing it as a user prerequisite.

- [x] 4.3 Confirm the notices list matches what is actually bundled, by comparing against `av.libs/` in the build venv and the artifact's own contents — not against this task list, which is a snapshot and may drift

  Checked all 32 DLLs in `av.libs/` against `THIRD-PARTY-LICENSES.txt`. Six did not match on a first pass; five were naming variants already covered by their parent project's entry (`libSvtAv1Enc`→SVT-AV1, `libmp3lame`→LAME, `libvorbisenc`→libvorbis, `libwebpmux`→libwebp, `libgcc_s_seh`→libgcc).

  **One was a real gap: `libsharpyuv`.** It ships as its own DLL and a reader could reasonably look it up and find nothing. It belongs to the libwebp project under the same licence and copyright, so the libwebp entry now names all three of `libwebp`, `libwebpmux` and `libsharpyuv` explicitly. Re-ran the check afterwards: 32/32 accounted for.
