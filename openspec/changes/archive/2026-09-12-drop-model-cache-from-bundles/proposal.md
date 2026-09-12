## Why

Every Tauri bundle ships the model directory's Hugging Face download bookkeeping. `rpm -qpl` on the CI-built package lists six files that have no business in a release:

```
/usr/lib/Transcriber/resources/model/.cache/huggingface/CACHEDIR.TAG
/usr/lib/Transcriber/resources/model/.cache/huggingface/download/config.json.lock
/usr/lib/Transcriber/resources/model/.cache/huggingface/download/model.bin.lock
/usr/lib/Transcriber/resources/model/.cache/huggingface/download/tokenizer.json.lock
/usr/lib/Transcriber/resources/model/.cache/huggingface/download/vocabulary.txt.lock
/usr/lib/Transcriber/resources/model/.cache/huggingface/trees/ebe41f70…json
```

`fetch_sidecar_resources.py` calls faster-whisper's `download_model()` with `output_dir=src-tauri/resources/model`, which leaves a `.cache/huggingface/` directory alongside the weights (~429 KB here). `tauri.conf.json`'s `bundle.resources` then copies `resources/model` wholesale, so the `.deb`, `.rpm` and AppImage all carry it. `build_portable.py` already excludes `.cache` when assembling the CLI archive, so the two paths disagree today.

This was found while investigating a package-size discrepancy during `switch-rpm-compression-to-zstd`: a local build had 21 files where CI's had 27, and the six extras were these.

## What Changes

- **`fetch_sidecar_resources.py` removes the `.cache` directory after staging the model.** The script's job is to leave a clean `resources/model` for bundling, so cleaning up the downloader's scratch state belongs there — one place, ahead of every bundler and of `build_portable.py`.
- **Nothing else.** The weights, `config.json`, `tokenizer.json`, `vocabulary.txt` and `LICENSE.txt` are untouched, and so is `bundle.resources`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — no requirement describes which files the model directory contains. `desktop-gui`'s "Fully offline first run" and "Sidecar always loads the bundled model explicitly" requirements are about the model being present and used, which is unaffected; `licensing`'s requirement that the model's license ship beside the weights is also unaffected, since `LICENSE.txt` is not in `.cache`.)

This change sets `skip_specs: true` in `.openspec.yaml`.

## Impact

- **Changed**: `fetch_sidecar_resources.py` (a few lines).
- **Effect**: six pointless files and ~429 KB leave the `.deb`, `.rpm` and AppImage. That is housekeeping, not a measurable download saving on a ~300 MB package.
- **Why do it at all**: a release shouldn't ship another tool's lock files, the two packaging paths shouldn't disagree about what the model directory is, and the stale `trees/*.json` records where the file came from on the build machine.
- **Unchanged**: the CLI archive, which already excluded `.cache`.
