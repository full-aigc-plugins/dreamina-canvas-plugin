"""行为回归：审批、损坏状态、一次提交和跨进程预算。"""
import json
from dataclasses import replace
from test_visual_loop import ControllerCase, FakeExecution, SESSION, SHA, vl
from loop_state import StateStoreError, LoopStateStore
from visual_loop_cli import _ensure_state


class RoundSafetyTests(ControllerCase):
    def test_bad_approval_never_submits(self):
        for index, approval in enumerate((vl.Approval(0, SHA, 'secret'),
                         vl.Approval(100, 'b' * 64, 'secret'),
                         vl.Approval(100, SHA, ''))):
            self.store = LoopStateStore(root=self.approved / str(index), session_id=SESSION)
            with self.subTest(approval=repr(approval)):
                controller, parts = self.controller(approval=approval)
                controller.run_until_pause()
                result = controller.run_until_pause()
                self.assertEqual(parts['execution'].submit_calls, [])
                self.assertEqual(result.required_action, 'request_approval')

    def test_changed_quote_never_submits(self):
        controller, parts = self.controller(approval=vl.Approval(100, SHA, 'secret'))
        controller.run_until_pause()
        parts['runtime'].credits = 60
        result = controller.run_until_pause()
        self.assertEqual(parts['execution'].submit_calls, [])
        self.assertEqual(result.required_action, 'request_approval')

    def test_corrupt_state_preserved_by_controller_and_cli(self):
        self.store.session_dir.mkdir(parents=True)
        self.store.state_path.write_text('{broken')
        controller, parts = self.controller()
        for run in (controller.run_until_pause, lambda: _ensure_state(self.store)):
            with self.assertRaises(StateStoreError):
                run()
        self.assertEqual(self.store.state_path.read_text(), '{broken')
        self.assertEqual(parts['runtime'].discover_calls, 0)

    def test_missing_state_in_existing_session_fails_closed(self):
        self.store.session_dir.mkdir(parents=True)
        (self.store.session_dir / 'intents').mkdir()
        controller, _ = self.controller()
        with self.assertRaises(StateStoreError):
            controller.run_until_pause()
        self.assertFalse(self.store.state_path.exists())

    def test_dangling_receipt_cannot_reset_session(self):
        controller, parts = self.controller()
        controller.run_until_pause()
        state = self.store.read()
        self.store.write(replace(state, receipt_refs=({'kind': 'quote', 'ref': 'gone.json'},)))
        before = self.store.state_path.read_bytes()
        with self.assertRaises(StateStoreError):
            controller.run_until_pause()
        self.assertEqual(before, self.store.state_path.read_bytes())
        self.assertEqual(parts['runtime'].draft_calls, 1)

    def test_transport_exception_restart_queries_without_token_or_resubmit(self):
        execution = FakeExecution(raise_on_submit=True)
        controller, _ = self.controller(approval=vl.Approval(100, SHA, 'secret'), execution=execution)
        controller.run_until_pause()
        controller.run_until_pause()
        restarted, _ = self.controller(execution=execution)
        result = restarted.run_until_pause()
        self.assertEqual(len(execution.submit_calls), 1)
        self.assertEqual(execution.status_calls, execution.submit_calls)
        self.assertEqual(result.state, 'AWAITING_JUDGE')
        self.assertEqual(restarted.budget.spent, 40)
        self.assertEqual(restarted.budget.reserved, 0)
        restarted.run_until_pause()
        self.assertEqual(restarted.budget.spent, 40)

    def test_restart_restores_reservation(self):
        controller, _ = self.controller()
        controller.run_until_pause()
        restarted, _ = self.controller()
        restarted.run_until_pause()
        self.assertEqual(restarted.budget.reserved, 40)
        self.assertIsNotNone(restarted.reservation)
        self.assertEqual(restarted.reservation.credits, 40)

    def test_draining_settles_after_restart(self):
        execution = FakeExecution(raise_on_submit=True)
        controller, _ = self.controller(approval=vl.Approval(100, SHA, 'secret'), execution=execution)
        controller.run_until_pause()
        controller.run_until_pause()
        controller.request_stop()
        restarted, _ = self.controller(execution=execution)
        self.assertEqual(restarted.run_until_pause().state, 'STOPPED')
        self.assertEqual(restarted.budget.spent, 40)
        self.assertEqual(restarted.budget.reserved, 0)

    def test_invalid_remote_status_keeps_reservation(self):
        execution = FakeExecution(statuses=[vl.RemoteStatus('', 'unrecognized')])
        controller, _ = self.controller(approval=vl.Approval(100, SHA, 'secret'), execution=execution)
        controller.run_until_pause()
        self.assertEqual(controller.run_until_pause().state, 'WAITING')
        self.assertEqual(controller.budget.reserved, 40)

    def test_restart_restores_policy_and_enforces_expired_deadline(self):
        from budget import BoundedBatchPolicy
        from unittest.mock import patch
        with patch('round_safety.time.time', return_value=10):
            controller, _ = self.controller(policy=BoundedBatchPolicy(1, 50, 50, 20))
            controller.run_until_pause()
        restarted, parts = self.controller(approval=vl.Approval(100, SHA, 'secret'))
        with patch('round_safety.time.time', return_value=30):
            result = restarted.run_until_pause()
        self.assertEqual(result.required_action, 'request_approval')
        self.assertEqual(restarted.policy.max_total_credits, 50)
        self.assertEqual(restarted.budget.reserved, 40)
        self.assertFalse(parts['execution'].submit_calls)

    def test_corrupt_safety_does_not_default_budget_to_zero(self):
        controller, _ = self.controller()
        controller.run_until_pause()
        state = json.loads(self.store.state_path.read_text())
        state['safety']['ledger']['reserved'] = 0
        self.store.state_path.write_text(json.dumps(state))
        before = self.store.state_path.read_bytes()
        restarted, parts = self.controller()
        with self.assertRaises(StateStoreError):
            restarted.run_until_pause()
        self.assertEqual(before, self.store.state_path.read_bytes())
        self.assertFalse(parts['execution'].submit_calls)

    def test_process_interruption_after_attempt_is_query_only(self):
        from unittest.mock import patch
        controller, parts = self.controller(approval=vl.Approval(100, SHA, 'secret'))
        controller.run_until_pause()
        with patch.object(parts['execution'], 'submit', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                controller.run_until_pause()
        restarted, parts = self.controller()
        self.assertEqual(restarted.run_until_pause().state, 'AWAITING_JUDGE')
        self.assertEqual(len(parts['execution'].status_calls), 1)
        self.assertFalse(parts['execution'].submit_calls)

    def test_concurrent_controllers_submit_once(self):
        from concurrent.futures import ThreadPoolExecutor
        execution = FakeExecution()
        first, _ = self.controller(approval=vl.Approval(100, SHA, 'secret'), execution=execution)
        first.run_until_pause()
        second, _ = self.controller(approval=vl.Approval(100, SHA, 'secret'), execution=execution)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda c: c.run_until_pause(), [first, second]))
        self.assertEqual(len(execution.submit_calls), 1)
        self.assertTrue(all(r.state == 'AWAITING_JUDGE' for r in results))
        self.assertEqual(self.store.read().safety['ledger']['spent'], 40)

    def test_quote_persistence_crash_does_not_double_reserve(self):
        from unittest.mock import patch
        controller, _ = self.controller()
        original = controller._persist
        def crash_before_approval(state):
            if state.state == 'AWAITING_APPROVAL':
                raise KeyboardInterrupt()
            return original(state)
        with patch.object(controller, '_persist', side_effect=crash_before_approval):
            with self.assertRaises(KeyboardInterrupt):
                controller.run_until_pause()
        restarted, _ = self.controller()
        restarted.run_until_pause()
        self.assertEqual(restarted.budget.reserved, 40)

    def test_legacy_approval_session_requires_manual_reconciliation(self):
        controller, _ = self.controller()
        controller.run_until_pause()
        state = json.loads(self.store.state_path.read_text())
        del state['safety']
        self.store.state_path.write_text(json.dumps(state))
        restarted, parts = self.controller(approval=vl.Approval(100, SHA, 'secret'))
        with self.assertRaisesRegex(StateStoreError, 'legacy'):
            restarted.run_until_pause()
        self.assertFalse(parts['execution'].submit_calls)

    def test_draft_change_after_intent_requires_reapproval_and_records_new_binding(self):
        from unittest.mock import patch
        controller, parts = self.controller(approval=vl.Approval(100, SHA, 'secret'))
        controller.run_until_pause()
        self.assertEqual(controller.step().state, 'SUBMITTED')
        changed = vl.Quote(SESSION, 60, True, 'b' * 64)
        with patch.object(parts['runtime'], 'quote', return_value=changed):
            result = controller.step()
            self.assertEqual(result.required_action, 'request_approval')
            self.assertEqual(result.request_fingerprint, 'b' * 64)
            self.assertFalse(parts['execution'].submit_calls)
            parts['approval'].value = vl.Approval(100, 'b' * 64, 'new-secret')
            self.assertEqual(controller.run_until_pause().state, 'AWAITING_JUDGE')
        approvals = [json.loads(p.read_text()) for p in (self.store.session_dir / 'receipts').glob('approval-*.json')]
        self.assertEqual(approvals[-1]['requestFingerprint'], 'b' * 64)
        self.assertEqual(controller.budget.spent, 60)
        self.assertEqual(len(parts['execution'].submit_calls), 1)

    def test_recovery_rejects_different_project(self):
        controller, parts = self.controller()
        controller.run_until_pause()
        state = self.store.read()
        snapshot = dict(state.safety)
        snapshot['quote']['project_id'] = SESSION
        self.store.write(replace(state, safety=snapshot))
        parts['runtime'].project_id = 'different-project'
        with self.assertRaisesRegex(StateStoreError, 'project'):
            controller.run_until_pause()
        self.assertFalse(parts['execution'].submit_calls)
