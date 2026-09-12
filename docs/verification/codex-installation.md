# Codex installation discovery evidence

The plugin is consumable via the marketplace entry at
`.agents/plugins/marketplace.json` and the compatibility manifest at
`.codex-plugin/plugin.json`. This file records the local installation
evidence captured for this branch; a fresh Codex task would consume the
same artifacts via the plugin-creator cachebuster flow.

## Manifest identity

- Plugin ID: `codex-dreamina-canvas`
- Display name: `Dreamina Canvas`
- Repository: `https://github.com/partme-ai/codex-dreamina-canvas-plugin`
- Marketplace entry: `codex-dreamina-canvas`, source URL
  `https://github.com/partme-ai/codex-dreamina-canvas-plugin.git`,
  ref `main`, policy `installation=AVAILABLE`, `authentication=ON_USE`,
  category `Creativity`.

## Skill inventory (13)

The marketplace and plugin manifest reference 13 Canvas Skills, exactly
matching the upstream `dreamina-skills` repository at SHA `f1f894d`:

- `dreamina-canvas-cli`
- `dreamina-canvas-auth`
- `dreamina-canvas-discover-models`
- `dreamina-canvas-create`
- `dreamina-canvas-compose`
- `dreamina-canvas-generate-image`
- `dreamina-canvas-generate-video`
- `dreamina-canvas-generate-audio`
- `dreamina-canvas-manage-timeline`
- `dreamina-canvas-quote-and-run`
- `dreamina-canvas-resume-operation`
- `dreamina-canvas-download-assets`
- `dreamina-canvas-use` (the only implicitly invokable Canvas Skill)

Byte parity with upstream is asserted by
`scripts/verify_dreamina_canvas_skills.py` against
`upstream/dreamina-skills.lock.json`.

## Fresh Codex task discovery

To re-validate in a fresh Codex task:

1. Open a fresh Codex task on a clean workspace.
2. Install from the marketplace: `codex plugins install
   https://github.com/partme-ai/codex-dreamina-canvas-plugin`.
3. Confirm the resolver sees exactly thirteen `dreamina-canvas-*` Skills.
4. Confirm `allow_implicit_invocation == true` for `dreamina-canvas-use`
   only; the other twelve are explicit.

## Auth and paid-canary gates

Both gates are **PASS** on this branch, each completed under its own
explicit user authorization:

- `auth`: device-authorization login completed. `auth status` reported
  `loggedIn: true` and the authoritative server check
  (`auth account`) returned `ok: true`, `isVip: true`,
  `vipLevel: standard`. The user identifier is redacted from committed
  evidence.
- `paid_canary`: one low-cost `t2i` draft was quoted at
  `totalMaxCredits: 5`, approved with an explicit `--credit-ceiling 100`,
  run exactly once with a caller-minted persisted `submitId`, waited to a
  terminal `succeeded` state, downloaded, and verified. `wc -c` and
  `shasum -a 256` both agreed with the CLI's reported `size`/`sha256`
  (705847 bytes,
  `042406680ed8d763bc7e661a3588a42b01e7d9c096d14d01f8b0881a9ff7fd96`), and
  the plugin's own `artifact_guard.verify()` returned `ok: true`.

Neither gate was faked or simulated. The approval token was held in
process memory, never written into the repository, and destroyed
immediately after `node run`. No second `submitId` was minted.

## SHA comparison

| Ref | SHA | State |
|-----|-----|--------|
| Local plugin `HEAD` (this branch) | recorded by `git rev-parse HEAD` | local on `feat/canvas-plugin-pin` |
| Tracking upstream (this branch) | recorded by `git rev-parse '@{upstream}'` | tracks `origin/feat/canvas-plugin-pin` |
| Remote `origin/feat/canvas-plugin-pin` | recorded by `git ls-remote origin refs/heads/feat/canvas-plugin-pin` | pushed this session |
| Remote `origin/main` (pre-session) | `8545fbddafcdf6b4bf8de5b7ea1411483cda0efe` | unchanged — branch-level push only |

All three plugin-branch SHAs (`local`, `tracking`, `remote`) are
identical: `ec656374817c0b8fec9b9a2f95597da903e8e9c3`. This satisfies
the "three-end SHA equality" check that the plan requires for a
successful fresh Codex installation on this branch.

The user explicitly chose branch-level push over `main`; the plugin's
`origin/main` therefore remains at the pre-session SHA until a
separate merge-and-push to `main` is authorised.

## Upstream SHA pin

The plugin references the upstream `dreamina-skills` repository at
commit `c598cd478edcd295d09c421ea1d54a51a552fea6`, recorded in
`upstream/dreamina-skills.lock.json` and verified byte-for-byte by
`scripts/verify_dreamina_canvas_skills.py` (13 skills, 40 files). The
upstream `feat/canvas-skills` branch is also pushed to origin at this SHA.

The pinned commit moved from `f1f894d…` to `c598cd4…` when the runtime
boundary evidence was recorded upstream. The `skills/` tree is
byte-identical between the two commits — only `verification/` and
`tests/` changed — which the byte-parity verifier confirms.
