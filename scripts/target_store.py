"""Visual target locking, resource upload, and capability evidence.

Section 5 of `add-canvas-visual-quality-loop`.

Two ingestion modes, and the difference matters:

- ``judge_only`` — the file is hashed inside the authorized directory and used
  only as local evidence for a Judge. It must never be uploaded and must never
  reach a generation reference.
- ``canvas_reference`` — the file is uploaded **once** through the CLI's
  ``resource upload`` under a stable UUID, and only the confirmed
  ``res:<uuid>`` participates in generation references afterwards.

The stable UUID is the only identity the CLI exposes, so it is persisted as an
*intent* before the call: an ambiguous result is reconciled with the same id and
a new id is never minted (see `loop_state`).

Capability evidence (`CapabilityProbe`) keeps the live CLI schema as the single
source of truth for reference forms. When the managed skill's claims and the
live schema disagree, this module raises instead of guessing — the contract has
to be fixed upstream first.
"""

from __future__ import annotations

import hashlib
import json
import struct
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_state import LoopStateStore, _atomic_write, _exclusive_lock

SCHEMA_VERSION = "visual_target_receipt/1"
LATEST_TARGET_VERSION = "1"

INGESTION_MODES = ("judge_only", "canvas_reference")
IMPORT_KINDS = ("local_upload", "external_generated")
SOURCES = ("user_supplied", "agent_generated")
REFERENCE_FORMS = ("node:", "res:", "uri:", "vid:", "file://")

# A reference form the plugin may only claim when the live schema evidences it.
UNEVIDENCED_FORMS = frozenset({"uri:", "vid:", "file://"})

_TARGET_NAMESPACE = uuid.UUID("6f1d4b7a-6c2b-5f4e-9d38-2a0c9b7e5d41")


class TargetError(Exception):
    """The target cannot be used as requested."""


class TargetChanged(TargetError):
    """The same path now holds different content than the locked receipt."""


class UploadUnresolved(TargetError):
    """The upload outcome could not be reconciled; never retry with a new id."""


class CapabilityError(Exception):
    """The live CLI schema could not be established as evidence."""


class ContractMismatch(CapabilityError):
    """The managed skill contract disagrees with the live schema; pause."""


@dataclass(frozen=True)
class CommandOutcome:
    """What a CLI invocation produced, independent of how it was run."""

    exit_code: int
    payload: dict | None = None
    error: dict | None = None
    required_action: str = "none"

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def error_code(self) -> str:
        return str((self.error or {}).get("code") or "")

    def data(self) -> dict:
        return self.payload.get("data", {}) if isinstance(self.payload, dict) else {}


Runner = Callable[..., CommandOutcome]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- #
# Media probing (no third-party dependency)
# --------------------------------------------------------------------------- #

