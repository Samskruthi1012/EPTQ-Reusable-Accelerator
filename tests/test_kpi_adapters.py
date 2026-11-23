import unittest
import pandas as pd

from src.transform.adapters.factory_b_adapter import build_kpi_inputs as build_b
from src.transform.adapters.factory_a_adapter import build_kpi_inputs as build_a
from src.transform.kpi_engine import calculate_order_kpis


class AdapterTests(unittest.TestCase):
    def test_factory_b_uses_order_quantities_and_linked_downtime(self):
        orders = pd.DataFrame([{
            "factory_id": "FACTORY_B", "production_order_id": "WO-1",
            "product_id": "ITEM-1", "product_revision": "A", "machine_id": "MC-1",
            "start_time": "2026-01-01 08:00:00", "end_time": "2026-01-01 10:00:00",
            "good_quantity": 90, "rejected_quantity": 10,
        }])
        downtime = pd.DataFrame([
            {"production_order_id": "WO-1", "machine_id": "MC-1", "start_time": "2026-01-01 07:50:00", "end_time": "2026-01-01 08:20:00"},
            {"production_order_id": "WO-1", "machine_id": "MC-1", "start_time": "2026-01-01 08:10:00", "end_time": "2026-01-01 08:30:00"},
        ])
        inputs, warnings = build_b(orders, downtime)
        row = inputs.iloc[0]
        self.assertEqual(row.total_output, 100)
        self.assertEqual(row.good_quantity, 90)
        self.assertEqual(row.downtime_ms, 30 * 60 * 1000)
        self.assertEqual(row.planned_time_ms, 2 * 60 * 60 * 1000)
        self.assertFalse(warnings)
        kpi = calculate_order_kpis(inputs).iloc[0]
        self.assertAlmostEqual(kpi.quality, 0.9)

    def test_factory_a_does_not_turn_defect_flags_into_unit_quality(self):
        orders = pd.DataFrame([{
            "factory_id": "FACTORY_A", "production_order_id": "ORD-1", "product_id": "P1",
            "start_time": "2026-01-01 08:00:00", "end_time": "2026-01-01 09:00:00",
        }])
        logs = pd.DataFrame([{
            "event_timestamp": "2026-01-01 08:10:00", "output_count": 5,
            "defect_flag": True, "machine_id": "M1",
        }, {
            "event_timestamp": "2026-01-01 10:10:00", "output_count": 7,
            "defect_flag": False, "machine_id": "M1",
        }])
        downtime = pd.DataFrame(columns=["start_time", "end_time", "machine_id"])
        inputs, warnings = build_a(orders, logs, downtime)
        self.assertEqual(inputs.iloc[0].total_output, 5)
        self.assertTrue(pd.isna(inputs.iloc[0].good_quantity))
        self.assertIn("1 machine-log rows matched no order", warnings[0] if warnings else "")
        kpi = calculate_order_kpis(inputs).iloc[0]
        self.assertTrue(pd.isna(kpi.quality))
        self.assertTrue(pd.isna(kpi.oee))


if __name__ == "__main__":
    unittest.main()
