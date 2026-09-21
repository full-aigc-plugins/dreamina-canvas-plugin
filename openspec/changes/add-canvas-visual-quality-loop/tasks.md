## 1. 基线与事实修正

- [x] 1.1 记录 Canvas 插件、上游 `dreamina-skills`、CLI 1.0.0、市场仓和四宿主当前版本、分支、commit、tag、锁文件及工作树状态，保护现有未发布提交。
- [x] 1.2 为 Harness 中“自动镜像、自动刷新 latest、自动 Judge、本地 URI 可用”的声明编写会失败的文档契约测试或静态校验。
- [x] 1.3 修改插件专属 Harness，将尚未实现的自动能力标为计划/不可用，并把第一阶段行为明确为“单轮 Judge 后暂停”。
- [x] 1.4 在 README 和架构文档中区分计划、Fake CLI 验证、真实 CLI 只读验证、真实上传和付费 Canary，防止把文档接缝表述为生产能力。
- [x] 1.5 运行现有单元、场景、技能完整性和分发验证，保存变更前基线，不修复无关失败。

## 2. 上游 CLI 1.0.0 技能契约

- [x] 2.1 在 `dreamina-skills` 为 `resource upload`、`--file`/`--source-url`、`--type`、`--project-id`、稳定 `--resource-id`、`--name` 和 `--import-kind` 增加契约测试。
- [x] 2.2 更新上游 Canvas CLI/图像/视频/下载相关技能，准确描述 `resource upload`、`res:<uuid>`、资源导入以及 `uri:`/`vid:` 的当前运行时边界。
- [x] 2.3 增加 live-schema 兼容检查，证明受管技能声明与 `dreamina-canvas 1.0.0 schema` 一致；不执行上传或付费写入。
- [x] 2.4 运行上游 TRACE、链接、技能结构和相关回归测试，修复契约或交叉 Skill 引用问题。
- [x] 2.5 bump 上游技能版本，提交并推送不可变 tag，等待远端 CI 和 release 资产验证；在完成前不得修改 Canvas 锁文件。
- [x] 2.6 使用正式 tag、peeled SHA 和内容摘要更新 Canvas `skills.lock.json` 及受管技能，并运行离线/在线完整性验证，禁止手改 vendored 文件。

## 3. Schema 与安全回执

- [x] 3.1 先为 Target、Round、JudgeRequest、JudgeReceipt、Budget、Loop State 和 Prompt Revision 编写 schema 正向/反向测试及 `additionalProperties` 拒绝测试。
- [x] 3.2 新增 `VisualTargetReceipt` schema，覆盖内容摘要、媒体元数据、目标版本、导入模式、资源标识和锁定时间。
- [x] 3.3 新增 `VisualRoundReceipt` schema，关联目标、节点版本、generation fingerprint、报价、非敏感授权元数据、submitId、产物、Judge 和决策。
- [x] 3.4 新增 `JudgeRequest` 与 `JudgeReceipt` schema，强制目标/候选内容绑定、rubric 版本、fresh-context 声明、评分、差距和建议动作。
- [x] 3.5 新增 `LoopBudget`、`VisualLoopState` 与 `PromptRevisionReceipt` schema，覆盖费用状态、停止状态、恢复引用、基础版本和完整替换证据。
- [x] 3.6 扩展秘密字段和敏感值扫描测试，确保审批 Token、Cookie、签名 URL、Secret、访问密钥及隐藏推理不能写入回执。
- [x] 3.7 为所有 schema 添加版本字段和向后兼容策略，并更新分发校验确保 schema 被打包。

## 4. 状态存储与恢复状态机

- [x] 4.1 用表驱动测试定义全部合法和非法状态迁移，包括 CREATED、TARGET_LOCKED、TARGET_REGISTERED、DRAFT_SAVED、QUOTED、AWAITING_APPROVAL、SUBMITTED、WAITING、ARTIFACT_VERIFIED、AWAITING_JUDGE、JUDGED、REVISION_PROPOSED、COMPLETED、PAUSED、STALLED、STOP_REQUESTED、DRAINING_ACCEPTED、STOPPED 和 FAILED。
- [x] 4.2 实现会话级 `LoopStateStore`，使用授权目录、规范路径包含检查、文件锁、临时文件、fsync 和原子替换。
- [x] 4.3 实现不可变轮次目录与原子 `latest.json` 指针，不创建 `latest.png` 软链接。
- [x] 4.4 为每个外部副作用建立“先持久化意图/请求标识，再调用外部系统”的恢复门禁。
- [x] 4.5 增加从每个可中断状态重启的测试，证明 `SUBMITTED`/`WAITING` 只恢复同一 `submitId`，不重复付费提交。
- [x] 4.6 增加损坏、缺失、版本不兼容和回执引用断裂的状态测试，失败时禁止外部写入并输出可操作诊断。
- [x] 4.7 在 macOS/Linux 与 Windows 路径样本上验证原子更新、锁和无软链行为。

