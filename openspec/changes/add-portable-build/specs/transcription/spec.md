## MODIFIED Requirements

### Requirement: Control model, device, and compute settings
The system SHALL let users choose the whisper model size (tiny, base, small, medium, large, turbo), the execution device (auto, cpu, cuda), and compute type (auto, int8, float16, float32), with auto-detection from the environment. The system SHALL also accept an explicit local model directory path, which SHALL be used to load the model directly instead of resolving the model by name through the network/cache lookup, when provided.

#### Scenario: Auto device detection
- **WHEN** no device is specified
- **THEN** the system selects CUDA if torch reports a GPU available, otherwise CPU, and picks float16 for GPU or int8 for CPU when compute type is auto

#### Scenario: Explicit local model path provided
- **WHEN** a local model directory path is provided
- **THEN** the system loads the model from that directory directly, without attempting a network or cache-based model name lookup

#### Scenario: Local model path missing or incomplete
- **WHEN** a local model directory path is provided but the directory does not exist or is missing required model files
- **THEN** the system reports a clear error identifying the missing path before attempting to construct the model

#### Scenario: No local model path provided
- **WHEN** no local model directory path is provided
- **THEN** the system resolves the model by name exactly as before (network/cache lookup), unaffected by this capability
