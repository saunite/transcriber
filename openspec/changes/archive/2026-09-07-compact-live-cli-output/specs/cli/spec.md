## ADDED Requirements

### Requirement: Live capture output is compact by default, with verbose detail available on request
During live capture, the system SHALL print a compact default output — one line naming the output file, one line summarizing model/language/capture mode/devices, and one line confirming it is listening — rather than the full startup/device-detection/shutdown detail. The system SHALL provide a `--verbose` flag that restores the full detail (startup banners, explicit per-device auto-detection messages, and capture-module start/stop announcements) in addition to the compact lines, and SHALL leave transcript line formatting and file-mode output unaffected by this flag.

#### Scenario: Default live capture output
- **WHEN** a user runs `--live` without `--verbose`
- **THEN** the system prints a compact preamble (output file, model/language/mode/device summary, listening confirmation) and a compact stop summary, without the full startup banners or per-device detail

#### Scenario: Verbose live capture output
- **WHEN** a user runs `--live --verbose`
- **THEN** the system prints the compact lines plus the full startup banners, explicit device auto-detection messages, and capture-module start/stop announcements

#### Scenario: File transcription is unaffected
- **WHEN** a user runs `--file` with or without `--verbose`
- **THEN** file-mode output is unchanged by this flag
