## ADDED Requirements

### Requirement: Validate approval against durable and current requests
The controller SHALL validate a nonempty credential, approval ceiling and request fingerprint against the persisted quote and a fresh quote of the same project, node and generation draft before the first submission.

#### Scenario: Stale or insufficient approval
- **WHEN** approval is missing, insufficient, mismatched, or the live draft/quote changed
- **THEN** no submission is issued and a new approval is requested

### Requirement: Fail closed on damaged state
The controller and CLI SHALL initialize only a genuinely new session and SHALL preserve malformed, foreign, missing-existing and dangling-reference state without side effects.

#### Scenario: Corrupt session
- **WHEN** an existing session cannot be read
- **THEN** execution fails without overwriting its state or creating a draft

### Requirement: Reconcile attempted submissions without resending
The controller SHALL durably mark the submission attempt before invoking the execution port and SHALL only query that submitId on every subsequent recovery, including after transport exceptions or process interruption. Concurrent steps SHALL serialize.

#### Scenario: Ambiguous response
- **WHEN** a submit attempt throws or its response is lost
- **THEN** restart queries the original identity and does not submit again

### Requirement: Persist conservative round accounting
The controller SHALL atomically persist ledger totals, reservation, approval binding and policy alongside state and SHALL restore them on restart. Unknown results SHALL retain reserved credits. Verified terminal outcomes SHALL settle exactly once, including draining.

#### Scenario: Restart while reserved
- **WHEN** the process restarts awaiting approval or remote completion
- **THEN** the same reservation and budget bounds are restored

### Requirement: Compose uploads and document actual capabilities
ResourceUploader SHALL consume actual CommandResult envelopes for success, conflicts and recovery without duplicate upload identities. Harness documentation SHALL list distributed skills and distinguish historical live evidence from current local regression results and unfinished automation.

#### Scenario: Adapter envelope
- **WHEN** resource upload succeeds or needs reconciliation through CommandResult
- **THEN** the uploader completes or returns a diagnosable unresolved result without attribute errors
