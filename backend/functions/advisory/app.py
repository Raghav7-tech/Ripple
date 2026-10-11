from __future__ import annotations

import os
from typing import Any

from ripple.advisory import compose_advisory
from ripple.bedrock_advisory import compose_bedrock_advisory
from ripple.http import event_body, response
from ripple.models import ImpactResult, ValidationError


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    is_http = "requestContext" in event
    try:
        body = event_body(event)
        impact = ImpactResult.from_dict(body["impact"])
        languages = body.get("languages", ["en", "hi"])
        if not isinstance(languages, list) or not languages:
            raise ValidationError("languages must be a non-empty array")
        use_bedrock = os.environ.get("ENABLE_BEDROCK_ADVISORY", "false").lower() == "true"
        model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")
        advisories = []
        fallback_reasons: list[str] = []
        for language_value in languages:
            language = str(language_value)
            if use_bedrock:
                advisory, fallback_reason = compose_bedrock_advisory(
                    impact,
                    language,
                    model_id=model_id,
                )
                if fallback_reason:
                    fallback_reasons.append(f"{language}:{fallback_reason}")
            else:
                advisory = compose_advisory(impact, language)
            advisories.append(advisory.to_dict())
        payload = {
            "schemaVersion": "1.0",
            "impactId": impact.impact_id,
            "generationMode": "bedrock" if use_bedrock and not fallback_reasons else "deterministic_fallback",
            "fallbackReasons": fallback_reasons,
            "advisories": advisories,
        }
        return response(200, payload) if is_http else payload
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        payload = {"error": {"code": "INVALID_ADVISORY_INPUT", "message": str(exc), "retryable": False}}
        return response(400, payload) if is_http else payload
