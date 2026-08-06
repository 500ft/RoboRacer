# Item 12 Design-Review Report - Test Report

Date: 2026-07-24
Suite: `python experiments/test_final_report.py` - PASS (6 tests)

Repository regression suites:

- `env PYTHONPATH=gym python experiments/test_rosbag_to_telemetry.py` - PASS
- `env PYTHONPATH=gym python experiments/test_bag_evidence.py` - PASS
- `env PYTHONPATH=gym python experiments/validate_item11.py` - PASS
- `env PYTHONPATH=gym python experiments/test_mast_physical_validation.py` -
  PASS (5 tests)
- `python -m py_compile scripts/build_final_report.py
  experiments/test_final_report.py` - PASS
- `git diff --check` - PASS

## Acceptance criteria coverage

| Criterion | Test(s) | Status |
| --- | --- | --- |
| No unresolved report markers | `test_report_has_no_unresolved_markers` | PASS |
| 10-20 rendered pages | `test_report_builds_review_length_pdf` | PASS (15 pages) |
| Mechanical number traceability | `test_mechanical_headlines_trace_to_committed_artifacts` | PASS |
| Simulation number traceability | `test_simulation_headlines_trace_to_committed_artifacts` | PASS |
| Physical gate remains honest | `test_physical_gate_is_registered_and_pending` | PASS |
| Local references resolve | `test_local_report_references_exist` | PASS |

## Deviations from plan

The source roadmap expected a render/visual review but did not prescribe a PDF
toolchain. A portable ReportLab builder and checked PDF were added so the gate
is executable from a clean checkout.

CSV traceability checks parse source fields numerically, apply the report's
declared rounding, and convert solver seconds to reported milliseconds. This
avoids treating correct rounded claims as literal-string mismatches.

## Deferred / known gaps

Parametric CAD, fabrication, as-built inspection, and physical compliance data
are downstream Nodes 11-12 and remain explicitly pending.
