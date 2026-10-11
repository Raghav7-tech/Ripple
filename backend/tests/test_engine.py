from __future__ import annotations

import copy
from datetime import datetime
import unittest

from ripple.engine import CascadeEngine
from ripple.models import (
    DependencyGraph,
    Edge,
    EvidenceStatus,
    ImpactResult,
    Node,
    Observation,
    PathStep,
    ResourceType,
    Severity,
    ValidationError,
)
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

    def test_multi_resource_fixture_returns_exact_three_hospital_impacts(self) -> None:
        multi_graph_data = fixture("data/samples/multi-resource-demo-graph.json")
        multi_trigger_data = fixture("data/samples/multi-resource-trigger.json")
        graph = DependencyGraph.from_dict(multi_graph_data)
        observation = Observation.from_dict(multi_trigger_data)
        engine = CascadeEngine(graph)

        impacts = engine.calculate(observation, "run-multi-resource")
        self.assertEqual(len(impacts), 3)

        # Deterministic order by (etaMinutes, target_node_id, resourceType)
        # staff: 30 min, water: 38 min, medical_supply: 50 min
        self.assertEqual([imp.resource_type.value for imp in impacts], ["staff", "water", "medical_supply"])
        self.assertEqual([imp.eta_minutes for imp in impacts], [30, 38, 50])
        self.assertEqual(
            [imp.target_node_id for imp in impacts],
            ["hospital-demo-01", "hospital-demo-01", "hospital-demo-01"],
        )
        self.assertEqual(
            [imp.expected_impact_at.isoformat() for imp in impacts],
            [
                "2026-10-11T10:30:00+05:30",
                "2026-10-11T10:38:00+05:30",
                "2026-10-11T10:50:00+05:30",
            ],
        )
        self.assertEqual([imp.confidence for imp in impacts], [1.0, 1.0, 1.0])
        self.assertEqual([imp.severity.value for imp in impacts], ["critical", "critical", "critical"])

        # Check path steps match resource type
        for impact in impacts:
            self.assertEqual(len(impact.path), 3)
            for step in impact.path:
                self.assertEqual(step.resource_type, impact.resource_type)

        # Distinct impact IDs
        impact_ids = [imp.impact_id for imp in impacts]
        self.assertEqual(len(set(impact_ids)), 3)

    def test_water_cannot_cross_onto_staff_or_medical_supply_mid_path(self) -> None:
        graph_dict = {
            "schemaVersion": "1.0",
            "graphVersion": "test-cross-isolation-v1",
            "createdAt": "2026-10-11T10:00:00+05:30",
            "thresholdsM": {"watch": 204.5, "warning": 205.33, "critical": 206.0},
            "nodes": [
                {
                    "nodeId": "gauge-01",
                    "name": "Gauge",
                    "type": "gauge",
                    "notify": False,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
                {
                    "nodeId": "node-mid-1",
                    "name": "Mid 1",
                    "type": "substation",
                    "notify": False,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
                {
                    "nodeId": "hospital-01",
                    "name": "Hospital",
                    "type": "hospital",
                    "notify": True,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
            ],
            "edges": [
                # Water from gauge to mid-1
                {
                    "edgeId": "e-1",
                    "from": "gauge-01",
                    "to": "node-mid-1",
                    "delayMinutes": 10,
                    "confidence": 1.0,
                    "minSeverity": "warning",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test edge",
                    "resourceType": "water",
                },
                # Staff from mid-1 to hospital (cross-resource!)
                {
                    "edgeId": "e-2",
                    "from": "node-mid-1",
                    "to": "hospital-01",
                    "delayMinutes": 10,
                    "confidence": 1.0,
                    "minSeverity": "warning",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test edge",
                    "resourceType": "staff",
                },
            ],
        }
        graph = DependencyGraph.from_dict(graph_dict)
        obs_dict = {
            "schemaVersion": "1.0",
            "observationId": "obs-01",
            "eventId": "event-01",
            "sourceNodeId": "gauge-01",
            "observedAt": "2026-10-11T10:00:00+05:30",
            "receivedAt": "2026-10-11T10:01:00+05:30",
            "levelM": 206.5,
            "confidence": 1.0,
            "mode": "replay",
            "sourceId": "test-source",
        }
        observation = Observation.from_dict(obs_dict)
        engine = CascadeEngine(graph)

        # Hospital should not be reachable because lane started as water and cannot traverse staff edge
        impacts = engine.calculate(observation, "run-isolation")
        self.assertEqual(impacts, [])

        # Now test staff attempting to cross to medical_supply
        graph_dict["edges"] = [
            {
                "edgeId": "e-s1",
                "from": "gauge-01",
                "to": "node-mid-1",
                "delayMinutes": 10,
                "confidence": 1.0,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Test edge",
                "resourceType": "staff",
            },
            {
                "edgeId": "e-m2",
                "from": "node-mid-1",
                "to": "hospital-01",
                "delayMinutes": 10,
                "confidence": 1.0,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Test edge",
                "resourceType": "medical_supply",
            },
        ]
        graph2 = DependencyGraph.from_dict(graph_dict)
        impacts2 = CascadeEngine(graph2).calculate(observation, "run-isolation-2")
        self.assertEqual(impacts2, [])

    def test_notify_false_traversed_but_not_emitted_as_targets(self) -> None:
        multi_graph_data = fixture("data/samples/multi-resource-demo-graph.json")
        multi_trigger_data = fixture("data/samples/multi-resource-trigger.json")
        graph = DependencyGraph.from_dict(multi_graph_data)
        observation = Observation.from_dict(multi_trigger_data)
        engine = CascadeEngine(graph)

        impacts = engine.calculate(observation, "run-notify-check")
        target_ids = [imp.target_node_id for imp in impacts]
        # Only hospital has notify: True
        self.assertEqual(set(target_ids), {"hospital-demo-01"})

        # Verify intermediate notify: False nodes were indeed traversed
        all_path_nodes = {
            step.target for imp in impacts for step in imp.path[:-1]
        } | {step.source for imp in impacts for step in imp.path[1:]}
        self.assertTrue(
            {"wtp-demo-01", "zone-demo-01", "corridor-demo-01", "staff-pool-demo-01", "supply-route-demo-01", "medical-depot-demo-01"}.issubset(
                all_path_nodes
            )
        )

    def test_earliest_route_and_tie_break_rules(self) -> None:
        base_graph_dict = {
            "schemaVersion": "1.0",
            "graphVersion": "test-tie-break-v1",
            "createdAt": "2026-10-11T10:00:00+05:30",
            "thresholdsM": {"watch": 204.5, "warning": 205.33, "critical": 206.0},
            "nodes": [
                {
                    "nodeId": "gauge-01",
                    "name": "Gauge",
                    "type": "gauge",
                    "notify": False,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
                {
                    "nodeId": "hospital-01",
                    "name": "Hospital",
                    "type": "hospital",
                    "notify": True,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
            ],
            "edges": [],
        }
        obs = Observation.from_dict(
            {
                "schemaVersion": "1.0",
                "observationId": "obs-01",
                "eventId": "event-01",
                "sourceNodeId": "gauge-01",
                "observedAt": "2026-10-11T10:00:00+05:30",
                "receivedAt": "2026-10-11T10:01:00+05:30",
                "levelM": 206.5,
                "confidence": 1.0,
                "mode": "replay",
                "sourceId": "test-source",
            }
        )

        # 1. Lower-ETA path wins even if another path has higher confidence
        g1 = copy.deepcopy(base_graph_dict)
        g1["edges"] = [
            {
                "edgeId": "e-fast-lowconf",
                "from": "gauge-01",
                "to": "hospital-01",
                "delayMinutes": 10,
                "confidence": 0.5,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Fast route",
                "resourceType": "water",
            },
            {
                "edgeId": "e-slow-highconf",
                "from": "gauge-01",
                "to": "hospital-01",
                "delayMinutes": 25,
                "confidence": 0.99,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Slow route",
                "resourceType": "water",
            },
        ]
        impacts1 = CascadeEngine(DependencyGraph.from_dict(g1)).calculate(obs, "run-1")
        self.assertEqual(len(impacts1), 1)
        self.assertEqual(impacts1[0].eta_minutes, 10)
        self.assertEqual(impacts1[0].confidence, 0.5)
        self.assertEqual(impacts1[0].path[0].edge_id, "e-fast-lowconf")

        # 2. Equal ETA: higher confidence wins
        g2 = copy.deepcopy(base_graph_dict)
        g2["edges"] = [
            {
                "edgeId": "e-equal-lowconf",
                "from": "gauge-01",
                "to": "hospital-01",
                "delayMinutes": 15,
                "confidence": 0.65,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Route A",
                "resourceType": "water",
            },
            {
                "edgeId": "e-equal-highconf",
                "from": "gauge-01",
                "to": "hospital-01",
                "delayMinutes": 15,
                "confidence": 0.95,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Route B",
                "resourceType": "water",
            },
        ]
        impacts2 = CascadeEngine(DependencyGraph.from_dict(g2)).calculate(obs, "run-2")
        self.assertEqual(len(impacts2), 1)
        self.assertEqual(impacts2[0].eta_minutes, 15)
        self.assertEqual(impacts2[0].confidence, 0.95)
        self.assertEqual(impacts2[0].path[0].edge_id, "e-equal-highconf")

        # 3. Equal ETA and equal confidence: lexicographically smallest sequence of edge IDs wins
        g3 = copy.deepcopy(base_graph_dict)
        g3["edges"] = [
            {
                "edgeId": "e-route-z",
                "from": "gauge-01",
                "to": "hospital-01",
                "delayMinutes": 20,
                "confidence": 0.9,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Route Z",
                "resourceType": "water",
            },
            {
                "edgeId": "e-route-a",
                "from": "gauge-01",
                "to": "hospital-01",
                "delayMinutes": 20,
                "confidence": 0.9,
                "minSeverity": "warning",
                "evidenceStatus": "demonstration",
                "assumption": "Route A",
                "resourceType": "water",
            },
        ]
        impacts3 = CascadeEngine(DependencyGraph.from_dict(g3)).calculate(obs, "run-3")
        self.assertEqual(len(impacts3), 1)
        self.assertEqual(impacts3[0].eta_minutes, 20)
        self.assertEqual(impacts3[0].confidence, 0.9)
        self.assertEqual(impacts3[0].path[0].edge_id, "e-route-a")

        # 4. Reordering edges array does not change chosen path or serialized result
        g3_rev = copy.deepcopy(g3)
        g3_rev["edges"] = list(reversed(g3["edges"]))
        impacts3_rev = CascadeEngine(DependencyGraph.from_dict(g3_rev)).calculate(obs, "run-3")
        self.assertEqual(impacts3[0].to_dict(), impacts3_rev[0].to_dict())

    def test_confidence_multiplication_includes_observation_and_path_edges(self) -> None:
        graph_dict = {
            "schemaVersion": "1.0",
            "graphVersion": "test-conf-mult-v1",
            "createdAt": "2026-10-11T10:00:00+05:30",
            "thresholdsM": {"watch": 204.5, "warning": 205.33, "critical": 206.0},
            "nodes": [
                {
                    "nodeId": "gauge-01",
                    "name": "Gauge",
                    "type": "gauge",
                    "notify": False,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
                {
                    "nodeId": "zone-01",
                    "name": "Zone",
                    "type": "supply-zone",
                    "notify": False,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
                {
                    "nodeId": "hospital-01",
                    "name": "Hospital",
                    "type": "hospital",
                    "notify": True,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Test node",
                },
            ],
            "edges": [
                {
                    "edgeId": "e-1",
                    "from": "gauge-01",
                    "to": "zone-01",
                    "delayMinutes": 10,
                    "confidence": 0.9,
                    "minSeverity": "warning",
                    "evidenceStatus": "demonstration",
                    "assumption": "Edge 1",
                    "resourceType": "water",
                },
                {
                    "edgeId": "e-2",
                    "from": "zone-01",
                    "to": "hospital-01",
                    "delayMinutes": 10,
                    "confidence": 0.5,
                    "minSeverity": "warning",
                    "evidenceStatus": "demonstration",
                    "assumption": "Edge 2",
                    "resourceType": "water",
                },
            ],
        }
        obs = Observation.from_dict(
            {
                "schemaVersion": "1.0",
                "observationId": "obs-01",
                "eventId": "event-01",
                "sourceNodeId": "gauge-01",
                "observedAt": "2026-10-11T10:00:00+05:30",
                "receivedAt": "2026-10-11T10:01:00+05:30",
                "levelM": 206.5,
                "confidence": 0.8,
                "mode": "replay",
                "sourceId": "test-source",
            }
        )
        impacts = CascadeEngine(DependencyGraph.from_dict(graph_dict)).calculate(obs, "run-conf")
        self.assertEqual(len(impacts), 1)
        # 0.8 * 0.9 * 0.5 = 0.36
        self.assertEqual(impacts[0].confidence, 0.36)

    def test_resource_specific_impact_ids_are_deterministic_and_distinct(self) -> None:
        multi_graph_data = fixture("data/samples/multi-resource-demo-graph.json")
        multi_trigger_data = fixture("data/samples/multi-resource-trigger.json")
        graph = DependencyGraph.from_dict(multi_graph_data)
        obs = Observation.from_dict(multi_trigger_data)
        engine = CascadeEngine(graph)

        impacts_a = engine.calculate(obs, "run-id-test")
        impacts_b = engine.calculate(obs, "run-id-test")

        # Stable across identical runs
        self.assertEqual(
            [imp.impact_id for imp in impacts_a],
            [imp.impact_id for imp in impacts_b],
        )

        # Distinct for each resource type in the same run
        ids = [imp.impact_id for imp in impacts_a]
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)

    def test_serialized_output_schema_valid_and_contains_resource_type(self) -> None:
        multi_graph_data = fixture("data/samples/multi-resource-demo-graph.json")
        multi_trigger_data = fixture("data/samples/multi-resource-trigger.json")
        graph = DependencyGraph.from_dict(multi_graph_data)
        obs = Observation.from_dict(multi_trigger_data)
        impacts = CascadeEngine(graph).calculate(obs, "run-serialize")

        for impact in impacts:
            serialized = impact.to_dict()
            self.assertEqual(serialized["schemaVersion"], "1.0")
            self.assertIn("resourceType", serialized)
            self.assertEqual(serialized["resourceType"], impact.resource_type.value)
            self.assertTrue(serialized["resourceType"] in {"water", "staff", "medical_supply"})

            for step in serialized["path"]:
                self.assertIn("resourceType", step)
                self.assertEqual(step["resourceType"], impact.resource_type.value)

            # Re-parsing succeeds and preserves fields
            parsed = ImpactResult.from_dict(serialized)
            self.assertEqual(parsed.impact_id, impact.impact_id)
            self.assertEqual(parsed.resource_type, impact.resource_type)

    def test_repeated_runs_stability(self) -> None:
        multi_graph_data = fixture("data/samples/multi-resource-demo-graph.json")
        multi_trigger_data = fixture("data/samples/multi-resource-trigger.json")
        graph = DependencyGraph.from_dict(multi_graph_data)
        obs = Observation.from_dict(multi_trigger_data)
        engine = CascadeEngine(graph)

        baseline = [imp.to_dict() for imp in engine.calculate(obs, "run-repeat")]
        for _ in range(10):
            repeated = [imp.to_dict() for imp in engine.calculate(obs, "run-repeat")]
            self.assertEqual(baseline, repeated)

    def test_observation_source_node_not_in_graph_raises_validation_error(self) -> None:
        obs_bad = Observation.from_dict(
            {
                "schemaVersion": "1.0",
                "observationId": "obs-bad",
                "eventId": "event-01",
                "sourceNodeId": "nonexistent-gauge",
                "observedAt": "2026-10-11T10:00:00+05:30",
                "receivedAt": "2026-10-11T10:01:00+05:30",
                "levelM": 206.5,
                "confidence": 1.0,
                "mode": "replay",
                "sourceId": "test-source",
            }
        )
        with self.assertRaisesRegex(ValidationError, "observation sourceNodeId"):
            self.engine.calculate(obs_bad, "run-bad-source")


if __name__ == "__main__":
    unittest.main()

