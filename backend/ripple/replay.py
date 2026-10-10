from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .advisory import compose_advisory
from .engine import CascadeEngine
from .models import DependencyGraph, Observation, ValidationError


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return payload


def run_replay(replay_data: dict[str, Any], graph_data: dict[str, Any], run_id: str) -> dict[str, Any]:
    graph = DependencyGraph.from_dict(graph_data)
    observations_data = replay_data.get("observations")
    if not isinstance(observations_data, list) or not observations_data:
        raise ValidationError("replay.observations must be a non-empty array")

    engine = CascadeEngine(graph)
    steps: list[dict[str, Any]] = []
    latest_impacts = []
    for raw in observations_data:
        if not isinstance(raw, dict):
            raise ValidationError("each replay observation must be an object")
        observation = Observation.from_dict(raw)
        if observation.event_id != replay_data.get("eventId"):
            raise ValidationError("observation eventId must match replay eventId")
        impacts = engine.calculate(observation, run_id)
        latest_impacts = impacts
        steps.append(
            {
                "observation": raw,
                "severity": graph.severity_for_level(observation.level_m).value,
                "impacts": [impact.to_dict() for impact in impacts],
            }
        )

    advisories = [
        {
            "en": compose_advisory(impact, "en").to_dict(),
            "hi": compose_advisory(impact, "hi").to_dict(),
        }
        for impact in latest_impacts
    ]
    return {
        "schemaVersion": "1.0",
        "runId": run_id,
        "eventId": replay_data.get("eventId"),
        "graphVersion": graph.version,
        "mode": "replay",
        "status": "completed",
        "steps": steps,
        "latestImpacts": [impact.to_dict() for impact in latest_impacts],
        "advisories": advisories,
    }


def run_replay_files(replay_path: str | Path, graph_path: str | Path, run_id: str) -> dict[str, Any]:
    return run_replay(load_json(replay_path), load_json(graph_path), run_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic Ripple replay")
    parser.add_argument("replay", help="Path to the replay JSON file")
    parser.add_argument("graph", help="Path to the dependency graph JSON file")
    parser.add_argument("--run-id", default="run-local-demo")
    args = parser.parse_args()
    print(json.dumps(run_replay_files(args.replay, args.graph, args.run_id), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
