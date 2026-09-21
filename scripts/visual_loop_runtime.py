"""CLI-backed ports for the visual-quality loop (tasks 6.3 composition, 6.4-6.7).

This module is the ONLY place that knows about the real `dreamina-canvas` CLI.
It composes the existing, independently tested pieces:

- `dreamina_canvas_adapter` — strict argv-only invocation, JSON envelopes
- `error_router`            — exit code → typed next action
- `operation_ledger`        — non-secret submitId receipts, reconcile rules
- `artifact_guard`          — byte count + SHA-256 + approved-dir verification
- `target_store.CapabilityProbe` — live-schema evidence for reference forms

The controller (`visual_loop`) never imports the adapter directly; it only sees
the port dataclasses. Every port takes an injectable `runner` so tests can drive
the full composition against scripted CLI envelopes without a network.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import artifact_guard
import error_router
from dreamina_canvas_adapter import CommandResult, run_dreamina_canvas
from loop_state import LoopStateStore, _atomic_write, _exclusive_lock
from operation_ledger import OperationReceipt, persist
from target_store import CapabilityProbe
from visual_loop import (
    Artifact,
    Quote,
    RemoteStatus,
    Submission,
)

Runner = Callable[..., CommandResult]

# Operation-status states reported by the CLI, mapped to the controller's vocabulary.
_STATUS_MAP = {
    "running": "in_progress",
    "in_progress": "in_progress",
    "queued": "in_progress",
    "success": "completed",
    "completed": "completed",
    "failed": "failed",
    "canceled": "failed",
    "absent": "absent",
}


class RuntimePortError(Exception):
    """A CLI exchange failed in a way the controller must treat as diagnostic."""


def _data(result: CommandResult) -> dict:
    if isinstance(result.payload, dict):
        return result.payload.get("data") or {}
    return {}


class CliCanvasRuntime:
    """Discovers capabilities, saves drafts, and quotes — never generates."""

    def __init__(self, *, runner: Runner = run_dreamina_canvas,
                 probe: CapabilityProbe, project_id: str) -> None:
        self.runner = runner
        self.probe = probe
        self.project_id = project_id

    def discover(self) -> Mapping[str, Any]:
        snapshot = self.probe.refresh()
        return {"schemaSha256": snapshot.schema_sha256,
                "referenceForms": sorted(snapshot.reference_forms())}

    def save_draft(self, *, target: Mapping[str, Any], round_index: int) -> Mapping[str, Any]:
        """Create an image draft node. `--run` is never passed here."""
        argv = ["--format", "json", "node", "create", "image",
                "--title", f"visual-loop r{round_index}",
                "--prompt", str(target.get("prompt", "")),
                "--mode", "t2i", "--model", str(target.get("model", "")),
                "--ratio", str(target.get("ratio", "1:1")),
                "--resolution", str(target.get("resolution", "1K")),
                "--project-id", self.project_id]
        for reference in target.get("refs", ()):  # already-confirmed res:<uuid> forms
            argv += ["--ref", reference]
        result = self.runner(argv)
        if result.exit_code != 0:
            raise RuntimePortError(
                f"save_draft failed: exit={result.exit_code} "
                f"action={result.required_action} error={result.error}")
        data = _data(result)
        node_id = (data.get("node") or {}).get("nodeId") or data.get("nodeId")
        if not node_id:
            raise RuntimePortError(f"save_draft returned no nodeId: {data}")
        return {"nodeId": node_id,
                "mutationVersion": (data.get("node") or {}).get("savedDraftVersion")}

    def quote(self, *, node_id: str) -> Quote:
        result = self.runner(["--format", "json", "node", "quote",
                              "--node-id", node_id, "--project-id", self.project_id])
        if result.exit_code != 0:
            raise RuntimePortError(
                f"quote failed: exit={result.exit_code} action={result.required_action}")
        data = _data(result)
        return Quote(quote_id=str(data.get("quoteId") or node_id),
                     total_max_credits=int(data.get("totalMaxCredits", 0)),
                     confirmable=bool(data.get("confirmable")))


class CliExecution:
    """Submits once under a persisted identity and reconciles by that identity."""

    def __init__(self, *, runner: Runner = run_dreamina_canvas,
                 store: LoopStateStore, project_id: str,
                 profile_env: str = "default") -> None:
        self.runner = runner
        self.store = store
        self.project_id = project_id
        self.profile_env = profile_env

    def submit(self, *, node_id: str, submit_id: str, credit_token: str) -> Submission:
        # Ledger first: the identity exists outside the process before the call.
        fingerprint = hashlib.sha256(
            "|".join((self.project_id, node_id, submit_id)).encode("utf-8")).hexdigest()
        persist(OperationReceipt(
            project_id=self.project_id, node_id=node_id, submit_id=submit_id,
            last_known_state="in_progress", resubmittable=False,
            request_fingerprint=fingerprint, exit_code=-1,
            timestamp=_now()), root=self.store.session_dir / "ledger",
            profile_env=self.profile_env)
        try:
            result = self.runner(["--format", "json", "node", "run",
                                  "--node-id", node_id,
                                  "--project-id", self.project_id,
                                  "--credit-token", credit_token,
                                  "--submit-id", submit_id])
        except Exception as exc:  # transport failure: identity is already on disk
            raise RuntimePortError(f"node run transport failure: {exc}") from exc
        decision = error_router.route(result.exit_code)
        if result.exit_code == 0:
            return Submission(submit_id=submit_id, state="accepted")
        if decision.action == error_router.Action.RESUME_OPERATION:
            return Submission(submit_id=submit_id, state="unknown")
        if result.exit_code == 2:
            return Submission(submit_id=submit_id, state="rejected")
        raise RuntimePortError(
            f"node run failed: exit={result.exit_code} action={decision.action}")

    def status(self, *, submit_id: str) -> RemoteStatus:
        result = self.runner(["--format", "json", "operation", "status",
                              submit_id, "--project-id", self.project_id])
        if result.exit_code != 0:
            return RemoteStatus(submit_id=submit_id, state="unknown")
        data = _data(result)
        raw = str(data.get("state") or data.get("status") or "unknown").lower()
        state = _STATUS_MAP.get(raw, "unknown")
        resource_id = data.get("resourceId")
        return RemoteStatus(submit_id=submit_id, state=state,
                            resource_id=str(resource_id) if resource_id else None)


class CliArtifacts:
    """Downloads through the CLI and verifies with the artifact guard."""

    def __init__(self, *, runner: Runner = run_dreamina_canvas,
                 store: LoopStateStore, project_id: str,
                 approved_dir: Path) -> None:
        self.runner = runner
        self.store = store
        self.project_id = project_id
        self.approved_dir = Path(approved_dir)

    def fetch(self, *, resource_id: str, destination: Path) -> Artifact:
        """Transactional download: stage → verify → atomically commit.

        A failed verification never creates the round directory and never leaves
        an unverified file in it; the blob is quarantined for inspection.
        """
        self.store.session_dir.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(dir=self.store.session_dir, prefix="staging-"))
        result = self.runner(["--format", "json", "resource", "download",
                              resource_id, "--project-id", self.project_id,
                              "--output", str(staging)])
        if result.exit_code != 0:
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimePortError(
                f"download failed: exit={result.exit_code} action={result.required_action}")
        data = _data(result)
        canonical = Path(str(data.get("canonicalPath") or ""))
        media = data.get("media") or {}
        receipt = artifact_guard.ArtifactReceipt(
            resource_id=resource_id, canonical_path=canonical,
            byte_count=int(data.get("byteCount", canonical.stat().st_size if canonical.is_file() else 0)),
            sha256=str(data.get("sha256") or ""), media=media)
        decision = artifact_guard.verify(receipt, approved_dir=self.approved_dir,
                                         raw_response=data or None)
        if not decision.ok:
            quarantine = self.store.session_dir / "quarantine"
            quarantine.mkdir(parents=True, exist_ok=True)
            if canonical.is_file():
                shutil.move(str(canonical), str(quarantine / canonical.name))
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimePortError(f"artifact verification failed: {decision.reason}")
        # Verified: commit atomically into the immutable round directory.
        destination.mkdir(parents=True, exist_ok=True)
        final = destination / canonical.name
        with _exclusive_lock(self.store.lock_path):
            _atomic_write(final, canonical.read_bytes())
        canonical.unlink(missing_ok=True)
        shutil.rmtree(staging, ignore_errors=True)
        return Artifact(resource_id=resource_id, canonical_path=final,
                        bytes=receipt.byte_count, sha256=receipt.sha256)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
