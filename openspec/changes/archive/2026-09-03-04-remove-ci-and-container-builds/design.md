## Context

See proposal.md - Why. This is a deletion change: no new mechanism is introduced, only the removal of machinery superseded by `02-add-wsl-linux-build` and `03-add-wsl-windows-build`.

## Goals / Non-Goals

**Goals:**
- Remove CI and the container cleanly, with no dangling references to either in specs or docs.
- Leave `linux-sidecar-build`'s still-true requirement (frozen binary runs standalone) intact.

**Non-Goals:**
- Building any new capability — this change only deletes and documents.
- Deciding whether to reintroduce CI later (out of scope; if wanted again, it's a new change against the specs this one leaves behind).

## Decisions

**REMOVE `docker-build` outright rather than MODIFY it.** Both of its requirements are specifically about container mechanics (bind-mount avoidance, copying output across a host/container boundary) — with no container, there is no boundary to describe. `wsl-linux-build`/`wsl-windows-build` (added in `02`/`03`) already state the WSL-equivalent filesystem requirement in their own terms; this isn't a rename of the old requirement; it's a genuinely different mechanism replacing it, hence REMOVE + already-ADDED elsewhere rather than MODIFIED.

**REMOVE only the CI-specific requirement in `linux-sidecar-build`, not the whole capability.** The "Frozen Linux sidecar runs standalone" requirement describes the binary's own behavior (runs without a Python interpreter, handles `--list-devices-json`) — true regardless of what built it. Only "CI produces a verified Linux build" is deleted, since it names the exact workflow file and runner being removed.

**Delete `.dockerignore` alongside `docker/`.** It exists only to scope the Docker build context; with no `docker build` invocation anywhere, it has no reader.

## Risks / Trade-offs

- [Deleting CI removes the only "did main branch's build actually still work" signal] → Mitigation: accepted deliberately — that signal's value was already in question (explicit user statement: "having the CI like this was not my end goal"); manual verification via `02`/`03`'s tasks replaces it for now.
- [A future contributor expects `.github/workflows/` to exist] → Mitigation: README's updated build section is the replacement source of truth for "how do I build this."
