# Offline distribution gate evidence

Upstream SHA: `300bfc1d649a68c1802a43aa7a64c50000e095d4`
Upstream branch: `feat/canvas-skills`
Plugin branch: `feat/canvas-plugin-pin`
Local plugin HEAD: `6638fe3b4afe7411a5a2747cbf9a7ed943da106c`
Remote `origin/main` (last known pre-session): `8545fbddafcdf6b4bf8de5b7ea1411483cda0efe`

## Commands and exit codes

| Command | Exit | Notes |
|---------|------|-------|
| `python3 -m unittest discover -s tests` | 0 | 55 tests, 0 failures, 0 errors |
| `python3 scripts/verify_dreamina_canvas_skills.py` | 0 | 13 skills, 40 files match the pinned upstream commit |
| `python3 scripts/validate_distribution.py` | 0 | compatibility foundation 0.1.0 |
| `python3 /Users/wandl/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .` | 0 | Plugin validation passed |
| `git diff --check` | 0 | No whitespace conflicts |

## Runtime boundary

- `cli_runtime`: PASS — dreamina-canvas installed at `/Users/wandl/.local/bin/dreamina-canvas`,
  `dreamina-canvas version` returns `1.0.0` / commit `ae2c968` / edition `public`
  / distribution `cn` / build `2026-09-05T08:54:32Z`.
- `auth`: **PASS** — Device-authorization login completed after the user
  supplied an authorization decision and finished the browser step. `auth
  status` reported `loggedIn: true`; `auth account` (the authoritative
  server check) returned `ok: true` with `isVip: true`, `vipLevel: standard`.
  The user identifier is redacted from committed evidence.
- `paid_canary`: **PASS** — One low-cost `t2i` draft was created, quoted
  (`totalMaxCredits: 5`), approved with an explicit `--credit-ceiling 100`,
  run exactly once with a caller-minted persisted `submitId`, waited to a
  terminal `succeeded` state, downloaded via `resource download`, and
  verified: `wc -c` and `shasum -a 256` both matched the CLI's reported
  `size`/`sha256`, and the plugin's own `artifact_guard.verify()` returned
  `ok: true`.

Verified canary facts (non-secret):

```text
resourceId : b062d52f-fa20-4093-ae8b-d011ba853d82
size       : 705847 bytes
sha256     : 042406680ed8d763bc7e661a3588a42b01e7d9c096d14d01f8b0881a9ff7fd96
media      : 1536 × 1536, jpeg
credits    : 5 consumed against a 100-credit approved ceiling
```

The approval token was held in process memory only, was never written to
the repository, and was destroyed immediately after `node run`. No second
`submitId` was ever minted.

Full detail, including the observed schema drift between the guide and
the installed `1.0.0` artifact, is recorded in
[dreamina-canvas-runtime.md](dreamina-canvas-runtime.md).

## Publication status

Both branches are pushed to their respective origins and each is
three-end SHA identical (`local == tracking == remote`) on its branch:

| Repository | Branch | State |
|------------|--------|-------|
| `full-aigc-skills/dreamina-skills` | `feat/canvas-skills` | pushed; `local == tracking == remote` |
| `partme-ai/codex-dreamina-canvas-plugin` | `feat/canvas-plugin-pin` | pushed; `local == tracking == remote` |

Exact SHAs are recorded in [codex-installation.md](codex-installation.md)
and can be re-derived at any time with `git rev-parse HEAD`,
`git rev-parse '@{u}'`, and `git ls-remote origin <branch>`.

`origin/main` on both repositories is intentionally **not** moved: the
user authorised branch-level push only. Merging to `main` remains a
separate decision.

Both branches were pushed under explicit user authorization in this
session. The plugin `main` branch on origin remains at the pre-session
SHA `8545fbddafcdf6b4bf8de5b7ea1411483cda0efe` because the user chose
branch-level push (not `main`).

The plugin's packaged Skill inventory is byte-identical to upstream
the pinned upstream commit, asserted by
`scripts/verify_dreamina_canvas_skills.py` against
`upstream/dreamina-skills.lock.json`.

## TRACE evaluation

Each of the thirteen Canvas Skills was evaluated **separately** with the
TRACE evaluator (static base score + evidence packet). No aggregate score
is used as evidence for an individual Skill.

- 13/13 Skills at or above the 3.0 threshold.
- Per-Skill means: min 3.84, max 4.03, mean 3.88.
- Per-Skill table: [skill-trace.md](skill-trace.md).

## Completion gate

```text
upstream_canvas_skill_count          = 13        PASS
packaged_canvas_skill_count          = 13        PASS
upstream_snapshot_parity             = PASS      (40 files)
only_use_allows_implicit_invocation  = PASS
plugin_manifest_validation           = PASS
contract_and_adapter_tests           = PASS      (19 tests)
approval_recovery_artifact_tests     = PASS      (21 tests)
atomic_skill_scenarios               = 7/7 PASS
domain_skill_scenarios               = 4/4 PASS
orchestration_skill_scenarios        = 2/2 PASS
skill_trace                          = 13/13 PASS
distribution_and_secret_scan         = PASS
read_only_cli_runtime                = PASS
paid_canary                          = PASS      (5 credits vs 100 ceiling)
local_tracking_remote_sha            = identical PASS
```
