# Contributing

Thanks for looking. This is an offline transcription tool with two front ends
over one Python engine: a CLI (`transcriber.py`) and a Tauri desktop app
(`src-tauri/` for the Rust shell, `src/` for the HTML, CSS and JavaScript). The
app runs the CLI, frozen with PyInstaller, as a bundled sidecar process.

To use the tool, read [the user guide](docs/user-guide.md). To build artifacts,
read [docs/building.md](docs/building.md).

## How changes are made

Work here runs on [OpenSpec](https://github.com/Fission-AI/OpenSpec), so what the
project promises lives in files rather than in commit messages:

- **`openspec/specs/`** is the contract: one folder per capability, each holding
  requirements and the scenarios that make them concrete. It describes what the
  tool does today.
- **`openspec/changes/<name>/`** is work in flight. A change holds a `proposal.md`
  (why, and what changes), spec deltas under `specs/` saying which requirements
  are added, modified or removed, a `tasks.md`, and a `design.md` when there are
  technical decisions worth arguing.
- **`openspec/changes/archive/`** holds finished changes, and
  **`openspec/backlog.md`** holds work that was deliberately parked.

A change moves through three steps: propose it, implement it, then archive it.
Archiving merges the deltas into `openspec/specs/`, so the specs stay true
without anyone editing them by hand. `openspec validate --strict` checks a
change's shape, and `openspec status --change <name>` shows what is left.

Two habits make a change easy to review:

- **Write the test first.** A bug fix starts with a check that fails on today's
  code; record what it failed with. Then fix it and watch the same check pass.
- **Say what you verified.** Each task in `tasks.md` names how it was checked,
  so a reader doesn't have to take the result on faith.

## Running the tests

One-time setup, in the project venv. The tests also need the bundled model (`python fetch_sidecar_resources.py`) and a Rust toolchain for `cargo test`:

```bash
pip install -r requirements-dev.txt          # Playwright, for the GUI tests only
python -m playwright install chromium        # one-time browser download
```

Run everything:

```bash
.venv/bin/python run_tests.py
```

It runs each suite, prints PASS/FAIL with its duration, and exits 1 if any failed. A failing suite does not stop the others.

| Suite | What it covers |
|---|---|
| `cargo test` (in `src-tauri/`) | Sidecar argument building, Windows path handling, and stopping the whole engine process tree |
| `test_*.py` (repo root) | Engine and packaging units: bundled model default, live output path, transcript line format, mic fallback, macOS/WASAPI capture helpers, AppImage stripping |
| `tests/test_gui.py` | The real `src/index.html` in headless Chromium with a fake `window.__TAURI__` (`tests/fake_tauri.js`), so no app build, audio or engine: live start/stop and the SYS/MIC indicators, the one-at-a-time file queue, unsupported files, a refused file run, and a check that every command the page invokes is registered in `src-tauri/src/main.rs` |
| `tests/test_engine.py` | Transcribes a local English recording and checks the timestamped transcript, the detected language and at least 70% of its script's key words; random bytes must fail cleanly with no traceback and no transcript file |
| `tests/test_e2e_linux.py` | Linux only. Builds the debug app and drives its real window through `tauri-driver`. Checks: the update check gives a real verdict online; with no network (inside `unshare -rn`) it says it couldn't check and the engine still transcribes; nothing opens a network connection at startup (`strace`); **Open download page** hands exactly the releases URL to the OS opener (a recording `xdg-open`); a chosen model folder is remembered across restarts, refused without `model.bin`, and actually loaded. Each app run gets its own data directory, so your real app settings are untouched |

**The speech recording is not in the repo.** Use any English recording you have, in any format the engine decodes, kept outside the repository and never committed. Put the words it says in a `.txt` with the same name beside it, then:

```bash
TRANSCRIBER_TEST_SPEECH=~/recordings/sample.ogg .venv/bin/python run_tests.py   # reads ~/recordings/sample.txt
```

Without it, the speech check prints `SKIP` and the rest still runs. `tests/test_engine.py` also takes `--speech <audio>` and `--script <txt>` directly.

**The end-to-end suite** (`tests/test_e2e_linux.py`) runs only on Linux, from a graphical desktop session. **App windows open and close on screen while it runs.** It also needs the staged sidecar in `src-tauri/binaries/` and these tools, installed once:

```bash
cargo install tauri-driver --locked            # WebDriver bridge for Tauri apps
sudo dnf install webkitgtk6.0 strace           # Fedora: WebKitWebDriver + strace
sudo apt install webkitgtk-webdriver strace    # Debian/Ubuntu equivalent (webkit2gtk-driver on older releases)
```

`unshare` (util-linux) and `ip` (iproute2) are normally present already. When something is missing, every scenario prints `SKIP` with what to install, and the suite doesn't fail. The online update check prints `SKIP` when `api.github.com` can't be reached (some VPNs block it). WebKitWebDriver doesn't support native clicks here ([tauri#6541](https://github.com/tauri-apps/tauri/issues/6541)), so the suite clicks the real buttons from script.

**Testing a frozen engine.** The engine tests use `transcriber.py` by default. Point them at a built sidecar with `--engine`:

```bash
.venv/bin/python tests/test_engine.py --engine dist/linux/transcriber-sidecar
```

Every change lands with the whole suite passing. If a suite is skipped because
something isn't installed, say so rather than reporting a clean run.

## Changing the desktop interface

The app has a deliberate visual design, written down in
[DESIGN.md](DESIGN.md): a chart recorder, with two pens drawing on a time axis.
A change to the layout, the styling, or how the interface behaves goes through
the design pass that produced it, which means an explicit design step,
screenshots in light and dark at the normal window size and at the 640x480
minimum, an independent review of the finished work, and an update to
`DESIGN.md` when the system itself changes.

That sounds heavy for a one-line CSS edit, and it is deliberate: the interface
is the part of this project that can't be checked by a test alone.

## Branches

Work lands on `dev`. `main` only ever fast-forwards to `dev`, so it always
points at a commit that was already on `dev`, and history is never rewritten on
either branch. Releases are tagged from `main`; see
[docs/building.md](docs/building.md) for how one is made.
