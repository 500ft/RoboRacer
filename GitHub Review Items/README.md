# GitHub Review Items

This folder tracks the post-review action list for the F1TENTH/RoboRacer portfolio project. It is separate from `Things to Complete/`, which is the older internal roadmap. Use this file to track the current reviewer-facing sequence of work.

## Status Summary

| Item | Workstream | Status | Primary output |
| ---: | --- | --- | --- |
| 1 | Tag milestone and clean remote branches | Partial | Git tag exists; remote branches deleted; GitHub release page still needed |
| 2 | Clean up local folders | Done | Stale checkout archived; VLM paper folder renamed |
| 3 | Factor shared code into a module | Done | `gym/roboracer/` shared utilities |
| 4 | Pure pursuit sweep | Done | `reports/pure_pursuit_sweep.md` |
| 5 | LQR controller | Done | `reports/lqr_controller.md` |
| 6 | MPC controller | Done | `reports/mpc_controller.md`, `reports/controller_comparison.md` |
| 7 | EKF study | Done | `reports/ekf_study.md` |
| 8 | Failure-mode FMEA | Done | `reports/failure_mode_fmea.md` |
| 9 | Noise robustness of parameter ID | Done | `reports/parameter_id_robustness.md` |
| 10 | LiDAR mast mechanical package | Pending | 4g load case, FEA, modal, tolerance page (now the first structural artifact of item 16) |
| 11 | Real rosbag through pipeline | Pending | Design-only scope: `f1tenth_gym_ros` fallback bag now; real-hardware rerun deferred to the post-build milestone (item 17) |
| 12 | Final portfolio report | Pending | 10-20 page report and README results gallery |
| 13 | Vehicle requirements & architecture | Pending | Requirements table + system block diagram (sensing/compute/actuation/power) |
| 14 | Chassis, drivetrain & actuator selection | Pending | Platform choice; geometry locked to sim wheelbase 0.3302 m; motor/ESC/servo sizing |
| 15 | Sensor, compute & power package | Pending | LiDAR/IMU/encoders, compute sized to MPC budget, battery/power budget, wiring diagram |
| 16 | Mechanical design & analysis | Pending | Chassis/sensor-deck CAD, mass & CG budget, FEA (absorbs item 10), mesh convergence, modal |
| 17 | Pipeline integration & build-readiness | Pending | Topic map to existing ROS2 pipeline, BOM/cost, assembly plan, deferred build+bring-up milestone |

Items 13-17 form the **Vehicle Design Package** — a *parallel*, *design-only* workstream (no fabrication) added because NYU has no RoboRacer car, so the real-hardware path (item 11) requires designing the platform from scratch. It does not block the simulation items (7-9).

## 1. Tag Milestone and Clean Remote Branches

**Status:** Partial.

Done:

- `v0.1-identification-validated` exists and resolves to `dd0a47b`.
- Already-merged remote feature branches were deleted; only `origin/main` remains.

Remaining:

- Create the GitHub release page for `v0.1-identification-validated`.

Blocked by:

- The local environment does not have `gh`.
- No `GITHUB_TOKEN` or `GH_TOKEN` is available.

Recommended release command once GitHub CLI authentication exists:

```bash
gh release create v0.1-identification-validated \
  --repo 500ft/F1TENTH \
  --target dd0a47b \
  --title "v0.1 Identification Validated" \
  --notes "Dynamic parameter identification milestone validated against held-out replay."
```

## 2. Clean Up Local Folders

**Status:** Done.

Done:

- Archived stale checkout to `/Users/redhose/Documents/Codex/archived-F1TENTH-2026-06-17`.
- Renamed the RoboTracer/VLM reference folder to `/Users/redhose/Documents/Codex/robotracer-vlm-paper`.

## 3. Factor Shared Code Into a Module

**Status:** Done.

Done:

- Added the importable shared package `gym/roboracer/`.
- Centralized numerical helpers, RK4 stepping, dynamic model loading, telemetry loading/validation, pure pursuit, waypoint metrics, and shared scalar extraction.
- Refactored replay, fitting, convergence, lap, and sysID scripts to use shared utilities.
- Committed and pushed as `634a918 Factor shared RoboRacer experiment utilities`.

