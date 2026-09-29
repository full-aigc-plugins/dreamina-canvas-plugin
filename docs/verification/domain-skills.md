# Domain Canvas Skills validation report

> **Superseded (plugin 0.4.0, 2026-09-29).** This record covers the thirteen-Skill atom layout, pinned to the
> upstream SHA recorded below. The upstream consolidation retired those Skills into
> operation references under the nine `dreamina-canvas-cli*` entries. Current evidence:
> [`consolidated-nine-entries.md`](consolidated-nine-entries.md). This file is kept as
> the historical record for its version and must not be read as current state.


Upstream SHA: `7a9b0fffc6e85b6e75a98e3abb793f8abc20e1a5`

## Per-Skill validation results

| Skill | upstream byte-parity | scenario result |
|-------|---------------------|-----------------|
| `dreamina-canvas-generate-image` | PASS | PASS — generation edit full-replace + reference syntax + paid handoff |
| `dreamina-canvas-generate-video` | PASS | PASS — public modes t2v/first_last_frame/m2v; i2v/multi_modal rejected |
| `dreamina-canvas-generate-audio` | PASS | PASS — TTS/music exclusivity + --count forbidden |
| `dreamina-canvas-manage-timeline` | PASS | PASS — destructive track replacement warning |

## Aggregate

- 4/4 domain Skill scenarios PASS
- 4/4 byte-parity PASS (vs upstream SHA `7a9b0ff`)
- All 4 Skills verified independently via `tests/scenarios/test_domain_skills.py`
