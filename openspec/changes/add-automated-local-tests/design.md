## Context

See proposal.md - Why. The facts that shape the approach:

- **The page's only link to the app is `window.__TAURI__`.** `tauri.conf.json` serves `src/` (`frontendDist: "../src"`) and injects the bridge (`withGlobalTauri: true`). The first lines of `main.js` destructure `core.invoke`, `event.listen`, `dialog.open`/`save`, `window.getCurrentWindow` and `path.documentDir`/`homeDir`/`join`/`isAbsolute`. So the bridge must exist *before* `main.js` executes.
- **`main.js` is a classic script** (`<script src="main.js">`, no module, no bundler, no `fetch`). A browser can load it straight from `file://`.
- **What the page sends and receives.** It invokes `get_platform`, `list_devices`, `start_live_session`, `stop_live_session` and `start_file_transcription`. It listens for `transcript-line`, `sidecar-log`, `sidecar-crashed`, `file-transcription-complete`, `tauri://drag-drop` (with `payload.paths`) and `tauri://drag-enter`. The real command list is `generate_handler![…]` in `src-tauri/src/main.rs`.
- **Unsupported files are filtered in the page** (`SUPPORTED_EXTENSIONS`, `main.js:733`), so an unsupported drop never invokes anything.
- **File-mode engine output.** Segments go only to the output file, as `[mm:ss -> mm:ss] text` (`TranscriptionEngine.format_timestamp`). Stdout carries `Detected language: <code> (probability: …)` and the summary. Failures exit 1 with a message: `No decodable audio in …` for `NoDecodableAudioError`, or `Could not decode …` for FFmpeg errors. `--output` sets the transcript path.
- **Existing test conventions.** Plain `python test_x.py` scripts with `assert`, no pytest, no fixtures framework. All 7 pass on Linux today. The 13 Rust tests run under `cargo test` in `src-tauri/`.
- **Tooling on the development machine.** A project `.venv`, Node 22 with no `package.json`, and Playwright browsers already cached in `~/.cache/ms-playwright`. Development happens on Linux/WSL.

## Goals / Non-Goals

**Goals:**
- One command, run locally, that exercises every test the project has.
- GUI state and command logic checked in seconds, with no app build, no audio and no engine.
- Proof that real speech comes out as text, and that bad input fails without crashing.

**Non-Goals:**
- CI integration (a follow-up; the engine parameter is there to make it easy).
- Real-app end-to-end testing, visual or screenshot comparison, and WebKit-engine runs.
- Asserting the GUI shows a file run's transcript. See proposal.md's observed gap; it is untested in either direction.
- Moving or rewriting the existing tests.

## Decisions

### 1. Python Playwright, written as plain scripts

The GUI tests use Playwright's synchronous Python API in a plain script run as `python tests/test_gui.py`, the same shape as every existing test.

**Rejected: Node's `@playwright/test`.** Its runner is nicer (traces, UI mode), but it would add a `package.json`, `node_modules` and a second test ecosystem to a repo whose tests are all Python.

**Rejected: pytest.** Nothing in the repo uses it, and the existing scripts would need no change to keep working, so adopting it now buys a dependency and nothing else.

**Rejected: `tauri-driver`/WebDriver against the real app.** The local `WebKitWebDriver` belongs to `webkitgtk6.0` rather than the `webkit2gtk-4.1` Tauri uses, it isn't supported on macOS, and it needs a display and audio.

### 2. Load the page over `file://`, with no web server

Because `main.js` is a classic script with no `fetch`, Chromium loads `src/index.html` directly from disk. A local HTTP server would add a moving part for no gain.

### 3. One small fake bridge, injected before the page runs

`tests/fake_tauri.js` is injected with `page.add_init_script`, so it defines `window.__TAURI__` before `main.js` executes. It keeps state on `window.__fake`:

- `invoke(cmd, args)` records `{cmd, args}` in `__fake.calls`. It answers from `__fake.responses[cmd]` (a value, or `{reject: "message"}`), with defaults: `get_platform` → `"linux"`, `list_devices` → one input device, the others → `undefined`.
- `listen(name, handler)` stores the handler and resolves to an unlisten function. `__fake.emit(name, payload)` calls every stored handler with `{payload}`, which is how tests fire `transcript-line`, `file-transcription-complete`, `sidecar-crashed` and `tauri://drag-drop`.
- `path.*` resolves fixed POSIX strings. `dialog.open`/`save` resolve `null`, as a cancelled dialog would. `getCurrentWindow()` returns a `Proxy` whose every method is an async no-op, so window-chrome calls neither need listing one by one nor break when a new one is added.

