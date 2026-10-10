from __future__ import annotations

from typing import Any

from ripple.advisory import compose_advisory
from ripple.models import ImpactResult, ValidationError


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        impact = ImpactResult.from_dict(event["impact"])
        languages = event.get("languages", ["en", "hi"])
        if not isinstance(languages, list) or not languages:
            raise ValidationError("languages must be a non-empty array")
        return {
            "schemaVersion": "1.0",
            "impactId": impact.impact_id,
            "advisories": [compose_advisory(impact, str(language)).to_dict() for language in languages],
        }
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        return {"error": "INVALID_ADVISORY_INPUT", "message": str(exc)}
