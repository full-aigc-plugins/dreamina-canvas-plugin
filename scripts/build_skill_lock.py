#!/usr/bin/env python3
"""Generate upstream/dreamina-skills.lock.json from the local upstream snapshot.

Records the upstream commit SHA and the SHA-256 of every file under each
declared dreamina-canvas-* Skill directory. The verify script consumes
this lock to enforce byte parity.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

UPSTREAM_REPO = Path(
    "/Users/wandl/workspaces/workspace-agent-skills/"
    "full-aigc-skills-repositories/dreamina-skills/.worktrees/canvas-skills"
)
DOWNSTREAM_ROOT = Path(__file__).resolve().parents[1]
LOCK = DOWNSTREAM_ROOT / "upstream" / "dreamina-skills.lock.json"

CANVAS_SKILLS = [
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
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=UPSTREAM_REPO).decode().strip()


def main() -> None:
    commit = git("rev-parse", "HEAD")
    skills: dict[str, dict[str, str]] = {}
    for name in CANVAS_SKILLS:
        skill_dir = UPSTREAM_REPO / "skills" / name
        if not skill_dir.is_dir():
            print(f"FAIL: missing skill dir: {skill_dir}", file=sys.stderr)
            sys.exit(1)
        files: dict[str, str] = {}
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(skill_dir).as_posix()
                files[rel] = sha256_file(path)
        skills[name] = files

    lock = {
        "schemaVersion": "1.0",
        "repository": "https://github.com/full-aigc-skills/dreamina-skills",
        "commit": commit,
        "skills": skills,
        "sourceContract": "verification/dreamina-canvas-guide-contract.json",
        "suiteReport": "verification/dreamina-canvas-skill-suite.json",
    }
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: wrote {LOCK} (commit {commit[:12]}, {sum(len(v) for v in skills.values())} files)")


if __name__ == "__main__":
    main()
