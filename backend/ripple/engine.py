from __future__ import annotations

import hashlib
import heapq
from dataclasses import dataclass
from datetime import timedelta

from .models import (
    DependencyGraph,
    Edge,
    ImpactResult,
    Observation,
    PathStep,
    ResourceType,
    Severity,
    ValidationError,
)


@dataclass(frozen=True)
class _Route:
    arrival_minutes: int
    confidence: float
    path: tuple[Edge, ...]
    resource_type: ResourceType
    edge_ids: tuple[str, ...] = ()


class CascadeEngine:
    """Deterministic earliest-impact traversal over a validated dependency DAG."""

    def __init__(self, graph: DependencyGraph):
        self.graph = graph
        self._adjacency: dict[tuple[str, ResourceType], list[Edge]] = {}
        self._outgoing_resources: dict[str, set[ResourceType]] = {node_id: set() for node_id in graph.nodes}
        for edge in graph.edges:
            key = (edge.source, edge.resource_type)
            if key not in self._adjacency:
                self._adjacency[key] = []
            self._adjacency[key].append(edge)
            self._outgoing_resources[edge.source].add(edge.resource_type)
        for edges in self._adjacency.values():
            edges.sort(key=lambda edge: (edge.delay_minutes, edge.edge_id))

    def calculate(self, observation: Observation, run_id: str) -> list[ImpactResult]:
        if observation.source_node_id not in self.graph.nodes:
            raise ValidationError("observation sourceNodeId does not exist in the selected graph")
        source_severity = self.graph.severity_for_level(observation.level_m)
        if source_severity is Severity.STABLE:
            return []

        active_resource_types = sorted(
            self._outgoing_resources.get(observation.source_node_id, set()),
            key=lambda r: r.value,
        )

        all_routes: list[tuple[str, ResourceType, _Route]] = []
        for resource_type in active_resource_types:
            routes: dict[str, _Route] = {
                observation.source_node_id: _Route(
                    arrival_minutes=0,
                    confidence=observation.confidence,
                    path=tuple(),
                    resource_type=resource_type,
                    edge_ids=tuple(),
                )
            }
            queue: list[tuple[int, float, tuple[str, ...], str]] = [
                (0, -observation.confidence, (), observation.source_node_id)
            ]

            while queue:
                arrival, neg_conf, edge_ids, node_id = heapq.heappop(queue)
                current = routes[node_id]
                if (arrival, -neg_conf, edge_ids) != (current.arrival_minutes, current.confidence, current.edge_ids):
                    continue
                for edge in self._adjacency.get((node_id, resource_type), []):
                    if source_severity.rank < edge.min_severity.rank:
                        continue
                    candidate = _Route(
                        arrival_minutes=arrival + edge.delay_minutes,
                        confidence=current.confidence * edge.confidence,
                        path=current.path + (edge,),
                        resource_type=resource_type,
                        edge_ids=current.edge_ids + (edge.edge_id,),
                    )
                    existing = routes.get(edge.target)
                    if self._is_better(candidate, existing):
                        routes[edge.target] = candidate
                        heapq.heappush(
                            queue,
                            (
                                candidate.arrival_minutes,
                                -candidate.confidence,
                                candidate.edge_ids,
                                edge.target,
                            ),
                        )

            for node_id, route in routes.items():
                if route.path:
                    all_routes.append((node_id, resource_type, route))

        impacts: list[ImpactResult] = []
        for node_id, resource_type, route in all_routes:
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
            impact_key = f"{run_id}|{node_id}|{resource_type.value}|{observation.observed_at.isoformat()}"
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
                    resource_type=resource_type,
                    path=tuple(
                        PathStep(
                            edge_id=edge.edge_id,
                            source=edge.source,
                            target=edge.target,
                            delay_minutes=edge.delay_minutes,
                            confidence=edge.confidence,
                            evidence_status=edge.evidence_status,
                            assumption=edge.assumption,
                            resource_type=edge.resource_type,
                        )
                        for edge in route.path
                    ),
                    assumptions=tuple(sorted(assumptions)),
                    action_code=self._action_code(node.node_type, severity),
                )
            )
        return sorted(impacts, key=lambda item: (item.eta_minutes, item.target_node_id, item.resource_type.value))

    @staticmethod
    def _is_better(candidate: _Route, existing: _Route | None) -> bool:
        if existing is None:
            return True
        if candidate.arrival_minutes != existing.arrival_minutes:
            return candidate.arrival_minutes < existing.arrival_minutes
        if candidate.confidence != existing.confidence:
            return candidate.confidence > existing.confidence
        return candidate.edge_ids < existing.edge_ids

    @staticmethod
    def _action_code(node_type: str, severity: Severity) -> str:
        if node_type in {"hospital", "clinic"} and severity.rank >= Severity.WARNING.rank:
            return "VERIFY_RESERVE_AND_PREALERT_TANKER"
        if node_type == "shelter":
            return "INSPECT_POTABLE_WATER_INVENTORY"
        return "MONITOR_AND_CONFIRM_STORAGE"

