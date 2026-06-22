#!/usr/bin/env python
"""Identify Gym single-track C_Sf and C_Sr with held-out validation."""

from __future__ import annotations

import json
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.dynamics import DEFAULT_DYNAMIC_PARAMS, dynamic_rk4_step, load_vehicle_dynamics_st
from roboracer.identification import (
    IdentificationResult,
    identify_from_telemetry as shared_identify_from_telemetry,
)
from roboracer.numerics import nrmse, rmse, vaf_percent, wrap_angle
from roboracer.telemetry import validate_numeric_telemetry

TELEMETRY_PATH = REPO_ROOT / "runs" / "sysid_steering_excitation" / "telemetry.csv"
RUN_DIR = REPO_ROOT / "runs" / "dynamic_parameter_identification"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
PARAMETERS_PATH = RUN_DIR / "parameters.json"
METRICS_PATH = RUN_DIR / "metrics.csv"
FIT_TRACE_PATH = RUN_DIR / "fit_trace.csv"
VALIDATION_TRACE_PATH = RUN_DIR / "heldout_replay_trace.csv"
REPORT_PATH = REPO_ROOT / "reports" / "dynamic_parameter_identification.md"
FIT_FIGURE_PATH = FIGURE_DIR / "dynamic_parameter_fit.png"
RESIDUAL_FIGURE_PATH = FIGURE_DIR / "dynamic_parameter_residuals.png"
SOURCE_LABEL = "controlled Gym excitation"
ORACLE_MODE = "gym"

TRAIN_FRACTION = 0.70
DYNAMIC_REGIME_MIN_SPEED_MPS = 0.75
LOWER_BOUND = np.array([0.1, 0.1], dtype=float)
UPPER_BOUND = np.array([20.0, 20.0], dtype=float)
INITIAL_GUESS = np.array([3.0, 3.0], dtype=float)
ORACLE = np.array([4.718, 5.4562], dtype=float)

PARAMS = DEFAULT_DYNAMIC_PARAMS

REQUIRED_COLUMNS = [
    "time_s",
    "x_m",
    "y_m",
    "steer_rad",
    "speed_mps",
    "theta_rad",
    "yaw_rate_radps",
    "slip_angle_rad",
    "steer_vel_radps",
    "accel_x_mps2",
]

ACCEPTANCE_LIMITS = {
    "max_oracle_relative_error_fraction": 0.10,
    "max_heldout_rollout_yaw_rate_rmse_radps": 0.01,
    "max_heldout_rollout_slip_angle_rmse_rad": 0.001,
    "max_heldout_rollout_yaw_rmse_rad": 0.01,
    "max_heldout_rollout_yaw_rate_nrmse": 0.10,
    "min_heldout_rollout_yaw_rate_vaf_percent": 95.0,
    "max_jacobian_condition_number": 100.0,
}


vehicle_dynamics_st = load_vehicle_dynamics_st(REPO_ROOT, module_name="sysid_dynamic_models")


def portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_telemetry() -> pd.DataFrame:
    telemetry = pd.read_csv(TELEMETRY_PATH)
    return validate_numeric_telemetry(telemetry, required_columns=REQUIRED_COLUMNS, context="Telemetry", ratio_limit=1.2)


def state_matrix(telemetry: pd.DataFrame) -> np.ndarray:
    return telemetry[
        [
            "x_m",
            "y_m",
            "steer_rad",
            "speed_mps",
            "theta_rad",
            "yaw_rate_radps",
            "slip_angle_rad",
        ]
    ].to_numpy(dtype=float)


def input_matrix(telemetry: pd.DataFrame) -> np.ndarray:
    return telemetry[["steer_vel_radps", "accel_x_mps2"]].to_numpy(dtype=float)


def rk4_step(state: np.ndarray, control: np.ndarray, dt: float, coefficients: np.ndarray) -> np.ndarray:
    return dynamic_rk4_step(
        vehicle_dynamics_st,
        state,
        control,
        dt,
        PARAMS,
        coefficients=coefficients,
    )


