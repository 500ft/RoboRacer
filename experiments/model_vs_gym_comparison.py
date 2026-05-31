#!/usr/bin/env python
"""Replay Gym telemetry through the documented kinematic bicycle model."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

TELEMETRY_PATH = REPO_ROOT / "runs" / "first_lap" / "telemetry.csv"
RUN_DIR = REPO_ROOT / "runs" / "model_vs_gym_comparison"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
REPORT_PATH = REPO_ROOT / "reports" / "model_vs_gym_comparison.md"
TRACE_PATH = RUN_DIR / "replay_trace.csv"
METRICS_PATH = RUN_DIR / "metrics.csv"
TRAJECTORY_FIGURE_PATH = FIGURE_DIR / "model_vs_gym_trajectory_error.png"
STATE_ERRORS_FIGURE_PATH = FIGURE_DIR / "model_vs_gym_state_errors.png"

LF_M = 0.15875
LR_M = 0.17145
DT_RATIO_LIMIT = 1.2
DT_GAP_FACTOR_LIMIT = 3.0

REQUIRED_COLUMNS = [
    "integrator",
    "time_s",
    "x_m",
    "y_m",
    "theta_rad",
    "speed_mps",
    "accel_x_mps2",
    "steer_rad",
    "command_steer_rad",
    "accel_y_mps2",
]


def ensure_exists(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def wrap_angle(angle: np.ndarray | float) -> np.ndarray | float:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def load_rk4_telemetry(path: Path) -> pd.DataFrame:
    ensure_exists(path, "first-lap telemetry")
    telemetry = pd.read_csv(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in telemetry.columns]
    if missing:
        raise ValueError(
            f"Telemetry missing required columns: {missing}\n"
            f"Available columns: {list(telemetry.columns)}"
        )

    rk4 = telemetry[telemetry["integrator"].astype(str).str.lower().eq("rk4")].copy()
    if rk4.empty:
        raise ValueError("No RK4 rows found in first-lap telemetry.")

    numeric_columns = [
        "time_s",
        "x_m",
        "y_m",
        "theta_rad",
        "speed_mps",
        "accel_x_mps2",
        "steer_rad",
        "command_steer_rad",
        "accel_y_mps2",
    ]
    for column in numeric_columns:
        rk4[column] = pd.to_numeric(rk4[column], errors="raise")

    return rk4.sort_values("time_s").reset_index(drop=True)


def dt_summary(time_s: np.ndarray) -> dict[str, float]:
    dt = np.diff(time_s)
    if dt.size == 0:
        raise ValueError("Need at least two telemetry samples for replay.")
    if np.any(dt <= 0.0):
        raise ValueError("Telemetry time_s must be strictly increasing.")

    dt_min = float(np.min(dt))
    dt_max = float(np.max(dt))
    dt_mean = float(np.mean(dt))
    dt_median = float(np.median(dt))
    ratio = dt_max / dt_min

    if ratio > DT_RATIO_LIMIT or dt_max > DT_GAP_FACTOR_LIMIT * dt_median:
        raise ValueError(
            "Telemetry dt has a large gap or jitter: "
            f"dt_min={dt_min:.9f}, dt_max={dt_max:.9f}, ratio={ratio:.6f}"
        )

    return {
        "dt_min_s": dt_min,
        "dt_max_s": dt_max,
        "dt_mean_s": dt_mean,
        "dt_median_s": dt_median,
        "dt_ratio": float(ratio),
    }


def kinematic_derivative(state: np.ndarray, accel: float, steer: float) -> np.ndarray:
    x, y, psi, velocity = state
    beta = np.arctan((LR_M / (LF_M + LR_M)) * np.tan(steer))
    return np.array(
        [
            velocity * np.cos(psi + beta),
            velocity * np.sin(psi + beta),
            (velocity / LR_M) * np.sin(beta),
            accel,
        ],
        dtype=float,
    )


def rk4_step(state: np.ndarray, accel: float, steer: float, dt: float) -> np.ndarray:
    k1 = kinematic_derivative(state, accel, steer)
    k2 = kinematic_derivative(state + 0.5 * dt * k1, accel, steer)
    k3 = kinematic_derivative(state + 0.5 * dt * k2, accel, steer)
    k4 = kinematic_derivative(state + dt * k3, accel, steer)
    next_state = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    next_state[2] = float(wrap_angle(next_state[2]))
    return next_state


def replay_kinematic_model(rk4: pd.DataFrame) -> pd.DataFrame:
    time_s = rk4["time_s"].to_numpy(dtype=float)
    summary = dt_summary(time_s)
    dt = np.diff(time_s)

    model = np.zeros((len(rk4), 4), dtype=float)
    model[0] = rk4.loc[0, ["x_m", "y_m", "theta_rad", "speed_mps"]].to_numpy(dtype=float)

    for idx, step_dt in enumerate(dt):
        accel = float(rk4.loc[idx, "accel_x_mps2"])
        steer = float(rk4.loc[idx, "steer_rad"])
        model[idx + 1] = rk4_step(model[idx], accel, steer, float(step_dt))

    trace = pd.DataFrame(
        {
            "time_s": time_s,
            "dt_to_next_s": np.append(dt, np.nan),
            "input_accel_x_mps2": rk4["accel_x_mps2"].to_numpy(dtype=float),
            "input_steer_rad": rk4["steer_rad"].to_numpy(dtype=float),
            "command_steer_rad": rk4["command_steer_rad"].to_numpy(dtype=float),
            "gym_x_m": rk4["x_m"].to_numpy(dtype=float),
            "gym_y_m": rk4["y_m"].to_numpy(dtype=float),
            "gym_theta_rad": rk4["theta_rad"].to_numpy(dtype=float),
            "gym_speed_mps": rk4["speed_mps"].to_numpy(dtype=float),
            "model_x_m": model[:, 0],
            "model_y_m": model[:, 1],
            "model_theta_rad": model[:, 2],
            "model_speed_mps": model[:, 3],
            "accel_y_mps2": rk4["accel_y_mps2"].to_numpy(dtype=float),
        }
    )
    trace["error_x_m"] = trace["model_x_m"] - trace["gym_x_m"]
    trace["error_y_m"] = trace["model_y_m"] - trace["gym_y_m"]
    trace["error_position_m"] = np.sqrt(trace["error_x_m"] ** 2 + trace["error_y_m"] ** 2)
    trace["error_yaw_rad"] = wrap_angle(trace["model_theta_rad"] - trace["gym_theta_rad"])
    trace["error_speed_mps"] = trace["model_speed_mps"] - trace["gym_speed_mps"]

    for key, value in summary.items():
        trace.attrs[key] = value
    return trace


def metric_rows(trace: pd.DataFrame) -> list[dict[str, str | float]]:
    dt_values = trace["dt_to_next_s"].dropna()
    rows: list[dict[str, str | float]] = [
        {
            "metric": "rmse_position_m",
            "value": float(np.sqrt(np.mean(trace["error_position_m"] ** 2))),
            "units": "m",
            "description": "RMSE position error between kinematic replay and Gym trajectory.",
        },
        {
            "metric": "max_position_error_m",
            "value": float(trace["error_position_m"].max()),
            "units": "m",
            "description": "Maximum position error over replay.",
        },
        {
            "metric": "final_position_error_m",
            "value": float(trace["error_position_m"].iloc[-1]),
            "units": "m",
            "description": "Position drift at final replay sample.",
        },
        {
            "metric": "rmse_yaw_rad",
            "value": float(np.sqrt(np.mean(trace["error_yaw_rad"] ** 2))),
            "units": "rad",
            "description": "RMSE wrapped yaw error.",
        },
        {
            "metric": "max_abs_yaw_error_rad",
            "value": float(trace["error_yaw_rad"].abs().max()),
            "units": "rad",
            "description": "Maximum absolute wrapped yaw error.",
        },
        {
            "metric": "rmse_speed_mps",
            "value": float(np.sqrt(np.mean(trace["error_speed_mps"] ** 2))),
            "units": "m/s",
            "description": "RMSE speed error after integrating logged acceleration.",
        },
        {
            "metric": "final_speed_error_mps",
            "value": float(trace["error_speed_mps"].iloc[-1]),
            "units": "m/s",
            "description": "Speed error at final replay sample.",
        },
        {
            "metric": "duration_replayed_s",
            "value": float(trace["time_s"].iloc[-1] - trace["time_s"].iloc[0]),
            "units": "s",
            "description": "Elapsed replay duration covered by RK4 telemetry.",
        },
        {
            "metric": "num_samples",
            "value": int(len(trace)),
            "units": "count",
            "description": "Number of RK4 telemetry samples replayed.",
        },
        {
            "metric": "dt_min_s",
            "value": float(dt_values.min()),
            "units": "s",
            "description": "Minimum telemetry timestep.",
        },
        {
            "metric": "dt_max_s",
            "value": float(dt_values.max()),
            "units": "s",
            "description": "Maximum telemetry timestep.",
        },
        {
            "metric": "dt_mean_s",
            "value": float(dt_values.mean()),
            "units": "s",
            "description": "Mean telemetry timestep.",
        },
        {
            "metric": "dt_ratio",
            "value": float(dt_values.max() / dt_values.min()),
            "units": "unitless",
            "description": "Maximum timestep divided by minimum timestep.",
        },
    ]
    return rows


def metrics_as_dict(metrics: pd.DataFrame) -> dict[str, float]:
    return {str(row.metric): float(row.value) for row in metrics.itertuples(index=False)}


def save_trajectory_figure(trace: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    ax.plot(trace["gym_x_m"], trace["gym_y_m"], linewidth=2.2, label="Gym RK4 trajectory", color="#1f77b4")
    ax.plot(
        trace["model_x_m"],
        trace["model_y_m"],
        linewidth=2.0,
        linestyle="--",
        label="Kinematic replay",
        color="#d62728",
    )
    ax.scatter(trace["gym_x_m"].iloc[0], trace["gym_y_m"].iloc[0], marker="o", s=75, color="#2ca02c", label="Start")
    ax.scatter(trace["gym_x_m"].iloc[-1], trace["gym_y_m"].iloc[-1], marker="s", s=70, color="#1f77b4", label="Gym end")
    ax.scatter(
        trace["model_x_m"].iloc[-1],
        trace["model_y_m"].iloc[-1],
        marker="x",
        s=90,
        linewidths=2.2,
        color="#d62728",
        label="Replay end",
    )
    ax.set_title("Kinematic Replay vs F1TENTH Gym")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.axis("equal")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", framealpha=0.95)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_state_error_figure(trace: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    time_s = trace["time_s"]

    axes[0].plot(time_s, trace["error_position_m"], color="#1f77b4", linewidth=1.8)
    axes[0].set_ylabel("Position error [m]")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(time_s, trace["error_yaw_rad"], color="#9467bd", linewidth=1.8)
    axes[1].set_ylabel("Yaw error [rad]")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(time_s, trace["error_speed_mps"], color="#2ca02c", linewidth=1.8)
    axes[2].set_ylabel("Speed error [m/s]")
    axes[2].set_xlabel("Time [s]")
    axes[2].grid(True, alpha=0.3)

    fig.suptitle("Kinematic Replay State Errors")
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def metric_table(metrics: pd.DataFrame, selected: list[str]) -> str:
    metric_map = {str(row.metric): row for row in metrics.itertuples(index=False)}
    lines = ["| Metric | Value | Units |", "| --- | ---: | --- |"]
    labels = {
        "rmse_position_m": "RMSE position",
        "max_position_error_m": "Max position error",
        "final_position_error_m": "Final position error",
        "rmse_yaw_rad": "RMSE yaw",
        "max_abs_yaw_error_rad": "Max abs yaw error",
        "rmse_speed_mps": "RMSE speed",
        "final_speed_error_mps": "Final speed error",
        "duration_replayed_s": "Duration replayed",
        "num_samples": "Number of samples",
        "dt_min_s": "dt min",
        "dt_max_s": "dt max",
        "dt_mean_s": "dt mean",
        "dt_ratio": "dt ratio",
    }
    for key in selected:
        row = metric_map[key]
        value = f"{float(row.value):.6g}"
        lines.append(f"| {labels[key]} | {value} | {row.units} |")
    return "\n".join(lines)


def write_report(metrics: pd.DataFrame, trace: pd.DataFrame, output_path: Path) -> None:
    summary_keys = [
        "rmse_position_m",
        "max_position_error_m",
        "final_position_error_m",
        "rmse_yaw_rad",
        "max_abs_yaw_error_rad",
        "rmse_speed_mps",
        "final_speed_error_mps",
        "duration_replayed_s",
        "num_samples",
    ]
    dt_keys = ["dt_min_s", "dt_max_s", "dt_mean_s", "dt_ratio"]

    text = f"""# Kinematic Model vs F1TENTH Gym Replay

