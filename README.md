# EPTQ Manufacturing Intelligence Accelerator

## 1. Overview

The **Engineering-to-Production-to-Quality (EPTQ) Manufacturing Intelligence Accelerator** is a reusable data solution designed to connect engineering changes with production operations and quality outcomes.

The solution integrates data from Manufacturing Execution Systems (MES) and Product Lifecycle Management (PLM) sources to establish traceability across:

- Engineering Change Notices (ECNs)
- Products and Bill of Materials (BOM)
- Production Orders
- Machines and Machine Logs
- Quality Events and Inspections
- Finished Lots

The objective is to establish a reusable manufacturing data foundation that can be extended across multiple factories with different source systems, schemas and data structures.

The accelerator is designed to work on top of data platforms such as Microsoft Fabric or Databricks rather than replacing the underlying data platform.

## 2. Key Objectives

- Establish a standardized manufacturing entity model.
- Support ingestion of multiple different source datasets.
- Provide configuration-driven source-to-standard data mapping.
- Support factory-specific data adapters.
- Validate source schemas, data quality and entity relationships.
- Establish engineering change traceability.
- Apply BOM revision and effective-date logic.
- Provide a KPI computation foundation.
- Support automated regression testing through CI.

## 3. Solution Architecture

The solution follows a modular architecture with separate responsibilities for configuration, ingestion, mapping, validation, transformation and KPI computation.

### High-Level Data Flow

```text
MES / PLM Source Systems
          |
          v
    Raw Data Layer
          |
          v
   Data Ingestion
          |
          v
   Schema Validation
          |
          v
    Landing Layer
          |
          v
    Mapping Engine
          |
          v
 Standardized Data Model
          |
          +----------------------+
          |                      |
          v                      v
 Relationship Validation   Engineering Change
                            Impact Analysis
          |                      |
          +----------+-----------+
                     |
                     v
              KPI Processing
                     |
                     v
             Curated KPI Output
```

The architecture separates factory-specific source handling from shared transformation and analytical components.

## 4. Repository Structure

