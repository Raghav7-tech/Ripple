# Project status

Last verified: 10 October 2026

## Current state

| Area | Status | Evidence |
|---|---|---|
| Problem definition | Documented | README and project guide |
| Demo scenario | Documented | Yamuna 2023 replay plan |
| Architecture | Planned | Architecture document and diagrams |
| Data contracts | Specified | Data and API documentation |
| Backend implementation | Not started in this repository | No application code present |
| Frontend implementation | Interactive prototype implemented | React application in `frontend/`; production build verified locally |
| Infrastructure as code | Not started in this repository | No SAM or CDK files present |
| Automated tests | Not started | Production type-check and build pass; no dedicated test suite yet |
| AWS deployment | Not verified | No deployment evidence or URL present |
| Demo video | Not verified | No video link present |

## Definition of done for the hackathon MVP

- [ ] Recorded river-level event stored with provenance
- [ ] Dependency graph loads successfully
- [ ] Cascade engine returns an explainable result
- [x] Frontend prototype displays dependency surface, timeline, severity, and confidence
- [x] Frontend prototype renders advisory content in English and Hindi
- [ ] Deterministic advisory fallback works without Bedrock
- [ ] SNS email reaches a verified recipient
- [ ] CloudWatch logs contain a correlation ID for the full run
- [ ] Core unit and replay tests pass
- [ ] Infrastructure deploys from source control
- [ ] Public deployment URL is documented
- [ ] Three-minute demo video is recorded and linked

Update this file only with verifiable evidence. Do not mark planned features as complete.
