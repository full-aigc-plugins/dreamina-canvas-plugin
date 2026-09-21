"""Domain Skill scenarios (downstream Task 7).

Asserts the documented mode / reference / generation-edit semantics for
the image / video / audio / timeline Skills by reading each SKILL.md and
matching against the routing rules derived from the upstream guide.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def _plain(name: str) -> str:
    """Strip markdown emphasis and lowercase for robust substring checks."""
    import re

    raw = skill_text(name)
    raw = re.sub(r"\*\*([^*]+)\*\*", r"\1", raw)
    raw = re.sub(r"\*([^*]+)\*", r"\1", raw)
    return raw.lower()


class DomainSkillScenarios(unittest.TestCase):
    def test_image_replaces_generation_fully(self) -> None:
        text = skill_text("dreamina-canvas-generate-image")
        # Generation edit must include the complete block
        self.assertIn("--mode t2i", text)
        self.assertIn("--mode i2i", text)
        self.assertIn("--clear-generation", text)
        # Reference syntax
        self.assertIn("node:", text)
        self.assertIn("res:", text)
        # The skill must hand off paid execution
        self.assertIn("quote-and-run", text.lower())

    def test_video_rejects_i2v_and_multi_modal(self) -> None:
        text = skill_text("dreamina-canvas-generate-video")
        for mode in ("t2v", "first_last_frame", "m2v"):
            self.assertIn(mode, text, mode)
        # Must explicitly call out the rejected modes
        self.assertIn("i2v", text)
        self.assertIn("multi_modal", text)

    def test_audio_enforces_tts_vs_music_exclusivity(self) -> None:
        text = _plain("dreamina-canvas-generate-audio")
        self.assertIn("--voice-name", text)
        self.assertIn("--model", text)
        self.assertIn("--count", text)
        self.assertIn("music", text)
        self.assertIn("tts", text)
        # The skill must forbid --count on audio nodes
        self.assertIn("not accepted on audio nodes", text)

    def test_timeline_warns_before_track_replacement(self) -> None:
        text = skill_text("dreamina-canvas-manage-timeline")
        self.assertIn("--clip", text)
        self.assertIn("--audio-clip", text)
        self.assertIn("rebuild", text.lower())
        self.assertIn("destructive", text.lower())


if __name__ == "__main__":
    unittest.main()
