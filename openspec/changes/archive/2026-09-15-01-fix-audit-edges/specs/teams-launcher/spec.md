## ADDED Requirements

### Requirement: Launcher works from any folder and names the model it loads
The Linux and macOS launcher scripts SHALL run `transcriber.py` from the folder the script is in, so they work when started from any current folder, while still saving the transcript in the current folder. They SHALL NOT pass a model size of their own, so a `--model-path` passed through to them is loaded and named after its folder, and a `--model` passed through selects that size.

#### Scenario: Started from another folder in a source checkout
- **WHEN** a user runs `/path/to/checkout/linux-start-transcription.sh` from a different current folder
- **THEN** the launcher runs the checkout's `transcriber.py` and the transcript file is created in the current folder

#### Scenario: A model folder passed through
- **WHEN** a user runs a Linux or macOS launcher with `--model-path /models/small`
- **THEN** the underlying invocation contains no `--model` flag, and the transcription output names the model `small`

#### Scenario: No model flags passed
- **WHEN** a user runs a Linux or macOS launcher without `--model` or `--model-path`
- **THEN** the session uses the default `base` model, including the bundled model next to a standalone CLI
