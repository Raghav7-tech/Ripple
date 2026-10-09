# Data directory

Only small, redistributable demonstration samples belong in Git.

Suggested structure:

```text
data/
├── samples/
│   ├── observations.json
│   ├── dependency-graph.json
│   └── expected-cascade.json
└── README.md
```

Do not commit private, scraped-without-permission, or personally identifiable data. Every sample must state its source, license or permitted use, retrieval time, transformation, and whether it is verified, inferred, or synthetic.

Detailed contracts are in [docs/DATA_AND_ASSUMPTIONS.md](../docs/DATA_AND_ASSUMPTIONS.md).
