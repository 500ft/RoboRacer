# Things to Complete

This roadmap turns the current F1TENTH simulator baseline into a robotics and mechatronics engineering investigation. Use this folder for planning only. Keep code in `experiments/`, generated run data in `runs/`, and finished report material in `reports/`.

## Recommended Execution Order

| Order | Task | Output |
| ---: | --- | --- |
| 1 | Clean RK4 vs Euler plot | Report-quality integrator sensitivity figure |
| 2 | Run timestep/speed/lookahead sweep | Integrator sensitivity table |
| 3 | Add track centerline and collision marker | Better trajectory plot |
| 4 | Derive kinematic bicycle model | Model derivation report section |
| 5 | Run controlled Gym input tests | Step, sine, and straight-line telemetry |
| 6 | Overlay Gym vs bicycle model | First true model-comparison plot |
| 7 | Fit model parameters | System ID metrics table |
| 8 | Tune pure pursuit | Controller tuning curves |
| 9 | Implement LQR | Controller comparison baseline |
| 10 | Start LiDAR mast CAD/FEA | Mechanical engineering artifact |

## Current Baseline

The current baseline is a headless pure-pursuit run in F1TENTH Gym comparing built-in RK4 and Euler integrators. RK4 completes the lap; Euler collides. This is an integrator sensitivity result, not yet a comparison against a derived vehicle model.

**Status:** Done — see `reports/first_run.md`.

Baseline artifacts:

- `runs/first_lap/telemetry.csv`
- `runs/first_lap/metadata.json`
- `reports/figures/first_integrator_comparison.png`
- `reports/first_run.md`

Baseline tasks:

- [x] Preserve RK4 as the default completed-lap reference.
- [x] Treat Euler collision as a controlled failure case to explain.
- [x] Keep all new studies reproducible from scripts.
- [x] Add every generated figure to the report with units and assumptions.

## 1. RK4 vs Euler Integrator Sensitivity

**Status:** Partial — `reports/first_run.md` covers RK4 vs Euler at the baseline timestep; `reports/integrator_convergence.md` sweeps RK4 across timesteps but does not re-run Euler at multiple timesteps or explain its failure mechanism.

### Goal

Explain whether Euler crashes because of numerical integration error, timestep choice, controller sensitivity, or track geometry.

### What to calculate

- RMS CTE.
- Max absolute CTE.
- Heading error relative to path tangent.
- Mean speed and progress rate.
- Collision point in track progress.

### What to test

- RK4 vs Euler at the current timestep.
- RK4 vs Euler at smaller and larger timesteps.
- Collision location for each failed run.

### Deliverable

A report-quality plot showing success/failure, RMS CTE, and collision point for RK4 and Euler.

### Done when

- [ ] RK4 and Euler are run at multiple timestep values.
- [x] Each run logs termination reason.
- [ ] Collision point is marked on the trajectory plot.
- [ ] The report explains why Euler fails under the tested settings.

## 2. Timestep, Speed, and Lookahead Sweep

**Status:** Partial — `reports/integrator_convergence.md` sweeps RK4 timestep only (selects `dt = 0.002 s`); the speed/lookahead grid and Euler comparison from this section are not yet run.

### Goal

Map the closed-loop sensitivity of the simulator and pure-pursuit controller across timestep, speed, and lookahead.

### What to calculate

- Success rate.
- RMS CTE.
- Max CTE.
- Lap time.
- Mean progress rate.

### What to test

- Integrator: RK4 and Euler.
- Timestep scale: `0.5x`, `1x`, `2x`.
- Speed command: `4 m/s`, `6 m/s`, `8 m/s`, `10 m/s`.
- Lookahead: low, medium, high.

### Deliverable

A sweep table and figure titled `Closed-loop integrator sensitivity: success rate, RMS CTE, and collision point vs timestep and speed`.

### Done when

- [ ] Sweep script runs all planned parameter combinations.
- [ ] Sweep output includes one row per run.
- [ ] Failed runs are included instead of discarded.
- [ ] Figure shows success rate and RMS CTE across the grid.

