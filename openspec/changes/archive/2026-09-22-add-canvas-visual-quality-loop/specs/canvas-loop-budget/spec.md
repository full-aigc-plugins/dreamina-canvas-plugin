## Purpose

约束视觉循环的总费用、单轮支出、轮数、期限和停滞行为，使自动化不会扩大用户授权，也不会在远端结果未知时重复付费。

## ADDED Requirements

### Requirement: Every paid round remains bounded by current evidence
每个付费轮次 SHALL 使用实时报价，并在提交前验证单轮上限、剩余总预算、授权范围和短期审批凭证；控制器级整批预算不得被解释为可复用的供应商审批 Token。

#### Scenario: Per-round approval succeeds
- **WHEN** 最新报价不超过单轮及总预算且当前审批与请求匹配
- **THEN** 系统预留报价最大金额并允许使用一个稳定 `submitId` 提交

#### Scenario: Batch allowance exists but provider approval is absent
- **WHEN** 会话具有 `bounded_batch` 策略但当前 CLI 仍要求新的短期审批凭证
- **THEN** 系统停在 `AWAITING_APPROVAL`，不得仅凭整批策略提交

### Requirement: Budget accounting is conservative under uncertainty
系统 SHALL 分别记录已消费、已预留和结果未知金额；任务被远端接受但费用未最终确认时 MUST 保留预留，不得假定本地超时、停止或失败会退款。

#### Scenario: Accepted operation times out locally
- **WHEN** 远端已接受任务但本地等待超时
- **THEN** 对应金额保持 `reserved` 或 `unknown`，恢复流程继续查询且禁止重复提交

#### Scenario: New quote exceeds remaining budget
- **WHEN** 最新报价超过单轮上限或可用总预算
- **THEN** 系统进入 `PAUSED` 并输出超限证据，不签发或请求执行

### Requirement: Loop policy enforces finite execution and stall detection
循环策略 MUST 定义最大轮数、最低退出分数、截止时间和停滞阈值；连续轮次未改善、主要差距重复或重规划次数达到阈值时 SHALL 进入 `STALLED` 或 `PAUSED`。

#### Scenario: Score fails to improve
- **WHEN** 连续指定轮数的总分或关键分项改善低于阈值
- **THEN** 系统停止自动推进，记录停滞原因并请求人工决策

#### Scenario: Maximum rounds reached
- **WHEN** 当前轮达到授权最大轮数且未满足退出条件
- **THEN** 系统终止后续轮次并保留最佳候选及未满足差距

### Requirement: Automatic next-round execution requires an explicit bounded policy
只有当用户明确授权 `bounded_batch` 且运行时能为每轮提供有效审批时，系统 MAY 自动进入下一轮；默认 `per_round` 模式 SHALL 在每轮 Judge 后暂停。

#### Scenario: Default policy completes one round
- **WHEN** 未提供明确整批授权
- **THEN** 系统在 Judge 或 Revision 提案后暂停，不自动修改、报价或提交

