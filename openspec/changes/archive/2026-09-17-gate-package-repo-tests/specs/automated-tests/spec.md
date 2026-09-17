## ADDED Requirements

### Requirement: Package repository checks run only when requested
The package repository checks (the apt and dnf repositories and the upgrade behaviour of the installed repository file, run in throwaway containers) SHALL run only when the developer asks for them through an environment variable. When not requested, each check SHALL be reported as skipped with how to request it, and the suite SHALL NOT fail. When requested but no container runtime is available, each check SHALL be reported as skipped with that reason. The contributor document SHALL describe the variable, what the checks need, roughly how long they take, and when to run them.

#### Scenario: A normal test run
- **WHEN** a developer runs the test command without requesting the package repository checks
- **THEN** those checks are reported as skipped with the variable that turns them on, start no containers, and the suite passes

#### Scenario: The checks are requested
- **WHEN** a developer runs the test command, or the suite on its own, with the variable set
- **THEN** the apt, dnf and repository-file checks run and report pass or fail as before

#### Scenario: A contributor changes the packaging
- **WHEN** a contributor reads the contributor document before changing how the Linux packages or their repositories are built
- **THEN** it names the suite, the variable that turns it on, what the suite needs, and that it should be run for such changes and before a release
