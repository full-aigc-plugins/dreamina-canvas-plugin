"""Domain Skill scenarios for the nine CLI entry Skills (post 2026-09-29).

Asserts the mode, reference, and generation-edit semantics that the
consolidated package now owns: per-mode task Skills keep the mode
constraints, the public CLI Skill keeps the shared node/operation
contracts under references/, and paid execution is always handed off.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def ref_text(skill: str, ref: str) -> str:
    return (ROOT / "skills" / skill / "references" / ref).read_text(encoding="utf-8")


def _plain(text: str) -> str:
    """Strip markdown emphasis and lowercase for robust substring checks."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.lower()


class DomainSkillScenarios(unittest.TestCase):
    def test_text2image_owns_t2i_draft_and_hands_off_paid_run(self) -> None:
        text = skill_text("dreamina-canvas-cli-text2image")
        self.assertIn("--mode t2i", text)
        # Paid execution is never approved here; the chain is handed off.
        self.assertIn("node quote", text)
        self.assertIn("dreamina-canvas-cli", text)
        # Placeholders must not be mistaken for literal values
        self.assertIn("<model>", text)

    def test_image2image_owns_i2i_reference_and_separate_upscale(self) -> None:
        text = skill_text("dreamina-canvas-cli-image2image")
        self.assertIn("--mode i2i", text)
        self.assertIn("res:", text)
        self.assertIn("node:", text)
        # Upscale is separately priced and never reuses a node confirm token
        self.assertIn("upscale", text.lower())
        self.assertIn("separately priced", text.lower())

    def test_image_node_contract_keeps_generation_replace_semantics(self) -> None:
        text = ref_text("dreamina-canvas-cli", "image-node.md")
        for token in ("--clear-generation", "node:", "res:", "full replace"):
            self.assertIn(token, text.lower(), token)

    def test_text2video_owns_t2v(self) -> None:
        text = skill_text("dreamina-canvas-cli-text2video")
        self.assertIn("--mode t2v", text)
        self.assertIn("--duration", text)

    def test_ref2video_rejects_i2v_and_multi_modal(self) -> None:
        text = skill_text("dreamina-canvas-cli-ref2video")
        for mode in ("m2v", "first_last_frame"):
            self.assertIn(mode, text, mode)
        # The rejected public-mode names must still be called out explicitly
        self.assertIn("i2v", text)
        self.assertIn("multi_modal", text)

    def test_audio_entries_enforce_mode_field_exclusivity(self) -> None:
        tts = skill_text("dreamina-canvas-cli-text2voice")
        music = skill_text("dreamina-canvas-cli-text2audio")
        # TTS: voice-driven, never a model
        self.assertIn("--voice-name", tts)
        self.assertIn("不传 --model", tts)
        # Music: model-driven, never a voice name
        self.assertIn("--model", music)
        self.assertIn("不传 --voice-name", music)
        # Neither entry may pass --count
        for text in (tts, music):
            self.assertIn("--count", text)

    def test_timeline_warns_before_track_replacement(self) -> None:
        text = _plain(ref_text("dreamina-canvas-cli", "timeline.md"))
        self.assertIn("--clip", text)
        self.assertIn("--audio-clip", text)
        self.assertIn("rebuild", text)
        self.assertIn("destructive", text)


if __name__ == "__main__":
    unittest.main()
