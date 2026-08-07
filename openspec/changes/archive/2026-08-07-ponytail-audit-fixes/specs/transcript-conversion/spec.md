# Transcript Conversion (removed)

## REMOVED Requirements

### Requirement: Parse timestamped transcript lines
**Reason**: The standalone `convert_to_srt.py` script is deleted; parsing an existing timestamped transcript file into SRT is no longer a feature.
**Migration**: Generate SRT directly at transcription time with `--format srt` instead of converting a saved transcript afterward.

### Requirement: Convert parsed entries to SRT
**Reason**: The standalone converter is deleted; SRT writing is already provided by the transcription engine's `--format srt` output.
**Migration**: Use `transcriber.py --format srt` when transcribing.

### Requirement: Default output naming
**Reason**: The standalone converter is deleted.
**Migration**: Use the engine's default output naming for SRT files.
