"""Direct unit tests for validate_distribution.validate (graph top hub).

The existing suite only reaches it through subprocess; these tests bind the
function directly so signature drift cannot slip through.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_distribution import validate, validate_contracts

ROOT = Path(__file__).resolve().parents[1]


class ValidateDistributionDirectTests(unittest.TestCase):
    def test_repository_root_validates_clean(self) -> None:
        self.assertEqual(validate(ROOT), [])

    def test_empty_root_reports_missing_pieces(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            errors = validate(Path(td))
        self.assertTrue(errors)
        self.assertTrue(any("missing" in e for e in errors), errors[:3])

    def test_open_contract_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "schemas").mkdir()
            (root / "schemas" / "bad.schema.json").write_text(
                '{"$schema": "https://json-schema.org/draft/2020-12/schema",'
                ' "$id": "dreamina-canvas/schemas/bad.schema.json"}',
                encoding="utf-8")
            errors = validate_contracts(root)
        self.assertTrue(any("closed" in e for e in errors), errors[:5])


if __name__ == "__main__":
    unittest.main()
