#!/usr/bin/env python3
"""SessionStart hook: report Dreamina Canvas readiness. Advisory only."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    lines: list[str] = [f"python3: {sys.version.split()[0]}"]

    cli = shutil.which("dreamina-canvas")
    lines.append(f"dreamina-canvas CLI: {cli}" if cli else
                 "dreamina-canvas CLI: 不在 PATH——按 dreamina-canvas-cli 技能指引安装/定位")

    adapter = ROOT / "scripts" / "dreamina_canvas_adapter.py"
    lines.append("canvas adapter: 就绪" if adapter.is_file() else "canvas adapter: 缺失")

    try:
        sys.stdin.read()
    except Exception:
        pass
    print("即梦画布插件环境：" + "；".join(lines))
    return 0


if __name__ == "__main__":
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    sys.exit(main())
