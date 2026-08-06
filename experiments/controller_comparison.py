#!/usr/bin/env python
"""Build PP/LQR/MPC controller comparison report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PP_RESULTS = REPO_ROOT / "runs" / "pure_pursuit_sweep" / "results.csv"
LQR_RESULTS = REPO_ROOT / "runs" / "lqr_controller" / "results.csv"
MPC_RESULTS = REPO_ROOT / "runs" / "mpc_controller" / "results.csv"
RUN_DIR = REPO_ROOT / "runs" / "controller_comparison"
RESULTS_PATH = RUN_DIR / "results.csv"
REPORT_PATH = REPO_ROOT / "reports" / "controller_comparison.md"


def baseline_pp() -> dict[str, object]:
    row = pd.read_csv(PP_RESULTS).query("selected_baseline == True").iloc[0]
    return {
        "controller": "pure_pursuit",
        "case": "selected_baseline",
        "completed_lap": bool(row["completed_lap"]),
        "collision": bool(row["collision"]),
        "lap_time_s": float(row["lap_time_s"]),
        "rms_cte_m": float(row["rms_cte_m"]),
        "max_abs_cte_m": float(row["max_abs_cte_m"]),
        "steering_effort_rad": float(row["steering_effort_rad"]),
        "mean_abs_command_steer_rad": float(row["mean_abs_command_steer_rad"]),
        "max_abs_command_steer_rad": float(row["max_abs_command_steer_rad"]),
        "mpc_p95_solve_time_s": float("nan"),
        "mpc_meets_100hz_budget": "",
        "mpc_meets_50hz_budget": "",
    }


def lqr_nominal() -> dict[str, object]:
    row = pd.read_csv(LQR_RESULTS).query("case == 'nominal'").iloc[0]
    return {
        "controller": "lqr",
        "case": "nominal",
        "completed_lap": bool(row["completed_lap"]),
        "collision": bool(row["collision"]),
        "lap_time_s": float(row["lap_time_s"]),
        "rms_cte_m": float(row["rms_cte_m"]),
        "max_abs_cte_m": float(row["max_abs_cte_m"]),
        "steering_effort_rad": float(row["steering_effort_rad"]),
        "mean_abs_command_steer_rad": float(row["mean_abs_command_steer_rad"]),
        "max_abs_command_steer_rad": float(row["max_abs_command_steer_rad"]),
        "mpc_p95_solve_time_s": float("nan"),
        "mpc_meets_100hz_budget": "",
        "mpc_meets_50hz_budget": "",
    }


def mpc_nominal() -> dict[str, object]:
    row = pd.read_csv(MPC_RESULTS).iloc[0]
    return {
        "controller": "mpc",
        "case": "nominal",
        "completed_lap": bool(row["completed_lap"]),
        "collision": bool(row["collision"]),
        "lap_time_s": float(row["lap_time_s"]),
        "rms_cte_m": float(row["rms_cte_m"]),
        "max_abs_cte_m": float(row["max_abs_cte_m"]),
        "steering_effort_rad": float(row["steering_effort_rad"]),
        "mean_abs_command_steer_rad": float(row["mean_abs_command_steer_rad"]),
        "max_abs_command_steer_rad": float(row["max_abs_command_steer_rad"]),
        "mpc_p95_solve_time_s": float(row["mpc_p95_solve_time_s"]),
        "mpc_meets_100hz_budget": bool(row["mpc_meets_100hz_budget"]),
        "mpc_meets_50hz_budget": bool(row["mpc_meets_50hz_budget"]),
    }


def markdown_table(frame: pd.DataFrame) -> str:
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.6g}")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---" for _ in display.columns]) + " |"]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
    return "\n".join(lines)


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    comparison = pd.DataFrame([baseline_pp(), lqr_nominal(), mpc_nominal()])
    comparison.to_csv(RESULTS_PATH, index=False)
    report = f"""# Controller Comparison

## Objective

Compare tuned pure pursuit, LQR, and MPC under the same map, integration timestep, and 100 Hz controller update rate.

## Results

{markdown_table(comparison)}

## Notes

- Pure pursuit is the selected baseline from `reports/pure_pursuit_sweep.md`.
- LQR is the nominal case from `reports/lqr_controller.md`.
- MPC is the nominal constrained SLSQP controller from `reports/mpc_controller.md`.
- MPC runtime fields are only meaningful for the MPC row.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
