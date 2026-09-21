# Real paid single-round canary — 2026-09-22 (task 11.4)

Authorization: user directive to complete all remaining change tasks
(2026-09-22). Spend ceiling approved: 1 credit (actual charge: 1 credit).

## Round record

| Stage | Evidence |
|---|---|
| Canvas (temporary) | `58ae987e-d24c-4501-ab38-de0d29f3d4ec` ("visual-loop-upload-canary") |
| Session | `11111111-2222-3333-4444-555555555555` (state under `.loop/sessions/`) |
| Target locked | 8×8 solid blue PNG, sha256 `31ec98a7…` |
| Quote (phase A, no credentials) | paused `AWAITING_APPROVAL`; quote receipt `totalMaxCredits: 1`, node `node_9n06jrpdja` |
| Host approval | `node confirm --credit-ceiling 1` minted `v1.key-1.eyJ…` token; passed via env var only |
| Submission | single `submitId 313bfd44-7c7f-48e1-ba6e-2554d0cadfb8`, **1 credit actually charged** |
| Remote result | operation `succeeded`; resource `304796cd-2079-4a1f-ab22-f06353294042` (1024×1024 jpeg) |
| Download + verify | 314,670 bytes, sha256 `a290813a…`, byte-for-byte verified, committed into `rounds/r1/` |
| Judge request | `judges/request-0.json` (content-bound to both digests, fresh-context asserted) |
| Judge verdict | independent image-vs-image review: **5.5 / 10**, recommendation `revise` (`docs/verification/visual-loop-paid-canary-verdict-2026-09-22.json`; candidate image archived beside it) |
| Final state | `JUDGED` → **`REVISION_PROPOSED`**, controller STOPPED — it did **not** quote or submit a second round |

## Defects the canary exposed and fixed (live-path only, each pushed separately)

1. `cmd_step` missing `hashlib` import (first real execution of the fingerprint path).
2. `CapabilityProbe` used `outcome.ok` / `outcome.error_code()` / `outcome.data()` —
   methods of our internal `CommandOutcome`, not the adapter's `CommandResult`.
3. Probe/uploader argv carried the binary name although the adapter prepends it.
4. Operation-status mapping lacked `succeeded` (the live `-ed` form) and missed
   `resources[].resourceId` nesting — the controller idled at `WAITING` while the
   remote had already succeeded.
5. Download response shape is `path`/`size`/`sha256` with **no media block**;
   `artifact_guard`'s mandatory-media check (a documentation-derived premise)
   is falsified — media is now informational, digests stay authoritative.

Every fix landed with its regression test; suite count grew accordingly.

## Honesty notes

- The judge marked `adapter: human`; scoring used the two images only (the
  8×8 solid-blue target vs the returned castle-on-white), never the prompt text.
- The deliberately non-matching target guarantees a `revise` outcome: the canary's
  purpose is to prove the round **stops after judging** and never auto-retries —
  which it did.
