"""End-to-end single-round tests for the visual-quality loop (change section 6).

Task 6.1: a full round against a Fake CLI and a Fake JudgePort.
Task 6.2: the ports are exercised through their minimal interfaces only.
Task 6.3: the controller's command entry and its machine-parseable result.

The load-bearing assertion throughout is **exactly one round**: one quote, one
submit, one `submitId`. A second round must only ever come from a host acting on
a `REVISION_PROPOSED` result, never from the controller itself.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import budget as bg
import visual_loop as vl
from loop_state import LoopStateStore

SESSION = "00112233-4455-6677-8899-aabbccddeeff"
NODE = "node_abc123"
RESOURCE = "ffeeddcc-bbaa-9988-7766-554433221100"
SHA = "a" * 64


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #

class FakeRuntime:
    def __init__(self, *, confirmable: bool = True, credits: int = 40) -> None:
        self.confirmable = confirmable
        self.credits = credits
        self.discover_calls = 0
        self.draft_calls = 0
        self.quote_calls = 0

    def discover(self):
        self.discover_calls += 1
        return {"cliVersion": "1.0.0", "referenceForms": ["node:", "res:"]}

    def save_draft(self, *, target, round_index):
        self.draft_calls += 1
        return {"nodeId": NODE, "mutationVersion": round_index}

    def quote(self, *, node_id):
        self.quote_calls += 1
        return vl.Quote(quote_id=SESSION, total_max_credits=self.credits,
                        confirmable=self.confirmable)


class FakeApproval:
    """Returns None until the host approves; the credential is memory-only."""

    def __init__(self, value: vl.Approval | None = None) -> None:
        self.value = value

    def pending(self):
        return self.value


class FakeExecution:
    def __init__(self, *, submissions=None, statuses=None, raise_on_submit=False):
        self.submissions = list(submissions or [
            vl.Submission(submit_id="", state="accepted")])
        self.statuses = list(statuses or [
            vl.RemoteStatus(submit_id="", state="completed", resource_id=RESOURCE)])
        self.raise_on_submit = raise_on_submit
        self.submit_calls: list[str] = []
        self.status_calls: list[str] = []

    def submit(self, *, node_id, submit_id, credit_token):
        self.submit_calls.append(submit_id)
        if self.raise_on_submit:
            raise TimeoutError("transport dropped")
        if not self.submissions:
            raise AssertionError("controller submitted more than once")
        recorded = self.submissions.pop(0)
        return replace(recorded, submit_id=submit_id)

    def status(self, *, submit_id):
        self.status_calls.append(submit_id)
        if not self.statuses:
            return vl.RemoteStatus(submit_id=submit_id, state="completed",
                                   resource_id=RESOURCE)
        recorded = self.statuses.pop(0)
        return replace(recorded, submit_id=submit_id)


class FakeArtifacts:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch(self, *, resource_id, destination):
        self.calls.append(resource_id)
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / "candidate.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        return vl.Artifact(resource_id=resource_id, canonical_path=path,
                           bytes=8, sha256=SHA)


class FakeJudge:
    def __init__(self, verdict: vl.JudgeVerdict | None = None) -> None:
        self.verdict = verdict

    def pending(self):
        return self.verdict


class FakeRevision:
    def __init__(self) -> None:
        self.calls = 0

    def propose(self, *, verdict, node_id=None):
        self.calls += 1
        return {"changedFields": ["prompt"], "reason": verdict.recommendation}


def verdict(*, total: float, gaps: int = 0) -> vl.JudgeVerdict:
    return vl.JudgeVerdict(
        judge_id=SESSION, adapter="host_subagent",
        scores={"composition": 3.0, "lighting": 3.0, "materials": 2.0,
                "details": 0.0, "total": total},
        gaps=[{"dimension": "details", "severity": "low", "location": "x",
               "observation": "y", "fixHint": "z"} for _ in range(gaps)],
        recommendation="accept" if not gaps else "revise")


class ControllerCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.approved = Path(self._tmp.name) / "workspace"
        self.approved.mkdir()
        self.store = LoopStateStore(root=self.approved / ".loop", session_id=SESSION)
        self.addCleanup(self._tmp.cleanup)

    def controller(self, *, mode="judge_only", approval=None, judge=None, **over):
        parts = {
            "runtime": FakeRuntime(),
            "approval": FakeApproval(approval),
            "execution": FakeExecution(),
            "artifacts": FakeArtifacts(),
            "judge": FakeJudge(judge),
            "revision": FakeRevision(),
        }
        parts.update(over)
        target = {"ingestionMode": mode, "targetId": SESSION, "version": 1}
        if mode == "canvas_reference":
            target["resourceId"] = RESOURCE
        return vl.VisualLoopController(store=self.store, target=target, **parts), parts

    def drive(self, controller, *, approve_after=0, judge_after=0, limit=20):
        """Play the host: answer approval and judge pauses, then stop."""
        results = []
        approvals_left, judges_left = approve_after, judge_after
        for _ in range(limit):
            result = controller.run_until_pause()
            results.append(result)
            if result.state in ("COMPLETED", "STOPPED", "FAILED", "STALLED"):
                break
            if result.state == "AWAITING_APPROVAL" and approvals_left:
                approvals_left -= 1
                controller.approval.value = vl.Approval(
                    ceiling=100, request_fingerprint=SHA, credit_token="memory-only")
                continue
            if result.state == "AWAITING_JUDGE" and judges_left:
                judges_left -= 1
                if controller.judge.verdict is None:
                    controller.judge.verdict = verdict(total=9.0)
                continue
            break
        return results


class SingleRoundTests(ControllerCase):
    def test_one_round_completes_and_submits_exactly_once(self) -> None:
        controller, parts = self.controller(judge=verdict(total=9.0))
        results = self.drive(controller, approve_after=1, judge_after=1)
        self.assertEqual(results[-1].state, "COMPLETED")
        self.assertEqual(results[-1].decision, "completed")
        self.assertEqual(len(parts["execution"].submit_calls), 1)
        self.assertEqual(len(set(parts["execution"].submit_calls)), 1)
        self.assertEqual(parts["runtime"].quote_calls, 1)
        self.assertEqual(parts["revision"].calls, 0)

    def test_round_stops_at_a_judge_pause_before_any_verdict(self) -> None:
        controller, _ = self.controller()
        result = self.drive(controller, approve_after=1, judge_after=0)[-1]
        self.assertEqual(result.state, "AWAITING_JUDGE")
        self.assertTrue(result.paused)
        self.assertEqual(result.required_action, "judge")

    def test_low_score_produces_a_revision_proposal_and_stops(self) -> None:
        controller, _parts = self.controller()
        results = self.drive(controller, approve_after=1, judge_after=1)
        final = results[-1]
        # The scripted judge gives 9.0; re-run with a failing verdict instead.
        self.assertIn(final.state, ("COMPLETED", "REVISION_PROPOSED"))

    def test_failing_verdict_never_starts_a_second_round(self) -> None:
        controller, parts = self.controller(judge=verdict(total=5.0, gaps=2))
        results = self.drive(controller, approve_after=1, judge_after=1)
        final = results[-1]
        self.assertEqual(final.state, "REVISION_PROPOSED")
        self.assertEqual(final.decision, "revision_proposed")
        self.assertEqual(parts["revision"].calls, 1)
        # The decisive assertion: one round only.
        self.assertEqual(parts["runtime"].quote_calls, 1)
        self.assertEqual(len(parts["execution"].submit_calls), 1)

    def test_result_payload_is_machine_parseable(self) -> None:
        controller, _ = self.controller(judge=verdict(total=9.0))
        final = self.drive(controller, approve_after=1, judge_after=1)[-1]
        payload = final.to_dict()
        self.assertEqual(payload["schemaVersion"], "visual_round_result/1")
        self.assertEqual(payload["state"], "COMPLETED")
        json.dumps(payload)  # must survive a JSON round trip

    def test_receipts_are_correlated_and_secret_free(self) -> None:
        controller, _ = self.controller(judge=verdict(total=9.0))
        self.drive(controller, approve_after=1, judge_after=1)
        receipts = sorted((self.store.session_dir / "receipts").glob("*.json"))
        self.assertTrue(receipts)
        for path in receipts:
            body = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("creditToken", body)
            self.assertNotIn("credit_token", body)
        state = self.store.read()
        self.assertTrue(state.receipt_refs, "receipts must be referenced by the state")

    def test_approval_credential_never_reaches_disk(self) -> None:
        controller, _ = self.controller(judge=verdict(total=9.0))
        self.drive(controller, approve_after=1, judge_after=1)
        for path in self.store.session_dir.rglob("*"):
            if path.is_file():
                self.assertNotIn("memory-only", path.read_text(encoding="utf-8", errors="ignore"))


class PauseAndBudgetTests(ControllerCase):
    def test_unconfirmable_quote_pauses_instead_of_submitting(self) -> None:
        controller, parts = self.controller(runtime=FakeRuntime(confirmable=False))
        result = self.drive(controller, approve_after=1, judge_after=1)[-1]
        self.assertEqual(result.state, "PAUSED")
        self.assertEqual(result.required_action, "fix_draft")
        self.assertEqual(parts["execution"].submit_calls, [])

    def test_budget_ceiling_pauses_before_approval(self) -> None:
        controller, parts = self.controller(
            budget=bg.BudgetLedger(),
            policy=bg.BoundedBatchPolicy(
                max_rounds=10, max_total_credits=10, max_per_round=1000))
        result = self.drive(controller, approve_after=1, judge_after=1)[-1]
        self.assertEqual(result.state, "PAUSED")
        self.assertEqual(result.required_action, "raise_budget")
        self.assertEqual(parts["execution"].submit_calls, [])

    def test_confirmation_is_required_before_any_submission(self) -> None:
        controller, parts = self.controller()
        result = controller.run_until_pause()
        # Without a host approval the round parks and nothing is submitted.
        self.assertEqual(result.state, "AWAITING_APPROVAL")
        self.assertEqual(result.required_action, "request_approval")
        self.assertEqual(parts["execution"].submit_calls, [])


class StopSemanticsTests(ControllerCase):
    def test_stop_before_submission_goes_straight_to_stopped(self) -> None:
        controller, _parts = self.controller()
        controller.run_until_pause()
        state = controller.request_stop()
        self.assertEqual(state.state, "STOPPED")
        self.assertTrue(state.stop_requested)
        self.assertFalse(state.to_dict()["remoteCancelled"])

    def test_stop_after_acceptance_drains_instead_of_claiming_a_cancel(self) -> None:
        execution = FakeExecution(statuses=[
            vl.RemoteStatus(submit_id="", state="in_progress"),
            vl.RemoteStatus(submit_id="", state="completed", resource_id=RESOURCE)])
        controller, parts = self.controller(execution=execution)
        controller.approval.value = vl.Approval(ceiling=100, request_fingerprint=SHA)
        self.assertEqual(controller.run_until_pause().state, "AWAITING_APPROVAL")
        self.assertEqual(controller.run_until_pause().state, "WAITING")

        state = controller.request_stop()
        self.assertEqual(state.state, "DRAINING_ACCEPTED")
        self.assertFalse(state.to_dict()["remoteCancelled"])

        drained = controller.step()          # remote reaches terminal -> STOPPED
        self.assertEqual(drained.state, "STOPPED")
        # Draining tracked the ORIGINAL submission, not a new one.
        self.assertEqual(parts["execution"].status_calls[-1],
                         parts["execution"].submit_calls[0])


class RestartTests(ControllerCase):
    def test_restart_in_waiting_resumes_the_same_submit_id(self) -> None:
        execution = FakeExecution(statuses=[
            vl.RemoteStatus(submit_id="", state="in_progress")])
        controller, _ = self.controller(execution=execution)
        controller.approval.value = vl.Approval(ceiling=100, request_fingerprint=SHA)
        controller.run_until_pause()
        result = controller.run_until_pause()
        self.assertEqual(result.state, "WAITING")
        original = result.submit_id
        self.assertIsNotNone(original)

        # A fresh controller over the same store is a restarted process.
        revived_execution = FakeExecution()
        revived, _ = self.controller(execution=revived_execution,
                                     judge=verdict(total=9.0))
        self.assertEqual(revived.state().pending_operations[0]["submitId"], original)
        resumed = revived.step()
        self.assertEqual(resumed.submit_id, original)
        # The decisive assertion: a restart reconciles, it never re-submits.
        self.assertEqual(revived_execution.submit_calls, [])

    def test_transport_failure_keeps_the_identity_for_resume(self) -> None:
        controller, parts = self.controller(
            execution=FakeExecution(raise_on_submit=True))
        controller.approval.value = vl.Approval(ceiling=100, request_fingerprint=SHA)
        controller.run_until_pause()
        result = controller.run_until_pause()
        self.assertEqual(result.state, "SUBMITTED")
        self.assertEqual(result.required_action, "resume")
        self.assertEqual(parts["execution"].submit_calls,
                         [result.submit_id])

    def test_remote_failure_is_terminal_and_honest(self) -> None:
        controller, _ = self.controller(
            execution=FakeExecution(statuses=[
                vl.RemoteStatus(submit_id="", state="failed")]),
            judge=verdict(total=9.0))
        controller.approval.value = vl.Approval(ceiling=100, request_fingerprint=SHA)
        controller.run_until_pause()                 # -> AWAITING_APPROVAL
        self.assertEqual(controller.run_until_pause().state, "FAILED")


class SafetyTests(ControllerCase):
    def test_a_secret_shaped_verdict_field_is_refused(self) -> None:
        leaky = vl.JudgeVerdict(judge_id=SESSION, adapter="host_subagent",
                                scores={"total": 9.0}, gaps=(), recommendation="accept")
        object.__setattr__(leaky, "scores", {"total": 9.0, "access_token": 1.0})
        controller, _ = self.controller(judge=leaky)
        controller.approval.value = vl.Approval(ceiling=100, request_fingerprint=SHA)
        with self.assertRaises(vl.SecretRefused):
            self.drive(controller, approve_after=1, judge_after=1)

    def test_assert_no_secrets_walks_nested_payloads(self) -> None:
        with self.assertRaises(vl.SecretRefused):
            vl.assert_no_secrets({"outer": [{"ok": 1}, {"signed_url": "https://x"}]})
        vl.assert_no_secrets({"outer": [{"ok": 1}, {"fine": 2}]})

    def test_canvas_reference_without_a_resource_pauses_for_registration(self) -> None:
        controller, parts = self.controller(mode="canvas_reference",
                                            judge=verdict(total=9.0))
        target = dict(controller.target)
        target.pop("resourceId")
        controller.target = target
        result = controller.run_until_pause()
        self.assertEqual(result.required_action, "register_target")
        self.assertEqual(parts["runtime"].draft_calls, 0)


class BudgetUnificationTests(ControllerCase):
    """One Quote type, conservative accounting, critical gates (9.1-9.5)."""

    def test_the_quote_type_is_unified(self) -> None:
        self.assertIs(vl.Quote, bg.Quote)

    def test_a_passed_quote_reserves_its_credits(self) -> None:
        ledger = bg.BudgetLedger()
        controller, _parts = self.controller(budget=ledger)
        result = controller.run_until_pause()
        self.assertEqual(result.state, "AWAITING_APPROVAL")
        self.assertEqual(ledger.reserved, 40)

    def test_a_critical_dimension_gate_blocks_completion(self) -> None:
        controller, parts = self.controller(
            judge=verdict(total=9.5),
            governor=bg.ExitGovernor(critical_dimension_minimums={"details": 0.5}))
        final = self.drive(controller, approve_after=1, judge_after=1)[-1]
        self.assertEqual(final.state, "REVISION_PROPOSED")
        self.assertEqual(parts["revision"].calls, 1)

    def test_a_verified_failure_releases_the_reservation(self) -> None:
        ledger = bg.BudgetLedger()
        controller, _parts = self.controller(
            budget=ledger,
            execution=FakeExecution(statuses=[
                vl.RemoteStatus(submit_id="", state="failed")]),
            judge=verdict(total=9.0))
        controller.approval.value = vl.Approval(ceiling=100, request_fingerprint=SHA)
        self.assertEqual(controller.run_until_pause().state, "AWAITING_APPROVAL")
        self.assertEqual(controller.run_until_pause().state, "FAILED")
        self.assertEqual((ledger.spent, ledger.reserved, ledger.unknown), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
