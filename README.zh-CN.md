# Codex Dreamina Canvas 插件

<img src="assets/logo.png" alt="Dreamina Canvas Logo" width="128">

> 面向 Dreamina Canvas CLI 编排的 Codex 兼容基础。

[English](README.md) | [简体中文](README.zh-CN.md)

## 状态与定位

当前仓库包含经过验证的兼容 manifest、Marketplace 元数据、品牌资产、Legal 文档，以及 Canvas 实现：13 个 Agent Skill、严格 CLI 适配器、操作台账，以及审批与产物守卫。

## 许可证

Apache-2.0，见 [LICENSE](LICENSE)。

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
- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)
- [生产就绪证据](docs/verification/production-readiness.md)
- [真实环境验收](docs/verification/real-environment-acceptance-2026-09-13.md)

## 开发验证

使用 Python 3.11+ 创建隔离环境，安装 `requirements-dev.txt`，然后执行
[CONTRIBUTING.md](CONTRIBUTING.md) 中的离线门禁。CI 会在 Python 3.11、3.12、
3.13 上重复相同的无扣费检查。

## 证据

目标行为来自 2026-09-11 查阅的 Dreamina Canvas CLI 指南。CLI 运行期、版本、命令兼容性、经明确授权的账号认证，以及单独批准的付费金丝雀均在[运行期证据](docs/verification/dreamina-canvas-runtime.md)中记录为 **PASS**。常规 CI 仍保持离线、无认证、无扣费。
