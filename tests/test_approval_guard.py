import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from approval_guard import (
    Approval,
    Quote,
    RunRequest,
    check_approval,
    mark_used,
)

PROJECT = "proj_00112233445566778899aabbccddeeff"
NODE_A = "node_aaaaaaaaaaaa"
NODE_B = "node_bbbbbbbbbbbb"


def q(total=120, confirmable=True, ceiling=150):
    return Quote(
        project_id=PROJECT,
        ordered_node_ids=(NODE_A, NODE_B),
        total_max_credits=total,
        ceiling=ceiling,
        confirmable=confirmable,
    )


def a(total=200):
    return Approval(
        project_id=PROJECT, ordered_node_ids=(NODE_A, NODE_B), ceiling=total
    )


def r(total=120):
    return RunRequest(
        project_id=PROJECT, ordered_node_ids=(NODE_A, NODE_B), latest_total=total
    )


class ApprovalGuardTests(unittest.TestCase):
    def test_no_quote_confirmable_false(self) -> None:
        decision = check_approval(q(confirmable=False), a(), r())
        self.assertFalse(decision.ok)
        self.assertIn("confirmable=false", decision.reason)

    def test_ceiling_below_total_rejected(self) -> None:
        decision = check_approval(q(total=200), a(total=150), r(total=180))
        self.assertFalse(decision.ok)
        self.assertIn("below quote.totalMaxCredits", decision.reason)

    def test_changed_project_rejected(self) -> None:
        decision = check_approval(q(), Approval(project_id="other", ordered_node_ids=(NODE_A,), ceiling=200), r())
        self.assertFalse(decision.ok)

    def test_changed_ordered_node_set_rejected(self) -> None:
        decision = check_approval(q(), Approval(project_id=PROJECT, ordered_node_ids=(NODE_A,), ceiling=200), r())
        self.assertFalse(decision.ok)

    def test_replay_rejected(self) -> None:
        approval = mark_used(a())
        decision = check_approval(q(), approval, r())
        self.assertFalse(decision.ok)
        self.assertIn("already been used", decision.reason)

    def test_latest_total_above_ceiling_rejected(self) -> None:
        # quote.total=120, approval.ceiling=200 (above quote.total),
        # latest_total=300 → exceeds the approved ceiling
        decision = check_approval(q(total=120), a(total=200), r(total=300))
        self.assertFalse(decision.ok)
        self.assertIn("exceeds approved ceiling", decision.reason)

    def test_happy_path(self) -> None:
        decision = check_approval(q(total=120), a(total=200), r(total=100))
        self.assertTrue(decision.ok, decision.reason)


if __name__ == "__main__":
    unittest.main()