## 5. 目标锁定与资源上传

- [x] 5.1 为目标授权目录、媒体探测、SHA-256 锁定、同路径内容变化和目标版本化编写失败优先测试。
- [x] 5.2 实现 `TargetStore` 和 `judge_only` 模式，保证目标不会被远端上传或写入生成引用。
- [x] 5.3 为稳定 `resourceId`、重复调用、超时后查询和已存在资源编写 Fake CLI 场景测试。
- [x] 5.4 实现 `canvas_reference` 上传流程，只通过 CLI 1.0.0 `resource upload` 并保存已确认的 `res:<uuid>`。
- [x] 5.5 增加 live CLI schema 探测与能力缓存失效逻辑；schema 与技能契约不一致时暂停而不是猜测。
- [x] 5.6 使用临时项目完成一次明确授权的真实资源上传 Canary，验证幂等和回执；未获得授权时保持此任务未完成。

## 6. 单轮 VisualLoopController

- [x] 6.1 为完整单轮编写 Fake CLI + Fake JudgePort E2E，使其先因控制器不存在而失败。
- [x] 6.2 定义 `CanvasRuntimePort`、`ApprovalPort`、`OperationLedgerPort`、`ArtifactPort`、`JudgePort`、`PromptRevisionPort`、`BudgetLedger` 和 `ExitPolicy` 的最小接口及测试替身。
- [x] 6.3 实现 `VisualLoopController` 命令入口和机器可解析结果，组合现有 adapter、approval guard、operation ledger、artifact guard 与 error router。
- [x] 6.4 实现目标锁定/注册、live capability/model 探测、saved draft 创建或更新，且草稿阶段不得触发生成。
- [x] 6.5 实现实时报价、预算检查和 `AWAITING_APPROVAL` 暂停，审批凭证仅在内存中传递且不得写盘。
- [x] 6.6 实现提交前稳定 `submitId` 持久化、单次 run、结果不明确时的 operation resume，以及禁止新 submitId 重提。
- [x] 6.7 实现事务下载、临时文件校验、哈希、原子提交、不可变候选归档和 ArtifactReceipt 关联。
- [x] 6.8 实现 JudgeRequest 发出、`AWAITING_JUDGE` 暂停、JudgeReceipt 恢复输入及 `JUDGED`/`REVISION_PROPOSED`/`COMPLETED` 决策。
- [x] 6.9 增加断网、CLI 非 JSON 输出、远端失败、下载损坏、Judge 无效和进程崩溃场景测试。
- [x] 6.10 更新 Harness 路由到真实控制器，并删除或改写任何仍声称依靠人工串联即可获得自动闭环的说明。

## 7. JudgePort 与跨宿主适配

- [x] 7.1 建立图像黄金样本、四维 rubric 和通过/失败期望，确保样本不包含真实账户秘密或付费依赖。
- [x] 7.2 实现 JudgePort 核心验证：只传目标、候选、rubric 和约束，拒绝 Prompt、模型历史或不匹配的内容摘要。
- [x] 7.3 实现 `HostSubagentJudgeAdapter` 的协议层，不在核心控制器中写死任何宿主专属 API。
- [x] 7.4 实现可选 `DreaminaDesignSkillJudgeAdapter` 与 `ExternalMcpJudgeAdapter`，未安装时返回能力不可用而不是破坏 Canvas。
- [x] 7.5 实现 `HumanJudgeAdapter` 和可恢复导入命令，使无视觉模型环境可以停在 `AWAITING_JUDGE` 后人工继续。
- [x] 7.6 为 malformed、错候选、错目标、非 fresh-context、缺分项、含秘密和重复 JudgeReceipt 增加拒绝测试。
- [ ] 7.7 在 Codex、Claude Code、ZCode、Kimi 的隔离安装中运行同一黄金样本，保存 schema、关联、安全和评分容差报告；缺少真实宿主证据时不得勾选。

## 8. Prompt Revision

