---
name: dreamina-canvas-harness
description: Dreamina Canvas invocation spec for WorkBuddy - the dreamina-canvas CLI (auth, create/compose, generate image/video/audio, timeline management, quote-and-run, resume), asset download and model discovery. Read this before any canvas creation task.
---

# 即梦画布调用规范（智能体通用）

执行通道：`dreamina-canvas` CLI（安装/校验/调用见 `dreamina-canvas-cli` 技能）；本插件随附其脚本与技能。
画布 = **多模态画布创作**：图、视频、**音频**、时间线与成片。

## 1. 能力族（13 个技能已随插件分发）

| 族 | 技能 |
|---|---|
| 环境与入口 | `dreamina-canvas-auth`（登录授权）、`dreamina-canvas-cli`、`dreamina-canvas-use` |
| 画布创建与编排 | `dreamina-canvas-create`、`dreamina-canvas-compose`、`dreamina-canvas-manage-timeline` |
| 生成（图/视频/**音频**） | `dreamina-canvas-generate-image` / `-video` / **`-audio`** |
| 运营 | `dreamina-canvas-quote-and-run`（报价与执行）、`dreamina-canvas-resume-operation`（断点续作）、`dreamina-canvas-discover-models`、`dreamina-canvas-download-assets` |

## 2. 硬规则

- 先 `auth` 后一切；授权态丢失就引导重登，不重试烧配额。
- `quote-and-run`：先报价后执行，报价/预算超限即停。
- 长任务断点走 `resume-operation`，不从头重跑。
- 模型选择用 `discover-models` 实测面（本机 CLI 面可能滞后于主干），不硬编码目录。

## 3. 标准工作流

1. `auth` 确认授权 → `create` 建画布。
2. 按需生成：图 / 视频 / 音频（音频是本套件独有能力，设计套件没有）。
3. `manage-timeline` 编排时间线 → `compose` 合成。
4. `download-assets` 取产物；交付列出：画布标识、素材清单、时间线摘要、产物路径、配额消耗、未验证项。

## 4. 纪律

- CLI 的 stdout/stderr 与标识持久化按 `dreamina-canvas-cli` 技能规范执行。
- 付费动作同样 submit-once：一次授权一次提交，恢复走 resume 技能。

## 5. 视觉质量闭环（单轮控制器已实现；付费 Canary 与多轮未运行）

单轮视觉闭环控制器已在本仓实现并有测试覆盖：目标锁定 → 草稿 → 报价 →
**审批暂停** → 单次提交（submitId 先行落盘，重启只对账同一身份）→ 恢复等待 →
事务下载与校验（摘要不符即隔离）→ Judge 请求/回执文件对 → 停在
`JUDGED` / `REVISION_PROPOSED`。控制器自身永不报价或提交第二轮。

宿主入口：`scripts/visual_loop_cli.py`（`lock-target` / `step` / `status` /
`request-judge` / `import-judge` / `stop`）。审批凭证只经环境变量在提交瞬间
读取，绝不写入 argv、日志或任何持久化文件。

```text
VISUAL_LOOP_STATUS: SINGLE_ROUND_IMPLEMENTED_PAID_CANARY_NOT_RUN
VISUAL_TARGET_UPLOAD: IMPLEMENTED_UPLOAD_CANARY_NOT_RUN
VISUAL_CANDIDATE_POINTER: IMMUTABLE_ROUNDS_PLUS_ATOMIC_LATEST_JSON
VISUAL_JUDGE_AUTOMATION: HOST_MEDIATED_RECEIPT_IMPORT_IMPLEMENTED
LOCAL_FILE_URI_REFERENCE: UNSUPPORTED
PAID_EXECUTION: REQUIRES_THE_STANDARD_QUOTE_CONFIRM_RUN_CHAIN
WINDOWS_LOCK_SEMANTICS: NOT_VERIFIED
```

当前边界：

- 不把本地文件 URI 写入节点 prompt 或引用参数；`uri:` / `vid:` 是否受支持必须以
  当前 CLI schema 和已锁定上游技能为准。
- **未执行**真实资源上传 Canary 与真实付费单轮 Canary；在此之前不得把上传与
  付费能力表述为已验收。Windows 上的文件锁与原子替换语义未在真实 Windows 上
  验证。
- Judge 由宿主在暂停点之间提供：`request-judge` 落盘请求，宿主子代理 / 兄弟
  插件 / 人工产出的裁决经 `import-judge` 校验（内容摘要绑定、fresh-context、
  拒绝秘密字段）后才能被控制器消费；本 Harness 不自动调用任何宿主。
- 停止语义诚实：已接受的任务进入排空（`DRAINING_ACCEPTED`），继续以原
  `submitId` 对账；从不声称远端取消。
- Prompt Revision（change 第 8 节）落地前，修订提案只记录不自动应用。

不要把本节的控制器实现表述为已通过真实付费验收；对应证据等级见
[`docs/verification/visual-loop-baseline-2026-09-21.md`](../../docs/verification/visual-loop-baseline-2026-09-21.md)。
