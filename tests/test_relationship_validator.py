import pandas as pd

from src.validation.relationship_validator import validate_relationships


def sample_datasets():
    return {
        "product_metadata": pd.DataFrame([
            {"product_id": "P001"}
        ]),

        "production_orders": pd.DataFrame([
            {
                "production_order_id": "O001",
                "product_id": "P001",
                "machine_id": "M001",
            }
        ]),

        "quality_events": pd.DataFrame([
            {
                "quality_event_id": "Q001",
                "production_order_id": "O001",
                "machine_id": "M001",
                "finished_lot_id": "LOT001",
            }
        ]),

        "machine_logs": pd.DataFrame([
            {
                "machine_id": "M001",
                "production_order_id": "O001",
                "source_record_id": "LOG001",
            }
        ]),

        "engineering_changes": pd.DataFrame([
            {
                "ecn_id": "ECN001",
                "product_id": "P001",
                "component_id": "C001",
            }
        ]),

        "bom": pd.DataFrame([
            {
                "product_id": "P001",
                "component_id": "C001",
            }
        ]),
    }


def test_production_order_with_unknown_product():
    data = sample_datasets()
    data["production_orders"].loc[0, "product_id"] = "UNKNOWN"

    issues = validate_relationships(data)

    assert (
        (issues["dataset"] == "production_orders")
        & (issues["classification"] == "UNMATCHED")
    ).any()


def test_quality_event_with_missing_finished_lot():
    data = sample_datasets()
    data["quality_events"].loc[0, "finished_lot_id"] = None

    issues = validate_relationships(data)

    assert (
        (issues["dataset"] == "quality_events")
        & (issues["classification"] == "MISSING_RELATIONSHIP")
    ).any()


def test_machine_log_with_unmatched_machine():
    data = sample_datasets()
    data["machine_logs"].loc[0, "machine_id"] = "UNKNOWN"

    issues = validate_relationships(data)

    assert (
        (issues["dataset"] == "machine_logs")
        & (issues["classification"] == "UNMATCHED")
    ).any()


def test_ecn_with_unknown_product():
    data = sample_datasets()
    data["engineering_changes"].loc[0, "product_id"] = "UNKNOWN"

    issues = validate_relationships(data)

    assert (
        (issues["dataset"] == "engineering_changes")
        & (issues["classification"] == "UNRESOLVED")
    ).any()


def test_ecn_component_not_found_in_bom():
    data = sample_datasets()
    data["engineering_changes"].loc[0, "component_id"] = "UNKNOWN"

    issues = validate_relationships(data)

    assert (
        (issues["dataset"] == "engineering_changes")
        & (issues["classification"] == "UNRESOLVED")
        & (issues["field"] == "component_id")
    ).any()


def test_valid_relationships_produce_no_issues():
    issues = validate_relationships(sample_datasets())

    assert issues.empty