## Objective

Replay the existing RK4 F1TENTH Gym telemetry through the documented kinematic bicycle model and quantify how far the model drifts from the Gym trajectory.

## Method

The replay uses the kinematic equations from `docs/vehicle_model.md`:

```text
dX/dt = v cos(psi + beta)
dY/dt = v sin(psi + beta)
dpsi/dt = (v / lr) sin(beta)
dv/dt = a
beta = atan((lr / (lf + lr)) tan(delta))
```

The model is integrated with RK4 over the logged telemetry intervals. Steering input is the achieved simulator steering state `steer_rad`, and acceleration input is `accel_x_mps2`.

## Inputs

- Telemetry: `runs/first_lap/telemetry.csv`
- Integrator filtered: `rk4`
- State initialized from the first RK4 row: `x_m`, `y_m`, `theta_rad`, `speed_mps`
- Geometry: `lf = {LF_M:.5f} m`, `lr = {LR_M:.5f} m`
- Timestep: `time_s[k+1] - time_s[k]`

## Assumptions

- Gym logs `poses_x`, `poses_y`, and `poses_theta` from the simulator vehicle state. The collision geometry treats that pose as the vehicle body center, so this replay uses the same vehicle-body/CG pose reference.
- Achieved steering `steer_rad` is used instead of `command_steer_rad` to avoid mixing actuator-rate effects into the kinematic model error.
- Acceleration is the logged finite-difference estimate from `speed_mps`.
- Inputs are held constant over each telemetry interval.

