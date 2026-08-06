#!/usr/bin/env python
"""Create a report-quality RK4 vs Euler integrator sensitivity figure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

TELEMETRY_PATH = REPO_ROOT / "runs" / "first_lap" / "telemetry.csv"
METADATA_PATH = REPO_ROOT / "runs" / "first_lap" / "metadata.json"
CONFIG_PATH = REPO_ROOT / "examples" / "config_example_map.yaml"
WAYPOINTS_PATH = REPO_ROOT / "examples" / "example_waypoints.csv"
COMBINED_PATH = REPO_ROOT / "reports" / "figures" / "first_integrator_comparison.png"
TRAJECTORY_PATH = REPO_ROOT / "reports" / "figures" / "integrator_trajectory_overlay.png"
TRACKING_ERROR_PATH = REPO_ROOT / "reports" / "figures" / "integrator_tracking_error_vs_progress.png"
SUMMARY_METRICS_PATH = REPO_ROOT / "reports" / "figures" / "integrator_summary_metrics.png"
SUMMARY_TITLE = "Summary Metrics"


def ensure_exists(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def load_metadata(path: Path) -> dict[str, Any]:
    ensure_exists(path, "metadata file")
    with path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)
    if not isinstance(metadata, dict):
        raise ValueError(f"Metadata did not load as a dictionary: {path}")
    return metadata


def load_telemetry(path: Path) -> pd.DataFrame:
    ensure_exists(path, "telemetry file")
    df = pd.read_csv(path)
    required = [
        "integrator",
        "time_s",
        "x_m",
        "y_m",
        "speed_mps",
        "cte_m",
        "abs_cte_m",
        "progress_m",
        "collision",
        "termination_reason",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            f"Telemetry missing required columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    for column in ["time_s", "x_m", "y_m", "speed_mps", "cte_m", "abs_cte_m", "progress_m", "collision"]:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df["integrator"] = df["integrator"].astype(str)
    return df


def load_map_config(path: Path) -> dict[str, Any]:
    ensure_exists(path, "map config")
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError(f"Map config did not load as a dictionary: {path}")
    return config


def config_value(config: dict[str, Any], candidates: list[str]) -> Any | None:
    lower_map = {str(key).lower(): value for key, value in config.items()}
    for key in candidates:
        if key.lower() in lower_map:
            return lower_map[key.lower()]
    return None


def normalize_delimiter(delimiter: Any | None) -> str | None:
    if delimiter is None:
        return None
    value = str(delimiter)
    if value.lower() in {"whitespace", "space", r"\s+", "regex_whitespace"}:
        return r"\s+"
    return value


def read_waypoint_csv(path: Path, delimiter_hint: Any | None) -> tuple[pd.DataFrame, bool]:
    delimiter = normalize_delimiter(delimiter_hint)
    f1tenth_style = False

    with path.open("r", encoding="utf-8") as file:
        first_data_line = ""
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            first_data_line = stripped
            break

    if not first_data_line:
        raise ValueError(f"Waypoint file has no data rows after comments: {path}")

    if delimiter is None:
        delimiter = ";" if ";" in first_data_line else None
    if delimiter == ";":
        f1tenth_style = True

    read_kwargs: dict[str, Any] = {"comment": "#"}
    if delimiter == r"\s+":
        read_kwargs.update({"sep": delimiter, "engine": "python"})
    elif delimiter is not None:
        read_kwargs["sep"] = delimiter

    # F1TENTH waypoint examples are comment-headered and data-only; keep the
    # first numeric row as data instead of accidentally treating it as headers.
    if f1tenth_style:
        waypoint_df = pd.read_csv(path, header=None, **read_kwargs)
        waypoint_df.columns = list(range(waypoint_df.shape[1]))
        return waypoint_df, True

    waypoint_df = pd.read_csv(path, **read_kwargs)
    if waypoint_df.shape[1] >= 2:
        return waypoint_df, False

    waypoint_df = pd.read_csv(path, header=None, **read_kwargs)
    waypoint_df.columns = list(range(waypoint_df.shape[1]))
    return waypoint_df, False


def load_waypoints(path: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, bool]:
    ensure_exists(path, "waypoint file")
    delimiter_hint = config_value(
        config,
        [
            "wpt_delim",
            "waypoint_delimiter",
            "waypoints_delimiter",
            "waypoint_sep",
            "waypoints_sep",
            "csv_delimiter",
            "delimiter",
            "sep",
        ],
    )
    waypoints, f1tenth_style = read_waypoint_csv(path, delimiter_hint)
    if waypoints.shape[1] < 2:
        raise ValueError(
            f"Waypoint file has fewer than 2 columns after parsing: {path}\n"
            f"Columns found: {list(waypoints.columns)}"
        )
    return waypoints, f1tenth_style


def infer_xy_columns(waypoints: pd.DataFrame, config: dict[str, Any], f1tenth_style: bool) -> tuple[Any, Any]:
    x_hint = config_value(config, ["wpt_xind", "waypoint_x_col", "x_col", "x_column", "waypoints_x_col", "waypoints_x"])
    y_hint = config_value(config, ["wpt_yind", "waypoint_y_col", "y_col", "y_column", "waypoints_y_col", "waypoints_y"])

    if x_hint is not None and y_hint is not None:
        x_column = int(x_hint) if f1tenth_style and str(x_hint).isdigit() else x_hint
        y_column = int(y_hint) if f1tenth_style and str(y_hint).isdigit() else y_hint
        if x_column in waypoints.columns and y_column in waypoints.columns:
            return x_column, y_column
        raise ValueError(
            "Waypoint x/y columns were specified in config but were not found in CSV.\n"
            f"x_hint={x_hint}, y_hint={y_hint}, available={list(waypoints.columns)}"
        )

    possible_x = ["x", "x_m", "pos_x", "waypoint_x", "x_pos"]
    possible_y = ["y", "y_m", "pos_y", "waypoint_y", "y_pos"]
    cols_lower = {str(column).lower(): column for column in waypoints.columns}

    for x_name in possible_x:
        for y_name in possible_y:
            if x_name in cols_lower and y_name in cols_lower:
                return cols_lower[x_name], cols_lower[y_name]

    numeric_cols = list(waypoints.select_dtypes(include=[np.number]).columns)
    if f1tenth_style and len(numeric_cols) >= 3:
        # Known F1TENTH format: s, x, y, psi, kappa, vx, ax.
        return numeric_cols[1], numeric_cols[2]

    raise ValueError(
        "Could not infer waypoint x/y columns from CSV or config.\n"
        f"Available columns: {list(waypoints.columns)}"
    )


def summarize_run(telemetry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for integrator, group in telemetry.groupby("integrator"):
        group = group.sort_values("time_s").reset_index(drop=True)
        collision = bool(pd.to_numeric(group["collision"], errors="coerce").fillna(0).max() > 0)
        termination_series = group["termination_reason"].dropna()
        termination = str(termination_series.iloc[-1]) if not termination_series.empty else "unknown"

        rows.append(
            {
                "Integrator": str(integrator).upper(),
                "Termination": termination,
                "Final time [s]": float(group["time_s"].iloc[-1]),
                "Collision": collision,
                "RMS CTE [m]": float(np.sqrt(np.mean(group["cte_m"] ** 2))),
                "Max CTE [m]": float(group["abs_cte_m"].max()),
                "Mean speed [m/s]": float(group["speed_mps"].mean()),
            }
        )

    summary = pd.DataFrame(rows)
    order = ["RK4", "EULER"]
    if not summary.empty:
        summary["order"] = summary["Integrator"].map(lambda value: order.index(value) if value in order else 999)
        summary = summary.sort_values("order").drop(columns="order").reset_index(drop=True)
    return summary


def trajectory_group(telemetry: pd.DataFrame, integrator: str) -> pd.DataFrame:
    group = telemetry[telemetry["integrator"].str.lower() == integrator].sort_values("time_s")
    if group.empty:
        raise ValueError(f"No {integrator.upper()} rows found in telemetry.")
    return group


def format_summary_for_table(summary: pd.DataFrame) -> pd.DataFrame:
    table_df = summary.copy()
    for column in ["Final time [s]", "RMS CTE [m]", "Max CTE [m]", "Mean speed [m/s]"]:
        table_df[column] = table_df[column].map(lambda value: f"{value:.3f}")
    table_df["Collision"] = table_df["Collision"].map(lambda value: "Yes" if value else "No")
    table_df["Termination"] = table_df["Termination"].map(lambda value: str(value).replace("completed_lap", "completed"))
    return table_df.rename(
        columns={
            "Integrator": "Int.",
            "Termination": "End",
            "Final time [s]": "Final\nTime [s]",
            "Collision": "Hit?",
            "RMS CTE [m]": "RMS\nCTE [m]",
            "Max CTE [m]": "Max\nCTE [m]",
            "Mean speed [m/s]": "Mean\nSpeed [m/s]",
        }
    )


def endpoint_label(group: pd.DataFrame, integrator: str) -> str:
    end = group.iloc[-1]
    collision = bool(pd.to_numeric(group["collision"], errors="coerce").fillna(0).max() > 0)
    termination = str(end["termination_reason"])
    if collision:
        return f"{integrator} collision"
    return f"{integrator} {termination.replace('_', ' ')}"


def endpoint_annotation(group: pd.DataFrame, integrator: str) -> str:
    end = group.iloc[-1]
    return (
        f"{endpoint_label(group, integrator)}\n"
        f"t = {end['time_s']:.2f} s\n"
        f"s = {end['progress_m']:.1f} m"
    )


def save_trajectory_overlay(
    waypoints: pd.DataFrame,
    x_col: Any,
    y_col: Any,
    rk4: pd.DataFrame,
    euler: pd.DataFrame,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)

    ax.plot(
        waypoints[x_col],
        waypoints[y_col],
        linestyle="--",
        linewidth=1.8,
        color="0.55",
        label="Reference path",
        zorder=1,
    )
    ax.plot(rk4["x_m"], rk4["y_m"], linewidth=2.3, color="#1f77b4", label="RK4 trajectory", zorder=2)
    ax.plot(euler["x_m"], euler["y_m"], linewidth=2.3, color="#d62728", label="Euler trajectory", zorder=2)

    start = rk4.iloc[0]
    rk4_finish = rk4.iloc[-1]
    euler_end = euler.iloc[-1]
    euler_label = endpoint_label(euler, "Euler")

    ax.scatter(start["x_m"], start["y_m"], marker="o", s=85, color="#2ca02c", label="Start", zorder=3)
    ax.scatter(
        rk4_finish["x_m"],
        rk4_finish["y_m"],
        marker="s",
        s=85,
        color="#1f77b4",
        label="RK4 finish",
        zorder=3,
    )
    ax.scatter(
        euler_end["x_m"],
        euler_end["y_m"],
        marker="x",
        s=140,
        linewidths=2.6,
        color="#d62728",
        label=euler_label,
        zorder=4,
    )

    ax.annotate(
        "Start / RK4 finish",
        xy=(start["x_m"], start["y_m"]),
        xytext=(-125, 18),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "0.25"},
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.8", "alpha": 0.85},
    )
    ax.annotate(
        endpoint_annotation(euler, "Euler"),
        xy=(euler_end["x_m"], euler_end["y_m"]),
        xytext=(18, -42),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#d62728"},
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.8", "alpha": 0.9},
    )

    ax.set_title("Trajectory Overlay")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.axis("equal")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", framealpha=0.95)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_tracking_error_plot(rk4: pd.DataFrame, euler: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.8), constrained_layout=True)
    euler_end = euler.iloc[-1]
    euler_label = endpoint_label(euler, "Euler")

    ax.plot(rk4["progress_m"], rk4["abs_cte_m"], linewidth=2.2, color="#1f77b4", label="RK4")
    ax.plot(euler["progress_m"], euler["abs_cte_m"], linewidth=2.2, color="#d62728", label="Euler")
    ax.scatter(
        euler_end["progress_m"],
        euler_end["abs_cte_m"],
        marker="x",
        s=110,
        linewidths=2.4,
        color="#d62728",
        label=euler_label,
        zorder=4,
    )
    ax.annotate(
        f"{euler_label}\n"
        f"t = {euler_end['time_s']:.2f} s",
        xy=(euler_end["progress_m"], euler_end["abs_cte_m"]),
        xytext=(-110, -58),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#d62728"},
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.8", "alpha": 0.9},
    )

    ax.set_title("Tracking Error vs Progress")
    ax.set_xlabel("Progress along path [m]")
    ax.set_ylabel("|CTE| [m]")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0.0, framealpha=0.95)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_summary_metrics_table(summary: pd.DataFrame, output_path: Path) -> None:
    table_df = format_summary_for_table(summary)
    fig, ax = plt.subplots(figsize=(12, 3.8), constrained_layout=True)
    ax.axis("off")

    col_widths = [0.12, 0.2, 0.13, 0.11, 0.13, 0.13, 0.18]
    table = ax.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        loc="center",
        cellLoc="center",
        colLoc="center",
        colWidths=col_widths,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 2.0)

    for (row, _), cell in table.get_celld().items():
        cell.set_edgecolor("0.25")
        if row == 0:
            cell.set_facecolor("0.92")
            cell.set_text_props(weight="bold")

    ax.set_title(SUMMARY_TITLE, fontsize=16, fontweight="bold", pad=18)
    fig.text(
        0.5,
        0.04,
        "Closed-loop pure pursuit integrator sensitivity check inside F1TENTH Gym.",
        ha="center",
        fontsize=10,
    )
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_combined_integrator_comparison(
    waypoints: pd.DataFrame,
    x_col: Any,
    y_col: Any,
    rk4: pd.DataFrame,
    euler: pd.DataFrame,
    summary: pd.DataFrame,
    output_path: Path,
) -> None:
    fig = plt.figure(figsize=(16, 9), constrained_layout=False)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.45, 1.0], height_ratios=[1.0, 1.0], wspace=0.28, hspace=0.36)
    ax_traj = fig.add_subplot(grid[:, 0])
    ax_cte = fig.add_subplot(grid[0, 1])
    ax_table = fig.add_subplot(grid[1, 1])

    start = rk4.iloc[0]
    rk4_finish = rk4.iloc[-1]
    euler_end = euler.iloc[-1]
    euler_label = endpoint_label(euler, "Euler")

    ax_traj.plot(
        waypoints[x_col],
        waypoints[y_col],
        linestyle="--",
        linewidth=1.6,
        color="0.55",
        label="Reference path",
        zorder=1,
    )
    ax_traj.plot(rk4["x_m"], rk4["y_m"], linewidth=2.2, color="#1f77b4", label="RK4 trajectory", zorder=2)
    ax_traj.plot(euler["x_m"], euler["y_m"], linewidth=2.2, color="#d62728", label="Euler trajectory", zorder=2)
    ax_traj.scatter(start["x_m"], start["y_m"], marker="o", s=80, color="#2ca02c", label="Start", zorder=3)
    ax_traj.scatter(
        rk4_finish["x_m"],
        rk4_finish["y_m"],
        marker="s",
        s=80,
        color="#1f77b4",
        label="RK4 finish",
        zorder=3,
    )
    ax_traj.scatter(
        euler_end["x_m"],
        euler_end["y_m"],
        marker="x",
        s=130,
        linewidths=2.5,
        color="#d62728",
        label=euler_label,
        zorder=4,
    )
    ax_traj.annotate(
        "Start / RK4 finish",
        xy=(start["x_m"], start["y_m"]),
        xytext=(-125, 20),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "0.25"},
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.8", "alpha": 0.88},
    )
    ax_traj.annotate(
        endpoint_annotation(euler, "Euler"),
        xy=(euler_end["x_m"], euler_end["y_m"]),
        xytext=(16, -40),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#d62728"},
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.8", "alpha": 0.9},
    )
    ax_traj.set_title("Trajectory Overlay")
    ax_traj.set_xlabel("x [m]")
    ax_traj.set_ylabel("y [m]")
    ax_traj.axis("equal")
    ax_traj.grid(True, alpha=0.3)
    ax_traj.legend(loc="upper right", framealpha=0.95)

    ax_cte.plot(rk4["progress_m"], rk4["abs_cte_m"], linewidth=2.0, color="#1f77b4", label="RK4")
    ax_cte.plot(euler["progress_m"], euler["abs_cte_m"], linewidth=2.0, color="#d62728", label="Euler")
    ax_cte.scatter(
        euler_end["progress_m"],
        euler_end["abs_cte_m"],
        marker="x",
        s=95,
        linewidths=2.2,
        color="#d62728",
        label=euler_label,
        zorder=4,
    )
    ax_cte.set_title("Tracking Error vs Progress")
    ax_cte.set_xlabel("Progress along path [m]")
    ax_cte.set_ylabel("|CTE| [m]")
    ax_cte.set_xlim(left=0)
    ax_cte.set_ylim(bottom=0)
    ax_cte.grid(True, alpha=0.3)
    ax_cte.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0.0, framealpha=0.95)

    table_df = format_summary_for_table(summary)
    ax_table.axis("off")
    table = ax_table.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        loc="center",
        cellLoc="center",
        colLoc="center",
        colWidths=[0.11, 0.17, 0.14, 0.10, 0.14, 0.14, 0.20],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.2)
    table.scale(1.0, 1.65)
    for (row, _), cell in table.get_celld().items():
        cell.set_edgecolor("0.25")
        if row == 0:
            cell.set_facecolor("0.92")
            cell.set_text_props(weight="bold")
    ax_table.set_title("Summary Metrics", fontsize=14, fontweight="bold", pad=12)

    fig.suptitle(
        "First Dynamics Sanity Check: RK4 vs Euler Trajectory Overlay",
        fontsize=18,
        fontweight="bold",
        y=0.975,
    )
    fig.text(
        0.5,
        0.018,
        "Closed-loop pure pursuit integrator sensitivity check inside F1TENTH Gym. "
        "This is not yet a derived bicycle-model comparison.",
        ha="center",
        fontsize=10,
    )
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_integrator_comparison(
    telemetry: pd.DataFrame,
    waypoints: pd.DataFrame,
    config: dict[str, Any],
    f1tenth_style_waypoints: bool,
) -> None:
    x_col, y_col = infer_xy_columns(waypoints, config, f1tenth_style_waypoints)
    print(f"Using waypoint columns: x={x_col}, y={y_col}")

    rk4 = trajectory_group(telemetry, "rk4")
    euler = trajectory_group(telemetry, "euler")
    summary = summarize_run(telemetry)

    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "legend.fontsize": 10,
        }
    )

    TRAJECTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_combined_integrator_comparison(waypoints, x_col, y_col, rk4, euler, summary, COMBINED_PATH)
    save_trajectory_overlay(waypoints, x_col, y_col, rk4, euler, TRAJECTORY_PATH)
    save_tracking_error_plot(rk4, euler, TRACKING_ERROR_PATH)
    save_summary_metrics_table(summary, SUMMARY_METRICS_PATH)


def main() -> None:
    metadata = load_metadata(METADATA_PATH)
    telemetry = load_telemetry(TELEMETRY_PATH)
    config = load_map_config(CONFIG_PATH)
    waypoints, f1tenth_style_waypoints = load_waypoints(WAYPOINTS_PATH, config)
    print(f"Loaded metadata for control={metadata.get('control', 'unknown')}")

    plot_integrator_comparison(
        telemetry=telemetry,
        waypoints=waypoints,
        config=config,
        f1tenth_style_waypoints=f1tenth_style_waypoints,
    )
    print(f"Wrote combined figure to {COMBINED_PATH}")
    print(f"Wrote trajectory figure to {TRAJECTORY_PATH}")
    print(f"Wrote tracking error figure to {TRACKING_ERROR_PATH}")
    print(f"Wrote summary metrics figure to {SUMMARY_METRICS_PATH}")


if __name__ == "__main__":
    main()
