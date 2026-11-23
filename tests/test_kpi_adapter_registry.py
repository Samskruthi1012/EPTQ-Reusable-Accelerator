"""Tests for configuration-driven factory adapter discovery."""
import tempfile
import unittest
from pathlib import Path

from src.transform.run_kpi_pipeline import available_factories, load_registry

ROOT = Path(__file__).resolve().parents[1]


class AdapterRegistryTests(unittest.TestCase):
    def test_registry_loads_factory_adapters_from_yaml(self):
        factories = load_registry(ROOT)
        self.assertEqual(set(factories), {"FACTORY_A", "FACTORY_B"})
        self.assertEqual(
            factories["FACTORY_A"]["adapter_module"],
            "src.transform.adapters.factory_a_adapter",
        )
        self.assertEqual(
            factories["FACTORY_B"]["adapter_module"],
            "src.transform.adapters.factory_b_adapter",
        )

    def test_available_factories_comes_from_registry(self):
        self.assertEqual(available_factories(ROOT), ["FACTORY_A", "FACTORY_B"])


if __name__ == "__main__":
    unittest.main()
