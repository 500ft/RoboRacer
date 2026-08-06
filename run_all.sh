#!/usr/bin/env bash
# Reproduce the F1TENTH modeling pipeline end-to-end, in dependency order.
# Run from a shell with the f1tenth-gym conda environment active.
set -euo pipefail
cd "$(dirname "$0")"

# Baseline: RK4 vs Euler on the scripted lap.
python experiments/run_scripted_lap.py
python experiments/plot_integrator_comparison.py
python experiments/validate_first_run.py

# RK4 timestep convergence sweep.
python experiments/integrator_convergence.py

# Model replays against the recorded Gym telemetry.
python experiments/dynamic_model_replay.py
python experiments/model_vs_gym_comparison.py

# SysID excitation dataset and quality gates.
python experiments/sysid_steering_excitation.py
python experiments/validate_sysid_excitation.py

# Dynamic parameter identification and held-out validation.
python experiments/fit_dynamic_parameters.py
python experiments/validate_dynamic_parameter_identification.py
python experiments/validate_noise_helpers.py
python experiments/validate_estimation_helpers.py
python experiments/validate_item11.py

# Controller tuning and comparison at RK4 dt=0.002 s with 100 Hz zero-order-held commands.
python experiments/pure_pursuit_sweep.py
python experiments/validate_pure_pursuit_sweep.py
python experiments/lqr_controller.py
python experiments/validate_lqr_controller.py

if [[ "${RUN_FULL_MPC:-0}" == "1" ]]; then
  python experiments/mpc_controller.py
  python experiments/validate_mpc_controller.py
  python experiments/controller_comparison.py
  python experiments/validate_controller_comparison.py
else
  echo "Skipping full MPC/controller comparison. Set RUN_FULL_MPC=1 to run."
fi

# Estimation study uses the tuned pure-pursuit baseline and runs in the default repro path.
python experiments/ekf_study.py
python experiments/validate_ekf_study.py

if [[ "${RUN_ROBUSTNESS:-0}" == "1" ]]; then
  python experiments/failure_mode_fmea.py
  python experiments/validate_failure_mode_fmea.py
  python experiments/parameter_id_robustness.py
  python experiments/validate_parameter_id_robustness.py
else
  echo "Skipping FMEA and parameter-ID robustness sweeps. Set RUN_ROBUSTNESS=1 to run."
fi

echo "All experiments completed."
