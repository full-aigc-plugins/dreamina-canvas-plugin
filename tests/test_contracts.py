"""Contract tests for schemas/ (downstream Task 2).

Plan Step 1: every schema is closed (additionalProperties=false) and
rejects secret-like field names. Step 4: positive and negative fixtures
are validated.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"

FORBIDDEN_FIELD_NAMES = (
    "access_token",
    "refresh_token",
    "cookie",
    "signed_url",
    "signedurl",
    "creditconfirmationtoken",
    "credit_confirmation_token",
)


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _validator_for(name: str):
    schema = _load(name)
    base = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
    }
    base.update(schema)
    return jsonschema.Draft202012Validator(base)


class ContractTests(unittest.TestCase):
    def test_all_contracts_are_closed_and_reject_secrets(self) -> None:
        paths = sorted(SCHEMAS.glob("*.schema.json"))
        self.assertEqual(len(paths), 7)
        for path in paths:
            schema = _load(path.name)
            self.assertIs(
                schema.get("additionalProperties"), False, path.name
            )
            serialized = json.dumps(schema).lower()
            for forbidden in FORBIDDEN_FIELD_NAMES:
                self.assertNotIn(forbidden, serialized, path.name)

    def test_capability_snapshot_positive(self) -> None:
        v = _validator_for("capability_snapshot.schema.json")
        v.validate(
            {
                "cliVersion": "1.0.0",
                "cliCommit": "ae2c968",
                "cliEdition": "public",
                "cliDistribution": "cn",
                "schemaHash": "abc123",
                "fetchedAt": "2026-09-12T00:00:00Z",
            }
        )

    def test_capability_snapshot_rejects_uppercase_commit(self) -> None:
        v = _validator_for("capability_snapshot.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(
                {
                    "cliVersion": "1.0.0",
                    "cliCommit": "AE2C968",
                    "cliEdition": "public",
                    "cliDistribution": "cn",
                    "schemaHash": "abc123",
                    "fetchedAt": "2026-09-12T00:00:00Z",
                }
            )

    def test_command_result_positive(self) -> None:
        v = _validator_for("command_result.schema.json")
        v.validate(
            {
                "exit_code": 0,
                "payload": {"data": "ok"},
                "error": None,
                "required_action": "none",
                "partial_data": None,
            }
        )

    def test_command_result_failure_envelope(self) -> None:
        v = _validator_for("command_result.schema.json")
        v.validate(
            {
                "exit_code": 20,
                "payload": None,
                "error": {
                    "code": "cli.node_run_unknown",
                    "message": "operation not converged",
                    "requiredAction": "resume",
                },
                "required_action": "resume",
                "partial_data": {"items": []},
            }
        )

    def test_quote_receipt_rejects_uppercase_uuid_in_items(self) -> None:
        v = _validator_for("quote_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(
                {
                    "projectId": "00112233-4455-6677-8899-aabbccddeeff",
                    "orderedNodeIds": ["node_x"],
                    "items": [{"nodeId": "NODE_X"}],
                    "totalMaxCredits": 100,
                    "confirmable": True,
                }
            )

    def test_approval_receipt_rejects_empty_submit_id(self) -> None:
        v = _validator_for("operation_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(
                {
                    "projectId": "00112233-4455-6677-8899-aabbccddeeff",
                    "nodeId": "node_x",
                    "submitId": "",
                    "lastKnownState": "in_progress",
                    "resubmittable": False,
                    "requiredAction": "resume",
                    "fetchedAt": "2026-09-12T00:00:00Z",
                }
            )

    def test_artifact_receipt_requires_checksum(self) -> None:
        v = _validator_for("artifact_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(
                {
                    "resourceId": "00112233-4455-6677-8899-aabbccddeeff",
                    "canonicalPath": "/tmp/out.bin",
                    "byteCount": 5,
                    "media": {"mime": "image/png"},
                }
            )

    def test_artifact_receipt_rejects_uppercase_resource_id(self) -> None:
        v = _validator_for("artifact_receipt.schema.json")
        with self.assertRaises(jsonschema.ValidationError):
            v.validate(
                {
                    "resourceId": "00112233-4455-6677-8899-AABBCCDDEEFF",
                    "canonicalPath": "/tmp/out.bin",
                    "byteCount": 5,
                    "sha256": "0" * 64,
                    "media": {"mime": "image/png"},
                }
            )


if __name__ == "__main__":
    unittest.main()
