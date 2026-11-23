# Standardized KPI input contract

One row represents one production order. Factory-specific adapters translate
source data into this contract; the KPI engine must not read source schemas.

| Field | Required | Meaning |
|---|---|---|
| factory_id | yes | Factory identifier |
| production_order_id | yes | Production order identifier |
| product_id | yes | Product identifier |
| product_revision | no | Revision applicable to the order |
| machine_id | no | Machine assigned to the order |
| operation_id | no | Operation identifier |
| planned_time_ms | yes | Order end minus order start, in milliseconds |
| downtime_ms | yes | Sum of downtime intervals clipped to the order window |
| total_output | yes | Total units produced, with source basis documented |
| good_quantity | no | Good units; required for unit-based quality |
| rejected_quantity | no | Rejected units, where source semantics support it |
| ideal_cycle_time_ms | no | Resolved ideal cycle time in milliseconds |
| ideal_cycle_time_rule_id | no | Rule used by the resolver |
| quality_basis | yes | Meaning/source of the quality numerator and denominator |
| input_warnings | no | Adapter data-quality warnings |

## Calculation rules

- operating_time_ms = planned_time_ms - downtime_ms.
- availability = operating_time_ms / planned_time_ms.
- performance = ideal_cycle_time_ms * total_output / operating_time_ms.
- quality = good_quantity / total_output.
- oee = availability * performance * quality.
- A KPI is null when a required input is missing, invalid, or not defensible.
- Do not cap performance or OEE silently; flag values above 1 for review.
- Downtime intervals are clipped to the production-order interval. For linked events,
  validate order and machine IDs. Avoid double counting overlapping stoppage intervals.

## Factory-specific evidence and limitations

- Factory B: total_output = good_quantity + rejected_quantity. The supplied dataset
  verifies this equals planned_quantity for all 64 orders. `quality_events` are
  inspection samples and must not be treated as total production rejects.
- Factory B: downtime is linked by production_order_id and machine_id. The supplied
  28 stoppages match their order and machine, and their timestamp durations match
  `duration_minutes`.
- Factory B: no engineering ideal-cycle-time standard is supplied in the current
  dataset. For the accelerator demonstration, the config includes clearly labelled
  provisional product-level baselines derived as the median of (order duration minus
  linked downtime) / planned quantity across the supplied Factory B orders. These are
  observed historical proxies, not approved ideal standards. They allow Performance
  and OEE to be demonstrated while preserving source/status metadata for review.
- Factory B: no operation_id is supplied; operation-level rules cannot resolve for it.
- Factory A: production orders have no machine_id/order_id in machine logs. A source
  CSV audit found 2,338/3,000 logs match no order and 82 match multiple orders by time.
  Its `defect_flag` is a log-row flag, not verified unit-level good/reject quantity.
  Do not claim reliable unit-based quality/OEE from this source without a better key
  and business confirmation.
- Factory A: the electrolyser reference formula is retained as an optional legacy
  adapter, not embedded in the common KPI engine. Factory A unit-based Quality/OEE
  remains unavailable where source log-to-order assignment is unmatched/ambiguous or
  where defect flags cannot be interpreted as rejected units.
