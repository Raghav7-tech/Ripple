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
- Delays are non-negative integers bounded between 0 and 10,080 minutes.
- Confidence is between 0 and 1.
- Each inferred or demonstration edge has an assumption note.
- Graph must be acyclic (DAG). Cycles are strictly forbidden and rejected at graph load time.
- Coordinates are real and sourced, or `null`; never use plausible fake coordinates.
- Edge `resourceType` must be one of `water`, `staff`, or `medical_supply`. Missing `resourceType` defaults to `water` for backward compatibility.

## Resource-aware propagation rules

1. **Independent resource lanes**: At the source node, propagation begins independently for each resource type present on outgoing edges from that node.
2. **Lane isolation**: Once a lane begins with a specific resource type, traversal is strictly restricted to edges matching that exact resource type. Water paths cannot transition onto staff or medical supply edges, and vice-versa.
3. **Route selection**:
   - Earliest arrival: the path with the minimum cumulative `delayMinutes` is selected.
   - Confidence tie-break: if arrival times are equal, the candidate path with higher multiplied confidence is selected.
   - Deterministic tie-break: if arrival time and multiplied confidence are identical, the route with the lexicographically smallest sequence of edge IDs is selected. This guarantees determinism irrespective of edge ordering in the JSON input.
4. **Target impacts**: Impacts are emitted per `(targetNodeId, resourceType)`. A facility reachable by both water and staff receives distinct impact records with distinct IDs, causal paths, arrival times, and action codes.
5. **Notification filter**: Intermediate nodes marked with `notify: false` are traversed during cascade search but are never emitted as impact targets.
6. **Multiplied confidence**: Impact confidence is calculated as `observation.confidence × product(edge.confidence)` along the selected path, rounded to 2 decimal places in public outputs.

## Fixture status and operational boundaries

- **Synthetic demonstration inputs**: The multi-resource graph (`multi-resource-demo-graph.json`) and trigger (`multi-resource-trigger.json`) are fully synthetic test fixtures with fictional delays, node identities, and facilities.
- **Engineered test paths**: The multi-resource test branches (`water`, `staff`, `medical_supply`) are engineered algorithmic test paths to verify propagation mechanics, not empirical evidence that a real Delhi hospital depends on those exact routes.
- **Historical replay boundary**: The Yamuna 2023 demo graph (`delhi-water-demo-graph.json`) uses illustrative demonstration edges. Historical-looking timestamps in the replay fixture do not convert synthetic graph edges into verified government utility observations.
- **Rule-based cascade vs physical modeling**: The engine calculates deterministic, rule-based cascade dependencies over user-provided DAGs. It is **not** a hydrodynamic flood simulation, hydraulic pipe model, water-balance model, or official meteorological forecast.
- **Unsuitable for emergency action**: These outputs are decision-support prototypes and are strictly unsuitable for real-world emergency decisions without reviewed graph data and operator validation.

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
