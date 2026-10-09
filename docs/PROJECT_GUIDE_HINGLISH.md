# Ripple Complete Project Guide

## 1 Project ka short answer

**Ripple ek dependency-aware early-warning system hai jo flood ya river-level trigger ko downstream water aur essential-service impact mein translate karta hai.**

Normal flood alert batata hai ki river level dangerous hai. Ripple next question answer karta hai: *iska effect kis treatment plant, supply zone, hospital ya clinic par padega, kitne time mein padega, aur humne ye conclusion kis evidence se nikala?*

Hackathon MVP ka target ek real historical Yamuna flood event ko replay karke ek small, explainable cascade end to end dikhana hai. Product ko national-scale disaster platform ke jaise present nahi karna hai.

## 2 Project status

Repository abhi documentation-first state mein hai. Architecture, contracts, demo flow aur safety boundaries defined hain, lekin backend, frontend, tests aur AWS deployment abhi repository mein implemented nahi hain. `PROJECT_STATUS.md` hi verified status ka source of truth hai.

## 3 Problem statement

Flood forecasting systems hazard ke baare mein useful information dete hain: water level, rainfall, warning category aur expected flood situation. Lekin operational impact aksar multiple dependencies ke through travel karta hai.

Example:

1. River water pumping station mein enter karta hai.
2. Water treatment plant ko production reduce ya stop karna padta hai.
3. Plant se served zones mein water capacity reduce hoti hai.
4. Hospitals, clinics aur vulnerable communities ko tanker, storage ya operational planning karni padti hai.

Is chain ke har step ki alag delay, uncertainty aur evidence quality hoti hai. Ripple ka kaam official hazard warning replace karna nahi, balki us warning ko transparent dependency impact mein convert karna hai.

## 4 One line pitch

**Hazard alerts dikhate hain ki paani kahan badh raha hai. Ripple dikhata hai ki kaunsi services next fail ho sakti hain, kab, aur kyun.**

## 5 Hackathon alignment

Ripple Environmental Hacks ke Heat and Water track mein fit hota hai. Judging ke five important areas hain:

| Criterion | Ripple ka answer |
|---|---|
| Idea and impact | Flood ke secondary water-service impact ko early aur explainable banana |
| Built on AWS | Serverless ingestion, storage, cascade API, dashboard aur alerts |
| Design and usability | Map ke saath list, timeline, bilingual advisory aur causal explanation |
| Execution | Ek recorded event ka working end-to-end replay |
| Demo video | Three-minute product-led story with visible AWS role |

Project ko prize-eligible banane ke liye AWS open-source tool use karna ya AWS par deploy karna required hai. Ripple ka plan actual AWS deployment hai.

## 6 Target users

### Primary operator

City control room, water utility operator, hospital operations team ya disaster-management volunteer jo event ko verify karke targeted advisory approve karta hai.

### Facility user

Hospital ya clinic administrator jise simple answer chahiye: likely impact, expected time, confidence aur next action.

### Public user

Affected zone ka resident jise low-bandwidth, easy Hindi ya English advisory chahiye. Public view mein technical graph details optional honge.

### Developer and reviewer

Team member, mentor ya judge jise source, assumption, graph version, calculation path aur AWS implementation inspect karni hai.

## 7 Demo scenario

Primary demo July 2023 Yamuna flood ka recorded replay hai. Public government material ke according river level 208.66 metres tak gaya, three water treatment plants shut hue, aur Delhi ke large area mein water scarcity hui.

Demo graph deliberately small rahega:

```text
Yamuna gauge observation
  ├── Wazirabad treatment plant
  ├── Chandrawal treatment plant
  └── Okhla treatment plant
          ↓
    selected demonstration supply zones
          ↓
    selected demonstration hospitals or clinics
```

Facility aur supply-zone edges tab tak demonstration assumptions rahenge jab tak reliable public evidence available na ho. UI mein ye label visible hona mandatory hai.

## 8 Product principles

