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

## 5. 视觉质量闭环（计划中，尚未实现）

目标素材锁定、候选产物指针、跨宿主 Judge 与 Prompt Revision 将由
[`add-canvas-visual-quality-loop`](../../openspec/changes/add-canvas-visual-quality-loop/proposal.md)
逐步交付。当前发布版本只有画布保存、报价、一次提交、续查与下载校验；它**没有**
视觉闭环控制器。

```text
VISUAL_LOOP_STATUS: PLANNED_NOT_IMPLEMENTED
VISUAL_TARGET_UPLOAD: NOT_IMPLEMENTED
VISUAL_CANDIDATE_POINTER: NOT_IMPLEMENTED
VISUAL_JUDGE_AUTOMATION: NOT_IMPLEMENTED
LOCAL_FILE_URI_REFERENCE: UNSUPPORTED
```

当前边界：

- 不把本地文件 URI 写入节点 prompt 或引用参数；`uri:` / `vid:` 是否受支持必须以
  当前 CLI schema 和已锁定上游技能为准。
- `download-assets` 当前只将已完成资源下载到用户批准的目录，并校验字节数和
  SHA-256；不会自动维护候选副本、最新产物指针或跨轮目录。
- 本插件当前不自动调用兄弟插件、宿主子智能体或外部 MCP 进行视觉评估；用户如需
  人工评审，应在不泄露凭据的前提下自行提供目标与候选素材。
- 第一阶段控制器落地后，只执行一轮“目标锁定/可选上传 → 草稿 → 报价与批准 →
  生成与恢复 → 下载与校验 → Judge”。Judge 后形成完成结论或修订提案，并暂停，
  不自动发起下一轮。
- `dreamina-design-plugin` 可在未来作为 `JudgePort` 的可选适配器，但不是当前
  Harness 的运行时依赖，也不能替代结构化 JudgeReceipt。

不要把本节的计划描述、Fake CLI 测试或只读 CLI 探测表述为真实资源上传、真实模型
生成或付费验收。对应证据等级见
[`docs/verification/visual-loop-baseline-2026-09-21.md`](../../docs/verification/visual-loop-baseline-2026-09-21.md)。