```text
mes-plm-data-pipeline/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── config/
│   ├── common/
│   │   ├── entity_model.yaml
│   │   └── validation_rules.yaml
│   │
│   ├── factories/
│   │   ├── factory_a.yaml
│   │   ├── factory_b.yaml
│   │   ├── factory_b_negative_test.yaml
│   │   ├── factory_c.yaml
│   │   └── FACTORY_B_SCENARIO6_TEST.yaml
│   │
│   ├── kpi/
│   │   ├── factory_adapters.yaml
│   │   └── ideal_cycle_time.yaml
│   │
│   └── mappings/
│       ├── factory_a_mapping.yaml
│       ├── factory_b_mapping.yaml
│       └── factory_c_mapping.yaml
│
├── data/
│   ├── raw/
│   │   ├── mes/
│   │   │   ├── downtime_events.csv
│   │   │   ├── machine_logs.csv
│   │   │   └── production_orders.csv
│   │   │
│   │   ├── plm/
│   │   │   ├── bom.csv
│   │   │   ├── ecn_requests.csv
│   │   │   └── product_metadata.csv
│   │   │
│   │   └── electrolyser_reference.csv
│   │
│   ├── landing/
│   │   ├── FACTORY_A/
│   │   ├── FACTORY_B/
│   │   ├── FACTORY_C/
│   │   └── [Parquet datasets]
│   │
│   ├── standardized/
│   │   ├── FACTORY_A/
│   │   ├── FACTORY_B/
│   │   └── FACTORY_C/
│   │
│   ├── curated/
│   │   └── kpi/
│   │       ├── FACTORY_A/
│   │       └── FACTORY_B/
│   │
│   ├── errors/
│   ├── impact_analysis/
│   │   └── FACTORY_B/
│   │
│   ├── relationship_validation/
│   │   └── FACTORY_B/
│   │
│   ├── scenario6_test/
│   │   ├── source/
│   │   ├── landing/
│   │   ├── standardized/
│   │   └── errors/
│   │
│   └── temp_scenario1_negative/
│       ├── FACTORY_B_SOURCE/
│       ├── landing/
│       ├── standardized/
│       └── errors/
│
├── docs/
│   └── KPI_REFACTOR_README.md
│
├── powerbi/
│   └── powerbi.md
│
├── src/
│   ├── data_gen/
│   │   ├── generate_electrolyser_reference.py
│   │   ├── synthetic_data.py
│   │   └── synthetic_data.ipynb
│   │
│   ├── etl/
│   │   ├── ingest_electrolyser_reference.py
│   │   ├── ingest_mes.py
│   │   └── ingest_plm.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── ingestion_engine.py
│   │   ├── reader.py
│   │   └── validator.py
│   │
│   ├── mapping/
│   │   ├── __init__.py
│   │   └── mapping_engine.py
│   │
│   ├── transform/
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── factory_a_adapter.py
│   │   │   └── factory_b_adapter.py
│   │   │
│   │   ├── engineering_change_impact.py
│   │   ├── ideal_cycle_time_resolver.py
│   │   ├── kpi_engine.py
│   │   ├── kpi_input_contract.md
│   │   ├── run_kpi_pipeline.py
│   │   ├── transform_kpis.py
│   │   └── transform_kpis_legacy.py
│   │
│   └── validation/
│       └── relationship_validator.py
│
├── tests/
│   ├── __init__.py
│   ├── test_engineering_change_impact.py
│   ├── test_factory_b_dataset_integration.py
│   ├── test_kpi_adapter_registry.py
│   ├── test_kpi_adapters.py
│   ├── test_kpi_engine.py
│   ├── test_relationship_validator.py
│   └── test_scenario8_regression.py
│
├── Factory_B_Refactoring_Test_Dataset_CSVs/
│   ├── README.txt
│   ├── asset_telemetry.csv
│   ├── bom_structure.csv
│   ├── engineering_changes.csv
│   ├── expected_results.csv
│   ├── field_mapping.csv
│   ├── product_master.csv
│   ├── production_jobs.csv
│   ├── quality_inspections.csv
│   └── stoppage_records.csv
│
├── logs/
│
├── .gitignore
├── README.md
└── requirements.txt
```

### Directory Responsibilities

| Directory | Responsibility |
|---|---|
| `config/` | Shared, factory-specific, mapping and KPI configurations |
| `data/raw/` | Original MES and PLM source datasets |
| `data/landing/` | Ingested Parquet datasets |
| `data/standardized/` | Standardized factory datasets |
| `data/curated/` | Curated production KPI outputs |
| `data/errors/` | Invalid data and error outputs |
| `data/impact_analysis/` | Engineering change impact results |
| `data/relationship_validation/` | Relationship validation results |
| `src/data_gen/` | Synthetic manufacturing data generation |
| `src/etl/` | Existing source-specific ingestion scripts |
| `src/ingestion/` | Shared ingestion components |
| `src/mapping/` | Source-to-standard mapping engine |
| `src/transform/` | Engineering change and KPI transformation components |
| `src/validation/` | Manufacturing relationship validation |
| `tests/` | Unit, integration and regression tests |
| `docs/` | Project and implementation documentation |
| `powerbi/` | Power BI-related documentation |
| `.github/workflows/` | Automated CI workflow |

*Note: Data output directories contain generated files and may be populated during pipeline execution. The folder structure above reflects the uploaded repository, not a proposed future architecture.*

## 5. Core Components

### 5.1 Configuration Management

The `config/` directory maintains shared and factory-specific configuration.

**Common configuration**

- Standard manufacturing entity definitions.
- Shared validation rules.

**Factory configuration**

- Factory-specific source definitions.
- Dataset and schema configuration.
- Input and output locations.

**Mapping configuration**

- Source field mappings to standardized fields.

**KPI configuration**

- Factory adapter registration.
- Ideal cycle-time configuration.

The configuration-driven approach is intended to reduce factory-specific conditions in shared processing logic.

