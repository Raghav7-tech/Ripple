# API contract

## Principles

- All payloads include `schemaVersion`.
- All processing runs include `correlationId` and `runId`.
- Times use ISO 8601 with an explicit offset.
- Replay and live records are never indistinguishable.
- Administrative operations require authentication.
- Error responses are structured and safe to show without exposing internals.

## Health

`GET /health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "time": "2026-10-09T22:00:00+05:30"
}
```

## Start replay

`POST /admin/replays/{eventId}/start`

```json
{
  "graphVersion": "yamuna-demo-v1",
  "speed": 60,
  "notificationMode": "preview_only"
}
```

Response:

```json
{
  "runId": "run-001",
  "correlationId": "corr-001",
  "mode": "replay",
  "status": "accepted"
}
```

## Run summary

`GET /runs/{runId}`

```json
{
  "runId": "run-001",
  "mode": "replay",
  "eventId": "yamuna-2023-replay",
  "graphVersion": "yamuna-demo-v1",
  "status": "completed",
  "startedAt": "2026-10-09T22:00:00+05:30",
  "completedAt": "2026-10-09T22:00:01+05:30",
  "impactCount": 7,
  "highestSeverity": "high",
  "containsAssumptions": true
}
```

## Impact explanation

`GET /impacts/{impactId}/explanation`

Impacts are resource-specific. When an upstream trigger propagates across multiple resource lanes (e.g. `water`, `staff`, `medical_supply`), distinct impact records are generated per `(targetNodeId, resourceType)` pair with independent paths, arrival times, confidences, and deterministic identifiers.

```json
{
  "schemaVersion": "1.0",
  "impactId": "impact-a1b2c3d4e5f6",
  "runId": "run-001",
  "target": {
    "nodeId": "hospital-demo-01",
    "name": "Demonstration Hospital"
  },
  "expectedImpactAt": "2026-10-11T10:38:00+05:30",
  "etaMinutes": 38,
  "severity": "critical",
  "confidence": 1.0,
  "resourceType": "water",
  "path": [
    {
      "edgeId": "e-water-01",
      "from": "gauge-demo-01",
      "to": "wtp-demo-01",
      "delayMinutes": 8,
      "confidence": 1.0,
      "evidenceStatus": "demonstration",
      "assumption": "Fictional water intake flood delay.",
      "resourceType": "water"
    },
    {
      "edgeId": "e-water-02",
      "from": "wtp-demo-01",
      "to": "zone-demo-01",
      "delayMinutes": 18,
      "confidence": 1.0,
      "evidenceStatus": "demonstration",
      "assumption": "Fictional treatment plant to distribution zone delay.",
      "resourceType": "water"
    },
    {
      "edgeId": "e-water-03",
      "from": "zone-demo-01",
      "to": "hospital-demo-01",
      "delayMinutes": 12,
      "confidence": 1.0,
      "evidenceStatus": "demonstration",
      "assumption": "Fictional municipal water pipe supply failure delay.",
      "resourceType": "water"
    }
  ],
  "assumptions": [
    "Fictional demonstration hospital asset for multi-resource cascade testing.",
    "Fictional municipal water pipe supply failure delay.",
    "Fictional treatment plant to distribution zone delay.",
    "Fictional water intake flood delay."
  ],
  "actionCode": "VERIFY_RESERVE_AND_PREALERT_TANKER"
}
```

A companion staff impact for the same facility during the same event run produces an independent impact record:

