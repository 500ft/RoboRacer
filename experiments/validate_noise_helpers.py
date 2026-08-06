#!/usr/bin/env python
"""Validate deterministic measurement corruption helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.noise import DropoutWindow, NoiseSpec, apply_dropout_windows, apply_quantization, apply_sensor_noise


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    frame = pd.DataFrame(
        {
            "time_s": [0.0, 0.5, 1.0, 1.5],
            "x_m": [1.0, 2.0, 3.0, 4.0],
            "theta_rad": [0.1, 0.2, 0.3, 0.4],
        }
    )
    spec = NoiseSpec(std_by_column={"x_m": 0.1, "theta_rad": 0.01})
    noisy_a = apply_sensor_noise(frame, spec, seed=7)
    noisy_b = apply_sensor_noise(frame, spec, seed=7)
    require(len(noisy_a) == len(frame), "Noise helper changed row count")
    require({"meas_x_m", "meas_theta_rad"}.issubset(noisy_a.columns), "Missing meas_* columns")
    require(noisy_a[["meas_x_m", "meas_theta_rad"]].equals(noisy_b[["meas_x_m", "meas_theta_rad"]]), "Seeded noise is not deterministic")

    quantized = apply_quantization(noisy_a, {"x_m": 0.25})
    require(np.allclose((quantized["meas_x_m"] / 0.25).round(), quantized["meas_x_m"] / 0.25), "Quantization did not snap to grid")

    dropped = apply_dropout_windows(quantized, [DropoutWindow(0.5, 0.6, ("x_m",))])
    mask = (dropped["time_s"] >= 0.5) & (dropped["time_s"] <= 1.1)
    require(dropped.loc[mask, "meas_x_m"].isna().all(), "Dropout did not blank measurement rows")
    require(dropped.loc[mask, "x_m"].notna().all(), "Dropout modified ground truth")
    print("noise helper validation: PASS")


if __name__ == "__main__":
    main()
