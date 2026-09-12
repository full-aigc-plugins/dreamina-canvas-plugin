# Dreamina Canvas CLI runtime evidence

Read-only evidence captured after the dreamina-canvas binary was installed
to `/Users/wandl/.local/bin/dreamina-canvas`. No login was performed; no paid
generation was attempted. `auth account` was not invoked because the active
session has no user-supplied credentials.

## version

```bash
$ dreamina-canvas --format json version
```

```json
{
  "schemaVersion": "1",
  "ok": true,
  "data": {
    "version": "1.0.0",
    "commit": "ae2c968",
    "buildTime": "2026-09-05T08:54:32Z",
    "edition": "public",
    "distribution": "cn",
    "releaseDate": "2026-09-05",
    "releaseNotes": "初始版本：支持登录与模型发现、画布及多类型节点编辑、素材上传下载、积分报价确认和可恢复生成，并提供 Agent/TTY 双模式输出。"
  }
}
```

## schema (per-family declared exit codes)

| Family | Declared exit codes |
|--------|---------------------|
| `auth` | 0, 1, 2, 11, 12, 20, 21 |
| `model` | 0, 1, 2, 11, 12, 13, 21 |
| `voice` | 0, 1, 2, 11, 12, 13, 21 |
| `canvas` | 0, 1, 2, 11, 12, 13, 20, 21, 22 |
| `node` | 0, 1, 2, 11, 12, 13, 21, 22 |
| `operation` | 0, 1, 2, 11, 12, 20, 21, 22 |
| `resource` | 0, 1, 2, 11, 12, 13, 21, 22 |
| `schema` | 0, 1, 2 |
| `version` | 0, 1, 2 |

## Read-only commands performed

- `dreamina-canvas version` (full payload above).
- `dreamina-canvas schema` (returned full command tree and exit-code
  map; per-family table above).

## Commands intentionally NOT performed

- `dreamina-canvas auth login` / `auth account` — no credentials supplied.
- `dreamina-canvas auth status` — local-only and not informative without
  auth account as the authoritative check.
## Runtime boundary summary

| Boundary | Status | Notes |
|----------|--------|-------|
| `cli_runtime` | **PASS** | Binary installed; `version` and `schema` returned successfully. |
| `auth` | **PASS** | Device-authorization login completed under explicit user authorization; `auth account` confirmed the server-side identity. |
| `paid_canary` | **PASS** | One low-cost `t2i` draft quoted, approved with `--credit-ceiling 100`, run once with a persisted `submitId`, waited to terminal, downloaded, and verified with the plugin's `artifact_guard`. |

## Auth evidence (2026-09-12)

Device-authorization flow, executed only after the user supplied an
authorization decision and completed the browser step:

```bash
$ dreamina-canvas --format json auth login
# → {"status":"authorization_required","challenge":{"deviceCode":"<redacted>",
#    "userCode":"<redacted>","verificationUri":"https://jimeng.jianying.com/…",
#    "expiresAt":"…"},"profile":"default","authMode":"oauth",
#    "distribution":"cn","version":"1.0.0","edition":"public"}

$ dreamina-canvas --format json auth wait --device-code <deviceCode> --timeout 10m
# → completed after the user finished the browser authorization

$ dreamina-canvas --format json auth status
# → {"loggedIn":true,"profile":"default","region":"cn","environment":"prod",
#    "authMode":"oauth","distribution":"cn","version":"1.0.0","edition":"public"}

$ dreamina-canvas --format json auth account
# → {"ok":true,"data":{"userId":"<REDACTED>","isVip":true,"vipLevel":"standard"}}
```

`auth status` reported `loggedIn: true`; `auth account` (the authoritative
server check) confirmed the identity. The user identifier is redacted.

## Paid canary evidence (2026-09-12)

Full `quote → confirm → run → wait → download → verify` chain, all on the
`default` profile against `distribution=cn`, `environment=prod`.

| Step | Command | Result |
|------|---------|--------|
| Discover | `model list --type image` | 7 image models; `t2i` and `i2i` modes with per-model ratio / resolution / count bounds |
| Validate | `node create image --dry-run …` | `ok:true`, `validationScope:"local"`, `sideEffects:[]` |
| Canvas | `canvas create "canary-canvas" --project-id <uuid>` | `ok:true`, explicit caller-minted `projectId` |
| Draft | `node create image --mode t2i --model … --ratio 1:1 --resolution 1.5K --count 1` | `ok:true`, saved as draft (no credits) |
| Quote | `node quote --node-id <id>` | `totalMaxCredits: 5`, `confirmable: true`, `confirmationRequired: false` |
| Approve | `node confirm --node-id <id> --credit-ceiling 100` | token issued, `creditCeiling: 100`, short-lived expiry; token kept in process memory and destroyed after use |
| Run | `node run --node-id <id> --credit-token <t> --submit-id <uuid>` | `state: accepted`, `resourceId` returned, `submitId` matches the persisted value |
| Wait | `operation wait <submitId> --timeout 10m --interval 5s` | `state: succeeded`; resource `1536×1536`, `format: jpeg` |
| Readiness | `resource get <resourceId>` | `status: success`, `source: generated` |
| Download | `resource download <resourceId> --output ./out` | atomic write; `path`, `size`, `sha256` returned |
| Verify | `shasum -a 256` + `wc -c` + `artifact_guard.verify()` | byte count and SHA-256 match the CLI report; guard returned `ok: true` |

Verified artifact facts (non-secret):

```text
resourceId : b062d52f-fa20-4093-ae8b-d011ba853d82
path       : <canary-output-dir>/dreamina-b062d52f-fa20-4093-ae8b-d011ba853d82.png
size       : 705847 bytes           (wc -c agreed)
sha256     : 042406680ed8d763bc7e661a3588a42b01e7d9c096d14d01f8b0881a9ff7fd96
             (shasum -a 256 agreed; artifact_guard.verify() → ok=true)
media      : 1536 × 1536, jpeg
```

The canary consumed **5 credits** against a **100-credit** approved
ceiling. No second `submitId` was minted; the run was executed once and
resumed by ID only.

## Schema drift observed (runtime truth vs. guide)

The installed artifact is `1.0.0` / `ae2c968` while the 2026-09-11 guide
describes a later surface. Confirmed divergences, recorded here as runtime
truth rather than treated as defects:

| Guide | Installed `1.0.0` |
|-------|-------------------|
| `model search --type image` | `model list --type image` |
| `model <name> --type image` | `model find <name> --type image` |
| — (not documented) | `node create image --dry-run` (local validation, zero side effects) |

This is exactly the drift the Canvas Skills are designed to absorb: the
`dreamina-canvas-cli` Skill requires `version` + `schema` before command
construction, and `dreamina-canvas-discover-models` requires a live
discovery payload rather than a remembered catalog. No packaged Skill
prose was modified to accommodate the drift; the adapter routed by exit
code and `requiredAction` throughout.

A minor additional observation: `node show --node-id <id>` for this node
returned `status: null` with an empty `resources` array while
`operation wait` and `resource get` both reported success. Consumers
should read the terminal state from `operation wait` / `resource get`
rather than from `node show` alone, which matches the Skills' existing
guidance.

## Commands intentionally NOT performed

- Any write outside the `default` profile.
- Any second submission for the same node (no new `submitId` was minted).
- Any `--yes` approval (the explicit `--credit-ceiling 100` was used).
- Any printing or persisting of the credit approval token, signed URLs,
  cookies, or account identifiers.
