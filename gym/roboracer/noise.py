"""Measurement corruption helpers for robustness studies."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class NoiseSpec:
    std_by_column: dict[str, float] = field(default_factory=dict)
    bias_by_column: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class DropoutWindow:
    start_s: float
    duration_s: float
    columns: tuple[str, ...] | None = None

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


def make_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(int(seed))


def measurement_name(column: str) -> str:
    return column if column.startswith("meas_") else f"meas_{column}"


def measurement_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column.startswith("meas_")]


def apply_sensor_noise(frame: pd.DataFrame, spec: NoiseSpec, *, seed: int) -> pd.DataFrame:
    output = frame.copy()
    rng = make_rng(seed)
    for column in sorted(set(spec.std_by_column) | set(spec.bias_by_column)):
        if column not in frame.columns:
            raise KeyError(f"Noise column not present in frame: {column}")
        meas_column = measurement_name(column)
        std = float(spec.std_by_column.get(column, 0.0))
        bias = float(spec.bias_by_column.get(column, 0.0))
        noise = rng.normal(loc=bias, scale=std, size=len(frame)) if std > 0.0 else bias
        output[meas_column] = frame[column].to_numpy(dtype=float) + noise
    return output


def apply_dropout_windows(frame: pd.DataFrame, windows: list[DropoutWindow]) -> pd.DataFrame:
    output = frame.copy()
    if "time_s" not in output.columns:
        raise KeyError("Dropout windows require time_s.")
    for window in windows:
        columns = list(window.columns) if window.columns is not None else measurement_columns(output)
        meas_columns = [measurement_name(column) for column in columns]
        missing = [column for column in meas_columns if column not in output.columns]
        if missing:
            raise KeyError(f"Dropout measurement columns not present: {missing}")
        mask = (output["time_s"].to_numpy(dtype=float) >= window.start_s) & (
            output["time_s"].to_numpy(dtype=float) <= window.end_s
        )
        output.loc[mask, meas_columns] = np.nan
    return output


def apply_quantization(frame: pd.DataFrame, steps: dict[str, float]) -> pd.DataFrame:
    output = frame.copy()
    for column, step in steps.items():
        if step <= 0.0:
            raise ValueError(f"Quantization step must be positive for {column}.")
        source = measurement_name(column) if measurement_name(column) in output.columns else column
        if source not in output.columns:
            raise KeyError(f"Quantization column not present in frame: {column}")
        target = measurement_name(column)
        values = output[source].to_numpy(dtype=float)
        output[target] = np.round(values / float(step)) * float(step)
    return output
