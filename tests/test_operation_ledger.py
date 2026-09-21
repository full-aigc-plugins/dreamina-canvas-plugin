import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from operation_ledger import (
    OperationReceipt,
    RecoveryDecision,
    decide,
    persist,
)

SUBMIT = "submit_b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6"


def r(state="in_progress", resubmittable=False, submit=SUBMIT):
    return OperationReceipt(
        project_id="proj_00112233445566778899aabbccddeeff",
        node_id="node_aaaaaaaaaaaa",
        submit_id=submit,
        last_known_state=state,
        resubmittable=resubmittable,
        request_fingerprint="sha256:deadbeef",
        exit_code=0,
        timestamp="2026-09-12T00:00:00Z",
    )


class OperationLedgerTests(unittest.TestCase):
    def test_process_restart_no_local_record(self) -> None:
        action, _ = decide(None, SUBMIT)
        self.assertEqual(action, RecoveryDecision.RESUME)

    def test_empty_submit_id_rejected(self) -> None:
        action, _reason = decide(r(submit=""), "")
        self.assertEqual(action, RecoveryDecision.REJECT_EMPTY_SUBMIT_ID)

    def test_in_progress_continues(self) -> None:
        action, _ = decide(r(state="in_progress"), SUBMIT)
        self.assertEqual(action, RecoveryDecision.RESUME)

    def test_completed_terminal(self) -> None:
        action, _ = decide(r(state="completed"), SUBMIT)
        self.assertEqual(action, RecoveryDecision.TERMINAL_SUCCESS)

    def test_absent_resubmittable_escalates(self) -> None:
        action, _ = decide(r(state="absent", resubmittable=True), SUBMIT)
        self.assertEqual(action, RecoveryDecision.ESCALATE)

    def test_absent_without_resubmittable_treated_as_accepted(self) -> None:
        action, _ = decide(r(state="absent", resubmittable=False), SUBMIT)
        self.assertEqual(action, RecoveryDecision.RESUME)

    def test_persist_atomic_0600(self) -> None:
        if os.name == "nt":
            # NTFS has no POSIX mode bits; the 0600 invariant is POSIX-scoped.
            self.skipTest("POSIX permission bits do not exist on Windows")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = persist(r(state="in_progress"), root, "default/cn")
            self.assertTrue(target.is_file())
            mode = target.stat().st_mode & 0o777
            self.assertEqual(mode, 0o600)
            data = json.loads(target.read_text())
            for required in (
                "projectId",
                "nodeId",
                "submitId",
                "last_known_state",
                "resubmittable",
            ):
                self.assertIn(required, data)

    def test_persist_rejects_forbidden_fields(self) -> None:
        bad = r()
        bad.extra["creditConfirmationToken"] = "secret"
        with tempfile.TemporaryDirectory() as td, self.assertRaises(ValueError):
            persist(bad, Path(td), "default/cn")


if __name__ == "__main__":
    unittest.main()
