## Purpose

统一 Canvas 插件与 `dreamina-canvas` CLI 1.0.0 的资源上传、引用和导入行为，避免 Harness 继续依赖未经验证的本地 URI 或过期技能说明。

## ADDED Requirements

### Requirement: Local targets use the supported resource upload contract
当目标素材需要参与 Canvas 生成时，系统 SHALL 通过当前 CLI schema 公开的 `resource upload` 能力上传文件，并 SHALL 使用稳定 UUID 作为资源幂等标识；成功后 SHALL 仅以返回或确认的 `res:<uuid>` 参与生成引用。

#### Scenario: Local image becomes a Canvas reference
- **WHEN** 操作者选择 `canvas_reference` 模式并提供授权目录中的本地图片
- **THEN** 系统以稳定资源标识上传一次，并在后续草稿中使用对应 `res:<uuid>`

#### Scenario: Upload result is ambiguous
- **WHEN** 上传调用超时或退出结果不能证明资源是否已创建
- **THEN** 系统以同一资源标识查询或重试，且不得生成新的资源标识造成重复上传

### Requirement: Reference support follows live CLI capability evidence
系统 MUST 将 CLI 的实时 schema 或经过版本锁定的等价 schema 作为引用能力事实源，并 MUST 拒绝把未被当前运行时接受的 `uri:`、`vid:` 或 `file://` 形式写成可用能力。

#### Scenario: Skill documentation disagrees with live schema
- **WHEN** 受管技能文档与 CLI 1.0.0 的实时 schema 对同一引用类型描述不一致
- **THEN** 验证流程失败并要求先更新上游技能契约，插件不得静默猜测

### Requirement: Managed resource skills are updated only from an immutable release
涉及资源上传和引用的受管技能 SHALL 先在上游技能仓完成测试并发布不可变 tag；Canvas 插件 SHALL 通过 tag、peeled SHA 和内容摘要更新锁文件，不得直接修改 vendored 副本。

#### Scenario: Upstream resource contract is ready
- **WHEN** 上游发布包含 `resource upload`、`res:` 和 `uri/vid` 当前边界的正式版本
- **THEN** Canvas 同步工具验证 tag、SHA 和摘要后更新受管技能

#### Scenario: Only a working-tree edit exists upstream
- **WHEN** 资源契约仅存在于上游未发布提交或本地修改中
- **THEN** Canvas 发布门禁拒绝更新锁文件或宣称新契约已交付

