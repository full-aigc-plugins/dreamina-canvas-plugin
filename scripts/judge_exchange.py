"""Durable Judge request/receipt exchange (task 6.8).

The controller pauses at `AWAITING_JUDGE`. To resume — possibly in a different
process, on a different host, or after a human verdict — the pause must be a
**file pair**, not chat context:

1. `write_judge_request`  — persists a schema-valid `JudgeRequest` bound to the
   target and candidate content digests, and records it in the loop state.
2. `import_judge_receipt` — validates an externally produced verdict against the
   shipped `judge_receipt` schema, the stored request, and the round's artifact;
   rejects malformed, content-mismatched, non-fresh-context, secret-bearing, or
   duplicate receipts; then persists it and marks it consumable.

`PendingJudgePort` implements the controller's `JudgePort` on top of that pair:
a restarted process finds the imported receipt and finishes the round without
re-judging or re-submitting.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import jsonschema
from loop_state import (
    LoopState,
    LoopStateStore,
    _atomic_write,
    _exclusive_lock,
    replace,
)
from visual_loop import JudgeVerdict

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
REQUEST_SCHEMA = "judge_request.schema.json"
RECEIPT_SCHEMA = "judge_receipt.schema.json"


class JudgeExchangeError(Exception):
    """The judge request or receipt cannot be trusted."""


def _validator(name: str) -> jsonschema.Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    base = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
    base.update(schema)
    return jsonschema.Draft202012Validator(base)


def _next_path(directory: Path, prefix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{prefix}-{len(list(directory.glob(f'{prefix}-*.json')))}.json"


def current_request_path(store: LoopStateStore) -> Path | None:
    """The latest judge request recorded in the state, if any."""
    state = store.read()
    judge_requests = [ref for ref in state.receipt_refs
                      if ref.get("kind") == "judge_request"]
    if not judge_requests:
        return None
    return store.session_dir / str(judge_requests[-1]["ref"])


def write_judge_request(store: LoopStateStore, *, target_id: str,
                        target_sha256: str, candidate_resource_id: str,
                        candidate_sha256: str, rubric_version: str = "vision_judge/1",
                        media_type: str = "image/png") -> Path:
    """Persist the JudgeRequest for the paused round and reference it in state."""
    payload = {
        "schemaVersion": "judge_request/1",
        "requestId": str(uuid.uuid4()),
        "target": {"targetId": target_id, "sha256": target_sha256},
        "candidate": {"resourceId": candidate_resource_id,
                      "sha256": candidate_sha256, "mediaType": media_type},
        "rubricVersion": rubric_version,
        "freshContext": True,
        "forbidPromptDraft": True,
        "createdAt": _utc_now(),
    }
    _validator(REQUEST_SCHEMA).validate(payload)
    store.session_dir.mkdir(parents=True, exist_ok=True)
    if not store.state_path.is_file():
        store.write(LoopState(session_id=store.session_id))
    path = _next_path(store.session_dir / "judges", "request")
    with _exclusive_lock(store.lock_path):
        _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2,
                                       sort_keys=True).encode("utf-8"))
    state = store.read()
    refs = tuple(state.receipt_refs) + (
        {"kind": "judge_request", "ref": f"judges/{path.name}"},)
    store.write(replace(state, receipt_refs=refs))
    return path


def import_judge_receipt(store: LoopStateStore, payload: Mapping[str, Any]) -> Path:
    """Validate and persist an externally produced verdict.

    Rejections are total: schema violation, content mismatch against the stored
    request, non-fresh-context declarations, secret-bearing fields, or a
    duplicate import for the same request. Nothing is written on rejection.
    """
    from artifact_guard import SECRET_FIELD_NAMES

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if isinstance(key, str) and key in SECRET_FIELD_NAMES:
                    raise JudgeExchangeError(f"forbidden field {key!r} in a receipt")
                walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(payload)
    try:
        _validator(RECEIPT_SCHEMA).validate(payload)
    except jsonschema.ValidationError as exc:
        raise JudgeExchangeError(f"receipt violates the contract: {exc.message}") from exc

    request_path = current_request_path(store)
    if request_path is None or not request_path.is_file():
        raise JudgeExchangeError("no judge request is pending for this session")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if payload.get("targetSha256") != request["target"]["sha256"]:
        raise JudgeExchangeError("receipt targetSha256 does not match the request")
    if payload.get("candidateSha256") != request["candidate"]["sha256"]:
        raise JudgeExchangeError("receipt candidateSha256 does not match the request")

    state = store.read()
    request_count = sum(1 for ref in state.receipt_refs
                        if ref.get("kind") == "judge_request")
    receipt_count = sum(1 for ref in state.receipt_refs
                        if ref.get("kind") == "judge_receipt")
    # One verdict per request: a second import for the same request is a
    # duplicate (a follow-up round writes its own request first).
    if receipt_count >= request_count:
        raise JudgeExchangeError("duplicate receipt for the current request")
    path = store.session_dir / "judges" / f"receipt-{receipt_count}.json"
    relative = f"judges/{path.name}"

    with _exclusive_lock(store.lock_path):
        _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2,
                                       sort_keys=True).encode("utf-8"))
    refs = tuple(state.receipt_refs) + ({"kind": "judge_receipt", "ref": relative},)
    store.write(replace(state, receipt_refs=refs))
    return path


class PendingJudgePort:
    """The controller's JudgePort over the durable request/receipt pair."""

    def __init__(self, store: LoopStateStore) -> None:
        self.store = store

    def pending(self) -> JudgeVerdict | None:
        state = self.store.read()
        receipts = [ref for ref in state.receipt_refs
                    if ref.get("kind") == "judge_receipt"]
        if not receipts:
            return None
        path = self.store.session_dir / str(receipts[-1]["ref"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        return JudgeVerdict(
            judge_id=str(payload["judgeId"]),
            adapter=str(payload["adapter"]),
            scores=dict(payload["scores"]),
            gaps=[dict(gap) for gap in payload.get("gaps", [])],
            recommendation=str(payload["recommendation"]))


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
