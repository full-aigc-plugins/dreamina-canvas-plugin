# Codex plugin specification compliance audit

Audited against `https://developers.openai.com/plugins/build/plugins` and the
published schema `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`.

Method: every requirement was checked against the files in this repository
**and** verified against the installed Codex runtime
(`/Applications/ChatGPT.app/Contents/Resources/codex`) by performing a real
install. Where the documentation and the installed toolchain disagreed, both
were recorded and the empirical result noted.

## Package layout

| Spec requirement | Implementation | Verdict |
|---|---|---|
| `plugin.json` at root — canonical portable manifest | present, `$schema` + identity + `extensions.com.openai.interface` | PASS |
| `skills/` at root, auto-discovered, manifest needs no `skills` field | 13 directories, discovered without relying on a `skills` field | PASS |
| `mcp.json` — optional, only for bundled MCP servers | absent; no MCP server is bundled, so nothing is declared (validated) | PASS |
| `.codex-plugin/plugin.json` — optional compatibility fallback | present and validator-clean | PASS |
| Visual assets under `./assets/` | `assets/{logo,logo-dark,composer-icon}.png`, all referenced with `./assets/` prefixes | PASS |
| Extension/compat paths relative to root, begin `./` | all manifest paths begin `./` | PASS |

## Portable `plugin.json`

| Spec requirement | Implementation | Verdict |
|---|---|---|
| `$schema` required, exact constant | `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` | PASS |
| `name` required, pattern `^(?!.*(?:--\|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$`, ≤ 64 | `codex-dreamina-canvas` | PASS |
| `additionalProperties: false` at top level | only `$schema`/`name`/`version`/`description`/`author`/`homepage`/`repository`/`license`/`keywords`/`extensions` | PASS |
| `author` nested keys limited to `name`/`email`/`url` | `name` + `url` only | PASS |
| `extensions` keyed by reverse-domain namespace | `extensions.com.openai.interface` | PASS |
| `interface` under `extensions.com.openai`, not top level | correct | PASS |
| When `extensions.com.openai` is present it replaces (not merges) the compat overlay | both manifests therefore carry a complete, identical interface block; parity is machine-asserted | PASS |

## Marketplace file

| Spec requirement | Implementation | Verdict |
|---|---|---|
| Location `$REPO_ROOT/.agents/plugins/marketplace.json` | present | PASS |
| Top level `name`, `interface.displayName`, `plugins[]` | present | PASS |
| Each entry has `name`, `source`, `policy.installation`, `policy.authentication`, `category` | present | PASS |
| Git source variant `"url"` for repo root, with optional ref | `{"source":"url","url":"…git","ref":"main"}` | PASS |
| `source.path`/paths relative to marketplace root, begin `./`, stay inside | n/a for the Git variant; the local personal-marketplace entry uses `./workspaces/...` | PASS |
| Unresolvable entries are skipped rather than fatal | no unresolvable entries; verified by a successful `codex plugin list` | PASS |

The Git source shape is not merely schema-plausible: the sibling plugin
`codex-dreamina-design` is configured in this environment as a working Git
marketplace with the byte-identical entry shape, and Codex resolves it
successfully.

## Skills

| Spec requirement | Implementation | Verdict |
|---|---|---|
| `skills/<skill-name>/SKILL.md` | 13 directories, one `SKILL.md` each | PASS |
| Frontmatter `name` and `description` | present on all 13; `name` matches the directory | PASS |
| Only the intended Skill is implicitly invokable | `dreamina-canvas-use` only; the other twelve set `false` | PASS |

## Installation and enablement

| Spec requirement | Observed | Verdict |
|---|---|---|
| Install lands in `~/.codex/plugins/cache/$MARKETPLACE/$PLUGIN/$VERSION/` | `~/.codex/plugins/cache/personal/codex-dreamina-canvas/0.1.0/` | PASS |
| Enablement key `[plugins."<plugin>@<marketplace>"] enabled = true` in `config.toml` | `[plugins."codex-dreamina-canvas@personal"] enabled = true` written by the CLI | PASS |
| `version` accepts versions/tags/ranges, not path or URL selectors | `"0.1.0"` | PASS |
| `--sparse` only for Git sources | not used | PASS |

**Documentation imprecision found:** the page states `$VERSION` "is `local`
for local plugins". Observed behaviour is that the manifest's `version`
value is used instead (`0.1.0` for this plugin, `0.3.0` for a sibling local
plugin). A probe plugin installed from a local source also landed under its
manifest version (`0.0.1`), not `local`. Recorded as a doc/implementation
divergence rather than a defect in this repository.

## Verification performed

1. **Portable-layout probe.** An isolated scratch plugin with *only* a
   portable root `plugin.json` plus `skills/probe-skill/SKILL.md` was
   registered in a scratch marketplace. Codex discovered and installed it,
   materialising `plugin.json` and `skills/probe-skill/SKILL.md`. This
   confirms the portable layout is supported by the installed runtime, not
   just by the documentation. Probe marketplace, plugin and cache entry were
   removed afterwards.
2. **Real reinstall of this plugin.** `codex plugin remove` followed by
   `codex plugin add codex-dreamina-canvas@personal` after adding the
   portable manifest. Result: `plugin.json` present in the install root,
   13 Skills discovered, only `dreamina-canvas-use` implicit, plugin
   `installed, enabled`. No regression from adding the portable manifest.
3. **Negative tests on the distribution gate.** Three deliberate violations
   — tampered interface parity, a top-level `skills` field in the portable
   manifest, and a removed `$schema` — each produced the corresponding
   failure. The gate is not vacuous.

## Residual notes

- **Family convention.** The three sibling plugins in this workspace
  (`codex-dreamina-3d`, `codex-dreamina-design`, `codex-stitch-design`) ship
  only `.codex-plugin/plugin.json`. This repository is now the first to also
  carry the canonical portable manifest. Both layouts were confirmed to work
  with the installed Codex, so the siblings are not broken — they are simply
  on the fallback path.
- **Toolchain lag.** The installed `plugin-creator` scaffold still emits only
  the compatibility manifest. If a future scaffold starts emitting a portable
  root manifest, re-run the parity tests rather than hand-editing.
- **Public marketplace install — resolved.** The in-repo marketplace pins
  `ref: "main"`, so the public path requires `main` to carry the Skills.
  After `feat/canvas-plugin-pin` was merged to `main` and pushed, the public
  flow was executed end-to-end: `codex plugin marketplace add
  https://github.com/partme-ai/partme-dreamina-canvas.git` resolved the
  plugin, and `codex plugin add codex-dreamina-canvas@partme-ai-dreamina-canvas`
  installed it with 13 Skills discovered and only `dreamina-canvas-use`
  implicit. See `docs/verification/fresh-installation.md`.