Key files:

- `gym/roboracer/numerics.py`
- `gym/roboracer/dynamics.py`
- `gym/roboracer/telemetry.py`
- `gym/roboracer/track.py`

## 4. Pure Pursuit Sweep

**Status:** Done.

Goal:

- Sweep lookahead distance and speed/velocity gain at the converged RK4 timestep, `dt = 0.002 s`.

Deliverables:

- Metrics table with lap time, RMS CTE, max CTE, steering effort, collision/completion, and termination reason.
- Plot identifying stable, oscillatory, corner-cutting, and collision regions.
- Justified baseline lookahead and speed/gain pair for later LQR/MPC comparison.

Completed artifacts:

- `experiments/pure_pursuit_sweep.py`
- `runs/pure_pursuit_sweep/results.csv`
- `reports/pure_pursuit_sweep.md`
- `reports/figures/pure_pursuit_sweep_regions.png`
- `reports/figures/pure_pursuit_sweep_lap_time_heatmap.png`
- `reports/figures/pure_pursuit_sweep_rms_cte_heatmap.png`

Result:

- Selected baseline: lookahead `1.2 m`, velocity gain `1.2`.
- Baseline completed one lap at RK4 integration `dt = 0.002 s` with a 100 Hz zero-order-held controller update.

## 5. LQR Controller

**Status:** Done.

Goal:

- Linearize the path-tracking/error-state model from the identified dynamic model.

Deliverables:

- Documented `A`, `B`, `Q`, and `R`.
- LQR gain `K`.
- Closed-loop eigenvalues.
- Comparison against tuned pure pursuit on the same map.
- Off-nominal tests for input delay and bad initial offset.

Completed artifacts:

- `experiments/lqr_controller.py`
- `experiments/validate_lqr_controller.py`
- `runs/lqr_controller/results.csv`
- `runs/lqr_controller/linear_model.json`
- `reports/lqr_controller.md`
- `reports/figures/lqr_controller_cte_cases.png`

Result:

- Nominal, `+0.5 m` initial offset, and `30 ms` input-delay cases complete on the example map.
- The implementation uses the tuned pure-pursuit command as feedforward and applies a bounded LQR correction from the local path-error model.

## 6. MPC Controller

**Status:** Done.

Goal:

- Implement constrained predictive control with steering angle and steering-rate limits.

Deliverables:

- MPC formulation and controller script.
- PP/LQR/MPC comparison table.
- Solver runtime measured against a 50-100 Hz real-time budget.

Completed artifacts:

- `experiments/mpc_controller.py`
- `experiments/validate_mpc_controller.py`
- `experiments/controller_comparison.py`
- `experiments/validate_controller_comparison.py`
- `runs/mpc_controller/results.csv`
- `runs/controller_comparison/results.csv`
- `reports/mpc_controller.md`
- `reports/controller_comparison.md`
- `reports/figures/mpc_solver_runtime.png`
- `reports/figures/mpc_controller_cte.png`

Result:

- MPC completed the nominal lap using SciPy SLSQP, analytic objective gradient, and linear input-rate constraints.
- Runtime is measured against 100 Hz and 50 Hz budgets in `reports/mpc_controller.md`.

## 7. EKF Study

**Status:** Done.

Goal:

- Compare dead reckoning and EKF state estimation under noisy measurements and dropout windows.

Deliverables:

- Reproducible noisy/dropout measurement generator.
- EKF prediction/correction implementation.
- RMSE over time against Gym ground truth.
- Summary table showing when EKF improves over dead reckoning.

Completed artifacts:

- `gym/roboracer/noise.py`
- `gym/roboracer/estimation.py`
- `experiments/ekf_study.py`
- `experiments/validate_ekf_study.py`
- `runs/ekf_study/summary.csv`
- `runs/ekf_study/trace.csv`
- `runs/ekf_study/metadata.json`
- `reports/ekf_study.md`
- `reports/figures/ekf_position_error_over_time.png`
- `reports/figures/ekf_rmse_summary.png`
- `reports/figures/ekf_dropout_zoom.png`

