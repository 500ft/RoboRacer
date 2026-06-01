#!/usr/bin/env python
"""Replay RK4 telemetry through Gym's known-parameter nonlinear single-track model."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import importlib.util
import types

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

if importlib.util.find_spec("numba") is None:
    numba_stub = types.ModuleType("numba")

    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]

        def decorator(func):
            return func

        return decorator

    numba_stub.njit = njit
    sys.modules["numba"] = numba_stub

dynamic_models_path = REPO_ROOT / "gym" / "f110_gym" / "envs" / "dynamic_models.py"
dynamic_models_spec = importlib.util.spec_from_file_location("dynamic_models", dynamic_models_path)
if dynamic_models_spec is None or dynamic_models_spec.loader is None:
    raise ImportError(f"Could not load dynamic model source: {dynamic_models_path}")
dynamic_models = importlib.util.module_from_spec(dynamic_models_spec)
sys.modules["dynamic_models"] = dynamic_models
dynamic_models_spec.loader.exec_module(dynamic_models)
vehicle_dynamics_st = dynamic_models.vehicle_dynamics_st

TELEMETRY_PATH = REPO_ROOT / "runs" / "first_lap" / "telemetry.csv"
KINEMATIC_TRACE_PATH = REPO_ROOT / "runs" / "model_vs_gym_comparison" / "replay_trace.csv"
RUN_DIR = REPO_ROOT / "runs" / "dynamic_model_replay"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
TRACE_PATH = RUN_DIR / "replay_trace.csv"
METRICS_PATH = RUN_DIR / "metrics.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
REPORT_PATH = REPO_ROOT / "reports" / "dynamic_model_replay.md"
YAW_RATE_FIGURE_PATH = FIGURE_DIR / "dynamic_replay_yaw_rate_overlay.png"
STATE_ERRORS_FIGURE_PATH = FIGURE_DIR / "dynamic_replay_state_errors.png"

PARAMS = {
    "mu": 1.0489,
    "C_Sf": 4.718,
    "C_Sr": 5.4562,
    "lf": 0.15875,
    "lr": 0.17145,
    "h": 0.074,
    "m": 3.74,
    "I": 0.04712,
    "s_min": -0.4189,
    "s_max": 0.4189,
    "sv_min": -3.2,
    "sv_max": 3.2,
    "v_switch": 7.319,
    "a_max": 9.51,
    "v_min": -5.0,
    "v_max": 20.0,
}

REQUIRED_COLUMNS = [
    "integrator",
    "time_s",
    "x_m",
    "y_m",
    "theta_rad",
    "speed_mps",
    "steer_rad",
    "yaw_rate_radps",
    "accel_x_mps2",
]


def wrap_angle(angle: np.ndarray | float) -> np.ndarray | float:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def load_rk4_telemetry(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing telemetry: {path}")
    telemetry = pd.read_csv(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in telemetry.columns]
    if missing:
        raise ValueError(f"Telemetry missing required columns: {missing}")

    rk4 = telemetry[telemetry["integrator"].astype(str).str.lower().eq("rk4")].copy()
    if rk4.empty:
        raise ValueError("No RK4 telemetry rows found.")

    numeric_columns = [column for column in REQUIRED_COLUMNS if column != "integrator"]
    for column in numeric_columns:
        rk4[column] = pd.to_numeric(rk4[column], errors="raise")

    return rk4.sort_values("time_s").reset_index(drop=True)


def validate_dt(time_s: np.ndarray) -> np.ndarray:
    dt = np.diff(time_s)
    if dt.size == 0:
        raise ValueError("Need at least two telemetry samples.")
    if np.any(dt <= 0.0):
        raise ValueError("Telemetry time_s must be strictly increasing.")
    ratio = float(np.max(dt) / np.min(dt))
    if ratio > 1.2:
        raise ValueError(f"Telemetry dt is not sufficiently uniform: ratio={ratio:.6f}")
    return dt


def dynamics_derivative(state: np.ndarray, steering_velocity: float, accel_x: float) -> np.ndarray:
    return vehicle_dynamics_st(
        state,
        np.array([steering_velocity, accel_x], dtype=float),
        PARAMS["mu"],
        PARAMS["C_Sf"],
        PARAMS["C_Sr"],
        PARAMS["lf"],
        PARAMS["lr"],
        PARAMS["h"],
        PARAMS["m"],
        PARAMS["I"],
        PARAMS["s_min"],
        PARAMS["s_max"],
        PARAMS["sv_min"],
        PARAMS["sv_max"],
        PARAMS["v_switch"],
        PARAMS["a_max"],
        PARAMS["v_min"],
        PARAMS["v_max"],
    )


def rk4_step(state: np.ndarray, steering_velocity: float, accel_x: float, dt: float) -> np.ndarray:
    k1 = dynamics_derivative(state, steering_velocity, accel_x)
    k2 = dynamics_derivative(state + 0.5 * dt * k1, steering_velocity, accel_x)
    k3 = dynamics_derivative(state + 0.5 * dt * k2, steering_velocity, accel_x)
    k4 = dynamics_derivative(state + dt * k3, steering_velocity, accel_x)
    next_state = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    next_state[4] = float(wrap_angle(next_state[4]))
    return next_state


def kinematic_yaw_rate(speed: np.ndarray, steer: np.ndarray) -> np.ndarray:
    lf = PARAMS["lf"]
    lr = PARAMS["lr"]
    beta = np.arctan((lr / (lf + lr)) * np.tan(steer))
    return (speed / lr) * np.sin(beta)


def replay_dynamic_model(rk4: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    time_s = rk4["time_s"].to_numpy(dtype=float)
    dt = validate_dt(time_s)
    steer = rk4["steer_rad"].to_numpy(dtype=float)
    steering_velocity = np.diff(steer) / dt
    steering_velocity_for_trace = np.append(steering_velocity, np.nan)

    slip_columns = [column for column in rk4.columns if "slip" in column.lower() or column.lower() == "beta"]
    slip_angle_column = slip_columns[0] if slip_columns else None
    if slip_angle_column:
        initial_beta = float(rk4.loc[0, slip_angle_column])
        slip_note = f"initialized from telemetry column {slip_angle_column}"
    else:
        initial_beta = 0.0
        slip_note = "0.0 because slip angle is not logged"

    states = np.zeros((len(rk4), 7), dtype=float)
    states[0] = np.array(
        [
            float(rk4.loc[0, "x_m"]),
            float(rk4.loc[0, "y_m"]),
            float(rk4.loc[0, "steer_rad"]),
            float(rk4.loc[0, "speed_mps"]),
            float(rk4.loc[0, "theta_rad"]),
            float(rk4.loc[0, "yaw_rate_radps"]),
            initial_beta,
        ],
        dtype=float,
    )

    for idx, step_dt in enumerate(dt):
        states[idx + 1] = rk4_step(
            states[idx],
            float(steering_velocity[idx]),
            float(rk4.loc[idx, "accel_x_mps2"]),
            float(step_dt),
        )

    trace = pd.DataFrame(
        {
            "time_s": time_s,
            "dt_to_next_s": np.append(dt, np.nan),
            "input_steering_velocity_radps": steering_velocity_for_trace,
            "input_accel_x_mps2": rk4["accel_x_mps2"].to_numpy(dtype=float),
            "gym_x_m": rk4["x_m"].to_numpy(dtype=float),
            "gym_y_m": rk4["y_m"].to_numpy(dtype=float),
            "gym_steer_rad": rk4["steer_rad"].to_numpy(dtype=float),
            "gym_speed_mps": rk4["speed_mps"].to_numpy(dtype=float),
            "gym_theta_rad": rk4["theta_rad"].to_numpy(dtype=float),
            "gym_yaw_rate_radps": rk4["yaw_rate_radps"].to_numpy(dtype=float),
            "dynamic_x_m": states[:, 0],
            "dynamic_y_m": states[:, 1],
            "dynamic_steer_rad": states[:, 2],
            "dynamic_speed_mps": states[:, 3],
            "dynamic_theta_rad": states[:, 4],
            "dynamic_yaw_rate_radps": states[:, 5],
            "dynamic_slip_angle_rad": states[:, 6],
        }
    )
    trace["kinematic_yaw_rate_radps"] = kinematic_yaw_rate(trace["gym_speed_mps"].to_numpy(), trace["gym_steer_rad"].to_numpy())
    trace["error_x_m"] = trace["dynamic_x_m"] - trace["gym_x_m"]
    trace["error_y_m"] = trace["dynamic_y_m"] - trace["gym_y_m"]
    trace["error_position_m"] = np.sqrt(trace["error_x_m"] ** 2 + trace["error_y_m"] ** 2)
    trace["error_yaw_rad"] = wrap_angle(trace["dynamic_theta_rad"] - trace["gym_theta_rad"])
    trace["error_yaw_rate_radps"] = trace["dynamic_yaw_rate_radps"] - trace["gym_yaw_rate_radps"]
    trace["error_speed_mps"] = trace["dynamic_speed_mps"] - trace["gym_speed_mps"]

    metadata = {
        "slip_angle_initialization": slip_note,
        "slip_angle_column": slip_angle_column or "",
    }
    return trace, metadata


def rmse(values: pd.Series | np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(arr**2)))


def metric_rows(trace: pd.DataFrame, metadata: dict[str, str]) -> list[dict[str, str | float]]:
    kinematic_yaw_error = trace["kinematic_yaw_rate_radps"] - trace["gym_yaw_rate_radps"]
    kinematic_yaw_rmse = rmse(kinematic_yaw_error)
    dynamic_yaw_rmse = rmse(trace["error_yaw_rate_radps"])
    improvement = 100.0 * (kinematic_yaw_rmse - dynamic_yaw_rmse) / kinematic_yaw_rmse if kinematic_yaw_rmse else np.nan

    return [
        {"metric": "rmse_x_m", "value": rmse(trace["error_x_m"]), "units": "m", "description": "RMSE global x position error."},
        {"metric": "rmse_y_m", "value": rmse(trace["error_y_m"]), "units": "m", "description": "RMSE global y position error."},
        {"metric": "rmse_position_m", "value": rmse(trace["error_position_m"]), "units": "m", "description": "RMSE position error."},
        {"metric": "max_position_error_m", "value": float(trace["error_position_m"].max()), "units": "m", "description": "Maximum position error."},
        {"metric": "final_position_error_m", "value": float(trace["error_position_m"].iloc[-1]), "units": "m", "description": "Final position error."},
        {"metric": "rmse_yaw_rad", "value": rmse(trace["error_yaw_rad"]), "units": "rad", "description": "RMSE wrapped yaw error."},
        {"metric": "max_abs_yaw_error_rad", "value": float(trace["error_yaw_rad"].abs().max()), "units": "rad", "description": "Maximum absolute wrapped yaw error."},
        {"metric": "rmse_yaw_rate_radps", "value": dynamic_yaw_rmse, "units": "rad/s", "description": "RMSE yaw-rate error for dynamic replay."},
        {"metric": "max_abs_yaw_rate_error_radps", "value": float(trace["error_yaw_rate_radps"].abs().max()), "units": "rad/s", "description": "Maximum absolute yaw-rate error."},
        {"metric": "final_yaw_rate_error_radps", "value": float(trace["error_yaw_rate_radps"].iloc[-1]), "units": "rad/s", "description": "Final yaw-rate error."},
        {"metric": "rmse_speed_mps", "value": rmse(trace["error_speed_mps"]), "units": "m/s", "description": "RMSE speed error."},
        {"metric": "max_abs_speed_error_mps", "value": float(trace["error_speed_mps"].abs().max()), "units": "m/s", "description": "Maximum absolute speed error."},
        {"metric": "num_samples", "value": int(len(trace)), "units": "count", "description": "Number of RK4 telemetry samples replayed."},
        {"metric": "duration_s", "value": float(trace["time_s"].iloc[-1] - trace["time_s"].iloc[0]), "units": "s", "description": "Elapsed replay duration."},
        {"metric": "kinematic_yaw_rate_rmse_radps", "value": kinematic_yaw_rmse, "units": "rad/s", "description": "Kinematic yaw-rate RMSE baseline from the same telemetry."},
        {"metric": "dynamic_yaw_rate_rmse_radps", "value": dynamic_yaw_rmse, "units": "rad/s", "description": "Dynamic replay yaw-rate RMSE."},
        {"metric": "yaw_rate_rmse_improvement_percent", "value": float(improvement), "units": "%", "description": "Percent improvement in yaw-rate RMSE relative to kinematic yaw law."},
        {"metric": "initial_slip_angle_rad", "value": float(trace["dynamic_slip_angle_rad"].iloc[0]), "units": "rad", "description": metadata["slip_angle_initialization"]},
    ]


def metrics_as_dict(metrics: pd.DataFrame) -> dict[str, float]:
    return {str(row.metric): float(row.value) for row in metrics.itertuples(index=False)}


def write_metadata(metadata: dict[str, str]) -> None:
    payload = {
        "model": "vehicle_dynamics_st",
        "parameter_source": "gym/f110_gym/envs/f110_env.py",
        "model_source": "gym/f110_gym/envs/dynamic_models.py",
        "integrator": "RK4",
        "telemetry_source": "runs/first_lap/telemetry.csv",
        "telemetry_integrator_filter": "rk4",
        "slip_angle_initialization": metadata["slip_angle_initialization"],
        "input_convention": "[steering_velocity, longitudinal_acceleration]",
        "state_convention": "[x, y, steer_angle, speed, yaw, yaw_rate, slip_angle]",
    }
    METADATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def save_yaw_rate_figure(trace: pd.DataFrame, output_path: Path) -> None:
    time_s = trace["time_s"]
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    ax.plot(time_s, trace["gym_yaw_rate_radps"], linewidth=2.0, label="Gym yaw rate", color="#1f77b4")
    ax.plot(time_s, trace["kinematic_yaw_rate_radps"], linewidth=1.5, linestyle="--", label="Kinematic yaw law", color="#9467bd")
    ax.plot(time_s, trace["dynamic_yaw_rate_radps"], linewidth=1.7, label="Dynamic replay yaw rate", color="#d62728")
    ax.axvline(2.0, color="#555555", linestyle=":", linewidth=1.4, label="t = 2.0 s diagnostic")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Yaw rate [rad/s]")
    ax.grid(True, alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(time_s, trace["gym_steer_rad"], linewidth=1.0, alpha=0.55, color="#2ca02c", label="Achieved steering")
    ax2.set_ylabel("Steering [rad]")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper right", framealpha=0.95)
    ax.set_title("Known-Parameter Dynamic Replay Yaw Rate")
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_state_error_figure(trace: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True, constrained_layout=True)
    time_s = trace["time_s"]
    series = [
        ("error_position_m", "Position error [m]", "#1f77b4"),
        ("error_yaw_rad", "Yaw error [rad]", "#9467bd"),
        ("error_yaw_rate_radps", "Yaw-rate error [rad/s]", "#d62728"),
        ("error_speed_mps", "Speed error [m/s]", "#2ca02c"),
    ]
    for ax, (column, ylabel, color) in zip(axes, series):
        ax.plot(time_s, trace[column], linewidth=1.6, color=color)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Time [s]")
    fig.suptitle("Known-Parameter Dynamic Replay State Errors")
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def metric_table(metrics: pd.DataFrame, selected: list[str]) -> str:
    labels = {
        "rmse_position_m": "RMSE position",
        "max_position_error_m": "Max position error",
        "final_position_error_m": "Final position error",
        "rmse_yaw_rad": "RMSE yaw",
        "rmse_yaw_rate_radps": "RMSE yaw rate",
        "max_abs_yaw_rate_error_radps": "Max abs yaw-rate error",
        "final_yaw_rate_error_radps": "Final yaw-rate error",
        "rmse_speed_mps": "RMSE speed",
        "num_samples": "Number of samples",
        "duration_s": "Duration",
        "kinematic_yaw_rate_rmse_radps": "Kinematic yaw-rate RMSE",
        "dynamic_yaw_rate_rmse_radps": "Dynamic yaw-rate RMSE",
        "yaw_rate_rmse_improvement_percent": "Yaw-rate RMSE improvement",
    }
    metric_map = {str(row.metric): row for row in metrics.itertuples(index=False)}
    lines = ["| Metric | Value | Units |", "| --- | ---: | --- |"]
    for key in selected:
        row = metric_map[key]
        lines.append(f"| {labels[key]} | {float(row.value):.6g} | {row.units} |")
    return "\n".join(lines)


def write_report(metrics: pd.DataFrame, metadata: dict[str, str], output_path: Path) -> None:
    summary_keys = [
        "rmse_position_m",
        "max_position_error_m",
        "final_position_error_m",
        "rmse_yaw_rad",
        "rmse_yaw_rate_radps",
        "max_abs_yaw_rate_error_radps",
        "final_yaw_rate_error_radps",
        "rmse_speed_mps",
        "num_samples",
        "duration_s",
    ]
    comparison_keys = [
        "kinematic_yaw_rate_rmse_radps",
        "dynamic_yaw_rate_rmse_radps",
        "yaw_rate_rmse_improvement_percent",
    ]

    slip_text = (
        "The initial slip angle is set to zero because slip angle is not available in the current telemetry. "
        "This can introduce an initial transient, so early-time dynamic replay error should not be interpreted as tire-parameter error."
        if metadata["slip_angle_column"] == ""
        else f"The initial slip angle is read from telemetry column `{metadata['slip_angle_column']}`."
    )

    text = f"""# Known-Parameter Dynamic Model Replay

