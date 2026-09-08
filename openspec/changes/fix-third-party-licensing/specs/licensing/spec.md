## Purpose

Ensure that what this project actually redistributes — bundled third-party libraries, model weights, and runtime components — is accurately disclosed and that the obligations those licenses impose are met by the shipped artifact, not merely by files in the repository.

## ADDED Requirements

### Requirement: Distributed artifacts carry third-party notices

Every artifact this project distributes SHALL contain, inside the artifact itself, a notices file listing each bundled third-party component with its license and copyright attribution. Notices present only in the source repository SHALL NOT be treated as satisfying this requirement, because the artifact is what reaches the user.

#### Scenario: User inspects an extracted artifact

- **WHEN** a user extracts the distributed archive
- **THEN** a third-party notices file is present in the extracted folder, naming each bundled component, its license, and its copyright holder

#### Scenario: Bundled model weights

- **WHEN** model weights are bundled into an artifact
- **THEN** their license and attribution ship alongside them, in the same directory as the weights

#### Scenario: A new third-party component becomes bundled

- **WHEN** a dependency change causes a new third-party component to be bundled into a distributed artifact
- **THEN** the notices file is updated to include it before that artifact is distributed

### Requirement: Corresponding source for bundled GPL components stays reachable

Where this project distributes binaries of GPL-licensed third-party components, it SHALL publish, alongside the distributed artifact, directions to the corresponding source for the exact versions bundled, and SHALL keep those directions resolvable for as long as the artifact is offered.

#### Scenario: A release contains GPL-licensed binaries

- **WHEN** a release publishes an artifact bundling GPL-licensed third-party binaries
- **THEN** directions to the corresponding source for those components accompany the artifact, identifying each component's exact version and where to obtain its source

#### Scenario: The binaries were built by an upstream packager

- **WHEN** the bundled GPL binaries come from a third-party packaged distribution rather than a local build
- **THEN** the packaging version, the resulting library versions, and the build configuration are recorded, so the corresponding source is identifiable without inspecting the binaries

#### Scenario: An upstream source location stops resolving

- **WHEN** a published source location becomes unavailable while the artifact is still offered
- **THEN** the directions are updated, or the source is rehosted, so that the corresponding source remains obtainable

#### Scenario: A later release changes the bundled versions

- **WHEN** a dependency update changes the version of a bundled GPL component
- **THEN** the directions published with the new release identify the new versions, rather than carrying forward an earlier release's

### Requirement: License statements describe what is actually distributed

The project's `LICENSE` and `README` SHALL describe the licensing of what the project actually ships. They SHALL NOT describe a bundled component as an external prerequisite the user must install, and they SHALL state the effective license of the distributed binary where it differs from the license of the source.

#### Scenario: A dependency moves from external to bundled

- **WHEN** a component that users previously installed themselves becomes bundled into the distributed artifact
- **THEN** `LICENSE` is updated to describe it as bundled, and any statement that it must be installed separately is removed

#### Scenario: Bundled components constrain the effective license

- **WHEN** bundled components are licensed under terms stricter than the project's own source license
- **THEN** the effective license of the distributed binary is stated explicitly, rather than left to be inferred from the source license alone
