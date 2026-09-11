# Codex Dreamina Canvas Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build safe Dreamina Canvas CLI orchestration for Codex.

**Architecture:** A strict subprocess adapter and approval guard expose normalized receipts to Canvas Skills. Remote generation remains owned by the CLI.

**Tech Stack:** Codex plugin, Agent Skills, Python, JSON Schema, unittest/pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-codex-dreamina-canvas-plugin-design.md`

## Constraints

- ID `codex-dreamina-canvas`; installed CLI only; JSON mode only.
- Runtime catalogs are authoritative.
- Paid submission requires quote-bound approval and at-most-once execution.
- Unknown submission state is reconciled, never resubmitted automatically.

### Task 1: Manifest and receipt schemas
- [ ] Write failing identity and closed-schema tests.
- [ ] Add plugin manifest and capability/quote/approval/operation/artifact schemas.
- [ ] Validate and commit `feat: define Dreamina Canvas contracts`.

### Task 2: CLI capability adapter
- [ ] Write failing fixtures for version, schema, auth/account, model and voice discovery.
- [ ] Implement argv-only JSON execution and stable error mapping.
- [ ] Run tests and commit `feat: adapt Dreamina Canvas CLI`.

### Task 3: Quote and approval guard
- [ ] Write failing tests for missing, stale, changed, replayed, and expired approvals.
- [ ] Implement quote/request fingerprints and single-consumption approval tokens stored without secrets.
- [ ] Run tests and commit `feat: guard Dreamina Canvas credit use`.

### Task 4: Operation ledger and recovery
- [ ] Write failing tests for submitted/querying/completed/failed/unknown states and restart recovery.
- [ ] Implement atomic ledger writes and bounded polling.
- [ ] Prove timeout does not resubmit; commit `feat: recover Dreamina Canvas operations`.

### Task 5: Canvas Skills
- [ ] Baseline no-skill scenarios for hard-coded models, unsafe approval, and blind retry.
- [ ] Create and individually validate use/auth/discover/canvas/node/timeline/quote/run/recover/download Skills.
- [ ] Run TRACE and forward scenarios; commit `feat: add Dreamina Canvas skills`.

### Task 6: Distribution and acceptance
- [ ] Add failing marketplace, identity, link, secret, and Skill-inventory tests.
- [ ] Implement validator and repository marketplace.
- [ ] Run offline tests and read-only CLI smoke tests; record paid runtime acceptance separately.
- [ ] Commit `test: verify Dreamina Canvas distribution`.
