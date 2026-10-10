from __future__ import annotations

import unittest

from ripple.forecast import ExplainableBaselinePredictor, ShortageFeatures
from tests.support import fixture


class ForecastTests(unittest.TestCase):
    def test_baseline_is_explainable_and_explicitly_not_production_ready(self) -> None:
        features = ShortageFeatures.from_dict(fixture("data/samples/shortage-forecast-request.json"))
        prediction = ExplainableBaselinePredictor().predict(features)
        self.assertGreaterEqual(prediction.shortage_probability, 0.6)
        self.assertEqual(prediction.estimated_hours_to_shortage, 45.0)
        self.assertEqual(len(prediction.top_factors), 3)
        self.assertFalse(prediction.production_ready)

    def test_no_supply_gap_has_no_depletion_time(self) -> None:
        raw = fixture("data/samples/shortage-forecast-request.json")
        raw["expectedSupplyM3h"] = raw["expectedDemandM3h"]
        prediction = ExplainableBaselinePredictor().predict(ShortageFeatures.from_dict(raw))
        self.assertIsNone(prediction.estimated_hours_to_shortage)


if __name__ == "__main__":
    unittest.main()
