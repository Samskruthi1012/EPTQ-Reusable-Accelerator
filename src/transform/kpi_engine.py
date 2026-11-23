"""Factory-independent production KPI calculations.

Input is one standardized row per production order. Factory-specific source
interpretation belongs in adapters, never in this module.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

REQUIRED_INPUT_COLUMNS = {
    "factory_id", "production_order_id", "product_id",
    "planned_time_ms", "downtime_ms", "total_output",
}


def _number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def calculate_order_kpis(inputs: pd.DataFrame) -> pd.DataFrame:
    """Calculate availability, performance, quality and OEE per order.

    Quality is calculated only when the adapter supplies a defensible
    good_quantity. Performance is calculated only when ideal_cycle_time_ms is
    supplied. Missing inputs remain null and are explained in kpi_status.
    """
    missing = REQUIRED_INPUT_COLUMNS - set(inputs.columns)
    if missing:
        raise ValueError(f"Missing standardized KPI input columns: {sorted(missing)}")

    results: list[dict[str, Any]] = []
    for row in inputs.to_dict(orient="records"):
        planned = _number(row.get("planned_time_ms"))
        downtime = _number(row.get("downtime_ms"))
        output = _number(row.get("total_output"))
        good = _number(row.get("good_quantity"))
        ideal = _number(row.get("ideal_cycle_time_ms"))

        operating = None
        availability = None
        performance = None
        quality = None
        oee = None
        reasons: list[str] = []

        if planned is None or planned <= 0:
            reasons.append("invalid_or_missing_planned_time")
        elif downtime is None or downtime < 0:
            reasons.append("invalid_or_missing_downtime")
        elif downtime > planned:
            reasons.append("downtime_exceeds_planned_time")
        else:
            operating = planned - downtime
            availability = operating / planned

        if output is None or output <= 0:
            reasons.append("zero_or_missing_total_output")
        if good is None:
            reasons.append("good_quantity_unavailable_quality_not_calculated")
        elif output is not None and (good < 0 or good > output):
            reasons.append("good_quantity_outside_total_output_range")
            good = None
        elif output is not None and output > 0:
            quality = good / output

        if ideal is None or ideal <= 0:
            reasons.append("ideal_cycle_time_unavailable_performance_not_calculated")
        elif operating is not None and operating > 0 and output is not None and output > 0:
            performance = (ideal * output) / operating
        elif operating == 0:
            reasons.append("zero_operating_time_performance_not_calculated")

        if performance is not None and performance > 1.0:
            reasons.append("performance_above_100_percent_review_ideal_cycle_time_or_inputs")

        if availability is not None and performance is not None and quality is not None:
            oee = availability * performance * quality
            if oee > 1.0:
                reasons.append("oee_above_100_percent_review_provisional_cycle_time_or_inputs")
        else:
            reasons.append("oee_unavailable_one_or_more_components_missing")

        result = dict(row)
        result.update({
            "operating_time_ms": operating,
            "availability": availability,
            "performance": performance,
            "quality": quality,
            "oee": oee,
            "kpi_status": "complete" if oee is not None else "partial",
            "kpi_status_reasons": ";".join(dict.fromkeys(reasons)),
        })
        results.append(result)

    return pd.DataFrame(results)


def summarize_kpis(results: pd.DataFrame, group_by: list[str] | None = None) -> pd.DataFrame:
    """Return ratio-of-sums KPI summaries (not unweighted averages of orders)."""
    group_by = group_by or []
    groups = [((), results)] if not group_by else list(results.groupby(group_by, dropna=False))
    summaries: list[dict[str, Any]] = []
    for key, frame in groups:
        if not isinstance(key, tuple):
            key = (key,)
        row: dict[str, Any] = {field: value for field, value in zip(group_by, key)}
        planned = pd.to_numeric(frame.get("planned_time_ms"), errors="coerce")
        operating = pd.to_numeric(frame.get("operating_time_ms"), errors="coerce")
        downtime = pd.to_numeric(frame.get("downtime_ms"), errors="coerce")
        output = pd.to_numeric(frame.get("total_output"), errors="coerce")
        good = pd.to_numeric(frame.get("good_quantity"), errors="coerce")
        ideal = pd.to_numeric(frame.get("ideal_cycle_time_ms"), errors="coerce")

        valid_time = planned.notna() & operating.notna() & (planned > 0) & (operating >= 0)
        valid_output = output.notna() & (output > 0)
        valid_quality = valid_output & good.notna() & (good >= 0) & (good <= output)
        valid_performance = valid_time & valid_output & ideal.notna() & (ideal > 0) & (operating > 0)

        total_planned = float(planned[valid_time].sum()) if valid_time.any() else 0.0
        total_operating = float(operating[valid_time].sum()) if valid_time.any() else 0.0
        total_output = float(output[valid_quality].sum()) if valid_quality.any() else 0.0
        total_good = float(good[valid_quality].sum()) if valid_quality.any() else 0.0
        total_ideal_output_time = float((ideal[valid_performance] * output[valid_performance]).sum()) if valid_performance.any() else 0.0
        performance_operating = float(operating[valid_performance].sum()) if valid_performance.any() else 0.0

        availability = total_operating / total_planned if total_planned > 0 else None
        performance = total_ideal_output_time / performance_operating if valid_performance.any() and performance_operating > 0 else None
        quality = total_good / total_output if valid_quality.any() and total_output > 0 else None
        oee = availability * performance * quality if None not in (availability, performance, quality) else None

        row.update({
            "order_count": int(len(frame)),
            "complete_oee_order_count": int(frame["oee"].notna().sum()) if "oee" in frame else 0,
            "planned_time_ms": total_planned,
            "operating_time_ms": total_operating,
            "downtime_ms": float(downtime.dropna().sum()) if downtime is not None else None,
            "total_output": total_output,
            "good_quantity": total_good,
            "availability": availability,
            "performance": performance,
            "quality": quality,
            "oee": oee,
        })
        summaries.append(row)
    return pd.DataFrame(summaries)
