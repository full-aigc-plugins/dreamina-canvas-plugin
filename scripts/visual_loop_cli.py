#!/usr/bin/env python3
"""Command entry for the single-round visual loop (task 6.10).

Hosts (Codex / ZCode / Kimi / Claude Code) invoke this script instead of
hand-chaining skills. Every subcommand maps to a pause boundary:

    lock-target   lock the visual target and record it in the loop state
    step          advance the round until the next pause or decision
    status        print the persisted loop state
    request-judge emit the JudgeRequest for the paused round
    import-judge  validate + persist an externally produced JudgeReceipt
    stop          request a stop (drains if the remote already accepted)

The approval credential is read from an environment variable at submit time and
lives only in memory — it never appears in argv, logs, or any persisted file.
The judge verdict arrives through `import-judge` between pauses; this entry
never fabricates one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import judge_exchange as jx
from loop_state import LoopState, LoopStateStore, StateStoreError, advance, replace
from target_store import TargetStore
from visual_loop import (
    Approval,
    VisualLoopController,
)
from visual_loop_runtime import (
    CliArtifacts,
    CliCanvasRuntime,
    CliExecution,
)


def _approved(args: argparse.Namespace) -> Path:
    return Path(args.approved_root).expanduser().resolve()


def _store(args: argparse.Namespace) -> LoopStateStore:
    approved = _approved(args)
    return LoopStateStore(root=approved / args.root, session_id=args.session_id,
                          approved_root=approved)


def _target_store(args: argparse.Namespace) -> TargetStore:
    approved = _approved(args)
    return TargetStore(root=approved / args.root, session_id=args.session_id,
                       approved_root=approved)


def _ensure_state(store: LoopStateStore) -> LoopState:
    try:
        return store.read()
    except StateStoreError:
        state = LoopState(session_id=store.session_id)
        store.write(state)
        return state


def cmd_lock_target(args: argparse.Namespace) -> int:
    tstore = _target_store(args)
    receipt = tstore.lock(Path(args.target).expanduser(),
                          mode=args.mode, source=args.source, relock=args.relock)
    store = _store(args)
    state = _ensure_state(store)
    state = store.write(replace(
        state, target_id=receipt.target_id,
        receipt_refs=state.receipt_refs + (
            {"kind": "target",
             "ref": f"targets/{receipt.target_id}/v{receipt.version}.json"},)))
    print(json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


class _EnvApproval:
    """One-shot approval read from the environment at call time."""

    def __init__(self, ceiling: int, token_env: str, fingerprint: str) -> None:
        self.ceiling = ceiling
        self.token_env = token_env
        self.fingerprint = fingerprint

    def pending(self) -> Approval | None:
        token = os.environ.get(self.token_env, "")
        if not token:
            return None
        return Approval(ceiling=self.ceiling,
                        request_fingerprint=self.fingerprint,
                        credit_token=token)


def cmd_step(args: argparse.Namespace) -> int:
    store = _store(args)
    state = _ensure_state(store)

    target_ref = next((ref for ref in state.receipt_refs
                       if ref.get("kind") == "target"), None)
    if target_ref is None:
        print(json.dumps({"ok": False,
                          "error": "lock a target first (lock-target)"}))
        return 1
    target_receipt = json.loads(
        (store.session_dir / str(target_ref["ref"])).read_text(encoding="utf-8"))
    target = {"ingestionMode": target_receipt["ingestionMode"],
              "targetId": target_receipt["targetId"],
              "prompt": args.prompt, "model": args.model,
              "ratio": args.ratio, "resolution": args.resolution,
              "resourceId": target_receipt.get("resourceId"),
              "refs": ([f"res:{target_receipt['resourceId']}"]
                       if target_receipt.get("resourceId") else [])}

    fingerprint = hashlib.sha256(
        f"{args.session_id}|{state.current_round}".encode()).hexdigest()
    controller = VisualLoopController(
        store=store, target=target,
        runtime=CliCanvasRuntime(project_id=args.project_id, probe=None) if False
        else _runtime(args),
        approval=_EnvApproval(ceiling=args.approve_credit_ceiling,
                              token_env=args.credit_token_env,
                              fingerprint=fingerprint),
        execution=CliExecution(store=store, project_id=args.project_id),
        artifacts=CliArtifacts(store=store, project_id=args.project_id,
                               approved_dir=Path(args.approved_root).expanduser()),
        judge=jx.PendingJudgePort(store),
        revision=_NoRevision())
    result = controller.run_until_pause()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _runtime(args: argparse.Namespace):
    """Build the CLI runtime with a live-schema probe; no network here."""
    from dreamina_canvas_adapter import run_dreamina_canvas
    from target_store import CapabilityProbe
    store = _store(args)
    probe = CapabilityProbe(runner=run_dreamina_canvas,
                            root=store.session_dir)
    return CliCanvasRuntime(runner=run_dreamina_canvas, probe=probe,
                            project_id=args.project_id)


class _NoRevision:
    """Phase-1 stand-in: a revision proposal is recorded, never auto-applied."""

    def propose(self, *, verdict):
        return {"changedFields": [], "deferred": True,
                "reason": "prompt revision lands in change section 8"}


def cmd_status(args: argparse.Namespace) -> int:
    store = _store(args)
    try:
        state = store.read()
    except StateStoreError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_request_judge(args: argparse.Namespace) -> int:
    store = _store(args)
    state = store.read()
    target_ref = next((ref for ref in state.receipt_refs
                       if ref.get("kind") == "target"), None)
    if target_ref is None:
        print(json.dumps({"ok": False, "error": "no locked target in this session"}))
        return 1
    target_receipt = json.loads(
        (store.session_dir / str(target_ref["ref"])).read_text(encoding="utf-8"))
    path = jx.write_judge_request(
        store, target_id=str(target_receipt["targetId"]),
        target_sha256=str(target_receipt["sha256"]),
        candidate_resource_id=args.candidate_resource_id,
        candidate_sha256=args.candidate_sha256)
    print(json.dumps({"ok": True, "request": str(path)}, ensure_ascii=False))
    return 0


def cmd_import_judge(args: argparse.Namespace) -> int:
    store = _store(args)
    payload = json.loads(Path(args.receipt).expanduser().read_text(encoding="utf-8"))
    try:
        path = jx.import_judge_receipt(store, payload)
    except jx.JudgeExchangeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "receipt": str(path)}, ensure_ascii=False))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    from loop_state import REMOTE_PENDING_STATES

    store = _store(args)
    state = _ensure_state(store)
    target = ("DRAINING_ACCEPTED" if state.state in REMOTE_PENDING_STATES
              else "STOPPED")
    if state.state != target:
        state = advance(state, target)
        store.write(state)
    print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="visual-loop", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--root", default=".dreamina-loop")
        p.add_argument("--approved-root", default=".")
        p.add_argument("--session-id", required=True)

    p = sub.add_parser("lock-target")
    common(p)
    p.add_argument("target")
    p.add_argument("--mode", choices=("judge_only", "canvas_reference"),
                   default="judge_only")
    p.add_argument("--source", choices=("user_supplied", "agent_generated"),
                   default="user_supplied")
    p.add_argument("--relock", action="store_true")
    p.set_defaults(func=cmd_lock_target)

    p = sub.add_parser("step")
    common(p)
    p.add_argument("--project-id", required=True)
    p.add_argument("--prompt", default="")
    p.add_argument("--model", default="")
    p.add_argument("--ratio", default="1:1")
    p.add_argument("--resolution", default="1K")
    p.add_argument("--approve-credit-ceiling", type=int, default=0)
    p.add_argument("--credit-token-env", default="DREAMINA_CANVAS_CREDIT_TOKEN")
    p.set_defaults(func=cmd_step)

    p = sub.add_parser("status")
    common(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("request-judge")
    common(p)
    p.add_argument("--candidate-resource-id", required=True)
    p.add_argument("--candidate-sha256", required=True)
    p.set_defaults(func=cmd_request_judge)

    p = sub.add_parser("import-judge")
    common(p)
    p.add_argument("receipt")
    p.set_defaults(func=cmd_import_judge)

    p = sub.add_parser("stop")
    common(p)
    p.set_defaults(func=cmd_stop)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from loop_state import LoopStateError
    from target_store import TargetError
    try:
        return args.func(args)
    except (LoopStateError, TargetError, jx.JudgeExchangeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
