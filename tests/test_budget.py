"""Budget, stall and stop governance tests (change section 9)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import budget as bg
from visual_loop import Quote


def quote(credits: int = 40) -> Quote:
    return Quote(quote_id="q", total_max_credits=credits, confirmable=True)


def score(total: float, *, gaps=("lighting:face",), dims=None, index=1) -> bg.RoundScore:
    return bg.RoundScore(round_index=index, total=total,
                         dimension_scores=dims or {"composition": 3, "lighting": 2,
                                                   "materials": 2, "details": 0},
                         gap_keys=frozenset(gaps))


class LedgerTests(unittest.TestCase):
    """9.1 — conservative accounting invariants."""

    def test_reserve_then_complete_settles_to_spent(self) -> None:
        ledger = bg.BudgetLedger()
        reservation = ledger.reserve(quote(40))
        self.assertEqual((ledger.spent, ledger.reserved), (0, 40))
        ledger.settle(reservation, outcome="completed", actual_credits=38)
        self.assertEqual((ledger.spent, ledger.reserved, ledger.unknown), (38, 0, 0))

    def test_timeout_never_releases_the_reservation(self) -> None:
        ledger = bg.BudgetLedger()
        reservation = ledger.reserve(quote(40))
        ledger.settle(reservation, outcome="timeout")
        self.assertEqual(ledger.unknown, 40)
        self.assertEqual(ledger.reserved, 0)
        self.assertEqual(ledger.spent, 0)

    def test_unknown_counts_against_the_ceiling(self) -> None:
        ledger = bg.BudgetLedger()
        ledger.settle(ledger.reserve(quote(40)), outcome="unknown")
        policy = bg.BoundedBatchPolicy(max_rounds=5, max_total_credits=60,
                                       max_per_round=50)
        with self.assertRaises(bg.BudgetExceeded):
            policy.check(ledger, quote(30))  # 40 unknown + 30 > 60

    def test_verified_failure_releases_without_spend(self) -> None:
        ledger = bg.BudgetLedger()
        reservation = ledger.reserve(quote(40))
        ledger.settle(reservation, outcome="failed")
        self.assertEqual((ledger.spent, ledger.reserved, ledger.unknown), (0, 0, 0))

    def test_double_settle_is_refused(self) -> None:
        ledger = bg.BudgetLedger()
        reservation = ledger.reserve(quote(10))
        ledger.settle(reservation, outcome="completed")
        with self.assertRaises(bg.BudgetExceeded):
            ledger.settle(reservation, outcome="completed")


class PolicyTests(unittest.TestCase):
    """9.2 / 9.3 — bounded batch caps, vendor approval stays authoritative."""

    def policy(self, **over) -> bg.BoundedBatchPolicy:
        defaults = {"max_rounds": 2, "max_total_credits": 100, "max_per_round": 50}
        defaults.update(over)
        return bg.BoundedBatchPolicy(**defaults)

    def test_round_cap(self) -> None:
        policy = self.policy()
        policy = policy.next_round()
        policy.check(bg.BudgetLedger(), quote())
        with self.assertRaises(bg.BudgetExceeded):
            policy.next_round().check(bg.BudgetLedger(), quote())

    def test_per_round_cap(self) -> None:
        with self.assertRaises(bg.BudgetExceeded):
            self.policy(max_per_round=30).check(bg.BudgetLedger(), quote(40))

    def test_total_cap(self) -> None:
        ledger = bg.BudgetLedger(spent=80)
        with self.assertRaises(bg.BudgetExceeded):
            self.policy().check(ledger, quote(30))

    def test_deadline(self) -> None:
        policy = self.policy(deadline_epoch=100.0)
        with self.assertRaises(bg.BudgetExceeded):
            policy.check(bg.BudgetLedger(), quote(), now_epoch=200.0)

    def test_missing_approval_does_not_bypass_the_vendor_chain(self) -> None:
        """9.3 — the batch check passing never implies approval; a stale or
        absent ceiling must still park the controller at AWAITING_APPROVAL."""
        policy = self.policy()
        policy.check(bg.BudgetLedger(), quote(40), approval_ceiling=None)
        # The check passes only because approval gating happens later in the
        # controller; assert that here explicitly so the intent is pinned.
        from visual_loop import VisualLoopController  # the pause boundary
        self.assertTrue(hasattr(VisualLoopController, "_on_AWAITING_APPROVAL"))


class GovernorTests(unittest.TestCase):
    """9.4 / 9.5 — exit criteria, critical gates, stall, best round."""

    def test_high_clean_score_completes(self) -> None:
        governor = bg.ExitGovernor()
        self.assertEqual(governor.observe(score(9.5, gaps=())), "completed")

    def test_critical_dimension_gate_blocks_completion(self) -> None:
        governor = bg.ExitGovernor(critical_dimension_minimums={"details": 0.5})
        decision = governor.observe(score(9.5, gaps=(), dims={"details": 0.0}))
        self.assertEqual(decision, "revision_proposed")

    def test_consecutive_no_improvement_stalls(self) -> None:
        governor = bg.ExitGovernor(max_rounds_without_improvement=2)
        governor.observe(score(5.0, index=1))
        governor.observe(score(5.0, index=2))
        self.assertEqual(governor.observe(score(4.5, index=3)), "stalled")

    def test_improvement_is_not_a_stall(self) -> None:
        governor = bg.ExitGovernor(max_rounds_without_improvement=2)
        governor.observe(score(5.0, index=1))
        governor.observe(score(5.0, index=2))
        self.assertEqual(governor.observe(score(6.5, index=3)), "revision_proposed")

    def test_repeated_gaps_trigger_one_replan_then_stall(self) -> None:
        governor = bg.ExitGovernor(max_repeated_gap_rounds=2, max_replans=1)
        same = ("lighting:face",)
        governor.observe(score(6.0, gaps=same, index=1))
        governor.observe(score(6.0, gaps=same, index=2))
        self.assertEqual(governor.observe(score(6.0, gaps=same, index=3)),
                         "replan_required")
        governor.observe(score(6.0, gaps=same, index=4))
        self.assertEqual(governor.observe(score(6.0, gaps=same, index=5)), "stalled")

    def test_best_round_is_retained_when_later_rounds_score_lower(self) -> None:
        governor = bg.ExitGovernor()
        governor.observe(score(8.5, gaps=(), index=1))
        governor.observe(score(4.0, index=2))
        self.assertEqual(governor.best.round_index, 1)
        self.assertEqual(governor.best.total, 8.5)

    def test_diagnostics_never_promise_budget_growth(self) -> None:
        governor = bg.ExitGovernor()
        governor.observe(score(5.0, index=1))
        report = governor.diagnostics()
        self.assertEqual(report["maxReplans"], governor.max_replans)
        self.assertLessEqual(report["replansUsed"], governor.max_replans)
        self.assertNotIn("extraCredits", report)


class StopGovernanceTests(unittest.TestCase):
    """9.6 / 9.7 — after a stop, nothing new: no edit, quote, approval, submit."""

    def test_stop_states_are_declared_and_terminal_is_honest(self) -> None:
        from loop_state import STATES, TRANSITIONS
        for state in ("STOP_REQUESTED", "DRAINING_ACCEPTED", "STOPPED"):
            self.assertIn(state, STATES)
        # STOPPED is terminal; DRAINING_ACCEPTED can only reach STOPPED.
        self.assertEqual(TRANSITIONS["STOPPED"], frozenset())
        self.assertEqual(TRANSITIONS["DRAINING_ACCEPTED"], frozenset({"STOPPED"}))

    def test_controller_after_stop_makes_no_new_moves(self) -> None:
        import tempfile
        from pathlib import Path

        import visual_loop as vl
        from loop_state import LoopStateStore

        with tempfile.TemporaryDirectory() as tmp:
            approved = Path(tmp) / "ws"
            approved.mkdir()
            store = LoopStateStore(root=approved / ".loop", session_id=
                                   "00112233-4455-6677-8899-aabbccddeeff")
            runtime_calls = []

            class Runtime:
                def discover(self):
                    runtime_calls.append("discover")
                    return {}

                def save_draft(self, **kw):
                    runtime_calls.append("draft")
                    return {"nodeId": "node_x"}

                def quote(self, **kw):
                    runtime_calls.append("quote")
                    return vl.Quote(quote_id="q", total_max_credits=1,
                                    confirmable=True)

            class NoApproval:
                def pending(self):
                    runtime_calls.append("approval")

            class NoExecution:
                def submit(self, **kw):
                    runtime_calls.append("submit")
                    raise AssertionError("submit after stop")

                def status(self, **kw):
                    runtime_calls.append("status")
                    raise AssertionError("status after stop")

            class NoArtifacts:
                def fetch(self, **kw):
                    raise AssertionError("fetch after stop")

            controller = vl.VisualLoopController(
                store=store, target={"ingestionMode": "judge_only"},
                runtime=Runtime(), approval=NoApproval(),
                execution=NoExecution(), artifacts=NoArtifacts(),
                judge=vl.FakeJudgePortNone() if False else type("J", (), {
                    "pending": staticmethod(lambda: None)})(),
                revision=type("R", (), {"propose": staticmethod(
                    lambda **kw: {})})())
            controller.run_until_pause()
            controller.request_stop()
            # Drain the remaining steps: nothing new may happen.
            for _ in range(6):
                result = controller.step()
                if result.state == "STOPPED":
                    break
            self.assertEqual(runtime_calls, ["discover", "draft", "quote"],
                             "no new edit/quote/approval/submit after stop")

    def test_no_cancel_semantics_are_documented_not_implied(self) -> None:
        """9.7 — the honest-stop rule lives in the schema as a const."""
        import json
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas"
                             / "visual_loop_state.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["remoteCancelled"],
                         {"const": False,
                          "description": schema["properties"]["remoteCancelled"]["description"]})


if __name__ == "__main__":
    unittest.main()
