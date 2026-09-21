"""Prompt revision: full generation-block replacement (change section 8).

Rule of the house (from the Canvas generate skill): a generation edit is a
**full replace** — omitting a flag clears it. This module turns that hazard
into a guarded operation:

- the rewriter receives the complete current block plus *verified gaps only*,
  and must return a complete block;
- `fidelity_check` refuses the result if any field or reference disappeared
  outside the intentional-change whitelist;
- `apply_revision` re-reads the live node first: if the `mutationVersion` or
  the block fingerprint moved underneath us, the round pauses instead of
  clobbering a concurrent edit;
- the stable `updateId` is derived from base/result fingerprints, so a retry
  after an ambiguous result reuses the same identity and is answerable by
  `node show`;
- the outcome is persisted as a `PromptRevisionReceipt` conforming to the
  shipped schema.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loop_state import LoopStateStore, _atomic_write, _exclusive_lock

# Every field a generation block may carry. `node edit` is a full replace, so
# "missing" means "cleared" — the fidelity check treats an unexplained absence
# as data loss.
GENERATION_FIELDS = ("mode", "model", "ratio", "resolution", "count",
                     "duration", "prompt", "refs")

# Only these fields may differ between base and result, and only when the
# change was requested. `refs` may change only to ADD a verified reference.
CHANGEABLE_FIELDS = frozenset({"prompt", "refs"})

BLOCK_MODES = ("t2i", "i2i")
VIDEO_MODES = ("t2v", "first_last_frame", "m2v")
import re as _re

_REF_RE = _re.compile(r"^(?:node:[A-Za-z0-9_-]+|res:[0-9a-f-]{36})$")


class RevisionError(Exception):
    """The revision cannot be produced or applied safely."""


class ConcurrentChange(RevisionError):
    """The live node moved under us; the round must pause, not clobber."""


class FidelityViolation(RevisionError):
    """The proposed block lost fields or references outside the whitelist."""


def fingerprint(block: Mapping[str, Any]) -> str:
    canonical = json.dumps(block, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def parse_generation_block(node_view: Mapping[str, Any]) -> dict:
    """Extract the full generation block from a `node show` view."""
    block = node_view.get("generationDraft") or node_view.get("generation") or {}
    if not isinstance(block, dict) or not block:
        raise RevisionError("node view carries no generation block")
    parsed = {key: block[key] for key in GENERATION_FIELDS if key in block}
    # Unknown reserved fields must survive the round trip, not be dropped.
    for key, value in block.items():
        if key not in parsed:
            parsed[key] = value
    refs = parsed.get("refs")
    parsed["refs"] = list(refs) if isinstance(refs, (list, tuple)) else []
    return parsed


# --------------------------------------------------------------------------- #
# 8.3 — the rewriter interface
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class VerifiedGap:
    """A gap the judge named AND the caller verified as actionable."""

    dimension: str
    location: str
    observation: str
    fix_hint: str


def propose_revision(base: Mapping[str, Any], *, gaps: Sequence[VerifiedGap],
                     constraints: Mapping[str, str] | None = None,
                     new_refs: Sequence[str] = ()) -> dict:
    """Return a COMPLETE block with only whitelisted, gap-driven changes.

    Refusals happen here too: an empty gap list with nothing to add cannot
    justify any change, and refs may only grow (an intentional add), never
    silently shrink.
    """
    result = dict(base)
    changed: list[str] = []

    constraints = constraints or {}
    prompt = base.get("prompt", "")
    if gaps or constraints.get("prompt"):
        additions = " ".join(
            f"{gap.fix_hint}" for gap in gaps if gap.fix_hint)
        extra = constraints.get("prompt", "")
        merged = " ".join(part for part in (prompt, additions, extra) if part)
        if merged != prompt:
            result["prompt"] = merged
            changed.append("prompt")

    existing_refs = list(base.get("refs") or [])
    for ref in new_refs:
        if not _REF_RE.match(str(ref)):
            raise RevisionError(
                f"new reference must be node:<id> or res:<canonical uuid>: {ref!r}")
        if ref not in existing_refs:
            existing_refs.append(str(ref))
    if existing_refs != list(base.get("refs") or []):
        result["refs"] = existing_refs
        changed.append("refs")

    if not changed:
        raise RevisionError(
            "no verified gap or constraint produced a change; refusing to "
            "rewrite the block just to bump a version")
    result["__changedFields"] = changed
    return result


# --------------------------------------------------------------------------- #
# 8.4 — fidelity gate
# --------------------------------------------------------------------------- #

def fidelity_check(base: Mapping[str, Any], result: Mapping[str, Any]) -> list[str]:
    """Return the changed-field list, or raise on unexplained loss."""
    changed: list[str] = []
    for key in GENERATION_FIELDS:
        old, new = base.get(key), result.get(key)
        if key == "refs":
            old_refs = list(old or [])
            new_refs = list(new or [])
            dropped = [ref for ref in old_refs if ref not in new_refs]
            if dropped:
                raise FidelityViolation(
                    f"references were dropped without a whitelist entry: {dropped}")
            if new_refs != old_refs:
                changed.append("refs")
            continue
        if old != new:
            if key not in CHANGEABLE_FIELDS:
                raise FidelityViolation(
                    f"field {key!r} changed outside the whitelist "
                    f"({old!r} -> {new!r})")
            changed.append(key)
    # Unknown reserved fields: they must survive unchanged.
    for key in base:
        if key in GENERATION_FIELDS or key == "__changedFields":
            continue
        if key not in result:
            raise FidelityViolation(f"reserved field {key!r} was dropped")
    declared = result.get("__changedFields") or []
    if sorted(declared) != sorted(changed):
        raise FidelityViolation(
            f"declared changes {sorted(declared)} != actual {sorted(changed)}")
    if not changed:
        raise FidelityViolation("revision produced no change")
    return changed


# --------------------------------------------------------------------------- #
# 8.2 / 8.5 — live apply with concurrency guard and durable receipt
# --------------------------------------------------------------------------- #

class PromptRevisionService:
    def __init__(self, *, runner, store: LoopStateStore, project_id: str,
                 node_id: str) -> None:
        self.runner = runner
        self.store = store
        self.project_id = project_id
        self.node_id = node_id

    def _argv(self, *args: str) -> list[str]:
        return ["--format", "json", *args]

    def read_live_block(self) -> tuple[int, dict]:
        result = self.runner(self._argv("node", "show", "--node-id", self.node_id,
                                        "--project-id", self.project_id))
        if result.exit_code != 0:
            raise RevisionError(f"node show failed: exit={result.exit_code}")
        view = result.payload.get("data", {}) if isinstance(result.payload, dict) else {}
        version = int(view.get("mutationVersion")
                      or (view.get("node") or {}).get("mutationVersion") or 0)
        if not version:
            raise RevisionError("node view carries no mutationVersion")
        return version, parse_generation_block(view)

    def apply(self, *, base_version: int, base_block: Mapping[str, Any],
              result_block: Mapping[str, Any]) -> Path:
        """Apply a full replacement after re-checking the live node."""
        live_version, live_block = self.read_live_block()
        if live_version != base_version or fingerprint(live_block) != fingerprint(base_block):
            raise ConcurrentChange(
                f"node moved under us (base v{base_version}, live v{live_version}); "
                "pausing instead of clobbering the concurrent edit")

        result = self.runner(self._argv(
            "node", "edit", "image",
            "--node-id", self.node_id, "--project-id", self.project_id,
            "--prompt", str(result_block.get("prompt", "")),
            "--mode", str(result_block.get("mode", "t2i")),
            "--model", str(result_block.get("model", "")),
            "--ratio", str(result_block.get("ratio", "1:1")),
            "--resolution", str(result_block.get("resolution", "1K")),
            "--count", str(int(result_block.get("count", 1) or 1)),
            *(("--duration", str(result_block["duration"]))
              if result_block.get("duration") is not None else ()),
            *(("--ref", ref) for ref in result_block.get("refs", ())),
        ))
        if result.exit_code != 0:
            raise RevisionError(
                f"node edit failed: exit={result.exit_code} "
                f"action={result.required_action}")
        return self._persist_receipt(base_version, base_block, result_block)

    def _persist_receipt(self, base_version: int, base_block: Mapping[str, Any],
                         result_block: Mapping[str, Any]) -> Path:
        result_fp = fingerprint({k: v for k, v in result_block.items()
                                 if k != "__changedFields"})
        update_id = str(uuid.uuid5(
            uuid.UUID(self.store.session_id),
            f"{self.node_id}/{base_version}/{result_fp}"))
        payload = {
            "schemaVersion": "prompt_revision_receipt/1",
            "baseMutationVersion": base_version,
            "baseFingerprint": fingerprint(base_block),
            "resultFingerprint": result_fp,
            "judgeReceiptId": self.store.session_id,  # correlation anchor
            "updateId": update_id,
            "changedFields": list(result_block.get("__changedFields", [])),
            "result": "applied",
            "createdAt": _utc_now(),
        }
        from jsonschema import Draft202012Validator
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas"
                             / "prompt_revision_receipt.schema.json").read_text(encoding="utf-8"))
        schema_base = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
        schema_base.update(schema)
        Draft202012Validator(schema_base).validate(payload)
        directory = self.store.session_dir / "receipts"
        path = directory / f"prompt_revision-{update_id[:8]}.json"
        directory.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.store.lock_path):
            _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2,
                                           sort_keys=True).encode("utf-8"))
        return path


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
