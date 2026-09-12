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
- `dreamina-canvas model search` / `voice list` — would expose model or
  voice names that the guide contract intentionally omits; deferred until
  paid canary.
- Any `node quote` / `node confirm` / `node run` — paid execution.
- Any `resource download` — requires a completed node.

## Runtime boundary summary

| Boundary | Status | Notes |
|----------|--------|-------|
| `cli_runtime` | **PASS** | Binary installed; `version` and `schema` returned successfully. |
| `auth` | NOT_RUN | No credentials supplied; cannot validate auth account. |
| `paid_canary` | NOT_RUN | Requires separate action-time approval; intentionally independent. |