Result:

- EKF uses scenario-specific `R` from the injected measurement noise and a fixed documented process covariance `Q`.
- Dead reckoning is intentionally initialized with pose/state error so the estimator comparison measures drift recovery, not oracle replay.

## 8. Failure-Mode FMEA

**Status:** Done.

Goal:

- Reproduce at least five failure modes and document detection signals and mitigations.

Candidate failures:

- Euler instability.
- Lookahead too small.
- Lookahead too large.
- Input latency.
- Sensor noise.
- Measurement dropout.
- Actuator saturation.

Deliverable:

- FMEA table with cause, effect, detection signal, and mitigation.

Completed artifacts:

- `gym/roboracer/failures.py`
- `experiments/failure_mode_fmea.py`
- `experiments/validate_failure_mode_fmea.py`
- `runs/failure_mode_fmea/results.csv`
- `reports/failure_mode_fmea.md`
- `reports/figures/fmea_rpn_bar.png`
- `reports/figures/fmea_detection_signals.png`

Result:

- Seven failure cases are reproduced or quantified: Euler instability, too-small lookahead, too-large lookahead, 100 ms latency, high sensor noise, 3 s dropout, and steering saturation.
- Each row records detection signal, effect, mitigation, severity, occurrence, detectability, and RPN.

## 9. Noise Robustness of Parameter Identification

**Status:** Done.

Goal:

- Bridge the current near-oracle Gym fit to realistic data quality.

Tests:

- Inject sensor noise.
- Inject latency.
- Add quantization.
- Re-run the `C_Sf`/`C_Sr` fit.

Deliverables:

- Parameter degradation table.
- Condition number degradation table.
- Interpretation of when the fit stops being credible.

Completed artifacts:

- `gym/roboracer/identification.py`
- `experiments/parameter_id_robustness.py`
- `experiments/validate_parameter_id_robustness.py`
- `runs/parameter_id_robustness/results.csv`
- `runs/parameter_id_robustness/metrics.csv`
- `runs/parameter_id_robustness/metadata.json`
- `reports/parameter_id_robustness.md`
- `reports/figures/parameter_id_noise_degradation.png`
- `reports/figures/parameter_id_latency_degradation.png`
- `reports/figures/parameter_id_condition_number.png`

Result:

- The nominal dynamic-ID script and robustness sweep now share `roboracer.identification`, including the same named acceptance gates.
- The tested data-quality perturbations show latency as the dominant failure path for `C_Sf`/`C_Sr` recovery.

## 10. LiDAR Mast Mechanical Package

**Status:** Pending.

**Note:** Now executed as the first structural artifact inside the Vehicle Design Package (item 16), rather than as a standalone deliverable.

Goal:

- Add a mechanical engineering artifact that differentiates the portfolio from a pure simulation/control project.

Deliverables:

- 4g load case.
- Free-body diagram and hand calculation.
- CAD or simplified geometry.
- Static FEA compared against hand calculation.
- Mesh convergence with less than 5 percent stress change.
- Modal analysis.
- Tolerance stack effect on LiDAR angular error.
- One polished design page.

## 11. Real Rosbag Through the Pipeline

**Status:** Pending.

**Note:** Under the current design-only scope, this is satisfied with the `f1tenth_gym_ros` fallback (ROS-backed, still simulated). A true physical-RoboRacer bag is gated on actually building the car and is therefore part of the deferred build+bring-up milestone defined in item 17.

Goal:

- Run non-synthetic (or at least ROS-backed) telemetry through the existing pipeline.

Preferred data sources:

- `f1tenth_gym_ros` bag (current target under design-only scope).
- Physical RoboRacer bag from the future build (deferred milestone).

Pipeline:

- `rosbag_to_telemetry.py`
- telemetry quality gates
- dynamic parameter fit
- validation report

## 12. Final Portfolio Report

**Status:** Pending.

Goal:

- Produce a polished 10-20 page technical report.

Deliverables:

- Clean-environment rerun via `run_all.sh`.
- Final results gallery at the top of `README.md`.
- Best 3-4 figures.
- Dynamic parameter ID table.
- Controller comparison table.
- Failure-mode/FMEA summary.
- Mechanical design page.

