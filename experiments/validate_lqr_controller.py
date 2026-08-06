#!/usr/bin/env python
"""Validate LQR controller artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "runs" / "lqr_controller" / "results.csv"
MODEL_PATH = REPO_ROOT / "runs" / "lqr_controller" / "linear_model.json"
REPORT_PATH = REPO_ROOT / "reports" / "lqr_controller.md"
FIGURE_PATH = REPO_ROOT / "reports" / "figures" / "lqr_controller_cte_cases.png"
REQUIRED_CASES = {"nominal", "offset_plus_0p5m", "delay_30ms"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(RESULTS_PATH.exists(), f"Missing {RESULTS_PATH}")
    require(MODEL_PATH.exists(), f"Missing {MODEL_PATH}")
    results = pd.read_csv(RESULTS_PATH)
    require(REQUIRED_CASES.issubset(set(results["case"])), "Missing LQR cases")
    require((results["integration_dt_s"] == 0.002).all(), "integration_dt_s must be 0.002")
    require(results["control_rate_hz"].notna().all(), "control_rate_hz must be recorded")
    require(results["completed_lap"].all(), "All LQR cases should complete a lap")
    require((results["collision"] == False).all(), "LQR cases should not collide")  # noqa: E712
    payload = json.loads(MODEL_PATH.read_text())
    for key in ("A_continuous", "B_continuous", "A_discrete", "B_discrete", "K", "closed_loop_eigenvalues"):
        require(key in payload, f"Missing {key} in model payload")
    require(REPORT_PATH.exists() and REPORT_PATH.stat().st_size > 0, f"Missing report {REPORT_PATH}")
    require(FIGURE_PATH.exists() and FIGURE_PATH.stat().st_size > 0, f"Missing figure {FIGURE_PATH}")
    print("LQR controller validation: PASS")


if __name__ == "__main__":
    main()
