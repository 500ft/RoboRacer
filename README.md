![Python 3.8 3.9](https://github.com/500ft/F1TENTH/actions/workflows/ci.yml/badge.svg)
![Docker](https://github.com/500ft/F1TENTH/actions/workflows/docker.yml/badge.svg)
# The F1TENTH Gym environment

This is the repository of the F1TENTH Gym environment.

## Project Modeling Workflow

This fork keeps F1TENTH Gym as the offline modeling and validation baseline:

```text
Gym experiment
-> CSV telemetry
-> kinematic/dynamic replay
-> validation metrics
-> reports and figures
```

The current modeling work includes integrator comparison, vehicle-model derivation, kinematic replay, known-parameter dynamic replay, SysID steering excitation, held-out identification of Gym's nonlinear `C_Sf` and `C_Sr` coefficients, and controller studies for pure pursuit, LQR, and constrained MPC.

Run and validate the controlled Gym parameter identification:

```bash
python experiments/fit_dynamic_parameters.py
python experiments/validate_dynamic_parameter_identification.py
```

The fitting report is at `reports/dynamic_parameter_identification.md`. Controller reports are at `reports/pure_pursuit_sweep.md`, `reports/lqr_controller.md`, `reports/mpc_controller.md`, and `reports/controller_comparison.md`. A physical RoboRacer vehicle requires its own excitation dataset and held-out validation before its identified parameters are accepted.

## ROS 2 / RoboRacer Compatibility

RoboRacer is the current continuation of the F1TENTH ecosystem. This repository adds a ROS 2 sidecar package at:

```text
ros2_ws/src/f1tenth_modeling
```

Build from a ROS 2 environment:

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

Run the ROS 2 Gym bridge and SysID excitation node:

```bash
ros2 launch f1tenth_modeling sysid_excitation.launch.py
```

Convert a ROS 2 bag using standard RoboRacer-style topics:

```bash
python experiments/rosbag_to_telemetry.py \
  --bag path/to/rosbag \
  --output runs/ros2_sysid_steering_excitation/telemetry.csv \
  --metadata runs/ros2_sysid_steering_excitation/metadata.json \
  --quality runs/ros2_sysid_steering_excitation/quality_metrics.csv
```

Validate the converted telemetry:

```bash
python experiments/validate_sysid_excitation.py \
  --telemetry runs/ros2_sysid_steering_excitation/telemetry.csv \
  --quality runs/ros2_sysid_steering_excitation/quality_metrics.csv
```

The converter uses `/ego_racecar/odom` and `/drive` as the primary standard topics. The project-specific `/f1tenth/internal_state` topic is optional enrichment for achieved steering and slip angle.

Verified ROS 2 environment guides:

- [RoboStack Humble on macOS](docs/ros2_verification_robostack_macos.md)
- [Official ROS 2 Humble on Ubuntu 22.04](docs/ros2_verification_ubuntu_humble.md)
- [Environment comparison and switching guide](docs/ros2_verification_summary.md)

This project is still under heavy development.

You can find the [documentation](https://f1tenth-gym.readthedocs.io/en/latest/) of the environment here.

## Quickstart
We recommend installing the simulation inside a virtualenv. You can install the environment by running:

```bash
virtualenv gym_env
source gym_env/bin/activate
git clone https://github.com/f1tenth/f1tenth_gym.git
cd f1tenth_gym
pip install -e .
```

Then you can run a quick waypoint follow example by:
```bash
cd examples
python3 waypoint_follow.py
```

A Dockerfile is also provided with support for the GUI with nvidia-docker (nvidia GPU required):
```bash
docker build -t f1tenth_gym_container -f Dockerfile .
docker run --gpus all -it -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix f1tenth_gym_container
````
Then the same example can be ran.

## Known issues
- Library support issues on Windows. You must use Python 3.8 as of 10-2021
- On MacOS Big Sur and above, when rendering is turned on, you might encounter the error:
```
ImportError: Can't find framework /System/Library/Frameworks/OpenGL.framework.
```
You can fix the error by installing a newer version of pyglet:
```bash
$ pip3 install pyglet==1.5.20
```
And you might see an error similar to
```
f110-gym 0.2.1 requires pyglet<1.5, but you have pyglet 1.5.20 which is incompatible.
```
which could be ignored. The environment should still work without error.

## Citing
If you find this Gym environment useful, please consider citing:

```
@inproceedings{okelly2020f1tenth,
  title={F1TENTH: An Open-source Evaluation Environment for Continuous Control and Reinforcement Learning},
  author={O’Kelly, Matthew and Zheng, Hongrui and Karthik, Dhruv and Mangharam, Rahul},
  booktitle={NeurIPS 2019 Competition and Demonstration Track},
  pages={77--89},
  year={2020},
  organization={PMLR}
}
```
