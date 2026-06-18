"""Controllers and linear models used by RoboRacer experiments."""

from __future__ import annotations

import time
from argparse import Namespace
from dataclasses import dataclass, field
from math import atan

import numpy as np
from scipy.linalg import solve_discrete_are
from scipy.optimize import Bounds, LinearConstraint, minimize

from roboracer.closed_loop import WHEELBASE_M
from roboracer.dynamics import DEFAULT_DYNAMIC_PARAMS
from roboracer.numerics import wrap_angle
from roboracer.track import PurePursuitPlanner


def clamp(value: float, low: float, high: float) -> float:
    return float(np.clip(value, low, high))


class PurePursuitController:
    def __init__(self, conf: Namespace, *, lookahead_m: float, vgain: float, name: str | None = None):
        self.name = name or "pure_pursuit"
        self.lookahead_m = float(lookahead_m)
        self.vgain = float(vgain)
        self.planner = PurePursuitPlanner(conf, WHEELBASE_M)

    def reset(self) -> None:
        return None

    def command(self, state: dict[str, float], path_info: dict[str, float]) -> tuple[float, float]:
        speed, steer = self.planner.plan(
            state["x_m"],
            state["y_m"],
            state["theta_rad"],
            self.lookahead_m,
            self.vgain,
        )
        return steer, speed


@dataclass
class LinearPathModel:
    control_dt_s: float
    v0_mps: float
    kappa0_1pm: float
    q_diag: np.ndarray
    r_diag: np.ndarray
    params: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_DYNAMIC_PARAMS))

    def __post_init__(self) -> None:
        self.q = np.diag(self.q_diag)
        self.r = np.diag(self.r_diag)
        self.a_c, self.b_c = self._continuous_matrices()
        self.a_d = np.eye(6) + self.control_dt_s * self.a_c
        self.b_d = self.control_dt_s * self.b_c
        self.p = solve_discrete_are(self.a_d, self.b_d, self.q, self.r)
        self.k = np.linalg.solve(self.r + self.b_d.T @ self.p @ self.b_d, self.b_d.T @ self.p @ self.a_d)
        self.closed_loop_eigenvalues = np.linalg.eigvals(self.a_d - self.b_d @ self.k)

    def _continuous_matrices(self) -> tuple[np.ndarray, np.ndarray]:
        v0 = max(float(self.v0_mps), 0.75)
        lr = self.params["lr"]
        lf = self.params["lf"]
        c_sf = self.params["C_Sf"]
        c_sr = self.params["C_Sr"]
        mass = self.params["m"]
        inertia = self.params["I"]
        a = np.zeros((6, 6), dtype=float)
        b = np.zeros((6, 2), dtype=float)

        # e_y_dot ~= v * e_psi
        a[0, 1] = v0
        # e_psi_dot = yaw_rate - v*kappa0
        a[1, 3] = -self.kappa0_1pm
        a[1, 4] = 1.0
        # steer_dot = steering-rate command
        b[2, 0] = 1.0
        # speed_dot = acceleration command
        b[3, 1] = 1.0
        # Linear bicycle yaw/slip dynamics around small angles.
        a[4, 2] = lf * c_sf / inertia
        a[4, 4] = -((lf**2) * c_sf + (lr**2) * c_sr) / (inertia * v0)
        a[4, 5] = (-lf * c_sf + lr * c_sr) / inertia
        a[5, 2] = c_sf / (mass * v0)
        a[5, 4] = (-lf * c_sf + lr * c_sr) / (mass * v0**2) - 1.0
        a[5, 5] = -(c_sf + c_sr) / (mass * v0)
        return a, b

    def error_state(self, state: dict[str, float], path_info: dict[str, float], target_speed_mps: float) -> np.ndarray:
        local_kappa = float(path_info.get("path_curvature_1pm", self.kappa0_1pm))
        feedforward_steer = atan(WHEELBASE_M * local_kappa)
        return np.array(
            [
                path_info["cte_m"],
                wrap_angle(state["theta_rad"] - path_info["path_heading_rad"]),
                state["steer_rad"] - feedforward_steer,
                state["speed_mps"] - target_speed_mps,
                state["yaw_rate_radps"] - state["speed_mps"] * local_kappa,
                state["slip_angle_rad"],
            ],
            dtype=float,
        )


