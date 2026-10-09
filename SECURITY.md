# Security policy

## Reporting a vulnerability

Do not open a public issue for credentials, data exposure, unauthorised alert delivery, or a vulnerability that could affect an AWS deployment. Contact the repository owner privately through their GitHub profile and include:

- A concise description
- Reproduction steps
- Affected component
- Potential impact
- Suggested mitigation, if known

## Security boundaries

- Never commit AWS credentials or local `.env` files.
- Use least-privilege IAM roles for each service.
- Protect administrative replay and notification endpoints.
- Require human approval before any production-scale notification.
- Do not store personal staff locations or unnecessary phone numbers.
- Encrypt data in transit and use AWS-managed encryption at rest where available.
- Treat external feeds, uploaded replay files, and LLM output as untrusted input.
- Validate all event and API payloads against versioned schemas.

## Demo environment

The hackathon environment should use synthetic or public data and verified test recipients. It must not imply endorsement by a government agency or claim to be an official warning service.
