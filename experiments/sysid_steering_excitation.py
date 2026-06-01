#!/usr/bin/env python
"""Generate chirp-steering excitation data for future tire-parameter sysID."""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import subprocess
from argparse import Namespace
from pathlib import Path

import gym
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from PIL import Image

from f110_gym.envs.base_classes import Integrator

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
RUN_DIR = REPO_ROOT / "runs" / "sysid_steering_excitation"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
TELEMETRY_PATH = RUN_DIR / "telemetry.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
QUALITY_PATH = RUN_DIR / "quality_metrics.csv"
REPORT_PATH = REPO_ROOT / "reports" / "sysid_steering_excitation.md"
STEERING_FIGURE_PATH = FIGURE_DIR / "sysid_steering_input.png"
YAW_FIGURE_PATH = FIGURE_DIR / "sysid_yaw_response.png"
SPEED_FIGURE_PATH = FIGURE_DIR / "sysid_speed_hold.png"

TARGET_SPEED_MPS = 2.0
FREQ_START_HZ = 0.2
FREQ_END_HZ = 2.0
AMPLITUDE_CANDIDATES_RAD = [0.04, 0.06, 0.08]
DURATION_CANDIDATES_S = [20.0, 30.0]
TIMESTEP_S = 0.01
S_MAX_RAD = 0.4189
SATURATION_FRACTION_LIMIT = 0.02
SATURATION_SEGMENT_LIMIT_S = 0.25
SATURATION_THRESHOLD = 0.95 * S_MAX_RAD

FIELDNAMES = [
    "run_id",
    "step",
    "time_s",
    "profile_status",
    "command_speed_mps",
    "command_steer_rad",
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
    "collision",
]


