## ADDED Requirements

### Requirement: Judge adapters are reachable through a dispatch entry
系统 SHALL 通过 `visual_loop_cli.py judge --adapter {human,host-subagent,
design-skill,external-mcp}` 分派评审：`human` 停等 `import-judge`；其余以
shell-callable 桥接（request JSON stdin → verdict JSON stdout），产出 MUST 经
`judge_exchange.import_judge_receipt` 校验（摘要绑定、fresh-context、拒秘密、
一 request 一 receipt）后方可被控制器消费。`Judge absence never produces a
fabricated score` 继续成立：无 `--cmd` 时返回能力不可用，不产生分数。

#### Scenario: External adapter round trip
- **WHEN** 用户以 `--adapter external-mcp --cmd <command>` 触发
- **THEN** 请求经桥发出，verdict 校验通过后 receipt 落盘并自动 import

#### Scenario: Human adapter parks
- **WHEN** `--adapter human`
- **THEN** 只落 JudgeRequest 并返回 import-judge 指引，不产生分数

#### Scenario: Bad verdict is rejected at the boundary
- **WHEN** 桥返回缺分项 / 含秘密字段 / 摘要不符的 verdict
- **THEN** `judge_exchange` 拒绝，零写入，`judge` 子命令返回失败
