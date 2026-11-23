from pathlib import Path
import argparse
import pandas as pd


REQUIRED_DATASETS = [
    "product_metadata",
    "production_orders",
    "quality_events",
    "machine_logs",
    "engineering_changes",
    "bom",
]


def _check_columns(data, dataset, required):
    missing = set(required) - set(data[dataset].columns)
    if missing:
        raise ValueError(
            f"{dataset} is missing columns: {sorted(missing)}"
        )


def _add_issue(issues, dataset, record_id, field, value,
               classification, message):
    issues.append({
        "dataset": dataset,
        "record_id": str(record_id),
        "field": field,
        "value": str(value),
        "classification": classification,
        "message": message,
    })


def validate_relationships(datasets):
    """
    Validate cross-dataset relationships using standardized EPTQ data.

    Returns a DataFrame containing all detected relationship issues.
    Does not modify the input datasets or invent relationships.
    """
    required = {
        "product_metadata": ["product_id"],
        "production_orders": [
            "production_order_id", "product_id", "machine_id"
        ],
        "quality_events": [
            "quality_event_id", "production_order_id",
            "machine_id", "finished_lot_id"
        ],
        "machine_logs": [
            "machine_id", "production_order_id"
        ],
        "engineering_changes": [
            "ecn_id", "product_id", "component_id"
        ],
        "bom": ["product_id", "component_id"],
    }

    missing_datasets = set(REQUIRED_DATASETS) - set(datasets)
    if missing_datasets:
        raise ValueError(
            f"Missing datasets: {sorted(missing_datasets)}"
        )

    for dataset_name, columns in required.items():
        _check_columns(datasets, dataset_name, columns)

    products = datasets["product_metadata"]
    orders = datasets["production_orders"]
    quality = datasets["quality_events"]
    machine_logs = datasets["machine_logs"]
    ecns = datasets["engineering_changes"]
    bom = datasets["bom"]

    product_ids = set(
        products["product_id"].dropna().astype(str).str.strip()
    )

    order_ids = set(
        orders["production_order_id"].dropna().astype(str).str.strip()
    )

    # A machine relationship is valid only when both the order
    # and machine match the same production-order record.
    order_machine_pairs = set(
        zip(
            orders["production_order_id"].astype(str).str.strip(),
            orders["machine_id"].astype(str).str.strip()
        )
    )

    bom_product_components = set(
        zip(
            bom["product_id"].astype(str).str.strip(),
            bom["component_id"].astype(str).str.strip()
        )
    )

    issues = []

    # 1. Production order -> Product
    for _, row in orders.iterrows():
        product_id = str(row["product_id"]).strip()

        if not product_id or product_id.lower() == "nan":
            _add_issue(
                issues, "production_orders",
                row["production_order_id"], "product_id",
                product_id, "MISSING_RELATIONSHIP",
                "Production order has no product reference."
            )
        elif product_id not in product_ids:
            _add_issue(
                issues, "production_orders",
                row["production_order_id"], "product_id",
                product_id, "UNMATCHED",
                "Product does not exist in product_metadata."
            )

    # 2. Quality event -> Finished lot
    # No separate finished-lot master dataset exists in this model.
    for _, row in quality.iterrows():
        lot_id = row["finished_lot_id"]

        if pd.isna(lot_id) or not str(lot_id).strip():
            _add_issue(
                issues, "quality_events",
                row["quality_event_id"], "finished_lot_id",
                lot_id, "MISSING_RELATIONSHIP",
                "Quality event has no finished-lot reference."
            )

    # 3. Machine log -> Production order + Machine
    for _, row in machine_logs.iterrows():
        order_id = str(row["production_order_id"]).strip()
        machine_id = str(row["machine_id"]).strip()

        if (order_id, machine_id) not in order_machine_pairs:
            _add_issue(
                issues, "machine_logs",
                row["source_record_id"]
                if "source_record_id" in row.index else order_id,
                "production_order_id/machine_id",
                f"{order_id}/{machine_id}",
                "UNMATCHED",
                "No production order exists with this exact "
                "production-order and machine combination."
            )

    # 4. Engineering change -> Product
    for _, row in ecns.iterrows():
        product_id = str(row["product_id"]).strip()

        if not product_id or product_id.lower() == "nan":
            _add_issue(
                issues, "engineering_changes",
                row["ecn_id"], "product_id",
                product_id, "MISSING_RELATIONSHIP",
                "Engineering change has no product reference."
            )
        elif product_id not in product_ids:
            _add_issue(
                issues, "engineering_changes",
                row["ecn_id"], "product_id",
                product_id, "UNRESOLVED",
                "ECN product does not exist in product_metadata."
            )

    # 5. Engineering change component -> BOM
    for _, row in ecns.iterrows():
        product_id = str(row["product_id"]).strip()
        component_id = str(row["component_id"]).strip()

        if not product_id or not component_id:
            continue

        if (product_id, component_id) not in bom_product_components:
            _add_issue(
                issues, "engineering_changes",
                row["ecn_id"], "component_id",
                component_id, "UNRESOLVED",
                "ECN component could not be resolved to a BOM "
                "for the referenced product."
            )

    return pd.DataFrame(
        issues,
        columns=[
            "dataset", "record_id", "field", "value",
            "classification", "message"
        ]
    )


def load_factory_datasets(factory_dir):
    factory_dir = Path(factory_dir)

    datasets = {}
    for name in REQUIRED_DATASETS:
        path = factory_dir / f"{name}.parquet"

        if not path.exists():
            raise FileNotFoundError(
                f"Required standardized dataset not found: {path}"
            )

        datasets[name] = pd.read_parquet(path)

    return datasets


def main():
    parser = argparse.ArgumentParser(
        description="Validate cross-dataset EPTQ relationships."
    )
    parser.add_argument(
        "--factory",
        required=True,
        help="Factory ID, for example FACTORY_B."
    )
    parser.add_argument(
        "--data-root",
        default="data/standardized"
    )

    args = parser.parse_args()

    factory_dir = Path(args.data_root) / args.factory.upper()
    datasets = load_factory_datasets(factory_dir)

    issues = validate_relationships(datasets)

    output_dir = Path("data/relationship_validation") / args.factory.upper()
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "relationship_issues.csv"
    issues.to_csv(report_path, index=False)

    print("\nEPTQ RELATIONSHIP VALIDATION")
    print("----------------------------")
    print(f"Factory: {args.factory.upper()}")
    print(f"Issues found: {len(issues)}")
    print(f"Report: {report_path}")

    if issues.empty:
        print("RELATIONSHIP VALIDATION: PASS")
    else:
        print("\nIssue summary:")
        print(issues["classification"].value_counts().to_string())
        print("\nIssue details:")
        print(issues.to_string(index=False))
        print("\nRELATIONSHIP VALIDATION: ISSUES DETECTED")


if __name__ == "__main__":
    main()