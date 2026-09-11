# Start here — Autonomous Racing Systems

The [README](../README.md) is the project overview. This guide identifies the
shortest path to a useful review without requiring every environment or study.

## Choose a reading path

| Audience | Suggested route | What to look for |
| --- | --- | --- |
| Recruiter — about two minutes | [Evidence snapshot](../README.md#evidence-snapshot) → [integrated report](../reports/final_report.md) → [mechanical design](design/16_mechanical_design_analysis.md) | Model-to-data reasoning, control trade-offs, and design iteration |
| Technical reviewer | [Data and figures](data-and-figures.md) → one result and its raw inputs → [review index](REVIEW_READY.md) | Provenance, model assumptions, split boundaries, counterexamples, and limitations |
| Contributor | [Contributing](../CONTRIBUTING.md) → environment below → relevant contract and tests | A bounded change whose evidence can be reproduced |

## Read the two engineering lanes correctly

The vehicle lane uses F1TENTH Gym telemetry and simulator-backed ROS 2 captures.
A held-out segment tests prediction on that segment; it is not evidence of
transfer to a real vehicle. See the [identification study](../reports/dynamic_parameter_identification.md),
[controller comparison](../reports/controller_comparison.md), and
[EKF study](../reports/ekf_study.md).

The mechanical lane progresses from an idealized beam to FEA and a regenerable
nominal tube. The selected 285.5 Hz FEA result and rejected 174.7 Hz hand-model
baseline describe different designs. Neither is a measured modal frequency.
The [fixture preparation](../cad/roboracer/fixture-preparation.md) explains the
next interface and uncertainty work; the [physical protocol](specs/mast-physical-validation/design.md)
currently concerns static compliance only.

The [figure guide](data-and-figures.md) and
[machine-readable manifest](figure-manifest.json) connect plots to generators
and source artifacts. A test passing, a CAD export succeeding, and a physical
validation verdict are different observations.

## Reproduce by environment

Run the following from the repository root unless a command explicitly changes
directory. Do not combine the four environments into one installation.

### Portable evidence checks — Python 3.10

Use the [README setup](../README.md#quick-start), then run the same six commands
listed in the [CI workflow](../.github/workflows/ci.yml):

```bash
PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py
PYTHONPATH=gym python experiments/test_bag_evidence.py
PYTHONPATH=gym python experiments/validate_item11.py
PYTHONPATH=gym python experiments/test_mast_physical_validation.py
PYTHONPATH=gym python experiments/test_cad_inputs.py
PYTHONPATH=gym python experiments/test_final_report.py
```

Expected: zero exit status from every command; unittest commands report `OK`.
These checks exercise portable captures, invalid-input controls, campaign
admission rules, and the report build. They do not require a running ROS graph,
real vehicle, or physical test apparatus.

### Nominal CAD — separate pinned environment

The [CAD workflow](../.github/workflows/cad-geometry.yml) consumes
[direct package constraints](../cad/requirements.lock). They are not a complete
transitive, platform-specific environment lock. With Conda available:

```bash
conda create -n racing-cad -c conda-forge --strict-channel-priority --file cad/requirements.lock
conda activate racing-cad
python cad/input_requests.py --check
python cad/generate.py --parameters cad/roboracer/parameters.csv --output /tmp/racing-cad-review
python -m pytest cad/tests -q
```

The generator writes `mast_tube.step` and `geometry.json` to the chosen output
directory. The report records parameter and STEP hashes, tool versions, solid
metrics, and STEP reimport metrics. Tests compare them with
[the geometry contract](../cad/contract.json).

This is nominal tube geometry, not an assembled fixture. Regeneration must not
promote a design choice into a measured dimension. If a local Python environment
crashes while pytest imports `readline`, the existing environment workaround is:

```bash
python -c 'import sys,types; sys.modules["readline"]=types.ModuleType("readline"); import pytest; raise SystemExit(pytest.main(["cad/tests","-q"]))'
```

Use that only for the import problem; it is not a substitute for correcting a
failing geometry test or installing the registered toolchain.

### Legacy simulation — Python 3.9

The [Gym environment](../environment.yml) preserves the older simulator stack.
Use a separate checkout when regenerating committed results so comparisons are
not mixed with unrelated edits.

```bash
conda env create -f environment.yml
conda activate f1tenth-gym
python -m pip install -e .
./run_all.sh
```

This regenerates study artifacts and takes longer than the portable checks.
Long MPC and robustness sweeps remain explicit opt-ins:

```bash
RUN_FULL_MPC=1 RUN_ROBUSTNESS=1 ./run_all.sh
```

See [data and figures](data-and-figures.md) for a single-study command instead
of rerunning the full chain. GUI rendering additionally requires OpenGL.

### ROS 2 integration — platform-specific

Read [Ubuntu Humble setup](ros2_verification_ubuntu_humble.md) or
[RoboStack macOS setup](ros2_verification_robostack_macos.md) first. The sidecar is
[`f1tenth_modeling`](../ros2_ws/src/f1tenth_modeling); its package name does not
change with the repository title. The [telemetry dictionary](telemetry_data_dictionary.md)
defines standard inputs and optional simulator enrichment.

Build in the configured ROS environment:

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

Do not launch excitation against a physical vehicle as a quickstart. Select
the intended simulator or hardware context deliberately and follow the setup
notes. Portable regression success does not verify a new ROS installation.

## Review and contribute

Choose one result, follow its lineage to the committed inputs, run the relevant
checks, and state what your reproduction did and did not establish. Keep raw
captures, parameter registers, and generated results distinguishable.

The [review index](REVIEW_READY.md) and [existing task ledger](SPRINT_TASKS.csv)
are the status sources; this guide does not maintain a competing checklist.
Read the [upstream register](upstream_roboracer_sources.md),
[license](../LICENSE), and [contribution rules](../CONTRIBUTING.md) before reusing
code or changing an interface. Record the source commit in any external review
or citation.
