# F1TENTH / RoboRacer Modeling, Identification, and Control — Final Report

**Status:** Skeleton / outline. DONE sections below are filled from existing reports in `reports/` and run outputs in `runs/`. Sections marked **TODO** / **TEMPLATE** are not yet executed.

**Scope guardrail (read first):** Every quantitative result in this report is **simulation-vs-simulation**. No physical RoboRacer vehicle has been built, instrumented, or tested. Where a number is not yet present in the repository, it is marked `[confirm]` rather than guessed.

**Reproduction:** `./run_all.sh` (see Section 10). Heavier sweeps are gated behind `RUN_FULL_MPC=1` and `RUN_ROBUSTNESS=1`.

---

## Table of Contents

1. Introduction and Scope
2. Modeling Pipeline
3. Dynamic Parameter Identification and Held-Out Validation
4. Controller Comparison (Pure Pursuit / LQR / MPC)
5. State Estimation (EKF)
6. Failure-Mode FMEA
7. Parameter-ID Robustness (Sim → Real Bridge)
8. Mechanical Design and Analysis — **PLACEHOLDER (see `docs/design/16_mechanical_design_analysis.md`)**
9. Limitations
10. Reproduction

---

## 1. Introduction and Scope

**Status: DONE (summary).**

This project uses the F1TENTH/RoboRacer Gym simulator as an offline modeling and validation testbed for vehicle-model identification and path-tracking control. The pipeline is: Gym experiment → CSV telemetry → kinematic/dynamic replay → validation metrics → reports and figures (see top-level `README.md`). The central validated result is identification of the nonlinear single-track lateral coefficients `C_Sf` and `C_Sr` from controlled excitation, accepted only after an independent held-out replay passes (Section 3). On top of the identified model, three path-tracking controllers (pure pursuit, LQR, constrained MPC) are compared under a common map, integrator, and update rate (Section 4), with supporting studies on state estimation (Section 5), failure modes (Section 6), and degradation of the fit under realistic data quality (Section 7).

The deliberate boundary of this work is that it is **all in simulation**. The identification "oracle recovery" check measures whether the pipeline can recover known simulator parameters; it does not claim those parameters describe a physical car. A parallel design-only **Vehicle Design Package** (Section 8, `docs/design/`) scaffolds the hardware platform that would be needed to extend any of these results to real hardware, but no part is fabricated.

> TODO: Add a one-paragraph framing of motivation (NYU has no RoboRacer car; this is the sim/control credibility half of the portfolio) and a figure of the overall pipeline block diagram.

---

## 2. Modeling Pipeline

**Status: DONE (summary).**

The simulator is integrated with RK4 at `dt = 0.002 s`, chosen from a timestep-convergence sweep (`reports/integrator_convergence.md`); an Euler-vs-RK4 comparison (`reports/first_run.md`, `reports/figures/first_integrator_comparison.png`) motivates the integrator choice and is later reused as a numerical failure mode in the FMEA. The single-track dynamic model is replayed against recorded Gym telemetry both with known parameters (`reports/dynamic_model_replay.md`) and as a full model-vs-Gym comparison (`reports/model_vs_gym_comparison.md`), establishing that the model reproduces Gym's lateral/yaw evolution before any coefficient is fit. A scripted steering-excitation experiment (`reports/sysid_steering_excitation.md`, figures `sysid_steering_input.png`, `sysid_yaw_response.png`, `sysid_speed_hold.png`) generates the identification dataset and is screened by telemetry quality gates. Shared numerics, dynamics, telemetry I/O, pure pursuit, and track utilities live in the importable `gym/roboracer/` package so every experiment uses one code path.

> TODO: pull the exact RK4 convergence threshold / selected dt justification and the model-vs-Gym position-error figure number from `reports/integrator_convergence.md` and `reports/model_vs_gym_comparison.md`. Reference figures: `reports/figures/integrator_convergence_position_error.png`, `reports/figures/model_vs_gym_trajectory_error.png`.

---

## 3. Dynamic Parameter Identification and Held-Out Validation