# Vehicle Design Package (Items 13-17)

**Track type:** Parallel. Runs alongside the simulation items (7-9) and does not block them.

**Scope:** Design-only — CAD, analysis, architecture, and BOM sufficient to hand off to a build, with **no fabrication**. Physical build and on-car bring-up (which would turn item 11 into a real-hardware result) are a **deferred optional milestone**, defined in item 17, to commit to later.

**Why this exists:** NYU has no RoboRacer car, so the real-hardware validation path requires designing the platform from scratch. This package is the MechE-differentiating centerpiece of the portfolio. It must stay consistent with the already-identified dynamic model — in particular the wheelbase of **0.3302 m** used throughout the simulation (`WHEELBASE_M = 0.15875 + 0.17145` in `gym/roboracer/closed_loop.py`) and the speed/steering-rate envelope exercised by the controllers.

**Internal order:** 13 -> 14 -> 15/16 (can overlap) -> 17. Item 16 absorbs the existing item 10.

## 13. Vehicle Requirements and System Architecture

**Status:** Pending.

Goal:

- Define what the car must do and how its subsystems connect, before any part selection.

Deliverables:

- Requirements table: target speed, sensor payload, onboard compute, runtime, scale, and mass budget.
- System block diagram: sensing -> compute -> actuation -> power.
- Traceability back to the validated simulation envelope (speeds and steering rates used in experiments 4-6).

## 14. Chassis, Drivetrain, and Actuator Selection

**Status:** Pending.

Goal:

- Choose the rolling platform and actuation, geometry-locked to the identified model.

Deliverables:

- Base-platform decision (1/10-scale RC class vs custom chassis) with rationale.
- Wheelbase and track set to match the sim model (wheelbase 0.3302 m); any deviation documented with its effect on the identified `C_Sf`/`C_Sr` parameters.
- Motor/ESC and steering-servo sizing against the target speed/acceleration and the steering-rate limits used by the controllers.

## 15. Sensor, Compute, and Power Package

**Status:** Pending.

Goal:

- Specify the sensing, compute, and power stack.

Deliverables:

- LiDAR, IMU, and wheel/motor encoders selected so they produce the topics the pipeline already consumes (`/ego_racecar/odom`, `/drive`).
- Onboard compute (e.g., Jetson-class) sized against the measured MPC runtime budget (p95 1.33 ms at 100 Hz).
- Battery sizing, power budget, and a wiring/power-distribution diagram.

## 16. Mechanical Design and Analysis

**Status:** Pending.

Goal:

- Mechanical design and structural validation of the chassis and sensor deck.

Deliverables:

- CAD of the chassis plate and sensor deck; mass and CG budget.
- LiDAR mast structural analysis (item 10) as the first artifact: 4g load case, FBD + hand calc, FEA vs hand calc, mesh convergence under 5 percent, modal analysis, and tolerance stack -> LiDAR angular error.
- One polished design page per major part.

## 17. Pipeline Integration and Build-Readiness

**Status:** Pending.

Goal:

- Make the design build-ready and provably compatible with the existing software pipeline.

Deliverables:

- Mapping from the designed sensor suite to the existing ROS2 topics so the current sysID/identification/control stack runs unchanged on a future build.
- Full BOM with cost and lead times.
- Assembly sequence / build plan.
- Explicit definition of the deferred build + bring-up milestone (what "validated on real hardware" means), feeding item 11.

# Recommended Next Work

Two parallel tracks from here:

- **Simulation / data credibility:** item 11 next using a ROS-backed `f1tenth_gym_ros` bag through `rosbag_to_telemetry.py`, quality gates, and the shared dynamic-ID pipeline.
- **Vehicle design package (items 13-17):** start with item 13 (requirements + architecture); 14-17 depend on it. Item 16 absorbs the old item 10 (LiDAR mast FEA).

Item 11 (real rosbag) uses the `f1tenth_gym_ros` fallback under the current design-only scope; a real-hardware rerun is the deferred build milestone defined in item 17. Item 12 (final report) closes both tracks.
