## ADDED Requirements

### Requirement: Canvas 1.3.0 skill release is vendored immutably

插件 MUST 从正式发布的 dreamina-skills v1.7.2 tag 及其 peeled commit SHA 同步十个受管技能，两个锁文件 MUST 记录同一提交且本地内容摘要通过校验。

#### Scenario: New workflow skill is packaged

- **WHEN** 插件安装包包含 Canvas CLI 1.3.0 工作流和模板参考
- **THEN** 这些文件与上游 v1.7.2 内容逐字节一致，且插件独有 harness 技能保持不变

### Requirement: CLI v2 recoverable details survive adapter parsing

插件适配器 MUST 从 CLI v2 错误 envelope 的顶层 `partialData` 保留可恢复身份，同时兼容旧版 `error.partialData`。适配器 MUST 保留原退出码，不将部分结果解释为最终成功。

#### Scenario: CLI reports confirmation needed after saving a draft

- **WHEN** CLI 以退出码 10 返回顶层 `partialData.items`，含原 nodeId 和 submitId
- **THEN** 适配器将这些身份交给调用方继续原任务，不丢失也不生成新身份
