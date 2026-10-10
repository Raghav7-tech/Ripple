from __future__ import annotations

import math
from dataclasses import dataclass
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
