## Why

当前 Dreamina Canvas Harness 仅通过文档描述目标图、产物镜像和视觉评估流程，尚无可恢复、可审计的控制器把资源上传、生成、恢复、下载和 Judge 串成真实闭环；部分说明还与 `dreamina-canvas` CLI 1.0.0 的资源契约不一致。需要把 Dream Loop 的目标锁定、独立评估、预算和停滞治理方法转化为 Canvas 自有的可执行协议，同时保留付费授权、供应链锁定和跨宿主边界。

## What Changes

- 纠正 Harness 中“自动镜像、自动刷新 `latest.png`、自动 Judge”和本地 `uri:file://` 可用等未实现声明，在控制器落地前明确标记为计划能力。
- 在上游 `dreamina-skills` 更新 CLI 1.0.0 契约，覆盖 `resource upload`、稳定 `resourceId`、`res:<uuid>`、`uri/vid` 当前边界和资源导入；发布不可变技能版本后再更新本仓锁文件，禁止直接修改受管副本。
- 新增 Visual Target、Round、Judge、Budget、Loop State 和 Prompt Revision 的 JSON Schema、持久化回执与敏感字段约束。
- 新增 `VisualLoopController` 及端口层，先实现一次“目标锁定/可选上传 → 保存草稿 → 报价与审批 → 生成与恢复 → 下载与校验 → Judge”的单轮闭环；单轮结束后不自动开始下一轮。
- 新增 Prompt Revision：从最新节点读取完整 generation block，以 Judge 差距为输入全量重建，并通过 `mutationVersion`、fingerprint 和稳定 `updateId` 防止覆盖及重复编辑。
- 新增总预算、单轮上限、最大轮数、截止时间、停滞检测、费用预留及停止/排空语义；不把“停止后续提交”描述成远端取消。
- 新增宿主无关 `JudgePort`，使 Codex、Claude Code、ZCode、Kimi、外部 MCP 或人工 Judge 均返回同一结构化回执；无 Judge 时停在 `AWAITING_JUDGE`。
- 图像闭环稳定后扩展视频关键帧和时序 Judge，覆盖闪烁、主体漂移、动作连续、镜头运动、节奏和音画同步。
- 完成测试、真实宿主验收和供应链验证后，按不可变 tag 发布上游技能与 Canvas RC，并同步市场仓。

### Non-goals

- 不复制 Dream Loop 的提示词、Fal 3D 辅助程序或预览服务器。
- 不依赖 Dreamina Design 仓库中尚未完成的 proposal，也不强制安装兄弟插件。
- 不提供无限自动付费循环，不持久化审批 Token，不在 CLI 缺少取消能力时声称可以取消远端任务。
- 本变更不把计划文件、模拟 Judge 或 Fake CLI 测试视为真实付费生产验收。

## Capabilities

### New Capabilities

- `canvas-cli-resource-contract`: 定义 CLI 1.0.0 的资源上传、幂等资源标识、引用类型、导入边界以及受管技能同步要求。
- `canvas-visual-target`: 定义目标素材的锁定、摘要、导入模式、授权目录和跨平台持久化规则。
- `canvas-visual-loop`: 定义单轮闭环、可恢复状态机、回执关联、停止和故障恢复行为。
- `canvas-judge-port`: 定义新鲜上下文 Judge 请求/回执及跨 Codex、Claude Code、ZCode、Kimi 的一致性要求。
- `canvas-prompt-revision`: 定义根据 Judge 差距全量重建 generation block 的并发、幂等和保真约束。
- `canvas-loop-budget`: 定义逐轮与有界整批授权、费用预留、最大轮数、停滞检测和终止策略。
- `canvas-video-judge`: 定义视频关键帧采样、时序质量评估及缺少视频分析能力时的降级语义。

### Modified Capabilities

- `immutable-skill-supply-chain`: 增加 Visual Loop 发布前必须先获得上游正式技能 tag、peeled SHA 和一致内容摘要的验收场景。

## Impact

- 插件本仓：`skills/dreamina-canvas-harness/`、`scripts/`、`schemas/`、`tests/`、架构与验收文档、版本清单。
- 上游技能仓：`full-aigc-skills-repositories/dreamina-skills` 的 Canvas CLI、图像、视频、下载和资源契约；必须先独立发布。
- 外部运行时：`dreamina-canvas` CLI 1.0.0、可选 FFmpeg、宿主视觉 Judge 或外部 MCP Judge。
- 发布面：`skills.lock.json`、四端插件 manifest、不可变 Git tag/GitHub Release、`full-aigc-plugins` 市场清单和全新安装缓存。
- 付费与安全：所有生成继续经过实时报价、显式授权、稳定 `submitId`、授权目录、事务下载/导入和非敏感回执；真实付费 Canary 需要单独的账户与费用上限。
