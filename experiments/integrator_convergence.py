#!/usr/bin/env python
"""Run an RK4 timestep convergence study for the first F1TENTH Gym lap."""

from __future__ import annotations

import csv
import math
import os
from argparse import Namespace
from pathlib import Path

import gym
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from f110_gym.envs.base_classes import Integrator

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"

RUN_DIR = REPO_ROOT / "runs" / "integrator_convergence"
TELEMETRY_DIR = RUN_DIR / "telemetry_by_dt"
RESULTS_PATH = RUN_DIR / "convergence_results.csv"

REPORT_PATH = REPO_ROOT / "reports" / "integrator_convergence.md"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
POSITION_ERROR_FIGURE = FIGURE_DIR / "integrator_convergence_position_error.png"
METRICS_FIGURE = FIGURE_DIR / "integrator_convergence_metrics.png"

INTEGRATOR_NAME = "rk4"
INTEGRATOR = Integrator.RK4

WORK_PARAMS = {
    "mass": 3.463388126201571,
    "lf": 0.15597534362552312,
    "tlad": 0.82461887897713965,
    "vgain": 1.375,
}

DT_VALUES = [0.02, 0.01, 0.005, 0.002, 0.001, 0.0005]
REFERENCE_DT = 0.0005
MAX_SIM_TIME_S = 45.0

RMS_REFINEMENT_TOL_M = 0.05
MAX_REFINEMENT_TOL_M = 0.20
ERROR_GRID_POINTS = 2000

FIELDNAMES = [
    "run_id",
    "integrator",
    "dt_s",
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
    "completed_lap",
    "termination_reason",
]

RESULT_FIELDNAMES = [
    "integrator",
    "dt_s",
    "completed_lap",
    "collision",
    "final_time_s",
    "final_progress_m",
    "rms_cte_m",
    "max_abs_cte_m",
    "rms_position_error_vs_ref_progress_m",
    "max_position_error_vs_ref_progress_m",
    "rms_position_error_vs_ref_time_m",
    "max_position_error_vs_ref_time_m",
    "rms_position_change_vs_next_finer_dt_progress_m",
    "max_position_change_vs_next_finer_dt_progress_m",
    "rms_position_change_vs_next_finer_dt_time_m",
    "max_position_change_vs_next_finer_dt_time_m",
    "termination_reason",
]


def dt_to_tag(dt_s: float) -> str:
    return f"{dt_s:.4f}".replace(".", "p")


def load_config() -> Namespace:
    with (EXAMPLES_DIR / "config_example_map.yaml").open() as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    config["map_path"] = str((EXAMPLES_DIR / config["map_path"]).resolve())
    config["wpt_path"] = str((EXAMPLES_DIR / config["wpt_path"]).resolve())
    return Namespace(**config)


def load_waypoints(conf: Namespace) -> np.ndarray:
    return np.loadtxt(conf.wpt_path, delimiter=conf.wpt_delim, skiprows=conf.wpt_rowskip)


def nearest_point_on_trajectory(point: np.ndarray, trajectory: np.ndarray) -> tuple[np.ndarray, float, float, int]:
    diffs = trajectory[1:, :] - trajectory[:-1, :]
    l2s = diffs[:, 0] ** 2 + diffs[:, 1] ** 2
    dots = np.sum((point - trajectory[:-1, :]) * diffs[:, :], axis=1)
    t = np.clip(dots / l2s, 0.0, 1.0)
    projections = trajectory[:-1, :] + (t * diffs.T).T
    dists = np.linalg.norm(point - projections, axis=1)
    segment = int(np.argmin(dists))
    return projections[segment], float(dists[segment]), float(t[segment]), segment