1. **Explainability first:** Har alert ke saath causal path dikhna chahiye.
2. **Facts deterministic:** LLM time, severity, entity ya action invent nahi karega.
3. **Assumptions visible:** Synthetic aur inferred data ko hide nahi karna hai.
4. **Small working scope:** Ek reliable cascade five incomplete modules se better hai.
5. **Human approval:** Prototype mass alert automatically send nahi karega.
6. **Graceful failure:** Data stale ya unavailable ho to system uncertainty show karega, fake confidence nahi.
7. **Privacy minimisation:** Individual staff addresses ya unnecessary phone data store nahi karna hai.

## 9 MVP scope

### Build now

- One recorded Yamuna flood event
- One versioned dependency graph
- River observation ingestion and validation
- Deterministic cascade calculation
- Impact map, ordered list and timeline
- Why this alert explanation
- English and Hindi advisory
- SNS email to verified demo recipient
- CloudWatch logs and basic metrics
- AWS deployment through infrastructure as code
- Automated unit and replay tests

### Do not build for the first demo

- National or multi-city coverage
- Machine-learning flood forecasting
- Auto-discovery of infrastructure dependencies
- Personal doctor or employee commute tracking
- Production WhatsApp integration
- Unreviewed public mass notification
- Mobile native application
- Complex graph database migration

## 10 User journeys

### Operator replay journey

1. Operator historical event select karta hai.
2. System event source, timestamp aur replay label show karta hai.
3. Operator replay start karta hai.
4. Observation danger threshold cross karti hai.
5. Cascade engine affected nodes calculate karta hai.
6. Dashboard map, list aur timeline update karta hai.
7. Operator causal path aur assumptions inspect karta hai.
8. System advisory draft banata hai.
9. Operator verified test recipient ke liye alert approve karta hai.

### Facility alert journey

1. User bilingual email ya dashboard advisory open karta hai.
2. Top section mein severity, expected impact window aur action hota hai.
3. User Why this alert open karke evidence path dekh sakta hai.
4. Stale ya assumption-based information clearly marked hoti hai.

## 11 Functional requirements

| ID | Requirement | MVP acceptance |
|---|---|---|
| FR 1 | Observation ingest | Versioned JSON accept, validate aur store ho |
| FR 2 | Replay | Recorded observations timestamp order mein process hon |
| FR 3 | Graph load | Invalid nodes, duplicate IDs aur broken edges reject hon |
| FR 4 | Cascade | Affected nodes, earliest impact time, severity aur path return ho |
| FR 5 | Explainability | Har result mein source-to-target path available ho |
| FR 6 | Advisory | Engine facts se bilingual draft generate ho |
| FR 7 | Fallback | Bedrock unavailable ho to deterministic template work kare |
| FR 8 | Dashboard | Map ke saath accessible list aur timeline render ho |
| FR 9 | Notification | Verified recipient ko approved email send ho |
| FR 10 | Audit | Event, graph version, calculation aur approval log ho |

## 12 Non functional requirements

- Demo graph ka cascade computation one second se kam.
- Duplicate event processing idempotent ho.
- External request timeout aur retry bounded ho.
- All stored records schema version carry karein.
- Logs structured JSON mein hon aur correlation ID share karein.
- Dashboard mobile viewport aur keyboard navigation support kare.
- Map ke bina bhi same information list ya table mein available ho.
- Data freshness aur confidence user ko visible ho.

## 13 Proposed AWS architecture

### Data ingestion

Recorded JSON S3 mein rahega. EventBridge Scheduler ya controlled replay endpoint ingestion Lambda invoke karega. Live source optional hai; demo reliability recorded replay se aayegi.

### Storage

DynamoDB observations, graph metadata aur impact results store karega. Small graph file S3 ya DynamoDB dono mein possible hai, lekin MVP mein simple, versioned representation choose karna hai.

### Cascade processing

Lambda deterministic graph algorithm run karega. Calculation ka input, graph version aur output audit ke liye persist hoga.

### Dashboard API

API Gateway read endpoints expose karega. Admin replay aur approval endpoints authenticated aur separate honge. Amplify static frontend host kar sakta hai.

### Advisory pipeline

