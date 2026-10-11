from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path


FIELDS = [
    "schema_version",
    "record_id",
    "event_id",
    "split_group",
    "timestamp",
    "entity_id",
    "entity_type",
    "zone_id",
    "river_level_m",
    "river_rise_m_per_hour",
    "rainfall_mm_24h",
    "max_temperature_c",
    "treatment_capacity_pct",
    "expected_supply_m3h",
    "expected_demand_m3h",
    "reserve_hours",
    "upstream_disruption_probability",
    "outage_active",
    "criticality",
    "sensor_quality",
    "horizon_hours",
    "shortage_within_horizon",
    "hours_to_shortage",
    "label_source",
    "evidence_status",
    "synthetic",
    "source_ids",
]

ENTITY_PROFILES = {
    "locality": {"demand": (240, 780), "reserve": (4, 20), "criticality": (0.45, 0.75)},
    "school": {"demand": (4, 16), "reserve": (6, 30), "criticality": (0.45, 0.7)},
    "college": {"demand": (12, 42), "reserve": (8, 36), "criticality": (0.45, 0.72)},
    "restaurant": {"demand": (1.2, 6.5), "reserve": (3, 18), "criticality": (0.3, 0.58)},
    "healthcare": {"demand": (8, 38), "reserve": (10, 48), "criticality": (0.82, 1.0)},
}

ZONES = ("north", "central", "east", "south", "west")
HORIZONS = (24, 48, 72)


def _round(value: float, digits: int = 3) -> float:
    return round(max(0.0, value), digits)


def generate_rows(event_count: int, rows_per_event: int, seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    start = datetime(2023, 1, 3, 0, 0, tzinfo=UTC)
    entity_types = tuple(ENTITY_PROFILES)

    for event_index in range(event_count):
        event_id = f"synthetic-event-{event_index + 1:03d}"
        intensity = 0.82 if event_index % 7 == 0 else 0.56 if event_index % 3 == 0 else 0.22
        event_start = start + timedelta(days=event_index * 17)
        for row_index in range(rows_per_event):
            entity_type = entity_types[row_index % len(entity_types)]
            profile = ENTITY_PROFILES[entity_type]
            zone = ZONES[(event_index + row_index) % len(ZONES)]
            timestamp = event_start + timedelta(hours=row_index * 2)
            demand = rng.uniform(*profile["demand"])
            demand *= 1.0 + max(0.0, rng.gauss(0.05 + intensity * 0.14, 0.08))
            capacity = max(10.0, min(100.0, rng.gauss(102.0 - intensity * 58.0, 12.0)))
            upstream = max(0.0, min(1.0, rng.gauss(intensity, 0.14)))
            outage = rng.random() < (0.03 + intensity * 0.42)
            nominal_supply = demand * rng.uniform(0.78, 1.2)
            supply = nominal_supply * (capacity / 100.0) * (1.0 - 0.32 * upstream)
            if outage:
                supply *= rng.uniform(0.12, 0.58)
            reserve = max(1.0, rng.gauss(sum(profile["reserve"]) / 2, (profile["reserve"][1] - profile["reserve"][0]) / 5))
            river_rise = max(-0.08, rng.gauss(-0.01 + intensity * 0.48, 0.09))
            river_level = rng.gauss(204.0 + intensity * 3.8, 0.28)
            rainfall = max(0.0, rng.gauss(8 + intensity * 78, 18))
            temperature = rng.gauss(30 + (1 - intensity) * 7, 3.5)
            criticality = rng.uniform(*profile["criticality"])
            sensor_quality = max(0.55, min(1.0, rng.gauss(0.92, 0.08)))
            horizon = HORIZONS[(event_index + row_index) % len(HORIZONS)]

            deficit_ratio = max(0.0, (demand - supply) / demand)
            if deficit_ratio <= 0.015:
                hours_to_shortage: float | None = None
                shortage = False
            else:
                depletion = reserve / max(deficit_ratio, 0.02)
                disruption_acceleration = 1.0 - min(0.38, upstream * 0.25 + (0.16 if outage else 0.0))
                noisy_depletion = max(0.5, depletion * disruption_acceleration * math.exp(rng.gauss(0, 0.12)))
                hours_to_shortage = round(noisy_depletion, 2)
                shortage = noisy_depletion <= horizon

            rows.append(
                {
                    "schema_version": "1.0",
                    "record_id": f"syn-{event_index + 1:03d}-{row_index + 1:04d}",
                    "event_id": event_id,
                    "split_group": event_id,
                    "timestamp": timestamp.isoformat(),
                    "entity_id": f"{entity_type}-{zone}-{(row_index % 18) + 1:02d}",
                    "entity_type": entity_type,
                    "zone_id": zone,
                    "river_level_m": _round(river_level, 2),
                    "river_rise_m_per_hour": round(river_rise, 3),
                    "rainfall_mm_24h": _round(rainfall, 2),
                    "max_temperature_c": _round(temperature, 2),
                    "treatment_capacity_pct": _round(capacity, 2),
                    "expected_supply_m3h": _round(supply, 3),
                    "expected_demand_m3h": _round(demand, 3),
                    "reserve_hours": _round(reserve, 2),
                    "upstream_disruption_probability": _round(upstream, 3),
                    "outage_active": outage,
                    "criticality": _round(criticality, 3),
                    "sensor_quality": _round(sensor_quality, 3),
                    "horizon_hours": horizon,
                    "shortage_within_horizon": shortage,
                    "hours_to_shortage": hours_to_shortage if hours_to_shortage is not None else "",
                    "label_source": "hydraulic-reserve-simulation-v1",
                    "evidence_status": "demonstration",
                    "synthetic": True,
                    "source_ids": "ripple-synthetic-v1",
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Ripple's assumption-labelled synthetic shortage dataset.")
    parser.add_argument("--output", type=Path, default=Path("data/training/synthetic_shortage_v1.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("data/training/synthetic_shortage_v1.metadata.json"))
    parser.add_argument("--events", type=int, default=36)
    parser.add_argument("--rows-per-event", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.events < 10 or args.rows_per_event < 10:
        raise SystemExit("events and rows-per-event must both be at least 10")

    rows = generate_rows(args.events, args.rows_per_event, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    positives = sum(bool(row["shortage_within_horizon"]) for row in rows)
    metadata = {
        "schemaVersion": "1.0",
        "datasetId": "ripple-synthetic-shortage-v1",
        "createdAt": datetime.now(UTC).isoformat(),
        "generator": "ml/scripts/generate_dataset.py",
        "seed": args.seed,
        "rowCount": len(rows),
        "eventCount": args.events,
        "positiveCount": positives,
        "positiveRate": round(positives / len(rows), 4),
        "syntheticShare": 1.0,
        "operationalUseAllowed": False,
        "limitations": [
            "All entity-level features and labels are synthetic.",
            "Verified event anchors are stored separately and are not treated as facility labels.",
            "Use only for pipeline development, tests, and hackathon demonstration.",
        ],
    }
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
