# Backend

This directory is reserved for the ingestion, cascade, advisory, and API services.

Recommended initial modules:

```text
backend/
├── ingestion/       Validate and persist observations
├── cascade/         Deterministic graph propagation
├── advisory/        Template and optional translation pipeline
├── api/             Read-only results and controlled replay endpoints
└── tests/           Unit, contract, replay, and failure tests
```

The cascade engine must not depend on an LLM. Use the versioned contracts in `docs/API_CONTRACT.md` and `docs/DATA_AND_ASSUMPTIONS.md` before implementing handlers.