def first_point_on_trajectory_intersecting_circle(
    point: np.ndarray,
    radius: float,
    trajectory: np.ndarray,
    t: float = 0.0,
    wrap: bool = False,
) -> tuple[np.ndarray | None, int | None, float | None]:
    start_i = int(t)
    start_t = t % 1.0

    ranges = [range(start_i, trajectory.shape[0] - 1)]
    if wrap:
        ranges.append(range(-1, start_i))

    for idx_range in ranges:
        for i in idx_range:
            start = trajectory[i % trajectory.shape[0], :]
            end = trajectory[(i + 1) % trajectory.shape[0], :] + 1e-6
            segment = end - start
            a = float(np.dot(segment, segment))
            b = float(2.0 * np.dot(segment, start - point))
            c = float(np.dot(start, start) + np.dot(point, point) - 2.0 * np.dot(start, point) - radius * radius)
            discriminant = b * b - 4 * a * c
            if discriminant < 0:
                continue

            root = float(np.sqrt(discriminant))
            for candidate_t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if 0.0 <= candidate_t <= 1.0 and (i != start_i or candidate_t >= start_t):
                    return start + candidate_t * segment, i, float(candidate_t)

    return None, None, None


def get_actuation(
    pose_theta: float,
    lookahead_point: np.ndarray,
    position: np.ndarray,
    lookahead_distance: float,
    wheelbase: float,
) -> tuple[float, float]:
    waypoint_y = float(np.dot(np.array([np.sin(-pose_theta), np.cos(-pose_theta)]), lookahead_point[0:2] - position))
    speed = float(lookahead_point[2])
    if abs(waypoint_y) < 1e-6:
        return speed, 0.0
    radius = 1.0 / (2.0 * waypoint_y / lookahead_distance**2)
    steering_angle = float(np.arctan(wheelbase / radius))
    return speed, steering_angle


class PurePursuitPlanner:
    def __init__(self, conf: Namespace, wheelbase: float):
        self.conf = conf
        self.wheelbase = wheelbase
        self.waypoints = np.loadtxt(conf.wpt_path, delimiter=conf.wpt_delim, skiprows=conf.wpt_rowskip)
        self.max_reacquire = 20.0

    def _get_current_waypoint(
        self,
        waypoints: np.ndarray,
        lookahead_distance: float,
        position: np.ndarray,
    ) -> np.ndarray | None:
        wpts = np.vstack((self.waypoints[:, self.conf.wpt_xind], self.waypoints[:, self.conf.wpt_yind])).T
        _, nearest_dist, t, i = nearest_point_on_trajectory(position, wpts)
        if nearest_dist < lookahead_distance:
            _, i2, _ = first_point_on_trajectory_intersecting_circle(
                position,
                lookahead_distance,
                wpts,
                i + t,
                wrap=True,
            )
            if i2 is None:
                return None
            current_waypoint = np.empty((3,))
            current_waypoint[0:2] = wpts[i2, :]
            current_waypoint[2] = waypoints[i, self.conf.wpt_vind]
            return current_waypoint
        if nearest_dist < self.max_reacquire:
            return np.append(wpts[i, :], waypoints[i, self.conf.wpt_vind])
        return None

    def plan(
        self,
        pose_x: float,
        pose_y: float,
        pose_theta: float,
        lookahead_distance: float,
        vgain: float,
    ) -> tuple[float, float]:
        position = np.array([pose_x, pose_y])
        lookahead_point = self._get_current_waypoint(self.waypoints, lookahead_distance, position)
        if lookahead_point is None:
            return 4.0, 0.0
        speed, steering_angle = get_actuation(
            pose_theta,
            lookahead_point,
            position,
            lookahead_distance,
            self.wheelbase,
        )
        return vgain * speed, steering_angle


