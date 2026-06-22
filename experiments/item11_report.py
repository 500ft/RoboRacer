#!/usr/bin/env python
"""Generate the committed item 11 report and steering-channel evidence figure."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = REPO_ROOT / "evidence" / "item11"


def metric_map(path: Path) -> dict[str, float]:
    frame = pd.read_csv(path)
    return {str(row.metric): float(row.value) for row in frame.itertuples(index=False)}


def main() -> None:
    enriched = pd.read_csv(EVIDENCE / "telemetry" / "enriched_bridge.csv")
    upstream = pd.read_csv(EVIDENCE / "telemetry" / "upstream_gym_ros.csv")
    preflight = json.loads((EVIDENCE / "metrics" / "enriched_preflight.json").read_text())
    enriched_meta = json.loads((EVIDENCE / "metrics" / "enriched_conversion_metadata.json").read_text())
    upstream_meta = json.loads((EVIDENCE / "metrics" / "upstream_conversion_metadata.json").read_text())
    enriched_fit = metric_map(EVIDENCE / "metrics" / "enriched_fit" / "metrics.csv")
    direct_fit = metric_map(REPO_ROOT / "runs" / "dynamic_parameter_identification" / "metrics.csv")

    figure_dir = EVIDENCE / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    axis.plot(enriched["time_s"], enriched["command_steer_rad"], label="Command", linewidth=1.0)
    axis.plot(enriched["time_s"], enriched["steer_rad"], label="Native achieved state", linewidth=1.0)
    axis.set_xlabel("Simulator time [s]")
    axis.set_ylabel("Steering angle [rad]")
    axis.set_title("Enriched ROS Bag: Command and Achieved Steering")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.savefig(figure_dir / "steering_command_vs_achieved.png", dpi=180)
    plt.close(fig)

    steering = preflight["metrics"]
    realized = upstream_meta["realized_frequency_band_sim_hz"]
    report = f"""# Item 11: ROS-Backed Pipeline Validation

## Result

Two genuine ROS 2 middleware recordings passed their source-specific gates:

- The project bridge supplied native achieved steering and recovered Gym's known `C_Sf` and `C_Sr` through the complete bag-to-fit pipeline.
- Stock `f1tenth_gym_ros` at `883394df0964c555ee05bea69c3002daf6f2d405` supplied only `/ego_racecar/odom` and `/drive`; it passed ingestion and excitation checks and was not used for parameter identification.

Raw bags were validated locally through deterministic ZIP, SHA-256, reconversion, and byte-identical telemetry checks. GitHub release publication remains pending; `bags/MANIFEST.yaml` intentionally contains no entries until the assets exist at their claimed URLs.

## Enriched Identification

| Metric | Direct Gym | ROS-backed enriched |
| --- | ---: | ---: |
| `C_Sf` | {direct_fit['fitted_C_Sf']:.9f} | {enriched_fit['fitted_C_Sf']:.9f} |
| `C_Sr` | {direct_fit['fitted_C_Sr']:.9f} | {enriched_fit['fitted_C_Sr']:.9f} |
| Normalized Jacobian condition | {direct_fit['jacobian_condition_number']:.3f} | {enriched_fit['jacobian_condition_number']:.3f} |
| Raw Jacobian condition | — | {enriched_fit['raw_jacobian_condition_number']:.3f} |
| Parameter correlation | — | {enriched_fit['parameter_correlation']:.3f} |
| Held-out yaw-rate RMSE | {direct_fit['heldout_rollout_yaw_rate_rmse']:.3e} rad/s | {enriched_fit['heldout_rollout_yaw_rate_rmse']:.3e} rad/s |

Primary held-out evidence duration was `{steering['heldout_duration_s']:.2f} s`. The `{int(steering['heldout_native_transitions'])}` native transitions are bookkeeping, not a claim of independent statistical samples.

## Steering Observability

