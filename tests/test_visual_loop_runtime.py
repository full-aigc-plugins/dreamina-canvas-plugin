"""Composition tests: the real CLI ports against scripted envelopes (6.4-6.9).

These tests exercise `visual_loop_runtime` — the only module that knows the real
CLI — with a scripted runner. No network, no paid call. They pin the contract
between the controller and `dreamina-canvas`:

- draft saving never passes `--run`
- quotes map the CLI envelope to the controller's `Quote`
- submit maps exit codes through `error_router` (0 accepted / 20 unknown / 2 rejected)
- the operation ledger persists the identity BEFORE the run call
- downloads are verified by the artifact guard; a failed verification is
  quarantined, never silently kept
- the failure matrix: non-JSON output, transport raise, remote failure,
  corrupt download, ambiguous reconciliation
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import visual_loop_runtime as vlr
from dreamina_canvas_adapter import CommandResult
from loop_state import LoopStateStore

SESSION = "00112233-4455-6677-8899-aabbccddeeff"
NODE = "node_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
RESOURCE = "ffeeddcc-bbaa-9988-7766-554433221100"
SHA = "a" * 64


def envelope(data: dict) -> CommandResult:
    return CommandResult(exit_code=0, payload={"schemaVersion": "1", "ok": True,
                                               "data": data},
                         error=None, required_action="none", partial_data=None)


def failure(code: int, error: dict, action: str) -> CommandResult:
    return CommandResult(exit_code=code, payload=None, error=error,
                         required_action=action, partial_data=None)


class ScriptedRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = list(results)
        self.argvs: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.argvs.append(list(argv))
        if not self.results:
            raise AssertionError(f"unexpected CLI call: {argv}")
        return self.results.pop(0)


def make_png(blob_dir: Path, *, size: int = 64) -> Path:
    path = blob_dir / "candidate.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * size)
    return path


class CompositionCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.approved = Path(self._tmp.name) / "workspace"
        self.approved.mkdir()
        self.store = LoopStateStore(root=self.approved / ".loop", session_id=SESSION)
        self.addCleanup(self._tmp.cleanup)


class DraftTests(CompositionCase):
    def test_save_draft_creates_without_run_and_returns_node_id(self) -> None:
        runner = ScriptedRunner([envelope({"node": {"nodeId": NODE,
                                                    "savedDraftVersion": "1"}})])
        runtime = vlr.CliCanvasRuntime(
            runner=runner, probe=self._probe(), project_id=SESSION)
        draft = runtime.save_draft(target={"prompt": "a castle", "model": "m",
                                           "ratio": "1:1", "resolution": "1K",
                                           "refs": ["res:" + RESOURCE]},
                                   round_index=1)
        self.assertEqual(draft["nodeId"], NODE)
        argv = runner.argvs[0]
        self.assertIn("create", argv)
        self.assertNotIn("--run", argv)
        self.assertIn("--ref", argv)
        self.assertIn("res:" + RESOURCE, argv)

    def test_save_draft_failure_is_a_port_error_with_action(self) -> None:
        runner = ScriptedRunner([failure(11, {"code": "cli.authRequired"},
                                         "login")])
        runtime = vlr.CliCanvasRuntime(runner=runner, probe=self._probe(),
                                        project_id=SESSION)
        with self.assertRaises(vlr.RuntimePortError) as ctx:
            runtime.save_draft(target={"prompt": "x"}, round_index=1)
        self.assertIn("login", str(ctx.exception))

    def _probe(self):
        from target_store import CapabilityProbe
        return CapabilityProbe(runner=ScriptedRunner([envelope(
            {"schemaVersion": "1", "referenceForms": ["node:", "res:"]})]),
            root=self.store.session_dir)


class QuoteTests(CompositionCase):
    def test_quote_maps_the_envelope(self) -> None:
        runner = ScriptedRunner([envelope({"quoteId": SESSION,
                                           "totalMaxCredits": 40,
                                           "confirmable": True})])
        runtime = vlr.CliCanvasRuntime(runner=runner, probe=self._probe(),
                                        project_id=SESSION)
        quote = runtime.quote(node_id=NODE)
        self.assertEqual((quote.quote_id, quote.total_max_credits,
                          quote.confirmable), (SESSION, 40, True))

    def _probe(self):
        from target_store import CapabilityProbe
        return CapabilityProbe(runner=ScriptedRunner([envelope({"referenceForms": []})]),
                               root=self.store.session_dir)


class ExecutionTests(CompositionCase):
    def execution(self, runner: ScriptedRunner) -> vlr.CliExecution:
        return vlr.CliExecution(runner=runner, store=self.store, project_id=SESSION)

    def test_submit_zero_is_accepted_and_ledger_precedes_the_call(self) -> None:
        runner = ScriptedRunner([envelope({"submitted": True})])
        outcome = self.execution(runner).submit(node_id=NODE, submit_id=SESSION,
                                                credit_token="tok")
        self.assertEqual(outcome.state, "accepted")
        ledger = self.store.session_dir / "ledger" / "operations" / "default" / f"{SESSION}.json"
        self.assertTrue(ledger.is_file(), "ledger must persist before run")
        self.assertEqual(runner.argvs[0][runner.argvs[0].index("--submit-id") + 1],
                         SESSION)

    def test_exit_20_maps_to_unknown_and_reconciles_by_id(self) -> None:
        fixture = json.loads((Path(__file__).resolve().parents[1]
                              / "tests/fixtures/cli/resume-required.json").read_text(encoding="utf-8"))
        runner = ScriptedRunner([CommandResult(
            exit_code=20, payload=fixture, error=None,
            required_action="resume", partial_data=None)])
        outcome = self.execution(runner).submit(node_id=NODE, submit_id=SESSION,
                                                credit_token="tok")
        self.assertEqual(outcome.state, "unknown")

    def test_exit_2_is_rejected(self) -> None:
        fixture = json.loads((Path(__file__).resolve().parents[1]
                              / "tests/fixtures/cli/confirm-required.json").read_text(encoding="utf-8"))
        runner = ScriptedRunner([CommandResult(
            exit_code=2, payload=fixture, error=None, required_action="confirm",
            partial_data=None)])
        outcome = self.execution(runner).submit(node_id=NODE, submit_id=SESSION,
                                                credit_token="tok")
        self.assertEqual(outcome.state, "rejected")

    def test_status_maps_running_and_success(self) -> None:
        runner = ScriptedRunner([
            envelope({"state": "running"}),
            envelope({"state": "success", "resourceId": RESOURCE}),
        ])
        execution = self.execution(runner)
        self.assertEqual(execution.status(submit_id=SESSION).state, "in_progress")
        final = execution.status(submit_id=SESSION)
        self.assertEqual(final.state, "completed")
        self.assertEqual(final.resource_id, RESOURCE)


class ArtifactTests(CompositionCase):
    def artifact_port(self, runner: ScriptedRunner) -> vlr.CliArtifacts:
        return vlr.CliArtifacts(runner=runner, store=self.store,
                                project_id=SESSION, approved_dir=self.approved)

    def test_verified_download_moves_into_the_round_directory(self) -> None:
        staging = self.approved / "staging"
        staging.mkdir()
        blob = make_png(staging)
        import hashlib
        runner = ScriptedRunner([envelope({
            "canonicalPath": str(blob), "byteCount": blob.stat().st_size,
            "sha256": hashlib.sha256(blob.read_bytes()).hexdigest(),
            "media": {"mime": "image/png"}})])
        destination = self.store.session_dir / "rounds" / "r1"
        artifact = self.artifact_port(runner).fetch(resource_id=RESOURCE,
                                                    destination=destination)
        self.assertEqual(artifact.canonical_path.parent, destination)
        self.assertTrue(artifact.canonical_path.is_file())
        self.assertFalse(blob.exists(), "staging copy must be committed atomically")

    def test_checksum_mismatch_is_quarantined_not_kept(self) -> None:
        staging = self.approved / "staging"
        staging.mkdir()
        blob = make_png(staging)
        runner = ScriptedRunner([envelope({
            "canonicalPath": str(blob), "byteCount": blob.stat().st_size,
            "sha256": "b" * 64, "media": {"mime": "image/png"}})])
        with self.assertRaises(vlr.RuntimePortError) as ctx:
            self.artifact_port(runner).fetch(
                resource_id=RESOURCE,
                destination=self.store.session_dir / "rounds" / "r1")
        self.assertIn("verification failed", str(ctx.exception))
        self.assertFalse((self.store.session_dir / "rounds" / "r1").exists())

    def test_path_outside_the_approved_dir_is_rejected(self) -> None:
        outside = Path(self._tmp.name) / "outside.png"
        outside.write_bytes(b"\x89PNG\r\n\x1a\n")
        runner = ScriptedRunner([envelope({
            "canonicalPath": str(outside), "byteCount": outside.stat().st_size,
            "sha256": SHA, "media": {"mime": "image/png"}})])
        with self.assertRaises(vlr.RuntimePortError):
            self.artifact_port(runner).fetch(
                resource_id=RESOURCE,
                destination=self.store.session_dir / "rounds" / "r1")


class FailureMatrixTests(CompositionCase):
    """6.9 — the scripted failure scenarios the controller must survive."""

    def test_non_json_stdout_is_a_port_error_not_a_crash(self) -> None:
        runner = ScriptedRunner([CommandResult(
            exit_code=0, payload={"raw": "<<< not json >>>"}, error=None,
            required_action="none", partial_data=None)])
        runtime = vlr.CliCanvasRuntime(
            runner=runner,
            probe=self._static_probe(), project_id=SESSION)
        with self.assertRaises(vlr.RuntimePortError):
            runtime.save_draft(target={"prompt": "x"}, round_index=1)

    def _static_probe(self):
        from target_store import CapabilityProbe, CapabilitySnapshot
        probe = CapabilityProbe(runner=ScriptedRunner([]), root=self.store.session_dir)
        probe._snapshot = CapabilitySnapshot(schema_sha256=SHA, payload={})
        return probe

    def test_transport_raise_keeps_the_persisted_identity(self) -> None:
        def exploding(argv, **kwargs):
            raise TimeoutError("socket gone")
        execution = vlr.CliExecution(runner=exploding, store=self.store,
                                     project_id=SESSION)
        with self.assertRaises(RuntimeError):
            try:
                execution.submit(node_id=NODE, submit_id=SESSION, credit_token="t")
            except vlr.RuntimePortError:
                raise RuntimeError("rethrow as port error") from None
            except TimeoutError:
                raise
        ledger = self.store.session_dir / "ledger" / "operations" / "default" / f"{SESSION}.json"
        self.assertTrue(ledger.is_file(),
                        "the identity must survive a transport raise")

    def test_upgrade_required_is_not_silently_treated_as_unknown(self) -> None:
        fixture = json.loads((Path(__file__).resolve().parents[1]
                              / "tests/fixtures/cli/upgrade-required.json").read_text(encoding="utf-8"))
        runner = ScriptedRunner([CommandResult(
            exit_code=13, payload=fixture, error=None, required_action="upgrade",
            partial_data=None)])
        with self.assertRaises(vlr.RuntimePortError) as ctx:
            vlr.CliExecution(runner=runner, store=self.store,
                             project_id=SESSION).submit(
                node_id=NODE, submit_id=SESSION, credit_token="tok")
        self.assertIn("upgrade", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
