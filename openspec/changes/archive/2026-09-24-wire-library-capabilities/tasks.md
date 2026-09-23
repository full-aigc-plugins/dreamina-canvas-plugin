## 1. 账本统一与环依赖消除

- [x] 1.1 `Quote` 迁入 `budget.py`；`visual_loop.py` 重新导出保持兼容。
- [x] 1.2 删除 `visual_loop.py` 内嵌 `BudgetLedger`/`ExitPolicy`；控制器换
      `BudgetLedger` + `BudgetPolicy` + `ExitGovernor` + `Reservation`。
- [x] 1.3 `_on_QUOTED` 走 `policy.check` + `budget.reserve`；
      `_on_WAITING` 终态 `settle`（completed/failed）；`_on_AWAITING_JUDGE`
      决策走 `ExitGovernor.observe`（含 stalled → STALLED）。
- [x] 1.4 tests 迁移并新增账本统一断言（环依赖回归测试）。

## 2. 修订面（revise）

- [x] 2.1 `prompt_revision.py`：`gaps_from_dicts` + `plan_revision` + `apply_plan`。
- [x] 2.2 `visual_loop_runtime.CliPromptRevision`（PromptRevisionPort 实现），
      替换 `_NoRevision`；控制器 `propose(*, verdict, node_id)` 签名。
- [x] 2.3 CLI `revise` 子命令（默认提案，`--apply` 显式应用）+ 测试。

## 3. Judge 面（judge --adapter）

- [x] 3.1 `judge_adapters.make_shell_judge` + `dispatch_judge`。
- [x] 3.2 CLI `judge` 子命令（human 停等 / 三类 shell-callable 自动产 receipt
      并经 `judge_exchange` 导入）+ 测试。

## 4. 视频面（sample-frames / video-verdict）

- [x] 4.1 `FFmpegFrameSampler`/`DegradedTemporalEvaluator` 显式继承协议。
- [x] 4.2 CLI `sample-frames` + `video-verdict` 子命令 + 测试。

## 5. 清理与文档

- [x] 5.1 清理 `judge_exchange._append_ref` 死代码。
- [x] 5.2 `validate_distribution.validate` 直接单测。
- [x] 5.3 README/README.zh-CN 入口对照表 + docs 同步。

## 6. 验证与发布

- [x] 6.1 全量测试 + ruff + OpenSpec strict + 分发/技能校验。
- [x] 6.2 bump minor 版本 + 全链同步 + tag + Release + 市场同步。
