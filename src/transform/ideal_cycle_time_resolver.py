"""Resolve factory/product/machine/operation ideal-cycle-time rules."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

DIMENSION_FIELDS = ("operation_id", "product_id", "machine_id")


class IdealCycleTimeResolver:
    def __init__(self, config_path: str | Path):
        with Path(config_path).open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.settings = self.config.get("configuration", {})
        self.rules = self.config.get("rules", [])
        self.require_approved = bool(self.settings.get("require_approved", False))
        self.resolution_order = self.settings.get("resolution_order", [])

    @staticmethod
    def _as_date(value: Any) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    def _scope(self, rule: dict[str, Any]) -> str:
        # Match the canonical names in resolution_order.
        present = {field for field in DIMENSION_FIELDS if rule.get(field) not in (None, "")}
        aliases = {"operation_id": "operation", "product_id": "product", "machine_id": "machine"}
        if not present:
            return "factory"
        # Resolve the exact configured combination regardless of field order.
        for configured_scope in self.resolution_order:
            if set(configured_scope.split("+")) == {aliases[field] for field in present}:
                return configured_scope
        return "+".join(sorted(aliases[field] for field in present))

    def resolve(self, *, factory_id: str, product_id: str | None,
                machine_id: str | None = None, operation_id: str | None = None,
                as_of: str | date | datetime | None = None) -> dict[str, Any] | None:
        effective_date = self._as_date(as_of)
        context = {
            "operation_id": operation_id,
            "product_id": product_id,
            "machine_id": machine_id,
        }
        candidates: list[tuple[int, int, dict[str, Any]]] = []
        for rule in self.rules:
            if rule.get("factory_id") != factory_id:
                continue
            status = str(rule.get("status", "")).lower()
            if self.require_approved and status != "approved":
                continue
            start = self._as_date(rule.get("effective_from"))
            end = self._as_date(rule.get("effective_to"))
            if effective_date is not None and ((start and effective_date < start) or (end and effective_date > end)):
                continue
            rule_dimensions = {field: rule.get(field) for field in DIMENSION_FIELDS
                               if rule.get(field) not in (None, "")}
            if any(context.get(field) != value for field, value in rule_dimensions.items()):
                continue
            # A rule with a dimension absent from context cannot match (checked above).
            scope = self._scope(rule)
            try:
                priority = self.resolution_order.index(scope)
            except ValueError:
                # Unknown combinations still resolve deterministically by specificity.
                priority = len(self.resolution_order) + (3 - len(rule_dimensions))
            approval_rank = 0 if status == "approved" else 1
            candidates.append((priority, -len(rule_dimensions), approval_rank, rule))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        best_key = candidates[0][:3]
        best = [rule for priority, specificity, approval_rank, rule in candidates
                if (priority, specificity, approval_rank) == best_key]
        if len(best) > 1:
            raise ValueError(
                f"Ambiguous ideal cycle time configuration for "
                f"{factory_id}/{product_id}/{machine_id}/{operation_id}"
            )
        return best[0]
