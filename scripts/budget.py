"""Budget, stall, and stop governance (change section 9).

Principles (design.md decision 9 + the loop spec):

- Accounting is **conservative**: `reserved` is committed the moment a quote is
  accepted, and a local timeout never releases it — only a verified terminal
  outcome settles a reservation.
- `bounded_batch` bounds rounds, total credits, per-round credits and a
  deadline. It **never bypasses** the CLI's short-lived approval: without a
  fresh approval the controller parks at `AWAITING_APPROVAL` regardless of
  batch state.
- Exit policy extends dream-loop's criteria with critical dimension gates and
  stall detection (consecutive no-improvement, repeated gap sets, replan
  count). Stalling never widens the budget and never retargets.
- The best round is retained even when later rounds score lower.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Quote:
    quote_id: str
    total_max_credits: int
    confirmable: bool


BudgetPolicy = "PerRoundPolicy | BoundedBatchPolicy"


class BudgetExceeded(Exception):
    """The policy refuses the next reservation."""


@dataclass
class Reservation:
    quote_id: str
    credits: int
    settled: bool = False


@dataclass
class BudgetLedger:
    """Conservative credit accounting (task 9.1)."""

    spent: int = 0
    reserved: int = 0
    unknown: int = 0

    @property
    def available(self) -> int | None:
        return None  # an unbounded ledger has no ceiling

    def reserve(self, quote: Quote) -> Reservation:
        self.reserved += quote.total_max_credits
        return Reservation(quote_id=quote.quote_id,
                           credits=quote.total_max_credits)

    def settle(self, reservation: Reservation, *, outcome: str,
               actual_credits: int | None = None) -> None:
        """Settle a reservation. Only a *verified terminal* outcome releases it.

        `timeout` and `unknown` move the credits to `unknown` — the remote may
        still be running and may still bill. This is the anti-optimistic rule.
        """
        if reservation.settled:
            raise BudgetExceeded("reservation already settled")
        self.reserved -= reservation.credits
        if outcome == "completed":
            self.spent += actual_credits if actual_credits is not None else reservation.credits
        elif outcome in ("failed",):
            pass  # verified failure: the reservation is released, nothing spent
        else:  # timeout / unknown: the truth is not in yet
            self.unknown += reservation.credits
        reservation.settled = True


@dataclass(frozen=True)
class PerRoundPolicy:
    """Default: every round asks for its own fresh approval."""

    mode: str = "per_round"

    def check(self, ledger: BudgetLedger, quote: Quote, *,
              approval_ceiling: int | None = None) -> None:
        if approval_ceiling is not None and quote.total_max_credits > approval_ceiling:
            raise BudgetExceeded("quote exceeds the round approval ceiling")


@dataclass(frozen=True)
class BoundedBatchPolicy:
    """Bounds an entire batch (task 9.2). Never replaces vendor approval."""

    max_rounds: int
    max_total_credits: int
    max_per_round: int
    deadline_epoch: float | None = None
    rounds_started: int = 0

    def check(self, ledger: BudgetLedger, quote: Quote, *,
              approval_ceiling: int | None = None,
              now_epoch: float | None = None) -> None:
        if self.rounds_started + 1 > self.max_rounds:
            raise BudgetExceeded("batch round budget exhausted")
        if quote.total_max_credits > self.max_per_round:
            raise BudgetExceeded("quote exceeds the per-round cap")
        if ledger.spent + ledger.reserved + ledger.unknown + quote.total_max_credits \
                > self.max_total_credits:
            raise BudgetExceeded("batch total credit cap would be exceeded")
        if self.deadline_epoch is not None and now_epoch is not None \
                and now_epoch > self.deadline_epoch:
            raise BudgetExceeded("batch deadline passed")
        # The vendor chain stays authoritative: a missing/stale approval still
        # parks the round at AWAITING_APPROVAL (task 9.3).
        if approval_ceiling is not None and quote.total_max_credits > approval_ceiling:
            raise BudgetExceeded("quote exceeds the batch approval ceiling")

    def next_round(self) -> BoundedBatchPolicy:
        return replace(self, rounds_started=self.rounds_started + 1)


# --------------------------------------------------------------------------- #
# 9.4 / 9.5 — exit policy with critical gates and stall detection
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RoundScore:
    round_index: int
    total: float
    dimension_scores: Mapping[str, float]
    gap_keys: frozenset[str] = frozenset()
    recommendation: str = "revise"


@dataclass
class ExitGovernor:
    min_total: float = 8.0
    critical_dimension_minimums: Mapping[str, float] = field(default_factory=dict)
    max_rounds_without_improvement: int = 2
    max_repeated_gap_rounds: int = 2
    max_replans: int = 1
    replans_used: int = 0
    history: list[RoundScore] = field(default_factory=list)
    best: RoundScore | None = None

    def observe(self, score: RoundScore) -> str:
        """Record a round and return the governance decision."""
        self.history.append(score)
        if self.best is None or score.total > self.best.total:
            self.best = score  # 9.5: best round is retained, never regressed

        for dimension, minimum in self.critical_dimension_minimums.items():
            if score.dimension_scores.get(dimension, 0.0) < minimum:
                return "revision_proposed"  # a critical gate blocks completion

        if score.total >= self.min_total and not score.gap_keys:
            return "completed"

        if self._stalled():
            return "stalled"
        if self._improved_this_round():
            return "revision_proposed"  # improvement interrupts gap repetition
        if self._repeated_gaps():
            if self.replans_used < self.max_replans:
                self.replans_used += 1
                return "replan_required"
            return "stalled"
        return "revision_proposed"

    def _stalled(self) -> bool:
        if len(self.history) < self.max_rounds_without_improvement + 1:
            return False
        recent = self.history[-(self.max_rounds_without_improvement + 1):]
        best_recent = max(entry.total for entry in recent[:-1])
        # Strictly worse = decline; flat scores are the repeated-gap path's
        # business (replan first), not the decline stall's.
        return recent[-1].total < best_recent

    def _improved_this_round(self) -> bool:
        if len(self.history) < 2:
            return False
        previous_best = max(entry.total for entry in self.history[:-1])
        return self.history[-1].total > previous_best

    def _repeated_gaps(self) -> bool:
        """The same non-empty gap set named in max_repeated_gap_rounds + 1
        consecutive rounds: the first round names it, the rest repeat it."""
        window = self.max_repeated_gap_rounds + 1
        if len(self.history) < window:
            return False
        recent = self.history[-window:]
        gap_sets = [entry.gap_keys for entry in recent]
        return all(keys and keys == gap_sets[0] for keys in gap_sets)

    def diagnostics(self) -> Mapping[str, object]:
        """9.5 — stall/pause diagnostics. Never widens budget or retargets."""
        return {
            "roundsObserved": len(self.history),
            "bestRound": self.best.round_index if self.best else None,
            "bestTotal": self.best.total if self.best else None,
            "replansUsed": self.replans_used,
            "maxReplans": self.max_replans,
        }
