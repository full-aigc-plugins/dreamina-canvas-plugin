## Source and ownership

受管技能只能通过 `scripts/vendor/skill_vendor.py update --source-ref dreamina-skills=v1.7.2 --expected-sha ...` 获取，`upstream/dreamina-skills.lock.json` 从同一已发布提交生成；插件不直接改受管技能。CLI 操作仍由当前运行时 schema 决定。

## Adapter compatibility

`run_dreamina_canvas` 保留原始退出码和错误对象。失败 envelope 优先从顶层读取字典类型 `partialData`；旧版只在 `error.partialData` 提供时回退读取。无效类型继续按无部分结果处理，不推测提交是否失败。既有错误路由和提交身份不改变。

## Release

功能扩展按插件仓 AGENTS.md 使用 minor 版本，并同步市场仓 catalog 与生成清单。仅在全量本地检查和 CI 满足时发布。
