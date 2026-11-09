## Why

插件当前锁定 dreamina-skills v1.7.0，缺少 Canvas CLI 1.3.0 的工作流与模板技能。CLI 1.3.0 的错误 envelope 升至 schemaVersion 2，并将可恢复的 `partialData` 放在顶层；现有适配器只读取嵌套字段。

## What Changes

- 从已发布的 dreamina-skills v1.7.2、peeled SHA 和摘要同步十个受管技能及两份锁文件。
- 兼容解析 CLI schemaVersion 2 顶层 `partialData`，保留旧版嵌套形态。
- 更新插件版本与市场元数据，运行分发和回归检查。
