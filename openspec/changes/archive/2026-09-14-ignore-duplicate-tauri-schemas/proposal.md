## Why

`src-tauri/gen/schemas/` tracks four byte-identical 137,527-byte JSON schemas (sha256 `0b57b906…`): `desktop-schema.json`, `linux-schema.json`, `windows-schema.json` and `macOS-schema.json`, 2,677 lines each. Tauri writes one per platform it builds on. Only `desktop-schema.json` is referenced, by `src-tauri/capabilities/default.json`'s `$schema`, for editor completion. The other three are 8,031 tracked lines that no code, workflow or document uses. They also churn together on every Tauri upgrade, cluttering those diffs. Found by the ponytail audit on 2026-09-14.

## What Changes

- Stop tracking `linux-schema.json`, `windows-schema.json` and `macOS-schema.json`, and ignore them in `src-tauri/.gitignore`, so a local or CI build that regenerates them leaves the working tree clean.
- Keep `desktop-schema.json`, `acl-manifests.json` and `capabilities.json` tracked. Editor completion for `capabilities/default.json` keeps working in a fresh clone, before any build.
- **Not in scope:** ignoring the whole `gen/schemas/` directory, which is what Tauri's app template does. That would also drop the one referenced schema until the first build, which the maintainer didn't ask for.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none. Repository housekeeping with no behaviour change; `skip_specs` is set.)

## Impact

- **Changed:** `src-tauri/.gitignore`. Three files are removed from the index; they stay on disk.
- **Unchanged:** every build output, since Tauri regenerates the schemas itself. Also CI, packaging, and `capabilities/default.json`.
- **Net:** -8,031 tracked lines.
