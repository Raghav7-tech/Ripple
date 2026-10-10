from __future__ import annotations

import copy
import unittest

from ripple.models import DependencyGraph, Observation, Severity, ValidationError
from tests.support import fixture


class ModelValidationTests(unittest.TestCase):
    def test_demo_graph_loads_and_thresholds_are_deterministic(self) -> None:
        graph = DependencyGraph.from_dict(fixture("data/samples/delhi-water-demo-graph.json"))
        self.assertEqual(graph.severity_for_level(204.49), Severity.STABLE)
        self.assertEqual(graph.severity_for_level(204.5), Severity.WATCH)
        self.assertEqual(graph.severity_for_level(205.33), Severity.WARNING)
        self.assertEqual(graph.severity_for_level(206.0), Severity.CRITICAL)

    def test_graph_rejects_a_cycle(self) -> None:
        raw = fixture("data/samples/delhi-water-demo-graph.json")
        raw["edges"].append(
            {
                "edgeId": "cycle",
                "from": "hospital-north-01",
                "to": "gauge-yamuna-01",
                "delayMinutes": 1,
                "confidence": 1,
                "minSeverity": "watch",
                "evidenceStatus": "demonstration",
                "assumption": "Test-only cycle",
            }
        )
        with self.assertRaisesRegex(ValidationError, "cycle"):
            DependencyGraph.from_dict(raw)

    def test_observation_requires_timezone(self) -> None:
        raw = copy.deepcopy(fixture("data/samples/yamuna-2023-replay.json")["observations"][0])
        raw["observedAt"] = "2023-07-13T05:00:00"
        with self.assertRaisesRegex(ValidationError, "timezone"):
            Observation.from_dict(raw)

    def test_observation_rejects_non_finite_measurement(self) -> None:
        raw = copy.deepcopy(fixture("data/samples/yamuna-2023-replay.json")["observations"][0])
        raw["levelM"] = float("nan")
        with self.assertRaisesRegex(ValidationError, "finite"):
            Observation.from_dict(raw)


if __name__ == "__main__":
    unittest.main()
