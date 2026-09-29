"""Orchestration Skill scenarios (downstream Task 8).

Asserts:
- Only dreamina-canvas-use has allow_implicit_invocation == true.
- composition (owned by the public CLI Skill) never runs; it saves only and plans DAG batches.
- dreamina-canvas-use is a thin router that does not duplicate details.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


CANVAS_SKILLS = {
    # Nine stable CLI entry skills plus the implicit orchestrator
    "dreamina-canvas-cli",
    "dreamina-canvas-cli-setup",
    "dreamina-canvas-cli-auth",
    "dreamina-canvas-cli-text2image",
    "dreamina-canvas-cli-image2image",
    "dreamina-canvas-cli-text2video",
    "dreamina-canvas-cli-ref2video",
    "dreamina-canvas-cli-text2voice",
    "dreamina-canvas-cli-text2audio",
    "dreamina-canvas-use",
}


def _plain(name: str) -> str:
    import re

    raw = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    raw = re.sub(r"\*\*([^*]+)\*\*", r"\1", raw)
    raw = re.sub(r"\*([^*]+)\*", r"\1", raw)
    return raw.lower()


def _plain_ref(skill: str, ref: str) -> str:
    """Read one operation reference under a Skill and normalise for matching."""
    import re

    raw = (ROOT / "skills" / skill / "references" / ref).read_text(encoding="utf-8")
    raw = re.sub(r"\*\*([^*]+)\*\*", r"\1", raw)
    raw = re.sub(r"\*([^*]+)\*", r"\1", raw)
    return raw.lower()


def _policy(name: str) -> dict:
    return yaml.safe_load(
        (ROOT / "skills" / name / "agents" / "openai.yaml").read_text(encoding="utf-8")
    )["policy"]


class OrchestrationSkillScenarios(unittest.TestCase):
    def test_use_is_the_only_implicit_canvas_skill(self) -> None:
        for name in CANVAS_SKILLS - {"dreamina-canvas-use"}:
            self.assertEqual(_policy(name)["allow_implicit_invocation"], False, name)
        self.assertTrue(_policy("dreamina-canvas-use")["allow_implicit_invocation"])

    def test_compose_never_runs(self) -> None:
        # Composition moved into the public CLI skill's operation reference.
        text = _plain_ref("dreamina-canvas-cli", "composition.md")
        # Never calls --run
        self.assertIn("never", text)
        self.assertIn("node run", text)
        # Builds explicit DAG layers
        self.assertIn("dag", text)
        # Default-only-save contract
        self.assertIn("default-only-save", text)

    def test_use_is_a_thin_router(self) -> None:
        text = _plain("dreamina-canvas-use")
        # Routes to the nine entries by name without owning a second
        # parameter contract; the table is the routing surface.
        for entry in (
            "dreamina-canvas-cli-setup",
            "dreamina-canvas-cli-auth",
            "dreamina-canvas-cli-text2image",
            "dreamina-canvas-cli-image2image",
            "dreamina-canvas-cli-text2video",
            "dreamina-canvas-cli-ref2video",
            "dreamina-canvas-cli-text2voice",
            "dreamina-canvas-cli-text2audio",
        ):
            self.assertIn(entry, text, entry)
        # Handoff is by name plus an install command, never sibling paths
        self.assertIn("npx skills add", text)
        # Reports the lifecycle stages in order
        for stage in ("草稿", "报价", "已批准", "已提交", "终态", "已验证"):
            self.assertIn(stage, text, stage)


if __name__ == "__main__":
    unittest.main()
