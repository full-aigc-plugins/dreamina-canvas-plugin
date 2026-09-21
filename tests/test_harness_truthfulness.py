"""Truthfulness gates for the plugin-local visual-loop Harness.

The Harness is discoverable by every supported host, so it must not describe
planned controller behavior as an already-executed runtime capability.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "skills" / "dreamina-canvas-harness" / "SKILL.md"
PUBLIC_DOCS = (
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "docs" / "Dreamina-Canvas-Plugin-Architecture.md",
    ROOT / "docs" / "Dreamina-Canvas-Plugin-Architecture.zh_CN.md",
)
CHANGE_ID = "add-canvas-visual-quality-loop"


class HarnessTruthfulnessTests(unittest.TestCase):
    def test_harness_marks_visual_loop_features_as_planned(self) -> None:
        content = HARNESS.read_text(encoding="utf-8")
        for marker in (
            "VISUAL_LOOP_STATUS: PLANNED_NOT_IMPLEMENTED",
            "VISUAL_TARGET_UPLOAD: NOT_IMPLEMENTED",
            "VISUAL_CANDIDATE_POINTER: NOT_IMPLEMENTED",
            "VISUAL_JUDGE_AUTOMATION: NOT_IMPLEMENTED",
            "LOCAL_FILE_URI_REFERENCE: UNSUPPORTED",
        ):
            self.assertIn(marker, content)

        for retired_claim in (
            "{{uri:file://",
            "download-assets` 自动镜像",
            "刷新 `latest.png`",
        ):
            self.assertNotIn(retired_claim, content)

    def test_public_docs_link_the_active_visual_loop_change(self) -> None:
        for path in PUBLIC_DOCS:
            content = path.read_text(encoding="utf-8")
            self.assertIn(CHANGE_ID, content, path.name)


if __name__ == "__main__":
    unittest.main()