Template composer verified result object banayega. Optional Bedrock call sirf language simplify ya translate karega. Output schema validation fail hone par original deterministic template use hoga.

### Notification

Hackathon ke liye SNS email recommended hai. New SMS accounts sandbox restrictions ke under ho sakte hain aur India routes ke liye additional registration concerns ho sakte hain.

### Operations

CloudWatch logs, metrics aur alarms provide karega. Failed asynchronous events ke liye SQS dead-letter queue use hogi.

## 14 Core data model

### Observation

```json
{
  "schemaVersion": "1.0",
  "eventId": "yamuna-2023-replay",
  "observationId": "obs-001",
  "stationId": "delhi-railway-bridge",
  "observedAt": "2023-07-13T12:00:00+05:30",
  "metric": "water_level_m",
  "value": 208.66,
  "threshold": 205.33,
  "mode": "replay",
  "source": {
    "name": "National Institute of Disaster Management",
    "url": "https://nidm.gov.in/PDF/TrgReports/2023/December/Report_12December2023sp.pdf",
    "retrievedAt": "2026-10-09T00:00:00+05:30"
  }
}
```

### Dependency node

```json
{
  "nodeId": "wtp-wazirabad",
  "nodeType": "water_treatment_plant",
  "name": "Wazirabad Water Treatment Plant",
  "location": { "lat": 0, "lon": 0 },
  "status": "verified_or_demo",
  "sourceRefs": ["source-001"]
}
```

Zero coordinates sirf placeholder explain karne ke liye hain; committed sample mein real verified coordinates ya explicit `null` use hoga, fake coordinate nahi.

### Dependency edge

```json
{
  "edgeId": "edge-001",
  "from": "gauge-delhi-railway-bridge",
  "to": "wtp-wazirabad",
  "resourceType": "flood_exposure",
  "delayMinutes": 60,
  "capacityFactor": 0.75,
  "confidence": 0.8,
  "evidenceStatus": "inferred",
  "sourceRefs": ["source-001"],
  "assumptionNote": "Demo delay pending operational validation"
}
```

### Impact result

```json
{
  "runId": "run-001",
  "graphVersion": "yamuna-demo-v1",
  "targetNodeId": "hospital-demo-01",
  "expectedImpactAt": "2023-07-13T17:00:00+05:30",
  "severity": "high",
  "confidence": 0.55,
  "path": ["gauge", "treatment-plant", "supply-zone", "hospital"],
  "assumptions": ["edge-zone-hospital is demonstration data"]
}
```

## 15 Cascade algorithm

Graph directed aur weighted hoga. Har edge mein delay, capacity factor aur confidence hoga.

1. Trigger node ko observed severity aur time ke saath initialise karo.
2. Earliest-arrival priority queue se outgoing edges process karo.
3. Candidate impact time = current impact time + edge delay.
4. Severity ko explicit resource rule se propagate karo; arbitrary string comparison mat use karo.
5. Path confidence ko conservative rule se combine karo, for example minimum edge confidence.
6. Better earlier path mile to result update karo.
7. Visited state aur path rules se cycles ko infinite processing se roko.
8. Result mein predecessor path store karo for explanation.

MVP graph small hai, isliye normal adjacency-list implementation enough hai. Graph database add karna required nahi.

## 16 Severity and confidence

Severity aur confidence separate concepts hain.

- **Severity:** Expected operational effect kitna serious hai.
- **Confidence:** Evidence aur data quality ke basis par estimate kitna reliable hai.

Example: high-severity impact low-confidence ho sakta hai. UI ko dono show karne chahiye.

Suggested confidence inputs:

- Source authority
- Observation freshness
- Edge verification status
- Graph version age
- Missing data
- Number of assumption-based edges in the path

## 17 Advisory safety contract

Engine ek locked fact object produce karega:

```text
zone, facility, impact window, severity, confidence, action code, source time
```

Bedrock ko instruction milegi ki wo sirf supplied facts ko Hindi ya English mein simple language mein present kare. Model output parse hone ke baad:

1. Required fields validate honge.
2. Numbers aur entity IDs engine output se compare honge.
3. Unsupported text reject hoga.
4. Failure par deterministic template use hoga.

