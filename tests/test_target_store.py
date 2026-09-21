"""Target locking, resource upload, and capability evidence (change section 5).

Task 5.1: failure-first coverage for the authorized target directory, media
probing, SHA-256 locking, same-path content change, and target versioning.
Task 5.2: `TargetStore` and `judge_only` — that mode must never upload or reach
a generation reference.
Task 5.3: Fake-CLI scenarios for the stable resource id: repeated calls,
query-after-timeout, an already-existing resource.
Task 5.5: live-schema probing with capability-cache invalidation; a schema that
disagrees with the managed skill contract must PAUSE, never guess.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import target_store as ts

SESSION = "00112233-4455-6677-8899-aabbccddeeff"
RESOURCE = "ffeeddcc-bbaa-9988-7766-554433221100"
SUBMIT = "00112233-4455-6677-8899-001122334455"


def png_bytes(*, width: int = 8, height: int = 6, seed: bytes = b"\x00") -> bytes:
    """A minimal, structurally valid PNG with a real IHDR."""

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + seed * (width * 3) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def jpeg_bytes(*, width: int = 4, height: int = 2) -> bytes:
    """A minimal JPEG carrying only the SOF0 marker the prober reads."""
    sof = (b"\xff\xc0" + struct.pack(">H", 17) + b"\x08"
           + struct.pack(">HH", height, width) + b"\x03" + b"\x01\x11\x00" * 3)
    return b"\xff\xd8" + sof + b"\xff\xd9"


class FakeRunner:
    """A scripted `dreamina-canvas` stand-in."""

    def __init__(self, results: list[dict]) -> None:
        self.results = list(results)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_kwargs):
        self.calls.append(list(argv))
        if not self.results:
            raise AssertionError(f"unexpected extra CLI call: {argv}")
        payload = self.results.pop(0)
        return ts.CommandOutcome(
            exit_code=payload.get("exit_code", 0),
            payload=payload.get("payload"),
            error=payload.get("error"),
            required_action=payload.get("required_action", "none"),
        )

    def uploaded_resource_ids(self) -> list[str]:
        found = []
        for argv in self.calls:
            if "upload" in argv:
                found.append(argv[argv.index("--resource-id") + 1])
        return found


class TargetLockTests(unittest.TestCase):
    """5.1 / 5.2 — locking inside an authorized directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.approved = Path(self._tmp.name) / "workspace"
        self.approved.mkdir()
        self.store = ts.TargetStore(root=self.approved / ".loop", session_id=SESSION,
                                   approved_root=self.approved)
        self.addCleanup(self._tmp.cleanup)

    def write(self, name: str, blob: bytes) -> Path:
        path = self.approved / name
        path.write_bytes(blob)
        return path

    def test_target_outside_the_approved_directory_is_refused(self) -> None:
        outside = Path(self._tmp.name) / "outside.png"
        outside.write_bytes(png_bytes())
        with self.assertRaises(ts.TargetError):
            self.store.lock(outside, mode="judge_only", source="user_supplied")

    def test_directory_is_not_a_target(self) -> None:
        with self.assertRaises(ts.TargetError):
            self.store.lock(self.approved, mode="judge_only", source="user_supplied")

    def test_empty_file_is_refused(self) -> None:
        with self.assertRaises(ts.TargetError):
            self.store.lock(self.write("empty.png", b""),
                            mode="judge_only", source="user_supplied")

    def test_unsupported_media_type_is_refused(self) -> None:
        with self.assertRaises(ts.TargetError):
            self.store.lock(self.write("notes.txt", b"just text"),
                            mode="judge_only", source="user_supplied")

    def test_png_is_probed_for_media_type_and_dimensions(self) -> None:
        receipt = self.store.lock(self.write("target.png", png_bytes(width=12, height=7)),
                                  mode="judge_only", source="user_supplied")
        self.assertEqual(receipt.media_type, "image/png")
        self.assertEqual((receipt.width, receipt.height), (12, 7))

    def test_jpeg_is_probed_for_media_type_and_dimensions(self) -> None:
        receipt = self.store.lock(self.write("target.jpg", jpeg_bytes(width=9, height=5)),
                                  mode="judge_only", source="user_supplied")
        self.assertEqual(receipt.media_type, "image/jpeg")
        self.assertEqual((receipt.width, receipt.height), (9, 5))

    def test_lock_records_the_content_digest_not_the_path(self) -> None:
        blob = png_bytes()
        receipt = self.store.lock(self.write("target.png", blob),
                                  mode="judge_only", source="user_supplied")
        self.assertEqual(receipt.sha256, hashlib.sha256(blob).hexdigest())
        self.assertEqual(receipt.bytes, len(blob))
        self.assertEqual(receipt.version, 1)

    def test_relocking_identical_content_is_idempotent(self) -> None:
        blob = png_bytes()
        first = self.store.lock(self.write("t.png", blob), mode="judge_only",
                                source="user_supplied")
        second = self.store.lock(self.approved / "t.png", mode="judge_only",
                                 source="user_supplied")
        self.assertEqual(first, second)
        self.assertEqual(second.version, 1)

    def test_same_path_with_new_content_refuses_to_continue(self) -> None:
        path = self.write("t.png", png_bytes(seed=b"\x00"))
        self.store.lock(path, mode="judge_only", source="user_supplied")
        path.write_bytes(png_bytes(seed=b"\x11"))
        with self.assertRaises(ts.TargetChanged):
            self.store.lock(path, mode="judge_only", source="user_supplied")

    def test_explicit_relock_creates_a_new_version(self) -> None:
        path = self.write("t.png", png_bytes(seed=b"\x00"))
        first = self.store.lock(path, mode="judge_only", source="user_supplied")
        path.write_bytes(png_bytes(seed=b"\x11"))
        second = self.store.lock(path, mode="judge_only", source="user_supplied",
                                 relock=True)
        self.assertEqual(second.target_id, first.target_id)
        self.assertEqual(second.version, 2)
        self.assertNotEqual(second.sha256, first.sha256)

    def test_receipt_on_disk_validates_against_the_shipped_contract(self) -> None:
        import jsonschema

        receipt = self.store.lock(self.write("t.png", png_bytes()),
                                  mode="judge_only", source="user_supplied")
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas"
                             / "visual_target_receipt.schema.json").read_text(encoding="utf-8"))
        base = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
        base.update(schema)
        jsonschema.Draft202012Validator(base).validate(
            json.loads(receipt.path.read_text(encoding="utf-8")))

    def test_locked_receipt_is_private(self) -> None:
        if os.name == "nt":
            self.skipTest("POSIX permission bits do not exist on Windows")
        receipt = self.store.lock(self.write("t.png", png_bytes()),
                                  mode="judge_only", source="user_supplied")
        self.assertEqual(oct(os.stat(receipt.path).st_mode & 0o777), "0o600")

    # ---- 5.2 judge_only never uploads -----------------------------------
    def test_judge_only_target_refuses_an_upload(self) -> None:
        receipt = self.store.lock(self.write("t.png", png_bytes()),
                                  mode="judge_only", source="user_supplied")
        with self.assertRaises(ts.TargetError):
            self.store.register_canvas_reference(receipt, resource_id=RESOURCE,
                                                 import_kind="local_upload",
                                                 upload_evidence="c" * 64)

    def test_judge_only_target_refuses_a_generation_reference(self) -> None:
        receipt = self.store.lock(self.write("t.png", png_bytes()),
                                  mode="judge_only", source="user_supplied")
        with self.assertRaises(ts.TargetError):
            self.store.generation_reference(receipt)

    def test_canvas_reference_requires_a_confirmed_resource_id(self) -> None:
        receipt = self.store.lock(self.write("t.png", png_bytes()),
                                  mode="canvas_reference", source="user_supplied")
        with self.assertRaises(ts.TargetError):
            self.store.generation_reference(receipt)
        registered = self.store.register_canvas_reference(
            receipt, resource_id=RESOURCE, import_kind="local_upload",
            upload_evidence="c" * 64)
        self.assertEqual(self.store.generation_reference(registered), f"res:{RESOURCE}")

    def test_register_rejects_a_non_canonical_resource_id(self) -> None:
        receipt = self.store.lock(self.write("t.png", png_bytes()),
                                  mode="canvas_reference", source="user_supplied")
        for bogus in (RESOURCE.upper(), "res:" + RESOURCE, "not-a-uuid"):
            with self.subTest(resource=bogus), self.assertRaises(ts.TargetError):
                self.store.register_canvas_reference(
                    receipt, resource_id=bogus, import_kind="local_upload",
                    upload_evidence="c" * 64)


