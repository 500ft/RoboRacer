#!/usr/bin/env python
"""Validate parameter-identification robustness artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.identification import ACCEPTANCE_GATE_ORDER, acceptance, first_failed_gate

RUN_DIR = REPO_ROOT / "runs" / "parameter_id_robustness"
RESULTS_PATH = RUN_DIR / "results.csv"
METRICS_PATH = RUN_DIR / "metrics.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
REPORT_PATH = REPO_ROOT / "reports" / "parameter_id_robustness.md"
FIGURE_PATHS = [
    REPO_ROOT / "reports" / "figures" / "parameter_id_noise_degradation.png",
    REPO_ROOT / "reports" / "figures" / "parameter_id_latency_degradation.png",
    REPO_ROOT / "reports" / "figures" / "parameter_id_condition_number.png",
]


def assert_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise AssertionError(f"Missing or empty artifact: {path}")


def main() -> int:
    for path in [RESULTS_PATH, METRICS_PATH, METADATA_PATH, REPORT_PATH, *FIGURE_PATHS]:
        assert_file(path)

    results = pd.read_csv(RESULTS_PATH)
    metrics = pd.read_csv(METRICS_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    required_kinds = {"nominal", "noise", "latency", "quantization", "combined"}
    observed_kinds = set(results["kind"].astype(str))
    missing = required_kinds - observed_kinds
    if missing:
        raise AssertionError(f"Missing perturbation kinds: {sorted(missing)}")
    if len(results) < 10:
        raise AssertionError("Expected at least ten parameter-ID robustness scenarios.")

    numeric_columns = [
        "fitted_C_Sf",
        "fitted_C_Sr",
        "C_Sf_oracle_relative_error",
        "C_Sr_oracle_relative_error",
        "jacobian_condition_number",
        "condition_growth_vs_nominal",
        "heldout_rollout_yaw_rate_rmse",
        "heldout_rollout_slip_angle_rmse",
    ]
    numeric = results[numeric_columns].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise AssertionError("Results contain non-finite numeric values.")
    if (results[["fitted_C_Sf", "fitted_C_Sr", "jacobian_condition_number"]] <= 0.0).any().any():
        raise AssertionError("Fitted coefficients and condition numbers must be positive.")

    valid_failed_gates = set(ACCEPTANCE_GATE_ORDER)
    for row in results.itertuples(index=False):
        scenario_metrics = metrics[metrics["scenario"] == row.scenario]
        if scenario_metrics.empty:
            raise AssertionError(f"Missing metrics for scenario {row.scenario}")
        checks = acceptance(scenario_metrics)
        recomputed_pass = bool(all(checks.values()))
        if bool(row.acceptance_passed) != recomputed_pass:
            raise AssertionError(f"Acceptance mismatch for {row.scenario}")
        recomputed_first_failed = first_failed_gate(checks)
        observed_first_failed = "" if pd.isna(row.first_failed_gate) else str(row.first_failed_gate)
        if observed_first_failed != recomputed_first_failed:
            raise AssertionError(
                f"First failed gate mismatch for {row.scenario}: "
                f"{observed_first_failed!r} != {recomputed_first_failed!r}"
            )
        if observed_first_failed and observed_first_failed not in valid_failed_gates:
            raise AssertionError(f"Unknown failed gate {observed_first_failed!r}")
        for gate in ACCEPTANCE_GATE_ORDER:
            observed = bool(getattr(row, f"gate_{gate}"))
            if observed != bool(checks[gate]):
                raise AssertionError(f"Gate {gate} mismatch for {row.scenario}")

    if "seed" not in metadata or "perturbations" not in metadata:
        raise AssertionError("Metadata must record seed and perturbation levels.")
    if set(metadata["perturbations"]) != set(results["scenario"]):
        raise AssertionError("Metadata perturbations must match result scenarios.")

    report = REPORT_PATH.read_text(encoding="utf-8")
    for figure in FIGURE_PATHS:
        if figure.name not in report:
            raise AssertionError(f"Report does not link {figure.name}")

    print("parameter-ID robustness validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
