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

- `auth` and `paid_canary` are NOT_RUN on this branch. Both are
  intentionally independent of the distribution gate. They require
  separate action-time approval:
  - Provide credentials and re-run `auth account` for the auth gate.
  - Provide one explicit paid canary: a low-cost draft, quote,
    approve, run, observe terminal completion, verify the downloaded
    artifact with the artifact guard.

## SHA comparison

| Ref | SHA | State |
|-----|-----|--------|
| Local plugin `HEAD` (this branch) | `ec656374817c0b8fec9b9a2f95597da903e8e9c3` | local on `feat/canvas-plugin-pin` |
| Tracking upstream (this branch) | `ec656374817c0b8fec9b9a2f95597da903e8e9c3` | tracks `origin/feat/canvas-plugin-pin` |
| Remote `origin/feat/canvas-plugin-pin` | `ec656374817c0b8fec9b9a2f95597da903e8e9c3` | pushed this session |
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
commit `f1f894d0374c8f3ff2e54e2aa896bcd2ad0e15d7`, recorded in
`upstream/dreamina-skills.lock.json` and verified byte-for-byte by
`scripts/verify_dreamina_canvas_skills.py`. The upstream
`feat/canvas-skills` branch is also pushed to origin at this SHA.
