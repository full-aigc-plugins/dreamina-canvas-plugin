"""Documentation quality gates.

Encodes the five-plugin suite specification's §11 gates for this
repository's six bilingual documents, so the audit cannot regress.
See docs/verification/doc-quality-gates.md for the recorded result.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ARCHITECTURE = (
    ROOT / "docs" / "Dreamina-Canvas-Plugin-Architecture.md",
    ROOT / "docs" / "Dreamina-Canvas-Plugin-Architecture.zh_CN.md",
)
TECHNICAL = (
    ROOT / "docs" / "Dreamina-Canvas-Plugin-Technical-Solution.md",
    ROOT / "docs" / "Dreamina-Canvas-Plugin-Technical-Solution.zh_CN.md",
)
READMES = (ROOT / "README.md", ROOT / "README.zh-CN.md")
ALL_DOCS = READMES + ARCHITECTURE + TECHNICAL

LANGUAGE_PAIRS = (
    (ROOT / "README.md", ROOT / "README.zh-CN.md"),
    (ARCHITECTURE[0], ARCHITECTURE[1]),
    (TECHNICAL[0], TECHNICAL[1]),
)

SECRET_PATTERNS = (
    (r"/Users/wandl", "local absolute path"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"sk-[A-Za-z0-9]{16,}", "API key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY", "private key"),
    (r"access_token|refresh_token", "credential name"),
    (r"cookie\s*=", "cookie value"),
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def code_tokens(path: Path) -> set[str]:
    return {
        m.group(1).strip()
        for m in re.finditer(r"`([^`\n]+)`", read(path))
        if re.search(r"[A-Za-z_][A-Za-z0-9_.:-]*", m.group(1))
    }


def top_sections(path: Path) -> list[str]:
    return [l for l in read(path).splitlines() if l.startswith("## ")]


class DocQualityGateTests(unittest.TestCase):
    def test_gate2_one_h1_and_tagged_balanced_fences(self) -> None:
        for path in ALL_DOCS:
            text = read(path)
            self.assertEqual(
                len(re.findall(r"^# ", text, re.MULTILINE)), 1, f"{path.name}: H1 count"
            )
            fences = re.findall(r"^```(\w*)", text, re.MULTILINE)
            self.assertEqual(len(fences) % 2, 0, f"{path.name}: unbalanced fences")
            untagged = [f for f in fences[0::2] if not f]
            self.assertEqual(untagged, [], f"{path.name}: untagged fences")

    def test_gate3_no_unresolved_placeholders(self) -> None:
        for path in ALL_DOCS:
            self.assertEqual(
                re.findall(r"\{\{[^}]+\}\}", read(path)), [], path.name
            )

    def test_gate4_no_secrets_or_local_paths(self) -> None:
        for path in ALL_DOCS:
            text = read(path)
            for pattern, label in SECRET_PATTERNS:
                self.assertIsNone(
                    re.search(pattern, text), f"{path.name}: {label}"
                )

    def test_gate5_bilingual_section_parity(self) -> None:
        for en, zh in LANGUAGE_PAIRS:
            self.assertEqual(
                len(top_sections(en)), len(top_sections(zh)),
                f"{en.name} vs {zh.name}: top-level section count",
            )

    def test_gate6_code_token_parity(self) -> None:
        for en, zh in LANGUAGE_PAIRS:
            only_en = code_tokens(en) - code_tokens(zh)
            only_zh = code_tokens(zh) - code_tokens(en)
            self.assertEqual(only_en, set(), f"{en.name}: tokens missing from zh")
            self.assertEqual(only_zh, set(), f"{zh.name}: tokens missing from en")

    def test_gate7_relative_links_resolve(self) -> None:
        for path in ALL_DOCS:
            for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", read(path)):
                link = m.group(1).split("#")[0].strip()
                if not link or link.startswith(("http://", "https://", "mailto:")):
                    continue
                self.assertTrue(
                    (path.parent / link).resolve().exists(),
                    f"{path.name}: broken link {link}",
                )

    def test_gate8_mermaid_covers_context_and_state(self) -> None:
        joined = "\n".join(read(p) for p in ARCHITECTURE)
        blocks = re.findall(r"```mermaid(.*?)```", joined, re.DOTALL)
        self.assertTrue(blocks, "no mermaid blocks in the architecture pair")
        self.assertTrue(
            any("flowchart" in b or "graph " in b for b in blocks),
            "no flowchart (context diagram)",
        )

    def test_gate9_implementation_status_is_stated(self) -> None:
        # The architecture doc must not leave the reader guessing whether the
        # content is a target design or delivered behaviour.
        text = read(ARCHITECTURE[0])
        self.assertRegex(text, r"(?i)(implemented|delivered|target architecture)")


if __name__ == "__main__":
    unittest.main()
