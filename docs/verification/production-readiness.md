# Production-readiness verification

Date: 2026-09-12

Branch: `feat/production-hardening`

## Scope

This gate closes the repository-level reproducibility and maintenance gaps
after the functional Canvas implementation and separately authorized runtime
acceptance were completed. It does not repeat login or consume credits.

## Added controls

- `requirements-dev.txt` declares the complete third-party test dependency set.
- GitHub Actions runs the offline gate on Python 3.11, 3.12, and 3.13.
- Actions are pinned to immutable upstream commit SHAs.
- CI has read-only repository permissions, bounded runtime, and concurrency
  cancellation.
- `SECURITY.md` defines private vulnerability reporting and the approval,
  recovery, secret-handling, and artifact-integrity boundaries.
- `CONTRIBUTING.md` defines isolated setup, complete verification, upstream
  Skill ownership, and paid-operation restrictions.
- Distribution tests reject missing production files, movable Action tags,
  stale runtime status, and unchecked implementation tasks.

## Fresh isolated-environment evidence

The following commands completed with exit code 0 in a newly created Python
virtual environment populated only from `requirements-dev.txt`:

| Gate | Result |
|---|---|
| Unit tests | 63/63 PASS |
| Skill scenarios | 14/14 PASS |
| Pinned upstream snapshot | 13 Skills, 40 files PASS |
| Distribution validator | PASS |
| System plugin validator | PASS |
| Python compileall | PASS |
| Workflow YAML parse | PASS |
| `git diff --check` | PASS |

Runtime `version` and `schema`, public Marketplace installation, account
authentication, and the separately approved paid canary remain evidenced in
the other files in this directory. They are not CI steps because CI must remain
unauthenticated and non-charging.
