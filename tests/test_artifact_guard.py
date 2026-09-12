import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from artifact_guard import (  # noqa: E402
    ArtifactReceipt,
    hash_file,
    verify,
)


class ArtifactGuardTests(unittest.TestCase):
    def _write_file(self, tmp: Path, name: str, content: bytes) -> Path:
        path = tmp / name
        path.write_bytes(content)
        return path

    def test_approved_path_containment(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            approved = Path(td) / "approved"
            approved.mkdir()
            outside = Path(td) / "outside.bin"
            outside.write_bytes(b"hello")
            receipt = ArtifactReceipt(
                resource_id="res_00112233445566778899aabbccddeeff",
                canonical_path=outside,
                byte_count=5,
                sha256=hash_file(outside),
                media={"mime": "image/png"},
            )
            d = verify(receipt, approved_dir=approved)
            self.assertFalse(d.ok)
            self.assertIn("not within approved directory", d.reason)

    def test_byte_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            approved = Path(td)
            p = self._write_file(approved, "a.bin", b"hello world")
            receipt = ArtifactReceipt(
                resource_id="res_00112233445566778899aabbccddeeff",
                canonical_path=p,
                byte_count=999,
                sha256=hash_file(p),
                media={"mime": "image/png"},
            )
            d = verify(receipt, approved_dir=approved)
            self.assertFalse(d.ok)
            self.assertIn("byte count mismatch", d.reason)

    def test_sha256_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            approved = Path(td)
            p = self._write_file(approved, "a.bin", b"hello world")
            receipt = ArtifactReceipt(
                resource_id="res_00112233445566778899aabbccddeeff",
                canonical_path=p,
                byte_count=p.stat().st_size,
                sha256="0" * 64,
                media={"mime": "image/png"},
            )
            d = verify(receipt, approved_dir=approved)
            self.assertFalse(d.ok)
            self.assertIn("sha256 mismatch", d.reason)

    def test_media_metadata_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            approved = Path(td)
            p = self._write_file(approved, "a.bin", b"hello")
            receipt = ArtifactReceipt(
                resource_id="res_00112233445566778899aabbccddeeff",
                canonical_path=p,
                byte_count=p.stat().st_size,
                sha256=hash_file(p),
                media={},
            )
            d = verify(receipt, approved_dir=approved)
            self.assertFalse(d.ok)
            self.assertIn("media metadata missing", d.reason)

    def test_secret_field_in_payload_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            approved = Path(td)
            p = self._write_file(approved, "a.bin", b"hello")
            receipt = ArtifactReceipt(
                resource_id="res_00112233445566778899aabbccddeeff",
                canonical_path=p,
                byte_count=p.stat().st_size,
                sha256=hash_file(p),
                media={"mime": "image/png"},
            )
            d = verify(
                receipt,
                approved_dir=approved,
                raw_response={"signedUrl": "https://example.invalid/x"},
            )
            self.assertFalse(d.ok)
            self.assertIn("signedUrl", d.reason)

    def test_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            approved = Path(td)
            p = self._write_file(approved, "a.bin", b"hello world")
            receipt = ArtifactReceipt(
                resource_id="res_00112233445566778899aabbccddeeff",
                canonical_path=p,
                byte_count=p.stat().st_size,
                sha256=hash_file(p),
                media={"mime": "application/octet-stream"},
            )
            d = verify(receipt, approved_dir=approved)
            self.assertTrue(d.ok, d.reason)


if __name__ == "__main__":
    unittest.main()
