from __future__ import annotations

import copy
import unittest

from ripple.models import (
    DependencyGraph,
    ImpactResult,
    Observation,
    PathStep,
    ResourceType,
    Severity,
    ValidationError,
)
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
                "resourceType": "water",
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

    def test_legacy_graph_without_resource_type_loads_as_water(self) -> None:
        raw = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        for edge in raw["edges"]:
            edge.pop("resourceType", None)
        graph = DependencyGraph.from_dict(raw)
        for edge in graph.edges:
            self.assertEqual(edge.resource_type, ResourceType.WATER)

    def test_legacy_impact_and_path_step_without_resource_type_parse_as_water(self) -> None:
        legacy_impact = {
            "schemaVersion": "1.0",
            "impactId": "impact-legacy-01",
            "runId": "run-legacy",
            "target": {"nodeId": "hospital-01", "name": "Legacy Hospital"},
            "expectedImpactAt": "2026-10-11T10:30:00+05:30",
            "etaMinutes": 30,
            "severity": "critical",
            "confidence": 0.95,
            "path": [
                {
                    "edgeId": "e-leg-01",
                    "from": "gauge-01",
                    "to": "hospital-01",
                    "delayMinutes": 30,
                    "confidence": 0.95,
                    "evidenceStatus": "demonstration",
                    "assumption": "Legacy path step",
                }
            ],
            "assumptions": ["Legacy assumption"],
            "actionCode": "VERIFY_RESERVE",
        }
        step = PathStep.from_dict(legacy_impact["path"][0])
        self.assertEqual(step.resource_type, ResourceType.WATER)

        impact = ImpactResult.from_dict(legacy_impact)
        self.assertEqual(impact.resource_type, ResourceType.WATER)
        self.assertEqual(impact.path[0].resource_type, ResourceType.WATER)

    def test_invalid_resource_type_raises_validation_error(self) -> None:
        raw = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw["edges"][0]["resourceType"] = "workforce"
        with self.assertRaisesRegex(ValidationError, "resourceType"):
            DependencyGraph.from_dict(raw)

        raw["edges"][0]["resourceType"] = "medical"
        with self.assertRaisesRegex(ValidationError, "resourceType"):
            DependencyGraph.from_dict(raw)

        raw["edges"][0]["resourceType"] = 12345
        with self.assertRaisesRegex(ValidationError, "resourceType"):
            DependencyGraph.from_dict(raw)

        # Invalid in PathStep
        with self.assertRaisesRegex(ValidationError, "resourceType"):
            PathStep.from_dict(
                {
                    "edgeId": "e-bad",
                    "from": "a",
                    "to": "b",
                    "delayMinutes": 10,
                    "confidence": 1.0,
                    "evidenceStatus": "demonstration",
                    "resourceType": "invalid_res",
                }
            )

        # Invalid in ImpactResult
        with self.assertRaisesRegex(ValidationError, "resourceType"):
            ImpactResult.from_dict(
                {
                    "schemaVersion": "1.0",
                    "impactId": "impact-bad",
                    "runId": "run-bad",
                    "target": {"nodeId": "h-01", "name": "H"},
                    "expectedImpactAt": "2026-10-11T10:30:00+05:30",
                    "etaMinutes": 30,
                    "severity": "critical",
                    "confidence": 0.9,
                    "path": [
                        {
                            "edgeId": "e-ok",
                            "from": "a",
                            "to": "b",
                            "delayMinutes": 10,
                            "confidence": 1.0,
                            "evidenceStatus": "demonstration",
                        }
                    ],
                    "assumptions": [],
                    "actionCode": "VERIFY",
                    "resourceType": "bad_type",
                }
            )

    def test_graph_validation_invariants(self) -> None:
        # 1. Duplicate node IDs
        raw_dup_node = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw_dup_node["nodes"].append(copy.deepcopy(raw_dup_node["nodes"][0]))
        with self.assertRaisesRegex(ValidationError, "unique"):
            DependencyGraph.from_dict(raw_dup_node)

        # 2. Duplicate edge IDs
        raw_dup_edge = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw_dup_edge["edges"].append(copy.deepcopy(raw_dup_edge["edges"][0]))
        with self.assertRaisesRegex(ValidationError, "unique"):
            DependencyGraph.from_dict(raw_dup_edge)

        # 3. Missing endpoint
        raw_missing = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw_missing["edges"][0]["to"] = "non-existent-node"
        with self.assertRaisesRegex(ValidationError, "missing node"):
            DependencyGraph.from_dict(raw_missing)

        # 4. Self-loop
        raw_loop = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw_loop["edges"][0]["to"] = raw_loop["edges"][0]["from"]
        with self.assertRaisesRegex(ValidationError, "self-loop"):
            DependencyGraph.from_dict(raw_loop)

        # 5. Invalid delay minutes
        raw_delay = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw_delay["edges"][0]["delayMinutes"] = -5
        with self.assertRaisesRegex(ValidationError, "delayMinutes"):
            DependencyGraph.from_dict(raw_delay)

        raw_delay["edges"][0]["delayMinutes"] = 20000
        with self.assertRaisesRegex(ValidationError, "delayMinutes"):
            DependencyGraph.from_dict(raw_delay)

        # 6. Invalid confidence
        raw_conf = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw_conf["edges"][0]["confidence"] = 1.5
        with self.assertRaisesRegex(ValidationError, "confidence"):
            DependencyGraph.from_dict(raw_conf)

        # 7. Non-increasing thresholds
        raw_thresh = copy.deepcopy(fixture("data/samples/delhi-water-demo-graph.json"))
        raw_thresh["thresholdsM"] = {"watch": 205.0, "warning": 204.0, "critical": 206.0}
        with self.assertRaisesRegex(ValidationError, "thresholds"):
            DependencyGraph.from_dict(raw_thresh)

        # 8. Observation receivedAt < observedAt
        raw_obs = copy.deepcopy(fixture("data/samples/yamuna-2023-replay.json")["observations"][0])
        raw_obs["receivedAt"] = "2023-07-13T04:59:00+05:30"
        with self.assertRaisesRegex(ValidationError, "earlier than observedAt"):
            Observation.from_dict(raw_obs)


if __name__ == "__main__":
    unittest.main()

