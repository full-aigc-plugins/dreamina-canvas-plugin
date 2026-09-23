## Context

`add-canvas-visual-quality-loop` 的四个库模块已按 domain 契约实现并通过 307 项
测试；缺的只是「谁调用它们」。本 change 把接缝接上，不重写任何模块。

## Goals / Non-Goals

**Goals:**

- 生产入口可达四个模块（CLI 子命令面）。
- 控制器账本与 `loop_budget` 契约语义统一。
- Judge 自动产 receipt 并经 `judge_exchange` 校验导入。

**Non-Goals:**

- 多轮自动循环；修订自动应用（无 `--apply`）；控制器内视频编排。

## Decisions

1. **账本统一与环依赖消除**：`Quote` 迁入 `budget.py`（`budget` 原
   `from visual_loop import Quote` 反向依赖）；`visual_loop.py` 重新导出
   `Quote` 保持向后兼容。控制器字段换成 `BudgetLedger` + `PerRoundPolicy |
   BoundedBatchPolicy` + `ExitGovernor`；`Reservation` 内存承载（loop_budget
   schema 保留为未来回执契约）。
2. **修订面三段式**：`plan_revision`（gap→VerifiedGap 转换 + `propose_revision`
   + `fidelity_check`）→ 打印提案；`--apply` 才走 `PromptRevisionService.apply`
   （自带 mutationVersion/fingerprint 并发守卫 + `updateId` 幂等 + receipt 落盘）。
3. **Judge 面 shell-callable 桥接**：`judge --adapter {human,host-subagent,
   design-skill,external-mcp}`；后三者以 `--cmd` 为宿主无关桥（request JSON
   走 stdin，verdict JSON 走 stdout），产出直接经 `judge_exchange.
   import_judge_receipt` 校验导入——内容摘要绑定、fresh-context、拒秘密、
   一 request 一 receipt 全部生效。`human` 保留为停等路径。
4. **视频面只做组合入口**：`sample-frames` 输出 `VideoEvidence` JSON；
   `video-verdict` 组合 `decide_video_verdict`（静态必要非充分、时序缺失
   `MANUAL_REVIEW_REQUIRED`）。控制器视频编排明确为 Non-goal。
5. **协议显式继承**：`FFmpegFrameSampler(FrameSamplerPort)`、
   `DegradedTemporalEvaluator(TemporalGateEvaluator)`——消除「协议孤立」假象，
   编译期即保证接口形状。

## Risks / Trade-offs

- 预算账本不持久化：进程崩溃丢账本 → 保守方向（多记 unknown）由调用方
  在重启后重估；`loop_budget.schema.json` 已就位待回执化。
- `judge --cmd` 的 shell-callable 信任宿主：与 JudgePort「宿主负责取评价、
  插件只验证」的分工一致，且产出必过 `judge_exchange` 校验。

## Migration Plan

API 只增不删（`visual_loop.BudgetLedger/ExitPolicy` 删除是内部符号；外部符号
`Quote` 保留）。tests 同步迁移到 `budget.py` 账本 API。
