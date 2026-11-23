"""Integration test against the bundled Factory B synthetic test dataset."""
from pathlib import Path
import unittest

import pandas as pd

from src.transform.adapters.factory_b_adapter import build_kpi_inputs
from src.transform.ideal_cycle_time_resolver import IdealCycleTimeResolver
from src.transform.kpi_engine import calculate_order_kpis, summarize_kpis

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Factory_B_Refactoring_Test_Dataset_CSVs"


class FactoryBDatasetIntegrationTests(unittest.TestCase):
    def test_all_factory_b_orders_produce_complete_kpis_and_oee(self):
        orders = pd.read_csv(DATA / "production_jobs.csv", parse_dates=["actual_start_ts", "actual_end_ts"])
        downtime = pd.read_csv(DATA / "stoppage_records.csv", parse_dates=["stop_start", "stop_end"])
        orders = orders.rename(columns={
            "work_order_no": "production_order_id", "material_code": "product_id",
            "item_revision": "product_revision", "actual_start_ts": "start_time",
            "actual_end_ts": "end_time", "asset_number": "machine_id",
            "planned_qty": "planned_quantity", "good_qty": "good_quantity",
            "reject_qty": "rejected_quantity",
        })
        downtime = downtime.rename(columns={
            "work_order_ref": "production_order_id", "asset_no": "machine_id",
            "stop_start": "start_time", "stop_end": "end_time",
            "duration_min": "duration_minutes", "stoppage_id": "downtime_event_id",
            "reason_code": "downtime_reason",
        })
        resolver = IdealCycleTimeResolver(ROOT / "config" / "kpi" / "ideal_cycle_time.yaml")
        inputs, warnings = build_kpi_inputs(orders, downtime, resolver)
        results = calculate_order_kpis(inputs)
        summary = summarize_kpis(results).iloc[0]

        self.assertEqual(len(results), 64)
        self.assertFalse(warnings)
        self.assertEqual(int(results.oee.notna().sum()), 64)
        self.assertTrue(results.ideal_cycle_time_status.eq("provisional").all())
        self.assertGreater(summary.availability, 0)
        self.assertGreater(summary.performance, 0)
        self.assertGreater(summary.quality, 0)
        self.assertGreater(summary.oee, 0)
        self.assertLessEqual(summary.quality, 1)
        self.assertAlmostEqual(summary.oee, summary.availability * summary.performance * summary.quality)


if __name__ == "__main__":
    unittest.main()
