# Building Transcriber

How to build the app and the CLI from source, and how a release is made. To
use the tool, see [the user guide](user-guide.md); to work on it, see
[CONTRIBUTING.md](../CONTRIBUTING.md).

All development happens on Linux/WSL; the sections below cover the Windows and Linux artifacts from there. On macOS (or any other platform with a native Rust toolchain + [Tauri CLI](https://tauri.app/) already set up), stage the sidecar binary under `src-tauri/binaries/transcriber-sidecar-<target-triple>.exe`, then:

```bash
cargo tauri build          # from src-tauri/
python build_portable.py   # assembles the portable artifact for the current OS into dist/portable/
```

## Updating the icon

The master icon is `resources/transcriber-icon-1024.png`, exported from `resources/src/transcriber-icon-full-size.xcf`, and every app icon under `src-tauri/icons/` is generated from it. After editing the `.xcf`, regenerate both, then drop the Android, iOS and Windows Store outputs this app doesn't use:

```bash
# -compose over matters: the XCF reader leaves "Compose: None" on the image,
# and without it -extent produces a blank light-blue square.
magick resources/src/transcriber-icon-full-size.xcf -background none -flatten -trim +repage \
  -compose over -gravity center -extent '%[fx:max(w,h)*1.24]x%[fx:max(w,h)*1.24]' \
  -background 'rgb(186,244,255)' -flatten -resize 1024x1024 resources/transcriber-icon-1024.png
cargo tauri icon resources/transcriber-icon-1024.png
rm -rf src-tauri/icons/android src-tauri/icons/ios src-tauri/icons/Square*Logo.png src-tauri/icons/StoreLogo.png
```

## Linux build (WSL or native Linux)

**Check out the repo on WSL's own (ext4) filesystem, not under `/mnt/c/...`.** `/mnt/c` is a 9p/DrvFs mount of the Windows drive — `CARGO_TARGET_DIR` (below) keeps cargo's *output* off it, but the *source* (`Cargo.toml`, every `src-tauri/src/*.rs`, `tauri.conf.json`) still has to be read from wherever the checkout lives, and Tauri writes generated schema files into `src-tauri/gen/` on every build. From a native path (e.g. `~/repos/transcriber`) none of that touches the Windows filesystem at all. Confirmed working from `~/repos/transcriber`: the `.venv` Windows Python interop (used to freeze the Windows sidecar, see the Windows build notes) still reaches the venv fine via WSL's `\\wsl.localhost\...` path — only that one-shot freeze crosses the boundary, in the direction that doesn't matter for build speed.

Building directly in a WSL (or any native Linux) environment needs these system packages, plus `rustup` and the Tauri CLI:

```bash
sudo apt-get install -y build-essential pkg-config libssl-dev \
    libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev \
    librsvg2-dev patchelf
rustup default stable
cargo install --locked tauri-cli --version "^2"
```

Point cargo's `target/` directory at a native (ext4) filesystem path, persistently — via `~/.cargo/config.toml` rather than an exported env var, so it doesn't depend on remembering to set it in every shell:

```toml
# ~/.cargo/config.toml (machine-local, not part of this repo)
[build]
target-dir = "/home/YOU/.cache/transcriber/target"
```

Keep the last path component named `target`: Tauri only treats the running binary as a development build (and so resolves the bundled model next to it) when its folder is `target/<profile>` or `target/<triple>/<profile>`. Under a differently named directory the app looks for the model at its *installed* path instead, and a dev run with no model folder chosen fails with `--model-path /usr/lib/Transcriber/resources/model does not exist`.

An exported `CARGO_TARGET_DIR` still works too and takes precedence if set. `build_portable.py` finds the real location either way (it asks `cargo metadata` directly, rather than only checking the env var).

Freeze the Linux sidecar from a **venv**, not the system Python — on distros where numpy is a system package (e.g. Fedora, linked against FlexiBLAS), building against system Python bundles a BLAS shim with no backend, and the frozen binary aborts on first transcription:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-linux.txt pyinstaller
./.venv/bin/python build_sidecar.py
mkdir -p src-tauri/binaries
cp dist/linux/transcriber-sidecar src-tauri/binaries/transcriber-sidecar-x86_64-unknown-linux-gnu
```

Then the rest of the Linux build. `NO_STRIP=1` is not optional on current distros: linuxdeploy strips every library it bundles using the `strip` from its own AppImage, and that binutils cannot parse `.relr.dyn` (`unknown type [0x13] section`), a compact relocation format Fedora and other modern toolchains emit by default — so every system library it copied in fails to strip and the bundle aborts with `failed to run linuxdeploy`. Skipping the strip pass costs a slightly larger AppImage and nothing else:

```bash
NO_STRIP=1 cargo tauri build   # from src-tauri/
python fetch_sidecar_resources.py   # stage the model, if not already staged
python build_portable.py
# Linux artifacts: dist/portable/*.AppImage (GUI)
#                  dist/portable/transcriber-cli_<version>_linux-x64.tar.gz (CLI)
# Add --bundles appimage,deb,rpm to the build above for the .deb/.rpm packages.
```

## Windows build (from WSL)

The Windows shell (Tauri) cross-compiles cleanly from WSL, but the Windows sidecar is a PyInstaller freeze, and PyInstaller does not cross-compile — it must run under a real Windows Python. WSL can execute Windows `.exe` binaries directly, so this uses a Windows Python venv reached from WSL rather than a separate Windows build step.

Add the mingw cross-toolchain (on top of the base toolchain from the Linux section above):

```bash
sudo apt-get install -y gcc-mingw-w64-x86-64 binutils-mingw-w64-x86-64
rustup target add x86_64-pc-windows-gnu
```

If `.venv/` (a Windows-targeted venv) doesn't already exist, create it from WSL via Windows Python and install the sidecar's dependencies:

```bash
python.exe -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt pyinstaller
```

Freeze the Windows sidecar through that venv. This checks for the specific venv interpreter, not just any `python.exe` on `PATH` — a generic `PATH` lookup can resolve to an unrelated interpreter (e.g. the Windows Store's stub launcher) that lacks the sidecar's dependencies, which would pass a looser check and then fail confusingly inside the freeze itself instead of failing clearly up front:

```bash
[ -x .venv/Scripts/python.exe ] || { echo "ERROR: no Windows Python venv at .venv/Scripts/python.exe -- see venv setup above" >&2; exit 1; }
./.venv/Scripts/python.exe build_sidecar.py
cp dist/windows/transcriber-sidecar.exe src-tauri/binaries/transcriber-sidecar-x86_64-pc-windows-gnu.exe
```

Then the rest of the Windows build, same as any other target:

```bash
cargo tauri build --target x86_64-pc-windows-gnu   # from src-tauri/
python fetch_sidecar_resources.py                  # stage the model, if not already staged
python build_portable.py --target x86_64-pc-windows-gnu
# Windows artifacts: dist/portable/Transcriber_<version>_windows-x64.zip (GUI)
#                    dist/portable/transcriber-cli_<version>_windows-x64.zip (CLI)
```

The bundled artifact ships the `base` Whisper model (~145MB) for a fully offline first run. No ffmpeg bundling is needed — the sidecar decodes audio and video via PyAV (bundled with faster-whisper), not an external ffmpeg binary; see `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`.

The GUI always passes the sidecar an explicit `--model-path`: the bundled model directory (resolved relative to the running app, so it works the same whether run from the extracted Windows folder, the AppImage, or the `.app`), or the model folder the user chose in the Model field. It never relies on faster-whisper's network/cache-based model lookup. The CLI gained the same `--model-path <dir>` flag for anyone running from a bundled build directly.

## Releasing

Releases are built by GitHub Actions (`.github/workflows/release.yml`) on fresh Linux, Windows, and macOS runners, not on a developer machine:

1. Set `version` in both `src-tauri/tauri.conf.json` and `src-tauri/Cargo.toml` to the new value. Run `cargo update -p transcriber-gui` in `src-tauri/` so `Cargo.lock` follows, and commit all three files.
2. Merge to `main`, then tag that commit and push the tag:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. The workflow first checks that the tag matches both version fields and that every source link in `SOURCE-PROVENANCE.txt` still resolves. Then it builds every platform and uploads the results to a **draft** release. Nothing is public yet.
4. Download and try at least one artifact from the draft, then click **Publish** on the release page. If something is wrong, delete it with `gh release delete v0.2.0 --cleanup-tag`, fix it, and tag again.

To build everything without releasing, for example to check that a branch still builds on every platform, start the workflow from the Actions tab (**Run workflow**). The outputs are downloadable from that run. GitHub only shows the button once the workflow file is on the default branch.

**Licensing: one step still needs a human.** The artifacts bundle GPL-licensed libraries (FFmpeg, x264, x265, via PyAV), so publishing one carries a source-availability obligation. `build_portable.py` and the Tauri bundle config copy `LICENSE`, `THIRD-PARTY-LICENSES.txt`, and `SOURCE-PROVENANCE.txt` into every artifact, and every release's notes link to `SOURCE-PROVENANCE.txt` as it was at that release's tag, instead of attaching it among the downloads.

- The links in that file *are* the compliance mechanism (GPLv3 §6(d)); a dead link is an unmet obligation. The workflow's link check fails the release when one stops resolving. The x265 archive on Bitbucket is the most likely to disappear; if the check flags it, correct the link or rehost the archive.
- **PyAV is pinned (`av==18.1.0` in the three `requirements*.txt` files), and bumping it means re-deriving everything in `SOURCE-PROVENANCE.txt`**: read the new PyAV `scripts/ffmpeg-*.json` for its `pyav-ffmpeg` tag, that tag's `scripts/pkg.py` and `build-ffmpeg.py` for the component versions and flags, and the new wheels for what actually ships. The workflow's preflight enforces it: a build fails when any pin differs from the `av ==` version the file records.
