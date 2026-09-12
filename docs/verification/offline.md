# Offline distribution gate evidence

Upstream SHA: `f1f894d0374c4ca99d11a40fb09eb4b8aaa89d3c`
Upstream branch: `feat/canvas-skills`
Plugin branch: `feat/canvas-plugin-pin`
Local plugin HEAD: `6ea56fe88ca45e19af5d5e6bb4318111205ec89d` (final after this session's evidence commit; immediate prior commit `b0b54e7a45f56cdd86848ca3dd2e2ed9d654bc1b` contained the runtime + contract + adapter + router changes)
Remote `origin/main` (last known pre-session): `8545fbddafcdf6b4bf8de5b7ea1411483cda0efe`

## Commands and exit codes

| Command | Exit | Notes |
|---------|------|-------|
| `python3 -m unittest discover -s tests` | 0 | 55 tests, 0 failures, 0 errors |
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

## Publication status

| Ref | SHA | State |
|-----|-----|--------|
| Upstream published SHA (target) | `f1f894d0374c4ca99d11a40fb09eb4b8aaa89d3c` | local on `feat/canvas-skills` |
| Local plugin HEAD | `b0b54e7a45f56cdd86848ca3dd2e2ed9d654bc1b` | local on `feat/canvas-plugin-pin` |
| Remote `origin/main` (pre-session) | `8545fbddafcdf6b4bf8de5b7ea1411483cda0efe` | unchanged — no push performed this session |

Push to remote origin was **not** performed this session because it is a
destructive operation that requires explicit user authorization. To
finish the publication step:

1. Confirm push authorization for both repositories.
2. `git push origin feat/canvas-skills` from the upstream worktree.
3. After upstream is visible on the remote, optionally merge into `main`
   and `git push origin main` there.
4. `git push origin feat/canvas-plugin-pin` from the downstream worktree,
   then optionally merge into `main` and `git push origin main`.
5. Re-record the three SHAs (`local`, `tracking`, `remote main`) and
   confirm they all match the published SHA `f1f894d` for upstream and
   `b0b54e7` for downstream.

