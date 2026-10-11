from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ripple.forecast import ArtifactLogisticPredictor, ExplainableBaselinePredictor, ShortageFeatures
from ripple.http import event_body, response
from ripple.models import ValidationError


_PREDICTOR: ArtifactLogisticPredictor | ExplainableBaselinePredictor | None = None


def _predictor() -> ArtifactLogisticPredictor | ExplainableBaselinePredictor:
    global _PREDICTOR
    if _PREDICTOR is not None:
        return _PREDICTOR
    mode = os.environ.get("SHORTAGE_MODEL_MODE", "baseline").lower()
    if mode == "artifact":
        default_path = Path(__file__).resolve().parents[2] / "ripple" / "model_artifacts" / "shortage_logistic_v1.json"
        _PREDICTOR = ArtifactLogisticPredictor.from_path(os.environ.get("SHORTAGE_MODEL_PATH", str(default_path)))
    elif mode == "baseline":
        _PREDICTOR = ExplainableBaselinePredictor()
    else:
        raise ValidationError("SHORTAGE_MODEL_MODE must be baseline or artifact")
    return _PREDICTOR


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    is_http = "requestContext" in event
    try:
        body = event_body(event)
        features = ShortageFeatures.from_dict(body.get("features", body))
        payload = _predictor().predict(features).to_dict()
        return response(200, payload) if is_http else payload
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        payload = {"error": {"code": "INVALID_FORECAST_INPUT", "message": str(exc), "retryable": False}}
        return response(400, payload) if is_http else payload
