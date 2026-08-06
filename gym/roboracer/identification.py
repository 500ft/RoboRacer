"""Reusable dynamic-parameter identification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from roboracer.dynamics import DEFAULT_DYNAMIC_PARAMS, dynamic_rk4_step, load_vehicle_dynamics_st
from roboracer.numerics import nrmse, rmse, vaf_percent, wrap_angle
from roboracer.telemetry import validate_numeric_telemetry


TRAIN_FRACTION = 0.70
DYNAMIC_REGIME_MIN_SPEED_MPS = 0.75
LOWER_BOUND = np.array([0.1, 0.1], dtype=float)
UPPER_BOUND = np.array([20.0, 20.0], dtype=float)
INITIAL_GUESS = np.array([3.0, 3.0], dtype=float)
ORACLE = np.array([4.718, 5.4562], dtype=float)
PARAMS = DEFAULT_DYNAMIC_PARAMS

REQUIRED_COLUMNS = [
    "time_s",
    "x_m",
    "y_m",
    "steer_rad",
    "speed_mps",
    "theta_rad",
    "yaw_rate_radps",
    "slip_angle_rad",
    "steer_vel_radps",
    "accel_x_mps2",
]

ACCEPTANCE_LIMITS = {
    "max_oracle_relative_error_fraction": 0.10,
    "max_heldout_rollout_yaw_rate_rmse_radps": 0.01,
    "max_heldout_rollout_slip_angle_rmse_rad": 0.001,
    "max_heldout_rollout_yaw_rmse_rad": 0.01,
    "max_heldout_rollout_yaw_rate_nrmse": 0.10,
    "min_heldout_rollout_yaw_rate_vaf_percent": 95.0,
    "max_jacobian_condition_number": 100.0,
    "max_parameter_correlation_abs": 0.95,
}

ACCEPTANCE_GATE_ORDER = [
    "oracle_recovery",
    "heldout_yaw_rate",
    "heldout_slip_angle",
    "heldout_yaw",
    "heldout_normalized_fit",
    "heldout_variance_accounted_for",
    "identifiability",
    "parameter_correlation",
]


@dataclass
class IdentificationResult:
    coefficients: np.ndarray
    metrics: pd.DataFrame
    fit_trace: pd.DataFrame
    validation_trace: pd.DataFrame
    acceptance_checks: dict[str, bool]
    acceptance_limits: dict[str, float]
    optimizer_success: bool
    optimizer_message: str
    optimizer_cost: float
    optimizer_evaluations: int
    jacobian_condition_number: float
    raw_jacobian_condition_number: float
    parameter_correlation: float
    sensitivity_column_cosine: float
    train_intervals: int
    heldout_intervals: int
    split_interval: int


def validate_identification_telemetry(telemetry: pd.DataFrame) -> pd.DataFrame:
    return validate_numeric_telemetry(telemetry, required_columns=REQUIRED_COLUMNS, context="Telemetry", ratio_limit=1.2)


def state_matrix(telemetry: pd.DataFrame) -> np.ndarray:
    return telemetry[
        [
            "x_m",
            "y_m",
            "steer_rad",
            "speed_mps",
            "theta_rad",
            "yaw_rate_radps",
            "slip_angle_rad",
        ]
    ].to_numpy(dtype=float)


def input_matrix(telemetry: pd.DataFrame) -> np.ndarray:
    return telemetry[["steer_vel_radps", "accel_x_mps2"]].to_numpy(dtype=float)


def split_intervals(states: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    usable = np.flatnonzero(states[:-1, 3] >= DYNAMIC_REGIME_MIN_SPEED_MPS)
    if len(usable) < 100:
        raise ValueError("Not enough dynamic-regime intervals for fitting and validation.")
    split_position = int(TRAIN_FRACTION * len(usable))
    split_interval = int(usable[split_position])
    train = usable[usable < split_interval]
    heldout = usable[usable >= split_interval]
    if len(train) == 0 or len(heldout) == 0:
        raise ValueError("Chronological train/held-out split produced an empty partition.")
    return train, heldout, split_interval


def _rk4_step(
    vehicle_dynamics_st,
    state: np.ndarray,
    control: np.ndarray,
    dt: float,
    coefficients: np.ndarray,
) -> np.ndarray:
    return dynamic_rk4_step(
        vehicle_dynamics_st,
        state,
        control,
        dt,
        PARAMS,
        coefficients=coefficients,
    )


def one_step_predictions(
    vehicle_dynamics_st,
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    intervals: np.ndarray,
    coefficients: np.ndarray,
) -> np.ndarray:
    return np.array(
        [
            _rk4_step(vehicle_dynamics_st, states[index], controls[index + 1], dt[index], coefficients)
            for index in intervals
        ]
    )


def fit_coefficients(
    vehicle_dynamics_st,
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    train: np.ndarray,
) -> tuple[np.ndarray, object, np.ndarray]:
    targets = states[train + 1][:, [5, 6]]
    scales = np.std(targets, axis=0)
    if np.any(scales <= 0.0):
        raise ValueError("Training response lacks variation required for identification.")

    def residual(log_coefficients: np.ndarray) -> np.ndarray:
        predicted = one_step_predictions(
            vehicle_dynamics_st,
            states,
            controls,
            dt,
            train,
            np.exp(log_coefficients),
        )[:, [5, 6]]
        return ((predicted - targets) / scales).ravel()

    result = least_squares(
        residual,
        np.log(INITIAL_GUESS),
        bounds=(np.log(LOWER_BOUND), np.log(UPPER_BOUND)),
        xtol=1e-13,
        ftol=1e-13,
        gtol=1e-13,
        max_nfev=1000,
    )
    if not result.success:
        raise RuntimeError(f"Parameter fit failed: {result.message}")
    return np.exp(result.x), result, scales


def build_fit_trace(
    vehicle_dynamics_st,
    telemetry: pd.DataFrame,
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    train: np.ndarray,
    heldout: np.ndarray,
    coefficients: np.ndarray,
) -> pd.DataFrame:
    intervals = np.concatenate([train, heldout])
    predictions = one_step_predictions(vehicle_dynamics_st, states, controls, dt, intervals, coefficients)
    targets = states[intervals + 1]
    partitions = np.where(np.isin(intervals, train), "train", "heldout")
    return pd.DataFrame(
        {
            "interval_start_index": intervals,
            "partition": partitions,
            "time_s": telemetry.loc[intervals + 1, "time_s"].to_numpy(dtype=float),
            "speed_mps": states[intervals, 3],
            "steer_rad": states[intervals, 2],
            "input_steer_vel_radps": controls[intervals + 1, 0],
            "input_accel_x_mps2": controls[intervals + 1, 1],
            "measured_yaw_rate_radps": targets[:, 5],
            "predicted_yaw_rate_radps": predictions[:, 5],
            "yaw_rate_residual_radps": predictions[:, 5] - targets[:, 5],
            "measured_slip_angle_rad": targets[:, 6],
            "predicted_slip_angle_rad": predictions[:, 6],
            "slip_angle_residual_rad": predictions[:, 6] - targets[:, 6],
        }
    )


def heldout_rollout(
    vehicle_dynamics_st,
    telemetry: pd.DataFrame,
    states: np.ndarray,
    controls: np.ndarray,
    dt: np.ndarray,
    split_interval: int,
    coefficients: np.ndarray,
) -> pd.DataFrame:
    predicted = np.zeros((len(states) - split_interval, states.shape[1]), dtype=float)
    predicted[0] = states[split_interval]
    for output_index, interval in enumerate(range(split_interval, len(states) - 1)):
        predicted[output_index + 1] = _rk4_step(
            vehicle_dynamics_st,
            predicted[output_index],
            controls[interval + 1],
            float(dt[interval]),
            coefficients,
        )

    measured = states[split_interval:]
    error = predicted - measured
    error[:, 4] = wrap_angle(error[:, 4])
    position_error = np.linalg.norm(error[:, :2], axis=1)
    return pd.DataFrame(
        {
            "time_s": telemetry.loc[split_interval:, "time_s"].to_numpy(dtype=float),
            "measured_x_m": measured[:, 0],
            "predicted_x_m": predicted[:, 0],
            "measured_y_m": measured[:, 1],
            "predicted_y_m": predicted[:, 1],
            "position_error_m": position_error,
            "measured_yaw_rad": measured[:, 4],
            "predicted_yaw_rad": predicted[:, 4],
            "yaw_error_rad": error[:, 4],
            "measured_yaw_rate_radps": measured[:, 5],
            "predicted_yaw_rate_radps": predicted[:, 5],
            "yaw_rate_error_radps": error[:, 5],
            "measured_slip_angle_rad": measured[:, 6],
            "predicted_slip_angle_rad": predicted[:, 6],
            "slip_angle_error_rad": error[:, 6],
        }
    )


def metric_row(metric: str, value: float, units: str, partition: str, description: str) -> dict[str, object]:
    return {
        "metric": metric,
        "value": value,
        "units": units,
        "partition": partition,
        "description": description,
    }


def create_metrics(
    fit_trace: pd.DataFrame,
    validation_trace: pd.DataFrame,
    coefficients: np.ndarray,
    result: object,
    train: np.ndarray,
    heldout: np.ndarray,
    oracle: np.ndarray | None,
) -> pd.DataFrame:
    train_trace = fit_trace[fit_trace["partition"] == "train"]
    heldout_trace = fit_trace[fit_trace["partition"] == "heldout"]
    jacobian_condition = float(np.linalg.cond(result.jac))
    row_scales = np.tile(np.asarray(result.response_scales, dtype=float), len(train))
    raw_jacobian = result.jac * row_scales[:, None] / coefficients[None, :]
    raw_jacobian_condition = float(np.linalg.cond(raw_jacobian))
    information = result.jac.T @ result.jac
    covariance_shape = np.linalg.inv(information)
    parameter_correlation = float(
        covariance_shape[0, 1]
        / np.sqrt(covariance_shape[0, 0] * covariance_shape[1, 1])
    )
    sensitivity_column_cosine = float(
        np.dot(result.jac[:, 0], result.jac[:, 1])
        / (np.linalg.norm(result.jac[:, 0]) * np.linalg.norm(result.jac[:, 1]))
    )
    rows = [
        metric_row("fitted_C_Sf", float(coefficients[0]), "Gym coefficient", "fit", "Identified front cornering stiffness coefficient."),
        metric_row("fitted_C_Sr", float(coefficients[1]), "Gym coefficient", "fit", "Identified rear cornering stiffness coefficient."),
        metric_row("jacobian_condition_number", jacobian_condition, "unitless", "fit", "Condition number of the normalized residual Jacobian."),
        metric_row("raw_jacobian_condition_number", raw_jacobian_condition, "unitless", "fit", "Condition number after undoing response and log-parameter scaling."),
        metric_row("parameter_correlation", parameter_correlation, "correlation", "fit", "C_Sf-C_Sr correlation implied by the inverse normalized information matrix."),
        metric_row("sensitivity_column_cosine", sensitivity_column_cosine, "cosine", "fit", "Cosine between normalized C_Sf and C_Sr sensitivity columns."),
        metric_row("train_one_step_yaw_rate_rmse", rmse(train_trace["yaw_rate_residual_radps"].to_numpy()), "rad/s", "train", "One-step yaw-rate RMSE."),
        metric_row("train_one_step_slip_angle_rmse", rmse(train_trace["slip_angle_residual_rad"].to_numpy()), "rad", "train", "One-step slip-angle RMSE."),
        metric_row("heldout_one_step_yaw_rate_rmse", rmse(heldout_trace["yaw_rate_residual_radps"].to_numpy()), "rad/s", "heldout", "One-step yaw-rate RMSE."),
        metric_row("heldout_one_step_slip_angle_rmse", rmse(heldout_trace["slip_angle_residual_rad"].to_numpy()), "rad", "heldout", "One-step slip-angle RMSE."),
        metric_row("heldout_rollout_position_rmse", rmse(validation_trace["position_error_m"].to_numpy()), "m", "heldout", "Independent held-out rollout position RMSE."),
        metric_row("heldout_rollout_yaw_rmse", rmse(validation_trace["yaw_error_rad"].to_numpy()), "rad", "heldout", "Independent held-out rollout yaw RMSE."),
        metric_row("heldout_rollout_yaw_rate_rmse", rmse(validation_trace["yaw_rate_error_radps"].to_numpy()), "rad/s", "heldout", "Independent held-out rollout yaw-rate RMSE."),
        metric_row("heldout_rollout_yaw_rate_nrmse", nrmse(validation_trace["yaw_rate_error_radps"].to_numpy(), validation_trace["measured_yaw_rate_radps"].to_numpy()), "fraction of measured range", "heldout", "Independent held-out rollout yaw-rate RMSE normalized by measured range."),
        metric_row("heldout_rollout_yaw_rate_vaf_percent", vaf_percent(validation_trace["yaw_rate_error_radps"].to_numpy(), validation_trace["measured_yaw_rate_radps"].to_numpy()), "%", "heldout", "Independent held-out rollout yaw-rate variance accounted for."),
        metric_row("heldout_rollout_slip_angle_rmse", rmse(validation_trace["slip_angle_error_rad"].to_numpy()), "rad", "heldout", "Independent held-out rollout slip-angle RMSE."),
        metric_row("heldout_rollout_slip_angle_nrmse", nrmse(validation_trace["slip_angle_error_rad"].to_numpy(), validation_trace["measured_slip_angle_rad"].to_numpy()), "fraction of measured range", "heldout", "Independent held-out rollout slip-angle RMSE normalized by measured range."),
        metric_row("heldout_rollout_slip_angle_vaf_percent", vaf_percent(validation_trace["slip_angle_error_rad"].to_numpy(), validation_trace["measured_slip_angle_rad"].to_numpy()), "%", "heldout", "Independent held-out rollout slip-angle variance accounted for."),
        metric_row("train_intervals", float(len(train)), "count", "train", "Dynamic-regime intervals used for fitting."),
        metric_row("heldout_intervals", float(len(heldout)), "count", "heldout", "Chronologically held-out dynamic-regime intervals."),
        metric_row("optimizer_cost", float(result.cost), "unitless", "fit", "Least-squares objective at the solution."),
        metric_row("optimizer_evaluations", float(result.nfev), "count", "fit", "Optimizer function evaluations."),
    ]
    if oracle is not None:
        relative_error = np.abs(coefficients - oracle) / oracle
        rows[2:2] = [
            metric_row("C_Sf_oracle_relative_error", float(relative_error[0]), "fraction", "oracle_check", "Relative error against the supplied synthetic-data oracle."),
            metric_row("C_Sr_oracle_relative_error", float(relative_error[1]), "fraction", "oracle_check", "Relative error against the supplied synthetic-data oracle."),
        ]
    return pd.DataFrame(rows)


def metric_dict(metrics: pd.DataFrame) -> dict[str, float]:
    return {str(row.metric): float(row.value) for row in metrics.itertuples(index=False)}


def acceptance(metrics: pd.DataFrame) -> dict[str, bool]:
    values = metric_dict(metrics)
    checks = {
        "heldout_yaw_rate": values["heldout_rollout_yaw_rate_rmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_yaw_rate_rmse_radps"],
        "heldout_slip_angle": values["heldout_rollout_slip_angle_rmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_slip_angle_rmse_rad"],
        "heldout_yaw": values["heldout_rollout_yaw_rmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_yaw_rmse_rad"],
        "heldout_normalized_fit": values["heldout_rollout_yaw_rate_nrmse"]
        <= ACCEPTANCE_LIMITS["max_heldout_rollout_yaw_rate_nrmse"],
        "heldout_variance_accounted_for": values["heldout_rollout_yaw_rate_vaf_percent"]
        >= ACCEPTANCE_LIMITS["min_heldout_rollout_yaw_rate_vaf_percent"],
        "identifiability": values["jacobian_condition_number"]
        <= ACCEPTANCE_LIMITS["max_jacobian_condition_number"],
        "parameter_correlation": abs(values["parameter_correlation"])
        <= ACCEPTANCE_LIMITS["max_parameter_correlation_abs"],
    }
    if "C_Sf_oracle_relative_error" in values:
        checks = {
            "oracle_recovery": max(
                values["C_Sf_oracle_relative_error"],
                values["C_Sr_oracle_relative_error"],
            )
            <= ACCEPTANCE_LIMITS["max_oracle_relative_error_fraction"],
            **checks,
        }
    return checks


def first_failed_gate(checks: dict[str, bool]) -> str:
    for gate in ACCEPTANCE_GATE_ORDER:
        if gate in checks and not bool(checks[gate]):
            return gate
    return ""


def identify_from_telemetry(
    telemetry: pd.DataFrame,
    *,
    repo_root: Path,
    oracle: np.ndarray | None = ORACLE,
) -> IdentificationResult:
    telemetry = validate_identification_telemetry(telemetry.copy())
    vehicle_dynamics_st = load_vehicle_dynamics_st(repo_root, module_name="roboracer_identification_dynamic_models")
    states = state_matrix(telemetry)
    controls = input_matrix(telemetry)
    dt = np.diff(telemetry["time_s"].to_numpy(dtype=float))
    train, heldout, split_interval = split_intervals(states)
    coefficients, optimizer, response_scales = fit_coefficients(vehicle_dynamics_st, states, controls, dt, train)
    optimizer.response_scales = response_scales
    fit_trace = build_fit_trace(vehicle_dynamics_st, telemetry, states, controls, dt, train, heldout, coefficients)
    validation_trace = heldout_rollout(vehicle_dynamics_st, telemetry, states, controls, dt, split_interval, coefficients)
    metrics = create_metrics(
        fit_trace,
        validation_trace,
        coefficients,
        optimizer,
        train,
        heldout,
        oracle,
    )
    checks = acceptance(metrics)
    values = metric_dict(metrics)
    return IdentificationResult(
        coefficients=coefficients,
        metrics=metrics,
        fit_trace=fit_trace,
        validation_trace=validation_trace,
        acceptance_checks=checks,
        acceptance_limits=dict(ACCEPTANCE_LIMITS),
        optimizer_success=bool(optimizer.success),
        optimizer_message=str(optimizer.message),
        optimizer_cost=float(optimizer.cost),
        optimizer_evaluations=int(optimizer.nfev),
        jacobian_condition_number=float(values["jacobian_condition_number"]),
        raw_jacobian_condition_number=float(values["raw_jacobian_condition_number"]),
        parameter_correlation=float(values["parameter_correlation"]),
        sensitivity_column_cosine=float(values["sensitivity_column_cosine"]),
        train_intervals=int(values["train_intervals"]),
        heldout_intervals=int(values["heldout_intervals"]),
        split_interval=split_interval,
    )
