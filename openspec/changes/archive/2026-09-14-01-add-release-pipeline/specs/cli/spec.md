## MODIFIED Requirements

### Requirement: Accept an explicit local model path
The system SHALL provide `--model-path <dir>` to load the whisper model from a local directory directly, bypassing the network/cache-based model name lookup, for both file and live transcription modes. When `--model-path` is not given, the standalone (frozen) CLI executable SHALL load its bundled model from a `model` directory next to the executable if that directory holds a model and the requested `--model` size is the bundled size (`base`).

#### Scenario: File transcription with explicit model path
- **WHEN** a user runs `--file audio.wav --model-path C:\path\to\model`
- **THEN** the system loads the model from the given directory instead of resolving `--model` by name

#### Scenario: Live capture with explicit model path
- **WHEN** a user runs `--live --model-path C:\path\to\model`
- **THEN** the system loads the model from the given directory instead of resolving `--model` by name

#### Scenario: No model path given
- **WHEN** `--model-path` is not passed and the system is not running as a standalone executable with a bundled model next to it
- **THEN** the system behaves exactly as before, resolving `--model` by name

#### Scenario: Standalone executable with its bundled model
- **WHEN** the standalone CLI executable is run without `--model-path`, with `--model base` or no `--model` flag, and a `model` directory containing a model sits next to the executable
- **THEN** the system loads the model from that directory and attempts no download

#### Scenario: Standalone executable asked for a different model size
- **WHEN** the standalone CLI executable is run without `--model-path` and with a `--model` size other than `base`
- **THEN** the system ignores the bundled model and resolves the requested size by name, as before
