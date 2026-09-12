"""Orchestration Skill scenarios (downstream Task 8).

Asserts:
- Only dreamina-canvas-use has allow_implicit_invocation == true.
- dreamina-canvas-compose never runs (saves only) and plans DAG batches.
- dreamina-canvas-use is a thin router that does not duplicate details.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


CANVAS_SKILLS = {
    "dreamina-canvas-cli",
    "dreamina-canvas-auth",
    "dreamina-canvas-discover-models",
    "dreamina-canvas-create",
    "dreamina-canvas-compose",
    "dreamina-canvas-generate-image",
    "dreamina-canvas-generate-video",
    "dreamina-canvas-generate-audio",
    "dreamina-canvas-manage-timeline",
    "dreamina-canvas-quote-and-run",
    "dreamina-canvas-resume-operation",
    "dreamina-canvas-download-assets",
    "dreamina-canvas-use",
}


def _plain(name: str) -> str:
    import re

    raw = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
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
        text = _plain("dreamina-canvas-compose")
        # Never calls --run
        self.assertIn("never", text)
        self.assertIn("node run", text)
        # Builds explicit DAG layers
        self.assertIn("dag", text)
        # Default-only-save contract
        self.assertIn("default-only-save", text)

    def test_use_is_a_thin_router(self) -> None:
        text = _plain("dreamina-canvas-use")
        # Routes to other Skills without duplicating command details
        self.assertIn("smallest applicable", text)
        # References the lifecycle stages in order
        for stage in ("saved draft", "quoted amount", "user approval",
                      "submission acceptance", "terminal completion", "verified artifact"):
            self.assertIn(stage, text, stage)


if __name__ == "__main__":
    unittest.main()
