# Items 7-9 Estimation and Robustness - Implementation Plan
Design: inline draft below
Status: implemented
Date: 2026-06-19

## Draft Design Header

### Scope

Implement the next simulation-side robustness block after the controller work:

- Item 7: EKF study comparing dead reckoning and EKF under noisy measurements and dropout windows.
- Item 8: failure-mode FMEA reproducing at least five failures with detection signals and mitigations.
- Item 9: parameter-identification robustness under injected noise, latency, and quantization.

### Non-Scope

- No physical RoboRacer bag requirement; item 11 covers ROS-backed or physical-bag data.
- No fabrication or CAD work; items 10 and 13-17 cover the vehicle-design package.
- No new solver dependencies unless an existing dependency cannot support the required study.

### Acceptance Criteria

| ID | Requirement |
| --- | --- |
| FR-7A | Generate reproducible noisy/dropout measurements from existing Gym/controller traces. |
| FR-7B | Implement dead reckoning and EKF estimators using the shared vehicle-model utilities. |
| FR-7C | Report estimator RMSE over time and a summary table showing when EKF improves over dead reckoning. |
| FR-8A | Reproduce at least five failure modes from the current pipeline. |
| FR-8B | Record cause, trigger, observable detection signal, effect, severity, and mitigation for each failure. |
| FR-8C | Produce an FMEA report and validation script. |
| FR-9A | Re-run `C_Sf`/`C_Sr` identification under injected sensor noise, latency, and quantization. |
| FR-9B | Report coefficient error, held-out degradation, and Jacobian condition number degradation. |
| FR-9C | Identify the first perturbation level where the parameter-ID acceptance gates stop passing. |
| FR-X | Update `GitHub Review Items/README.md`, README/report links, `run_all.sh`, and validators. |

### Conventions From Current Repo

- Experiment scripts live in `experiments/`.
- Shared utilities live in `gym/roboracer/`.
- Reports live in `reports/`; figures live in `reports/figures/`.
- Result artifacts live in `runs/<experiment_name>/`.
- Validation scripts are named `experiments/validate_<experiment_name>.py`.
- Scripts should add `gym/` to `sys.path` the same way current controller and SysID scripts do.
- Heavy studies should be gated in `run_all.sh` with an environment flag.

## Tasks

