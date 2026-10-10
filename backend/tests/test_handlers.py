from __future__ import annotations

import json
import unittest

from functions.api.app import handler as api_handler
from functions.alert.app import handler as alert_handler
from functions.cascade.app import handler as cascade_handler
from functions.forecast.app import handler as forecast_handler
from functions.replay.app import handler as replay_handler
from tests.support import fixture


class HandlerTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        result = api_handler({"rawPath": "/health"}, None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["status"], "ok")

    def test_cascade_handler(self) -> None:
        replay = fixture("data/samples/yamuna-2023-replay.json")
        result = cascade_handler(
            {
                "runId": "run-handler",
                "graph": fixture("data/samples/delhi-water-demo-graph.json"),
                "observation": replay["observations"][-1],
            },
            None,
        )
        self.assertEqual(result["severity"], "critical")
        self.assertEqual(len(result["impacts"]), 3)

    def test_replay_handler_accepts_embedded_event(self) -> None:
        result = replay_handler(
            {
                "runId": "run-local",
                "correlationId": "corr-test",
                "graph": fixture("data/samples/delhi-water-demo-graph.json"),
                "replay": fixture("data/samples/yamuna-2023-replay.json"),
            },
            None,
        )
        self.assertEqual(result["correlationId"], "corr-test")
        self.assertEqual(result["status"], "completed")

    def test_forecast_handler_marks_baseline(self) -> None:
        result = forecast_handler(fixture("data/samples/shortage-forecast-request.json"), None)
        self.assertEqual(result["modelVersion"], "explainable-baseline-v1")
        self.assertFalse(result["productionReady"])

    def test_alert_handler_requires_explicit_approval_and_defaults_to_preview(self) -> None:
        replay = replay_handler(
            {
                "runId": "run-alert",
                "graph": fixture("data/samples/delhi-water-demo-graph.json"),
                "replay": fixture("data/samples/yamuna-2023-replay.json"),
            },
            None,
        )
        impact = replay["latestImpacts"][0]
        rejected = alert_handler({"body": json.dumps({"impact": impact, "expectedRunId": "run-alert"})}, None)
        self.assertEqual(rejected["statusCode"], 400)

        preview = alert_handler(
            {
                "body": json.dumps(
                    {"impact": impact, "expectedRunId": "run-alert", "approved": True, "language": "en"}
                )
            },
            None,
        )
        self.assertEqual(preview["statusCode"], 200)
        self.assertFalse(json.loads(preview["body"])["delivered"])


if __name__ == "__main__":
    unittest.main()
