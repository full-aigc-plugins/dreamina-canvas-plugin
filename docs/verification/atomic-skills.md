# Atomic Canvas Skills validation report

Upstream SHA: `7a9b0fffc6e85b6e75a98e3abb793f8abc20e1a5`
Downstream validator: `scripts/verify_dreamina_canvas_skills.py`
Downstream sync: `scripts/sync_dreamina_canvas_skills.py`

## Per-Skill validation results

| Skill | byte-parity | scenario | notes |
|-------|-------------|----------|-------|
| `dreamina-canvas-cli` | PASS (3 files) | 1 (CLI invariants) | foundation |
| `dreamina-canvas-auth` | PASS (3 files) | 1 (local vs server) | auth-status local-only |
| `dreamina-canvas-discover-models` | PASS (3 files) | 1 (no hard-coded catalog) | runtime catalog only |
| `dreamina-canvas-create` | PASS (3 files) | 1 (concurrent projectId reuse) | explicit --project-id |
| `dreamina-canvas-quote-and-run` | PASS (3 files) | 1 (exit-10 approval pause) | quote-bound approval |
| `dreamina-canvas-resume-operation` | PASS (3 files) | 1 (exit-20 → resume, never node run) | submitId reuse |
| `dreamina-canvas-download-assets` | PASS (3 files) | 1 (verified SHA-256) | no signed URL persist |

## Aggregate

- 7/7 atomic Skill scenarios PASS
- 7/7 byte-parity PASS (vs upstream SHA `7a9b0ff`)
- 39/39 upstream suite tests PASS at upstream
- Downstream `tests/scenarios/test_atomic_skills.py`: 7/7 PASS
