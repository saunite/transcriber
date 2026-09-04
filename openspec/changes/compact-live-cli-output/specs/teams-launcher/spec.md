## ADDED Requirements

### Requirement: Launcher prints the literal command instead of a banner
`start_teams_transcription.bat` SHALL NOT print its own descriptive banner (title, source legend, output-filename notice). Instead, it SHALL print the exact `transcriber.py` command line it is about to execute, built and executed from the same value so the printed line cannot drift from the actual invocation.

#### Scenario: Launch prints the real command
- **WHEN** a user runs `start_teams_transcription.bat sprint-review --silence-timeout 0`
- **THEN** the script prints the literal `python transcriber.py ...` invocation, including the resolved output filename and all passed-through flags, before running that exact command

#### Scenario: No separate banner text
- **WHEN** a user runs the launcher with any arguments
- **THEN** no title banner, source legend, or separately-worded output-filename notice is printed by the launcher itself
