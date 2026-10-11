from __future__ import annotations

import json
import time
from typing import Any
import uuid

from ripple.engine import CascadeEngine
from ripple.http import event_body, response
from ripple.models import DependencyGraph, Observation, ValidationError

MAX_BODY_SIZE_BYTES = 1024 * 1024  # 1 MiB
MAX_GRAPH_NODES = 500
MAX_GRAPH_EDGES = 2500


def _is_http_event(event: dict[str, Any]) -> bool:
    return bool(
        "rawPath" in event
        or "requestContext" in event
        or "httpMethod" in event
        or ("body" in event and "graph" not in event)
    )


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    is_http = _is_http_event(event)

    # 1. Size check for HTTP raw body if present as string
    raw_body = event.get("body")
    if isinstance(raw_body, str):
        if len(raw_body.encode("utf-8")) > MAX_BODY_SIZE_BYTES:
            err = {
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": f"Request body exceeds maximum size of 1 MiB ({len(raw_body.encode('utf-8'))} bytes received)",
                },
                "message": f"Request body exceeds maximum size of 1 MiB ({len(raw_body.encode('utf-8'))} bytes received)",
            }
            return response(400, err) if is_http else err

    try:
        body = event_body(event) if is_http else event
    except Exception as exc:
        err = {
            "error": {"code": "MALFORMED_JSON", "message": f"Malformed request JSON: {exc}"},
            "message": f"Malformed request JSON: {exc}",
        }
        return response(400, err) if is_http else err

    # Extract correlation ID if HTTP or in body
    headers = event.get("headers") or {}
    correlation_id = (
        headers.get("x-correlation-id")
        or headers.get("X-Correlation-Id")
        or body.get("correlationId")
        or f"corr-{uuid.uuid4().hex[:8]}"
    )

    try:
        if not isinstance(body, dict):
            raise ValidationError("Request body must be a JSON object")

        if "graph" not in body or not isinstance(body["graph"], dict):
            raise ValidationError("Field 'graph' is required and must be an object")

        if "observation" not in body or not isinstance(body["observation"], dict):
            raise ValidationError("Field 'observation' is required and must be an object")

        graph_dict = body["graph"]
        nodes = graph_dict.get("nodes")
        edges = graph_dict.get("edges")

        if not isinstance(nodes, list):
            raise ValidationError("graph.nodes must be an array")
        if not isinstance(edges, list):
            raise ValidationError("graph.edges must be an array")

        if len(nodes) > MAX_GRAPH_NODES:
            raise ValidationError(
                f"Graph exceeds limit of {MAX_GRAPH_NODES} nodes (received {len(nodes)})"
            )
        if len(edges) > MAX_GRAPH_EDGES:
            raise ValidationError(
                f"Graph exceeds limit of {MAX_GRAPH_EDGES} edges (received {len(edges)})"
            )

        graph = DependencyGraph.from_dict(graph_dict)
        observation = Observation.from_dict(body["observation"])
        run_id = str(body.get("runId") or f"run-{uuid.uuid4().hex[:8]}")

        engine = CascadeEngine(graph)

        # Isolated calculation timing (excludes network, JSON deserialization, and model validation)
        t0 = time.perf_counter()
        impacts = engine.calculate(observation, run_id)
        calc_ms = round((time.perf_counter() - t0) * 1000, 3)

        result = {
            "schemaVersion": "1.0",
            "runId": run_id,
            "observationId": observation.observation_id,
            "severity": graph.severity_for_level(observation.level_m).value,
            "impacts": [impact.to_dict() for impact in impacts],
            "correlationId": str(correlation_id),
            "engineCalculationMs": calc_ms,
        }

        return response(200, result) if is_http else result

    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        code = "GRAPH_TOO_LARGE" if "limit of" in str(exc) else "INVALID_CASCADE_INPUT"
        err = {
            "error": {"code": code, "message": str(exc)},
            "message": str(exc),
        }
        return response(400, err) if is_http else {"error": code, "message": str(exc)}
