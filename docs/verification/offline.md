# Offline distribution gate evidence

Upstream SHA: `f1f894d0374c8f3ff2e54e2aa896bcd2ad0e15d7`
Upstream branch: `feat/canvas-skills`
Plugin branch: `feat/canvas-plugin-pin`
Local plugin HEAD: `6638fe3b4afe7411a5a2747cbf9a7ed943da106c`
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
  Per plan Task 15 Step 3 / upstream plan §21, `auth account` is run only when
  authentication/account access is separately authorized. The user did not
  supply credentials or a `auth wait --device-code <code>` value within this
  session. Recording `NOT_RUN` here is the documented compliance behaviour,
  not a gap.
- `paid_canary`: NOT_RUN — Paid generation requires separate action-time
  approval. Per plan Task 15 Step 4, a canary proceeds only after the user
  supplies a `--credit-ceiling` and explicit approval. No canary was
  performed; no `submitId` was minted against a paid batch.

To flip these gates to PASS in a future session, the user must supply:

1. Either a fresh `dreamina-canvas auth login` device-code (so the agent
   can resume `auth wait --device-code <code> --timeout 10m`), OR
   credentials that the agent can pass to `auth login` itself.
2. An explicit `--credit-ceiling <integer>` value and a one-line media
   prompt for the canary draft.

## Publication status

| Ref | SHA | State |
|-----|-----|--------|
| Upstream published SHA (target) | `f1f894d0374c8f3ff2e54e2aa896bcd2ad0e15d7` | pushed to `origin/feat/canvas-skills` |
| Local upstream HEAD | `f1f894d0374c8f3ff2e54e2aa896bcd2ad0e15d7` | tracks `origin/feat/canvas-skills` |
| Local plugin HEAD | `ec656374817c0b8fec9b9a2f95597da903e8e9c3` | local on `feat/canvas-plugin-pin` |
| Local plugin tracking | `ec656374817c0b8fec9b9a2f95597da903e8e9c3` | tracks `origin/feat/canvas-plugin-pin` |
| Remote `origin/feat/canvas-plugin-pin` | `ec656374817c0b8fec9b9a2f95597da903e8e9c3` | pushed |
| Remote `origin/main` (pre-session) | `8545fbddafcdf6b4bf8de5b7ea1411483cda0efe` | unchanged — branch-level push only |

Both branches were pushed under explicit user authorization in this
session. The plugin `main` branch on origin remains at the pre-session
SHA `8545fbddafcdf6b4bf8de5b7ea1411483cda0efe` because the user chose
branch-level push (not `main`).

The plugin's packaged Skill inventory is byte-identical to upstream
`f1f894d0374c8f3ff2e54e2aa896bcd2ad0e15d7`, asserted by
`scripts/verify_dreamina_canvas_skills.py` against
`upstream/dreamina-skills.lock.json`.

