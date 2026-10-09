# Infrastructure

Use AWS SAM or AWS CDK for reproducible deployment. The first implementation should provision only the services required by the MVP:

- S3
- EventBridge Scheduler
- Lambda
- DynamoDB
- API Gateway
- Amplify Hosting or equivalent static hosting
- SNS email
- CloudWatch
- SQS dead-letter queue
- Optional Bedrock model access for translation or simplification

Keep IAM permissions per function, enable encryption and structured logs, and expose outputs such as API URL, dashboard URL, and table names. Add budget alarms before enabling paid or high-volume services.
