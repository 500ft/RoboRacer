#!/usr/bin/env python
"""Evaluate dynamic-parameter identification under data-quality perturbations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.identification import (
    ACCEPTANCE_GATE_ORDER,
    ORACLE,
    acceptance,
    first_failed_gate,
    identify_from_telemetry,
    metric_dict,
    validate_identification_telemetry,
)

TELEMETRY_PATH = REPO_ROOT / "runs" / "sysid_steering_excitation" / "telemetry.csv"
RUN_DIR = REPO_ROOT / "runs" / "parameter_id_robustness"
FIGURE_DIR = REPO_ROOT / "reports" / "figures"
RESULTS_PATH = RUN_DIR / "results.csv"
METRICS_PATH = RUN_DIR / "metrics.csv"
METADATA_PATH = RUN_DIR / "metadata.json"
REPORT_PATH = REPO_ROOT / "reports" / "parameter_id_robustness.md"
NOISE_FIGURE = FIGURE_DIR / "parameter_id_noise_degradation.png"
LATENCY_FIGURE = FIGURE_DIR / "parameter_id_latency_degradation.png"
CONDITION_FIGURE = FIGURE_DIR / "parameter_id_condition_number.png"
SEED = 99


def load_telemetry() -> pd.DataFrame:
    return validate_identification_telemetry(pd.read_csv(TELEMETRY_PATH))


def add_noise(frame: pd.DataFrame, *, yaw_rate: float, speed: float, steer: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    output = frame.copy()
    output["yaw_rate_radps"] += rng.normal(0.0, yaw_rate, size=len(output))
    output["speed_mps"] += rng.normal(0.0, speed, size=len(output))
    output["steer_rad"] += rng.normal(0.0, steer, size=len(output))
    return output


def add_latency(frame: pd.DataFrame, *, latency_s: float) -> pd.DataFrame:
    output = frame.copy()
    dt = float(np.median(np.diff(output["time_s"].to_numpy(dtype=float))))
    samples = max(1, int(round(latency_s / dt)))
    for column in ("steer_vel_radps", "accel_x_mps2"):
        output[column] = output[column].shift(samples).bfill()
    return output


def add_quantization(frame: pd.DataFrame, *, yaw_rate: float, speed: float, steer: float, accel: float) -> pd.DataFrame:
    output = frame.copy()
    for column, step in {
        "yaw_rate_radps": yaw_rate,
        "speed_mps": speed,
        "steer_rad": steer,
        "accel_x_mps2": accel,
    }.items():
        output[column] = np.round(output[column].to_numpy(dtype=float) / step) * step
    return output


def perturbations() -> dict[str, dict[str, object]]:
    return {
        "nominal": {"kind": "nominal"},
        "noise_low": {"kind": "noise", "yaw_rate": 0.002, "speed": 0.005, "steer": 0.0005},
        "noise_medium": {"kind": "noise", "yaw_rate": 0.01, "speed": 0.02, "steer": 0.002},
        "noise_high": {"kind": "noise", "yaw_rate": 0.04, "speed": 0.08, "steer": 0.006},
        "latency_20ms": {"kind": "latency", "latency_s": 0.020},
        "latency_50ms": {"kind": "latency", "latency_s": 0.050},
        "latency_100ms": {"kind": "latency", "latency_s": 0.100},
        "quantization_low": {"kind": "quantization", "yaw_rate": 0.001, "speed": 0.002, "steer": 0.0005, "accel": 0.01},
        "quantization_medium": {"kind": "quantization", "yaw_rate": 0.005, "speed": 0.01, "steer": 0.002, "accel": 0.05},
        "quantization_high": {"kind": "quantization", "yaw_rate": 0.02, "speed": 0.05, "steer": 0.005, "accel": 0.15},
        "combined_medium": {"kind": "combined", "yaw_rate": 0.01, "speed": 0.02, "steer": 0.002, "latency_s": 0.050, "accel": 0.05},
    }


def apply_perturbation(frame: pd.DataFrame, name: str, config: dict[str, object]) -> pd.DataFrame:
    kind = str(config["kind"])
    if kind == "nominal":
        return frame.copy()
    if kind == "noise":
        return add_noise(
            frame,
            yaw_rate=float(config["yaw_rate"]),
            speed=float(config["speed"]),
            steer=float(config["steer"]),
            seed=SEED + len(name),
        )
    if kind == "latency":
        return add_latency(frame, latency_s=float(config["latency_s"]))
    if kind == "quantization":
        return add_quantization(
            frame,
            yaw_rate=float(config["yaw_rate"]),
            speed=float(config["speed"]),
            steer=float(config["steer"]),
            accel=float(config["accel"]),
        )
    if kind == "combined":
        noisy = add_noise(
            frame,
            yaw_rate=float(config["yaw_rate"]),
            speed=float(config["speed"]),
            steer=float(config["steer"]),
            seed=SEED + len(name),
        )
        delayed = add_latency(noisy, latency_s=float(config["latency_s"]))
        return add_quantization(
            delayed,
            yaw_rate=float(config["yaw_rate"]),
            speed=float(config["speed"]),
            steer=float(config["steer"]),
            accel=float(config["accel"]),
        )
    raise ValueError(f"Unknown perturbation kind: {kind}")


def result_row(name: str, config: dict[str, object], metrics: pd.DataFrame, nominal_values: dict[str, float]) -> dict[str, object]:
    values = metric_dict(metrics)
    checks = acceptance(metrics)
    c_sf_error = abs(values["fitted_C_Sf"] - ORACLE[0]) / ORACLE[0]
    c_sr_error = abs(values["fitted_C_Sr"] - ORACLE[1]) / ORACLE[1]
    nominal_c_sf_error = max(nominal_values["C_Sf_oracle_relative_error"], 1e-15)
    nominal_c_sr_error = max(nominal_values["C_Sr_oracle_relative_error"], 1e-15)
    nominal_condition = max(nominal_values["jacobian_condition_number"], 1e-15)
    row = {
        "scenario": name,
        "kind": config["kind"],
        "fitted_C_Sf": values["fitted_C_Sf"],
        "fitted_C_Sr": values["fitted_C_Sr"],
        "C_Sf_oracle_relative_error": c_sf_error,
        "C_Sr_oracle_relative_error": c_sr_error,
        "C_Sf_error_growth_vs_nominal": c_sf_error / nominal_c_sf_error,
        "C_Sr_error_growth_vs_nominal": c_sr_error / nominal_c_sr_error,
        "jacobian_condition_number": values["jacobian_condition_number"],
        "condition_growth_vs_nominal": values["jacobian_condition_number"] / nominal_condition,
        "heldout_rollout_yaw_rate_rmse": values["heldout_rollout_yaw_rate_rmse"],
        "heldout_rollout_slip_angle_rmse": values["heldout_rollout_slip_angle_rmse"],
        "acceptance_passed": bool(all(checks.values())),
        "first_failed_gate": first_failed_gate(checks),
    }
    for gate in ACCEPTANCE_GATE_ORDER:
        row[f"gate_{gate}"] = bool(checks[gate])
    return row


def plot_by_kind(results: pd.DataFrame, kind: str, output_path: Path, title: str) -> None:
    subset = results[results["kind"].isin(["nominal", kind])]
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.plot(subset["scenario"], subset["C_Sf_oracle_relative_error"], marker="o", label="C_Sf error")
    ax.plot(subset["scenario"], subset["C_Sr_oracle_relative_error"], marker="o", label="C_Sr error")
    ax.set_ylabel("Oracle relative error")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_condition(results: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.bar(results["scenario"], results["jacobian_condition_number"], color="#4c78a8")
    ax.set_ylabel("Jacobian condition number")
    ax.set_title("Parameter-ID Conditioning Under Perturbations")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(True, axis="y", alpha=0.25)
    fig.savefig(CONDITION_FIGURE, dpi=200)
    plt.close(fig)


def markdown_table(frame: pd.DataFrame) -> str:
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: f"{value:.6g}")
    lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---" for _ in display.columns]) + " |"]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
    return "\n".join(lines)


def write_report(results: pd.DataFrame) -> None:
    compact = results[
        [
            "scenario",
            "kind",
            "fitted_C_Sf",
            "fitted_C_Sr",
            "C_Sf_oracle_relative_error",
            "C_Sr_oracle_relative_error",
            "jacobian_condition_number",
            "acceptance_passed",
            "first_failed_gate",
        ]
    ]
    degradation = results[
        [
            "scenario",
            "C_Sf_error_growth_vs_nominal",
            "C_Sr_error_growth_vs_nominal",
            "condition_growth_vs_nominal",
            "heldout_rollout_yaw_rate_rmse",
            "heldout_rollout_slip_angle_rmse",
        ]
    ]
    gates = results[
        [
            "scenario",
            "gate_oracle_recovery",
            "gate_heldout_yaw_rate",
            "gate_heldout_slip_angle",
            "gate_heldout_yaw",
            "gate_heldout_normalized_fit",
            "gate_heldout_variance_accounted_for",
            "gate_identifiability",
        ]
    ]
    failed = results[results["acceptance_passed"] == False]  # noqa: E712
    failure_sentence = (
        f"First failed perturbation: `{failed.iloc[0]['scenario']}` at gate `{failed.iloc[0]['first_failed_gate']}`."
        if not failed.empty
        else "All tested perturbation levels passed the current acceptance gates; degradation is reported as trend data."
    )
    report = f"""# Parameter-ID Robustness

