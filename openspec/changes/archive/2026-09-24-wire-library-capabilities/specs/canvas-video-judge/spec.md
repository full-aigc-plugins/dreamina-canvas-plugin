## ADDED Requirements

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
