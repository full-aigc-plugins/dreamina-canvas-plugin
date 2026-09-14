# Codex Dreamina Canvas Plugin

<img src="assets/logo.png" alt="Dreamina Canvas logo" width="128">

> Compatibility foundation for Dreamina Canvas CLI orchestration in Codex.

[English](README.md) | [简体中文](README.zh-CN.md)

## Status and version

This repository contains a validated compatibility manifest, marketplace metadata, brand assets, legal documents, and the Canvas implementation: thirteen Agent Skills, a strict CLI adapter, an operation ledger, and approval and artifact guards. CLI runtime, version, command compatibility, explicitly authorized account authentication, and a separately approved paid canary are recorded as **PASS** in the [runtime evidence](docs/verification/dreamina-canvas-runtime.md).

## Quick start

```bash
codex plugin marketplace add partme-ai/codex-dreamina-canvas-plugin --ref main
codex plugin add codex-dreamina-canvas@partme-ai-dreamina-canvas
```

Restart Codex or the ChatGPT desktop app, open a new task, and ask Codex to draft a Canvas plan. Capability discovery runs first, then a non-charging save, then a fresh quote and explicit approval before any cost-bearing execution.

## What you can build

```text
Codex -> capability discovery -> canvas/node plan -> save(no charge)
      -> quote -> explicit user approval -> run -> query -> download
```

The plugin never hard-codes catalog values (models, voices, ratios, resolutions) and never skips the quote-approval step. A timeout never causes an automatic resubmission; the user can query by stable operation identifiers instead.

## Boundaries and contracts

- Discover models, voices, ratios, and resolutions at runtime; never hard-code catalog values.
- Saving a node and running generation are separate operations.
- Cost-bearing execution requires a fresh quote and explicit user approval.
- A timeout never authorizes resubmission; query by stable operation identifiers first.
- Do not install the CLI or authenticate without user authorization.

## Documentation

- [Architecture](docs/Codex-Dreamina-Canvas-Plugin-Architecture.md) · [架构文档](docs/Codex-Dreamina-Canvas-Plugin-Architecture.zh_CN.md)
- [Technical solution](docs/Codex-Dreamina-Canvas-Plugin-Technical-Solution.md) · [技术方案](docs/Codex-Dreamina-Canvas-Plugin-Technical-Solution.zh_CN.md)
- [Design spec](docs/superpowers/specs/2026-09-11-codex-dreamina-canvas-plugin-design.md)
- [Implementation plan](docs/superpowers/plans/2026-09-11-codex-dreamina-canvas-plugin-implementation.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Production-readiness evidence](docs/verification/production-readiness.md)
- [Real-environment acceptance](docs/verification/real-environment-acceptance-2026-09-13.md)
- [Runtime evidence](docs/verification/dreamina-canvas-runtime.md)

### Development verification

Create an isolated Python 3.11+ environment, install `requirements-dev.txt`, and run the offline gate documented in [CONTRIBUTING.md](CONTRIBUTING.md). CI repeats the same non-charging checks on Python 3.11, 3.12, and 3.13.

## License

Apache-2.0 — see [LICENSE](LICENSE).
