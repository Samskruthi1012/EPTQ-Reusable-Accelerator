import pandas as pd

from src.mapping.mapping_engine import (
    load_mapping_config,
    map_dataset,
)
from src.ingestion.validator import (
    load_validation_config,
    validate_standard_dataset,
)
from src.transform.engineering_change_impact import (
    analyse_engineering_change,
)

from tests.test_engineering_change_impact import sample_datasets


def test_factory_b_production_order_mapping():
    """Verify Factory B source fields map to standard EPTQ fields."""

    mapping_config = load_mapping_config(
        "config/mappings/factory_b_mapping.yaml"
    )

    source = pd.DataFrame([{
        "work_order_no": "WO-TEST-001",
        "material_code": "ITEM-001",
        "item_revision": "REV-B",
        "bom_used": "BOM-001",
        "actual_start_ts": "2026-10-02 08:00:00",
        "actual_end_ts": "2026-10-02 10:00:00",
        "asset_number": "M-01",
        "operator_badge": "OP-001",
        "planned_qty": 100,
        "good_qty": 95,
        "reject_qty": 5,
        "order_status": "COMPLETED",
    }])

    result = map_dataset(
        source,
        mapping_config,
        "production_orders",
    )

    assert result.loc[0, "production_order_id"] == "WO-TEST-001"
    assert result.loc[0, "product_id"] == "ITEM-001"
    assert result.loc[0, "product_revision"] == "REV-B"
    assert result.loc[0, "bom_id"] == "BOM-001"
    assert result.loc[0, "machine_id"] == "M-01"
    assert result.loc[0, "planned_quantity"] == 100
    assert result.loc[0, "good_quantity"] == 95
    assert result.loc[0, "rejected_quantity"] == 5
    assert result.loc[0, "factory_id"] == mapping_config["factory_id"]


def test_approved_ecn_excludes_orders_using_wrong_bom_revision():
    """Verify orders using a non-target BOM revision are excluded."""

    datasets = sample_datasets("APPROVED")

    datasets["bom"] = pd.concat([
        datasets["bom"],
        pd.DataFrame([{
            "bom_id": "BOM-OLD",
            "product_id": "ITEM-001",
            "product_revision": "REV-A",
            "component_id": "COMP-001",
            "factory_id": "FACTORY_TEST",
        }]),
    ], ignore_index=True)

    datasets["production_orders"] = pd.concat([
        datasets["production_orders"],
        pd.DataFrame([{
            "production_order_id": "ORDER-WRONG-REVISION",
            "product_id": "ITEM-001",
            "product_revision": "REV-A",
            "bom_id": "BOM-OLD",
            "start_time": "2026-10-02",
            "machine_id": "M-01",
            "factory_id": "FACTORY_TEST",
        }]),
    ], ignore_index=True)

    result = analyse_engineering_change(
        "FACTORY_TEST",
        "CHG-TEST-001",
        datasets,
    )

    order_ids = set(
        result["affected_orders"]["production_order_id"]
    )

    assert result["status"] == "ANALYSED"
    assert "ORDER-AFTER" in order_ids
    assert "ORDER-WRONG-REVISION" not in order_ids
    assert result["summary"]["affected_order_count"] == 1


def test_duplicate_production_order_ids_are_detected():
    """Verify duplicate standardized production order IDs are flagged."""

    validation_config = load_validation_config(
        "config/common/validation_rules.yaml"
    )

    dataframe = pd.DataFrame({
        "production_order_id": [
            "WO-001",
            "WO-001",
            "WO-002",
        ],
        "product_id": [
            "ITEM-001",
            "ITEM-001",
            "ITEM-002",
        ],
    })

    result = validate_standard_dataset(
        dataframe,
        validation_config,
        "production_orders",
    )

    assert result["valid"] is False
    assert result["invalid_unique_values"]["production_order_id"] == [1, 2]
    assert result["invalid_rows"] == [1, 2]
