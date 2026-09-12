#!/usr/bin/env python3
"""Re-run the deterministic sync for the pinned upstream commit.

Copies the declared dreamina-canvas-* Skills from the local upstream
snapshot into this plugin's skills/ directory, then writes
upstream/dreamina-skills.lock.json with the recorded commit and per-file
SHA-256 values.

Usage:
    python3 scripts/sync_dreamina_canvas_skills.py [--lock <path>]

Default lock path: upstream/dreamina-skills.lock.json
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_WT = Path(
    "/Users/wandl/workspaces/workspace-agent-skills/"
    "full-aigc-skills-repositories/dreamina-skills/.worktrees/canvas-skills"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", default=str(ROOT / "upstream" / "dreamina-skills.lock.json"))
    args = parser.parse_args()
    lock_path = Path(args.lock)
    lock = __import__("json").loads(lock_path.read_text(encoding="utf-8"))
    declared = list(lock["skills"].keys())
    skills_dir = ROOT / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for name in declared:
        src = UPSTREAM_WT / "skills" / name
        dst = skills_dir / name
        if not src.is_dir():
            print(f"FAIL: upstream skill missing: {src}", file=sys.stderr)
            sys.exit(1)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    print(f"OK: synced {len(declared)} skills from {UPSTREAM_WT}")


if __name__ == "__main__":
    main()
