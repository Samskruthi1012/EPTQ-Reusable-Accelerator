"""Run the reusable KPI pipeline using a configuration-driven adapter registry."""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.transform.kpi_engine import calculate_order_kpis, summarize_kpis
from src.transform.ideal_cycle_time_resolver import IdealCycleTimeResolver

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = Path("config/kpi/factory_adapters.yaml")
DEFAULT_IDEAL_CYCLE_CONFIG = Path("config/kpi/ideal_cycle_time.yaml")


def load_registry(project_root: Path = PROJECT_ROOT,
                  registry_path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    path = project_root / registry_path
    if not path.exists():
        raise FileNotFoundError(f"Factory adapter registry not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        registry = yaml.safe_load(handle) or {}
    factories = registry.get("factories", {})
    if not isinstance(factories, dict) or not factories:
        raise ValueError(f"No factories configured in adapter registry: {path}")
    return factories


def read_parquet(path: Path, required: bool = True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required standardized dataset not found: {path}")
        return None
    return pd.read_parquet(path)


def available_factories(project_root: Path = PROJECT_ROOT) -> list[str]:
    return sorted(load_registry(project_root).keys())


def run(factory_id: str, project_root: Path = PROJECT_ROOT) -> Path:
    factory_id = factory_id.upper()
    registry = load_registry(project_root)
    if factory_id not in registry:
        raise ValueError(
            f"Factory '{factory_id}' is not registered. Registered factories: "
            f"{', '.join(sorted(registry))}"
        )

    factory_config = registry[factory_id]
    adapter_module_name = factory_config.get("adapter_module")
    if not adapter_module_name:
        raise ValueError(f"No adapter_module configured for {factory_id}")
    adapter_module = importlib.import_module(adapter_module_name)
    adapter_builder = getattr(adapter_module, "build_kpi_inputs", None)
    if not callable(adapter_builder):
        raise TypeError(
            f"Adapter '{adapter_module_name}' must expose callable build_kpi_inputs"
        )

    base = project_root / "data" / "standardized" / factory_id
    adapter_inputs: dict[str, Any] = {}
    for argument_name, dataset_config in factory_config.get("input_datasets", {}).items():
        if isinstance(dataset_config, str):
            dataset_file, required = dataset_config, True
        else:
            dataset_file = dataset_config.get("file")
            required = bool(dataset_config.get("required", True))
        if not dataset_file:
            raise ValueError(
                f"Missing file setting for {factory_id}.input_datasets.{argument_name}"
            )
        adapter_inputs[argument_name] = read_parquet(base / dataset_file, required=required)

    resolver = IdealCycleTimeResolver(project_root / DEFAULT_IDEAL_CYCLE_CONFIG)
    inputs, adapter_warnings = adapter_builder(**adapter_inputs, resolver=resolver)
    results = calculate_order_kpis(inputs)
    results["performance_warning"] = results["performance"].gt(1.0).fillna(False)
    results["oee_warning"] = results["oee"].gt(1.0).fillna(False)

    output_dir = project_root / "data" / "curated" / "kpi" / factory_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "production_order_kpis.parquet"
    results.to_parquet(output_path, index=False)
    results.to_csv(output_dir / "production_order_kpis.csv", index=False)
    summary = summarize_kpis(results)
    product_summary = summarize_kpis(results, ["product_id"])
    summary_path = output_dir / "kpi_summary.csv"
    summary.to_csv(summary_path, index=False)
    product_summary.to_csv(output_dir / "kpi_product_summary.csv", index=False)

    statuses = results.get("kpi_status", pd.Series(dtype=str))
    cycle_status = results.get("ideal_cycle_time_status", pd.Series(dtype=str))
    diagnostics = [
        f"Factory: {factory_id}",
        f"Adapter: {adapter_module_name}",
        f"Orders processed: {len(results)}",
        f"Complete OEE rows: {(statuses == 'complete').sum()}",
        f"Partial KPI rows: {(statuses == 'partial').sum()}",
        f"Provisional ideal-cycle-time rows: {(cycle_status == 'provisional').sum()}",
        f"Performance > 100% rows: {int(results.performance_warning.sum())}",
        f"OEE > 100% rows: {int(results.oee_warning.sum())}",
        "Factory KPI summary:",
        summary.to_string(index=False),
        "Adapter warnings:",
    ] + [f"- {warning}" for warning in adapter_warnings]
    (output_dir / "kpi_run_report.txt").write_text(
        "\n".join(diagnostics) + "\n", encoding="utf-8"
    )
    print("\n".join(diagnostics))
    print(f"Output: {output_path}")
    print(f"Summary: {summary_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate standardized production KPIs")
    parser.add_argument("--factory", help="Factory ID registered in config/kpi/factory_adapters.yaml")
    parser.add_argument("--list-factories", action="store_true", help="List registered factory IDs")
    args = parser.parse_args()
    if args.list_factories:
        print("\n".join(available_factories()))
        return
    if not args.factory:
        parser.error("--factory is required unless --list-factories is used")
    run(args.factory)


if __name__ == "__main__":
    main()
