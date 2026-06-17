"""Numerical helpers shared by RoboRacer experiments."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd


def wrap_angle(angle: np.ndarray | float) -> np.ndarray | float:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def rmse(values: pd.Series | np.ndarray | Sequence[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(arr**2)))


def nrmse(error: np.ndarray | Sequence[float], measured: np.ndarray | Sequence[float]) -> float:
    signal_range = float(np.ptp(np.asarray(measured, dtype=float)))
    return rmse(error) / signal_range if signal_range > 0.0 else float("inf")


def vaf_percent(error: np.ndarray | Sequence[float], measured: np.ndarray | Sequence[float]) -> float:
    measured_variance = float(np.var(np.asarray(measured, dtype=float)))
    if measured_variance <= 0.0:
        return float("-inf")
    return 100.0 * (1.0 - float(np.var(np.asarray(error, dtype=float))) / measured_variance)


def validate_uniform_time(
    time_s: np.ndarray | Sequence[float],
    *,
    ratio_limit: float = 1.2,
    gap_factor_limit: float | None = None,
    context: str = "Telemetry",
) -> np.ndarray:
    dt = np.diff(np.asarray(time_s, dtype=float))
    if dt.size == 0:
        raise ValueError(f"{context} needs at least two samples.")
    if np.any(dt <= 0.0):
        raise ValueError(f"{context} time_s must be strictly increasing.")

    ratio = float(np.max(dt) / np.min(dt))
    dt_median = float(np.median(dt))
    if ratio > ratio_limit or (gap_factor_limit is not None and float(np.max(dt)) > gap_factor_limit * dt_median):
        raise ValueError(
            f"{context} dt is not sufficiently uniform: "
            f"dt_min={float(np.min(dt)):.9f}, dt_max={float(np.max(dt)):.9f}, ratio={ratio:.6f}"
        )
    return dt


def dt_summary(
    time_s: np.ndarray | Sequence[float],
    *,
    ratio_limit: float = 1.2,
    gap_factor_limit: float | None = None,
    context: str = "Telemetry",
) -> dict[str, float]:
    dt = validate_uniform_time(
        time_s,
        ratio_limit=ratio_limit,
        gap_factor_limit=gap_factor_limit,
        context=context,
    )
    return {
        "dt_min_s": float(np.min(dt)),
        "dt_max_s": float(np.max(dt)),
        "dt_mean_s": float(np.mean(dt)),
        "dt_median_s": float(np.median(dt)),
        "dt_ratio": float(np.max(dt) / np.min(dt)),
    }


def rk4_step(
    state: np.ndarray,
    dt: float,
    derivative: Callable[[np.ndarray], np.ndarray],
    *,
    angle_index: int | None = None,
) -> np.ndarray:
    k1 = derivative(state)
    k2 = derivative(state + 0.5 * dt * k1)
    k3 = derivative(state + 0.5 * dt * k2)
    k4 = derivative(state + dt * k3)
    next_state = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    if angle_index is not None:
        next_state[angle_index] = float(wrap_angle(next_state[angle_index]))
    return next_state

