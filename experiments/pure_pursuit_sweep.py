#!/usr/bin/env python
"""Sweep pure-pursuit lookahead and velocity gain at validated RK4 timestep."""

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

EXAMPLES_DIR = REPO_ROOT / "examples"
RUN_DIR = REPO_ROOT / "runs" / "pure_pursuit_sweep"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
REPORT_PATH = REPO_ROOT / "reports" / "pure_pursuit_sweep.md"
RESULTS_PATH = RUN_DIR / "results.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
CTE_HEATMAP_PATH = FIGURE_DIR / "pure_pursuit_sweep_rms_cte_heatmap.png"
LAP_TIME_HEATMAP_PATH = FIGURE_DIR / "pure_pursuit_sweep_lap_time_heatmap.png"
REGIONS_PATH = FIGURE_DIR / "pure_pursuit_sweep_regions.png"

INTEGRATION_DT_S = 0.002
CONTROL_RATE_HZ = 100.0
MAX_SIM_TIME_S = 45.0
LOOKAHEAD_VALUES_M = [0.4, 0.6, 0.8, 1.0, 1.2, 1.5]
VGAIN_VALUES = [0.8, 1.0, 1.2, 1.375, 1.6]
CORNER_CUTTING_CTE_M = 0.8


def load_config() -> Namespace:
    with (EXAMPLES_DIR / "config_example_map.yaml").open() as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    config["map_path"] = str((EXAMPLES_DIR / config["map_path"]).resolve())
    config["wpt_path"] = str((EXAMPLES_DIR / config["wpt_path"]).resolve())
    return Namespace(**config)


def load_waypoints(conf: Namespace) -> np.ndarray:
    return np.loadtxt(conf.wpt_path, delimiter=conf.wpt_delim, skiprows=conf.wpt_rowskip)


def classify(results: pd.DataFrame) -> pd.DataFrame:
    results = results.copy()
    completed = results[(results["completed_lap"] == True) & (results["collision"] == False)]  # noqa: E712
    effort_threshold = float(completed["steering_effort_rad"].quantile(0.75)) if not completed.empty else float("inf")
    labels = []
    for row in results.itertuples(index=False):
        if bool(row.collision):
            labels.append("collision")
        elif not bool(row.completed_lap):
            labels.append("incomplete")
        elif float(row.max_abs_cte_m) > CORNER_CUTTING_CTE_M:
            labels.append("corner_cutting")
        elif float(row.steering_effort_rad) > effort_threshold:
            labels.append("oscillatory")
        else:
            labels.append("stable")
    results["classification"] = labels
    results["weighted_score"] = (
        results["rms_cte_m"] + 0.25 * results["max_abs_cte_m"] + 0.05 * results["steering_effort_rad"]
    )
    return results


def select_baseline(results: pd.DataFrame) -> pd.Series:
    candidates = results[
        (results["completed_lap"] == True)  # noqa: E712
        & (results["collision"] == False)  # noqa: E712
        & (results["classification"] == "stable")
    ].copy()
    if candidates.empty:
        candidates = results[(results["completed_lap"] == True) & (results["collision"] == False)].copy()  # noqa: E712
    if candidates.empty:
        raise RuntimeError("No completed non-collision pure-pursuit run found; lower the speed sweep before continuing.")
    return candidates.sort_values("weighted_score").iloc[0]


