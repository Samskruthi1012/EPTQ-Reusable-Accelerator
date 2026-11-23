"""Factory A adapter using explicit production-order and machine relationships.

Factory A source records are linked by production_order_id. Ideal cycle time is
resolved exclusively through the shared configuration-driven resolver; the
optional electrolyser reference is deliberately not used here.
"""
from __future__ import annotations

import pandas as pd


def _merged_overlap_ms(
    events: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> float:
    """Return the union of downtime intervals clipped to an order window."""
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]] = []

    for row in events.itertuples(index=False):
        event_start = row.start_time
        event_end = row.end_time
        if pd.isna(event_start) or pd.isna(event_end):
            continue

        left = max(event_start, start)
        right = min(event_end, end)
        if right > left:
            intervals.append((left, right))

    if not intervals:
        return 0.0

    intervals.sort(key=lambda interval: interval[0])
    total_ms = 0.0
    current_start, current_end = intervals[0]

    for next_start, next_end in intervals[1:]:
        if next_start <= current_end:
            current_end = max(current_end, next_end)
        else:
            total_ms += (current_end - current_start).total_seconds() * 1000
            current_start, current_end = next_start, next_end

    total_ms += (current_end - current_start).total_seconds() * 1000
    return total_ms


def build_kpi_inputs(
    orders: pd.DataFrame,
    logs: pd.DataFrame,
    downtime: pd.DataFrame,
    reference: pd.DataFrame | None = None,
    resolver=None,
) -> tuple[pd.DataFrame, list[str]]:
    """Build the common KPI input contract for Factory A.

    ``reference`` remains an optional parameter for compatibility with the
    existing pipeline runner, but is intentionally ignored. Factory A ideal
    cycle time must come from the shared resolver/configuration only.
    """
    del reference  # Never use electrolyser reference values for Factory A.

    required_orders = {
        "production_order_id",
        "product_id",
        "machine_id",
        "start_time",
        "end_time",
    }
    required_logs = {
        "production_order_id",
        "machine_id",
        "event_timestamp",
        "output_count",
        "rejected_quantity",
    }
    required_downtime = {
        "production_order_id",
        "machine_id",
        "start_time",
        "end_time",
    }

    if missing := required_orders - set(orders.columns):
        raise ValueError(
            f"Factory A production_orders missing: {sorted(missing)}"
        )
    if missing := required_logs - set(logs.columns):
        raise ValueError(
            f"Factory A machine_logs missing: {sorted(missing)}"
        )
    if missing := required_downtime - set(downtime.columns):
        raise ValueError(
            f"Factory A downtime_events missing: {sorted(missing)}"
        )

    orders = orders.copy().reset_index(drop=True)
    logs = logs.copy()
    downtime = downtime.copy()

    for frame, columns in (
        (orders, ("start_time", "end_time")),
        (logs, ("event_timestamp",)),
        (downtime, ("start_time", "end_time")),
    ):
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")

    # Normalize numeric measures before aggregating.
    logs["output_count"] = pd.to_numeric(
        logs["output_count"], errors="coerce"
    ).fillna(0)
    logs["rejected_quantity"] = pd.to_numeric(
        logs["rejected_quantity"], errors="coerce"
    ).fillna(0)

    warnings: list[str] = []

    order_ids = set(orders["production_order_id"].dropna())
    log_unknown_ids = int(
        (~logs["production_order_id"].isin(order_ids)).sum()
    )
    downtime_unknown_ids = int(
        (~downtime["production_order_id"].isin(order_ids)).sum()
    )

    if log_unknown_ids:
        warnings.append(
            f"{log_unknown_ids} machine-log rows reference unknown production orders and were excluded"
        )
    if downtime_unknown_ids:
        warnings.append(
            f"{downtime_unknown_ids} downtime rows reference unknown production orders and were excluded"
        )

    # Build lookups using the explicit production-order key.
    valid_order_ids = order_ids
    logs = logs[logs["production_order_id"].isin(valid_order_ids)].copy()
    downtime = downtime[
        downtime["production_order_id"].isin(valid_order_ids)
    ].copy()

    # Check machine identity consistency for linked records.
    order_machine = orders.set_index("production_order_id")["machine_id"].to_dict()

    log_machine_mismatch = logs[
        logs.apply(
            lambda row: row["machine_id"]
            != order_machine.get(row["production_order_id"]),
            axis=1,
        )
    ]
    downtime_machine_mismatch = downtime[
        downtime.apply(
            lambda row: row["machine_id"]
            != order_machine.get(row["production_order_id"]),
            axis=1,
        )
    ]

    if not log_machine_mismatch.empty:
        warnings.append(
            f"{len(log_machine_mismatch)} machine-log rows have a machine_id inconsistent with their order and were excluded"
        )
        logs = logs.drop(index=log_machine_mismatch.index)

    if not downtime_machine_mismatch.empty:
        warnings.append(
            f"{len(downtime_machine_mismatch)} downtime rows have a machine_id inconsistent with their order and were excluded"
        )
        downtime = downtime.drop(index=downtime_machine_mismatch.index)

    logs_by_order = {
        order_id: group
        for order_id, group in logs.groupby("production_order_id", sort=False)
    }
    downtime_by_order = {
        order_id: group
        for order_id, group in downtime.groupby("production_order_id", sort=False)
    }

    rows: list[dict] = []

    for order in orders.itertuples(index=False):
        order_id = order.production_order_id
        start = order.start_time
        end = order.end_time
        machine_id = order.machine_id
        factory_id = getattr(order, "factory_id", "FACTORY_A")

        valid_window = (
            pd.notna(start)
            and pd.notna(end)
            and end > start
        )
        planned_ms = (
            (end - start).total_seconds() * 1000
            if valid_window
            else None
        )

        order_logs = logs_by_order.get(order_id, logs.iloc[0:0])
        total_output = float(order_logs["output_count"].sum())
        rejected_quantity = float(order_logs["rejected_quantity"].sum())

        # Reject invalid source quantities rather than producing negative good output.
        if rejected_quantity > total_output:
            warnings.append(
                f"Order {order_id}: rejected_quantity exceeds total_output; quality quantities were set to unavailable"
            )
            good_quantity = None
            rejected_for_kpi = None
        else:
            good_quantity = total_output - rejected_quantity
            rejected_for_kpi = rejected_quantity

        order_downtime = downtime_by_order.get(
            order_id, downtime.iloc[0:0]
        )
        downtime_ms = (
            _merged_overlap_ms(order_downtime, start, end)
            if valid_window
            else None
        )

        resolved = None
        if resolver is not None and pd.notna(start):
            resolved = resolver.resolve(
                factory_id=factory_id,
                product_id=order.product_id,
                machine_id=machine_id,
                operation_id=None,
                as_of=start,
            )

        ideal_cycle_time_ms = (
            resolved.get("ideal_cycle_time_ms") if resolved else None
        )

        rows.append(
            {
                "factory_id": factory_id,
                "production_order_id": order_id,
                "product_id": order.product_id,
                "product_revision": getattr(order, "product_revision", None),
                "machine_id": machine_id,
                "operation_id": None,
                "planned_time_ms": planned_ms,
                "downtime_ms": downtime_ms,
                "total_output": total_output,
                "good_quantity": good_quantity,
                "rejected_quantity": rejected_for_kpi,
                "defect_event_count": int(
                    (order_logs.get("defect_flag", pd.Series(dtype=object))
                     .fillna(False)
                     .astype(str)
                     .str.strip()
                     .str.lower()
                     .isin(["true", "1", "yes"])
                    ).sum()
                ),
                "ideal_cycle_time_ms": ideal_cycle_time_ms,
                "ideal_cycle_time_rule_id": (
                    resolved.get("rule_id") if resolved else None
                ),
                "ideal_cycle_time_source": (
                    resolved.get("source") if resolved else None
                ),
                "ideal_cycle_time_status": (
                    resolved.get("status") if resolved else "unconfigured"
                ),
                "quality_basis": "unit_counts_from_output_count_and_rejected_quantity",
                "input_warnings": None,
            }
        )

    if not logs.empty:
        orders_without_logs = len(
            order_ids - set(logs["production_order_id"].dropna())
        )
    else:
        orders_without_logs = len(order_ids)
    if orders_without_logs:
        warnings.append(
            f"{orders_without_logs} production orders have no linked machine-log rows"
        )

    return pd.DataFrame(rows), warnings
