# Codex Dreamina Canvas Plugin Design

## Goal

Provide safe Codex workflows for Dreamina Canvas while separating no-cost saves from quoted, explicitly approved generation.

## Requirements

- Discover the installed CLI contract and remote catalogs before composing commands.
- Model canvases, nodes, references, timelines, quotes, approvals, operations, and artifacts as explicit receipts.
- Submit each approved paid request at most once.
- Reconcile ambiguous results by ID instead of resubmitting.
- Package a pinned, byte-identical snapshot of the 13 Canvas Skills sourced from `full-aigc-skills/dreamina-skills`.
- Preserve the source layering: CLI foundation, atomic protocols, media/timeline capabilities, then composition and `use` orchestration.
- Allow implicit invocation only for `dreamina-canvas-use`; keep the twelve lower-level Skills explicit building blocks.

## Packaged Skill inventory

| Layer | Skills |
|---|---|
| Foundation | `dreamina-canvas-cli` |
| Atomic | `dreamina-canvas-auth`, `dreamina-canvas-discover-models`, `dreamina-canvas-create`, `dreamina-canvas-quote-and-run`, `dreamina-canvas-resume-operation`, `dreamina-canvas-download-assets` |
| Domain | `dreamina-canvas-generate-image`, `dreamina-canvas-generate-video`, `dreamina-canvas-generate-audio`, `dreamina-canvas-manage-timeline` |
| Orchestration | `dreamina-canvas-compose`, `dreamina-canvas-use` |

The plugin must not maintain parallel Skill prose. A deterministic sync command records the upstream repository URL and commit, copies the declared inventory, and fails when packaged bytes drift.

## Implementation order

1. Validate plugin scaffold and strict JSON CLI adapter.
2. Pin the published `dreamina-skills` source SHA and verify all 13 Skill identities.
3. Package foundation and atomic Skills.
4. Package media and timeline Skills.
5. Package `compose`, then package `use` last.
6. Run fresh-install discovery and read-only runtime acceptance.

## Non-goals

No CLI installation, silent login, hard-coded catalogs, automatic credit approval, browser scraping, or direct private API calls.
