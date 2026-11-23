
import hashlib
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_mapping_config(mapping_config_path):
    """Load a factory's source-to-standard mapping configuration."""

    config_path = Path(mapping_config_path)

    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"Mapping configuration not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Invalid mapping configuration.")

    if "factory_id" not in config or "datasets" not in config:
        raise ValueError(
            "Mapping configuration must contain factory_id and datasets."
        )

    return config


def convert_data_type(series, data_type):
    """Convert a source column into its configured standard data type."""

    if data_type == "string":
        return series.astype("string")

    if data_type == "integer":
        numeric = pd.to_numeric(series, errors="coerce")

        invalid = series.notna() & numeric.isna()

        if invalid.any():
            raise ValueError(
                f"Invalid integer values: {series[invalid].head().tolist()}"
            )

        fractional = numeric.notna() & (numeric % 1 != 0)

        if fractional.any():
            raise ValueError(
                "Fractional values cannot be converted to integer."
            )

        return numeric.astype("Int64")

    if data_type == "float":
        numeric = pd.to_numeric(series, errors="coerce")

        invalid = series.notna() & numeric.isna()

        if invalid.any():
            raise ValueError(
                f"Invalid numeric values: {series[invalid].head().tolist()}"
            )

        return numeric.astype("Float64")

    if data_type == "datetime":
        converted = pd.to_datetime(series, errors="coerce")

        invalid = series.notna() & converted.isna()

        if invalid.any():
            raise ValueError(
                f"Invalid datetime values: {series[invalid].head().tolist()}"
            )

        return converted

    if data_type == "boolean":
        values = series.astype("string").str.strip().str.lower()

        mapping = {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False
        }

        result = values.map(mapping)

        invalid = values.notna() & result.isna()

        if invalid.any():
            raise ValueError(
                f"Invalid boolean values: {values[invalid].tolist()}"
            )

        return result.astype("boolean")

    raise ValueError(f"Unsupported data type: {data_type}")


def apply_mapping_rule(series, rule):
    """Apply an approved transformation rule to a source column."""

    if rule == "identity":
        return series

    if rule == "parse_datetime":
        return pd.to_datetime(series, errors="coerce")

    if rule == "boolean_to_approval_status":
        values = series.astype("string").str.strip().str.lower()

        mapping = {
            "true": "APPROVED",
            "1": "APPROVED",
            "yes": "APPROVED",
            "false": "PENDING",
            "0": "PENDING",
            "no": "PENDING"
        }

        result = values.map(mapping)

        invalid = values.notna() & result.isna()

        if invalid.any():
            raise ValueError(
                f"Unrecognized approval values: "
                f"{values[invalid].unique().tolist()}"
            )

        return result

    if rule == "normalize_approval_status":
        values = series.astype("string").str.strip().str.upper()

        mapping = {
            "APPROVED": "APPROVED",
            "PENDING": "PENDING",
            "REJECTED": "REJECTED",
            "APPROVE": "APPROVED",
            "WAITING": "PENDING"
        }

        result = values.map(mapping)

        # Preserve unknown statuses so the validation
        # layer can detect and quarantine invalid records.
        return result.fillna(values)

    raise ValueError(f"Unsupported mapping rule: {rule}")


def generate_deterministic_row_ids(dataframe, dataset_name):
    """
    Generate repeatable IDs for source rows without source identifiers.

    Identical duplicate rows receive different IDs using an occurrence number.
    """

    generated_ids = []
    occurrences = {}

    for row in dataframe.itertuples(index=False, name=None):

        row_content = repr(tuple(
            None if pd.isna(value) else str(value)
            for value in row
        ))

        base_value = f"{dataset_name}|{row_content}"

        occurrence = occurrences.get(base_value, 0)
        occurrences[base_value] = occurrence + 1

        unique_value = f"{base_value}|{occurrence}"

        record_id = hashlib.sha256(
            unique_value.encode("utf-8")
        ).hexdigest()

        generated_ids.append(record_id)

    return generated_ids


def map_dataset(dataframe, mapping_config, dataset_name):
    """Convert a source DataFrame into standard EPTQ fields."""

    factory_id = mapping_config["factory_id"]
    datasets = mapping_config.get("datasets", {})

    if dataset_name not in datasets:
        raise KeyError(
            f"Dataset '{dataset_name}' has no mapping configuration."
        )

    dataset_mapping = datasets[dataset_name]

    mapped_data = pd.DataFrame(index=dataframe.index)

    for field_mapping in dataset_mapping.get("mappings", []):

        source_field = field_mapping["source_field"]
        target_field = field_mapping["target_field"]
        data_type = field_mapping["data_type"]
        rule = field_mapping["rule"]

        if source_field not in dataframe.columns:

            if source_field in dataset_mapping.get("optional_fields", []):
                continue

            raise ValueError(
                f"Required mapping source column '{source_field}' "
                f"not found in dataset '{dataset_name}'."
            )

        transformed = apply_mapping_rule(
            dataframe[source_field],
            rule
        )

        mapped_data[target_field] = convert_data_type(
            transformed,
            data_type
        )

    for generated_field in dataset_mapping.get("generated_fields", []):

        target_field = generated_field["target_field"]
        rule = generated_field["rule"]

        if rule == "deterministic_row_id":
            mapped_data[target_field] = (
                generate_deterministic_row_ids(
                    dataframe,
                    dataset_name
                )
            )
        else:
            raise ValueError(
                f"Unsupported generated field rule: {rule}"
            )

    # Add factory identity to every standardized record.
    mapped_data["factory_id"] = factory_id

    return mapped_data


# Load factory-specific mapping configuration.
# Convert source columns into standard data types.
# Apply transformation rules to source values.
# Generate IDs for records without source identifiers.
# Convert source datasets into the common EPTQ structure.
# Add factory_id to identify the source factory.
