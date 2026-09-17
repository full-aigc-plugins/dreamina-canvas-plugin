"""Portable / compatibility manifest parity tests.

The repository ships both:
  - `plugin.json`                  canonical portable manifest
  - `.codex-plugin/plugin.json`    compatibility fallback

Per `docs/portable-migration.md`, migration acceptance requires schema
validation and parity between both manifests, plus confirmation that the
plugin identity is unchanged. These tests are the machine-checkable half of
that requirement.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTABLE = ROOT / "plugin.json"
COMPAT = ROOT / ".codex-plugin" / "plugin.json"

PLUGIN_ID = "dreamina-canvas"
SCHEMA_URL = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"

# Top-level fields allowed by the published portable schema
# (additionalProperties: false).
PORTABLE_ALLOWED = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
AUTHOR_ALLOWED = {"name", "email", "url"}
NAME_RE = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")

IDENTITY_FIELDS = (
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PortableManifestTests(unittest.TestCase):
    def test_portable_manifest_exists_and_satisfies_schema(self) -> None:
        manifest = load(PORTABLE)
        self.assertEqual(set(manifest) - PORTABLE_ALLOWED, set())
        self.assertEqual(manifest["$schema"], SCHEMA_URL)
        self.assertEqual(manifest["name"], PLUGIN_ID)
        self.assertRegex(manifest["name"], NAME_RE)
        self.assertLessEqual(len(manifest["name"]), 64)
        self.assertEqual(set(manifest["author"]) - AUTHOR_ALLOWED, set())

    def test_portable_interface_lives_under_extensions(self) -> None:
        manifest = load(PORTABLE)
        # The published schema is additionalProperties:false, so `interface`
        # and `skills` must NOT appear at the top level of the portable file.
        self.assertNotIn("interface", manifest)
        self.assertNotIn("skills", manifest)
        interface = manifest["extensions"]["com.openai"]["interface"]
        for required in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "capabilities",
            "defaultPrompt",
        ):
            self.assertIn(required, interface, required)

    def test_identity_parity_between_both_manifests(self) -> None:
        portable = load(PORTABLE)
        compat = load(COMPAT)
        for field in IDENTITY_FIELDS:
            self.assertEqual(portable.get(field), compat.get(field), field)

    def test_interface_parity_between_both_manifests(self) -> None:
        portable_interface = load(PORTABLE)["extensions"]["com.openai"]["interface"]
        compat_interface = load(COMPAT)["interface"]
        self.assertEqual(set(portable_interface), set(compat_interface))
        for field in sorted(portable_interface):
            self.assertEqual(
                portable_interface[field], compat_interface[field], field
            )

    def test_both_manifests_declare_no_mcp_or_apps(self) -> None:
        # This plugin ships no MCP servers and no apps; declaring either
        # without the companion file would be an untruthful claim.
        portable = load(PORTABLE)
        compat = load(COMPAT)
        self.assertNotIn("mcpServers", compat)
        self.assertNotIn("apps", compat)
        extension = portable["extensions"]["com.openai"]
        self.assertNotIn("mcpServers", portable)
        self.assertNotIn("apps", extension)
        # ...and no companion files exist to contradict that
        for name in ("mcp.json", ".mcp.json", ".app.json"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_referenced_brand_assets_exist(self) -> None:
        interface = load(PORTABLE)["extensions"]["com.openai"]["interface"]
        for field in ("composerIcon", "logo", "logoDark"):
            rel = interface[field]
            self.assertTrue(rel.startswith("./assets/"), rel)
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
