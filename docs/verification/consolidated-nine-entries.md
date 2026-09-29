# Consolidated nine-entry Skill layout — plugin 0.4.0

Date: 2026-09-29
Upstream: `full-aigc-skills/dreamina-skills` @ `4e776ace9819b402dc1774034f8928f62095fdd9`
Upstream change: `consolidate-canvas-cli-atoms` (archived)

## Scope

The upstream package retired twelve installable atom Skills and folded their
operation documentation into the nine `dreamina-canvas-cli*` entries. This
plugin re-vendors the new layout, re-points the command surface, and records
the resulting evidence below.

## Packaged Skill set (10 vendored + 1 local)

| Skill | Role |
|---|---|
| `dreamina-canvas-cli` | shared operations: discovery, canvas, resources, node mechanics, composition, timeline, execution, recovery |
| `dreamina-canvas-cli-setup` | install, upgrade, environment readiness |
| `dreamina-canvas-cli-auth` | login, device-code wait, account check, refresh, logout |
| `dreamina-canvas-cli-text2image` | t2i |
| `dreamina-canvas-cli-image2image` | i2i and separately priced upscale |
| `dreamina-canvas-cli-text2video` | t2v |
| `dreamina-canvas-cli-ref2video` | m2v and first_last_frame |
| `dreamina-canvas-cli-text2voice` | tts |
| `dreamina-canvas-cli-text2audio` | music |
| `dreamina-canvas-use` | the single implicit orchestrator |
| `dreamina-canvas-harness` | plugin-local harness (not vendored) |

`dreamina-canvas-use` remains the only Skill with
`allow_implicit_invocation: true`.

## Byte parity

- `upstream/dreamina-skills.lock.json` — commit `4e776ace9819`, 10 Skills,
  178 files.
- `skills.lock.json` — source ref `v1.7.0`, sha `4e776ace9819`, 10 Skills with
  per-Skill directory digests.
- `python3 scripts/verify_dreamina_canvas_skills.py` → `OK: 10 skills, 178
  files match upstream commit 4e776ace9819`.

## Command surface (15 commands, two host mirrors)

- Generation: `/dreamina-canvas-image`, `-image2image`, `-video`,
  `-ref2video`, `-audio`, `-music`.
- Session: `/dreamina-canvas-setup`, `-auth`.
- Public operations (all resolve to `dreamina-canvas-cli` and name the
  operation reference to read): `-create`, `-compose`, `-assets`, `-run`,
  `-resume`, `-timeline`.
- Entry: `/dreamina-canvas` → `dreamina-canvas-use`.
- `hooks/check_canvas_intent.py` and its two host copies enumerate the new set.

## Test and gate evidence

| Gate | Result |
|---|---|
| `python3 -m unittest discover -s tests` | 317 tests, OK |
| `python3 -m unittest discover -s tests/scenarios` | 17 tests, OK |
| `python3 scripts/validate_distribution.py` | identity parity confirmed for `0.4.0+codex.20260929` |
| `python3 scripts/verify_dreamina_canvas_skills.py` | byte parity OK |

Scenario coverage was repointed to the new owners: per-mode semantics are
asserted on the task Skills, shared node/operation semantics on the public
CLI Skill's references, and the download-receipt harness now keys on the
response envelope (a resource id or server digest) rather than a Skill name,
because the owning Skills were merged.

## Upstream quality evidence (inherited, not re-run here)

`verification/dreamina-canvas-atomic-verification.json` in the upstream
records TRACE average 4.651 across 33 Skills (threshold 4.50; the nine Canvas
entries score 4.55–4.72) and a read-only CLI 1.0.1 probe covering 36 leaf
commands. That record is evidence for the upstream package, not for this
plugin's runtime.

## Boundaries

- No account authentication, upload, remote draft, or paid generation was
  executed for this layout; `auth` and `paid_canary` remain `NOT_RUN`.
- The visual single-round loop and library wiring are carried forward
  unchanged from 0.3.0; their paid canary and 8/8 cross-host golden samples
  (2026-09-22) are recorded in their own dated records.
- Consumer distributions that pin the retired atom Skill paths must be
  updated per the upstream `docs/canvas-atomic-migration.md` before adopting
  this release.
