# immutable-skill-supply-chain Specification

## Purpose
确保插件安装的外部技能只来自不可变且可验证的正式发布，并通过 release tag、peeled commit SHA、内容摘要和本地技能清单建立可审计的供应链；同时允许少量明确声明的插件专属技能安全共存，而不被外部同步覆盖。
## Requirements
### Requirement: External skills are immutable and verifiable
插件 MUST 以 release tag、peeled commit SHA 和内容摘要锁定每个受管技能，检查命令 MUST 在 ref 移动、内容篡改、技能缺失或摘要不一致时失败。

#### Scenario: Managed skill content is unchanged
- **WHEN** 对已同步插件运行在线或离线完整性检查
- **THEN** 所有受管技能的来源、提交和内容摘要均与锁文件一致

#### Scenario: Managed content is tampered
- **WHEN** 已锁定的受管技能文件被修改、删除或其 tag 指向不同提交
- **THEN** 完整性检查以非零状态失败且不静默重写锁文件

### Requirement: Plugin-local skills are explicit
插件 MUST 通过声明式清单列出插件专属技能，vendor 更新 MUST 保留已声明的本地技能并拒绝未声明的额外技能目录。

#### Scenario: Declared plugin-local skill exists
- **WHEN** vendor 更新受管技能
- **THEN** 已声明的插件专属技能保持不变并继续被三端发现

#### Scenario: Undeclared skill appears
- **WHEN** `skills/` 中出现既不受锁管理也未列入本地清单的目录
- **THEN** 更新或检查命令失败并指出该目录

### Requirement: Upgrade events identify exact source state
技能升级事件 MUST 携带 release tag 和 peeled commit SHA，插件同步流程 MUST 校验二者与锁定来源匹配后才可更新并创建升级变更。

#### Scenario: Valid release event arrives
- **WHEN** 受信任的技能源发布新 release 并提供匹配的 tag 与 commit
- **THEN** 插件生成只包含预期技能、锁文件和版本更新的可审查升级变更

#### Scenario: Event commit does not match tag
- **WHEN** 事件中的 commit 与远端 tag 的 peeled SHA 不一致
- **THEN** 同步流程失败且不修改插件技能或锁文件

### Requirement: Release surfaces remain consistent
发布前验证 MUST 确认 Codex、ZCode、Kimi manifest、市场版本、插件 tag 和测试结果属于同一发布。

#### Scenario: Release candidate is consistent
- **WHEN** 发布候选通过分发检查
- **THEN** 三端 manifest 版本一致，受管技能检查通过，插件 tag 与 GitHub Release 可对应到同一 commit

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

