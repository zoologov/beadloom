# beadloom:domain=application
# beadloom:feature=debt-report
"""Debt-weights config loading — ``config.yml`` ``debt_report`` section -> typed weights.

Falls back to defaults for a missing file, missing section, or missing keys so
the rest of the pipeline always receives a complete :class:`DebtWeights`.
"""

from __future__ import annotations

import logging
from dataclasses import fields
from typing import TYPE_CHECKING

import yaml

from beadloom.application.debt_report.models import DebtWeights

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def load_debt_weights(project_root: Path) -> DebtWeights:
    """Load debt weights from ``config.yml`` ``debt_report`` section.

    Falls back to defaults for missing keys or missing file.
    """
    config_path = project_root / "config.yml"
    if not config_path.is_file():
        return DebtWeights()

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        logger.warning("Failed to read config.yml, using default weights")
        return DebtWeights()

    if not isinstance(data, dict):
        return DebtWeights()

    debt_section = data.get("debt_report")
    if not isinstance(debt_section, dict):
        return DebtWeights()

    # Merge weights
    weights_data = debt_section.get("weights", {})
    thresholds_data = debt_section.get("thresholds", {})

    if not isinstance(weights_data, dict):
        weights_data = {}
    if not isinstance(thresholds_data, dict):
        thresholds_data = {}

    defaults = DebtWeights()
    kwargs: dict[str, float | int] = {}

    # Weight fields
    weight_fields = {
        "rule_error", "rule_warning", "undocumented_node", "stale_doc",
        "untracked_file", "oversized_domain", "high_fan_out",
        "dormant_domain", "untested_domain", "meta_doc_stale",
    }
    for field_name in weight_fields:
        if field_name in weights_data:
            kwargs[field_name] = float(weights_data[field_name])

    # Threshold fields (mapped from config names to dataclass names)
    threshold_map = {
        "oversized_symbols": "oversized_symbols",
        "high_fan_out": "high_fan_out_threshold",
        "dormant_months": "dormant_months",
    }
    for config_key, field_name in threshold_map.items():
        if config_key in thresholds_data:
            kwargs[field_name] = int(thresholds_data[config_key])

    # Build with defaults for unset fields
    all_fields = {f.name for f in fields(DebtWeights)}
    for fname in all_fields:
        if fname not in kwargs:
            kwargs[fname] = getattr(defaults, fname)

    return DebtWeights(**kwargs)  # type: ignore[arg-type]
