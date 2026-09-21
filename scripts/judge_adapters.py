"""JudgePort adapters and request hygiene (change section 7).

Task 7.2: `build_judge_request` is the only way a request is created, and it
refuses to carry prompt text, model history, or prior verdicts — the request
binds content digests and constraints only.

Task 7.3: `HostSubagentJudgeAdapter` speaks to the host through a single
callable boundary; no host API appears in this module.

Task 7.4: `DreaminaDesignSkillJudgeAdapter` and `ExternalMcpJudgeAdapter`
report *capability unavailable* when their dependency is absent instead of
breaking the canvas round.

Task 7.5: `HumanJudgeAdapter` parks the round at `AWAITING_JUDGE`; the resumable
import command is `visual_loop_cli.py import-judge`.

Task 7.6: rejection tests live in `test_judge_adapters.py`; the golden-sample
expectations in `tests/fixtures/judge/golden/` define pass/fail so a judge that
scores byte-identical images below 9, or divergent images at full score, is
wrong by construction.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from visual_loop import JudgeVerdict

_FORBIDDEN_REQUEST_KEYS = (
    "prompt", "promptDraft", "history", "priorVerdicts", "modelHistory",
    "conversation", "messages",
)


class JudgeRequestError(Exception):
    """The judge request would carry biasing or forbidden material."""


class CapabilityUnavailable(Exception):
    """The judge dependency is not installed/configured on this host."""


def build_judge_request(*, target_id: str, target_sha256: str,
                        candidate_resource_id: str, candidate_sha256: str,
                        rubric_version: str = "vision_judge/1",
                        media_type: str = "image/png") -> dict:
    """A request carries digests and constraints — nothing that could bias."""
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
    return payload


def assert_request_hygiene(payload: Mapping[str, Any]) -> None:
    for key in _FORBIDDEN_REQUEST_KEYS:
        if key in payload:
            raise JudgeRequestError(
                f"judge requests must not carry {key!r}: it biases the verdict")
    if payload.get("freshContext") is not True or payload.get("forbidPromptDraft") is not True:
        raise JudgeRequestError("fresh-context constraints must be asserted, not optional")


# --------------------------------------------------------------------------- #
# Adapters
# --------------------------------------------------------------------------- #

class HostSubagentJudgeAdapter:
    """Delegates to a host-supplied callable (task 7.3).

    The callable receives `(request: dict, target_path, candidate_path)` and
    returns a verdict dict. This module never imports a host SDK; the host wires
    itself in at composition time.
    """

    def __init__(self, *, invoke: Callable[[dict, Path, Path], dict],
                 target_path: Path, candidate_path: Path) -> None:
        self._invoke = invoke
        self._target_path = Path(target_path)
        self._candidate_path = Path(candidate_path)

    def pending(self) -> JudgeVerdict | None:
        raise CapabilityUnavailable(
            "HostSubagentJudgeAdapter is host-driven; use `.evaluate(request)`")

    def evaluate(self, request: Mapping[str, Any]) -> dict:
        assert_request_hygiene(request)
        return self._invoke(dict(request), self._target_path, self._candidate_path)


class DreaminaDesignSkillJudgeAdapter:
    """Optional adapter over the sibling design plugin (task 7.4)."""

    def __init__(self, *, skill_runner: Callable[[dict], dict] | None = None) -> None:
        self._skill_runner = skill_runner

    def pending(self) -> JudgeVerdict | None:
        raise CapabilityUnavailable("drive via evaluate(request)")

    def evaluate(self, request: Mapping[str, Any]) -> dict:
        if self._skill_runner is None:
            raise CapabilityUnavailable(
                "dreamina-design-plugin is not installed; install it or wire "
                "another judge adapter — the canvas round stays paused")
        assert_request_hygiene(request)
        return self._skill_runner(dict(request))


class ExternalMcpJudgeAdapter:
    """Optional adapter over an external MCP judge server (task 7.4)."""

    def __init__(self, *, server: Callable[[dict], dict] | None = None) -> None:
        self._server = server

    def pending(self) -> JudgeVerdict | None:
        raise CapabilityUnavailable("drive via evaluate(request)")

    def evaluate(self, request: Mapping[str, Any]) -> dict:
        if self._server is None:
            raise CapabilityUnavailable(
                "no external MCP judge configured; the canvas round stays paused")
        assert_request_hygiene(request)
        return self._server(dict(request))


class HumanJudgeAdapter:
    """Parks the round for a human verdict (task 7.5).

    `pending()` always returns None so the controller stays at
    `AWAITING_JUDGE`. The human delivers the verdict through the resumable
    import command (`visual_loop_cli.py import-judge`), which validates and
    persists it for the next controller run.
    """

    def pending(self) -> JudgeVerdict | None:
        return None


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
