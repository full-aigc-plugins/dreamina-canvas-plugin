"""Error router tests (downstream Task 3, Step 4).

Asserts the documented exit-code → typed action map.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import error_router as router


class ErrorRouterTests(unittest.TestCase):
    def test_zero_continues(self) -> None:
        d = router.route(0)
        self.assertEqual(d.action, router.Action.CONTINUE)

    def test_two_is_fix_and_retry(self) -> None:
        d = router.route(2)
        self.assertEqual(d.action, router.Action.FIX_AND_RETRY)

    def test_ten_is_approval_pause(self) -> None:
        d = router.route(10)
        self.assertEqual(d.action, router.Action.APPROVAL_PAUSE)

    def test_eleven_is_reauth(self) -> None:
        d = router.route(11)
        self.assertEqual(d.action, router.Action.REAUTH_AND_RETRY)

    def test_twelve_is_escalate(self) -> None:
        d = router.route(12)
        self.assertEqual(d.action, router.Action.ESCALATE)

    def test_thirteen_is_upgrade(self) -> None:
        d = router.route(13)
        self.assertEqual(d.action, router.Action.UPGRADE_CLI)

    def test_twenty_is_resume(self) -> None:
        d = router.route(20)
        self.assertEqual(d.action, router.Action.RESUME_OPERATION)

    def test_twentyone_is_bounded_retry(self) -> None:
        d = router.route(21)
        self.assertEqual(d.action, router.Action.BOUNDED_BACKOFF_RETRY)

    def test_twentytwo_is_human(self) -> None:
        d = router.route(22)
        self.assertEqual(d.action, router.Action.HAND_TO_HUMAN)

    def test_unknown_code_alerts(self) -> None:
        d = router.route(99)
        self.assertEqual(d.action, router.Action.ALERT)


if __name__ == "__main__":
    unittest.main()
