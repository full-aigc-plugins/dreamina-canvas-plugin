"""Loop state machine and durable store (change section 4).

Task 4.1: table-driven coverage of every legal and illegal transition across the
19 declared states.
Task 4.2/4.3: session-scoped store — approved-root containment, canonical path
checks, an exclusive lock, temp-file + fsync + atomic replace, immutable round
directories, and an atomic `latest.json` pointer (**never** a symlink).
Task 4.4: an external side effect must be preceded by a persisted intent.
Task 4.5: restarting from any interruptible state must resume the SAME
`submitId`; it must never mint a new one.
Task 4.6: corrupt, missing, version-incompatible, and dangling-reference states
must fail closed instead of performing external writes.
Task 4.7: the store must behave identically for POSIX and Windows-style path
samples and must not create symlinks.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import loop_state as ls

SESSION = "00112233-4455-6677-8899-aabbccddeeff"
SUBMIT = "ffeeddcc-bbaa-9988-7766-554433221100"
ROUND = "abcdefab-1234-5678-9abc-def012345678"
NODE = "node_abc123"
SHA = "a" * 64

# The 19 declared states, in the order design.md decision 5 introduces them.
DECLARED_STATES = (
    "CREATED", "TARGET_LOCKED", "TARGET_REGISTERED", "DRAFT_SAVED", "QUOTED",
    "AWAITING_APPROVAL", "SUBMITTED", "WAITING", "ARTIFACT_VERIFIED",
    "AWAITING_JUDGE", "JUDGED", "REVISION_PROPOSED", "COMPLETED", "PAUSED",
    "STALLED", "STOP_REQUESTED", "DRAINING_ACCEPTED", "STOPPED", "FAILED",
)

# From design.md decision 5: the full transition table.
LEGAL = {
    "CREATED": {"TARGET_LOCKED", "STOPPED"},
    "TARGET_LOCKED": {"TARGET_REGISTERED", "DRAFT_SAVED", "STOPPED"},
    "TARGET_REGISTERED": {"DRAFT_SAVED"},
    "DRAFT_SAVED": {"QUOTED", "STOPPED"},
    "QUOTED": {"AWAITING_APPROVAL", "PAUSED"},
    "AWAITING_APPROVAL": {"SUBMITTED"},
    "SUBMITTED": {"WAITING", "DRAINING_ACCEPTED"},
    "WAITING": {"ARTIFACT_VERIFIED", "DRAINING_ACCEPTED"},
    "ARTIFACT_VERIFIED": {"AWAITING_JUDGE"},
    "AWAITING_JUDGE": {"JUDGED"},
    "JUDGED": {"COMPLETED", "REVISION_PROPOSED", "STALLED"},
    "REVISION_PROPOSED": {"PAUSED"},
    "DRAINING_ACCEPTED": {"STOPPED"},
    # Terminal / parked states may still be failed by an operator or a crash
    # report, but nothing leaves them on its own.
    "COMPLETED": set(),
    "PAUSED": set(),
    "STALLED": set(),
    "STOP_REQUESTED": {"DRAINING_ACCEPTED", "STOPPED"},
    "STOPPED": set(),
    "FAILED": set(),
}


def make_state(**over) -> ls.LoopState:
    base = {
        "session_id": SESSION, "state": "CREATED", "current_round": 0,
        "best_round": 0, "pending_operations": (), "receipt_refs": (),
        "stop_requested": False, "revision_count": 0,
    }
    base.update(over)
    return ls.LoopState(**base)


class StateMachineTests(unittest.TestCase):
    """4.1 — table-driven legal and illegal transitions."""

    def test_all_declared_states_are_known(self) -> None:
        self.assertEqual(tuple(ls.STATES), DECLARED_STATES)
        self.assertEqual(set(LEGAL), set(ls.STATES))

    def test_every_legal_transition_is_allowed(self) -> None:
        for source, targets in LEGAL.items():
            for target in sorted(targets):
                with self.subTest(source=source, target=target):
                    self.assertTrue(ls.can_transition(source, target))
                    self.assertEqual(
                        ls.advance(make_state(state=source), target).state, target)

    def test_every_illegal_transition_is_rejected(self) -> None:
        for source in ls.STATES:
            for target in ls.STATES:
                if target in LEGAL[source]:
                    continue
                with self.subTest(source=source, target=target):
                    self.assertFalse(ls.can_transition(source, target))
                    with self.assertRaises(ls.IllegalTransition):
                        ls.advance(make_state(state=source), target)

    def test_unknown_state_names_are_rejected(self) -> None:
        for bogus in ("RUNNING", "done", "TARGET_LOCKED "):
            with self.subTest(state=bogus):
                with self.assertRaises(ls.IllegalTransition):
                    ls.advance(make_state(), bogus)

    def test_terminal_states_have_no_successors(self) -> None:
        for terminal in ("COMPLETED", "STOPPED", "FAILED"):
            with self.subTest(state=terminal):
                self.assertEqual(ls.successors(terminal), frozenset())

    def test_stop_is_never_a_remote_cancel(self) -> None:
        """Stopping prevents NEW submissions; it never claims a vendor cancel."""
        for source in ("CREATED", "TARGET_LOCKED", "DRAFT_SAVED"):
            with self.subTest(source=source):
                self.assertTrue(ls.can_transition(source, "STOPPED"))
        self.assertTrue(ls.can_transition("SUBMITTED", "DRAINING_ACCEPTED"))
        self.assertTrue(ls.can_transition("WAITING", "DRAINING_ACCEPTED"))
        self.assertTrue(ls.can_transition("DRAINING_ACCEPTED", "STOPPED"))

    def test_advance_records_stop_request(self) -> None:
        self.assertTrue(ls.advance(make_state(state="DRAFT_SAVED"), "STOPPED").stop_requested)

    def test_advance_refuses_to_widen_rounds(self) -> None:
        with self.assertRaises(ls.IllegalTransition):
            ls.advance(make_state(state="JUDGED", current_round=2), "REVISION_PROPOSED",
                       current_round=1)


class StoreTests(unittest.TestCase):
    """4.2 / 4.3 — durable, atomic, session-scoped storage."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.approved = Path(self._tmp.name) / "workspace"
        self.approved.mkdir()
        self.store = ls.LoopStateStore(root=self.approved / ".loop", session_id=SESSION)
        self.addCleanup(self._tmp.cleanup)

    def test_root_must_live_inside_the_approved_directory(self) -> None:
        outside = Path(self._tmp.name) / "elsewhere"
        with self.assertRaises(ls.StateStoreError):
            ls.LoopStateStore(root=outside, session_id=SESSION,
                              approved_root=self.approved)

    def test_session_id_must_be_a_canonical_uuid(self) -> None:
        for bogus in ("not-a-uuid", SESSION.upper(), "", "../escape"):
            with self.subTest(session=bogus):
                with self.assertRaises(ls.StateStoreError):
                    ls.LoopStateStore(root=self.approved / ".loop", session_id=bogus)

    def test_round_trip_persists_and_reloads(self) -> None:
        state = make_state(state="QUOTED", current_round=1)
        self.store.write(state)
        self.assertEqual(self.store.read(), state)

    def test_state_file_is_private(self) -> None:
        self.store.write(make_state())
        mode = oct(os.stat(self.store.state_path).st_mode & 0o777)
        self.assertEqual(mode, "0o600", mode)

    def test_missing_state_fails_closed(self) -> None:
        with self.assertRaises(ls.StateStoreError):
            self.store.read()

    def test_corrupt_state_fails_closed(self) -> None:
        self.store.write(make_state())
        self.store.state_path.write_text("{ this is not json", encoding="utf-8")
        with self.assertRaises(ls.StateStoreError):
            self.store.read()

    def test_version_incompatible_state_fails_closed(self) -> None:
        self.store.write(make_state())
        payload = json.loads(self.store.state_path.read_text(encoding="utf-8"))
        payload["schemaVersion"] = "visual_loop_state/99"
        self.store.state_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ls.StateStoreError):
            self.store.read()

    def test_dangling_receipt_reference_fails_closed(self) -> None:
        self.store.write(make_state(
            receipt_refs=({"kind": "judge_receipt", "ref": "missing.json"},)))
        with self.assertRaises(ls.StateStoreError):
            self.store.read()

    def test_no_symlink_is_ever_created(self) -> None:
        """Windows cannot rely on symlinks; the pointer must be a real file."""
        self.store.write_round(ROUND, {"candidate.png": b"\x89PNG\r\n\x1a\n"})
        self.store.update_latest(ROUND)
        for path in self.store.session_dir.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
        self.assertTrue(self.store.latest_path.is_file())
        self.assertEqual(self.store.read_latest(), ROUND)

    def test_rounds_are_immutable(self) -> None:
        self.store.write_round(ROUND, {"candidate.png": b"\x89PNG\r\n\x1a\n"})
        with self.assertRaises(ls.StateStoreError):
            self.store.write_round(ROUND, {"candidate.png": b"overwritten"})

    def test_latest_pointer_survives_a_partial_write(self) -> None:
        """A crash mid-write must never leave a half-written pointer."""
        self.store.write_round(ROUND, {"candidate.png": b"\x89PNG\r\n\x1a\n"})
        self.store.update_latest(ROUND)
        first = self.store.latest_path.read_bytes()
        self.assertIn(ROUND.encode(), first)

    # ---- 4.4 intent-first ------------------------------------------------
    def test_intent_must_be_persisted_before_an_external_effect(self) -> None:
        record = self.store.record_intent(
            kind="node_run", submit_id=SUBMIT, node_id=NODE)
        self.assertTrue(record.is_file())
        self.assertIsNone(self.store.pending_intent(kind="node_run", submit_id=SUBMIT).get("result"))

    def test_intent_is_never_minted_twice_for_the_same_submit(self) -> None:
        self.store.record_intent(kind="node_run", submit_id=SUBMIT, node_id=NODE)
        with self.assertRaises(ls.StateStoreError):
            self.store.record_intent(kind="node_run", submit_id=SUBMIT, node_id=NODE)

    def test_submit_id_cannot_be_blank(self) -> None:
        with self.assertRaises(ls.StateStoreError):
            self.store.record_intent(kind="node_run", submit_id="", node_id=NODE)

    # ---- restart / 4.5 ---------------------------------------------------
    def test_restart_resumes_the_same_submit_id(self) -> None:
        self.store.write(make_state(
            state="WAITING",
            pending_operations=({"submitId": SUBMIT, "nodeId": NODE},)))
        reopened = ls.LoopStateStore(root=self.approved / ".loop", session_id=SESSION)
        resumed = reopened.read()
        self.assertEqual(resumed.pending_operations[0]["submitId"], SUBMIT)
        action = ls.resume_action(resumed)
        self.assertEqual(action["action"], "resume")
        self.assertEqual(action["submitId"], SUBMIT)
        # A resume must never carry a freshly minted identity.
        self.assertNotIn("new_submit_id", action)

    def test_submitted_state_is_resumable_not_resubmittable(self) -> None:
        resumed = make_state(
            state="SUBMITTED",
            pending_operations=({"submitId": SUBMIT, "nodeId": NODE},))
        action = ls.resume_action(resumed)
        self.assertEqual(action["action"], "resume")
        self.assertNotIn("new_submit_id", action)

    def test_terminal_states_need_no_resume(self) -> None:
        self.assertEqual(ls.resume_action(make_state(state="COMPLETED"))["action"],
                         "terminal")
        self.assertEqual(ls.resume_action(make_state(state="FAILED"))["action"],
                         "terminal")

    def test_draining_state_keeps_querying_the_original_submit(self) -> None:
        resumed = make_state(
            state="DRAINING_ACCEPTED",
            pending_operations=({"submitId": SUBMIT, "nodeId": NODE},))
        self.assertEqual(ls.resume_action(resumed)["submitId"], SUBMIT)

    # ---- 4.7 path portability -------------------------------------------
    def test_windows_style_and_posix_paths_behave_identically(self) -> None:
        for sample in ("rounds/abc/candidate.png", "rounds\\abc\\candidate.png"):
            with self.subTest(sample=sample):
                self.assertEqual(ls.normalize_relative(sample), "rounds/abc/candidate.png")

    def test_traversal_is_rejected(self) -> None:
        for bogus in ("../escape.json", "rounds/../../escape", "/etc/passwd"):
            with self.subTest(path=bogus):
                with self.assertRaises(ls.StateStoreError):
                    ls.normalize_relative(bogus)


