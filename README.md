# Autonomous Racing Systems

Vehicle modeling, control, telemetry, and sensor-mount engineering for a
F1TENTH-scale autonomous race car.

[![CI](https://github.com/500ft/autonomous-racing-systems/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/500ft/autonomous-racing-systems/actions/workflows/ci.yml)
[![Docker](https://github.com/500ft/autonomous-racing-systems/actions/workflows/docker.yml/badge.svg?branch=main)](https://github.com/500ft/autonomous-racing-systems/actions/workflows/docker.yml)
[![Evidence: simulation and nominal CAD](https://img.shields.io/badge/evidence-simulation%20%2B%20nominal%20CAD-465B70)](#evidence-snapshot)
[![License: MIT](https://img.shields.io/badge/license-MIT-276C6B)](LICENSE)

[Start here](docs/START_HERE.md) · [Results](reports/final_report.md) ·
[Quick start](#quick-start) · [Documentation](#documentation) ·
[Contribute](CONTRIBUTING.md)

![Conceptual overview of the modeling, control, telemetry, and mechanical evidence paths](docs/media/project-overview.svg)

*Project overview, not a photograph, CAD assembly, or physical test result.*

## About

An autonomous vehicle needs more than a controller that completes one lap.
Its models must explain the recorded motion, its telemetry must be usable by
other tools, and its sensor mounting must meet a defensible mechanical design.

This repository connects those tasks in two engineering lanes:

- **Vehicle systems:** dynamics replay, parameter identification, controller
  comparisons, state estimation, and a shared Gym/ROS 2 telemetry format.
- **Mechanical design:** a LiDAR-mast load case, hand calculations, finite
  element analysis, nominal parametric CAD, and a physical-test contract.

The result is a reviewable analysis pipeline with source-linked reports, not
a claim of a field-validated race car. The project retains its
[F1TENTH/RoboRacer lineage](docs/upstream_roboracer_sources.md); package and ROS
interface names are unchanged by the repository rename.

## Evidence snapshot

| Engineering result | What the repository demonstrates | Source |
| --- | --- | --- |
| Vehicle identification | Dynamic bicycle-model fitting with a held-out telemetry segment; simulator data, not physical vehicle identification | [Identification study](reports/dynamic_parameter_identification.md) |
| Control and estimation | Pure pursuit, LQR, MPC, and EKF comparisons under documented simulation scenarios | [Controllers](reports/controller_comparison.md), [EKF](reports/ekf_study.md) |
| Telemetry integration | ROS 2 bag conversion with portable, simulator-backed regression captures | [Bridge evidence](evidence/item11/report.md) |
| Mast redesign | Selected nominal FEA predicts a 285.5 Hz first mode; 174.7 Hz belongs to the rejected baseline hand model | [Mechanical analysis](docs/design/16_mechanical_design_analysis.md), [FEA output](runs/mast_fea/fea_summary.txt) |
| Parametric geometry | A nominal mast tube regenerates from its parameter register and survives STEP round-trip checks | [Generator](cad/generate.py), [Geometry contract](cad/contract.json) |
| Physical compliance | Test protocol and evidence evaluator exist; measured agreement has not been established | [Frozen protocol](docs/specs/mast-physical-validation/design.md) |

![Identified bicycle-model yaw-rate and slip-angle predictions against simulator telemetry, with the held-out segment marked](reports/figures/dynamic_parameter_fit.png)

*Simulation result: the segment right of the dashed line is held out from the
fit. Read the [study](reports/dynamic_parameter_identification.md) for the split
and limitations; [figure lineage](docs/data-and-figures.md) identifies the inputs
and generator. This is not independent physical-vehicle validation.*

## Quick start

For a bounded first check, use the portable report environment. This path
does not launch ROS, drive a vehicle, or regenerate the full simulation study.
Prerequisites: Git and **Python 3.10**, matching the portable CI workflow.

```bash
git clone https://github.com/500ft/autonomous-racing-systems.git
cd autonomous-racing-systems
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-item11-regression.txt
python -m pip install -r requirements-report.txt
PYTHONPATH=gym python experiments/test_cad_inputs.py
PYTHONPATH=gym python experiments/test_final_report.py
```

Expected: both test commands finish with `OK`. They check registered design
inputs and source-linked report content, including a temporary PDF build;
they do not establish physical agreement or run the complete evidence suite.

The [reproduction guide](docs/START_HERE.md#reproduce-by-environment) separates
the full portable checks, legacy Gym experiments, ROS 2 integration, and pinned
CadQuery environment. Keep these environments separate: their dependency
versions intentionally differ.

## Documentation

| Start with | Use it to |
| --- | --- |
| [Reading and reproduction guide](docs/START_HERE.md) | Choose a recruiter, reviewer, or contributor route |
| [Integrated report](reports/final_report.md) | Review the modeling, controls, estimation, and mast results |
| [Data and figures](docs/data-and-figures.md) | Trace a figure back to its inputs and generator |
| [Vehicle model](docs/vehicle_model.md) | Inspect equations and assumptions |
| [Telemetry dictionary](docs/telemetry_data_dictionary.md) | Understand the shared data format |
| [Parameter inventory](docs/parameter_inventory.md) | Distinguish configured, identified, and measured inputs |
| [Fixture preparation](cad/roboracer/fixture-preparation.md) | Inspect the mast interface and metrology decisions |
| [CAD inventory](docs/CAD_ITEMS.md) | See planned parts without confusing them with completed geometry |
| [Review index](docs/REVIEW_READY.md) | Find verification records and unresolved gates |

```text
gym/          F1TENTH simulator package and dynamics
experiments/  replay, identification, control, telemetry, and mast checks
reports/      engineering reports and result figures
runs/         study inputs, generated metrics, and solver summaries
ros2_ws/      f1tenth_modeling ROS 2 sidecar
cad/          parameter-driven nominal geometry and contract tests
evidence/     provenance and portable regression captures
docs/         models, interfaces, test protocols, and reading guides
```

## Next engineering gate

The next mechanical result is **static mast compliance**, not another render.
Resolve the actual mount, tip assembly, load height, and fixture observability;
then freeze inspection-linked as-built predictions before applying campaign
loads. The [measurement contract](docs/CAD_MEASUREMENT_CONTRACT.md) specifies
fixture stiffness, root-motion observations, and uncertainty requirements.

The existing ±15% static agreement band is **not** a modal tap-test criterion.
Sensor/cable mass and the installed thermal mounting arrangement also need
confirmation before the nominal FEA can represent the built assembly.

Physical vehicle telemetry, a completed mounting fixture, and measured mast
compliance remain outside the demonstrated results. Nominal STEP geometry
does not close any of those gates. The [review index](docs/REVIEW_READY.md)
and existing task ledger retain the detailed work status.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing models, evidence, or
generated outputs. A useful pull request identifies the affected contract,
records its environment and checks, and links the result to its inputs.

Use [issues](https://github.com/500ft/autonomous-racing-systems/issues) for a
reproducible defect or a scoped engineering proposal. Do not substitute a
simulation output for a pending physical measurement.

## Attribution and license

Released under the [MIT License](LICENSE), retaining the original simulator
copyright notice. The [upstream source register](docs/upstream_roboracer_sources.md)
records reference repositories, licenses, and revision pins.

When citing this work, identify the repository revision and the particular
report or dataset used; cite upstream work separately where applicable. The
[repository identity note](docs/REPOSITORY_IDENTITY.md) explains historical names
and preserves the distinction between project branding and software APIs.
