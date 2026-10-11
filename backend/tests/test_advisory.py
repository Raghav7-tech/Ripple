from __future__ import annotations

import unittest

from ripple.advisory import compose_advisory, validate_generated_advisory
from ripple.bedrock_advisory import compose_bedrock_advisory
from ripple.models import ImpactResult
from ripple.replay import run_replay
from tests.support import fixture


class AdvisoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        replay = run_replay(
            fixture("data/samples/yamuna-2023-replay.json"),
            fixture("data/samples/delhi-water-demo-graph.json"),
            "run-advisory",
        )
        cls.impact = ImpactResult.from_dict(replay["latestImpacts"][0])

    def test_bilingual_templates_preserve_locked_facts(self) -> None:
        english = compose_advisory(self.impact, "en")
        hindi = compose_advisory(self.impact, "hi")
        self.assertEqual(english.locked_facts, hindi.locked_facts)
        self.assertIn("38", english.body)
        self.assertIn("38", hindi.body)
        self.assertTrue(english.to_dict()["requiresHumanApproval"])

    def test_fact_lock_rejects_changed_eta(self) -> None:
        advisory = compose_advisory(self.impact, "en")
        candidate = advisory.to_dict()
        candidate["lockedFacts"] = dict(candidate["lockedFacts"])
        candidate["lockedFacts"]["etaMinutes"] = 5
        self.assertFalse(validate_generated_advisory(candidate, advisory.locked_facts))

    def test_bedrock_adapter_accepts_locked_json(self) -> None:
        fallback = compose_advisory(self.impact, "en")

        class FakeClient:
            def converse(self, **_kwargs):
                candidate = {
                    "title": fallback.title,
                    "body": fallback.body,
                    "action": fallback.action,
                    "lockedFacts": fallback.locked_facts,
                }
                return {"output": {"message": {"content": [{"text": __import__("json").dumps(candidate)}]}}}

        advisory, reason = compose_bedrock_advisory(
            self.impact,
            "en",
            model_id="test-model",
            client=FakeClient(),
        )
        self.assertIsNone(reason)
        self.assertEqual(advisory.generator, "bedrock-converse:test-model")
        self.assertEqual(advisory.locked_facts, fallback.locked_facts)

    def test_bedrock_adapter_falls_back_when_facts_change(self) -> None:
        fallback = compose_advisory(self.impact, "en")

        class FakeClient:
            def converse(self, **_kwargs):
                candidate = {
                    "title": fallback.title,
                    "body": fallback.body.replace("38", "5"),
                    "action": fallback.action,
                    "lockedFacts": {**fallback.locked_facts, "etaMinutes": 5},
                }
                return {"output": {"message": {"content": [{"text": __import__("json").dumps(candidate)}]}}}

        advisory, reason = compose_bedrock_advisory(
            self.impact,
            "en",
            model_id="test-model",
            client=FakeClient(),
        )
        self.assertIsNotNone(reason)
        self.assertEqual(advisory.generator, "deterministic-template-v1")
        self.assertEqual(advisory.locked_facts["etaMinutes"], 38)


if __name__ == "__main__":
    unittest.main()