## 3. Kinematic Bicycle Model

**Status:** Partial — equations derived in `docs/vehicle_model.md` and exercised in `reports/model_vs_gym_comparison.md`; the standalone controlled-input tests (straight-line/step/sine/chirp) below have not been run independently of the Gym overlay.

### Goal

Derive and implement a simple kinematic bicycle model that can be compared against Gym RK4 under controlled inputs.

### What to calculate

- Wheelbase `L`.
- State equations for `x`, `y`, and heading.
- Yaw rate from speed and steering angle.
- Turning radius for constant steering.

### What to test

- Straight-line input.
- Constant step steer input.
- Sine steer input.
- Chirp steer input.

### Deliverable

A derivation section plus a script that simulates the kinematic bicycle model for fixed input sequences.

### Done when

- [x] Equations are written with units and assumptions.
- [x] Model script runs without Gym.
- [ ] Straight-line test preserves heading.
- [ ] Constant-steer test matches expected turning radius.

## 4. Gym RK4 vs Derived Bicycle Model Overlay

**Status:** Done — see `reports/model_vs_gym_comparison.md`.

### Goal

Create the first true model comparison: F1TENTH Gym RK4 plant vs the derived bicycle model under the same controlled inputs.

### What to calculate

- Position error over time.
- Heading error over time.
- Yaw-rate error over time.
- NRMSE for `x`, `y`, heading, and yaw rate.

### What to test

- Straight-line Gym RK4 vs bicycle model.
- Step-steer Gym RK4 vs bicycle model.
- Sine-steer Gym RK4 vs bicycle model.

### Deliverable

Overlay plots comparing `x(t)`, `y(t)`, heading, yaw rate, and position error.

### Done when

- [x] Controlled Gym telemetry is generated.
- [x] Bicycle model consumes the same input sequence.
- [x] Overlay plot uses the same time base for both systems.
- [x] Report states where the simple model matches and fails.

## 5. System Identification

**Status:** Done — see `reports/sysid_steering_excitation.md` (excitation) and `reports/dynamic_parameter_identification.md` (fit + held-out validation, 100% VAF).

### Goal

Fit model parameters from Gym telemetry instead of assuming hand-selected values are correct.

### What to calculate

- Estimated wheelbase or effective wheelbase.
- Steering response time constant.
- Yaw dynamics fit quality.
- NRMSE and VAF.

### What to test

- Step steer.
- Sine steer.
- PRBS steer.
- Constant-radius turn.
- Holdout validation input.

### Deliverable

A system identification table comparing kinematic, dynamic, and identified model performance.

### Done when

- [x] Excitation inputs are generated and logged.
- [x] Fit script estimates at least one model parameter.
- [x] Holdout validation is separate from fitting data.
- [x] Report includes NRMSE and VAF table.

## 6. Pure Pursuit Tuning Study

### Goal

Analyze pure pursuit as a controller instead of treating it as a black-box baseline.

### What to calculate

- Lookahead distance.
- Curvature command.
- Steering command.
- RMS CTE and max CTE.
- Steering effort.

### What to test

- Low, medium, and high lookahead distances.
- Multiple speeds.
- Tight turns and straight segments.
- Stability under high-speed tracking.

### Deliverable

Plots of RMS CTE vs lookahead and lap time vs lookahead.

### Done when

- [ ] Lookahead sweep script runs from the command line.
- [ ] Results include lap time, RMS CTE, max CTE, and collision.
- [ ] Report identifies stable, oscillatory, and corner-cutting regions.
- [ ] Recommended baseline lookahead is justified.

## 7. LQR Controller

### Goal

Design and test an LQR controller using a linearized path-tracking model.

### What to calculate

- Error-state model.
- `A` and `B` matrices.
- `Q` and `R` weights.
- LQR gain `K`.
- Closed-loop eigenvalues.

### What to test

- LQR vs pure pursuit on nominal lap.
- LQR with input delay.
- LQR with bad initial offset.
- Steering effort compared to pure pursuit.

### Deliverable

