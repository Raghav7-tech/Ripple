# Infrastructure

[`template.yaml`](template.yaml) is an AWS SAM definition for the first deployable backend slice. It provisions:

- encrypted, versioned S3 replay storage;
- DynamoDB run and impact persistence;
- HTTP API routes;
- a Cognito operator pool and JWT protection on administrative routes;
- replay, cascade, forecast, advisory, read API, and approval Lambda functions;
- encrypted SNS and SQS resources;
- JSON Lambda logs and X-Ray tracing;
- a disabled EventBridge Scheduler placeholder.

The scheduled ingestion placeholder is deliberately disabled until an authorised source is configured. SNS delivery is also disabled by default and returns a preview after validating approval. Set `EnableAlertDelivery=true` only for a reviewed demo account with a confirmed SNS subscription.

Deployment outline:

```bash
sam build --template-file infrastructure/template.yaml
sam deploy --guided
aws s3 cp data/samples/yamuna-2023-replay.json s3://<ReplayBucketName>/replays/yamuna-2023-demo.json
aws s3 cp data/samples/delhi-water-demo-graph.json s3://<ReplayBucketName>/graphs/delhi-water-demo-v1.json
```

Copy the `ApiUrl` output into `frontend/.env.local` as `VITE_API_BASE_URL`, then rebuild the frontend. AWS SAM CLI is required for template validation and deployment; it is not bundled with this repository.
