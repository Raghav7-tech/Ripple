# Contributing to Ripple

Ripple deals with disaster and essential-service information, so correctness and transparency matter more than feature count.

## Before starting

1. Read the [project guide](docs/PROJECT_GUIDE_HINGLISH.md).
2. Check [PROJECT_STATUS.md](PROJECT_STATUS.md) and the open issues.
3. Keep the hackathon MVP focused on one end-to-end Yamuna replay.
4. Open an issue before introducing a new AWS service, data source, or large dependency.

## Branches and commits

- Use a short branch name such as `feature/cascade-engine` or `docs/data-provenance`.
- Keep commits focused and use an imperative message, for example `Add graph validation tests`.
- Never commit credentials, phone numbers, private location data, or unlicensed datasets.

## Pull-request checklist

- [ ] The change solves a documented problem.
- [ ] Planned behavior is not described as implemented behavior.
- [ ] Tests cover success, stale-data, malformed-input, and failure cases where relevant.
- [ ] New data includes its source, timestamp, license or usage terms, and transformation notes.
- [ ] Alerts preserve engine-produced facts and numbers.
- [ ] Accessibility and mobile behavior have been considered for UI changes.
- [ ] Documentation and PROJECT_STATUS have been updated.
- [ ] No secret or personal information is present in the diff.

## Data contribution rules

Every dataset or dependency edge must state whether it is verified, inferred, or a demonstration assumption. See [docs/DATA_AND_ASSUMPTIONS.md](docs/DATA_AND_ASSUMPTIONS.md).

## Code-quality expectations

- Prefer small deterministic functions for hazard and cascade logic.
- Pass a correlation ID through ingestion, calculation, storage, API, and alert delivery.
- Keep LLM output outside the decision path.
- Reject unknown schema versions rather than guessing.
- Log structured events without personal or secret data.
