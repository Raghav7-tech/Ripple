# Ripple shortage prediction — model card

## Current status

Ripple ships two interchangeable implementations of the `ShortagePredictor` contract:

- `explainable-baseline-v1`: an untrained, hand-authored fallback.
- `shortage-logistic-synthetic-v1`: a dependency-free logistic classifier trained by `ml/scripts/train_model.py` from `data/training/synthetic_shortage_v1.csv`.

Both return `productionReady: false`. The trained artifact is a software-pipeline candidate, not a validated operational forecast.

## Development dataset and result

The deterministic generator produces 2,160 observations in 36 simulated disruption events for localities, schools, colleges, restaurants, and healthcare facilities. There are 1,119 positive labels (51.8%). The train/validation/test split is grouped by event, not random rows.

On the synthetic test partition, `shortage-logistic-synthetic-v1` recorded precision 0.9235, recall 0.9235, F1 0.9235, Brier score 0.0690, and AUPRC 0.9834. These figures measure recovery of the generator's own relationships and must never be quoted as real-world accuracy. Reproducible details are stored in `ml/reports/shortage_logistic_v1.metrics.json`.

## Intended operational model

The first operationally evaluated model should predict two related outputs for each entity:

1. Probability of a water shortage inside a chosen horizon (classification).
2. Hours until usable reserve falls below the facility's minimum threshold (survival or regression estimate).

Candidate features:

- recent river level, rate of rise, and forecast quantiles;
- treatment-plant intake and production capacity;
- zone-level flow and pressure;
- facility reserve volume and storage telemetry;
- hourly/weekly demand seasonality;
- planned maintenance and outage state;
- cascade-path confidence and upstream disruption probability;
- weather and heat-demand indicators.

Do not train on facility names, free-text operator notes, or post-event fields that would leak the target.

## Labels and split strategy

- Positive label: verified reserve falling below the reviewed minimum within the prediction horizon.
- Time label: time from feature timestamp to the verified threshold crossing.
- Split by event and time, never random rows, so observations from one flood do not appear in both training and test sets.
- Keep a final, untouched disaster-event holdout.

## Required evaluation gates

- precision/recall and area under the precision-recall curve;
- calibration error and reliability diagram;
- early-warning lead-time distribution;
- false-negative rate for high-criticality entities;
- performance by entity type, zone, season, and sensor-quality band;
- comparison with the deterministic baseline;
- backtest reproducing every input version and model artifact.

Thresholds must be agreed with emergency-response operators. A model that is accurate on average but misses critical facilities is not acceptable.

## Serving and safety

The artifact adapter implements the same contract as the baseline and requires no third-party runtime package. Ripple must store the model version, feature timestamp, prediction, uncertainty, and top contributing factors with each run. Prediction text is advisory; the graph engine and human approval gate remain authoritative for notifications. Retraining requires reviewed utility/facility labels, calibration, subgroup evaluation, and an explicit production approval record.
