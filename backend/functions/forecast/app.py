from __future__ import annotations

from typing import Any

from ripple.forecast import ExplainableBaselinePredictor, ShortageFeatures
from ripple.models import ValidationError


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        features = ShortageFeatures.from_dict(event.get("features", event))
        return ExplainableBaselinePredictor().predict(features).to_dict()
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        return {"error": "INVALID_FORECAST_INPUT", "message": str(exc)}
