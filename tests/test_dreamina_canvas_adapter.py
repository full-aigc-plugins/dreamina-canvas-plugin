"""Adapter tests (downstream Task 3).

The adapter is the boundary between the plugin and the CLI; we exercise
its argv construction, exit-code preservation, JSON parsing, and error
envelope extraction. The CLI itself is mocked — never invoked.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dreamina_canvas_adapter as adapter


class FakeProc:
    def __init__(self, *, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class AdapterTests(unittest.TestCase):
    def test_build_argv_inserts_format_json_and_profile(self) -> None:
        argv = adapter.build_argv(["schema", "node create image"], profile="work")
        self.assertEqual(
            argv,
            ["--format", "json", "--profile", "work", "schema", "node create image"],
        )

    def test_build_argv_preserves_existing_format(self) -> None:
        argv = adapter.build_argv(["--format", "table", "version"])
        self.assertEqual(argv, ["--format", "table", "version"])

    def test_adapter_uses_argv_and_json_mode(self) -> None:
        captured = {}
        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return FakeProc(returncode=0, stdout='{"schemaVersion":"1","ok":true,"data":{}}')

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            result = adapter.run_dreamina_canvas(
                ["schema", "node create image"], timeout_seconds=5
            )
        self.assertEqual(
            captured["argv"][:3], ["dreamina-canvas", "--format", "json"]
        )
        self.assertEqual(captured["argv"][3:], ["schema", "node create image"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.required_action, "none")
        self.assertIsNone(result.error)

    def test_missing_executable_surfaces_failure(self) -> None:
        def fake_run(argv, **kwargs):
            raise FileNotFoundError(2, "No such file", argv[0])

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            result = adapter.run_dreamina_canvas(["version"])
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.error["code"], "cli.binary_not_found")

    def test_malformed_json_on_success_is_carried(self) -> None:
        with mock.patch.object(
            subprocess,
            "run",
            lambda *a, **kw: FakeProc(returncode=0, stdout="not json"),
        ):
            result = adapter.run_dreamina_canvas(["version"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.payload, {"raw": "not json"})

    def test_failure_envelope_from_stderr(self) -> None:
        envelope = {
            "ok": False,
            "error": {
                "code": "cli.node_run_unknown",
                "message": "operation not converged",
                "requiredAction": "resume",
            },
        }
        with mock.patch.object(
            subprocess,
            "run",
            lambda *a, **kw: FakeProc(returncode=20, stderr=json.dumps(envelope)),
        ):
            result = adapter.run_dreamina_canvas(["node", "run"])
        self.assertEqual(result.exit_code, 20)
        self.assertEqual(result.required_action, "resume")
        self.assertEqual(result.error["code"], "cli.node_run_unknown")

    def test_stdout_on_error_is_not_treated_as_payload(self) -> None:
        envelope = {"ok": False, "error": {"code": "x", "requiredAction": "human_intervention"}}
        with mock.patch.object(
            subprocess,
            "run",
            lambda *a, **kw: FakeProc(
                returncode=12,
                stdout='{"some":"leak"}',
                stderr=json.dumps(envelope),
            ),
        ):
            result = adapter.run_dreamina_canvas(["node", "create", "image"])
        self.assertEqual(result.exit_code, 12)
        self.assertIsNone(result.payload)
        self.assertEqual(result.required_action, "human_intervention")

    def test_stderr_on_success_does_not_pollute_error(self) -> None:
        with mock.patch.object(
            subprocess,
            "run",
            lambda *a, **kw: FakeProc(
                returncode=0,
                stdout='{"ok":true,"data":{"v":1}}',
                stderr="progress noise",
            ),
        ):
            result = adapter.run_dreamina_canvas(["version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.error)
        self.assertEqual(result.payload["data"], {"v": 1})

    def test_timeout_propagates(self) -> None:
        with mock.patch.object(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd="x", timeout=1))), \
                self.assertRaises(subprocess.TimeoutExpired):
                adapter.run_dreamina_canvas(["version"], timeout_seconds=1)

    def test_output_size_limit_caps_strings(self) -> None:
        huge = "x" * (4 * 1024 * 1024)
        with mock.patch.object(
            subprocess,
            "run",
            lambda *a, **kw: FakeProc(returncode=0, stdout=huge, stderr=huge),
        ):
            result = adapter.run_dreamina_canvas(["version"], output_limit_bytes=1024)
        # The capped payload is still carried; we do not lose exit code.
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
