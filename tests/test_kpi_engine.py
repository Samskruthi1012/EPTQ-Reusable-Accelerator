import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

from src.transform.kpi_engine import calculate_order_kpis
from src.transform.ideal_cycle_time_resolver import IdealCycleTimeResolver


class KpiEngineTests(unittest.TestCase):
    def test_complete_order(self):
        source = pd.DataFrame([{
            "factory_id": "FACTORY_B", "production_order_id": "WO-1",
            "product_id": "ITEM-1", "planned_time_ms": 3_600_000,
            "downtime_ms": 600_000, "total_output": 100,
            "good_quantity": 95, "ideal_cycle_time_ms": 30_000,
        }])
        result = calculate_order_kpis(source).iloc[0]
        self.assertAlmostEqual(result.availability, 5 / 6)
        self.assertAlmostEqual(result.performance, 1.0)
        self.assertAlmostEqual(result.quality, 0.95)
        self.assertAlmostEqual(result.oee, (5 / 6) * 0.95)
        self.assertEqual(result.kpi_status, "complete")

    def test_missing_good_quantity_does_not_invent_quality(self):
        source = pd.DataFrame([{
            "factory_id": "FACTORY_A", "production_order_id": "ORD-1",
            "product_id": "PROD-1", "planned_time_ms": 1000,
            "downtime_ms": 100, "total_output": 10,
            "ideal_cycle_time_ms": 50,
        }])
        result = calculate_order_kpis(source).iloc[0]
        self.assertIsNone(result.quality)
        self.assertIsNone(result.oee)
        self.assertIn("good_quantity_unavailable", result.kpi_status_reasons)

    def test_resolver_prefers_more_specific_product_machine_rule(self):
        config = {
            "configuration": {
                "require_approved": True,
                "resolution_order": ["product+machine", "product", "machine", "factory"],
            },
            "rules": [
                {"rule_id": "factory", "factory_id": "FACTORY_B", "ideal_cycle_time_ms": 50000, "status": "approved"},
                {"rule_id": "product", "factory_id": "FACTORY_B", "product_id": "ITEM-1", "ideal_cycle_time_ms": 40000, "status": "approved"},
                {"rule_id": "product-machine", "factory_id": "FACTORY_B", "product_id": "ITEM-1", "machine_id": "MC-1", "ideal_cycle_time_ms": 30000, "status": "approved"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text(yaml.safe_dump(config), encoding="utf-8")
            resolver = IdealCycleTimeResolver(path)
            rule = resolver.resolve(factory_id="FACTORY_B", product_id="ITEM-1", machine_id="MC-1")
        self.assertEqual(rule["rule_id"], "product-machine")


if __name__ == "__main__":
    unittest.main()
