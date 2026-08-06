# Contributing

RoboRacer contains a legacy simulator, a portable telemetry/report toolchain,
ROS 2 integration, and generated research artifacts. Use the environment that
matches the part you are changing.

## Legacy Gym environment

```bash
conda env create -f environment.yml
conda activate f1tenth-gym
python -m pip install -e .
```

## Portable regression environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-item11-regression.txt
python -m pip install -r requirements-report.txt
```

Run the CI-aligned checks:

```bash
PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py
PYTHONPATH=gym python experiments/test_bag_evidence.py
PYTHONPATH=gym python experiments/validate_item11.py
PYTHONPATH=gym python experiments/test_mast_physical_validation.py
PYTHONPATH=gym python experiments/test_final_report.py
```

## Experiment changes

- Keep an experiment, its validation script, generated run data, figure, and
  report synchronized.
- Record whether each parameter is configured, identified from simulator data,
  identified from vehicle data, or measured physically.
- Do not present simulator coefficient recovery as vehicle identification.
- Do not replace pending mast or vehicle measurements with FEA output.
- Keep long MPC and robustness sweeps opt-in in the default pipeline.

## ROS 2 changes

Preserve the standard-topic path using `/ego_racecar/odom` and `/drive`.
Project-specific internal state may enrich a simulator study but should not be a
requirement for a normal RoboRacer bag.

## Pull requests

List the environment used, commands run, generated artifacts changed, and
whether the change affects simulation, ROS 2 ingestion, mechanical analysis, or
physical-test preparation.
