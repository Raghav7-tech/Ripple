from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import ImpactResult, ValidationError


ACTION_TEXT = {
    "VERIFY_RESERVE_AND_PREALERT_TANKER": {
        "en": "Confirm the facility water reserve and pre-alert the approved tanker vendor.",
        "hi": "Facility ka water reserve confirm karein aur approved tanker vendor ko pre-alert bhejein.",
    },
    "INSPECT_POTABLE_WATER_INVENTORY": {
        "en": "Inspect the potable-water inventory before demand increases.",
        "hi": "Demand badhne se pehle potable-water inventory inspect karein.",
    },
    "MONITOR_AND_CONFIRM_STORAGE": {
        "en": "Monitor the supply status and confirm available storage.",
        "hi": "Supply status monitor karein aur available storage confirm karein.",
    },
}


@dataclass(frozen=True)
class Advisory:
    impact_id: str
    target_node_id: str
    language: str
    title: str
    body: str
    action: str
    locked_facts: dict[str, Any]
    generator: str = "deterministic-template-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "impactId": self.impact_id,
            "targetNodeId": self.target_node_id,
            "language": self.language,
            "title": self.title,
            "body": self.body,
            "action": self.action,
            "lockedFacts": self.locked_facts,
            "generator": self.generator,
            "requiresHumanApproval": True,
        }


def compose_advisory(impact: ImpactResult, language: str = "en") -> Advisory:
    if language not in {"en", "hi"}:
        raise ValidationError("advisory language must be en or hi")
    facts = {
        "impactId": impact.impact_id,
        "targetNodeId": impact.target_node_id,
        "targetName": impact.target_name,
        "severity": impact.severity.value,
        "etaMinutes": impact.eta_minutes,
        "confidence": impact.confidence,
        "actionCode": impact.action_code,
    }
    action = ACTION_TEXT[impact.action_code][language]
    if language == "hi":
        title = "Sambhavit water supply disruption ke liye taiyaar rahein"
        body = f"{impact.target_name} mein lagbhag {impact.eta_minutes} minute mein municipal water supply kam ho sakti hai."
    else:
        title = "Prepare for possible water-supply disruption"
        body = f"{impact.target_name} may experience reduced municipal supply in approximately {impact.eta_minutes} minutes."
    return Advisory(
        impact_id=impact.impact_id,
        target_node_id=impact.target_node_id,
        language=language,
        title=title,
        body=body,
        action=action,
        locked_facts=facts,
    )


def validate_generated_advisory(candidate: dict[str, Any], locked_facts: dict[str, Any]) -> bool:
    """Fail closed if a generated response changes any engine-owned fact."""
    candidate_facts = candidate.get("lockedFacts")
    if not isinstance(candidate_facts, dict):
        return False
    return all(candidate_facts.get(key) == value for key, value in locked_facts.items())
