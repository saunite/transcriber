## ADDED Requirements

### Requirement: Launcher runs the standalone CLI when bundled with it
Each platform's launcher script SHALL invoke the standalone CLI executable, with the same flags, when that executable sits in the same directory as the script (as it does in a release's CLI archive). Otherwise it SHALL keep invoking `transcriber.py` through Python as before. Where the other launcher requirements name `transcriber.py`, the standalone executable satisfies them whenever this requirement applies.

#### Scenario: Run from an extracted CLI archive
- **WHEN** a user runs a platform's launcher script from an extracted release CLI archive, with no Python installed
- **THEN** the launcher runs the bundled standalone executable with its default flags (including `--actual-time` and `--include-mic`) plus any passed-through flags

#### Scenario: Run from a source checkout
- **WHEN** a user runs a platform's launcher script from a source checkout with no standalone executable next to it
- **THEN** the launcher runs `transcriber.py` through Python exactly as before
