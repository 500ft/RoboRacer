# Item 11 ROS-Bag Validation — Test Report
Date: 2026-06-21
Status: passed locally; external publication/container checks pending

## Acceptance coverage

| Criterion | Test | Status |
| --- | --- | --- |
| Manifest chain | `python experiments/test_bag_evidence.py` | pass |
| Converter behavior | `python experiments/test_rosbag_to_telemetry.py` | pass |
| Enriched ROS run | native conversion, validator, preflight, and fit | pass |
| Upstream ROS run | odom/drive native conversion and validator | pass |
| Offline regression | `python experiments/validate_item11.py --strict` | pass |

## Full gates

- `python -m compileall -q experiments gym/roboracer ros2_ws/src/f1tenth_modeling` — pass
- ROS package `colcon build` — pass
- `run_all.sh` — pass
- parameter-ID robustness regeneration and validator — pass
- pinned Docker image build/run — not executed because the local Docker daemon did not become available
- GitHub release asset verification — pending because `gh` authentication is unavailable
