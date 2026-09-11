# Codex Dreamina Canvas Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build safe Dreamina Canvas CLI orchestration for Codex.

**Architecture:** A strict subprocess adapter and approval guard expose normalized receipts to Canvas Skills. Remote generation remains owned by the CLI.

**Tech Stack:** Codex plugin, Agent Skills, Python, JSON Schema, unittest/pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-codex-dreamina-canvas-plugin-design.md`

## Constraints

- ID `codex-dreamina-canvas`; installed CLI only; JSON mode only.
- Runtime catalogs are authoritative.
- Paid submission requires quote-bound approval and at-most-once execution.
- Unknown submission state is reconciled, never resubmitted automatically.

### Task 1: Manifest and receipt schemas
- [ ] Write failing identity and closed-schema tests.
- [ ] Add plugin manifest and capability/quote/approval/operation/artifact schemas.
- [ ] Validate and commit `feat: define Dreamina Canvas contracts`.

### Task 2: CLI capability adapter
- [ ] Write failing fixtures for version, schema, auth/account, model and voice discovery.
- [ ] Implement argv-only JSON execution and stable error mapping.
- [ ] Run tests and commit `feat: adapt Dreamina Canvas CLI`.

### Task 3: Quote and approval guard
- [ ] Write failing tests for missing, stale, changed, replayed, and expired approvals.
- [ ] Implement quote/request fingerprints and single-consumption approval tokens stored without secrets.
- [ ] Run tests and commit `feat: guard Dreamina Canvas credit use`.

### Task 4: Operation ledger and recovery
- [ ] Write failing tests for submitted/querying/completed/failed/unknown states and restart recovery.
- [ ] Implement atomic ledger writes and bounded polling.
- [ ] Prove timeout does not resubmit; commit `feat: recover Dreamina Canvas operations`.

### Task 5: Canvas Skills
- [ ] Baseline no-skill scenarios for hard-coded models, unsafe approval, and blind retry.
- [ ] Create and individually validate use/auth/discover/canvas/node/timeline/quote/run/recover/download Skills.
- [ ] Run TRACE and forward scenarios; commit `feat: add Dreamina Canvas skills`.

### Task 6: Distribution and acceptance
- [ ] Add failing marketplace, identity, link, secret, and Skill-inventory tests.
- [ ] Implement validator and repository marketplace.
- [ ] Run offline tests and read-only CLI smoke tests; record paid runtime acceptance separately.
- [ ] Commit `test: verify Dreamina Canvas distribution`.

---

## Detailed executor contract

### Task 1 — package and domain schemas

**Files:** `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `schemas/capability_snapshot.schema.json`, `schemas/canvas_request.schema.json`, `schemas/quote_receipt.schema.json`, `schemas/approval_receipt.schema.json`, `schemas/operation_receipt.schema.json`, `schemas/artifact_receipt.schema.json`, `tests/test_contracts.py`.

- [ ] RED-test plugin ID `codex-dreamina-canvas`, display name, version `0.1.0`, closed objects, stable identifier types, and forbidden credential fields.
- [ ] Require every receipt to carry `schemaVersion`, `producer`, `createdAt`, and a non-secret correlation ID.
- [ ] Define quote/approval request fingerprints as lowercase SHA-256 over canonical JSON.
- [ ] Implement minimum schemas and run contract/plugin validation; commit.

### Task 2 — CLI discovery and normalized execution

**Files:** `scripts/canvas_adapter.py`, `tests/fixtures/cli/*.json`, `tests/test_canvas_adapter.py`.

```python
@dataclass(frozen=True)
class CliResult:
    exit_code: int
    payload: dict | list | None
    required_action: str | None
    error_code: str | None

def run_canvas_cli(args: list[str], timeout_seconds: int) -> CliResult: ...
def discover_capabilities() -> dict: ...
```

- [ ] Capture only authorized read-only `--help`, `version`, `schema`, auth status/account, model search and voice list fixtures; do not generate content.
- [ ] RED-test missing executable, invalid JSON, stdout/stderr separation, exit codes 0/10/13, authentication, permission, upgrade, timeout and malformed payloads.
- [ ] Implement argv-only execution, output-size limits, redaction and stable error mapping.
- [ ] Build `CapabilitySnapshot` from actual version/schema/catalog responses and hash the source contract.
- [ ] Run adapter/contract tests and commit.

