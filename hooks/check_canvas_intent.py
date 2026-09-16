#!/usr/bin/env python3
"""UserPromptSubmit hook: point Canvas-shaped requests at the plugin commands. Advisory only."""
from __future__ import annotations

import json
import re
import sys

INTENT_RE = re.compile(
    r"即梦画布|dreamina\s*canvas|画布|节点图|时间线编排|画布节点",
    re.IGNORECASE,
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    prompt = str(payload.get("prompt") or "") if isinstance(payload, dict) else ""
    if prompt.strip().startswith("/"):
        return 0
    if INTENT_RE.search(prompt):
        print(
            "提示：该请求疑似即梦画布相关。可用 /dreamina-canvas 总入口或细分命令 "
            "(/dreamina-canvas-create /dreamina-canvas-compose /dreamina-canvas-image "
            "/dreamina-canvas-video /dreamina-canvas-audio /dreamina-canvas-timeline "
            "/dreamina-canvas-run /dreamina-canvas-resume /dreamina-canvas-assets)。"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
