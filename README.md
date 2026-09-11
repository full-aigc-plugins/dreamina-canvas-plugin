# Codex Dreamina Canvas Plugin

> Design-stage Codex workflows for Dreamina Canvas CLI orchestration.

[English](README.md) | [简体中文](README.zh-CN.md)

## Status and purpose

This repository contains documentation and a checkable plan only. `codex-dreamina-canvas` will orchestrate the user-installed `dreamina-canvas` CLI for canvas, node, timeline, model/voice discovery, quotation, explicit credit approval, asynchronous recovery, and artifact download.

```text
Codex -> capability discovery -> canvas/node plan -> save(no charge)
      -> quote -> explicit user approval -> run -> query -> download
```

## Non-negotiable boundaries

- Discover models, voices, ratios, and resolutions at runtime; never hard-code catalog values.
- Saving a node and running generation are separate operations.
- Cost-bearing execution requires a fresh quote and explicit user approval.
- A timeout never authorizes resubmission; query by stable operation identifiers first.
- Do not install the CLI or authenticate without user authorization.

## Documentation

- [Architecture](docs/Codex-Dreamina-Canvas-Plugin-Architecture.md) / [中文](docs/Codex-Dreamina-Canvas-Plugin-Architecture.zh_CN.md)
- [Technical solution](docs/Codex-Dreamina-Canvas-Plugin-Technical-Solution.md) / [中文](docs/Codex-Dreamina-Canvas-Plugin-Technical-Solution.zh_CN.md)
- [Design spec](docs/superpowers/specs/2026-09-11-codex-dreamina-canvas-plugin-design.md)
- [Implementation plan](docs/superpowers/plans/2026-09-11-codex-dreamina-canvas-plugin-implementation.md)

## Evidence

The target behavior derives from the Dreamina Canvas CLI guide inspected on 2026-09-11. CLI runtime/version/command compatibility is not yet verified in this repository.
