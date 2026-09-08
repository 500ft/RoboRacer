# RR-CAD-01 verification — 2026-09-08

Base: `8bf86b6113d52f134abc0fb0cfef7eb0fa64beda`. Candidate identity is the
containing PR head. This is source reconciliation, not CAD or physical validation.

Deliverables: [30-row register](../../cad/roboracer/parameters.csv),
[input reconciliation](../../cad/roboracer/design-inputs.md), and
[three consistency tests](../../experiments/test_cad_inputs.py).
The authoritative status remains [CAD_TASKS.csv](../../docs/CAD_TASKS.csv);
the historical sprint ledger is byte-preserved.

## Baseline and reproduction

Runtime: Python 3.11.8 (`/Users/redhose/ENTER/bin/python`). The unchanged base was
checked at `/private/tmp/daily-baseline-20260908-RoboRacer` after the input draft
existed. All five portable baseline commands below passed (exit 0); no candidate
files were copied into that detached baseline worktree.

Run from the repository root:

```sh
PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py
PYTHONPATH=gym python experiments/test_bag_evidence.py
PYTHONPATH=gym python experiments/validate_item11.py
PYTHONPATH=gym python experiments/test_mast_physical_validation.py
PYTHONPATH=gym python experiments/test_final_report.py
python experiments/test_cad_inputs.py
```

Baseline outputs: synthetic rosbag conversion PASS; bag evidence PASS; Item 11
offline-portable PASS; 20 mast protocol tests PASS; six final-report tests PASS.
The three new tests pass and check source paths/evidence states, ideal-tube
stiffness and mass arithmetic, tip-mass accounting, clean simulated-load provenance,
and the intentionally distinct model/chassis wheelbases.

The 775.984 N/mm beam stiffness and 0.005155 mm low-load displacement are derived
planning values, not measurements. No FEA solve, ROS installation, hardware bag,
STEP export or independent human review occurred. Vendor-nominal values remain
reported from existing repository sources rather than freshly verified vendor data.

All six commands above were rerun on the candidate and exited 0;
[captured outputs](checks.json). The embedded CAD validator passed (eight tasks,
four rejected invalid mutations, dependency/link/sprint preservation PASS).

Also run the embedded Python validator in
[CAD_PLAN_CHECKS.md](../../docs/CAD_PLAN_CHECKS.md) and `git diff --check`.
CI now runs the new input test. Owner stock/clamp/fixture/metrology approval remains
open; as-built predictions must be committed and pushed before campaign loads.