## Objective

Test whether Gym's nonlinear single-track model structure can reproduce the yaw-rate behavior that the kinematic replay could not.

## Model Source

This replay uses Gym's known nonlinear single-track parameters as an oracle/reference case. It is not system identification. The purpose is to test whether the dynamic model structure and state/input convention reproduce the yaw-rate behavior that the kinematic replay could not.

- Model function: `vehicle_dynamics_st`
- Model source: `gym/f110_gym/envs/dynamic_models.py`
- Parameter source: `gym/f110_gym/envs/f110_env.py`

## Parameters

The replay uses the default nonlinear single-track parameters recorded in `docs/parameter_inventory.md`.

## Inputs

- Telemetry: `runs/first_lap/telemetry.csv`
- Integrator filtered: `rk4`
- State order: `[x, y, steer_angle, speed, yaw, yaw_rate, slip_angle]`
- Input order: `[steering_velocity, longitudinal_acceleration]`
- Steering velocity: reconstructed from achieved `steer_rad` by forward difference over each interval
- Longitudinal acceleration: `accel_x_mps2`

## Method

The state is initialized from the first RK4 telemetry row. The replay then integrates `vehicle_dynamics_st` with RK4 over each logged telemetry interval and compares the propagated state at row `k+1` against telemetry row `k+1`.

