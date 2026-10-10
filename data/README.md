# Data directory

This directory contains versioned JSON Schemas, a controlled replay, an assumption-labelled dependency graph, a source register, and a shortage-forecast request fixture.

```text
data/
├── schemas/   observation, dependency graph, and impact result contracts
├── samples/   synthetic replay, graph, and forecast inputs
└── sources/   provenance and operational-use register
```

Every included value is demonstration data. `operationalUseAllowed` is false in the source register. A real deployment must replace these fixtures with reviewed data and preserve the source ID, observed time, received time, and graph version in every run.

Do not commit private, scraped-without-permission, or personally identifiable data. Detailed rules are in [`docs/DATA_AND_ASSUMPTIONS.md`](../docs/DATA_AND_ASSUMPTIONS.md).
