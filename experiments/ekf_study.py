#!/usr/bin/env python
"""Compare dead reckoning and EKF under measurement noise/dropout."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.closed_loop import run_closed_loop
from roboracer.controllers import PurePursuitController
from roboracer.estimation import ExtendedKalmanFilter, STATE_COLUMNS, dead_reckon_step
from roboracer.noise import DropoutWindow, NoiseSpec, apply_dropout_windows, apply_sensor_noise
from roboracer.numerics import rmse, wrap_angle

EXAMPLES_DIR = REPO_ROOT / "examples"
PP_RESULTS_PATH = REPO_ROOT / "runs" / "pure_pursuit_sweep" / "results.csv"
RUN_DIR = REPO_ROOT / "runs" / "ekf_study"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
TRACE_PATH = RUN_DIR / "trace.csv"
SUMMARY_PATH = RUN_DIR / "summary.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
REPORT_PATH = REPO_ROOT / "reports" / "ekf_study.md"
POSITION_FIGURE = FIGURE_DIR / "ekf_position_error_over_time.png"
SUMMARY_FIGURE = FIGURE_DIR / "ekf_rmse_summary.png"
DROPOUT_FIGURE = FIGURE_DIR / "ekf_dropout_zoom.png"

SEED = 42
INTEGRATION_DT_S = 0.002
CONTROL_RATE_HZ = 100.0
MAX_SIM_TIME_S = 45.0
INITIAL_ESTIMATE_ERROR = np.array([0.25, -0.20, 0.08, -0.25, -0.10], dtype=float)
PROCESS_Q_DIAG = np.array([2e-5, 2e-5, 5e-6, 2e-4, 2e-4], dtype=float)
INITIAL_P_DIAG = np.array([0.20, 0.20, 0.05, 0.20, 0.20], dtype=float)
MEASUREMENT_COLUMNS = ("x_m", "y_m", "theta_rad", "speed_mps", "yaw_rate_radps")
MIN_R_STD = {
    "x_m": 0.01,
    "y_m": 0.01,
    "theta_rad": 0.005,
    "speed_mps": 0.02,
    "yaw_rate_radps": 0.02,
}


def load_config() -> Namespace:
    with (EXAMPLES_DIR / "config_example_map.yaml").open() as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    config["map_path"] = str((EXAMPLES_DIR / config["map_path"]).resolve())
    config["wpt_path"] = str((EXAMPLES_DIR / config["wpt_path"]).resolve())
    return Namespace(**config)


def load_waypoints(conf: Namespace) -> np.ndarray:
    return np.loadtxt(conf.wpt_path, delimiter=conf.wpt_delim, skiprows=conf.wpt_rowskip)


def selected_baseline() -> pd.Series:
    results = pd.read_csv(PP_RESULTS_PATH)
    selected = results[results["selected_baseline"] == True]  # noqa: E712
    if len(selected) != 1:
        raise ValueError("Pure-pursuit sweep must contain exactly one selected baseline.")
    return selected.iloc[0]


def nominal_trace() -> pd.DataFrame:
    conf = load_config()
    baseline = selected_baseline()
    controller = PurePursuitController(
        conf,
        lookahead_m=float(baseline["lookahead_m"]),
        vgain=float(baseline["vgain"]),
        name="ekf_baseline_pp",
    )
    trace, _ = run_closed_loop(
        controller,
        conf,
        load_waypoints(conf),
        integration_dt=INTEGRATION_DT_S,
        control_rate_hz=CONTROL_RATE_HZ,
        max_sim_time_s=MAX_SIM_TIME_S,
        run_id="ekf_baseline_trace",
    )
    return trace


def scenario_specs() -> dict[str, tuple[NoiseSpec, list[DropoutWindow]]]:
    return {
        "clean_measurements": (
            NoiseSpec(std_by_column={column: 0.0 for column in MEASUREMENT_COLUMNS}),
            [],
        ),
        "low_noise": (
            NoiseSpec(
                std_by_column={
                    "x_m": 0.03,
                    "y_m": 0.03,
                    "theta_rad": 0.01,
                    "speed_mps": 0.05,
                    "yaw_rate_radps": 0.05,
                }
            ),
            [],
        ),
        "high_noise": (
            NoiseSpec(
                std_by_column={
                    "x_m": 0.12,
                    "y_m": 0.12,
                    "theta_rad": 0.04,
                    "speed_mps": 0.20,
                    "yaw_rate_radps": 0.20,
                }
            ),
            [],
        ),
        "dropout_1s": (
            NoiseSpec(
                std_by_column={
                    "x_m": 0.04,
                    "y_m": 0.04,
                    "theta_rad": 0.015,
                    "speed_mps": 0.08,
                    "yaw_rate_radps": 0.08,
                }
            ),
            [DropoutWindow(12.0, 1.0, MEASUREMENT_COLUMNS)],
        ),
        "dropout_3s": (
            NoiseSpec(
                std_by_column={
                    "x_m": 0.04,
                    "y_m": 0.04,
                    "theta_rad": 0.015,
                    "speed_mps": 0.08,
                    "yaw_rate_radps": 0.08,
                }
            ),
            [DropoutWindow(12.0, 3.0, MEASUREMENT_COLUMNS)],
        ),
    }


def measurement_covariance(spec: NoiseSpec) -> np.ndarray:
    diag = []
    for column in STATE_COLUMNS:
        std = max(float(spec.std_by_column.get(column, 0.0)), MIN_R_STD[column])
        diag.append(std**2)
    return np.diag(diag)


def corrupt_measurements(trace: pd.DataFrame, spec: NoiseSpec, windows: list[DropoutWindow], seed: int) -> pd.DataFrame:
    measured = apply_sensor_noise(trace, spec, seed=seed)
    measured = apply_dropout_windows(measured, windows)
    return measured


def run_estimators(trace: pd.DataFrame, scenario: str, spec: NoiseSpec, windows: list[DropoutWindow]) -> pd.DataFrame:
    measured = corrupt_measurements(trace, spec, windows, SEED)
    truth0 = measured.loc[0, list(STATE_COLUMNS)].to_numpy(dtype=float)
    dr_state = truth0 + INITIAL_ESTIMATE_ERROR
    ekf = ExtendedKalmanFilter(
        state=dr_state.copy(),
        covariance=np.diag(INITIAL_P_DIAG),
        process_covariance=np.diag(PROCESS_Q_DIAG),
        measurement_covariance=measurement_covariance(spec),
    )
    rows = []
    previous_time = float(measured["time_s"].iloc[0])
    for idx, row in measured.iterrows():
        current_time = float(row["time_s"])
        dt = max(current_time - previous_time, INTEGRATION_DT_S)
        control = np.array([float(row["command_steer_rad"]), float(row["accel_x_mps2"])], dtype=float)
        if idx > 0:
            dr_state = dead_reckon_step(dr_state, control, dt)
            ekf.predict(control, dt)
            ekf.update({column: float(row[f"meas_{column}"]) for column in STATE_COLUMNS})
        truth = row[list(STATE_COLUMNS)].to_numpy(dtype=float)
        for estimator, estimate in (("dead_reckoning", dr_state), ("ekf", ekf.state)):
            error = estimate - truth
            error[2] = float(wrap_angle(error[2]))
            rows.append(
                {
                    "scenario": scenario,
                    "estimator": estimator,
                    "time_s": current_time,
                    "x_error_m": error[0],
                    "y_error_m": error[1],
                    "position_error_m": float(np.hypot(error[0], error[1])),
                    "theta_error_rad": error[2],
                    "speed_error_mps": error[3],
                    "yaw_rate_error_radps": error[4],
                    "measurement_available": int(
                        all(np.isfinite(float(row[f"meas_{column}"])) for column in STATE_COLUMNS)
                    ),
                }
            )
        previous_time = current_time
    return pd.DataFrame(rows)


def summarize(trace: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scenario, estimator), group in trace.groupby(["scenario", "estimator"]):
        rows.append(
            {
                "scenario": scenario,
                "estimator": estimator,
                "position_rmse_m": rmse(group["position_error_m"].to_numpy(dtype=float)),
                "max_position_error_m": float(group["position_error_m"].max()),
                "theta_rmse_rad": rmse(group["theta_error_rad"].to_numpy(dtype=float)),
                "speed_rmse_mps": rmse(group["speed_error_mps"].to_numpy(dtype=float)),
                "yaw_rate_rmse_radps": rmse(group["yaw_rate_error_radps"].to_numpy(dtype=float)),
                "measurement_availability_fraction": float(group["measurement_available"].mean()),
            }
        )
    summary = pd.DataFrame(rows)
    pivot = summary.pivot(index="scenario", columns="estimator", values="position_rmse_m")
    improvement = (pivot["dead_reckoning"] - pivot["ekf"]) / pivot["dead_reckoning"]
    summary = summary.merge(
        improvement.rename("ekf_position_rmse_improvement_fraction"),
        left_on="scenario",
        right_index=True,
        how="left",
    )
    return summary


def plot_position_errors(trace: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for (scenario, estimator), group in trace.groupby(["scenario", "estimator"]):
        if scenario in {"low_noise", "dropout_1s"}:
            ax.plot(group["time_s"], group["position_error_m"], label=f"{scenario} {estimator}", linewidth=1.1)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Position error [m]")
    ax.set_title("EKF vs Dead Reckoning Position Error")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(POSITION_FIGURE, dpi=200)
    plt.close(fig)


def plot_summary(summary: pd.DataFrame) -> None:
    pivot = summary.pivot(index="scenario", columns="estimator", values="position_rmse_m")
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    x = np.arange(len(pivot.index))
    width = 0.35
    ax.bar(x - width / 2, pivot["dead_reckoning"], width, label="Dead reckoning")
    ax.bar(x + width / 2, pivot["ekf"], width, label="EKF")
    ax.set_xticks(x, pivot.index, rotation=20, ha="right")
    ax.set_ylabel("Position RMSE [m]")
    ax.set_title("Estimator RMSE Summary")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(SUMMARY_FIGURE, dpi=200)
    plt.close(fig)


def plot_dropout_zoom(trace: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    group = trace[(trace["scenario"] == "dropout_3s") & (trace["time_s"].between(10.5, 16.0))]
    for estimator, estimator_group in group.groupby("estimator"):
        ax.plot(estimator_group["time_s"], estimator_group["position_error_m"], label=estimator, linewidth=1.4)
    ax.axvspan(12.0, 15.0, color="#d62728", alpha=0.12, label="dropout")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Position error [m]")
    ax.set_title("3 s Dropout Window")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(DROPOUT_FIGURE, dpi=200)
    plt.close(fig)


def markdown_table(frame: pd.DataFrame) -> str:
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: f"{value:.6g}")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---" for _ in display.columns]) + " |"]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
    return "\n".join(lines)


def write_report(summary: pd.DataFrame) -> None:
    compact = summary[
        [
            "scenario",
            "estimator",
            "position_rmse_m",
            "max_position_error_m",
            "theta_rmse_rad",
            "ekf_position_rmse_improvement_fraction",
        ]
    ]
    report = f"""# EKF Study

