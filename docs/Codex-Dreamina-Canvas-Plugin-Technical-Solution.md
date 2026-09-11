# Codex Dreamina Canvas Plugin Technical Solution

## Decision

Wrap the installed CLI through a strict argv adapter. Parse only JSON mode, normalize exit codes and `requiredAction`, and persist a minimal operation ledger under plugin data.

## Planned layout

```text
.codex-plugin/plugin.json
skills/codex-dreamina-canvas-*/
scripts/canvas_adapter.py
scripts/approval_guard.py
schemas/
tests/
```

## Contracts

`CapabilitySnapshot` records CLI version/schema hash and live catalogs. `QuoteReceipt` binds request fingerprint, amount, unit, and expiry. `OperationReceipt` records submit/operation IDs and state without credentials. `ArtifactReceipt` records approved path and checksum.

## Error model

Normalize `CLI_NOT_FOUND`, `AUTH_REQUIRED`, `UPGRADE_REQUIRED`, `INVALID_REFERENCE`, `QUOTE_REQUIRED`, `APPROVAL_REQUIRED`, `APPROVAL_STALE`, `SUBMISSION_UNKNOWN`, `REMOTE_FAILED`, and `DOWNLOAD_FAILED`. Preserve the original numeric exit code as evidence without exposing raw secrets.

## Test strategy

Use captured synthetic JSON fixtures for every state and exit code. Fake the subprocess boundary, never the parser or approval guard. Runtime smoke tests are help/schema/account read-only; paid generation is a separate explicitly approved acceptance gate.
