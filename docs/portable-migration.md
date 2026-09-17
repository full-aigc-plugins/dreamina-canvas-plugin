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
  "name": "codex-dreamina-canvas",
  "source": {
    "source": "url",
    "url": "https://github.com/partme-ai/partme-dreamina-canvas.git",
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
4. **Identity unchanged** — still `dreamina-canvas`; the current
   compatibility patch version is `0.1.2`.

## Known drift to watch

The installed Codex toolchain's `plugin-creator` scaffold still emits only
`.codex-plugin/plugin.json`. When that scaffold starts emitting a portable
root manifest, re-run the parity tests rather than hand-editing either file.