def plot_heatmap(results: pd.DataFrame, value_column: str, output_path: Path, title: str, cbar_label: str) -> None:
    pivot = results.pivot(index="vgain", columns="lookahead_m", values=value_column).sort_index(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="viridis")
    ax.set_xticks(np.arange(len(pivot.columns)), [f"{value:.2g}" for value in pivot.columns])
    ax.set_yticks(np.arange(len(pivot.index)), [f"{value:.3g}" for value in pivot.index])
    ax.set_xlabel("Lookahead [m]")
    ax.set_ylabel("Velocity gain")
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label(cbar_label)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_regions(results: pd.DataFrame, output_path: Path) -> None:
    color_map = {
        "stable": "#2ca02c",
        "oscillatory": "#ff7f0e",
        "corner_cutting": "#9467bd",
        "collision": "#d62728",
        "incomplete": "#7f7f7f",
    }
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    for label, group in results.groupby("classification"):
        ax.scatter(
            group["lookahead_m"],
            group["vgain"],
            s=120,
            label=label,
            color=color_map.get(label, "black"),
            edgecolor="white",
            linewidth=0.8,
        )
    ax.set_xlabel("Lookahead [m]")
    ax.set_ylabel("Velocity gain")
    ax.set_title("Pure Pursuit Sweep Regions")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    display = frame[columns].copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: f"{value:.6g}")
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---" for _ in columns]) + " |"]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def write_report(results: pd.DataFrame, baseline: pd.Series) -> None:
    top = results[(results["completed_lap"] == True) & (results["collision"] == False)].sort_values("weighted_score").head(8)  # noqa: E712
    report = f"""# Pure Pursuit Sweep

## Objective

Tune pure pursuit over lookahead and velocity gain before comparing against LQR and MPC.

## Setup

- Integrator: RK4
- Integration timestep: `{INTEGRATION_DT_S:.3f} s`
- Controller update rate: `{CONTROL_RATE_HZ:.0f} Hz`
- Command hold: zero-order hold between controller updates
- Track: `examples/example_map`
- Lookahead values: `{LOOKAHEAD_VALUES_M}`
- Velocity gains: `{VGAIN_VALUES}`

## Recommended Baseline

Recommended baseline: **lookahead = {baseline["lookahead_m"]:.3f} m, vgain = {baseline["vgain"]:.3f}**.

Reason: this run completed without collision and had the lowest weighted score among stable candidates.

| Metric | Value |
| --- | ---: |
| Lap time | {baseline["lap_time_s"]:.6g} s |
| RMS CTE | {baseline["rms_cte_m"]:.6g} m |
| Max CTE | {baseline["max_abs_cte_m"]:.6g} m |
| Steering effort | {baseline["steering_effort_rad"]:.6g} rad |
| Weighted score | {baseline["weighted_score"]:.6g} |

## Top Completed Runs

{markdown_table(top, ["lookahead_m", "vgain", "lap_time_s", "rms_cte_m", "max_abs_cte_m", "steering_effort_rad", "weighted_score", "classification"])}

## Classification Rules

Priority order: collision, incomplete, corner cutting, oscillatory, stable.

- Corner cutting threshold: max CTE > `{CORNER_CUTTING_CTE_M:.3f} m`
- Oscillatory threshold: steering effort above the completed-run 75th percentile
- Weighted score: `rms_cte + 0.25 * max_cte + 0.05 * steering_effort`

These thresholds are map-specific heuristics intended to select a controller baseline, not universal stability criteria.

## Figures

![RMS CTE heatmap](figures/pure_pursuit_sweep_rms_cte_heatmap.png)

![Lap time heatmap](figures/pure_pursuit_sweep_lap_time_heatmap.png)

![Sweep regions](figures/pure_pursuit_sweep_regions.png)

## Outputs

- `runs/pure_pursuit_sweep/results.csv`
- `runs/pure_pursuit_sweep/metadata.json`
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    conf = load_config()
    waypoints = load_waypoints(conf)

    rows = []
    for lookahead_m in LOOKAHEAD_VALUES_M:
        for vgain in VGAIN_VALUES:
            controller = PurePursuitController(
                conf,
                lookahead_m=lookahead_m,
                vgain=vgain,
                name="pure_pursuit",
            )
            _, summary = run_closed_loop(
                controller,
                conf,
                waypoints,
                integration_dt=INTEGRATION_DT_S,
                control_rate_hz=CONTROL_RATE_HZ,
                max_sim_time_s=MAX_SIM_TIME_S,
                run_id=f"pp_l{lookahead_m:.3f}_g{vgain:.3f}",
            )
            summary.update({"lookahead_m": lookahead_m, "vgain": vgain})
            rows.append(summary)
            print(
                f"lookahead={lookahead_m:.3f} vgain={vgain:.3f} "
                f"termination={summary['termination_reason']} rms_cte={summary['rms_cte_m']:.3f}"
            )

    results = classify(pd.DataFrame(rows))
    baseline = select_baseline(results)
    results["selected_baseline"] = (results["lookahead_m"] == baseline["lookahead_m"]) & (results["vgain"] == baseline["vgain"])
    results.to_csv(RESULTS_PATH, index=False)
    METADATA_PATH.write_text(
        json.dumps(
            {
                "integration_dt_s": INTEGRATION_DT_S,
                "control_rate_hz": CONTROL_RATE_HZ,
                "lookahead_values_m": LOOKAHEAD_VALUES_M,
                "vgain_values": VGAIN_VALUES,
                "baseline": {"lookahead_m": float(baseline["lookahead_m"]), "vgain": float(baseline["vgain"])},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    plot_heatmap(results, "rms_cte_m", CTE_HEATMAP_PATH, "Pure Pursuit RMS CTE", "RMS CTE [m]")
    completed_lap_time = results.copy()
    completed_lap_time.loc[completed_lap_time["completed_lap"] != True, "lap_time_s"] = np.nan  # noqa: E712
    plot_heatmap(completed_lap_time, "lap_time_s", LAP_TIME_HEATMAP_PATH, "Pure Pursuit Lap Time", "Lap time [s]")
    plot_regions(results, REGIONS_PATH)
    write_report(results, baseline)

    print(f"Selected baseline: lookahead={baseline['lookahead_m']:.3f}, vgain={baseline['vgain']:.3f}")
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
