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
    except (ValueError, UnicodeDecodeError, OSError):
        payload = {}
    prompt = str(payload.get("prompt") or "") if isinstance(payload, dict) else ""
    if prompt.strip().startswith("/"):
        return 0
    if INTENT_RE.search(prompt):
        print(
            "提示：该请求疑似即梦画布相关。可用 /dreamina-canvas 总入口或细分命令："
            "安装升级 /dreamina-canvas-setup，鉴权 /dreamina-canvas-auth，"
            "文生图 /dreamina-canvas-image，图生图与放大 /dreamina-canvas-image2image，"
            "文生视频 /dreamina-canvas-video，参考素材视频 /dreamina-canvas-ref2video，"
            "配音 /dreamina-canvas-audio，音乐 /dreamina-canvas-music，"
            "画布 /dreamina-canvas-create，节点组合 /dreamina-canvas-compose，"
            "素材 /dreamina-canvas-assets，运行 /dreamina-canvas-run，"
            "恢复 /dreamina-canvas-resume，时间轴 /dreamina-canvas-timeline。"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
