Factory B — Refactoring Test Dataset

Purpose
-------
This dataset is deliberately NOT a copy of the original POC schema.
It is designed to test whether Week-1 refactoring produces a configuration-driven,
reusable model rather than hard-coded transformations.

Core changes vs the original POC pattern
----------------------------------------
1. Different file names.
2. Different source field names.
3. Different product, machine, order, ECN and quality identifiers.
4. Multiple historical product/BOM revisions.
5. Approved and pending engineering changes.
6. Quality events added as an explicit dataset.
7. A negative test: CHG-26-074 is PENDING and must not affect production traceability.
8. Two ECNs have engineered before/after quality patterns for validation:
   - CHG-26-041 / ITM-A210: quality generally improves after REV-C.
   - CHG-26-052 / ITM-V310: quality generally worsens slightly after REV-D.
   These are associations in the synthetic data, not proof of causation.

Suggested Week-1 test
---------------------
A. Keep core accelerator model unchanged.
B. Create only mapping/configuration for Factory B fields.
C. Run existing transformations.
D. Confirm the standard model can populate:
   ECN -> Product Revision -> BOM -> Production Order -> Machine -> Finished Lot -> Quality Event.
E. Validate expected_results.csv.
F. Fail the test if developers must add Factory-B-specific if/else logic to core transformations.

Files
-----
product_master.csv
bom_structure.csv
engineering_changes.csv
production_jobs.csv
asset_telemetry.csv
stoppage_records.csv
quality_inspections.csv
field_mapping.csv
expected_results.csv
