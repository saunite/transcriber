# Project Workflow

## Purpose

Ensure every project change is optimized with the ponytail skill and that artifact instructions carry accurate project context.

## Requirements

### Requirement: Apply ponytail optimization to every change
The system SHALL ensure that every change to this project is optimized using the ponytail skill, and SHALL surface this requirement in the artifact instructions of every change via the project config.

#### Scenario: Skill available
- **WHEN** the ponytail skill is available while working on a change
- **THEN** the system uses it to review and optimize the change

#### Scenario: Skill unavailable
- **WHEN** the ponytail skill is not available while working on a change
- **THEN** the system proceeds with the change normally and informs the user that the ponytail skill was unavailable

### Requirement: Provide accurate application context
The system SHALL include an accurate description of the application (tech stack, purpose, conventions) in the project config context so that artifact instructions are written with correct project background.

#### Scenario: Artifact instructions generated
- **WHEN** artifact instructions are generated for any change
- **THEN** the instructions include the project context describing the application
