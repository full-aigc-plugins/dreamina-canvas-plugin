# Portable Agent Plugins migration

**Status: migrated.** The repository now ships both manifests:

| File | Role |
|------|------|
| `plugin.json` | Canonical portable manifest (published `agent-plugins.org` 1.0.0 schema) |
| `.codex-plugin/plugin.json` | Codex compatibility fallback |

## Why both

The published build documentation describes the portable root `plugin.json`
as the canonical entry point and `.codex-plugin/plugin.json` as an optional
compatibility fallback. Both are shipped so the plugin installs on the
toolchain that generated the original compatibility scaffold **and** on
clients that read the portable layout.

The two files are not merged by any runtime: when `extensions.com.openai` is
present the compatibility overlay is replaced rather than combined. Both
therefore carry a complete, identical interface block, and
`tests/test_portable_parity.py` fails the build if they ever drift.

## Client coverage

`skills/` and `mcp.json` are the portable component types, so **every client in
the [Agent Plugins registry](https://agent-plugins.org/compatible-clients) loads
this package with no client-specific work**: VS Code, Cursor, GitHub Copilot,
ChatGPT & Codex, Kiro, Hermes Agent, OpenClaw, Grok Bot, NanoClaw and OpenHands.

Commands, agents and hooks are explicitly *not* portable, so a client reads them
from the extension directory it owns (§8.2). This package mirrors accordingly:

- `com.github.copilot/` — `hooks/` for VS Code and GitHub Copilot (they share
  this namespace)
- `dev.openhands/` — `commands/`, `hooks/` for OpenHands
- `extensions["com.openai"]` — manifest data for ChatGPT & Codex

The root `commands/` and `hooks/` directories are kept unchanged, so the Codex,
ZCode and Kimi channels keep working. `scripts/validate_portable_plugin.py`
fails if a mirror drifts from its root copy.

> **OpenClaw precedence.** OpenClaw checks for a client-specific bundle marker
> (`.codex-plugin/`) before a root `plugin.json`, and treats the client-specific
> format as winning so its richer mappings survive. This package ships both, so
> OpenClaw loads it as a Codex bundle — which keeps its commands and hooks
> working — rather than as an Agent Plugins bundle. Removing `.codex-plugin/`
> would change that and break the Codex channel, so it stays.

## Layout rules honoured

- `plugin.json`, `skills/`, `assets/` all live at the package root.
- The portable manifest declares **only** published-schema fields. Its top
  level is `additionalProperties: false`, so it deliberately omits `skills`
  and `interface`:
  - `skills/` is auto-discovered at the root, so no `skills` field is needed.
  - `interface` lives at `extensions.com.openai.interface`.
- `name` is a stable kebab-case identifier (`dreamina-canvas`), used as
  the plugin's identifier and component namespace.
- `$schema` is the exact published constant
  `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`.

## Components we deliberately do NOT declare

- **No `mcp.json` / `.mcp.json`** — this plugin bundles no MCP servers.
  Declaring an empty server set would be noise; declaring a server without a
  working transport would be an untruthful claim.
- **No `app.json` / `.app.json`** — no apps.
- **No hooks** — no lifecycle hooks.
- **No screenshots** — `interface.screenshots` is present but empty, because
  none have been authored. It is never populated with placeholder images.

Each of the above is asserted by
`tests/test_portable_parity.py::test_both_manifests_declare_no_mcp_or_apps`
and by `scripts/validate_distribution.py`, so a future addition cannot land
without its companion file.

## Marketplace entry

`.agents/plugins/marketplace.json` uses the Git repo-root source variant:

```json
{
  "name": "dreamina-canvas",
  "source": {
    "source": "url",
    "url": "https://github.com/full-aigc-plugins/dreamina-canvas-plugin.git",
    "ref": "main"
  },
  "policy": { "installation": "AVAILABLE", "authentication": "ON_USE" },
  "category": "Creativity"
}
```

`policy.installation`, `policy.authentication`, and `category` are always
included, as the documentation requires.

## Migration acceptance evidence

The four criteria in the original migration plan are all satisfied:

1. **Schema validation** — the portable manifest is checked against the
   published schema's required fields, `name` pattern and length, and
   `additionalProperties: false` rule, both in
   `scripts/validate_distribution.py` and in
   `tests/test_portable_parity.py`.
2. **Parity between both manifests** — identity fields and all fifteen
   interface fields are asserted equal. Negative tests in the distribution
   gate confirm tampering is caught.
3. **Fresh local installation** — performed via the Codex CLI
   (`codex plugin add dreamina-canvas@personal`); the plugin
   materialises with `plugin.json` present, all thirteen Skills discovered,
   and only `dreamina-canvas-use` implicitly invokable. See
   `docs/verification/fresh-installation.md`.
4. **Identity unchanged** — still `dreamina-canvas`; the current base version is
   `0.3.0`, with `0.3.0+codex.20260923` in the compatibility manifest.

## Known drift to watch

The installed Codex toolchain's `plugin-creator` scaffold still emits only
`.codex-plugin/plugin.json`. When that scaffold starts emitting a portable
root manifest, re-run the parity tests rather than hand-editing either file.