class LQRController:
    def __init__(
        self,
        model: LinearPathModel,
        *,
        target_speed_mps: float,
        feedforward_controller: PurePursuitController | None = None,
        max_steer_correction_rad: float = 0.005,
        name: str = "lqr",
    ):
        self.name = name
        self.model = model
        self.target_speed_mps = float(target_speed_mps)
        self.feedforward_controller = feedforward_controller
        self.max_steer_correction_rad = float(max_steer_correction_rad)
        self.desired_steer_rad = 0.0
        self.desired_speed_delta_mps = 0.0

    def reset(self) -> None:
        self.desired_steer_rad = 0.0
        self.desired_speed_delta_mps = 0.0
        if self.feedforward_controller is not None:
            self.feedforward_controller.reset()

    def control(self, state: dict[str, float], path_info: dict[str, float]) -> np.ndarray:
        x_err = self.model.error_state(state, path_info, self.target_speed_mps)
        return -self.model.k @ x_err

    def command(self, state: dict[str, float], path_info: dict[str, float]) -> tuple[float, float]:
        u = self.control(state, path_info)
        params = self.model.params
        if self.feedforward_controller is None:
            feedforward_steer = atan(WHEELBASE_M * float(path_info.get("path_curvature_1pm", self.model.kappa0_1pm)))
            feedforward_speed = self.target_speed_mps
        else:
            feedforward_steer, feedforward_speed = self.feedforward_controller.command(state, path_info)
        steer_rate = clamp(u[0], params["sv_min"], params["sv_max"])
        accel = clamp(u[1], -params["a_max"], params["a_max"])
        self.desired_steer_rad = clamp(
            self.desired_steer_rad + steer_rate * self.model.control_dt_s,
            -self.max_steer_correction_rad,
            self.max_steer_correction_rad,
        )
        self.desired_speed_delta_mps = clamp(
            self.desired_speed_delta_mps + accel * self.model.control_dt_s,
            -1.0,
            1.0,
        )
        return (
            clamp(feedforward_steer + self.desired_steer_rad, params["s_min"], params["s_max"]),
            clamp(feedforward_speed + self.desired_speed_delta_mps, params["v_min"], params["v_max"]),
        )


