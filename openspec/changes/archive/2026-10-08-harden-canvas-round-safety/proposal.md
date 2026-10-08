## Why

审批、持久化预算和提交恢复未形成完整保护，上传器与真实适配器组合存在接口错误。重启和网络异常会放大这些缺口，因此必须先修复并验证单轮基础行为，再推进后续自动化。

## What Changes

- 修复已确认缺陷并增加可观察行为回归。
- 保持现有单轮、人工审批和默认兼容性边界。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `canvas-visual-loop`: 完善既有契约与失败路径。

## Impact

控制器/适配器/文档与本地测试；不新增外部调用授权，不启用多轮自动化。
