# Cross-host golden-sample JudgePort acceptance — 2026-09-22 (task 7.7 / 11.8)

Golden fixtures: `tests/fixtures/judge/golden/` (target `6cae5336…`;
identical candidate = same digest; divergent candidate `d7ccd208…`).
Protocol: per host, a **fresh-context headless judge** received only the two
image paths, their pre-computed SHA-256 digests, the four-dimension rubric and
the strict receipt shape — no prompt draft, no history. Both samples were run
on every host. Raw outputs and every receipt are archived in
`docs/verification/golden-hosts/`; the machine-checked rollup is
`golden-hosts-2026-09-22.json`.

## Results (validated against `schemas/judge_receipt.schema.json`)

| Host | Install | identical-pass (≥9) | divergent-fail (≤9, gaps named) | Gates |
|---|---|---|---|---|
| Codex (codex-cli 0.147.0, GPT-5) | marketplace `full-aigc-plugins`, **v0.2.0** | 10.0 accept | 6.0 revise, 2 gaps | **PASS / PASS** |
| Claude Code (2.1.273) | marketplace `dreamina-canvas-plugin`, **v0.2.0** | 10.0 accept | 4.0 revise, 3 gaps | **PASS / PASS** |
| Kimi (0.43.1) | isolated `--skills-dir`, **v0.2.0** | 10.0 accept | 6.0 revise, 2 gaps | **PASS / PASS** |
| ZCode (GLM-5.3-Flash) | isolated install, **v0.2.0** | 10.0 accept | 8.0 revise, 1 gap | **PASS / PASS** |

## Dimension checks per receipt

- **Schema**: every receipt validates against the shipped 2020-12 contract
  (`additionalProperties: false`); zero violations across 8 receipts.
- **Correlation**: every receipt echoes the exact pre-supplied target and
  candidate digests — content binding holds on all hosts.
- **Security**: no secret-shaped field appears in any receipt.
- **Scoring tolerance**: the identical sample scores 10.0 on all four hosts
  (tolerance ±0.0); the divergent sample scores 4.0-8.0 (all ≤ 9, every host
  names at least one concrete gap) — hosts disagree on *how bad* the
  divergent candidate is, none mistakes it for a match. The golden
  contradiction rule (identical must not score < 9; divergent must not score
  ≥ 10 with empty gaps) holds everywhere.

## Install surface (task 11.8)

- Codex: `codex plugin add dreamina-canvas@full-aigc-plugins` →
  `~/.codex/plugins/cache/full-aigc-plugins/dreamina-canvas/0.2.0`.
- Claude Code: required adding the missing `.claude-plugin/marketplace.json`
  (fixed in `074a580`), then `claude plugin install` → cache `…/0.2.0`.
- Kimi: no plugin client on this machine — isolated install via
  `--skills-dir` over the `v0.2.0` archive (14 skills).
- ZCode: isolated install over the `v0.2.0` archive (14 skills).
- Single-round non-paid acceptance per host: see
  `golden-hosts-nonpaid-2026-09-22.md`.
