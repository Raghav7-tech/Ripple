from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math
from typing import Any


class ValidationError(ValueError):
    """Raised when an input contract is unsafe or internally inconsistent."""


class Severity(str, Enum):
    STABLE = "stable"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {
            Severity.STABLE: 0,
            Severity.WATCH: 1,
            Severity.WARNING: 2,
            Severity.CRITICAL: 3,
        }[self]

    @classmethod
    def from_rank(cls, rank: int) -> "Severity":
        return [cls.STABLE, cls.WATCH, cls.WARNING, cls.CRITICAL][max(0, min(rank, 3))]


class EvidenceStatus(str, Enum):
    VERIFIED = "verified"
    INFERRED = "inferred"
    DEMONSTRATION = "demonstration"


class ResourceType(str, Enum):
    WATER = "water"
    STAFF = "staff"
    MEDICAL_SUPPLY = "medical_supply"


def _required(data: dict[str, Any], key: str, context: str) -> Any:
    value = data.get(key)
    if value is None or value == "":
        raise ValidationError(f"{context}.{key} is required")
    return value


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field_name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(f"{field_name} must be finite")
    return number


def _confidence(value: Any, field_name: str) -> float:
    number = _number(value, field_name)
    if not 0 <= number <= 1:
        raise ValidationError(f"{field_name} must be between 0 and 1")
    return number


