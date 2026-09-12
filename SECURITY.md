# Security Policy

## Supported versions

Security fixes are applied to the latest release on `main`. Older snapshots are
not maintained separately.

## Reporting a vulnerability

Do not open a public issue for a vulnerability, credential exposure, approval
bypass, duplicate paid submission, path traversal, or artifact-integrity flaw.
Use GitHub's private vulnerability reporting for this repository. Include the
affected version, reproduction steps, impact, and any safe test fixture.

Do not include access tokens, cookies, signed URLs, credit-confirmation tokens,
or account identifiers in a report. Redact them before submission.

## Security boundaries

- The plugin invokes `dreamina-canvas` with an argv list and never through a
  shell.
- Authentication remains owned by the CLI; this repository must not persist
  credentials.
- Paid execution requires a fresh quote and explicit, quote-bound approval.
- Ambiguous submissions are reconciled by stable identifiers and are never
  automatically resubmitted.
- Downloaded artifacts are constrained to an approved path and verified by
  byte count and SHA-256.

CI is deliberately offline and non-charging. Authentication and paid canaries
are separate, explicitly authorized acceptance procedures.