## 18 UI specification

### Dashboard home

- Current mode: Live or Replay
- Source freshness
- Active event summary
- Affected nodes count
- Highest severity
- Last successful processing time

### Impact map and list

- Severity-coded markers
- Equivalent sortable list
- Expected impact time
- Confidence badge
- Verified, inferred or demo label

### Timeline

- Trigger time
- Each predicted dependency impact
- Alert generation and delivery status

### Why this alert

- Full causal path
- Delay at every edge
- Evidence source
- Assumption note
- Graph version
- Calculation run ID

### Operator approval

- Recipient preview
- English and Hindi message
- Deterministic or Bedrock-generated label
- Approve or cancel action
- Audit record

## 19 API outline

Detailed contract `docs/API_CONTRACT.md` mein hai. MVP endpoints:

```text
GET  /health
GET  /events
GET  /events/{eventId}
POST /admin/replays/{eventId}/start
GET  /runs/{runId}
GET  /runs/{runId}/impacts
GET  /impacts/{impactId}/explanation
POST /admin/alerts/{impactId}/approve
```

Admin endpoints authentication ke bina public expose nahi honge.

## 20 Testing strategy

### Unit tests

- Threshold below, equal aur above cases
- One edge aur multiple path graphs
- Cycle detection
- Missing node aur broken edge rejection
- Earliest-arrival selection
- Severity propagation
- Confidence calculation
- Template fallback

### Contract tests

- Valid and invalid observation schema
- Unknown schema version
- API response compatibility
- Bedrock output mismatch rejection

### Replay tests

Fixed input observations aur graph ke against expected cascade JSON compare karo. Ye demo regression test hoga.

### Failure tests

- S3 object missing
- External source timeout
- DynamoDB throttling simulation
- Bedrock unavailable
- SNS delivery failure
- Stale observation
- Duplicate event

### Usability tests

Minimum five first-time users se test karo:

- Kya user 15 seconds mein highest-risk facility identify kar sakta hai?
- Kya user alert ka reason find kar sakta hai?
- Kya replay aur live mode confuse ho rahe hain?
- Kya confidence aur severity ka difference clear hai?

## 21 Success metrics

| Metric | Hackathon target |
|---|---|
| Demo replay success | 100 percent across final rehearsals |
| Cascade latency | Under 1 second for demo graph |
| Alert generation | Under 60 seconds after ingested trigger |
| Explainability coverage | 100 percent results have a path |
| Fact preservation | Zero LLM-modified numbers or entities |
| Test status | All core unit and replay tests pass |
| First-time comprehension | Highest-risk facility found within 15 seconds |

## 22 Observability

Every run mein common `correlationId` hona chahiye. Log events:

- Observation received or replayed
- Validation accepted or rejected
- Graph version loaded
- Cascade started and completed
- Results persisted
- Advisory composed
- Bedrock used or fallback selected
- Alert approved
- Notification delivered or failed

CloudWatch metrics:

- Ingestion errors
- Cascade latency
- Impact count
- Stale data count
- Advisory fallback count
- Notification success and failure

## 23 Security and privacy

- Least-privilege IAM role per Lambda
- Admin endpoints protected with Cognito or another controlled mechanism
- TLS for all external communication
- AWS-managed encryption for storage
- Secrets Manager or Parameter Store for secrets
- Input size limits and schema validation
- No staff home address or individual movement tracking
- Demo recipients explicitly verified
- Sensitive logs redacted
- Human approval before notification

## 24 Cost control

- Small replay files and on-demand DynamoDB capacity
- Short Lambda execution
- Bedrock optional and only invoked after a material impact
- CloudWatch log retention limited for demo environment
- AWS Budget alarm configured
- Demo infrastructure destroy instructions maintained

## 25 Three minute demo storyboard

### 0 to 25 seconds

Problem: flood alert available hai, lekin hospital ko water disruption ka early operational view nahi milta.

### 25 to 55 seconds

Recorded 2023 observation replay start karo. Source, timestamp aur replay label show karo.

