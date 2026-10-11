# Data directory

This directory contains versioned JSON Schemas, a controlled replay, an assumption-labelled dependency graph, a source register, and a shortage-forecast request fixture.

```text
data/
├── schemas/   observation, dependency graph, and impact result contracts
├── samples/   synthetic replay, graph, and forecast inputs
├── sources/   provenance and operational-use register
└── training/  synthetic ML rows, verified event anchors, metadata, and review workbook
```

Every included value is demonstration data. `operationalUseAllowed` is false in the source register. Fixtures include single-resource water replay (`yamuna-2023-replay.json`, `delhi-water-demo-graph.json`) and multi-resource cascade fixtures (`multi-resource-demo-graph.json`, `multi-resource-trigger.json`) covering `water`, `staff`, and `medical_supply`. All new multi-resource branches and trigger events are synthetic demonstration inputs. A real deployment must replace these fixtures with reviewed data and preserve the source ID, observed time, received time, and graph version in every run.

`training/synthetic_shortage_v1.csv` is generated development data, while `training/verified_event_anchors.jsonl` contains source-backed event-level facts. The anchors intentionally leave facility shortage timestamps null because the reviewed public sources do not provide those labels. The two evidence classes must not be blended or represented as equivalent.

Do not commit private, scraped-without-permission, or personally identifiable data. Detailed rules are in [`docs/DATA_AND_ASSUMPTIONS.md`](../docs/DATA_AND_ASSUMPTIONS.md).
