#!/usr/bin/env python
"""Validate pure-pursuit sweep artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "runs" / "pure_pursuit_sweep" / "results.csv"
REPORT_PATH = REPO_ROOT / "reports" / "pure_pursuit_sweep.md"
FIGURES = [
    REPO_ROOT / "reports" / "figures" / "pure_pursuit_sweep_rms_cte_heatmap.png",
    REPO_ROOT / "reports" / "figures" / "pure_pursuit_sweep_lap_time_heatmap.png",
    REPO_ROOT / "reports" / "figures" / "pure_pursuit_sweep_regions.png",
]
EXPECTED_RUNS = 30
REQUIRED_COLUMNS = {
    "lookahead_m",
    "vgain",
    "integration_dt_s",
    "control_rate_hz",
    "completed_lap",
    "collision",
    "rms_cte_m",
    "max_abs_cte_m",
    "steering_effort_rad",
    "classification",
    "selected_baseline",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(RESULTS_PATH.exists(), f"Missing {RESULTS_PATH}")
    results = pd.read_csv(RESULTS_PATH)
    require(len(results) == EXPECTED_RUNS, f"Expected {EXPECTED_RUNS} runs, found {len(results)}")
    missing = REQUIRED_COLUMNS - set(results.columns)
    require(not missing, f"Missing result columns: {sorted(missing)}")
    require((results["integration_dt_s"] == 0.002).all(), "integration_dt_s must be 0.002")
    require(results["control_rate_hz"].notna().all(), "control_rate_hz must be recorded")
    require(((results["completed_lap"] == True) & (results["collision"] == False)).any(), "No completed non-collision PP run")  # noqa: E712
    require(results["selected_baseline"].sum() == 1, "Exactly one baseline must be selected")
    require(REPORT_PATH.exists() and REPORT_PATH.stat().st_size > 0, f"Missing report {REPORT_PATH}")
    for figure in FIGURES:
        require(figure.exists() and figure.stat().st_size > 0, f"Missing figure {figure}")
    print("pure pursuit sweep validation: PASS")


if __name__ == "__main__":
    main()
