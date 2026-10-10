from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from ripple.aws_store import RippleStore
from ripple.http import event_body, response
from ripple.models import ValidationError
from ripple.replay import run_replay

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def _load_s3_json(bucket: str, key: str) -> dict[str, Any]:
    import boto3

    body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValidationError(f"s3://{bucket}/{key} must contain a JSON object")
    return payload


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    correlation_id = event.get("correlationId") or str(uuid.uuid4())
    run_id = event.get("runId") or f"run-{uuid.uuid4().hex[:12]}"
    is_http = "requestContext" in event
    try:
        if is_http:
            body = event_body(event)
            event_id = str((event.get("pathParameters") or {}).get("eventId", ""))
            graph_version = str(body["graphVersion"])
            bucket = os.environ["REPLAY_BUCKET"]
            replay_data = _load_s3_json(bucket, f"replays/{event_id}.json")
            graph_data = _load_s3_json(bucket, f"graphs/{graph_version}.json")
        else:
            replay_data = event["replay"]
            graph_data = event["graph"]

        result = run_replay(replay_data, graph_data, run_id)
        result.update(
            {
                "correlationId": correlation_id,
                "completedAt": datetime.now(UTC).isoformat(),
            }
        )
        if os.environ.get("TABLE_NAME"):
            store = RippleStore()
            run_record = {key: value for key, value in result.items() if key not in {"steps", "latestImpacts", "advisories"}}
            run_record["impactCount"] = len(result["latestImpacts"])
            store.put_run(run_record)
            for impact in result["latestImpacts"]:
                store.put_impact(impact)
        LOGGER.info(json.dumps({"event": "replay_completed", "runId": run_id, "correlationId": correlation_id}))
        return response(200, result) if is_http else result
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        LOGGER.warning(json.dumps({"event": "replay_rejected", "runId": run_id, "correlationId": correlation_id}))
        error = {
            "error": {
                "code": "REPLAY_VALIDATION_FAILED",
                "message": str(exc),
                "correlationId": correlation_id,
                "retryable": False,
            }
        }
        return response(400, error) if is_http else error
