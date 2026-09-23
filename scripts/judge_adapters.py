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

import json
import shlex
import subprocess
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


def make_shell_judge(cmd: str, *, pass_image_paths: bool = False) -> Callable[..., dict]:
    """Host-neutral bridge: request JSON on stdin, verdict JSON on stdout.

    The host supplies `cmd`; the plugin never imports a host SDK (JudgePort
    discipline). `pass_image_paths` appends the target/candidate paths as argv
    for adapters whose contract is (request, target_path, candidate_path).
    """
    tokens = shlex.split(cmd)

    def invoke(*args: Any) -> dict:
        request = args[0]
        argv = list(tokens)
        if pass_image_paths:
            argv += [str(a) for a in args[1:3] if a is not None]
        proc = subprocess.run(argv, input=json.dumps(request),
                              capture_output=True, text=True,
                              timeout=120, check=False)
        if proc.returncode != 0:
            raise JudgeRequestError(
                f"judge command failed: exit {proc.returncode}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise JudgeRequestError("judge command did not return JSON") from exc

    return invoke


def dispatch_judge(*, adapter: str, request: Mapping[str, Any],
                   cmd: str | None = None,
                   target_image: str | None = None,
                   candidate_image: str | None = None) -> dict:
    """Route one request to a named adapter. Human parks; the rest bridge.

    The returned payload is a JudgeReceipt-shaped dict — the caller must run it
    through `judge_exchange.import_judge_receipt` before any consumer trusts it.
    """
    if adapter == "human":
        return {"status": "awaiting_human",
                "note": "produce a JudgeReceipt and run import-judge"}
    if not cmd:
        raise CapabilityUnavailable(
            f"adapter {adapter!r} requires --cmd; the round stays paused")
    if adapter == "host-subagent":
        if not (target_image and candidate_image):
            raise JudgeRequestError(
                "host-subagent requires --target-image and --candidate-image")
        return HostSubagentJudgeAdapter(
            invoke=make_shell_judge(cmd, pass_image_paths=True),
            target_path=Path(target_image),
            candidate_path=Path(candidate_image),
        ).evaluate(request)
    if adapter == "design-skill":
        return DreaminaDesignSkillJudgeAdapter(
            skill_runner=make_shell_judge(cmd)).evaluate(request)
    if adapter == "external-mcp":
        return ExternalMcpJudgeAdapter(
            server=make_shell_judge(cmd)).evaluate(request)
    raise JudgeRequestError(f"unknown adapter: {adapter!r}")


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
