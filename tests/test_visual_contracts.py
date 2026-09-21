"""Contract tests for the visual-quality-loop schemas.

Task 3.1/3.6: every new contract is closed (`additionalProperties: false`),
rejects secret-shaped fields, and enforces its semantic invariants in the
schema itself rather than in prose.

Task 3.2-3.5: positive and negative fixtures for all seven contracts.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"

UUID_A = "00112233-4455-6677-8899-aabbccddeeff"
UUID_B = "ffeeddcc-bbaa-9988-7766-554433221100"
SHA = "a" * 64
SHA2 = "b" * 64
UTC = "2026-09-21T12:00:00Z"

# The whole point of the scan: none of these may appear anywhere in a receipt.
SECRET_FIELD_NAMES = (
    "access_token", "refresh_token", "cookie", "signed_url", "signedurl",
    "creditconfirmationtoken", "credit_confirmation_token", "secret",
    "api_key", "apikey", "private_key",
)


def _validator_for(name: str):
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    base = {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "additionalProperties": False}
    base.update(schema)
    return jsonschema.Draft202012Validator(base)


def target_receipt(**over):
    fixture = {
        "schemaVersion": "visual_target_receipt/1",
        "targetId": UUID_A, "version": 1, "sha256": SHA, "bytes": 2048,
        "mediaType": "image/png",
        "dimensions": {"width": 1024, "height": 1024},
        "source": "user_supplied", "ingestionMode": "judge_only",
        "lockedAt": UTC,
    }
    fixture.update(over)
    return fixture


def round_receipt(**over):
    fixture = {
        "schemaVersion": "visual_round_receipt/1",
        "sessionId": UUID_A, "roundId": UUID_B, "targetId": UUID_A,
        "nodeId": "node_abc123", "mutationVersion": 3,
        "generationFingerprint": SHA, "submitId": UUID_B,
        "decision": "completed", "createdAt": UTC,
    }
    fixture.update(over)
    return fixture


def judge_request(**over):
    fixture = {
        "schemaVersion": "judge_request/1", "requestId": UUID_A,
        "target": {"targetId": UUID_A, "sha256": SHA},
        "candidate": {"resourceId": UUID_B, "sha256": SHA2, "mediaType": "image/png"},
        "rubricVersion": "vision_judge/1",
        "freshContext": True, "forbidPromptDraft": True, "createdAt": UTC,
    }
    fixture.update(over)
    return fixture


def judge_receipt(**over):
    fixture = {
        "schemaVersion": "judge_receipt/1", "judgeId": UUID_A,
        "adapter": "host_subagent", "modelClass": "gpt-6-astra",
        "targetSha256": SHA, "candidateSha256": SHA2,
        "scores": {"composition": 2.5, "lighting": 2.0, "materials": 2.5,
                   "details": 0.5, "total": 7.5},
        "gaps": [{"dimension": "lighting", "severity": "high",
                  "location": "面部右侧高光",
                  "observation": "主光方向与目标相反",
                  "fixHint": "key light 转到左上方 30°"}],
        "recommendation": "revise",
        "freshContext": True, "sawPromptDraft": False, "judgedAt": UTC,
    }
    fixture.update(over)
    return fixture


def loop_budget(**over):
    fixture = {
        "schemaVersion": "loop_budget/1", "mode": "per_round", "maxRounds": 3,
        "spent": 0, "reserved": 100, "unknown": 0,
        "stallPolicy": {"maxRoundsWithoutImprovement": 2,
                        "maxRepeatedGaps": 2, "maxReplans": 1},
    }
    fixture.update(over)
    return fixture


def loop_state(**over):
    fixture = {
        "schemaVersion": "visual_loop_state/1", "sessionId": UUID_A,
        "state": "AWAITING_JUDGE",
        "currentRound": 1, "pendingOperations": [], "receiptRefs": [],
        "stopRequested": False, "revisionCount": 0, "updatedAt": UTC,
    }
    fixture.update(over)
    return fixture


def revision_receipt(**over):
    fixture = {
        "schemaVersion": "prompt_revision_receipt/1", "baseMutationVersion": 3,
        "baseFingerprint": SHA, "resultFingerprint": SHA2,
        "judgeReceiptId": UUID_A, "updateId": UUID_B,
        "changedFields": ["prompt", "refs"], "result": "applied", "createdAt": UTC,
    }
    fixture.update(over)
    return fixture


POSITIVE = {
    "visual_target_receipt.schema.json": target_receipt,
    "visual_round_receipt.schema.json": round_receipt,
    "judge_request.schema.json": judge_request,
    "judge_receipt.schema.json": judge_receipt,
    "loop_budget.schema.json": loop_budget,
    "visual_loop_state.schema.json": loop_state,
    "prompt_revision_receipt.schema.json": revision_receipt,
}


class VisualContractTests(unittest.TestCase):
    # ---- 3.1 closure + 3.6 secrets -------------------------------------
    def test_every_new_contract_is_closed(self) -> None:
        for name in POSITIVE:
            schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
            self.assertIs(schema.get("additionalProperties"), False, name)

    def test_every_new_contract_rejects_an_unknown_field(self) -> None:
        for name, make in POSITIVE.items():
            with self.subTest(schema=name):
                with self.assertRaises(jsonschema.ValidationError):
                    _validator_for(name).validate(make(rogueField="x"))

    def test_every_new_contract_rejects_secret_shaped_fields(self) -> None:
        for name, make in POSITIVE.items():
            for secret in SECRET_FIELD_NAMES:
                with self.subTest(schema=name, field=secret):
                    with self.assertRaises(jsonschema.ValidationError):
                        _validator_for(name).validate(make(**{secret: "leaked"}))

    def test_no_secret_name_is_declared_by_any_new_contract(self) -> None:
        """Scan declared property NAMES, not prose: a description may legitimately
        contain the word "secret" while stating that a token is never stored."""
        def property_names(node) -> set[str]:
            found: set[str] = set()
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "properties" and isinstance(value, dict):
                        found.update(value.keys())
                    found |= property_names(value)
            elif isinstance(node, list):
                for item in node:
                    found |= property_names(item)
            return found

        for name in POSITIVE:
            declared = {n.lower() for n in property_names(
                json.loads((SCHEMAS / name).read_text(encoding="utf-8")))}
            for secret in SECRET_FIELD_NAMES:
                self.assertNotIn(secret, declared, f"{name} declares {secret}")

    # ---- 3.2 VisualTargetReceipt ---------------------------------------
    def test_target_receipt_positive(self) -> None:
        _validator_for("visual_target_receipt.schema.json").validate(target_receipt())

    def test_target_receipt_judge_only_must_not_carry_resource_id(self) -> None:
        v = _validator_for("visual_target_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(target_receipt(ingestionMode="judge_only", resourceId=UUID_A))

    def test_target_receipt_canvas_reference_declares_its_import_kind(self) -> None:
        """Lock time declares the mode and import kind; the resourceId only
        appears once an upload is confirmed (spec: 'and upload confirmed')."""
        v = _validator_for("visual_target_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(target_receipt(ingestionMode="canvas_reference"))
        v.validate(target_receipt(ingestionMode="canvas_reference",
                                  importKind="local_upload"))
        v.validate(target_receipt(ingestionMode="canvas_reference",
                                  importKind="local_upload", resourceId=UUID_A,
                                  uploadEvidence=SHA))

    def test_target_receipt_judge_only_forbids_import_kind_too(self) -> None:
        v = _validator_for("visual_target_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(target_receipt(ingestionMode="judge_only",
                                      importKind="local_upload"))

    def test_target_receipt_rejects_uppercase_digest_and_non_utc_time(self) -> None:
        v = _validator_for("visual_target_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(target_receipt(sha256=SHA.upper()))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(target_receipt(lockedAt="2026-09-21T12:00:00+08:00"))

    # ---- 3.3 VisualRoundReceipt ----------------------------------------
    def test_round_receipt_positive_and_optional_blocks(self) -> None:
        v = _validator_for("visual_round_receipt.schema.json")
        v.validate(round_receipt())
        v.validate(round_receipt(
            quoteRef={"quoteId": UUID_A, "totalMaxCredits": 100, "ceiling": 100},
            approvalRef={"requestFingerprint": SHA, "expiry": UTC},
            artifactRef={"resourceId": UUID_B, "sha256": SHA2, "bytes": 2048},
            judgeRef={"judgeId": UUID_B}))

    def test_round_receipt_approval_ref_cannot_carry_a_token(self) -> None:
        v = _validator_for("visual_round_receipt.schema.json")
        for leaked in ({"token": "x"}, {"creditConfirmationToken": "x"},
                       {"signedUrl": "https://x"}):
            with self.subTest(leaked=leaked):
                with self.assertRaises(jsonschema.ValidationError):
                    v.validate(round_receipt(
                        approvalRef={"requestFingerprint": SHA, "expiry": UTC, **leaked}))

    def test_round_receipt_rejects_unknown_decision(self) -> None:
        v = _validator_for("visual_round_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(round_receipt(decision="accepted"))

    # ---- 3.4 JudgeRequest + JudgeReceipt --------------------------------
    def test_judge_request_requires_fresh_context_and_no_prompt_draft(self) -> None:
        v = _validator_for("judge_request.schema.json")
        v.validate(judge_request())
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_request(freshContext=False))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_request(forbidPromptDraft=False))

    def test_judge_receipt_positive(self) -> None:
        _validator_for("judge_receipt.schema.json").validate(judge_receipt())

    def test_judge_receipt_enforces_fresh_context_hygiene(self) -> None:
        v = _validator_for("judge_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_receipt(freshContext=False))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_receipt(sawPromptDraft=True))

    def test_judge_receipt_score_ranges_and_dimension_caps(self) -> None:
        v = _validator_for("judge_receipt.schema.json")
        # details is capped at 1 so it cannot compensate for other dimensions.
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_receipt(
                scores={"composition": 3, "lighting": 3, "materials": 3,
                        "details": 2, "total": 11}))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_receipt(
                scores={"composition": 4, "lighting": 0, "materials": 0,
                        "details": 0, "total": 4}))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_receipt(
                scores={"composition": 0, "lighting": 0, "materials": 0,
                        "details": 0, "total": 11}))
        # `total == sum(dimensions)` is arithmetic and cannot be expressed in
        # JSON Schema; it is a runtime invariant of the JudgePort validator.
        # This schema deliberately validates ranges only.

    def test_judge_receipt_gap_must_name_location_observation_and_fix(self) -> None:
        v = _validator_for("judge_receipt.schema.json")
        for dropped in ("location", "observation", "fixHint"):
            with self.subTest(dropped=dropped):
                gap = {"dimension": "lighting", "severity": "low",
                       "location": "x", "observation": "y", "fixHint": "z"}
                gap.pop(dropped)
                with self.assertRaises(jsonschema.ValidationError):
                    v.validate(judge_receipt(gaps=[gap]))

    def test_judge_receipt_rejects_content_unbound_digests(self) -> None:
        v = _validator_for("judge_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_receipt(targetSha256="not-a-digest"))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(judge_receipt(candidateSha256=SHA2.upper()))

    # ---- 3.5 LoopBudget / VisualLoopState / PromptRevisionReceipt --------
    def test_loop_budget_rejects_negative_accounting(self) -> None:
        v = _validator_for("loop_budget.schema.json")
        v.validate(loop_budget())
        for field in ("spent", "reserved", "unknown"):
            with self.subTest(field=field):
                with self.assertRaises(jsonschema.ValidationError):
                    v.validate(loop_budget(**{field: -1}))

    def test_loop_budget_requires_a_stall_policy(self) -> None:
        v = _validator_for("loop_budget.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(loop_budget(stallPolicy=None))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(loop_budget(stallPolicy={"maxRepeatedGaps": 2}))

    def test_loop_state_accepts_only_the_declared_states(self) -> None:
        v = _validator_for("visual_loop_state.schema.json")
        for state in ("CREATED", "TARGET_LOCKED", "TARGET_REGISTERED", "DRAFT_SAVED",
                      "QUOTED", "AWAITING_APPROVAL", "SUBMITTED", "WAITING",
                      "ARTIFACT_VERIFIED", "AWAITING_JUDGE", "JUDGED",
                      "REVISION_PROPOSED", "COMPLETED", "PAUSED", "STALLED",
                      "STOP_REQUESTED", "DRAINING_ACCEPTED", "STOPPED", "FAILED"):
            with self.subTest(state=state):
                v.validate(loop_state(state=state))
        for bogus in ("RUNNING", "done", "TARGET_LOCKED "):
            with self.subTest(state=bogus):
                with self.assertRaises(jsonschema.ValidationError):
                    v.validate(loop_state(state=bogus))

    def test_loop_state_cannot_claim_a_remote_cancel(self) -> None:
        """Stopping prevents NEW submissions; it is never a vendor cancel."""
        v = _validator_for("visual_loop_state.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(loop_state(remoteCancelled=True))

    def test_loop_state_pending_operations_bind_submit_and_node(self) -> None:
        v = _validator_for("visual_loop_state.schema.json")
        v.validate(loop_state(pendingOperations=[{"submitId": UUID_A, "nodeId": "node_x"}]))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(loop_state(pendingOperations=[{"submitId": UUID_A}]))

    def test_revision_receipt_requires_at_least_one_changed_field(self) -> None:
        v = _validator_for("prompt_revision_receipt.schema.json")
        v.validate(revision_receipt())
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(revision_receipt(changedFields=[]))

    def test_revision_receipt_rejects_unknown_generation_field(self) -> None:
        v = _validator_for("prompt_revision_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(revision_receipt(changedFields=["prompt", "seed"]))

    def test_revision_receipt_distinguishes_refusal_from_application(self) -> None:
        v = _validator_for("prompt_revision_receipt.schema.json")
        v.validate(revision_receipt(result="refused_fidelity"))
        v.validate(revision_receipt(result="paused_concurrent_change"))
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(revision_receipt(result="ok"))


class ContractPackagingTests(unittest.TestCase):
    """Task 3.7: the distribution validator must reject a contract that stops
    being closed, parseable, or self-identifying. Without these cases the
    validator itself would be the next false green."""

    def _errors_for(self, filename: str, payload: str) -> list[str]:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_distribution import validate_contracts

        with tempfile.TemporaryDirectory() as tmp:
            schemas = Path(tmp) / "schemas"
            schemas.mkdir()
            (schemas / filename).write_text(payload, encoding="utf-8")
            return validate_contracts(Path(tmp))

    def test_open_contract_is_rejected(self) -> None:
        errors = self._errors_for(
            "bad.schema.json",
            json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$id": "dreamina-canvas/schemas/bad.schema.json"}))
        self.assertTrue(any("closed" in e for e in errors), errors)

    def test_wrong_dialect_is_rejected(self) -> None:
        errors = self._errors_for(
            "bad.schema.json",
            json.dumps({"$schema": "http://json-schema.org/draft-07/schema#",
                        "$id": "dreamina-canvas/schemas/bad.schema.json",
                        "additionalProperties": False}))
        self.assertTrue(any("2020-12" in e for e in errors), errors)

    def test_foreign_id_is_rejected(self) -> None:
        errors = self._errors_for(
            "bad.schema.json",
            json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$id": "other/schemas/bad.schema.json",
                        "additionalProperties": False}))
        self.assertTrue(any("$id" in e for e in errors), errors)

    def test_unparseable_contract_is_rejected(self) -> None:
        errors = self._errors_for("bad.schema.json", "{not json")
        self.assertTrue(any("unparseable" in e for e in errors), errors)

    def test_empty_schemas_directory_is_rejected(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_distribution import validate_contracts

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "schemas").mkdir()
            errors = validate_contracts(Path(tmp))
        self.assertTrue(any("missing shipped JSON contracts" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
