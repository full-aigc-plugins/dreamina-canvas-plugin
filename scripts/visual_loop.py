"""Single bounded round of the visual-quality loop (change section 6).

The controller performs **exactly one** round: lock or register the target, save
a draft, quote, pause for approval, submit once, resume-wait, download, verify,
then judge — and stop at `JUDGED`, `REVISION_PROPOSED`, or a terminal state. It
never quotes or submits a second round on its own (visual-loop spec: "The first
delivery executes exactly one bounded round").

Design: the durable state machine from `loop_state` is the only scheduler. Each
`step()` performs the work the *current* state allows and advances, so a process
that dies anywhere resumes by reading its own persisted state — no chat context,
no in-memory bookkeeping. The `submitId` is generated once and persisted as an
intent **before** the submission attempt, so a restart reconciles the original
identity instead of billing a new one.

Pause boundaries are deliberate: the controller stops at `AWAITING_APPROVAL`
and `AWAITING_JUDGE` and hands control back. It never approves spend and never
fabricates a verdict. The approval credential lives only in memory.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from artifact_guard import SECRET_FIELD_NAMES
from loop_state import (
    REMOTE_PENDING_STATES,
    LoopState,
    LoopStateStore,
    StateStoreError,
    # Same-package internals, used to persist receipts atomically.
    _atomic_write,
    _exclusive_lock,
    advance,
)

SCHEMA_VERSION = "visual_round_result/1"


class LoopError(Exception):
    """The controller cannot continue safely."""


class SecretRefused(LoopError):
    """A receipt offered for persistence carried a forbidden field."""


# --------------------------------------------------------------------------- #
# Ports (6.2) — the controller depends on these and nothing else
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Quote:
    quote_id: str
    total_max_credits: int
    confirmable: bool


@dataclass(frozen=True)
class Approval:
    ceiling: int
    request_fingerprint: str
    # Memory-only. The dataclass is never persisted, and the receipt written for
    # an approval carries only the fingerprint and the ceiling.
    credit_token: str = field(default="", repr=False)


@dataclass(frozen=True)
class Submission:
    submit_id: str
    state: str  # accepted | unknown | rejected


@dataclass(frozen=True)
class RemoteStatus:
    submit_id: str
    state: str  # in_progress | completed | failed | absent | unknown
    resource_id: str | None = None


@dataclass(frozen=True)
class Artifact:
    resource_id: str
    canonical_path: Path
    bytes: int
    sha256: str


@dataclass(frozen=True)
class JudgeVerdict:
    judge_id: str
    adapter: str
    scores: Mapping[str, float]
    gaps: Sequence[Mapping[str, str]]
    recommendation: str


@runtime_checkable
class CanvasRuntimePort(Protocol):
    def discover(self) -> Mapping[str, Any]: ...
    def save_draft(self, *, target: Mapping[str, Any], round_index: int) -> Mapping[str, Any]: ...
    def quote(self, *, node_id: str) -> Quote: ...


@runtime_checkable
class ApprovalPort(Protocol):
    """Non-blocking: returns None until the host has approved the spend."""

    def pending(self) -> Approval | None: ...


@runtime_checkable
class ExecutionPort(Protocol):
    def submit(self, *, node_id: str, submit_id: str,
               credit_token: str) -> Submission: ...
    def status(self, *, submit_id: str) -> RemoteStatus: ...


@runtime_checkable
class ArtifactPort(Protocol):
    def fetch(self, *, resource_id: str, destination: Path) -> Artifact: ...


@runtime_checkable
class JudgePort(Protocol):
    def pending(self) -> JudgeVerdict | None: ...


@runtime_checkable
class PromptRevisionPort(Protocol):
    def propose(self, *, verdict: JudgeVerdict) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class BudgetLedger:
    """Conservative accounting: a local timeout never releases a reservation."""

    max_total_credits: int = 0
    spent: int = 0
    reserved: int = 0

    def would_exceed(self, quote: Quote) -> bool:
        return bool(self.max_total_credits) and (
            self.spent + self.reserved + quote.total_max_credits > self.max_total_credits)


@dataclass(frozen=True)
class ExitPolicy:
    """dream-loop's exit criteria expressed as data, not prose."""

    min_total: float = 8.0

    def decided(self, verdict: JudgeVerdict) -> str:
        total = float(verdict.scores.get("total", 0.0))
        if total >= self.min_total and not verdict.gaps:
            return "completed"
        return "revision_proposed"