```json
{
  "schemaVersion": "1.0",
  "impactId": "impact-f7e8d9c0b1a2",
  "runId": "run-001",
  "target": {
    "nodeId": "hospital-demo-01",
    "name": "Demonstration Hospital"
  },
  "expectedImpactAt": "2026-10-11T10:30:00+05:30",
  "etaMinutes": 30,
  "severity": "critical",
  "confidence": 1.0,
  "resourceType": "staff",
  "path": [
    {
      "edgeId": "e-staff-01",
      "from": "gauge-demo-01",
      "to": "corridor-demo-01",
      "delayMinutes": 10,
      "confidence": 1.0,
      "evidenceStatus": "demonstration",
      "assumption": "Fictional road waterlogging delay affecting staff transit.",
      "resourceType": "staff"
    },
    {
      "edgeId": "e-staff-02",
      "from": "corridor-demo-01",
      "to": "staff-pool-demo-01",
      "delayMinutes": 15,
      "confidence": 1.0,
      "evidenceStatus": "demonstration",
      "assumption": "Fictional staff dispatch and rerouting delay.",
      "resourceType": "staff"
    },
    {
      "edgeId": "e-staff-03",
      "from": "staff-pool-demo-01",
      "to": "hospital-demo-01",
      "delayMinutes": 5,
      "confidence": 1.0,
      "evidenceStatus": "demonstration",
      "assumption": "Fictional final transit delay to hospital.",
      "resourceType": "staff"
    }
  ],
  "assumptions": [
    "Fictional demonstration hospital asset for multi-resource cascade testing.",
    "Fictional final transit delay to hospital.",
    "Fictional road waterlogging delay affecting staff transit.",
    "Fictional staff dispatch and rerouting delay."
  ],
  "actionCode": "VERIFY_RESERVE_AND_PREALERT_TANKER"
}
```

### Backward compatibility

- Legacy graphs where edge objects omit `resourceType` default to `"water"`.
- Legacy impact records where `resourceType` is absent parse into domain models with `"water"`.
- `schemaVersion` remains `"1.0"`. The `resourceType` property is additive and optional in JSON schemas to maintain backward-compatibility with existing data.

### Modeling boundary and safety disclaimer

- The engine evaluates rule-based dependency cascade graphs and deterministic propagation delays; it is **not** a hydrodynamic flood model, water-balance model, or official forecast.
- Multi-resource test branches and facilities are synthetic demonstration inputs.
- Outputs must not be used for real-world emergency decision-making without domain-operator verification.

## Approve alert

`POST /admin/alerts/{impactId}/approve`

```json
{
  "channel": "email",
  "recipientGroupId": "demo-reviewers",
  "language": "hi-en",
  "expectedRunId": "run-001"
}
```

The server must reject approval when the run is stale, incomplete, mismatched, or already superseded.

## Shortage forecast

`POST /forecasts/shortage`

```json
{
  "features": {
    "facilityId": "hospital-north-01",
    "reserveHours": 18,
    "expectedSupplyM3h": 42,
    "expectedDemandM3h": 70,
    "riverRiseMPerHour": 0.31,
    "upstreamDisruptionProbability": 0.84,
    "criticality": 1,
    "horizonHours": 48
  }
}
```

The current response uses `explainable-baseline-v1` and includes `productionReady: false`. A future trained model must implement this same contract and pass the evaluation gates in [`ml/MODEL_CARD.md`](../ml/MODEL_CARD.md).

## Stateless modeling simulation

`POST /modeling/simulate`

Stateless execution of the deterministic `CascadeEngine` over an assumption-labelled `DependencyGraph` and `Observation`. This sandbox route has no persistence or side-effects: no DynamoDB writes, S3 writes, SNS alerts, or external model calls.

### Limits
- Maximum graph nodes: 500
- Maximum graph edges: 2,500
- Maximum request payload size: 1 MiB

### Request

```json
{
  "runId": "sim-run-001",
  "graph": { /* DependencyGraph JSON */ },
  "observation": { /* Observation JSON */ }
}
```

### Response

```json
{
  "schemaVersion": "1.0",
  "runId": "sim-run-001",
  "observationId": "obs-001",
  "severity": "critical",
  "impacts": [ /* ImpactResult array */ ],
  "correlationId": "corr-12345",
  "engineCalculationMs": 0.421
}
```

Note: `engineCalculationMs` isolates the execution time of `CascadeEngine.calculate(...)` on the server, excluding network transit, JSON serialization, and schema parsing.

## Errors

```json
{
  "error": {
    "code": "GRAPH_VALIDATION_FAILED",
    "message": "The selected graph contains an edge with a missing target node.",
    "correlationId": "corr-001",
    "retryable": false
  }
}
```
