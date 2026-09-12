"""Fixture-driven Skill evaluator used by atomic and orchestration tests.

Each Skill is expected to read a CLI envelope (fixture) and produce a
plan: a list of argv arrays the agent should execute next, plus any
side-channel decisions (e.g. "use operation wait, not node run").

This module is the *fixture boundary* under test. The CLI itself is
never invoked; we read a JSON fixture and run a tiny dispatcher that
mirrors the documented routing rules of each Canvas Skill.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "cli"


class Plan(list):
    """A plan is an ordered list of argv arrays plus optional notes."""

    def __init__(self, commands: Iterable[list[str]] | None = None):
        super().__init__(commands or [])
        self.notes: list[str] = []

    @property
    def commands(self) -> "Plan":
        # alias for readability
        return self


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def evaluate_skill(skill: str, fixture: str | None = None) -> Plan:
    """Route a CLI envelope fixture to the chosen Skill's response plan."""
    payload = load_fixture(fixture) if fixture else {}
    error = payload.get("error") if isinstance(payload, dict) else None
    if error is None:
        # success envelope — Skills that own save/list still surface next steps
        return _handle_success(skill)
    required = error.get("requiredAction")
    code = error.get("code")
    if required == "resume":
        return _resume_plan(payload)
    if required == "confirm":
        return _confirm_plan(payload)
    if required == "upgrade":
        return _upgrade_plan(payload)
    if required == "login":
        return _login_plan(payload)
    if required == "human_intervention":
        return _human_intervention_plan(payload)
    if required == "retry":
        return _retry_plan(payload)
    if required == "none":
        return _none_plan(code)
    return _none_plan(code)


# --- per-required-action routing ----------------------------------------------------

def _resume_plan(payload: dict) -> Plan:
    """Exit-20 / requiredAction=resume: continue with operation wait."""
    op_ref = (payload.get("error") or {}).get("operationRef")
    argv = ["dreamina-canvas", "--format", "json", "operation", "wait", op_ref or "<submitId>"]
    argv += ["--project-id", "<projectId>", "--timeout", "10m", "--interval", "5s"]
    plan = Plan([argv])
    plan.notes.append(
        "recovery: reuse submitId, do not call node run with a new submitId"
    )
    return plan


def _confirm_plan(payload: dict) -> Plan:
    """Exit-10 / requiredAction=confirm: pause for user approval, do not auto-run."""
    plan = Plan([])
    plan.notes.append(
        "paid execution paused: hand the creditConfirmation.minimumCreditCeiling "
        "to the user and wait for explicit --credit-ceiling / --credit-token"
    )
    return plan


def _upgrade_plan(payload: dict) -> Plan:
    upgrade_url = (payload.get("error") or {}).get("clientUpgrade", {}).get(
        "upgradeUrl"
    )
    argv = ["curl", "-s", upgrade_url or "<upgradeUrl>", "|", "bash"]
    plan = Plan([argv])
    plan.notes.append("upgrade required before retrying the original command")
    return plan


def _login_plan(payload: dict) -> Plan:
    argv = ["dreamina-canvas", "--format", "json", "auth", "login"]
    plan = Plan([argv])
    plan.notes.append(
        "re-login on the active profile then retry with the same projectId / submitId"
    )
    return plan


def _human_intervention_plan(payload: dict) -> Plan:
    plan = Plan([])
    plan.notes.append("escalate to the user; never auto-retry on human_intervention")
    return plan


def _retry_plan(payload: dict) -> Plan:
    plan = Plan([])
    plan.notes.append("back off and retry the original command with bounded retries")
    return plan


def _none_plan(code: str | None) -> Plan:
    plan = Plan([])
    plan.notes.append(f"code={code!r}: no script-driven next step")
    return plan


def _handle_success(skill: str) -> Plan:
    """Skills that own success envelopes emit confirmation commands."""
    if skill == "dreamina-canvas-download-assets":
        plan = Plan(
            [
                [
                    "shasum",
                    "-a",
                    "256",
                    "<downloaded-path>",
                ]
            ]
        )
        plan.notes.append("verify downloaded file SHA-256 against response.sha256")
        return plan
    return Plan([])
