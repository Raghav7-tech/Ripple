param(
  [string]$StackName = "ripple-demo",
  [string]$Region = "ap-south-1",
  [ValidateSet("true", "false")]
  [string]$EnableBedrockAdvisory = "true",
  [string]$BedrockModelId = "amazon.nova-micro-v1:0"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$template = Join-Path $repoRoot "infrastructure\template.yaml"

foreach ($command in @("aws", "sam")) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    throw "$command CLI is required. Install and authenticate it before deployment."
  }
}

$identity = aws sts get-caller-identity --region $Region | ConvertFrom-Json
Write-Host "Deploying as AWS account $($identity.Account) in $Region"

sam validate --lint --template-file $template
sam build --template-file $template
sam deploy `
  --stack-name $StackName `
  --region $Region `
  --resolve-s3 `
  --capabilities CAPABILITY_IAM `
  --confirm-changeset `
  --parameter-overrides `
    "EnvironmentName=demo" `
    "EnableAlertDelivery=false" `
    "EnableBedrockAdvisory=$EnableBedrockAdvisory" `
    "BedrockModelId=$BedrockModelId"

$outputs = aws cloudformation describe-stacks `
  --stack-name $StackName `
  --region $Region `
  --query "Stacks[0].Outputs" | ConvertFrom-Json
$outputMap = @{}
foreach ($item in $outputs) { $outputMap[$item.OutputKey] = $item.OutputValue }

aws s3 cp (Join-Path $repoRoot "data\samples\yamuna-2023-replay.json") "s3://$($outputMap.ReplayBucketName)/replays/yamuna-2023-demo.json" --region $Region
aws s3 cp (Join-Path $repoRoot "data\samples\delhi-water-demo-graph.json") "s3://$($outputMap.ReplayBucketName)/graphs/yamuna-demo-v1.json" --region $Region
aws s3 cp (Join-Path $repoRoot "data\training\synthetic_shortage_v1.csv") "s3://$($outputMap.TrainingDataBucketName)/datasets/synthetic_shortage_v1.csv" --region $Region
aws s3 cp (Join-Path $repoRoot "data\training\synthetic_shortage_v1.metadata.json") "s3://$($outputMap.TrainingDataBucketName)/datasets/synthetic_shortage_v1.metadata.json" --region $Region
aws s3 cp (Join-Path $repoRoot "backend\ripple\model_artifacts\shortage_logistic_v1.json") "s3://$($outputMap.TrainingDataBucketName)/models/shortage_logistic_v1.json" --region $Region

Write-Host "Ripple deployment complete."
$outputs | Format-Table OutputKey, OutputValue
