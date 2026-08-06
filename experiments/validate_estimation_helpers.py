#!/usr/bin/env python
"""Validate dead-reckoning and EKF helper behavior."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
GYM_ROOT = REPO_ROOT / "gym"
if str(GYM_ROOT) not in sys.path:
    sys.path.insert(0, str(GYM_ROOT))

from roboracer.estimation import ExtendedKalmanFilter, STATE_COLUMNS, dead_reckon_step
from roboracer.numerics import rmse, wrap_angle


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    dt = 0.02
    controls = [np.array([0.08, 0.0], dtype=float) for _ in range(200)]
    truth = [np.array([0.0, 0.0, 0.0, 2.0, 0.45], dtype=float)]
    for control in controls:
        current = truth[-1].copy()
        current[0] += current[3] * np.cos(current[2]) * dt
        current[1] += current[3] * np.sin(current[2]) * dt
        current[2] = float(wrap_angle(current[2] + current[4] * dt))
        truth.append(current)
    truth = np.asarray(truth)
    rng = np.random.default_rng(11)
    measurements = truth + rng.normal(scale=[0.03, 0.03, 0.01, 0.02, 0.02], size=truth.shape)

    dr = truth[0] + np.array([0.4, -0.3, 0.15, -0.15, -0.2], dtype=float)
    ekf = ExtendedKalmanFilter(
        state=dr.copy(),
        covariance=np.diag([0.25, 0.25, 0.05, 0.1, 0.1]),
        process_covariance=np.diag([1e-4, 1e-4, 1e-5, 1e-4, 1e-4]),
        measurement_covariance=np.diag([0.03**2, 0.03**2, 0.01**2, 0.02**2, 0.02**2]),
    )
    dr_states = [dr.copy()]
    ekf_states = [ekf.state.copy()]
    for idx, control in enumerate(controls):
        dr = dead_reckon_step(dr, control, dt)
        ekf.predict(control, dt)
        ekf.update({column: measurements[idx + 1, col_idx] for col_idx, column in enumerate(STATE_COLUMNS)})
        dr_states.append(dr.copy())
        ekf_states.append(ekf.state.copy())
        require(np.isfinite(ekf.covariance).all(), "EKF covariance contains non-finite values")
        require(np.allclose(ekf.covariance, ekf.covariance.T, atol=1e-10), "EKF covariance is not symmetric")
        require(-np.pi <= ekf.state[2] <= np.pi, "EKF heading is not wrapped")

    dr_states = np.asarray(dr_states)
    ekf_states = np.asarray(ekf_states)
    dr_position_rmse = rmse(np.hypot(dr_states[:, 0] - truth[:, 0], dr_states[:, 1] - truth[:, 1]))
    ekf_position_rmse = rmse(np.hypot(ekf_states[:, 0] - truth[:, 0], ekf_states[:, 1] - truth[:, 1]))
    require(ekf_position_rmse <= dr_position_rmse, "EKF did not improve over handicapped dead reckoning")
    print("estimation helper validation: PASS")


if __name__ == "__main__":
    main()
