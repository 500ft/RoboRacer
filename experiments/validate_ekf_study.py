#!/usr/bin/env python
"""Validate EKF study artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = REPO_ROOT / "runs" / "ekf_study"
TRACE_PATH = RUN_DIR / "trace.csv"
SUMMARY_PATH = RUN_DIR / "summary.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
REPORT_PATH = REPO_ROOT / "reports" / "ekf_study.md"
FIGURES = [
    REPO_ROOT / "reports" / "figures" / "ekf_position_error_over_time.png",
    REPO_ROOT / "reports" / "figures" / "ekf_rmse_summary.png",
    REPO_ROOT / "reports" / "figures" / "ekf_dropout_zoom.png",
]
SCENARIOS = {"clean_measurements", "low_noise", "high_noise", "dropout_1s", "dropout_3s"}
ESTIMATORS = {"dead_reckoning", "ekf"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(TRACE_PATH.exists(), f"Missing {TRACE_PATH}")
    require(SUMMARY_PATH.exists(), f"Missing {SUMMARY_PATH}")
    require(METADATA_PATH.exists(), f"Missing {METADATA_PATH}")
    trace = pd.read_csv(TRACE_PATH)
    summary = pd.read_csv(SUMMARY_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    require(SCENARIOS == set(summary["scenario"]), "EKF summary missing scenarios")
    for scenario in SCENARIOS:
        estimators = set(summary.loc[summary["scenario"] == scenario, "estimator"])
        require(estimators == ESTIMATORS, f"Scenario {scenario} missing estimator rows")
        require(scenario in metadata["scenarios"], f"Scenario {scenario} missing metadata")
        require(metadata["scenarios"][scenario]["measurement_R_diag"], f"Scenario {scenario} missing R metadata")
    require("process_Q_diag" in metadata and len(metadata["process_Q_diag"]) == 5, "Missing EKF Q metadata")
    require("seed" in metadata and "integration_dt_s" in metadata, "Missing seed/timestep metadata")
    pivot = summary.pivot(index="scenario", columns="estimator", values="position_rmse_m")
    require(pivot.loc["low_noise", "ekf"] < pivot.loc["low_noise", "dead_reckoning"], "EKF did not improve low_noise")
    require(pivot.loc["dropout_1s", "ekf"] < pivot.loc["dropout_1s", "dead_reckoning"], "EKF did not improve dropout_1s")
    require(np.isfinite(trace.select_dtypes(include=[np.number]).to_numpy(dtype=float)).all(), "Trace contains non-finite numeric values")
    require(REPORT_PATH.exists() and REPORT_PATH.stat().st_size > 0, f"Missing report {REPORT_PATH}")
    for figure in FIGURES:
        require(figure.exists() and figure.stat().st_size > 0, f"Missing figure {figure}")
    print("EKF study validation: PASS")


if __name__ == "__main__":
    main()
