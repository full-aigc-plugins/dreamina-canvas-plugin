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
    def test_harness_separates_local_and_historical_evidence(self) -> None:
        content = HARNESS.read_text(encoding="utf-8")
        for marker in (
            "VISUAL_LOOP_STATUS: SINGLE_ROUND_LOCAL_REGRESSION",
            "VISUAL_TARGET_UPLOAD: ADAPTER_COMPOSITION_TESTED_HOST_REGISTRATION_REQUIRED",
            "VISUAL_JUDGE_AUTOMATION: HOST_MEDIATED_RECEIPT_IMPORT_IMPLEMENTED",
            "LOCAL_FILE_URI_REFERENCE: UNSUPPORTED",
            "PAID_EXECUTION: REQUIRES_THE_STANDARD_QUOTE_CONFIRM_RUN_CHAIN",
            "CURRENT_WINDOWS_AND_PAID_VERIFICATION: NOT_RERUN",
        ):
            self.assertIn(marker, content)

        for retired_claim in (
            "{{uri:file://",
            "download-assets` 自动镜像",
            "刷新 `latest.png`",
        ):
            self.assertNotIn(retired_claim, content)

    def test_all_named_skill_routes_exist_in_distribution(self):
        import re
        content = HARNESS.read_text(encoding="utf-8")
        routes = set(re.findall(r"`(dreamina-canvas-[a-z0-9-]+)`", content))
        distributed = {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}
        self.assertEqual(routes, distributed)
        self.assertIn('--approve-request-fingerprint', content)
        self.assertIn('argv', content)
        self.assertIn('2026-09-22', content)
        self.assertIn('register_target', content)

    def test_public_docs_link_the_active_visual_loop_change(self) -> None:
        for path in PUBLIC_DOCS:
            content = path.read_text(encoding="utf-8")
            self.assertIn(CHANGE_ID, content, path.name)


if __name__ == "__main__":
    unittest.main()
