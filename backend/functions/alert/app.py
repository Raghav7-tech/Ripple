from __future__ import annotations

import json
import os
from typing import Any

from ripple.advisory import compose_advisory
from ripple.aws_store import RippleStore
from ripple.http import event_body, response
from ripple.models import ImpactResult, ValidationError


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        body = event_body(event)
        expected_run_id = str(body["expectedRunId"])
        path_impact_id = str((event.get("pathParameters") or {}).get("impactId", ""))
        if os.environ.get("TABLE_NAME") and path_impact_id:
            store = RippleStore()
            stored_impact = store.get_impact(path_impact_id)
            if not stored_impact:
                raise ValidationError("impact was not found")
            impact = ImpactResult.from_dict(stored_impact)
            run = store.get_run(impact.run_id)
            if not run or run.get("status") != "completed":
                raise ValidationError("impact run is missing or incomplete")
        else:
            impact = ImpactResult.from_dict(body["impact"])
        if path_impact_id and path_impact_id != impact.impact_id:
            raise ValidationError("path impactId does not match the stored impact")
        if impact.run_id != expected_run_id:
            raise ValidationError("expectedRunId does not match the impact run")
        if body.get("approved") is not True:
            raise ValidationError("approved must be true; Ripple never sends automatically")

        language = str(body.get("language", "en"))
        advisory = compose_advisory(impact, language).to_dict()
        delivery_enabled = os.environ.get("ENABLE_ALERT_DELIVERY", "false").lower() == "true"
        if not delivery_enabled:
            return response(
                200,
                {
                    "status": "preview_only",
                    "delivered": False,
                    "advisory": advisory,
                    "message": "Approval validated; external delivery is disabled.",
                },
            )

        import boto3

        publish = boto3.client("sns").publish(
            TopicArn=os.environ["ALERT_TOPIC_ARN"],
            Subject=f"Ripple {impact.severity.value.upper()} advisory",
            Message=json.dumps(advisory, ensure_ascii=False),
            MessageAttributes={
                "impactId": {"DataType": "String", "StringValue": impact.impact_id},
                "runId": {"DataType": "String", "StringValue": impact.run_id},
            },
        )
        return response(202, {"status": "accepted", "delivered": True, "messageId": publish["MessageId"]})
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        return response(
            400,
            {"error": {"code": "ALERT_APPROVAL_REJECTED", "message": str(exc), "retryable": False}},
        )
