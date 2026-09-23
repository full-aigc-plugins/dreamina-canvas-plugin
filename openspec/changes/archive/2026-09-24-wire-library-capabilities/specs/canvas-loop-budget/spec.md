## ADDED Requirements

### Requirement: The controller uses one budget ledger
系统 SHALL 让 `VisualLoopController` 消费 `budget.py` 的 `BudgetLedger` 与
`PerRoundPolicy | BoundedBatchPolicy` 与 `ExitGovernor`：报价通过即 `reserve`，
仅已验证终态 `settle`（completed 记 spent、failed 释放、timeout/unknown 转
unknown 持续占额），单轮决策 MUST 由 `ExitGovernor.observe` 产出。

#### Scenario: Quote reservation
- **WHEN** 报价通过 policy 校验
- **THEN** 立即 reserve，PAUSE 判定与决策均走 budget.py 语义

#### Scenario: Decision comes from the governor
- **WHEN** Judge 回执导入后
- **THEN** 决策 completed / revision_proposed / stalled 由 `ExitGovernor` 产出