**Status: DONE (summary).** Source: `reports/dynamic_parameter_identification.md`.

The nonlinear single-track coefficients `C_Sf` and `C_Sr` are estimated from controlled Gym excitation by bounded nonlinear least squares on normalized one-step yaw-rate and slip-angle residuals (RK4 one-step propagation through `vehicle_dynamics_st`), using only intervals at `speed_mps >= 0.75` to exclude Gym's low-speed kinematic fallback. The first 70% of usable intervals are training data; the final 30% are held out chronologically, and the held-out rollout propagates recursively from a single measured split state with no state resets. The identification is accepted **only because the independent held-out replay passes** every named acceptance gate — this gate also blocks controller design until satisfied.

| Parameter | Identified | Gym oracle | Relative error |
| --- | ---: | ---: | ---: |
| `C_Sf` | 4.717999998 | 4.718000000 | 5.197e-10 |
| `C_Sr` | 5.456200004 | 5.456200000 | 6.527e-10 |

Held-out validation (passed): yaw-rate **VAF 100.000%** (RMSE 3.028881e-10 rad/s, NRMSE 5.347e-10), slip-angle **VAF 100.000%** (RMSE 2.877898e-10 rad), yaw RMSE 3.846e-10 rad, position RMSE 2.067e-09 m, normalized-residual Jacobian condition number 1.340140, `C_Sf`-`C_Sr` parameter correlation 0.090721. Figures: `reports/figures/dynamic_parameter_fit.png`, `reports/figures/dynamic_parameter_residuals.png`.

**Honest framing:** the oracle comparison is a controlled simulator-recovery check. The near-zero errors reflect that the data was generated by the same simulator model, not that the coefficients describe a physical RoboRacer. Section 7 quantifies how this fit degrades once the data is made realistic.

---

## 4. Controller Comparison (Pure Pursuit / LQR / MPC)

**Status: DONE (summary).** Sources: `reports/controller_comparison.md`, `reports/pure_pursuit_sweep.md`, `reports/lqr_controller.md`, `reports/mpc_controller.md`.

All three controllers run on the same map at RK4 `dt = 0.002 s` with a 100 Hz zero-order-held command. Pure pursuit is tuned first by a lookahead × velocity-gain sweep; the selected baseline (lookahead 1.2 m, vgain 1.2) is the lowest-weighted-score stable lap and becomes the reference. LQR and MPC are both implemented as a **bounded correction on top of the tuned pure-pursuit feedforward** (max correction 0.005 rad), so the comparison isolates the value added by feedback/optimization rather than re-deriving a controller from scratch.

| controller | case | lap_time_s | rms_cte_m | max_abs_cte_m | steering_effort_rad | mpc_p95_solve_time_s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| pure_pursuit | selected_baseline | 38.042 | **0.157892** | 0.403062 | **8.19853** | — |
| lqr | nominal | 38.064 | 0.178628 | 0.497708 | 8.98777 | — |
| mpc | nominal | 37.860 | 0.169238 | 0.476650 | 8.67710 | 0.00132644 |

**Headline:** pure pursuit wins on both RMS CTE and steering effort; neither model-based controller beats it on tracking. LQR is stable (max discrete eigenvalue 0.996291, inside the unit circle) and survives a +0.5 m initial offset and a 30 ms input delay, but is worse on RMS CTE. **MPC's justification is constraint handling plus a measured runtime guarantee, not accuracy:** it enforces steering / steering-rate / acceleration limits and meets the 100 Hz budget at **p95 1.32644 ms** (mean 1.0739 ms), while its max solve time can spike to ~36.8 ms — above one 10 ms control period — which the report flags as a deployment risk (dedicated QP solver, watchdog timing, or shorter horizon). Figures: `reports/figures/pure_pursuit_sweep_rms_cte_heatmap.png`, `reports/figures/lqr_controller_cte_cases.png`, `reports/figures/mpc_solver_runtime.png`, `reports/figures/mpc_controller_cte.png`.

---

## 5. State Estimation (EKF)

**Status: DONE (summary).** Source: `reports/ekf_study.md`.