# --------------------------------------------------------------------------- #
# Result (machine-parseable)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RoundResult:
    state: str
    round_index: int
    submit_id: str | None = None
    node_id: str | None = None
    resource_id: str | None = None
    decision: str | None = None
    revision: Mapping[str, Any] | None = None
    required_action: str = "none"
    paused: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "state": self.state,
            "roundIndex": self.round_index,
            "submitId": self.submit_id,
            "nodeId": self.node_id,
            "resourceId": self.resource_id,
            "decision": self.decision,
            "revision": dict(self.revision) if self.revision else None,
            "requiredAction": self.required_action,
            "paused": self.paused,
        }


def assert_no_secrets(payload: Any) -> None:
    """Receipts must never carry authentication material (visual-loop spec)."""
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if isinstance(key, str) and key in SECRET_FIELD_NAMES:
                raise SecretRefused(f"forbidden field {key!r} in a persisted receipt")
            assert_no_secrets(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            assert_no_secrets(item)


# --------------------------------------------------------------------------- #
# Controller (6.3)
# --------------------------------------------------------------------------- #

@dataclass
class VisualLoopController:
    """Drives one bounded round through the persisted state machine."""

    store: LoopStateStore
    target: Mapping[str, Any]
    runtime: CanvasRuntimePort
    approval: ApprovalPort
    execution: ExecutionPort
    artifacts: ArtifactPort
    judge: JudgePort
    revision: PromptRevisionPort
    budget: BudgetLedger = field(default_factory=BudgetLedger)
    exit_policy: ExitPolicy = field(default_factory=ExitPolicy)

    # ---- state helpers --------------------------------------------------- #
    def state(self) -> LoopState:
        try:
            return self.store.read()
        except StateStoreError:
            return LoopState(session_id=self.store.session_id)

    def _persist(self, state: LoopState) -> LoopState:
        self.store.write(state)
        return state

    def request_stop(self) -> LoopState:
        """Stop prevents NEW work; it never claims a remote cancellation."""
        state = self.state()
        target = ("DRAINING_ACCEPTED" if state.state in REMOTE_PENDING_STATES
                  else "STOPPED")
        if state.state == target:
            return state
        return self._persist(advance(state, target))

    # ---- stepping -------------------------------------------------------- #
    def step(self) -> RoundResult:
        state = self.state()
        handler = getattr(self, f"_on_{state.state}", None)
        if handler is None:
            return self._result(state, required_action="none", paused=True)
        return handler(state)

    def run_until_pause(self, *, max_steps: int = 12) -> RoundResult:
        """Step until a pause boundary, a decision, a terminal state, or budget."""
        result = self._result(self.state(), paused=True)
        for _ in range(max_steps):
            result = self.step()
            if result.paused or result.state in (
                    "COMPLETED", "STOPPED", "FAILED", "REVISION_PROPOSED", "STALLED"):
                return result
        return result

    def _result(self, state: LoopState, **over: Any) -> RoundResult:
        pending = state.pending_operations[0] if state.pending_operations else {}
        payload: dict[str, Any] = {
            "state": state.state,
            "round_index": state.current_round,
            "submit_id": pending.get("submitId"),
            "node_id": pending.get("nodeId"),
            "paused": state.state in ("AWAITING_APPROVAL", "AWAITING_JUDGE", "PAUSED"),
        }
        payload.update(over)
        return RoundResult(**payload)

    def _with_pending(self, state: LoopState, **fields: str) -> LoopState:
        merged = dict(state.pending_operations[0]) if state.pending_operations else {}
        merged.update({k: v for k, v in fields.items() if v is not None})
        return self._persist(replace(state, pending_operations=(merged,)))

    # ---- state handlers -------------------------------------------------- #
    def _on_CREATED(self, state: LoopState) -> RoundResult:
        self.runtime.discover()
        return self._result(self._persist(advance(state, "TARGET_LOCKED")))

    def _on_TARGET_LOCKED(self, state: LoopState) -> RoundResult:
        mode = self.target.get("ingestionMode")
        if mode == "canvas_reference" and not self.target.get("resourceId"):
            return self._result(state, required_action="register_target", paused=True)
        if mode not in ("judge_only", "canvas_reference"):
            return self._result(self._persist(advance(state, "STOPPED")),
                                required_action="human_intervention")
        next_state = "DRAFT_SAVED" if mode == "judge_only" else "TARGET_REGISTERED"
        return self._result(self._persist(advance(state, next_state)))

    def _on_TARGET_REGISTERED(self, state: LoopState) -> RoundResult:
        return self._result(self._persist(advance(state, "DRAFT_SAVED")))

    def _on_DRAFT_SAVED(self, state: LoopState) -> RoundResult:
        draft = self.runtime.save_draft(target=self.target,
                                        round_index=state.current_round + 1)
        node_id = str(draft["nodeId"])
        state = self._persist(advance(state, "QUOTED",
                                      current_round=state.current_round + 1))
        state = self._with_pending(state, nodeId=node_id)
        return self._result(state, node_id=node_id)

    def _on_QUOTED(self, state: LoopState) -> RoundResult:
        node_id = str(state.pending_operations[0]["nodeId"])
        quote = self.runtime.quote(node_id=node_id)
        if not quote.confirmable:
            return self._result(self._persist(advance(state, "PAUSED")),
                                node_id=node_id, required_action="fix_draft",
                                paused=True)
        if self.budget.would_exceed(quote):
            return self._result(self._persist(advance(state, "PAUSED")),
                                node_id=node_id, required_action="raise_budget",
                                paused=True)
        state = self._persist_receipt("quote", {
            "quoteId": quote.quote_id, "totalMaxCredits": quote.total_max_credits})
        return self._result(self._persist(advance(state, "AWAITING_APPROVAL")),
                            node_id=node_id, required_action="request_approval",
                            paused=True)

    def _on_AWAITING_APPROVAL(self, state: LoopState) -> RoundResult:
        approval = self.approval.pending()
        if approval is None:
            return self._result(state, required_action="request_approval", paused=True)
        # Non-secret metadata only. `credit_token` is never serialized.
        state = self._persist_receipt("approval", {
            "requestFingerprint": approval.request_fingerprint,
            "ceiling": approval.ceiling})
        node_id = str(state.pending_operations[0]["nodeId"])
        submit_id = (state.pending_operations[0].get("submitId")
                     or str(uuid.uuid4()))
        # Intent-first: the identity exists on disk before any submission call.
        if not self.store.intent_path(submit_id).is_file():
            self.store.record_intent(kind="node_run", submit_id=submit_id,
                                     node_id=node_id)
        state = self._with_pending(state, submitId=submit_id, creditToken=None)
        return self._result(self._persist(advance(state, "SUBMITTED")),
                            node_id=node_id, submit_id=submit_id,
                            required_action="submit")

    def _on_SUBMITTED(self, state: LoopState) -> RoundResult:
        pending = state.pending_operations[0]
        node_id, submit_id = str(pending["nodeId"]), str(pending["submitId"])
        approval = self.approval.pending()
        guarantee = approval.credit_token if approval else ""
        try:
            submission = self.execution.submit(node_id=node_id, submit_id=submit_id,
                                               credit_token=guarantee)
        except Exception:  # transport failure: keep the identity, ask to resume
            return self._result(state, node_id=node_id, submit_id=submit_id,
                                required_action="resume", paused=True)
        if submission.state == "rejected":
            return self._result(self._persist(advance(state, "FAILED")),
                                node_id=node_id, submit_id=submit_id,
                                required_action="human_intervention")
        # accepted or unknown: both continue to WAITING and are reconciled by ID.
        return self._result(self._persist(advance(state, "WAITING")),
                            node_id=node_id, submit_id=submit_id)

    def _on_WAITING(self, state: LoopState) -> RoundResult:
        submit_id = str(state.pending_operations[0]["submitId"])
        status = self.execution.status(submit_id=submit_id)
        if status.state in ("in_progress", "unknown", "absent"):
            return self._result(state, submit_id=submit_id,
                                required_action="resume", paused=True)
        if status.state != "completed" or not status.resource_id:
            return self._result(self._persist(advance(state, "FAILED")),
                                submit_id=submit_id,
                                required_action="human_intervention")
        artifact = self.artifacts.fetch(
            resource_id=str(status.resource_id),
            destination=self.store.session_dir / "rounds" / f"r{state.current_round}")
        assert_no_secrets({"resourceId": artifact.resource_id,
                           "sha256": artifact.sha256})
        return self._result(self._persist(advance(state, "ARTIFACT_VERIFIED")),
                            submit_id=submit_id, resource_id=artifact.resource_id)

    def _on_ARTIFACT_VERIFIED(self, state: LoopState) -> RoundResult:
        return self._result(self._persist(advance(state, "AWAITING_JUDGE")),
                            required_action="judge", paused=True)

    def _on_AWAITING_JUDGE(self, state: LoopState) -> RoundResult:
        verdict = self.judge.pending()
        if verdict is None:
            return self._result(state, required_action="judge", paused=True)
        assert_no_secrets({"judgeId": verdict.judge_id, "adapter": verdict.adapter,
                           "scores": dict(verdict.scores),
                           "gaps": [dict(gap) for gap in verdict.gaps]})
        judged = self._persist(advance(state, "JUDGED"))
        if self.exit_policy.decided(verdict) == "completed":
            return self._result(self._persist(advance(judged, "COMPLETED")),
                                decision="completed")
        proposal = self.revision.propose(verdict=verdict)
        # A revision proposal is where the round ENDS. Nothing quotes or submits
        # the next round from here.
        return self._result(self._persist(advance(judged, "REVISION_PROPOSED")),
                            decision="revision_proposed", revision=proposal)

    # ---- stop states ----------------------------------------------------- #
    def _on_DRAINING_ACCEPTED(self, state: LoopState) -> RoundResult:
        if not state.pending_operations:
            return self._result(self._persist(advance(state, "STOPPED")))
        submit_id = str(state.pending_operations[0]["submitId"])
        status = self.execution.status(submit_id=submit_id)
        if status.state in ("in_progress", "unknown", "absent"):
            return self._result(state, submit_id=submit_id,
                                required_action="drain", paused=True)
        return self._result(self._persist(advance(state, "STOPPED")),
                            submit_id=submit_id)

    # ---- receipt plumbing ------------------------------------------------ #
    def _persist_receipt(self, kind: str, payload: Mapping[str, Any]) -> LoopState:
        """Write a receipt and return the state with the new reference attached.

        Callers MUST advance from the returned state: reusing the state they read
        before the receipt would silently drop the reference.
        """
        assert_no_secrets(payload)
        directory = self.store.session_dir / "receipts"
        directory.mkdir(parents=True, exist_ok=True)
        index = len(list(directory.glob(f"{kind}-*.json")))
        target = directory / f"{kind}-{index}.json"
        body = json.dumps({"kind": kind, **payload}, ensure_ascii=False,
                          indent=2, sort_keys=True)
        with _exclusive_lock(self.store.lock_path):
            _atomic_write(target, body.encode("utf-8"))
        state = self.state()
        refs = tuple(state.receipt_refs) + (
            {"kind": kind, "ref": f"receipts/{target.name}"},)
        return self._persist(replace(state, receipt_refs=refs))
