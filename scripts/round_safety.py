"""单轮安全快照：预算、报价绑定、策略与提交尝试标记，不存储凭证。"""
from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any
import re
import time
from budget import BudgetLedger, Reservation, Quote, PerRoundPolicy, BoundedBatchPolicy

if TYPE_CHECKING:
    from visual_loop import VisualLoopController
    from loop_state import LoopState

EARLY_STATES = {'CREATED', 'TARGET_LOCKED', 'TARGET_REGISTERED', 'DRAFT_SAVED', 'QUOTED'}


def validate_snapshot(value: object) -> None:
    """拒绝缺字段、非法金额、损坏保留额和未知策略，避免默认为零预算。"""
    if not isinstance(value, dict):
        raise ValueError('safety must be an object')
    if not value:  # 旧状态兼容；是否可执行由 restore 判定。
        return
    if set(value) != {'ledger', 'reservation', 'quote', 'policy', 'attempted'}:
        raise ValueError('incomplete safety snapshot')
    def amount(v):
        if type(v) is not int or v < 0:
            raise ValueError('credits must be nonnegative integers')
    ledger = value['ledger']
    if not isinstance(ledger, dict) or set(ledger) != {'spent', 'reserved', 'unknown'}:
        raise ValueError('invalid budget ledger')
    for v in ledger.values():
        amount(v)
    if type(value['attempted']) is not bool:
        raise ValueError('invalid attempted marker')
    quote = value['quote']
    if quote is not None:
        if not isinstance(quote, dict) or set(quote) != set(Quote.__dataclass_fields__):
            raise ValueError('invalid persisted quote')
        amount(quote['total_max_credits'])
        if not isinstance(quote['quote_id'], str) or not quote['quote_id']:
            raise ValueError('invalid quote id')
        if not isinstance(quote['project_id'], str):
            raise ValueError('invalid quote project')
        if quote['confirmable'] is not True or not re.fullmatch(r'[0-9a-f]{64}', quote['request_fingerprint']):
            raise ValueError('quote lacks an approvable request binding')
    reservation = value['reservation']
    if reservation is not None:
        if not isinstance(reservation, dict) or set(reservation) != set(Reservation.__dataclass_fields__):
            raise ValueError('invalid reservation')
        amount(reservation['credits'])
        if reservation['settled'] is not False or quote is None or reservation['quote_id'] != quote['quote_id'] or reservation['credits'] != quote['total_max_credits']:
            raise ValueError('reservation does not match quote')
        if ledger['reserved'] != reservation['credits']:
            raise ValueError('reservation does not match ledger')
    elif ledger['reserved'] != 0:
        raise ValueError('reserved credits lack a reservation')
    policy = value['policy']
    if not isinstance(policy, dict):
        raise ValueError('invalid policy')
    if policy == {'mode': 'per_round'}:
        return
    if set(policy) != {'mode', 'max_rounds', 'max_total_credits', 'max_per_round', 'deadline_epoch', 'rounds_started'} or policy['mode'] != 'bounded_batch':
        raise ValueError('invalid batch policy')
    for key in ('max_rounds', 'max_total_credits', 'max_per_round', 'rounds_started'):
        amount(policy[key])
    deadline = policy['deadline_epoch']
    if deadline is not None and (type(deadline) not in (int, float) or not 0 <= deadline < float('inf')):
        raise ValueError('invalid deadline')


def snapshot(controller: VisualLoopController) -> dict[str, Any]:
    policy = asdict(controller.policy)
    if isinstance(controller.policy, BoundedBatchPolicy):
        policy['mode'] = 'bounded_batch'
    value = dict(ledger=asdict(controller.budget),
                 reservation=asdict(controller.reservation) if controller.reservation else None,
                 quote=asdict(controller._quote) if controller._quote else None,
                 policy=policy, attempted=controller._attempted)
    validate_snapshot(value)
    return value


def restore(controller: VisualLoopController, state: LoopState) -> None:
    value = state.safety
    validate_snapshot(value)
    if not value:
        if state.state not in EARLY_STATES and state.state != 'STOPPED':
            raise ValueError('legacy session lacks durable budget; inspect and reconcile manually')
        return
    if state.state in {'AWAITING_APPROVAL', 'SUBMITTED', 'WAITING', 'DRAINING_ACCEPTED'} and (value['quote'] is None or value['reservation'] is None):
        raise ValueError('active round lacks quote or reservation')
    if state.state in {'WAITING', 'DRAINING_ACCEPTED'} and not value['attempted']:
        # A stop may have happened before the actual attempt; query-only is safe.
        if state.state != 'DRAINING_ACCEPTED':
            raise ValueError('waiting state lacks submission attempt marker')
    for key, amount in value['ledger'].items():
        setattr(controller.budget, key, amount)
    controller.reservation = Reservation(**value['reservation']) if value['reservation'] else None
    controller._quote = Quote(**value['quote']) if value['quote'] else None
    controller._attempted = value['attempted']
    policy = dict(value['policy'])
    mode = policy.pop('mode')
    controller.policy = BoundedBatchPolicy(**policy) if mode == 'bounded_batch' else PerRoundPolicy()


def check_policy(controller: VisualLoopController, quote: Quote, *,
                 ceiling: int | None = None, reserved: bool = False) -> None:
    # 审批前复核已有保留额，不能再把同一轮加一次。
    ledger = controller.budget
    if reserved and controller.reservation:
        ledger = BudgetLedger(ledger.spent, ledger.reserved - controller.reservation.credits, ledger.unknown)
    kwargs = {'approval_ceiling': ceiling}
    if isinstance(controller.policy, BoundedBatchPolicy):
        kwargs['now_epoch'] = time.time()
    controller.policy.check(ledger, quote, **kwargs)