## Results

{metric_table(metrics, summary_keys)}

## Comparison Against Kinematic Replay

{metric_table(metrics, comparison_keys)}

## Figures

![Dynamic replay yaw-rate overlay](figures/dynamic_replay_yaw_rate_overlay.png)

![Dynamic replay state errors](figures/dynamic_replay_state_errors.png)

## Limitations

{slip_text}

The replay uses logged longitudinal acceleration as the best available input proxy. That signal may not be the exact constrained acceleration used internally during the original Gym integration, so residual drift should be interpreted as replay/input-reconstruction error before treating it as model-structure error.

This is not parameter identification, not controller design, and not proof that fitted dynamic parameters have been recovered.

## Next Step

Use this oracle replay to decide the first system-identification experiment. The next sysID branch should excite steering and fit dynamic tire parameters only after the known-parameter replay path is accepted.
"""
    output_path.write_text(text, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    rk4 = load_rk4_telemetry(TELEMETRY_PATH)
    trace, metadata = replay_dynamic_model(rk4)
    metrics = pd.DataFrame(metric_rows(trace, metadata), columns=["metric", "value", "units", "description"])

    trace.to_csv(TRACE_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    write_metadata(metadata)
    save_yaw_rate_figure(trace, YAW_RATE_FIGURE_PATH)
    save_state_error_figure(trace, STATE_ERRORS_FIGURE_PATH)
    write_report(metrics, metadata, REPORT_PATH)

    metric_values = metrics_as_dict(metrics)
    print(f"Wrote replay trace to {TRACE_PATH}")
    print(f"Wrote metrics to {METRICS_PATH}")
    print(f"Wrote metadata to {METADATA_PATH}")
    print(f"Wrote yaw-rate figure to {YAW_RATE_FIGURE_PATH}")
    print(f"Wrote state-error figure to {STATE_ERRORS_FIGURE_PATH}")
    print(f"Wrote report to {REPORT_PATH}")
    print(
        "Summary: "
        f"dynamic yaw-rate RMSE={metric_values['dynamic_yaw_rate_rmse_radps']:.3f} rad/s, "
        f"kinematic yaw-rate RMSE={metric_values['kinematic_yaw_rate_rmse_radps']:.3f} rad/s, "
        f"improvement={metric_values['yaw_rate_rmse_improvement_percent']:.1f}%"
    )


if __name__ == "__main__":
    main()
