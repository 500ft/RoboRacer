#!/usr/bin/env python
"""Validate failure-mode FMEA artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "runs" / "failure_mode_fmea" / "results.csv"
REPORT_PATH = REPO_ROOT / "reports" / "failure_mode_fmea.md"
FIGURES = [
    REPO_ROOT / "reports" / "figures" / "fmea_rpn_bar.png",
    REPO_ROOT / "reports" / "figures" / "fmea_detection_signals.png",
]
REQUIRED_CATEGORIES = {"numerics", "controller", "latency", "noise"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(RESULTS_PATH.exists(), f"Missing {RESULTS_PATH}")
    results = pd.read_csv(RESULTS_PATH)
    require(int(results["reproduced"].sum()) >= 5, "Expected at least five reproduced failures")
    require(REQUIRED_CATEGORIES.issubset(set(results["category"])), "Missing required FMEA categories")
    require({"dropout", "actuator"}.intersection(set(results["category"])), "Missing saturation or dropout category")
    reproduced = results[results["reproduced"] == True]  # noqa: E712
    require(reproduced["detection_signal"].astype(str).str.len().gt(0).all(), "Missing detection signal")
    require(reproduced["mitigation"].astype(str).str.len().gt(0).all(), "Missing mitigation")
    require((results["rpn"] > 0).all(), "RPN must be positive")
    require(np.isfinite(results.select_dtypes(include=[np.number]).to_numpy(dtype=float)).all(), "Non-finite numeric FMEA values")
    require(REPORT_PATH.exists() and REPORT_PATH.stat().st_size > 0, f"Missing report {REPORT_PATH}")
    for figure in FIGURES:
        require(figure.exists() and figure.stat().st_size > 0, f"Missing figure {figure}")
    print("failure-mode FMEA validation: PASS")


if __name__ == "__main__":
    main()
