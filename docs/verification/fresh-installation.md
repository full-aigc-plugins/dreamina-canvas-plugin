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

## Marketplace-source note

The plan's step describes installing *from the public repository
marketplace*. That variant depends on the plugin's `origin/main` carrying
the Canvas Skills, because the in-repo marketplace entry
(`.agents/plugins/marketplace.json`) pins `ref: "main"`. The user
authorised branch-level push only, so `origin/main` does not yet carry the
skills and a public-marketplace install would resolve an empty Skill set.

This gate was therefore verified end-to-end via the **local** marketplace
against the same byte-verified checkout. The verification is substantive:
the Codex CLI performed the real install, materialised the cache, wrote the
config entry, and the resulting discovery is exactly thirteen names with a
single implicit Skill. No manifest or Skill byte differs between the local
checkout and the pushed branch.

To repeat the *public* variant, merge the branch into `main` and push, then
install from the repository URL instead of the local path.
