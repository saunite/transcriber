## ADDED Requirements

### Requirement: Capture native macOS system audio loopback
The system SHALL support native system-audio loopback capture on macOS 14.4+ via the Core Audio Process Tap API, requiring no virtual audio driver, and SHALL convert captured audio to float32 mono for transcription.

#### Scenario: Native tap capture on supported macOS
- **WHEN** a user starts live capture with the macOS native tap on macOS 14.4 or later
- **THEN** the system captures system audio output via the Core Audio Process Tap and delivers float32 mono chunks to the transcription pipeline

#### Scenario: Unsupported macOS version
- **WHEN** a user requests native tap capture on macOS older than 14.4
- **THEN** the system fails fast with a message explaining the version requirement and pointing to the virtual-driver fallback, without attempting to spawn the native helper

#### Scenario: Audio capture permission not granted
- **WHEN** the native helper creates a process tap without the required privacy permission granted, which Core Audio reports as success at every call while never delivering audio frames
- **THEN** the system detects that no audio arrived within a few seconds of the stream starting and reports that audio capture permission must be granted in System Settings, rather than hanging indefinitely with no output

#### Scenario: Native tap capture attempted outside a packaged application bundle
- **WHEN** native tap capture is attempted from a bare command-line process rather than from a launched `.app` bundle
- **THEN** macOS never presents the authorization prompt and no audio frames arrive, and the system surfaces the same no-audio permission error rather than hanging — native tap capture requires the packaged application

#### Scenario: Tap creation fails for another reason
- **WHEN** the native helper's tap-creation call fails for a reason other than OS version or permission
- **THEN** the system surfaces the underlying error to the user and suggests the virtual-driver fallback, without automatically switching capture modes

### Requirement: macOS virtual-driver fallback capture
The system SHALL support live capture on macOS through the existing device-based capture path when the user has installed a virtual audio loopback driver and selected it as the input device, providing a working capture path independent of native tap availability.

#### Scenario: Fallback capture via virtual driver
- **WHEN** a user starts live capture on macOS with a virtual loopback device selected via `--audio-device`
- **THEN** the system captures system audio through that device using the existing simple capture path, unchanged
