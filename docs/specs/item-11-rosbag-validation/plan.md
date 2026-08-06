# Item 11 ROS-Bag Validation — Implementation Plan
Design: ./design.md
Status: in-progress
Date: 2026-06-21

## Quality gates

- Syntax: `python -m compileall -q experiments gym/roboracer ros2_ws/src/f1tenth_modeling`
- Converter tests: `python experiments/test_rosbag_to_telemetry.py`
- Existing validators: commands in `run_all.sh`
- ROS build/run: `bash scripts/verify_ros2_robostack_macos.sh`

## Tasks

- [x] T01 — Add manifest schema, local dry-run publisher, verifier, and tests. (`python experiments/test_bag_evidence.py`)
- [x] T02 — Make conversion byte deterministic and add native sampling/timing diagnostics. (`python experiments/test_rosbag_to_telemetry.py`)
- [x] T03 — Extend internal state with simulator time and add command-only excitation. (ROS package builds; both capture launches ran)
- [x] T04 — Add steering, RTF, excitation, and identifiability screening metrics. (`experiments/item11_preflight.py` passes)
- [x] T05 — Generalize identification paths and oracle policy without changing defaults. (Gym and no-oracle modes tested)
- [x] T06 — Capture, convert, and validate the enriched ROS-backed bag. (19.94 s overlap, RTF 0.9995, full fit passes)
- [x] T07 — Capture, convert, and validate the pinned upstream standard-topic bag. (19.91 s overlap, RTF proxy 0.9998, ingestion gates pass)
- [x] T08 — Produce committed item 11 evidence and report. (`evidence/item11/report.md`)
- [x] T09 — Add ROS-free regression validation to CI and `run_all.sh`. (portable and strict local modes pass)
- [ ] T10 — Run full quality gates and record results. (all repository/ROS gates pass; pinned Docker execution and release publication remain externally blocked)

## Traceability

| Requirement | Tasks |
| --- | --- |
| Chain of custody | T01, T06, T07 |
| Deterministic conversion and diagnostics | T02 |
| Simulator time and source-specific contracts | T03, T06, T07 |
| Scientifically screened identification | T04, T05, T06 |
| Evidence report | T08 |
| Durable ROS-free validation | T09, T10 |
