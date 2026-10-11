# Infrastructure

[`template.yaml`](template.yaml) is an AWS SAM definition for the first deployable backend slice. It provisions:

- encrypted, versioned S3 replay and ML training storage;
- DynamoDB run and impact persistence;
- HTTP API routes;
- a Cognito operator pool and JWT protection on administrative routes;
- replay, cascade, forecast, advisory, read API, and approval Lambda functions;
- encrypted SNS and SQS resources;
- optional Amazon Bedrock advisory rewriting with locked-fact validation and deterministic fallback;
- JSON Lambda logs and X-Ray tracing;
- a disabled EventBridge Scheduler placeholder.

The scheduled ingestion placeholder is deliberately disabled until an authorised source is configured. SNS delivery is also disabled by default and returns a preview after validating approval. Set `EnableAlertDelivery=true` only for a reviewed demo account with a confirmed SNS subscription.

Deployment outline (PowerShell):

```powershell
Copy-Item infrastructure/samconfig.toml.example infrastructure/samconfig.toml
./scripts/deploy-aws.ps1
```

Equivalent manual commands:

```bash
sam build --template-file infrastructure/template.yaml
sam deploy --guided
aws s3 cp data/samples/yamuna-2023-replay.json s3://<ReplayBucketName>/replays/yamuna-2023-demo.json
aws s3 cp data/samples/delhi-water-demo-graph.json s3://<ReplayBucketName>/graphs/delhi-water-demo-v1.json
aws s3 cp data/training/synthetic_shortage_v1.csv s3://<TrainingDataBucketName>/datasets/synthetic_shortage_v1.csv
```

`EnableBedrockAdvisory` defaults to `false`; enable it only in a supported region after model access is available. Bedrock never calculates risk—it may only rewrite a locked advisory, and invalid output falls back to deterministic copy. Copy the `ApiUrl` output into `frontend/.env.local` as `VITE_API_BASE_URL`, then rebuild the frontend. AWS CLI, authenticated credentials, and AWS SAM CLI are required; they are not bundled with this repository.
