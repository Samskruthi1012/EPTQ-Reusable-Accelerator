

from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_factory_config(factory_config_path):
    """Load a factory-specific YAML configuration."""

    config_path = Path(factory_config_path)

    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"Factory configuration not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Invalid factory configuration.")

    for section in ["factory", "source", "datasets"]:
        if section not in config:
            raise ValueError(
                f"Missing '{section}' section in {config_path.name}"
            )

    return config


def get_dataset_path(config, dataset_name):
    """Resolve the full source-file path for a dataset."""

    datasets = config.get("datasets", {})

    if dataset_name not in datasets:
        raise KeyError(
            f"Dataset '{dataset_name}' is not configured."
        )

    dataset_config = datasets[dataset_name]

    root_path = Path(config["source"]["root_path"])

    if not root_path.is_absolute():
        root_path = PROJECT_ROOT / root_path

    source_folder = dataset_config.get("source_folder", "")
    source_file = dataset_config.get("source_file")

    if not source_file:
        raise ValueError(
            f"Missing source_file for dataset '{dataset_name}'."
        )

    return (root_path / source_folder / source_file).resolve()


def read_source_file(file_path, source_format):
    """
    Read supported source formats into a pandas DataFrame.
    """

    source_format = source_format.lower().strip()

    if source_format == "csv":
        return pd.read_csv(
            file_path,
            dtype=str,
            encoding="utf-8-sig"
        )

    elif source_format in ["excel", "xlsx", "xls"]:
        return pd.read_excel(file_path)

    elif source_format == "parquet":
        return pd.read_parquet(file_path)

    elif source_format == "json":
        return pd.read_json(file_path)

    elif source_format in ["jsonl", "ndjson"]:
        return pd.read_json(file_path, lines=True)

    else:
        raise ValueError(
            f"Unsupported source format: {source_format}. "
            "Supported formats: CSV, Excel, Parquet, JSON, JSONL."
        )


def read_dataset(config, dataset_name):
    """
    Read a configured dataset regardless of its file format.
    """

    dataset_config = config["datasets"][dataset_name]

    file_path = get_dataset_path(config, dataset_name)

    if not file_path.exists():

        if dataset_config.get("optional", False):
            print(
                f"Optional dataset '{dataset_name}' not found. Skipping."
            )
            return None

        raise FileNotFoundError(
            f"Required dataset '{dataset_name}' not found: {file_path}"
        )

    # Prefer dataset-level format.
    # Fall back to factory-level format for backward compatibility.
    source_format = dataset_config.get(
        "source_format",
        config["source"].get("file_format", file_path.suffix.lstrip("."))
    )

    try:
        dataframe = read_source_file(file_path, source_format)

    except Exception as error:
        raise RuntimeError(
            f"Failed to read dataset '{dataset_name}' "
            f"from {file_path}: {error}"
        ) from error

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            f"Dataset '{dataset_name}' did not produce a DataFrame."
        )

    print(
        f"Successfully read {dataset_name}: "
        f"{len(dataframe)} rows, "
        f"{len(dataframe.columns)} columns "
        f"({source_format})."
    )

    return dataframe


#Loads Factory A, B, or future factory configurations.
# Resolves source paths relative to the repository root.
# Reads datasets without hardcoding factory names.
# Preserves identifiers as strings during initial reading.
# Skips missing datasets only when explicitly marked optional.
# Gives clear errors for missing required files and unsupported formats.