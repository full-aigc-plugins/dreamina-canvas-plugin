"""Video keyframes and temporal judging (change section 10).

Design (per `canvas-video-judge` spec):

- Static keyframe scores and temporal gates are **separate verdicts**. A video
  passes only when BOTH pass; identical-looking frames with a flicker failure
  must never grade as an overall pass (task 10.5).
- When temporal analysis is impossible (no FFmpeg, no video-capable judge), the
  verdict is `MANUAL_REVIEW_REQUIRED` — never a first-frame proxy (task 10.6).
- The sampler records evidence for every claim: source digest, duration, fps,
  sampling strategy, per-frame timestamps and digests (task 10.3).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TEMPORAL_GATES = ("flicker", "subject_drift", "motion_continuity",
                  "camera_motion", "pacing", "av_sync")

MANUAL_REVIEW = "MANUAL_REVIEW_REQUIRED"


class VideoJudgeError(Exception):
    """Video evidence cannot be produced; fail closed."""


# --------------------------------------------------------------------------- #
# 10.2 / 10.3 — the sampler port and the optional FFmpeg adapter
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class FrameSample:
    index: int
    timestamp: float
    sha256: str


@dataclass(frozen=True)
class VideoEvidence:
    source_sha256: str
    duration_seconds: float
    fps: float
    sampling_strategy: str
    frames: Sequence[FrameSample]


class FrameSamplerPort(ABC):
    """Explicit nominal port: implementations inherit this base."""

    @abstractmethod
    def sample(self, video_path: Path) -> VideoEvidence: ...


class FFmpegFrameSampler(FrameSamplerPort):
    """Optional adapter: present only when `ffmpeg` exists on the host."""

    def __init__(self, *, fps: float = 2.0, max_frames: int = 32,
                 binary: str = "ffmpeg") -> None:
        self.fps = fps
        self.max_frames = max_frames
        self.binary = binary

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def sample(self, video_path: Path) -> VideoEvidence:
        source_sha = _sha256_file(video_path)
        duration, fps = self._probe(video_path)
        workdir = Path(tempfile.mkdtemp(prefix="vloop-frames-"))
        try:
            try:
                subprocess.run(
                    [self.binary, "-loglevel", "error", "-i", str(video_path),
                     "-vf", f"fps={self.fps}", "-frames:v", str(self.max_frames),
                     "-f", "image2", str(workdir / "f%04d.png")],
                    check=True, capture_output=True, timeout=120)
            except FileNotFoundError as exc:
                raise VideoJudgeError(f"{self.binary} is unavailable") from exc
            frames = []
            for index, path in enumerate(sorted(workdir.glob("f*.png"))):
                timestamp = (index + 1) / self.fps
                frames.append(FrameSample(
                    index=index, timestamp=round(timestamp, 3),
                    sha256=_sha256_file(path)))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        return VideoEvidence(source_sha256=source_sha, duration_seconds=duration,
                             fps=fps, sampling_strategy=f"uniform@{self.fps}fps",
                             frames=frames)

    def _probe(self, video_path: Path) -> tuple[float, float]:
        ffprobe = shutil.which("ffprobe")
        if ffprobe is None:
            raise VideoJudgeError("ffprobe is unavailable; cannot sample video")
        result = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=avg_frame_rate,duration",
             "-of", "json", str(video_path)],
            capture_output=True, text=True, timeout=60, check=False)
        if result.returncode != 0:
            raise VideoJudgeError(f"ffprobe failed: {result.stderr.strip()[:200]}")
        stream = (json.loads(result.stdout).get("streams") or [{}])[0]
        duration = float(stream.get("duration") or 0.0)
        rate = str(stream.get("avg_frame_rate") or "0/1")
        num, _, den = rate.partition("/")
        fps = float(num) / float(den or 1) if den else float(num or 0)
        return duration, fps


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- #
# 10.4 — the extended request: static scores + temporal gates
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class VideoJudgeRequest:
    image_request: Mapping[str, Any]      # the content-bound image request
    evidence: VideoEvidence
    temporal_gates: Sequence[str] = field(default_factory=lambda: list(TEMPORAL_GATES))

    def to_payload(self) -> dict:
        return {
            **self.image_request,
            "video": {
                "sourceSha256": self.evidence.source_sha256,
                "durationSeconds": self.evidence.duration_seconds,
                "fps": self.evidence.fps,
                "samplingStrategy": self.evidence.sampling_strategy,
                "frames": [{"index": f.index, "timestamp": f.timestamp,
                            "sha256": f.sha256} for f in self.evidence.frames],
                "temporalGates": list(self.temporal_gates),
            },
        }


@dataclass(frozen=True)
class VideoJudgeVerdict:
    static_total: float | None
    temporal: Mapping[str, str]           # gate -> pass | fail | unknown
    overall: str                          # pass | fail | MANUAL_REVIEW_REQUIRED
    reasons: Sequence[str] = ()

    @property
    def passed(self) -> bool:
        return self.overall == "pass"


def decide_video_verdict(*, static_total: float | None,
                         temporal: Mapping[str, str],
                         min_total: float = 8.0) -> VideoJudgeVerdict:
    """Static pass is NECESSARY, never SUFFICIENT (tasks 10.5 / 10.6)."""
    reasons: list[str] = []
    if static_total is None:
        return VideoJudgeVerdict(None, temporal, MANUAL_REVIEW,
                                 ("no static score available",))
    if static_total < min_total:
        reasons.append(f"static total {static_total} below {min_total}")
    failed = [gate for gate, state in temporal.items() if state == "fail"]
    unknown = [gate for gate, state in temporal.items() if state == "unknown"]
    if not temporal:
        return VideoJudgeVerdict(static_total, temporal, MANUAL_REVIEW,
                                 ("no temporal gates were evaluated",))
    if failed:
        reasons.append("temporal gates failed: " + ", ".join(failed))
    if unknown:
        reasons.append("temporal gates unevaluated: " + ", ".join(unknown))
    overall = "pass" if not reasons else (
        MANUAL_REVIEW if unknown and not failed else "fail")
    return VideoJudgeVerdict(static_total, temporal, overall, reasons)


class TemporalGateEvaluator(ABC):
    """Explicit nominal port: implementations inherit this base."""

    @abstractmethod
    def evaluate(self, evidence: VideoEvidence) -> Mapping[str, str]: ...


class DegradedTemporalEvaluator(TemporalGateEvaluator):
    """The honest fallback: without a temporal analyzer, nothing is claimed."""

    def evaluate(self, evidence: VideoEvidence) -> Mapping[str, str]:
        return {gate: "unknown" for gate in TEMPORAL_GATES}


class StaticOnlyJudgeAdapter:
    """A judge that can score stills but not motion. Refuses to fake temporals.

    This is the guard behind task 10.6: given only a static score, it returns
    MANUAL_REVIEW rather than letting the first frame stand in for the video.
    """

    def verdict(self, *, static_total: float | None,
                evidence: VideoEvidence | None,
                temporal: Mapping[str, str] | None = None) -> VideoJudgeVerdict:
        gates = temporal if temporal is not None else (
            DegradedTemporalEvaluator().evaluate(evidence) if evidence else {})
        return decide_video_verdict(static_total=static_total, temporal=gates)