## Metrics

{metric_table(metrics, summary_keys)}

## Timestep Diagnostics

{metric_table(metrics, dt_keys)}

## Results

The replay trace is written to `runs/model_vs_gym_comparison/replay_trace.csv`. The metrics are written as a tidy key/value table to `runs/model_vs_gym_comparison/metrics.csv`.

Large drift that grows with speed, steering magnitude, or lateral acceleration is expected evidence of missing tire dynamics in the kinematic model. Drift at low speed and low steering should be treated as a possible sign-convention, geometry, or replay-mapping issue, except during the launch-from-rest regime noted below.

## Figures

![Kinematic replay trajectory error](figures/model_vs_gym_trajectory_error.png)

![Kinematic replay state errors](figures/model_vs_gym_state_errors.png)

## Limitations

This comparison tests kinematic model replay against recorded Gym telemetry. It is not parameter identification, not controller design, and not proof that the dynamic bicycle model matches Gym.

The initial launch-from-rest regime (`v ~= 0`) is a low-information zone for the kinematic model; small early offsets there are expected and are not treated as evidence of a convention error.

The kinematic model does not represent tire slip, load transfer, combined slip, steering actuator dynamics, or the full dynamic bicycle model.

## Next Step

Inspect the replay errors before sysID. If the mapping and signs are coherent, the next implementation step is a focused dynamic-model/sysID experiment using explicit excitation and fitted parameters.
"""
    output_path.write_text(text, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    rk4 = load_rk4_telemetry(TELEMETRY_PATH)
    trace = replay_kinematic_model(rk4)
    metrics = pd.DataFrame(metric_rows(trace), columns=["metric", "value", "units", "description"])

    trace.to_csv(TRACE_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    save_trajectory_figure(trace, TRAJECTORY_FIGURE_PATH)
    save_state_error_figure(trace, STATE_ERRORS_FIGURE_PATH)
    write_report(metrics, trace, REPORT_PATH)

    metric_values = metrics_as_dict(metrics)
    print(f"Wrote replay trace to {TRACE_PATH}")
    print(f"Wrote metrics to {METRICS_PATH}")
    print(f"Wrote trajectory figure to {TRAJECTORY_FIGURE_PATH}")
    print(f"Wrote state error figure to {STATE_ERRORS_FIGURE_PATH}")
    print(f"Wrote report to {REPORT_PATH}")
    print(
        "Summary: "
        f"RMSE position={metric_values['rmse_position_m']:.3f} m, "
        f"max position={metric_values['max_position_error_m']:.3f} m, "
        f"RMSE yaw={metric_values['rmse_yaw_rad']:.3f} rad, "
        f"RMSE speed={metric_values['rmse_speed_mps']:.3f} m/s"
    )


if __name__ == "__main__":
    main()
