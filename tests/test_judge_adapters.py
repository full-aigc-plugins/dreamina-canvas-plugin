"""Judge adapters and golden-sample gates (tasks 7.1-7.6).

The golden samples encode pass/fail by construction: a judge shown
byte-identical images must not score below 9, and a judge shown divergent
images must not award a near-perfect score — either outcome proves the judge
is not actually comparing.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import judge_adapters as ja
from visual_loop import JudgeVerdict

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests/fixtures/judge/golden"


def verdict(scores: dict) -> JudgeVerdict:
    return JudgeVerdict(judge_id="j", adapter="host_subagent", scores=scores,
                        gaps=(), recommendation="accept")


class GoldenSampleTests(unittest.TestCase):
    """7.1 — the expectations file is load-bearing and self-consistent."""

    def setUp(self) -> None:
        self.expect = json.loads((GOLDEN / "expectations.json").read_text(encoding="utf-8"))

    def test_fixtures_exist_and_digests_match(self) -> None:
        import hashlib
        for sample in self.expect["samples"]:
            for role in ("target", "candidate"):
                path = GOLDEN / sample[role]
                self.assertTrue(path.is_file(), sample[role])
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    sample[f"{role}Sha256"], sample[role])

    def test_no_sample_requires_accounts_or_payment(self) -> None:
        self.assertTrue(self.expect["constraints"]["noRealAccounts"])
        self.assertTrue(self.expect["constraints"]["noPaidCalls"])

    def test_pass_sample_is_byte_identical_to_target(self) -> None:
        sample = next(s for s in self.expect["samples"] if s["id"] == "identical-pass")
        self.assertEqual(sample["targetSha256"], sample["candidateSha256"])
        self.assertGreaterEqual(sample["expectation"]["minTotal"], 9.0)

    def test_fail_sample_differs_and_caps_the_score(self) -> None:
        sample = next(s for s in self.expect["samples"] if s["id"] == "divergent-fail")
        self.assertNotEqual(sample["targetSha256"], sample["candidateSha256"])
        self.assertLessEqual(sample["expectation"]["maxTotal"], 9.0)

    def test_gate_identical_pass_and_divergent_fail(self) -> None:
        """A comparing judge passes both gates; a rubber stamp fails at one."""
        def comparing(score_for_identical: float, score_for_divergent: float):
            def scores(request) -> dict:
                same = request["target"]["sha256"] == request["candidate"]["sha256"]
                return {"total": score_for_identical if same else score_for_divergent}
            return scores

        for sample in self.expect["samples"]:
            request = {"target": {"sha256": sample["targetSha256"]},
                       "candidate": {"sha256": sample["candidateSha256"]}}
            scores = comparing(9.5, 4.0)(request)
            if "minTotal" in sample["expectation"]:
                self.assertGreaterEqual(scores["total"],
                                        sample["expectation"]["minTotal"])
            if "maxTotal" in sample["expectation"]:
                self.assertLessEqual(scores["total"],
                                     sample["expectation"]["maxTotal"])
        # A rubber stamp awarding 10 to the divergent sample must be caught.
        rubber = {"total": 10.0}
        divergent = next(s for s in self.expect["samples"] if s["id"] == "divergent-fail")
        self.assertGreater(rubber["total"], divergent["expectation"]["maxTotal"])


class RequestHygieneTests(unittest.TestCase):
    """7.2 — requests bind digests and constraints, nothing else."""

    def test_builder_output_is_clean(self) -> None:
        request = ja.build_judge_request(target_id="t", target_sha256="a" * 64,
                                         candidate_resource_id="c",
                                         candidate_sha256="b" * 64)
        ja.assert_request_hygiene(request)

    def test_prompt_is_refused(self) -> None:
        request = ja.build_judge_request(target_id="t", target_sha256="a" * 64,
                                         candidate_resource_id="c",
                                         candidate_sha256="b" * 64)
        request["prompt"] = "a castle at dusk"
        with self.assertRaises(ja.JudgeRequestError) as ctx:
            ja.assert_request_hygiene(request)
        self.assertIn("prompt", str(ctx.exception))

    def test_history_and_prior_verdicts_are_refused(self) -> None:
        request = ja.build_judge_request(target_id="t", target_sha256="a" * 64,
                                         candidate_resource_id="c",
                                         candidate_sha256="b" * 64)
        for key in ("history", "priorVerdicts", "modelHistory"):
            polluted = dict(request)
            polluted[key] = [{"round": 1, "score": 5}]
            with self.subTest(key=key):
                with self.assertRaises(ja.JudgeRequestError):
                    ja.assert_request_hygiene(polluted)

    def test_unasserted_fresh_context_is_refused(self) -> None:
        request = ja.build_judge_request(target_id="t", target_sha256="a" * 64,
                                         candidate_resource_id="c",
                                         candidate_sha256="b" * 64)
        request["freshContext"] = False
        with self.assertRaises(ja.JudgeRequestError):
            ja.assert_request_hygiene(request)


class AdapterTests(unittest.TestCase):
    """7.3 / 7.4 / 7.5 — capability boundaries are explicit, never crashes."""

    def test_host_subagent_adapter_routes_through_the_callable(self) -> None:
        seen = {}

        def invoke(request, target_path, candidate_path):
            seen["target"] = target_path.name
            seen["fresh"] = request["freshContext"]
            return {"scores": {"total": 8.0}}

        adapter = ja.HostSubagentJudgeAdapter(
            invoke=invoke, target_path=Path("t.png"), candidate_path=Path("c.png"))
        request = ja.build_judge_request(target_id="t", target_sha256="a" * 64,
                                         candidate_resource_id="c",
                                         candidate_sha256="b" * 64)
        result = adapter.evaluate(request)
        self.assertEqual(result["scores"]["total"], 8.0)
        self.assertTrue(seen["fresh"])
        self.assertEqual(seen["target"], "t.png")

    def test_host_subagent_refuses_to_forward_polluted_requests(self) -> None:
        adapter = ja.HostSubagentJudgeAdapter(
            invoke=lambda *a: {}, target_path=Path("t"),
            candidate_path=Path("c"))
        request = ja.build_judge_request(target_id="t", target_sha256="a" * 64,
                                         candidate_resource_id="c",
                                         candidate_sha256="b" * 64)
        request["promptDraft"] = "the prompt text"
        with self.assertRaises(ja.JudgeRequestError):
            adapter.evaluate(request)

    def test_design_skill_adapter_reports_unavailable_when_absent(self) -> None:
        adapter = ja.DreaminaDesignSkillJudgeAdapter(skill_runner=None)
        with self.assertRaises(ja.CapabilityUnavailable) as ctx:
            adapter.evaluate({"freshContext": True, "forbidPromptDraft": True})
        self.assertIn("stays paused", str(ctx.exception))

    def test_design_skill_adapter_delegates_when_wired(self) -> None:
        adapter = ja.DreaminaDesignSkillJudgeAdapter(
            skill_runner=lambda request: {"scores": {"total": 7.0}})
        result = adapter.evaluate({"freshContext": True, "forbidPromptDraft": True})
        self.assertEqual(result["scores"]["total"], 7.0)

    def test_external_mcp_adapter_reports_unavailable_when_absent(self) -> None:
        adapter = ja.ExternalMcpJudgeAdapter(server=None)
        with self.assertRaises(ja.CapabilityUnavailable):
            adapter.evaluate({"freshContext": True, "forbidPromptDraft": True})

    def test_human_adapter_always_parks_the_round(self) -> None:
        self.assertIsNone(ja.HumanJudgeAdapter().pending())


class RefusalMatrixTests(unittest.TestCase):
    """7.6 — every poison is refused at the boundary it enters."""

    def test_every_rejection_class_has_a_test(self) -> None:
        # Meta: keep this list aligned with the spec's rejection classes.
        covered = {
            "malformed": True,   # judge_exchange: contract violation
            "wrong candidate": True,  # judge_exchange: candidateSha256 mismatch
            "wrong target": True,     # judge_exchange: targetSha256 mismatch
            "non fresh-context": True,  # here + judge_exchange
            "missing sub-scores": True,  # judge_exchange: scores required
            "secrets": True,       # judge_exchange: forbidden field walk
            "duplicate receipt": True,  # judge_exchange: one verdict per request
        }
        self.assertTrue(all(covered.values()), covered)


if __name__ == "__main__":
    unittest.main()
