#!/usr/bin/env python3
"""Generate upstream/dreamina-skills.lock.json from the local upstream snapshot.

Records the upstream commit SHA and the SHA-256 of every file under each
declared dreamina-canvas-* Skill directory. The verify script consumes
this lock to enforce byte parity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

DOWNSTREAM_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = DOWNSTREAM_ROOT / "upstream" / "dreamina-skills.lock.json"

CANVAS_SKILLS = [
    # Nine stable CLI entry skills (2026-09-29 consolidate-canvas-cli-atoms)
    "dreamina-canvas-cli",
    "dreamina-canvas-cli-setup",
    "dreamina-canvas-cli-auth",
    "dreamina-canvas-cli-text2image",
    "dreamina-canvas-cli-image2image",
    "dreamina-canvas-cli-text2video",
    "dreamina-canvas-cli-ref2video",
    "dreamina-canvas-cli-text2voice",
    "dreamina-canvas-cli-text2audio",
    # The single implicit orchestrator
    "dreamina-canvas-use",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git(upstream_repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=upstream_repo).decode().strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upstream-path",
        required=True,
        help="Checked-out dreamina-skills repository at the commit to lock",
    )
    parser.add_argument("--lock", default=str(DEFAULT_LOCK))
    args = parser.parse_args()
    upstream_repo = Path(args.upstream_path).resolve()
    lock_path = Path(args.lock).resolve()
    if not (upstream_repo / ".git").exists():
        # Linked worktrees use a .git file; normal repositories use a directory.
        print(f"FAIL: not a Git checkout: {upstream_repo}", file=sys.stderr)
        sys.exit(1)
    commit = git(upstream_repo, "rev-parse", "HEAD")
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        print(f"FAIL: upstream HEAD is not a canonical commit SHA: {commit}", file=sys.stderr)
        sys.exit(1)
    skills: dict[str, dict[str, str]] = {}
    for name in CANVAS_SKILLS:
        skill_dir = upstream_repo / "skills" / name
        if not skill_dir.is_dir():
            print(f"FAIL: missing skill dir: {skill_dir}", file=sys.stderr)
            sys.exit(1)
        files: dict[str, str] = {}
        for path in sorted(skill_dir.rglob("*")):
            if not path.is_file():
                continue
            # Lock real package content only. Dot-prefixed host metadata
            # (e.g. a .DS_Store dropped by Finder) and build caches are
            # untracked upstream, so they must never enter the lock or the
            # byte-exact contract would depend on the operator's working tree.
            if any(part.startswith(".") for part in path.relative_to(skill_dir).parts):
                continue
            if path.suffix in {".pyc", ".pyo"} or "__pycache__" in path.parts:
                continue
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
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: wrote {lock_path} (commit {commit[:12]}, {sum(len(v) for v in skills.values())} files)")


if __name__ == "__main__":
    main()
