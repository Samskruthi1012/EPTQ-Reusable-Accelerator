from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "engineering_changes": {
        "ecn_id", "product_id", "revision_from", "revision_to",
        "effective_date", "approval_status", "component_id",
    },
    "bom": {
        "bom_id", "product_id", "product_revision", "component_id",
    },
    "production_orders": {
        "production_order_id", "product_id", "product_revision",
        "bom_id", "start_time", "machine_id",
    },
    "machine_logs": {
        "production_order_id", "machine_id",
    },
    "quality_events": {
        "production_order_id", "machine_id", "finished_lot_id",
    },
}


def _normalise_status(value: Any) -> str:
    """Return a consistent approval status."""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def _validate_columns(
    dataset_name: str,
    dataframe: pd.DataFrame,
) -> None:
    missing = REQUIRED_COLUMNS[dataset_name] - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"{dataset_name} is missing required columns: "
            f"{', '.join(sorted(missing))}"
        )


def _filter_factory(
    dataframe: pd.DataFrame,
    factory_id: str,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Restrict a standardized dataset to the requested factory.

    If factory_id is absent, the data is treated as already factory-scoped.
    """
    if "factory_id" not in dataframe.columns:
        return dataframe.copy()

    return dataframe[
        dataframe["factory_id"].astype(str).str.upper()
        == factory_id.upper()
    ].copy()


def analyse_engineering_change(
    factory_id: str,
    ecn_id: str,
    datasets: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """
    Analyse the production and quality impact of one engineering change.

    Only APPROVED ECNs are eligible for impact analysis.

    Expected datasets:
        engineering_changes
        bom
        production_orders
        machine_logs
        quality_events
    """
    required_datasets = set(REQUIRED_COLUMNS)
    missing_datasets = required_datasets - set(datasets)

    if missing_datasets:
        raise ValueError(
            "Missing datasets: "
            + ", ".join(sorted(missing_datasets))
        )

    scoped = {}

    for name in required_datasets:
        _validate_columns(name, datasets[name])
        scoped[name] = _filter_factory(
            datasets[name], factory_id, name
        )

    ecns = scoped["engineering_changes"]

    matching_ecn = ecns[
        ecns["ecn_id"].astype(str).str.strip() == str(ecn_id).strip()
    ]

    if matching_ecn.empty:
        raise ValueError(
            f"ECN {ecn_id} was not found for factory {factory_id}."
        )

    if len(matching_ecn) > 1:
        raise ValueError(
            f"More than one ECN record found for {ecn_id} "
            f"in factory {factory_id}."
        )

    ecn = matching_ecn.iloc[0]
    status = _normalise_status(ecn["approval_status"])

    base_result = {
        "factory_id": factory_id,
        "ecn_id": ecn_id,
        "approval_status": status,
        "product_id": str(ecn["product_id"]),
        "revision_from": str(ecn["revision_from"]),
        "revision_to": str(ecn["revision_to"]),
        "effective_date": str(ecn["effective_date"]),
        "component_id": str(ecn["component_id"]),
    }

    # Approval gate: do not calculate impact for non-approved ECNs.
    if status != "APPROVED":
        return {
            **base_result,
            "status": "EXCLUDED",
            "reason": (
                f"ECN approval status is {status or 'UNKNOWN'}. "
                "Only APPROVED engineering changes are eligible "
                "for impact analysis."
            ),
            "affected_bom": pd.DataFrame(),
            "affected_orders": pd.DataFrame(),
            "affected_machine_logs": pd.DataFrame(),
            "affected_quality_events": pd.DataFrame(),
            "summary": {
                "affected_bom_count": 0,
                "affected_order_count": 0,
                "affected_machine_log_count": 0,
                "affected_quality_event_count": 0,
                "affected_finished_lot_count": 0,
            },
        }

    product_id = str(ecn["product_id"])
    target_revision = str(ecn["revision_to"])
    component_id = str(ecn["component_id"])

    effective_date = pd.to_datetime(
        ecn["effective_date"], errors="coerce"
    )

    if pd.isna(effective_date):
        raise ValueError(
            f"ECN {ecn_id} has an invalid effective date."
        )

    # Find target-revision BOMs containing the affected component.
    bom = scoped["bom"].copy()

    affected_bom = bom[
        (bom["product_id"].astype(str) == product_id)
        & (bom["product_revision"].astype(str) == target_revision)
        & (bom["component_id"].astype(str) == component_id)
    ].copy()

    affected_bom_ids = affected_bom["bom_id"].dropna().astype(str).unique()

    # Find production orders using those BOMs on/after the effective date.
    orders = scoped["production_orders"].copy()
    orders["_start_datetime"] = pd.to_datetime(
        orders["start_time"], errors="coerce"
    )

    affected_orders = orders[
        (orders["product_id"].astype(str) == product_id)
        & (orders["product_revision"].astype(str) == target_revision)
        & (orders["bom_id"].astype(str).isin(affected_bom_ids))
        & (orders["_start_datetime"] >= effective_date)
    ].copy()

    order_ids = (
        affected_orders["production_order_id"]
        .dropna().astype(str).unique()
    )

    # Trace machine telemetry using production order and machine.
    machine_logs = scoped["machine_logs"].copy()
    order_machine_pairs = affected_orders[
        ["production_order_id", "machine_id"]
    ].drop_duplicates()

    affected_machine_logs = machine_logs.merge(
        order_machine_pairs,
        on=["production_order_id", "machine_id"],
        how="inner",
    )

    # Trace quality events using production order and machine.
    quality_events = scoped["quality_events"].copy()

    affected_quality_events = quality_events.merge(
        order_machine_pairs,
        on=["production_order_id", "machine_id"],
        how="inner",
    )

    finished_lot_count = (
        affected_quality_events["finished_lot_id"]
        .dropna().astype(str).nunique()
    )

    # Remove helper column from the returned orders.
    affected_orders = affected_orders.drop(
        columns=["_start_datetime"], errors="ignore"
    )

    return {
        **base_result,
        "status": "ANALYSED",
        "reason": (
            "Approved ECN analysed using the target revision, "
            "affected component, BOM relationship and effective date."
        ),
        "affected_bom": affected_bom,
        "affected_orders": affected_orders,
        "affected_machine_logs": affected_machine_logs,
        "affected_quality_events": affected_quality_events,
        "summary": {
            "affected_bom_count": len(affected_bom),
            "affected_order_count": len(affected_orders),
            "affected_machine_log_count": len(affected_machine_logs),
            "affected_quality_event_count": len(affected_quality_events),
            "affected_finished_lot_count": finished_lot_count,
        },
    }


def _load_dataset(data_dir: Path, dataset_name: str) -> pd.DataFrame:
    """Load a standardized dataset from CSV or Parquet."""
    matches = []

    for extension in (".parquet", ".csv"):
        matches.extend(data_dir.rglob(dataset_name + extension))

    if not matches:
        raise FileNotFoundError(
            f"Could not find {dataset_name}.parquet or "
            f"{dataset_name}.csv under {data_dir}"
        )

    if len(matches) > 1:
        raise ValueError(
            f"Multiple files found for {dataset_name}: "
            + ", ".join(str(path) for path in matches)
        )

    path = matches[0]

    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)

    return pd.read_csv(path)


def load_factory_datasets(
    factory_id: str,
    data_root: str = "data/standardized",
) -> dict[str, pd.DataFrame]:
    """Load the five standardized datasets for one factory."""
    factory_dir = Path(data_root) / factory_id.upper()

    if not factory_dir.exists():
        raise FileNotFoundError(
            f"Factory data directory not found: {factory_dir}"
        )

    return {
        name: _load_dataset(factory_dir, name)
        for name in REQUIRED_COLUMNS
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse engineering change production impact."
    )
    parser.add_argument("--factory", required=True)
    parser.add_argument("--ecn", required=True)
    parser.add_argument(
        "--data-root",
        default="data/standardized",
    )

    args = parser.parse_args()

    datasets = load_factory_datasets(
        args.factory, args.data_root
    )

    result = analyse_engineering_change(
        args.factory,
        args.ecn,
        datasets,
    )

    print("\nENGINEERING CHANGE IMPACT ANALYSIS")
    print("----------------------------------")
    print(f"Factory:          {result['factory_id']}")
    print(f"ECN:              {result['ecn_id']}")
    print(f"Approval status:  {result['approval_status']}")
    print(f"Analysis status:  {result['status']}")
    print(f"Reason:           {result['reason']}")

    print("\nSUMMARY")
    for key, value in result["summary"].items():
        print(f"{key}: {value}")

    if result["status"] == "EXCLUDED":
        print("\nNEGATIVE TEST: PASS")
        print("The non-approved ECN was excluded.")
    else:
        print("\nImpact analysis completed.")

    output_dir = (
        Path("data/impact_analysis") / args.factory.upper()
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    for key in (
        "affected_bom",
        "affected_orders",
        "affected_machine_logs",
        "affected_quality_events",
    ):
        result[key].to_csv(
            output_dir / f"{args.ecn}_{key}.csv",
            index=False,
        )

    print(f"\nOutput files saved to: {output_dir}")


if __name__ == "__main__":
    main()