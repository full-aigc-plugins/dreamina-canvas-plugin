# canvas-prompt-revision Specification

## Purpose
定义由 Judge 差距驱动的安全生成修订，使下一轮草稿完整保留引用和生成参数，并能抵抗并发修改、重复调用与结果不明确。
## Requirements
### Requirement: Revision rebuilds the complete generation block
系统 SHALL 在修订前读取最新节点，并 SHALL 从该节点的完整 generation block 与已验证 Judge 差距生成完整替换值；修订 MUST 显式保留或有意修改模型、模式、比例、分辨率、数量、时长、引用和其他生成字段。

#### Scenario: Image prompt is revised
- **WHEN** JudgeReceipt 指出构图和材质差距且节点版本仍匹配
- **THEN** 系统产生包含全部生成字段的新 generation block，而不是只发送 prompt 局部补丁

#### Scenario: Reference would be dropped
- **WHEN** 修订结果缺少原节点仍应保留的 `res:` 或 `node:` 引用
- **THEN** 系统拒绝更新并报告 generation block 不完整

### Requirement: Revision is concurrency-safe and idempotent
每次修订 SHALL 绑定基础 `mutationVersion`、基础 generation fingerprint、JudgeReceipt ID 和稳定 `updateId`；节点在读取后发生变化时 MUST 暂停并重新规划，不得覆盖他人修改。

#### Scenario: Node changed concurrently
- **WHEN** 提交修订前节点 `mutationVersion` 或 fingerprint 已改变
- **THEN** 系统拒绝旧修订并要求基于新节点重新生成提案

#### Scenario: Update response is ambiguous
- **WHEN** 修订调用超时且无法确认写入结果
- **THEN** 系统使用同一 `updateId` 查询或安全恢复，不生成新的重复更新

### Requirement: Revision evidence is auditable without leaking judge internals
系统 SHALL 保存基础与结果 generation fingerprint、变更字段、JudgeReceipt 引用和更新结果；Prompt Revision 输入 SHALL 只使用经验证的差距与约束，不得把隐藏推理或敏感认证材料写入节点。

#### Scenario: Revision receipt is persisted
- **WHEN** 修订成功或形成可审查提案
- **THEN** 非敏感回执足以证明修改依据和字段范围，但不包含审批 Token 或 Judge 隐藏推理

