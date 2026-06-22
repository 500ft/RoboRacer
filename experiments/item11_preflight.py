#!/usr/bin/env python
"""Screen an enriched SysID profile before recording item 11 evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.identification import identify_from_telemetry, metric_dict

DEFAULT_TELEMETRY = REPO_ROOT / "runs" / "sysid_steering_excitation" / "telemetry.csv"


def steering_metrics(frame: pd.DataFrame, timestep_s: float, rate_limit_radps: float) -> dict[str, float]:
    command = frame["command_steer_rad"].to_numpy(dtype=float)
    achieved = frame["steer_rad"].to_numpy(dtype=float)
    error = achieved - command
    lag_rows = []
    for lag in range(6):
        lag_error = achieved[lag:] - command[: len(command) - lag] if lag else error
        lag_rows.append((lag, float(np.sqrt(np.mean(lag_error**2)))))
    best_lag, best_rmse = min(lag_rows, key=lambda item: item[1])
    steer_velocity = np.diff(achieved) / np.diff(frame["time_s"].to_numpy(dtype=float))
    return {
        "command_achieved_rmse_rad": float(np.sqrt(np.mean(error**2))),
        "command_achieved_max_abs_rad": float(np.max(np.abs(error))),
        "best_command_lag_samples": int(best_lag),
        "best_command_lag_s": float(best_lag * timestep_s),
        "best_lag_rmse_rad": best_rmse,
        "steering_rate_limit_fraction": float(
            np.mean(np.isclose(np.abs(steer_velocity), rate_limit_radps, atol=1e-6))
        ),
    }


def evaluate(telemetry_path: Path, target_speed_mps: float) -> dict[str, object]:
    frame = pd.read_csv(telemetry_path)
    identified = identify_from_telemetry(frame, repo_root=REPO_ROOT)
    values = metric_dict(identified.metrics)
    timestep = float(np.median(np.diff(frame["time_s"].to_numpy(dtype=float))))
    acceleration_y = frame["speed_mps"].to_numpy(dtype=float) * frame["yaw_rate_radps"].to_numpy(dtype=float)
    post_start = frame[frame["time_s"] >= frame["time_s"].iloc[0] + 0.5]
    speed_in_band = np.abs(post_start["speed_mps"] - target_speed_mps) <= 0.15 * target_speed_mps
    heldout_duration = float(
        identified.validation_trace["time_s"].iloc[-1]
        - identified.validation_trace["time_s"].iloc[0]
    )
    metrics: dict[str, float | int] = {
        **steering_metrics(frame, timestep, 3.2),
        "normalized_jacobian_condition_number": identified.jacobian_condition_number,
        "raw_jacobian_condition_number": identified.raw_jacobian_condition_number,
        "parameter_correlation": identified.parameter_correlation,
        "sensitivity_column_cosine": identified.sensitivity_column_cosine,
        "lateral_acceleration_rms_mps2": float(np.sqrt(np.mean(acceleration_y**2))),
        "lateral_acceleration_peak_abs_mps2": float(np.max(np.abs(acceleration_y))),
        "speed_in_band_fraction": float(np.mean(speed_in_band)),
        "heldout_duration_s": heldout_duration,
        "heldout_native_transitions": identified.heldout_intervals,
        "fitted_C_Sf": values["fitted_C_Sf"],
        "fitted_C_Sr": values["fitted_C_Sr"],
    }
    checks = {
        "normalized_condition": identified.jacobian_condition_number <= 10.0,
        "parameter_correlation": abs(identified.parameter_correlation) <= 0.95,
        "lateral_acceleration_rms": metrics["lateral_acceleration_rms_mps2"] >= 0.25,
        "lateral_acceleration_peak": metrics["lateral_acceleration_peak_abs_mps2"] >= 0.40,
        "speed_band": metrics["speed_in_band_fraction"] >= 0.95,
        "heldout_duration": heldout_duration >= 5.5,
        "heldout_transitions": identified.heldout_intervals >= 400,
        "achieved_channel_differs": metrics["command_achieved_rmse_rad"] > 0.001,
    }
    return {"telemetry": str(telemetry_path), "metrics": metrics, "checks": checks, "passed": all(checks.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", type=Path, default=DEFAULT_TELEMETRY)
    parser.add_argument("--target-speed", type=float, default=2.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.telemetry, args.target_speed)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

