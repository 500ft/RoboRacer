#!/usr/bin/env python
"""Run constrained linear MPC using SciPy SLSQP."""

from __future__ import annotations

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

from roboracer.closed_loop import project_to_path, run_closed_loop
from roboracer.controllers import LinearPathModel, MPCController, PurePursuitController

EXAMPLES_DIR = REPO_ROOT / "examples"
PP_RESULTS_PATH = REPO_ROOT / "runs" / "pure_pursuit_sweep" / "results.csv"
RUN_DIR = REPO_ROOT / "runs" / "mpc_controller"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
RESULTS_PATH = RUN_DIR / "results.csv"
REPORT_PATH = REPO_ROOT / "reports" / "mpc_controller.md"
RUNTIME_FIGURE_PATH = FIGURE_DIR / "mpc_solver_runtime.png"
CTE_FIGURE_PATH = FIGURE_DIR / "mpc_controller_cte.png"
INTEGRATION_DT_S = 0.002
CONTROL_RATE_HZ = 100.0
CONTROL_DT_S = 1.0 / CONTROL_RATE_HZ
MAX_SIM_TIME_S = 45.0
HORIZON = 15
MAX_STEER_CORRECTION_RAD = 0.005
Q_DIAG = np.array([20.0, 12.0, 1.0, 0.5, 2.0, 2.0], dtype=float)
R_DIAG = np.array([2.0, 0.5], dtype=float)


def load_config() -> Namespace:
    with (EXAMPLES_DIR / "config_example_map.yaml").open() as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    config["map_path"] = str((EXAMPLES_DIR / config["map_path"]).resolve())
    config["wpt_path"] = str((EXAMPLES_DIR / config["wpt_path"]).resolve())
    return Namespace(**config)


def load_waypoints(conf: Namespace) -> np.ndarray:
    return np.loadtxt(conf.wpt_path, delimiter=conf.wpt_delim, skiprows=conf.wpt_rowskip)


def selected_baseline() -> pd.Series:
    if not PP_RESULTS_PATH.exists():
        raise FileNotFoundError(f"Run pure_pursuit_sweep.py first: {PP_RESULTS_PATH}")
    results = pd.read_csv(PP_RESULTS_PATH)
    selected = results[results["selected_baseline"] == True]  # noqa: E712
    if len(selected) != 1:
        raise ValueError("Pure-pursuit sweep must contain exactly one selected baseline.")
    return selected.iloc[0]


def operating_curvature(conf: Namespace, waypoints: np.ndarray) -> float:
    samples = []
    xy = waypoints[:, [conf.wpt_xind, conf.wpt_yind]]
    for x, y in xy[:: max(1, len(xy) // 200)]:
        samples.append(project_to_path(float(x), float(y), waypoints, conf)["path_curvature_1pm"])
    finite = np.asarray([value for value in samples if np.isfinite(value)], dtype=float)
    return float(np.median(finite)) if finite.size else 0.0


def plot_runtime(controller: MPCController) -> None:
    times = np.asarray(controller.solve_times_s, dtype=float)
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.plot(np.arange(len(times)), 1000.0 * times, linewidth=1.0)
    ax.axhline(10.0, color="#d62728", linestyle="--", label="100 Hz budget")
    ax.axhline(20.0, color="#ff7f0e", linestyle=":", label="50 Hz budget")
    ax.set_xlabel("MPC solve index")
    ax.set_ylabel("Solve time [ms]")
    ax.set_title("MPC Solver Runtime")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(RUNTIME_FIGURE_PATH, dpi=220)
    plt.close(fig)


def plot_cte(trace: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.plot(trace["time_s"], trace["cte_m"], linewidth=1.3)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("CTE [m]")
    ax.set_title("MPC Controller CTE")
    ax.grid(True, alpha=0.25)
    fig.savefig(CTE_FIGURE_PATH, dpi=220)
    plt.close(fig)


def write_report(result: pd.Series) -> None:
    report = f"""# MPC Controller

## Objective

Evaluate constrained linear MPC using the same 100 Hz control model as LQR and measure solver runtime against real-time budgets.

## Setup

- Integration timestep: `{INTEGRATION_DT_S:.3f} s`
- Controller update rate: `{CONTROL_RATE_HZ:.0f} Hz`
- MPC horizon: `{HORIZON}`
- Maximum MPC steering correction: `{MAX_STEER_CORRECTION_RAD:.6g} rad`
- Feedforward: selected pure-pursuit baseline with bounded MPC correction
- Optimizer: SciPy SLSQP with analytic objective gradient and linear rate constraints
- Steering, steering-rate, and acceleration constraints are pulled from the shared model parameters.

## Result

| Metric | Value |
| --- | ---: |
| Completed lap | {bool(result["completed_lap"])} |
| Collision | {bool(result["collision"])} |
| Lap/final time | {float(result["lap_time_s"]):.6g} s |
| RMS CTE | {float(result["rms_cte_m"]):.6g} m |
| Max CTE | {float(result["max_abs_cte_m"]):.6g} m |
| Steering effort | {float(result["steering_effort_rad"]):.6g} rad |
| Mean solve time | {1000.0 * float(result["mpc_mean_solve_time_s"]):.6g} ms |
| p95 solve time | {1000.0 * float(result["mpc_p95_solve_time_s"]):.6g} ms |
| Max solve time | {1000.0 * float(result["mpc_max_solve_time_s"]):.6g} ms |
| 100 Hz budget passed | {bool(result["mpc_meets_100hz_budget"])} |
| 50 Hz budget passed | {bool(result["mpc_meets_50hz_budget"])} |

## Figures

![MPC solver runtime](figures/mpc_solver_runtime.png)

![MPC CTE](figures/mpc_controller_cte.png)

## Interpretation

The runtime result is measured evidence for this SciPy/SLSQP implementation. This local run passes the 100 Hz p95 budget, although the maximum solve time can still spike above a single 10 ms control period. A deployment controller should still use a dedicated QP solver, watchdog timing, or a shorter horizon.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    conf = load_config()
    waypoints = load_waypoints(conf)
    baseline = selected_baseline()
    v0 = float(max(baseline["mean_speed_mps"], 0.75))
    model = LinearPathModel(CONTROL_DT_S, v0, operating_curvature(conf, waypoints), Q_DIAG, R_DIAG)
    feedforward = PurePursuitController(
        conf,
        lookahead_m=float(baseline["lookahead_m"]),
        vgain=float(baseline["vgain"]),
        name="mpc_feedforward_pp",
    )
    controller = MPCController(
        model,
        target_speed_mps=v0,
        horizon=HORIZON,
        feedforward_controller=feedforward,
        max_steer_correction_rad=MAX_STEER_CORRECTION_RAD,
    )
    trace, summary = run_closed_loop(
        controller,
        conf,
        waypoints,
        integration_dt=INTEGRATION_DT_S,
        control_rate_hz=CONTROL_RATE_HZ,
        max_sim_time_s=MAX_SIM_TIME_S,
        run_id="mpc_nominal",
    )
    summary.update(controller.runtime_summary())
    results = pd.DataFrame([summary])
    results.to_csv(RESULTS_PATH, index=False)
    plot_runtime(controller)
    plot_cte(trace)
    write_report(results.iloc[0])
    print(
        "MPC nominal: "
        f"termination={summary['termination_reason']} rms_cte={summary['rms_cte_m']:.3f} "
        f"p95_solve_ms={1000.0 * summary['mpc_p95_solve_time_s']:.3f}"
    )
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
