#!/usr/bin/env python
"""Validate dynamic-parameter identification artifacts and held-out gates."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = REPO_ROOT / "runs" / "dynamic_parameter_identification"
PARAMETERS_PATH = RUN_DIR / "parameters.json"
METRICS_PATH = RUN_DIR / "metrics.csv"
FIT_TRACE_PATH = RUN_DIR / "fit_trace.csv"
VALIDATION_TRACE_PATH = RUN_DIR / "heldout_replay_trace.csv"

REQUIRED_METRICS = {
    "fitted_C_Sf",
    "fitted_C_Sr",
    "C_Sf_oracle_relative_error",
    "C_Sr_oracle_relative_error",
    "jacobian_condition_number",
    "raw_jacobian_condition_number",
    "parameter_correlation",
    "sensitivity_column_cosine",
    "heldout_one_step_yaw_rate_rmse",
    "heldout_one_step_slip_angle_rmse",
    "heldout_rollout_position_rmse",
    "heldout_rollout_yaw_rmse",
    "heldout_rollout_yaw_rate_rmse",
    "heldout_rollout_yaw_rate_nrmse",
    "heldout_rollout_yaw_rate_vaf_percent",
    "heldout_rollout_slip_angle_rmse",
    "heldout_rollout_slip_angle_nrmse",
    "heldout_rollout_slip_angle_vaf_percent",
}


def require_finite_frame(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"Missing or empty artifact: {path}")
    frame = pd.read_csv(path)
    numeric = frame.select_dtypes(include=[np.number])
    if numeric.empty or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f"Artifact has missing/non-finite numeric content: {path}")
    return frame


def main() -> int:
    metrics = require_finite_frame(METRICS_PATH)
    fit_trace = require_finite_frame(FIT_TRACE_PATH)
    validation_trace = require_finite_frame(VALIDATION_TRACE_PATH)
    parameters = json.loads(PARAMETERS_PATH.read_text(encoding="utf-8"))

    missing = REQUIRED_METRICS - set(metrics["metric"].astype(str))
    if missing:
        raise ValueError(f"Missing required metrics: {sorted(missing)}")
    if set(fit_trace["partition"].astype(str)) != {"train", "heldout"}:
        raise ValueError("Fit trace must contain both train and heldout partitions.")
    if len(validation_trace) < 100:
        raise ValueError("Held-out replay is too short.")
    if not np.all(np.diff(validation_trace["time_s"].to_numpy(dtype=float)) > 0.0):
        raise ValueError("Held-out replay time_s must be strictly increasing.")

    values = {str(row.metric): float(row.value) for row in metrics.itertuples(index=False)}
    limits = parameters.get("acceptance_limits", {})
    calculated_checks = {
        "oracle_recovery": max(
            values["C_Sf_oracle_relative_error"],
            values["C_Sr_oracle_relative_error"],
        )
        <= float(limits["max_oracle_relative_error_fraction"]),
        "heldout_yaw_rate": values["heldout_rollout_yaw_rate_rmse"]
        <= float(limits["max_heldout_rollout_yaw_rate_rmse_radps"]),
        "heldout_slip_angle": values["heldout_rollout_slip_angle_rmse"]
        <= float(limits["max_heldout_rollout_slip_angle_rmse_rad"]),
        "heldout_yaw": values["heldout_rollout_yaw_rmse"]
        <= float(limits["max_heldout_rollout_yaw_rmse_rad"]),
        "heldout_normalized_fit": values["heldout_rollout_yaw_rate_nrmse"]
        <= float(limits["max_heldout_rollout_yaw_rate_nrmse"]),
        "heldout_variance_accounted_for": values["heldout_rollout_yaw_rate_vaf_percent"]
        >= float(limits["min_heldout_rollout_yaw_rate_vaf_percent"]),
        "identifiability": values["jacobian_condition_number"]
        <= float(limits["max_jacobian_condition_number"]),
        "parameter_correlation": abs(values["parameter_correlation"])
        <= float(limits["max_parameter_correlation_abs"]),
    }
    saved_checks = parameters.get("acceptance_checks", {})
    if calculated_checks != saved_checks:
        raise ValueError(
            f"Recomputed acceptance checks disagree with parameters.json: "
            f"calculated={calculated_checks}, saved={saved_checks}"
        )
    if not all(calculated_checks.values()):
        raise ValueError(f"Held-out acceptance checks did not all pass: {calculated_checks}")
    if not bool(parameters.get("heldout_validation_passed")):
        raise ValueError("parameters.json does not mark held-out validation as passed.")

    fitted = parameters["fitted"]
    if float(fitted["C_Sf"]) <= 0.0 or float(fitted["C_Sr"]) <= 0.0:
        raise ValueError("Identified coefficients must be positive.")

    print("Dynamic parameter identification validation: PASS")
    print(f"C_Sf={float(fitted['C_Sf']):.9f}")
    print(f"C_Sr={float(fitted['C_Sr']):.9f}")
    for name, value in calculated_checks.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