def nearest_waypoint_metrics(
    x: float,
    y: float,
    waypoints: np.ndarray,
    conf: Namespace,
) -> tuple[int, float, float, float]:
    point = np.array([x, y], dtype=float)
    xy = waypoints[:, [conf.wpt_xind, conf.wpt_yind]]
    progress = waypoints[:, 0]

    starts = xy[:-1]
    ends = xy[1:]
    segments = ends - starts
    seg_len_sq = np.sum(segments * segments, axis=1)
    valid = seg_len_sq > 0.0
    if not np.any(valid):
        raise ValueError("Waypoint path has no valid segments.")

    t = np.zeros(len(segments))
    t[valid] = np.clip(np.sum((point - starts[valid]) * segments[valid], axis=1) / seg_len_sq[valid], 0.0, 1.0)
    projections = starts + (t * segments.T).T
    deltas = point - projections
    dists = np.linalg.norm(deltas, axis=1)
    dists[~valid] = np.inf

    best_idx = int(np.argmin(dists))
    best_t = float(t[best_idx])
    seg_len = float(np.sqrt(seg_len_sq[best_idx]))
    start = starts[best_idx]
    segment = segments[best_idx]
    cross = float(segment[0] * (point[1] - start[1]) - segment[1] * (point[0] - start[0]))
    signed_dist = cross / seg_len
    progress_m = float(progress[best_idx] + best_t * (progress[best_idx + 1] - progress[best_idx]))
    return best_idx, progress_m, signed_dist, abs(signed_dist)


def scalar(obs: dict, key: str, index: int = 0) -> float:
    return float(obs[key][index])


def run_variant(conf: Namespace, waypoints: np.ndarray, dt_s: float) -> list[dict]:
    run_id = f"rk4_dt_{dt_to_tag(dt_s)}"
    planner = PurePursuitPlanner(conf, 0.17145 + 0.15875)
    env = gym.make(
        "f110_gym:f110-v0",
        map=conf.map_path,
        map_ext=conf.map_ext,
        num_agents=1,
        timestep=dt_s,
        integrator=INTEGRATOR,
    )

    obs, _, _, info = env.reset(np.array([[conf.sx, conf.sy, conf.stheta]]))
    rows = []
    previous_speed = scalar(obs, "linear_vels_x")
    termination_reason = "max_steps"
    max_steps = math.ceil(MAX_SIM_TIME_S / dt_s)

    try:
        for step in range(max_steps):
            x = scalar(obs, "poses_x")
            y = scalar(obs, "poses_y")
            theta = scalar(obs, "poses_theta")
            command_speed, command_steer = planner.plan(
                x,
                y,
                theta,
                WORK_PARAMS["tlad"],
                WORK_PARAMS["vgain"],
            )

            obs, step_reward, done, info = env.step(np.array([[command_steer, command_speed]]))
            step_dt = float(step_reward)
            speed = scalar(obs, "linear_vels_x")
            yaw_rate = scalar(obs, "ang_vels_z")
            accel_x = (speed - previous_speed) / step_dt
            accel_y = speed * yaw_rate
            previous_speed = speed

            x = scalar(obs, "poses_x")
            y = scalar(obs, "poses_y")
            theta = scalar(obs, "poses_theta")
            nearest_idx, progress_m, cte_m, abs_cte_m = nearest_waypoint_metrics(x, y, waypoints, conf)
            collision = bool(scalar(obs, "collisions"))
            completed_lap = bool(np.asarray(info.get("checkpoint_done", [False]))[0])

            if completed_lap:
                termination_reason = "completed_lap"
            elif collision:
                termination_reason = "collision"
            elif step == max_steps - 1:
                termination_reason = "max_steps"
            else:
                termination_reason = ""

            rows.append(
                {
                    "run_id": run_id,
                    "integrator": INTEGRATOR_NAME,
                    "dt_s": f"{dt_s:.6f}",
                    "step": step + 1,
                    "time_s": f"{(step + 1) * step_dt:.6f}",
                    "x_m": f"{x:.9f}",
                    "y_m": f"{y:.9f}",
                    "theta_rad": f"{theta:.9f}",
                    "speed_mps": f"{speed:.9f}",
                    "steer_rad": f"{float(env.sim.agents[0].state[2]):.9f}",
                    "command_speed_mps": f"{float(command_speed):.9f}",
                    "command_steer_rad": f"{float(command_steer):.9f}",
                    "yaw_rate_radps": f"{yaw_rate:.9f}",
                    "accel_x_mps2": f"{accel_x:.9f}",
                    "accel_y_mps2": f"{accel_y:.9f}",
                    "nearest_waypoint_index": nearest_idx,
                    "progress_m": f"{progress_m:.9f}",
                    "cte_m": f"{cte_m:.9f}",
                    "abs_cte_m": f"{abs_cte_m:.9f}",
                    "lap_time_s": f"{float(obs['lap_times'][0]):.6f}",
                    "lap_count": f"{float(obs['lap_counts'][0]):.0f}",
                    "collision": int(collision),
                    "completed_lap": int(completed_lap),
                    "termination_reason": termination_reason,
                }
            )

            if done or termination_reason in {"completed_lap", "collision"}:
                break
    except Exception:
        if rows:
            rows[-1]["termination_reason"] = "error"
        raise
    finally:
        close = getattr(env, "close", None)
        if callable(close):
            close()

    if rows and not rows[-1]["termination_reason"]:
        rows[-1]["termination_reason"] = termination_reason
    if rows:
        final_reason = rows[-1]["termination_reason"]
        final_completed = rows[-1]["completed_lap"]
        final_collision = rows[-1]["collision"]
        for row in rows:
            row["termination_reason"] = final_reason
            row["completed_lap"] = final_completed
            row["collision"] = final_collision
    return rows


