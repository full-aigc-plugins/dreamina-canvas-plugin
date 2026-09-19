# Documentation quality gates

The five-plugin suite specification
(`dreamina-skills/docs/superpowers/specs/2026-09-11-dreamina-five-plugin-suite-documentation-design.md`,
§11 文档质量门禁) defines eleven gates that every plugin's bilingual document
set must pass. This file records the result for this repository's six
documents.

Audited set:

```text
README.md
README.zh-CN.md
docs/Dreamina-Canvas-Plugin-Architecture.md
docs/Dreamina-Canvas-Plugin-Architecture.zh_CN.md
docs/Dreamina-Canvas-Plugin-Technical-Solution.md
docs/Dreamina-Canvas-Plugin-Technical-Solution.zh_CN.md
```

| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 1 | Filenames conform; architecture files pass `validate_architecture_filenames.py` | PASS | `--require-pairs` on the two Architecture files: `architecture_files=2 errors=0` |
| 2 | Exactly one H1; code fences balanced and language-tagged | PASS | all 6 docs: 1 H1 each; no unbalanced or untagged fences |
| 3 | No unresolved `{{...}}` placeholders | PASS | zero matches |
| 4 | No local absolute paths, real accounts, tokens, cookies, secrets, or private project data | PASS | zero matches for `/Users/…`, key/token patterns, credentials |
| 5 | Bilingual top-level sections correspond | PASS | README 6/6, Architecture 5/5, Technical-Solution 5/5 |
| 6 | Identifiers, commands, schema fields, versions, statuses consistent across languages | PASS | backticked code-token sets identical: README 1/1, Architecture 7/7, Technical-Solution 15/15 |
| 7 | All relative links resolve | PASS | zero broken links |
| 8 | Mermaid answers concrete architecture questions (context / main sequence / failure-recovery / state transitions) | PASS | Architecture carries `flowchart` (context) and `stateDiagram-v2` (state machine) |
| 9 | Current facts vs target design vs inference vs unverified clearly distinguished | PASS | implementation status line updated to `Implemented. Updated 2026-09-12. Runtime evidence is recorded in docs/verification/` |
| 10 | Every requirement has an observable acceptance criterion | PASS | Technical-Solution states the contract set (`CapabilitySnapshot`, `QuoteReceipt`, `OperationReceipt`, `ArtifactReceipt`), the normalized error model, and the subprocess-boundary test strategy |
| 11 | `git diff --check` | PASS | clean |

## Notes

- Gate 1 covers only the `*-Architecture*.md` pair. `*-Technical-Solution*.md`
  files are intentionally excluded: the validator's contract is
  architecture-file specific, and passing them returns a false failure.
- This repository's six documents were already complete when the gates were
  first run; the record exists because the gate had no evidence trail, not
  because anything was remediated.
- The wider 30-document deliverable (five plugins × six documents) is a
  separate program spanning five repositories and is tracked outside this
  repository. Its status at the time of writing: 26/30 — this repository 6/6,
  `maya-design-plugin` 6/6, `dreamina-design-plugin` 6/6,
  `dreamina-3d-plugin` 6/6, `blender-design-plugin` 2/6.