class MPCController:
    def __init__(
        self,
        model: LinearPathModel,
        *,
        target_speed_mps: float,
        horizon: int = 15,
        feedforward_controller: PurePursuitController | None = None,
        max_steer_correction_rad: float = 0.005,
        name: str = "mpc",
    ):
        self.name = name
        self.model = model
        self.target_speed_mps = float(target_speed_mps)
        self.horizon = int(horizon)
        self.feedforward_controller = feedforward_controller
        self.max_steer_correction_rad = float(max_steer_correction_rad)
        self.desired_steer_rad = 0.0
        self.desired_speed_delta_mps = 0.0
        self.last_solution = np.zeros((self.horizon, 2), dtype=float)
        self.solve_times_s: list[float] = []
        self.success_flags: list[bool] = []

    def reset(self) -> None:
        self.desired_steer_rad = 0.0
        self.desired_speed_delta_mps = 0.0
        self.last_solution = np.zeros((self.horizon, 2), dtype=float)
        self.solve_times_s = []
        self.success_flags = []
        if self.feedforward_controller is not None:
            self.feedforward_controller.reset()

    def _cost_and_grad(self, z: np.ndarray, x0: np.ndarray) -> tuple[float, np.ndarray]:
        u_seq = z.reshape(self.horizon, 2)
        x = x0.copy()
        states = []
        for u in u_seq:
            x = self.model.a_d @ x + self.model.b_d @ u
            states.append(x)
        qf = 5.0 * self.model.q
        cost = 0.0
        for idx, (x_state, u) in enumerate(zip(states, u_seq)):
            q = qf if idx == self.horizon - 1 else self.model.q
            cost += float(x_state.T @ q @ x_state + u.T @ self.model.r @ u)

        grad = np.zeros_like(u_seq)
        lam = 2.0 * qf @ states[-1]
        grad[-1] = 2.0 * self.model.r @ u_seq[-1] + self.model.b_d.T @ lam
        for idx in range(self.horizon - 2, -1, -1):
            lam = 2.0 * self.model.q @ states[idx] + self.model.a_d.T @ lam
            grad[idx] = 2.0 * self.model.r @ u_seq[idx] + self.model.b_d.T @ lam
        return cost, grad.ravel()

    def _rate_constraint(self) -> LinearConstraint:
        n = self.horizon * 2
        rows = []
        lower = []
        upper = []
        for idx in range(self.horizon - 1):
            row = np.zeros(n)
            row[(idx + 1) * 2] = 1.0
            row[idx * 2] = -1.0
            rows.append(row)
            limit = self.model.params["sv_max"]
            lower.append(-limit)
            upper.append(limit)
        if not rows:
            return LinearConstraint(np.zeros((1, n)), [0.0], [0.0])
        return LinearConstraint(np.vstack(rows), np.asarray(lower), np.asarray(upper))

    def command(self, state: dict[str, float], path_info: dict[str, float]) -> tuple[float, float]:
        x_err = self.model.error_state(state, path_info, self.target_speed_mps)
        params = self.model.params
        if self.feedforward_controller is None:
            feedforward_steer = atan(WHEELBASE_M * float(path_info.get("path_curvature_1pm", self.model.kappa0_1pm)))
            feedforward_speed = self.target_speed_mps
        else:
            feedforward_steer, feedforward_speed = self.feedforward_controller.command(state, path_info)
        z0 = np.vstack([self.last_solution[1:], self.last_solution[-1:]]).ravel()
        bounds = Bounds(
            np.tile([params["sv_min"], -params["a_max"]], self.horizon),
            np.tile([params["sv_max"], params["a_max"]], self.horizon),
        )
        start = time.perf_counter()
        result = minimize(
            lambda z: self._cost_and_grad(z, x_err),
            z0,
            jac=True,
            method="SLSQP",
            bounds=bounds,
            constraints=[self._rate_constraint()],
            options={"maxiter": 40, "ftol": 1e-4, "disp": False},
        )
        self.solve_times_s.append(time.perf_counter() - start)
        self.success_flags.append(bool(result.success))
        solution = result.x.reshape(self.horizon, 2) if result.success else z0.reshape(self.horizon, 2)
        self.last_solution = solution
        steer_rate = clamp(solution[0, 0], params["sv_min"], params["sv_max"])
        accel = clamp(solution[0, 1], -params["a_max"], params["a_max"])
        self.desired_steer_rad = clamp(
            self.desired_steer_rad + steer_rate * self.model.control_dt_s,
            -self.max_steer_correction_rad,
            self.max_steer_correction_rad,
        )
        self.desired_speed_delta_mps = clamp(
            self.desired_speed_delta_mps + accel * self.model.control_dt_s,
            -1.0,
            1.0,
        )
        return (
            clamp(feedforward_steer + self.desired_steer_rad, params["s_min"], params["s_max"]),
            clamp(feedforward_speed + self.desired_speed_delta_mps, params["v_min"], params["v_max"]),
        )

    def runtime_summary(self) -> dict[str, float | bool]:
        if not self.solve_times_s:
            return {
                "mpc_solve_count": 0,
                "mpc_mean_solve_time_s": float("nan"),
                "mpc_p95_solve_time_s": float("nan"),
                "mpc_max_solve_time_s": float("nan"),
                "mpc_success_fraction": float("nan"),
                "mpc_meets_100hz_budget": False,
                "mpc_meets_50hz_budget": False,
            }
        times = np.asarray(self.solve_times_s, dtype=float)
        p95 = float(np.percentile(times, 95))
        return {
            "mpc_solve_count": int(len(times)),
            "mpc_mean_solve_time_s": float(np.mean(times)),
            "mpc_p95_solve_time_s": p95,
            "mpc_max_solve_time_s": float(np.max(times)),
            "mpc_success_fraction": float(np.mean(self.success_flags)),
            "mpc_meets_100hz_budget": bool(p95 <= 0.010),
            "mpc_meets_50hz_budget": bool(p95 <= 0.020),
        }
