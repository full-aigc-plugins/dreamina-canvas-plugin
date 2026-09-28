---
description: 画布鉴权：检查、刷新与恢复 Dreamina Canvas 登录态
argument-hint: "[要处理的项：check|refresh|recover]"
---

按 `dreamina-canvas-auth` 技能处理画布鉴权：

1. **check**：区分本地登录态与服务器侧状态，报告当前可用性。
2. **refresh**：令牌过期/失效时按技能指引刷新。
3. **recover**：仍不可用则走恢复流程（重新登录），完成后复检。

鉴权通过后可直接使用 `/dreamina-canvas-create` 等画布命令。
