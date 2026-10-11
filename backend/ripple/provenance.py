"""Ripple Provenance & Historical Data Models.

Defines provenance metadata, evidence classifications, station metadata,
normalized observations, and historical event structures.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
import math
from typing import Any


class EvidenceClassification(str, Enum):
    OBSERVED = "observed"
    REPORTED_EVENT = "reported_event"
    DERIVED = "derived"
    ASSUMED = "assumed"
    SYNTHETIC = "synthetic"


@dataclass(frozen=True)
class ProvenanceMetadata:
    source_id: str
    source_locator: str
    evidence_classification: EvidenceClassification
    retrieval_date: str = "2026-10-11"
    transformation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "sourceLocator": self.source_locator,
            "evidenceClassification": self.evidence_classification.value,
            "retrievalDate": self.retrieval_date,
            "transformation": self.transformation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceMetadata":
        return cls(
            source_id=str(data.get("sourceId", "unknown")),
            source_locator=str(data.get("sourceLocator", "")),
            evidence_classification=EvidenceClassification(
                str(data.get("evidenceClassification", EvidenceClassification.ASSUMED.value))
            ),
            retrieval_date=str(data.get("retrievalDate", "2026-10-11")),
            transformation=data.get("transformation"),
        )


@dataclass(frozen=True)
class StationMetadata:
    station_id: str
    name: str
    river: str
    basin: str
    state: str
    district: str
    latitude: float
    longitude: float
    zero_gauge_rl_m: float | None = None
    warning_threshold_m: float | None = None
    danger_threshold_m: float | None = None
    hfl_m: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stationId": self.station_id,
            "name": self.name,
            "river": self.river,
            "basin": self.basin,
            "state": self.state,
            "district": self.district,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "zeroGaugeRlM": self.zero_gauge_rl_m,
            "warningThresholdM": self.warning_threshold_m,
            "dangerThresholdM": self.danger_threshold_m,
            "hflM": self.hfl_m,
        }


@dataclass(frozen=True)
class HistoricalObservation:
    observation_id: str
    station_id: str
    observed_at: datetime
    level_m: float
    unit: str = "meter"
    provenance: ProvenanceMetadata = field(
        default_factory=lambda: ProvenanceMetadata(
            source_id="src-cwc-yamuna-hourly",
            source_locator="CWC Hourly Manual Telemetry",
            evidence_classification=EvidenceClassification.OBSERVED,
        )
    )
    confidence: float = 1.0
    data_quality: str = "valid"

    def to_dict(self) -> dict[str, Any]:
        return {
            "observationId": self.observation_id,
            "stationId": self.station_id,
            "observedAt": self.observed_at.isoformat(),
            "levelM": round(self.level_m, 3),
            "unit": self.unit,
            "provenance": self.provenance.to_dict(),
            "confidence": self.confidence,
            "dataQuality": self.data_quality,
        }


@dataclass(frozen=True)
class HistoricalEventRecord:
    event_id: str
    step_index: int
    timestamp: str  # ISO 8601 with explicit timezone
    phase: str
    location_id: str
    location_name: str
    headline: str
    description: str
    reported_metrics: dict[str, Any]
    evidence_classification: EvidenceClassification
    source_id: str
    source_locator: str
    review_status: str = "verified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventId": self.event_id,
            "stepIndex": self.step_index,
            "timestamp": self.timestamp,
            "phase": self.phase,
            "locationId": self.location_id,
            "locationName": self.location_name,
            "headline": self.headline,
            "description": self.description,
            "reportedMetrics": self.reported_metrics,
            "evidenceClassification": self.evidence_classification.value,
            "sourceId": self.source_id,
            "sourceLocator": self.source_locator,
            "reviewStatus": self.review_status,
        }


@dataclass(frozen=True)
class WtpProductionRecord:
    record_date: str
    wtp_id: str
    wtp_name: str
    capacity_mgd: float
    actual_mgd: float
    shortfall_mgd: float
    source_id: str
    source_locator: str
    evidence_classification: EvidenceClassification = EvidenceClassification.OBSERVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "recordDate": self.record_date,
            "wtpId": self.wtp_id,
            "wtpName": self.wtp_name,
            "capacityMgd": self.capacity_mgd,
            "actualMgd": self.actual_mgd,
            "shortfallMgd": self.shortfall_mgd,
            "sourceId": self.source_id,
            "sourceLocator": self.source_locator,
            "evidenceClassification": self.evidence_classification.value,
        }


@dataclass(frozen=True)
class HospitalRegistryRecord:
    facility_id: str
    name: str
    address: str
    zone: str
    contact: str
    email: str
    source_id: str = "src-delhi-hospitals-registry"
    source_locator: str = "Delhi Govt Health Directory"

    def to_dict(self) -> dict[str, Any]:
        return {
            "facilityId": self.facility_id,
            "name": self.name,
            "address": self.address,
            "zone": self.zone,
            "contact": self.contact,
            "email": self.email,
            "sourceId": self.source_id,
            "sourceLocator": self.source_locator,
        }
