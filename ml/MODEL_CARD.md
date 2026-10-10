# Ripple shortage prediction — model card

## Current status

`explainable-baseline-v1` is an untrained, hand-authored baseline. It exists to make the feature contract, safety behavior, UI integration, and evaluation pipeline executable before a real labeled dataset is available. Its output always includes `productionReady: false`.

It must not be presented as a trained ML forecast or used for public-safety decisions.

## Intended trained model

The first trained candidate should predict two related outputs for each facility:

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
- false-negative rate for hospitals and shelters;
- performance by facility type, zone, season, and sensor-quality band;
- comparison with the deterministic baseline;
- backtest reproducing every input version and model artifact.

Thresholds must be agreed with emergency-response operators. A model that is accurate on average but misses critical facilities is not acceptable.

## Serving and safety

The production adapter will implement the same `ShortagePredictor` contract as the baseline. Ripple must store the model version, feature timestamp, prediction, uncertainty, and top contributing factors with each run. Prediction text is advisory; the graph engine and human approval gate remain authoritative for notifications.