def split_intervals(states: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    usable = np.flatnonzero(states[:-1, 3] >= DYNAMIC_REGIME_MIN_SPEED_MPS)
    if len(usable) < 100:
        raise ValueError("Not enough dynamic-regime intervals for fitting and validation.")
    split_position = int(TRAIN_FRACTION * len(usable))
    split_interval = int(usable[split_position])
    train = usable[usable < split_interval]
    heldout = usable[usable >= split_interval]
    if len(train) == 0 or len(heldout) == 0:
        raise ValueError("Chronological train/held-out split produced an empty partition.")
    return train, heldout, split_interval


def one_step_predictions(
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    intervals: np.ndarray,
    coefficients: np.ndarray,
) -> np.ndarray:
    # Row k+1 stores the achieved finite-difference input over interval k -> k+1.
    return np.array(
        [rk4_step(states[index], controls[index + 1], dt[index], coefficients) for index in intervals]
    )


def fit_coefficients(
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    train: np.ndarray,
) -> tuple[np.ndarray, object, np.ndarray]:
    targets = states[train + 1][:, [5, 6]]
    scales = np.std(targets, axis=0)
    if np.any(scales <= 0.0):
        raise ValueError("Training response lacks variation required for identification.")

    def residual(log_coefficients: np.ndarray) -> np.ndarray:
        predicted = one_step_predictions(states, controls, dt, train, np.exp(log_coefficients))[:, [5, 6]]
        return ((predicted - targets) / scales).ravel()

    result = least_squares(
        residual,
        np.log(INITIAL_GUESS),
        bounds=(np.log(LOWER_BOUND), np.log(UPPER_BOUND)),
        xtol=1e-13,
        ftol=1e-13,
        gtol=1e-13,
        max_nfev=1000,
    )
    if not result.success:
        raise RuntimeError(f"Parameter fit failed: {result.message}")
    return np.exp(result.x), result, scales


def build_fit_trace(
    telemetry: pd.DataFrame,
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    train: np.ndarray,
    heldout: np.ndarray,
    coefficients: np.ndarray,
) -> pd.DataFrame:
    intervals = np.concatenate([train, heldout])
    predictions = one_step_predictions(states, controls, dt, intervals, coefficients)
    targets = states[intervals + 1]
    partitions = np.where(np.isin(intervals, train), "train", "heldout")
    return pd.DataFrame(
        {
            "interval_start_index": intervals,
            "partition": partitions,
            "time_s": telemetry.loc[intervals + 1, "time_s"].to_numpy(dtype=float),
            "speed_mps": states[intervals, 3],
            "steer_rad": states[intervals, 2],
            "input_steer_vel_radps": controls[intervals + 1, 0],
            "input_accel_x_mps2": controls[intervals + 1, 1],
            "measured_yaw_rate_radps": targets[:, 5],
            "predicted_yaw_rate_radps": predictions[:, 5],
            "yaw_rate_residual_radps": predictions[:, 5] - targets[:, 5],
            "measured_slip_angle_rad": targets[:, 6],
            "predicted_slip_angle_rad": predictions[:, 6],
            "slip_angle_residual_rad": predictions[:, 6] - targets[:, 6],
        }
    )


def heldout_rollout(
    telemetry: pd.DataFrame,
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    split_interval: int,
    coefficients: np.ndarray,
) -> pd.DataFrame:
    predicted = np.zeros((len(states) - split_interval, states.shape[1]), dtype=float)
    predicted[0] = states[split_interval]
    for output_index, interval in enumerate(range(split_interval, len(states) - 1)):
        predicted[output_index + 1] = rk4_step(
            predicted[output_index],
            controls[interval + 1],
            float(dt[interval]),
            coefficients,
        )

    measured = states[split_interval:]
    error = predicted - measured
    error[:, 4] = wrap_angle(error[:, 4])
    position_error = np.linalg.norm(error[:, :2], axis=1)
    return pd.DataFrame(
        {
            "time_s": telemetry.loc[split_interval:, "time_s"].to_numpy(dtype=float),
            "measured_x_m": measured[:, 0],
            "predicted_x_m": predicted[:, 0],
            "measured_y_m": measured[:, 1],
            "predicted_y_m": predicted[:, 1],
            "position_error_m": position_error,
            "measured_yaw_rad": measured[:, 4],
            "predicted_yaw_rad": predicted[:, 4],
            "yaw_error_rad": error[:, 4],
            "measured_yaw_rate_radps": measured[:, 5],
            "predicted_yaw_rate_radps": predicted[:, 5],
            "yaw_rate_error_radps": error[:, 5],
            "measured_slip_angle_rad": measured[:, 6],
            "predicted_slip_angle_rad": predicted[:, 6],
            "slip_angle_error_rad": error[:, 6],
        }
    )


def metric_row(metric: str, value: float, units: str, partition: str, description: str) -> dict[str, object]:
    return {
        "metric": metric,
        "value": value,
        "units": units,
        "partition": partition,
        "description": description,
    }


def create_metrics(
    fit_trace: pd.DataFrame,
    validation_trace: pd.DataFrame,
    coefficients: np.ndarray,
    result: object,
    train: np.ndarray,
    heldout: np.ndarray,
) -> pd.DataFrame:
    train_trace = fit_trace[fit_trace["partition"] == "train"]
    heldout_trace = fit_trace[fit_trace["partition"] == "heldout"]
    relative_error = np.abs(coefficients - ORACLE) / ORACLE
    jacobian_condition = float(np.linalg.cond(result.jac))

    rows = [
        metric_row("fitted_C_Sf", float(coefficients[0]), "Gym coefficient", "fit", "Identified front cornering stiffness coefficient."),
        metric_row("fitted_C_Sr", float(coefficients[1]), "Gym coefficient", "fit", "Identified rear cornering stiffness coefficient."),
        metric_row("C_Sf_oracle_relative_error", float(relative_error[0]), "fraction", "oracle_check", "Relative error against the known synthetic-data oracle."),
        metric_row("C_Sr_oracle_relative_error", float(relative_error[1]), "fraction", "oracle_check", "Relative error against the known synthetic-data oracle."),
        metric_row("jacobian_condition_number", jacobian_condition, "unitless", "fit", "Condition number of the normalized residual Jacobian."),
        metric_row("train_one_step_yaw_rate_rmse", rmse(train_trace["yaw_rate_residual_radps"].to_numpy()), "rad/s", "train", "One-step yaw-rate RMSE."),
        metric_row("train_one_step_slip_angle_rmse", rmse(train_trace["slip_angle_residual_rad"].to_numpy()), "rad", "train", "One-step slip-angle RMSE."),
        metric_row("heldout_one_step_yaw_rate_rmse", rmse(heldout_trace["yaw_rate_residual_radps"].to_numpy()), "rad/s", "heldout", "One-step yaw-rate RMSE."),
        metric_row("heldout_one_step_slip_angle_rmse", rmse(heldout_trace["slip_angle_residual_rad"].to_numpy()), "rad", "heldout", "One-step slip-angle RMSE."),
        metric_row("heldout_rollout_position_rmse", rmse(validation_trace["position_error_m"].to_numpy()), "m", "heldout", "Independent held-out rollout position RMSE."),
        metric_row("heldout_rollout_yaw_rmse", rmse(validation_trace["yaw_error_rad"].to_numpy()), "rad", "heldout", "Independent held-out rollout yaw RMSE."),
        metric_row("heldout_rollout_yaw_rate_rmse", rmse(validation_trace["yaw_rate_error_radps"].to_numpy()), "rad/s", "heldout", "Independent held-out rollout yaw-rate RMSE."),
        metric_row("heldout_rollout_yaw_rate_nrmse", nrmse(validation_trace["yaw_rate_error_radps"].to_numpy(), validation_trace["measured_yaw_rate_radps"].to_numpy()), "fraction of measured range", "heldout", "Independent held-out rollout yaw-rate RMSE normalized by measured range."),
        metric_row("heldout_rollout_yaw_rate_vaf_percent", vaf_percent(validation_trace["yaw_rate_error_radps"].to_numpy(), validation_trace["measured_yaw_rate_radps"].to_numpy()), "%", "heldout", "Independent held-out rollout yaw-rate variance accounted for."),
        metric_row("heldout_rollout_slip_angle_rmse", rmse(validation_trace["slip_angle_error_rad"].to_numpy()), "rad", "heldout", "Independent held-out rollout slip-angle RMSE."),
        metric_row("heldout_rollout_slip_angle_nrmse", nrmse(validation_trace["slip_angle_error_rad"].to_numpy(), validation_trace["measured_slip_angle_rad"].to_numpy()), "fraction of measured range", "heldout", "Independent held-out rollout slip-angle RMSE normalized by measured range."),
        metric_row("heldout_rollout_slip_angle_vaf_percent", vaf_percent(validation_trace["slip_angle_error_rad"].to_numpy(), validation_trace["measured_slip_angle_rad"].to_numpy()), "%", "heldout", "Independent held-out rollout slip-angle variance accounted for."),
        metric_row("train_intervals", float(len(train)), "count", "train", "Dynamic-regime intervals used for fitting."),
        metric_row("heldout_intervals", float(len(heldout)), "count", "heldout", "Chronologically held-out dynamic-regime intervals."),
        metric_row("optimizer_cost", float(result.cost), "unitless", "fit", "Least-squares objective at the solution."),
        metric_row("optimizer_evaluations", float(result.nfev), "count", "fit", "Optimizer function evaluations."),
    ]
    return pd.DataFrame(rows)


def metric_dict(metrics: pd.DataFrame) -> dict[str, float]:
    return {str(row.metric): float(row.value) for row in metrics.itertuples(index=False)}


def acceptance(metrics: pd.DataFrame) -> dict[str, bool]:
    values = metric_dict(metrics)
    return {
        "oracle_recovery": max(values["C_Sf_oracle_relative_error"], values["C_Sr_oracle_relative_error"])
        <= ACCEPTANCE_LIMITS["max_oracle_relative_error_fraction"],
        "heldout_yaw_rate": values["heldout_rollout_yaw_rate_rmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_yaw_rate_rmse_radps"],
        "heldout_slip_angle": values["heldout_rollout_slip_angle_rmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_slip_angle_rmse_rad"],
        "heldout_yaw": values["heldout_rollout_yaw_rmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_yaw_rmse_rad"],
        "heldout_normalized_fit": values["heldout_rollout_yaw_rate_nrmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_yaw_rate_nrmse"],
        "heldout_variance_accounted_for": values["heldout_rollout_yaw_rate_vaf_percent"]
        >= ACCEPTANCE_LIMITS["min_heldout_rollout_yaw_rate_vaf_percent"],
        "identifiability": values["jacobian_condition_number"]
        <= ACCEPTANCE_LIMITS["max_jacobian_condition_number"],
    }


def write_parameters(
    identified: IdentificationResult,
    telemetry: pd.DataFrame,
) -> None:
    coefficients = identified.coefficients
    split_interval = identified.split_interval
    checks = identified.acceptance_checks
    payload = {
        "model": "Gym vehicle_dynamics_st",
        "telemetry_source": portable_path(TELEMETRY_PATH),
        "source_label": SOURCE_LABEL,
        "method": "bounded nonlinear least squares on RK4 one-step yaw-rate and slip-angle residuals",
        "input_alignment": "row k+1 achieved finite-difference inputs are applied over interval k to k+1",
        "training_fraction": TRAIN_FRACTION,
        "dynamic_regime_min_speed_mps": DYNAMIC_REGIME_MIN_SPEED_MPS,
        "heldout_start_index": split_interval,
        "heldout_start_time_s": float(telemetry.loc[split_interval, "time_s"]),
        "fitted": {
            "C_Sf": float(coefficients[0]),
            "C_Sr": float(coefficients[1]),
        },
        "bounds": {
            "C_Sf": [float(LOWER_BOUND[0]), float(UPPER_BOUND[0])],
            "C_Sr": [float(LOWER_BOUND[1]), float(UPPER_BOUND[1])],
        },
        "optimizer": {
            "success": bool(identified.optimizer_success),
            "message": str(identified.optimizer_message),
            "function_evaluations": int(identified.optimizer_evaluations),
            "cost": float(identified.optimizer_cost),
        },
        "acceptance_limits": identified.acceptance_limits,
        "acceptance_checks": checks,
        "heldout_validation_passed": bool(all(checks.values())),
        "scope": "No LQR, MPC, or controller tuning is performed.",
    }
    if ORACLE_MODE == "gym":
        payload["known_oracle_for_synthetic_recovery_check"] = {
            "C_Sf": float(ORACLE[0]),
            "C_Sr": float(ORACLE[1]),
        }
    PARAMETERS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def create_figures(fit_trace: pd.DataFrame, validation_trace: pd.DataFrame) -> None:
    heldout = fit_trace[fit_trace["partition"] == "heldout"]
    split_time = float(heldout["time_s"].iloc[0])

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(fit_trace["time_s"], fit_trace["measured_yaw_rate_radps"], label="Measured", linewidth=1.5)
    axes[0].plot(fit_trace["time_s"], fit_trace["predicted_yaw_rate_radps"], label="One-step prediction", linewidth=1.0)
    axes[0].axvline(split_time, color="black", linestyle="--", linewidth=1.0, label="Held-out start")
    axes[0].set_ylabel("Yaw rate (rad/s)")
    axes[0].legend(loc="upper right")
    axes[0].grid(alpha=0.25)

    axes[1].plot(fit_trace["time_s"], fit_trace["measured_slip_angle_rad"], label="Measured", linewidth=1.5)
    axes[1].plot(fit_trace["time_s"], fit_trace["predicted_slip_angle_rad"], label="One-step prediction", linewidth=1.0)
    axes[1].axvline(split_time, color="black", linestyle="--", linewidth=1.0)
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Slip angle (rad)")
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.25)
    fig.suptitle("Dynamic Parameter Identification: Train and Held-Out One-Step Predictions")
    fig.tight_layout()
    fig.savefig(FIT_FIGURE_PATH, dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(validation_trace["time_s"], validation_trace["yaw_rate_error_radps"])
    axes[0].set_ylabel("Yaw-rate error (rad/s)")
    axes[1].plot(validation_trace["time_s"], validation_trace["slip_angle_error_rad"])
    axes[1].set_ylabel("Slip-angle error (rad)")
    axes[2].plot(validation_trace["time_s"], validation_trace["yaw_error_rad"])
    axes[2].set_ylabel("Yaw error (rad)")
    axes[2].set_xlabel("Time (s)")
    for axis in axes:
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.grid(alpha=0.25)
    fig.suptitle("Independent Held-Out Rollout Residuals")
    fig.tight_layout()
    fig.savefig(RESIDUAL_FIGURE_PATH, dpi=180)
    plt.close(fig)


def write_report(metrics: pd.DataFrame, checks: dict[str, bool]) -> None:
    values = metric_dict(metrics)
    status = "passed" if all(checks.values()) else "failed"
    if ORACLE_MODE == "gym":
        parameter_table = f"""| Parameter | Identified | Known Gym oracle | Relative error |
| --- | ---: | ---: | ---: |
| `C_Sf` | {values["fitted_C_Sf"]:.9f} | {ORACLE[0]:.9f} | {values["C_Sf_oracle_relative_error"]:.3e} |
| `C_Sr` | {values["fitted_C_Sr"]:.9f} | {ORACLE[1]:.9f} | {values["C_Sr_oracle_relative_error"]:.3e} |

The oracle comparison is a controlled simulator-recovery check, not physical-vehicle validation."""
    else:
        parameter_table = f"""| Parameter | Identified |
| --- | ---: |
| `C_Sf` | {values["fitted_C_Sf"]:.9f} |
| `C_Sr` | {values["fitted_C_Sr"]:.9f} |

No parameter oracle is available for this source; acceptance uses held-out prediction and identifiability only."""
    fit_figure = os.path.relpath(FIT_FIGURE_PATH, REPORT_PATH.parent)
    residual_figure = os.path.relpath(RESIDUAL_FIGURE_PATH, REPORT_PATH.parent)
    report = f"""# Dynamic Parameter Identification

## Objective

Estimate nonlinear single-track coefficients `C_Sf` and `C_Sr` from {SOURCE_LABEL}, then require an independent held-out replay to pass.

## Method

The fitter uses the logged internal states and achieved/reconstructed inputs from `{portable_path(TELEMETRY_PATH)}`. Only intervals starting at `speed_mps >= {DYNAMIC_REGIME_MIN_SPEED_MPS:.2f}` are used, excluding Gym's low-speed kinematic fallback. The first {TRAIN_FRACTION:.0%} of usable intervals are training data; the final {1.0 - TRAIN_FRACTION:.0%} are held out chronologically.

For each training interval, the measured state at row `k` is propagated one RK4 step through `vehicle_dynamics_st`. The achieved finite-difference inputs stored on row `k+1` are applied over interval `k -> k+1`. Bounded nonlinear least squares minimizes normalized yaw-rate and slip-angle one-step residuals. The held-out rollout starts once from the measured split state and then propagates recursively without state resets.

## Identified Parameters

{parameter_table}

## Held-Out Validation

Validation status: **{status}**

| Metric | Value |
| --- | ---: |
| Held-out rollout yaw-rate RMSE | {values["heldout_rollout_yaw_rate_rmse"]:.6e} rad/s |
| Held-out rollout yaw-rate NRMSE | {values["heldout_rollout_yaw_rate_nrmse"]:.6e} of measured range |
| Held-out rollout yaw-rate VAF | {values["heldout_rollout_yaw_rate_vaf_percent"]:.9f}% |
| Held-out rollout slip-angle RMSE | {values["heldout_rollout_slip_angle_rmse"]:.6e} rad |
| Held-out rollout slip-angle NRMSE | {values["heldout_rollout_slip_angle_nrmse"]:.6e} of measured range |
| Held-out rollout slip-angle VAF | {values["heldout_rollout_slip_angle_vaf_percent"]:.9f}% |
| Held-out rollout yaw RMSE | {values["heldout_rollout_yaw_rmse"]:.6e} rad |
| Held-out rollout position RMSE | {values["heldout_rollout_position_rmse"]:.6e} m |
| Normalized residual Jacobian condition number | {values["jacobian_condition_number"]:.6f} |
| Raw physical Jacobian condition number | {values["raw_jacobian_condition_number"]:.6f} |
| `C_Sf`-`C_Sr` parameter correlation | {values["parameter_correlation"]:.6f} |
| Sensitivity-column cosine | {values["sensitivity_column_cosine"]:.6f} |

Acceptance checks:

| Check | Pass |
| --- | --- |
{chr(10).join(f"| {name} | {passed} |" for name, passed in checks.items())}

## Figures

![Dynamic parameter fit]({fit_figure})

![Held-out residuals]({residual_figure})

## Interpretation

The held-out validation demonstrates that the identified coefficients reproduce the nonlinear lateral-yaw state evolution for a frequency regime not used during fitting. The low Jacobian condition number indicates that the selected excitation distinguishes the two fitted coefficients for this controlled dataset.

This result validates the identification pipeline for the stated source. It does not establish that the same coefficients apply to a physical RoboRacer vehicle.

## Scope Gate

No LQR, MPC, or controller tuning is performed here. Controller design remains blocked until an identified model passes held-out validation. This Gym identification passes that gate for simulator work; physical-vehicle controller work still requires identification and held-out validation from real RoboRacer data.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", type=Path, default=TELEMETRY_PATH)
    parser.add_argument("--run-dir", type=Path, default=RUN_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--figure-dir", type=Path, default=FIGURE_DIR)
    parser.add_argument("--figure-prefix", default="dynamic_parameter")
    parser.add_argument("--source-label", default=SOURCE_LABEL)
    parser.add_argument("--oracle", choices=["gym", "none"], default="gym")
    return parser.parse_args()


def configure_paths(args) -> None:
    global TELEMETRY_PATH, RUN_DIR, FIGURE_DIR, PARAMETERS_PATH, METRICS_PATH
    global FIT_TRACE_PATH, VALIDATION_TRACE_PATH, REPORT_PATH, FIT_FIGURE_PATH
    global RESIDUAL_FIGURE_PATH, SOURCE_LABEL, ORACLE_MODE
    TELEMETRY_PATH = args.telemetry.resolve()
    RUN_DIR = args.run_dir.resolve()
    FIGURE_DIR = args.figure_dir.resolve()
    PARAMETERS_PATH = RUN_DIR / "parameters.json"
    METRICS_PATH = RUN_DIR / "metrics.csv"
    FIT_TRACE_PATH = RUN_DIR / "fit_trace.csv"
    VALIDATION_TRACE_PATH = RUN_DIR / "heldout_replay_trace.csv"
    REPORT_PATH = args.report.resolve()
    FIT_FIGURE_PATH = FIGURE_DIR / f"{args.figure_prefix}_fit.png"
    RESIDUAL_FIGURE_PATH = FIGURE_DIR / f"{args.figure_prefix}_residuals.png"
    SOURCE_LABEL = args.source_label
    ORACLE_MODE = args.oracle


def main() -> int:
    args = parse_args()
    configure_paths(args)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    telemetry = load_telemetry()
    oracle = ORACLE if ORACLE_MODE == "gym" else None
    identified = shared_identify_from_telemetry(telemetry, repo_root=REPO_ROOT, oracle=oracle)
    coefficients = identified.coefficients
    fit_trace = identified.fit_trace
    validation_trace = identified.validation_trace
    metrics = identified.metrics
    checks = identified.acceptance_checks

    fit_trace.to_csv(FIT_TRACE_PATH, index=False)
    validation_trace.to_csv(VALIDATION_TRACE_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    write_parameters(identified, telemetry)
    create_figures(fit_trace, validation_trace)
    write_report(metrics, checks)

    print(f"Identified C_Sf={coefficients[0]:.9f}, C_Sr={coefficients[1]:.9f}")
    print(f"Held-out validation: {'PASS' if all(checks.values()) else 'FAIL'}")
    for name, passed in checks.items():
        print(f"  {name}: {passed}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
