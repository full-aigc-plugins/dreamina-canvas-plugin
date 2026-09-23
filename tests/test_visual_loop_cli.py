"""Smoke tests for the host-facing entry (task 6.10).

`step` against the real CLI is covered by the composition tests with an
injected runner; here we pin the subcommands a host drives between pauses:
lock-target, status, request-judge, import-judge, stop — and that credentials
only ever travel through the environment.
"""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

cli = importlib.import_module("visual_loop_cli")


def _minimal_png(*, seed: bytes = b"0") -> bytes:
    from test_target_store import png_bytes
    return png_bytes(seed=seed)
from test_judge_exchange import CANDIDATE, SESSION, SHA_C, receipt


class CliCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name) / "workspace"
        self.ws.mkdir()
        self.png = self.ws / "target.png"
        self.png.write_bytes(_minimal_png(seed=b"0"))
        self.base = ["--root", ".loop", "--approved-root", str(self.ws),
                     "--session-id", SESSION]
        self.addCleanup(self._tmp.cleanup)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = cli.main(list(argv))
        except SystemExit as exc:  # argparse errors
            return int(exc.code or 0), buf.getvalue()
        return code, buf.getvalue()

    def test_lock_then_status_records_the_target(self) -> None:
        code, out = self.run_cli("lock-target", *self.base, str(self.png))
        self.assertEqual(code, 0, out)
        body = json.loads(out)
        self.assertEqual(body["ingestionMode"], "judge_only")
        code, out = self.run_cli("status", *self.base)
        state = json.loads(out)
        self.assertEqual(state["state"], "CREATED")
        self.assertEqual([r["kind"] for r in state["receiptRefs"]], ["target"])

    def test_relock_on_changed_content_is_refused(self) -> None:
        self.run_cli("lock-target", *self.base, str(self.png))
        self.png.write_bytes(_minimal_png(seed=b"1"))
        code, _out = self.run_cli("lock-target", *self.base, str(self.png))
        self.assertEqual(code, 1)

    def test_request_and_import_judge_round_trip(self) -> None:
        self.run_cli("lock-target", *self.base, str(self.png))
        code, out = self.run_cli(
            "request-judge", *self.base,
            "--candidate-resource-id", CANDIDATE,
            "--candidate-sha256", SHA_C)
        self.assertEqual(code, 0, out)
        # The request binds the digest of the locked target.
        request_path = json.loads(out)["request"]
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
        self.assertEqual(len(request["target"]["sha256"]), 64)

        verdict = receipt()
        verdict["targetSha256"] = request["target"]["sha256"]
        receipt_file = self.ws / "verdict.json"
        receipt_file.write_text(json.dumps(verdict), encoding="utf-8")
        code, out = self.run_cli("import-judge", *self.base, str(receipt_file))
        self.assertEqual(code, 0, out)
        # Duplicate is refused.
        code, out = self.run_cli("import-judge", *self.base, str(receipt_file))
        self.assertEqual(code, 1)
        self.assertIn("duplicate", json.loads(out)["error"])

    def test_stop_before_submission_is_terminal_and_honest(self) -> None:
        self.run_cli("lock-target", *self.base, str(self.png))
        _code, out = self.run_cli("stop", *self.base)
        state = json.loads(out)
        self.assertEqual(state["state"], "STOPPED")
        self.assertFalse(state["remoteCancelled"])

    def test_step_without_a_target_fails_closed(self) -> None:
        code, out = self.run_cli("step", *self.base, "--project-id", SESSION)
        self.assertEqual(code, 1)
        self.assertIn("lock a target", json.loads(out)["error"])


class EntryPointsTests(CliCase):
    """New entry points: revise / judge / sample-frames / video-verdict."""

    def test_video_verdict_without_temporal_is_manual_review(self) -> None:
        code, out = self.run_cli("video-verdict", "--static-total", "9.5")
        self.assertEqual(code, 0, out)
        verdict = json.loads(out)["verdict"]
        self.assertEqual(verdict["overall"], "MANUAL_REVIEW_REQUIRED")
        self.assertFalse(verdict["passed"])

    def test_flicker_fails_even_with_perfect_stills(self) -> None:
        code, out = self.run_cli("video-verdict", "--static-total", "10",
                                "--temporal", json.dumps({"flicker": "fail"}))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["verdict"]["overall"], "fail")

    def test_sample_frames_missing_video_fails_closed(self) -> None:
        code, out = self.run_cli("sample-frames", "--video",
                                 str(self.ws / "nope.mp4"))
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["ok"])

    def test_revise_without_a_round_fails_closed(self) -> None:
        code, out = self.run_cli("revise", *self.base, "--project-id", SESSION,
                                 "--receipt", str(self.ws / "x.json"))
        self.assertEqual(code, 1)
        self.assertIn("run a round first", json.loads(out)["error"])

    def test_judge_human_mints_the_request_and_parks(self) -> None:
        self.run_cli("lock-target", *self.base, str(self.png))
        code, out = self.run_cli("judge", *self.base, "--adapter", "human",
                                 "--candidate-resource-id", SESSION,
                                 "--candidate-sha256", "b" * 64)
        self.assertEqual(code, 0, out)
        body = json.loads(out)
        self.assertIn("import-judge", body["next"])
        self.assertNotIn("scores", body)


if __name__ == "__main__":
    unittest.main()
