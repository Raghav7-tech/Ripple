from __future__ import annotations

import unittest

from ripple.advisory import compose_advisory, validate_generated_advisory
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


if __name__ == "__main__":
    unittest.main()