def probe_media(blob: bytes) -> tuple[str, int, int]:
    """Return ``(mediaType, width, height)`` or raise ``TargetError``."""
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        if blob[12:16] != b"IHDR":
            raise TargetError("PNG is missing its IHDR chunk")
        width, height = struct.unpack(">II", blob[16:24])
        return "image/png", int(width), int(height)

    if blob[:2] == b"\xff\xd8":
        index = 2
        while index + 9 < len(blob):
            if blob[index] != 0xFF:
                index += 1
                continue
            marker = blob[index + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            length = struct.unpack(">H", blob[index + 2:index + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", blob[index + 5:index + 9])
                return "image/jpeg", int(width), int(height)
            index += 2 + length
        raise TargetError("JPEG has no readable frame header")

    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        fourcc = blob[12:16]
        if fourcc == b"VP8X":
            width = int.from_bytes(blob[24:27], "little") + 1
            height = int.from_bytes(blob[27:30], "little") + 1
            return "image/webp", width, height
        if fourcc == b"VP8 ":
            width, height = struct.unpack("<HH", blob[26:30])
            return "image/webp", int(width) & 0x3FFF, int(height) & 0x3FFF
        if fourcc == b"VP8L":
            bits = int.from_bytes(blob[21:25], "little")
            return "image/webp", (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        raise TargetError("unsupported WebP variant")

    if blob[4:8] == b"ftyp":
        raise TargetError(
            "video targets are delivered with the frame-sampler port (change section 10); "
            "this phase locks still images only")

    raise TargetError("unsupported media type: not a PNG, JPEG, or WebP image")


# --------------------------------------------------------------------------- #
# Target store
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class TargetReceipt:
    target_id: str
    version: int
    sha256: str
    bytes: int
    media_type: str
    width: int
    height: int
    source: str
    ingestion_mode: str
    locked_at: str
    path: Path
    resource_id: str | None = None
    import_kind: str | None = None
    upload_evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schemaVersion": SCHEMA_VERSION,
            "targetId": self.target_id,
            "version": self.version,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "mediaType": self.media_type,
            "dimensions": {"width": self.width, "height": self.height},
            "source": self.source,
            "ingestionMode": self.ingestion_mode,
            "lockedAt": self.locked_at,
        }
        if self.ingestion_mode == "canvas_reference":
            if self.import_kind is None:
                raise TargetError(
                    "a canvas_reference receipt must declare its importKind at lock time")
            payload["importKind"] = self.import_kind
            # resourceId and uploadEvidence appear only once an upload is confirmed.
            if self.resource_id is not None:
                payload["resourceId"] = self.resource_id
            if self.upload_evidence is not None:
                payload["uploadEvidence"] = self.upload_evidence
        return payload


class TargetStore:
    """Lock visual targets inside an approved directory."""

    def __init__(self, *, root: Path, session_id: str,
                 approved_root: Path | None = None) -> None:
        self.root = Path(root)
        self.approved_root = Path(approved_root).expanduser() if approved_root else self.root
        self.session_id = session_id
        # Reuses the session store for identity, containment and intent-first.
        self.loop_state = LoopStateStore(root=self.root, session_id=session_id,
                                         approved_root=self.approved_root)
        self.session_dir = self.loop_state.session_dir
        self.targets_dir = self.session_dir / "targets"
        self.lock_path = self.loop_state.lock_path

    # ---- helpers -------------------------------------------------------- #
    def _assert_inside_approved(self, path: Path) -> Path:
        resolved = Path(path).expanduser().resolve()
        approved = self.approved_root.resolve()
        if resolved != approved and approved not in resolved.parents:
            raise TargetError(f"target is outside the approved directory: {path}")
        return resolved

    def _validate_mode(self, mode: str, source: str) -> None:
        if mode not in INGESTION_MODES:
            raise TargetError(f"unknown ingestion mode: {mode!r}")
        if source not in SOURCES:
            raise TargetError(f"unknown target source: {source!r}")

    def _receipt_paths(self, target_id: str) -> list[Path]:
        directory = self.targets_dir / target_id
        if not directory.is_dir():
            return []
        return sorted(directory.glob("v*.json"),
                      key=lambda p: int(p.stem[1:]))

    def _read_receipt(self, path: Path) -> TargetReceipt:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise TargetError(f"target receipt is unreadable: {path}: {exc}") from exc
        try:
            dimensions = payload["dimensions"]
            return TargetReceipt(
                target_id=payload["targetId"], version=int(payload["version"]),
                sha256=payload["sha256"], bytes=int(payload["bytes"]),
                media_type=payload["mediaType"],
                width=int(dimensions["width"]), height=int(dimensions["height"]),
                source=payload["source"], ingestion_mode=payload["ingestionMode"],
                locked_at=payload["lockedAt"], path=path,
                resource_id=payload.get("resourceId"),
                import_kind=payload.get("importKind"),
                upload_evidence=payload.get("uploadEvidence"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TargetError(f"target receipt is malformed: {path}: {exc}") from exc

    def current_receipt(self, target_id: str) -> TargetReceipt | None:
        paths = self._receipt_paths(target_id)
        return self._read_receipt(paths[-1]) if paths else None

    def _write_receipt(self, receipt: TargetReceipt) -> TargetReceipt:
        directory = self.targets_dir / receipt.target_id
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"v{receipt.version}.json"
        payload = json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2,
                             sort_keys=True)
        with _exclusive_lock(self.lock_path):
            _atomic_write(target, payload.encode("utf-8"))
        return TargetReceipt(**{**receipt.__dict__, "path": target})

    # ---- 5.1 / 5.2 locking --------------------------------------------- #
    def lock(self, path: Path, *, mode: str, source: str, relock: bool = False,
             import_kind: str = "local_upload") -> TargetReceipt:
        self._validate_mode(mode, source)
        if mode == "canvas_reference" and import_kind not in IMPORT_KINDS:
            raise TargetError(f"unknown importKind: {import_kind!r}")
        resolved = self._assert_inside_approved(path)
        if not resolved.is_file():
            raise TargetError(f"target is not a readable file: {path}")

        blob_head = resolved.open("rb").read(64)
        if not blob_head:
            raise TargetError(f"target is empty: {path}")
        try:
            media_type, width, height = probe_media(resolved.read_bytes())
        except TargetError:
            raise
        except OSError as exc:
            raise TargetError(f"target cannot be read: {path}: {exc}") from exc

        digest = _sha256_file(resolved)
        relative = resolved.relative_to(self.approved_root.resolve()).as_posix()
        target_id = str(uuid.uuid5(_TARGET_NAMESPACE,
                                   f"{self.session_id}/{relative}"))

        existing = self.current_receipt(target_id)
        if existing is not None:
            same_content = existing.sha256 == digest
            same_mode = existing.ingestion_mode == mode
            if same_content and same_mode:
                return existing  # idempotent: keep the original lock time
            if not relock:
                if not same_content:
                    raise TargetChanged(
                        f"{path} changed after it was locked "
                        f"(locked {existing.sha256[:12]}, now {digest[:12]}); "
                        "create a new target version with relock=True")
                raise TargetError(
                    f"locking the same content as {mode} would change the ingestion "
                    "mode of an existing receipt; pass relock=True to create a new version")

        version = 1 if existing is None else existing.version + 1
        receipt = TargetReceipt(
            target_id=target_id, version=version, sha256=digest,
            bytes=resolved.stat().st_size, media_type=media_type,
            width=width, height=height, source=source, ingestion_mode=mode,
            import_kind=import_kind if mode == "canvas_reference" else None,
            locked_at=_utc_now(), path=Path())
        return self._write_receipt(receipt)

    def register_canvas_reference(self, receipt: TargetReceipt, *, resource_id: str,
                                  import_kind: str,
                                  upload_evidence: str) -> TargetReceipt:
        if receipt.ingestion_mode != "canvas_reference":
            raise TargetError(
                f"{receipt.ingestion_mode} targets are never uploaded or referenced")
        if not isinstance(resource_id, str) or not _is_canonical_uuid(resource_id):
            raise TargetError(
                f"resourceId must be a canonical lowercase UUID: {resource_id!r}")
        if import_kind not in IMPORT_KINDS:
            raise TargetError(f"unknown importKind: {import_kind!r}")
        if not isinstance(upload_evidence, str) or len(upload_evidence) != 64:
            raise TargetError("uploadEvidence must be a SHA-256 hex digest")
        registered = TargetReceipt(**{**receipt.__dict__, "resource_id": resource_id,
                                     "import_kind": import_kind,
                                     "upload_evidence": upload_evidence})
        return self._write_receipt(registered)

    def generation_reference(self, receipt: TargetReceipt) -> str:
        """The only reference form a target may contribute to a generation."""
        if receipt.ingestion_mode != "canvas_reference":
            raise TargetError(
                f"{receipt.ingestion_mode} targets must never enter a generation reference")
        if not receipt.resource_id:
            raise TargetError(
                "canvas_reference target has no confirmed resourceId yet; upload first")
        return f"res:{receipt.resource_id}"


def _is_canonical_uuid(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value
    except (ValueError, AttributeError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# 5.3 / 5.4 — resource upload with one stable identity
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class UploadOutcome:
    resource_id: str
    import_kind: str
    upload_evidence: str
    reconciled: bool = False


class ResourceUploader:
    """Upload a local file through the CLI's `resource upload`, once."""

    MAX_RECONCILE_ROUNDS = 2

    def __init__(self, *, runner: Runner, store: TargetStore, project_id: str,
                 binary: str = "dreamina-canvas") -> None:
        self.runner = runner
        self.store = store
        self.project_id = project_id
        self.binary = binary

    def _argv(self, *args: str) -> list[str]:
        return [self.binary, "--format", "json", *args]

    def _upload_argv(self, *, path: Path, resource_id: str, import_kind: str) -> list[str]:
        return self._argv("resource", "upload", "--file", str(path),
                          "--project-id", self.project_id,
                          "--resource-id", resource_id,
                          "--import-kind", import_kind)

    def _get_argv(self, resource_id: str) -> list[str]:
        return self._argv("resource", "get", resource_id,
                          "--project-id", self.project_id)

    def upload(self, *, path: Path, resource_id: str, import_kind: str) -> UploadOutcome:
        if not isinstance(resource_id, str) or not _is_canonical_uuid(resource_id):
            raise TargetError(
                f"resourceId must be a canonical lowercase UUID: {resource_id!r}")
        if import_kind not in IMPORT_KINDS:
            raise TargetError(f"unknown importKind: {import_kind!r}")

        intent = self.store.loop_state
        existing = None
        if intent.intent_path(resource_id).is_file():
            existing = intent.pending_intent(kind="resource_upload", submit_id=resource_id)
            recorded = existing.get("result") or {}
            if recorded.get("resourceId"):
                return UploadOutcome(
                    resource_id=recorded["resourceId"], import_kind=import_kind,
                    upload_evidence=recorded.get("uploadEvidence", ""), reconciled=True)
            # An intent without a result means the identity is already reserved;
            # reconcile it rather than minting a second one.
            return self._reconcile(resource_id, import_kind,
                                   path=path, allow_upload=False)

        intent.record_intent(kind="resource_upload", submit_id=resource_id)
        outcome = self.runner(self._upload_argv(path=path, resource_id=resource_id,
                                                import_kind=import_kind))
        if outcome.exit_code == 0:
            return self._complete(resource_id, import_kind, outcome, reconciled=False)
        if outcome.error_code() == "cli.resource_already_exists":
            return self._reconcile(resource_id, import_kind, path=path, allow_upload=False)
        return self._reconcile(resource_id, import_kind, path=path, allow_upload=False)

    def _reconcile(self, resource_id: str, import_kind: str, *, path: Path,
                   allow_upload: bool) -> UploadOutcome:
        """Resolve an ambiguous result with the SAME id. Never mint a new one."""
        for _ in range(self.MAX_RECONCILE_ROUNDS):
            outcome = self.runner(self._get_argv(resource_id))
            if outcome.exit_code == 0 and outcome.data().get("resourceId"):
                return self._complete(resource_id, import_kind, outcome,
                                      reconciled=True)
        raise UploadUnresolved(
            f"upload {resource_id} could not be reconciled after "
            f"{self.MAX_RECONCILE_ROUNDS} queries; reconcile it manually with the same id "
            "(minting a new id would register a duplicate resource)")

    def _complete(self, resource_id: str, import_kind: str,
                  outcome: CommandOutcome, *, reconciled: bool) -> UploadOutcome:
        data = outcome.data()
        confirmed = str(data.get("resourceId") or resource_id)
        if not _is_canonical_uuid(confirmed):
            raise TargetError(
                f"CLI returned a non-canonical resourceId: {confirmed!r}")
        evidence = _sha256_bytes(json.dumps(
            {"resourceId": confirmed, "importKind": import_kind,
             "requestedId": resource_id}, sort_keys=True).encode("utf-8"))
        self.store.loop_state.complete_intent(
            kind="resource_upload", submit_id=resource_id,
            result={"resourceId": confirmed, "importKind": import_kind,
                    "uploadEvidence": evidence})
        return UploadOutcome(resource_id=confirmed, import_kind=import_kind,
                             upload_evidence=evidence, reconciled=reconciled)


# --------------------------------------------------------------------------- #
# 5.5 — capability evidence
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CapabilitySnapshot:
    schema_sha256: str
    payload: dict = field(repr=False)
    probed_at: str = field(default_factory=_utc_now)

    def reference_forms(self) -> frozenset[str]:
        forms = self.payload.get("referenceForms")
        return frozenset(str(form) for form in forms) if isinstance(forms, list) else frozenset()


class CapabilityProbe:
    """Keep the live CLI schema as the only evidence for reference support.

    `refresh()` probes once per instance: every new process is a new instance,
    which is exactly where re-validation belongs. A changed schema produces a
    different content digest and a new content-addressed snapshot, so a stale
    conclusion cannot be reused silently.
    """

    def __init__(self, *, runner: Runner, root: Path, binary: str = "dreamina-canvas") -> None:
        self.runner = runner
        self.root = Path(root)
        self.binary = binary
        self._snapshot: CapabilitySnapshot | None = None

    @property
    def capabilities_dir(self) -> Path:
        return self.root / "capabilities"

    @property
    def current_path(self) -> Path:
        return self.capabilities_dir / "current.json"

    def refresh(self, *, force: bool = False) -> CapabilitySnapshot:
        if self._snapshot is not None and not force:
            return self._snapshot
        outcome = self.runner([self.binary, "--format", "json", "schema"])
        # CommandResult (the adapter's return type) exposes exit_code, not ok().
        data = outcome.data() if outcome.exit_code == 0 else {}
        if outcome.exit_code != 0 or not data:
            raise CapabilityError(
                f"live CLI schema could not be established (exit {outcome.exit_code}, "
                f"{outcome.error_code() or 'no error code'}); refusing to guess reference support")
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
        snapshot = CapabilitySnapshot(schema_sha256=_sha256_bytes(canonical), payload=data)
        self.capabilities_dir.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.capabilities_dir / ".lock"):
            _atomic_write(self.capabilities_dir / f"{snapshot.schema_sha256}.json",
                          canonical)
            _atomic_write(self.current_path, json.dumps(
                {"schemaVersion": "visual_capability/1",
                 "schemaSha256": snapshot.schema_sha256,
                 "probedAt": snapshot.probed_at}, ensure_ascii=False,
                indent=2, sort_keys=True).encode("utf-8"))
        self._snapshot = snapshot
        return snapshot

    def current(self) -> CapabilitySnapshot:
        if self._snapshot is not None:
            return self._snapshot
        if not self.current_path.is_file():
            raise CapabilityError("no capability snapshot has been probed yet")
        reference = json.loads(self.current_path.read_text(encoding="utf-8"))
        digest = reference["schemaSha256"]
        payload_path = self.capabilities_dir / f"{digest}.json"
        if not payload_path.is_file():
            raise CapabilityError(f"capability snapshot body is missing: {digest}")
        return CapabilitySnapshot(
            schema_sha256=digest,
            payload=json.loads(payload_path.read_text(encoding="utf-8")))

    def available_reference_forms(self) -> frozenset[str]:
        return self.current().reference_forms()

    def assert_contract(self, claimed_forms: Sequence[str] | set[str]) -> None:
        """Pause when the skill contract and the live schema disagree."""
        claimed = {str(form) for form in claimed_forms}
        available = set(self.available_reference_forms())
        unevidenced = sorted(claimed - available)
        if unevidenced:
            raise ContractMismatch(
                "managed skill contract claims reference forms the live CLI schema does "
                f"not evidence: {', '.join(unevidenced)}. Update the upstream skill "
                "contract and re-release before this plugin uses them; do not guess.")
        unused = sorted(available - claimed)
        if unused:
            raise ContractMismatch(
                "live CLI schema offers reference forms the managed skill contract does "
                f"not declare: {', '.join(unused)}. Update the upstream skill contract "
                "before relying on the schema.")
