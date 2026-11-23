
import logging
from pathlib import Path
import argparse

import yaml

from src.ingestion.reader import (
    load_factory_config,
    read_dataset
)

from src.ingestion.validator import (
    validate_source_schema,
    load_validation_config,
    validate_standard_dataset
)

from src.mapping.mapping_engine import (
    load_mapping_config,
    map_dataset
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VALIDATION_CONFIG_PATH = (
    PROJECT_ROOT / "config/common/validation_rules.yaml"
)

ENTITY_MODEL_PATH = (
    PROJECT_ROOT / "config/common/entity_model.yaml"
)


def setup_logger(factory_id):
    """Create a separate log file for each factory."""

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"ingestion.{factory_id}")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(
            log_dir / f"ingestion_{factory_id}.log",
            encoding="utf-8"
        )

        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )
        )

        logger.addHandler(handler)

    return logger


def resolve_project_path(path):
    """Resolve paths relative to the repository."""

    path = Path(path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def load_entity_model():
    """Load the common EPTQ entity model."""

    if not ENTITY_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Entity model not found: {ENTITY_MODEL_PATH}"
        )

    with open(ENTITY_MODEL_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_error_dataframe(dataframe, error_dir, filename):
    """Save invalid records in the factory-specific error folder."""

    if dataframe is not None and not dataframe.empty:
        error_file = error_dir / filename
        dataframe.to_csv(error_file, index=False)
        return error_file

    return None


def save_validation_report(
    factory_id,
    dataset_name,
    dataframe,
    validation_result,
    error_dir
):
    """Save a reusable text report for a failed source-schema validation."""

    missing_columns = validation_result.get("missing_required", [])
    available_columns = (
        sorted(dataframe.columns)
        if dataframe is not None
        else []
    )
    errors = validation_result.get("errors", [])

    report_lines = [
        f"Factory: {factory_id}",
        f"Dataset: {dataset_name}",
        "Validation stage: Source schema",
        "Status: Failed",
        "Missing required columns: "
        + (", ".join(missing_columns) if missing_columns else "None"),
        "Available columns: "
        + (", ".join(available_columns) if available_columns else "None"),
        "",
        "Validation errors:"
    ]

    if errors:
        report_lines.extend(f"- {error}" for error in errors)
    else:
        report_lines.append("- No validation error details were provided.")

    report_path = error_dir / f"{dataset_name}_validation_report.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return report_path


def run_ingestion(factory_config_path):
    """
    Run the configuration-driven EPTQ pipeline for one factory.

    Reads, validates, maps and stores configured datasets.
    """

    config = load_factory_config(factory_config_path)

    factory_id = config["factory"]["factory_id"]
    logger = setup_logger(factory_id)

    # Load the factory-specific mapping configuration.
    mapping_path = config.get("mapping_config")

    if not mapping_path:
        raise ValueError(
            f"Mapping configuration is missing for {factory_id}."
        )

    mapping_config = load_mapping_config(mapping_path)

    if mapping_config.get("factory_id") != factory_id:
        raise ValueError(
            "Factory ID mismatch between factory and mapping "
            f"configurations: {factory_id} != "
            f"{mapping_config.get('factory_id')}"
        )

    # Load shared EPTQ validation rules and entity definitions.
    validation_config = load_validation_config(
        VALIDATION_CONFIG_PATH
    )

    entity_model = load_entity_model()

    output_config = config.get("output", {})

    landing_root = resolve_project_path(
        output_config.get("landing_path", "data/landing")
    )

    error_root = resolve_project_path(
        output_config.get("error_path", "data/errors")
    )

    standardized_root = resolve_project_path(
        output_config.get(
            "standardized_path",
            "data/standardized"
        )
    )

    landing_dir = landing_root / factory_id
    error_dir = error_root / factory_id
    standardized_dir = standardized_root / factory_id

    landing_dir.mkdir(parents=True, exist_ok=True)
    error_dir.mkdir(parents=True, exist_ok=True)
    standardized_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "factory_id": factory_id,
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "valid_records": 0,
        "invalid_records": 0
    }

    logger.info(
        "Starting EPTQ pipeline for %s",
        factory_id
    )

    for dataset_name, dataset_config in config["datasets"].items():

        logger.info("Processing dataset: %s", dataset_name)

        try:
            # Step 1: Read source data.
            dataframe = read_dataset(config, dataset_name)

            if dataframe is None:
                summary["skipped"] += 1

                logger.info(
                    "Skipped optional dataset: %s",
                    dataset_name
                )

                continue

            # Step 2: Validate original source columns.
            source_validation = validate_source_schema(
                dataframe,
                dataset_config,
                dataset_name
            )

            for warning in source_validation["warnings"]:
                logger.warning(warning)

            if not source_validation["valid"]:

                for error in source_validation["errors"]:
                    logger.error(error)

                save_error_dataframe(
                    dataframe,
                    error_dir,
                    f"{dataset_name}_source_error.csv"
                )

                report_path = save_validation_report(
                    factory_id,
                    dataset_name,
                    dataframe,
                    source_validation,
                    error_dir
                )
                logger.info("Validation report saved: %s", report_path)

                summary["failed"] += 1
                continue

            # Step 3: Preserve original source data.
            raw_dataframe = dataframe.copy()

            if "factory_id" in raw_dataframe.columns:
                if not raw_dataframe["factory_id"].eq(
                    factory_id
                ).all():
                    raise ValueError(
                        "Source data contains a conflicting factory_id."
                    )
            else:
                raw_dataframe["factory_id"] = factory_id

            raw_file = (
                landing_dir / f"{dataset_name}.parquet"
            )

            raw_dataframe.to_parquet(
                raw_file,
                index=False
            )

            # Step 4: Map source fields into standard EPTQ fields.
            mapped_dataframe = map_dataset(
                dataframe,
                mapping_config,
                dataset_name
            )

            # Step 5: Validate standardized records.
            standard_validation = validate_standard_dataset(
                mapped_dataframe,
                validation_config,
                dataset_name,
                entity_model
            )

            for warning in standard_validation["warnings"]:
                logger.warning(warning)

            if not standard_validation["valid"]:

                for error in standard_validation["errors"]:
                    logger.error(error)

                invalid_rows = (
                    standard_validation.get("invalid_rows", [])
                )

                defaults = validation_config.get("defaults", {})

                allow_extra = defaults.get(
                    "allow_extra_columns", True
                )

                # Determine whether the failure is structural.
                structural_failure = (
                    bool(standard_validation["missing_required"])
                    or (
                        bool(standard_validation["extra_fields"])
                        and not allow_extra
                    )
                )

                # Entity configuration errors are structural too.
                if standard_validation.get("entity"):
                    entity_exists = (
                        standard_validation["entity"]
                        in entity_model.get("entities", {})
                    )

                    if not entity_exists:
                        structural_failure = True

                else:
                    structural_failure = True

                # Only split records when errors are row-specific.
                if invalid_rows and not structural_failure:

                    invalid_positions = [
                        row_number - 1
                        for row_number in invalid_rows
                    ]

                    invalid_dataframe = mapped_dataframe.iloc[
                        invalid_positions
                    ].copy()

                    # Identify positions that passed validation.
                    invalid_position_set = set(invalid_positions)

                    valid_positions = [
                        position
                        for position in range(len(mapped_dataframe))
                        if position not in invalid_position_set
                    ]

                    # Keep only valid rows using positional indexing.
                    valid_dataframe = mapped_dataframe.iloc[valid_positions].copy()
                    # Save valid records separately.
                    if not valid_dataframe.empty:

                        standardized_file = (
                            standardized_dir /
                            f"{dataset_name}.parquet"
                        )

                        valid_dataframe.to_parquet(
                            standardized_file,
                            index=False
                        )

                        summary["valid_records"] += len(
                            valid_dataframe
                        )

                else:
                    # Structural errors invalidate the whole dataset.
                    invalid_dataframe = mapped_dataframe.copy()

                    valid_dataframe = None

                save_error_dataframe(
                    invalid_dataframe,
                    error_dir,
                    f"{dataset_name}_standard_error.csv"
                )

                summary["invalid_records"] += len(
                    invalid_dataframe
                )

                summary["failed"] += 1
                continue

            # Step 6: Save fully validated standardized data.
            standardized_file = (
                standardized_dir /
                f"{dataset_name}.parquet"
            )

            mapped_dataframe.to_parquet(
                standardized_file,
                index=False
            )

            summary["valid_records"] += len(
                mapped_dataframe
            )

            logger.info(
                "Successfully processed %s. Raw: %s, "
                "Standardized: %s",
                dataset_name,
                raw_file,
                standardized_file
            )

            summary["processed"] += 1

        except Exception as error:

            logger.exception(
                "Failed to process dataset %s: %s",
                dataset_name,
                error
            )

            summary["failed"] += 1

    logger.info(
        "EPTQ pipeline completed for %s. Summary: %s",
        factory_id,
        summary
    )

    print(f"\nEPTQ pipeline summary for {factory_id}")
    print(f"Processed: {summary['processed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Valid records: {summary['valid_records']}")
    print(f"Invalid records: {summary['invalid_records']}")
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Run the configuration-driven EPTQ ingestion pipeline."
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to the factory configuration YAML file."
    )

    args = parser.parse_args()

    summary = run_ingestion(args.config)

    if summary["failed"] > 0:
        raise SystemExit(1)

    if summary["processed"] == 0 and summary["skipped"] == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()



# Load factory and mapping configurations.
# Preserve raw source data separately for every factory.
# Convert factory-specific fields into standard EPTQ fields.
# Validate mapped records against shared validation rules.
# Save valid records and invalid records separately.
# Keep factory-specific outputs and logs isolated.
# resolve_project_path() resolves paths relative to the project.
# map_dataset() converts factory-specific fields into standard fields.
# validate_standard_dataset() checks standard EPTQ requirements.
# Structural errors reject the dataset; row-level errors isolate bad records.
# factory_id keeps records from different factories separate.