An EKF over state `[x, y, theta, speed, yaw_rate]` is compared against a dead-reckoning baseline under reproducible measurement noise and dropout (seed 42, fixed documented process covariance, scenario-specific measurement covariance from the injected noise). Dead reckoning is intentionally seeded with pose/state error so the comparison measures drift recovery rather than oracle replay; it diverges to a 46.10 m position RMSE in every scenario.

| scenario | EKF position RMSE (m) | EKF max position error (m) |
| --- | ---: | ---: |
| clean_measurements | 0.00397259 | 0.320156 |
| low_noise | 0.0163569 | 0.320156 |
| high_noise | 0.0527243 | 0.320156 |
| dropout_1s | 0.133975 | 1.41835 |
| dropout_3s | 0.705808 | 5.07754 |

The EKF stays sub-metre in RMSE across all scenarios, with the 3 s dropout producing the largest transient peak (5.08 m) before recovery. Figures: `reports/figures/ekf_rmse_summary.png`, `reports/figures/ekf_position_error_over_time.png`, `reports/figures/ekf_dropout_zoom.png`.

---

## 6. Failure-Mode FMEA

**Status: DONE (summary).** Source: `reports/failure_mode_fmea.md`.

Seven controller / estimator / numerical / latency / actuator failures are reproduced or quantified, each scored with severity × occurrence × detectability into an RPN with a stated detection signal and mitigation. Highest-risk modes are 100 ms input latency (RPN 200, collision at 1.484 s), high sensor noise (RPN 180), and 3 s measurement dropout (RPN 168). Figures: `reports/figures/fmea_rpn_bar.png`, `reports/figures/fmea_detection_signals.png`.

| scenario | category | reproduced | detection_signal | rpn |
| --- | --- | --- | --- | ---: |
| latency_100ms | latency | True | collision at 1.484 s | 200 |
| sensor_noise_high | noise | False | EKF high-noise position RMSE 0.053 m | 180 |
| measurement_dropout_3s | dropout | True | EKF dropout position RMSE 0.706 m | 168 |
| bad_lookahead_small | controller | True | collision at 0.432 s | 140 |
| bad_lookahead_large | controller | True | collision at 6.566 s | 112 |
| euler_instability | numerics | False | no failure, rms CTE 0.166 m | 96 |
| steering_saturation | actuator | True | command steer dwell at limit 0.419 rad | 72 |

> Note: `sensor_noise_high` and `euler_instability` are marked `reproduced = False` because they are quantified through their detection signal rather than driven to a hard failure; preserve that nuance when summarizing.

---

## 7. Parameter-ID Robustness (Sim → Real Bridge)

**Status: DONE (summary).** Source: `reports/parameter_id_robustness.md`.

The near-oracle fit of Section 3 is re-run under injected sensor noise, input latency, quantization, and a combined medium perturbation to find where it stops being credible. The fit holds through low noise and low/medium quantization but **first fails acceptance at `noise_medium`, on gate `heldout_yaw_rate`**; **input latency is the dominant failure path** — a 20 ms latency already drives `C_Sf` relative error to ~0.440 (oracle-recovery gate fails), worsening to ~0.892 at 50 ms.

| scenario | fitted_C_Sf | fitted_C_Sr | C_Sf rel. error | acceptance_passed | first_failed_gate |
| --- | ---: | ---: | ---: | --- | --- |
| nominal | 4.7180 | 5.4562 | 5.20e-10 | True | — |
| noise_low | 4.71218 | 5.45865 | 0.00123 | True | — |
| noise_medium | 4.5970 | 5.54669 | 0.02565 | False | heldout_yaw_rate |
| latency_20ms | 2.64023 | 5.17179 | 0.44039 | False | oracle_recovery |
| latency_50ms | 0.507641 | 4.5440 | 0.89240 | False | oracle_recovery |
| quantization_high | 4.84796 | 5.37615 | 0.02754 | False | heldout_yaw_rate |
| combined_medium | 0.532886 | 4.70612 | 0.88705 | False | oracle_recovery |