def write_telemetry(rows: list[dict], dt_s: float) -> Path:
    path = TELEMETRY_DIR / f"rk4_dt_{dt_to_tag(dt_s)}.csv"
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return path


def rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    numeric_cols = [
        "dt_s",
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
        "completed_lap",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def summarize_run(df: pd.DataFrame, dt_s: float) -> dict:
    return {
        "integrator": INTEGRATOR_NAME,
        "dt_s": dt_s,
        "completed_lap": bool(df["completed_lap"].max()),
        "collision": bool(df["collision"].max()),
        "final_time_s": float(df["time_s"].iloc[-1]),
        "final_progress_m": float(df["progress_m"].max()),
        "rms_cte_m": float(np.sqrt(np.mean(df["cte_m"] ** 2))),
        "max_abs_cte_m": float(df["abs_cte_m"].max()),
        "rms_position_error_vs_ref_progress_m": np.nan,
        "max_position_error_vs_ref_progress_m": np.nan,
        "rms_position_error_vs_ref_time_m": np.nan,
        "max_position_error_vs_ref_time_m": np.nan,
        "rms_position_change_vs_next_finer_dt_progress_m": np.nan,
        "max_position_change_vs_next_finer_dt_progress_m": np.nan,
        "rms_position_change_vs_next_finer_dt_time_m": np.nan,
        "max_position_change_vs_next_finer_dt_time_m": np.nan,
        "termination_reason": str(df["termination_reason"].iloc[-1]),
    }


def prepare_for_interp(df: pd.DataFrame, key: str) -> pd.DataFrame:
    clean = df[[key, "x_m", "y_m"]].dropna().copy()
    clean = clean.sort_values(key)
    clean = clean.drop_duplicates(subset=key, keep="last")
    if clean[key].nunique() < 2:
        raise ValueError(f"Not enough unique {key} values for interpolation.")
    return clean


def position_error_metrics(test_df: pd.DataFrame, ref_df: pd.DataFrame, key: str) -> tuple[float, float]:
    test_clean = prepare_for_interp(test_df, key)
    ref_clean = prepare_for_interp(ref_df, key)

    start = max(float(test_clean[key].iloc[0]), float(ref_clean[key].iloc[0]))
    end = min(float(test_clean[key].iloc[-1]), float(ref_clean[key].iloc[-1]))
    if end <= start:
        raise ValueError(f"No common {key} range for interpolation.")

    grid = np.linspace(start, end, ERROR_GRID_POINTS)
    test_x = np.interp(grid, test_clean[key], test_clean["x_m"])
    test_y = np.interp(grid, test_clean[key], test_clean["y_m"])
    ref_x = np.interp(grid, ref_clean[key], ref_clean["x_m"])
    ref_y = np.interp(grid, ref_clean[key], ref_clean["y_m"])

    err = np.sqrt((test_x - ref_x) ** 2 + (test_y - ref_y) ** 2)
    return float(np.sqrt(np.mean(err**2))), float(np.max(err))


def apply_error_metrics(results: dict[float, dict], telemetry: dict[float, pd.DataFrame]) -> pd.DataFrame:
    ref_df = telemetry[REFERENCE_DT]
    results[REFERENCE_DT]["rms_position_error_vs_ref_progress_m"] = 0.0
    results[REFERENCE_DT]["max_position_error_vs_ref_progress_m"] = 0.0
    results[REFERENCE_DT]["rms_position_error_vs_ref_time_m"] = 0.0
    results[REFERENCE_DT]["max_position_error_vs_ref_time_m"] = 0.0

    for dt_s in DT_VALUES:
        if dt_s == REFERENCE_DT:
            continue
        progress_rms, progress_max = position_error_metrics(telemetry[dt_s], ref_df, "progress_m")
        time_rms, time_max = position_error_metrics(telemetry[dt_s], ref_df, "time_s")
        results[dt_s]["rms_position_error_vs_ref_progress_m"] = progress_rms
        results[dt_s]["max_position_error_vs_ref_progress_m"] = progress_max
        results[dt_s]["rms_position_error_vs_ref_time_m"] = time_rms
        results[dt_s]["max_position_error_vs_ref_time_m"] = time_max

    for index, dt_s in enumerate(DT_VALUES[:-1]):
        next_finer_dt = DT_VALUES[index + 1]
        progress_rms, progress_max = position_error_metrics(telemetry[dt_s], telemetry[next_finer_dt], "progress_m")
        time_rms, time_max = position_error_metrics(telemetry[dt_s], telemetry[next_finer_dt], "time_s")
        results[dt_s]["rms_position_change_vs_next_finer_dt_progress_m"] = progress_rms
        results[dt_s]["max_position_change_vs_next_finer_dt_progress_m"] = progress_max
        results[dt_s]["rms_position_change_vs_next_finer_dt_time_m"] = time_rms
        results[dt_s]["max_position_change_vs_next_finer_dt_time_m"] = time_max

    df = pd.DataFrame([results[dt_s] for dt_s in DT_VALUES])
    return df[RESULT_FIELDNAMES]


def select_timestep(results: pd.DataFrame) -> float | None:
    candidates = results.dropna(
        subset=[
            "rms_position_change_vs_next_finer_dt_progress_m",
            "max_position_change_vs_next_finer_dt_progress_m",
        ]
    ).copy()

    acceptable = candidates[
        (candidates["completed_lap"] == True)
        & (candidates["collision"] == False)
        & (candidates["rms_position_change_vs_next_finer_dt_progress_m"] < RMS_REFINEMENT_TOL_M)
        & (candidates["max_position_change_vs_next_finer_dt_progress_m"] < MAX_REFINEMENT_TOL_M)
    ]

    if acceptable.empty:
        return None
    return float(acceptable["dt_s"].max())


def save_results(results: pd.DataFrame) -> None:
    results.to_csv(RESULTS_PATH, index=False)


def plot_position_error(results: pd.DataFrame) -> None:
    plot_df = results.sort_values("dt_s")
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        plot_df["dt_s"],
        plot_df["rms_position_error_vs_ref_progress_m"],
        marker="o",
        label="RMS error vs finest reference",
    )
    ax.plot(
        plot_df["dt_s"],
        plot_df["max_position_error_vs_ref_progress_m"],
        marker="s",
        label="Max error vs finest reference",
    )
    ax.plot(
        plot_df["dt_s"],
        plot_df["rms_position_change_vs_next_finer_dt_progress_m"],
        marker="^",
        label="RMS refinement change",
    )
    ax.plot(
        plot_df["dt_s"],
        plot_df["max_position_change_vs_next_finer_dt_progress_m"],
        marker="D",
        label="Max refinement change",
    )
    ax.axhline(RMS_REFINEMENT_TOL_M, color="0.35", linestyle="--", linewidth=1.2, label="RMS tolerance")
    ax.axhline(MAX_REFINEMENT_TOL_M, color="0.15", linestyle=":", linewidth=1.4, label="Max tolerance")

    ax.set_xscale("log")
    ax.set_xlabel("RK4 timestep dt [s]")
    ax.set_ylabel("Position error/change [m]")
    ax.set_title("RK4 Timestep Convergence: Position Error")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)

    fig.tight_layout()
    fig.savefig(POSITION_ERROR_FIGURE, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_convergence_metrics(results: pd.DataFrame) -> None:
    plot_df = results.sort_values("dt_s")
    status = np.where(plot_df["completed_lap"] & ~plot_df["collision"], 1.0, 0.0)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    axes = axes.ravel()

    axes[0].plot(plot_df["dt_s"], plot_df["final_progress_m"], marker="o")
    axes[0].set_ylabel("Final progress [m]")
    axes[0].set_title("Final Progress")

    axes[1].plot(plot_df["dt_s"], plot_df["rms_cte_m"], marker="o", color="#1f77b4")
    axes[1].set_ylabel("RMS CTE [m]")
    axes[1].set_title("Tracking Error")

    axes[2].plot(plot_df["dt_s"], plot_df["max_abs_cte_m"], marker="o", color="#ff7f0e")
    axes[2].set_ylabel("Max |CTE| [m]")
    axes[2].set_title("Worst Tracking Error")

    axes[3].step(plot_df["dt_s"], status, where="mid", color="#2ca02c")
    axes[3].scatter(plot_df["dt_s"], status, color=np.where(plot_df["collision"], "#d62728", "#2ca02c"), zorder=3)
    axes[3].set_yticks([0, 1])
    axes[3].set_yticklabels(["failed/collided", "completed"])
    axes[3].set_ylabel("Status")
    axes[3].set_title("Completion Status")

    for ax in axes:
        ax.set_xscale("log")
        ax.set_xlabel("RK4 timestep dt [s]")
        ax.grid(True, which="both", alpha=0.3)

    fig.suptitle("RK4 Timestep Convergence Metrics", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(METRICS_FIGURE, dpi=300, bbox_inches="tight")
    plt.close(fig)


def markdown_table(df: pd.DataFrame) -> str:
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda value: "" if pd.isna(value) else f"{value:.6g}")
    headers = list(display.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---" for _ in headers]) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def write_report(results: pd.DataFrame, selected_dt: float | None) -> None:
    selected_text = (
        f"RK4 timestep selected: `dt = {selected_dt:.4f} s`."
        if selected_dt is not None
        else "No timestep satisfied the preselected criterion."
    )
    baseline_row = results[np.isclose(results["dt_s"], 0.01)]
    if not baseline_row.empty:
        row = baseline_row.iloc[0]
        acceptable = (
            bool(row["completed_lap"])
            and not bool(row["collision"])
            and row["rms_position_change_vs_next_finer_dt_progress_m"] < RMS_REFINEMENT_TOL_M
            and row["max_position_change_vs_next_finer_dt_progress_m"] < MAX_REFINEMENT_TOL_M
        )
        baseline_text = (
            "`dt = 0.01 s`, the original baseline timestep, satisfies the preselected refinement criterion."
            if acceptable
            else "`dt = 0.01 s`, the original baseline timestep, does not satisfy the preselected refinement criterion."
        )
    else:
        baseline_text = "The original baseline timestep `dt = 0.01 s` was not present in the convergence results."

    report = f"""# RK4 Integrator Convergence Study

## Purpose

This study selects a numerically acceptable RK4 timestep for F1TENTH Gym closed-loop pure-pursuit simulations.

This is simulator timestep convergence, not system identification.

## Fixed Experiment Setup

- Integrator: RK4
- Track: examples/example_map
- Waypoints: examples/example_waypoints.csv
- Controller: pure pursuit
- Lookahead: {WORK_PARAMS["tlad"]} m
- Velocity gain: {WORK_PARAMS["vgain"]}
- Speed behavior: waypoint speed multiplied by velocity gain
- Maximum simulation time: {MAX_SIM_TIME_S} s

## Preselected Acceptance Criterion

RK4 timestep is acceptable if the pairwise refinement-change metric satisfies:

- RMS progress-aligned position change < {RMS_REFINEMENT_TOL_M} m
- max progress-aligned position change < {MAX_REFINEMENT_TOL_M} m

over the common completed progress range.

This criterion was selected before interpreting the convergence results.

## Timestep Cases

| dt [s] |
|---:|
| 0.0200 |
| 0.0100 |
| 0.0050 |
| 0.0020 |
| 0.0010 |
| 0.0005 |

## Results

{markdown_table(results)}

## Figures

![Position error convergence](figures/integrator_convergence_position_error.png)

![Convergence metrics](figures/integrator_convergence_metrics.png)

## Selected Timestep

{selected_text}

## Interpretation

{baseline_text}

The progress-aligned refinement-change metric is the decision metric because it compares vehicle position at the same distance along the path. Time-aligned error is included as a secondary diagnostic because it also includes timing and speed-phase differences.

## Limitations

This study only addresses RK4 timestep convergence for the fixed pure-pursuit lap. It does not identify vehicle parameters, tune the controller, or compare against a derived bicycle model.
"""
    REPORT_PATH.write_text(report)


def run_all_cases(conf: Namespace, waypoints: np.ndarray) -> dict[float, pd.DataFrame]:
    telemetry = {}

    ordered_dt = [REFERENCE_DT] + [dt for dt in DT_VALUES if dt != REFERENCE_DT]
    for dt_s in ordered_dt:
        rows = run_variant(conf, waypoints, dt_s)
        path = write_telemetry(rows, dt_s)
        frame = rows_to_frame(rows)
        telemetry[dt_s] = frame
        final = summarize_run(frame, dt_s)
        print(
            f"Wrote {path} | dt={dt_s:.4f} s | "
            f"termination={final['termination_reason']} | "
            f"final_progress={final['final_progress_m']:.2f} m"
        )

        if dt_s == REFERENCE_DT and (not final["completed_lap"] or final["collision"]):
            raise RuntimeError("Reference run dt=0.0005 failed. Convergence metrics are invalid.")

    return telemetry


def main() -> None:
    os.chdir(REPO_ROOT)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    conf = load_config()
    waypoints = load_waypoints(conf)

    telemetry = run_all_cases(conf, waypoints)
    summaries = {dt_s: summarize_run(telemetry[dt_s], dt_s) for dt_s in DT_VALUES}
    results = apply_error_metrics(summaries, telemetry)
    selected_dt = select_timestep(results)

    save_results(results)
    plot_position_error(results)
    plot_convergence_metrics(results)
    write_report(results, selected_dt)

    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {POSITION_ERROR_FIGURE}")
    print(f"Wrote {METRICS_FIGURE}")
    print(f"Wrote {REPORT_PATH}")
    if selected_dt is None:
        print("No RK4 timestep satisfied the preselected refinement criterion.")
    else:
        print(f"Selected RK4 timestep: dt={selected_dt:.4f} s")


if __name__ == "__main__":
    main()
