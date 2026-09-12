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

| Ref | SHA |
|-----|-----|
| Local plugin `HEAD` (this branch) | captured by `git rev-parse HEAD` |
| Tracking upstream (when pushed) | captured by `git rev-parse '@{upstream}'` |
| Remote `origin/main` | captured by `git ls-remote origin refs/heads/main` |

A successful "fresh Codex installation" is the case where all three
SHAs are identical 40-character hex strings.

This branch has **not** been pushed to `origin/main`. Local SHA is the
single source of truth for the packaged plugin until a push is performed
under separate authorization.