## Objective

Compare dead reckoning and EKF estimates against Gym ground truth under reproducible measurement noise and dropout.

## Setup

- Integration timestep: `{INTEGRATION_DT_S:.3f} s`
- Controller update rate: `{CONTROL_RATE_HZ:.0f} Hz`
- Seed: `{SEED}`
- EKF state: `{list(STATE_COLUMNS)}`
- EKF process covariance diagonal: `{PROCESS_Q_DIAG.tolist()}`

## Results

{markdown_table(compact)}

## Figures

![Position error over time](figures/ekf_position_error_over_time.png)

![RMSE summary](figures/ekf_rmse_summary.png)

![Dropout zoom](figures/ekf_dropout_zoom.png)

## Interpretation

The EKF uses only degraded `meas_*` columns for correction and is scored against the original Gym state columns. The covariance values are fixed from the scenario noise settings and the documented process-noise table, not tuned per result.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    trace = nominal_trace()
    scenario_trace = []
    metadata_scenarios = {}
    for scenario, (spec, windows) in scenario_specs().items():
        scenario_trace.append(run_estimators(trace, scenario, spec, windows))
        metadata_scenarios[scenario] = {
            "noise_std_by_column": spec.std_by_column,
            "dropout_windows": [
                {"start_s": window.start_s, "duration_s": window.duration_s, "columns": list(window.columns or [])}
                for window in windows
            ],
            "measurement_R_diag": np.diag(measurement_covariance(spec)).tolist(),
        }
    results = pd.concat(scenario_trace, ignore_index=True)
    summary = summarize(results)
    results.to_csv(TRACE_PATH, index=False)
    summary.to_csv(SUMMARY_PATH, index=False)
    METADATA_PATH.write_text(
        json.dumps(
            {
                "seed": SEED,
                "integration_dt_s": INTEGRATION_DT_S,
                "control_rate_hz": CONTROL_RATE_HZ,
                "initial_estimate_error": INITIAL_ESTIMATE_ERROR.tolist(),
                "process_Q_diag": PROCESS_Q_DIAG.tolist(),
                "scenarios": metadata_scenarios,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    plot_position_errors(results)
    plot_summary(summary)
    plot_dropout_zoom(results)
    write_report(summary)
    print(f"Wrote {TRACE_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
