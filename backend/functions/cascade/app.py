from __future__ import annotations

from typing import Any

from ripple.engine import CascadeEngine
from ripple.models import DependencyGraph, Observation, ValidationError


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        graph = DependencyGraph.from_dict(event["graph"])
        observation = Observation.from_dict(event["observation"])
        run_id = str(event["runId"])
        impacts = CascadeEngine(graph).calculate(observation, run_id)
        return {
            "schemaVersion": "1.0",
            "runId": run_id,
            "observationId": observation.observation_id,
            "severity": graph.severity_for_level(observation.level_m).value,
            "impacts": [impact.to_dict() for impact in impacts],
        }
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        return {"error": "INVALID_CASCADE_INPUT", "message": str(exc)}
