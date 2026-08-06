"""Vehicle model helpers shared by RoboRacer replay and sysID scripts."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np

from roboracer.numerics import rk4_step, wrap_angle

DEFAULT_DYNAMIC_PARAMS = {
    "mu": 1.0489,
    "C_Sf": 4.718,
    "C_Sr": 5.4562,
    "lf": 0.15875,
    "lr": 0.17145,
    "h": 0.074,
    "m": 3.74,
    "I": 0.04712,
    "s_min": -0.4189,
    "s_max": 0.4189,
    "sv_min": -3.2,
    "sv_max": 3.2,
    "v_switch": 7.319,
    "a_max": 9.51,
    "v_min": -5.0,
    "v_max": 20.0,
}


def install_numba_stub_if_missing() -> None:
    if importlib.util.find_spec("numba") is not None:
        return

    numba_stub = types.ModuleType("numba")

    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]

        def decorator(func):
            return func

        return decorator

    numba_stub.njit = njit
    sys.modules["numba"] = numba_stub


def load_vehicle_dynamics_st(repo_root: Path, *, module_name: str = "roboracer_dynamic_models"):
    install_numba_stub_if_missing()
    path = repo_root / "gym" / "f110_gym" / "envs" / "dynamic_models.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load dynamic model source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.vehicle_dynamics_st


def dynamic_derivative(
    vehicle_dynamics_st,
    state: np.ndarray,
    control: np.ndarray,
    params: dict[str, float],
    *,
    coefficients: np.ndarray | None = None,
) -> np.ndarray:
    c_sf = float(coefficients[0]) if coefficients is not None else params["C_Sf"]
    c_sr = float(coefficients[1]) if coefficients is not None else params["C_Sr"]
    return vehicle_dynamics_st(
        state,
        control,
        params["mu"],
        c_sf,
        c_sr,
        params["lf"],
        params["lr"],
        params["h"],
        params["m"],
        params["I"],
        params["s_min"],
        params["s_max"],
        params["sv_min"],
        params["sv_max"],
        params["v_switch"],
        params["a_max"],
        params["v_min"],
        params["v_max"],
    )


def dynamic_rk4_step(
    vehicle_dynamics_st,
    state: np.ndarray,
    control: np.ndarray,
    dt: float,
    params: dict[str, float],
    *,
    coefficients: np.ndarray | None = None,
) -> np.ndarray:
    return rk4_step(
        state,
        dt,
        lambda candidate: dynamic_derivative(
            vehicle_dynamics_st,
            candidate,
            control,
            params,
            coefficients=coefficients,
        ),
        angle_index=4,
    )


def kinematic_yaw_rate(speed: np.ndarray, steer: np.ndarray, *, lf: float, lr: float) -> np.ndarray:
    beta = np.arctan((lr / (lf + lr)) * np.tan(steer))
    return (speed / lr) * np.sin(beta)


def kinematic_bicycle_derivative(state: np.ndarray, accel: float, steer: float, *, lf: float, lr: float) -> np.ndarray:
    x, y, psi, velocity = state
    beta = np.arctan((lr / (lf + lr)) * np.tan(steer))
    return np.array(
        [
            velocity * np.cos(psi + beta),
            velocity * np.sin(psi + beta),
            (velocity / lr) * np.sin(beta),
            accel,
        ],
        dtype=float,
    )


def kinematic_bicycle_rk4_step(
    state: np.ndarray,
    accel: float,
    steer: float,
    dt: float,
    *,
    lf: float,
    lr: float,
) -> np.ndarray:
    return rk4_step(
        state,
        dt,
        lambda candidate: kinematic_bicycle_derivative(candidate, accel, steer, lf=lf, lr=lr),
        angle_index=2,
    )

