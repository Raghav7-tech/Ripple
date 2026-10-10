from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from ripple.aws_store import RippleStore
from ripple.http import response


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    path = event.get("rawPath") or event.get("path") or "/"
    params = event.get("pathParameters") or {}

    if path == "/health":
        return response(
            200,
            {
                "status": "ok",
                "version": os.environ.get("APP_VERSION", "dev"),
                "time": datetime.now(UTC).isoformat(),
                "mode": os.environ.get("APP_MODE", "replay"),
            },
        )

    try:
        store = RippleStore()
        if path.startswith("/runs/"):
            run = store.get_run(str(params.get("runId", "")))
            return response(200, run) if run else response(404, {"error": {"code": "RUN_NOT_FOUND"}})
        if path.startswith("/impacts/"):
            impact = store.get_impact(str(params.get("impactId", "")))
            return response(200, impact) if impact else response(404, {"error": {"code": "IMPACT_NOT_FOUND"}})
        return response(404, {"error": {"code": "ROUTE_NOT_FOUND"}})
    except Exception:
        return response(503, {"error": {"code": "STORE_UNAVAILABLE", "retryable": True}})
