import pandas as pd

from src.transform.engineering_change_impact import (
    analyse_engineering_change,
)


def sample_datasets(status="PENDING"):
    return {
        "engineering_changes": pd.DataFrame([{
            "ecn_id": "CHG-TEST-001",
            "product_id": "ITEM-001",
            "revision_from": "REV-A",
            "revision_to": "REV-B",
            "effective_date": "2026-10-01",
            "approval_status": status,
            "component_id": "COMP-001",
            "factory_id": "FACTORY_TEST",
        }]),

        "bom": pd.DataFrame([{
            "bom_id": "BOM-001",
            "product_id": "ITEM-001",
            "product_revision": "REV-B",
            "component_id": "COMP-001",
            "factory_id": "FACTORY_TEST",
        }]),

        "production_orders": pd.DataFrame([
            {
                "production_order_id": "ORDER-BEFORE",
                "product_id": "ITEM-001",
                "product_revision": "REV-B",
                "bom_id": "BOM-001",
                "start_time": "2026-09-30",
                "machine_id": "M-01",
                "factory_id": "FACTORY_TEST",
            },
            {
                "production_order_id": "ORDER-AFTER",
                "product_id": "ITEM-001",
                "product_revision": "REV-B",
                "bom_id": "BOM-001",
                "start_time": "2026-10-02",
                "machine_id": "M-01",
                "factory_id": "FACTORY_TEST",
            },
        ]),

        "machine_logs": pd.DataFrame([{
            "production_order_id": "ORDER-AFTER",
            "machine_id": "M-01",
            "factory_id": "FACTORY_TEST",
        }]),

        "quality_events": pd.DataFrame([{
            "production_order_id": "ORDER-AFTER",
            "machine_id": "M-01",
            "finished_lot_id": "LOT-001",
            "factory_id": "FACTORY_TEST",
        }]),
    }


def test_pending_ecn_is_excluded():
    result = analyse_engineering_change(
        "FACTORY_TEST",
        "CHG-TEST-001",
        sample_datasets("PENDING"),
    )

    assert result["status"] == "EXCLUDED"
    assert result["summary"]["affected_order_count"] == 0
    assert result["summary"]["affected_machine_log_count"] == 0
    assert result["summary"]["affected_quality_event_count"] == 0


def test_approved_ecn_finds_only_orders_after_effective_date():
    result = analyse_engineering_change(
        "FACTORY_TEST",
        "CHG-TEST-001",
        sample_datasets("APPROVED"),
    )

    assert result["status"] == "ANALYSED"
    assert result["summary"]["affected_order_count"] == 1

    order_ids = set(
        result["affected_orders"]["production_order_id"]
    )

    assert order_ids == {"ORDER-AFTER"}
    assert result["summary"]["affected_machine_log_count"] == 1
    assert result["summary"]["affected_quality_event_count"] == 1
    assert result["summary"]["affected_finished_lot_count"] == 1