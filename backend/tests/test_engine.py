from __future__ import annotations

import unittest

from ripple.engine import CascadeEngine
from ripple.models import DependencyGraph, Observation, Severity
from ripple.replay import run_replay
from tests.support import fixture


class CascadeEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph_data = fixture("data/samples/delhi-water-demo-graph.json")
        cls.replay_data = fixture("data/samples/yamuna-2023-replay.json")
        cls.graph = DependencyGraph.from_dict(cls.graph_data)
        cls.engine = CascadeEngine(cls.graph)

    def test_stable_observation_has_no_impacts(self) -> None:
        observation = Observation.from_dict(self.replay_data["observations"][0])
        self.assertEqual(self.engine.calculate(observation, "run-stable"), [])

    def test_warning_excludes_critical_only_shelter_edge(self) -> None:
        observation = Observation.from_dict(self.replay_data["observations"][2])
        impacts = self.engine.calculate(observation, "run-warning")
        self.assertEqual([impact.target_node_id for impact in impacts], ["hospital-north-01", "clinic-civil-lines-01"])

    def test_critical_replay_matches_explainable_regression(self) -> None:
        result = run_replay(self.replay_data, self.graph_data, "run-regression")
        impacts = result["latestImpacts"]
        self.assertEqual([item["etaMinutes"] for item in impacts], [38, 72, 125])
        self.assertEqual([item["confidence"] for item in impacts], [0.84, 0.78, 0.76])
        self.assertEqual([item["severity"] for item in impacts], ["critical", "warning", "watch"])
        self.assertEqual(len(impacts[0]["path"]), 3)
        self.assertTrue(impacts[0]["assumptions"])
        self.assertEqual(result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
