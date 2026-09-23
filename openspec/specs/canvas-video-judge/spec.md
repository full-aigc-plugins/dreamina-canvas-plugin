# canvas-video-judge Specification

## Purpose
在图像闭环稳定后定义视频候选的关键帧和时序质量评估，防止以单帧图像分数冒充整段视频的运动、节奏和连续性结论。
## Requirements
### Requirement: Video judging binds sampled frames to the source video
系统 SHALL 保存视频内容摘要、时长、帧率、采样策略和每个关键帧摘要，使 JudgeReceipt 可以证明关键帧来自被评估的视频。

#### Scenario: Video frames are sampled successfully
- **WHEN** 视频产物通过完整性校验且可用帧采样器存在
- **THEN** 系统按声明策略提取关键帧并产生与源视频摘要绑定的采样回执

### Requirement: Video judgment separates still and temporal criteria
视频 Judge SHALL 分别输出关键帧视觉评分和时序门禁，时序门禁至少覆盖动作连续、闪烁、主体漂移、镜头运动和节奏；存在音频时 SHALL 额外评估音画同步。

#### Scenario: Keyframes look correct but motion flickers
- **WHEN** 静态关键帧达到阈值但相邻时段存在明显闪烁
- **THEN** 视频整体不得判定为通过，并在时序差距中记录闪烁证据

### Requirement: Missing temporal analysis degrades to manual review
当系统缺少 FFmpeg 或等价时序分析能力时 SHALL 返回 `MANUAL_REVIEW_REQUIRED` 或等价状态，不得仅评估首帧后声称视频通过。

#### Scenario: Frame sampler is unavailable
- **WHEN** 当前环境无法安全提取或查看足够视频帧
- **THEN** 系统保留视频产物并请求人工预览，不产生完整视频通过分数

### Requirement: Video judging is reachable from a production entry point
系统 SHALL 通过 `visual_loop_cli.py sample-frames` 输出 `VideoEvidence` JSON
（源摘要、时长、帧率、采样策略、逐帧摘要），并以
`video-verdict` 组合静态分与门禁裁决输出 `VideoJudgeVerdict`。三条 domain 规则
（帧绑定、静态/时序分离、缺时序 MANUAL_REVIEW_REQUIRED）继续成立。

#### Scenario: Sample evidence
- **WHEN** FFmpeg 可用且用户运行 `sample-frames --video <file>`
- **THEN** 输出完整 VideoEvidence JSON；FFmpeg 缺失时返回能力不可用而非空结果

#### Scenario: Missing temporal analysis degrades honestly
- **WHEN** `video-verdict` 未提供 temporal 结果
- **THEN** 返回 `MANUAL_REVIEW_REQUIRED`，不以静态分代替视频结论