### [x] T00 - Record baseline commands
- Files: `docs/specs/items-7-9-estimation-robustness/plan.md`
- Do: run and record these commands under Execution notes:
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python -m compileall -q gym/roboracer experiments`
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python experiments/validate_controller_comparison.py`
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python experiments/validate_dynamic_parameter_identification.py`
- Depends on: none
- Done when: commands are recorded with pass/fail status.
- Parallel group: setup

### [x] T01 - Add shared measurement-noise helpers
- Files: `gym/roboracer/noise.py` (new)
- Do: implement:
  - `@dataclass class NoiseSpec`
  - `@dataclass class DropoutWindow`
  - `def make_rng(seed: int) -> np.random.Generator`
  - `def apply_sensor_noise(frame: pd.DataFrame, spec: NoiseSpec, *, seed: int) -> pd.DataFrame`
  - `def apply_dropout_windows(frame: pd.DataFrame, windows: list[DropoutWindow]) -> pd.DataFrame`
  - `def apply_quantization(frame: pd.DataFrame, steps: dict[str, float]) -> pd.DataFrame`
  These functions must preserve original ground-truth columns and add noisy measurement columns with a `meas_` prefix.
- Depends on: T00
- Done when: module imports with `from roboracer.noise import NoiseSpec`.
- Parallel group: A

### [x] T02 - Add measurement-noise unit validator
- Files: `experiments/validate_noise_helpers.py` (new)
- Do: create a deterministic smoke validator that builds a tiny DataFrame, applies noise/dropout/quantization, and asserts:
  - same row count,
  - `meas_*` columns exist,
  - dropout rows contain NaN in measurement columns only,
  - same seed gives identical noisy outputs.
- Depends on: T01
- Done when: `python experiments/validate_noise_helpers.py` prints `noise helper validation: PASS`.
- Parallel group: A

### [x] T03 - Add shared estimator models
- Files: `gym/roboracer/estimation.py` (new)
- Do: implement:
  - `def dead_reckon_step(state: np.ndarray, control: np.ndarray, dt: float, params: dict[str, float]) -> np.ndarray`
  - `class ExtendedKalmanFilter`
  - `def finite_difference_jacobian(fn, x: np.ndarray, eps: np.ndarray) -> np.ndarray`
  - `def angle_residual(value: float, reference: float) -> float`
  EKF state should be `[x_m, y_m, theta_rad, speed_mps, yaw_rate_radps]`. Use existing `roboracer.dynamics.kinematic_bicycle_rk4_step` or a documented reduced model for prediction; update with position, yaw, speed, and yaw-rate measurements when present. Add explicit constructor inputs for process covariance `Q` and measurement covariance `R`; do not hardcode tuning inside the EKF class.
- Depends on: T00
- Done when: module imports with `from roboracer.estimation import ExtendedKalmanFilter`.
- Parallel group: A

### [x] T04 - Add estimator smoke validator
- Files: `experiments/validate_estimation_helpers.py` (new)
- Do: create a short synthetic constant-turn trajectory with dead reckoning intentionally handicapped by at least one documented source of drift: wrong initial pose, process-model mismatch, or process noise. Use noisy measurements for EKF updates and assert:
  - EKF covariance stays finite and symmetric,
  - angle wrapping is bounded within `[-pi, pi]`,
  - EKF RMSE is not worse than dead reckoning on the synthetic noisy measurements.
- Depends on: T03
- Done when: `python experiments/validate_estimation_helpers.py` prints `estimation helper validation: PASS`.
- Parallel group: A

### [x] T05 - Implement EKF study runner
- Files: `experiments/ekf_study.py` (new)
- Do: load a completed controller trace, preferably `runs/pure_pursuit_sweep/results.csv` for baseline metadata and regenerate a nominal trace via `run_closed_loop`; create scenarios:
  - `clean_measurements`,
  - `low_noise`,
  - `high_noise`,
  - `dropout_1s`,
  - `dropout_3s`.
  For each scenario, run dead reckoning and EKF against Gym ground truth, write per-timestep errors and summary metrics.
  Set measurement covariance `R` from the known injected `NoiseSpec` values for each scenario. Set process covariance `Q` from a documented model-uncertainty table in the script, not by hand-tuning per scenario. Record both `Q` and `R` in metadata.
- Depends on: T01, T03
- Done when: outputs exist:
  - `runs/ekf_study/trace.csv`,
  - `runs/ekf_study/summary.csv`,
  - `runs/ekf_study/metadata.json`.
- Parallel group: B

### [x] T06 - Add EKF figures
- Files: `experiments/ekf_study.py`
- Do: generate:
  - `reports/figures/ekf_position_error_over_time.png`,
  - `reports/figures/ekf_rmse_summary.png`,
  - `reports/figures/ekf_dropout_zoom.png`.
- Depends on: T05
- Done when: all figures exist and are non-empty.
- Parallel group: B

### [x] T07 - Add EKF report
- Files: `experiments/ekf_study.py`, `reports/ekf_study.md` (generated)
- Do: write a Markdown report with:
  - scenario definitions,
  - dead-reckoning vs EKF summary table,
  - RMSE-over-time interpretation,
  - dropout-window interpretation,
  - limitations of using simulated ground truth.
- Depends on: T05, T06
- Done when: `reports/ekf_study.md` exists and links the three EKF figures.
- Parallel group: B

### [x] T08 - Add EKF validator
- Files: `experiments/validate_ekf_study.py` (new)
- Do: validate artifact existence and assert:
  - all five scenarios exist,
  - both estimators exist per scenario,
  - EKF position RMSE is lower than dead reckoning for at least `low_noise` and `dropout_1s`,
  - metadata records seed, integration timestep, measurement noise settings, EKF `Q`, and scenario-specific EKF `R`.
- Depends on: T07
- Done when: `python experiments/validate_ekf_study.py` prints `EKF study validation: PASS`.
- Parallel group: B

### [x] T09 - Add failure-mode scenario definitions
- Files: `gym/roboracer/failures.py` (new)
- Do: define:
  - `@dataclass class FailureScenario`
  - `def default_failure_scenarios() -> list[FailureScenario]`
  Include at least these scenarios: `euler_instability`, `bad_lookahead_small`, `bad_lookahead_large`, `latency_100ms`, `sensor_noise_high`, `measurement_dropout_3s`, `steering_saturation`.
- Depends on: T00
- Done when: the scenario list contains at least seven named scenarios with trigger metadata.
- Parallel group: C

### [x] T10 - Implement failure reproduction runner
- Files: `experiments/failure_mode_fmea.py` (new)
- Do: run scenarios using existing scripts/utilities:
  - Euler instability via `run_scripted_lap.py` telemetry or a dedicated `run_closed_loop` Euler scenario,
  - bad lookahead via `PurePursuitController`,
  - latency via `run_closed_loop(control_delay_steps=...)`,
  - sensor noise/dropout by feeding item 7 measurement degradation into estimator detection metrics,
  - steering saturation by limiting or commanding beyond model steering bounds.
- Depends on: T09, T05
- Done when: `runs/failure_mode_fmea/results.csv` contains at least five reproduced failures with non-empty detection signals.
- Parallel group: C

### [x] T11 - Define FMEA severity/detection scoring
- Files: `experiments/failure_mode_fmea.py`
- Do: add columns:
  - `severity_1_to_10`,
  - `occurrence_1_to_10`,
  - `detectability_1_to_10`,
  - `rpn`,
  - `detection_signal`,
  - `mitigation`.
  Compute `rpn = severity * occurrence * detectability`.
- Depends on: T10
- Done when: every row has finite scores and mitigation text.
- Parallel group: C

### [x] T12 - Add FMEA report and figures
- Files: `experiments/failure_mode_fmea.py`, `reports/failure_mode_fmea.md` (generated)
- Do: generate:
  - FMEA table sorted by descending RPN,
  - `reports/figures/fmea_rpn_bar.png`,
  - `reports/figures/fmea_detection_signals.png`.
- Depends on: T11
- Done when: report exists and includes at least five reproduced failures.
- Parallel group: C

### [x] T13 - Add FMEA validator
- Files: `experiments/validate_failure_mode_fmea.py` (new)
- Do: assert:
  - at least five rows have `reproduced == True`,
  - required scenarios include Euler instability, bad lookahead, latency, noise, and saturation or dropout,
  - each reproduced failure has detection signal and mitigation,
  - RPN is positive.
- Depends on: T12
- Done when: `python experiments/validate_failure_mode_fmea.py` prints `failure-mode FMEA validation: PASS`.
- Parallel group: C

### [x] T14 - Define identification result contract
- Files: `gym/roboracer/identification.py`
- Do: add `@dataclass class IdentificationResult` with fields for fitted coefficients, metrics DataFrame, fit trace DataFrame, validation trace DataFrame, acceptance checks, acceptance limits, optimizer status/message, Jacobian condition number, train interval count, and held-out interval count. Keep field names explicit so `parameter_id_robustness.py` can consume results without scraping generated files.
- Depends on: T00
- Done when: `from roboracer.identification import IdentificationResult` works and existing `fit_dynamic_parameters.py` output is unchanged.
- Parallel group: D

### [x] T15 - Refactor parameter fitting for robustness reuse
- Files: `gym/roboracer/identification.py`, `experiments/fit_dynamic_parameters.py`
- Do: extract pure fitting and acceptance functions into `roboracer.identification`, then have `fit_dynamic_parameters.py` call `identify_from_telemetry(...)` while preserving the existing CLI artifacts.
- Depends on: T14
- Done when: `python experiments/fit_dynamic_parameters.py` and `python experiments/validate_dynamic_parameter_identification.py` still pass.
- Parallel group: D

### [x] T16 - Add parameter-robustness perturbation utilities
- Files: `experiments/parameter_id_robustness.py` (new)
- Do: implement perturbation builders for:
  - yaw-rate noise,
  - speed noise,
  - steering noise,
  - input latency in samples,
  - quantization for speed, yaw rate, steering, and acceleration.
  Use `gym/roboracer/noise.py` helpers where possible.
- Depends on: T01, T15
- Done when: module can build a perturbed telemetry DataFrame without mutating the source.
- Parallel group: D

### [x] T17 - Implement parameter-robustness sweep
- Files: `experiments/parameter_id_robustness.py`
- Do: run nominal plus perturbation levels:
  - `noise_low`, `noise_medium`, `noise_high`,
  - `latency_20ms`, `latency_50ms`, `latency_100ms`,
  - `quantization_low`, `quantization_medium`, `quantization_high`,
  - `combined_medium`.
  For each level, re-run identification and collect fitted `C_Sf`, `C_Sr`, oracle relative error, held-out metrics, and Jacobian condition number.
- Depends on: T16
- Done when: `runs/parameter_id_robustness/results.csv` exists with at least ten rows.
- Parallel group: D

### [x] T18 - Add parameter-robustness degradation analysis
- Files: `experiments/parameter_id_robustness.py`
- Do: add columns:
  - `C_Sf_error_growth_vs_nominal`,
  - `C_Sr_error_growth_vs_nominal`,
  - `condition_growth_vs_nominal`,
  - `acceptance_passed`,
  - `first_failed_gate`.
  Compute `acceptance_passed` by calling `roboracer.identification.acceptance(metrics)` for each perturbed fit. Compute `first_failed_gate` from the ordered named gates returned by that function: `oracle_recovery`, `heldout_yaw_rate`, `heldout_slip_angle`, `heldout_yaw`, `heldout_normalized_fit`, `heldout_variance_accounted_for`, `identifiability`.
- Depends on: T17
- Done when: at least one high perturbation row records a failed or degraded gate, or the report explicitly says all tested gates passed.
- Parallel group: D

### [x] T19 - Add parameter-robustness figures
- Files: `experiments/parameter_id_robustness.py`
- Do: generate:
  - `reports/figures/parameter_id_noise_degradation.png`,
  - `reports/figures/parameter_id_latency_degradation.png`,
  - `reports/figures/parameter_id_condition_number.png`.
- Depends on: T18
- Done when: all figures exist and are non-empty.
- Parallel group: D

### [x] T20 - Add parameter-robustness report
- Files: `experiments/parameter_id_robustness.py`, `reports/parameter_id_robustness.md` (generated)
- Do: write a report with:
  - perturbation table,
  - coefficient degradation table,
  - condition-number degradation table,
  - acceptance-gate pass/fail table using the named gates from `roboracer.identification.acceptance(metrics)`,
  - interpretation connecting synthetic oracle performance to expected real-data sensitivity.
- Depends on: T19
- Done when: report exists and links all parameter-robustness figures.
- Parallel group: D

### [x] T21 - Add parameter-robustness validator
- Files: `experiments/validate_parameter_id_robustness.py` (new)
- Do: assert:
  - results include noise, latency, quantization, and combined perturbations,
  - fitted `C_Sf`/`C_Sr` are positive and finite,
  - condition numbers are finite,
  - `acceptance_passed` equals the recomputed result from `roboracer.identification.acceptance(metrics)` for each perturbation,
  - `first_failed_gate` is either empty for passing rows or one of the existing named dynamic-ID acceptance gates,
  - report and figures exist,
  - metadata records perturbation levels and seed.
- Depends on: T20
- Done when: `python experiments/validate_parameter_id_robustness.py` prints `parameter-ID robustness validation: PASS`.
- Parallel group: D

### [x] T22 - Update ignored artifact exceptions
- Files: `.gitignore`
- Do: add narrow exceptions for:
  - `runs/ekf_study/**`,
  - `runs/failure_mode_fmea/**`,
  - `runs/parameter_id_robustness/**`,
  - new item 7-9 report figures.
- Depends on: T07, T12, T20
- Done when: `git status --short --ignored` shows intended new artifacts as trackable and unrelated caches still ignored.
- Parallel group: E

### [x] T23 - Wire item 7 into `run_all.sh`
- Files: `run_all.sh`
- Do: add EKF study and validator after controller comparison or after the dynamic-ID validation block:
  - `python experiments/ekf_study.py`
  - `python experiments/validate_ekf_study.py`
- Depends on: T08
- Done when: the command ordering is reviewed and the default run clearly includes the EKF validator without requiring `RUN_ROBUSTNESS=1`.
- Parallel group: E

### [x] T24 - Gate heavier robustness studies in `run_all.sh`
- Files: `run_all.sh`
- Do: add:
  - `if [[ "${RUN_ROBUSTNESS:-0}" == "1" ]]; then ... fi`
  for FMEA and parameter-ID robustness scripts and validators.
- Depends on: T13, T21
- Done when: default `run_all.sh` does not run the heavy sweeps, and `RUN_ROBUSTNESS=1 ./run_all.sh` would include them.
- Parallel group: E

### [x] T25 - Update review tracker statuses
- Files: `GitHub Review Items/README.md`
- Do: after artifacts validate, mark:
  - item 7 Done with `reports/ekf_study.md`,
  - item 8 Done with `reports/failure_mode_fmea.md`,
  - item 9 Done with `reports/parameter_id_robustness.md`.
  Update Recommended Next Work to item 10 or the vehicle-design package depending on current tracker status.
- Depends on: T08, T13, T21
- Done when: tracker summary table and item sections agree.
- Parallel group: E

### [x] T26 - Update README report links
- Files: `README.md`
- Do: add one concise sentence near the Project Modeling Workflow section linking:
  - `reports/ekf_study.md`,
  - `reports/failure_mode_fmea.md`,
  - `reports/parameter_id_robustness.md`.
- Depends on: T25
- Done when: README names the three new study reports.
- Parallel group: E

### [x] T27 - Run item 7-9 quality gates
- Files: none
- Do: run:
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python -m compileall -q gym/roboracer experiments`
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python experiments/validate_noise_helpers.py`
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python experiments/validate_estimation_helpers.py`
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python experiments/validate_ekf_study.py`
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python experiments/validate_failure_mode_fmea.py`
  - `env PYTHONPATH=/Users/redhose/Documents/Codex/F1TENTH-current/gym /Users/redhose/ENTER/envs/f1tenth-gym/bin/python experiments/validate_parameter_id_robustness.py`
- Depends on: T22, T23, T24, T25, T26
- Done when: all commands pass and outputs are recorded in this plan.
- Parallel group: final

### [x] T28 - Final integration review
- Files: `docs/specs/items-7-9-estimation-robustness/plan.md`
- Do: verify traceability table, update task checkboxes, and record final commit hash after implementation.
- Depends on: T27
- Done when: this plan has implementation notes and all tasks are checked off.
- Parallel group: final

## Traceability

| Requirement | Tasks |
| --- | --- |
| FR-7A | T01, T02, T05 |
| FR-7B | T03, T04, T05 |
| FR-7C | T06, T07, T08 |
| FR-8A | T09, T10, T13 |
| FR-8B | T11, T12, T13 |
| FR-8C | T12, T13 |
| FR-9A | T14, T15, T16, T17 |
| FR-9B | T18, T19, T20, T21 |
| FR-9C | T18, T20, T21 |
| FR-X | T22, T23, T24, T25, T26, T27, T28 |

## Execution Notes

- Recommended order: complete shared helpers first (`T01`-`T04`), then run item 7 (`T05`-`T08`), item 8 (`T09`-`T13`), item 9 (`T14`-`T21`), then integration tasks (`T22`-`T28`).
- Parallelizable groups after setup:
  - Group B: EKF study tasks after shared helpers.
  - Group C: FMEA tasks after failure definitions and EKF noise/dropout traces exist; this group is not independent of Group B because `T10` depends on `T05`.
  - Group D: parameter-ID robustness after fitting refactor and noise helpers.
- Risk: T15 touches the existing accepted parameter-ID pipeline. Preserve current CLI outputs first, then add robustness reuse.
- Risk: EKF can be made to look artificially good if it updates on ground truth. Measurements must use `meas_*` degraded columns; metrics must compare estimates against original ground-truth columns.
- Risk: EKF results are dominated by `Q` and `R`. Set `R` mechanically from injected measurement noise and record the fixed `Q` model-uncertainty table in metadata before looking at results.
- Risk: if high perturbation levels do not fail acceptance gates, report degradation trends honestly and add a stronger `combined_high` perturbation only if it is documented in metadata.
- Implementation note: the reusable identification contract lives in `gym/roboracer/identification.py`, not under `experiments/`, because experiment scripts are not importable as a package under the repo's current run pattern.

## Implementation Results

- `python -m compileall -q gym/roboracer experiments`: PASS
- `experiments/validate_controller_comparison.py`: PASS
- `experiments/validate_dynamic_parameter_identification.py`: PASS
- `experiments/validate_noise_helpers.py`: PASS
- `experiments/validate_estimation_helpers.py`: PASS
- `experiments/validate_ekf_study.py`: PASS
- `experiments/validate_failure_mode_fmea.py`: PASS
- `experiments/validate_parameter_id_robustness.py`: PASS
- Item 7 artifacts: `runs/ekf_study/`, `reports/ekf_study.md`, EKF figures.
- Item 8 artifacts: `runs/failure_mode_fmea/`, `reports/failure_mode_fmea.md`, FMEA figures.
- Item 9 artifacts: `runs/parameter_id_robustness/`, `reports/parameter_id_robustness.md`, parameter-ID robustness figures.
- Final commit: recorded in git history for `Add estimation and robustness studies`.
