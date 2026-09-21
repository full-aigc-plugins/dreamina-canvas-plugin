# canvas-visual-target Specification

## Purpose
定义视觉目标素材在循环中的身份、完整性、授权目录和导入模式，使每次生成与评估都能证明使用的是同一个不可变目标。
## Requirements
### Requirement: A visual target is locked by content identity
系统 SHALL 为目标素材生成包含稳定目标 ID、SHA-256、字节数、媒体类型、尺寸、来源和锁定时间的结构化回执；已开始的会话 SHALL 通过内容摘要而不是可变路径识别目标。

#### Scenario: Target is accepted
- **WHEN** 文件位于授权目录、可读且媒体类型受支持
- **THEN** 系统写入非敏感 `VisualTargetReceipt` 并把目标状态推进到 `TARGET_LOCKED`

#### Scenario: Target content changes after locking
- **WHEN** 同一路径的当前 SHA-256 与已锁定回执不一致
- **THEN** 系统拒绝继续本轮，并要求创建新目标版本或显式重新锁定

### Requirement: Target ingestion mode is explicit
每个目标 SHALL 明确选择 `judge_only` 或 `canvas_reference`；`judge_only` SHALL 禁止远端上传，`canvas_reference` SHALL 保存已确认的 Canvas 资源标识。

#### Scenario: Judge-only target is evaluated
- **WHEN** 目标模式为 `judge_only`
- **THEN** 系统允许其进入 JudgeRequest，但不得把该文件上传或写入生成引用

#### Scenario: Canvas-reference target is registered
- **WHEN** 目标模式为 `canvas_reference` 且上传已确认
- **THEN** 目标回执记录 Canvas `resourceId`、导入类型和上传证据摘要

### Requirement: Latest candidate tracking is cross-platform and recoverable
系统 MUST 使用不可变轮次产物和原子更新的指针文件追踪最新候选，不得要求文件系统软链接才能工作。

#### Scenario: Latest candidate is updated on Windows
- **WHEN** 新候选产物通过完整性校验并成为最新候选
- **THEN** 系统原子更新 `latest.json` 或等价指针，且不创建需要额外权限的软链接

