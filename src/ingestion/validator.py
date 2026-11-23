
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_validation_config(validation_config_path):
    """Load the common EPTQ validation configuration."""

    config_path = Path(validation_config_path)

    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"Validation configuration not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict) or "datasets" not in config:
        raise ValueError(
            "Invalid validation configuration. "
            "A datasets section is required."
        )

    return config


def validate_field_data_type(series, data_type):
    """Check whether non-empty values match the configured standard type."""

    values = series.dropna()
    values = values[values.astype("string").str.strip() != ""]

    if values.empty:
        return []

    if data_type == "string":
        return []

    if data_type == "integer":
        numeric = pd.to_numeric(values, errors="coerce")
        invalid = numeric.isna() | (numeric % 1 != 0)

    elif data_type == "float":
        numeric = pd.to_numeric(values, errors="coerce")
        invalid = numeric.isna() | ~numeric.map(
            lambda value: pd.notna(value) and abs(value) != float("inf")
        )

    elif data_type == "boolean":
        allowed = {True, False, 1, 0, "true", "false", "1", "0"}
        invalid = ~values.map(
            lambda value: value in allowed
            if not isinstance(value, str)
            else value.strip().lower() in {"true", "false", "1", "0"}
        )

    elif data_type == "datetime":
        parsed = pd.to_datetime(values, errors="coerce")
        invalid = parsed.isna()

    else:
        raise ValueError(f"Unsupported field data type: {data_type}")

    return [
        int(position) + 1
        for position, is_invalid in zip(values.index, invalid)
        if is_invalid
    ]


def validate_source_schema(dataframe, dataset_config, dataset_name):
    """
    Validate incoming source columns against factory configuration.
    """

    if dataframe is None:
        return {
            "valid": True,
            "missing_required": [],
            "missing_optional": [],
            "extra_columns": [],
            "errors": [],
            "warnings": []
        }

    required_columns = set(
        dataset_config.get("required_columns", [])
    )

    optional_columns = set(
        dataset_config.get("optional_columns", [])
    )

    actual_columns = set(dataframe.columns)

    missing_required = sorted(
        required_columns - actual_columns
    )

    missing_optional = sorted(
        optional_columns - actual_columns
    )

    expected_columns = required_columns | optional_columns

    extra_columns = sorted(
        actual_columns - expected_columns
    )

    errors = []
    warnings = []

    if missing_required:
        errors.append(
            f"{dataset_name}: Missing required source columns: "
            f"{missing_required}"
        )

    if missing_optional:
        warnings.append(
            f"{dataset_name}: Optional source columns not present: "
            f"{missing_optional}"
        )

    allow_extra_columns = dataset_config.get(
        "allow_extra_columns", True
    )

    if extra_columns:
        message = (
            f"{dataset_name}: Unexpected extra source columns: "
            f"{extra_columns}"
        )

        if allow_extra_columns:
            warnings.append(message)
        else:
            errors.append(message)

    return {
        "valid": len(errors) == 0,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "extra_columns": extra_columns,
        "errors": errors,
        "warnings": warnings
    }