### 5.2 Data Ingestion

Location: `src/ingestion/`

The ingestion component is responsible for:

- Reading source datasets.
- Loading MES and PLM files.
- Validating required source fields.
- Converting supported source datasets into Parquet.
- Separating invalid records and datasets.
- Maintaining ingestion execution logs.

Main modules:

- `ingestion_engine.py`
- `reader.py`
- `validator.py`

### 5.3 Data Mapping

Location: `src/mapping/`

The mapping component translates factory-specific source fields into the standardized manufacturing data structure.

Main module:

- `mapping_engine.py`

Factory mappings are maintained separately under `config/mappings/`.

### 5.4 Relationship Validation

Location: `src/validation/`

The relationship validation component checks relationships between manufacturing entities.

Main module:

- `relationship_validator.py`

It supports validation of missing and unmatched relationships between relevant manufacturing datasets.

### 5.5 Engineering Change Impact Analysis

Location: `src/transform/engineering_change_impact.py`

This component supports engineering change traceability by examining relationships between:

- Engineering Change Notices
- BOM revisions
- Production Orders
- Machine Logs
- Quality Events
- Finished Lots

The implementation includes approved and pending engineering change handling, along with BOM revision and effective-date checks.

Pending engineering changes are excluded from approved-change impact analysis.

### 5.6 Factory-Specific KPI Adapters

Location: `src/transform/adapters/`

Factory adapters handle differences in source data structures and manufacturing relationships.

Current adapter modules:

- `factory_a_adapter.py`
- `factory_b_adapter.py`

The adapters provide a common interface for the shared KPI processing layer while handling factory-specific data requirements.

### 5.7 Shared KPI Processing

Main modules:

- `kpi_engine.py`
- `ideal_cycle_time_resolver.py`
- `run_kpi_pipeline.py`

The KPI architecture separates factory-specific input preparation from shared KPI processing.

The KPI input contract is documented in:

`src/transform/kpi_input_contract.md`

The intended output grain is one record per production order.

**KPI business definitions and transformation logic remain subject to validation and approval.**

## 6. Factory Onboarding Approach

The solution is designed to support multiple factories through configuration and adapter-based integration.

| Factory   | Implementation focus                                                     |
| --------- | ------------------------------------------------------------------------ |
| Factory A | MES/PLM source handling and factory-specific KPI adapter                 |
| Factory B | Source mapping, order-level production and quality data, KPI integration |
| Factory C | Factory configuration and mapping foundation                             |

The intended onboarding approach is:

1. Define the factory configuration.
2. Identify source datasets and schemas.
3. Configure source-to-standard mappings.
4. Define validation requirements.
5. Register the appropriate factory adapter.
6. Validate relationships and standardized outputs.
7. Integrate the factory into the shared processing pipeline.

New factory integrations should primarily require configuration and adapter extensions rather than changes to shared processing logic.

## 7. Data Quality and Validation

The solution includes validation capabilities for:

- Required source columns.
- Invalid and missing values.
- Duplicate identifiers.
- Allowed values.
- Missing manufacturing relationships.
- Unmatched entity references.
- BOM revision consistency.
- Engineering change approval status.

Invalid records are handled through validation and error-reporting mechanisms rather than silently accepted into standardized outputs.

## 8. KPI Definitions and Data Limitations

KPI interpretation depends on the availability and reliability of source data.

### Factory A

Machine logs do not provide reliable production-order linkage for every record. Therefore, timestamp-based matching alone cannot establish reliable order-level quality or OEE for all records.

The `defect_flag` in machine logs must not automatically be interpreted as verified unit-level rejected quantity.

### Factory B

Factory B provides order-level good and rejected quantity information. Quality inspection records represent samples and should not be interpreted as total rejected production.

Ideal cycle-time baselines currently use historical proxies and should not be treated as approved engineering standards.

Some calculated Performance and OEE values exceed 100%. These should be flagged for review rather than silently capped.

### KPI Interpretation

