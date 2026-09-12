## Context

See proposal.md - Why. The relevant pieces:

- `fetch_sidecar_resources.py` is three lines of work: it calls faster-whisper's `download_model("base", output_dir="src-tauri/resources/model")` and prints where the model landed. The downloader creates `.cache/huggingface/` inside that output directory for its own bookkeeping: per-file `.lock` files, a `CACHEDIR.TAG`, and a `trees/<hash>.json` recording what it fetched.
- `src-tauri/tauri.conf.json` maps `"resources/model": "resources/model"`, and Tauri copies the directory recursively, so whatever sits in it ships.
- `build_portable.py` copies the same directory for the CLI archive but passes `shutil.ignore_patterns(".cache")`, so the two packaging paths already disagree about what belongs in a release.
- On this machine the directory is ~429 KB across six files, inside a ~300 MB package.

## Goals / Non-Goals

**Goals:**
- A staged `resources/model` that contains only what the app needs, so every packaging path ships the same thing.

**Non-Goals:**
- Changing `bundle.resources`, or listing model files individually (brittle: the file set depends on the model).
- Removing `build_portable.py`'s `.cache` exclusion. It becomes redundant, but it is one argument and it keeps the CLI archive correct even if someone stages the model by hand.
- Any change to which model is fetched, or to how the sidecar resolves it.

## Decisions

### 1. Clean up in `fetch_sidecar_resources.py`, not in the bundler config

The script owns staging, so it should hand over a clean directory. Doing it there fixes every consumer at once — the three Tauri bundles, the CLI archive, and any future packaging path — rather than teaching each one to skip the same directory. It also keeps the fix next to its cause: the line that creates `.cache` is the `download_model()` call immediately above.

`shutil.rmtree(model_dir / ".cache", ignore_errors=True)` after the download is enough. `ignore_errors` covers the case where a future faster-whisper version stops creating the directory, so the script doesn't fail on a missing path.

**Rejected: excluding it in `tauri.conf.json`.** Tauri's `bundle.resources` maps paths to destinations and has no ignore-pattern support, so the alternative would be enumerating the model's files — which breaks the moment the model changes.

**Rejected: deleting it in the workflow.** That would fix CI only, leaving local builds shipping the files, and would spread packaging knowledge into the pipeline.

### 2. Verify by listing a built package, not by inspecting the directory

The staged directory being clean is necessary but not sufficient — what matters is what ends up inside a bundle. So the check is `rpm -qpl` on a locally built `.rpm` showing no `.cache` entries, with the model's real files (`model.bin`, `config.json`, `tokenizer.json`, `vocabulary.txt`, `LICENSE.txt`) still present. That also guards `licensing`'s requirement that the model's license ship beside the weights.

## Risks / Trade-offs

- **[Risk]** A future faster-whisper stores something *needed* under `.cache` → today it holds only locks, a `CACHEDIR.TAG` and a provenance JSON, and the model loads from the four files beside it (proved by every offline transcription so far, including the CLI archive, which has never shipped `.cache`). Task 1.2's package listing plus an offline transcription would catch a regression.
- **[Trade-off]** Re-running the script re-downloads nothing but does re-create and re-delete `.cache`; the `trees/*.json` that lets the downloader skip work is deleted too, so a subsequent run re-verifies the files. That costs seconds at staging time and is irrelevant in CI, which always starts clean.
