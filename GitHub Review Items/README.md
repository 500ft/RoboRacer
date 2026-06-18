# GitHub Review Items

This folder tracks the post-review action list for the F1TENTH/RoboRacer portfolio project. It is separate from `Things to Complete/`, which is the older internal roadmap. Use this file to track the current reviewer-facing sequence of work.

## Status Summary

| Item | Workstream | Status | Primary output |
| ---: | --- | --- | --- |
| 1 | Tag milestone and clean remote branches | Partial | Git tag exists; remote branches deleted; GitHub release page still needed |
| 2 | Clean up local folders | Done | Stale checkout archived; VLM paper folder renamed |
| 3 | Factor shared code into a module | Done | `gym/roboracer/` shared utilities |
| 4 | Pure pursuit sweep | Next | Lookahead x speed grid, metrics table, stability plot |
| 5 | LQR controller | Pending | Linearized model, gain, eigenvalues, comparison |
| 6 | MPC controller | Pending | Constrained controller and runtime budget report |
| 7 | EKF study | Pending | Dead reckoning vs EKF under noise/dropout |
| 8 | Failure-mode FMEA | Pending | At least five reproduced failures with mitigations |
| 9 | Noise robustness of parameter ID | Pending | Parameter degradation under noise/latency/quantization |
| 10 | LiDAR mast mechanical package | Pending | 4g load case, FEA, modal, tolerance page |
| 11 | Real rosbag through pipeline | Pending | Real or ROS-backed bag through telemetry and fit pipeline |
| 12 | Final portfolio report | Pending | 10-20 page report and README results gallery |

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

**Status:** Next.

Goal:

- Sweep lookahead distance and speed/velocity gain at the converged RK4 timestep, `dt = 0.002 s`.

Deliverables:

- Metrics table with lap time, RMS CTE, max CTE, steering effort, collision/completion, and termination reason.
- Plot identifying stable, oscillatory, corner-cutting, and collision regions.
- Justified baseline lookahead and speed/gain pair for later LQR/MPC comparison.

Suggested artifacts:

- `experiments/pure_pursuit_sweep.py`
- `runs/pure_pursuit_sweep/results.csv`
- `reports/pure_pursuit_sweep.md`
- `reports/figures/pure_pursuit_sweep_regions.png`

## 5. LQR Controller

**Status:** Pending.

Goal:

- Linearize the path-tracking/error-state model from the identified dynamic model.

Deliverables:

- Documented `A`, `B`, `Q`, and `R`.
- LQR gain `K`.
- Closed-loop eigenvalues.
- Comparison against tuned pure pursuit on the same map.
- Off-nominal tests for input delay and bad initial offset.

## 6. MPC Controller

**Status:** Pending.

Goal:

- Implement constrained predictive control with steering angle and steering-rate limits.

Deliverables:

- MPC formulation and controller script.
- PP/LQR/MPC comparison table.
- Solver runtime measured against a 50-100 Hz real-time budget.

Preferred starting point:

- Use `cvxpy` for a linear MPC unless nonlinear constraints require CasADi.

## 7. EKF Study

**Status:** Pending.

Goal:

- Compare dead reckoning and EKF state estimation under noisy measurements and dropout windows.

Deliverables:

- Reproducible noisy/dropout measurement generator.
- EKF prediction/correction implementation.
- RMSE over time against Gym ground truth.
- Summary table showing when EKF improves over dead reckoning.

## 8. Failure-Mode FMEA

**Status:** Pending.

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

## 9. Noise Robustness of Parameter Identification

**Status:** Pending.

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

## 10. LiDAR Mast Mechanical Package

**Status:** Pending.

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

Goal:

- Run non-synthetic telemetry through the existing pipeline.

Preferred data sources:

- Physical RoboRacer bag, such as NYU/community data.
- At minimum, an `f1tenth_gym_ros` bag.

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

## Recommended Next Work

Start with item 4, the pure pursuit sweep. It creates the tuned baseline needed for LQR and MPC and should reuse the shared utilities now available in `gym/roboracer/`.