## Objective

Re-run `C_Sf`/`C_Sr` identification under injected sensor noise, input latency, quantization, and a combined medium perturbation.

## Results

{markdown_table(compact)}

{failure_sentence}

## Degradation

{markdown_table(degradation)}

## Acceptance Gates

{markdown_table(gates)}

## Figures

![Noise degradation](figures/parameter_id_noise_degradation.png)

![Latency degradation](figures/parameter_id_latency_degradation.png)

![Condition number](figures/parameter_id_condition_number.png)
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    telemetry = load_telemetry()
    rows = []
    metrics_frames = []
    nominal_values: dict[str, float] | None = None
    configs = perturbations()
    for name, config in configs.items():
        perturbed = apply_perturbation(telemetry, name, config)
        identified = identify_from_telemetry(perturbed, repo_root=REPO_ROOT)
        metrics = identified.metrics.copy()
        metrics.insert(0, "scenario", name)
        metrics_frames.append(metrics)
        values = metric_dict(identified.metrics)
        if name == "nominal":
            nominal_values = values
        assert nominal_values is not None
        rows.append(result_row(name, config, identified.metrics, nominal_values))
        print(f"{name}: C_Sf={values['fitted_C_Sf']:.6f} C_Sr={values['fitted_C_Sr']:.6f}")
    results = pd.DataFrame(rows)
    metrics_long = pd.concat(metrics_frames, ignore_index=True)
    results.to_csv(RESULTS_PATH, index=False)
    metrics_long.to_csv(METRICS_PATH, index=False)
    METADATA_PATH.write_text(json.dumps({"seed": SEED, "perturbations": configs}, indent=2) + "\n", encoding="utf-8")
    plot_by_kind(results, "noise", NOISE_FIGURE, "Noise Robustness")
    plot_by_kind(results, "latency", LATENCY_FIGURE, "Latency Robustness")
    plot_condition(results)
    write_report(results)
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
