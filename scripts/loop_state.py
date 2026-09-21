"""Loop state machine and durable store for the visual-quality loop.

The state machine is the **only** source of execution permission (design.md
decision 5). It is deliberately small, explicit and table-driven so that an
illegal transition is a rejected value rather than a runtime surprise.

Storage rules (tasks 4.2 / 4.3 / 4.4 / 4.6):

- The session root must live inside an approved directory, checked on
  canonical paths so a symlinked or relative root cannot escape it.
- Every write goes to a same-directory temp file, is flushed and ``fsync``-ed,
  then atomically replaced. A crash therefore leaves either the old or the new
  content, never a half-written file.
- State files are private (0600).
- Round directories are immutable: writing an existing round is an error.
- The newest candidate is published through an atomically updated
  ``latest.json`` pointer. No symlink is ever created, because Windows cannot
  rely on them.
- Any state that requires an external side effect must first persist an
  *intent* carrying the stable ``submitId``. A resume never mints a new one.
- Unreadable, missing, version-incompatible, or dangling-reference state fails
  closed: the caller gets an exception instead of a silent default.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

try:  # Windows
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None  # type: ignore[assignment]

SCHEMA_VERSION = "visual_loop_state/1"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
NODE_RE = re.compile(r"^node_[A-Za-z0-9_-]+$")

# The 19 declared states, in the order design.md decision 5 introduces them.
STATES: tuple[str, ...] = (
    "CREATED", "TARGET_LOCKED", "TARGET_REGISTERED", "DRAFT_SAVED", "QUOTED",
    "AWAITING_APPROVAL", "SUBMITTED", "WAITING", "ARTIFACT_VERIFIED",
    "AWAITING_JUDGE", "JUDGED", "REVISION_PROPOSED", "COMPLETED", "PAUSED",
    "STALLED", "STOP_REQUESTED", "DRAINING_ACCEPTED", "STOPPED", "FAILED",
)

TERMINAL_STATES = frozenset({"COMPLETED", "STOPPED", "FAILED"})

# States a restart cannot simply abandon: an intent may already exist and must
# be reconciled with the ORIGINAL submitId rather than re-submitted.
INTERRUPTIBLE_STATES = frozenset({
    "SUBMITTED", "WAITING", "ARTIFACT_VERIFIED", "DRAINING_ACCEPTED",
    "AWAITING_APPROVAL", "QUOTED",
})

# States in which the remote may already have ACCEPTED work. A stop request from
# here must drain (keep reconciling) instead of claiming a cancellation; every
# other state can stop outright. Deliberately narrower than
# INTERRUPTIBLE_STATES, which also covers pre-submission reconciliation.
REMOTE_PENDING_STATES = frozenset({"SUBMITTED", "WAITING", "DRAINING_ACCEPTED"})

# Edges beyond design.md decision 5's diagram, both required by the
# visual-loop spec: stopping before submission enters STOPPED directly
# ("Stop is requested before submission"), and an unrecoverable remote,
# artifact or judge failure enters the diagnosable FAILED state.
TRANSITIONS: Mapping[str, frozenset[str]] = {
    "CREATED": frozenset({"TARGET_LOCKED", "STOPPED"}),
    "TARGET_LOCKED": frozenset({"TARGET_REGISTERED", "DRAFT_SAVED", "STOPPED"}),
    "TARGET_REGISTERED": frozenset({"DRAFT_SAVED", "STOPPED"}),
    "DRAFT_SAVED": frozenset({"QUOTED", "STOPPED"}),
    "QUOTED": frozenset({"AWAITING_APPROVAL", "PAUSED", "STOPPED"}),
    "AWAITING_APPROVAL": frozenset({"SUBMITTED", "STOPPED"}),
    "SUBMITTED": frozenset({"WAITING", "DRAINING_ACCEPTED", "FAILED"}),
    "WAITING": frozenset({"ARTIFACT_VERIFIED", "DRAINING_ACCEPTED", "FAILED"}),
    "ARTIFACT_VERIFIED": frozenset({"AWAITING_JUDGE", "FAILED"}),
    "AWAITING_JUDGE": frozenset({"JUDGED", "FAILED"}),
    "JUDGED": frozenset({"COMPLETED", "REVISION_PROPOSED", "STALLED"}),
    "REVISION_PROPOSED": frozenset({"PAUSED"}),
    "DRAINING_ACCEPTED": frozenset({"STOPPED"}),
    "COMPLETED": frozenset(),
    "PAUSED": frozenset(),
    "STALLED": frozenset(),
    "STOP_REQUESTED": frozenset({"DRAINING_ACCEPTED", "STOPPED"}),
    "STOPPED": frozenset(),
    "FAILED": frozenset(),
}

# The six main contracts of design.md decision 4, plus the two auxiliary
# correlation receipts that `VisualRoundReceipt.quoteRef` / `.approvalRef`
# point at. Both carry non-secret metadata only (a quote id and ceiling; an
# approval request fingerprint and ceiling) — never an approval credential.
RECEIPT_KINDS = frozenset({
    "target", "round", "judge_request", "judge_receipt", "prompt_revision", "budget",
    "quote", "approval",
})


class LoopStateError(Exception):
    """Base class for state-machine and storage failures."""


class IllegalTransition(LoopStateError):
    """A requested transition is not permitted by the table."""


class StateStoreError(LoopStateError):
    """Storage refused to read or write: fail closed, perform no side effect."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def can_transition(source: str, target: str) -> bool:
    return target in TRANSITIONS.get(source, frozenset())


