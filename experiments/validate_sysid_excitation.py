#!/usr/bin/env python
"""Validate sysID steering excitation telemetry quality gates."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TELEMETRY_PATH = REPO_ROOT / "runs" / "sysid_steering_excitation" / "telemetry.csv"
DEFAULT_QUALITY_PATH = REPO_ROOT / "runs" / "sysid_steering_excitation" / "quality_metrics.csv"

S_MAX_RAD = 0.4189
SATURATION_THRESHOLD = 0.95 * S_MAX_RAD
SATURATION_FRACTION_LIMIT = 0.02
SATURATION_SEGMENT_LIMIT_S = 0.25

REQUIRED_COLUMNS = [
    "time_s",
    "x_m",
    "y_m",
    "theta_rad",
    "speed_mps",
    "vx_mps",
    "vy_mps",
    "yaw_rate_radps",
    "steer_rad",
    "steer_vel_radps",
    "command_steer_rad",
    "command_speed_mps",
    "accel_x_mps2",
    "slip_angle_rad",
    "collision",
]

NUMERIC_COLUMNS = [column for column in REQUIRED_COLUMNS if column not in {"run_id", "profile_status"}]


def longest_true_segment_s(mask: np.ndarray, dt_s: float) -> float:
    longest = 0
    current = 0
    for value in mask:
        if bool(value):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return float(longest * dt_s)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--telemetry",
        type=Path,
        default=DEFAULT_TELEMETRY_PATH,
        help="Telemetry CSV to validate.",
    )
    parser.add_argument(
        "--quality",
        type=Path,
        default=DEFAULT_QUALITY_PATH,
        help="Optional quality metrics CSV to echo when present.",
    )
    return parser


def main() -> None:
    args = parse_args().parse_args()
    telemetry_path = args.telemetry
    quality_path = args.quality

    if not telemetry_path.exists():
        fail(f"missing telemetry file: {telemetry_path}")

    df = pd.read_csv(telemetry_path)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        fail(f"missing required columns: {missing}")

    if df.empty:
        fail("telemetry is empty")

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        if not np.isfinite(df[column].to_numpy(dtype=float)).all():
            fail(f"non-finite or NaN values in {column}")

    time_s = df["time_s"].to_numpy(dtype=float)
    dt = np.diff(time_s)
    if dt.size == 0 or np.any(dt <= 0.0):
        fail("time_s must be strictly monotonic increasing")

    duration = float(time_s[-1] - time_s[0])
    steer_range = float(df["steer_rad"].max() - df["steer_rad"].min())
    yaw_rate_range = float(df["yaw_rate_radps"].max() - df["yaw_rate_radps"].min())
    speed_mean = float(df["speed_mps"].mean())
    speed_std = float(df["speed_mps"].std())
    speed_cv = float(speed_std / max(abs(speed_mean), 1e-6))
    collision = bool(df["collision"].max())
    saturation_mask = df["steer_rad"].abs().to_numpy(dtype=float) >= SATURATION_THRESHOLD
    saturation_fraction = float(np.mean(saturation_mask))
    max_saturation_segment_s = longest_true_segment_s(saturation_mask, float(np.median(dt)))

    checks = [
        ("collision occurred", not collision),
        ("duration too short", duration >= 15.0),
        ("steering excitation too small", steer_range >= 0.05),
        ("yaw-rate response too small", yaw_rate_range >= 0.1),
        ("speed hold too poor", speed_cv <= 0.15),
        ("too many steering-saturation samples", saturation_fraction <= SATURATION_FRACTION_LIMIT),
        ("continuous steering-saturation segment too long", max_saturation_segment_s <= SATURATION_SEGMENT_LIMIT_S),
    ]
    failures = [message for message, passed in checks if not passed]
    if failures:
        fail("; ".join(failures))

    summary = pd.DataFrame(
        [
            {"metric": "duration_s", "value": duration},
            {"metric": "steer_range_rad", "value": steer_range},
            {"metric": "yaw_rate_range_radps", "value": yaw_rate_range},
            {"metric": "speed_mean_mps", "value": speed_mean},
            {"metric": "speed_std_mps", "value": speed_std},
            {"metric": "speed_cv", "value": speed_cv},
            {"metric": "steering_saturation_fraction", "value": saturation_fraction},
            {"metric": "max_saturation_segment_s", "value": max_saturation_segment_s},
        ]
    )
    if quality_path.exists():
        quality = pd.read_csv(quality_path)
        print("Saved quality metrics:")
        print(quality.to_string(index=False))
    print("\nValidation summary:")
    print(summary.to_string(index=False))
    print("\nExcitation quality checks passed")


if __name__ == "__main__":
    main()
