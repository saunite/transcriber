## Context

See proposal.md - Why. The field's value was already used correctly end-to-end (empty → `null` → no `--language` flag → faster-whisper auto-detects); this change only replaces how the value is entered.

## Goals / Non-Goals

**Goals:**
- Replace ambiguous placeholder text ("auto") with an explicit, selectable "Auto-detect" state.
- Only offer languages faster-whisper actually supports, closing off invalid free-text codes.

**Non-Goals:**
- Surfacing the engine's detected language back to the user (explored and deferred this session — see Why).
- Any change to the IPC contract (`language: Option<String>`) or how `transcriber.py`/`transcription_engine.py` consume it.

## Decisions

**Full faster-whisper language table, not a curated subset.** A shorter "common languages" list was considered and rejected — narrowing it would be a real functionality regression for anyone who typed a less-common code into the old free-text field (Whisper supports roughly 100 languages), and the full table costs nothing at runtime; it's static data matching a fixed model capability, not something worth trimming for the picker's sake.

**List sourced by hand in `src/main.js`, not fetched from the sidecar.** The language table is fixed by the bundled faster-whisper model, not runtime app state — no IPC round-trip needed, and it's already how `model-select` and `format-select`'s static options work in this codebase.

**Sorted by language name, "Auto-detect" pinned first.** Codes (`af`, `am`, `ar`, ...) aren't how a person scans for "Spanish" — alphabetizing by the readable name is the useful order; "Auto-detect" is pinned above it since it's the default and most common choice, not alphabetized into the middle of the list.

## Risks / Trade-offs

- [A user who previously relied on typing an arbitrary/unlisted code loses that path] → Accepted; free text never actually worked reliably for codes faster-whisper doesn't recognize (transcription would just fail), so the dropdown mostly forecloses inputs that were already broken.
