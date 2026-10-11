from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any

# Ensure backend root is on sys.path for direct script execution
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ripple.engine import CascadeEngine
from ripple.models import DependencyGraph, Observation, ResourceType


def build_synthetic_graph(num_nodes: int, out_degree: int, max_layers: int = 20) -> dict[str, Any]:
    if num_nodes < 2:
        raise ValueError("num_nodes must be at least 2")
    if out_degree < 1:
        raise ValueError("out_degree must be at least 1")

    # Layer 0 is the root gauge
    # Layers 1 to max_layers - 1 partition the remaining nodes
    num_layers = min(max_layers, num_nodes)
    remaining_nodes = num_nodes - 1
    layer_count = num_layers - 1
    base_size = remaining_nodes // layer_count
    extra = remaining_nodes % layer_count

    layers: list[list[str]] = [["node-0"]]
    current_idx = 1
    for layer_i in range(layer_count):
        size = base_size + (1 if layer_i < extra else 0)
        layers.append([f"node-{current_idx + j}" for j in range(size)])
        current_idx += size

    nodes = [
        {
            "nodeId": "node-0",
            "name": "Benchmark Root Gauge",
            "type": "gauge",
            "notify": False,
            "severityCap": "critical",
            "evidenceStatus": "demonstration",
            "assumption": "Synthetic root gauge for benchmark.",
        }
    ]

    for layer in layers[1:]:
        for node_id in layer:
            nodes.append(
                {
                    "nodeId": node_id,
                    "name": f"Synthetic Hospital {node_id}",
                    "type": "hospital",
                    "notify": True,
                    "severityCap": "critical",
                    "evidenceStatus": "demonstration",
                    "assumption": "Synthetic benchmark facility node.",
                }
            )

    edges: list[dict[str, Any]] = []
    edge_counter = 0

    for l in range(len(layers) - 1):
        sources = layers[l]
        targets = layers[l + 1]
        target_count = len(targets)
        k = min(out_degree, target_count)

        for u_idx, src in enumerate(sources):
            # Deterministically choose k distinct targets in next layer
            for j in range(k):
                target_idx = (u_idx + j) % target_count
                tgt = targets[target_idx]
                edge_counter += 1
                edges.append(
                    {
                        "edgeId": f"e-{edge_counter}-{src}-{tgt}",
                        "from": src,
                        "to": tgt,
                        "delayMinutes": (u_idx + j) % 15 + 1,
                        "confidence": 1.0,
                        "minSeverity": "warning",
                        "evidenceStatus": "demonstration",
                        "assumption": "Synthetic benchmark dependency edge.",
                        "resourceType": "water",
                    }
                )

    return {
        "schemaVersion": "1.0",
        "graphVersion": f"benchmark-dag-{num_nodes}",
        "createdAt": "2026-10-11T10:00:00+05:30",
        "approvedAt": None,
        "thresholdsM": {
            "watch": 204.5,
            "warning": 205.33,
            "critical": 206.0,
        },
        "nodes": nodes,
        "edges": edges,
    }


def build_synthetic_observation(source_node_id: str = "node-0") -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "observationId": "benchmark-obs-001",
        "eventId": "benchmark-event-001",
        "sourceNodeId": source_node_id,
        "observedAt": "2026-10-11T10:00:00+05:30",
        "receivedAt": "2026-10-11T10:01:00+05:30",
        "levelM": 206.12,
        "confidence": 1.0,
        "mode": "replay",
        "sourceId": "benchmark-synthetic-source",
    }


def run_benchmark(nodes: int, out_degree: int, repeats: int, max_layers: int = 20) -> dict[str, Any]:
    # 1. Build and validate graph and observation
    t_build_start = time.perf_counter()
    raw_graph = build_synthetic_graph(nodes, out_degree, max_layers)
    raw_obs = build_synthetic_observation()
    graph = DependencyGraph.from_dict(raw_graph)
    observation = Observation.from_dict(raw_obs)
    engine = CascadeEngine(graph)
    t_build_end = time.perf_counter()
    build_validation_seconds = t_build_end - t_build_start

    # 2. Warm up once
    warmup_impacts = engine.calculate(observation, "run-warmup")
    if not warmup_impacts:
        raise RuntimeError("Benchmark warmup produced zero impacts; DAG propagation failed")

    # Invariant checks
    if any(imp.resource_type != ResourceType.WATER for imp in warmup_impacts):
        raise RuntimeError("Benchmark warmup returned non-water impact")

    # 3. Time calculation runs
    durations: list[float] = []
    for r in range(repeats):
        t0 = time.perf_counter()
        impacts = engine.calculate(observation, f"run-bench-{r}")
        t1 = time.perf_counter()
        durations.append(t1 - t0)
        if len(impacts) != len(warmup_impacts):
            raise RuntimeError("Impact count varied between repeats; non-deterministic execution detected")

    median_duration = statistics.median(durations)
    max_duration = max(durations)
    min_duration = min(durations)

    return {
        "pythonVersion": sys.version,
        "graphNodeCount": len(graph.nodes),
        "graphEdgeCount": len(graph.edges),
        "outDegree": out_degree,
        "repeatCount": repeats,
        "graphBuildValidationSeconds": round(build_validation_seconds, 6),
        "calculationDurationsSeconds": [round(d, 6) for d in durations],
        "medianCalculationSeconds": round(median_duration, 6),
        "maxCalculationSeconds": round(max_duration, 6),
        "minCalculationSeconds": round(min_duration, 6),
        "impactCount": len(warmup_impacts),
        "benchmarkConfiguration": {
            "nodes": nodes,
            "outDegree": out_degree,
            "repeats": repeats,
            "maxLayers": max_layers,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ripple deterministic cascade simulation-capacity benchmark")
    parser.add_argument("--nodes", type=int, default=1000, help="Number of nodes in the synthetic layered DAG")
    parser.add_argument("--out-degree", type=int, default=5, help="Out-degree per node to next layer")
    parser.add_argument("--repeats", type=int, default=5, help="Number of calculation repeat measurements")
    parser.add_argument("--layers", type=int, default=20, help="Maximum number of DAG layers")

    try:
        args = parser.parse_args()
    except Exception as exc:
        sys.stderr.write(f"Argument parsing error: {exc}\n")
        sys.exit(2)

    if args.nodes < 2 or args.out_degree < 1 or args.repeats < 1:
        sys.stderr.write("Invalid arguments: nodes >= 2, out-degree >= 1, repeats >= 1 required\n")
        sys.exit(2)

    try:
        result = run_benchmark(
            nodes=args.nodes,
            out_degree=args.out_degree,
            repeats=args.repeats,
            max_layers=args.layers,
        )
    except Exception as exc:
        sys.stderr.write(f"Benchmark execution failed: {exc}\n")
        sys.exit(1)

    print(json.dumps(result, indent=2))

    # Performance threshold check for default 1,000-node workload
    if args.nodes == 1000 and result["medianCalculationSeconds"] > 2.0:
        sys.stderr.write(
            f"FAIL: median calculation time ({result['medianCalculationSeconds']}s) exceeded 2.0s threshold\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
