# Roadmap

## Milestone 0 Documentation foundation

- [x] Project positioning
- [x] Planned architecture
- [x] Data and safety contracts
- [x] API outline
- [x] Demo plan
- [ ] Owner review and approval

## Milestone 1 Deterministic core

- [x] Observation schema and validator
- [x] Dependency graph schema and validator
- [x] Earliest-impact cascade engine
- [x] Severity and confidence rules
- [x] Unit tests
- [x] Fixed replay regression test

## Milestone 2 AWS backend

- [x] S3 replay storage defined in SAM
- [x] Disabled EventBridge Scheduler placeholder defined
- [x] Replay and cascade Lambda source implemented
- [x] DynamoDB persistence adapter and table defined
- [x] API Gateway routes defined
- [x] Structured CloudWatch logs configured
- [x] SQS dead-letter queue defined
- [ ] Deploy and verify the SAM stack in AWS

## Milestone 3 User experience

- [x] Replay controls
- [x] Dependency surface
- [x] Accessible impact list
- [x] Timeline
- [x] Why this alert view
- [x] English and Hindi advisory preview
- [x] Approval-gated backend handler (delivery disabled by default)

## Milestone 4 Alerts and demo

- [ ] SNS email subscription
- [x] Deterministic template
- [ ] Optional Bedrock translation
- [x] Fact-lock validation
- [ ] End-to-end rehearsals
- [ ] Three-minute recording
- [ ] Deployment and video links in README

## Post-hackathon

- Mitigation what-if simulator
- Authorised live data feed
- Graph editing and approval workflow
- Historical calibration
- Train and calibrate the shortage model on reviewed, labelled utility/facility telemetry
- Drought and heatwave models
- Common Alerting Protocol export
- Multi-city graph governance
