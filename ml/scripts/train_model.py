from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


FEATURE_ORDER = [
    "reserveHours",
    "supplyDemandGapRatio",
    "riverRiseMPerHour",
    "upstreamDisruptionProbability",
    "criticality",
    "horizonHours",
]


def _features(row: dict[str, str]) -> list[float]:
    demand = float(row["expected_demand_m3h"])
    supply = float(row["expected_supply_m3h"])
    return [
        float(row["reserve_hours"]),
        max(0.0, (demand - supply) / demand),
        float(row["river_rise_m_per_hour"]),
        float(row["upstream_disruption_probability"]),
        float(row["criticality"]),
        float(row["horizon_hours"]),
    ]


def _label(row: dict[str, str]) -> int:
    return 1 if row["shortage_within_horizon"].lower() == "true" else 0


def _split_groups(groups: Iterable[str]) -> dict[str, str]:
    ordered = sorted(set(groups), key=lambda value: hashlib.sha256(value.encode()).hexdigest())
    train_end = max(1, int(len(ordered) * 0.7))
    validation_end = max(train_end + 1, int(len(ordered) * 0.85))
    return {
        group: "train" if index < train_end else "validation" if index < validation_end else "test"
        for index, group in enumerate(ordered)
    }


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def _metrics(labels: list[int], probabilities: list[float], threshold: float = 0.5) -> dict[str, float | int]:
    predictions = [value >= threshold for value in probabilities]
    tp = sum(label == 1 and prediction for label, prediction in zip(labels, predictions, strict=True))
    fp = sum(label == 0 and prediction for label, prediction in zip(labels, predictions, strict=True))
    fn = sum(label == 1 and not prediction for label, prediction in zip(labels, predictions, strict=True))
    tn = len(labels) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    brier = sum((probability - label) ** 2 for label, probability in zip(labels, probabilities, strict=True)) / len(labels)
    ranked = sorted(zip(probabilities, labels, strict=True), reverse=True)
    positives = sum(labels)
    prior_recall = 0.0
    prior_precision = 1.0
    area = 0.0
    running_tp = 0
    running_fp = 0
    for _, label in ranked:
        running_tp += label
        running_fp += 1 - label
        recall_point = running_tp / positives if positives else 0.0
        precision_point = running_tp / (running_tp + running_fp)
        area += (recall_point - prior_recall) * ((precision_point + prior_precision) / 2)
        prior_recall = recall_point
        prior_precision = precision_point
    return {
        "rows": len(labels),
        "positives": positives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
        "brierScore": round(brier, 4),
        "areaUnderPrecisionRecall": round(area, 4),
        "truePositives": tp,
        "falsePositives": fp,
        "falseNegatives": fn,
        "trueNegatives": tn,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the dependency-free Ripple logistic shortage candidate.")
    parser.add_argument("--input", type=Path, default=Path("data/training/synthetic_shortage_v1.csv"))
    parser.add_argument("--output", type=Path, default=Path("backend/ripple/model_artifacts/shortage_logistic_v1.json"))
    parser.add_argument("--report", type=Path, default=Path("ml/reports/shortage_logistic_v1.metrics.json"))
    parser.add_argument("--epochs", type=int, default=900)
    parser.add_argument("--learning-rate", type=float, default=0.035)
    args = parser.parse_args()

    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("training dataset is empty")
    split_for = _split_groups(row["split_group"] for row in rows)
    data = [(_features(row), _label(row), split_for[row["split_group"]]) for row in rows]
    train = [(features, label) for features, label, split in data if split == "train"]
    means = [sum(features[index] for features, _ in train) / len(train) for index in range(len(FEATURE_ORDER))]
    scales = []
    for index, mean in enumerate(means):
        variance = sum((features[index] - mean) ** 2 for features, _ in train) / len(train)
        scales.append(max(math.sqrt(variance), 1e-6))

    standardized = [
        ([((value - means[index]) / scales[index]) for index, value in enumerate(features)], label, split)
        for features, label, split in data
    ]
    train_standardized = [(features, label) for features, label, split in standardized if split == "train"]
    positive_count = sum(label for _, label in train_standardized)
    negative_count = len(train_standardized) - positive_count
    positive_weight = len(train_standardized) / (2 * positive_count) if positive_count else 1.0
    negative_weight = len(train_standardized) / (2 * negative_count) if negative_count else 1.0
    weights = [0.0] * len(FEATURE_ORDER)
    bias = 0.0
    rng = random.Random(19)
    for epoch in range(args.epochs):
        rng.shuffle(train_standardized)
        gradient = [0.0] * len(weights)
        bias_gradient = 0.0
        for features, label in train_standardized:
            probability = _sigmoid(bias + sum(weight * value for weight, value in zip(weights, features, strict=True)))
            sample_weight = positive_weight if label else negative_weight
            error = (probability - label) * sample_weight
            bias_gradient += error
            for index, value in enumerate(features):
                gradient[index] += error * value
        rate = args.learning_rate / (1 + epoch / 600)
        count = len(train_standardized)
        bias -= rate * bias_gradient / count
        for index in range(len(weights)):
            weights[index] -= rate * ((gradient[index] / count) + 0.002 * weights[index])

    split_metrics: dict[str, dict[str, float | int]] = {}
    for split in ("train", "validation", "test"):
        subset = [(features, label) for features, label, item_split in standardized if item_split == split]
        probabilities = [_sigmoid(bias + sum(weight * value for weight, value in zip(weights, features, strict=True))) for features, _ in subset]
        split_metrics[split] = _metrics([label for _, label in subset], probabilities)

    artifact = {
        "schemaVersion": "1.0",
        "modelType": "logistic_regression",
        "modelVersion": "shortage-logistic-synthetic-v1",
        "createdAt": datetime.now(UTC).isoformat(),
        "featureOrder": FEATURE_ORDER,
        "means": [round(value, 8) for value in means],
        "scales": [round(value, 8) for value in scales],
        "weights": [round(value, 8) for value in weights],
        "bias": round(bias, 8),
        "classificationThreshold": 0.5,
        "training": {
            "datasetId": "ripple-synthetic-shortage-v1",
            "rowCount": len(rows),
            "eventSplit": "grouped-by-event-70-15-15",
            "syntheticShare": 1.0,
            "metrics": split_metrics,
        },
        "productionReady": False,
        "limitations": [
            "Trained entirely on assumption-labelled synthetic entity rows.",
            "Must be retrained and calibrated on verified shortage timestamps before operational use.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(json.dumps(artifact["training"], indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["training"], indent=2))


if __name__ == "__main__":
    main()
