#!/usr/bin/env python
"""Exercise rosbag conversion through the existing SysID validator."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "experiments"))

from generate_synthetic_rosbag import create_bag  # noqa: E402
from rosbag_to_telemetry import convert_bag  # noqa: E402

TEST_DIR = REPO_ROOT / "runs" / "rosbag_to_telemetry_test"


def assert_close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def run_validator(telemetry: Path, quality: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "experiments" / "validate_sysid_excitation.py"),
            "--telemetry",
            str(telemetry),
            "--quality",
            str(quality),
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def assert_common_schema(telemetry: Path) -> pd.DataFrame:
    df = pd.read_csv(telemetry)
    required = {
        "time_s",
        "x_m",
        "y_m",
        "theta_rad",
        "speed_mps",
        "vx_mps",
        "vy_mps",
        "steer_rad",
        "steer_vel_radps",
        "yaw_rate_radps",
        "slip_angle_rad",
        "accel_x_mps2",
        "command_steer_rad",
        "command_speed_mps",
        "collision",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise AssertionError(f"missing converted columns: {missing}")
    if not np.all(np.diff(df["time_s"].to_numpy()) > 0.0):
        raise AssertionError("time_s is not strictly increasing")
    row = df.iloc[20]
    expected_speed = math.hypot(float(row["vx_mps"]), float(row["vy_mps"]))
    expected_beta = math.atan2(float(row["vy_mps"]), float(row["vx_mps"]))
    assert_close(float(row["speed_mps"]), expected_speed, 1e-6, "speed from vx/vy")
    assert_close(float(row["slip_angle_rad"]), expected_beta, 1e-6, "slip angle from vx/vy")
    return df


def run_case(name: str, include_internal_state: bool, sample_clock: str = "fixed") -> None:
    case_dir = TEST_DIR / name
    bag = case_dir / "bag"
    telemetry = case_dir / "telemetry.csv"
    metadata = case_dir / "metadata.json"
    quality = case_dir / "quality_metrics.csv"
    create_bag(bag, include_internal_state=include_internal_state, force=True)
    result = convert_bag(bag, telemetry, metadata, quality, sample_clock=sample_clock)
    df = assert_common_schema(telemetry)
    run_validator(telemetry, quality)
    saved_metadata = json.loads(metadata.read_text())
    expected_source = "internal_state" if include_internal_state else "command_proxy"
    if result["steer_rad_source"] != expected_source or saved_metadata["steer_rad_source"] != expected_source:
        raise AssertionError(f"wrong steering source for {name}")
    if include_internal_state:
        row = df.iloc[40]
        if abs(float(row["steer_rad"]) - float(row["command_steer_rad"])) < 1e-6:
            raise AssertionError("internal-state steering should differ from command steering in synthetic case")
    if result["sample_clock"] != sample_clock:
        raise AssertionError(f"wrong sample clock for {name}")
    if "topic_diagnostics" not in saved_metadata:
        raise AssertionError(f"missing topic diagnostics for {name}")
    if sample_clock == "internal_state":
        if not saved_metadata["sim_time_observed"]:
            raise AssertionError("internal-state native export did not observe simulator time")
        if not np.allclose(df["time_s"], df["wall_time_s"], atol=1e-9):
            raise AssertionError("synthetic native simulator and wall clocks should agree")


def run_determinism_case() -> None:
    case_dir = TEST_DIR / "determinism"
    bag = case_dir / "bag"
    create_bag(bag, include_internal_state=True, force=True)
    outputs = []
    for suffix in ("a", "b"):
        telemetry = case_dir / f"telemetry_{suffix}.csv"
        convert_bag(
            bag,
            telemetry,
            case_dir / f"metadata_{suffix}.json",
            case_dir / f"quality_{suffix}.csv",
            sample_clock="internal_state",
        )
        outputs.append(telemetry.read_bytes())
    if outputs[0] != outputs[1]:
        raise AssertionError("converter telemetry output is not byte deterministic")


def run_missing_sim_time_case() -> None:
    case_dir = TEST_DIR / "missing_sim_time"
    bag = case_dir / "bag"
    create_bag(
        bag,
        include_internal_state=True,
        include_sim_time=False,
        force=True,
    )
    try:
        convert_bag(
            bag,
            case_dir / "telemetry.csv",
            case_dir / "metadata.json",
            case_dir / "quality.csv",
            sample_clock="internal_state",
        )
    except SystemExit as exc:
        if "sim_time_s" not in str(exc):
            raise
    else:
        raise AssertionError("native internal-state export accepted missing simulator time")


def main() -> None:
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    run_case("standard_topics", include_internal_state=False)
    run_case("with_internal_state", include_internal_state=True)
    run_case("standard_topics_native", include_internal_state=False, sample_clock="odom")
    run_case("with_internal_state_native", include_internal_state=True, sample_clock="internal_state")
    run_determinism_case()
    run_missing_sim_time_case()
    print("rosbag_to_telemetry synthetic tests passed")


if __name__ == "__main__":
    main()