This is the report's honest sim-to-real caution: the perfect Section 3 numbers are a property of clean simulator data, and any future physical-bag fit must be treated skeptically — especially for timing/latency. Figures: `reports/figures/parameter_id_noise_degradation.png`, `reports/figures/parameter_id_latency_degradation.png`, `reports/figures/parameter_id_condition_number.png`.

---

## 8. Mechanical Design and Analysis — PLACEHOLDER

**Status: TODO.** This is the MechE centerpiece and is scaffolded but not executed. See the Vehicle Design Package in `docs/design/`, which must be completed in dependency order **13 → 14 → 15 → 16** so the FEA uses real geometry and real masses rather than being FEA-first:

- `docs/design/13_requirements_architecture.md` — requirements table + system block diagram, traced to the validated sim speed/steering envelope.
- `docs/design/14_chassis_drivetrain_actuators.md` — platform decision; geometry locked to wheelbase **0.3302 m** (`WHEELBASE_M` in `gym/roboracer/closed_loop.py`); motor/ESC/servo sizing.
- `docs/design/15_sensor_compute_power.md` — LiDAR/IMU/encoders mapped to `/ego_racecar/odom` and `/drive`; compute sized to the MPC p95 budget (1.32644 ms); battery/power budget.
- `docs/design/16_mechanical_design_analysis.md` — LiDAR-mast load case **derived from telemetry** (measured peak lateral acceleration × LiDAR tip mass × stated safety factor) as the governing maneuvering case, plus a separate crash/drop case; FBD + hand calc, static FEA vs hand calc, mesh convergence <5%, modal analysis with an acceptance criterion, and tolerance-stack → LiDAR angular error.

The author does the CAD and FEA. **No mechanical results exist yet; do not cite any until item 16 is executed.** When complete, summarize here: governing load case and value, hand-calc vs FEA stress agreement, mesh-convergence result, first natural frequency vs the excitation/control bands, and the tolerance-driven LiDAR angular error.

---

## 9. Limitations

**Status: DONE (summary).**

- **All results are simulation-vs-simulation.** There is no physical RoboRacer car; nothing here is hardware-validated.
- **Identification is simulator recovery.** The Section 3 errors are near-zero because the data was generated by the same model being fit (Section 7 shows the fit degrades sharply once data is made realistic; latency is the worst case).
- **Controllers are feedforward-corrected, single-map.** LQR/MPC are bounded corrections on a tuned pure-pursuit feedforward, evaluated on one example map; the sweep thresholds are map-specific heuristics, not universal stability criteria.
- **MPC timing is implementation-specific.** The p95 budget is met by this SciPy/SLSQP build, but max solve time can exceed one 10 ms control period; a deployment build needs a dedicated QP solver and watchdog timing.
- **EKF/FMEA scenarios are scripted injections**, not measured field conditions.
- **The Vehicle Design Package is design-only** (no fabrication); item 11's "real rosbag" is currently satisfied only with the simulated `f1tenth_gym_ros` ROS-backed fallback.

---

## 10. Reproduction

**Status: DONE (summary).** Driver: `run_all.sh`.

`./run_all.sh` reruns the pipeline in dependency order from a shell with the f1tenth-gym conda environment active: integrator baseline + validation, RK4 convergence sweep, dynamic model replays, SysID excitation + quality gates, dynamic parameter fit + held-out validation (+ noise/estimation/item-11 helper validations), pure-pursuit sweep + LQR (and validators), then the EKF study. Heavier sweeps are opt-in: set `RUN_FULL_MPC=1` for the MPC controller and the PP/LQR/MPC comparison, and `RUN_ROBUSTNESS=1` for the FMEA and parameter-ID robustness sweeps.

> Note: the ride-quality lateral-acceleration columns added in commit `9e603d0` (`summarize_run` in `gym/roboracer/closed_loop.py`) populate the closed-loop run outputs only on the next rerun in the gym==0.19.0 environment; the telemetry-derived load case in item 16 depends on that rerun (see Section 8 / `docs/design/16_mechanical_design_analysis.md`).
