#!/usr/bin/env python
"""Race the tuned pure-pursuit baseline closed-loop and report ride-quality accel/jerk.

Produces ONE honest representative peak lateral acceleration from a clean, completed
lap. The number feeds the LiDAR-mast maneuvering load case in
``docs/design/16_mechanical_design_analysis.md``
(``F_lateral = m_LiDAR_tip * a_lat,peak * SF``).

Primary controller: the selected pure-pursuit baseline from
``runs/pure_pursuit_sweep/results.csv`` (the single row where
``selected_baseline == True``: lookahead 1.2 m, velocity gain 1.2). If that run
does not complete a clean lap, fall back to the LQR nominal controller, which is
known to complete.

Integration is RK4 at ``dt = 0.002 s`` with the controller updated at 100 Hz, the
same configuration validated across the controller experiments. Lateral accel is
``v * yaw_rate`` per step (see ``summarize_run`` in ``gym/roboracer/closed_loop.py``);
``runs/first_lap/telemetry.csv`` (collision spikes) is deliberately NOT used.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.closed_loop import project_to_path, race_and_report
from roboracer.controllers import LinearPathModel, LQRController, PurePursuitController

EXAMPLES_DIR = REPO_ROOT / "examples"
PP_RESULTS_PATH = REPO_ROOT / "runs" / "pure_pursuit_sweep" / "results.csv"
RUN_DIR = REPO_ROOT / "runs" / "ride_quality_baseline"
SUMMARY_PATH = RUN_DIR / "summary.json"
TELEMETRY_PATH = RUN_DIR / "telemetry.csv"

INTEGRATION_DT_S = 0.002
CONTROL_RATE_HZ = 100.0
CONTROL_DT_S = 1.0 / CONTROL_RATE_HZ
MAX_SIM_TIME_S = 45.0

# LQR fallback weights, matching experiments/lqr_controller.py (nominal case).
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


def race_pure_pursuit(conf: Namespace, waypoints: np.ndarray, baseline: pd.Series):
    controller = PurePursuitController(
        conf,
        lookahead_m=float(baseline["lookahead_m"]),
        vgain=float(baseline["vgain"]),
        name="pure_pursuit",
    )
    summary, trace = race_and_report(
        controller,
        conf,
        waypoints,
        return_trace=True,
        integration_dt=INTEGRATION_DT_S,
        control_rate_hz=CONTROL_RATE_HZ,
        max_sim_time_s=MAX_SIM_TIME_S,
        run_id="ride_quality_pure_pursuit",
    )
    label = (
        f"pure_pursuit (lookahead={float(baseline['lookahead_m']):.3f} m, "
        f"vgain={float(baseline['vgain']):.3f})"
    )
    return summary, trace, label


def race_lqr_nominal(conf: Namespace, waypoints: np.ndarray, baseline: pd.Series):
    v0 = float(max(baseline["mean_speed_mps"], 0.75))
    kappa0 = operating_curvature(conf, waypoints)
    model = LinearPathModel(CONTROL_DT_S, v0, kappa0, Q_DIAG, R_DIAG)
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
    summary, trace = race_and_report(
        controller,
        conf,
        waypoints,
        return_trace=True,
        integration_dt=INTEGRATION_DT_S,
        control_rate_hz=CONTROL_RATE_HZ,
        max_sim_time_s=MAX_SIM_TIME_S,
        run_id="ride_quality_lqr_nominal",
    )
    return summary, trace, "lqr (nominal)"


def is_clean(summary: dict) -> bool:
    return bool(summary["completed_lap"]) and not bool(summary["collision"])


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    conf = load_config()
    waypoints = load_waypoints(conf)
    baseline = selected_baseline()

    summary, trace, label = race_pure_pursuit(conf, waypoints, baseline)
    print(
        f"pure_pursuit: completed_lap={summary['completed_lap']} "
        f"collision={summary['collision']} "
        f"max_abs_lat_accel_mps2={summary['max_abs_lat_accel_mps2']:.4f}"
    )
    if not is_clean(summary):
        print("Pure-pursuit baseline did not complete a clean lap; falling back to LQR nominal.")
        summary, trace, label = race_lqr_nominal(conf, waypoints, baseline)
        print(
            f"lqr (nominal): completed_lap={summary['completed_lap']} "
            f"collision={summary['collision']} "
            f"max_abs_lat_accel_mps2={summary['max_abs_lat_accel_mps2']:.4f}"
        )

    if not is_clean(summary):
        raise RuntimeError(
            "Neither the pure-pursuit baseline nor the LQR nominal controller completed a clean lap; "
            "no honest ride-quality number is available."
        )

    summary_out = dict(summary)
    summary_out["controller_label"] = label
    summary_out["clean_lap"] = True
    summary_out["integrator"] = "RK4"

    SUMMARY_PATH.write_text(json.dumps(summary_out, indent=2) + "\n", encoding="utf-8")
    trace.to_csv(TELEMETRY_PATH, index=False)

    print()
    print(f"Controller producing the number: {label}")
    print(json.dumps(summary_out, indent=2))
    print()
    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {TELEMETRY_PATH}")
    print()
    print(
        "Representative ride-quality figures (clean completed lap, RK4 dt=0.002 s, 100 Hz control):\n"
        f"  mean_abs_lat_accel_mps2 = {summary_out['mean_abs_lat_accel_mps2']:.4f}\n"
        f"  max_abs_lat_accel_mps2  = {summary_out['max_abs_lat_accel_mps2']:.4f}  <-- a_lat,peak\n"
        f"  max_abs_long_accel_mps2 = {summary_out['max_abs_long_accel_mps2']:.4f}\n"
        f"  rms_lat_jerk_mps3       = {summary_out['rms_lat_jerk_mps3']:.4f}"
    )


if __name__ == "__main__":
    main()
