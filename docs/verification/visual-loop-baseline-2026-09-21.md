# Visual-loop baseline — 2026-09-21

## Scope and evidence rule

This is the pre-implementation baseline for OpenSpec change
[`add-canvas-visual-quality-loop`](../../openspec/changes/add-canvas-visual-quality-loop/proposal.md).
It records observed local facts only. It is not a release record, a real
resource-upload proof, a paid-generation proof, or a cross-host JudgePort
acceptance report.

## Repository and supply-chain baseline

| Surface | Observed state | Interpretation |
|---|---|---|
| Canvas checkout | `main`, `2e04d88e85e90e3bffb476f29ce44da852e12927`, ahead of `origin/main` by one commit | Local Harness work is unreleased and must not be presented as marketplace capability |
| Published Canvas tag | `v0.1.6`, annotated tag object `021a623e7eb5437433f0c5a28786853824bbbc01`, commit `39d1cf0cbad009fcefe56b2ecbd137789e6f1ca7` | Last confirmed plugin release baseline |
| Plugin manifests | `0.1.6`; Codex compatibility manifest `0.1.6+codex.20260920` | No visual-loop version has been released |
| Root skill lock | `dreamina-skills v1.6.2`, `f739b86fff342c1f75a179865356580dfb90b4c7` | Resource-contract work must use a future immutable upstream release |
| Legacy verifier output | `13 skills, 119 files match upstream commit b263ade8e3e3` | The verifier's legacy lock and root `skills.lock.json` disagree; phase 2 must reconcile them before any lock update |
| Upstream checkout | `main`, clean, tag `v1.6.2`, commit `f739b86fff342c1f75a179865356580dfb90b4c7` | No local upstream change is relied on |
| Marketplace checkout | Dirty before this change | Marketplace contents are not fresh release evidence and are not modified by this baseline |

## Runtime and host baseline

| Surface | Observed command result | Scope of evidence |
|---|---|---|
| `dreamina-canvas` | `1.0.0`, commit `ae2c968`, public/CN distribution | Version and metadata probe only; no upload, generation, or paid action was run |
| Codex | `codex-cli 0.153.4` | Executable found; plugin installation and JudgePort were not tested here |
| Claude Code | `2.1.273` | Executable found; plugin installation and JudgePort were not tested here |
| Kimi | `0.43.1` | Executable found; plugin installation and JudgePort were not tested here |
| ZCode | No `zcode` executable on this shell `PATH` | Not verified; this does not prove that ZCode is not installed elsewhere |

## Existing verification baseline

| Gate | Result | Boundary |
|---|---|---|
| `python3.13 -m unittest discover -s tests -v` | PASS, 84 tests | Existing adapter, guard, ledger, schema, manifest and vendor checks; no visual-loop controller |
| `python3.13 -m unittest discover -s tests/scenarios -v` | PASS, 14 tests | Existing orchestration and skill scenarios; no JudgePort or target lifecycle |
| `python3.13 scripts/verify_dreamina_canvas_skills.py` | PASS | Verifies legacy upstream lock only; see supply-chain discrepancy above |
| `python3.13 scripts/validate_distribution.py` | PASS | Verifies current `0.1.6` distribution identity, not a future visual-loop release |

## Visual-loop status at baseline

| Capability | Status | Evidence or limitation |
|---|---|---|
| Target content lock | NOT_IMPLEMENTED | No target receipt schema or persistent target store |
| Canvas target upload | NOT_RUN / NOT_IMPLEMENTED | No controller path; no remote write was authorized |
| Candidate pointer | NOT_IMPLEMENTED | No cross-platform atomic pointer implementation |
| Automated JudgePort | NOT_IMPLEMENTED | No request/receipt adapter or cross-host acceptance |
| Prompt Revision | NOT_IMPLEMENTED | No full generation-block reconstruction path |
| Automatic next round | NOT_IMPLEMENTED | No loop controller or bounded-batch policy |
| Real paid visual-loop canary | NOT_RUN | Requires separate credentials and explicit cost ceiling |

The active change defines the implementation order. Until its required tests,
real-runtime evidence, and release gates are complete, these rows MUST remain
planned or not run rather than being advertised as delivered behavior.
