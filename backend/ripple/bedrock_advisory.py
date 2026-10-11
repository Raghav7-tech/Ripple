from __future__ import annotations

import json
import re
from typing import Any

from .advisory import Advisory, compose_advisory, validate_generated_advisory
from .models import ImpactResult, ValidationError


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValidationError("Bedrock response did not contain a JSON object")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValidationError("Bedrock response JSON must be an object")
    return value


def _validate_text(candidate: dict[str, Any], fallback: Advisory) -> None:
    for key in ("title", "body", "action"):
        value = candidate.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 600:
            raise ValidationError(f"Bedrock advisory {key} is invalid")
    if fallback.locked_facts["targetName"] not in candidate["body"]:
        raise ValidationError("Bedrock advisory omitted the target name")
    eta = str(fallback.locked_facts["etaMinutes"])
    if eta not in candidate["body"]:
        raise ValidationError("Bedrock advisory omitted the locked ETA")
    allowed_numbers = {
        eta,
        str(round(float(fallback.locked_facts["confidence"]), 2)),
        str(round(float(fallback.locked_facts["confidence"]) * 100)),
    }
    emitted_numbers = set(re.findall(r"\d+(?:\.\d+)?", " ".join(candidate[key] for key in ("title", "body", "action"))))
    if not emitted_numbers.issubset(allowed_numbers):
        raise ValidationError("Bedrock advisory introduced an unlocked number")


def compose_bedrock_advisory(
    impact: ImpactResult,
    language: str,
    *,
    model_id: str,
    client: Any | None = None,
) -> tuple[Advisory, str | None]:
    """Simplify locked facts with Bedrock and fail closed to a template.

    Returns the advisory plus a fallback reason. A null reason means Bedrock was
    used successfully. Runtime or validation errors never escape to the caller.
    """

    fallback = compose_advisory(impact, language)
    if client is None:
        import boto3

        client = boto3.client("bedrock-runtime")
    prompt = {
        "task": "Rewrite this water-supply advisory in plain language without changing any fact.",
        "language": language,
        "rules": [
            "Return one JSON object only with title, body, action, and lockedFacts.",
            "Copy lockedFacts exactly.",
            "Keep the target name and ETA in body.",
            "Do not add numbers, causes, guarantees, or instructions.",
        ],
        "fallbackAdvisory": fallback.to_dict(),
    }
    try:
        result = client.converse(
            modelId=model_id,
            system=[{"text": "You are a controlled public-service copy editor. Facts are immutable."}],
            messages=[{"role": "user", "content": [{"text": json.dumps(prompt, ensure_ascii=False)}]}],
            inferenceConfig={"maxTokens": 450, "temperature": 0.0, "topP": 0.9},
        )
        blocks = result["output"]["message"]["content"]
        text = "".join(str(block.get("text", "")) for block in blocks if isinstance(block, dict))
        candidate = _extract_json(text)
        if not validate_generated_advisory(candidate, fallback.locked_facts):
            raise ValidationError("Bedrock changed or omitted locked facts")
        _validate_text(candidate, fallback)
        return (
            Advisory(
                impact_id=fallback.impact_id,
                target_node_id=fallback.target_node_id,
                language=language,
                title=candidate["title"].strip(),
                body=candidate["body"].strip(),
                action=candidate["action"].strip(),
                locked_facts=fallback.locked_facts,
                generator=f"bedrock-converse:{model_id}",
            ),
            None,
        )
    except Exception as exc:
        return fallback, exc.__class__.__name__
