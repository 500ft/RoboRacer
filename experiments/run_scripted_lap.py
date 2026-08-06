#!/usr/bin/env python
"""Run a headless pure-pursuit lap and log RK4/Euler telemetry."""

from __future__ import annotations

import csv
import json
import os
import platform
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import gym
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.track import PurePursuitPlanner, nearest_waypoint_metrics, scalar

EXAMPLES_DIR = REPO_ROOT / "examples"
RUN_DIR = REPO_ROOT / "runs" / "first_lap"
TELEMETRY_PATH = RUN_DIR / "telemetry.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
MAX_STEPS = 20000

from f110_gym.envs.base_classes import Integrator  # noqa: E402

WORK_PARAMS = {
    "mass": 3.463388126201571,
    "lf": 0.15597534362552312,
    "tlad": 0.82461887897713965,
    "vgain": 1.375,
}

FIELDNAMES = [
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


def load_config() -> Namespace:
    with (EXAMPLES_DIR / "config_example_map.yaml").open() as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    config["map_path"] = str((EXAMPLES_DIR / config["map_path"]).resolve())
    config["wpt_path"] = str((EXAMPLES_DIR / config["wpt_path"]).resolve())
    return Namespace(**config)


def load_waypoints(conf: Namespace) -> np.ndarray:
    return np.loadtxt(conf.wpt_path, delimiter=conf.wpt_delim, skiprows=conf.wpt_rowskip)


def run_variant(conf: Namespace, waypoints: np.ndarray, name: str, integrator: Integrator) -> list[dict]:
    run_id = f"first_lap_{name}"
    planner = PurePursuitPlanner(conf, 0.17145 + 0.15875)
    env = gym.make(
        "f110_gym:f110-v0",
        map=conf.map_path,
        map_ext=conf.map_ext,
        num_agents=1,
        timestep=0.01,
        integrator=integrator,
    )

    obs, _, _, info = env.reset(np.array([[conf.sx, conf.sy, conf.stheta]]))
    rows = []
    previous_speed = scalar(obs, "linear_vels_x")
    termination_reason = "max_steps"

    try:
        for step in range(MAX_STEPS):
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
            speed = scalar(obs, "linear_vels_x")
            yaw_rate = scalar(obs, "ang_vels_z")
            accel_x = (speed - previous_speed) / float(step_reward)
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
            elif step == MAX_STEPS - 1:
                termination_reason = "max_steps"
            else:
                termination_reason = ""

            rows.append(
                {
                    "run_id": run_id,
                    "integrator": name,
                    "step": step + 1,
                    "time_s": f"{(step + 1) * float(step_reward):.6f}",
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
        for row in rows:
            row["termination_reason"] = final_reason
    return rows


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


def write_metadata(conf: Namespace) -> None:
    metadata = {
        "python_version": platform.python_version(),
        "f1tenth_gym_commit": git_commit(),
        "map": "examples/example_map",
        "waypoints": "examples/example_waypoints.csv",
        "control": "pure_pursuit",
        "integrators": ["rk4", "euler"],
        "max_steps": MAX_STEPS,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")


def main() -> None:
    os.chdir(REPO_ROOT)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    conf = load_config()
    waypoints = load_waypoints(conf)

    all_rows = []
    for name, integrator in (("rk4", Integrator.RK4), ("euler", Integrator.Euler)):
        all_rows.extend(run_variant(conf, waypoints, name, integrator))

    with TELEMETRY_PATH.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    write_metadata(conf)
    print(f"Wrote {len(all_rows)} telemetry rows to {TELEMETRY_PATH}")
    print(f"Wrote metadata to {METADATA_PATH}")


if __name__ == "__main__":
    main()
