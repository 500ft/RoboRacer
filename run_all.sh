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

echo "All experiments completed."
