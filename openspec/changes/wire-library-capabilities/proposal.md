## Why

归档的 `add-canvas-visual-quality-loop` 交付了完整且测试齐备的四个模块——
`budget.py`、`prompt_revision.py`、`judge_adapters.py`、`video_judge.py`——
但 codegraph 接缝分析（2026-09-23，841 节点/6892 边）显示这四个模块在生产入口
`visual_loop_cli.py` 中**零 import**：

- 修订提案固定为 `_NoRevision` 桩，`REVISION_PROPOSED` 后用户必须手工改 prompt；
- 预算走 `visual_loop.py` 内嵌的同名简化 `BudgetLedger`（3 字段 + would_exceed），
  与 `budget.py` 的 `BudgetLedger`（unknown 语义 + reserve/settle）**同名不同物**，
  且 `schemas/loop_budget.schema.json` 契约对齐的是后者；
- 四类 Judge 适配器只能手跑 headless CLI，不经 `judge_exchange` 校验导入；
- `video_judge` 的 `decide_video_verdict` 唯一调用者是它自己文件内的
  `StaticOnlyJudgeAdapter`。

能力对用户不可达——「库完备、缝未接」。

## What Changes

- 新增 CLI 子命令 `revise` / `judge` / `sample-frames` / `video-verdict`：
  分别接通 `PromptRevisionService`、四类 Judge 适配器（含自动产 receipt +
  `judge_exchange` 校验导入）、`FFmpegFrameSampler` 与视频判定组合。
- 控制器账本统一到 `budget.py`（保守 reserve/settle、unknown 持续占额、
  `ExitGovernor` 停滞/重复-gap/最佳轮次治理），删除 `visual_loop.py` 内嵌简化版；
  `Quote` 数据类迁入 `budget.py` 消除环依赖。
- `revise` 默认只产出提案，`--apply` 显式应用（守约「修订仅提案」的非目标）。
- README 增加入口对照表；清理 `judge_exchange._append_ref` 死代码；
  为 `validate_distribution.validate` 补直接单测。

### Non-goals

- 不实现多轮自动循环：`JUDGED` 后不得自动报价或提交下一轮。
- 不实现修订「自动应用」：`--apply` 必须显式。
- 不做控制器内视频轮次编排：视频判定以 CLI 组合入口暴露。

## Capabilities

### Modified Capabilities

- `canvas-prompt-revision`：新增 revision 入口面要求。
- `canvas-loop-budget`：新增控制器单一账本与策略入口要求。
- `canvas-judge-port`：新增 judge 适配器分派与自动导入要求。
- `canvas-video-judge`：新增视频采样/判定入口面要求。

## Impact

- `scripts/`、`tests/`、`README.md`、`README.zh-CN.md`、`docs/`。
- 不改 `schemas/`、不动付费安全链（quote→confirm→run 语义不变）、
  不动技能锁与上游 vendored 内容。