def successors(state: str) -> frozenset[str]:
    return TRANSITIONS.get(state, frozenset())


def normalize_relative(raw: str) -> str:
    """Return a POSIX relative path, rejecting absolute paths and traversal.

    Windows-style separators are accepted so the same logical path behaves
    identically on both platforms (task 4.7).
    """
    if not isinstance(raw, str) or not raw.strip():
        raise StateStoreError("path must be a non-empty string")
    candidate = raw.replace("\\", "/").strip()
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        raise StateStoreError(f"absolute path rejected: {raw!r}")
    parts = [part for part in candidate.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise StateStoreError(f"path traversal rejected: {raw!r}")
    if not parts:
        raise StateStoreError(f"path is empty after normalization: {raw!r}")
    return "/".join(parts)


@dataclass(frozen=True)
class LoopState:
    session_id: str
    state: str = "CREATED"
    current_round: int = 0
    best_round: int = 0
    target_id: str | None = None
    pending_operations: tuple[dict[str, str], ...] = ()
    receipt_refs: tuple[dict[str, str], ...] = ()
    stop_requested: bool = False
    revision_count: int = 0
    updated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if self.state not in TRANSITIONS:
            raise IllegalTransition(f"unknown state: {self.state!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "sessionId": self.session_id,
            "state": self.state,
            "currentRound": self.current_round,
            "bestRound": self.best_round,
            "targetId": self.target_id,
            "pendingOperations": [dict(op) for op in self.pending_operations],
            "receiptRefs": [dict(ref) for ref in self.receipt_refs],
            "stopRequested": self.stop_requested,
            # Stopping prevents new submissions; it never claims a remote cancel.
            "remoteCancelled": False,
            "revisionCount": self.revision_count,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LoopState:
        if payload.get("schemaVersion") != SCHEMA_VERSION:
            raise StateStoreError(
                f"unsupported state schemaVersion: {payload.get('schemaVersion')!r}")
        if payload.get("remoteCancelled") not in (False, None):
            raise StateStoreError("remoteCancelled must be false: stopping is not a cancel")
        try:
            return cls(
                session_id=payload["sessionId"],
                state=payload["state"],
                current_round=int(payload.get("currentRound", 0)),
                best_round=int(payload.get("bestRound", 0)),
                target_id=payload.get("targetId"),
                pending_operations=tuple(
                    dict(op) for op in payload.get("pendingOperations", ())),
                receipt_refs=tuple(
                    dict(ref) for ref in payload.get("receiptRefs", ())),
                stop_requested=bool(payload.get("stopRequested", False)),
                revision_count=int(payload.get("revisionCount", 0)),
                updated_at=str(payload.get("updatedAt") or _utc_now()),
            )
        except KeyError as exc:
            raise StateStoreError(f"state is missing required field {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise StateStoreError(f"state field has the wrong shape: {exc}") from exc


def advance(state: LoopState, target: str, *, current_round: int | None = None) -> LoopState:
    """Return the state advanced to *target*, or raise ``IllegalTransition``."""
    if target not in TRANSITIONS:
        raise IllegalTransition(f"unknown target state: {target!r}")
    if not can_transition(state.state, target):
        raise IllegalTransition(f"{state.state} -> {target} is not permitted")
    if current_round is not None and current_round < state.current_round:
        raise IllegalTransition(
            f"current_round cannot move backwards: {state.current_round} -> {current_round}")
    return replace(
        state,
        state=target,
        current_round=state.current_round if current_round is None else current_round,
        best_round=max(state.best_round, state.current_round if current_round is None
                       else current_round),
        stop_requested=state.stop_requested or target in ("STOPPED", "DRAINING_ACCEPTED"),
        updated_at=_utc_now(),
    )


def resume_action(state: LoopState) -> dict[str, Any]:
    """Describe how to resume without ever minting a new ``submitId``."""
    if state.state in TERMINAL_STATES:
        return {"action": "terminal", "state": state.state}
    if state.pending_operations:
        first = state.pending_operations[0]
        return {"action": "resume", "submitId": first.get("submitId"),
                "nodeId": first.get("nodeId"), "state": state.state}
    return {"action": "idle", "state": state.state}


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #

@contextmanager
def _exclusive_lock(lock_path: Path) -> Iterator[None]:
    """A cross-platform exclusive lock held for the duration of a write."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        elif msvcrt is not None:  # pragma: no cover - Windows
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        yield
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
            elif msvcrt is not None:  # pragma: no cover - Windows
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(fd)


def _atomic_write(target: Path, data: bytes, *, mode: int = 0o600) -> None:
    """Write via a same-directory temp file, fsync, then atomically replace."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".tmp-", suffix=".json")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
        # Persist the rename itself. Directory fsync is POSIX-only: Windows
        # cannot open a directory with O_RDONLY (PermissionError), and the
        # NTFS/Metadata journaling already orders the rename there.
        if os.name != "nt":
            dir_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise


class LoopStateStore:
    """Session-scoped, crash-safe state and artifact store."""

    def __init__(self, *, root: Path, session_id: str,
                 approved_root: Path | None = None) -> None:
        if not isinstance(session_id, str) or not UUID_RE.match(session_id):
            raise StateStoreError(f"session id must be a canonical lowercase UUID: {session_id!r}")
        self.root = Path(root).expanduser()
        self.approved_root = Path(approved_root).expanduser() if approved_root else self.root
        self.session_id = session_id
        self._assert_contained(self.root, self.approved_root, "store root")
        self.session_dir = self.root / "sessions" / session_id
        self.state_path = self.session_dir / "state.json"
        self.latest_path = self.session_dir / "latest.json"
        self.lock_path = self.session_dir / ".lock"

    @staticmethod
    def _assert_contained(path: Path, approved: Path, label: str) -> None:
        resolved = path.resolve()
        approved_resolved = approved.resolve()
        if resolved != approved_resolved and approved_resolved not in resolved.parents:
            raise StateStoreError(f"{label} escapes the approved directory: {path}")

    def _resolve_receipt_ref(self, ref: Mapping[str, str]) -> Path:
        kind = ref.get("kind")
        if kind not in RECEIPT_KINDS:
            raise StateStoreError(f"unknown receipt kind: {kind!r}")
        relative = normalize_relative(str(ref.get("ref", "")))
        candidate = (self.session_dir / relative).resolve()
        self._assert_contained(candidate, self.session_dir, "receipt reference")
        return candidate

    # ---- state ---------------------------------------------------------- #
    def write(self, state: LoopState) -> Path:
        if state.session_id != self.session_id:
            raise StateStoreError(
                f"state belongs to session {state.session_id!r}, not {self.session_id!r}")
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        with _exclusive_lock(self.lock_path):
            _atomic_write(self.state_path, payload.encode("utf-8"))
        return self.state_path

    def read(self) -> LoopState:
        if not self.state_path.is_file():
            raise StateStoreError(f"state file is missing: {self.state_path}")
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateStoreError(f"state file is unreadable: {exc}") from exc
        state = LoopState.from_dict(payload)
        if state.session_id != self.session_id:
            raise StateStoreError("state file belongs to a different session")
        for ref in state.receipt_refs:
            if not self._resolve_receipt_ref(ref).exists():
                raise StateStoreError(f"receipt reference is dangling: {ref!r}")
        return state

    # ---- rounds and the latest pointer ---------------------------------- #
    def write_round(self, round_id: str, files: Mapping[str, bytes]) -> Path:
        round_dir = self.session_dir / "rounds" / round_id
        if round_dir.exists():
            raise StateStoreError(f"round is immutable and already exists: {round_id}")
        round_dir.mkdir(parents=True)
        for name, blob in files.items():
            relative = normalize_relative(name)
            target = round_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with _exclusive_lock(self.lock_path):
                _atomic_write(target, blob)
        return round_dir

    def update_latest(self, round_id: str) -> Path:
        """Publish the newest candidate through an atomic pointer, never a symlink."""
        round_dir = self.session_dir / "rounds" / round_id
        if not round_dir.is_dir():
            raise StateStoreError(f"cannot point at a missing round: {round_id}")
        payload = json.dumps(
            {"schemaVersion": "visual_latest/1", "roundId": round_id,
             "updatedAt": _utc_now()},
            ensure_ascii=False, indent=2, sort_keys=True)
        with _exclusive_lock(self.lock_path):
            _atomic_write(self.latest_path, payload.encode("utf-8"))
        return self.latest_path

    def read_latest(self) -> str | None:
        if not self.latest_path.is_file():
            return None
        try:
            payload = json.loads(self.latest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateStoreError(f"latest pointer is unreadable: {exc}") from exc
        round_id = payload.get("roundId")
        if not isinstance(round_id, str) or not round_id:
            raise StateStoreError("latest pointer has no roundId")
        return round_id

    # ---- intent-first persistence (task 4.4) ---------------------------- #
    def intent_path(self, submit_id: str) -> Path:
        return self.session_dir / "intents" / f"{submit_id}.json"

    def record_intent(self, *, kind: str, submit_id: str,
                      node_id: str | None = None) -> Path:
        """Persist intent BEFORE the external call so a crash is reconcilable."""
        if not isinstance(submit_id, str) or not UUID_RE.match(submit_id):
            raise StateStoreError(
                f"submitId must be a canonical lowercase UUID, got {submit_id!r}")
        if not isinstance(kind, str) or not kind.strip():
            raise StateStoreError("intent kind must be a non-empty string")
        if node_id is not None and not NODE_RE.match(node_id):
            raise StateStoreError(f"nodeId has the wrong shape: {node_id!r}")
        target = self.intent_path(submit_id)
        if target.exists():
            raise StateStoreError(
                f"intent for {submit_id} already exists; reuse it instead of minting a new one")
        payload = json.dumps(
            {"schemaVersion": "visual_intent/1", "kind": kind, "submitId": submit_id,
             "nodeId": node_id, "createdAt": _utc_now(), "result": None},
            ensure_ascii=False, indent=2, sort_keys=True)
        with _exclusive_lock(self.lock_path):
            _atomic_write(target, payload.encode("utf-8"))
        return target

    def complete_intent(self, *, kind: str, submit_id: str,
                        result: Mapping[str, Any]) -> Path:
        """Record the confirmed outcome of an intent that was already persisted.

        The intent exists precisely so an interrupted caller can reconcile the
        SAME identity instead of minting a new one; a completed intent therefore
        stays addressable by its original id.
        """
        target = self.intent_path(submit_id)
        if not target.is_file():
            raise StateStoreError(
                f"cannot complete an intent that was never recorded: {submit_id}")
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateStoreError(f"intent is unreadable: {exc}") from exc
        if payload.get("kind") != kind:
            raise StateStoreError(
                f"intent kind mismatch: recorded {payload.get('kind')!r}, asked {kind!r}")
        payload["result"] = dict(result)
        payload["completedAt"] = _utc_now()
        with _exclusive_lock(self.lock_path):
            _atomic_write(target, json.dumps(payload, ensure_ascii=False, indent=2,
                                             sort_keys=True).encode("utf-8"))
        return target

    def pending_intent(self, *, kind: str, submit_id: str) -> dict[str, Any]:
        target = self.intent_path(submit_id)
        if not target.is_file():
            raise StateStoreError(f"no intent recorded for {submit_id}")
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateStoreError(f"intent is unreadable: {exc}") from exc
        if payload.get("kind") != kind:
            raise StateStoreError(
                f"intent kind mismatch: recorded {payload.get('kind')!r}, asked {kind!r}")
        return payload