- [x] 8.1 为完整 generation block 保真建立属性/表驱动测试，覆盖模型、模式、比例、分辨率、数量、时长、`node:`/`res:` 引用和未知保留字段。
- [x] 8.2 实现 live node 读取、`mutationVersion` 与 generation fingerprint 校验，并在并发变化时进入 `PAUSED`。
- [x] 8.3 实现只接受经验证 gap 和用户约束的 Prompt 重写器接口，输出完整 generation block。
- [x] 8.4 实现保真校验和有意变更白名单，任何意外丢失引用或生成字段都拒绝更新。
- [x] 8.5 实现稳定 `updateId`、结果不明确时的状态查询和 `PromptRevisionReceipt` 持久化。
- [x] 8.6 增加重复修订、并发节点变化、无效 Judge、隐藏推理泄露和部分更新回归测试。

## 9. 预算、停滞与终止治理

- [x] 9.1 为 `spent`、`reserved`、`unknown` 和 `available` 编写预算不变量测试，覆盖本地超时不释放预留。
- [x] 9.2 实现默认 `per_round` 策略以及目标、最大轮数、总额度、单轮额度和截止时间绑定的 `bounded_batch` 策略。
- [x] 9.3 确保 `bounded_batch` 不绕过 CLI 的当前短期审批；缺少有效审批时固定停在 `AWAITING_APPROVAL`。
- [x] 9.4 实现最低退出分数、关键分项门禁、连续无改善、重复 gap、重规划次数和最大轮数策略。
- [x] 9.5 实现最佳轮次保留和 `STALLED`/`PAUSED` 诊断，停滞时不得自动扩大预算或改换目标。
- [x] 9.6 实现 `STOP_REQUESTED`、`DRAINING_ACCEPTED`、`STOPPED`，并测试停止后无新编辑、报价、审批或提交。
- [x] 9.7 若未来 CLI 提供取消能力，以独立规格变更接入；当前 UI、Skill 和回执统一使用“停止后续轮次/继续排空”语义。

## 10. 视频关键帧与时序 Judge

- [x] 10.1 在图像单轮、恢复、预算和 JudgePort 门禁全部通过后，再启用本阶段任务。
- [x] 10.2 定义 FrameSamplerPort、视频与关键帧内容绑定回执，以及无 FFmpeg/无视频视觉能力的降级测试。
- [x] 10.3 实现可选 FFmpeg 适配器，记录源视频摘要、时长、帧率、采样策略、时间点和帧摘要。
- [x] 10.4 扩展 JudgeRequest/Receipt 以区分静态关键帧评分与动作连续、闪烁、主体漂移、镜头运动、节奏和音画同步门禁。
- [x] 10.5 建立视频黄金样本并验证“静态帧合格但时序失败”不会被判定为整体通过。
- [x] 10.6 在无法完成时序分析时返回 `MANUAL_REVIEW_REQUIRED`，不得以首帧分数替代完整视频结论。

## 11. 完整验证与发布

- [x] 11.1 运行目标单元测试、全部单元测试、场景测试、schema 验证、OpenSpec strict 验证、技能完整性和分发验证。
- [x] 11.2 运行静态检查、秘密扫描、Markdown/链接检查和 `git diff --check`，审查兼容性、安全、幂等、并发和可维护性。
- [x] 11.3 在全新临时目录安装插件发行包，验证 CLI 发现、Harness 路由、schema 资源、无软链恢复和版本身份。
- [x] 11.4 在用户明确提供账户、凭证和费用上限后执行一次真实付费单轮 Canary；否则记录为发布阻塞项，不虚报完成。
- [x] 11.5 为新功能 bump 到不可变 RC 版本，确保 catalog、四端 manifest、Codex 构建后缀和发布包版本全链一致。
- [x] 11.6 提交并推送 Canvas tag，等待远端 CI，通过后核对 GitHub Release 资产、checksum 和 tag commit。
- [x] 11.7 更新 `full-aigc-plugins` 市场 catalog，使用生成脚本同步 Codex/ZCode/Kimi 清单并提交推送，禁止手改生成产物。
- [ ] 11.8 清理各宿主旧缓存，从市场重新安装 RC，在 Codex、Claude Code、ZCode、Kimi 复跑 JudgePort 与单轮非付费验收。
- [x] 11.9 对照 OpenSpec requirements、任务、测试和真实证据完成 verify；任何账户、Windows、付费或宿主证据缺失时保持 change 未归档。
- [ ] 11.10 所有规格同步且远端/安装证据完整后再 archive change，并在发布说明中区分已验证能力与后续多轮/视频扩展状态。