def validate_standard_dataset(
    dataframe,
    validation_config,
    dataset_name,
    entity_model=None
):
    """
    Validate mapped data against common EPTQ validation rules.

    Checks:
    - Required fields and empty values
    - Optional fields
    - Unexpected fields
    - Entity-model compatibility
    - Configured field data types
    - Duplicate values in configured unique fields
    - Values against configured allowed-value lists

    Invalid row numbers are returned using 1-based numbering.
    """

    if dataframe is None:
        return {
            "valid": True,
            "skipped": True,
            "errors": [],
            "warnings": [],
            "invalid_rows": [],
            "missing_required": [],
            "missing_optional": [],
            "extra_fields": []
        }

    datasets = validation_config.get("datasets", {})

    if dataset_name not in datasets:
        raise ValueError(
            f"No common validation rules found for dataset: "
            f"{dataset_name}"
        )

    dataset_rules = datasets[dataset_name]
    defaults = validation_config.get("defaults", {})

    errors = []
    warnings = []

    required_fields = set(
        dataset_rules.get("required_fields", [])
    )

    optional_fields = set(
        dataset_rules.get("optional_fields", [])
    )

    actual_fields = set(dataframe.columns)

    # Check required and optional standard fields.
    missing_required = sorted(
        required_fields - actual_fields
    )

    missing_optional = sorted(
        optional_fields - actual_fields
    )

    # Read the missing-column behavior from shared YAML.
    if missing_required:
        message = (
            f"{dataset_name}: Missing required standard fields: "
            f"{missing_required}"
        )

        behavior = str(
            defaults.get("missing_required_columns", "error")
        ).lower()

        if behavior == "error":
            errors.append(message)
        elif behavior == "warning":
            warnings.append(message)
        else:
            errors.append(
                f"Unsupported missing_required_columns setting: "
                f"{behavior}"
            )

    if missing_optional:
        warnings.append(
            f"{dataset_name}: Optional standard fields not present: "
            f"{missing_optional}"
        )

    # Check that the configured entity and its fields exist.
    entity_name = dataset_rules.get("entity")

    if entity_model is not None:
        entities = entity_model.get("entities", {})

        if not entity_name:
            errors.append(
                f"{dataset_name}: No standard entity configured."
            )

        elif entity_name not in entities:
            errors.append(
                f"{dataset_name}: Entity '{entity_name}' "
                f"does not exist in the common entity model."
            )

        else:
            entity_fields = set(
                entities[entity_name].get("fields", [])
            )

            invalid_fields = sorted(
                (required_fields | optional_fields)
                - entity_fields
            )

            if invalid_fields:
                errors.append(
                    f"{dataset_name}: Fields not defined in "
                    f"entity '{entity_name}': {invalid_fields}"
                )

    # Check for unexpected standardized fields.
    expected_fields = (
        required_fields | optional_fields | {"factory_id"}
    )

    extra_fields = sorted(
        actual_fields - expected_fields
    )

    allow_extra_fields = defaults.get(
        "allow_extra_columns", True
    )

    if extra_fields:
        message = (
            f"{dataset_name}: Unexpected standardized fields: "
            f"{extra_fields}"
        )

        if allow_extra_fields:
            warnings.append(message)
        else:
            errors.append(message)

    # Initialize row-level validation results.
    invalid_rows = set()
    missing_required_values = {}
    empty_optional_values = {}
    invalid_data_types = {}
    invalid_unique_values = {}
    invalid_allowed_values = {}

    # Check empty values in required fields.
    required_value_behavior = str(
        defaults.get("missing_required_values", "error")
    ).lower()

    optional_value_behavior = str(
        defaults.get("empty_optional_values", "allow")
    ).lower()

    fields_to_check = (
        (required_fields & actual_fields)
        if required_value_behavior in ("error", "warning")
        else set()
    )

    for field in sorted(fields_to_check):

        values = dataframe[field]

        empty_values = (
            values.isna()
            | values.astype("string").str.strip().eq("").fillna(False)
        )

        if empty_values.any():

            row_numbers = [
                position + 1
                for position in range(len(dataframe))
                if empty_values.iloc[position]
            ]

            missing_required_values[field] = row_numbers
            invalid_rows.update(row_numbers)

            message = (
                f"{dataset_name}: Required field '{field}' "
                f"has {len(row_numbers)} empty value(s). "
                f"Data row numbers: {row_numbers[:20]}"
            )

            if required_value_behavior == "error":
                errors.append(message)
            else:
                warnings.append(message)

    # Optional fields can allow, warn about or reject empty values.
    if optional_value_behavior in ("error", "warning"):

        for field in sorted(optional_fields & actual_fields):

            values = dataframe[field]

            empty_values = (
                values.isna()
                | values.astype("string").str.strip().eq("").fillna(False)
            )

            if empty_values.any():

                row_numbers = [
                    position + 1
                    for position in range(len(dataframe))
                    if empty_values.iloc[position]
                ]

                empty_optional_values[field] = row_numbers

                message = (
                    f"{dataset_name}: Optional field '{field}' "
                    f"has {len(row_numbers)} empty value(s). "
                    f"Data row numbers: {row_numbers[:20]}"
                )

                if optional_value_behavior == "error":
                    errors.append(message)
                    invalid_rows.update(row_numbers)
                else:
                    warnings.append(message)

    elif optional_value_behavior != "allow":
        errors.append(
            "Unsupported empty_optional_values setting: "
            f"{optional_value_behavior}"
        )

    if required_value_behavior not in ("error", "warning", "allow"):
        errors.append(
            "Unsupported missing_required_values setting: "
            f"{required_value_behavior}"
        )

    # Validate standard field data types using common configuration.
    field_types = validation_config.get("field_types", {})

    invalid_type_behavior = str(
        defaults.get("invalid_data_types", "error")
    ).lower()

    if invalid_type_behavior not in ("error", "warning", "allow"):
        errors.append(
            f"Unsupported invalid_data_types setting: "
            f"{invalid_type_behavior}"
        )

    elif invalid_type_behavior != "allow":

        for data_type, fields in field_types.items():

            for field in fields:

                if field not in dataframe.columns:
                    continue

                invalid_positions = validate_field_data_type(
                    dataframe[field], data_type
                )

                if invalid_positions:
                    invalid_data_types[field] = invalid_positions
                    invalid_rows.update(invalid_positions)

                    message = (
                        f"{dataset_name}: Field '{field}' contains "
                        f"invalid {data_type} values at rows "
                        f"{invalid_positions[:20]}"
                    )

                    if invalid_type_behavior == "error":
                        errors.append(message)
                    else:
                        warnings.append(message)

    # ---------------------------------------------------------
    # Scenario 6: Duplicate value detection.
    # ---------------------------------------------------------
    # Every row participating in a duplicate is marked invalid.
    # Empty values are excluded because required-value validation
    # handles missing IDs separately.
    unique_fields = dataset_rules.get("unique_fields", [])

    for field in unique_fields:

        if field not in dataframe.columns:
            errors.append(
                f"{dataset_name}: Configured unique field "
                f"'{field}' is missing from the dataset."
            )
            continue

        values = dataframe[field]

        non_empty_mask = (
            values.notna()
            & values.astype("string").str.strip().ne("").fillna(False)
        )

        normalized_values = (
            values.astype("string").str.strip()
        )

        duplicate_mask = (
            non_empty_mask
            & normalized_values.duplicated(keep=False)
        )

        if duplicate_mask.any():

            duplicate_positions = [
                position + 1
                for position, is_duplicate
                in enumerate(duplicate_mask.tolist())
                if is_duplicate
            ]

            invalid_unique_values[field] = duplicate_positions
            invalid_rows.update(duplicate_positions)

            duplicate_values = sorted(
                normalized_values[duplicate_mask].unique().tolist()
            )

            errors.append(
                f"{dataset_name}: Duplicate values found in unique "
                f"field '{field}'. "
                f"Duplicate values: {duplicate_values[:20]}. "
                f"Data row numbers: {duplicate_positions[:20]}"
            )

    # ---------------------------------------------------------
    # Scenario 6: Allowed-value validation.
    # ---------------------------------------------------------
    # Values are compared after trimming whitespace and converting
    # to uppercase. This allows harmless differences in casing.
    allowed_values_config = dataset_rules.get("allowed_values", {})

    for field, allowed_values in allowed_values_config.items():

        if field not in dataframe.columns:
            errors.append(
                f"{dataset_name}: Configured allowed-value field "
                f"'{field}' is missing from the dataset."
            )
            continue

        if not isinstance(allowed_values, list) or not allowed_values:
            errors.append(
                f"{dataset_name}: Allowed values for field "
                f"'{field}' must be a non-empty list."
            )
            continue

        normalized_allowed_values = {
            str(value).strip().upper()
            for value in allowed_values
        }

        values = dataframe[field]

        # Empty values are handled by required-value validation.
        non_empty_mask = (
            values.notna()
            & values.astype("string").str.strip().ne("").fillna(False)
        )

        normalized_values = (
            values.astype("string").str.strip().str.upper()
        )

        invalid_mask = (
            non_empty_mask
            & ~normalized_values.isin(normalized_allowed_values)
        )

        if invalid_mask.any():

            invalid_positions = [
                position + 1
                for position, is_invalid
                in enumerate(invalid_mask.tolist())
                if is_invalid
            ]

            invalid_values = sorted(
                values[invalid_mask].astype("string").unique().tolist()
            )

            invalid_allowed_values[field] = invalid_positions
            invalid_rows.update(invalid_positions)

            errors.append(
                f"{dataset_name}: Field '{field}' contains "
                f"values outside the allowed list. "
                f"Invalid values: {invalid_values[:20]}. "
                f"Allowed values: {sorted(normalized_allowed_values)}. "
                f"Data row numbers: {invalid_positions[:20]}"
            )

    # Return the existing validation result structure with
    # additional Scenario 6 validation details.
    return {
        "valid": len(errors) == 0,
        "skipped": False,
        "entity": entity_name,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "extra_fields": extra_fields,
        "missing_required_values": missing_required_values,
        "empty_optional_values": empty_optional_values,
        "invalid_data_types": invalid_data_types,
        "invalid_unique_values": invalid_unique_values,
        "invalid_allowed_values": invalid_allowed_values,
        "invalid_rows": sorted(invalid_rows),
        "errors": errors,
        "warnings": warnings
    }


# Load common EPTQ validation rules.
# Validate source columns separately from standardized fields.
# Check required fields and empty required values.
# Allow optional fields to be absent or empty when configured.
# Check entity-model compatibility and unexpected fields.
# Check duplicate values and configured allowed-value lists.
