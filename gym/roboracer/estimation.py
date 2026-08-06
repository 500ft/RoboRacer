"""Dead-reckoning and EKF utilities for RoboRacer robustness studies."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, tan
from collections.abc import Sequence

import numpy as np

from roboracer.closed_loop import WHEELBASE_M
from roboracer.dynamics import DEFAULT_DYNAMIC_PARAMS
from roboracer.numerics import rmse, wrap_angle


STATE_COLUMNS = ("x_m", "y_m", "theta_rad", "speed_mps", "yaw_rate_radps")


def angle_residual(value: float, reference: float) -> float:
    return float(wrap_angle(value - reference))


def finite_difference_jacobian(fn, x: np.ndarray, eps: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    eps = np.asarray(eps, dtype=float)
    base = np.asarray(fn(x), dtype=float)
    jac = np.zeros((base.size, x.size), dtype=float)
    for idx in range(x.size):
        step = np.zeros_like(x)
        step[idx] = eps[idx]
        plus = np.asarray(fn(x + step), dtype=float)
        minus = np.asarray(fn(x - step), dtype=float)
        jac[:, idx] = (plus - minus) / (2.0 * eps[idx])
    return jac


def dead_reckon_step(
    state: np.ndarray,
    control: np.ndarray,
    dt: float,
    params: dict[str, float] | None = None,
) -> np.ndarray:
    params = params or DEFAULT_DYNAMIC_PARAMS
    x, y, theta, speed, yaw_rate = np.asarray(state, dtype=float)
    steer = float(control[0])
    accel = float(control[1])
    wheelbase = float(params.get("lf", WHEELBASE_M / 2.0) + params.get("lr", WHEELBASE_M / 2.0))
    target_yaw_rate = speed * tan(steer) / max(wheelbase, 1e-6)
    tau = 0.08
    next_state = np.array(
        [
            x + speed * cos(theta) * dt,
            y + speed * np.sin(theta) * dt,
            theta + yaw_rate * dt,
            speed + accel * dt,
            yaw_rate + (target_yaw_rate - yaw_rate) * dt / tau,
        ],
        dtype=float,
    )
    next_state[2] = float(wrap_angle(next_state[2]))
    return next_state


@dataclass
class ExtendedKalmanFilter:
    state: np.ndarray
    covariance: np.ndarray
    process_covariance: np.ndarray
    measurement_covariance: np.ndarray
    params: dict[str, float] | None = None

    def predict(self, control: np.ndarray, dt: float) -> np.ndarray:
        eps = np.array([1e-4, 1e-4, 1e-5, 1e-4, 1e-5], dtype=float)

        def transition(candidate: np.ndarray) -> np.ndarray:
            return dead_reckon_step(candidate, control, dt, self.params)

        f = finite_difference_jacobian(transition, self.state, eps)
        self.state = transition(self.state)
        self.covariance = f @ self.covariance @ f.T + self.process_covariance
        self.covariance = 0.5 * (self.covariance + self.covariance.T)
        return self.state

    def update(self, measurement: dict[str, float]) -> np.ndarray:
        available = [
            idx
            for idx, column in enumerate(STATE_COLUMNS)
            if column in measurement and np.isfinite(float(measurement[column]))
        ]
        if not available:
            return self.state
        h = np.zeros((len(available), len(STATE_COLUMNS)), dtype=float)
        z = np.zeros(len(available), dtype=float)
        predicted = np.zeros(len(available), dtype=float)
        for row, state_idx in enumerate(available):
            h[row, state_idx] = 1.0
            column = STATE_COLUMNS[state_idx]
            z[row] = float(measurement[column])
            predicted[row] = self.state[state_idx]
        residual = z - predicted
        for row, state_idx in enumerate(available):
            if STATE_COLUMNS[state_idx] == "theta_rad":
                residual[row] = angle_residual(z[row], predicted[row])
        r = self.measurement_covariance[np.ix_(available, available)]
        s = h @ self.covariance @ h.T + r
        k = self.covariance @ h.T @ np.linalg.inv(s)
        self.state = self.state + k @ residual
        self.state[2] = float(wrap_angle(self.state[2]))
        identity = np.eye(len(STATE_COLUMNS))
        self.covariance = (identity - k @ h) @ self.covariance @ (identity - k @ h).T + k @ r @ k.T
        self.covariance = 0.5 * (self.covariance + self.covariance.T)
        return self.state


def position_rmse(x_error: Sequence[float], y_error: Sequence[float]) -> float:
    return rmse(np.hypot(np.asarray(x_error, dtype=float), np.asarray(y_error, dtype=float)))
