## MODIFIED Requirements

### Requirement: Launcher prints the literal command instead of a banner
`win-start-transcription.bat` SHALL NOT print its own descriptive banner (title, source legend, output-filename notice). Instead, it SHALL print the exact command line it is about to execute (the `python transcriber.py` invocation from a source checkout, or the bundled `transcriber.exe` invocation from a release CLI archive), built and executed from the same value so the printed line cannot drift from the actual invocation.

#### Scenario: Launch prints the real command
- **WHEN** a user runs `win-start-transcription.bat sprint-review --silence-timeout 0` from a source checkout
- **THEN** the script prints the literal `python transcriber.py ...` invocation, including the resolved output filename and all passed-through flags, before running that exact command

#### Scenario: Launch from a release CLI archive prints the real command
- **WHEN** a user runs `win-start-transcription.bat sprint-review` from an extracted release CLI archive
- **THEN** the script prints the literal `transcriber.exe ...` invocation it is about to run, including the resolved output filename and all flags, before running that exact command

#### Scenario: No separate banner text
- **WHEN** a user runs the launcher with any arguments
- **THEN** no title banner, source legend, or separately-worded output-filename notice is printed by the launcher itself
