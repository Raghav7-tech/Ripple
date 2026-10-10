# Backend

This directory contains Ripple's dependency-free deterministic domain core and AWS Lambda entry points.

```text
backend/
├── ripple/          Contracts, graph traversal, replay, forecast baseline, persistence adapter
├── functions/       API, replay, cascade, forecast, advisory, and approval Lambdas
└── tests/           Validation, regression, advisory, forecast, and handler tests
```

The cascade engine does not depend on an LLM. Advisory facts are locked by the engine, and outbound delivery requires explicit approval. The shortage predictor currently implements an honest, untrained baseline contract; see [`ml/MODEL_CARD.md`](../ml/MODEL_CARD.md).

Run the tests from the repository root:

```bash
python -m unittest discover -s backend/tests -t backend -v
```

Run the complete local replay and print its JSON result:

```bash
python -m backend.ripple.replay data/samples/yamuna-2023-replay.json data/samples/delhi-water-demo-graph.json
```

The Lambda adapters import the same `ripple` package because `backend/` is the SAM `CodeUri`; tests use `backend/` as their top-level import directory.
