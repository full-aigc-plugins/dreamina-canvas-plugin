# Real resource-upload canary — 2026-09-22 (task 5.6)

Authorization: user directive to complete all remaining change tasks
(2026-09-22). No generation was executed; no credits were spent.

## Facts

| Item | Value |
|---|---|
| CLI | `dreamina-canvas` 1.0.0 (commit ae2c968, cn) |
| Auth | OAuth, profile default, prod/cn, `loggedIn: true` |
| Temporary canvas | `58ae987e-d24c-4501-ab38-de0d29f3d4ec` ("visual-loop-upload-canary") |
| Canary file | 8×8 PNG (64 bytes payload), local |
| Stable resource id | `7f4ea513-2a38-443e-9e44-ed086f93a2e9` (persisted BEFORE upload) |

## Sequence and results

1. `resource upload --file canary-target.png --resource-id 7f4ea513… --import-kind local_upload`
   → `ok: true`, echoed `resourceId = 7f4ea513…`, `mediaType: image`, requestId recorded.
2. Second upload with the SAME resource id → `ok: true`, same `resourceId`
   returned; `resource get` shows exactly one resource — **idempotent, no duplicate**.
3. `resource get 7f4ea513…` → `status: success`, `type: image`,
   `source: uploaded`, `name: canary-target.png`, server requestId recorded.

## Verdict

The stable-UUID idempotency contract and the receipt shape used by
`scripts/target_store.ResourceUploader` are confirmed against the real CLI and
server. Task 5.6 satisfied.
