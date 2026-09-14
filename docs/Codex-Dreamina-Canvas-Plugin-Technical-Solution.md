# Codex Dreamina Canvas Plugin Technical Solution

> **Document control**
>
> | Field | Value |
> |---|---|
> | Status | Implemented and released as `0.1.2` |
> | Scope | How this repository integrates the Dreamina Canvas CLI, and how that integration is verified |
> | Audience | Implementers extending or reviewing this plugin |
> | Runtime evidence | `docs/verification/` |

## 1. Decision

Wrap the installed CLI through a strict argv adapter. Parse only JSON mode, normalize exit codes and `requiredAction`, and persist a minimal operation ledger under plugin data.

### Alternatives considered

| Alternative | Why it was rejected |
|---|---|
| Call the remote service directly | Would duplicate authentication, entitlement, and pricing logic that the CLI already owns |
| Shell out through a command string | Invites injection and makes arguments unauditable |
| Cache catalog values in source | Values change without notice, so a cache would silently mislead users |
| Treat "save" and "run" as one command | Makes accidental spend impossible to review |
| Retry a paid run automatically after a timeout | Turns one paid action into two, with no way to prove which succeeded |

## 2. Repository layout

```text
.codex-plugin/plugin.json
plugin.json
skills/codex-dreamina-canvas-*/
scripts/dreamina_canvas_adapter.py
scripts/approval_guard.py
scripts/artifact_guard.py
scripts/error_router.py
scripts/operation_ledger.py
tests/
upstream/dreamina-skills.lock.json
```

| Path | Responsibility |
|---|---|
| `scripts/dreamina_canvas_adapter.py` | argv-only CLI invocation, JSON parsing, typed adapter errors |
| `scripts/approval_guard.py` | Quote binding, credit ceiling enforcement, replay rejection |
| `scripts/operation_ledger.py` | Non-secret operation receipts keyed by `submitId` |
| `scripts/artifact_guard.py` | Byte count and SHA-256 verification of downloads |
| `scripts/error_router.py` | Exit-code to next-action mapping |
| `tests/` | Unit tests plus `tests/scenarios/` integration-style tests |

## 3. Contracts

`CapabilitySnapshot` records CLI version/schema hash and live catalogs. `QuoteReceipt` binds request fingerprint, amount, unit, and expiry. `OperationReceipt` records submit/operation IDs and state without credentials. `ArtifactReceipt` records approved path and checksum.

| Contract | Required fields | Invariant |
|---|---|---|
| `CapabilitySnapshot` | CLI version, schema hash, live catalogs | Never persisted as authoritative; re-read every run |
| `QuoteReceipt` | Request fingerprint, amount, unit, expiry | An approval is valid only for the fingerprint it was created against |
| `OperationReceipt` | `submitId`, request fingerprint, last known state | Contains no credential-like field |
| `ArtifactReceipt` | Approved destination, byte count, SHA-256 | A mismatch is a hard failure, not a warning |

## 4. Configuration and state

| Setting | Location | Notes |
|---|---|---|
| CLI binary | `dreamina-canvas` on `PATH` | Overridable through the adapter for controlled deployments |
| Operation ledger | `<root>/operations/<profile-and-environment>/<submitId>.json` | Mode `0600`; non-secret fields only |
| Authentication | The CLI's own store | Never read or written here |
| Credit ceiling | Supplied with each approval | A ceiling below the latest authoritative total is refused |

## 5. Error model

Normalize the CLI's exit codes into typed actions so no caller parses a human message.

| Exit code | Routed action | Meaning |
|---|---|---|
| `0` | `continue` | Success |
| `1` | `alert` | Uncategorized internal failure |
| `2` | `fix_and_retry` | Invalid command, argument, or schema |
| `10` | `approval_pause` | Structured credit approval required |
| `11` | `reauth_and_retry` | Login required or session expired |
| `12` | `escalate` | Permission, capability, or entitlement denied |
| `13` | `upgrade_cli` | Environment or release compatibility blocked |
| `20` | `resume_operation` | Operation recoverable, not yet converged |
| `21` | `bounded_backoff_retry` | Retryable service or transport failure |
| `22` | `hand_to_human` | Human intervention required |

Adapter-level values of `requiredAction` are `none`, `login`, `confirm`, `retry`, `resume`, `upgrade`, `human_intervention`, and `contact_support`. The original numeric exit code is preserved as evidence; raw secrets are never surfaced.

## 6. State machine mapping

| State | Written by | Trigger |
|---|---|---|
| Draft | Ledger | A canvas is composed but not submitted |
| Saved | Ledger | A free save succeeds |
| Quoted | Approval guard | A quote is obtained for an exact node set |
| Approved | Approval guard | The user approves that quote |
| Submitted | Ledger | A single run starts and the `submitId` is persisted |
| Querying | Ledger | Polling observes a non-terminal state |
| Completed | Ledger | A terminal success |
| Failed | Ledger | A terminal failure |
| Unknown | Ledger | A timeout or an ambiguous transport outcome |

`Unknown` never transitions to `Submitted` automatically. Recovery always queries the existing `submitId`.

## 7. Test strategy

Use captured synthetic JSON fixtures for every state and exit code. Fake the subprocess boundary, never the parser or approval guard. Runtime smoke tests are help/schema/account read-only; paid generation is a separate explicitly approved acceptance gate.

| Layer | What it proves | Command |
|---|---|---|
| Unit | Parser, guards, ledger, and router behavior | `python -m unittest discover -s tests -v` |
| Scenario | Multi-step flows and state transitions | `python -m unittest discover -s tests/scenarios -v` |
| Skill parity | Packaged Skills match the upstream lock file | `python scripts/verify_dreamina_canvas_skills.py` |
| Distribution | Manifests, references, and required files | `python scripts/validate_distribution.py` |
| Runtime | CLI version, command compatibility, authorized authentication | `docs/verification/dreamina-canvas-runtime.md` |

## 8. Compatibility and rollout

| Aspect | Position |
|---|---|
| Python | 3.11, 3.12, and 3.13 in the CI matrix |
| Upstream Skills | Pinned by commit and byte-verified against `upstream/dreamina-skills.lock.json` |
| Upgrade path | Exit code `13` routes to an explicit CLI upgrade action rather than failing silently |
| Rollback | Restore the previous pinned commit and reinstall; operation receipts remain readable because the format is additive |

## 9. Evidence map

| Claim | Evidence |
|---|---|
| Adapter boundary | `scripts/dreamina_canvas_adapter.py` |
| Approval binding | `scripts/approval_guard.py` and its tests |
| Ledger fields | `scripts/operation_ledger.py` and its tests |
| Download verification | `scripts/artifact_guard.py` and its tests |
| Real-environment acceptance | `docs/verification/real-environment-acceptance-2026-09-13.md` |
