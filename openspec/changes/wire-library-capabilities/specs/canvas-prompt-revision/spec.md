## ADDED Requirements

### Requirement: Revision is reachable from a production entry point
系统 SHALL 通过 `visual_loop_cli.py revise` 暴露修订能力：默认产出完整 generation
block 提案，`--apply` 显式时才写回节点。提案 MUST 完成 gap→VerifiedGap 转换与
fidelity gate 校验；应用 MUST 走 `mutationVersion`/fingerprint 并发守卫与
`updateId` 幂等回执。

#### Scenario: Propose only
- **WHEN** 用户运行 `revise` 且未传 `--apply`
- **THEN** 输出完整 generation block 提案与 changedFields，节点未被修改

#### Scenario: Explicit apply
- **WHEN** 用户传 `--apply` 且 live node 未并发变化
- **THEN** 写回完整 block，持久化 `PromptRevisionReceipt`，返回 receipt 路径

#### Scenario: Concurrent change pauses instead of clobbering
- **WHEN** live node 的 mutationVersion 或 block 指纹已变化
- **THEN** 抛 `ConcurrentChange`，节点保持不变
