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
        self.assertEqual(len(lock["skills"]), 13)
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


if __name__ == "__main__":
    unittest.main()
