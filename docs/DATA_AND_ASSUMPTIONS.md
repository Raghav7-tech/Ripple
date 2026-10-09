# Data provenance and assumptions

## Why this matters

Ripple's output is only as trustworthy as its observations and dependency edges. A polished map must never hide synthetic or weakly supported data.

## Evidence classes

| Class | Meaning | UI label |
|---|---|---|
| Verified | Directly supported by an authoritative source | Verified |
| Inferred | Reasonable relationship derived from one or more sources | Inferred |
| Demonstration | Synthetic value used to exercise the prototype | Demo assumption |

## Required source metadata

Every observation, node, and dependency edge should be traceable to a source record containing:

```json
{
  "sourceId": "source-001",
  "name": "Source name",
  "publisher": "Publishing organisation",
  "url": "https://example.org/source",
  "publishedAt": "2023-07-13T00:00:00+05:30",
  "retrievedAt": "2026-10-09T00:00:00+05:30",
  "licenseOrTerms": "Public report; verify reuse terms",
  "notes": "Relevant page or transformation"
}
```

## Freshness policy

- Replay data is historical and must always display `Replay`.
- Live observations require an observation timestamp and retrieval timestamp.
- The UI must mark data stale after a configured source-specific interval.
- Stale data may be displayed but must not silently trigger a new notification.

## Graph governance

Each graph version should include:

- Unique version
- Created and approved timestamps
- Author or team role
- Source registry version
- Number of verified, inferred, and demonstration edges
- Validation result
- Change summary from the previous version

## Validation rules

- Node and edge IDs are unique.
- Every edge references existing nodes.
- Delays are non-negative and bounded.
- Capacity factors use a documented range.
- Confidence is between 0 and 1.
- Each inferred or demonstration edge has an assumption note.
- Cycles are either forbidden or explicitly supported by the algorithm.
- Coordinates are real and sourced, or `null`; never use plausible fake coordinates.

## Privacy rules

- Do not store staff home addresses.
- Model workforce availability by aggregate zone if needed.
- Use test email addresses and verified recipients.
- Keep phone numbers outside committed sample data.
- Remove personal identifiers from logs and screenshots.

## Initial source register

| Source | Planned use | Limitation |
|---|---|---|
| NIDM Delhi flood report | Historical event and treatment-plant disruption | Not a machine-readable time series |
| CWC forecast portal or reports | River forecast context | Automated access must be verified |
| Open-Meteo | Rainfall context | Rainfall is not a river gauge measurement |
| Team-authored graph | Demonstration dependencies | Must be visibly labelled and reviewed |