### Task 3 — canvas and node planning

**Files:** `scripts/canvas_planner.py`, `tests/test_canvas_planner.py`.

```python
def normalize_canvas_plan(intent: dict, capabilities: dict) -> dict: ...
def validate_references(plan: dict, capabilities: dict) -> list[str]: ...
```

- [ ] RED-test create/select canvas, image/video/audio/text/element/timeline nodes, node find/show, image upscale, local/remote references, and full-replacement generation semantics.
- [ ] Reject model, voice, ratio or resolution values absent from the current snapshot.
- [ ] Treat node metadata update as sparse and generation configuration as complete replacement.
- [ ] Prove `save` plans contain no approval and cannot invoke `run`; commit.

### Task 4 — quotation and approval

**Files:** `scripts/approval_guard.py`, `tests/test_approval_guard.py`.

```python
def fingerprint_request(request: dict) -> str: ...
def create_approval(quote: dict, user_decision: dict, now: datetime) -> dict: ...
def consume_approval(approval: dict, request: dict, now: datetime) -> None: ...
```

- [ ] RED-test no quote, rejected quote, amount/unit mismatch, modified prompt/reference/model, expiry, replay, and approval for a different canvas/node.
- [ ] Implement single-use approvals stored atomically in plugin data without account or token values.
- [ ] Map CLI confirmation-required exit 10 to an action-time user prompt; never append approval flags automatically.
- [ ] Run focused tests and commit.

### Task 5 — at-most-once submission and recovery

**Files:** `scripts/operation_ledger.py`, `scripts/canvas_service.py`, `tests/test_operation_ledger.py`, `tests/test_canvas_service.py`.

- [ ] RED-test Draft/Saved/Quoted/Approved/Submitted/Querying/Completed/Failed/Unknown transitions, duplicate call attempts, process crash, corrupted ledger, and batch per-item states.
- [ ] Atomically persist request fingerprint and operation/submit ID before returning submission success.
- [ ] On timeout or connection loss, enter `Unknown`; query operation/history/local records and never call run again automatically.
- [ ] Use bounded polling with explicit maximum elapsed time and no blocking sleep longer than 60 seconds.
- [ ] Validate downloaded artifact path/hash/media and preserve failed items in batch receipts; commit.

### Task 6 — Canvas Skill suite

**Files:** create `skills/codex-dreamina-canvas-use`, `-auth`, `-discover`, `-canvas`, `-node`, `-timeline`, `-quote`, `-run`, `-recover`, `-download`; create `tests/scenarios/`.

- [ ] Run no-skill baselines for hard-coded model values, mixed save/run, implicit credit approval, exit-10 auto-retry, unknown-state resubmission and batch summary loss.
- [ ] Implement the router first only after its RED routing test; then implement each capability Skill separately.
- [ ] After each Skill: quick validate, strict TRACE, run its retrieval/application scenario, and commit or include in a reviewable task commit.
- [ ] Prove non-interactive agents stop at quotation without explicit approval.
- [ ] Prove every completion response includes canvas/node IDs, operation status, artifact evidence and unverified boundaries.

### Task 7 — distribution and live-read gates

**Files:** `scripts/validate_distribution.py`, `tests/test_distribution.py`, `docs/verification/offline.md`, `docs/verification/canvas-cli-runtime.md`.

- [ ] RED-test repository URL, identity, ten-Skill inventory, references, executable bits, marketplace policy, symlinks and secret patterns.
- [ ] Run all offline tests, quick validation/TRACE, links, plugin validator and `git diff --check`.
- [ ] Install through the public repository marketplace and confirm a fresh Codex task discovers the ten Skills.
- [ ] With user-authorized CLI authentication, run only version/schema/catalog/account read checks and record exact CLI version/commit/environment.
- [ ] Treat any credit-consuming canary as a separate approval; ordinary acceptance stays green without it but records paid-runtime status as unverified.
- [ ] Commit evidence and stop for integration choice.

## Completion gate

```text
schema_tests = PASS
adapter_fixtures = PASS
planner_tests = PASS
approval_guard_tests = PASS
at_most_once_and_recovery_tests = PASS
skill_quick_validation = 10/10
skill_trace = 10/10
plugin_validation = PASS
secret_matches = 0
read_only_cli_contract = observed or explicitly blocked
paid_generation_canary = separately approved or NOT_RUN
```