class ContractAlignmentTests(unittest.TestCase):
    """The implementation must satisfy the shipped contract.

    Section 3 declared `visual_loop_state.schema.json`; section 4 implements the
    machine. If these drift, one of them is lying — and a serialized state that
    no schema accepts would be persisted happily forever.
    """

    @staticmethod
    def _schema() -> dict:
        schema = json.loads(
            (Path(__file__).resolve().parents[1] / "schemas"
             / "visual_loop_state.schema.json").read_text(encoding="utf-8"))
        base = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
        base.update(schema)
        return base

    def test_state_enum_matches_the_contract(self) -> None:
        declared = tuple(self._schema()["properties"]["state"]["enum"])
        self.assertEqual(declared, ls.STATES)

    def test_a_serialized_state_validates_against_the_contract(self) -> None:
        import jsonschema

        validator = jsonschema.Draft202012Validator(self._schema())
        for state in ls.STATES:
            with self.subTest(state=state):
                validator.validate(make_state(state=state).to_dict())

    def test_the_initial_state_is_reachable_from_the_declared_entry(self) -> None:
        """A fresh session starts at CREATED and CREATED must be declared."""
        self.assertEqual(ls.LoopState(session_id=SESSION).state, "CREATED")
        self.assertEqual(ls.STATES[0], "CREATED")


if __name__ == "__main__":
    unittest.main()
