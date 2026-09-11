# Codex Dreamina Canvas 插件技术方案

## 技术决策

通过严格 argv 适配器封装已安装 CLI。只解析 JSON 模式，统一退出码和 `requiredAction`，并在插件数据目录保存最小操作台账。

## 目标目录

```text
.codex-plugin/plugin.json
skills/codex-dreamina-canvas-*/
scripts/canvas_adapter.py
scripts/approval_guard.py
schemas/
tests/
```

## 契约

`CapabilitySnapshot` 记录 CLI 版本、schema 哈希和实时目录；`QuoteReceipt` 绑定请求指纹、金额、单位和有效期；`OperationReceipt` 保存非敏感 submit/operation ID 与状态；`ArtifactReceipt` 保存批准路径和校验和。

## 错误模型

统一为 `CLI_NOT_FOUND`、`AUTH_REQUIRED`、`UPGRADE_REQUIRED`、`INVALID_REFERENCE`、`QUOTE_REQUIRED`、`APPROVAL_REQUIRED`、`APPROVAL_STALE`、`SUBMISSION_UNKNOWN`、`REMOTE_FAILED`、`DOWNLOAD_FAILED`。保留原始退出码作为证据，但不暴露敏感内容。

## 测试策略

使用合成 JSON fixture 覆盖每个状态和退出码，只替换 subprocess 边界，不 mock 解析器和批准门禁。运行冒烟仅执行只读 help/schema/account；付费生成必须单独明确批准。
