from __future__ import annotations

import math
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .models import ValidationError, _confidence, _number, _required


@dataclass(frozen=True)
class ShortageFeatures:
    facility_id: str
    reserve_hours: float
    expected_supply_m3h: float
    expected_demand_m3h: float
    river_rise_m_per_hour: float
    upstream_disruption_probability: float
    criticality: float
    horizon_hours: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShortageFeatures":
        values = {
            key: _number(_required(data, key, "forecast"), f"forecast.{key}")
            for key in (
                "reserveHours",
                "expectedSupplyM3h",
                "expectedDemandM3h",
                "riverRiseMPerHour",
                "criticality",
                "horizonHours",
            )
        }
        if values["reserveHours"] < 0:
            raise ValidationError("forecast.reserveHours must be non-negative")
        if values["expectedSupplyM3h"] < 0 or values["expectedDemandM3h"] <= 0:
            raise ValidationError("forecast supply must be non-negative and demand must be positive")
        if not 1 <= values["horizonHours"] <= 168 or not values["horizonHours"].is_integer():
            raise ValidationError("forecast.horizonHours must be an integer from 1 to 168")
        return cls(
            facility_id=str(_required(data, "facilityId", "forecast")),
            reserve_hours=values["reserveHours"],
            expected_supply_m3h=values["expectedSupplyM3h"],
            expected_demand_m3h=values["expectedDemandM3h"],
            river_rise_m_per_hour=values["riverRiseMPerHour"],
            upstream_disruption_probability=_confidence(
                data.get("upstreamDisruptionProbability"),
                "forecast.upstreamDisruptionProbability",
            ),
            criticality=_confidence(values["criticality"], "forecast.criticality"),
            horizon_hours=int(values["horizonHours"]),
        )


@dataclass(frozen=True)
class ShortageForecast:
    facility_id: str
    shortage_probability: float
    estimated_hours_to_shortage: float | None
    risk_band: str
    horizon_hours: int
    top_factors: tuple[str, ...]
    model_version: str
    production_ready: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "facilityId": self.facility_id,
            "shortageProbability": self.shortage_probability,
            "estimatedHoursToShortage": self.estimated_hours_to_shortage,
            "riskBand": self.risk_band,
            "horizonHours": self.horizon_hours,
            "topFactors": list(self.top_factors),
            "modelVersion": self.model_version,
            "productionReady": self.production_ready,
        }


class ShortagePredictor(Protocol):
    def predict(self, features: ShortageFeatures) -> ShortageForecast: ...


class ExplainableBaselinePredictor:
    """Safe pre-ML baseline that defines the production model's contract.

    Coefficients are explicitly hand-authored and not represented as trained or
    calibrated. Replace this class with a validated model adapter after obtaining
    labeled facility shortage data.
    """

    model_version = "explainable-baseline-v1"

    def predict(self, features: ShortageFeatures) -> ShortageForecast:
        gap_ratio = max(
            0.0,
            (features.expected_demand_m3h - features.expected_supply_m3h)
            / features.expected_demand_m3h,
        )
        reserve_pressure = max(0.0, min(1.0, (24.0 - features.reserve_hours) / 24.0))
        rise_pressure = max(0.0, min(1.0, features.river_rise_m_per_hour / 0.5))
        factors = {
            "supply-demand gap": 3.2 * gap_ratio,
            "low reserve": 1.8 * reserve_pressure,
            "rising river": 1.2 * rise_pressure,
            "upstream disruption": 1.5 * features.upstream_disruption_probability,
            "facility criticality": 0.8 * features.criticality,
        }
        logit = -3.0 + sum(factors.values())
        probability = 1.0 / (1.0 + math.exp(-logit))

        hours_to_shortage: float | None = None
        if gap_ratio > 0:
            hours_to_shortage = round(features.reserve_hours / gap_ratio, 1)
            within_horizon = max(0.0, min(1.0, 1.0 - hours_to_shortage / features.horizon_hours))
            probability = max(probability, 0.35 + 0.6 * within_horizon)

        probability = round(max(0.0, min(1.0, probability)), 2)
        risk_band = "critical" if probability >= 0.8 else "high" if probability >= 0.6 else "moderate" if probability >= 0.35 else "low"
        top_factors = tuple(
            name for name, value in sorted(factors.items(), key=lambda item: item[1], reverse=True)[:3]
        )
        return ShortageForecast(
            facility_id=features.facility_id,
            shortage_probability=probability,
            estimated_hours_to_shortage=hours_to_shortage,
            risk_band=risk_band,
            horizon_hours=features.horizon_hours,
            top_factors=top_factors,
            model_version=self.model_version,
            production_ready=False,
        )


