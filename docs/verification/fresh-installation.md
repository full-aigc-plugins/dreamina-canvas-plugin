# Fresh Codex installation discovery evidence

Executed under explicit user authorization as the final acceptance gate of
the implementation plan.

## Install flow

The canonical Codex install is two steps: register the repository in a
marketplace, then let the Codex CLI materialise it.

```bash
# 1. register in the personal marketplace (~/.agents/plugins/marketplace.json)
#    entry: codex-dreamina-canvas -> source: {source: local, path: <checkout>}
#           policy: {installation: AVAILABLE, authentication: ON_USE}

# 2. install
$ /Applications/ChatGPT.app/Contents/Resources/codex plugin add codex-dreamina-canvas@personal
Added plugin `codex-dreamina-canvas` from marketplace `personal`.
Installed plugin root: /Users/wandl/.codex/plugins/cache/personal/codex-dreamina-canvas/0.1.0
```

The Codex CLI owns `config.toml`; the entry it wrote is:

```toml
[plugins."codex-dreamina-canvas@personal"]
enabled = true
```

`codex plugin list` confirms:

```text
codex-dreamina-canvas@personal  installed, enabled  0.1.0  <checkout>/.worktrees/canvas-plugin
```

## Discovery result

Materialised plugin root:
`~/.codex/plugins/cache/personal/codex-dreamina-canvas/0.1.0/`

Skills discovered (exactly thirteen):

```text
dreamina-canvas-auth                dreamina-canvas-generate-video
dreamina-canvas-cli                 dreamina-canvas-manage-timeline
dreamina-canvas-compose             dreamina-canvas-quote-and-run
dreamina-canvas-create              dreamina-canvas-resume-operation
dreamina-canvas-discover-models     dreamina-canvas-use
dreamina-canvas-download-assets
dreamina-canvas-generate-audio
dreamina-canvas-generate-image
```

Count check: `ls skills/ | grep -c '^dreamina-canvas-'` → **13**.

Invocation policy per discovered Skill:

| Skill | `allow_implicit_invocation` |
|-------|----------------------------|
| `dreamina-canvas-use` | **true** |
| all other twelve | false |

Only `dreamina-canvas-use` is implicitly invokable. The other twelve remain
explicit building blocks, exactly as the design requires.

## Public repository marketplace install (primary evidence)

The plan's step describes installing *from the public repository
marketplace*. That path was executed end-to-end after the feature branch was
merged to `main` and pushed:

```bash
$ codex plugin marketplace add https://github.com/partme-ai/partme-dreamina-canvas.git
Added marketplace `partme-ai-dreamina-canvas` from https://github.com/partme-ai/partme-dreamina-canvas.git.
Installed marketplace root: ~/.codex/.tmp/marketplaces/partme-ai-dreamina-canvas

$ codex plugin list
codex-dreamina-canvas@partme-ai-dreamina-canvas  not installed  https://github.com/partme-ai/partme-dreamina-canvas.git, ref `main`

$ codex plugin add codex-dreamina-canvas@partme-ai-dreamina-canvas
Added plugin `codex-dreamina-canvas` from marketplace `partme-ai-dreamina-canvas`.
Installed plugin root: ~/.codex/plugins/cache/partme-ai-dreamina-canvas/codex-dreamina-canvas/0.1.0
```

Verification of the publicly installed copy:

- Skills discovered: **13**
- `allow_implicit_invocation` true for **`dreamina-canvas-use` only**
- Installed under the Git marketplace's own cache namespace
  (`partme-ai-dreamina-canvas`), separate from the local `personal` one

This confirms the in-repo marketplace entry (`.agents/plugins/marketplace.json`)
resolves correctly through the documented Git repo-root `"url"` + `ref`
source variant, and that the packaged Skills are reachable from the public
repository.

## Local marketplace install (secondary evidence)

The same plugin was also installed from the local `personal` marketplace,
against the worktree rather than the pushed `main`. That path produced the
identical result (13 Skills, only `dreamina-canvas-use` implicit), which is
what allowed the packaging to be validated before the merge.

Both installs are retained so the discovery result can be reproduced without
network access.
