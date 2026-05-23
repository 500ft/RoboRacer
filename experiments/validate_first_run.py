#!/usr/bin/env python
"""Validate first-run F1TENTH artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import f110_gym  # noqa: F401
import gym  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = REPO_ROOT / "runs" / "first_lap" / "telemetry.csv"
METADATA_PATH = REPO_ROOT / "runs" / "first_lap" / "metadata.json"
FIGURE_PATH = REPO_ROOT / "reports" / "figures" / "first_integrator_comparison.png"
REPORT_PATH = REPO_ROOT / "reports" / "first_run.md"

EXPECTED_COLUMNS = [
    "run_id",
    "integrator",
    "step",
    "time_s",
    "x_m",
    "y_m",
    "theta_rad",
    "speed_mps",
    "steer_rad",
    "command_speed_mps",
    "command_steer_rad",
    "yaw_rate_radps",
    "accel_x_mps2",
    "accel_y_mps2",
    "nearest_waypoint_index",
    "progress_m",
    "cte_m",
    "abs_cte_m",
    "lap_time_s",
    "lap_count",
    "collision",
    "termination_reason",
]

NUMERIC_COLUMNS = [
    column
    for column in EXPECTED_COLUMNS
    if column not in {"run_id", "integrator", "termination_reason"}
]

ALLOWED_TERMINATION_REASONS = {"completed_lap", "collision", "max_steps", "error"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    for path in (TELEMETRY_PATH, METADATA_PATH, FIGURE_PATH, REPORT_PATH):
        require(path.exists(), f"Missing artifact: {path}")
        require(path.stat().st_size > 0, f"Empty artifact: {path}")

    metadata = json.loads(METADATA_PATH.read_text())
    require(metadata["control"] == "pure_pursuit", "metadata control must be pure_pursuit")
    require(metadata["integrators"] == ["rk4", "euler"], "metadata integrators must be rk4/euler")
    require(metadata["max_steps"] == 20000, "metadata max_steps must be 20000")

    df = pd.read_csv(TELEMETRY_PATH)
    missing = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    require(not missing, f"Missing telemetry columns: {missing}")
    require(set(df["integrator"]) == {"rk4", "euler"}, "Telemetry must contain rk4 and euler")
    require(np.isfinite(df[NUMERIC_COLUMNS].to_numpy()).all(), "Telemetry numeric values must be finite")
    require(
        set(df["termination_reason"]).issubset(ALLOWED_TERMINATION_REASONS),
        f"Unexpected termination reasons: {sorted(set(df['termination_reason']))}",
    )

    summary = df.groupby("integrator").agg(
        rows=("step", "count"),
        final_time_s=("time_s", "max"),
        collision=("collision", "max"),
        termination_reason=("termination_reason", "last"),
    )
    print("first-run validation ok")
    print(summary.to_string())


if __name__ == "__main__":
    main()
