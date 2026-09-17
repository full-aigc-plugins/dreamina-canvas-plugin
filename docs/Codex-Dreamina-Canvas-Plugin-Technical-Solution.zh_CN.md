# Codex Dreamina Canvas 插件技术方案

> **文档信息**
>
> | 字段 | 值 |
> |---|---|
> | 状态 | 已实现，以 `0.1.2` 发布 |
> | 范围 | 本仓库如何集成 Dreamina Canvas CLI，以及如何验证该集成 |
> | 读者 | 扩展或评审本插件的实现者 |
> | 运行证据 | `docs/verification/` |

## 1. 技术决策

通过严格 argv 适配器封装已安装 CLI。只解析 JSON 模式，统一退出码和 `requiredAction`，并在插件数据目录保存最小操作台账。

### 备选方案

| 备选方案 | 被否的原因 |
|---|---|
| 直接调用远端服务 | 会重复实现 CLI 已经拥有的认证、权益与定价逻辑 |
| 通过命令字符串调用 shell | 引入注入风险，且参数无法审计 |
| 把目录值缓存到源码 | 值会随时变化，缓存会悄悄误导用户 |
| 把"保存"与"运行"合并为一条命令 | 会让意外花费无法复核 |
| 超时后自动重试付费运行 | 把一次付费动作变成两次，且无法证明哪次成功 |

## 2. 仓库布局

```text
.codex-plugin/plugin.json
plugin.json
skills/dreamina-canvas-*/
scripts/dreamina_canvas_adapter.py
scripts/approval_guard.py
scripts/artifact_guard.py
scripts/error_router.py
scripts/operation_ledger.py
tests/
upstream/dreamina-skills.lock.json
```

| 路径 | 职责 |
|---|---|
| `scripts/dreamina_canvas_adapter.py` | 仅用 argv 调用 CLI、解析 JSON、给出带类型的适配器错误 |
| `scripts/approval_guard.py` | 报价绑定、额度上限强制、拒绝重放 |
| `scripts/operation_ledger.py` | 以 `submitId` 为键的非敏感操作回执 |
| `scripts/artifact_guard.py` | 下载的字节数与 SHA-256 校验 |
| `scripts/error_router.py` | 退出码到下一步动作的映射 |
| `tests/` | 单元测试与 `tests/scenarios/` 集成式测试 |

## 3. 契约

`CapabilitySnapshot` 记录 CLI 版本、schema 哈希和实时目录；`QuoteReceipt` 绑定请求指纹、金额、单位和有效期；`OperationReceipt` 保存非敏感 submit/operation ID 与状态；`ArtifactReceipt` 保存批准路径和校验和。

| 契约 | 必填字段 | 不变量 |
|---|---|---|
| `CapabilitySnapshot` | CLI 版本、schema 哈希、实时目录 | 绝不作为权威持久化；每次运行重新读取 |
| `QuoteReceipt` | 请求指纹、金额、单位、有效期 | 批准仅对其创建时对应的指纹有效 |
| `OperationReceipt` | `submitId`、请求指纹、最后已知状态 | 不含任何形似凭据的字段 |
| `ArtifactReceipt` | 已批准目标位置、字节数、SHA-256 | 不匹配是硬失败，不是告警 |

## 4. 配置与状态

| 设置 | 位置 | 说明 |
|---|---|---|
| CLI 可执行文件 | `PATH` 上的 `dreamina-canvas` | 受控部署可在适配器中覆盖 |
| 操作台账 | `<root>/operations/<profile-and-environment>/<submitId>.json` | 权限 `0600`；仅非敏感字段 |
| 认证 | CLI 自己的存储 | 本仓库从不读写 |
| 额度上限 | 随每次批准提供 | 低于最新权威总计的上限会被拒绝 |

## 5. 错误模型

把 CLI 的退出码统一为带类型的动作，使任何调用方都不必解析人类可读消息。

| 退出码 | 路由动作 | 含义 |
|---|---|---|
| `0` | `continue` | 成功 |
| `1` | `alert` | 未归类的内部失败 |
| `2` | `fix_and_retry` | 命令、参数或 schema 非法 |
| `10` | `approval_pause` | 需要结构化的额度批准 |
| `11` | `reauth_and_retry` | 需要登录或会话已过期 |
| `12` | `escalate` | 权限、能力或权益被拒绝 |
| `13` | `upgrade_cli` | 环境或版本兼容性受阻 |
| `20` | `resume_operation` | 操作可恢复但尚未收敛 |
| `21` | `bounded_backoff_retry` | 可重试的服务或传输故障 |
| `22` | `hand_to_human` | 需要人工介入 |

适配器层面的 `requiredAction` 取值为 `none`、`login`、`confirm`、`retry`、`resume`、`upgrade`、`human_intervention` 与 `contact_support`。原始数字退出码作为证据保留，但绝不暴露敏感内容。

## 6. 状态机映射

| 状态 | 写入方 | 触发条件 |
|---|---|---|
| Draft | 台账 | 画布已编排但未提交 |
| Saved | 台账 | 免费保存成功 |
| Quoted | 批准守卫 | 针对确切节点集合取得报价 |
| Approved | 批准守卫 | 用户批准该报价 |
| Submitted | 台账 | 单次运行开始，且 `submitId` 已持久化 |
| Querying | 台账 | 轮询观察到非终态 |
| Completed | 台账 | 终态成功 |
| Failed | 台账 | 终态失败 |
| Unknown | 台账 | 超时或传输结果含糊 |

`Unknown` 绝不自动迁移到 `Submitted`。恢复始终查询已有的 `submitId`。

## 7. 测试策略

使用合成 JSON fixture 覆盖每个状态和退出码，只替换 subprocess 边界，不 mock 解析器和批准门禁。运行冒烟仅执行只读 help/schema/account；付费生成必须单独明确批准。

| 层次 | 证明什么 | 命令 |
|---|---|---|
| 单元 | 解析器、守卫、台账与路由的行为 | `python -m unittest discover -s tests -v` |
| 场景 | 多步流程与状态迁移 | `python -m unittest discover -s tests/scenarios -v` |
| Skill 一致性 | 打包的 Skill 与上游锁文件一致 | `python scripts/verify_dreamina_canvas_skills.py` |
| 分发 | 清单、引用与必需文件 | `python scripts/validate_distribution.py` |
| 运行期 | CLI 版本、命令兼容性、经授权的认证 | `docs/verification/dreamina-canvas-runtime.md` |

## 8. 兼容性与上线

| 方面 | 立场 |
|---|---|
| Python | CI 矩阵覆盖 3.11、3.12 与 3.13 |
| 上游 Skill | 按提交固定，并与 `upstream/dreamina-skills.lock.json` 逐字节校验 |
| 升级路径 | 退出码 `13` 路由到明确的 CLI 升级动作，而不是静默失败 |
| 回滚 | 恢复上一个固定提交并重装；操作回执因格式可追加而仍可读 |

## 9. 证据映射

| 断言 | 证据 |
|---|---|
| 适配器边界 | `scripts/dreamina_canvas_adapter.py` |
| 批准绑定 | `scripts/approval_guard.py` 及其测试 |
| 台账字段 | `scripts/operation_ledger.py` 及其测试 |
| 下载校验 | `scripts/artifact_guard.py` 及其测试 |
| 真实环境验收 | `docs/verification/real-environment-acceptance-2026-09-13.md` |
