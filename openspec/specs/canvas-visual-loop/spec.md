# canvas-visual-loop Specification

## Purpose
定义可持久化和恢复的视觉生成单轮闭环，使上传、草稿、付费执行、下载和评估不会依赖聊天上下文或人工记忆进行串联。
## Requirements
### Requirement: The first delivery executes exactly one bounded round
系统 SHALL 支持一次“目标锁定或注册、保存草稿、报价、审批、提交、恢复等待、下载、校验、Judge”的完整单轮，并 SHALL 在 `JUDGED`、`REVISION_PROPOSED` 或终止状态停止，不自动提交下一轮。

#### Scenario: Single round succeeds
- **WHEN** 目标、报价、审批、远端操作、产物和 Judge 均有效
- **THEN** 系统写入相互可关联的 Target、Round、Operation、Artifact 和 Judge 回执，并停止在本轮决策结果

#### Scenario: Judge recommends another iteration
- **WHEN** JudgeReceipt 未达到退出阈值且给出可执行差距
- **THEN** 系统生成 Revision 提案并进入 `REVISION_PROPOSED`，不得自动报价或提交下一轮

### Requirement: Loop state transitions are explicit and durable
系统 SHALL 持久化状态、当前轮、最佳轮、待处理远端操作、停止标记和回执引用；未在状态表中声明的迁移 MUST 被拒绝。

#### Scenario: Process restarts while a remote task is pending
- **WHEN** 进程在 `SUBMITTED` 或 `WAITING` 后重启
- **THEN** 系统从持久化 `submitId` 恢复查询，不得以新 `submitId` 再次提交

#### Scenario: State file is incomplete or corrupt
- **WHEN** 状态文件无法通过 schema 或回执引用校验
- **THEN** 系统进入可诊断失败状态并禁止付费写入，直到人工修复或从有效回执恢复

### Requirement: Stop does not overclaim remote cancellation
系统 SHALL 将停止建模为 `STOP_REQUESTED`、`DRAINING_ACCEPTED` 和 `STOPPED`；除非运行时提供并验证取消能力，否则停止 SHALL 仅阻止后续编辑和提交，并继续追踪已接受任务。

#### Scenario: Stop is requested before submission
- **WHEN** 会话尚未远端接受且收到停止请求
- **THEN** 系统禁止后续写入并直接进入 `STOPPED`

#### Scenario: Stop is requested after acceptance
- **WHEN** 远端已接受任务且收到停止请求
- **THEN** 系统进入 `DRAINING_ACCEPTED`，持续恢复任务和费用状态，但不得发起新轮次

### Requirement: Receipts exclude secrets and preserve correlation
所有持久化回执 MUST 通过 schema 校验并携带会话、目标、轮次和请求关联标识，且 MUST 排除审批 Token、Cookie、签名 URL、访问密钥和其他认证材料。

#### Scenario: Secret-like field is offered for persistence
- **WHEN** 待写入回执包含被禁止的认证字段或值类型
- **THEN** 系统拒绝持久化并报告安全校验失败

