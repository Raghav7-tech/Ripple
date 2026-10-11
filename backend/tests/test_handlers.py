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

    def test_forecast_http_handler_uses_api_gateway_response(self) -> None:
        result = forecast_handler(
            {"requestContext": {"http": {}}, "body": json.dumps({"features": fixture("data/samples/shortage-forecast-request.json")})},
            None,
        )
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["modelVersion"], "explainable-baseline-v1")

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

    def test_cascade_http_simulation_valid(self) -> None:
        replay = fixture("data/samples/yamuna-2023-replay.json")
        event = {
            "rawPath": "/modeling/simulate",
            "headers": {"x-correlation-id": "test-corr-123"},
            "body": json.dumps(
                {
                    "runId": "run-http-1",
                    "graph": fixture("data/samples/delhi-water-demo-graph.json"),
                    "observation": replay["observations"][-1],
                }
            ),
        }
        res = cascade_handler(event, None)
        self.assertEqual(res["statusCode"], 200)
        body = json.loads(res["body"])
        self.assertEqual(body["schemaVersion"], "1.0")
        self.assertEqual(body["runId"], "run-http-1")
        self.assertEqual(body["severity"], "critical")
        self.assertEqual(len(body["impacts"]), 3)
        self.assertEqual(body["correlationId"], "test-corr-123")
        self.assertIn("engineCalculationMs", body)
        self.assertIsInstance(body["engineCalculationMs"], (int, float))

    def test_cascade_http_simulation_invalid_body(self) -> None:
        event = {"rawPath": "/modeling/simulate", "body": "{not valid json"}
        res = cascade_handler(event, None)
        self.assertEqual(res["statusCode"], 400)
        body = json.loads(res["body"])
        self.assertEqual(body["error"]["code"], "MALFORMED_JSON")

    def test_cascade_http_simulation_missing_fields(self) -> None:
        event = {"rawPath": "/modeling/simulate", "body": json.dumps({"runId": "r1"})}
        res = cascade_handler(event, None)
        self.assertEqual(res["statusCode"], 400)
        body = json.loads(res["body"])
        self.assertEqual(body["error"]["code"], "INVALID_CASCADE_INPUT")

    def test_cascade_http_simulation_invalid_resource(self) -> None:
        graph = fixture("data/samples/delhi-water-demo-graph.json")
        graph_copy = json.loads(json.dumps(graph))
        graph_copy["edges"][0]["resourceType"] = "uranium"
        replay = fixture("data/samples/yamuna-2023-replay.json")
        event = {
            "rawPath": "/modeling/simulate",
            "body": json.dumps(
                {
                    "runId": "run-bad-res",
                    "graph": graph_copy,
                    "observation": replay["observations"][-1],
                }
            ),
        }
        res = cascade_handler(event, None)
        self.assertEqual(res["statusCode"], 400)
        body = json.loads(res["body"])
        self.assertEqual(body["error"]["code"], "INVALID_CASCADE_INPUT")

    def test_cascade_http_simulation_node_cap(self) -> None:
        graph = fixture("data/samples/delhi-water-demo-graph.json")
        graph_copy = json.loads(json.dumps(graph))
        base_node = graph_copy["nodes"][0]
        graph_copy["nodes"] = [
            {**base_node, "nodeId": f"node-{i}", "name": f"Node {i}"} for i in range(501)
        ]
        replay = fixture("data/samples/yamuna-2023-replay.json")
        event = {
            "rawPath": "/modeling/simulate",
            "body": json.dumps(
                {
                    "runId": "run-cap",
                    "graph": graph_copy,
                    "observation": replay["observations"][-1],
                }
            ),
        }
        res = cascade_handler(event, None)
        self.assertEqual(res["statusCode"], 400)
        body = json.loads(res["body"])
        self.assertEqual(body["error"]["code"], "GRAPH_TOO_LARGE")

    def test_cascade_http_simulation_edge_cap(self) -> None:
        graph = fixture("data/samples/delhi-water-demo-graph.json")
        graph_copy = json.loads(json.dumps(graph))
        base_edge = graph_copy["edges"][0]
        graph_copy["edges"] = [
            {**base_edge, "edgeId": f"edge-{i}"} for i in range(2501)
        ]
        replay = fixture("data/samples/yamuna-2023-replay.json")
        event = {
            "rawPath": "/modeling/simulate",
            "body": json.dumps(
                {
                    "runId": "run-cap",
                    "graph": graph_copy,
                    "observation": replay["observations"][-1],
                }
            ),
        }
        res = cascade_handler(event, None)
        self.assertEqual(res["statusCode"], 400)
        body = json.loads(res["body"])
        self.assertEqual(body["error"]["code"], "GRAPH_TOO_LARGE")

    def test_cascade_http_simulation_payload_cap(self) -> None:
        event = {
            "rawPath": "/modeling/simulate",
            "body": "x" * (1024 * 1024 + 10),
        }
        res = cascade_handler(event, None)
        self.assertEqual(res["statusCode"], 400)
        body = json.loads(res["body"])
        self.assertEqual(body["error"]["code"], "PAYLOAD_TOO_LARGE")

    def test_cascade_http_simulation_deterministic(self) -> None:
        replay = fixture("data/samples/yamuna-2023-replay.json")
        payload = json.dumps(
            {
                "runId": "run-det",
                "graph": fixture("data/samples/delhi-water-demo-graph.json"),
                "observation": replay["observations"][-1],
            }
        )
        res1 = cascade_handler({"rawPath": "/modeling/simulate", "body": payload}, None)
        res2 = cascade_handler({"rawPath": "/modeling/simulate", "body": payload}, None)
        b1 = json.loads(res1["body"])
        b2 = json.loads(res2["body"])
        self.assertEqual(b1["runId"], b2["runId"])
        self.assertEqual(b1["severity"], b2["severity"])
        self.assertEqual(b1["impacts"], b2["impacts"])


if __name__ == "__main__":
    unittest.main()
