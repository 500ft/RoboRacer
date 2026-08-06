"""Telemetry loading helpers shared by replay and fitting scripts."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

import numpy as np
import pandas as pd

from roboracer.numerics import validate_uniform_time


def ensure_exists(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def require_columns(frame: pd.DataFrame, columns: Sequence[str], *, context: str = "Telemetry") -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{context} missing required columns: {missing}")


def coerce_numeric(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def load_rk4_telemetry(
    path: Path,
    *,
    required_columns: Sequence[str],
    numeric_columns: Sequence[str] | None = None,
    description: str = "telemetry",
) -> pd.DataFrame:
    ensure_exists(path, description)
    telemetry = pd.read_csv(path)
    require_columns(telemetry, required_columns, context="Telemetry")

    rk4 = telemetry[telemetry["integrator"].astype(str).str.lower().eq("rk4")].copy()
    if rk4.empty:
        raise ValueError("No RK4 telemetry rows found.")

    columns_to_coerce = list(numeric_columns or [column for column in required_columns if column != "integrator"])
    coerce_numeric(rk4, columns_to_coerce)
    return rk4.sort_values("time_s").reset_index(drop=True)


def validate_numeric_telemetry(
    telemetry: pd.DataFrame,
    *,
    required_columns: Sequence[str],
    context: str = "Telemetry",
    ratio_limit: float = 1.2,
) -> pd.DataFrame:
    require_columns(telemetry, required_columns, context=context)
    coerce_numeric(telemetry, required_columns)
    values = telemetry[list(required_columns)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{context} contains non-finite values.")

    telemetry = telemetry.sort_values("time_s").reset_index(drop=True)
    validate_uniform_time(telemetry["time_s"].to_numpy(dtype=float), ratio_limit=ratio_limit, context=context)
    return telemetry

