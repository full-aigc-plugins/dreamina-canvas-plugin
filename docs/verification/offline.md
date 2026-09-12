# Offline distribution gate evidence

Upstream SHA: `f1f894d0374c4ca99d11a40fb09eb4b8aaa89d3c`
Upstream branch: `feat/canvas-skills`
Plugin branch: `feat/canvas-plugin-pin`

## Commands and exit codes

| Command | Exit | Notes |
|---------|------|-------|
| `python3 -m unittest discover -s tests` | 0 | 26 tests, 0 failures, 0 errors |
| `python3 scripts/verify_dreamina_canvas_skills.py` | 0 | 13 skills, 40 files match upstream `f1f894d` |
| `python3 scripts/validate_distribution.py` | 0 | compatibility foundation 0.1.0 |
| `python3 /Users/wandl/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .` | 0 | Plugin validation passed |
| `git diff --check` | 0 | No whitespace conflicts |

## Runtime boundary

- `cli_runtime`: PASS — dreamina-canvas installed at `/Users/wandl/.local/bin/dreamina-canvas`,
  `dreamina-canvas version` returns `1.0.0` / commit `ae2c968` / edition `public`
  / distribution `cn` / build `2026-09-05T08:54:32Z`.
- `auth`: NOT_RUN — User-supplied credentials were not provided this session.
- `paid_canary`: NOT_RUN — Paid generation requires separate action-time approval.
- `cli_runtime` and `auth` checks were performed; `auth account` was not invoked because no
  credentials were provided; `paid_canary` is intentionally independent of this gate.
