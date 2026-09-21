"""Video temporal judging tests (change section 10, tasks 10.2-10.6)."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import video_judge as vj  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "tests/fixtures/judge/golden"


def tiny_mp4(path: Path, *, frames: int = 8, fps: int = 4, color: str = "0x4080c0") -> bool:
    """Real 64x64 test-source video; skipped cleanly when ffmpeg is absent."""
    if not shutil.which("ffmpeg"):
        return False
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi",
         "-i", f"color=c={color}:s=64x64:d={frames / fps}:r={fps}",
         "-frames:v", str(frames), "-y", str(path)],
        check=True, capture_output=True, timeout=60)
    return path.is_file() and path.stat().st_size > 0


def evidence(frames: int = 4) -> vj.VideoEvidence:
    samples = [vj.FrameSample(index=i, timestamp=i / 2.0, sha256=f"{i:064x}")
               for i in range(frames)]
    return vj.VideoEvidence(source_sha256="a" * 64, duration_seconds=2.0, fps=2.0,
                            sampling_strategy="uniform@2fps", frames=samples)


class SamplerTests(unittest.TestCase):
    """10.2 / 10.3 — evidence is complete or the sampler fails closed."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_ffmpeg_sampler_records_full_evidence(self) -> None:
        video = self.dir / "clip.mp4"
        if not tiny_mp4(video):
            self.skipTest("could not render a test clip")
        sampler = vj.FFmpegFrameSampler(fps=2.0)
        ev = sampler.sample(video)
        self.assertEqual(len(ev.source_sha256), 64)
        self.assertGreater(ev.duration_seconds, 0)
        self.assertGreater(ev.fps, 0)
        self.assertGreaterEqual(len(ev.frames), 2)
        self.assertTrue(all(len(f.sha256) == 64 for f in ev.frames))
        self.assertTrue(ev.frames[0].timestamp < ev.frames[-1].timestamp)

    def test_missing_ffmpeg_reports_unavailable(self) -> None:
        source = self.dir / "input.mp4"
        source.write_bytes(b"not really a video, but present")
        sampler = vj.FFmpegFrameSampler(binary="definitely-not-ffmpeg-xyz")
        self.assertFalse(sampler.available())
        with self.assertRaises(vj.VideoJudgeError):
            sampler.sample(source)


class RequestTests(unittest.TestCase):
    """10.4 — the extended request separates static and temporal dimensions."""

    def test_payload_carries_video_block(self) -> None:
        request = vj.VideoJudgeRequest(
            image_request={"schemaVersion": "judge_request/1",
                           "target": {"sha256": "a" * 64}},
            evidence=evidence())
        payload = request.to_payload()
        self.assertIn("video", payload)
        self.assertEqual(payload["video"]["temporalGates"], list(vj.TEMPORAL_GATES))
        self.assertEqual(len(payload["video"]["frames"]), 4)
        json.dumps(payload)  # serializable for any host transport


class VerdictTests(unittest.TestCase):
    """10.5 / 10.6 — static pass is necessary, never sufficient."""

    def test_all_pass_static_and_temporal_passes(self) -> None:
        verdict = vj.decide_video_verdict(
            static_total=9.0, temporal={gate: "pass" for gate in vj.TEMPORAL_GATES})
        self.assertTrue(verdict.passed)

    def test_golden_contradiction_never_passes(self) -> None:
        """The load-bearing golden rule: perfect stills + flicker = NOT a pass."""
        verdict = vj.decide_video_verdict(
            static_total=10.0, temporal={"flicker": "fail"})
        self.assertEqual(verdict.overall, "fail")
        self.assertFalse(verdict.passed)
        self.assertIn("flicker", " ".join(verdict.reasons))

    def test_unknown_temporal_gate_is_manual_review_not_pass(self) -> None:
        verdict = vj.decide_video_verdict(
            static_total=9.5,
            temporal={gate: "unknown" for gate in vj.TEMPORAL_GATES})
        self.assertEqual(verdict.overall, vj.MANUAL_REVIEW)

    def test_no_temporal_evaluation_at_all_is_manual_review(self) -> None:
        verdict = vj.decide_video_verdict(static_total=9.5, temporal={})
        self.assertEqual(verdict.overall, vj.MANUAL_REVIEW)

    def test_missing_static_score_is_manual_review(self) -> None:
        verdict = vj.decide_video_verdict(
            static_total=None,
            temporal={gate: "pass" for gate in vj.TEMPORAL_GATES})
        self.assertEqual(verdict.overall, vj.MANUAL_REVIEW)

    def test_low_static_score_fails_even_with_clean_motion(self) -> None:
        verdict = vj.decide_video_verdict(
            static_total=5.0, temporal={gate: "pass" for gate in vj.TEMPORAL_GATES})
        self.assertEqual(verdict.overall, "fail")


class DegradationTests(unittest.TestCase):
    """10.6 — the static-only judge never substitutes for the video."""

    def test_degraded_evaluator_claims_unknown_not_pass(self) -> None:
        result = vj.DegradedTemporalEvaluator().evaluate(evidence())
        self.assertEqual(set(result.values()), {"unknown"})

    def test_static_only_adapter_returns_manual_review(self) -> None:
        adapter = vj.StaticOnlyJudgeAdapter()
        verdict = adapter.verdict(static_total=9.5, evidence=evidence())
        self.assertEqual(verdict.overall, vj.MANUAL_REVIEW)
        self.assertFalse(verdict.passed)

    def test_static_only_adapter_without_any_evidence_is_manual_review(self) -> None:
        verdict = vj.StaticOnlyJudgeAdapter().verdict(static_total=9.0, evidence=None)
        self.assertEqual(verdict.overall, vj.MANUAL_REVIEW)

    def test_explicit_temporal_results_are_honoured(self) -> None:
        adapter = vj.StaticOnlyJudgeAdapter()
        gates = {gate: "pass" for gate in vj.TEMPORAL_GATES}
        verdict = adapter.verdict(static_total=9.5, evidence=evidence(), temporal=gates)
        self.assertTrue(verdict.passed)


class VideoGoldenTests(unittest.TestCase):
    """10.5 — expectations file carries the contradiction rule."""

    def test_golden_expectations_encode_the_contradiction(self) -> None:
        path = GOLDEN / "video-expectations.json"
        self.assertTrue(path.is_file(), "video golden expectations missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        sample = next(s for s in data["samples"] if s["id"] == "static-pass-temporal-fail")
        self.assertEqual(sample["staticTotal"], 10.0)
        self.assertIn("fail", sample["temporal"].values())
        self.assertEqual(sample["expectedOverall"], "fail")
        self.assertEqual(data["constraints"]["noRealAccounts"], True)


if __name__ == "__main__":
    unittest.main()
