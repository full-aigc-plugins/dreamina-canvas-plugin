## ADDED Requirements

### Requirement: Visual loop release depends on a released CLI resource contract
Visual Loop 的发布候选 MUST 锁定一个已经正式发布、与 `dreamina-canvas` CLI 1.0.0 资源 schema 一致的上游技能版本；验证 MUST 覆盖 release tag、peeled commit SHA、内容摘要和受管技能行为契约。

#### Scenario: Visual loop candidate uses a valid upstream release
- **WHEN** Canvas 插件准备发布包含目标上传和资源引用的 RC
- **THEN** 锁文件指向已发布上游 tag，其 peeled SHA 与摘要匹配，资源契约测试通过

#### Scenario: Vendored skill was patched locally
- **WHEN** 受管 Canvas 技能内容与锁文件摘要不一致或仅在插件仓被直接修改
- **THEN** 发布验证失败，并要求回到上游技能仓发布新版本后重新同步

### Requirement: Release evidence covers clean installation on every declared host
Visual Loop 发布证据 MUST 来自与 tag 相同提交构建的插件，并 SHALL 在 Codex、Claude Code、ZCode 和 Kimi 的全新安装或等价隔离环境中验证技能发现、JudgePort 契约和版本身份；仅源码测试或 Git push 不构成市场发布证明。

#### Scenario: Cross-host RC is ready
- **WHEN** 四个宿主的隔离安装均加载相同插件版本并通过 JudgePort 黄金样本
- **THEN** 发布记录可以将插件 tag、上游技能 tag、市场清单版本和测试证据关联到同一 RC

