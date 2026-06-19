"""Failure-mode scenario definitions for FMEA studies."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FailureScenario:
    scenario: str
    category: str
    trigger: str
    cause: str
    effect: str
    severity_1_to_10: int
    occurrence_1_to_10: int
    detectability_1_to_10: int
    mitigation: str
    parameters: dict[str, float | str] = field(default_factory=dict)


def default_failure_scenarios() -> list[FailureScenario]:
    return [
        FailureScenario(
            "euler_instability",
            "numerics",
            "Run the baseline lap with Euler integration.",
            "Low-order integration is unstable for the closed-loop vehicle dynamics.",
            "Early collision or large trajectory divergence.",
            8,
            4,
            3,
            "Use RK4 and keep timestep convergence gates in CI.",
            {"integrator": "Euler", "dt_s": 0.01},
        ),
        FailureScenario(
            "bad_lookahead_small",
            "controller",
            "Pure pursuit lookahead is too small.",
            "Controller chases local waypoint geometry and creates high steering activity.",
            "Oscillation, saturation, and elevated CTE.",
            7,
            5,
            4,
            "Use the sweep-selected baseline lookahead and steering-effort gates.",
            {"lookahead_m": 0.2, "vgain": 1.375},
        ),
        FailureScenario(
            "bad_lookahead_large",
            "controller",
            "Pure pursuit lookahead is too large.",
            "Controller cuts corners and under-reacts to curvature.",
            "Corner cutting, large CTE, or missed lap completion.",
            7,
            4,
            4,
            "Bound lookahead by map curvature and validate max CTE.",
            {"lookahead_m": 3.0, "vgain": 1.2},
        ),
        FailureScenario(
            "latency_100ms",
            "latency",
            "Hold controller commands behind a 100 ms delay.",
            "Control action arrives after the vehicle has moved to a different path state.",
            "Increased CTE and possible collision.",
            8,
            5,
            5,
            "Timestamp commands, reduce delay, and add delay compensation.",
            {"delay_ms": 100.0},
        ),
        FailureScenario(
            "sensor_noise_high",
            "noise",
            "Inject high measurement noise into estimator inputs.",
            "Measurement uncertainty overwhelms estimator correction.",
            "Estimator position RMSE increases and confidence degrades.",
            6,
            6,
            5,
            "Tune measurement covariance from sensor specs and reject outliers.",
            {"scenario_source": "ekf_high_noise"},
        ),
        FailureScenario(
            "measurement_dropout_3s",
            "dropout",
            "Remove measurements for a 3 s window.",
            "Estimator runs open loop through a long measurement outage.",
            "State uncertainty and position error grow during dropout.",
            7,
            4,
            6,
            "Detect stale measurements and slow or stop until updates recover.",
            {"scenario_source": "ekf_dropout_3s"},
        ),
        FailureScenario(
            "steering_saturation",
            "actuator",
            "Force steering command to the actuator limit.",
            "Requested curvature exceeds steering authority.",
            "Path tracking degrades and saturation masks controller intent.",
            8,
            3,
            3,
            "Monitor steering limit dwell time and lower speed when saturated.",
            {"steer_rad": 0.4189},
        ),
    ]
