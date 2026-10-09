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

```json
{
  "impactId": "impact-001",
  "target": {
    "nodeId": "hospital-demo-01",
    "name": "Demonstration Hospital"
  },
  "expectedImpactAt": "2023-07-13T17:00:00+05:30",
  "severity": "high",
  "confidence": 0.55,
  "path": [
    {
      "from": "gauge-delhi-railway-bridge",
      "to": "wtp-wazirabad",
      "delayMinutes": 60,
      "evidenceStatus": "verified"
    },
    {
      "from": "wtp-wazirabad",
      "to": "zone-demo-01",
      "delayMinutes": 120,
      "evidenceStatus": "demonstration"
    }
  ],
  "assumptions": ["Supply-zone delay is demonstration data"]
}
```

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
