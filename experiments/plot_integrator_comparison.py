#!/usr/bin/env python
"""Plot the first RK4 vs Euler integrator comparison."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = REPO_ROOT / "runs" / "first_lap" / "telemetry.csv"
FIGURE_PATH = REPO_ROOT / "reports" / "figures" / "first_integrator_comparison.png"
TITLE = "First Dynamics Sanity Check: RK4 vs Euler Trajectory Overlay"


def final_summary(group: pd.DataFrame) -> pd.Series:
    final = group.iloc[-1]
    return pd.Series(
        {
            "lap_time_s": float(final["lap_time_s"]),
            "collision": int(final["collision"]),
            "termination_reason": final["termination_reason"],
            "rms_cte_m": float((group["cte_m"] ** 2).mean() ** 0.5),
            "max_abs_cte_m": float(group["abs_cte_m"].max()),
            "mean_speed_mps": float(group["speed_mps"].mean()),
        }
    )


def main() -> None:
    if not TELEMETRY_PATH.exists():
        raise FileNotFoundError(f"Telemetry not found: {TELEMETRY_PATH}")

    df = pd.read_csv(TELEMETRY_PATH)
    summary = df.groupby("integrator", sort=False).apply(final_summary)

    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.35, 1.0]})
    fig.suptitle(TITLE, fontsize=14, fontweight="bold")

    ax = axes[0]
    for integrator, group in df.groupby("integrator", sort=False):
        ax.plot(group["x_m"], group["y_m"], linewidth=1.8, label=integrator.upper())
        ax.scatter(group["x_m"].iloc[0], group["y_m"].iloc[0], s=28)
    ax.set_xlabel("x position (m)")
    ax.set_ylabel("y position (m)")
    ax.set_title("Trajectory Overlay")
    ax.axis("equal")
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = axes[1]
    metrics = summary[["lap_time_s", "rms_cte_m", "max_abs_cte_m", "mean_speed_mps"]]
    normalized = metrics / metrics.max(axis=0).replace(0, 1)
    normalized.plot(kind="bar", ax=ax, width=0.75)
    ax.set_title("Normalized Summary Metrics")
    ax.set_ylabel("relative value")
    ax.set_ylim(0, 1.15)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8)

    text_lines = ["Summary"]
    for integrator, row in summary.iterrows():
        text_lines.append(
            f"{integrator.upper()}: lap={row.lap_time_s:.2f}s, "
            f"collision={int(row.collision)}, rms_cte={row.rms_cte_m:.3f}m, "
            f"max_cte={row.max_abs_cte_m:.3f}m, mean_v={row.mean_speed_mps:.2f}m/s, "
            f"end={row.termination_reason}"
        )
    fig.text(0.08, 0.01, "\n".join(text_lines), fontsize=9, va="bottom")
    fig.tight_layout(rect=[0, 0.12, 1, 0.93])
    fig.savefig(FIGURE_PATH, dpi=180)
    print(f"Wrote {FIGURE_PATH}")


if __name__ == "__main__":
    main()
