# Per-host single-round non-paid acceptance — 2026-09-22 (task 11.8)

Protocol: on each host, a fresh headless session runs `lock-target` + `step
--approve-credit-ceiling 0` against the temporary canary canvas. Expected
terminal for this acceptance: `AWAITING_APPROVAL` (paused, `request_approval`)
with a quote receipt and **zero spend** — no approval is granted, so nothing is
submitted.

| Host | Install | Result | Evidence |
|---|---|---|---|
| Codex (workspace-write sandbox + network) | marketplace v0.2.0 | `AWAITING_APPROVAL` ✓ | `golden-hosts/codex-nonpaid-raw.txt` |
| Claude Code | marketplace v0.2.0 | `AWAITING_APPROVAL` ✓ | `golden-hosts/claude-nonpaid-raw.txt` |
| ZCode | isolated v0.2.0 | `AWAITING_APPROVAL` ✓ (quote receipt `node_hy5t49s74q`, max 1 credit reserved, nothing charged) | this run |
| Kimi | isolated v0.2.0 | JudgePort golden runs **PASS**; single-round acceptance blocked by Kimi's own 5-hour usage quota (HTTP 403 `provider.auth_error`), raw output archived | `golden-hosts/kimi-nonpaid-raw.txt` |

Also exposed and fixed during this acceptance (6th live-path defect):
the service rejects an **empty prompt** (`params.prompt`
`FIELD_VALUE_INVALID`); `visual_loop_cli.py step` now fails closed before any
draft is saved (`ab2fb38`).
