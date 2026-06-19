#!/usr/bin/env python
"""Reproduce failure modes and write an FMEA table."""

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

from f110_gym.envs.base_classes import Integrator
from roboracer.closed_loop import run_closed_loop
from roboracer.controllers import PurePursuitController
from roboracer.dynamics import DEFAULT_DYNAMIC_PARAMS
from roboracer.failures import FailureScenario, default_failure_scenarios

EXAMPLES_DIR = REPO_ROOT / "examples"
PP_RESULTS_PATH = REPO_ROOT / "runs" / "pure_pursuit_sweep" / "results.csv"
EKF_SUMMARY_PATH = REPO_ROOT / "runs" / "ekf_study" / "summary.csv"
RUN_DIR = REPO_ROOT / "runs" / "failure_mode_fmea"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
RESULTS_PATH = RUN_DIR / "results.csv"
REPORT_PATH = REPO_ROOT / "reports" / "failure_mode_fmea.md"
RPN_FIGURE = FIGURE_DIR / "fmea_rpn_bar.png"
SIGNALS_FIGURE = FIGURE_DIR / "fmea_detection_signals.png"
INTEGRATION_DT_S = 0.002
CONTROL_RATE_HZ = 100.0
MAX_SIM_TIME_S = 45.0


class SaturatingSteerController:
    name = "saturating_steer"

    def __init__(self, steer_rad: float, speed_mps: float):
        self.steer_rad = float(steer_rad)
        self.speed_mps = float(speed_mps)

    def reset(self) -> None:
        return None

    def command(self, state: dict[str, float], path_info: dict[str, float]) -> tuple[float, float]:
        return self.steer_rad, self.speed_mps


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


def scenario_row(scenario: FailureScenario, reproduced: bool, signal: str, metric: float) -> dict[str, object]:
    return {
        "scenario": scenario.scenario,
        "category": scenario.category,
        "reproduced": bool(reproduced),
        "cause": scenario.cause,
        "trigger": scenario.trigger,
        "effect": scenario.effect,
        "detection_signal": signal,
        "detection_metric": float(metric),
        "mitigation": scenario.mitigation,
        "severity_1_to_10": scenario.severity_1_to_10,
        "occurrence_1_to_10": scenario.occurrence_1_to_10,
        "detectability_1_to_10": scenario.detectability_1_to_10,
        "rpn": scenario.severity_1_to_10 * scenario.occurrence_1_to_10 * scenario.detectability_1_to_10,
    }


def run_pp_case(conf: Namespace, waypoints: np.ndarray, scenario: FailureScenario, baseline: pd.Series) -> dict[str, object]:
    params = scenario.parameters
    lookahead = float(params.get("lookahead_m", baseline["lookahead_m"]))
    vgain = float(params.get("vgain", baseline["vgain"]))
    controller = PurePursuitController(conf, lookahead_m=lookahead, vgain=vgain, name=scenario.scenario)
    delay_steps = int(round(float(params.get("delay_ms", 0.0)) / 1000.0 * CONTROL_RATE_HZ))
    integrator = Integrator.Euler if str(params.get("integrator", "RK4")) == "Euler" else Integrator.RK4
    integration_dt = float(params.get("dt_s", INTEGRATION_DT_S))
    _, summary = run_closed_loop(
        controller,
        conf,
        waypoints,
        integration_dt=integration_dt,
        control_rate_hz=CONTROL_RATE_HZ,
        integrator=integrator,
        max_sim_time_s=MAX_SIM_TIME_S,
        control_delay_steps=delay_steps,
        run_id=scenario.scenario,
    )
    if summary["collision"]:
        signal = f"collision at {summary['final_time_s']:.3f} s"
        reproduced = True
        metric = float(summary["final_time_s"])
    elif not summary["completed_lap"]:
        signal = f"incomplete lap, progress={summary['final_progress_m']:.3f} m"
        reproduced = True
        metric = float(summary["final_progress_m"])
    elif float(summary["max_abs_cte_m"]) > 0.55:
        signal = f"max CTE {summary['max_abs_cte_m']:.3f} m"
        reproduced = True
        metric = float(summary["max_abs_cte_m"])
    elif float(summary["steering_effort_rad"]) > 14.0:
        signal = f"steering effort {summary['steering_effort_rad']:.3f} rad"
        reproduced = True
        metric = float(summary["steering_effort_rad"])
    else:
        signal = f"no failure, rms CTE={summary['rms_cte_m']:.3f} m"
        reproduced = False
        metric = float(summary["rms_cte_m"])
    return scenario_row(scenario, reproduced, signal, metric)