Controller comparison plot and table with lap time, RMS CTE, max CTE, collision, and steering effort.

### Done when

- [ ] Linearized model is documented.
- [ ] LQR gain is computed from script.
- [ ] Closed-loop eigenvalues are reported.
- [ ] LQR is compared against pure pursuit on the same map.

## 8. MPC Controller

### Goal

Implement constrained predictive control and compare it against pure pursuit and LQR.

### What to calculate

- Prediction horizon.
- State and input cost weights.
- Steering angle limits.
- Steering-rate limits.
- Solver runtime.

### What to test

- Nominal lap.
- High-speed lap.
- Added input delay.
- Noisy pose.
- Bad initial offset.

### Deliverable

A controller comparison table for pure pursuit, LQR, and MPC.

### Done when

- [ ] MPC optimization problem is written clearly.
- [ ] Constraints match the vehicle limits used by Gym.
- [ ] MPC runs on at least one lap or controlled segment.
- [ ] Runtime and failure cases are reported.

## 9. EKF State Estimation

### Goal

Compare dead reckoning and EKF state estimation under noisy measurements.

### What to calculate

- Process model.
- Measurement model.
- Process covariance.
- Measurement covariance.
- Position and heading RMSE.

### What to test

- Dead reckoning only.
- EKF with odometry-like measurements.
- EKF with noisy pose measurements.
- Dropout windows.

### Deliverable

RMSE-over-time plot and table comparing dead reckoning vs EKF.

### Done when

- [ ] Noisy measurement generator is reproducible.
- [ ] EKF prediction and correction steps are implemented.
- [ ] RMSE is computed against Gym ground truth.
- [ ] Report states whether EKF reduced RMSE and by how much.

## 10. Failure-Mode Testing

### Goal

Show controlled failure cases and mitigation strategies instead of only successful runs.

### What to calculate

- Collision rate.
- Failure timestep and progress.
- Peak CTE before failure.
- Steering sign changes.
- Recovery time after disturbance.

### What to test

- Euler instability.
- Lookahead too small.
- Lookahead too large.
- Sensor noise.
- Input latency.
- Measurement dropout.
- Model mismatch.
- Actuator saturation.

### Deliverable

An FMEA table with cause, effect, detection, and mitigation.

### Done when

- [ ] At least five failure modes are reproduced.
- [ ] Each failure mode has a measurable detection signal.
- [ ] Each failure mode has a proposed mitigation.
- [ ] Report includes an FMEA table.

## 11. Mechanical Engineering Package

### Goal

Add a mechanical engineering artifact so the portfolio is not only software and controls.

### What to calculate

- LiDAR mast lateral load for a 4g case.
- Bending stress.
- Tip deflection.
- Safety factor.
- First natural frequency.
- Tolerance stack effect on LiDAR angular error.

### What to test

- Hand calculation.
- Static FEA.
- Mesh convergence.
- Modal analysis.
- Tolerance sensitivity.

### Deliverable

One mechanical design page with FBD, hand calc, FEA contour, mesh convergence table, safety factor, and tolerance result.

### Done when

- [ ] Load case is defined with units.
- [ ] Hand calculation is complete.
- [ ] CAD or simplified geometry exists.
- [ ] FEA result is compared against hand calculation.
- [ ] Mesh convergence is below 5 percent stress change.

## 12. Final Portfolio Report

### Goal

Turn the investigation into a clean 10 to 20 page technical report.

### What to calculate

- Final baseline metrics.
- Model comparison metrics.
- Controller comparison metrics.
- Failure-mode summary metrics.
- Mechanical safety factor.

### What to test

- Re-run all scripts from a clean environment.
- Validate all figures regenerate.
- Check every claim against an artifact.
- Review assumptions and limitations.

### Deliverable

A polished report with reproducible figures, equations, tables, assumptions, and limitations.

### Done when

- [ ] Every figure has a script and source data.
- [ ] Every table has units.
- [ ] The report distinguishes simulator results from derived model results.
- [ ] The report explains failures, not only successes.
- [ ] The final README points readers to the best artifacts.
