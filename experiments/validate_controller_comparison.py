#!/usr/bin/env python
"""Validate controller comparison artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "runs" / "controller_comparison" / "results.csv"
REPORT_PATH = REPO_ROOT / "reports" / "controller_comparison.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(RESULTS_PATH.exists(), f"Missing {RESULTS_PATH}")
    results = pd.read_csv(RESULTS_PATH)
    require({"pure_pursuit", "lqr", "mpc"}.issubset(set(results["controller"])), "Comparison must include PP, LQR, MPC")
    for column in ["rms_cte_m", "max_abs_cte_m", "steering_effort_rad", "completed_lap", "collision"]:
        require(column in results.columns, f"Missing column {column}")
    require(results["completed_lap"].all(), "All comparison controllers should complete a lap")
    require((results["collision"] == False).all(), "Comparison controllers should not collide")  # noqa: E712
    require(REPORT_PATH.exists() and REPORT_PATH.stat().st_size > 0, f"Missing report {REPORT_PATH}")
    print("controller comparison validation: PASS")


if __name__ == "__main__":
    main()
