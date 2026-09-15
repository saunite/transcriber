## ADDED Requirements

### Requirement: GUI tests run under the application's content security policy
The GUI tests SHALL load the application's frontend under the same content security policy the application window enforces, derived from the application's configuration and its bundled pages in the way the application framework derives it. Every GUI behaviour scenario SHALL fail if the page reports any content-security-policy violation. The tests SHALL also prove that the policy refuses script that isn't part of the application, by checking that injected script had no effect.

#### Scenario: Normal use violates nothing
- **WHEN** the GUI behaviour scenarios run under the application's policy
- **THEN** they pass, and the page reports no content-security-policy violation

#### Scenario: A frontend change breaks under the policy
- **WHEN** the frontend gains code the policy blocks, such as an inline event handler or an unhashed inline script
- **THEN** the GUI tests fail and report the violation

#### Scenario: Injected script is refused
- **WHEN** a test injects an inline event handler and string-evaluated code into the running page
- **THEN** neither changes the page's state, and each is reported as a violation

#### Scenario: The policy is not actually applied
- **WHEN** the page is served without the application's policy
- **THEN** the injected-script scenario fails, because the injected script takes effect
