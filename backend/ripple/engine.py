from __future__ import annotations

import hashlib
import heapq
from dataclasses import dataclass
from datetime import timedelta

from .models import DependencyGraph, Edge, ImpactResult, Observation, PathStep, Severity, ValidationError


@dataclass(frozen=True)
class _Route:
    arrival_minutes: int
    confidence: float
    path: tuple[Edge, ...]


class CascadeEngine:
    """Deterministic earliest-impact traversal over a validated dependency DAG."""

    def __init__(self, graph: DependencyGraph):
        self.graph = graph
        self._adjacency: dict[str, list[Edge]] = {node_id: [] for node_id in graph.nodes}
        for edge in graph.edges:
            self._adjacency[edge.source].append(edge)
        for edges in self._adjacency.values():
            edges.sort(key=lambda edge: (edge.delay_minutes, edge.edge_id))

    def calculate(self, observation: Observation, run_id: str) -> list[ImpactResult]:
        if observation.source_node_id not in self.graph.nodes:
            raise ValidationError("observation sourceNodeId does not exist in the selected graph")
        source_severity = self.graph.severity_for_level(observation.level_m)
        if source_severity is Severity.STABLE:
            return []

        routes: dict[str, _Route] = {
            observation.source_node_id: _Route(0, observation.confidence, tuple())
        }
        queue: list[tuple[int, str]] = [(0, observation.source_node_id)]

        while queue:
            arrival, node_id = heapq.heappop(queue)
            current = routes[node_id]
            if arrival != current.arrival_minutes:
                continue
            for edge in self._adjacency[node_id]:
                if source_severity.rank < edge.min_severity.rank:
                    continue
                candidate = _Route(
                    arrival_minutes=arrival + edge.delay_minutes,
                    confidence=current.confidence * edge.confidence,
                    path=current.path + (edge,),
                )
                existing = routes.get(edge.target)
                is_better = existing is None or candidate.arrival_minutes < existing.arrival_minutes
                same_time_higher_confidence = (
                    existing is not None
                    and candidate.arrival_minutes == existing.arrival_minutes
                    and candidate.confidence > existing.confidence
                )
                if is_better or same_time_higher_confidence:
                    routes[edge.target] = candidate
                    heapq.heappush(queue, (candidate.arrival_minutes, edge.target))

        impacts: list[ImpactResult] = []
        for node_id, route in routes.items():
            node = self.graph.nodes[node_id]
            if not node.notify or not route.path:
                continue
            severity = Severity.from_rank(min(source_severity.rank, node.severity_cap.rank))
            assumptions = {
                assumption
                for edge in route.path
                for assumption in [edge.assumption]
                if assumption
            }
            if node.assumption:
                assumptions.add(node.assumption)
            impact_key = f"{run_id}|{node_id}|{observation.observed_at.isoformat()}"
            impact_id = "impact-" + hashlib.sha256(impact_key.encode("utf-8")).hexdigest()[:12]
            impacts.append(
                ImpactResult(
                    impact_id=impact_id,
                    run_id=run_id,
                    target_node_id=node_id,
                    target_name=node.name,
                    expected_impact_at=observation.observed_at + timedelta(minutes=route.arrival_minutes),
                    eta_minutes=route.arrival_minutes,
                    severity=severity,
                    confidence=round(route.confidence, 2),
                    path=tuple(
                        PathStep(
                            edge_id=edge.edge_id,
                            source=edge.source,
                            target=edge.target,
                            delay_minutes=edge.delay_minutes,
                            confidence=edge.confidence,
                            evidence_status=edge.evidence_status,
                            assumption=edge.assumption,
                        )
                        for edge in route.path
                    ),
                    assumptions=tuple(sorted(assumptions)),
                    action_code=self._action_code(node.node_type, severity),
                )
            )
        return sorted(impacts, key=lambda item: (item.eta_minutes, item.target_node_id))

    @staticmethod
    def _action_code(node_type: str, severity: Severity) -> str:
        if node_type in {"hospital", "clinic"} and severity.rank >= Severity.WARNING.rank:
            return "VERIFY_RESERVE_AND_PREALERT_TANKER"
        if node_type == "shelter":
            return "INSPECT_POTABLE_WATER_INVENTORY"
        return "MONITOR_AND_CONFIRM_STORAGE"
