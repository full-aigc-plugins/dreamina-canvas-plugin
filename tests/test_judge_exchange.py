"""Judge request/receipt exchange tests (task 6.8).

The pause at AWAITING_JUDGE must survive a process restart as a file pair:
request written at pause time, receipt imported by a host (or a human), the
restarted controller consumes it and finishes the round. Everything that could
poison the verdict is rejected outright.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import judge_exchange as jx
import visual_loop as vl
from loop_state import LoopStateStore

SESSION = "00112233-4455-6677-8899-aabbccddeeff"
TARGET = "abcdefab-1234-5678-9abc-def012345678"
CANDIDATE = "ffeeddcc-bbaa-9988-7766-554433221100"
SHA_T = "a" * 64
SHA_C = "b" * 64


def receipt(**over) -> dict:
    base = {
        "schemaVersion": "judge_receipt/1", "judgeId": SESSION,
        "adapter": "host_subagent", "modelClass": "gpt-6-astra",
        "targetSha256": SHA_T, "candidateSha256": SHA_C,
        "scores": {"composition": 2.5, "lighting": 2.0, "materials": 2.5,
                   "details": 0.5, "total": 7.5},
        "gaps": [{"dimension": "lighting", "severity": "high",
                  "location": "face", "observation": "key light reversed",
                  "fixHint": "rotate 30°"}],
        "recommendation": "revise",
        "freshContext": True, "sawPromptDraft": False,
        "judgedAt": "2026-09-21T12:00:00Z",
    }
    base.update(over)
    return base


class ExchangeCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.approved = Path(self._tmp.name) / "workspace"
        self.approved.mkdir()
        self.store = LoopStateStore(root=self.approved / ".loop", session_id=SESSION)
        self.request = jx.write_judge_request(
            self.store, target_id=TARGET, target_sha256=SHA_T,
            candidate_resource_id=CANDIDATE, candidate_sha256=SHA_C)
        self.addCleanup(self._tmp.cleanup)


class RequestTests(ExchangeCase):
    def test_request_is_persisted_and_referenced(self) -> None:
        self.assertTrue(self.request.is_file())
        body = json.loads(self.request.read_text(encoding="utf-8"))
        self.assertTrue(body["freshContext"])
        self.assertTrue(body["forbidPromptDraft"])
        kinds = [ref["kind"] for ref in self.store.read().receipt_refs]
        self.assertIn("judge_request", kinds)

    def test_request_validates_against_the_shipped_schema(self) -> None:
        import jsonschema
        schema = json.loads((jx.SCHEMA_DIR / jx.REQUEST_SCHEMA).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(
            json.loads(self.request.read_text(encoding="utf-8")))


class ImportTests(ExchangeCase):
    def test_valid_receipt_is_imported_and_consumable(self) -> None:
        path = jx.import_judge_receipt(self.store, receipt())
        self.assertTrue(path.is_file())
        port = jx.PendingJudgePort(self.store)
        verdict = port.pending()
        self.assertIsInstance(verdict, vl.JudgeVerdict)
        self.assertEqual(verdict.recommendation, "revise")
        self.assertEqual(verdict.scores["total"], 7.5)

    def test_wrong_candidate_digest_is_rejected(self) -> None:
        with self.assertRaises(jx.JudgeExchangeError) as ctx:
            jx.import_judge_receipt(self.store, receipt(candidateSha256="c" * 64))
        self.assertIn("candidateSha256", str(ctx.exception))

    def test_wrong_target_digest_is_rejected(self) -> None:
        with self.assertRaises(jx.JudgeExchangeError):
            jx.import_judge_receipt(self.store, receipt(targetSha256="c" * 64))

    def test_non_fresh_context_is_rejected(self) -> None:
        with self.assertRaises(jx.JudgeExchangeError):
            jx.import_judge_receipt(self.store, receipt(freshContext=False))

    def test_prompt_draft_seen_is_rejected(self) -> None:
        with self.assertRaises(jx.JudgeExchangeError):
            jx.import_judge_receipt(self.store, receipt(sawPromptDraft=True))

    def test_secret_bearing_receipt_is_rejected(self) -> None:
        with self.assertRaises(jx.JudgeExchangeError) as ctx:
            jx.import_judge_receipt(self.store, receipt(extra={"signed_url": "x"}))
        self.assertIn("signed_url", str(ctx.exception))

    def test_malformed_receipt_is_rejected(self) -> None:
        broken = receipt()
        del broken["scores"]
        with self.assertRaises(jx.JudgeExchangeError) as ctx:
            jx.import_judge_receipt(self.store, broken)
        self.assertIn("contract", str(ctx.exception))

    def test_details_above_one_is_rejected(self) -> None:
        scores = {"composition": 3, "lighting": 3, "materials": 3,
                  "details": 2, "total": 11}
        with self.assertRaises(jx.JudgeExchangeError):
            jx.import_judge_receipt(self.store, receipt(scores=scores))

    def test_duplicate_import_for_the_same_request_is_rejected(self) -> None:
        jx.import_judge_receipt(self.store, receipt())
        with self.assertRaises(jx.JudgeExchangeError) as ctx:
            jx.import_judge_receipt(self.store, receipt())
        self.assertIn("duplicate", str(ctx.exception))

    def test_rejection_writes_nothing(self) -> None:
        before = sorted(p.name for p in (self.store.session_dir / "judges").glob("*"))
        try:
            jx.import_judge_receipt(self.store, receipt(candidateSha256="c" * 64))
        except jx.JudgeExchangeError:
            pass
        after = sorted(p.name for p in (self.store.session_dir / "judges").glob("*"))
        self.assertEqual(before, after)


class RestartTests(ExchangeCase):
    def test_restarted_controller_consumes_the_imported_receipt(self) -> None:
        # Round is paused at AWAITING_JUDGE with a pending request on disk.
        state = self.store.read()
        self.assertIsNotNone(jx.current_request_path(self.store))

        # A different process imports the verdict.
        jx.import_judge_receipt(self.store, receipt())

        # The restarted controller sees it through the port only.
        revived_port = jx.PendingJudgePort(self.store)
        verdict = revived_port.pending()
        self.assertIsNotNone(verdict)
        self.assertEqual(verdict.scores["total"], 7.5)
        # And the state still carries the same submit identity — no resubmission.
        self.assertEqual(state.session_id, self.store.read().session_id)


if __name__ == "__main__":
    unittest.main()