Tests assert on two things only: the recorded calls, and visible state read through the existing element IDs (`run-state-label`, the `.pen-sys`/`.pen-mic` `.pen-state` text, `file-queue` items, `note-root`). A page `pageerror` listener fails the test on any uncaught script error.

**Guarding against the fake drifting from the real app:** a mock accepts whatever it is told, so a command renamed in Rust but not in `main.js` would still pass. One check reads the command names from `generate_handler![…]` in `src-tauri/src/main.rs` and every `invoke("…")` literal in `src/main.js`, and fails naming any command the page uses that the app doesn't register. It is a text comparison, needing no build.

### 4. Engine test: a subprocess, a selectable engine, loose word matching

`tests/test_engine.py` runs the engine as a subprocess with `--file <clip> --model-path src-tauri/resources/model --output <tmp>`. By default the engine is `[sys.executable, "transcriber.py"]`; `--engine <path>` swaps in a frozen binary, the same idea as `.github/smoke-test.sh`'s argument.

**Speech check.** It fails unless:
- the exit status is 0;
- no `Traceback` appears in stdout or stderr;
- the transcript file exists, and its non-comment lines match `^\[[^\]]+ -> [^\]]+\] \S`;
- stdout contains `Detected language: en`;
- the transcript recognises most of the script's key words, taken as the distinct words of five or more letters in the script file, compared case- and punctuation-insensitively, with at least 70% required.

**Why a threshold instead of exact text:** the `base` model is not word-perfect, and exact matching would fail on a harmless misheard word, which trains everyone to ignore the test. 70% of distinctive words still fails decisively when the engine produces nothing, the wrong language, or garbage.

**Undecodable-input check.** The test writes random bytes to a temporary `garbage.mp3` and expects:
- a non-zero exit;
- either `No decodable audio` or `Could not decode` in the output (random bytes may reach either handler, and both are the engine's clean-failure paths);
- no `Traceback`;
- no transcript file.

**Missing model:** if `src-tauri/resources/model/model.bin` is absent, the test stops with a message naming `fetch_sidecar_resources.py`, instead of letting the engine try a network download.

### 5. The speech fixture

The fixture lives at `tests/fixtures/speech-en.<ext>`, in whatever format the recording device produced, since the engine decodes it through PyAV. Beside it, `tests/fixtures/speech-en.txt` holds the script it was read from. The test finds the recording with `speech-en.*`, excluding the `.txt`. It is recorded by the maintainer, so it is redistributable under the repository's licence. The recording should be 10–15 seconds long, spoken at a normal pace somewhere quiet, reading:

> This is a test of the transcriber. The quick brown fox jumps over the lazy dog. Please record this meeting and save the notes.

### 6. One runner, at the repository root

`run_tests.py` runs, in order:
1. `cargo test` in `src-tauri/`;
2. every `test_*.py` at the root;
3. every `tests/test_*.py`.

Each suite runs as a subprocess with `sys.executable`, so running it as `.venv/bin/python run_tests.py` uses the project venv. Every suite runs even when an earlier one fails. The runner prints PASS/FAIL per suite and a summary, and exits 1 if any failed. It is standard library only.

### 7. Development dependencies kept apart from the app's

`requirements-dev.txt` lists `playwright`. Setup is `pip install -r requirements-dev.txt` followed by `python -m playwright install chromium`, the one-time browser download. The app's per-platform requirements files are untouched, because no user or build needs Playwright. README gains a short "Running the tests" section covering setup, the command and the fixture.

## Risks / Trade-offs

- **[Risk]** Chromium is not the engine the app ships with (WebKitGTK on Linux and macOS, WebView2 on Windows). → The state and command logic the recent bugs lived in behaves the same in any engine. Engine-specific rendering issues stay uncaught. A WebKit run is a possible follow-up, most practical on an Ubuntu CI runner.
- **[Risk]** The fake bridge drifts from the real app. → The command-name check in Decision 3 catches renames. Argument-shape drift, such as a renamed field, is still possible, and the Rust unit tests on argument building cover part of it.
- **[Risk]** A future model or CTranslate2 update shifts the transcription. → The 70% threshold absorbs small changes. A failure beyond that is worth looking at, not suppressing.
- **[Risk]** The Playwright browser download needs network access once, and a cached build may not match the pip-installed Playwright version. → `playwright install chromium` fetches the right build. After that, tests run offline.
- **[Trade-off]** The engine test loads a 142 MB model, so it takes roughly 5–15 seconds. That is acceptable for a command run before committing, and the GUI tests stay fast because they never touch the engine.
- **[Trade-off]** The recording is a binary file in git. It is small (tens of kilobytes compressed) and is the only way to test real speech deterministically without adding a text-to-speech dependency whose output differs between machines.
