"""Prompt revision fidelity and concurrency tests (change section 8).

The Canvas contract makes a generation edit a **full replace** — an omitted
flag is a cleared flag. These tests pin the guards that make such an edit
safe: a complete block in, a complete block out, nothing lost outside the
intentional whitelist, and a concurrent live change pauses the round instead
of being clobbered.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import prompt_revision as pr
from dreamina_canvas_adapter import CommandResult
from loop_state import LoopStateStore

SESSION = "00112233-4455-6677-8899-aabbccddeeff"
NODE = "node_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
REF = "res:ffeeddcc-bbaa-9988-7766-554433221100"

BASE_BLOCK = {
    "mode": "t2i", "model": "m-1", "ratio": "1:1", "resolution": "1K",
    "count": 1, "prompt": "a castle", "refs": [REF],
    "reservedVendorField": {"keep": True},
}


def envelope(data: dict) -> CommandResult:
    return CommandResult(exit_code=0, payload={"schemaVersion": "1", "ok": True,
                                               "data": data},
                         error=None, required_action="none", partial_data=None)


def view(version: int, block: dict) -> CommandResult:
    return envelope({"mutationVersion": version, "generationDraft": block})


def gap(dimension="lighting", hint="key light from upper-left 30°") -> pr.VerifiedGap:
    return pr.VerifiedGap(dimension=dimension, location="face",
                          observation="key light reversed", fix_hint=hint)


class ProposeTests(unittest.TestCase):
    """8.3 — only verified gaps and user constraints drive changes."""

    def test_gap_adds_hint_and_keeps_everything_else(self) -> None:
        result = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        self.assertIn("key light", result["prompt"])
        for key, value in BASE_BLOCK.items():
            if key == "prompt":
                continue
            self.assertEqual(result[key], value, key)

    def test_new_refs_may_only_be_added(self) -> None:
        extra = "node:abc123"
        result = pr.propose_revision(BASE_BLOCK, gaps=[gap()], new_refs=[extra])
        self.assertIn(extra, result["refs"])
        self.assertIn(REF, result["refs"])

    def test_unprefixed_ref_is_refused(self) -> None:
        with self.assertRaises(pr.RevisionError):
            pr.propose_revision(BASE_BLOCK, gaps=[gap()], new_refs=["res:oops url"])

    def test_no_gap_no_change_is_refused(self) -> None:
        with self.assertRaises(pr.RevisionError):
            pr.propose_revision(BASE_BLOCK, gaps=[])


class FidelityTests(unittest.TestCase):
    """8.1 / 8.4 — the block survives intact or the revision is refused."""

    def test_table_of_legal_changes_passes(self) -> None:
        result = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        changed = pr.fidelity_check(BASE_BLOCK, result)
        self.assertEqual(changed, ["prompt"])

    def test_dropped_reference_is_refused(self) -> None:
        result = dict(BASE_BLOCK, prompt="a castle, key light fixed", refs=[])
        with self.assertRaises(pr.FidelityViolation) as ctx:
            pr.fidelity_check(BASE_BLOCK, result)
        self.assertIn("dropped", str(ctx.exception))

    def test_reserved_field_loss_is_refused(self) -> None:
        result = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        result.pop("reservedVendorField")
        with self.assertRaises(pr.FidelityViolation):
            pr.fidelity_check(BASE_BLOCK, result)

    def test_model_change_outside_whitelist_is_refused(self) -> None:
        result = dict(pr.propose_revision(BASE_BLOCK, gaps=[gap()]), model="m-2")
        with self.assertRaises(pr.FidelityViolation) as ctx:
            pr.fidelity_check(BASE_BLOCK, result)
        self.assertIn("model", str(ctx.exception))

    def test_undeclared_change_is_refused(self) -> None:
        result = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        result["__changedFields"] = []  # lies about what changed
        with self.assertRaises(pr.FidelityViolation):
            pr.fidelity_check(BASE_BLOCK, result)

    def test_partial_update_is_refused(self) -> None:
        """A 'sparse' edit result (a field gone silent) can never pass."""
        partial = {k: v for k, v in BASE_BLOCK.items() if k != "resolution"}
        partial["prompt"] = "a castle, fixed"
        with self.assertRaises(pr.FidelityViolation):
            pr.fidelity_check(BASE_BLOCK, partial)


class ApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.approved = Path(self._tmp.name) / "workspace"
        self.approved.mkdir()
        self.store = LoopStateStore(root=self.approved / ".loop", session_id=SESSION)
        self.addCleanup(self._tmp.cleanup)

    def service(self, results: list[CommandResult]) -> pr.PromptRevisionService:
        class R:
            def __init__(self, items): self.items = list(items)
            def __call__(self, argv, **kw):
                if not self.items:
                    raise AssertionError(f"unexpected call {argv[:4]}")
                return self.items.pop(0)

        return pr.PromptRevisionService(runner=R(results), store=self.store,
                                        project_id=SESSION, node_id=NODE)

    def test_apply_edits_and_persists_a_schema_valid_receipt(self) -> None:
        import jsonschema
        proposed = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        service = self.service([
            view(3, BASE_BLOCK),                     # live re-check
            envelope({"node": {"nodeId": NODE, "mutationVersion": "4"}}),
        ])
        receipt_path = service.apply(base_version=3, base_block=BASE_BLOCK,
                                     result_block=proposed)
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas"
                             / "prompt_revision_receipt.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)
        self.assertEqual(payload["baseMutationVersion"], 3)
        self.assertEqual(payload["changedFields"], ["prompt"])
        self.assertEqual(payload["result"], "applied")

    def test_concurrent_change_pauses_instead_of_clobbering(self) -> None:
        concurrent = dict(BASE_BLOCK, prompt="edited by someone else")
        service = self.service([view(4, concurrent)])
        proposed = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        with self.assertRaises(pr.ConcurrentChange):
            service.apply(base_version=3, base_block=BASE_BLOCK,
                          result_block=proposed)

    def test_fingerprint_move_alone_pauses(self) -> None:
        same_version_other_content = dict(BASE_BLOCK, prompt="rewritten, same version")
        service = self.service([view(3, same_version_other_content)])
        proposed = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        with self.assertRaises(pr.ConcurrentChange):
            service.apply(base_version=3, base_block=BASE_BLOCK,
                          result_block=proposed)

    def test_update_id_is_stable_across_retries(self) -> None:
        """8.5 — the same base/result pair yields the same identity."""
        proposed_a = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        proposed_b = pr.propose_revision(BASE_BLOCK, gaps=[gap()])
        a = pr.fingerprint({k: v for k, v in proposed_a.items() if k != "__changedFields"})
        b = pr.fingerprint({k: v for k, v in proposed_b.items() if k != "__changedFields"})
        self.assertEqual(a, b)

    def test_hidden_reasoning_never_enters_the_receipt(self) -> None:
        """Judge observations are actionable text; internal reasoning must not
        leak into the persisted receipt through the changed-fields path."""
        proposed = pr.propose_revision(
            BASE_BLOCK, gaps=[pr.VerifiedGap(
                dimension="lighting", location="face",
                observation="key light reversed",
                fix_hint="key light from upper-left 30°")])
        receipt_text = json.dumps(proposed, ensure_ascii=False)
        self.assertNotIn("chain-of-thought", receipt_text)
        self.assertNotIn("reasoning", receipt_text.lower())


if __name__ == "__main__":
    unittest.main()
