# Demo and submission plan

## Core rule

The video should show one complete working cascade. Do not spend the three minutes listing every planned feature.

## Storyboard

| Time | Screen | Message |
|---|---|---|
| 0:00-0:25 | Problem and one-line diagram | Hazard warning exists; secondary service impact is hard to see |
| 0:25-0:55 | Replay selector | Real historical event, timestamp, source and replay label |
| 0:55-1:50 | Map, list and timeline | Trigger propagates through the dependency graph |
| 1:50-2:25 | Why this alert | Path, delays, evidence, confidence and assumptions |
| 2:25-2:45 | Advisory preview and email | Bilingual actionable output with human approval |
| 2:45-3:00 | AWS architecture and measured result | Where AWS fits and what value Ripple creates |

## Recording checklist

- Use a clean browser profile and readable zoom.
- Hide bookmarks, credentials, account IDs, and unrelated notifications.
- Preload the event but start the replay on camera.
- Keep a visible Replay label throughout.
- Show at least one real application log or metric without exposing secrets.
- Show the received email, not only a success toast.
- Record voice and screen locally to avoid live network dependency.
- Keep a backup recording after the final deployed version is verified.

## Submission assets

- Repository URL
- Deployed dashboard URL
- Three-minute video URL
- Architecture diagram
- Problem and impact statement
- Data sources and assumptions
- AWS service list with a sentence explaining each service
- Setup and test instructions
- Builder Center blog link, if submitted

## Judge questions to prepare

1. How is Ripple different from an existing flood-warning portal?
2. Which data is verified and which is synthetic?
3. How do you calculate impact time and confidence?
4. What stops Bedrock from hallucinating an emergency detail?
5. What happens when the source is stale or unavailable?
6. Why DynamoDB instead of a graph database?
7. How would a real utility validate the dependency graph?
8. What exactly is deployed on AWS?
9. How much warning time did the demonstration produce?
10. What would you build next with another month?

## Honest fallback language

- "This is a recorded replay of a real historical event."
- "The treatment-plant shutdown is sourced; selected zone and facility edges are demonstration assumptions."
- "Ripple is decision support and not an official public-warning authority."
- "Bedrock formats language only; the graph engine calculates all facts."