### 55 to 110 seconds

Threshold cross hote hi graph animate karo. Treatment plant, zone aur facility timeline show karo.

### 110 to 145 seconds

Why this alert panel open karo. Evidence, assumptions, delay aur confidence highlight karo.

### 145 to 165 seconds

English aur Hindi advisory preview karke SNS email deliver karo.

### 165 to 180 seconds

AWS architecture, measured latency, who benefits aur clear next step show karo.

## 26 Team execution plan

### Backend owner

Schemas, graph validation, cascade engine, result persistence aur tests.

### Frontend owner

Replay controls, map, accessible list, timeline aur explanation view.

### Cloud owner

SAM or CDK, IAM, API Gateway, deployment, CloudWatch aur notification.

### Product and evidence owner

Data provenance, assumption review, copy, usability test, demo script aur submission assets.

Small team mein roles combine ho sakte hain, lekin ownership clear rehni chahiye.

## 27 Risks and fallbacks

| Risk | Fallback |
|---|---|
| Official API unstable or unavailable | Recorded sourced replay use karo |
| Supply-zone data public nahi | Small synthetic graph label karke use karo |
| Bedrock access or output issue | Deterministic bilingual template |
| SNS SMS restriction | Verified SNS email recipient |
| Map library fails | Ordered impact list and timeline |
| Deployment issue | Pre-verified AWS environment and recorded backup walkthrough |
| Feature incomplete | Feature remove karo; fake implementation mat show karo |
| Wrong alert risk | Human approval and demo-only boundary |

## 28 Roadmap

### Phase 1 Hackathon MVP

Recorded replay, deterministic cascade, dashboard, explanation, bilingual advisory, email alert, tests and deployment.

### Phase 2 Decision support

What-if mitigation simulator: tanker capacity, plant partial operation, hospital reserve duration aur alternate supply.

### Phase 3 Better forecasting

CWC forecast or authorised feed integration, forecast-triggered cascade, calibration and uncertainty evaluation.

### Phase 4 Multi-hazard expansion

Drought, heatwave, road access, power and medical-supply dependencies.

### Phase 5 Institutional integration

Common Alerting Protocol export, municipal control-room feed, graph governance and audit history.

## 29 Submission checklist

- [ ] Team checked in and student verification complete
- [ ] AWS deployment URL works
- [ ] README status is accurate
- [ ] Demo replay works from a clean session
- [ ] Data sources and assumptions are visible
- [ ] Architecture diagram matches deployed system
- [ ] Three-minute video is under the limit
- [ ] Video shows product, target user and AWS role
- [ ] Repository contains setup and test instructions
- [ ] Blog explains problem, build, challenges and learning
- [ ] No secret, private data or misleading claim is committed

## 30 Source register

- Environmental Hacks event and judging: https://www.wemakedevs.org/aws/env
- National Institute of Disaster Management report on the July 2023 Delhi flood: https://nidm.gov.in/PDF/TrgReports/2023/December/Report_12December2023sp.pdf
- Central Water Commission flood forecasting SOP: https://cwc.gov.in/sites/default/files/sopapril2025.pdf
- AWS Lambda event-driven architecture: https://docs.aws.amazon.com/lambda/latest/dg/concepts-event-driven-architectures.html
- Amazon SNS SMS sandbox: https://docs.aws.amazon.com/sns/latest/dg/sns-sms-sandbox.html
- AWS messaging routes for India: https://docs.aws.amazon.com/sms-voice/latest/userguide/registrations-sms-senderid-india-routes.html
- Amazon Bedrock Guardrails: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-how.html

## 31 Final positioning

Ripple ko *AI disaster predictor* ke tarah pitch mat karo. Stronger aur honest positioning ye hai:

> Ripple ek explainable dependency-impact layer hai jo trusted hazard data ko facility-level operational warning mein convert karta hai.

Winning demo ka hero Bedrock ya services ki quantity nahi hogi. Hero hoga ek transparent historical replay jahan judge trigger se alert tak full path dekh sake, assumptions samajh sake, aur measurable warning value observe kar sake.