def run_saturation_case(conf: Namespace, waypoints: np.ndarray, scenario: FailureScenario) -> dict[str, object]:
    steer = float(DEFAULT_DYNAMIC_PARAMS["s_max"])
    controller = SaturatingSteerController(steer, speed_mps=4.0)
    _, summary = run_closed_loop(
        controller,
        conf,
        waypoints,
        integration_dt=INTEGRATION_DT_S,
        control_rate_hz=CONTROL_RATE_HZ,
        max_sim_time_s=8.0,
        run_id=scenario.scenario,
    )
    reproduced = bool(summary["collision"]) or float(summary["max_abs_command_steer_rad"]) >= 0.99 * steer
    signal = f"command steer dwell at limit {summary['max_abs_command_steer_rad']:.3f} rad"
    return scenario_row(scenario, reproduced, signal, float(summary["max_abs_command_steer_rad"]))


def ekf_failure_rows(scenarios: list[FailureScenario]) -> list[dict[str, object]]:
    summary = pd.read_csv(EKF_SUMMARY_PATH)
    pivot = summary.pivot(index="scenario", columns="estimator", values="position_rmse_m")
    rows = []
    for scenario in scenarios:
        if scenario.scenario == "sensor_noise_high":
            value = float(pivot.loc["high_noise", "ekf"])
            rows.append(scenario_row(scenario, value > 0.10, f"EKF high-noise position RMSE {value:.3f} m", value))
        if scenario.scenario == "measurement_dropout_3s":
            value = float(pivot.loc["dropout_3s", "ekf"])
            rows.append(scenario_row(scenario, value > 0.10, f"EKF dropout position RMSE {value:.3f} m", value))
    return rows


def markdown_table(frame: pd.DataFrame) -> str:
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: f"{value:.6g}")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---" for _ in display.columns]) + " |"]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
    return "\n".join(lines)


def create_figures(results: pd.DataFrame) -> None:
    ordered = results.sort_values("rpn", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.bar(ordered["scenario"], ordered["rpn"], color="#4c78a8")
    ax.set_ylabel("RPN")
    ax.set_title("Failure-Mode Risk Priority Number")
    ax.tick_params(axis="x", rotation=30)
    fig.savefig(RPN_FIGURE, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.bar(ordered["scenario"], ordered["detection_metric"], color="#f58518")
    ax.set_ylabel("Detection metric")
    ax.set_title("Failure Detection Signals")
    ax.tick_params(axis="x", rotation=30)
    fig.savefig(SIGNALS_FIGURE, dpi=200)
    plt.close(fig)


def write_report(results: pd.DataFrame) -> None:
    table = results.sort_values("rpn", ascending=False)[
        [
            "scenario",
            "category",
            "reproduced",
            "detection_signal",
            "severity_1_to_10",
            "occurrence_1_to_10",
            "detectability_1_to_10",
            "rpn",
            "mitigation",
        ]
    ]
    report = f"""# Failure-Mode FMEA

## Objective

Reproduce controller, estimator, numerical, latency, and actuator failures and document detection signals plus mitigations.

## FMEA Table

{markdown_table(table)}

## Figures

![FMEA RPN](figures/fmea_rpn_bar.png)

![FMEA detection signals](figures/fmea_detection_signals.png)
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    conf = load_config()
    waypoints = load_waypoints(conf)
    baseline = selected_baseline()
    scenarios = default_failure_scenarios()
    rows = []
    for scenario in scenarios:
        if scenario.category in {"noise", "dropout"}:
            continue
        if scenario.scenario == "steering_saturation":
            rows.append(run_saturation_case(conf, waypoints, scenario))
        else:
            rows.append(run_pp_case(conf, waypoints, scenario, baseline))
    rows.extend(ekf_failure_rows(scenarios))
    results = pd.DataFrame(rows)
    results.to_csv(RESULTS_PATH, index=False)
    create_figures(results)
    write_report(results)
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
