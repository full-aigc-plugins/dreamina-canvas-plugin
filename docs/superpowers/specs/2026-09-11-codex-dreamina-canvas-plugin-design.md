# Codex Dreamina Canvas Plugin Design

## Goal

Provide safe Codex workflows for Dreamina Canvas while separating no-cost saves from quoted, explicitly approved generation.

## Requirements

- Discover the installed CLI contract and remote catalogs before composing commands.
- Model canvases, nodes, references, timelines, quotes, approvals, operations, and artifacts as explicit receipts.
- Submit each approved paid request at most once.
- Reconcile ambiguous results by ID instead of resubmitting.
- Package Canvas Skills sourced from `dreamina-skills`.

## Non-goals

No CLI installation, silent login, hard-coded catalogs, automatic credit approval, browser scraping, or direct private API calls.
