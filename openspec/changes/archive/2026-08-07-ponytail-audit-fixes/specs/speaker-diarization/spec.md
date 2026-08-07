# Speaker Diarization (removed)

## REMOVED Requirements

### Requirement: Diarize audio to identify speakers
**Reason**: The capability was never implemented — `speaker_diarization.py` and `audio_buffer.py` do not exist in the repository, so the `--diarize` path crashes at runtime instead of working.
**Migration**: Remove the `--diarize` flag and related speaker arguments from any scripts or invocations.

### Requirement: Constrain speaker count
**Reason**: Part of the never-implemented diarization feature; dead code referencing nonexistent modules.
**Migration**: Remove `--num-speakers`, `--min-speakers`, `--max-speakers` arguments.

### Requirement: Merge transcription with diarization
**Reason**: Part of the never-implemented diarization feature.
**Migration**: None; transcription output no longer carries speaker labels.

### Requirement: Report speaker statistics
**Reason**: Part of the never-implemented diarization feature.
**Migration**: None; per-speaker statistics are no longer reported.

### Requirement: Format transcript with speaker labels
**Reason**: Part of the never-implemented diarization feature.
**Migration**: Use plain transcription output without speaker labels.

### Requirement: Gracefully handle missing diarization dependencies
**Reason**: No longer applicable — the diarization feature itself is removed, so there is nothing to degrade gracefully.
**Migration**: None.
