## Context

`openspec/config.yaml` currently holds only the schema name and commented-out examples for `context` and per-artifact `rules`. The OpenSpec loader injects the `context` field into every artifact instruction and the `rules` entries into their matching artifact instructions (proposal, specs, design, tasks) — so config is the single place to make a standing project-wide rule stick.

## Goals / Non-Goals

**Goals:**
- Populate `context` with an accurate description of the application.
- Add the ponytail rule (with fallback) as a custom rule on all four artifacts so it surfaces on any change.

**Non-Goals:**
- No change to application code or runtime behavior.
- No new dependency. The ponytail skill is referenced by name only; if the skill isn't present, nothing in this repo changes behavior.

## Decisions

1. **Put the ponytail rule in `rules` under every artifact** (proposal, specs, design, tasks). The config loader validates rule keys against the schema's artifact ids, so these four keys are exactly the supported set; covering all of them makes the rule apply to any change regardless of which artifact is being written. The alternative — adding it only to `context` — would also surface it everywhere, but the user explicitly asked for a custom rule.

2. **Phrase the rule as one string with two sentences.** The rule must state both the mandatory use of the ponytail skill and the fallback ("if the skill is not available, continue normally but inform the user") as a single rule so an agent sees the full instruction together.

3. **Keep `context` concise** (a few lines) since it is injected into every artifact instruction; the loader warns above a 50KB limit, so brevity avoids noise. Content: application purpose (offline audio/video transcription using faster-whisper), platforms (Windows/Linux), key stack (Python, faster-whisper, sounddevice, pyaudiowpatch, numpy/scipy, ffmpeg), output formats, and the OpenSpec workflow used.

4. **Model the requirement as a new `project-workflow` capability** in the delta spec, because the OpenSpec schema requires at least one delta and no existing capability (audio-capture, audio-extraction, cli, transcription) covers development-workflow rules. The spec documents the ponytail requirement and the context requirement; config.yaml is the enforcement mechanism.

## Risks / Trade-offs

- Rule repetition across four artifacts → acceptable: it is the only supported way to express a global rule in this config format, and it is four short lines.
- Skill reference could go stale → mitigation: the rule names the skill and defines a safe fallback, so a missing/unavailable skill never blocks work.
- Context descriptions can drift → mitigation: keep it short and generic enough to stay accurate (purpose, platform, key libs) rather than a detailed inventory.
