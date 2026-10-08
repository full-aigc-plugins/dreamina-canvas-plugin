---
name: dreamina-canvas-harness
description: 在宿主需要编排 Dreamina Canvas 的审批、单轮视觉评估、恢复或交付证据时使用；提供随插件分发的技能路由和控制器边界。
---

# 即梦画布宿主编排规范

执行通道是 `dreamina-canvas` CLI。使用已安装插件根目录的绝对路径定位
`scripts/visual_loop_cli.py`；不要假定当前目录就是插件根目录。

## 随插件分发的入口

本插件包含 10 个上游技能及本地 `dreamina-canvas-harness`，共 11 个：

| 任务 | 交给对应技能 |
|---|---|
| 编排入口 | `dreamina-canvas-use` |
| CLI 契约与运行时发现 | `dreamina-canvas-cli` |
| 安装与环境诊断 | `dreamina-canvas-cli-setup` |
| 登录授权 | `dreamina-canvas-cli-auth` |
| 文生图 / 图生图 | `dreamina-canvas-cli-text2image` / `dreamina-canvas-cli-image2image` |
| 文生视频 / 参考视频 | `dreamina-canvas-cli-text2video` / `dreamina-canvas-cli-ref2video` |
| 音乐音效 / 人声 | `dreamina-canvas-cli-text2audio` / `dreamina-canvas-cli-text2voice` |

上述上游技能已随插件安装；缺失时安装指定技能：
`npx skills add full-aigc-skills/dreamina-skills --skill <技能名>`。
创建、编排、时间线、模型发现、报价、恢复与下载由 `dreamina-canvas-cli` 的
命令契约承载，不派发给已退役的同名领域技能。

## 执行与交付

1. 检查登录状态；失效时引导重登。模型、引用形式和参数以当前 CLI schema 为准。
2. 保存草稿后报价，确认报价可审批、项目和节点正确；付费执行须经过
   quote → 人工授权 → confirm → run，不代替用户批准费用。
3. 提交身份先落盘。超时、连接异常、未知状态都查询原 `submitId`，不能重发
   或换新身份。状态损坏、回执丢失时停止并保留原文件供恢复。
4. 校验下载的字节数与摘要，再交付画布标识、素材、产物路径、费用和未验证项。

## 单轮视觉控制器

`visual_loop_cli.py` 提供 `lock-target`、`step`、`status`、`request-judge`、
`import-judge`、`judge`、`revise`、`stop` 等入口；具体参数读取 `--help`。
运行时需 `requirements.txt` 的 `jsonschema`；测试额外需 `requirements-dev.txt`。

流程：目标锁定 → 保存图像草稿 → 报价 → 审批暂停 → 单次提交 → 查询 →
下载校验 → Judge 回执 → `COMPLETED` / `REVISION_PROPOSED` 等结束态。
控制器当前保存的是图像 t2i 草稿，不把视频、音频入口当作该控制器已支持的模式。

- 审批暂停输出 `requestFingerprint`，绑定项目、节点、生成草稿、版本和报价上限。
  宿主审核后在 `step` 传入 `--approve-request-fingerprint` 与
  `--approve-credit-ceiling`，审批凭证通过 `--credit-token-env` 指定的环境变量读取。
  首次提交前再次核对实时报价；变化时暂停并重新审批，不沿用旧授权。
- token 不写入状态、回执或控制器输出。外部 CLI 当前需要 `--credit-token`，
  因而适配器启动子进程时会通过 argv 传递；不能声称它永不进入进程参数。
- 预算、保留额和策略随状态原子保存；重启不归零，未知状态不释放预算。
  标记已经尝试提交后，即使缺少 token 也只查询原身份。
- 旧的中途会话若没有 safety 快照，控制器拒绝自动执行。先用 `status` 检查并按
  原 `submitId` 人工对账，保留原记录；不要删除状态文件来绕过恢复检查。
- `judge_only` 目标不上传。`canvas_reference` 缺少 `resourceId` 时返回
  `register_target`；上传器已可与适配器组合，但 CLI 尚未自动串联上传与注册。
  禁止将本地 `file://` URI 当成服务端引用。
- Judge 由宿主、外部命令或人工提供，回执必须通过摘要绑定与结构校验。
  `revise --apply` 是显式修订入口，不会自动开始下一轮。
- `stop` 对已提交任务进入 `DRAINING_ACCEPTED`，继续查询并结算，绝不声称远端取消。
  多轮调度与全流程自动化尚未启用。

## 验证边界

```text
VISUAL_LOOP_STATUS: SINGLE_ROUND_LOCAL_REGRESSION
VISUAL_TARGET_UPLOAD: ADAPTER_COMPOSITION_TESTED_HOST_REGISTRATION_REQUIRED
VISUAL_JUDGE_AUTOMATION: HOST_MEDIATED_RECEIPT_IMPORT_IMPLEMENTED
LOCAL_FILE_URI_REFERENCE: UNSUPPORTED
PAID_EXECUTION: REQUIRES_THE_STANDARD_QUOTE_CONFIRM_RUN_CHAIN
CURRENT_WINDOWS_AND_PAID_VERIFICATION: NOT_RERUN
```

仓库保存了 [2026-09-22 付费单轮记录](https://github.com/full-aigc-plugins/dreamina-canvas-plugin/blob/main/docs/verification/visual-loop-paid-canary-2026-09-22.md)
与 [同日上传记录](https://github.com/full-aigc-plugins/dreamina-canvas-plugin/blob/main/docs/verification/visual-loop-upload-canary-2026-09-22.md)，
README 也记录过 Windows CI 通过。这些是历史证据，本次安全修复后的真实服务、
付费执行及 Windows 环境尚未重验；本地回归不能替代这些验收。
