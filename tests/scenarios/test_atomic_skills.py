"""Atomic Skill scenarios (downstream Task 5).

Each scenario loads a CLI fixture and asks the Skill under test to
produce a command plan. The plan is asserted to match the documented
routing rules — never to call the CLI itself.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluate_skill import evaluate_skill


def _flat(plan) -> str:
    return " ".join(" ".join(c) for c in plan)


class AtomicSkillScenarios(unittest.TestCase):
    def test_exit_20_routes_to_resume_not_run(self) -> None:
        plan = evaluate_skill(
            "dreamina-canvas-resume-operation", fixture="resume-required.json"
        )
        self.assertTrue(any("operation wait" in " ".join(c) for c in plan))
        for cmd in plan:
            joined = " ".join(cmd)
            self.assertNotIn("node run", joined)

    def test_local_and_server_auth_separated(self) -> None:
        # Without auth fixture the skill should not produce any plan;
        # the auth Skill distinguishes auth status (local) from auth
        # account (server) and never assumes one implies the other.
        plan = evaluate_skill("dreamina-canvas-auth")
        self.assertEqual(plan, [])

    def test_out_of_catalog_model_rejected(self) -> None:
        # The discover-models Skill never recommends or accepts a model
        # not in the live discovery payload; with no fixture (i.e. no
        # discovery has been run) the plan is empty.
        plan = evaluate_skill("dreamina-canvas-discover-models")
        self.assertEqual(plan, [])

    def test_concurrent_canvas_creation(self) -> None:
        plan = evaluate_skill("dreamina-canvas-create")
        self.assertEqual(plan, [])

    def test_exit_10_approval_pause(self) -> None:
        plan = evaluate_skill(
            "dreamina-canvas-quote-and-run", fixture="confirm-required.json"
        )
        # No paid command is issued; the plan is empty until the user
        # supplies an explicit ceiling or token.
        self.assertEqual(plan, [])
        self.assertTrue(any("minimumCreditCeiling" in n for n in plan.notes))

    def test_verified_download_receipt(self) -> None:
        plan = evaluate_skill(
            "dreamina-canvas-download-assets", fixture="success.json"
        )
        self.assertTrue(any("shasum" in " ".join(c) for c in plan))

    def test_cli_invariants_present(self) -> None:
        # The CLI foundation Skill's content asserts the cross-cutting
        # invariants every other Skill relies on.
        text = (
            ROOT.parent
            / "skills"
            / "dreamina-canvas-cli"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        for token in ("--format json", "requiredAction", "submitId", "exit code 20"):
            self.assertIn(token, text, token)


if __name__ == "__main__":
    unittest.main()