def create_open_map() -> Path:
    map_stem = RUN_DIR / "open_sysid_map"
    image_path = map_stem.with_suffix(".png")
    yaml_path = map_stem.with_suffix(".yaml")
    size_px = 2000
    border_px = 8
    resolution_m = 0.08
    image = np.full((size_px, size_px), 255, dtype=np.uint8)
    image[:border_px, :] = 0
    image[-border_px:, :] = 0
    image[:, :border_px] = 0
    image[:, -border_px:] = 0
    Image.fromarray(image).save(image_path)
    yaml_path.write_text(
        "\n".join(
            [
                "image: open_sysid_map.png",
                f"resolution: {resolution_m:.6f}",
                f"origin: [{-(size_px * resolution_m) / 2:.6f}, {-(size_px * resolution_m) / 2:.6f}, 0.000000]",
                "negate: 0",
                "occupied_thresh: 0.45",
                "free_thresh: 0.196",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return map_stem


def load_config() -> Namespace:
    with (EXAMPLES_DIR / "config_example_map.yaml").open() as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    config["map_path"] = str(create_open_map().resolve())
    return Namespace(**config)


def scalar(obs: dict, key: str, index: int = 0) -> float:
    return float(obs[key][index])


def chirp_steer(time_s: float, amplitude_rad: float, duration_s: float) -> float:
    ramp = (FREQ_END_HZ - FREQ_START_HZ) / duration_s
    phase = 2.0 * math.pi * (FREQ_START_HZ * time_s + 0.5 * ramp * time_s**2)
    return float(amplitude_rad * math.sin(phase))


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def create_env(conf: Namespace):
    return gym.make(
        "f110_gym:f110-v0",
        map=conf.map_path,
        map_ext=conf.map_ext,
        num_agents=1,
        timestep=TIMESTEP_S,
        integrator=Integrator.RK4,
    )


def run_profile(
    conf: Namespace,
    amplitude_rad: float,
    duration_s: float,
) -> list[dict[str, str | float | int]]:
    env = create_env(conf)
    obs, _, _, _ = env.reset(np.array([[conf.sx, conf.sy, conf.stheta]]))
    rows: list[dict[str, str | float | int]] = []
    state = env.sim.agents[0].state
    previous_steer = float(state[2])
    previous_speed = float(state[3])
    run_id = f"chirp_a{amplitude_rad:.3f}_d{duration_s:.0f}"
    max_steps = int(round(duration_s / TIMESTEP_S))

    try:
        for step in range(max_steps):
            command_time = step * TIMESTEP_S
            command_steer = chirp_steer(command_time, amplitude_rad, duration_s)
            command_steer = float(np.clip(command_steer, -0.75 * S_MAX_RAD, 0.75 * S_MAX_RAD))
            command_speed = TARGET_SPEED_MPS
            obs, step_reward, done, _ = env.step(np.array([[command_steer, command_speed]]))

            state = env.sim.agents[0].state
            x = float(state[0])
            y = float(state[1])
            steer = float(state[2])
            speed = float(state[3])
            theta = float(state[4])
            yaw_rate = float(state[5])
            slip_angle = float(state[6])
            dt = float(step_reward)
            steer_vel = (steer - previous_steer) / dt
            accel_x = (speed - previous_speed) / dt
            previous_steer = steer
            previous_speed = speed
            collision = bool(scalar(obs, "collisions"))
            vx = speed * math.cos(slip_angle)
            vy = speed * math.sin(slip_angle)

            rows.append(
                {
                    "run_id": run_id,
                    "step": step + 1,
                    "time_s": f"{(step + 1) * dt:.6f}",
                    "profile_status": "candidate",
                    "command_speed_mps": f"{command_speed:.9f}",
                    "command_steer_rad": f"{command_steer:.9f}",
                    "x_m": f"{x:.9f}",
                    "y_m": f"{y:.9f}",
                    "theta_rad": f"{theta:.9f}",
                    "speed_mps": f"{speed:.9f}",
                    "vx_mps": f"{vx:.9f}",
                    "vy_mps": f"{vy:.9f}",
                    "steer_rad": f"{steer:.9f}",
                    "steer_vel_radps": f"{steer_vel:.9f}",
                    "yaw_rate_radps": f"{yaw_rate:.9f}",
                    "slip_angle_rad": f"{slip_angle:.9f}",
                    "accel_x_mps2": f"{accel_x:.9f}",
                    "collision": int(collision),
                }
            )

            if done or collision:
                break
    finally:
        close = getattr(env, "close", None)
        if callable(close):
            close()

    return rows


def longest_true_segment_s(mask: np.ndarray, dt_s: float) -> float:
    longest = 0
    current = 0
    for item in mask:
        if bool(item):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return float(longest * dt_s)


def quality_metrics(rows: list[dict[str, str | float | int]]) -> tuple[list[dict[str, str | float]], bool]:
    df = pd.DataFrame(rows)
    numeric = [
        "time_s",
        "command_speed_mps",
        "command_steer_rad",
        "speed_mps",
        "vx_mps",
        "vy_mps",
        "steer_rad",
        "steer_vel_radps",
        "yaw_rate_radps",
        "slip_angle_rad",
        "accel_x_mps2",
        "collision",
    ]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    dt = np.diff(df["time_s"].to_numpy(dtype=float))
    dt_median = float(np.median(dt)) if dt.size else TIMESTEP_S
    saturation_mask = df["steer_rad"].abs().to_numpy() >= SATURATION_THRESHOLD
    saturation_fraction = float(np.mean(saturation_mask)) if len(saturation_mask) else 1.0
    max_saturation_segment_s = longest_true_segment_s(saturation_mask, dt_median)
    duration_s = float(df["time_s"].iloc[-1] - df["time_s"].iloc[0]) if len(df) >= 2 else 0.0
    speed_mean = float(df["speed_mps"].mean()) if not df.empty else 0.0
    speed_std = float(df["speed_mps"].std()) if len(df) > 1 else 0.0
    speed_cv = float(speed_std / max(abs(speed_mean), 1e-6))
    steer_range = float(df["steer_rad"].max() - df["steer_rad"].min()) if not df.empty else 0.0
    yaw_rate_range = float(df["yaw_rate_radps"].max() - df["yaw_rate_radps"].min()) if not df.empty else 0.0
    collision = bool(df["collision"].max()) if not df.empty else True

    metrics = [
        {"metric": "duration_s", "value": duration_s, "units": "s", "pass": duration_s >= 15.0},
        {"metric": "num_samples", "value": int(len(df)), "units": "count", "pass": len(df) > 0},
        {"metric": "collision", "value": int(collision), "units": "bool", "pass": not collision},
        {"metric": "speed_mean_mps", "value": speed_mean, "units": "m/s", "pass": True},
        {"metric": "speed_std_mps", "value": speed_std, "units": "m/s", "pass": True},
        {"metric": "speed_cv", "value": speed_cv, "units": "unitless", "pass": speed_cv <= 0.15},
        {"metric": "steer_range_rad", "value": steer_range, "units": "rad", "pass": steer_range >= 0.05},
        {"metric": "yaw_rate_range_radps", "value": yaw_rate_range, "units": "rad/s", "pass": yaw_rate_range >= 0.1},
        {"metric": "steering_saturation_fraction", "value": saturation_fraction, "units": "fraction", "pass": saturation_fraction <= SATURATION_FRACTION_LIMIT},
        {"metric": "max_saturation_segment_s", "value": max_saturation_segment_s, "units": "s", "pass": max_saturation_segment_s <= SATURATION_SEGMENT_LIMIT_S},
    ]
    passed = all(bool(row["pass"]) for row in metrics)
    return metrics, passed


def select_profile(conf: Namespace) -> tuple[list[dict[str, str | float | int]], list[dict[str, str | float]], dict[str, str | float | bool]]:
    attempts = []
    last_rows: list[dict[str, str | float | int]] = []
    last_metrics: list[dict[str, str | float]] = []
    for amplitude in AMPLITUDE_CANDIDATES_RAD:
        for duration in DURATION_CANDIDATES_S:
            rows = run_profile(conf, amplitude, duration)
            metrics, passed = quality_metrics(rows)
            attempts.append(
                {
                    "amplitude_rad": amplitude,
                    "duration_s": duration,
                    "passed_quality_gates": passed,
                }
            )
            last_rows = rows
            last_metrics = metrics
            if passed:
                for row in rows:
                    row["profile_status"] = "selected_pass"
                return rows, metrics, {
                    "amplitude_rad": amplitude,
                    "duration_s": duration,
                    "passed_quality_gates": True,
                    "attempts": attempts,
                }

    for row in last_rows:
        row["profile_status"] = "selected_fail"
    return last_rows, last_metrics, {
        "amplitude_rad": attempts[-1]["amplitude_rad"] if attempts else 0.0,
        "duration_s": attempts[-1]["duration_s"] if attempts else 0.0,
        "passed_quality_gates": False,
        "attempts": attempts,
    }


def write_csv(rows: list[dict[str, str | float | int]]) -> None:
    with TELEMETRY_PATH.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_quality(metrics: list[dict[str, str | float]]) -> None:
    pd.DataFrame(metrics, columns=["metric", "value", "units", "pass"]).to_csv(QUALITY_PATH, index=False)


def write_metadata(selection: dict[str, str | float | bool]) -> None:
    payload = {
        "python_version": platform.python_version(),
        "f1tenth_gym_commit": git_commit(),
        "telemetry_source": "generated",
        "experiment": "sysid_steering_excitation",
        "integrator": "rk4",
        "control": "speed_hold_plus_steering_chirp",
        "map": "generated open occupancy map in runs/sysid_steering_excitation",
        "steering_command": "zero-centered steering chirp; no pure-pursuit feedback",
        "target_speed_mps": TARGET_SPEED_MPS,
        "frequency_start_hz": FREQ_START_HZ,
        "frequency_end_hz": FREQ_END_HZ,
        "selected_profile": selection,
        "state_source": "env.sim.agents[0].state",
        "command_convention": "[command_steer_rad, command_speed_mps] passed to env.step",
        "future_sysid_input_convention": "[steer_vel_radps, accel_x_mps2] reconstructed from achieved state",
        "saturation_threshold_rad": SATURATION_THRESHOLD,
        "no_parameter_fitting": True,
    }
    METADATA_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def save_figures(rows: list[dict[str, str | float | int]]) -> None:
    df = pd.DataFrame(rows)
    for column in FIELDNAMES:
        if column not in {"run_id", "profile_status"}:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.plot(df["time_s"], df["command_steer_rad"], label="Commanded steering", linestyle="--", color="#9467bd")
    ax.plot(df["time_s"], df["steer_rad"], label="Achieved steering", color="#1f77b4")
    ax.axhline(SATURATION_THRESHOLD, color="#d62728", linestyle=":", linewidth=1.2, label="95% steering limit")
    ax.axhline(-SATURATION_THRESHOLD, color="#d62728", linestyle=":", linewidth=1.2)
    ax.set_title("SysID Steering Chirp Input")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Steering [rad]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.savefig(STEERING_FIGURE_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.plot(df["time_s"], df["yaw_rate_radps"], label="Yaw rate", color="#d62728")
    ax2 = ax.twinx()
    ax2.plot(df["time_s"], df["slip_angle_rad"], label="Slip angle", color="#2ca02c", alpha=0.75)
    ax.set_title("SysID Yaw Response")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Yaw rate [rad/s]")
    ax2.set_ylabel("Slip angle [rad]")
    ax.grid(True, alpha=0.3)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="best")
    fig.savefig(YAW_FIGURE_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.plot(df["time_s"], df["speed_mps"], label="Achieved speed", color="#1f77b4")
    ax.plot(df["time_s"], df["command_speed_mps"], label="Commanded speed", linestyle="--", color="#555555")
    ax.fill_between(df["time_s"], TARGET_SPEED_MPS * 0.85, TARGET_SPEED_MPS * 1.15, color="#2ca02c", alpha=0.12, label="+/-15% band")
    ax.set_title("SysID Speed Hold")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Speed [m/s]")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.savefig(SPEED_FIGURE_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def metric_value(metrics: list[dict[str, str | float]], name: str) -> float:
    for row in metrics:
        if row["metric"] == name:
            return float(row["value"])
    raise KeyError(name)


def quality_table(metrics: list[dict[str, str | float]]) -> str:
    lines = ["| Metric | Value | Units | Pass |", "| --- | ---: | --- | --- |"]
    for row in metrics:
        value = row["value"]
        if isinstance(value, (int, float, np.integer, np.floating)):
            value_text = f"{float(value):.6g}"
        else:
            value_text = str(value)
        lines.append(f"| {row['metric']} | {value_text} | {row['units']} | {bool(row['pass'])} |")
    return "\n".join(lines)


def write_report(metrics: list[dict[str, str | float]], selection: dict[str, str | float | bool]) -> None:
    status = "passed" if bool(selection["passed_quality_gates"]) else "failed"
    text = f"""# SysID Steering Excitation

## Objective

Collect a clean lateral-yaw excitation dataset for later tire-stiffness identification. This branch performs no parameter fitting.

## Method

The experiment uses F1TENTH Gym RK4 on a generated open occupancy map with a speed-hold command and zero-centered chirp steering. This is not pure pursuit feedback. The selected profile has chirp amplitude `{float(selection['amplitude_rad']):.3f} rad`, target speed `{TARGET_SPEED_MPS:.3f} m/s`, and duration `{float(selection['duration_s']):.3f} s`.

Environment commands are not the same as internal dynamic-model input. `command_steer_rad` and `command_speed_mps` are setpoints passed to `env.step`; future sysID should use achieved/reconstructed signals: `steer_rad`, `steer_vel_radps`, `speed_mps`, and `accel_x_mps2`.

## Logged State

Telemetry logs internal dynamic state from `env.sim.agents[0].state`, including achieved steering, speed, yaw rate, and slip angle. The lateral/longitudinal body velocity components are derived as `vx_mps = speed_mps * cos(slip_angle_rad)` and `vy_mps = speed_mps * sin(slip_angle_rad)`.

## Quality Gates

Quality status: `{status}`.

{quality_table(metrics)}

## Results

- Duration: `{metric_value(metrics, 'duration_s'):.3f} s`
- Steering range: `{metric_value(metrics, 'steer_range_rad'):.4f} rad`
- Yaw-rate range: `{metric_value(metrics, 'yaw_rate_range_radps'):.4f} rad/s`
- Speed coefficient of variation: `{metric_value(metrics, 'speed_cv'):.4f}`

## Figures

![SysID steering input](figures/sysid_steering_input.png)

![SysID yaw response](figures/sysid_yaw_response.png)

![SysID speed hold](figures/sysid_speed_hold.png)

## Limitations

This branch collects excitation data only; no `C_Sf` or `C_Sr` fitting is performed. Fitting starts only after excitation quality passes and the telemetry mapping is accepted.

## Next Step

If the quality gates pass, create a separate fitting branch to estimate `C_Sf` and `C_Sr` and compare fitted values against Gym defaults.
"""
    REPORT_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    os.chdir(REPO_ROOT)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    conf = load_config()
    rows, metrics, selection = select_profile(conf)
    write_csv(rows)
    write_quality(metrics)
    write_metadata(selection)
    save_figures(rows)
    write_report(metrics, selection)

    print(f"Wrote telemetry to {TELEMETRY_PATH}")
    print(f"Wrote quality metrics to {QUALITY_PATH}")
    print(f"Wrote metadata to {METADATA_PATH}")
    print(f"Wrote report to {REPORT_PATH}")
    print(f"Quality gates passed: {bool(selection['passed_quality_gates'])}")


if __name__ == "__main__":
    main()
