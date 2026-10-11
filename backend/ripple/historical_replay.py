"""Ripple Historical Replay & Scenario Construction Layer.

Adapts verified historical observations, reported events, and facility registries
into deterministic DependencyGraph and Observation payloads for the cascade engine.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .provenance import (
    EvidenceClassification,
    HistoricalEventRecord,
    HistoricalObservation,
    HospitalRegistryRecord,
    ProvenanceMetadata,
    StationMetadata,
    WtpProductionRecord,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SOURCES_DIR = BASE_DIR / "data" / "sources"


def load_json_file(rel_path: str | Path) -> dict[str, Any]:
    full_path = SOURCES_DIR / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"Source file not found: {full_path}")
    with full_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_cwc_observations(station_name: str = "Juddo Dam") -> list[dict[str, Any]]:
    safe_name = station_name.lower().replace(" ", "_")
    data = load_json_file(f"cwc/cwc_yamuna_{safe_name}_2024.json")
    return data.get("observations", [])


def get_djb_production_records() -> list[dict[str, Any]]:
    data = load_json_file("djb/djb_wtp_production_2024.json")
    return data.get("records", [])


def get_delhi_hospitals() -> list[dict[str, Any]]:
    data = load_json_file("health/delhi_hospitals_registry.json")
    return data.get("facilities", [])


def get_july_2023_flood_chronology() -> list[dict[str, Any]]:
    data = load_json_file("events/yamuna_july_2023_flood_chronology.json")
    return data.get("steps", [])


class HospitalDemandCalculator:
    """Calculates hospital water demand proxy based on MoHFW IPHS guidelines (Page 47)."""

    NORM_MIN_L_PER_BED_DAY = 450.0
    NORM_MAX_L_PER_BED_DAY = 500.0
    NORM_RECOMMENDED_L_PER_BED_DAY = 475.0
    CITATION = "Indian Public Health Standards (IPHS) Guidelines for District Hospitals, Page 47"

    @classmethod
    def calculate_daily_demand(cls, bed_count: int) -> dict[str, Any]:
        if bed_count <= 0:
            raise ValueError("bed_count must be a positive integer")
        min_demand = bed_count * cls.NORM_MIN_L_PER_BED_DAY
        max_demand = bed_count * cls.NORM_MAX_L_PER_BED_DAY
        recommended = bed_count * cls.NORM_RECOMMENDED_L_PER_BED_DAY
        return {
            "bedCount": bed_count,
            "normLitersPerBedDay": cls.NORM_RECOMMENDED_L_PER_BED_DAY,
            "minDailyDemandLiters": round(min_demand, 1),
            "maxDailyDemandLiters": round(max_demand, 1),
            "recommendedDailyDemandLiters": round(recommended, 1),
            "emergency48hStorageLiters": round(recommended * 2.0, 1),
            "evidenceClassification": EvidenceClassification.DERIVED.value,
            "sourceCitation": cls.CITATION,
            "formula": "daily_demand_liters = bed_count * 475 L/bed/day",
            "isProxy": True,
            "proxyLimitation": "Engineering norm proxy; does not represent actual meter-measured consumption.",
        }


def build_historical_yamuna_2023_scenario() -> dict[str, Any]:
    """Builds the evidence-backed July 2023 Delhi Flood Disaster scenario."""
    graph = {
        "schemaVersion": "1.0",
        "graphVersion": "yamuna-july-2023-historical-v1",
        "createdAt": "2026-10-11T12:00:00+05:30",
        "approvedAt": "2026-10-11T12:00:00+05:30",
        "thresholdsM": {
            "watch": 204.50,    # Official CWC Warning Level at Old Railway Bridge
            "warning": 205.33,  # Official CWC Danger Level at Old Railway Bridge
            "critical": 207.49, # 1978 Historical HFL Record breached in July 2023
        },
        "nodes": [
            {
                "nodeId": "gauge-delhi-orb",
                "name": "Old Delhi Railway Bridge (ORB) CWC Gauge",
                "type": "gauge",
                "notify": False,
                "severityCap": "critical",
                "evidenceStatus": "verified",
                "assumption": "Official CWC hydrometric station; Warning 204.5m, Danger 205.33m, Peak 208.66m (CWC Case Study p.6, p.9).",
            },
            {
                "nodeId": "wtp-wazirabad",
                "name": "Wazirabad Water Treatment Plant",
                "type": "treatment-plant",
                "notify": False,
                "severityCap": "critical",
                "evidenceStatus": "verified",
                "assumption": "Inundated and shut down on 13 July 2023 due to pump house submergence (NIDM Yamuna Report p.77).",
            },
            {
                "nodeId": "wtp-chandrawal",
                "name": "Chandrawal Water Treatment Plant",
                "type": "treatment-plant",
                "notify": False,
                "severityCap": "critical",
                "evidenceStatus": "verified",
                "assumption": "Inundated and shut down on 13 July 2023 due to pump house submergence (NIDM Yamuna Report p.77).",
            },
            {
                "nodeId": "wtp-okhla",
                "name": "Okhla Water Treatment Plant",
                "type": "treatment-plant",
                "notify": False,
                "severityCap": "critical",
                "evidenceStatus": "verified",
                "assumption": "Inundated and shut down on 13 July 2023 due to river flooding (NIDM Yamuna Report p.77).",
            },
            {
                "nodeId": "zone-north-delhi",
                "name": "North Delhi Water Distribution Zone",
                "type": "supply-zone",
                "notify": False,
                "severityCap": "critical",
                "evidenceStatus": "inferred",
                "assumption": "Fed by Wazirabad WTP; severe water supply disruption reported on 13-16 July (NIDM Report p.77).",
            },
            {
                "nodeId": "zone-central-delhi",
                "name": "Central Delhi Water Distribution Zone",
                "type": "supply-zone",
                "notify": False,
                "severityCap": "critical",
                "evidenceStatus": "inferred",
                "assumption": "Fed by Chandrawal WTP; municipal supply rationalized (NIDM Report p.77).",
            },
            {
                "nodeId": "hosp-sushruta-trauma",
                "name": "Sushruta Trauma Centre (Civil Lines)",
                "type": "hospital",
                "notify": True,
                "severityCap": "critical",
                "evidenceStatus": "verified",
                "assumption": "Directly inundated on 13 July 2023; patients emergency-evacuated (NIDM Report p.77).",
            },
            {
                "nodeId": "hosp-aruna-asaf-ali",
                "name": "Aruna Asaf Ali Govt. Hospital (Civil Lines)",
                "type": "hospital",
                "notify": True,
                "severityCap": "critical",
                "evidenceStatus": "verified",
                "assumption": "Located at 5-Rajpur Road, Civil Lines; water supply disrupted by Wazirabad shutdown (Delhi Health Directory).",
            },
            {
                "nodeId": "hosp-lnjp",
                "name": "Lok Nayak Hospital (LNJP / Delhi Gate)",
                "type": "hospital",
                "notify": True,
                "severityCap": "warning",
                "evidenceStatus": "verified",
                "assumption": "Major referral center; received evacuated patients and emergency water tankers (NIDM Report p.77, p.89).",
            },
            {
                "nodeId": "shelter-kashmere-gate",
                "name": "Kashmere Gate Flood Relief Shelter",
                "type": "shelter",
                "notify": True,
                "severityCap": "watch",
                "evidenceStatus": "inferred",
                "assumption": "District relief camp supporting flood-displaced citizens from Yamuna Bazar (NIDM Report p.73, p.93).",
            },
        ],
        "edges": [
            {
                "edgeId": "e-orb-wazirabad",
                "from": "gauge-delhi-orb",
                "to": "wtp-wazirabad",
                "delayMinutes": 15,
                "confidence": 0.98,
                "minSeverity": "warning",
                "evidenceStatus": "verified",
                "assumption": "Overbank floodwaters reach Wazirabad raw intake pump house (CWC/NIDM flood chronology).",
                "resourceType": "water",
            },
            {
                "edgeId": "e-orb-sushruta",
                "from": "gauge-delhi-orb",
                "to": "hosp-sushruta-trauma",
                "delayMinutes": 25,
                "confidence": 0.96,
                "minSeverity": "critical",
                "evidenceStatus": "verified",
                "assumption": "Direct floodwater overtopping along Metcalf Road riverbank (NIDM Report p.77).",
                "resourceType": "water",
            },
            {
                "edgeId": "e-orb-chandrawal",
                "from": "gauge-delhi-orb",
                "to": "wtp-chandrawal",
                "delayMinutes": 20,
                "confidence": 0.97,
                "minSeverity": "warning",
                "evidenceStatus": "verified",
                "assumption": "River backflow reaches Chandrawal pump station (NIDM Report p.77).",
                "resourceType": "water",
            },
            {
                "edgeId": "e-wazirabad-north",
                "from": "wtp-wazirabad",
                "to": "zone-north-delhi",
                "delayMinutes": 20,
                "confidence": 0.95,
                "minSeverity": "warning",
                "evidenceStatus": "inferred",
                "assumption": "Plant shutdown causes immediate pressure loss in North zone mains.",
                "resourceType": "water",
            },
            {
                "edgeId": "e-chandrawal-central",
                "from": "wtp-chandrawal",
                "to": "zone-central-delhi",
                "delayMinutes": 30,
                "confidence": 0.94,
                "minSeverity": "warning",
                "evidenceStatus": "inferred",
                "assumption": "Plant shutdown causes pressure loss in Central zone distribution network.",
                "resourceType": "water",
            },
            {
                "edgeId": "e-north-aruna",
                "from": "zone-north-delhi",
                "to": "hosp-aruna-asaf-ali",
                "delayMinutes": 15,
                "confidence": 0.93,
                "minSeverity": "warning",
                "evidenceStatus": "inferred",
                "assumption": "Municipal feeder connection to Civil Lines hospital.",
                "resourceType": "water",
            },
            {
                "edgeId": "e-central-lnjp",
                "from": "zone-central-delhi",
                "to": "hosp-lnjp",
                "delayMinutes": 25,
                "confidence": 0.92,
                "minSeverity": "warning",
                "evidenceStatus": "inferred",
                "assumption": "Municipal feeder connection to LNJP hospital complex.",
                "resourceType": "water",
            },
            {
                "edgeId": "e-north-shelter",
                "from": "zone-north-delhi",
                "to": "shelter-kashmere-gate",
                "delayMinutes": 45,
                "confidence": 0.88,
                "minSeverity": "critical",
                "evidenceStatus": "inferred",
                "assumption": "Secondary water supply disruption at relief camp.",
                "resourceType": "water",
            },
            {
                "edgeId": "e-sushruta-lnjp-staff",
                "from": "hosp-sushruta-trauma",
                "to": "hosp-lnjp",
                "delayMinutes": 40,
                "confidence": 0.95,
                "minSeverity": "critical",
                "evidenceStatus": "verified",
                "assumption": "Patient and clinical staff evacuation transfer from flooded trauma center to LNJP (NIDM Report p.77).",
                "resourceType": "staff",
            },
        ],
    }

    # Historical observation sequence corresponding to 11-13 July 2023 flood progression
    observations = [
        {
            "schemaVersion": "1.0",
            "observationId": "orb-flood-2023-01",
            "eventId": "flood-delhi-2023",
            "sourceNodeId": "gauge-delhi-orb",
            "observedAt": "2023-07-11T12:00:00+05:30",
            "receivedAt": "2023-07-11T12:05:00+05:30",
            "levelM": 204.10,
            "confidence": 1.0,
            "mode": "replay",
            "sourceId": "src-cwc-delhi-floods-2023",
        },
        {
            "schemaVersion": "1.0",
            "observationId": "orb-flood-2023-02",
            "eventId": "flood-delhi-2023",
            "sourceNodeId": "gauge-delhi-orb",
            "observedAt": "2023-07-11T17:00:00+05:30",
            "receivedAt": "2023-07-11T17:05:00+05:30",
            "levelM": 204.50,
            "confidence": 1.0,
            "mode": "replay",
            "sourceId": "src-cwc-delhi-floods-2023",
        },
        {
            "schemaVersion": "1.0",
            "observationId": "orb-flood-2023-03",
            "eventId": "flood-delhi-2023",
            "sourceNodeId": "gauge-delhi-orb",
            "observedAt": "2023-07-12T08:00:00+05:30",
            "receivedAt": "2023-07-12T08:05:00+05:30",
            "levelM": 205.33,
            "confidence": 1.0,
            "mode": "replay",
            "sourceId": "src-cwc-delhi-floods-2023",
        },
        {
            "schemaVersion": "1.0",
            "observationId": "orb-flood-2023-04",
            "eventId": "flood-delhi-2023",
            "sourceNodeId": "gauge-delhi-orb",
            "observedAt": "2023-07-12T13:00:00+05:30",
            "receivedAt": "2023-07-12T13:05:00+05:30",
            "levelM": 207.49,
            "confidence": 1.0,
            "mode": "replay",
            "sourceId": "src-cwc-delhi-floods-2023",
        },
        {
            "schemaVersion": "1.0",
            "observationId": "orb-flood-2023-05",
            "eventId": "flood-delhi-2023",
            "sourceNodeId": "gauge-delhi-orb",
            "observedAt": "2023-07-13T18:00:00+05:30",
            "receivedAt": "2023-07-13T18:05:00+05:30",
            "levelM": 208.66,
            "confidence": 1.0,
            "mode": "replay",
            "sourceId": "src-cwc-delhi-floods-2023",
        },
    ]

    return {
        "graph": graph,
        "observations": observations,
        "chronology": get_july_2023_flood_chronology(),
    }