KPI results must be interpreted in the context of source-data availability, relationship quality, approved business definitions and validated manufacturing assumptions.

## 9. Engineering Change Traceability

Engineering change analysis follows the relationship between an approved engineering change and the affected production records.

The implementation includes:

- Approved ECN filtering.
- Pending ECN exclusion.
- BOM revision checks.
- Effective-date validation.
- Production-order relationship analysis.
- Related machine, quality and finished-lot record analysis.

The current implementation has been validated through defined test scenarios. Manual relationship checks and available dataset limitations should be considered when interpreting results.

## 10. Automated Regression Testing

The repository includes automated tests covering key solution behavior.

Test areas include:

- Factory B source mapping.
- Factory B dataset integration.
- KPI engine and factory adapters.
- Adapter registry.
- Approved engineering change handling.
- Pending engineering change exclusion.
- BOM revision and effective-date logic.
- Missing and unmatched relationship handling.
- Duplicate production-order detection.
- Invalid data validation.

### Running Tests Locally

Install dependencies:

```bash
pip install -r requirements.txt
pip install pytest flake8
```

Run the regression tests:

```bash
python -m pytest tests/ -v --tb=short -k "not test_factory_a_does_not_turn_defect_flags_into_unit_quality"
```

The excluded Factory A test remains pending fixture correction and should not be interpreted as a passing test.

### GitHub Actions

The CI workflow is maintained at:

`.github/workflows/ci.yml`

The workflow is configured to run on pushes and pull requests targeting `main`.

It includes:

- Python environment setup.
- Dependency installation.
- Critical Flake8 checks.
- Python compilation checks.
- Unit tests.
- Factory mapping and integration tests.
- Relationship validation tests.
- Engineering change and business-rule tests.

Critical test failures cause the workflow to fail.

GitHub branch protection and required status checks must be configured separately to enforce successful CI before merging.

## 11. Technology Stack

| Area                 | Technology                |
| -------------------- | ------------------------- |
| Programming Language | Python                    |
| Data Processing      | Pandas                    |
| Data Storage         | CSV, Parquet              |
| Configuration        | YAML                      |
| Data Validation      | Python validation modules |
| Version Control      | Git and GitHub            |
| CI/CD                | GitHub Actions            |
| Testing              | Pytest                    |
| Code Quality         | Flake8                    |
| Analytical Domain    | Manufacturing MES and PLM |

## 12. Getting Started

### Prerequisites

- Python 3.11
- Git
- Access to the repository
- Required source datasets or test fixtures

### Clone the Repository

```bash
git clone https://github.com/ARKTECQ/mes-plm-data-pipeline.git
cd mes-plm-data-pipeline
```

### Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Review Factory Configurations

Factory-specific configurations are maintained under:

```text
config/factories/
```

Source-to-standard mappings are maintained under:

```text
config/mappings/
```

Review the relevant factory configuration and dataset paths before executing ingestion or transformation workflows.

## 13. Current Implementation Scope

The current repository establishes the foundation for a reusable EPTQ accelerator.

Implemented areas include:

- Modular ingestion architecture.
- Configuration-driven source mappings.
- Factory-specific adapters.
- Standardized manufacturing entity definitions.
- Relationship validation.
- Engineering change impact analysis.
- KPI engine foundation.
- Automated regression test coverage.
- GitHub Actions CI workflow.

Some areas remain subject to further development and business validation, including:

- Complete production-grade onboarding across additional factories.
- Approved ideal cycle-time standards.
- Final KPI business-rule approval.
- Reliable unit-level quality linkage where source relationships are incomplete.
- Full integration of all validation stages into an end-to-end production pipeline.

## 14. Project Direction

The long-term direction is to establish a reusable manufacturing intelligence foundation that can be extended across factories, production lines and source systems.

The accelerator aims to provide standardized manufacturing entities, reusable mappings, validation rules, engineering change traceability and KPI definitions while allowing factory-specific differences to be handled through configuration and adapters.

The architecture is intended to support future expansion without repeatedly redesigning the core ingestion, mapping and transformation components.
