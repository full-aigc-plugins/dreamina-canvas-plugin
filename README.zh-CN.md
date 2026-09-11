# Codex Dreamina Canvas 插件

> 面向 Dreamina Canvas CLI 编排的 Codex 插件，目前处于设计阶段。

[English](README.md) | [简体中文](README.zh-CN.md)

## 状态与定位

当前仓库只有文档和可检查计划。`codex-dreamina-canvas` 将编排用户已安装的 `dreamina-canvas` CLI，覆盖画布、节点、时间轴、模型/音色发现、报价、积分批准、异步恢复和产物下载。

```text
Codex -> 发现能力 -> 规划画布/节点 -> 保存（不扣费）
      -> 报价 -> 用户明确批准 -> 运行 -> 查询 -> 下载
```

## 不可变边界

- 运行时发现模型、音色、比例和分辨率，不写死目录值。
- 保存节点与运行生成是两个独立动作。
- 产生费用的执行必须重新报价并获得明确批准。
- 超时不代表可重新提交，必须先按稳定 operation 标识查询。
- 未经用户授权，不安装 CLI、不发起登录。

## 文档

- [Architecture](docs/Codex-Dreamina-Canvas-Plugin-Architecture.md) / [中文](docs/Codex-Dreamina-Canvas-Plugin-Architecture.zh_CN.md)
- [Technical solution](docs/Codex-Dreamina-Canvas-Plugin-Technical-Solution.md) / [中文](docs/Codex-Dreamina-Canvas-Plugin-Technical-Solution.zh_CN.md)
- [设计规格](docs/superpowers/specs/2026-09-11-codex-dreamina-canvas-plugin-design.md)
- [实施计划](docs/superpowers/plans/2026-09-11-codex-dreamina-canvas-plugin-implementation.md)

## 证据

目标行为来自 2026-09-11 查阅的 Dreamina Canvas CLI 指南；仓库尚未验证实际 CLI 版本和命令兼容性。
