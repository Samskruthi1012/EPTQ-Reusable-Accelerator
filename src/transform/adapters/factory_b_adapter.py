"""Factory B adapter: standardized landing/standardized data -> KPI contract."""
from __future__ import annotations

import pandas as pd


def _merged_overlap_ms(events: pd.DataFrame, order_start: pd.Timestamp,
                       order_end: pd.Timestamp) -> float:
    """Clip stoppages to the order window and merge overlaps to avoid double count."""
    intervals = []
    for row in events.itertuples(index=False):
        start = max(pd.Timestamp(row.start_time), order_start)
        end = min(pd.Timestamp(row.end_time), order_end)
        if end > start:
            intervals.append((start, end))
    if not intervals:
        return 0.0
    intervals.sort(key=lambda item: item[0])
    merged = []
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    merged.append((current_start, current_end))
    return sum((end - start).total_seconds() * 1000 for start, end in merged)


def build_kpi_inputs(orders: pd.DataFrame, downtime: pd.DataFrame,
                     resolver=None) -> tuple[pd.DataFrame, list[str]]:
    required_orders = {"production_order_id", "product_id", "start_time", "end_time",
                       "machine_id", "good_quantity", "rejected_quantity"}
    required_downtime = {"production_order_id", "machine_id", "start_time", "end_time"}
    if missing := required_orders - set(orders.columns):
        raise ValueError(f"Factory B production_orders missing: {sorted(missing)}")
    if missing := required_downtime - set(downtime.columns):
        raise ValueError(f"Factory B downtime_events missing: {sorted(missing)}")

    orders = orders.copy()
    downtime = downtime.copy()
    for frame, columns in ((orders, ("start_time", "end_time")),
                           (downtime, ("start_time", "end_time"))):
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")

    warnings: list[str] = []
    order_keys = set(orders.production_order_id.dropna())
    missing_refs = downtime.loc[~downtime.production_order_id.isin(order_keys)]
    if not missing_refs.empty:
        warnings.append(f"{len(missing_refs)} downtime rows reference unknown production orders")

    rows = []
    for order in orders.itertuples(index=False):
        start, end = pd.Timestamp(order.start_time), pd.Timestamp(order.end_time)
        if pd.isna(start) or pd.isna(end) or end <= start:
            planned_ms = None
            warnings.append(f"{order.production_order_id}: invalid production time window")
        else:
            planned_ms = (end - start).total_seconds() * 1000

        linked = downtime[downtime.production_order_id == order.production_order_id]
        if "factory_id" in downtime.columns and hasattr(order, "factory_id"):
            linked = linked[linked.factory_id == order.factory_id]
        if not linked.empty:
            mismatches = linked[linked.machine_id != order.machine_id]
            if not mismatches.empty:
                warnings.append(f"{order.production_order_id}: {len(mismatches)} downtime machine mismatch(es) excluded")
                linked = linked[linked.machine_id == order.machine_id]
        downtime_ms = _merged_overlap_ms(linked, start, end) if planned_ms is not None else None
        good = float(order.good_quantity) if pd.notna(order.good_quantity) else None
        rejected = float(order.rejected_quantity) if pd.notna(order.rejected_quantity) else None
        total = good + rejected if good is not None and rejected is not None else None
        revision = getattr(order, "product_revision", None)
        factory_id = getattr(order, "factory_id", "FACTORY_B")
        operation_id = getattr(order, "operation_id", None)
        resolved = None
        if resolver is not None:
            resolved = resolver.resolve(factory_id=factory_id, product_id=order.product_id,
                                        machine_id=order.machine_id, operation_id=operation_id,
                                        as_of=start)
        rows.append({
            "factory_id": factory_id,
            "production_order_id": order.production_order_id,
            "product_id": order.product_id,
            "product_revision": revision,
            "machine_id": order.machine_id,
            "operation_id": operation_id,
            "planned_time_ms": planned_ms,
            "downtime_ms": downtime_ms,
            "total_output": total,
            "good_quantity": good,
            "rejected_quantity": rejected,
            "ideal_cycle_time_ms": resolved.get("ideal_cycle_time_ms") if resolved else None,
            "ideal_cycle_time_rule_id": resolved.get("rule_id") if resolved else None,
            "ideal_cycle_time_source": resolved.get("source") if resolved else None,
            "ideal_cycle_time_status": resolved.get("status") if resolved else "unconfigured",
            "quality_basis": "production_order_good_and_rejected_quantities",
            "input_warnings": "",
        })
    return pd.DataFrame(rows), warnings
