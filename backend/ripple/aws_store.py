from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any


def _dynamo_value(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value), parse_float=Decimal)


class RippleStore:
    """Small DynamoDB adapter kept outside the deterministic domain layer."""

    def __init__(self, table_name: str | None = None):
        import boto3

        self.table_name = table_name or os.environ["TABLE_NAME"]
        self.table = boto3.resource("dynamodb").Table(self.table_name)

    def put_run(self, run: dict[str, Any]) -> None:
        item = {"pk": f"RUN#{run['runId']}", "sk": "META", **run}
        self.table.put_item(Item=_dynamo_value(item))

    def put_impact(self, impact: dict[str, Any]) -> None:
        run_id = impact["runId"]
        impact_id = impact["impactId"]
        item = {"pk": f"RUN#{run_id}", "sk": f"IMPACT#{impact_id}", **impact}
        self.table.put_item(Item=_dynamo_value(item))
        lookup = {"pk": f"IMPACT#{impact_id}", "sk": "META", **impact}
        self.table.put_item(Item=_dynamo_value(lookup))

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        item = self.table.get_item(Key={"pk": f"RUN#{run_id}", "sk": "META"}).get("Item")
        return json.loads(json.dumps(item, default=float)) if item else None

    def get_impact(self, impact_id: str) -> dict[str, Any] | None:
        item = self.table.get_item(Key={"pk": f"IMPACT#{impact_id}", "sk": "META"}).get("Item")
        return json.loads(json.dumps(item, default=float)) if item else None
