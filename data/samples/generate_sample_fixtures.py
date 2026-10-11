"""Generates sample replay fixtures for Ripple historical scenarios."""
import json
from pathlib import Path

import sys
sys.path.insert(0, "backend")
from ripple.historical_replay import build_historical_yamuna_2023_scenario

SAMPLES_DIR = Path("data/samples")
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# 1. July 2023 Flood Replay
flood_scen = build_historical_yamuna_2023_scenario()
flood_payload = {
    "schemaVersion": "1.0",
    "eventId": "flood-delhi-2023",
    "name": "July 2023 Yamuna Flood & Water Supply Cascade Disaster",
    "description": (
        "Evidence-backed historical replay of the historic July 2023 Yamuna River flood in Delhi. "
        "River level thresholds are verified from CWC hydrometric data at Old Railway Bridge; "
        "WTP inundations and Sushruta Trauma Centre evacuation are sourced from NIDM/CWC reports."
    ),
    "primarySources": [
        {
            "sourceId": "src-cwc-delhi-floods-2023",
            "title": "Delhi Floods - 2023: A Case Study (Central Water Commission, Jan 2025)",
            "citation": "Pages 6, 9 (Old Railway Bridge HFL 208.66m, Hathnikund 3.59L cusecs)",
        },
        {
            "sourceId": "src-nidm-yamuna-2025",
            "title": "Impact of Inundation along River Yamuna in Delhi (NIDM, 2025)",
            "citation": "Pages 77, 89, 93 (Wazirabad, Chandrawal, Okhla shutdowns; Sushruta evacuation)",
        },
    ],
    "graph": flood_scen["graph"],
    "observations": flood_scen["observations"],
    "chronology": flood_scen["chronology"],
}

with open(SAMPLES_DIR / "yamuna-july-2023-flood-replay.json", "w", encoding="utf-8") as f:
    json.dump(flood_payload, f, indent=2, ensure_ascii=False)
print("Saved yamuna-july-2023-flood-replay.json")

# 2. CWC Juddo Dam 2024 Monsoon Surge (Upper Yamuna)
with open("data/sources/cwc/cwc_yamuna_juddo_dam_2024.json", "r", encoding="utf-8") as f:
    cwc_juddo = json.load(f)

# Take a curated 24-hour sequence from July 1, 2024 showing real hydrological diurnal/surge variations
monsoon_window = cwc_juddo["observations"][:24]
juddo_observations = [
    {
        "schemaVersion": "1.0",
        "observationId": o["observationId"],
        "eventId": "juddo-dam-monsoon-2024",
        "sourceNodeId": "gauge-cwc-juddo-dam",
        "observedAt": o["observedAt"],
        "receivedAt": o["observedAt"][:16] + ":15+05:30",
        "levelM": o["levelM"],
        "confidence": o["confidence"],
        "mode": "replay",
        "sourceId": "src-cwc-yamuna-hourly",
    }
    for o in monsoon_window
]

juddo_graph = {
    "schemaVersion": "1.0",
    "graphVersion": "cwc-juddo-dam-hydrology-v1",
    "createdAt": "2026-10-11T12:00:00+05:30",
    "approvedAt": None,
    "thresholdsM": {
        "watch": 628.0,
        "warning": 628.5,
        "critical": 629.0,
    },
    "nodes": [
        {
            "nodeId": "gauge-cwc-juddo-dam",
            "name": "CWC Juddo Dam Gauge (Dehradun, Uttarakhand)",
            "type": "gauge",
            "notify": False,
            "severityCap": "critical",
            "evidenceStatus": "verified",
            "assumption": "Real CWC manual hourly station located in Upper Yamuna Basin (Dehradun, Uttarakhand, Lat 30.53, Lon 77.92).",
        },
        {
            "nodeId": "reservoir-juddo-dam",
            "name": "Juddo Dam Reservoir Pool",
            "type": "reservoir",
            "notify": False,
            "severityCap": "critical",
            "evidenceStatus": "inferred",
            "assumption": "Immediate reservoir storage pool subject to upper catchment inflow surges.",
        },
        {
            "nodeId": "hydro-station-juddo",
            "name": "Juddo Hydroelectric Intake Control",
            "type": "control-intake",
            "notify": True,
            "severityCap": "critical",
            "evidenceStatus": "inferred",
            "assumption": "Hydraulic intake gate with spillway protocol under high river discharge.",
        },
    ],
    "edges": [
        {
            "edgeId": "e-juddo-gauge-res",
            "from": "gauge-cwc-juddo-dam",
            "to": "reservoir-juddo-dam",
            "delayMinutes": 10,
            "confidence": 0.99,
            "minSeverity": "watch",
            "evidenceStatus": "inferred",
            "assumption": "Gauge measurement to reservoir stage propagation.",
            "resourceType": "water",
        },
        {
            "edgeId": "e-juddo-res-intake",
            "from": "reservoir-juddo-dam",
            "to": "hydro-station-juddo",
            "delayMinutes": 20,
            "confidence": 0.96,
            "minSeverity": "warning",
            "evidenceStatus": "inferred",
            "assumption": "Spillway gate actuation protocol.",
            "resourceType": "water",
        },
    ],
}

juddo_payload = {
    "schemaVersion": "1.0",
    "eventId": "juddo-dam-monsoon-2024",
    "name": "CWC Upper Yamuna Hydrology Replay (Juddo Dam, 2024)",
    "description": (
        "Empirical manual hourly river water level telemetry from CWC's Juddo Dam station in the Upper Yamuna Basin (Uttarakhand). "
        "Discloses geographic location in Dehradun; thresholds are configured model assumptions."
    ),
    "primarySources": [
        {
            "sourceId": "src-cwc-yamuna-hourly",
            "title": "River Water Level CWC Yamuna Basin (2021-2025) Manual Hourly",
            "citation": "Central Water Commission / NWIC Dataset dd3b9bba-6ba2-4954-93cf-e3ee84b5d9af",
        }
    ],
    "stationMetadata": cwc_juddo["station"],
    "graph": juddo_graph,
    "observations": juddo_observations,
}

with open(SAMPLES_DIR / "cwc-juddo-dam-monsoon-2024.json", "w", encoding="utf-8") as f:
    json.dump(juddo_payload, f, indent=2, ensure_ascii=False)
print("Saved cwc-juddo-dam-monsoon-2024.json")
