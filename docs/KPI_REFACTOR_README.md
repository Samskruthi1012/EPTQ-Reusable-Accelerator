# EPTQ KPI Refactor – Implementation Notes

## What changed

- Factory-specific preparation is isolated in `src/transform/adapters/`.
- `src/transform/kpi_engine.py` calculates Availability, Performance, Quality and OEE from one standardized per-order input contract.
- `src/transform/ideal_cycle_time_resolver.py` resolves factory-, product-, machine-, operation- and combined-scope rules from `config/kpi/ideal_cycle_time.yaml`.
- The electrolyser reference formula remains an optional Factory A adapter input; the reusable engine does not read electrolyser-specific fields.
- The legacy POC script is retained as `src/transform/transform_kpis_legacy.py` for reference.

## Factory B ideal cycle time used for this accelerator run

The supplied Factory B dataset does not contain an engineered ideal-cycle-time standard. To produce a complete demonstration KPI/OEE output, product-level provisional baselines are populated in `config/kpi/ideal_cycle_time.yaml`.

Each baseline is the median across that product's 16 production orders of:

`(order duration - linked downtime) / (good quantity + rejected quantity)`

The resulting values are marked `status: provisional` and source `factory_b_historical_order_duration_proxy`. They are observed historical run-time-per-unit proxies, **not approved engineering ideal standards**. They are explicitly visible in each output row as `ideal_cycle_time_status=provisional` and `ideal_cycle_time_source`.

This is suitable for a transparent accelerator demonstration and for validating the calculation flow. Replace these values with governed ideal standards when available. The resolver already supports effective dates, version, owner, source, approval status, and approval metadata.

## Factory B data validation

- 64 production orders processed.
- For all 64 orders, `good_quantity + rejected_quantity = planned_quantity` in the supplied dataset.
- 28 stoppage records link to existing production orders and matching machine IDs.
- Stoppage start/end intervals match their supplied `duration_min` values.
- Downtime is clipped to the production-order window and overlapping stoppage intervals are merged to avoid double counting.
- `quality_events` are inspection samples; they are not used as total production rejects.

## KPI formulas

- `operating_time_ms = planned_time_ms - downtime_ms`
- `availability = operating_time_ms / planned_time_ms`
- `performance = ideal_cycle_time_ms * total_output / operating_time_ms`
- `quality = good_quantity / total_output`
- `oee = availability * performance * quality`

Performance above 100% is not silently capped; it is flagged for review.

## Run on Windows PowerShell

From the repository root:

```powershell
python -m unittest discover -s tests -v
python -m src.transform.transform_kpis --factory FACTORY_B
```

Outputs are written to `data/curated/kpi/FACTORY_B/`:

- `production_order_kpis.parquet`
- `production_order_kpis.csv`
- `kpi_summary.csv`
- `kpi_product_summary.csv`
- `kpi_run_report.txt`

Run Factory A with `--factory FACTORY_A`. Factory A's source log data has no production-order key and its `defect_flag` is not a verified unit-level reject count; therefore unit-based Quality and OEE are intentionally left unavailable where the adapter cannot support them defensibly.

## Current Factory B result from the bundled CSV source data

The integration test computes all 64 order-level rows. The ratio-of-sums factory summary is:

| KPI | Result |
|---|---:|
| Availability | 97.2188% |
| Performance | 100.3505% |
| Quality | 96.5022% |
| OEE | 94.1471% |

These Performance/OEE figures use the provisional product baselines described above. Some individual orders exceed 100% Performance; those rows are flagged for review rather than capped.


## Configuration-driven factory adapter registry

Factory selection is configured in `config/kpi/factory_adapters.yaml`. The runner
loads the configured adapter module dynamically and passes the configured
standardized datasets as keyword arguments to its `build_kpi_inputs` function.
The runner contains no Factory A/Factory B conditional branches.

To onboard another factory:

1. Implement `src.transform.adapters.<factory>_adapter` with a
   `build_kpi_inputs(**configured_inputs, resolver=resolver)` function.
2. Add the factory ID, adapter module, and input dataset argument-to-file mapping
   under `factories` in `config/kpi/factory_adapters.yaml`.
3. Ensure its adapter returns the common KPI input contract documented in
   `src/transform/kpi_input_contract.md`.
4. Add that factory's ideal-cycle-time rules to `config/kpi/ideal_cycle_time.yaml`.
5. Run the unit and factory integration tests.

The common KPI engine and pipeline runner do not need factory-specific code
changes for a newly registered adapter. The adapter itself remains the place for
source-schema-specific normalization.

List registered factories with:

```powershell
python -m src.transform.transform_kpis --list-factories
```

Run a registered factory with:

```powershell
python -m src.transform.transform_kpis --factory FACTORY_B
```