class UploadTests(unittest.TestCase):
    """5.3 / 5.4 — the stable resource id contract."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.approved = Path(self._tmp.name) / "workspace"
        self.approved.mkdir()
        self.store = ts.TargetStore(root=self.approved / ".loop", session_id=SESSION,
                                   approved_root=self.approved)
        self.addCleanup(self._tmp.cleanup)
        self.image = self.approved / "t.png"
        self.image.write_bytes(png_bytes())

    def uploader(self, runner: FakeRunner) -> ts.ResourceUploader:
        return ts.ResourceUploader(runner=runner, store=self.store,
                                   project_id=RESOURCE)

    def test_upload_uses_one_stable_resource_id(self) -> None:
        runner = FakeRunner([{"payload": {"data": {"resourceId": RESOURCE}}}])
        outcome = self.uploader(runner).upload(
            path=self.image, resource_id=SUBMIT, import_kind="local_upload")
        self.assertEqual(outcome.resource_id, RESOURCE)
        self.assertEqual(runner.uploaded_resource_ids(), [SUBMIT])
        self.assertIn("resource", runner.calls[0])
        self.assertIn("upload", runner.calls[0])

    def test_upload_reuses_the_persisted_intent_across_retries(self) -> None:
        runner = FakeRunner([{"payload": {"data": {"resourceId": RESOURCE}}}])
        uploader = self.uploader(runner)
        uploader.upload(path=self.image, resource_id=SUBMIT, import_kind="local_upload")
        # Second attempt with the same id is idempotent: no second upload call.
        again = uploader.upload(path=self.image, resource_id=SUBMIT,
                                import_kind="local_upload")
        self.assertEqual(again.resource_id, RESOURCE)
        self.assertEqual(len(runner.uploaded_resource_ids()), 1)

    def test_ambiguous_upload_queries_instead_of_minting_a_new_id(self) -> None:
        runner = FakeRunner([
            {"exit_code": 21, "error": {"code": "cli.timeout"},
             "required_action": "retry"},
            {"payload": {"data": {"resourceId": RESOURCE, "status": "success"}}},
        ])
        outcome = self.uploader(runner).upload(
            path=self.image, resource_id=SUBMIT, import_kind="local_upload")
        self.assertEqual(outcome.resource_id, RESOURCE)
        # Exactly one upload, and the reconciliation used the SAME id.
        self.assertEqual(runner.uploaded_resource_ids(), [SUBMIT])
        self.assertTrue(any("get" in argv for argv in runner.calls),
                        f"expected a resource get reconciliation: {runner.calls}")

    def test_reconciliation_exhaustion_never_creates_a_second_resource(self) -> None:
        # One upload plus every reconciliation round the uploader is allowed.
        runner = FakeRunner([{"exit_code": 21, "error": {"code": "cli.timeout"},
                              "required_action": "retry"}] * 3)
        with self.assertRaises(ts.UploadUnresolved):
            self.uploader(runner).upload(path=self.image, resource_id=SUBMIT,
                                         import_kind="local_upload")
        self.assertEqual(runner.uploaded_resource_ids(), [SUBMIT])

    def test_already_registered_source_url_is_accepted(self) -> None:
        runner = FakeRunner([{
            "exit_code": 2,
            "error": {"code": "cli.resource_already_exists",
                      "message": "resource exists"},
            "required_action": "none",
            "payload": None,
        }, {"payload": {"data": {"resourceId": RESOURCE, "status": "success"}}}])
        outcome = self.uploader(runner).upload(
            path=self.image, resource_id=SUBMIT, import_kind="local_upload")
        self.assertEqual(outcome.resource_id, RESOURCE)

    def test_blank_resource_id_is_refused_before_any_call(self) -> None:
        runner = FakeRunner([])
        with self.assertRaises(ts.TargetError):
            self.uploader(runner).upload(path=self.image, resource_id="",
                                         import_kind="local_upload")
        self.assertEqual(runner.calls, [])

    def test_upload_rejects_an_unknown_import_kind(self) -> None:
        runner = FakeRunner([])
        with self.assertRaises(ts.TargetError):
            self.uploader(runner).upload(path=self.image, resource_id=SUBMIT,
                                         import_kind="sideways")
        self.assertEqual(runner.calls, [])


class CapabilityTests(unittest.TestCase):
    """5.5 — live-schema evidence, cache invalidation, pause-don't-guess."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".loop"
        self.addCleanup(self._tmp.cleanup)

    @staticmethod
    def schema_payload(reference_forms: list[str], version: str = "1") -> dict:
        return {"data": {"schemaVersion": version, "command": "dreamina-canvas",
                         "referenceForms": reference_forms}}

    def probe(self, payload: dict, runner: FakeRunner | None = None):
        runner = runner or FakeRunner([{"payload": payload}])
        return ts.CapabilityProbe(runner=runner, root=self.root)

    def test_probe_records_a_content_digest_of_the_live_schema(self) -> None:
        probe = self.probe(self.schema_payload(["node:", "res:"]))
        snapshot = probe.refresh()
        self.assertEqual(len(snapshot.schema_sha256), 64)
        self.assertEqual(probe.current().schema_sha256, snapshot.schema_sha256)

    def test_cache_is_reused_when_the_schema_is_unchanged(self) -> None:
        payload = self.schema_payload(["node:", "res:"])
        probe = self.probe(payload)
        probe.refresh()
        runner = FakeRunner([{"payload": payload}])
        probe.runner = runner
        probe.refresh()
        self.assertEqual(runner.calls, [], "an unchanged schema must not be re-fetched")

    def test_cache_invalidates_when_the_schema_changes(self) -> None:
        probe = self.probe(self.schema_payload(["node:", "res:"]))
        first = probe.refresh()
        later = ts.CapabilityProbe(
            runner=FakeRunner([{"payload": self.schema_payload(["node:", "res:", "uri:"])}]),
            root=self.root)
        second = later.refresh()
        self.assertNotEqual(first.schema_sha256, second.schema_sha256)
        self.assertIn("uri:", later.available_reference_forms())

    def test_contract_agreement_passes(self) -> None:
        probe = self.probe(self.schema_payload(["node:", "res:"]))
        probe.refresh()
        probe.assert_contract({"node:", "res:"})

    def test_skill_claiming_uri_while_the_schema_does_not_evidence_it_pauses(self) -> None:
        """The plugin must not silently accept a capability the runtime never proved."""
        probe = self.probe(self.schema_payload(["node:", "res:"]))
        probe.refresh()
        with self.assertRaises(ts.ContractMismatch) as ctx:
            probe.assert_contract({"node:", "res:", "uri:", "vid:", "file://"})
        message = str(ctx.exception)
        self.assertIn("uri:", message)
        self.assertIn("upstream", message.lower())

    def test_schema_missing_a_reference_form_the_skill_uses_pauses(self) -> None:
        probe = self.probe(self.schema_payload(["node:"]))
        probe.refresh()
        with self.assertRaises(ts.ContractMismatch):
            probe.assert_contract({"node:", "res:"})

    def test_unreadable_schema_never_yields_an_empty_capability_set(self) -> None:
        """An unparseable probe must fail, not look like 'no forms available'."""
        probe = ts.CapabilityProbe(
            runner=FakeRunner([{"exit_code": 1, "error": {"code": "cli.unknown"}}]),
            root=self.root)
        with self.assertRaises(ts.CapabilityError):
            probe.refresh()


if __name__ == "__main__":
    unittest.main()
