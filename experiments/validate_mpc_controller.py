#!/usr/bin/env python
"""Validate MPC controller artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "runs" / "mpc_controller" / "results.csv"
REPORT_PATH = REPO_ROOT / "reports" / "mpc_controller.md"
FIGURES = [
    REPO_ROOT / "reports" / "figures" / "mpc_solver_runtime.png",
    REPO_ROOT / "reports" / "figures" / "mpc_controller_cte.png",
]
REQUIRED_COLUMNS = {
    "integration_dt_s",
    "control_rate_hz",
    "rms_cte_m",
    "max_abs_cte_m",
    "mpc_mean_solve_time_s",
    "mpc_p95_solve_time_s",
    "mpc_max_solve_time_s",
    "mpc_meets_100hz_budget",
    "mpc_meets_50hz_budget",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(RESULTS_PATH.exists(), f"Missing {RESULTS_PATH}")
    results = pd.read_csv(RESULTS_PATH)
    missing = REQUIRED_COLUMNS - set(results.columns)
    require(not missing, f"Missing columns: {sorted(missing)}")
    row = results.iloc[0]
    require(float(row["integration_dt_s"]) == 0.002, "integration_dt_s must be 0.002")
    require(pd.notna(row["control_rate_hz"]), "control_rate_hz must be present")
    require(pd.notna(row["mpc_p95_solve_time_s"]), "p95 solve time must be present")
    require(bool(row["completed_lap"]), "MPC should complete a lap")
    require(not bool(row["collision"]), "MPC should not collide")
    require(REPORT_PATH.exists() and REPORT_PATH.stat().st_size > 0, f"Missing report {REPORT_PATH}")
    for figure in FIGURES:
        require(figure.exists() and figure.stat().st_size > 0, f"Missing figure {figure}")
    print("MPC controller validation: PASS")


if __name__ == "__main__":
    main()