The simulator has a two-sample command buffer and a bang-bang steering controller. It commands `±3.2 rad/s` whenever steering error exceeds `1e-4 rad`; this is not a second-order physical actuator model.

- Command/achieved RMSE: `{steering['command_achieved_rmse_rad']:.5f} rad`
- Maximum absolute difference: `{steering['command_achieved_max_abs_rad']:.5f} rad`
- Best command shift: `{int(steering['best_command_lag_samples'])}` samples (`{steering['best_command_lag_s']:.3f} s`)
- RMSE after that shift: `{steering['best_lag_rmse_rad']:.5f} rad`
- Achieved transitions at the rate limit: `{steering['steering_rate_limit_fraction']:.2%}`

The fit uses the raw native achieved state without smoothing or upsampling. This demonstrates correct transport and consumption of an achieved-steering channel in simulation; it does not validate a physical actuator.

![Command and achieved steering](figures/steering_command_vs_achieved.png)

## Timing and Topic Quality

| Source | Overlap | RTF | State/odom rate | Steering source | Collision |
| --- | ---: | ---: | ---: | --- | --- |
| Enriched bridge | {enriched_meta['required_topic_overlap_s']:.2f} s | {enriched_meta['real_time_factor']:.4f} | {enriched_meta['topic_diagnostics']['/f1tenth/internal_state']['observed_rate_hz']:.1f} Hz | internal state | observed false |
| Stock upstream | {upstream_meta['required_topic_overlap_s']:.2f} s | {upstream_meta['real_time_factor']:.4f} | {upstream_meta['topic_diagnostics']['/ego_racecar/odom']['observed_rate_hz']:.1f} Hz | command proxy | unobserved |

The enriched RTF comes from published simulator time. Upstream publishes odometry at 250 Hz while stepping Gym at 100 Hz, so its RTF proxy counts odometry state changes and multiplies by the audited 0.01 s simulation step. Its realized simulator-time chirp band was `{realized[0]:.3f}–{realized[1]:.3f} Hz`.

## Upstream Contract

All upstream gates use only odometry and drive data:

- command steering range: `{upstream['command_steer_rad'].max() - upstream['command_steer_rad'].min():.4f} rad`;
- yaw-rate response range: `{upstream['yaw_rate_radps'].max() - upstream['yaw_rate_radps'].min():.4f} rad/s`;
- speed coefficient of variation and topic timing from odometry;
- collision explicitly remains unobserved.

No upstream parameter fit is reported because achieved steering is unavailable.

## Reproduction

```bash
# Enriched capture
ros2 launch f1tenth_modeling item11_enriched_capture.launch.py
python experiments/rosbag_to_telemetry.py --bag <enriched-bag> \\
  --output evidence/item11/telemetry/enriched_bridge.csv \\
  --metadata evidence/item11/metrics/enriched_conversion_metadata.json \\
  --quality evidence/item11/metrics/enriched_quality.csv \\
  --sample-clock internal_state

# Stock upstream capture after sourcing the pinned upstream workspace
ros2 launch f1tenth_modeling item11_upstream_capture.launch.py
python experiments/rosbag_to_telemetry.py --bag <upstream-bag> \\
  --output evidence/item11/telemetry/upstream_gym_ros.csv \\
  --metadata evidence/item11/metrics/upstream_conversion_metadata.json \\
  --quality evidence/item11/metrics/upstream_quality.csv \\
  --sample-clock odom --sim-step-dt 0.01 \\
  --command-frequency-start 0.2 --command-frequency-end 2.0
```

## Scope

This is a controlled simulator-recovery and ROS-ingestion result. Physical `C_Sf`/`C_Sr`, actuator dynamics, and controller retuning remain gated on a calibrated hardware bag.
"""
    (EVIDENCE / "report.md").write_text(report, encoding="utf-8")
    print(f"Wrote {EVIDENCE / 'report.md'}")


if __name__ == "__main__":
    main()

