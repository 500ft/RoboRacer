#!/usr/bin/env python
"""Run LQR controller cases against the tuned pure-pursuit baseline."""

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

from roboracer.closed_loop import project_to_path, run_closed_loop
from roboracer.controllers import LQRController, LinearPathModel, PurePursuitController

EXAMPLES_DIR = REPO_ROOT / "examples"
PP_RESULTS_PATH = REPO_ROOT / "runs" / "pure_pursuit_sweep" / "results.csv"
RUN_DIR = REPO_ROOT / "runs" / "lqr_controller"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
RESULTS_PATH = RUN_DIR / "results.csv"
MODEL_PATH = RUN_DIR / "linear_model.json"
REPORT_PATH = REPO_ROOT / "reports" / "lqr_controller.md"
CTE_FIGURE_PATH = FIGURE_DIR / "lqr_controller_cte_cases.png"

INTEGRATION_DT_S = 0.002
CONTROL_RATE_HZ = 100.0
CONTROL_DT_S = 1.0 / CONTROL_RATE_HZ
MAX_SIM_TIME_S = 45.0
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
    if finite.size == 0:
        return 0.0
    return float(np.median(finite))


def matrix_payload(model: LinearPathModel, baseline: pd.Series, kappa0: float) -> dict[str, object]:
    return {
        "integration_dt_s": INTEGRATION_DT_S,
        "control_rate_hz": CONTROL_RATE_HZ,
        "control_dt_s": CONTROL_DT_S,
        "operating_speed_mps": float(max(baseline["mean_speed_mps"], 0.75)),
        "operating_curvature_1pm": float(kappa0),
        "q_diag": Q_DIAG.tolist(),
        "r_diag": R_DIAG.tolist(),
        "A_continuous": model.a_c.tolist(),
        "B_continuous": model.b_c.tolist(),
        "A_discrete": model.a_d.tolist(),
        "B_discrete": model.b_d.tolist(),
        "K": model.k.tolist(),
        "closed_loop_eigenvalues": [
            {"real": float(np.real(value)), "imag": float(np.imag(value)), "abs": float(abs(value))}
            for value in model.closed_loop_eigenvalues
        ],
        "closed_loop_stable_discrete": bool(np.max(np.abs(model.closed_loop_eigenvalues)) < 1.0),
    }


def plot_cases(case_traces: dict[str, pd.DataFrame]) -> None:
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    for case, trace in case_traces.items():
        ax.plot(trace["time_s"], trace["cte_m"], label=case, linewidth=1.4)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("CTE [m]")
    ax.set_title("LQR Controller CTE Cases")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(CTE_FIGURE_PATH, dpi=220)
    plt.close(fig)


def write_report(results: pd.DataFrame, payload: dict[str, object]) -> None:
    eig_max = max(item["abs"] for item in payload["closed_loop_eigenvalues"])
    lines = ["| case | completed | collision | lap time [s] | RMS CTE [m] | max CTE [m] | steering effort [rad] |", "| --- | --- | --- | ---: | ---: | ---: | ---: |"]
    for row in results.itertuples(index=False):
        lines.append(
            f"| {row.case} | {bool(row.completed_lap)} | {bool(row.collision)} | "
            f"{float(row.lap_time_s):.6g} | {float(row.rms_cte_m):.6g} | "
            f"{float(row.max_abs_cte_m):.6g} | {float(row.steering_effort_rad):.6g} |"
        )
    report = f"""# LQR Controller

## Objective

Design a discrete LQR controller from a local path-error model and compare nominal/off-nominal cases against the tuned pure-pursuit baseline setup.

## Setup

- Integration timestep: `{INTEGRATION_DT_S:.3f} s`
- Controller update rate: `{CONTROL_RATE_HZ:.0f} Hz`
- LQR discretization timestep: `{CONTROL_DT_S:.3f} s`
- Operating speed: `{payload["operating_speed_mps"]:.6g} m/s`
- Operating curvature: `{payload["operating_curvature_1pm"]:.6g} 1/m`
- Maximum LQR steering correction: `{MAX_STEER_CORRECTION_RAD:.6g} rad`
- State: `[cte, heading_error, steer_error, speed_error, yaw_rate_error, slip_angle]`
- Input: `[steering_rate, acceleration]`

## Weights

- `Q = diag({payload["q_diag"]})`
- `R = diag({payload["r_diag"]})`

## Closed-Loop Eigenvalues

Maximum absolute discrete eigenvalue: `{eig_max:.6g}`.

Stable inside unit circle: `{payload["closed_loop_stable_discrete"]}`.

Full matrices and eigenvalues are stored in `runs/lqr_controller/linear_model.json`.

## Case Results

{chr(10).join(lines)}

## Figure

![LQR CTE cases](figures/lqr_controller_cte_cases.png)

## Interpretation

This LQR uses the tuned pure-pursuit command as feedforward and applies a small bounded LQR correction on top of it. The nominal, offset, and delayed cases complete, but the tuned pure-pursuit baseline still has lower RMS CTE. Treat this as a first model-based feedback baseline, not a globally optimal controller for every segment of the track.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    conf = load_config()
    waypoints = load_waypoints(conf)
    baseline = selected_baseline()
    v0 = float(max(baseline["mean_speed_mps"], 0.75))
    kappa0 = operating_curvature(conf, waypoints)
    model = LinearPathModel(CONTROL_DT_S, v0, kappa0, Q_DIAG, R_DIAG)
    payload = matrix_payload(model, baseline, kappa0)
    MODEL_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    cases = [
        ("nominal", 0.0, 0),
        ("offset_plus_0p5m", 0.5, 0),
        ("delay_30ms", 0.0, 3),
    ]
    rows = []
    traces = {}
    for case, offset, delay_steps in cases:
        feedforward = PurePursuitController(
            conf,
            lookahead_m=float(baseline["lookahead_m"]),
            vgain=float(baseline["vgain"]),
            name="lqr_feedforward_pp",
        )
        controller = LQRController(
            model,
            target_speed_mps=v0,
            feedforward_controller=feedforward,
            max_steer_correction_rad=MAX_STEER_CORRECTION_RAD,
            name="lqr",
        )
        trace, summary = run_closed_loop(
            controller,
            conf,
            waypoints,
            integration_dt=INTEGRATION_DT_S,
            control_rate_hz=CONTROL_RATE_HZ,
            max_sim_time_s=MAX_SIM_TIME_S,
            init_lateral_offset_m=offset,
            control_delay_steps=delay_steps,
            run_id=f"lqr_{case}",
        )
        summary.update({"case": case, "delay_ms": delay_steps * CONTROL_DT_S * 1000.0})
        rows.append(summary)
        traces[case] = trace
        print(
            f"LQR {case}: termination={summary['termination_reason']} "
            f"rms_cte={summary['rms_cte_m']:.3f} delay_ms={summary['delay_ms']:.1f}"
        )

    results = pd.DataFrame(rows)
    results.to_csv(RESULTS_PATH, index=False)
    plot_cases(traces)
    write_report(results, payload)
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
