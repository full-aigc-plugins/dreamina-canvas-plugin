# canvas-judge-port Specification

## Purpose
定义宿主无关的视觉评估请求和回执，使不同客户端或人工评估器可以在隔离上下文中产生同一份可验证、可恢复的质量证据。
## Requirements
### Requirement: Judge receives only evaluation-relevant evidence
JudgeRequest SHALL 包含目标与候选的内容身份、可访问素材、媒体类型、rubric 版本和评估约束；默认 MUST 排除生成 Prompt、模型选择、历史评分和预期结论。

#### Scenario: Fresh-context image judge starts
- **WHEN** 单轮候选已通过产物校验
- **THEN** 系统发出不含生成历史的 JudgeRequest，并要求 Judge 声明 `freshContext=true` 和 `sawPromptDraft=false`

### Requirement: JudgeReceipt is structured and bound to exact media
JudgeReceipt SHALL 记录 Judge 适配器、模型或人工身份类别、目标与候选摘要、rubric 版本、分项分数、主要差距、建议动作、时间和有效性，且 MUST 与请求中的目标及候选内容身份完全匹配。

#### Scenario: Valid judge result is returned
- **WHEN** JudgeReceipt schema 有效且目标、候选摘要与请求匹配
- **THEN** 系统接受结果、保存非敏感回执并推进到 `JUDGED`

#### Scenario: Judge evaluates a different candidate
- **WHEN** JudgeReceipt 中的候选摘要与当前请求不一致
- **THEN** 系统拒绝结果并保持 `AWAITING_JUDGE`

### Requirement: Judge absence never produces a fabricated score
系统 SHALL 支持宿主子智能体、兄弟技能、外部 MCP 和人工适配器，但任何适配器不可用或输出无效时 MUST 停在 `AWAITING_JUDGE`，不得生成默认分数或把生成模型的自评当成独立 Judge。

#### Scenario: Current host has no compatible judge
- **WHEN** 当前客户端无法提供满足协议的视觉 Judge
- **THEN** 系统输出待评估请求和恢复说明，不改变质量分数或退出结论

### Requirement: Cross-host acceptance uses one semantic contract
Codex、Claude Code、ZCode 和 Kimi 的适配器 MUST 对同一 JudgeRequest 输出可由同一 schema 校验的 JudgeReceipt；宿主内部调用方式可以不同，但不得改变分数字段、关联语义和敏感数据边界。

#### Scenario: Golden corpus is executed across hosts
- **WHEN** 四个目标宿主分别评估同一组黄金样本
- **THEN** 每个宿主均产生 schema 有效、内容绑定正确且不含秘密的 JudgeReceipt

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