class ArtifactLogisticPredictor:
    """Dependency-free inference adapter for a versioned logistic model artifact.

    Training happens outside Lambda. The deployed function only loads reviewed
    coefficients and applies the same feature transforms recorded in the
    artifact, keeping cold starts small and predictions reproducible.
    """

    FEATURE_LABELS = {
        "reserveHours": "low reserve",
        "supplyDemandGapRatio": "supply-demand gap",
        "riverRiseMPerHour": "rising river",
        "upstreamDisruptionProbability": "upstream disruption",
        "criticality": "entity criticality",
        "horizonHours": "forecast horizon",
    }

    def __init__(self, artifact: dict[str, Any]) -> None:
        if artifact.get("schemaVersion") != "1.0" or artifact.get("modelType") != "logistic_regression":
            raise ValidationError("forecast artifact schema or model type is unsupported")
        feature_order = artifact.get("featureOrder")
        means = artifact.get("means")
        scales = artifact.get("scales")
        weights = artifact.get("weights")
        if not isinstance(feature_order, list) or not feature_order:
            raise ValidationError("forecast artifact featureOrder must be a non-empty array")
        if not all(isinstance(item, str) for item in feature_order):
            raise ValidationError("forecast artifact featureOrder values must be strings")
        for label, values in (("means", means), ("scales", scales), ("weights", weights)):
            if not isinstance(values, list) or len(values) != len(feature_order):
                raise ValidationError(f"forecast artifact {label} must match featureOrder")
            if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
                raise ValidationError(f"forecast artifact {label} must contain numbers")
        if any(float(scale) <= 0 for scale in scales):
            raise ValidationError("forecast artifact scales must be positive")
        self.feature_order = tuple(feature_order)
        self.means = tuple(float(value) for value in means)
        self.scales = tuple(float(value) for value in scales)
        self.weights = tuple(float(value) for value in weights)
        self.bias = _number(artifact.get("bias"), "forecast artifact.bias")
        self.model_version = str(_required(artifact, "modelVersion", "forecast artifact"))
        self.production_ready = bool(artifact.get("productionReady", False))

    @classmethod
    def from_path(cls, path: str | Path) -> "ArtifactLogisticPredictor":
        with Path(path).open(encoding="utf-8") as handle:
            artifact = json.load(handle)
        if not isinstance(artifact, dict):
            raise ValidationError("forecast artifact must contain a JSON object")
        return cls(artifact)

    @staticmethod
    def _raw_features(features: ShortageFeatures) -> dict[str, float]:
        gap_ratio = max(
            0.0,
            (features.expected_demand_m3h - features.expected_supply_m3h)
            / features.expected_demand_m3h,
        )
        return {
            "reserveHours": features.reserve_hours,
            "supplyDemandGapRatio": gap_ratio,
            "riverRiseMPerHour": features.river_rise_m_per_hour,
            "upstreamDisruptionProbability": features.upstream_disruption_probability,
            "criticality": features.criticality,
            "horizonHours": float(features.horizon_hours),
        }

    def predict(self, features: ShortageFeatures) -> ShortageForecast:
        raw = self._raw_features(features)
        try:
            standardized = [
                (raw[name] - mean) / scale
                for name, mean, scale in zip(self.feature_order, self.means, self.scales, strict=True)
            ]
        except KeyError as exc:
            raise ValidationError(f"forecast artifact requests unknown feature: {exc.args[0]}") from exc
        contributions = [weight * value for weight, value in zip(self.weights, standardized, strict=True)]
        logit = self.bias + sum(contributions)
        probability = round(1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, logit)))), 3)
        risk_band = "critical" if probability >= 0.8 else "high" if probability >= 0.6 else "moderate" if probability >= 0.35 else "low"

        gap_ratio = raw["supplyDemandGapRatio"]
        hours_to_shortage = round(features.reserve_hours / gap_ratio, 1) if gap_ratio > 0 else None
        ranked = sorted(
            zip(self.feature_order, contributions, strict=True),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
        top_factors = tuple(self.FEATURE_LABELS.get(name, name) for name, _ in ranked[:3])
        return ShortageForecast(
            facility_id=features.facility_id,
            shortage_probability=probability,
            estimated_hours_to_shortage=hours_to_shortage,
            risk_band=risk_band,
            horizon_hours=features.horizon_hours,
            top_factors=top_factors,
            model_version=self.model_version,
            production_ready=self.production_ready,
        )