def _timestamp(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be valid ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include an explicit timezone offset")
    return parsed


@dataclass(frozen=True)
class Observation:
    observation_id: str
    event_id: str
    source_node_id: str
    observed_at: datetime
    received_at: datetime
    level_m: float
    confidence: float
    mode: str
    source_id: str
    schema_version: str = "1.0"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        context = "observation"
        schema_version = str(_required(data, "schemaVersion", context))
        if schema_version != "1.0":
            raise ValidationError(f"Unsupported observation schemaVersion: {schema_version}")
        mode = str(_required(data, "mode", context))
        if mode not in {"replay", "live"}:
            raise ValidationError("observation.mode must be replay or live")
        observation = cls(
            observation_id=str(_required(data, "observationId", context)),
            event_id=str(_required(data, "eventId", context)),
            source_node_id=str(_required(data, "sourceNodeId", context)),
            observed_at=_timestamp(_required(data, "observedAt", context), "observation.observedAt"),
            received_at=_timestamp(_required(data, "receivedAt", context), "observation.receivedAt"),
            level_m=_number(_required(data, "levelM", context), "observation.levelM"),
            confidence=_confidence(data.get("confidence", 1.0), "observation.confidence"),
            mode=mode,
            source_id=str(_required(data, "sourceId", context)),
            schema_version=schema_version,
        )
        if observation.received_at < observation.observed_at:
            raise ValidationError("observation.receivedAt cannot be earlier than observedAt")
        return observation


@dataclass(frozen=True)
class Node:
    node_id: str
    name: str
    node_type: str
    notify: bool
    severity_cap: Severity
    evidence_status: EvidenceStatus
    assumption: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        node_id = str(_required(data, "nodeId", "node"))
        try:
            status = EvidenceStatus(str(_required(data, "evidenceStatus", f"node[{node_id}]")))
            cap = Severity(str(data.get("severityCap", Severity.CRITICAL.value)))
        except ValueError as exc:
            raise ValidationError(f"node[{node_id}] has an invalid enum value") from exc
        assumption = data.get("assumption")
        if status is not EvidenceStatus.VERIFIED and not assumption:
            raise ValidationError(f"node[{node_id}] requires an assumption note")
        return cls(
            node_id=node_id,
            name=str(_required(data, "name", f"node[{node_id}]")),
            node_type=str(_required(data, "type", f"node[{node_id}]")),
            notify=bool(data.get("notify", False)),
            severity_cap=cap,
            evidence_status=status,
            assumption=str(assumption) if assumption else None,
        )


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source: str
    target: str
    delay_minutes: int
    confidence: float
    min_severity: Severity
    evidence_status: EvidenceStatus
    assumption: str | None = None
    resource_type: ResourceType = ResourceType.WATER

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        edge_id = str(_required(data, "edgeId", "edge"))
        delay = _number(_required(data, "delayMinutes", f"edge[{edge_id}]"), f"edge[{edge_id}].delayMinutes")
        if not delay.is_integer() or not 0 <= delay <= 10_080:
            raise ValidationError(f"edge[{edge_id}].delayMinutes must be an integer from 0 to 10080")
        try:
            status = EvidenceStatus(str(_required(data, "evidenceStatus", f"edge[{edge_id}]")))
            min_severity = Severity(str(data.get("minSeverity", Severity.WATCH.value)))
        except ValueError as exc:
            raise ValidationError(f"edge[{edge_id}] has an invalid enum value") from exc
        assumption = data.get("assumption")
        if status is not EvidenceStatus.VERIFIED and not assumption:
            raise ValidationError(f"edge[{edge_id}] requires an assumption note")
        if "resourceType" in data:
            raw_resource = data["resourceType"]
            if not isinstance(raw_resource, str):
                raise ValidationError(f"edge[{edge_id}].resourceType must be a string")
            try:
                resource_type = ResourceType(raw_resource)
            except ValueError as exc:
                raise ValidationError(
                    f"edge[{edge_id}].resourceType must be water, staff, or medical_supply"
                ) from exc
        else:
            resource_type = ResourceType.WATER
        return cls(
            edge_id=edge_id,
            source=str(_required(data, "from", f"edge[{edge_id}]")),
            target=str(_required(data, "to", f"edge[{edge_id}]")),
            delay_minutes=int(delay),
            confidence=_confidence(data.get("confidence", 1.0), f"edge[{edge_id}].confidence"),
            min_severity=min_severity,
            evidence_status=status,
            assumption=str(assumption) if assumption else None,
            resource_type=resource_type,
        )


@dataclass(frozen=True)
class DependencyGraph:
    version: str
    nodes: dict[str, Node]
    edges: tuple[Edge, ...]
    thresholds: dict[Severity, float]
    created_at: datetime
    approved_at: datetime | None
    schema_version: str = "1.0"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DependencyGraph":
        schema_version = str(_required(data, "schemaVersion", "graph"))
        if schema_version != "1.0":
            raise ValidationError(f"Unsupported graph schemaVersion: {schema_version}")
        nodes_list = data.get("nodes")
        edges_list = data.get("edges")
        if not isinstance(nodes_list, list) or not nodes_list:
            raise ValidationError("graph.nodes must be a non-empty array")
        if not isinstance(edges_list, list):
            raise ValidationError("graph.edges must be an array")
        parsed_nodes = [Node.from_dict(item) for item in nodes_list]
        node_ids = [node.node_id for node in parsed_nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValidationError("graph node IDs must be unique")
        nodes = {node.node_id: node for node in parsed_nodes}
        edges = tuple(Edge.from_dict(item) for item in edges_list)
        edge_ids = [edge.edge_id for edge in edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValidationError("graph edge IDs must be unique")
        for edge in edges:
            if edge.source not in nodes or edge.target not in nodes:
                raise ValidationError(f"edge[{edge.edge_id}] references a missing node")
            if edge.source == edge.target:
                raise ValidationError(f"edge[{edge.edge_id}] cannot be a self-loop")

        thresholds_data = data.get("thresholdsM")
        if not isinstance(thresholds_data, dict):
            raise ValidationError("graph.thresholdsM must be an object")
        thresholds = {
            Severity.WATCH: _number(_required(thresholds_data, "watch", "graph.thresholdsM"), "thresholdsM.watch"),
            Severity.WARNING: _number(_required(thresholds_data, "warning", "graph.thresholdsM"), "thresholdsM.warning"),
            Severity.CRITICAL: _number(_required(thresholds_data, "critical", "graph.thresholdsM"), "thresholdsM.critical"),
        }
        if not thresholds[Severity.WATCH] < thresholds[Severity.WARNING] < thresholds[Severity.CRITICAL]:
            raise ValidationError("graph thresholds must increase: watch < warning < critical")

        graph = cls(
            version=str(_required(data, "graphVersion", "graph")),
            nodes=nodes,
            edges=edges,
            thresholds=thresholds,
            created_at=_timestamp(_required(data, "createdAt", "graph"), "graph.createdAt"),
            approved_at=_timestamp(data["approvedAt"], "graph.approvedAt") if data.get("approvedAt") else None,
            schema_version=schema_version,
        )
        graph._validate_acyclic()
        return graph

    def _validate_acyclic(self) -> None:
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        indegree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            adjacency[edge.source].append(edge.target)
            indegree[edge.target] += 1
        queue = [node_id for node_id, degree in indegree.items() if degree == 0]
        visited = 0
        while queue:
            node_id = queue.pop()
            visited += 1
            for target in adjacency[node_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        if visited != len(self.nodes):
            raise ValidationError("graph contains a cycle; MVP graphs must be acyclic")

    def severity_for_level(self, level_m: float) -> Severity:
        if level_m >= self.thresholds[Severity.CRITICAL]:
            return Severity.CRITICAL
        if level_m >= self.thresholds[Severity.WARNING]:
            return Severity.WARNING
        if level_m >= self.thresholds[Severity.WATCH]:
            return Severity.WATCH
        return Severity.STABLE


@dataclass(frozen=True)
class PathStep:
    edge_id: str
    source: str
    target: str
    delay_minutes: int
    confidence: float
    evidence_status: EvidenceStatus
    assumption: str | None
    resource_type: ResourceType = ResourceType.WATER

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathStep":
        try:
            evidence_status = EvidenceStatus(str(_required(data, "evidenceStatus", "pathStep")))
        except ValueError as exc:
            raise ValidationError("pathStep.evidenceStatus is invalid") from exc
        delay = _number(_required(data, "delayMinutes", "pathStep"), "pathStep.delayMinutes")
        if not delay.is_integer() or delay < 0:
            raise ValidationError("pathStep.delayMinutes must be a non-negative integer")
        if "resourceType" in data:
            raw_resource = data["resourceType"]
            if not isinstance(raw_resource, str):
                raise ValidationError("pathStep.resourceType must be a string")
            try:
                resource_type = ResourceType(raw_resource)
            except ValueError as exc:
                raise ValidationError(
                    "pathStep.resourceType must be water, staff, or medical_supply"
                ) from exc
        else:
            resource_type = ResourceType.WATER
        return cls(
            edge_id=str(_required(data, "edgeId", "pathStep")),
            source=str(_required(data, "from", "pathStep")),
            target=str(_required(data, "to", "pathStep")),
            delay_minutes=int(delay),
            confidence=_confidence(data.get("confidence", 1.0), "pathStep.confidence"),
            evidence_status=evidence_status,
            assumption=str(data["assumption"]) if data.get("assumption") else None,
            resource_type=resource_type,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "edgeId": self.edge_id,
            "from": self.source,
            "to": self.target,
            "delayMinutes": self.delay_minutes,
            "confidence": self.confidence,
            "evidenceStatus": self.evidence_status.value,
            "assumption": self.assumption,
            "resourceType": self.resource_type.value,
        }


@dataclass(frozen=True)
class ImpactResult:
    impact_id: str
    run_id: str
    target_node_id: str
    target_name: str
    expected_impact_at: datetime
    eta_minutes: int
    severity: Severity
    confidence: float
    path: tuple[PathStep, ...]
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    action_code: str = "VERIFY_RESERVE"
    resource_type: ResourceType = ResourceType.WATER

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImpactResult":
        target = data.get("target")
        path = data.get("path")
        if not isinstance(target, dict):
            raise ValidationError("impact.target must be an object")
        if not isinstance(path, list) or not path:
            raise ValidationError("impact.path must be a non-empty array")
        eta = _number(_required(data, "etaMinutes", "impact"), "impact.etaMinutes")
        if not eta.is_integer() or eta < 0:
            raise ValidationError("impact.etaMinutes must be a non-negative integer")
        try:
            severity = Severity(str(_required(data, "severity", "impact")))
        except ValueError as exc:
            raise ValidationError("impact.severity is invalid") from exc
        assumptions = data.get("assumptions", [])
        if not isinstance(assumptions, list) or any(not isinstance(item, str) for item in assumptions):
            raise ValidationError("impact.assumptions must be an array of strings")
        if "resourceType" in data:
            raw_resource = data["resourceType"]
            if not isinstance(raw_resource, str):
                raise ValidationError("impact.resourceType must be a string")
            try:
                resource_type = ResourceType(raw_resource)
            except ValueError as exc:
                raise ValidationError(
                    "impact.resourceType must be water, staff, or medical_supply"
                ) from exc
        else:
            resource_type = ResourceType.WATER
        return cls(
            impact_id=str(_required(data, "impactId", "impact")),
            run_id=str(_required(data, "runId", "impact")),
            target_node_id=str(_required(target, "nodeId", "impact.target")),
            target_name=str(_required(target, "name", "impact.target")),
            expected_impact_at=_timestamp(
                _required(data, "expectedImpactAt", "impact"), "impact.expectedImpactAt"
            ),
            eta_minutes=int(eta),
            severity=severity,
            confidence=_confidence(data.get("confidence"), "impact.confidence"),
            path=tuple(PathStep.from_dict(item) for item in path),
            assumptions=tuple(assumptions),
            action_code=str(_required(data, "actionCode", "impact")),
            resource_type=resource_type,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "impactId": self.impact_id,
            "runId": self.run_id,
            "target": {"nodeId": self.target_node_id, "name": self.target_name},
            "expectedImpactAt": self.expected_impact_at.isoformat(),
            "etaMinutes": self.eta_minutes,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "resourceType": self.resource_type.value,
            "path": [step.to_dict() for step in self.path],
            "assumptions": list(self.assumptions),
            "actionCode": self.action_code,
        }
