import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "upstream" / "dreamina-skills.lock.json"
SKILLS = ROOT / "skills"


class SkillSyncTests(unittest.TestCase):
    def test_sync_tools_are_portable_and_require_explicit_sources(self) -> None:
        for name in ("build_skill_lock.py", "sync_dreamina_canvas_skills.py"):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text, name)
            self.assertIn("--upstream-path", text, name)

    def test_packaged_skills_match_locked_source(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(
            lock["repository"],
            "https://github.com/full-aigc-skills/dreamina-skills",
        )
        # Nine CLI entries plus the implicit orchestrator (2026-09-29)
        self.assertEqual(len(lock["skills"]), 10)
        # Every packaged skill must have a non-empty file list
        for name, files in lock["skills"].items():
            self.assertGreater(len(files), 0, name)
        # Packaged directory set must match lock skill set
        packaged = {
            p.name
            for p in SKILLS.iterdir()
            if p.is_dir() and p.name.startswith("dreamina-canvas-") and p.name != "dreamina-canvas-harness"
        }
        self.assertEqual(packaged, set(lock["skills"].keys()))

    def test_locked_commit_is_40_hex(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        commit = lock["commit"]
        self.assertEqual(len(commit), 40)
        int(commit, 16)


    def test_lock_tools_exclude_untracked_host_noise(self) -> None:
        """A stray .DS_Store / __pycache__ must never enter the lock or vendor.

        Host metadata is untracked upstream, so letting it into the lock
        would make the byte-exact contract depend on one operator's working
        tree (this happened in 0.4.0 and broke parity in the design plugin).
        """
        for name in ("build_skill_lock.py", "sync_dreamina_canvas_skills.py",
                     "verify_dreamina_canvas_skills.py"):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("__pycache__", text, name)
            self.assertTrue(
                'startswith(".")' in text or 'ignore_patterns' in text, name
            )
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for skill, files in lock["skills"].items():
            for rel in files:
                self.assertFalse(
                    Path(rel).name.startswith("."), f"{skill}: {rel}"
                )
                self.assertNotIn("__pycache__", rel, f"{skill}: {rel}")


if __name__ == "__main__":
    unittest.main()
